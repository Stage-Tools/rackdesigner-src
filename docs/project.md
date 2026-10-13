# RackDesigner — Project

## What it is
Desktop application for designing 19" equipment racks (audio, video, lighting,
network, power) used in live-event and touring production. Part of the
**StageTools** product line.

Core workflow: build a project → add one or more racks (single or multi-bay)
→ populate them with devices from a library (drag & drop) → export a
technical PDF (rack diagrams, device lists, power/weight totals) for the
client or crew.

## Target user
Production/system technicians and rental houses who need a fast way to plan
rack layouts and generate a shareable technical document, without a full
CAD/EDA tool.

## Platform & stack
- **Language / UI**: Python 3, PyQt6
- **PDF export**: ReportLab
- **Packaging**: PyInstaller (onefile) → `rack_designer.spec`
- **Installer**: Inno Setup (`.iss`, not present in this project's uploaded
  files — confirm location if it needs to be tracked here)
- **Target OS**: Windows only (storage relies on `%APPDATA%`)

## Storage
- Library: `%APPDATA%\RackDesigner\library.json`
- Custom categories: `%APPDATA%\RackDesigner\custom_categories.json`
- Projects: `%APPDATA%\RackDesigner\projects\*.rackproj` (JSON)

## Distribution
Built and versioned locally on the author's machine, published to GitHub
Releases (installer + portable build) as a separate step outside this
documentation workflow.

## Version status
⚠️ See `status.md`. The version declared in code/build artifacts
(`v0.1.19`) is not confirmed to match the actual feature set present in the
codebase — see the documented drift in `changelog.md` (Unreleased section).

## Repository / version control
**Confirmed (Claude Code, 2026-07-22): no `.git` repository anywhere under
the project root.** The earlier assumption of a local git repo pushed to
GitHub was wrong — corrected here.

Actual versioning is manual: each release is kept as a full source+build
snapshot folder under `RarckDesigner History/RackDesigner_vX.Y.Z/`. Open
question (not yet resolved — see `status.md`): which tree is actually
edited day-to-day, the top-level `RackDesigner_v0.1.19/` or the copy inside
`RarckDesigner History/`. The installer (`rack_designer_installer.iss`)
builds from the **History** copy's `dist/`, not the top-level one, which
suggests the History copy may be closer to the "real" working copy than
the name implies.
