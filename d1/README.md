# D1 Schema And Migrations

This directory contains the authoritative SQLite schema for Cloudflare D1 and a simple TypeScript migration runner.

## Files

- `schema.sql`: full desired schema snapshot.
- `migrations/0001_initial.sql`: initial migration from v0.
- `migrate.ts`: migration runner utility for applying numbered SQL files.

## Usage

Import `runMigrations()` and pass a D1-like database object that supports:

- `prepare(sql).bind(...).first()`
- `prepare(sql).bind(...).run()`
- `exec(sql)`

Example:

```ts
import { runMigrations } from "./migrate";

await runMigrations(env.DB, {
  migrationsDir: "/absolute/path/to/d1/migrations",
});
```

The runner:

1. Ensures `schema_migrations` exists.
2. Reads and lexicographically sorts `*.sql` files.
3. Applies unapplied files in transactions.
4. Records each applied migration in `schema_migrations`.
