import {
  type D1DatabaseLike,
  type MemoryFilter,
  type MemoryInspectItem,
  type MemoryRetrieveResult,
  hashText,
} from "./types";
import {
  asInspectItems,
  ensureMemoryTables,
  mapMemoryRecord,
  touchMemoryAccess,
} from "./store";

type RetrieveOptions = {
  topK?: number;
  filters?: MemoryFilter;
};

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

function pushTagFilters(
  where: string[],
  params: unknown[],
  tags: string[] | undefined,
): void {
  if (!tags?.length) {
    return;
  }
  for (const tag of tags) {
    const normalized = tag.trim();
    if (!normalized) {
      continue;
    }
    where.push("tags LIKE ?");
    params.push(`%\"${normalized}\"%`);
  }
}

export async function memory_retrieve(
  db: D1DatabaseLike,
  query: string,
  topK = 10,
  filters: MemoryFilter = {},
): Promise<MemoryRetrieveResult> {
  await ensureMemoryTables(db);

  const normalizedTopK = Number.isFinite(topK) ? Math.max(1, Math.floor(topK)) : 10;
  const where: string[] = [];
  const params: unknown[] = [];

  const trimmedQuery = query.trim();
  if (trimmedQuery) {
    where.push("(content LIKE ? OR tags LIKE ?)");
    params.push(`%${trimmedQuery}%`, `%${trimmedQuery}%`);
  }

  if (filters.session_id?.trim()) {
    where.push("session_id = ?");
    params.push(filters.session_id.trim());
  }
  if (filters.since?.trim()) {
    where.push("created_at >= ?");
    params.push(filters.since.trim());
  }
  if (typeof filters.min_access_count === "number") {
    where.push("access_count >= ?");
    params.push(Math.max(0, Math.floor(filters.min_access_count)));
  }
  pushTagFilters(where, params, filters.tags);

  const queryHash = hashText(trimmedQuery || "__empty_query__");
  const sql = `
    SELECT *
    FROM memory_index
    ${where.length ? `WHERE ${where.join(" AND ")}` : ""}
    ORDER BY
      CASE WHEN content_hash = ? THEN 0 ELSE 1 END,
      last_accessed_at DESC,
      access_count DESC,
      created_at DESC
    LIMIT ?
  `;

  const result = await db
    .prepare(sql)
    .bind(...params, queryHash, normalizedTopK)
    .all<RawMemoryRow>();
  const rows = (result.results ?? []).map(mapMemoryRecord);

  await touchMemoryAccess(
    db,
    rows.map((row) => row.id),
  );

  const refreshedRows =
    rows.length === 0
      ? []
      : (
          await db
            .prepare(
              `SELECT * FROM memory_index WHERE id IN (${rows
                .map(() => "?")
                .join(", ")})`,
            )
            .bind(...rows.map((row) => row.id))
            .all<RawMemoryRow>()
        ).results?.map(mapMemoryRecord) ?? [];

  return {
    entries: refreshedRows,
    projection: asInspectItems(refreshedRows),
  };
}

export async function memory_inspect(
  db: D1DatabaseLike,
  query: string,
  options: RetrieveOptions = {},
): Promise<MemoryInspectItem[]> {
  const result = await memory_retrieve(
    db,
    query,
    options.topK ?? 20,
    options.filters ?? {},
  );
  return result.projection;
}
