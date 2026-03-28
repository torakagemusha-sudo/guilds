import { readFileSync, readdirSync } from "node:fs";
import { extname, join, resolve } from "node:path";

export interface D1PreparedStatement {
  bind(...values: Array<string | number | null>): D1PreparedStatement;
  run(): Promise<unknown>;
  first<T = unknown>(): Promise<T | null>;
}

export interface D1DatabaseLike {
  prepare(sql: string): D1PreparedStatement;
  exec(sql: string): Promise<unknown>;
}

export interface MigrationResult {
  migration: string;
  applied: boolean;
}

export interface RunMigrationsOptions {
  migrationsDir?: string;
  tableName?: string;
}

const DEFAULT_TABLE_NAME = "schema_migrations";
const CREATE_MIGRATIONS_TABLE_SQL = `
CREATE TABLE IF NOT EXISTS schema_migrations (
  name TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
  created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
`;

export function listMigrationFiles(migrationsDir: string): string[] {
  const entries = readdirSync(migrationsDir, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && extname(entry.name).toLowerCase() === ".sql")
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b));
}

export async function runMigrations(
  db: D1DatabaseLike,
  options: RunMigrationsOptions = {},
): Promise<MigrationResult[]> {
  const tableName = options.tableName ?? DEFAULT_TABLE_NAME;
  const migrationsDir = resolve(options.migrationsDir ?? join(process.cwd(), "d1", "migrations"));
  const migrationFiles = listMigrationFiles(migrationsDir);
  const results: MigrationResult[] = [];

  if (tableName !== DEFAULT_TABLE_NAME) {
    throw new Error(`Unsupported migrations table name: ${tableName}`);
  }

  await db.exec(CREATE_MIGRATIONS_TABLE_SQL);

  for (const migrationFile of migrationFiles) {
    const alreadyApplied = await db
      .prepare(`SELECT name FROM ${tableName} WHERE name = ?1`)
      .bind(migrationFile)
      .first<{ name: string }>();

    if (alreadyApplied) {
      results.push({ migration: migrationFile, applied: false });
      continue;
    }

    const sql = readFileSync(join(migrationsDir, migrationFile), "utf8").trim();
    if (!sql) {
      throw new Error(`Migration file is empty: ${migrationFile}`);
    }

    await db.exec("BEGIN TRANSACTION;");
    try {
      await db.exec(sql);
      await db
        .prepare(`INSERT INTO ${tableName} (name) VALUES (?1)`)
        .bind(migrationFile)
        .run();
      await db.exec("COMMIT;");
    } catch (error) {
      await db.exec("ROLLBACK;");
      throw new Error(
        `Failed migration ${migrationFile}: ${
          error instanceof Error ? error.message : String(error)
        }`,
      );
    }

    results.push({ migration: migrationFile, applied: true });
  }

  return results;
}

