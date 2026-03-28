export type JsonPrimitive = string | number | boolean | null;

export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];

export interface JsonObject {
  [key: string]: JsonValue;
}

export type ToolName =
  | "web_search"
  | "file_read"
  | "file_write"
  | "calendar_read"
  | "calendar_write"
  | "memory_write"
  | "code_execute";

export const KNOWN_TOOL_NAMES: readonly ToolName[] = [
  "web_search",
  "file_read",
  "file_write",
  "calendar_read",
  "calendar_write",
  "memory_write",
  "code_execute",
];

export function isToolName(value: string): value is ToolName {
  return KNOWN_TOOL_NAMES.includes(value as ToolName);
}

export interface ToolCallRequest {
  request_id?: string;
  tool_name: string;
  args: JsonObject;
  session_context: JsonObject;
}

export type ToolFailureClassification =
  | "TRANSIENT"
  | "PERMANENT"
  | "POLICY_VIOLATION";

export interface ToolCallResult {
  ok: true;
  type: "TOOL_CALL_RESULT";
  request_id: string;
  tool_name: ToolName;
  output: JsonValue;
  attempt_count: number;
  started_at: string;
  completed_at: string;
}

export interface ToolCallError {
  ok: false;
  type: "TOOL_CALL_ERROR";
  request_id: string;
  tool_name: string;
  code: string;
  message: string;
  classification: ToolFailureClassification;
  retryable: boolean;
  details?: JsonValue;
  started_at: string;
  completed_at: string;
}

export type ToolDispatchResult = ToolCallResult | ToolCallError;

export function createToolCallResult(params: {
  request_id: string;
  tool_name: ToolName;
  output: JsonValue;
  attempt_count: number;
  started_at: string;
  completed_at: string;
}): ToolCallResult {
  return {
    ok: true,
    type: "TOOL_CALL_RESULT",
    request_id: params.request_id,
    tool_name: params.tool_name,
    output: params.output,
    attempt_count: params.attempt_count,
    started_at: params.started_at,
    completed_at: params.completed_at,
  };
}

export function createToolCallError(params: {
  request_id: string;
  tool_name: string;
  code: string;
  message: string;
  classification: ToolFailureClassification;
  details?: JsonValue;
  started_at: string;
  completed_at: string;
}): ToolCallError {
  return {
    ok: false,
    type: "TOOL_CALL_ERROR",
    request_id: params.request_id,
    tool_name: params.tool_name,
    code: params.code,
    message: params.message,
    classification: params.classification,
    retryable: params.classification === "TRANSIENT",
    details: params.details,
    started_at: params.started_at,
    completed_at: params.completed_at,
  };
}
