# GUILDS

GUILDS is a toolkit for describing interfaces in a declarative `.guilds` spec and generating UI shells for multiple targets from one source.

This repository contains:

- `core/`: the Python CLI (`guilds`) for creating, validating, building, rendering, exporting, and packaging specs.
- `guilds_renderers/`: renderer backends used by the CLI.
- `builder/`: a Vite + React visual builder for drag-and-drop planning.

## Quick Start

From the repository root:

```bash
pip install -e core
guilds --help
```

Create, validate, and build a sample spec:

```bash
guilds new MyApp
guilds validate myapp.guilds
guilds build myapp.guilds
guilds serve myapp.guilds
```

Default output is written under `outputs/<spec-name>/`.

## Common Commands

```text
guilds new <name>
guilds validate <spec>
guilds build <spec> [--backend ...]
guilds render <spec> <phase>
guilds serve <spec> [--port ...]
guilds serve --builder [--port ...]
guilds export <spec> <json|react|vue|events|statemachine>
guilds compile <spec> [--backend ...] [--onefile]
guilds pdf <input> [--output ...]
```

## Visual Builder

Run the full React app:

```bash
cd builder
npm install
npm run dev
```

Or serve builder mode via the CLI:

```bash
guilds serve --builder
```

## Documentation

- CLI guide: `core/README.md`
- Builder guide: `builder/README.md`
- Language and examples: `docs/`, `examples/`

## Development Checks

Run from repository root:

```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
pytest
```
