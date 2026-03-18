# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

GUILDS is a monorepo with two independent sub-projects:

1. **`core/` + `guilds_renderers/`** — Python CLI toolkit (parser, validator, builder, renderer, exporter). Install with `pip install -e core` from repo root. Entry point: `guilds` command.
2. **`builder/`** — Vite + React visual drag-and-drop builder. Install with `npm install` in `builder/`. Dev server: `npm run dev` in `builder/`.

No databases, Docker, or external services are required.

### Running services

| Service | Command | Default port |
|---|---|---|
| GUILDS CLI dev server | `guilds serve <spec>.guilds` | 8080 |
| Visual Builder (Vite) | `cd builder && npm run dev` | 5173 |

### Lint / Test / Build

- **Lint:** `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics` (critical errors only — matches CI)
- **Tests:** `pytest` (no test files currently exist in this repo; CI runs pytest but collects nothing)
- **Build (Python CLI):** `guilds build <spec>.guilds` (generates HTML by default to `outputs/`)
- **Build (Builder):** `cd builder && npm run build` (outputs to `builder/dist/`)

### Non-obvious caveats

- After `pip install -e core`, the `guilds` binary lands in `~/.local/bin`. Ensure `$HOME/.local/bin` is on `PATH`.
- The `tools/invar/invar.py` referenced in user rules does not exist in this repo. If invariant tooling is needed, it must be added first.
- The CI workflow (`.github/workflows/python-package.yml`) targets Python 3.9–3.11, but `pyproject.toml` declares `requires-python = ">=3.10"`. The CLI works fine on Python 3.12.
- `guilds validate` warnings are informative; only errors produce a non-zero exit code.
- `watchdog` enables auto-rebuild in `guilds serve`; without it the server still works but requires manual rebuilds.
