import {
  type ConsolidateResult,
  type D1DatabaseLike,
  generateId,
  nowIso,
} from "./types";
import {
  ensureMemoryTables,
  mapMemoryRecord,
  mergeTags,
  upsertEvidenceLinks,
} from "./store";

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

type EvidenceRow = {
  evidence_ref: string;
};

async function getEvidenceLinks(
  db: D1DatabaseLike,
  memoryId: string,
): Promise<string[]> {
  const rows = (
    await db
      .prepare("SELECT evidence_ref FROM evidence_registry WHERE memory_id = ?")
      .bind(memoryId)
      .all<EvidenceRow>()
  ).results;
  return (rows ?? []).map((row) => row.evidence_ref);
}

async function markConsolidated(
  db: D1DatabaseLike,
  sourceId: string,
  durableId: string,
): Promise<void> {
  const now = nowIso();
  await db
    .prepare(
      `UPDATE memory_index
       SET consolidated_at = ?,
           consolidated_into = ?,
           updated_at = ?
       WHERE id = ?`,
    )
    .bind(now, durableId, now, sourceId)
    .run();
}

export async function memory_consolidate(
  db: D1DatabaseLike,
  session_id: string,
): Promise<ConsolidateResult> {
  await ensureMemoryTables(db);
  const sessionId = session_id.trim();
  if (!sessionId) {
    throw new Error("memory_consolidate requires a non-empty session_id");
  }

  const candidatesResult = await db
    .prepare(
      `SELECT *
       FROM memory_index
       WHERE session_id = ?
         AND durable = 0
         AND consolidated_at IS NULL
       ORDER BY created_at ASC`,
    )
    .bind(sessionId)
    .all<RawMemoryRow>();
  const candidates = (candidatesResult.results ?? []).map(mapMemoryRecord);

  let insertedDurable = 0;
  let linkedToExisting = 0;

  for (const candidate of candidates) {
    const existingDurableRow = await db
      .prepare(
        `SELECT *
         FROM memory_index
         WHERE durable = 1
           AND content_hash = ?
         LIMIT 1`,
      )
      .bind(candidate.content_hash)
      .first<RawMemoryRow>();

    if (!existingDurableRow) {
      const durableId = generateId();
      const now = nowIso();
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
           ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)`,
        )
        .bind(
          durableId,
          sessionId,
          candidate.content,
          candidate.content_hash,
          candidate.embedding_ref,
          JSON.stringify(candidate.tags),
          candidate.source,
          JSON.stringify(candidate.metadata),
          candidate.access_count,
          candidate.created_at,
          now,
          candidate.last_accessed_at,
        )
        .run();

      const links = await getEvidenceLinks(db, candidate.id);
      await upsertEvidenceLinks(db, durableId, links);
      await markConsolidated(db, candidate.id, durableId);
      insertedDurable += 1;
      continue;
    }

    const durable = mapMemoryRecord(existingDurableRow);
    const mergedTags = mergeTags(durable.tags, candidate.tags);
    const mergedAccess = durable.access_count + candidate.access_count;
    const now = nowIso();
    await db
      .prepare(
        `UPDATE memory_index
         SET tags = ?,
             access_count = ?,
             last_accessed_at = CASE
               WHEN last_accessed_at < ? THEN ?
               ELSE last_accessed_at
             END,
             updated_at = ?
         WHERE id = ?`,
      )
      .bind(
        JSON.stringify(mergedTags),
        mergedAccess,
        candidate.last_accessed_at,
        candidate.last_accessed_at,
        now,
        durable.id,
      )
      .run();

    const links = await getEvidenceLinks(db, candidate.id);
    await upsertEvidenceLinks(db, durable.id, links);
    await markConsolidated(db, candidate.id, durable.id);
    linkedToExisting += 1;
  }

  return {
    sessionId,
    processed: candidates.length,
    insertedDurable,
    linkedToExisting,
  };
}
