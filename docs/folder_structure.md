# RackDesigner — Folder Structure

Inferred from imports (`from app.main_window import MainWindow`, etc.) and
confirmed by the project owner. If a Claude Code session finds discrepancies
with the real disk layout, it should correct this file as part of its first
pass.

> **Corrected 2026-07-22 (Claude Code first pass).** The tree previously
> documented here showed `main.py`/`app/`/etc. directly at the project
> root. On disk, the live source tree is one level down, inside a
> version-named folder.

> **Repointed 2026-07-24 (Session 6).** The live tree was duplicated from
> `RackDesigner_v0.1.19/` to a new sibling folder, `RackDesigner_v0.1.20/`
> (same level, project root) — `build/`/`dist/`/`__pycache__` excluded
> from the copy (regenerable PyInstaller/bytecode output, not worth
> carrying over as stale clutter). **`RackDesigner_v0.1.19/` is now a
> frozen snapshot as of 2026-07-24** (it already contained the v0.1.20
> code under the old folder name, from Session 5's version bump — freezing
> it here just stops further edits landing in a folder named for the
> wrong version). **`RackDesigner_v0.1.20/` is the live/edited tree from
> this session onward.** See `task.md` (Build/release process) for the
> dated log entry, and `task.md` #10 for the earlier discussion of this
> exact naming drift.
>
> `RackDesigner_v0.1.19/` is a separate thing from the
> `RarckDesigner History/` archive below — same "frozen snapshot" idea,
> but it isn't part of that older per-release archive convention (it
> wasn't moved into `RarckDesigner History/`, it's just stopped-editing
> in place at the project root).

```
Rack Designer/                       # project root (no .git — local only)
├── docs/
│   ├── project.md
│   ├── design.md
│   ├── folder_structure.md   # this file
│   ├── status.md
│   ├── task.md
│   ├── changelog.md          # active changelog, continues from Unreleased
│   └── claude_code_prompt.md
│
├── RackDesigner_v0.1.20/     # current live source tree (edit here) — since Session 6, 2026-07-24
│   ├── main.py                  # entry point
│   ├── requirements.txt         # PyQt6, reportlab, pyinstaller
│   ├── rack_designer.spec       # PyInstaller build spec (onefile); name='RackDesigner_v0.1.20'
│   ├── icon.ico                 # referenced by the .spec
│   ├── icon old.ico              # superseded icon, kept alongside
│   ├── (no build/ or dist/ yet — excluded from the Session 6 copy; regenerate by building)
│   └── app/
│       ├── __init__.py           # APP_VERSION = "0.1.20" — app IS a proper Python package
│       ├── models.py             # data model (Project, Rack, RackSlot, DeviceDefinition)
│       ├── storage.py             # persistence: library, categories, projects, CSV import
│       ├── style.py                # global QSS + palette
│       ├── dialogs.py               # MsgBox and other themed dialogs
│       ├── library_dialog.py          # device library edit widgets
│       ├── rack_canvas.py              # interactive rack canvas (paint, DnD, undo, shortcuts)
│       ├── pdf_export.py                # ReportLab PDF generation
│       ├── preloaded_library.py          # default 119-device seed library
│       └── main_window.py                 # all UI tabs/sections + MainWindow shell
│                                            # (app/faceplates.py deleted Session 5 — was dead code;
│                                            #  correctly absent here, was excluded from the Session 6 copy
│                                            #  simply by no longer existing in the source at copy time)
│
├── RackDesigner_v0.1.19/     # ⚠️ FROZEN as of 2026-07-24 (Session 6) — do not edit
│   │                             # Byte-identical to RackDesigner_v0.1.20/ at the moment of the
│   │                             # copy (own build/dist/__pycache__ still present here, just not
│   │                             # copied forward). Kept only as a snapshot of that exact point in
│   │                             # time; RackDesigner_v0.1.20/ is where all further work happens.
│   └── ... (same layout as RackDesigner_v0.1.20/ above, as of the Session 6 copy)
│
├── rack_designer_installer.iss   # Inno Setup script (root, not inside either RackDesigner_v0.1.2X/)
│                                  # NOT touched in Session 6 (deliberately deferred). Still built
│                                  #    around the old live tree: [Files] source, [Icons], and [Run]
│                                  #    all still point at RackDesigner_v0.1.19/dist/... — which, as
│                                  #    of this session, is the now-frozen snapshot folder, not the
│                                  #    live one. Whenever the installer is next actually compiled,
│                                  #    it needs repointing at RackDesigner_v0.1.20/dist/... instead.
│                                  #    See task.md #4.
├── installer_output/             # built installers (v0.1.17–v0.1.19 .exe)
├── RackLibrary.csv               # sample/test data for storage.import_library_csv()
├── Icona eseguibile/              # icon source assets (.ai, .ico, .png)
├── Manual/                        # end-user manuals, one subfolder per version (v0.1.17–19)
│
└── RarckDesigner History/        # [sic] archived per-version snapshots, v0.1.0 → v0.1.19
    ├── Changelog.txt              # the historical log referenced by docs/changelog.md
    └── RackDesigner_v0.1.X/       # one full source+build snapshot per version (does NOT yet
                                    # include a v0.1.20 snapshot — this archive predates Session 6)
```

## Not covered by this documentation set
- `.git` status / branch structure — **confirmed: this is not a git
  repository at all** (no `.git` anywhere under the project root),
  contrary to `project.md`'s description of a local working copy pushed
  to GitHub separately. Flagged for the project owner; not corrected
  here since `project.md` wasn't in scope for this pass.
- Any assets folder for images bundled with the preloaded library —
  confirmed fully inline/base64 in `preloaded_library.py`, no separate
  assets folder exists.

## Confirm-on-first-Claude-Code-pass checklist
_(historical — as found during Session 1, 2026-07-22, before the Session 6
tree duplication; paths below updated to point at their current
equivalents where the item is still relevant)_
- [x] Actual on-disk paths match the tree above — **did not**, corrected above
- [x] `icon.ico` location — `RackDesigner_v0.1.20/icon.ico` as of Session 6
      (was `RackDesigner_v0.1.19/icon.ico` before the copy; also present
      per-version under `RarckDesigner History/`)
- [x] `.iss` installer script location — project root,
      `rack_designer_installer.iss`; see the `[Files]`-source note in the
      tree above (still points at the now-frozen `RackDesigner_v0.1.19/`,
      not yet repointed at `RackDesigner_v0.1.20/` — deliberately deferred,
      see `task.md` #4)
- [x] Whether `app/` is a proper Python package — yes, `__init__.py`
      present (now non-empty — holds `APP_VERSION`, since Session 5)
