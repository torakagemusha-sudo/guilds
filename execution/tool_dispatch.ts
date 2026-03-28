import {
  JsonObject,
  JsonValue,
  ToolCallRequest,
  ToolDispatchResult,
  ToolFailureClassification,
  ToolName,
  createToolCallError,
  createToolCallResult,
  isToolName,
} from "./tool_result";
import {
  ToolAdapters,
  ToolHandler,
  ToolHandlerError,
  ToolHandlerMap,
  buildDefaultToolHandlers,
} from "./tool_handlers";

type PolicyDecision = "ALLOW" | "DENY" | "REQUIRE_APPROVAL";

export interface PolicyEvaluateInput {
  request_id: string;
  tool_name: ToolName;
  args: JsonObject;
  session_context: JsonObject;
}

export interface PolicyEvaluateOutput {
  decision: PolicyDecision;
  reason?: string;
  policy_trace?: JsonValue;
}

export interface ApprovalQueueRecord {
  request_id: string;
  tool_name: ToolName;
  args: JsonObject;
  session_context: JsonObject;
  reason?: string;
  queued_at: string;
  timeout_ms: number;
}

export interface ApprovalResolution {
  approved: boolean;
  reason?: string;
  resolved_at: string;
}

export interface RetryPolicyInput {
  request_id: string;
  tool_name: ToolName;
  attempt: number;
  error: unknown;
  classification: ToolFailureClassification;
}

export interface RetryPolicyOutput {
  retry: boolean;
}

export interface DispatcherDependencies {
  policy_evaluate(input: PolicyEvaluateInput): Promise<PolicyEvaluateOutput>;
  enqueue_operator_approval(record: ApprovalQueueRecord): Promise<void>;
  wait_for_operator_approval(params: {
    request_id: string;
    timeout_ms: number;
  }): Promise<ApprovalResolution>;
  audit_log_write(entry: {
    event:
      | "TOOL_CALL_RECEIVED"
      | "TOOL_CALL_DENIED"
      | "TOOL_CALL_APPROVAL_REQUIRED"
      | "TOOL_CALL_APPROVAL_RESULT"
      | "TOOL_CALL_DISPATCHED"
      | "TOOL_CALL_COMPLETED"
      | "TOOL_CALL_FAILED";
    request_id: string;
    tool_name: string;
    timestamp: string;
    payload?: JsonValue;
  }): Promise<void>;
  tool_effect_log_write(entry: {
    request_id: string;
    tool_name: ToolName;
    timestamp: string;
    output: JsonValue;
    attempt_count: number;
  }): Promise<void>;
  evidence_registry_emit(entry: {
    request_id: string;
    tool_name: ToolName;
    timestamp: string;
    kind: "TOOL_RESULT";
    evidence: JsonValue;
  }): Promise<void>;
  retry_policy(input: RetryPolicyInput): Promise<RetryPolicyOutput>;
  now?(): string;
  make_request_id?(): string;
}

export interface ToolDispatcherOptions {
  handlers?: Partial<ToolHandlerMap>;
  adapters?: ToolAdapters;
  approval_timeout_ms?: number;
  max_attempts?: number;
}

const DEFAULT_APPROVAL_TIMEOUT_MS = 60_000;
const DEFAULT_MAX_ATTEMPTS = 3;

function defaultNow(): string {
  return new Date().toISOString();
}

function defaultRequestId(): string {
  return `tool_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function classifyToolFailure(error: unknown): {
  classification: ToolFailureClassification;
  code: string;
  message: string;
  details?: JsonValue;
} {
  if (error instanceof ToolHandlerError) {
    return {
      classification: error.classification,
      code: error.code,
      message: error.message,
      details: error.details,
    };
  }

  if (error instanceof Error) {
    return {
      classification: "TRANSIENT",
      code: "TOOL_EXECUTION_ERROR",
      message: error.message,
      details: { name: error.name },
    };
  }

  return {
    classification: "TRANSIENT",
    code: "TOOL_EXECUTION_ERROR",
    message: "Unknown tool execution failure",
  };
}

function toErrorResult(params: {
  request_id: string;
  tool_name: string;
  code: string;
  message: string;
  classification: ToolFailureClassification;
  details?: JsonValue;
  started_at: string;
  completed_at: string;
}): ToolDispatchResult {
  return createToolCallError(params);
}

async function writeAuditAndReturn(
  deps: DispatcherDependencies,
  auditEntry: Parameters<DispatcherDependencies["audit_log_write"]>[0],
  result: ToolDispatchResult,
): Promise<ToolDispatchResult> {
  await deps.audit_log_write(auditEntry);
  return result;
}

export function createToolDispatcher(
  deps: DispatcherDependencies,
  options: ToolDispatcherOptions = {},
): (request: ToolCallRequest) => Promise<ToolDispatchResult> {
  const approvalTimeoutMs = options.approval_timeout_ms ?? DEFAULT_APPROVAL_TIMEOUT_MS;
  const maxAttempts = options.max_attempts ?? DEFAULT_MAX_ATTEMPTS;
  const defaultHandlers = buildDefaultToolHandlers();
  const handlers: ToolHandlerMap = {
    ...defaultHandlers,
    ...(options.handlers ?? {}),
  } as ToolHandlerMap;
  const adapters = options.adapters ?? {};
  const now = deps.now ?? defaultNow;
  const makeRequestId = deps.make_request_id ?? defaultRequestId;

  return async (request: ToolCallRequest): Promise<ToolDispatchResult> => {
    const started_at = now();
    const request_id = request.request_id ?? makeRequestId();
    const normalizedToolName = request.tool_name;

    await deps.audit_log_write({
      event: "TOOL_CALL_RECEIVED",
      request_id,
      tool_name: normalizedToolName,
      timestamp: started_at,
      payload: {
        session_context: request.session_context,
        args: request.args,
      },
    });

    if (!isToolName(normalizedToolName)) {
      const completed_at = now();
      return writeAuditAndReturn(
        deps,
        {
          event: "TOOL_CALL_FAILED",
          request_id,
          tool_name: normalizedToolName,
          timestamp: completed_at,
          payload: { code: "UNKNOWN_TOOL" },
        },
        toErrorResult({
          request_id,
          tool_name: normalizedToolName,
          code: "UNKNOWN_TOOL",
          message: `Unknown tool '${normalizedToolName}'`,
          classification: "PERMANENT",
          started_at,
          completed_at,
        }),
      );
    }

    const tool_name: ToolName = normalizedToolName;

    const policy = await deps.policy_evaluate({
      request_id,
      tool_name,
      args: request.args,
      session_context: request.session_context,
    });

    if (policy.decision === "DENY") {
      const completed_at = now();
      return writeAuditAndReturn(
        deps,
        {
          event: "TOOL_CALL_DENIED",
          request_id,
          tool_name,
          timestamp: completed_at,
          payload: {
            reason: policy.reason ?? "Policy denied tool call",
            policy_trace: policy.policy_trace,
          },
        },
        toErrorResult({
          request_id,
          tool_name,
          code: "POLICY_DENIED",
          message: policy.reason ?? "Tool call denied by policy",
          classification: "POLICY_VIOLATION",
          details: policy.policy_trace,
          started_at,
          completed_at,
        }),
      );
    }

    if (policy.decision === "REQUIRE_APPROVAL") {
      const queued_at = now();
      await deps.enqueue_operator_approval({
        request_id,
        tool_name,
        args: request.args,
        session_context: request.session_context,
        reason: policy.reason,
        queued_at,
        timeout_ms: approvalTimeoutMs,
      });
      await deps.audit_log_write({
        event: "TOOL_CALL_APPROVAL_REQUIRED",
        request_id,
        tool_name,
        timestamp: queued_at,
        payload: { reason: policy.reason, timeout_ms: approvalTimeoutMs },
      });
      const approval = await deps.wait_for_operator_approval({
        request_id,
        timeout_ms: approvalTimeoutMs,
      });
      await deps.audit_log_write({
        event: "TOOL_CALL_APPROVAL_RESULT",
        request_id,
        tool_name,
        timestamp: approval.resolved_at,
        payload: { approved: approval.approved, reason: approval.reason },
      });
      if (!approval.approved) {
        const completed_at = now();
        return writeAuditAndReturn(
          deps,
          {
            event: "TOOL_CALL_DENIED",
            request_id,
            tool_name,
            timestamp: completed_at,
            payload: {
              reason: approval.reason ?? "Operator approval denied or timed out",
            },
          },
          toErrorResult({
            request_id,
            tool_name,
            code: "OPERATOR_APPROVAL_DENIED",
            message: approval.reason ?? "Operator approval denied or timed out",
            classification: "POLICY_VIOLATION",
            started_at,
            completed_at,
          }),
        );
      }
    }

    const handler: ToolHandler = handlers[tool_name];
    if (!handler) {
      const completed_at = now();
      return writeAuditAndReturn(
        deps,
        {
          event: "TOOL_CALL_FAILED",
          request_id,
          tool_name,
          timestamp: completed_at,
          payload: { code: "TOOL_HANDLER_NOT_FOUND" },
        },
        toErrorResult({
          request_id,
          tool_name,
          code: "TOOL_HANDLER_NOT_FOUND",
          message: `No handler registered for '${tool_name}'`,
          classification: "PERMANENT",
          started_at,
          completed_at,
        }),
      );
    }

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        await deps.audit_log_write({
          event: "TOOL_CALL_DISPATCHED",
          request_id,
          tool_name,
          timestamp: now(),
          payload: { attempt },
        });

        const output = await handler(request.args, {
          session_context: request.session_context,
          adapters,
        });
        const completed_at = now();

        const result = createToolCallResult({
          request_id,
          tool_name,
          output,
          attempt_count: attempt,
          started_at,
          completed_at,
        });

        await deps.tool_effect_log_write({
          request_id,
          tool_name,
          timestamp: completed_at,
          output,
          attempt_count: attempt,
        });
        await deps.evidence_registry_emit({
          request_id,
          tool_name,
          timestamp: completed_at,
          kind: "TOOL_RESULT",
          evidence: output,
        });

        return writeAuditAndReturn(
          deps,
          {
            event: "TOOL_CALL_COMPLETED",
            request_id,
            tool_name,
            timestamp: completed_at,
            payload: { attempt_count: attempt },
          },
          result,
        );
      } catch (error: unknown) {
        const completed_at = now();
        const classified = classifyToolFailure(error);
        const retryDecision =
          classified.classification === "TRANSIENT" && attempt < maxAttempts
            ? await deps.retry_policy({
                request_id,
                tool_name,
                attempt,
                error,
                classification: classified.classification,
              })
            : { retry: false };

        if (retryDecision.retry) {
          await deps.audit_log_write({
            event: "TOOL_CALL_FAILED",
            request_id,
            tool_name,
            timestamp: completed_at,
            payload: {
              code: classified.code,
              classification: classified.classification,
              attempt,
              retrying: true,
            },
          });
          continue;
        }

        const errorResult = toErrorResult({
          request_id,
          tool_name,
          code: classified.code,
          message: classified.message,
          classification: classified.classification,
          details: classified.details,
          started_at,
          completed_at,
        });
        return writeAuditAndReturn(
          deps,
          {
            event: "TOOL_CALL_FAILED",
            request_id,
            tool_name,
            timestamp: completed_at,
            payload: {
              code: classified.code,
              classification: classified.classification,
              attempt,
              retrying: false,
            },
          },
          errorResult,
        );
      }
    }

    const completed_at = now();
    return writeAuditAndReturn(
      deps,
      {
        event: "TOOL_CALL_FAILED",
        request_id,
        tool_name,
        timestamp: completed_at,
        payload: { code: "RETRY_EXHAUSTED" },
      },
      toErrorResult({
        request_id,
        tool_name,
        code: "RETRY_EXHAUSTED",
        message: "Retry attempts exhausted",
        classification: "TRANSIENT",
        started_at,
        completed_at,
      }),
    );
  };
}
