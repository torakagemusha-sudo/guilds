import {
  type D1DatabaseLike,
  type PrunePolicy,
  type PruneResult,
} from "./types";
import { ensureMemoryTables } from "./store";

type IdRow = { id: string };

async function selectIds(
  db: D1DatabaseLike,
  whereClause: string,
  params: unknown[],
): Promise<string[]> {
  const rows = await db
    .prepare(`SELECT id FROM memory_index WHERE ${whereClause}`)
    .bind(...params)
    .all<IdRow>();
  return (rows.results ?? []).map((row) => row.id);
}

async function deleteByIds(db: D1DatabaseLike, ids: string[]): Promise<number> {
  if (!ids.length) {
    return 0;
  }
  const placeholders = ids.map(() => "?").join(", ");
  await db
    .prepare(`DELETE FROM evidence_registry WHERE memory_id IN (${placeholders})`)
    .bind(...ids)
    .run();
  await db
    .prepare(`DELETE FROM memory_index WHERE id IN (${placeholders})`)
    .bind(...ids)
    .run();
  return ids.length;
}

export async function memory_prune(
  db: D1DatabaseLike,
  policy: PrunePolicy,
): Promise<PruneResult> {
  await ensureMemoryTables(db);
  const dryRun = Boolean(policy.dry_run);
  const now = Date.now();

  let ids: string[] = [];
  if (policy.mode === "ttl") {
    const ttl = Math.max(0, Math.floor(policy.older_than_seconds ?? 0));
    if (ttl === 0) {
      throw new Error("memory_prune ttl mode requires older_than_seconds > 0");
    }
    const threshold = new Date(now - ttl * 1000).toISOString();
    ids = await selectIds(db, "last_accessed_at < ?", [threshold]);
  } else if (policy.mode === "access_count") {
    const maxAccessCount = Math.max(0, Math.floor(policy.min_access_count ?? 0));
    ids = await selectIds(db, "access_count <= ?", [maxAccessCount]);
  } else {
    const explicitIds = (policy.ids ?? []).map((id) => id.trim()).filter(Boolean);
    if (!explicitIds.length) {
      return { mode: policy.mode, deleted: 0, ids: [], dryRun };
    }
    const placeholders = explicitIds.map(() => "?").join(", ");
    ids = await selectIds(db, `id IN (${placeholders})`, explicitIds);
  }

  const deleted = dryRun ? ids.length : await deleteByIds(db, ids);

  return {
    mode: policy.mode,
    deleted,
    ids,
    dryRun,
  };
}
