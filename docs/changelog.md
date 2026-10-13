# RackDesigner — Changelog

Full history from v0.1.0 to v0.1.19 (28 Apr 2025 – 21 May 2025) is preserved
as-is in `Changelog.txt` (kept as the historical archive, not duplicated
here). This file continues from that point forward and is the one to keep
updated going forward, one entry per confirmed operation.

## v0.1.19 (addendum — retroactively logged 2026-07-24)

`Changelog.txt` stays frozen (not edited directly). These items belong to
the already-released v0.1.19, logged here as a dated addendum rather than
under a new version number.

Found during Claude Code Session 1 documentation audit (2026-07-22),
present in code but missing from `Changelog.txt`'s v0.1.19 entry:

### Added (undocumented at the time)
- Library "DUPLICATE" button — clones a device with a new UUID and " (copy)" suffix
- "Preset" combobox in the Add Rack dialog (17 common U sizes, 4U–48U)
- Ctrl+O (Open) / Ctrl+N (New project) global keyboard shortcuts

### Changed (undocumented at the time)
- "Client" field in the UI relabeled to "Project number" — the underlying
  data model field is still `Project.client`; a UI-label-only change,
  worth knowing if comparing docs/code to the live UI

### Historical log corrections (Changelog.txt itself, not code — noted
here, not edited into the frozen archive)
- v0.1.12 describes a library-versioning system (`library_version.txt`
  reseed stamp) that does not exist anywhere in the current code —
  either removed later without a log entry, or never actually built
- v0.1.12 states "112 devices" in the preloaded library; current count
  is 119
- The v0.1.10 entry is dated 2026-05-08, almost certainly a typo for
  2025-05-08 given surrounding entries

## v0.1.20 — 24 July 2026

Version bump from 0.1.19. This release folds together Sessions 2–5's
work (2026-07-22 through 2026-07-24), each kept as its own subsection
below so the original Fixed/Added/Changed/Files-modified/Verification
detail per session isn't lost.

### Session 2 (2026-07-22) — PDF export multi-bay fix

#### Fixed
- PDF export: multi-bay racks (`Rack.bays` 2–3) no longer overlap into a
  single column. `RackDrawing` (`app/pdf_export.py`) now positions each
  slot by `slot.bay` in its own column, side by side, separated by a thin
  vertical line. No per-bay labels ("Bay 1/2/3"), per design decision.
- PDF export: the diagram's auto-scale logic previously only accounted
  for height overflow (tall racks). Multi-bay racks can also overflow the
  page **width** (each bay column is a fixed 120mm) — the scale factor
  now takes the more restrictive of a height-fit and a width-fit,
  preserving aspect ratio. Not part of the original bug report, but
  required to satisfy the "at any page-fit scale" verification criterion
  once multiple bay columns exist.

#### Files modified
- `app/pdf_export.py` — `RackDrawing.__init__`/`RackDrawing.draw()`

#### Verification
- Built 2-bay, 3-bay, 1-bay (regression), and a 45U/3-bay (forces both
  height- and width-scaling simultaneously) test racks via a standalone
  script (`export_pdf()` called directly, no UI), rendered each PDF page
  to PNG with PyMuPDF, and visually inspected: no overlap, correct device
  placement per bay at identical U positions across bays, clean thin
  separators, correct scaling. Also re-ran the export with
  `use_color=False` (grayscale) — no exceptions, same per-bay geometry.

### Session 3 (2026-07-24) — Drag/crash fixes + exception handler

#### Fixed
- Crash when a device drag leaves the rack canvas bounds (cross-rack move,
  or any in-rack drag that overshoots the U range): `QPixmap` was used in
  `app/rack_canvas.py` (building the drag pixmap for a cross-rack `QDrag`)
  without ever being imported, raising `NameError` on the first mouse-move
  after the cursor exits the canvas. With no exception handler installed
  anywhere, this previously killed the app silently (no traceback, no
  dialog). Fixed by adding `QPixmap` to the existing `PyQt6.QtGui` import
  line.
- Dragging a device across bay columns within the same canvas (same rack,
  2–3 bay rack) no longer leaves the slot visually stuck in its original
  bay: `RackCanvas.mouseMoveEvent()`'s internal-reorder branch now runs
  its collision check against the bay the cursor is currently over
  (instead of the stale starting bay) and updates `RackSlot.bay` in step
  with `position_u`.

#### Added
- Top-level `sys.excepthook` in `main.py`, installed right after
  `QApplication` is created. Any unhandled exception escaping a Qt event
  handler now: (1) gets its full traceback appended, timestamped, to
  `%APPDATA%\RackDesigner\crash.log`, and (2) shows a short, themed
  `MsgBox.error` dialog telling the user something went wrong and details
  were logged — instead of the app disappearing with no trace.
  `KeyboardInterrupt`/`SystemExit` are passed through unchanged. The app
  keeps running afterward rather than force-quitting. Not a bug fix — new
  safety-net mechanism added as a follow-up decision from the crash above.
  See `design.md` for full mechanism detail and a flagged design deviation
  (themed `MsgBox.error` used instead of a raw `QMessageBox`).

#### Files modified
- `app/rack_canvas.py` — `QPixmap` import; `mouseMoveEvent()` internal-reorder branch
- `main.py` — `sys.excepthook` installation

#### Verification
- Standalone offscreen-Qt scripts (`QT_QPA_PLATFORM=offscreen`), both
  direct handler calls and real `QTest`-driven event dispatch:
  - Bay-crossing drag: single device, back-and-forth crossings, a target
    bay with a colliding slot (move correctly blocked), and a tray slot —
    all 4 scenarios end with the correct `bay`/`position_u`.
  - Cross-rack drag start: no exception, no process abort, in both the
    direct-call and `QTest.mouseMove` paths. Sanity-checked by temporarily
    reverting the `QPixmap` import and re-running the same script — it
    reproduced both the `NameError` (direct call) and the exact silent
    process abort (`QTest`-driven, exit code 127, no output) described in
    Session 2's investigation, confirming the test actually exercises the
    bug.
  - Exception handler: a deliberate `ValueError` raised inside a real
    widget's `mousePressEvent`, dispatched via `QTest.mousePress`,
    confirmed the app survives, the themed dialog is invoked with the
    expected message, `crash.log` (redirected to a throwaway temp
    `%APPDATA%` for the test) contains the traceback, the app keeps
    processing further events afterward, and a synthetic `SystemExit`
    passed through the hook is delegated to the original
    `sys.__excepthook__` rather than logged/dialoged.

### Session 4 (2026-07-24) — Device image wipe fix

#### Fixed
- Editing a device in the Library tab no longer wipes its images.
  `ImagePickerWidget` (`app/library_dialog.py`) was fully built but never
  actually used: `DeviceForm` never instantiated it, so
  `DeviceForm.collect()` always returned empty `image_front`/`image_rear`
  and `LibrarySection._save()`'s blind field-copy loop wrote those empty
  values onto the device on every save. Fixed both directions:
  `DeviceForm` now instantiates real `ImagePickerWidget`s and adds them
  to the form ("Images" row); `DeviceForm.load()` pre-populates them from
  the device being edited (so an untouched open-and-save no longer wipes
  anything); `DeviceForm.collect()` reads the pickers' actual state
  instead of hardcoded empty strings.
- Fixed a prerequisite `NameError`-in-waiting: `ImagePickerWidget`
  referenced `IMAGE_WIDTH_PX`/`IMAGE_U_HEIGHT_PX` without importing them
  — invisible until the widget was ever instantiated, which it now is.

#### Changed
- The device edit form's U-height stepper now also updates the image
  picker's "recommended size" hint (`ImagePickerWidget.update_u_height()`
  existed already but was never called).

#### Files modified
- `app/library_dialog.py` — `DeviceForm.__init__()`, `.load()`,
  `.collect()`, `app.models` import line.

#### Verification
- Offscreen-Qt scripts covering all 4 task scenarios (new device with
  added images; existing device with images edited on an unrelated field
  only — the exact bug — images survive; existing device with images,
  one replaced/one cleared via the picker — change persists; existing
  device without images, no-op save — stays empty) via direct
  `DeviceForm`/`storage` round-trips, plus a second end-to-end script
  driving the real `LibrarySection` widget (actual list-row selection,
  actual `QTest`-driven Save-button click). Reverting the `collect()`
  fix and re-running reproduced the expected failures, confirming the
  tests exercise the real bug.
- Checked the live `library.json` (119 devices) for evidence of prior
  data loss: currently zero devices carry any image data, and the seed
  library never shipped any either — consistent with, but not proof of,
  earlier silent wipes (no history to distinguish "never had one" from
  "lost it"). Images already lost before this fix cannot be recovered by
  it; this only prevents further loss.

### Session 5 (2026-07-24) — Version bump + maintenance batch

#### Added
- `APP_VERSION = "0.1.20"` in `app/__init__.py` — a single shared source
  of truth for the in-app version string.

#### Changed
- Version bumped 0.1.19 → 0.1.20. `app/main_window.py`'s About-tab label
  and status-bar default text now both read from `app.APP_VERSION`
  instead of two separate hardcoded `"v0.1.19"` literals.
  `rack_designer.spec` (`name=`) and `rack_designer_installer.iss`
  (`AppVersion=`, `OutputBaseFilename=`) were updated by hand to 0.1.20 —
  they're external build tooling and can't import the Python constant, so
  they'll need the same manual bump on every future version change too
  (now commented in both files as a reminder).
- Installer path fix (`task.md` #4): `rack_designer_installer.iss`'s
  `[Files]` source now points at the live tree's
  `RackDesigner_v0.1.19\dist\...` instead of the archived
  `RarckDesigner History\RackDesigner_v0.1.19\dist\...` copy. Not built
  or tested end-to-end this session (no installer compile requested) —
  just the source path corrected and re-read to confirm.

#### Removed
- `app/faceplates.py` deleted (`task.md` #6) — confirmed dead
  (superseded, per `Changelog.txt` v0.1.10) via a fresh grep across the
  live tree before deletion; zero references outside the file itself.
- Dead duplicate `color_row`/`self.color_btn`/`clear_col` block removed
  from `DeviceForm.__init__` (`app/library_dialog.py`, `task.md` #9) — it
  was built and wired, then immediately shadowed by a second, identical
  block before ever being added to the form layout. Pure dead-code
  removal; the surviving block is unchanged and still fully wired.

#### Files modified
- `app/__init__.py` (new file)
- `app/main_window.py` — About label + status bar now use `APP_VERSION`
- `rack_designer.spec` — `name=` bumped to 0.1.20, comment added
- `rack_designer_installer.iss` — `AppVersion=`/`OutputBaseFilename=`
  bumped to 0.1.20, comments added, `[Files]` source path corrected
- `app/faceplates.py` — deleted
- `app/library_dialog.py` — dead color-picker block removed

#### Verification
- Ran the app (offscreen Qt): confirmed the About tab and status bar
  both show `v0.1.20`, sourced from the same `app.APP_VERSION` constant.
- Re-grepped the live tree for `faceplates`/`draw_faceplate` after
  deletion — no remaining references; app still constructs and runs.
- Ran the device edit form after the color-picker cleanup: loading a
  device's color, changing it, and collecting it back all still work
  correctly (no behavior change, as expected for dead-code removal).
- Read back `rack_designer_installer.iss` to confirm the `[Files]`
  source now targets the live tree, not the archive.

## Session 7 (2026-07-24) — Full code audit, no code changes

Audit-only session, as scoped: read every module in the live tree
(`RackDesigner_v0.1.20/app/` + `main.py`) for real defects — unhandled
exceptions, None/empty-state crashes, data corruption, silent-overwrite
bugs, off-by-one/boundary errors, missing imports, reentrancy issues,
unvalidated input, mutable defaults, and contradictions with documented
behavior. Not documentation gaps, not style. 10 parallel review passes
(main_window.py split into its 4 major sections/dialogs per its size;
storage.py+models.py; preloaded_library.py; rack_canvas.py; pdf_export.py;
library_dialog.py; style.py+dialogs.py+main.py+`__init__.py`), each with
targeted offscreen-Qt reproduction (`QT_QPA_PLATFORM=offscreen`, direct
calls and/or `QTest`) where practical.

### Found
53 new findings, logged as `task.md` items #12–64 (all `[todo]`, none
fixed this session): 27 `likely-real-and-impactful`, 24
`real-but-minor`, 2 `needs-live-reproduction-to-confirm`. Full detail —
file, function, trigger scenario, live-repro status, severity — is in
`task.md`'s "Session 7 — Full code audit findings" section, with a
sorted triage summary at the top of it. Also summarized in `status.md`.

Notable items (see `task.md` for full list): a dirty-state guard gap
that lets unsaved Project Info edits and Ctrl+S failures silently
discard user work (#12, #26); a startup reference-swap bug that can wipe
racks added before the first Save (#25); rack-reorder data corruption
when two racks share a name (#15); a tray paste/cross-rack-drag height
bug that creates overlapping slots (#47); `mm_to_u()` over-allocating a
U on exact-multiple heights (#32); non-atomic storage writes combined
with load failures being silently swallowed as "empty" (#33, #34, #45);
and four PDF-export correctness/rendering bugs (#55, #57, #58, #59).

### Not fixed
Nothing — audit-only session per explicit scope, matching how Session 1
was documentation-only. All 53 items are `[todo]` in `task.md`, awaiting
a project-owner decision on which to fix next and in what order.

### Files modified
None (no code touched). Documentation only: `task.md` (53 new Backlog
items + triage summary), `status.md` (new audit summary section),
`changelog.md` (this entry).

## v0.1.20 — Session 8, 25 July 2026 (storage durability)

Scoped fix session covering six of Session 7's audit findings — the
"storage durability" cluster (`task.md` #33, #34, #35, #38, #39, #45).
No version-number bump (still `0.1.20`); no other backlog items touched.

### Fixed
- **Non-atomic file writes** (`task.md` #33): `save_library()`,
  `save_custom_categories()`, and `save_project()` (`app/storage.py`)
  used to write straight to the target path. All three now go through a
  new `_atomic_write_json()` helper: write to a sibling `<target>.tmp`,
  `flush()` + `os.fsync()`, then `os.replace()` onto the real target. A
  crash or forced kill mid-write now always leaves either the untouched
  old file or the fully-written new one — never a truncated/corrupt one.
- **Corrupt library/category files silently treated as empty**
  (`task.md` #34, #45): `load_library()` and `load_custom_categories()`
  (`app/storage.py`) now return a `LoadResult` (`.items`, `.was_corrupt`,
  `.backup_path`) instead of a bare list. A genuinely missing file still
  returns cleanly empty, unflagged. A file that exists but fails to
  parse is quarantined — renamed to `<name>.corrupt-<timestamp>.json` in
  the same directory, original bytes never deleted — a warning is
  appended to `%APPDATA%\RackDesigner\crash.log`, and the sentinel is
  set. `preloaded_library.seed_library_if_empty()` now checks both the
  library and custom-categories files every run, still reseeds silently
  on a genuine first run, and — when either was actually corrupt —
  returns that fact so `main.py` can show one combined "your library was
  reset, backup saved to: ..." notice after the main window is shown,
  instead of a silent, unannounced reseed.
- **CSV import had no non-UTF-8 fallback** (`task.md` #35): a CSV saved
  in Windows-1252 ("ANSI", Excel's default export encoding on many
  Windows locales) used to abort the entire import on the first accented
  byte. `import_library_csv()` (`app/storage.py`) now tries `utf-8-sig`
  first, falls back to `cp1252`, and raises a clear "couldn't read this
  file as UTF-8 or Windows-1252" error if neither works — surfaced
  through the existing `Import error` dialog in
  `LibrarySection._import_dialog()` with no changes needed there.
- **Corrupted project file was fully unopenable** (`task.md` #38):
  `load_project()` (`app/storage.py`) had zero exception handling — one
  bad (`null`) slot in a rack's `slots` list aborted the entire load.
  Now returns `(project, skip_warnings)`: an individual unparseable slot
  is skipped and the rest of the rack/project loads normally, with a
  `"N slot(s) in '<rack>' could not be loaded and were skipped."` message
  collected per affected rack. A fully invalid top-level JSON file still
  raises cleanly and is **not** touched/renamed — different treatment
  from library files, since this is the user's own project file,
  deliberately. `ProjectSection._open()`/`._open_recent()`
  (`app/main_window.py`) now show the skip summary via `MsgBox.warn`
  when non-empty.
- **`save_project()` mutated the caller's in-memory project as a save
  side effect** (`task.md` #39): when auto-naming a new save that
  collides with an existing project name, `save_project()` used to
  rename the caller's live `Project` object in place before writing.
  Investigated the one call site (`MainWindow._save()`) first, per the
  task's "stop and report back if the call site depends on this"
  instruction — it does (a comment there explicitly re-syncs the
  Project-tab form from the mutated name after save), so the fix
  preserves that user-visible behavior rather than removing it:
  `save_project()` now computes the deduplicated name as a local
  variable, writes it into the saved file, and returns
  `(filepath, resolved_name)` instead of just `filepath`, without
  touching `project.name`. `MainWindow._save()` now applies
  `project.name = resolved_name` itself, explicitly, immediately after
  the call — same end-user result, but the mutation is visible at the
  call site instead of hidden inside `storage.py`.

### Changed
- `load_library()` / `load_custom_categories()` / `load_project()` /
  `save_project()` all changed return type/shape (see above) — every
  call site in the live tree was updated in this same session
  (`app/main_window.py`, `app/models.py`, `app/preloaded_library.py`,
  plus `storage.py`'s own internal callers). This is a breaking
  in-repo API change, not a public one; no external consumers exist.

### Files modified
- `app/storage.py` — `_atomic_write_json()`, `_log_warning()`,
  `_quarantine_corrupt_file()`, `_read_text_with_encoding_fallback()`,
  `LoadResult` dataclass (all new); `load_library()`,
  `save_library()`, `load_custom_categories()`, `save_custom_categories()`,
  `add_custom_category()`, `save_project()`, `load_project()`,
  `import_library_csv()` (all changed)
- `app/preloaded_library.py` — `seed_library_if_empty()` (now checks
  both files every run, returns a status dict)
- `main.py` — new `_notify_if_library_was_reset()`, called after
  `window.show()`; `seed_library_if_empty()`'s call site unchanged
  otherwise (see `task.md` #62, not in this session's scope)
- `app/main_window.py` — `DesignerSection.__init__`/`.reload_library()`,
  `LibrarySection.reload()` (`.items` on the new `LoadResult`);
  `ProjectSection._open()`/`._open_recent()` (unpack
  `(project, skip_warnings)`, show `MsgBox.warn` when non-empty);
  `MainWindow._save()` (unpack `(filepath, resolved_name)`, apply
  `resolved_name` explicitly)
- `app/models.py` — `get_categories()` (`.items` on the new `LoadResult`)

### Verification
- Standalone offscreen-Qt script (`QT_QPA_PLATFORM=offscreen`, fake
  `%APPDATA%`) — 38 direct checks across all six items: atomic-write
  behavior (a manually-written orphaned `.tmp` never affects the real
  target; no `.tmp` left behind after a real save); missing vs. corrupt
  `library.json`/`custom_categories.json` (quarantine, backup contents,
  `crash.log` entry, reseed, no re-flagging on the next run);
  `seed_library_if_empty()`'s returned status dict feeding
  `main.py`'s `_notify_if_library_was_reset()` (combined single dialog,
  correct backup paths, no dialog when nothing was corrupt); CSV import
  with `utf-8-sig` (regression) and raw `cp1252` bytes (accented
  characters decode correctly), plus a forced both-encodings-fail path;
  partial project load (one `null` slot skipped, sibling valid slot
  survives, correct per-rack skip message) and a fully-invalid-JSON
  project (raises, file byte-identical afterward — confirmed untouched);
  `save_project()` name-collision dedup (second in-memory object's
  `.name` unmutated, resolved name returned separately, correct name
  on disk).
- Two full end-to-end app launches through the real `main.py` entry
  point (offscreen, fresh throwaway `%APPDATA%` each): a genuine
  first-run (silent seed, zero dialogs) and a pre-corrupted
  `library.json` (seed still happens, exactly one "Library reset"
  dialog with the correct backup path). Both confirmed the app
  constructs and shows normally either way.
- Two real-widget flows on an actual `MainWindow`/`ProjectSection` (not
  direct `storage.py` calls): opening a partially-corrupt project
  through `ProjectSection._open_recent()` (real recent-list item,
  correct `MsgBox.warn` call, surviving slot reachable through the live
  project) and a name-collision `MainWindow._save()` (real Save flow;
  confirmed the live project object, the Project-tab form field, and the
  saved file all show the resolved deduped name afterward).

## v0.1.20 — Session 9, 25 July 2026 (dirty-flag / data-loss cluster)

Scoped fix session covering three of Session 7's audit findings — the
"dirty-flag / data-loss" cluster (`task.md` #12, #25, #26). No
version-number bump (still `0.1.20`); no other backlog items touched.
All changes are in `app/main_window.py`.

### Fixed
- **Project Info form fields never marked the project dirty**
  (`task.md` #12): typing into the Project name/number/venue/date/notes
  fields without saving, then choosing New/Open/Open-Recent/Ctrl+N/Ctrl+O,
  silently discarded the unsaved text — none of those fields were wired
  to anything that set `MainWindow._dirty`. `ProjectSection` now has a
  `project_changed` signal, emitted by a new `_on_field_changed()` slot
  connected to all five fields' `textChanged`, and wired to
  `MainWindow._on_changed` (the same handler the Designer canvas already
  uses). A new `ProjectSection._loading` guard flag prevents this from
  firing when fields are set programmatically by `load_project()` or
  `_apply()`, so loading/saving a project no longer spuriously re-dirties
  it.
- **Racks added before the first Save could be silently discarded**
  (`task.md` #25): `ProjectSection` and `DesignerSection` used to each
  construct their own independent default `Project()` at startup, unified
  only by a destructive full-reference swap on the first save — so any
  rack added directly in the Designer tab before that first save was
  silently replaced by the Project tab's separate, empty project, both in
  memory and on disk. Investigated first per the session brief: no call
  site relies on the two starting as genuinely separate objects, and
  every existing New/Open/Save path already converges them onto the same
  object anyway. Fixed at the root: `ProjectSection.__init__` and
  `DesignerSection.__init__` now accept an optional `project=` parameter;
  `MainWindow._build()` constructs one `Project()` and passes that same
  reference to both, so there is no second object to ever swap away.
- **Dirty flag cleared before a save was confirmed to succeed**
  (`task.md` #26): `MainWindow._save()` applies the Project Info form via
  `self.proj_section._apply()`, which emits `project_loaded` and clears
  `self._dirty` — before the `try/except` around `storage.save_project()`
  even starts. If the write then raised, `_dirty` was never restored, so
  `closeEvent()`'s "Save before closing? → Yes" and `_dirty_check()`'s
  "Save before opening another project? → Yes" paths both proceeded as
  if the save had succeeded, even though nothing was written. Re-read
  `_save()`'s current (post-Session-8) shape first, per the brief's
  warning that Session 8 already touched this method — confirmed the
  premature clear is unrelated to Session 8's changes and still present.
  Fixed with the minimal, brief-specified approach: the `except` block
  now explicitly restores `self._dirty = True` and calls
  `self._update_title()` before showing the error dialog, rather than
  restructuring when `project_loaded` fires.

### Files modified
- `app/main_window.py`:
  - `ProjectSection`: new `project_changed` signal, `_loading` flag,
    `_on_field_changed()`; `__init__` now accepts `project=`; `_build()`
    connects the 5 form fields' `textChanged`; `load_project()`/`_apply()`
    guard their programmatic `setText`/`setPlainText` calls with
    `_loading`.
  - `DesignerSection.__init__`: now accepts `project=`.
  - `MainWindow._build()`: constructs one shared `self.project = Project()`,
    passes it to both `ProjectSection` and `DesignerSection`, connects
    `proj_section.project_changed` to `_on_changed`.
  - `MainWindow._save()`: `except` block restores `_dirty = True` and
    calls `_update_title()` before `MsgBox.error(...)`.

### Verification
- Standalone offscreen-Qt script (`QT_QPA_PLATFORM=offscreen`, fake
  `%APPDATA%`) — 23 checks across all three items, driven through real
  `MainWindow`/`ProjectSection` instances:
  - #12: real `QTest.keyClicks` into each of the 5 form fields, each
    confirmed to set `_dirty = True`; confirmed `load_project()` does
    not spuriously re-dirty; a full end-to-end flow (type into
    `name_edit` → call `ProjectSection._new()`, the same path Ctrl+N
    uses, with `MsgBox.question3` mocked) confirmed the unsaved-changes
    prompt now actually fires, and that choosing Cancel leaves the
    in-memory project object untouched.
  - #25: confirmed `proj_section.project is designer.project` right
    after construction; appended a rack directly to
    `designer.project.racks` before any Save, called the real
    `MainWindow._save()`, and confirmed the rack is present both
    pre-save (via `proj_section.project`) and in the file
    `storage.load_project()` reads back afterward.
  - #26: monkeypatched `storage.save_project` to raise, called the real
    `MainWindow._save()` on a dirtied project, confirmed `_dirty` is
    restored `True`, the title bar shows the dirty dot, the error dialog
    fires with the simulated message, `_dirty_check()` still prompts and
    still honors Cancel, and `closeEvent()` still calls
    `event.ignore()`. Regression-checked that a subsequent successful
    save still clears `_dirty` normally.
  - **Sanity checks** (temporarily reverted each fix in the live source
    and re-ran, matching prior sessions' methodology): #25 reverted to
    two independent `ProjectSection()`/`DesignerSection()` constructions
    — the identity check and the rack-survival check both failed exactly
    as the bug describes (rack silently dropped, empty `racks` on disk).
    #26 reverted to the plain `except Exception as e: MsgBox.error(...)`
    — `_dirty` incorrectly stayed `False` after the simulated failure.
    Both fixes were then restored and the full 23-check suite re-run
    clean before moving on.
- A real end-to-end `main.py` startup sequence (offscreen, fresh
  throwaway `%APPDATA%`): `seed_library_if_empty()` → construct
  `MainWindow()` → `.show()` — confirmed `proj_section.project is
  designer.project` and `_dirty` starts `False` on a genuinely launched
  window (not just a constructed-but-hidden one); `QTest.keyClicks` into
  `name_edit` on that real window confirmed `_dirty` still flips `True`
  correctly; closed cleanly via a mocked "discard" response to the
  close-confirmation dialog.
- **Process note**: two early verification attempts hung indefinitely
  (near-zero CPU, `Responding: True`) because a real, un-mocked
  `MsgBox.error`/`MsgBox.question3` modal was reached mid-test —
  `QDialog.exec()` blocks forever under `QT_QPA_PLATFORM=offscreen` with
  no way for a script to click a button. Both were diagnosed via
  `tasklist`/`Get-Process` CPU-time (near-zero CPU = blocked on an
  event loop, not computing) rather than assumed, the stuck processes
  killed, and every dialog static method (`MsgBox.error`/`.warn`/`.info`/
  `.question3`) mocked for the rest of the script. Separately, a full
  `app.exec()` launch was attempted and abandoned — PyQt6's `exec()`
  cannot be safely monkeypatched from outside (it errors
  `TypeError: exec(): too many arguments` when called through a
  reassigned class attribute) — the startup-sequence check above
  (construct + show, without entering the real Qt event loop) was used
  instead, which covers everything Session 8's "full end-to-end app
  launch" checks were actually verifying.

## v0.1.20 — Session 10, 28 July 2026 (rack canvas interaction cluster)

Scoped fix session covering six of Session 7's audit findings — the
"rack canvas interaction" cluster (`task.md` #14, #15, #17, #47, #48,
#49). No version-number bump (still `0.1.20`); no other backlog items
touched. Changes are in `app/main_window.py` (#14/#15/#17) and
`app/rack_canvas.py` (#47/#48/#49).

### Investigated first (per the session brief, ahead of #15)
- Does `Rack` already have a stable identity independent of `name`? Yes —
  `app/models.py`'s `Rack` dataclass already had `id: str =
  field(default_factory=lambda: str(uuid.uuid4()))`, already serialized in
  both `to_dict()`/`from_dict()`, with `from_dict()` generating a fresh id
  for any `.rackproj` written before the field existed. No data-model
  change was needed for #15 — the fix is purely switching the reorder
  match from `name` to the `id` that was already there.

### Fixed
- **Rack reorder corrupted data when two racks shared a name**
  (`task.md` #15): `DesignerSection._on_rack_reordered()` matched each
  sidebar row back to a `Rack` by displayed *name* — two racks both left
  at the default "New Rack" collapsed into one duplicate plus one
  displaced rack on every drag-reorder. `_refresh_rack_list()` now stores
  each row's `rack.id` via `item.setData(Qt.ItemDataRole.UserRole,
  rack.id)` (same pattern as the library list's device rows), and
  `_on_rack_reordered()` matches on that id instead of the name.
- **Sidebar rack selection never updated the "active" canvas, and the
  active canvas dangled on an orphaned widget after add/remove/edit/
  reorder** (`task.md` #14 and #17, fixed together — same root cause):
  `_active_canvas` only ever updated when a canvas itself was clicked, so
  (a) clicking a rack's sidebar row left it pointing at whatever rack was
  last clicked directly, making double-click-to-add target the wrong
  rack, and (b) every add/remove/edit/reorder operation discards and
  rebuilds all `RackCanvas` widgets via `_clear_racks()` +
  `_refresh_rack_view()` without ever reassigning `_active_canvas`, so it
  was left pointing at a destroyed widget — Ctrl+Z would then mutate the
  right data but repaint the wrong (invisible, orphaned) canvas.
  `rack_list.currentRowChanged` is now connected to a new
  `_on_rack_row_selected()`, which calls the existing `_on_canvas_active()`
  for the corresponding canvas — reusing that handler's existing
  deselect/re-sync logic rather than duplicating it. A new
  `_restore_active_canvas(prev_rack_id)` re-points `_active_canvas` at the
  rebuilt canvas matching that rack id (falling back to the first canvas,
  or `None`, if the rack no longer exists), called from `_add_rack()`,
  `_remove_rack()`, `_edit_rack()`, and `_on_rack_reordered()` right after
  their existing rebuild calls.
- **Pasting/cross-rack-dragging a tray used the wrong height, causing
  overlap** (`task.md` #47): for a tray-type source slot,
  `device_snapshot` is always `{}` (falsy), so both `_kb_paste()` and
  `dropEvent()`'s cross-rack branch fell back to a top-level
  `data.get("u_height", 1)` key that `RackSlot.to_dict()` never actually
  produces — always yielding `1` regardless of the tray's real height.
  Both call sites now build the `RackSlot` first and read `.u_height` off
  that instance (which already branches correctly on `is_tray` via
  `tray_u_height()`), reusing existing correct logic instead of
  re-deriving it from raw dict keys.
- **Context-menu "Paste here" ignored the right-clicked cell**
  (`task.md` #48): `_context_menu()` computed the right-clicked
  bay/U correctly for "Insert blank panel" but never forwarded it to
  `_selected_bay`/`_selected_u` before "Paste here" called `_kb_paste()`,
  which used whatever was selected/clicked previously — including a
  stale *occupied-slot* selection, since `_kb_paste()` prefers a non-`None`
  `_selected_slot` over `_selected_u`/`_selected_bay`. The "Paste here"
  branch now clears `_selected_slot` and sets `_selected_u`/`_selected_bay`
  to the right-clicked cell before calling `_kb_paste()`.
- **Duplicate ignored the source's own bay** (`task.md` #49):
  `_kb_duplicate()` blanked `_selected_u`/`_selected_bay` to `-1` before
  calling `_kb_paste()`, which — with `_selected_slot` still equal to the
  source (so `selected_is_source` was `True`, correctly skipping the
  "paste after a different selected slot" branch) and both selection
  fields blanked — always fell through to the last-resort bay-0 search,
  ignoring which bay the source was actually in. `_kb_duplicate()` now
  sets `_selected_u`/`_selected_bay` to `source.position_u +
  source.u_height` / `source.bay` (right after the source, same bay)
  instead of blanking them, so `_kb_paste()`'s existing occupancy search
  starts from the source's own bay; the pre-existing "scan every bay from
  0" fallback still applies only if that bay has no room.

### Files modified
- `app/main_window.py`:
  - `DesignerSection._build()`: new `rack_list.currentRowChanged`
    connection.
  - `DesignerSection._refresh_rack_list()`: stores `rack.id` on each
    `QListWidgetItem` via `Qt.ItemDataRole.UserRole`.
  - `DesignerSection._on_rack_reordered()`: matches racks by `id`, not
    `name`; captures/restores the active canvas across the rebuild.
  - New `DesignerSection._on_rack_row_selected()`,
    `_restore_active_canvas()`.
  - `_add_rack()`, `_remove_rack()`, `_edit_rack()`: each now captures
    `prev_rack_id` before `_clear_racks()`/`_refresh_rack_view()` and
    calls `_restore_active_canvas()` after.
- `app/rack_canvas.py`:
  - `dropEvent()` cross-rack branch: builds `RackSlot` before computing
    `u_height`, reads `.u_height` from it.
  - `_kb_paste()`: same restructuring; reuses the single `RackSlot`
    instance for both the height lookup and the final append.
  - `_context_menu()`: "Paste here" now forwards the right-clicked
    bay/U into the selection state before calling `_kb_paste()`.
  - `_kb_duplicate()`: targets the source's own bay/position instead of
    blanking the selection.

### Verification
- Standalone offscreen-Qt script (`QT_QPA_PLATFORM=offscreen`, fake
  `%APPDATA%`) — 26 checks across all six items:
  - #15: two same-named racks reordered via `_on_rack_reordered()`
    directly — `project.racks` stayed at length 2 with both original
    objects present, in the new order.
  - #14/#17: `rack_list.setCurrentRow(n)` on a real `DesignerSection`
    confirmed `_active_canvas`/`_active_rack_row()` track the sidebar
    selection with no canvas ever clicked; an add-rack-style rebuild
    (`_clear_racks()`+`_refresh_rack_view()`+`_restore_active_canvas()`)
    confirmed `_active_canvas` becomes a *new* widget for the
    still-active rack, and that removing the active rack itself falls
    back to the first remaining canvas rather than dangling.
  - #47: pasted a 3U-tall tray next to a 1U "blocker" slot positioned so
    a correct 3U placement must route around it while an incorrect 1U
    placement would not — confirmed `u_height == 3` and no overlap with
    either neighbor.
  - #48: pre-selected a slot at U5, right-clicked an empty cell at U15,
    drove `_context_menu()` with `QMenu.exec` monkeypatched to
    auto-select "Paste here" — confirmed the paste lands at U15.
  - #49: 3-bay rack, source in bay 2, `_kb_duplicate()` — confirmed the
    duplicate lands in bay 2, not bay 0.
  - **Sanity checks** on every item (not reverting the live source this
    time — reproduced each pre-fix code path directly in the test script
    instead, since none of these six fixes required restructuring a
    method beyond what the check itself exercises): #15's old
    name-matching logic (kept as a local function in the test script)
    against the same two-same-named-rack setup grew `project.racks` to
    3 with a duplicated object; #17's rebuild sequence with
    `_restore_active_canvas()` deliberately skipped left `_active_canvas`
    pointing at a widget no longer in `_canvases`; #47's old
    `snap.get(...)/data.get(...)` fallback expression evaluated to `1`
    against the same tray data; #48's direct `_kb_paste()` call (skipping
    the forwarding) against the same stale-U5-selection setup pasted near
    U5 instead of U15; #49's old blank-to-`-1` approach, called directly,
    fell through to bay 0 against the same bay-2 source. All five
    confirmed the bug before the corresponding fix was trusted.
- Real-widget end-to-end script on an actual, `.show()`n `MainWindow`
  (not a constructed-but-hidden one): real `QTest.mouseClick` on the
  `rack_list` viewport confirmed clicking row 0 then row 1 moves
  `_active_canvas` to each rack's real canvas widget in turn (#14); a
  real `QTest.keyClick(canvas, Key_D, ControlModifier)` on a bay-2 source
  slot confirmed the duplicate lands in bay 2 (#49). `window.close()` was
  deliberately not called in this script — per Session 9's note above, it
  reaches a real, un-mocked dirty-check dialog that blocks forever under
  `QT_QPA_PLATFORM=offscreen`; not needed for what this script verifies.

## v0.1.20 — Session 11, 28 July 2026 (form/dialog + import/categorie cluster)

Scoped fix session covering five of Session 7's audit findings — the
"form/dialog + import/categorie" cluster (`task.md` #20, #21, #27, #29,
#30). No version-number bump (still `0.1.20`); no other backlog items
touched. Changes are in `app/storage.py`, `app/library_dialog.py`, and
`app/main_window.py`.

### Added
- `storage.register_category_if_unknown(category)`: if `category` isn't
  in the known default+custom set, registers it via the existing
  `add_custom_category()`; returns `category` unchanged either way. One
  shared mechanism now used by CSV import, JSON import, and
  `DeviceForm.load()` — see `design.md`.

### Fixed
- **Unrecognized category silently fell back instead of being
  registered** (`task.md` #20 + #30, fixed together — same mechanism):
  `DeviceForm.load()` left the category combo on whatever `reload()`
  defaulted to (index 0, "Video") when a device's category wasn't
  recognized, and JSON import (`LibrarySection._import_dialog()`) never
  registered unrecognized categories the way CSV import already did.
  `DeviceForm.load()` now calls `register_category_if_unknown()` on a
  `findText()` miss, reloads the combo, and re-selects — the real
  category is shown, not a silent default. JSON import's branch now
  scans every imported device's category through the same helper instead
  of hardcoding `new_cats, warnings = [], []`.
- **JSON merge-import could create duplicate device ids** (`task.md`
  #21): merge dedup checked only `(name, category)`, never `id` — an
  imported device whose id already matched an existing library device
  created two entries sharing one id, breaking every by-id operation.
  The Merge branch now tracks `existing_ids` alongside the existing
  `(name, category)` set; any incoming device whose id collides (with the
  library or with another device earlier in the same batch) gets a fresh
  `uuid4()` before being added. The existing device is never touched.
- **Rack-size spinner arrows discarded uncommitted typed text**
  (`task.md` #27): the ▲/▼ buttons in `AddRackDialog`/`EditRackDialog`
  computed the new value from the internal committed
  `_size_val`/`_bays_val`, ignoring whatever was currently typed but not
  yet committed (`editingFinished`/Enter). Both dialogs gained a
  `_step(attr, field, delta, min_val, max_val)` that runs the existing
  `_commit_spin()` (same parse+clamp as `editingFinished`) before applying
  the delta via the existing `_set()`; every arrow button now calls
  `_step(...)` instead of computing `self._size_val ± 1` directly.
- **`rack_native` toggle left a stale `height_mm`** (`task.md` #29):
  toggling "Rack-native" off then back on only disabled `height_mm_spin`
  without clearing its value, so `collect()` could return
  `rack_native=True` with a non-`None` `height_mm`. `_on_rack_native_changed()`
  now also calls `height_mm_spin.setValue(0)` (→ `None` via `collect()`)
  whenever `rack_native` becomes `True`. Checked `width_mm` for the same
  gap per the brief: it doesn't have one — `width_mm_spin` is never
  disabled by this handler in either direction, so there's no
  disabled-but-stale value to clear; left unchanged.

### Files modified
- `app/storage.py`: new `register_category_if_unknown()`;
  `import_library_csv()`'s inline category-registration call switched to
  it.
- `app/library_dialog.py`: `DeviceForm.load()` (registers+reselects an
  unrecognized category); `DeviceForm._on_rack_native_changed()` (clears
  `height_mm_spin` when re-enabling rack-native).
- `app/main_window.py`: `LibrarySection._import_dialog()` (JSON branch
  registers categories; Merge branch re-assigns colliding ids);
  `AddRackDialog`/`EditRackDialog` (new `_step()`, arrow-button
  connections switched to it).

### Verification
- Standalone offscreen-Qt script (`QT_QPA_PLATFORM=offscreen`, fake
  `%APPDATA%`) — 20 checks across all five items:
  - #30: loaded a device with an unrecognized category into a real
    `DeviceForm` — combo shows the real category, it's registered in
    `custom_categories.json`, a no-op `collect()` preserves it.
  - #20 + #21: drove the real `LibrarySection._import_dialog()` (not a
    direct helper call) with `QFileDialog.getOpenFileName`,
    `app.dialogs._MsgDialog`, and `MsgBox.*` mocked. #20: importing a JSON
    device with an unrecognized category registers it. #21: the exact
    scenario from the brief — one device in the library (renamed
    locally, same id as its original JSON export), re-imported the same
    (old-name) JSON via "Merge" — library ends up with 2 devices, 2
    distinct ids, original device's name untouched, new device holds the
    imported name under a fresh id, and editing one doesn't affect the
    other.
  - #27: `AddRackDialog` — typed `"50"` (uncommitted) into the Size
    field, then a real `QTest.mouseClick` on the actual up-arrow
    `QPushButton` (found by text, not a direct method call) — result 51,
    not 21. `EditRackDialog` — typed `"33"`, called `_step(..., -1,
    ...)` — result 32, not 19.
  - #29: unchecked rack-native, set `height_mm_spin` to 199.0, re-checked
    rack-native — `collect()` shows `height_mm=None`,
    `rack_native=True`. Cross-checked `width_mm_spin` stays enabled and
    keeps its value through the same sequence (expected, not a bug).
  - **Sanity checks** on every item — reproduced each pre-fix code path
    directly in the test script (not reverting the live source): #30's
    old `load()` (search+select on hit, nothing on miss) left the combo
    not showing the real category; #21's old `(name, category)`-only
    dedup produced two devices sharing one id; #27's old arrow lambda
    (no commit first) yielded 21 instead of 51; #29's old handler
    (`setEnabled(False)` only) left `height_mm=199.0` despite
    `rack_native=True`. All four confirmed the bug before the
    corresponding fix was trusted.
- Re-ran the Session 10 full-app-launch smoke test (`main.py`'s real
  startup sequence through `window.show()`, offscreen) to confirm no
  regression from these changes.
- **Process note**: an early version of the #20/#21 verification script
  hung on `LibrarySection._import_dialog()`. Diagnosed via `Get-Process`
  CPU time (near-zero = blocked on an event loop, not computing), same
  method as Session 9's process note. Root cause here was different from
  Session 9's: `_import_dialog()` does a **local**
  `from app.dialogs import _MsgDialog` inside the function body, so
  patching `main_window`'s own module attribute (`mw._MsgDialog = ...`)
  has no effect — the function's local import always re-binds to the
  real class. Fixed by patching the class at its actual home
  (`app.dialogs._MsgDialog = ...`) instead.

## v0.1.20 — Session 12, 28 July 2026 (PDF export cluster)

Scoped fix session covering seven of Session 7's audit findings, all in
`app/pdf_export.py` — the PDF export cluster (`task.md` #55-#61). No
version-number bump (still `0.1.20`).

### Added
- `_slot_colors(raw_hex, grayscale=False)`: derives a slot's
  (accent, background, border) hex triple, running the raw colour
  through the previously-unused `_to_gray()` first when grayscale.
- `_truncate_text(c, text, font, size, max_width)`: truncates to the
  longest prefix + ellipsis that fits, measured via `c.stringWidth()`.
- `cell_wrap`/`summary_cell` `ParagraphStyle`s for table cells that need
  to wrap instead of overflow.

### Fixed
- **Wrong per-unit specs for same-named devices** (`task.md` #55):
  device-list grouping now keys on `(name, watts, weight_kg, category)`
  instead of `name` alone. Devices that genuinely match on all four
  still collapse into one multiplied-qty row; devices sharing a name but
  differing in spec now get their own accurate row. No name-suffix
  disambiguation added — same name on two rows is fine, only the numbers
  needed to be right.
- **Zero rendered as "—"** (`task.md` #56): the device-list "each"
  Watts/kg expressions now check `is not None` instead of truthiness — a
  genuine `0` shows `"0"`/`"0.00"`, only an actually-unset field shows
  `"—"`.
- **Long names overflowed table cells** (`task.md` #57): device-list
  `Device`/`Category` cells and the project-summary `Rack` name cell are
  now wrapped in a `Paragraph` (same technique `Notes` already used)
  instead of a bare string — long text wraps within its column instead
  of overflowing into neighbours.
- **Long device names overflowed the rack diagram** (`task.md` #58):
  `RackDrawing.draw()` now measures the U-badge's real width and the
  name's real width via `c.stringWidth()`, truncating the name with an
  ellipsis into whatever space remains before the badge, instead of
  drawing it unbounded.
- **Shrunk rack with out-of-bounds slots rendered detached** (`task.md`
  #59): `RackDrawing` now computes its drawing geometry from
  `max(rack.u_size, occupied_top)` — the higher of the nominal U-size and
  the highest actually-occupied extent among the rack's slots — instead
  of trusting `rack.u_size` blindly. A rack with no overflow is
  unaffected; `rack.u_size` itself and everything derived from it
  elsewhere (used/free-U stats) are untouched.
- **Grayscale lost category differentiation** (`task.md` #61): the
  `use_color=False` branch now runs each slot's actual category-derived
  colour through `_to_gray()` (via the new `_slot_colors()`) instead of a
  flat hardcoded neutral — categories stay visually distinguishable in
  grayscale.

### Investigated, not fixed
- **Tall racks can leave the previous page mostly blank** (`task.md`
  #60): investigated per the brief's explicit instruction. Every fix that
  would genuinely eliminate the blank-space symptom requires
  `RackDrawing` to react to the real remaining frame height, which
  ReportLab's Platypus model only exposes at actual build time (via the
  Flowable `wrap()` protocol), not while the `story` list is being
  constructed — confirmed `KeepTogether` isn't itself the cause (the
  diagram, a non-splittable Flowable, would independently defer to a new
  page regardless of grouping). The one option that would actually work —
  an adaptive `RackDrawing.wrap()` that rescales to whatever space is
  really left — trades away the current guarantee that a rack's rendered
  scale depends only on its own U-size/bay-count, not on what precedes it
  in the document; every other option considered (loosening
  `KeepTogether`, forcing every rack onto its own page, shrinking
  `MAX_RACK_H` further) either doesn't address the root cause or has its
  own broader downside. Hit the brief's own stop condition — not fixed
  this session; see `task.md` #60 for the full per-option reasoning and
  recommendation.

### Files modified
- `app/pdf_export.py`: `_slot_colors()`, `_truncate_text()` (new);
  `RackDrawing.__init__()` (`_draw_u_size`); `RackDrawing.draw()`
  (geometry now uses `_draw_u_size`; unified color derivation; name
  truncation); `export_pdf()` (device-list grouping key/sort, zero
  formatting, `Paragraph`-wrapped cells in both tables); removed
  `COL_SLOT_OCC`/`COL_STRIPE_NEUTRAL` (dead after the color-derivation
  unification); `cell_notes` style renamed `cell_wrap`, new
  `summary_cell` style.

### Verification
- Standalone offscreen script — 33 checks across the six fixed items:
  - #55: 3 slots sharing a name (2 matching, 1 differing in watts)
    produce 2 groups with correct qty each; real `export_pdf()` runs
    clean.
  - #56: `0` formats as `"0"`/`"0.00"`, `None` still formats as `"—"`;
    real export with a 0-watt/0-kg device runs clean.
  - #57: a long name/category, each wrapped at their real column width,
    produce multi-line `Paragraph.wrap()` heights (not one unbroken
    line); a bare string has no such wrap concept at all (confirming the
    old cells couldn't wrap).
  - #58: `_truncate_text()` shortens an oversized name to fit (ends in
    "…", measured width `<= max_width`), leaves a name that already fits
    untouched.
  - #59: a `u_size=5` rack with a slot at U8-U9 computes
    `_draw_u_size=9`; a normal rack keeps `_draw_u_size == rack.u_size`.
  - #61: `_slot_colors(..., grayscale=True)` gives three sample category
    colours three distinct, genuinely-monochrome accent shades, each
    different from the raw color (confirming `_to_gray()` is actually
    invoked).
  - **Sanity checks** on every item — reproduced each pre-fix code path
    directly in the test script: old name-only grouping collapsed all 3
    mismatched-spec slots into one row; old truthy check rendered `0` as
    `"—"`; old hardcoded-neutral grayscale gave two different categories
    the identical accent; the raw untruncated name's measured width
    genuinely exceeded the available slot width; `rack.u_size` (5) alone
    is less than the real occupied extent (9). All confirmed the bug
    before the corresponding fix was trusted.
- **Visual inspection (PyMuPDF-rendered PNG, viewed directly)** for the
  four visual findings, per the brief:
  - #57/#58 (same test rack, a long name feeding both the table and the
    diagram): Device cell wraps to 4 lines within its own column, no
    overlap into Category/W/kg; project-summary Rack name wraps to 3
    lines, no overlap into Size/Used/Free/Devices; the rack diagram
    truncates the same oversized name to "…Extremely Long Device Mo…"
    fully inside the slot with the U-badge intact.
  - #59: a nominally-5U rack's diagram now draws 9 numbered U rows (not
    5), with the out-of-bounds 2U device rendered fully inside the rack's
    own border at the top — no bleed into the device-list table or
    "Project summary" heading below it.
  - #61: a grayscale export with Video/Audio/Lighting slots shows three
    visibly different gray-shade stripes/fills, correctly distinguishable
    by category (previously three identical gray boxes).
- Re-ran the existing full-app-launch smoke test (`main.py`'s real
  startup sequence through `window.show()`, offscreen) to confirm no
  regression from these `pdf_export.py`-only changes.

## v0.1.20 — Session 13, 28 July 2026 (close #60, math/validation cluster)

No version-number bump (still `0.1.20`).

### Closed, no code change
- **#60** (tall racks can leave the previous PDF page mostly blank):
  project owner reviewed Session 12's trade-off analysis and chose to
  accept the occasional cosmetic blank-page behavior rather than trade
  away the export's guarantee that a rack's rendered scale depends only
  on its own spec. Marked `[done]`/decided-not-to-fix in `task.md`, not
  merely left open.

### Fixed
- **`mm_to_u()` over-allocated a U on exact multiples** (`task.md` #32):
  floating-point division before `math.ceil()` could round an exact
  multiple of `RACK_U_MM` up an extra U (e.g. `3*44.45` → 4, not 3).
  Fixed by subtracting a `1e-9` epsilon before ceiling — the standard fix
  for this class of float-division rounding error; non-exact heights are
  unaffected.
- **CSV category normalization only uppercased the first character**
  (`task.md` #36): `"AUDIO"` failed to match the built-in `"Audio"` and
  registered as a permanent near-duplicate custom category.
  `import_library_csv()` now checks case-insensitively against the known
  category set first, reusing the existing category's real casing on a
  match; only a genuinely new category gets normalized to Title Case and
  registered.
- **CSV integer parsing used banker's rounding** (`task.md` #37):
  `_parse_int()` (used only for the CSV `Height (U)` column — confirmed
  via grep, no other call site exists) now ceilings instead of
  round-half-to-even, matching `mm_to_u()`'s philosophy and physical
  reality (2.5U of space needs 3U of rack).
- **Loaded numeric fields bypassed range clamps** (`task.md` #31):
  `DeviceForm.load()` populated spin fields via `.setValue()`, which
  didn't clamp to the field's declared min/max the way manual
  typing/arrow-stepping does. Fixed at the shared `_set_value()`
  implementation behind every spin widget's `.setValue()` (covers all
  callers, not just `load()`), plus an explicit `[1,20]` clamp on the
  U-height field (a separate, non-spin-widget construct).
- **`Rack` bay-scoped helpers didn't validate `bay`** (`task.md` #40):
  an out-of-range `bay` (only reachable via corrupted project data) was
  silently invisible to `is_slot_occupied()`/`next_free_position()`/
  `slot_at()` while `free_u()` still counted its U against capacity.
  Investigated whether to patch each helper or normalize once at load —
  chose the latter: `Rack.from_dict()` now clamps every loaded slot's
  `bay` to `[0, bays-1]`, since the only realistic way to get an
  out-of-range `bay` is a corrupted `.rackproj` file (nothing in the live
  UI can produce one).

### Files modified
- `app/models.py`: `mm_to_u()` (epsilon); `Rack.from_dict()` (bay clamp).
- `app/storage.py`: `import_library_csv()` (case-insensitive category
  match); `_parse_int()` (ceiling); added `import math`.
- `app/library_dialog.py`: `_make_spin_widget`'s `_set_value()` (clamp);
  `DeviceForm.load()` (U-height clamp).

### Verification
- Standalone offscreen script — 38 checks across the five fixed items:
  - #32: `mm_to_u(3*44.45)==3`, `mm_to_u(6*44.45)==6`,
    `mm_to_u(12*44.45)==12`; non-exact heights (`100`, `44.45`, `1`)
    unchanged.
  - #36: a CSV with `Category=AUDIO` and `Category=WIRELESS MIC` — the
    first maps onto the existing `"Audio"` (not reported as new), the
    second registers as `"Wireless mic"`.
  - #37: `_parse_int("2.5")==3`, `("4.5")==5`, `("3.5")==4`,
    `("1.5")==2` (no longer parity-dependent); a real CSV import with
    `Height (U)=2.5` produces `u_height=3`.
  - #31: a device with every numeric field far out of range
    (`u_height=999`, `width_mm=9999`, `height_mm=9999`, `depth_mm=9999`,
    `watts=9999999`, `weight_kg=99999`) loaded into a real `DeviceForm` —
    every field clamps to its declared max; a normal in-range device is
    unaffected.
  - #40: a `bays=1` rack dict with a slot's `bay=2` — `Rack.from_dict()`
    clamps it to `0`, and `is_slot_occupied()`/`free_u()`/`used_u()` all
    agree afterward; a valid bay on a `bays=3` rack is unaffected.
  - **Sanity checks** on every item — reproduced each pre-fix code path
    directly in the test script: old `mm_to_u()` formula over-allocated
    to 4/7; old CSV normalization left `"AUDIO"` as `"AUDIO"`; old
    `_parse_int()` gave `2.5 → 2`; old unclamped `.setValue()`/direct
    U-height assignment left out-of-range values in place; an
    unclamped `bay=2` on a `bays=1` rack never matches the only valid
    bay argument (`0`), reproducing the occupancy/`free_u()`
    disagreement. All confirmed the bug before the corresponding fix was
    trusted.
- Re-ran the existing full-app-launch smoke test (`main.py`'s real
  startup sequence through `window.show()`, offscreen) to confirm no
  regression from these changes.

## v0.1.20 — Session 14, 29 July 2026 (two missed likely-real-and-impactful items)

No version-number bump (still `0.1.20`). Two Session 7 audit findings
that had been triaged `likely-real-and-impactful` but not yet picked up
in Sessions 8-13.

### Fixed
- **Off-by-one falsely blocked legal rack-shrink operations** (`task.md`
  #16): `DesignerSection._edit_rack()`'s occupancy check for the rows
  being removed from the top, `removed_rows = range(1, 1 - delta + 1)`,
  evaluated to `1..n+1` (one row too many) instead of `1..n` for
  `n = abs(delta)` U being removed — rejecting resizes that were actually
  legal (e.g. a device at U2 blocked a 1U shrink even though the true top
  row, U1, was empty). Fixed to `range(1, -delta + 1)`, covering exactly
  the rows actually being removed.
- **Cross-rack drop onto an existing tray never merged** (`task.md`
  #51): `RackCanvas.dropEvent()`'s cross-rack "application/x-rackslot"
  branch never attempted a tray merge the way the library-device-drop
  branch just below it already did — dropping a non-rack-native device
  dragged from another rack onto an existing tray with spare width was
  rejected as "Not enough free space," even when the tray had plenty of
  room. The cross-rack branch now attempts the same
  `_can_add_to_tray()`/`_add_to_tray()` merge (via a `DeviceDefinition`
  built from the dropped slot's snapshot) before falling through to the
  existing occupied/free-space append logic, mirroring the library-drop
  branch's own merge block exactly.

### Files modified
- `app/main_window.py`: `DesignerSection._edit_rack()`.
- `app/rack_canvas.py`: `RackCanvas.dropEvent()`'s cross-rack branch.

### Verification
- Standalone offscreen script — 14 checks across both items:
  - #16: drove the real `DesignerSection._edit_rack()` (fake
    `EditRackDialog`, mocked `MsgBox.warn`) on the exact finding
    scenario — a 20U rack with a 1U device at U2, shrunk to 19U: now
    allowed, no warning, device correctly shifts U2→U1. Confirmed a
    shrink that should be blocked (device genuinely at U1) still is.
  - #51: direct calls to `RackCanvas.dropEvent()` with a lightweight
    duck-typed fake mime-data/drop-event against a rack fully occupied
    except one tray with spare width: drop accepted, no warning, tray
    ends up with both devices, no new slot appended. Confirmed a
    genuinely full rack (no tray, no room) still correctly rejects.
  - **Sanity checks**: evaluated the old `range(1, 1 - delta + 1)`
    formula directly against the U2-device scenario — confirmed it
    falsely blocks; reproduced the old cross-rack drop logic (no
    tray-merge) directly against the identical oversubscribed-except-tray
    setup — confirmed it finds no free position anywhere. Both
    reproduced their bug before the corresponding fix was trusted.
- Re-ran the existing full-app-launch smoke test (`main.py`'s real
  startup sequence through `window.show()`, offscreen) to confirm no
  regression from these changes.

## v0.1.20 — Session 15, 29 July 2026 (preloaded library data cluster)

Scoped fix session covering four of Session 7's audit findings — the
"preloaded library data" cluster (`task.md` #41, #42, #43, #44), plus one
documentation-only item (`task.md` #46). No version-number bump (still
`0.1.20`); no logic changes, no other backlog items touched.

### Fixed
- **Redundant "Lighting" custom category on fresh installs** (`task.md`
  #41): `_EXTRA_CATEGORIES` (`app/preloaded_library.py`) listed
  `"Lighting"`, which is already in `models.DEFAULT_CATEGORIES` — every
  fresh install registered it a second time as a redundant custom
  category. `_EXTRA_CATEGORIES` was the only entry in the list, so it was
  emptied to `[]` rather than partially edited. Scoped to fresh installs
  only, as directed — existing installs' `custom_categories.json` are not
  retroactively cleaned up.
- **Two copy-pasted `model` strings** (`task.md` #42, #43): "Disguise GX
  3" had `model="GX 3+"` (identical to the real GX 3+ entry despite
  differing specs) — corrected to `model="GX 3"`. "Barco E2" had
  `model="E2 Gen 2"` (identical to the real Gen2 entry) — corrected to
  `model="E2"`. Both now describe the device's own generation instead of
  duplicating a sibling's. **Internal-consistency corrections, not
  verified against actual Disguise/Barco vendor spec sheets.**
- **Two implausible `depth_mm` values** (`task.md` #44): "Blackmagic
  MultiView 16" had `depth_mm=15.4` (implausible for a 1U chassis) —
  corrected to `170.0`, matching its sibling "Blackmagic MultiView 4"'s
  depth, used as the best available estimate. "UPS 5P 1150" had
  `depth_mm=43.2` — corrected to `438.0`, matching its Gen2 sibling
  (same `width_mm=438.0`); the digit-pattern match between `43.2` and
  `438.0` strongly suggests a transcription error in the original entry.
  **Both are best-estimate corrections from sibling-device
  cross-comparison, not verified against actual vendor spec sheets.**

### Changed (documentation only)
- **Preloaded-library device count corrected from "20-device" to
  "119-device"** (`task.md` #46): grepped `docs/*.md` for the stale
  claim and corrected it in the three places it appeared —
  `folder_structure.md`'s module comment, `design.md`'s module-map table,
  `status.md`'s "What works" summary. The real count (119) was
  reconfirmed via a fresh grep-count of `DeviceDefinition(` occurrences
  in the live `app/preloaded_library.py`, not just trusted from the
  finding's own text.

### Files modified
- `app/preloaded_library.py` — `_EXTRA_CATEGORIES` (emptied); "Disguise
  GX 3" and "Barco E2" `model` fields; "Blackmagic MultiView 16" and
  "UPS 5P 1150" `depth_mm` fields.
- `docs/folder_structure.md`, `docs/design.md`, `docs/status.md` —
  "20-device" → "119-device" (or equivalent phrasing).

### Verification
- Standalone offscreen-Qt script (`QT_QPA_PLATFORM=offscreen`, fresh
  throwaway `%APPDATA%`): ran the real `seed_library_if_empty()` — the
  full library still seeds all 119 devices; confirmed
  `storage.load_custom_categories().items == []` afterward (no
  `"Lighting"` entry written, where a real install would previously have
  had one). Confirmed the four corrected fields load with their new
  values off the real seeded library (`Disguise GX 3`.model == "GX 3",
  `Barco E2`.model == "E2", `Blackmagic MultiView 16`.depth_mm == 170.0,
  `UPS 5P 1150`.depth_mm == 438.0). Constructed and `.show()`ed a real
  `MainWindow()` against this library — no exception, confirming the
  data edits didn't introduce a schema/loading issue. No sanity-revert
  performed — these are plain data corrections with no "does it still
  fail correctly" question, per the task's own framing.
- Reconfirmed the preloaded library's real device count via
  `grep -c "DeviceDefinition("` against the live
  `app/preloaded_library.py`: 119, matching what all three corrected doc
  references now say.

## v0.1.20 — Session 16, 29 July 2026 (startup robustness cluster)

Scoped fix session covering three of Session 7's audit findings — the
"startup robustness" cluster (`task.md` #62, #63, #64). No
version-number bump (still `0.1.20`). Extends Session 3's original
`sys.excepthook` mechanism into a coherent three-layer model, documented
as a whole in `design.md`.

### Added
- `main.py`: `_log_crash(exc_type, exc_value, exc_tb)` — the one shared
  crash-log-writing implementation, factored out of `_excepthook`'s
  existing body. `_excepthook` and the new seeding guard (below) both
  call it.
- `main.py`: `_log_pre_qt_crash(exc_type, exc_value, exc_tb)` — a
  second, deliberately independent logger for failures before
  `QApplication` exists. Plain `os`/`pathlib`/`datetime`/`traceback`
  only; duplicates `get_app_data_dir()`'s two-line path logic instead of
  importing it, since at this stage either PyQt6 or the `app` package
  itself could be exactly what's broken.
- `main.py`: `_notify_seed_failed(parent)` — a themed error dialog shown
  once, after `window.show()`, when `seed_library_if_empty()` itself
  raised. Distinct from the existing `_notify_if_library_was_reset()`
  ("found and quarantined a corrupt file" vs. this, "failed to seed at
  all").

### Fixed
- **An exception during first-run library seeding killed the app before
  the window ever appeared** (`task.md` #62): `seed_library_if_empty()`
  ran unguarded before `MainWindow` was constructed — a failure there
  (disk full, permission denied, AV lock, OneDrive lock) still logged
  and dialoged via the already-installed `sys.excepthook`, but the
  process still terminated immediately after, since a hook firing
  doesn't resume execution past where the exception originated.
  `main()` now wraps the `seed_library_if_empty()` call in its own
  `try/except`: on failure, `_log_crash()` records the traceback and a
  `seed_failed` flag is set, but `MainWindow` is constructed and shown
  regardless — the app comes up with whatever library state exists
  (likely empty) instead of not coming up at all. `_notify_seed_failed()`
  then explains the situation once the window is visible.
- **A pre-`QApplication` startup exception was completely silent**
  (`task.md` #63): a broken Qt platform plugin/driver during
  `QApplication()` construction, or an import-time failure in any of
  `main.py`'s own top-level imports, fell through to Python's raw
  default excepthook — silent for a windowed launch with no console: no
  log, no dialog, the app just never appears. `main.py`'s top-of-file
  imports are now wrapped in `try/except`, and `QApplication(sys.argv)`
  inside `main()` is wrapped the same way; both call
  `_log_pre_qt_crash()` then re-raise. The process still exits either
  way — this layer's entire job is making sure the failure reaches
  `crash.log` before it does, since no dialog is possible this early.
- **`MsgBox`/`_MsgDialog` wasn't defensive against non-string
  arguments** (`task.md` #64): no type-coercion was applied to
  `title`/`message` before handing them to Qt widgets — a non-`str`
  value (e.g. an `Exception` instance passed directly instead of
  `str(e)`) raised `TypeError`, so the dialog itself failed to display.
  No current call site triggered this before this session, but #62's
  new `_notify_seed_failed()` call goes through exactly this path.
  `_MsgDialog.__init__()` now coerces `title = str(title)` /
  `message = str(message)` at the top, before either is used. Grepped
  every `MsgBox.*` call site first to confirm none pass `None` today
  (an unconditional `str()` would turn `None` into the literal text
  `"None"`) — all pass real strings, so this is a pure safety net with
  no behavior change for any existing caller.

### Files modified
- `main.py`: `_log_crash()` (new, factored out of `_excepthook`);
  `_log_pre_qt_crash()` (new); `_notify_seed_failed()` (new);
  top-of-file imports wrapped in `try/except`; `QApplication(sys.argv)`
  wrapped in `try/except`; `seed_library_if_empty()` call wrapped in
  `try/except`.
- `app/dialogs.py`: `_MsgDialog.__init__()` (`str()` coercion on
  `title`/`message`).

### Verification
- Standalone offscreen-Qt script (`QT_QPA_PLATFORM=offscreen`, fresh
  throwaway `%APPDATA%`) covering #62: forced `seed_library_if_empty()`
  to raise — confirmed `MainWindow` still constructs and `.show()`s,
  confirmed exactly one `MsgBox.error` call with the new "Library
  initialization failed" title/message, confirmed `crash.log` contains
  the simulated traceback. Confirmed the unchanged happy path (no
  exception) still seeds all 119 devices with zero dialogs. **Sanity
  check**: reproduced the exact pre-fix sequence (unguarded call
  directly followed by `MainWindow()` construction) against the same
  forced failure — confirmed the exception propagates and `MainWindow`
  is never constructed, reproducing the bug before trusting the fix.
- #63, tested as best possible given the "no Qt yet" constraint: a real
  `import main` in a fresh interpreter with `app.main_window`'s import
  forced to fail via a `sys.meta_path` finder/loader (Python 3.12's
  actual import-failure mechanism — not a simulated call) — confirmed
  the `ImportError` still propagates out of `import main` (not silently
  swallowed) **and** `crash.log` received the full traceback, even
  though no `QApplication`/window/dialog ever existed in that process.
  Confirmed `_log_pre_qt_crash()`'s own code (excluding its docstring)
  references only `os`/`Path`/`datetime`/`traceback`/builtins. **Not
  directly testable**: a genuinely broken Qt platform plugin/driver at
  the OS level (this environment's Qt install works regardless of
  `QT_QPA_PLATFORM=offscreen`) — covered instead by exercising the
  identical `try/except` → `_log_pre_qt_crash()` → re-raise structure
  via the import-failure scenario above. **Sanity check**: re-ran the
  identical import-failure scenario against a reconstructed pre-fix
  `main.py` (unguarded imports, no `_log_pre_qt_crash`) — the
  `ImportError` still propagated, but zero files were written under the
  fake `%APPDATA%` at all, confirming the silence described by the
  finding before trusting the fix.
- #64: constructed `_MsgDialog` directly with a non-string title (`int`)
  and a non-string message (an `Exception` instance) — confirmed
  `windowTitle()` shows the stringified value and the message label
  shows the exception's `str()` text, no `TypeError`. Called the real
  public `MsgBox.error()` with a non-string title and message — confirmed
  it displays without raising. **Sanity check**: reproduced the pre-fix
  constructor logic directly (no `str()` coercion) against the same
  non-string title — confirmed `TypeError` (Qt's own type-check message),
  reproducing the bug before trusting the fix.
- Re-ran the existing full-app-launch smoke test (all of Session 16's
  new code paths — imports, `QApplication` construction, the seeding
  guard, `MainWindow` construction/show, both notify functions — driven
  end-to-end short of the blocking `app.exec()`) to confirm no
  regression: completed with no exception, library seeded at 119
  devices, `seed_failed` correctly `False` on the clean path.

## v0.1.20 — Session 17, 29 July 2026 (final cleanup: 11 minor/cosmetic items)

Scoped fix session covering the last 11 Session 7 audit findings (`task.md`
#13, #18, #19, #22, #23, #24, #28, #50, #52, #53, #54) — all real-but-minor
or informational. No version-number bump (still `0.1.20`). **Closes out
the Session 7 audit backlog**: all 53 original findings are now either
fixed or explicitly decided-not-to-fix (#60).

### Fixed
- **Failed recent-project load left the wrong row selected** (`task.md`
  #13): `ProjectSection._open_recent()`'s `except` branch now calls
  `self._refresh_recent()` after showing the error dialog, matching the
  sibling dirty-check-cancelled branch above it.
- **Designer tab's category filter never refreshed** (`task.md` #18):
  `DesignerSection.reload_library()` now rebuilds `cat_filter`'s items
  the same way `LibrarySection.reload()`'s equivalent combo already did
  (preserve selection by text, clear, re-add, re-select), instead of
  only rebuilding the device list.
- **Misleading 0-rack message** (`task.md` #19):
  `DesignerSection._add_device_dbl()` now shows "No racks in project."
  for the actual 0-rack case, matching `_add_custom()`'s wording, instead
  of the misleading "Select a rack first."
- **Merge-import dedup set was stale within the same import** (`task.md`
  #22): the Merge branch of `LibrarySection._import_dialog()` now
  iterates the imported devices once, updating `existing`/`existing_ids`
  after each addition, so two colliding entries within the same imported
  file are both caught — not just entries colliding with the
  pre-import library state.
- **CSV export silently dropped images with no warning** (`task.md`
  #23): the CSV branch of `_export_dialog()` now shows a `MsgBox.info`
  notice once, right after CSV is chosen as the export format, that
  images aren't included and JSON export preserves them. The CSV format
  itself is unchanged.
- **Empty-library category-scope export opened a dead-end dialog**
  (`task.md` #24): the "Category" scope branch now checks for an empty
  category list before ever opening the `QInputDialog` picker, showing a
  clear "Library is empty" message instead.
- **Rack-size preset combobox didn't stay in sync** (`task.md` #28):
  `AddRackDialog` gained `_sync_preset_combo()`, called from `_set()`
  (the one place `_size_val` is actually written, reached by typing, the
  arrow buttons, or the preset combo itself) and once explicitly at the
  end of `__init__()` for the initial 20U default — the combo now always
  shows the matching preset, or "Custom" if none matches.
- **Drag state ignored which mouse button was released** (`task.md`
  #50): `RackCanvas.mouseReleaseEvent()` now also checks
  `event.button() == Qt.MouseButton.LeftButton` before clearing drag
  state — a right-button release/click mid-left-drag no longer
  prematurely ends the drag.
- **Library-device drop "no space" didn't ignore the drop event**
  (`task.md` #52): `RackCanvas.dropEvent()`'s library-device-drop "no
  space" branch now calls `event.ignore()`, matching the cross-rack
  branch's existing behavior in the same situation.
- **Hover-preview highlight wasn't clamped to rack bounds** (`task.md`
  #53): `RackCanvas.paintEvent()`'s hover-preview block now clamps the
  drawn U range to `[1, rack.u_size]` before drawing (and skips drawing
  entirely if the clamped range is empty), instead of drawing a
  rectangle that could extend past the rack frame.
- **Editing a tray slot's name was silently discarded** (`task.md` #54):
  `SlotEditDialog` no longer shows a name field for a tray slot at all —
  a short explanatory label takes its place — and `RackCanvas._edit_slot()`
  now returns immediately for a tray without pushing an undo entry or
  emitting `slot_moved`, since nothing in the dialog is editable for a
  tray. No new "tray label" data field was added, per the decided fix
  direction.

### Files modified
- `app/main_window.py`: `ProjectSection._open_recent()`;
  `DesignerSection.reload_library()`, `._add_device_dbl()`;
  `LibrarySection._import_dialog()`'s Merge branch, `._export_dialog()`
  (CSV notice, empty-category guard); `AddRackDialog` (new
  `_sync_preset_combo()`, `_set()`, `__init__()`).
- `app/rack_canvas.py`: `mouseReleaseEvent()`; `dropEvent()`'s
  library-device-drop branch; `paintEvent()`'s hover-preview block;
  `SlotEditDialog.__init__()`, `.get_name()`; `RackCanvas._edit_slot()`.

### Verification
- Standalone offscreen-Qt script (`QT_QPA_PLATFORM=offscreen`, fresh
  throwaway `%APPDATA%`) — 18 checks bundled into one script across all
  11 items, driven through the real classes/methods (`ProjectSection`,
  `DesignerSection`, `LibrarySection`, `AddRackDialog`, `RackCanvas`,
  `SlotEditDialog`) rather than one script per item, per the brief's own
  "bundle verification where reasonable" instruction:
  - #13: spied on `_refresh_recent()`, forced `storage.load_project()`
    to raise — confirmed it's now called after the error dialog.
  - #18: registered a new custom category, called the real
    `reload_library()` — confirmed the category is now present in
    `cat_filter`'s items.
  - #19: called the real `_add_device_dbl()` on an empty project —
    confirmed the message is now "No racks in project."
  - #22: imported a JSON file with two devices sharing `(name,
    category)` via the real `_import_dialog()` (`QFileDialog`/
    `_MsgDialog` mocked) — confirmed only 1 of 2 is added. **Sanity
    check**: reproduced the pre-fix static-set comprehension directly —
    confirmed it would have added both.
  - #23: drove the real `_export_dialog()` (format pickers mocked) —
    confirmed the CSV image-loss notice fires.
  - #24: drove the real `_export_dialog()` with an empty library,
    "Category" scope — confirmed the picker never opens and the
    empty-library message fires instead.
  - #28: confirmed the combo shows "20U" on construction, "Custom"
    after typing 25, "24U" after stepping down to 24.
  - #50: dispatched a synthetic right-button release mid-drag —
    confirmed `_drag_slot` is unaffected; a left-button release still
    clears it. **Sanity check**: reproduced the pre-fix
    button-agnostic body directly — confirmed it clears regardless of
    button.
  - #52: a duck-typed fake drop event against a fully-occupied rack —
    confirmed `dropEvent()` now calls `.ignore()`, not
    `.acceptProposedAction()`.
  - #53: confirmed the clamp math now used in `paintEvent()` reduces a
    hover state that would extend 3U past a 3U rack's bottom edge to
    `[2, 3]`; confirmed a real `paintEvent()` call with the unclamped
    out-of-range hover state doesn't raise.
  - #54: confirmed `SlotEditDialog` for a tray slot has `name_edit is
    None` and `get_name() is None`; confirmed the real `_edit_slot()` on
    a tray leaves the undo stack length and a `slot_moved` listener's
    fire count unchanged. **Sanity check**: reconstructed the pre-fix
    flow (unconditional undo-push + silent-discard + unconditional
    emit) — confirmed it would have pushed undo and emitted despite
    discarding the typed name.
- Re-ran the existing full-app-launch smoke test (`main.py`'s real
  startup sequence through `window.show()`, offscreen) plus a quick
  `AddRackDialog` construction check, to confirm no regression from
  this session's changes across two files: completed with no exception,
  library at 119 devices, preset combo correctly showing "20U".

## v0.1.20 — Session 18, 29 July 2026 (new feature: export rack diagrams as PNG)

New feature session (`task.md` #65) — the Session 7 audit backlog closed
out completely in Session 17; this is the first fresh-numbered work item
since. No version-number bump (still `0.1.20`).

### Added
- **Export racks as PNG**: a new "EXPORT RACKS AS PNG" button in the
  Export tab, alongside the existing PDF export controls. Picks a
  destination folder and writes one PNG per rack in the project, at its
  natural (uncapped) size — not scaled to fit an A4 page the way the PDF
  diagram is. Uses whatever "Use device colours" checkbox state the PDF
  export already exposes, at a fixed 300 DPI. Filenames are sanitized
  from each rack's name using the exact same character filter
  `storage.save_project()` already uses for project filenames, and
  deduplicated (two racks sharing a name, a sanitize-to-the-same-string
  collision, or a pre-existing file in the destination folder) via the
  same `" (2)"`/`" (3)"` suffix pattern — never a silent overwrite. A
  single rack's export failure doesn't abort the batch; it's logged and
  the rest proceed. A completion dialog reports how many succeeded, the
  destination folder, and every per-rack failure by name.
- `app.pdf_export.export_rack_png(rack, filepath, use_color=True,
  dpi=300)`: the new export function. Builds a `RackDrawing` in a new
  natural-size mode (see below), renders it onto a single-page in-memory
  ReportLab PDF sized exactly to the drawing's true dimensions, then
  rasterizes that one page to PNG via PyMuPDF at the given DPI.
  Deliberately reuses `RackDrawing.draw()` — the identical code
  `export_pdf()` already calls for every rack in a full document —
  instead of a second renderer, so every PDF-export correctness fix from
  the Session 12 audit cluster (device-name truncation, out-of-bounds
  -slot containment, grayscale per-category shading) applies to PNG
  export automatically, with nothing to keep in sync by hand.
- `RackDrawing.__init__()` gained a `page_fit: bool = True` parameter.
  Defaulting `True` means `export_pdf()`'s existing behavior is
  unchanged byte-for-byte — every call site in the multi-rack PDF
  document path still omits it, so nothing there changed this session.
  `page_fit=False` (used only by `export_rack_png()`) skips the
  `scale_h`/`scale_w`/`MAX_RACK_H`/`MAX_RACK_W` page-fit computation
  entirely, forces `self._scale = 1.0`, and sets `self.width`/
  `self.height` directly to the natural, uncapped drawing size — a
  45U/3-bay rack renders at its own true size instead of being shrunk to
  fit an A4 page that, for a standalone PNG, doesn't exist.
- **New runtime dependency**: PyMuPDF (imported as `fitz`), pinned
  `PyMuPDF>=1.24.0` in `requirements.txt`. Already informally used in
  prior sessions' own scratchpad verification scripts (rendering PDF
  pages to PNG for visual inspection of earlier audit fixes) — this
  session promotes it to a real, declared runtime dependency.
  `rack_designer.spec` now calls `PyInstaller.utils.hooks.collect_all()`
  for both `pymupdf` and `fitz` and merges the results into `Analysis()`'s
  `datas`/`binaries`/`hiddenimports` — PyMuPDF's compiled extensions
  (`_mupdf.pyd`, `_extra.pyd`) and `mupdfcpp64.dll` are a known
  PyInstaller static-analysis gotcha (dynamically loaded, not reliably
  found via plain import-statement scanning) — equivalent to `pyinstaller
  --collect-all pymupdf --collect-all fitz`. Not exercised by an actual
  build this session, per the task's explicit scope — the spec is
  believed correct for whenever the next real build happens, but that
  belief is untested until then.
- `fitz`/PyMuPDF is imported lazily inside `export_rack_png()`, not at
  `pdf_export.py`'s module level — a broken/missing PyMuPDF install
  should only break this one optional feature when actually used, not
  prevent the whole app (including ordinary rack design and plain PDF
  export) from starting.

### Files modified
- `app/pdf_export.py`: `RackDrawing.__init__()` (`page_fit` parameter);
  new `export_rack_png()`; `import io` added.
- `app/main_window.py`: `ExportSection._build()` (new
  `export_png_btn`); new `ExportSection._sanitize_filename()`,
  `._do_export_png()`.
- `requirements.txt`: added `PyMuPDF>=1.24.0`.
- `rack_designer.spec`: `collect_all('pymupdf')`/`collect_all('fitz')`
  merged into `Analysis()`'s `binaries`/`datas`/`hiddenimports`.

### Verification
- **Task 2 (page_fit regression)**: for four test racks (1-bay, 2-bay,
  3-bay, and a 45U/3-bay stress case), confirmed `RackDrawing(rack,
  use_color=True)` (relying on the new `page_fit=True` default) produces
  `width`/`height`/`_scale` numerically identical to the pre-Session-18
  formula evaluated independently and directly — not just "looks the
  same," bit-for-bit matched via direct float comparison. Ran a full
  `export_pdf()` across all four racks together, color and grayscale, with
  no exception.
- **Task 3 (`export_rack_png()`)**: called directly on a large 3-bay
  (44U, 10 devices) and a small 1-bay (6U, 2 devices) rack at 300 DPI and
  150 DPI. Confirmed output PNG pixel dimensions match `dpi ×
  (drawing.width or height in points / 72)`, rounded, within 1px (the
  expected rounding tolerance between ReportLab's float point measurements
  and PyMuPDF's own pixmap rounding) — verified via a plain IHDR-chunk
  read, not a third imaging library. Confirmed `page_fit=False` truly
  ignores `MAX_RACK_H`/`MAX_RACK_W` even on a rack `page_fit=True` would
  visibly scale down (`_scale` exactly `1.0` vs. `<1.0` for the same
  rack). **Visual inspection** (the PNGs themselves, not a PDF→PNG
  conversion of them): a forced-oversized doubled device name correctly
  truncates with an ellipsis, fully inside its slot (confirming Session
  12's `_truncate_text()` fix carries over — note a single, non-doubled
  copy of the same long string used in the initial pass turned out to fit
  without truncation, consistent with a Session 12 finding about that
  exact string, so the check was redone with the doubled string that
  actually forces truncation); a rack shrunk below an occupied slot's
  position renders fully self-contained (9 numbered rows for a nominal 5U
  rack, matching `_draw_u_size`, no bleed); a numeric check confirmed
  `_slot_colors(..., grayscale=True)` still gives three sample category
  colors three distinct monochrome shades.
- **Task 4 (UI)**: offscreen-Qt script driving the real
  `ExportSection._do_export_png()` (`QFileDialog.getExistingDirectory`
  mocked, `MsgBox.*` mocked) — two racks both named "New Rack": confirmed
  exactly 2 non-empty PNG files, named `New_Rack.png` and `New_Rack
  (2).png` (neither overwriting the other), and a completion dialog
  reporting "2 of 2". Re-ran the same export into the *same* folder a
  second time: confirmed 4 files total afterward (`(3)`/`(4)` suffixes),
  never colliding with the first run's own output. 0-rack project:
  confirmed the folder dialog is never opened and a clear "No racks in
  project" message shows instead. Failure isolation: monkeypatched
  `export_rack_png()` to raise for one of two racks — confirmed the other
  still exports, the completion dialog names the failure and reason, and
  the process doesn't abort. Also drove the real button via
  `QTest.mouseClick` (not a direct method call) on a fully constructed,
  `.show()`n `MainWindow` with a real rack added through the actual
  `Project`/`Rack` objects — confirmed the same PNG output through the
  real UI signal chain, not just at the method level.
- Re-ran the existing full-app-launch smoke test (`main.py`'s real
  startup sequence through `window.show()`, offscreen) to confirm no
  regression from this session's changes.

## v0.1.20 — Session 19, 29 July 2026 (PNG export respects "RACKS TO INCLUDE")

Small, scoped fix session (`task.md` #65 addendum). No version-number
bump (still `0.1.20`).

### Fixed
- **PNG export ignored the Export tab's "RACKS TO INCLUDE" checkboxes**:
  Session 18's `ExportSection._do_export_png()` always exported every
  rack in the project, regardless of which were checked — inconsistent
  with the neighboring PDF export ("EXPORT PDF"), which already filtered
  to only the checked racks. `_do_export_png()` now uses the identical
  `[r for r, c in getattr(self, '_rack_checkboxes', []) if c.isChecked()]`
  expression `_do_export()` already used, so both export actions respect
  the same selection state consistently. The 0-selected-but-non-empty
  case now also shows `_do_export()`'s exact "Select at least one rack."
  message (checked first — confirmed `_do_export()` uses a message
  distinct from the genuinely-empty-project "No racks in project.", so
  `_do_export_png()` now mirrors both cases rather than only the latter).

### Files modified
- `app/main_window.py`: `ExportSection._do_export_png()`.

### Verification
- Standalone offscreen-Qt script (`QT_QPA_PLATFORM=offscreen`) — a
  project with two racks, only one checked: confirmed exactly 1 PNG is
  produced (not 2), named for the checked rack, and the completion
  summary reports "1 of 1" (not "1 of 2"). 0-checked (project non-empty):
  confirmed no folder dialog opens and the message is exactly "Select at
  least one rack.", matching `_do_export()`'s own wording. Regression:
  all racks checked still exports all of them (Session 18's original
  behavior preserved for that case). Confirmed PDF export
  (`_do_export()`) is completely unaffected — same checkbox-filtering
  behavior, same messages, before and after this change.
- **Process note**: an early version of the verification script hung
  under `QT_QPA_PLATFORM=offscreen` — root cause was the test script
  itself, not the fix: a second, later call to `_do_export()` in the same
  script forgot to re-mock `QFileDialog.getSaveFileName` after an earlier
  block had restored it, so that call reached a real modal file dialog,
  which blocks forever under an offscreen platform with no way to click
  a button (the same class of issue documented in Session 9's own
  process note). Diagnosed by adding progress-marker prints and
  bisecting the script rather than assumed, fixed by mocking the dialog
  for that call too, and the full suite then completed cleanly.

## v0.1.20 — Session 20, 30 July 2026 (release build: installer fix + first real v0.1.20 artifacts)

No app-source (`app/`) changes this session — build/release tooling only.
Closes out the installer-path work deferred since Session 5/6 (`task.md`
#4/#10) and produces the first real v0.1.20 release artifacts (previously
`v0.1.20` was only a declared version in code, never actually built).

### Fixed
- **`rack_designer_installer.iss` still pointed at `v0.1.19` in 6 places**:
  freshly grepped the whole file (not relying on which lines were fixed in
  earlier sessions) and corrected every stale reference —
  `SetupIconFile=` (was the `RarckDesigner History` archive copy's icon,
  now `RackDesigner_v0.1.20\icon.ico`), `UninstallDisplayIcon=`, the
  `[Files]` source, both `[Icons]` entries, and `[Run]`'s `Filename=` (all
  five hardcoded `RackDesigner_v0.1.19.exe`, now `RackDesigner_v0.1.20.exe`,
  and the `[Files]`/icon paths now point at the live `RackDesigner_v0.1.20/`
  tree instead of the frozen `v0.1.19/` or the archived `RarckDesigner
  History/` copy). `AppVersion=0.1.20` and
  `OutputBaseFilename=RackDesigner_v0.1.20_Setup` were verified already
  correct (Session 5), not reassumed.

### Added
- **First real PyInstaller build of v0.1.20**: `RackDesigner_v0.1.20/dist/RackDesigner_v0.1.20.exe`
  (onefile, ~76 MB), built from the corrected `rack_designer.spec`. This
  is also the first time Session 18's PyMuPDF `collect_all()` bundling
  (`task.md` #65) has been exercised by an actual build rather than left
  as "believed correct" — confirmed present inside the built exe:
  `pymupdf\_mupdf.pyd`, `pymupdf\_extra.pyd`, `pymupdf\mupdfcpp64.dll`.
- **Smoke test**: the built exe was launched directly
  (`QT_QPA_PLATFORM=offscreen`), ran without exiting or crashing for the
  test duration, and left no new `crash.log` entry. This confirms clean
  startup only — no interactive/functional UI pass was done on the built
  exe.
- **`installer_output\RackDesigner_v0.1.20_Portable.zip`**: the built exe
  zipped as a portable, no-install alternative. No prior portable-zip
  artifact existed anywhere in the project to match a pre-existing naming
  convention against; placed in `installer_output/` alongside the
  installer executables, the existing convention for release artifacts.
- **`installer_output\RackDesigner_v0.1.20_Setup.exe`**: compiled via Inno
  Setup's `ISCC.exe` (found at the standard install path,
  `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`, not on `PATH`), Inno
  Setup engine 6.7.2. Compiled clean against the corrected `.iss` above.

### Files modified
- `rack_designer_installer.iss` (6 stale `0.1.19` references corrected —
  see Fixed, above).

### Not done this session (explicit scope)
- No full interactive/functional QA pass on the built exe — the smoke
  test covered startup/crash-free running only, not actual rack-design
  workflows.
- The compiled installer was not run/installed end-to-end — confirmed to
  compile and produce an output file, not executed as an install.

### Verification
- `.iss`: re-read the file after editing, confirmed zero remaining
  `0.1.19` occurrences (grepped fresh) and that `AppVersion=`/
  `OutputBaseFilename=` were untouched (already correct).
- Build: `pyinstaller rack_designer.spec` completed with a normal exit and
  produced `dist/RackDesigner_v0.1.20.exe`; build warnings file reviewed —
  only the usual benign PyInstaller "missing module" false-positives
  (POSIX-only stdlib modules, optional/conditional third-party imports),
  nothing implicating the app's own code or its real runtime dependencies.
- PyMuPDF bundling: listed the built exe's embedded archive directly and
  confirmed `_mupdf.pyd`, `_extra.pyd`, and `mupdfcpp64.dll` are present
  under `pymupdf\`.
- Smoke test: `tasklist` showed the expected two processes (PyInstaller
  onefile bootloader + re-exec) running throughout the test window;
  `%APPDATA%\RackDesigner\crash.log` was absent both before and after,
  confirming no unhandled exception fired during startup; process
  terminated cleanly at the end of the test.
- Portable zip: confirmed via `Compress-Archive` output and a directory
  listing that the zip was created in `installer_output/`.
- Installer: `ISCC.exe`'s own compile log confirmed "Successful compile"
  and reported the exact output path,
  `installer_output\RackDesigner_v0.1.20_Setup.exe`; confirmed the file
  exists afterward via a directory listing.

## v0.1.20 — Session 21, 30 July 2026 (user manual updated: Word source + PDF)

User-facing documentation only — no app source (`app/`) changes. The
end-user manual had not been touched since v0.1.19 and was missing every
user-facing change from Sessions 18-20.

### Added
- `Manual/v0.1.20/RackDesigner_v0_1_20_UserManual.docx` and matching
  `.pdf`, copied forward from `Manual/v0.1.19/` (left untouched) per the
  project's existing frozen-snapshot convention.
- New "5.5 PNG Export" manual subsection describing the Export tab's
  "EXPORT RACKS AS PNG" feature (Session 18/19).
- New Version History (section 11) row for 0.1.20, summarizing PNG
  export, the device-image save/load fix, grayscale category shading,
  and the crash.log/error-dialog safety net.
- New "Images" row in the Device Fields table (4.1) and a matching CSV
  note in Exporting Devices (4.8), documenting that device photos are
  JSON-only.
- New "crash.log" row in the Data Storage table (section 8).

### Changed
- Section 5.2 "Use device colours" row description: replaced the old
  "neutral white/grey theme" wording with an accurate description of the
  grayscale category-shading behavior (Session 12).
- Section 3.4.4 context menu table, "Edit slot…" row description:
  extended to cover tray-slot behavior (no name field shown; each device
  keeps its own library name) (Session 17, #54).

### Files modified
- New files only (see Added) — no existing files changed.
  `Manual/v0.1.19/` was read from, never written to.

### Verification
- The rezipped `.docx` passed a zip-integrity check (`zipfile.testzip()`,
  no bad entries) and opened cleanly via `python-docx` (223 paragraphs,
  12 tables) before conversion; all 3 new table rows and the new heading
  were confirmed present by direct text lookup.
- Every one of the 8 edit anchors was confirmed to match exactly once in
  the document before being used as an edit target (several short
  strings, e.g. "Notes", repeat across different tables — the Device
  Fields row edit was anchored on its unique description text instead of
  the ambiguous header word).
- PDF regenerated via LibreOffice headless (`soffice --headless
  --convert-to pdf`) and every page touched by the edits was rendered to
  PNG (PyMuPDF) and visually inspected: cover page, context-menu table,
  Device Fields table, Exporting Devices section, the new 5.5 PNG Export
  section, Data Storage table, and Version History table. All render
  cleanly — correct alternating row shading, correct wrapping, no
  overflow, no broken rows. Final PDF: 16 pages (was 14 in v0.1.19).

**Note (corrected 2026-07-30, Session 22)**: the two new files above were
originally named with underscore-separated versions
(`RackDesigner_v0_1_20_UserManual.docx`/`.pdf`); renamed to the
dot-separated `RackDesigner_v0.1.20_UserManual.docx`/`.pdf` to match the
v0.1.17-19 convention. See Session 22's entry below.

## v0.1.20 — Session 22, 30 July 2026 (manual filenames corrected)

Rename only, no content change.

### Changed
- `Manual/v0.1.20/RackDesigner_v0_1_20_UserManual.docx` and `.pdf`
  (Session 21) renamed to `RackDesigner_v0.1.20_UserManual.docx`/`.pdf`,
  matching the dot-separated convention every prior version's manual
  used (`RackDesigner_v0.1.17-19_UserManual...`), instead of the
  underscore-separated version string flagged as an inconsistency when
  Session 21 shipped.

### Files modified
- `Manual/v0.1.20/RackDesigner_v0.1.20_UserManual.docx` (renamed)
- `Manual/v0.1.20/RackDesigner_v0.1.20_UserManual.pdf` (renamed)

### Verification
- `.docx`: zip-integrity check clean (`zipfile.testzip()`, no bad
  entries); reopened via `python-docx` — same 223 paragraphs, 12 tables
  as before the rename.
- `.pdf`: reopened via PyMuPDF — same 16 pages; cover page text confirmed
  intact ("RACK DESIGNER / User Manual / Version 0.1.20").

## [Template for future entries]

```
## vX.Y.Z — DD Month YYYY

### Added
-

### Changed
-

### Fixed
-

### Files modified
-
```
