# GUILDS User Guide

GUILDS helps you define a user interface as a set of visible claims, actions, phases, and failure states, then generate UI shells for multiple targets from one specification.

This guide is for people who want to use GUILDS to build interfaces for real programs such as:

- command wrappers
- internal tools
- dashboards
- file utilities
- process monitors
- admin panels
- desktop shells for existing scripts

If you want a visual planning surface before writing the spec by hand, there is also:

- a zero-setup drag-and-drop prototype at [docs/react_gui_builder.html](C:/Users/Thomas/Desktop/GUILDS/docs/react_gui_builder.html)
- a full Vite-based React builder app under [builder](C:/Users/Thomas/Desktop/GUILDS/builder)

## What GUILDS Is Good At

GUILDS is best when you want to:

- describe what the user sees and can do without hand-building the UI in a toolkit first
- prototype a UI quickly in HTML, then promote it to desktop or C++
- keep the same high-level interaction model across multiple render targets
- model states like `idle`, `execute`, `verify`, and `recover` explicitly
- surface failure states deliberately instead of relying on generic error popups

GUILDS is not a full application framework. It generates UI structure and state surfaces. Your program logic still lives in your application code.

## Install And Run

From the repository root:

```powershell
pip install -e core
```

That gives you the `guilds` command.

You can also run directly from source:

```powershell
python core/guilds_cli.py
```

## The Basic Workflow

The normal workflow is:

1. Create a `.guilds` spec.
2. Validate it.
3. Build the default HTML UI first.
4. Iterate until the structure and phases are right.
5. Generate a desktop backend.
6. Optionally compile the Python desktop app into an `.exe`.
7. Optionally turn local `.md`, `.txt`, or `.json` files into formatted PDFs.

Example:

```powershell
guilds new MyTool
guilds validate mytool.guilds
guilds build mytool.guilds
guilds serve mytool.guilds
guilds build mytool.guilds --backend pyside6
```

Builder mode:

```powershell
guilds serve --builder
```

PDF mode:

```powershell
guilds pdf docs\USER_GUIDE.md
guilds pdf docs\USER_GUIDE.md --output outputs\user_guide.pdf
guilds pdf --gui --input docs\USER_GUIDE.md --output outputs\user_guide.pdf
```

## The Mental Model

GUILDS specs are built from a few core parts.

`claim`

- Something the UI asserts or displays.
- Examples: current status, selected file, process output, progress, error text.

`afford`

- Something the user can do.
- Examples: Run, Cancel, Refresh, Open, Retry.

`vessel`

- A container that groups claims and affordances.
- Examples: Toolbar, Results Panel, Status Bar, Error Overlay.

`stage`

- The top-level phase-aware surface definition.
- It decides what is visible, faded, or hidden in each phase.

`flow`

- A modeled multi-step operation.
- Examples: upload flow, request flow, calculation flow, sync flow.

`bond`

- A declared relationship between vessels.

The most important practical concept is the `stage`: it lets you explicitly say what the UI should look like in `idle`, `execute`, `verify`, or `recover`.

## A Minimal Real Example

Imagine you have a Python script that runs a backup job. You want a UI with:

- a status message
- a last-run timestamp
- a `Run Backup` button
- a `Cancel` button while running
- a clear recovery surface when backup fails

A GUILDS spec for that kind of program starts with claims:

```text
claim StatusClaim {
    content:     text(backup_status)
    certainty:   0x03C40x2713
    provenance:  source.direct(backup_service)
    stakes:      high
    freshness:   event_driven(status_change)
    on_stale:    mark_stale
}

claim LastRunClaim {
    content:     text(last_run_time)
    certainty:   0x03C4~
    provenance:  source.derived(run_history, method = latest_success)
    stakes:      medium
    freshness:   event_driven(run_complete)
    on_stale:    mark_stale
}
```

Then the actions:

```text
afford RunBackupAfford {
    perceivable:  always_visible
    offered:      activate
    requires:     [backup_idle]
    contracts: [
        contract RunBackup {
            trigger:     user_action(RunBackupAfford)
            obligation:  execute(start_backup)
            deadline:    ms(100)
            on_breach:   0x03A60x22A3
        }
    ]
    on_unavail:   fade_locked
}

afford CancelBackupAfford {
    perceivable:  context_revealed(backup_running)
    offered:      activate
    requires:     [backup_running]
    contracts: [
        contract CancelBackup {
            trigger:     user_action(CancelBackupAfford)
            obligation:  execute(cancel_backup)
            deadline:    ms(100)
            on_breach:   0x03A60x2193
        }
    ]
    on_unavail:   hidden
}
```

Then group them into vessels:

```text
vessel StatusPanel {
    budget:      whole(0.35)
    phase:       any
    weight:      primary
    arrangement: sequence(primary, [0.6, 0.4])
    contains:    [StatusClaim, LastRunClaim]
}

vessel ActionPanel {
    budget:      whole(0.20)
    phase:       any
    weight:      secondary
    arrangement: sequence(primary, [0.5, 0.5])
    contains:    [RunBackupAfford, CancelBackupAfford]
}

vessel ErrorOverlay {
    budget:      whole(0.25)
    phase:       0x03C60x1D63
    weight:      primary
    arrangement: sequence(primary, [1.0])
    contains:    [StatusClaim, RunBackupAfford]
}
```

Then define the stage:

```text
stage BackupStage {
    budget:  whole(1.0)

    phases: {
        0x03C60x2205: {
            arrangement: sequence(cross, [0.65, 0.35])
            visible:     [StatusPanel, ActionPanel]
            faded:       []
            hidden:      [ErrorOverlay]
            dominant:    StatusPanel
        }
        0x03C60x2081: {
            arrangement: sequence(cross, [0.65, 0.35])
            visible:     [StatusPanel, ActionPanel]
            faded:       []
            hidden:      [ErrorOverlay]
            dominant:    ActionPanel
        }
        0x03C60x1D63: {
            arrangement: sequence(primary, [0.4, 0.6])
            visible:     [ErrorOverlay]
            faded:       [StatusPanel]
            hidden:      [ActionPanel]
            dominant:    ErrorOverlay
        }
    }

    default: {
        arrangement: sequence(cross, [0.65, 0.35])
        visible:     [StatusPanel, ActionPanel]
        faded:       []
        hidden:      [ErrorOverlay]
        dominant:    StatusPanel
    }

    transition: {
        duration:   ms(120)
        curve:      ease-out
        sequence:   anchor_first
    }
}
```

That is enough to generate a UI shell you can then hook into your actual backup code.

## How To Turn A Program Into A GUI

The simplest method is:

1. Identify the program states.
2. Identify the important displayed data.
3. Identify the safe actions a user can take.
4. Group those into a few vessels.
5. Map those vessels across phases.

### 1. Identify Program States

Most real tools can be modeled with these:

- `idle`: waiting for input
- `orient`: user is selecting context, reading, or preparing
- `execute`: work is actively running
- `verify`: user is confirming results or reviewing changes
- `recover`: an error or interruption happened

You do not have to use all of them, but you should use the ones that matter to the workflow.

### 2. Identify The Claims

Claims are the output your user needs to trust.

Good examples:

- current command
- selected target
- progress
- last result
- warning message
- system health
- file path
- connection state

If the user would ask, “what is happening?” or “what is selected?”, that answer is usually a claim.

### 3. Identify The Affordances

Affordances are actions the user can take right now.

Good examples:

- Run
- Stop
- Retry
- Open
- Refresh
- Save
- Export
- Delete

Keep them tied to real operations, not abstract UI filler.

### 4. Group Them Into Vessels

A good vessel should feel like one coherent part of the UI.

Good vessel patterns:

- `Toolbar`
- `StatusPanel`
- `ResultsPanel`
- `SelectionPanel`
- `ErrorOverlay`
- `ProgressPanel`

If a vessel contains too many children, the validator will flag it. Split large vessels into smaller nested vessels.

### 5. Define Phase Visibility

The most useful question to ask for each phase is:

- what must be obvious?
- what may remain visible but de-emphasized?
- what should disappear?

Use:

- `visible` for primary focus
- `faded` for secondary but still relevant items
- `hidden` for content that should be removed from attention

## Common Patterns For Real Programs

### Pattern: Command Wrapper

Use this when you have a CLI command or script and want a UI around it.

Typical claims:

- command text
- stdout preview
- stderr preview
- exit code
- elapsed time

Typical affordances:

- Run
- Cancel
- Copy Output
- Retry

Typical phases:

- `idle`: command entry and run action visible
- `execute`: output visible, cancel visible
- `verify`: exit code and result summary visible
- `recover`: error text and retry action dominant

Reference example:

- [examples/terminal.guilds](C:/Users/Thomas/Desktop/GUILDS/examples/terminal.guilds)

### Pattern: Internal Dashboard

Use this when you are presenting system metrics, charts, alerts, or health summaries.

Typical claims:

- KPIs
- time range
- alert summary
- connectivity state

Typical affordances:

- Refresh
- Change range
- Drill down
- Retry connection

Typical phases:

- `orient`: filtering and reading
- `execute`: refresh in progress
- `recover`: degraded data or connection failure

Reference example:

- [examples/dashboard.guilds](C:/Users/Thomas/Desktop/GUILDS/examples/dashboard.guilds)

### Pattern: File Utility

Use this when you are wrapping file system operations.

Typical claims:

- current path
- selected file
- file count
- available disk space

Typical affordances:

- Open
- Rename
- Delete
- Copy
- Paste
- Refresh

Typical phases:

- `orient`: browsing
- `execute`: copying, moving, deleting
- `verify`: confirmation dialogs
- `recover`: permission or IO failures

Reference example:

- [examples/file_browser.guilds](C:/Users/Thomas/Desktop/GUILDS/examples/file_browser.guilds)

### Pattern: Calculator Or Data Entry Tool

Use this when the user is entering values and receiving an immediate result.

Typical claims:

- current input
- result
- current operator

Typical affordances:

- number keys
- clear
- clear entry
- operator keys
- equals

Reference example:

- [examples/calculator.guilds](C:/Users/Thomas/Desktop/GUILDS/examples/calculator.guilds)

## Commands You Will Use Most

### Start From A Template

```powershell
guilds new MyTool
```

This writes `mytool.guilds`.

### Validate Before You Build

```powershell
guilds validate mytool.guilds
```

Validation catches:

- parser errors
- invalid sigil usage
- structural issues
- load ceiling violations
- some semantic risks

Warnings do not block output, but errors should be fixed first.

### Build The Default HTML UI

```powershell
guilds build mytool.guilds
```

Output:

```text
outputs/mytool/guilds_live.html
```

This is the fastest iteration path and should be your default first target.

### Run The Local Dev Server

```powershell
guilds serve mytool.guilds
```

This serves the HTML output locally so you can inspect and iterate quickly.

### Render One Phase Snapshot

```powershell
guilds render mytool.guilds execute
guilds render mytool.guilds recover
```

Output:

```text
outputs/mytool/guilds_surface_execute.html
outputs/mytool/guilds_surface_recover.html
```

This is the easiest way to check whether your phase definitions actually differ.

### Build Desktop Output

```powershell
guilds build mytool.guilds --backend python-tk
guilds build mytool.guilds --backend pyside6
```

Outputs:

```text
outputs/mytool/guilds_app_tk.py
outputs/mytool/guilds_app_pyside6.py
```

Recommended path:

- use `python-tk` for simplest desktop output
- use `pyside6` if you want a better desktop target or plan to compile an executable

### Build C++ Output

```powershell
guilds build mytool.guilds --backend cpp-qt
guilds build mytool.guilds --backend cpp-imgui
```

Outputs:

`cpp-qt`

- `guilds_ui.h`
- `guilds_ui.cpp`
- `main.cpp`
- `CMakeLists.txt`

`cpp-imgui`

- `guilds_ui.h`
- `guilds_ui.cpp`

### Export Data And Integration Artifacts

```powershell
guilds export mytool.guilds json
guilds export mytool.guilds react
guilds export mytool.guilds vue
guilds export mytool.guilds events
guilds export mytool.guilds statemachine
```

Current working outputs:

- `json`
- `react`
- `vue`
- `events`
- `statemachine`

### Generate A PDF From Local Files

The CLI also includes a document utility for turning local markdown, text, and JSON files into formatted PDFs.

Install the PDF support first:

```powershell
pip install -e core[pdf]
```

For the optional desktop picker UI:

```powershell
pip install -e core[pdf-gui]
```

Headless examples:

```powershell
guilds pdf docs\USER_GUIDE.md
guilds pdf docs\USER_GUIDE.md --output outputs\user_guide.pdf
guilds pdf notes.txt --output outputs\notes.pdf
```

Hybrid GUI example with preloaded paths:

```powershell
guilds pdf --gui --input docs\USER_GUIDE.md --output outputs\user_guide.pdf
```

That opens the Kivy PDF generator UI with the input file and output target already loaded.

### Compile To A Windows Executable

```powershell
guilds compile mytool.guilds --backend pyside6 --onefile
```

Use this only after the generated Python UI already builds correctly.

## Quick Recipes

These are practical patterns for turning existing programs into generated GUI shells quickly.

### Wrap A Python Script

Use this when you already have a script like `backup.py`, `transcode.py`, or `report_job.py`.

Model:

- script inputs as `claim` values
- primary buttons as `afford`
- script output and status as `claim`
- running, success, and failure states as stage phases

Typical loop:

```powershell
guilds validate backup_tool.guilds
guilds build backup_tool.guilds
guilds build backup_tool.guilds --backend pyside6
```

A good first vessel layout is:

- `InputPanel`
- `StatusPanel`
- `ActionPanel`
- `ErrorOverlay`

### Wrap A CLI Tool

Use this when the real work already happens in an executable such as `ffmpeg`, `git`, `robocopy`, or an internal command.

Represent:

- selected files, flags, and mode as `claim`
- `Run`, `Stop`, `Open Output`, and `Retry` as `afford`
- command progress or captured stdout as `claim`

Example workflow:

```powershell
guilds render file_tool.guilds idle
guilds render file_tool.guilds execute
guilds render file_tool.guilds recover
guilds build file_tool.guilds --backend python-tk
```

This is especially useful for tools where users should not remember flags or command syntax.

### Wrap A Long-Running Batch Job

Use this for imports, report generation, indexing, backups, or data sync tasks.

The most useful claims are usually:

- current phase or step
- progress percentage
- last successful run
- last error
- active target or dataset

The most useful affordances are usually:

- `StartJobAfford`
- `PauseJobAfford`
- `CancelJobAfford`
- `RetryJobAfford`

Recommended phase mapping:

- `idle`: setup and scheduling visible
- `execute`: progress and cancellation dominant
- `verify`: results summary dominant
- `recover`: failure summary and retry dominant

### Generate Integration Artifacts

If your program already has its own runtime, use exports as handoff artifacts:

```powershell
guilds export mytool.guilds json
guilds export mytool.guilds react
guilds export mytool.guilds events
guilds export mytool.guilds statemachine
```

Use:

- `json` when another system needs the structural model
- `react` when you want starter components for a web codebase
- `events` when you want a machine-readable action and claim contract
- `statemachine` when you want flow states and transitions as JSON plus Mermaid

### Use The Visual Builder

If you want to sketch before writing the spec:

```powershell
guilds serve --builder
```

That serves the visual builder at `http://localhost:8080`.

For the full React app with a build tool:

```powershell
cd builder
npm install
npm run dev
```

The builder lets you:

- drag claims, affords, vessels, flows, and stages into UI lanes
- edit node names, descriptions, notes, and phases
- model state machines for flows
- copy generated `.guilds`, React, JSON, and Mermaid starter outputs

## Practical End-To-End Example

Let’s say you already have a Python script `backup.py` and want a GUI front-end.

### Step 1: Write The Spec

Create `backup_tool.guilds` and model:

- status text
- current target
- run button
- cancel button
- error surface

### Step 2: Validate

```powershell
guilds validate backup_tool.guilds
```

### Step 3: Prototype In HTML

```powershell
guilds build backup_tool.guilds
guilds serve backup_tool.guilds
```

### Step 4: Inspect Phase Behavior

```powershell
guilds render backup_tool.guilds idle
guilds render backup_tool.guilds execute
guilds render backup_tool.guilds recover
```

### Step 5: Generate Desktop Output

```powershell
guilds build backup_tool.guilds --backend pyside6
```

Now you can integrate the generated UI shell with your own runtime code, or use it as a structural starting point.

### Step 6: Package If Needed

```powershell
guilds compile backup_tool.guilds --backend pyside6 --onefile
```

## Tips For Better Specs

### Start With HTML, Not Desktop

HTML builds are faster to iterate. Solve structure first, then move to desktop.

### Keep Vessels Focused

If one vessel contains too many elements, split it into nested vessels:

- `StatusPanel`
- `PrimaryActions`
- `SecondaryActions`
- `ErrorOverlay`

That makes the UI clearer and keeps validation cleaner.

### Use Real Action Names

Bad:

- `PrimaryActionAfford`
- `ProcessAfford`

Better:

- `RunBackupAfford`
- `CancelJobAfford`
- `RefreshDataAfford`
- `OpenFileAfford`

The generated labels are far more usable when the internal names are specific.

### Make `recover` Explicit

Most generated tools feel better when `recover` is designed on purpose:

- show the failure
- keep enough context visible to recover
- surface a clear retry or escape action

### Use `render` To Compare Phases

If every phase looks the same, your stage is probably underspecified.

## Current Limitations

This repository is usable, but it is not feature-complete.

Important current limits:

- The Qt backend now supports runtime top-level phase switching, but it is still a generated shell, not a full application runtime.
- The Qt renderer respects row vs column arrangements, but it does not fully implement true `grid(...)` placement.
- The `react` and `events` exports are structural starter artifacts, not fully wired application runtimes.
- The `statemachine` export is generated from `flow` declarations and assumes linear step order unless you model branching separately in your own runtime.
- Many examples validate with warnings because they intentionally use `hidden` affordances; those warnings are informative, not always blockers.

## Troubleshooting

### `Error: <file>.guilds not found`

Use the correct relative path.

Example:

```powershell
guilds build examples\calculator.guilds
```

Not:

```powershell
guilds build calculator.guilds
```

Unless the file is actually in the current directory.

### Parse Errors About `PHI_*` Or Phase Sigils

This codebase expects encoded sigils in strict grammar positions.

Use:

- `0x03A60x2193` for degraded
- `0x03A60x22A3` for blocked
- `0x03C60x2205` for idle
- `0x03C60x2081` for execute

Do not use plain words like `blocked` or `execute` in those positions unless the grammar specifically permits them.

### Build Works But The UI Looks Too Generic

That usually means one of these:

- your affordance names are too abstract
- your vessels are too broad
- your phases are too similar
- you are relying on a backend that does not fully implement all arrangement semantics

Fix the spec names and structure first; renderer polish comes second.

## Best Starting Points

If you want to learn by example, start here:

- [examples/calculator.guilds](C:/Users/Thomas/Desktop/GUILDS/examples/calculator.guilds)
- [examples/terminal.guilds](C:/Users/Thomas/Desktop/GUILDS/examples/terminal.guilds)
- [examples/dashboard.guilds](C:/Users/Thomas/Desktop/GUILDS/examples/dashboard.guilds)
- [examples/file_browser.guilds](C:/Users/Thomas/Desktop/GUILDS/examples/file_browser.guilds)

If you want the language spec itself, see:

- [docs/GUILDS_v2_ASCII_Encoded.md](C:/Users/Thomas/Desktop/GUILDS/docs/GUILDS_v2_ASCII_Encoded.md)
