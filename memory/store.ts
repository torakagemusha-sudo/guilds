import {
  type D1DatabaseLike,
  type MemoryEntry,
  type MemoryInspectItem,
  type MemoryRecord,
  ensureJsonObject,
  hashText,
  nowIso,
  parseJsonArray,
  parseJsonObject,
} from "./types";

type RawMemoryRow = {
  id: string;
  session_id: string | null;
  content: string;
  content_hash: string;
  embedding_ref: string;
  tags: string | string[];
  source: string | null;
  durable: number;
  metadata: string | Record<string, unknown>;
  access_count: number;
  created_at: string;
  updated_at: string;
  last_accessed_at: string;
};

const MEMORY_TABLE_SCHEMA = `
CREATE TABLE IF NOT EXISTS memory_index (
  id TEXT PRIMARY KEY,
  session_id TEXT,
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  embedding_ref TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '[]',
  source TEXT,
  durable INTEGER NOT NULL DEFAULT 0,
  metadata TEXT NOT NULL DEFAULT '{}',
  access_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_accessed_at TEXT NOT NULL,
  consolidated_at TEXT,
  consolidated_into TEXT
)`;

const MEMORY_INDEXES = [
  "CREATE INDEX IF NOT EXISTS idx_memory_index_content_hash ON memory_index(content_hash)",
  "CREATE INDEX IF NOT EXISTS idx_memory_index_session ON memory_index(session_id)",
  "CREATE INDEX IF NOT EXISTS idx_memory_index_durable ON memory_index(durable)",
  "CREATE INDEX IF NOT EXISTS idx_memory_index_last_accessed_at ON memory_index(last_accessed_at)",
  "CREATE INDEX IF NOT EXISTS idx_memory_index_access_count ON memory_index(access_count)",
];

const EVIDENCE_TABLE_SCHEMA = `
CREATE TABLE IF NOT EXISTS evidence_registry (
  id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL,
  evidence_ref TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(memory_id, evidence_ref)
)`;

const EVIDENCE_INDEXES = [
  "CREATE INDEX IF NOT EXISTS idx_evidence_registry_memory_id ON evidence_registry(memory_id)",
];

function createId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `mem_${Math.random().toString(36).slice(2)}_${Date.now()}`;
}

export async function ensureMemoryTables(db: D1DatabaseLike): Promise<void> {
  await db.prepare(MEMORY_TABLE_SCHEMA).run();
  for (const statement of MEMORY_INDEXES) {
    await db.prepare(statement).run();
  }
  await db.prepare(EVIDENCE_TABLE_SCHEMA).run();
  for (const statement of EVIDENCE_INDEXES) {
    await db.prepare(statement).run();
  }
}

function normalizeTags(tags: string[] | undefined): string[] {
  if (!tags?.length) {
    return [];
  }
  const seen = new Set<string>();
  for (const rawTag of tags) {
    const normalized = rawTag.trim();
    if (normalized) {
      seen.add(normalized);
    }
  }
  return [...seen];
}

export function mergeTags(base: string[], incoming: string[]): string[] {
  return normalizeTags([...base, ...incoming]);
}

export function mapMemoryRecord(raw: RawMemoryRow): MemoryRecord {
  return {
    id: raw.id,
    session_id: raw.session_id,
    content: raw.content,
    content_hash: raw.content_hash,
    embedding_ref: raw.embedding_ref,
    tags: parseJsonArray(raw.tags),
    source: raw.source,
    durable: Number(raw.durable) ? 1 : 0,
    metadata: parseJsonObject(raw.metadata),
    access_count: Number(raw.access_count ?? 0),
    created_at: raw.created_at,
    updated_at: raw.updated_at,
    last_accessed_at: raw.last_accessed_at,
  };
}

export function asInspectItems(entries: MemoryRecord[]): MemoryInspectItem[] {
  return entries.map((entry) => ({
    id: entry.id,
    sessionId: entry.session_id,
    preview:
      entry.content.length > 160
        ? `${entry.content.slice(0, 157)}...`
        : entry.content,
    tags: entry.tags,
    source: entry.source,
    durable: Boolean(entry.durable),
    accessCount: entry.access_count,
    createdAt: entry.created_at,
    lastAccessedAt: entry.last_accessed_at,
  }));
}

export async function touchMemoryAccess(
  db: D1DatabaseLike,
  ids: string[],
): Promise<void> {
  if (!ids.length) {
    return;
  }
  const now = nowIso();
  const placeholders = ids.map(() => "?").join(", ");
  await db
    .prepare(
      `UPDATE memory_index
       SET access_count = access_count + 1,
           last_accessed_at = ?,
           updated_at = ?
       WHERE id IN (${placeholders})`,
    )
    .bind(now, now, ...ids)
    .run();
}

export async function upsertEvidenceLinks(
  db: D1DatabaseLike,
  memoryId: string,
  evidenceLinks: string[] | undefined,
): Promise<void> {
  if (!evidenceLinks?.length) {
    return;
  }
  const now = nowIso();
  const links = normalizeTags(evidenceLinks);
  for (const link of links) {
    const evidenceId = createId();
    await db
      .prepare(
        `INSERT INTO evidence_registry (id, memory_id, evidence_ref, created_at)
         VALUES (?, ?, ?, ?)
         ON CONFLICT(memory_id, evidence_ref) DO NOTHING`,
      )
      .bind(evidenceId, memoryId, link, now)
      .run();
  }
}

export async function memory_write(
  db: D1DatabaseLike,
  entry: MemoryEntry,
): Promise<MemoryRecord> {
  await ensureMemoryTables(db);

  const content = entry.content?.trim();
  if (!content) {
    throw new Error("memory_write requires non-empty entry.content");
  }

  const id = entry.id ?? createId();
  const now = nowIso();
  const createdAt = entry.created_at ?? now;
  const tags = normalizeTags(entry.tags);
  const metadata = ensureJsonObject(entry.metadata);
  const contentHash = hashText(content);
  const embeddingRef = `hash:${contentHash}`;
  const durable = entry.durable ? 1 : 0;

  await db
    .prepare(
      `INSERT INTO memory_index (
         id,
         session_id,
         content,
         content_hash,
         embedding_ref,
         tags,
         source,
         durable,
         metadata,
         access_count,
         created_at,
         updated_at,
         last_accessed_at
       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(id) DO UPDATE SET
         session_id = excluded.session_id,
         content = excluded.content,
         content_hash = excluded.content_hash,
         embedding_ref = excluded.embedding_ref,
         tags = excluded.tags,
         source = excluded.source,
         durable = excluded.durable,
         metadata = excluded.metadata,
         access_count = memory_index.access_count + 1,
         updated_at = excluded.updated_at,
         last_accessed_at = excluded.last_accessed_at`,
    )
    .bind(
      id,
      entry.session_id ?? null,
      content,
      contentHash,
      embeddingRef,
      JSON.stringify(tags),
      entry.source ?? null,
      durable,
      JSON.stringify(metadata),
      1,
      createdAt,
      now,
      now,
    )
    .run();

  await upsertEvidenceLinks(db, id, entry.evidence_links);

  const row = await db
    .prepare("SELECT * FROM memory_index WHERE id = ? LIMIT 1")
    .bind(id)
    .first<RawMemoryRow>();

  if (!row) {
    throw new Error(`memory_write failed to read inserted record for id=${id}`);
  }

  return mapMemoryRecord(row);
}
