# GUILDS Builder

This is the full React-based visual builder for GUILDS.

It is separate from the CLI so the builder can evolve as a normal frontend app while the CLI keeps a simple Python runtime.

## Run It

```powershell
cd builder
npm install
npm run dev
```

## Build Static Assets

```powershell
npm run build
```

That writes static assets to `builder/dist/`.

If `builder/dist/` exists, `guilds serve --builder` will prefer serving that build. Otherwise, the CLI falls back to the standalone prototype page in `docs/react_gui_builder.html`.
