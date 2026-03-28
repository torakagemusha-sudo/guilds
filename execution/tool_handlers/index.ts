import { JsonObject, JsonValue, ToolFailureClassification, ToolName } from "../tool_result";

export class ToolHandlerError extends Error {
  readonly code: string;
  readonly classification: ToolFailureClassification;
  readonly details?: JsonValue;

  constructor(params: {
    code: string;
    message: string;
    classification?: ToolFailureClassification;
    details?: JsonValue;
  }) {
    super(params.message);
    this.name = "ToolHandlerError";
    this.code = params.code;
    this.classification = params.classification ?? "PERMANENT";
    this.details = params.details;
  }
}

export interface WebSearchAdapter {
  search(input: {
    query: string;
    args: JsonObject;
    session_context: JsonObject;
  }): Promise<JsonValue>;
}

export interface FileReadAdapter {
  read(input: {
    path: string;
    args: JsonObject;
    session_context: JsonObject;
  }): Promise<JsonValue>;
}

export interface FileWriteAdapter {
  write(input: {
    path: string;
    content: JsonValue;
    args: JsonObject;
    session_context: JsonObject;
  }): Promise<JsonValue>;
}

export interface CalendarReadAdapter {
  read(input: {
    args: JsonObject;
    session_context: JsonObject;
  }): Promise<JsonValue>;
}

export interface CalendarWriteAdapter {
  write(input: {
    args: JsonObject;
    session_context: JsonObject;
  }): Promise<JsonValue>;
}

export interface MemoryWriteAdapter {
  write(input: {
    key: string;
    value: JsonValue;
    args: JsonObject;
    session_context: JsonObject;
  }): Promise<JsonValue>;
}

export interface ToolAdapters {
  web_search?: WebSearchAdapter;
  file_read?: FileReadAdapter;
  file_write?: FileWriteAdapter;
  calendar_read?: CalendarReadAdapter;
  calendar_write?: CalendarWriteAdapter;
  memory_write?: MemoryWriteAdapter;
}

export interface ToolHandlerContext {
  // Intentionally minimal: handlers cannot access audit/operator state.
  session_context: JsonObject;
  adapters: ToolAdapters;
}

export type ToolHandler = (
  args: JsonObject,
  context: ToolHandlerContext,
) => Promise<JsonValue>;

export type ToolHandlerMap = Record<ToolName, ToolHandler>;

function expectStringArg(args: JsonObject, key: string, toolName: ToolName): string {
  const value = args[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new ToolHandlerError({
      code: "INVALID_ARGUMENT",
      message: `${toolName} requires a non-empty string argument '${key}'`,
      classification: "PERMANENT",
    });
  }
  return value;
}

function requireAdapter<T>(adapter: T | undefined, toolName: ToolName): T {
  if (!adapter) {
    throw new ToolHandlerError({
      code: "TOOL_NOT_CONFIGURED",
      message: `${toolName} adapter is not configured`,
      classification: "PERMANENT",
    });
  }
  return adapter;
}

export function buildDefaultToolHandlers(): ToolHandlerMap {
  return {
    web_search: async (args, context) => {
      const adapter = requireAdapter(context.adapters.web_search, "web_search");
      const query = expectStringArg(args, "query", "web_search");
      return adapter.search({ query, args, session_context: context.session_context });
    },
    file_read: async (args, context) => {
      const adapter = requireAdapter(context.adapters.file_read, "file_read");
      const path = expectStringArg(args, "path", "file_read");
      return adapter.read({ path, args, session_context: context.session_context });
    },
    file_write: async (args, context) => {
      const adapter = requireAdapter(context.adapters.file_write, "file_write");
      const path = expectStringArg(args, "path", "file_write");
      const content = args.content;
      if (content === undefined) {
        throw new ToolHandlerError({
          code: "INVALID_ARGUMENT",
          message: "file_write requires argument 'content'",
          classification: "PERMANENT",
        });
      }
      return adapter.write({ path, content, args, session_context: context.session_context });
    },
    calendar_read: async (args, context) => {
      const adapter = requireAdapter(context.adapters.calendar_read, "calendar_read");
      return adapter.read({ args, session_context: context.session_context });
    },
    calendar_write: async (args, context) => {
      const adapter = requireAdapter(context.adapters.calendar_write, "calendar_write");
      return adapter.write({ args, session_context: context.session_context });
    },
    memory_write: async (args, context) => {
      const adapter = requireAdapter(context.adapters.memory_write, "memory_write");
      const key = expectStringArg(args, "key", "memory_write");
      const value = args.value;
      if (value === undefined) {
        throw new ToolHandlerError({
          code: "INVALID_ARGUMENT",
          message: "memory_write requires argument 'value'",
          classification: "PERMANENT",
        });
      }
      return adapter.write({ key, value, args, session_context: context.session_context });
    },
    code_execute: async () => {
      throw new ToolHandlerError({
        code: "NOT_IMPLEMENTED",
        message: "code_execute is sandbox-stubbed until M4 hardening",
        classification: "PERMANENT",
        details: { milestone: "M4" },
      });
    },
  };
}
