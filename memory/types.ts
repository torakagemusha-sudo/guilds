export interface D1ResultLike<T = unknown> {
  results?: T[];
  success?: boolean;
  meta?: Record<string, unknown>;
}

export interface D1PreparedStatementLike {
  bind(...values: unknown[]): D1PreparedStatementLike;
  run<T = unknown>(): Promise<D1ResultLike<T>>;
  first<T = unknown>(): Promise<T | null>;
  all<T = unknown>(): Promise<D1ResultLike<T>>;
}

export interface D1DatabaseLike {
  prepare(query: string): D1PreparedStatementLike;
}

export interface MemoryEntry {
  id?: string;
  session_id?: string | null;
  content: string;
  tags?: string[];
  source?: string | null;
  durable?: boolean;
  evidence_links?: string[];
  metadata?: Record<string, unknown>;
  created_at?: string;
}

export interface MemoryFilter {
  tags?: string[];
  since?: string;
  session_id?: string;
  min_access_count?: number;
}

export interface MemoryRecord {
  id: string;
  session_id: string | null;
  content: string;
  content_hash: string;
  embedding_ref: string;
  tags: string[];
  source: string | null;
  durable: number;
  metadata: Record<string, unknown>;
  access_count: number;
  created_at: string;
  updated_at: string;
  last_accessed_at: string;
}

export interface MemoryInspectItem {
  id: string;
  sessionId: string | null;
  preview: string;
  tags: string[];
  source: string | null;
  durable: boolean;
  accessCount: number;
  createdAt: string;
  lastAccessedAt: string;
}

export interface MemoryRetrieveResult {
  entries: MemoryRecord[];
  projection: MemoryInspectItem[];
}

export type PruneMode = "ttl" | "access_count" | "explicit";

export interface PrunePolicy {
  mode: PruneMode;
  older_than_seconds?: number;
  min_access_count?: number;
  ids?: string[];
  dry_run?: boolean;
}

export interface PruneResult {
  mode: PruneMode;
  deleted: number;
  ids: string[];
  dryRun: boolean;
}

export interface ConsolidateResult {
  sessionId: string;
  processed: number;
  insertedDurable: number;
  linkedToExisting: number;
}

export function nowIso(): string {
  return new Date().toISOString();
}

export function hashText(text: string): string {
  // FNV-1a (32-bit) is sufficient as an embedding_ref stub.
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function generateId(): string {
  const cryptoRef = (globalThis as { crypto?: { randomUUID?: () => string } })
    .crypto;
  if (typeof cryptoRef?.randomUUID === "function") {
    return cryptoRef.randomUUID();
  }
  return `mem_${nowIso()}_${Math.random().toString(16).slice(2)}`;
}

export function ensureJsonObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return value as Record<string, unknown>;
}

export function parseJsonArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map(String);
  }
  if (typeof value !== "string") {
    return [];
  }
  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) {
      return parsed.map(String);
    }
  } catch {
    return [];
  }
  return [];
}

export function parseJsonObject(value: unknown): Record<string, unknown> {
  if (!value) {
    return {};
  }
  if (typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value !== "string") {
    return {};
  }
  try {
    return ensureJsonObject(JSON.parse(value));
  } catch {
    return {};
  }
}
