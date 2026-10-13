# RackDesigner — Tasks

Status legend: `todo` · `in progress` · `blocked` · `done`

## Bug fixes (priority)

### 1. [done] PDF export: multi-bay racks overlap into one column
- **File**: `app/pdf_export.py`, class `RackDrawing`
- **Fixed**: 2026-07-22 (Session 2). `RackDrawing` now applies a per-bay
  horizontal offset (`bay_rx = rx + bay_idx * RACK_W`) and the
  slot-drawing loop filters/positions by `slot.bay`. No bay labels — bays
  drawn side by side, separated by a thin vertical line. Also extended
  the auto-scale factor (previously height-only) to account for page
  width too, since multi-bay diagrams can exceed it — needed to satisfy
  "at any page-fit scale."
- **Verification (done)**: built 2-bay, 3-bay, 1-bay-regression, and a
  45U/3-bay (forces combined height+width scaling) test racks via a
  standalone script calling `export_pdf()` directly, rendered every PDF
  page to PNG (PyMuPDF) and visually inspected — no overlap, correct
  per-bay device placement at identical U positions across bays, clean
  separators, correct proportional scaling. Grayscale (`use_color=False`)
  re-tested too, no exceptions. See `changelog.md` Unreleased — Session 2
  fixes.

### 2. [done] Crash moving devices between racks/bays
- **Investigated 2026-07-22 (Session 2)**, **both sub-parts fixed and
  verified 2026-07-24 (Session 3)**. Two distinct bugs were conflated
  under this one title; findings and fixes below. Full evidence trail in
  `design.md` § Known architectural gaps, item 2.

- **2a. Stale bay during same-canvas bay-crossing drag — fixed.**
  `RackCanvas.mouseMoveEvent()`'s internal-reorder branch (`bay >= 0`
  case) used the stale starting `self._drag_bay` for the collision check
  and never updated `RackSlot.bay` when the cursor crossed into a
  different bay column, so the dragged slot stayed visually stuck in its
  original bay's column (only moved vertically). **Fix**: the collision
  check now uses the current `bay` (from `_point_to_bay_u()`) instead of
  `self._drag_bay`, and `self._drag_slot.bay` is assigned to the current
  `bay` whenever the move isn't blocked by a collision; the undo-push
  trigger now also fires on a bay change, not just a `position_u` change.
  `app/rack_canvas.py`, `RackCanvas.mouseMoveEvent()`.
- **2b. `QPixmap` NameError crash — fixed.** `QPixmap` is used at
  `rack_canvas.py` (building the drag pixmap when a cross-rack `QDrag`
  starts) but was never imported. **Fix**: added `QPixmap` to the
  existing `from PyQt6.QtGui import (...)` line.
- **Verification (both, 2026-07-24)**: standalone offscreen-Qt script
  (`QT_QPA_PLATFORM=offscreen`), both direct handler calls and real
  `QTest`-driven event dispatch:
  - 2a: single-bay-cross, back-and-forth crossing, target-bay collision
    (move correctly blocked, bay unchanged), and a tray-device slot — all
    4 scenarios end with the correct `bay`/`position_u`.
  - 2b: cross-rack drag start (direct call and `QTest.mouseMove` with the
    cursor driven outside canvas bounds) — no exception, no process
    abort.
  - **Sanity check**: temporarily reverted the `QPixmap` import and
    re-ran the same script — the direct call reproduced the `NameError`
    and the `QTest`-driven path reproduced the exact silent process abort
    (exit code 127, no output) described in `design.md`, confirming the
    test actually exercises the bug before confirming the fix.
- **Files modified**: `app/rack_canvas.py` (import line +
  `mouseMoveEvent()`'s internal-reorder branch).

### 5. [done] Editing a device in the Library tab silently wipes its images
- **Files**: `app/library_dialog.py` (`DeviceForm`), `app/main_window.py`
  (`LibrarySection._save()`, unchanged)
- **Found during**: Session 1 documentation audit (2026-07-22), while
  cross-checking `library_dialog.py` against the documented image-support
  feature (v0.1.0 changelog entry, "Supporto immagini fronte e retro").
- **Fixed 2026-07-24 (Session 4)**. Root cause confirmed exactly as
  hypothesized: `ImagePickerWidget` was defined in `library_dialog.py` but
  never instantiated anywhere in `DeviceForm`; `DeviceForm.collect()`
  unconditionally returned `"image_front": ""` / `"image_rear": ""`;
  `LibrarySection._save()`'s blind `for k, v in data.items():
  setattr(dev, k, v)` then overwrote any existing image data on every
  save, for any device (including ones that arrived with images via JSON
  import).
- **Fix (both directions, per task scope)**:
  - **Loading**: `DeviceForm.__init__` now actually instantiates
    `self.img_front` / `self.img_rear` as real `ImagePickerWidget`
    instances (replacing the old `None` placeholders) and adds them to
    the form layout as a new "Images" row. `DeviceForm.load()` calls
    `img_front.set_b64(device.image_front)` /
    `img_rear.set_b64(device.image_rear)` so an existing device's images
    are pre-populated in the picker *before* any save can happen — this
    was the critical half of the fix; without it, fixing `collect()`
    alone would still wipe images on an untouched open-and-save.
  - **Saving**: `DeviceForm.collect()` now returns
    `self.img_front.get_b64()` / `self.img_rear.get_b64()` instead of the
    hardcoded empty strings.
  - **`LibrarySection._save()`**: confirmed no change needed — its blind
    `setattr` loop is correct now that `collect()`'s input is correct
    (verified explicitly, per task item 3).
  - **Bonus wiring**: `ImagePickerWidget.update_u_height()` (existed but
    was never called anywhere) is now called from the U-height spinner's
    commit/up/down handlers and from `load()`, so the picker's
    "recommended image size" hint stays in sync with the device's actual
    U height instead of always showing the 1U default.
- **Incidental bug found and fixed as a required part of this fix (not
  separately scoped, but couldn't wire `ImagePickerWidget` without it)**:
  `library_dialog.py` used `IMAGE_WIDTH_PX` / `IMAGE_U_HEIGHT_PX` (in
  `ImagePickerWidget._update_hint()`) without ever importing them from
  `app.models` — instantiating the widget for the first time would have
  raised `NameError` immediately. Added both to the existing
  `from app.models import (...)` line.
- **Verification (2026-07-24, actually run — offscreen Qt)**: two
  scripts. (1) Direct `DeviceForm`/`storage` round-trip covering all 4
  scenarios from the task: new device add-images-save-reopen; existing
  device WITH images edited on an unrelated field only (**the exact bug
  scenario**) — images survive; existing device WITH images,
  replace-one/clear-the-other via the picker — change persists correctly;
  existing device WITHOUT images, no-op save — stays empty, no crash. (2)
  A second, fully end-to-end script drives the *real*
  `LibrarySection` widget — real `QListWidget` row selection (not a
  direct `load()` call) and a real `QTest.mouseClick` on the actual Save
  button (not a direct `_save()` call) — confirming the fix holds through
  the real signal chain, not just at the method level. Sanity-checked
  the harness itself by temporarily reverting the `collect()` fix and
  re-running: 3 of the 6 checks correctly failed (the bug-scenario one
  among them), confirming the tests actually exercise the bug.
- **Evidence of prior data loss (checked, cheap)**: the live
  `%APPDATA%\RackDesigner\library.json` on this machine has 119 devices,
  **zero** with any image data currently set; `preloaded_library.py`'s
  seed data never included image bytes for any of its devices either. This
  is consistent with the bug (any image, however it arrived, would be
  wiped the next time that device was opened and saved in the Library
  tab) but isn't conclusive proof anything was actually lost — there's no
  history/log to distinguish "never had images" from "had images, later
  silently wiped." Not investigated further (would require checking
  backup/export files outside this repo, out of scope).
- **Files modified**: `app/library_dialog.py` (`DeviceForm.__init__`,
  `.load()`, `.collect()`, plus the `IMAGE_WIDTH_PX`/`IMAGE_U_HEIGHT_PX`
  import). `app/main_window.py` unchanged (no fix needed there).

## Robustness

### 8. [done] Global exception handler (sys.excepthook)
- **Added 2026-07-24 (Session 3)**, as an explicit follow-up decision from
  bug #2b (the app had no safety net for unhandled exceptions in Qt event
  handlers — PyQt6's default behavior is a silent, traceback-less process
  abort). Not itself a bug fix — new architecture. See `design.md` for the
  mechanism description.
- **What it does**: `main.py` installs `sys.excepthook` right after
  `QApplication` is constructed.
  - `KeyboardInterrupt` / `SystemExit` are **not** intercepted — delegated
    straight to `sys.__excepthook__` so Ctrl+C / normal exit behave as
    before.
  - Any other uncaught exception: full traceback appended to
    `%APPDATA%\RackDesigner\crash.log` (timestamped, append mode — reuses
    `storage.get_app_data_dir()`, same convention as library/project
    storage), then a themed `MsgBox.error(...)` dialog tells the user
    something went wrong and details were logged. The app does **not**
    force-quit — execution continues (confirmed possible in Session 2's
    investigation of bug #2b).
  - Both the log write and the dialog call are wrapped in their own
    `try/except` so a failure in the handler itself (e.g. disk full) can't
    take the app down.
- **Design deviation flagged**: the task asked for "a short, non-technical
  `QMessageBox`"; used the app's existing themed `MsgBox.error` (from
  `app/dialogs.py`) instead of a raw `QMessageBox`, since the app already
  replaces default Qt dialogs everywhere (per `design.md`'s module map) —
  a bare `QMessageBox` would look inconsistent. Flagging in case a plain
  native dialog was actually wanted (e.g. to avoid depending on app
  styling/QSS if the crash is style-related) — easy to swap back.
- **Verification**: standalone offscreen-Qt script — a widget's
  `mousePressEvent` deliberately raises `ValueError`, triggered via real
  `QTest.mouseMove`/`mousePress` dispatch (not just a direct call).
  Confirmed: app survives, `MsgBox.error` is invoked with the expected
  non-technical title/message, `crash.log` (redirected to a throwaway temp
  `%APPDATA%` for the test) contains the traceback, the app keeps
  processing further events afterward, and a synthetic `SystemExit` passed
  through the hook is delegated to the original `sys.excepthook` rather
  than logged/dialoged.
- **Files modified**: `main.py`.

## Documentation

### 3. [done] Fix up changelog.md following Session 1 findings
- **Correction**: the original premise of this task was wrong. Tray
  system, `rack_native`/`width_mm`/`height_mm`, and CSV import ARE
  documented (`Changelog.txt` v0.1.6, v0.1.12/v0.1.13) — no backfill
  needed for those three. `changelog.md`'s current "Unreleased —
  documentation catch-up" section should be replaced, not filled in.
- **What actually needs logging** (found in Session 1) — **decision
  (project owner, 2026-07-22): log retroactively under the existing
  v0.1.19 entry in `changelog.md`**, not as a new version/Unreleased
  entry:
  - Library "DUPLICATE" button
  - "Preset" combobox in Add Rack dialog
  - "Client" field UI-relabeled to "Project number" (data model still
    `Project.client`)
  - Ctrl+O / Ctrl+N global shortcuts
  - `app/faceplates.py` removal (once Backlog #6 is executed)
- **Historical-log corrections to note** (not code changes):
  - v0.1.12's "library versioning system" (`library_version.txt` reseed
    stamp) doesn't exist anywhere in current code — either removed later
    without a log entry, or never actually built. Not investigated
    further this session.
  - v0.1.12 says "112 devices," current `preloaded_library.py` has 119 —
    minor, likely later additions.
  - v0.1.10 entry dated 2026-05-08 is almost certainly a typo for
    2025-05-08 — `Changelog.txt` is a frozen archive, not corrected.
- **Version number**: confirmed consistent at `v0.1.19` across all 4
  hardcoded locations (see #7) — no reconciliation needed there.
- **Done 2026-07-24 (Session 5)**: replaced the old "Unreleased —
  documentation catch-up" section (based on the corrected premise above)
  with a "## v0.1.19 (addendum — retroactively logged 2026-07-24)"
  section containing exactly the Added/Changed/historical-log-correction
  items listed above. The three former "Unreleased — Session 2/3/4
  fixes" sections were also merged into one "## v0.1.20 — 24 July 2026"
  entry (per the version bump in Task 1 of this session), each session's
  original Fixed/Added/Changed/Files-modified/Verification content kept
  intact under its own subheading, plus a new Session 5 subsection for
  this session's own changes. See `changelog.md`.

### 67. [done] Update user manual for v0.1.20 (Word source + PDF)
- **Done 2026-07-30 (Session 21)**. The end-user manual
  (`Manual/v0.1.X/RackDesigner_v0.1.X_UserManual.docx` + `.pdf`) had not
  been updated since v0.1.19 — none of Session 18-20's user-facing
  changes (PNG export, the image-save fix, grayscale category shading,
  the crash.log/error-dialog safety net) were reflected in it.
- **Task 0 — located the real source**: `Manual/v0.1.19/` (project root),
  containing `RackDesigner_v0.1.19_UserManual.docx` and a matching
  `.pdf`. Confirmed this is a real binary Word document (`file` reports
  "Microsoft Word 2007+"), not the text-extracted copy that exists
  separately in chat knowledge.
- **Task 1 — new v0.1.20 copy, per the project's existing frozen-snapshot
  convention** (same pattern as `RackDesigner_v0.1.19/` →
  `RackDesigner_v0.1.20/` in `task.md` #11): copied
  `Manual/v0.1.19/RackDesigner_v0.1.19_UserManual.docx` to a new
  `Manual/v0.1.20/RackDesigner_v0_1_20_UserManual.docx` (filename with
  underscores in the version, exactly as specified in this session's
  brief — note this departs from the dot-separated
  `RackDesigner_v0.1.19_UserManual.docx` pattern every prior version
  used; flagging the inconsistency here rather than silently
  "correcting" it, since the brief was explicit about the exact
  filename). `Manual/v0.1.19/` was left untouched.
  **Corrected 2026-07-30 (Session 22)**: both files renamed to the
  dot-separated `RackDesigner_v0.1.20_UserManual.docx`/`.pdf`, matching
  the v0.1.17-19 convention — see the Session 22 entry below.
- **Task 2 — 8 content edits**, made directly against `word/document.xml`
  (unzip → edit → rezip; no `docx`-specific skill was available in this
  environment, so the equivalent workflow was done by hand: a
  `merge_runs.py`-equivalent script first consolidated Word's
  spell-check-split runs within each paragraph so text could be matched
  reliably, then a second script applied all 8 edits via exact-text
  anchors verified unique beforehand, i.e. `grep`-equivalent match-count
  checks before touching anything):
  1. Cover page: "Version 0.1.19" → "Version 0.1.20".
  2. Section 11 (Version History table): new `0.1.20` row appended,
     continuing the table's existing alternating row-shading pattern.
  3. New "5.5 PNG Export" subsection added after 5.4 "PDF Structure"
     (heading + body paragraph + a "Note:" callout, all built from the
     exact paragraph-style/run-property templates already used
     elsewhere in the same document, not approximated).
  4. Section 5.2 (Content Options table), "Use device colours" row
     description updated to describe the grayscale/shade-distinguishing
     behavior instead of the old "neutral white/grey theme" wording.
  5. Section 4.1 (Device Fields table): new "Images" row appended after
     "Notes" (last row), continuing the alternating shading.
  6. Section 4.8 (Exporting Devices): new "Note: CSV export does not
     include device images…" paragraph added after the existing JSON
     note, matching its exact bold-amber-"Note:"-plus-italic-gray-body
     style.
  7. Section 8 (Data Storage table): new "crash.log" row appended after
     "projects\" (last row), continuing the alternating shading.
  8. Section 3.4.4 (context menu table), "Edit slot…" row description
     extended to cover tray-slot behavior (no name field, per-device
     names preserved).
- **Task 3 — PDF regenerated and visually verified**: converted via
  `soffice --headless --convert-to pdf` (LibreOffice, found at
  `C:\Program Files\LibreOffice\program\soffice.exe`), then every page
  touched by the 8 edits above was rendered to PNG (PyMuPDF, since
  `pdftoppm` wasn't available in this environment) and actually looked
  at: cover page, the context-menu table, the Device Fields table, the
  Exporting Devices section, the new PDF/PNG-export pages, the Data
  Storage table, and the Version History table. All render cleanly —
  correct alternating row shading, correct text wrapping, no overflow,
  no broken table rows. Output PDF is 16 pages (up from 14 in v0.1.19 —
  expected, given the added subsection/rows/notes).
- **Files added** (new, `Manual/v0.1.20/`, `Manual/v0.1.19/` untouched):
  `RackDesigner_v0_1_20_UserManual.docx`,
  `RackDesigner_v0_1_20_UserManual.pdf`. **Renamed 2026-07-30 (Session
  22)** to `RackDesigner_v0.1.20_UserManual.docx`/`.pdf` — see below.
- **Verification**: the rezipped `.docx` was checked for zip-archive
  integrity (`zipfile.testzip()`, no bad entries) and opened cleanly via
  `python-docx` (223 paragraphs, 12 tables, all 3 new table rows and the
  new heading confirmed present by direct text lookup) before ever
  converting to PDF. The 8 edits' anchor texts were each confirmed
  unique in the document (exact match-count check) before being used as
  edit targets, avoiding a wrong-instance edit in a manual with several
  repeated short strings (e.g. "Notes" appears 4 times as a bold table
  header/field name across different tables — the Device Fields row was
  targeted via its unique description text instead).
- **Not done this session (not requested)**: no changes to
  `Manual/v0.1.17/`, `Manual/v0.1.18/`, or `Manual/v0.1.19/`; the
  chat-knowledge text-extracted copy of the manual (a separate artifact
  outside this project's `Manual/` folder) was not touched.
- **Filename corrected 2026-07-30 (Session 22)**: renamed both files in
  `Manual/v0.1.20/` from the underscore-separated
  `RackDesigner_v0_1_20_UserManual.docx`/`.pdf` (flagged as an
  inconsistency in Session 21, above) to the dot-separated
  `RackDesigner_v0.1.20_UserManual.docx`/`.pdf`, matching the
  `RackDesigner_v0.1.17-19_UserManual` convention every prior version
  used. Rename only, no content change — confirmed both files still open
  cleanly afterward (`.docx`: zip-integrity check clean, `python-docx`
  reads 223 paragraphs/12 tables; `.pdf`: 16 pages, cover page text
  intact).

## Build / release process

### 4. [done] Installer builds from the wrong (archived) source tree
- **Confirmed**: `RackDesigner_v0.1.19/` (top level) is the real working
  copy; `RarckDesigner History/` is a pure archive, not meant to be
  edited or built from.
- **Fixed 2026-07-24 (Session 5)**: `rack_designer_installer.iss`'s
  `[Files]` source now reads
  `...\Rack Designer\RackDesigner_v0.1.19\dist\RackDesigner_v0.1.19.exe`
  (the live tree) instead of
  `...\Rack Designer\RarckDesigner History\RackDesigner_v0.1.19\dist\...`
  (the archive). Only the `[Files]` source line was changed, per session
  scope — confirmed by reading the file back after the edit. The
  installer was **not** compiled/tested end-to-end this session (not
  requested).
- **Flagged, not fixed (out of this session's explicit scope)**:
  - `SetupIconFile=` (near the top of `[Setup]`) still points at
    `RarckDesigner History\RackDesigner_v0.1.19\icon.ico` — same
    live-vs-archive mismatch as the `[Files]` source had, just for the
    icon instead of the exe. Low risk today since the two trees are
    still byte-identical, but same latent staleness risk.
  - After Task 1 (this session) bumped `rack_designer.spec`'s `name=` to
    `RackDesigner_v0.1.20`, a future PyInstaller build will produce
    `dist/RackDesigner_v0.1.20.exe`, not `...0.1.19.exe`. The `.iss`
    file's `[Files]` source, both `[Icons]` entries, `UninstallDisplayIcon=`,
    and `[Run]` all still hardcode the literal filename
    `RackDesigner_v0.1.19.exe`. These were intentionally left as-is this
    session (Task 2's scope was explicitly the directory prefix, not the
    exe filename) but will need updating before the next real installer
    build, or the installer will look for a file that no longer exists.
    Worth deciding whether to fix this now as a follow-up, or fold it
    into whatever process handles future version bumps.
- **Note added 2026-07-24 (Session 6)**: the live tree was duplicated to
  `RackDesigner_v0.1.20/` this session (see the new log entry below);
  `RackDesigner_v0.1.19/` is now frozen. Whenever the installer is next
  actually compiled, the `.iss` also needs to be repointed at
  `RackDesigner_v0.1.20\dist\...` (not `_v0.1.19\`), since that's now the
  live tree — on top of, not instead of, the exe-filename fix already
  noted above. Not done this session — deliberately deferred.
- **Fully resolved 2026-07-30 (Session 20)**: see #66 below. Every
  remaining `0.1.19` reference in the `.iss` (icon, exe filename in
  `[Files]`/`[Icons]`/`[Run]`/`UninstallDisplayIcon=`) is fixed, and the
  installer has now actually been compiled end-to-end against the real
  `RackDesigner_v0.1.20/dist/` build for the first time.

### 11. [done] Duplicated the working tree to `RackDesigner_v0.1.20/`
- **Done 2026-07-24 (Session 6)**. Copied `RackDesigner_v0.1.19/` to a new
  sibling folder `RackDesigner_v0.1.20/` (same level, project root),
  excluding `build/`, `dist/`, and `__pycache__` (regenerable
  PyInstaller/bytecode output — copying them would just be stale
  clutter). Verified via `diff -rq` that the copy is otherwise identical
  to the source.
- **Why**: Session 5 bumped the app to v0.1.20 but left the working
  folder named `RackDesigner_v0.1.19/` (flagged as `task.md` #10 at the
  time, deliberately not acted on then). This session resolves that by
  giving v0.1.20 its own correctly-named folder instead of renaming the
  old one in place — `RackDesigner_v0.1.19/` is left as a **frozen
  snapshot as of 2026-07-24** (not moved into `RarckDesigner History/`,
  just stopped-editing at the project root) rather than deleted, in case
  anything still references it.
- **`RackDesigner_v0.1.20/` is the live/edited tree from this session
  onward.** `rack_designer_installer.iss` was deliberately **not**
  updated this session (see the note under #4 above) — it still builds
  from the now-frozen `RackDesigner_v0.1.19/`.
- **Verification**: ran the app directly from `RackDesigner_v0.1.20/`
  (offscreen Qt) — constructs and starts correctly, About tab and status
  bar both still show `v0.1.20` from the same `app.APP_VERSION` constant
  (unchanged behavior, just confirming the copy didn't break anything).
- **Docs repointed**: `folder_structure.md`, `design.md` (path note),
  `status.md` (live/edited tree confirmation) all updated to reference
  `RackDesigner_v0.1.20/` as the live tree and `RackDesigner_v0.1.19/` as
  a frozen snapshot. No `changelog.md` entry — repo/workflow
  reorganization, not an app behavior change.

### 66. [done] Installer repointed at v0.1.20 + first real v0.1.20 release build produced
- **Closes out the long-deferred installer-path work flagged under #4 and
  #10** (both the directory-prefix and exe-filename staleness noted
  there).
- **Task 1 — `rack_designer_installer.iss` fixed, 2026-07-30 (Session
  20)**: grepped the whole file fresh for `0.1.19` (6 hits, not assumed
  from memory) and fixed every one:
  - `SetupIconFile=` — was `RarckDesigner History\RackDesigner_v0.1.19\icon.ico`,
    now `RackDesigner_v0.1.20\icon.ico`.
  - `UninstallDisplayIcon=` — was `{app}\RackDesigner_v0.1.19.exe`, now
    `{app}\RackDesigner_v0.1.20.exe`.
  - `[Files]` source — was
    `...\RackDesigner_v0.1.19\dist\RackDesigner_v0.1.19.exe`, now
    `...\RackDesigner_v0.1.20\dist\RackDesigner_v0.1.20.exe`.
  - `[Icons]` (both entries) and `[Run]` — all three referenced
    `{app}\RackDesigner_v0.1.19.exe`, now `{app}\RackDesigner_v0.1.20.exe`.
  - `AppVersion=0.1.20` and `OutputBaseFilename=RackDesigner_v0.1.20_Setup`
    were checked, not assumed — already correct since Session 5.
- **Task 2 — real PyInstaller build, 2026-07-30 (Session 20)**: ran
  `pyinstaller rack_designer.spec` from `RackDesigner_v0.1.20/` (Python
  3.12.2; PyQt6 6.11.0, ReportLab 4.4.10, PyMuPDF 1.28.0, PyInstaller
  6.11.1 all already installed). Build completed clean, producing
  `RackDesigner_v0.1.20/dist/RackDesigner_v0.1.20.exe` (~76 MB, onefile).
  **This is the first time Session 18's PyMuPDF `collect_all()` bundling
  (task #65) has actually been exercised by a real build** — confirmed via
  the built exe's own archive listing that `pymupdf\_mupdf.pyd`,
  `pymupdf\_extra.pyd`, and `pymupdf\mupdfcpp64.dll` are all present
  inside it, so the bundling is not just "believed correct" anymore.
  **Smoke test**: launched the built exe directly (`QT_QPA_PLATFORM=offscreen`)
  — process came up as two entries in `tasklist` (bootloader + re-exec,
  expected for PyInstaller onefile), ran for the full duration without
  exiting, and `%APPDATA%\RackDesigner\crash.log` did not exist/grow
  afterward (no exception logged). Killed cleanly at the end of the test.
  Full interactive UI exercise (opening the Designer tab, adding a device,
  etc.) was **not** done — this was a startup/crash smoke test only, not a
  functional QA pass.
- **Task 3 — portable zip, 2026-07-30 (Session 20)**: zipped the built exe
  as `installer_output\RackDesigner_v0.1.20_Portable.zip` (no prior
  portable-zip artifact existed anywhere in the project to match a
  pre-existing naming/location convention against — placed alongside the
  other release artifacts in `installer_output/`, the existing convention
  for installer `.exe`s).
- **Task 4 — installer compiled, 2026-07-30 (Session 20)**: found
  `ISCC.exe` at the standard location,
  `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` (not on `PATH`). Compiled
  the corrected `.iss` — succeeded (Inno Setup 6.7.2), producing
  `installer_output\RackDesigner_v0.1.20_Setup.exe` (~77 MB).
- **Files modified**: `rack_designer_installer.iss` (6 stale-path fixes,
  see above). No app source (`app/`) changes this session — build/release
  tooling only.
- **New artifacts produced this session** (all in
  `installer_output/`, gitignore/tracking not applicable — no git repo):
  `RackDesigner_v0.1.20_Portable.zip`, `RackDesigner_v0.1.20_Setup.exe`.
  The raw built exe itself lives at
  `RackDesigner_v0.1.20/dist/RackDesigner_v0.1.20.exe` (regenerable
  PyInstaller output, per `folder_structure.md`'s existing convention of
  not treating `dist/`/`build/` as tracked source).
- **Not done this session (out of explicit scope)**: no full interactive
  UI/functional QA pass on the built exe (startup smoke test only, per the
  brief); the installer itself was not run/installed end-to-end (compiled
  and confirmed to produce an output file, not executed).

## Backlog (open, not yet scoped)

### 6. [done] `app/faceplates.py` is dead code — **decision: delete it**
- **File**: `app/faceplates.py` (823 lines, 15 templates +
  `draw_faceplate()` dispatcher)
- **Found during**: Session 1 documentation audit (2026-07-22)
- **Detail**: `Changelog.txt` v0.1.10 states the file was deleted ("il
  renderer era già inutilizzato dal canvas"). Was still present on disk,
  unchanged, still referencing `patch_connector`/`patch_count` — fields
  removed from the data model in that same v0.1.10 pass.
- **Decided (project owner, 2026-07-22)**: delete the file completely —
  abandoned direction, not something to pick back up.
- **Done 2026-07-24 (Session 5)**: re-grepped the live tree for
  `faceplates`/`draw_faceplate` before deleting (Session 1's "zero
  references" finding was from before Sessions 2–4's changes) — still
  zero references outside the file itself. Deleted `app/faceplates.py`.
  Confirmed the app still constructs and runs after the deletion.
  `design.md`'s module table updated (row removed).

### 9. [done] `DeviceForm.__init__` builds a dead duplicate color-picker block
- **Found during**: Session 4 (2026-07-24), while fixing bug #5 in the
  same class.
- **File**: `app/library_dialog.py`, `DeviceForm.__init__`
- **Detail**: a `color_row = QHBoxLayout()` / `self.color_btn =
  ColorButton()` block was built once (right after the `rack_native_chk`
  setup), fully wired (button, "Use category color" clear button,
  signal connection) — and then **entirely rebuilt and reassigned** a
  bit further down (right after the W×H×D dimensions block), overwriting
  `self.color_btn` and `color_row` before either was ever added to the
  form's layout. The first block was pure dead code: constructed, wired,
  then discarded with no observable effect.
- **Done 2026-07-24 (Session 5)**: deleted the first (dead) block —
  the `color_row`/`self.color_btn`/`clear_col` setup right after
  `rack_native_chk`, before the "Spinner helper" comment. The second
  block (the one actually wired into the form layout) is untouched.
  Verified: loading a device's color into the form, changing it via
  `color_btn`, and collecting it back via `DeviceForm.collect()` all
  still work correctly — no behavior change, as expected for pure
  dead-code removal.

### 7. [done] Version string duplicated across 4 hardcoded locations
- **Found during**: Session 1 documentation audit (2026-07-22)
- **Locations**: `rack_designer.spec` (`name=`), `app/main_window.py`
  (About tab label, status bar default), `rack_designer_installer.iss`
  (`AppVersion=`, `OutputBaseFilename=`).
- **Done 2026-07-24 (Session 5), as part of the v0.1.19 → v0.1.20 version
  bump**: added `APP_VERSION = "0.1.20"` to `app/__init__.py` as a single
  shared constant. `app/main_window.py`'s About-tab label and status-bar
  default text both now read `app.APP_VERSION` instead of two separate
  hardcoded literals — verified by running the app (both show `v0.1.20`,
  from the same import).
  - `rack_designer.spec` and `rack_designer_installer.iss` are external
    build tooling and can't import a Python constant, so they remain
    separate hardcoded literals **by necessity**, not oversight — bumped
    to `0.1.20` by hand this session, with a comment added next to each
    version line in both files explicitly noting they must be
    hand-updated on every future bump and won't follow `APP_VERSION`
    automatically. This reduces the "4 hardcoded locations" problem to 2
    (down from 4), which is the practical floor given the tooling
    constraint.

### 10. [done] `RackDesigner_v0.1.19/` working-folder name now lags the real version
- **Raised**: Session 5 (2026-07-24), flagged rather than acted on per
  explicit instruction not to rename the folder this session.
- **Detail**: as of this session the app reports itself as `v0.1.20`
  (`app.APP_VERSION`), but the live working-tree folder is still named
  `RackDesigner_v0.1.19/` (project root) — it was never renamed when the
  version bumped. `rack_designer.spec`'s `name=` field now also says
  `RackDesigner_v0.1.20`, meaning a fresh build will produce
  `RackDesigner_v0.1.19/dist/RackDesigner_v0.1.20.exe` — the exe's own
  filename no longer matches the folder it lives in either.
- **Claude Code's opinion (asked for, since flagged as "if you think it
  matters")**: this is a real, growing inconsistency, but low urgency —
  purely cosmetic/organizational, not a functional bug, and every doc in
  `docs/` already treats `RackDesigner_v0.1.19/` as a fixed path name
  rather than something re-derived from the version. Renaming has a
  blast radius (this doc set's hardcoded paths, the `.iss` installer
  paths, the `RarckDesigner History/` mirroring convention) disproportionate
  to the problem it solves. Recommend either (a) renaming the folder to
  `RackDesigner_v0.1.20/` next time a version bump session also touches
  the installer/build path, doing both in one pass, or (b) deciding the
  working-folder name is intentionally decoupled from the app version
  going forward and closing this without action. Needs a project-owner
  decision either way — not resolving it here.
- **Resolved 2026-07-24 (Session 6)**: project owner chose a third option
  — not a rename, a duplication. `RackDesigner_v0.1.19/` was copied to a
  new `RackDesigner_v0.1.20/` sibling folder (build/dist/`__pycache__`
  excluded) and frozen in place rather than renamed or deleted. See #11
  below for the full log entry. `rack_designer_installer.iss` still
  isn't repointed (deliberately deferred, see the note under #4).
- **Related, surfaced under task #4**: the `.iss` file's `[Files]`
  source, `[Icons]`, `UninstallDisplayIcon=`, and `[Run]` sections all
  still hardcode the exe filename `RackDesigner_v0.1.19.exe`, which will
  be stale the moment a build actually picks up the `.spec`'s new
  `name=`. Same underlying "version bump touches more places than
  expected" issue as this item.

## Session 7 (2026-07-24) — Full code audit findings

**Audit-only session, no fixes applied.** Every real module was read in
full by 10 parallel review passes (main_window.py split into its 4 major
sections/dialogs; storage.py+models.py; preloaded_library.py;
rack_canvas.py; pdf_export.py; library_dialog.py; style.py+dialogs.py+
main.py+`__init__.py`), each looking specifically for unhandled
exceptions, None/empty-state crashes, data corruption, silent
overwrite-style bugs (the proven shape of bug #5), off-by-one/boundary
errors, missing imports, reentrancy issues, unvalidated input, and
contradictions with `design.md`/`task.md`'s documented behavior. Where
practical, findings were live-reproduced with standalone offscreen-Qt
scripts (`QT_QPA_PLATFORM=offscreen`, direct calls and/or `QTest`) rather
than left as static reasoning alone — noted per item below. All repro
scripts lived only in the session's scratch directory, never in the
project. Every item below is **not fixed** — cataloged for a future
session to triage and pick from.

### Triage summary (53 findings, sorted by severity)

**likely-real-and-impactful (27)** — candidates for "fix the top N":
#12, #14, #15, #16, #17, #20, #21, #25, #26, #27, #29, #30, #32, #33,
#34, #35, #47, #48, #49, #51, #55, #57, #58, #59, #62, and (cross-file,
same root cause) #39/#45 are related — see their notes.

**real-but-minor (24)**: #13, #18, #19, #22, #23, #24, #28, #31, #36,
#37, #38, #40, #41, #42, #43, #44, #46, #50, #52, #53, #54, #56, #60,
#61, #63, #64.

**needs-live-reproduction-to-confirm (2)**: #39, #45.

A handful of findings share one root cause across two files/sessions —
cross-referenced inline (#20↔#30, #34↔#45).

**Session 8 update (2026-07-25)**: #33, #34, #35, #38, #39, #45 — the
full "storage durability" cluster — are now `[done]`, see their entries
above and `changelog.md` Session 8. The remaining items in both lists
above are unchanged, still `[todo]`.

**Session 9 update (2026-07-25)**: #12, #25, #26 — the "dirty-flag /
data-loss" cluster — are now `[done]`, see their entries above and
`changelog.md` Session 9. 44 items remain `[todo]`.

**Session 10 update (2026-07-28)**: #14, #15, #17, #47, #48, #49 — the
"rack canvas interaction" cluster — are now `[done]`, see their entries
above and `changelog.md` Session 10. 38 items remain `[todo]`.

**Session 11 update (2026-07-28)**: #20, #21, #27, #29, #30 — the
"form/dialog + import/categorie" cluster — are now `[done]`, see their
entries above and `changelog.md` Session 11. 33 items remain `[todo]`.

**Session 12 update (2026-07-28)**: #55, #56, #57, #58, #59, #61 — the
PDF export cluster — are now `[done]`, see their entries above and
`changelog.md` Session 12. #60 was investigated but not fixed — see its
entry above for the full trade-off analysis and stop-condition reasoning.
27 items remain `[todo]` (including #60).

**Session 13 update (2026-07-28)**: #60 closed as decided-not-to-fix (no
code change — project owner accepted the trade-off analysis, see #60's
entry above). #31, #32, #36, #37, #40 — the math/validation cluster — are
now `[done]`, see their entries above and `changelog.md` Session 13. 21
items remain `[todo]`.

**Session 14 update (2026-07-29)**: #16 (rack-shrink off-by-one) and #51
(cross-rack drop onto a tray never merges) — two previously-missed
likely-real-and-impactful items — are now `[done]`, see their entries
above and `changelog.md` Session 14. 19 items remain `[todo]`.

**Session 15 update (2026-07-29)**: #41, #42, #43, #44, #46 — the
preloaded-library data cluster (redundant custom category, two
copy-pasted model strings, two implausible `depth_mm` values, and a
docs-only device-count correction) — are now `[done]`, see their entries
above and `changelog.md` Session 15. 15 items remain `[todo]`.

**Session 16 update (2026-07-29)**: #62, #63, #64 — the startup
robustness cluster (seeding-exception guard, pre-`QApplication` crash
logging, `MsgBox` non-string-argument defense) — are now `[done]`, see
their entries above and `changelog.md` Session 16. 12 items remain
`[todo]`.

**Session 17 update (2026-07-29)**: #13, #18, #19, #22, #23, #24, #28,
#50, #52, #53, #54 — the final 11 real-but-minor/informational backlog
items — are now `[done]`, see their entries above and `changelog.md`
Session 17. **0 items remain `[todo]`** — all 53 Session 7 audit
findings are now resolved (fixed, or explicitly decided-not-to-fix in
#60's case).

---

### 12. [done] Project Info form fields never mark the project dirty
- **File**: `app/main_window.py`, `ProjectSection` — form fields built in
  `_build()` (~lines 318–337: `name_edit`, `commessa_edit`, `venue_edit`,
  `date_edit`, `notes_edit`), consumed by `_apply()` (~457–466), `_new()`
  (~474–481), `_open()` (~483–496), `_open_recent()` (~401–415)
- **Detail**: none of the Project Info form fields are wired to any
  signal that marks `MainWindow._dirty = True` — only `designer.project_changed`
  (rack-canvas edits) does that. `_can_proceed()`/`_dirty_check()` see
  `_dirty == False` and let New/Open/Open-Recent proceed with zero
  "unsaved changes" prompt, even though the visible form has unsaved
  typed text.
- **Trigger**: type a new project name or notes, don't click Save, then
  click New Project / Open File / a recent-project row / Ctrl+N / Ctrl+O.
  Typed text is silently discarded.
- **Live-reproduced**: yes (offscreen Qt, direct calls) — typed text
  confirmed lost with `mw._dirty` staying `False` throughout.
- **Severity**: likely-real-and-impactful — silent loss of user-entered
  project metadata; exactly the "dirty-guard that doesn't guard what it
  claims to" class flagged as high-priority for this audit.
- **Fixed 2026-07-25 (Session 9)**. `ProjectSection` gained a new
  `project_changed` signal (parallel to `DesignerSection`'s), wired to
  `MainWindow._on_changed` (the same slot that already marks `_dirty =
  True` for rack-canvas edits) in `MainWindow._build()`. All five form
  fields (`name_edit`, `commessa_edit`, `venue_edit`, `date_edit`,
  `notes_edit`) connect their `textChanged` signal to a new
  `_on_field_changed()` handler that emits `project_changed` — guarded by
  a new `self._loading` flag so it does **not** fire when fields are set
  programmatically: `load_project()` (New/Open/Open-Recent) and `_apply()`
  (the `name_edit.setText()` re-sync after trimming) both wrap their
  `setText`/`setPlainText` calls in `self._loading = True` / `False`.
- **Verification (2026-07-25)**: offscreen-Qt script, real `QTest.keyClicks`
  (not direct signal calls) into each of the 5 fields on a real
  `MainWindow` — each confirmed to set `_dirty = True`; confirmed
  `load_project()` does not mark dirty (guard holds); full end-to-end
  flow — type into `name_edit`, invoke `ProjectSection._new()` (the same
  path Ctrl+N triggers) with `MsgBox.question3` mocked — confirmed the
  unsaved-changes prompt now actually fires (it did not before the fix)
  and that choosing Cancel leaves the in-memory project object untouched.
  Also re-run against a real, fully `main.py`-launched and `.show()`n
  `MainWindow` (not just a constructed-but-hidden one) — typing still
  correctly sets `_dirty = True`. See `changelog.md` Session 9 for the
  full verification list shared with #25/#26.
- **Files modified**: `app/main_window.py` (`ProjectSection`: new
  `project_changed` signal, `_loading` flag, `_on_field_changed()`,
  `_build()` field-signal wiring, `load_project()`, `_apply()`;
  `MainWindow._build()`: new `project_changed` connection).

### 13. [done] Failed recent-project load leaves wrong row selected
- **File**: `app/main_window.py`, `ProjectSection._open_recent()` (~401–415)
- **Detail**: the `except Exception` branch (corrupt/bad `.rackproj` file)
  shows `MsgBox.error` but never calls `_refresh_recent()` (unlike the
  sibling "user cancelled via dirty-check" branch just above it), so the
  sidebar list stays visually selected on the failed row even though
  `self.project`/`self._filepath` still point at the previously-loaded
  project.
- **Trigger**: load a valid recent project, then click a different recent
  entry whose file is corrupt.
- **Live-reproduced**: yes (real `QTest.mouseClick`) — confirmed
  `recent_list.currentItem()` mismatches the actually-loaded project.
- **Severity**: real-but-minor — no data corruption (Save still targets
  the real file), but misleading UI state.
- **Fixed 2026-07-29 (Session 17)**. `_open_recent()`'s `except` branch
  now calls `self._refresh_recent()` right after `MsgBox.error(...)`,
  matching the sibling dirty-check-cancelled branch above it.
- **Verification (2026-07-29)**: offscreen-Qt script — spied on
  `_refresh_recent()`, forced `storage.load_project()` to raise via a
  bogus path: confirmed `_refresh_recent()` is now called after the
  error dialog.
- **Files modified**: `app/main_window.py`
  (`ProjectSection._open_recent()`).

### 14. [done] Wrong-rack device placement: sidebar rack selection doesn't update the "active" canvas
- **File**: `app/main_window.py`, `DesignerSection._on_canvas_active`
  (~1021–1036), `_active_rack_row()` (~1213–1218), `_add_device_dbl()`
  (~1233–1250)
- **Detail**: `self._active_canvas` only updates when a canvas itself is
  clicked (`became_active` signal) — clicking a rack's row in the sidebar
  `rack_list` does not update it. `_add_device_dbl`/`_add_custom` prefer
  `_active_canvas` over the list's `currentRow()`, so a double-clicked
  library device can land in a different rack than the one visually
  highlighted in the sidebar.
- **Trigger**: with 2+ racks, click inside Rack A's canvas, then click
  Rack B's sidebar row (no click inside B), then double-click a library
  device — it's added to Rack A, not the visually-selected Rack B.
- **Live-reproduced**: yes — `_active_rack_row()` resolved to Rack A while
  `rack_list.currentRow()` showed Rack B.
- **Severity**: likely-real-and-impactful.
- **Fixed 2026-07-28 (Session 10), together with #17** (same root cause —
  `_active_canvas` staying stale — per the session brief). `rack_list`
  gained a `currentRowChanged` connection to a new
  `DesignerSection._on_rack_row_selected(row)`, which — for a valid row —
  calls the existing `_on_canvas_active(self._canvases[row])`. Reusing
  `_on_canvas_active()` rather than writing separate logic means clicking
  a sidebar row now does exactly what clicking inside that rack's canvas
  already did: deselects the previously-active canvas's slot selection,
  updates `_active_canvas`, and re-syncs `rack_list`'s own `currentRow`
  (a no-op in this direction, since the row is already what just changed —
  `_on_canvas_active`'s existing `blockSignals` guard prevents any
  feedback loop).
- **Verification (2026-07-28)**: offscreen-Qt script — direct calls via
  `rack_list.setCurrentRow(n)` confirmed `_active_canvas`/`_active_rack_row()`
  now track the sidebar selection with no canvas ever clicked directly.
  Also re-run with a real `MainWindow`/`DesignerSection` and real
  `QTest.mouseClick` on the actual `rack_list` viewport (not a direct
  `setCurrentRow()` call) — clicking row 0 then row 1 correctly moved
  `_active_canvas` to each rack's real canvas widget in turn.
- **Files modified**: `app/main_window.py` (`DesignerSection._build()`:
  new `rack_list.currentRowChanged` connection; new
  `_on_rack_row_selected()`).

### 15. [done] Rack reorder corrupts data when two racks share a name
- **File**: `app/main_window.py`, `DesignerSection._on_rack_reordered()` (~1078–1096)
- **Detail**: rebuilds `project.racks` after a drag-reorder by matching
  each row's displayed name back to a `Rack` via
  `next(r for r in self.project.racks if r.name == rack_name)`. Two
  same-named racks (trivial to create — `AddRackDialog` defaults the name
  field to the literal "New Rack" with no uniqueness check) collapse:
  `next()` always returns the first match, duplicating that rack object
  and displacing the second same-named rack to the end via the fallback
  append.
- **Trigger**: create two racks both left at the default name "New Rack",
  drag one to reorder.
- **Live-reproduced**: yes — `project.racks` grew from 2 to 3 entries,
  with one rack object duplicated (identical `id()`) and the other
  shoved to the end. Persists to disk on save.
- **Severity**: likely-real-and-impactful — real, save-serializable data
  corruption.
- **Investigated first, per the session brief** (Task 1: does `Rack` have a
  stable identity independent of `name`?). It already does:
  `app/models.py`'s `Rack` dataclass has had
  `id: str = field(default_factory=lambda: str(uuid.uuid4()))` since before
  this session, already included in both `to_dict()` and `from_dict()` —
  `from_dict()` generates a fresh id (`d.get("id", str(uuid.uuid4()))`) for
  any `.rackproj` written before this field existed, so old project files
  load safely. No data-model change was needed; the bug is purely that
  `_on_rack_reordered()` matched by `name` instead of using the `id` that
  was already there.
- **Fixed 2026-07-28 (Session 10)**. `_refresh_rack_list()` now stores each
  row's `rack.id` via `item.setData(Qt.ItemDataRole.UserRole, rack.id)`
  (the same pattern already used for library-device rows in `_refresh_lib()`).
  `_on_rack_reordered()` now reads that id back
  (`item.data(Qt.ItemDataRole.UserRole)`) and matches
  `next(r for r in self.project.racks if r.id == rack_id)` instead of
  matching on the displayed name — two racks named "New Rack" now reorder
  correctly without collapsing.
- **Verification (2026-07-28)**: offscreen-Qt script — two same-named racks,
  reordered via `_on_rack_reordered()` directly: `project.racks` stayed at
  length 2, both original rack objects present exactly once, in the new
  order. **Sanity check**: temporarily re-ran the *old* name-matching logic
  (kept as a local function in the test script, not restored into the
  source) against the same setup — reproduced the exact bug (`len`
  grew to 3, one rack duplicated) — confirming the test actually catches
  this failure mode before trusting the fix.
- **Files modified**: `app/main_window.py`
  (`DesignerSection._refresh_rack_list()`, `._on_rack_reordered()`).

### 16. [done] Off-by-one falsely blocks legal rack-shrink operations
- **File**: `app/main_window.py`, `DesignerSection._edit_rack()`, line
  ~1186: `removed_rows = range(1, 1 - delta + 1)`
- **Detail**: when shrinking a rack by `n = abs(delta)` U from the top,
  the occupancy check should cover rows `1..n` but the range evaluates to
  `1..n+1` — one row too many — so it can reject resizes that are
  actually legal.
- **Trigger**: rack with a device NOT in the top row but within the
  "extra" checked row; shrink by exactly 1U (top row genuinely empty).
- **Live-reproduced**: yes — shrinking 20U→19U with a 1U device at U2 was
  incorrectly blocked ("Cannot remove 1U: ... Dev@U2"), and `rack.u_size`
  stayed at 20. Only over-blocks (no under-block/corruption found), but a
  real functional defect on a common workflow, and the error message
  names a device outside the region actually being removed.
- **Severity**: likely-real-and-impactful.
- **Fixed 2026-07-29 (Session 14)**. `removed_rows` is now
  `range(1, -delta + 1)` (i.e. `range(1, n + 1)` for `n = abs(delta)`),
  covering exactly the rows actually being removed, `1..n`, instead of
  `1..n+1`. `-delta` (delta is already negative on this branch) reads
  the same as `abs(delta)`/`n` without introducing a new local variable.
  Nothing else in the shrink path changed — the shift-up logic
  (`s.position_u += delta`) and the collision-blocking behavior for a
  genuinely-occupied removed row are unchanged.
- **Verification (2026-07-29)**: offscreen script — drove the real
  `DesignerSection._edit_rack()` (with `EditRackDialog` swapped for a
  fake returning the target size, `MsgBox.warn` mocked to detect calls)
  on the exact scenario from the finding: a 20U rack with a 1U device at
  U2, shrunk to 19U — confirmed the resize is now allowed (`u_size ==
  19`), no "Units in use" warning fires, and the device correctly shifts
  from U2 to U1. Confirmed a shrink that *should* be blocked (device
  genuinely at U1) still is, with the warning still firing. **Sanity
  check**: evaluated the old `range(1, 1 - delta + 1)` formula directly
  against the U2-device scenario — confirmed it covers U2 as well as U1,
  reproducing the false block before trusting the fix.
- **Files modified**: `app/main_window.py` (`DesignerSection._edit_rack()`).

### 17. [done] `_active_canvas` never reset after rack add/remove/edit/reorder — undo desync
- **File**: `app/main_window.py`, `DesignerSection` — `_active_canvas`
  (set in `__init__` ~577, only reassigned in `_on_canvas_active` ~1028),
  never touched by `_add_rack`/`_remove_rack`/`_edit_rack`/
  `_on_rack_reordered` (~946–983, 1147–1211), consumed unguarded by
  `undo()` (~1098–1100)
- **Detail**: those four operations all call `_clear_racks()` +
  `_refresh_rack_view()`, discarding old `RackCanvas` widgets and
  building new ones — but `_active_canvas` keeps pointing at the
  now-orphaned old widget. Ctrl+Z then calls `.undo()` on the orphaned
  canvas: the underlying `Rack` data object is the same, so the undo does
  mutate correct data, but `.update()` repaints the invisible orphaned
  widget, not the new on-screen one — the visible canvas doesn't reflect
  the undo until an unrelated repaint happens. The first click inside the
  new canvas then permanently orphans whatever undo history existed.
- **Trigger**: remove/edit/reorder any rack while a different rack's
  canvas is active, then Ctrl+Z.
- **Live-reproduced**: yes — `update()` fired on the stale/detached
  canvas, not the actual visible parented one.
- **Severity**: likely-real-and-impactful — distinct from the
  already-documented "cross-rack move = two independent undo entries"
  behavior in `design.md`.
- **Fixed 2026-07-28 (Session 10), together with #14** (same root cause —
  per the session brief). Added `DesignerSection._restore_active_canvas
  (prev_rack_id)`: re-points `_active_canvas` at the rebuilt canvas whose
  `.rack.id` matches `prev_rack_id` (the previously-active rack's `id`,
  captured *before* the rebuild — matched by id per #15's identity model,
  not by list position or name, since both can shift under
  add/remove/reorder), falling back to the first canvas, or `None`, if
  that rack no longer exists (e.g. it was the one just removed).
  `_add_rack()`, `_remove_rack()`, `_edit_rack()`, and
  `_on_rack_reordered()` each now capture `prev_rack_id =
  self._active_canvas.rack.id if self._active_canvas else None` right
  before their existing `_clear_racks()` + `_refresh_rack_view()` call,
  then call `_restore_active_canvas(prev_rack_id)` immediately after —
  `_active_canvas` now always points at a live, on-screen `RackCanvas`
  belonging to the current `_canvases` list, never a discarded widget.
- **Verification (2026-07-28)**: offscreen-Qt script — made a rack active,
  triggered an add-rack-style rebuild (append + `_clear_racks()` +
  `_refresh_rack_view()` + `_restore_active_canvas()`), confirmed
  `_active_canvas` is a *new* widget instance (not the pre-rebuild one)
  but still resolves to the same rack; confirmed the identical sequence
  after removing the previously-active rack itself falls back to the
  first remaining canvas rather than `None`/orphaned. **Sanity check**:
  ran the same rebuild sequence while skipping the
  `_restore_active_canvas()` call (i.e., the exact pre-fix behavior) and
  confirmed `_active_canvas` was left pointing at a widget no longer
  present in the new `_canvases` list — reproducing the orphaned-widget
  bug before trusting the fix.
- **Files modified**: `app/main_window.py` (new
  `DesignerSection._restore_active_canvas()`; call sites added in
  `_add_rack()`, `_remove_rack()`, `_edit_rack()`, `_on_rack_reordered()`).

### 18. [done] Designer tab's category filter never refreshes on category changes
- **File**: `app/main_window.py`, `DesignerSection.cat_filter` (built once
  ~732–741 via `get_categories()`), `reload_library()` (~1102–1104)
- **Detail**: `reload_library()` only calls `_refresh_lib()` (rebuilds the
  device list), never rebuilds `cat_filter`'s items — unlike
  `LibrarySection`'s equivalent combo, which does refresh on every
  category change. A newly-added custom category is invisible in the
  Designer tab's filter dropdown until app restart.
- **Trigger**: add a device in a brand-new custom category via the
  Library tab, switch to Designer.
- **Live-reproduced**: no (code-path gap confirmed by inspection).
- **Severity**: real-but-minor.
- **Fixed 2026-07-29 (Session 17)**. `reload_library()` now rebuilds
  `cat_filter`'s items the same way `LibrarySection.reload()`'s
  equivalent combo already did: preserves the current selection by text,
  clears and re-adds `["All categories"] + get_categories()` with
  signals blocked, then re-selects the previous text if it still exists
  (falling back to index 0 otherwise).
- **Verification (2026-07-29)**: offscreen-Qt script — registered a new
  custom category, called the real `reload_library()`: confirmed the new
  category is now present in `cat_filter`'s items (it wasn't before the
  call).
- **Files modified**: `app/main_window.py`
  (`DesignerSection.reload_library()`).

### 19. [done] Misleading empty-state message adding a device with 0 racks
- **File**: `app/main_window.py`, `DesignerSection._add_device_dbl()` (~1233–1244)
- **Detail**: with 0 racks, falls through to `MsgBox.info("Add device",
  "Select a rack first.")` — misleading, since there's nothing to select.
  The sibling `_add_custom()` correctly says "No racks in project."
- **Live-reproduced**: yes.
- **Severity**: real-but-minor.
- **Fixed 2026-07-29 (Session 17)**. `_add_device_dbl()` now checks
  `len(self.project.racks) == 0` explicitly and shows "No racks in
  project." for that case, matching `_add_custom()`'s wording; the
  actual multi-rack-no-selection case still shows "Select a rack first.",
  which remains accurate there.
- **Verification (2026-07-29)**: offscreen-Qt script — called the real
  `_add_device_dbl()` on a `DesignerSection` with an empty project:
  confirmed the dialog message is now "No racks in project."
- **Files modified**: `app/main_window.py`
  (`DesignerSection._add_device_dbl()`).

### 20. [done] JSON library import doesn't register unrecognized categories → silent corruption on next save
- **File**: `app/main_window.py`, `LibrarySection._import_dialog()` JSON
  branch (~1838–1840, hardcodes `new_cats, warnings = [], []`), interacts
  with `LibrarySection._save()` (~1725–1740) and `DeviceForm.load()`
  (`app/library_dialog.py`, see #30)
- **Detail**: unlike the CSV import path (which calls
  `storage.add_custom_category()`), JSON import never registers a
  device's category if it's not already known locally. Selecting such a
  device in the Library tab makes `DeviceForm`'s category combo silently
  fall back to a default (see #30); saving any edit — even an unrelated
  field — then overwrites the real category via the blind
  `setattr(dev, k, v)` loop, the same shape as the previously-fixed
  image-wipe bug (#5).
- **Trigger**: import a JSON library containing a device whose category
  isn't in the local default+custom set (e.g. from another install, or an
  export made before a category was renamed/removed), select it, edit any
  field, Save.
- **Live-reproduced**: yes — category silently changed `"Wireless"` →
  `"Video"` after an unrelated wattage edit + save.
- **Severity**: likely-real-and-impactful. See #30 (same failure mode,
  root cause in `library_dialog.py`'s `DeviceForm.load()`).
- **Fixed 2026-07-28 (Session 11), together with #30 — one shared
  mechanism, per the session brief.** Added
  `storage.register_category_if_unknown(category)`: if `category` isn't
  in `get_categories()`'s known default+custom set, registers it via the
  existing `add_custom_category()` and returns it unchanged either way.
  `LibrarySection._import_dialog()`'s JSON branch now scans every
  imported device's category through this helper (mirroring what the CSV
  path already did inline) instead of hardcoding `new_cats, warnings =
  [], []` — any unrecognized category is registered and reported in the
  "New categories: …" summary, same as CSV import. CSV import's own
  inline `add_custom_category(category)` call was also switched to the
  same helper for consistency (behavior-preserving — `add_custom_category`
  is idempotent either way), so all three category-encountering paths
  (CSV import, JSON import, `DeviceForm.load()`) now go through one place.
- **Verification (2026-07-28)**: offscreen-Qt script — real
  `LibrarySection._import_dialog()` (not a direct helper call) with
  `QFileDialog.getOpenFileName`/`app.dialogs._MsgDialog`/`MsgBox.*`
  mocked, importing a JSON file with one device in an unrecognized
  category via "Merge": confirmed the category is now present in
  `custom_categories.json`.
- **Files modified**: `app/storage.py` (new
  `register_category_if_unknown()`; `import_library_csv()`'s inline call
  switched to it), `app/main_window.py`
  (`LibrarySection._import_dialog()`'s JSON branch).

### 21. [done] JSON merge-import can create duplicate device IDs
- **File**: `app/main_window.py`, `LibrarySection._import_dialog()`
  "Merge" branch (~1868–1874); `app/models.py`,
  `DeviceDefinition.from_dict()` (~92–93, preserves imported `id`)
- **Detail**: merge dedup checks only `(name, category)`, never `id`.
  Re-importing a JSON export of a device that was since renamed locally
  (or importing a foreign library seeded from the same original export)
  creates two library entries sharing one `id`. Every by-id operation
  (`_on_select`, `_save`, `_duplicate`, `_delete`) then either silently
  edits the wrong one of the pair (first list match wins) or, for
  `_delete`, removes **both** devices in one action with no warning.
- **Trigger** (pure UI): export a device to JSON → rename it in the
  Library tab and Save → re-import the same JSON file choosing "Merge."
- **Live-reproduced**: yes, at the data-model level — confirmed two
  devices sharing one UUID, traced the resulting `_delete`/`_save` paths.
- **Severity**: likely-real-and-impactful.
- **Fixed 2026-07-28 (Session 11)**. The Merge branch now tracks
  `existing_ids = {d.id for d in self.devices}` alongside the existing
  `(name, category)` dedup set. For each device that passes the existing
  name/category filter (`to_add`), if its `id` already exists — in the
  library *or* in another device already processed earlier in this same
  import batch — it's assigned a fresh `uuid4()` before being added;
  `existing_ids` is updated after each addition so a batch containing two
  colliding ids internally (not just against the library) is also
  resolved. The existing device holding that `id` is never touched.
  Import stays purely additive, and every device in the library has a
  unique `id` by construction afterward.
- **Verification (2026-07-28)**: offscreen-Qt script — exact scenario
  from the brief via the real `LibrarySection._import_dialog()`
  (`QFileDialog`/`_MsgDialog`/`MsgBox.*` mocked): one device in the
  library (renamed locally, same `id` as its original JSON export),
  re-imported the same (old-name) JSON via "Merge" — confirmed the
  library ends up with exactly 2 devices with 2 distinct ids, the
  original device's own name is untouched, the newly-added device holds
  the imported name under a fresh id, and editing one afterward doesn't
  affect the other. **Sanity check**: reproduced the pre-fix
  `(name, category)`-only dedup directly (no id handling at all) against
  the same setup — confirmed it produces two devices sharing one id,
  before trusting the fix.
- **Files modified**: `app/main_window.py`
  (`LibrarySection._import_dialog()`'s Merge branch).

### 22. [done] Merge-import dedup set is stale within the same import
- **File**: `app/main_window.py`, `LibrarySection._import_dialog()` Merge
  branch (~1868–1874)
- **Detail**: the `existing` dedup set is computed once from
  `self.devices` before the merge loop and never updated as new items are
  appended, so a file containing two entries with the same
  `(name, category)` gets both appended, with the "N duplicates skipped"
  count not reflecting this.
- **Live-reproduced**: no (static, clear from code).
- **Severity**: real-but-minor.
- **Fixed 2026-07-29 (Session 17)**. The Merge branch now iterates
  `imported` once in a single loop (instead of a static list
  comprehension against a snapshot set), checking each device against
  `existing`/`existing_ids` and adding both the `(name, category)` pair
  and the (possibly reassigned, per #21) `id` to those sets immediately
  after each addition — so a second entry in the same file that collides
  with the first is now correctly caught as a duplicate too, not just
  entries colliding with the pre-import library state.
- **Verification (2026-07-29)**: offscreen-Qt script — imported a JSON
  file with two devices sharing the same `(name, category)` (and no
  pre-existing library conflict) via the real `_import_dialog()`
  (`QFileDialog`/`_MsgDialog` mocked): confirmed only 1 of the 2 is
  added. **Sanity check**: reproduced the pre-fix static-set
  comprehension directly against the same two-duplicate input —
  confirmed it would have added both, reproducing the bug before
  trusting the fix.
- **Files modified**: `app/main_window.py`
  (`LibrarySection._import_dialog()`'s Merge branch).

### 23. [done] CSV export silently drops device images with no warning
- **File**: `app/main_window.py`, `LibrarySection._export_dialog()` CSV
  branch (~1792–1818)
- **Detail**: `image_front`/`image_rear` are omitted from CSV export with
  no UI hint; `storage.import_library_csv()` has no column to restore
  them. An "export as backup"/"export, reformat, reimport" workflow via
  CSV silently loses images (JSON export/import preserves them
  correctly).
- **Severity**: real-but-minor.
- **Fixed 2026-07-29 (Session 17)**. The CSV branch of `_export_dialog()`
  now shows a `MsgBox.info` notice ("CSV export does not include device
  images... Use JSON export to preserve them") once, right after the
  user picks CSV as the export format — the CSV format itself is
  unchanged, per the task's explicit scope.
- **Verification (2026-07-29)**: offscreen-Qt script — drove the real
  `_export_dialog()` (format pickers mocked to select "Entire library"
  then "CSV (.csv)"): confirmed the notice fires before the file is
  written.
- **Files modified**: `app/main_window.py`
  (`LibrarySection._export_dialog()`).

### 24. [done] Empty-library category-scope export opens a dead-end dialog
- **File**: `app/main_window.py`, `LibrarySection._export_dialog()`,
  "Category" scope (~1761–1767)
- **Detail**: with 0 devices, `all_cats` is `[]` and
  `QInputDialog.getItem(..., items=[], ...)` runs before the later
  `if not devs` guard — opens a functionally empty picker (no exception,
  but nothing to select; user can only Cancel).
- **Live-reproduced**: yes (no crash, confirmed empty combo).
- **Severity**: real-but-minor.
- **Fixed 2026-07-29 (Session 17)**. The "Category" scope branch now
  checks `if not all_cats` immediately after computing it and shows a
  clear "Library is empty — nothing to export." message before ever
  opening `QInputDialog.getItem`.
- **Verification (2026-07-29)**: offscreen-Qt script — drove the real
  `_export_dialog()` on a `LibrarySection` with an empty library, format
  picker forced to "Category": confirmed the category picker is never
  opened and the empty-library message fires instead.
- **Files modified**: `app/main_window.py`
  (`LibrarySection._export_dialog()`).

### 25. [done] Racks added before the first Save can be silently discarded
- **File**: `app/main_window.py`, `MainWindow._build()` (~2255–2265),
  `_on_project_loaded()` (~2312), interacting with
  `DesignerSection.set_project()`/`ProjectSection.__init__`/`_apply()`
- **Detail**: `ProjectSection` and `DesignerSection` each construct their
  own independent default `Project()` at startup. Nothing unifies them
  until the first `_apply()` call (any Save action), which does a
  destructive full-reference swap (`self.designer.project = project`)
  rather than a merge — so any racks added directly in the Designer tab
  before that first save are silently replaced by `ProjectSection`'s
  separate, empty default project, both in memory and on disk.
- **Trigger**: open the app, go straight to Designer (skip Project tab),
  add a rack, then Ctrl+S / Save.
- **Live-reproduced**: yes — after appending a rack directly to
  `mw.designer.project.racks` then calling `mw._save()`, the object
  passed to `storage.save_project()` had `racks=[]`.
- **Severity**: likely-real-and-impactful.
- **Investigated first, per the session brief.** Read
  `MainWindow.__init__`/`_build()`, `ProjectSection.__init__`,
  `DesignerSection.__init__`, and every `set_project()`. Found: each of
  `ProjectSection`, `DesignerSection` (and, unrelated to this bug,
  `ExportSection`) is constructed exactly once, only in
  `MainWindow._build()`; nothing reads `.project` on either before the
  point a shared reference could be assigned; and every existing
  New/Open/Save convergence point (`_new()`, `_open()`, `_open_recent()`,
  `_on_project_loaded()`) already reassigns *both* `proj_section.project`
  and `designer.project` to the same object going forward — so sharing a
  single `Project()` from construction only closes the pre-first-save
  gap and doesn't change any later behavior. No reason found to treat a
  shared-reference approach as unsafe; proceeded with the preferred fix
  rather than a merge-on-save patch.
- **Fixed 2026-07-25 (Session 9)**. `ProjectSection.__init__` and
  `DesignerSection.__init__` now accept an optional `project=` parameter
  (defaulting to a fresh `Project()` if omitted, so both classes remain
  independently constructible). `MainWindow._build()` now constructs one
  `self.project = Project()` and passes that same reference to both
  `ProjectSection(project=self.project)` and
  `DesignerSection(project=self.project)` — there is no longer a second
  object for the first `_apply()`/`set_project()` swap to discard.
  `ExportSection` (a third independent `Project()` at construction) was
  deliberately left unchanged — it's synced explicitly on both tab-switch
  and `_on_project_loaded()`, is never itself edited, and isn't part of
  this bug's failure mode; touching it wasn't in scope.
- **Verification (2026-07-25)**: offscreen-Qt script — confirmed
  `proj_section.project is designer.project` immediately after
  construction; appended a rack directly to `designer.project.racks`
  *before any Save*, called the real `MainWindow._save()`, and confirmed
  the rack is present both via `proj_section.project` (pre-save) and in
  the file `storage.load_project()` reads back (post-save). **Sanity
  check**: temporarily reverted the fix (back to two independent
  `ProjectSection()`/`DesignerSection()` constructions) and re-ran — the
  identity check and the rack-survival check both failed exactly as the
  bug describes (rack silently dropped, `racks=[]` on disk), confirming
  the test actually catches the bug before restoring the fix. Also
  re-run against a real `main.py`-launched, `.show()`n window. See
  `changelog.md` Session 9 for the full shared verification list.
- **Files modified**: `app/main_window.py`
  (`ProjectSection.__init__`, `DesignerSection.__init__`,
  `MainWindow._build()`).

### 26. [done] Dirty flag cleared before save is confirmed to succeed
- **File**: `app/main_window.py`, `MainWindow._save()` (~2343–2357),
  `closeEvent()` (~2359–2367), `_dirty_check()` (~2330–2341)
- **Detail**: `_save()` calls `self.proj_section._apply()` — which
  unconditionally emits `project_loaded`, wired to `_on_project_loaded()`,
  which unconditionally clears `self._dirty` — *before* the
  `try/except`-wrapped `storage.save_project()` call. If the write then
  raises (caught, shown via `MsgBox.error`), `self._dirty` is never
  restored to `True`. `closeEvent`'s "Save before closing? → Yes" and
  `_dirty_check`'s "Save before opening another project? → Yes" paths
  both then proceed as if the save succeeded — closing the window /
  loading the new project — even though nothing was written to disk.
- **Trigger**: make the project dirty, force `storage.save_project` to
  raise (read-only target folder, disk full, invalid path), press Ctrl+S,
  or close the window / open another project choosing "Save"/"Yes".
- **Live-reproduced**: yes (monkeypatched failing `storage.save_project`)
  — `mw._dirty` stayed `False` and `closeEvent`'s `event.isAccepted()`
  was `True` despite the failed write.
- **Severity**: likely-real-and-impactful.
- **Investigated first, per the session brief.** Re-read `_save()` in its
  current, post-Session-8 shape (Session 8 changed the return value of
  `storage.save_project()` to `(filepath, resolved_name)` and added the
  explicit `project.name = resolved_name` line, but did not touch the
  dirty-flag ordering) — confirmed the premature clear is still exactly
  where the finding describes: `self.proj_section._apply()`'s
  `project_loaded.emit()` reaches `_on_project_loaded()` (`self._dirty =
  False`) before the `try:` block around `storage.save_project()` even
  starts.
- **Fixed 2026-07-25 (Session 9), minimal fix as directed** (no
  restructuring of `project_loaded`'s emit order, since it likely has
  other listeners/uses and reordering it would be a bigger, riskier
  change than this bug needs): the `except Exception as e:` block in
  `_save()` now does `self._dirty = True` followed by `self._update_title()`
  (so the title-bar dirty dot and navbar indicator reflect the restored
  state immediately) **before** `MsgBox.error(...)`.
- **Verification (2026-07-25)**: offscreen-Qt script — dirtied a real
  project, monkeypatched `storage.save_project` to raise, called the
  real `MainWindow._save()`: confirmed `_dirty` is restored to `True`,
  the title bar shows the dirty dot, the error dialog fires with the
  simulated message, `_dirty_check()` still prompts (and still honors
  Cancel), and `closeEvent()` still calls `event.ignore()` — i.e. the
  window does not close and no data-loss path opens up, exactly the
  scenario the finding described as broken. Regression-checked that a
  subsequent *successful* save still clears `_dirty` normally. **Sanity
  check**: temporarily reverted the fix (removed the two added lines from
  the `except` block) and re-ran — `_dirty` incorrectly stayed `False`
  after the simulated failure, reproducing the exact bug, before
  restoring the fix. Also re-run against a real `main.py`-launched,
  `.show()`n window. See `changelog.md` Session 9 for the full shared
  verification list.
- **Files modified**: `app/main_window.py` (`MainWindow._save()`).

### 27. [done] Rack-size spinner arrows discard uncommitted typed text
- **File**: `app/main_window.py`, `AddRackDialog._make_spin()` (~1961–1973)
  and the identical pattern in `EditRackDialog` (~2118–2122)
- **Detail**: the ▲/▼ buttons compute the new value from the dialog's
  internal committed `_size_val`/`_bays_val` attribute, not from the
  QLineEdit's current (possibly uncommitted) text — the field only
  commits on `editingFinished`/Enter. Clicking an arrow after typing (but
  before losing focus/pressing Enter) silently overwrites the field with
  `(old committed value ± 1)`.
- **Trigger**: type a new value into Size(U)/Bays without Tab/Enter, then
  click an arrow button.
- **Live-reproduced**: yes — typing "50" then invoking the up-arrow
  handler yielded `_size_val == 21` (old value 20 + 1), not derived from
  50 at all.
- **Severity**: likely-real-and-impactful — silent, easily-hit input
  loss producing a wrong rack size with no warning (not a crash).
- **Fixed 2026-07-28 (Session 11)**. Both `AddRackDialog` and
  `EditRackDialog` gained a new `_step(attr, field, delta, min_val,
  max_val)` method that first calls the existing `_commit_spin()` (the
  same parse+clamp `editingFinished` already runs) to sync the committed
  attribute with whatever's currently typed, then applies `delta` via the
  existing `_set()`. Every arrow button's `clicked` connection
  (`size_up`/`size_dn`/`bays_up`/`bays_dn` in `AddRackDialog`,
  `size_up`/`size_dn` in `EditRackDialog`) now calls `_step(...)` instead
  of directly computing `self._size_val + 1`/`- 1`. `_commit_spin()` and
  `_set()` themselves are unchanged — `_step()` is duplicated between the
  two dialog classes rather than shared, matching how `_make_spin()`/
  `_set()`/`_commit_spin()` were already duplicated between them (they
  don't share a base class).
- **Verification (2026-07-28)**: offscreen-Qt script — `AddRackDialog`:
  typed `"50"` into the Size field without Tab/Enter, then a real
  `QTest.mouseClick` on the actual up-arrow `QPushButton` (found by text,
  not a direct method call) — confirmed `_size_val == 51`, not `21`.
  `EditRackDialog`: typed `"33"`, called `_step(..., -1, ...)` directly —
  confirmed `32`, not `19`. **Sanity check**: reproduced the pre-fix
  arrow behavior directly (`self._set("_size_val", ..., self._size_val +
  1, ...)`, skipping the commit) against the same typed-`"50"` setup —
  confirmed it yields `21` (old committed value + 1), reproducing the bug
  before trusting the fix.
- **Files modified**: `app/main_window.py` (`AddRackDialog`: new
  `_step()`, arrow-button connections; `EditRackDialog`: same).

### 28. [done] Rack-size preset combobox doesn't stay in sync
- **File**: `app/main_window.py`, `AddRackDialog.__init__()` preset combo
  wiring (~1954–1976)
- **Detail**: the preset combo only pushes values one-way into
  `_size_val`; nothing resets/re-syncs it when the size changes via
  typing or the spinner arrows (or even in the dialog's own initial
  state — defaults to 20U, which matches a real preset, but the combo
  shows "Custom").
- **Live-reproduced**: no (static, clear from code + confirmed initial
  mismatch).
- **Severity**: real-but-minor — cosmetic/UX only.
- **Fixed 2026-07-29 (Session 17)**. Added
  `AddRackDialog._sync_preset_combo(value)`: sets the preset combo to
  the matching preset index if `value` is one of the known preset sizes,
  or index 0 ("Custom") otherwise — wrapped in `blockSignals` so it
  can't re-trigger the combo's own `currentIndexChanged` handler. `_set()`
  (the one place `_size_val`/`_size_lbl` actually get written, reached by
  typing via `_commit_spin()`, the arrow buttons via `_step()`, and the
  preset combo's own selection) now calls it whenever `attr ==
  "_size_val"`. The dialog's initial 20U default (set directly, not
  through `_set()`) is synced explicitly once at the end of `__init__()`,
  so the combo correctly shows "20U" from the moment the dialog opens
  instead of defaulting to "Custom".
- **Verification (2026-07-29)**: offscreen-Qt script — confirmed the
  combo shows "20U" on construction; typing/committing 25 (not a preset)
  shows "Custom"; stepping down to 24 (a preset) shows "24U" again.
- **Files modified**: `app/main_window.py`
  (`AddRackDialog`: new `_sync_preset_combo()`; `_set()`; `__init__()`).

### 29. [done] `rack_native` toggle off-then-on leaves a stale `height_mm`
- **File**: `app/library_dialog.py`, `DeviceForm._on_rack_native_changed()`
  (~506), `DeviceForm.collect()` (~543–561)
- **Detail**: toggling "Rack-native" off then back on only
  `setEnabled(False)`s `height_mm_spin` — it never clears the stored
  value. `collect()` still returns a non-`None` `height_mm` for a device
  now flagged `rack_native=True`, contradicting `design.md`'s stated
  invariant ("True → standard 19" device, height in `u_height`").
- **Trigger**: open a device, uncheck Rack-native, type a height (e.g.
  199mm), re-check Rack-native, save.
- **Live-reproduced**: yes — final `collect()` returned
  `rack_native=True, height_mm=199.0`.
- **Severity**: likely-real-and-impactful — silent persisted data
  corruption, the proven bug shape this audit was told to hunt for.
- **Fixed 2026-07-28 (Session 11)**. `_on_rack_native_changed()` now
  calls `self.height_mm_spin.setValue(0)` (which `collect()` already
  treats as `None`, same as any other "empty" spin field) whenever
  `rack_native` becomes `True`, in addition to the existing
  `setEnabled(not native)`. Since `_on_rack_native_changed()` is also
  called as the last step of `DeviceForm.load()` (after all fields are
  populated), this additionally normalizes any *pre-existing*
  invariant-violating record (`rack_native=True` with a non-`None`
  `height_mm` already on disk, from before this fix) the moment it's
  opened and saved — not just newly-toggled ones.
- **`width_mm` cross-check (per the brief)**: `width_mm_spin` is **not**
  touched by `_on_rack_native_changed()` at all, in either direction —
  unlike `height_mm_spin` it's never `setEnabled(False)`, so there's no
  analogous "disabled-but-stale" gap to fix. This looks like existing,
  correct behavior rather than an oversight: `width_mm` is meaningful
  for tray-sharing regardless of `rack_native` (`RackSlot._can_add_to_tray()`
  in `rack_canvas.py` already independently blocks tray-sharing for any
  `rack_native=True` slot via its own `snap.get("rack_native", True)`
  check, not via `width_mm`), so leaving the field live either way is
  consistent rather than a second instance of #29's bug. No code change
  made for `width_mm`.
- **Verification (2026-07-28)**: offscreen-Qt script — unchecked
  rack-native, set `height_mm_spin` to 199.0, re-checked rack-native,
  `collect()`: confirmed `height_mm is None` and `rack_native is True` in
  the same result. Cross-check confirmed `width_mm_spin.isEnabled()` stays
  `True` through the same toggle sequence and its typed value survives
  (expected, not a bug). **Sanity check**: reproduced the pre-fix handler
  (`setEnabled(False)` only, no clear) directly against the same
  199.0-then-retoggle setup — confirmed `collect()` still returns
  `height_mm=199.0` despite `rack_native=True`, reproducing the bug
  before trusting the fix.
- **Files modified**: `app/library_dialog.py`
  (`DeviceForm._on_rack_native_changed()`).

### 30. [done] Unrecognized device category silently falls back on load, corrupted on next save
- **File**: `app/library_dialog.py`, `DeviceForm.load()` (~520–523)
- **Detail**: when `device.category` isn't in the current category list
  (e.g. a custom category later deleted from `custom_categories.json`, or
  a device imported from elsewhere — see #20), `findText()` returns -1
  and is silently ignored, leaving the combo at whatever `reload()`
  defaulted to (index 0, "Video" — not even the model's own "Other"
  fallback). No warning is shown. Saving then persists the wrong
  category via `collect()`, silently overwriting the original.
- **Trigger**: load a device whose category isn't currently registered,
  save (even with no other changes).
- **Live-reproduced**: yes — category `"ThisCategoryDoesNotExistAnywhere"`
  silently became `"Video"` after load()+collect(). No in-app UI
  currently exists to delete a custom category, so today's trigger
  requires manual JSON editing or a library moved between machines — but
  the reachable surface grows the moment a category-delete/rename feature
  is added, and #20 (JSON import) is one concrete way to hit it today.
- **Severity**: likely-real-and-impactful. See #20 (same failure mode).
- **Fixed 2026-07-28 (Session 11), together with #20 — one shared
  mechanism.** `DeviceForm.load()` now checks `findText(device.category)`
  as before, but on a miss (and a non-empty `device.category`) calls the
  new `storage.register_category_if_unknown(device.category)`, reloads
  the combo, and re-searches — the category is now in the combo's item
  list and gets selected for real, instead of leaving the combo on
  whatever `reload()` defaulted to.
- **Verification (2026-07-28)**: offscreen-Qt script — loaded a device
  with category `"ThisCategoryDoesNotExistAnywhere"` into a real
  `DeviceForm`: confirmed `category_combo.currentText()` shows the real
  category (not "Video"), confirmed it's now in
  `custom_categories.json`, and confirmed a no-op `collect()` (no field
  touched) preserves it. **Sanity check**: reproduced the pre-fix
  `load()` logic directly (search + select on hit, nothing on miss, no
  register/reload) against a different unrecognized category — confirmed
  the combo does *not* show the real category, reproducing the bug
  before trusting the fix.
- **Files modified**: `app/library_dialog.py` (`DeviceForm.load()`).

### 31. [done] Loaded numeric fields bypass the range clamps enforced on manual edits
- **File**: `app/library_dialog.py`, `DeviceForm.load()` (~525–535) vs.
  `_make_spin_widget`'s `_set_value`/`_commit` (~350–358, 407–409)
- **Detail**: `load()` populates numeric spin fields (`u_height`,
  `width_mm`, `height_mm`, `depth_mm`, `watts`, `weight_kg`) via direct
  `setValue()`/internal assignment, which does **not** apply the
  `max_val`/`[1,20]` clamp enforced on manual typing or the up/down
  buttons. An out-of-range value already on a `DeviceDefinition` (e.g.
  from unclamped CSV import, see #37) survives untouched through
  load→collect indefinitely as long as that specific field isn't touched.
- **Trigger**: a device with `u_height=999` or `width_mm=9999` (e.g. from
  CSV import) round-trips unchanged through the edit form.
- **Live-reproduced**: yes — both `u_height=999` and `width_mm=9999.0`
  survived load()+collect() unclamped.
- **Severity**: real-but-minor — no crash/field loss, but a validation
  inconsistency letting invalid data persist; an out-of-range `u_height`
  could misbehave in downstream rack-placement math.
- **Fixed 2026-07-28 (Session 13)**. `_make_spin_widget`'s `_set_value()`
  (the function behind every spin widget's public `.setValue()`) now
  applies the exact same `max(0.0, min(float(max_val), v))` clamp (and
  `round(v, decimals)`) that `_commit()` already applies on manual
  typing — fixing it at the shared `.setValue()` implementation, not just
  at `load()`'s call sites, so every current and future caller of
  `.setValue()` is covered (this also applies to Session 11's own
  `height_mm_spin.setValue(0)` call in `_on_rack_native_changed()`,
  though clamping 0 is a no-op there). `DeviceForm.load()`'s U-height
  assignment (`self._u_height_val = device.u_height`, which doesn't go
  through a spin-widget `.setValue()` at all — it's a separate
  hand-rolled construct) now clamps explicitly:
  `max(1, min(20, device.u_height))`, matching `_u_commit()`/`_u_up()`/
  `_u_dn()`'s existing `[1,20]` enforcement.
- **Verification (2026-07-28)**: offscreen script — loaded a device with
  every numeric field far out of range (`u_height=999`, `width_mm=9999`,
  `height_mm=9999`, `depth_mm=9999`, `watts=9999999`, `weight_kg=99999`)
  into a real `DeviceForm`: confirmed every field clamps to its declared
  max (`20`/`482`/`600`/`1200`/`99999`/`9999` respectively), and that a
  subsequent no-op `collect()` reflects the clamped values, not the
  stored out-of-range ones. Confirmed a normal, in-range device's values
  survive `load()` completely unchanged (no regression). **Sanity
  check**: reproduced the pre-fix unclamped `.setValue()`/direct
  `_u_height_val` assignment directly — confirmed an out-of-range value
  is left untouched, reproducing the bug before trusting the fix.
- **Files modified**: `app/library_dialog.py`
  (`_make_spin_widget`'s `_set_value()`; `DeviceForm.load()`'s U-height
  clamp).

### 32. [done] `mm_to_u()` over-allocates a U for exact-multiple heights
- **File**: `app/models.py`, `mm_to_u()` (~43–45),
  `DeviceDefinition.effective_u_height()` (~71–79)
- **Detail**: floating-point division before `math.ceil` causes a
  `height_mm` that's an *exact* multiple of `RACK_U_MM` (44.45) to be
  over-allocated by one full U. Confirmed: `mm_to_u(3*44.45)` → 4 (not 3);
  `mm_to_u(6*44.45)` → 7; `mm_to_u(12*44.45)` → 13. 1,2,4,5,7,8,9,10,11
  all round correctly.
- **Trigger**: import or hand-enter a non-rack-native device with
  `height_mm` exactly `n * 44.45` (e.g. a spec sheet giving "133.35 mm"
  for a 3U-equivalent enclosure).
- **Live-reproduced**: yes.
- **Severity**: likely-real-and-impactful — propagates into
  `RackSlot.u_height`/`tray_u_height()`/`Rack.used_u()`/`free_u()`/
  `next_free_position()`, silently wasting a U of rack space and possibly
  reporting a rack "full" one slot early.
- **Fixed 2026-07-28 (Session 13)**. `mm_to_u()` now subtracts a small
  epsilon (`1e-9`) before `math.ceil()` — the standard fix for exactly
  this float-division-then-ceil over-allocation. `1e-9` is far smaller
  than any real-world measurement precision, so it only ever changes the
  result for heights that land within a hair of an exact U multiple due
  to float error; genuinely non-exact heights round up exactly as before.
- **Verification (2026-07-28)**: confirmed `mm_to_u(3*44.45) == 3`,
  `mm_to_u(6*44.45) == 6`, `mm_to_u(12*44.45) == 12`; confirmed unchanged
  behavior for non-exact heights (`mm_to_u(100) == 3`,
  `mm_to_u(44.45) == 1`, `mm_to_u(1) == 1`). **Sanity check**: reproduced
  the old (no-epsilon) formula directly — confirmed it over-allocates to
  4 and 7 for the 3×/6× cases respectively, reproducing the bug before
  trusting the fix.
- **Files modified**: `app/models.py` (`mm_to_u()`).

### 33. [done] Library/category/project saves are not atomic
- **File**: `app/storage.py`, `save_library()` (~46–48),
  `save_custom_categories()` (~64–66), `save_project()` (~78–114)
- **Detail**: every write opens the destination path directly with `"w"`
  and writes in place — no temp-file + rename. A crash, forced
  termination, or full disk mid-write truncates/corrupts the real
  `library.json`/`custom_categories.json`/`*.rackproj` file.
- **Trigger**: any interruption during a save (OS crash, forced
  app-kill, disk-full).
- **Severity**: likely-real-and-impactful — combined with #34, a
  corrupted file is then silently treated as "empty" rather than flagged.
- **Fixed 2026-07-25 (Session 8)**. Added `storage._atomic_write_json()`:
  writes JSON to `<target>.tmp` in the same directory, `flush()` +
  `os.fsync()`, then `os.replace()` onto the real target (fsync added
  beyond the one-line finding's literal ask — genuinely required for the
  "crash/kill mid-write" guarantee to hold against a real interruption,
  not just a Python-level exception; a single extra line, not a
  redesign). `save_library()`, `save_custom_categories()`, and
  `save_project()` all now go through this helper. `os.replace()` is
  atomic on the same filesystem (same directory here, always), so a
  process kill at any point leaves either the untouched old file or the
  fully-written new one — never a truncated in-between state.
- **Verification (2026-07-25)**: offscreen-Qt script — simulated a
  mid-write kill by writing the `.tmp` sibling directly without ever
  calling `os.replace()`, and confirmed the real target file is
  byte-identical to its pre-save content throughout; confirmed a normal
  save leaves no `.tmp` file behind and produces valid JSON; repeated for
  all three save functions. See `changelog.md` Session 8 for the full
  verification list (shared with #34/#35/#38/#39/#45, one combined
  session).
- **Files modified**: `app/storage.py`.

### 34. [done] Library/category load failures are silently swallowed as empty data
- **File**: `app/storage.py`, `load_library()` (~34–43),
  `load_custom_categories()` (~53–61)
- **Detail**: both use a bare `except Exception: return []` — any
  read/parse error (corrupt JSON, permissions, encoding) silently
  presents an empty library/category list with no warning. If the user
  then edits/saves, `save_library([])` (non-atomic, #33) overwrites the
  real file with an empty one — permanent data loss with zero diagnostic.
- **Trigger**: corrupt/truncate `library.json` (e.g. via #33's mid-write
  crash scenario) and relaunch.
- **Severity**: likely-real-and-impactful.
- **Fixed 2026-07-25 (Session 8), together with #45** (same root cause,
  fixed as one change per the session brief). `load_library()` and
  `load_custom_categories()` now return a `storage.LoadResult` (`.items`,
  `.was_corrupt`, `.backup_path`) instead of a bare list:
  - File doesn't exist → `LoadResult([], was_corrupt=False)` — unchanged,
    legitimate case, no behavior change for a genuine first run.
  - File exists but fails to parse → the file is quarantined via
    `storage._quarantine_corrupt_file()` (renamed to
    `<name>.corrupt-<timestamp>.json` in the same directory — **never
    deleted**, so the original bytes stay recoverable), a warning is
    appended to `%APPDATA%\RackDesigner\crash.log` via
    `storage._log_warning()` (reuses the exact log file/format
    convention `main.py`'s `sys.excepthook` already established, per the
    task's "reuse the crash.log mechanism" instruction), and
    `LoadResult([], was_corrupt=True, backup_path=...)` is returned.
  - `preloaded_library.seed_library_if_empty()` (#45) is the one caller
    that acts on `was_corrupt`; all other call sites (`DesignerSection`,
    `LibrarySection`, `models.get_categories()`, `storage.
    add_custom_category()`, `storage.import_library_csv()`) were updated
    to read `.items` and otherwise behave exactly as before — this is a
    breaking return-type change to `load_library()`/
    `load_custom_categories()`, necessary for the sentinel to exist at
    all, but every call site in the live tree was updated in the same
    change (7 call sites total: `app/main_window.py` ×3,
    `app/models.py` ×1, `app/storage.py` ×2 internal, plus
    `app/preloaded_library.py`).
- **Verification (2026-07-25)**: offscreen-Qt script — missing file →
  `was_corrupt=False`, empty items (unchanged legitimate case); corrupt
  file → `was_corrupt=True`, original bytes preserved and found at
  `backup_path`, original path no longer exists (renamed not copied),
  warning present in `crash.log`; repeated for `custom_categories.json`.
  Also ran the real app twice end-to-end (`main.py`'s actual startup
  sequence, offscreen) — once with a fresh `%APPDATA%` (silent seed, no
  dialog) and once with a pre-corrupted `library.json` (reset dialog
  shown, correct backup path in the message) — see #45 and
  `changelog.md` Session 8.
- **Files modified**: `app/storage.py`, `app/preloaded_library.py`
  (see #45), `app/main_window.py`, `app/models.py`.

### 35. [done] CSV import has no encoding fallback — non-UTF-8 CSV aborts entirely
- **File**: `app/storage.py`, `import_library_csv()` (~148–253)
- **Detail**: hardcodes `encoding="utf-8-sig"` with no exception handling
  around the file read. A CSV saved in Windows-1252/"ANSI" (Excel's
  default export encoding — plausible for this Italian team's
  accented-character device names/descriptions) raises an unhandled
  `UnicodeDecodeError` on the very first read, aborting the whole import
  with zero devices imported and no partial recovery — one bad byte
  anywhere kills the entire file.
- **Trigger**: import a CSV saved by Excel's default "CSV (Comma
  delimited)" option on a machine with a non-UTF-8 default codepage.
- **Live-reproduced**: yes.
- **Severity**: likely-real-and-impactful — the app's global
  `sys.excepthook` catches it (logs + shows an error dialog rather than
  silently crashing) but the import itself gives no actionable "why."
- **Fixed 2026-07-25 (Session 8)**. Added
  `storage._read_text_with_encoding_fallback()`: reads the file as raw
  bytes once, tries decoding as `utf-8-sig` first, falls back to
  `cp1252` on `UnicodeDecodeError`, and raises a clear `ValueError`
  ("Couldn't read '<name>' as UTF-8 or Windows-1252...") if neither
  decodes — instead of a raw `UnicodeDecodeError` propagating from
  mid-way through `csv.DictReader` iteration. `import_library_csv()` now
  decodes the whole file up front via this helper and feeds the decoded
  text to `csv.DictReader` through an `io.StringIO`, rather than
  iterating an open file handle with a single hardcoded encoding. The
  existing call site (`LibrarySection._import_dialog()`,
  `app/main_window.py`) already wraps the call in `try/except Exception
  as e: MsgBox.error(self, "Import error", str(e))` — no change needed
  there; the clearer message now flows straight through.
- **Verification (2026-07-25)**: offscreen-Qt script — a CSV with
  accented characters (à/è/é/ù/ città) saved as `utf-8-sig` imports
  correctly (regression check); the same content saved as raw `cp1252`
  bytes now imports correctly via the fallback with correct character
  decoding (previously would have raised `UnicodeDecodeError`); directly
  exercised the "both encodings fail" path (forced) and confirmed the
  `ValueError` message names both encodings tried.
- **Files modified**: `app/storage.py`.

### 36. [done] CSV import category normalization doesn't lowercase the remainder
- **File**: `app/storage.py`, `import_library_csv()` category
  normalization (~202–210): `category = category[0].upper() + category[1:]`
- **Detail**: only uppercases the first character, never lowercases the
  rest — an all-caps/mixed-case value (e.g. `"AUDIO"` from an
  Excel-exported CSV) fails the match against the built-in `"Audio"` and
  gets registered as a brand-new, permanent duplicate custom category.
- **Live-reproduced**: yes — importing `Category=AUDIO` yielded
  `devices[0].category == "AUDIO"` and `new_cats == ["AUDIO"]`.
- **Severity**: real-but-minor.
- **Fixed 2026-07-28 (Session 13)**. `import_library_csv()` now checks
  the (stripped) imported category **case-insensitively** against
  `known_cats` first — `next((c for c in known_cats if c.lower() ==
  category.lower()), None)`. If a case-insensitive match exists (e.g.
  `"AUDIO"` vs. the already-known `"Audio"`), the category is set to the
  *existing* category's real casing and nothing new is registered. Only
  when there's genuinely no case-insensitive match does it normalize to
  Title Case (`category[0].upper() + category[1:].lower()`, fixing the
  original "only uppercases the first char" gap in the same change) and
  register it as new. `known_cats` (already loaded from
  `DEFAULT_CATEGORIES` + `load_custom_categories()`) is exactly the
  "known set" the task described checking against.
- **Verification (2026-07-28)**: offscreen script — a CSV with rows
  `Category=AUDIO` and `Category=WIRELESS MIC`: confirmed the first maps
  onto the existing `"Audio"` (not a new `"AUDIO"` category, and not
  reported in `new_cats`), and the second registers as `"Wireless mic"`
  (Title Case), reported in `new_cats` and present in
  `custom_categories.json` afterward. **Sanity check**: reproduced the
  old first-letter-only normalization directly against `"AUDIO"` —
  confirmed it stays `"AUDIO"` (the near-duplicate), reproducing the bug
  before trusting the fix.
- **Files modified**: `app/storage.py` (`import_library_csv()`'s
  category normalization).

### 37. [done] CSV integer parsing uses inconsistent (banker's) rounding
- **File**: `app/storage.py`, `_parse_int()` (~141–145)
- **Detail**: uses Python's `round()` (round-half-to-even) rather than
  ceiling, inconsistent with `mm_to_u()`'s ceiling behavior elsewhere in
  the same codebase. Confirmed: `_parse_int("2.5")` → 2, `_parse_int("4.5")`
  → 4 (rounds down); `_parse_int("3.5")` → 4, `_parse_int("1.5")` → 2
  (rounds up) — direction depends on parity.
- **Trigger**: CSV `Height (U)` value of `"2.5"` silently becomes 2U
  instead of the expected round-up to 3U.
- **Live-reproduced**: yes.
- **Severity**: real-but-minor.
- **Investigated first, per the session brief.** Grepped every call site
  of `_parse_int()` in the live tree (not just `storage.py`): there is
  exactly one, `import_library_csv()`'s `Height (U)` column
  (`u_val = _parse_int(col("Height (U)", "Height U", "U"))`). No other
  use exists that ceiling would be the wrong choice for, so a blanket
  change was safe — no need to special-case or stop and report back.
- **Fixed 2026-07-28 (Session 13)**. `_parse_int()` now returns
  `max(1, math.ceil(f))` instead of `max(1, int(round(f)))` — ceiling,
  matching `mm_to_u()`'s philosophy elsewhere in this module and physical
  reality (a device needing 2.5U of rack space genuinely needs 3U).
  Added `import math` to `storage.py` (not previously imported).
- **Verification (2026-07-28)**: confirmed `_parse_int("2.5") == 3`,
  `_parse_int("4.5") == 5`, `_parse_int("3.5") == 4`,
  `_parse_int("1.5") == 2` — no longer parity-dependent; confirmed whole
  numbers and empty strings are unaffected. Imported a real CSV row with
  `Height (U)=2.5` through `import_library_csv()` — confirmed
  `u_height == 3`. **Sanity check**: reproduced the old `round()`-based
  parsing directly — confirmed `"2.5"` gives `2`, not `3`, reproducing
  the bug before trusting the fix.
- **Files modified**: `app/storage.py` (`_parse_int()`; added `import
  math`).

### 38. [done] Corrupted project file is fully unopenable with no partial recovery
- **File**: `app/storage.py`, `load_project()` (~117–120)
- **Detail**: unlike `load_library()`/`load_custom_categories()` (which
  swallow everything, #34), `load_project()` has no exception handling at
  all. A corrupted/`null` entry in a rack's `slots` list (e.g. from a
  partial write per #33, or manual edit) causes `RackSlot.from_dict()` to
  call `.get()` on `None`, raising an unhandled `AttributeError` that
  aborts the whole load — the project becomes fully unopenable rather
  than degrading gracefully (e.g. skipping the bad slot).
- **Live-reproduced**: yes.
- **Severity**: real-but-minor — caught by the app's global exception
  handler (no silent crash), but zero recovery path for that project
  file.
- **Fixed 2026-07-25 (Session 8)**. `load_project()` now returns
  `(project, skip_warnings)` instead of a bare `Project`. Behavior split
  by failure level, per the session brief:
  - **Top-level JSON invalid** (the file itself isn't parseable, or
    `data` isn't dict-shaped) → the exception propagates unchanged, the
    file is **not** touched/renamed (deliberately different from #34's
    library-file quarantine — this is the user's own project file, not
    one the app owns the format of). Both existing call sites
    (`ProjectSection._open()`/`._open_recent()`, `app/main_window.py`)
    already wrap this in `try/except Exception as e: MsgBox.error(...)`,
    so this already "fails cleanly" with no code change needed there.
  - **One rack's structure unreadable** (the rack entry itself isn't
    dict-shaped) → that rack is skipped, a message is added to
    `skip_warnings`, the rest of the project keeps loading.
  - **One slot within an otherwise-valid rack unparseable** (`null` in
    `slots`, or anything else `RackSlot.from_dict()` raises on) → that
    slot alone is skipped, the rack keeps its remaining valid slots, and
    a `"N slot(s) in '<rack name>' could not be loaded and were
    skipped."` message is added to `skip_warnings`.
  - Both call sites now unpack the tuple and show
    `MsgBox.warn(self, "Project loaded with issues", "\n".join(skip_warnings))`
    when non-empty, in addition to loading the project normally.
- **Verification (2026-07-25)**: offscreen-Qt script — a rack with one
  `null` slot and one valid slot: loads successfully, valid slot
  survives, exactly one skip-warning naming the right rack and count.
  Fully-invalid top-level JSON: raises, file confirmed byte-identical
  afterward (untouched). Also driven through the **real**
  `ProjectSection._open_recent()` on a real `MainWindow` (not a direct
  `storage.load_project()` call) — confirmed the actual `MsgBox.warn`
  call fires with the correct rack name/count and the project's
  surviving slot is reachable through `window.proj_section.project`.
- **Files modified**: `app/storage.py`, `app/main_window.py`
  (`ProjectSection._open()`, `._open_recent()`).

### 39. [done] `save_project()` mutates the caller's in-memory project as a save side effect
- **File**: `app/storage.py`, `save_project()` (~78–114)
- **Detail**: when `filepath is None` and a project with the same `name`
  already exists on disk, the function mutates
  `project.name = f"{base_name} ({counter})"` **in place** before ever
  writing to disk — silently renaming the in-memory model the caller
  (e.g. `MainWindow`'s currently-open project) still holds a reference
  to. The dedup check also compares against a `name` field pulled from
  arbitrary `.rackproj` file *contents*, not filenames, so an unrelated
  file that happens to share the same internal `name` can trigger this.
- **Severity**: needs-live-reproduction-to-confirm — confirmed via code
  reading; would need the UI layer to confirm user-visible impact
  (e.g. does the displayed project title change unexpectedly after a
  routine Save?).
- **Investigated first, per the session brief's "stop and report back"
  instruction if the call site turns out to depend on the mutation.** It
  does: `MainWindow._save()` (`app/main_window.py`) has a comment
  reading (translated) "re-sync the form if save_project modified
  project.name (suffix)" — it calls `storage.save_project(...)` then
  immediately re-reads `project.name` back into the Project-tab form via
  `self.proj_section.load_project(project, filepath)`. This is exactly
  the "your open project's displayed name might legitimately need to
  update after a Save-As-new-name" case the brief warned about — so the
  fix keeps that behavior, just makes the mutation explicit at the call
  site instead of a hidden side effect inside `storage.py`.
- **Fixed 2026-07-25 (Session 8)**. `save_project()` now computes
  `resolved_name` as a local variable (never assigns `project.name`),
  writes `resolved_name` into the saved file's JSON (`data["name"] =
  resolved_name`, so the on-disk dedup behavior is unchanged), and
  returns `(filepath, resolved_name)` instead of just `filepath`.
  `MainWindow._save()` (the only call site) now does
  `project.name = resolved_name` itself, explicitly, right after the
  call — same end result as before (the open project's displayed name
  still updates after a dedup), but the mutation is now visible at the
  call site instead of buried in `storage.py`, and `save_project()` no
  longer has a side effect on its input beyond what it returns.
- **Verification (2026-07-25)**: offscreen-Qt script — saved a
  `Project(name="Dedup Target")` once, then created a **second**,
  separate `Project` object with the same name and called
  `save_project()` directly: confirmed the second object's `.name` was
  **not** mutated by the call, confirmed the returned `resolved_name` was
  `"Dedup Target (2)"`, and confirmed the file on disk contains that
  resolved name. Also drove the real `MainWindow._save()` path on a real
  `MainWindow`/`ProjectSection` (name collision pre-seeded on disk):
  confirmed the live in-memory project's `.name`, the Project-tab form
  field's text, and the saved file all correctly show `"Collide Me (2)"`
  afterward — i.e. the explicit call-site mutation reproduces the old
  auto-mutating behavior's user-visible effect exactly.
- **Files modified**: `app/storage.py`, `app/main_window.py`
  (`MainWindow._save()`).

### 40. [done] `Rack` bay-scoped helpers don't validate the `bay` argument
- **File**: `app/models.py`, `Rack.is_slot_occupied()` /
  `next_free_position()` / `slot_at()` (~250–276), `Rack.free_u()` (~241–242)
- **Detail**: none of the bay-scoped helpers validate `bay` is within
  `[0, self.bays)`. An out-of-range bay (e.g. from corrupted project data
  — `bays=1` but a slot's `bay=2`) is silently treated as "no slots in
  this bay" rather than flagged, while `free_u()` (`u_size * bays -
  used_u()`) still counts such an orphaned slot's U against total
  capacity — capacity accounting and actual placement can disagree.
- **Trigger**: requires already-corrupted/out-of-range bay data.
- **Live-reproduced**: no (static).
- **Severity**: real-but-minor.
- **Investigated first, per the session brief's "consider normalizing
  once in `Rack.from_dict()` vs. patching every helper" instruction.**
  The only realistic path to an out-of-range `bay` is a corrupted/
  hand-edited/foreign `.rackproj` file loaded via `Rack.from_dict()` —
  nothing in the live UI can produce one (every place that sets
  `RackSlot.bay` derives it from `_point_to_bay_u()`, already clamped to
  `[0, bays)`, and `EditRackDialog` has no bays-editing field at all, so
  a rack's `bays` can't even be shrunk below an existing slot's bay
  through the UI today). Given that, normalizing once at the data's entry
  point is the cleaner fix: it corrects the data itself (so every
  downstream reader — the four helpers named here, but also anything
  else that might iterate `rack.slots` in the future — sees consistent
  data by construction) rather than adding redundant, easy-to-forget
  bounds-checks to each individual helper. This also matches the
  project's existing "validate at the boundary, trust internal
  invariants elsewhere" convention (e.g. `load_project()`'s per-slot
  skip-on-corruption handling, Session 8).
- **Fixed 2026-07-28 (Session 13)**. `Rack.from_dict()` now clamps every
  loaded slot's `bay` to `[0, bays-1]`
  (`s.bay = max(0, min(bays - 1, s.bay))`) immediately after constructing
  the slot list, before the `Rack` is returned. `is_slot_occupied()`/
  `next_free_position()`/`slot_at()`/`free_u()` themselves are unchanged
  — they were already correct given valid input; the bug was that input
  wasn't guaranteed valid.
- **Verification (2026-07-28)**: offscreen script — a `bays=1` rack dict
  with one slot's `bay=2`: confirmed `Rack.from_dict()` clamps it to `0`,
  and that `is_slot_occupied()`/`free_u()`/`used_u()` now agree (the slot
  is visible to occupancy checks in bay 0, and free_u() correctly
  reflects 1U used). Confirmed a rack with an already-valid bay (e.g. bay
  2 of a real `bays=3` rack) is left unchanged (no regression). **Sanity
  check**: confirmed that without clamping, a slot with `bay=2` never
  matches the only valid bay argument (`0`) a `bays=1` rack's helpers
  would ever be called with — reproducing the occupancy/`free_u()`
  disagreement described in the finding before trusting the fix.
- **Files modified**: `app/models.py` (`Rack.from_dict()`).

### 41. [done] Seed library registers "Lighting" as a redundant custom category
- **File**: `app/preloaded_library.py`, `_EXTRA_CATEGORIES = ["Lighting"]`
  (~1573), consumed by `seed_library_if_empty()` (~1576–1583)
- **Detail**: the comment says this holds "custom categories not in
  DEFAULT_CATEGORIES," but `"Lighting"` is already in
  `models.DEFAULT_CATEGORIES`. First run calls
  `storage.add_custom_category("Lighting")`, writing a redundant entry
  into `custom_categories.json` on every fresh install.
- **Live-reproduced**: n/a (logic traced directly; effect is
  low-visibility since `get_categories()` dedupes by name and there's no
  UI to list/delete individual custom categories).
- **Severity**: real-but-minor.
- **Fixed 2026-07-29 (Session 15)**. Checked first: `_EXTRA_CATEGORIES`
  contained only `"Lighting"`, nothing else — emptied it to `[]` rather
  than removing just the one entry, per the task's "or empty the list
  entirely if nothing else is in it" instruction. Deliberately scoped to
  fresh installs only — existing installs that already have a redundant
  `"Lighting"` entry in their `custom_categories.json` are not
  retroactively cleaned up (explicitly out of scope).
- **Verification (2026-07-29)**: offscreen-Qt script — fresh throwaway
  `%APPDATA%`, ran the real `seed_library_if_empty()`: confirmed
  `load_custom_categories().items == []` afterward (no `"Lighting"`
  entry written), confirmed the library still seeds all 119 devices, and
  confirmed a real `MainWindow()` constructs and shows with no exception.
- **Files modified**: `app/preloaded_library.py` (`_EXTRA_CATEGORIES`).

### 42. [done] Preloaded "Disguise GX 3" has a copy-pasted model string
- **File**: `app/preloaded_library.py`, `name="Disguise GX 3"` (~39–51)
  vs. `name="Disguise GX 3+"` (~52–64)
- **Detail**: "Disguise GX 3" has `model="GX 3+"`, identical to the
  actual GX 3+ entry, despite differing specs (watts 700 vs 1089, weight
  14.4kg vs 19.8kg, width 445mm vs 440mm).
- **Severity**: real-but-minor — a model-keyed lookup/export/dedup
  feature would conflate the two; current in-app dedup keys on
  `(name, category)`, not model, so no active breakage today.
- **Fixed 2026-07-29 (Session 15)**. Changed `model="GX 3+"` →
  `model="GX 3"`, matching the device's own name/generation instead of
  its sibling's. **Not verified against an actual Disguise vendor spec
  sheet** — this is an internal-consistency correction (the model string
  should describe the device's own generation, not literally duplicate a
  different device's), per the task's explicit framing.
- **Files modified**: `app/preloaded_library.py`.

### 43. [done] Preloaded "Barco E2" has a copy-pasted model string
- **File**: `app/preloaded_library.py`, `name="Barco E2"` (~208–220) vs.
  `name="Barco E2 Gen2"` (~221–233)
- **Detail**: same class of bug as #42 — first-gen "Barco E2" has
  `model="E2 Gen 2"`, identical to the actual Gen2 entry, despite
  differing watts (826 vs 1100).
- **Severity**: real-but-minor.
- **Fixed 2026-07-29 (Session 15)**. Changed `model="E2 Gen 2"` →
  `model="E2"`, matching the first-gen device's own name instead of its
  Gen2 sibling's. **Not verified against an actual Barco vendor spec
  sheet** — same internal-consistency-only caveat as #42.
- **Files modified**: `app/preloaded_library.py`.

### 44. [done] Two preloaded devices have physically implausible `depth_mm`
- **File**: `app/preloaded_library.py`, `name="Blackmagic MultiView 16"`
  (~1210–1222, `depth_mm=15.4`) and `name="UPS 5P 1150"` (~970–981,
  `depth_mm=43.2`)
- **Detail**: likely decimal-point/digit transcription errors. Blackmagic
  MultiView 16's `depth_mm=15.4` is implausible for a 1U chassis (its
  sibling MultiView 4 has depth 170.0mm). UPS 5P 1150's `depth_mm=43.2`
  vs. its Gen2 sibling's `depth_mm=438.0` (same width) is a ~10x
  discrepancy.
- **Severity**: real-but-minor — internally inconsistent outliers
  confirmed by cross-comparison with sibling entries; would need the
  original vendor spec sheet to confirm the "correct" value.
- **Fixed 2026-07-29 (Session 15)**. Blackmagic MultiView 16's
  `depth_mm` changed `15.4` → `170.0` (its sibling MultiView 4's depth,
  used as the best available estimate). UPS 5P 1150's `depth_mm` changed
  `43.2` → `438.0` (matching its Gen2 sibling, which shares the same
  `width_mm=438.0` — the digit-pattern match between `43.2` and `438.0`
  strongly suggests a dropped/misplaced digit in the original entry).
  **Both are best-estimate corrections based on sibling-device
  cross-comparison, not verified against actual vendor spec sheets** —
  per the task's explicit framing.
- **Verification (2026-07-29)**: offscreen-Qt script — confirmed both
  corrected values load correctly off a real seeded library
  (`Blackmagic MultiView 16`.depth_mm == 170.0,
  `UPS 5P 1150`.depth_mm == 438.0) and a real `MainWindow()` still
  constructs/shows with no exception.
- **Files modified**: `app/preloaded_library.py`.

### 45. [done] Seeding logic conflates "library never existed" with "library file is corrupt"
- **File**: `app/preloaded_library.py`, `seed_library_if_empty()`
  (~1576–1583), calling `app/storage.py`'s `load_library()` (see #34)
- **Detail**: `seed_library_if_empty()`'s docstring treats "library is
  empty" as one case, but `storage.load_library()` returns `[]` for three
  different situations: file doesn't exist, file is a valid empty array,
  or file is corrupt/unparseable (swallowed by #34's bare except). Case 3
  means a corrupted-but-previously-populated `library.json` triggers
  silent, unannounced reseeding with the 119 preloaded devices, discarding
  whatever was actually in the file with no warning.
- **Severity**: needs-live-reproduction-to-confirm — logic is clear from
  code inspection; not simulated end-to-end (mid-write crash + relaunch).
  Same root cause as #34.
- **Fixed 2026-07-25 (Session 8), together with #34** (one change, per
  the session brief — #34 built the `was_corrupt`/`backup_path` sentinel
  in `storage.py`, this item is `seed_library_if_empty()` actually using
  it). Reseeding is no longer silent when the cause is corruption:
  `seed_library_if_empty()` now calls both `storage.load_library()` and
  `storage.load_custom_categories()` every run (previously only checked
  the library), and returns a dict —
  `{"library_corrupt", "library_backup", "categories_corrupt",
  "categories_backup"}` — describing what it found. It still reseeds
  silently on a genuine first run (both flags `False`), matching the
  original behavior exactly. On corruption it still seeds (the app must
  stay usable) but now flags it in the returned dict. `main.py`'s
  `main()` calls this **after** `MainWindow()` is constructed and shown
  (unchanged ordering — deliberately not touched, see #62, a separate,
  not-yet-approved finding about exceptions during seeding happening
  *before* the window exists) and, if either flag is set, shows **one**
  combined `MsgBox.info` via the new `_notify_if_library_was_reset()`
  helper: "Your device library / custom categories file appeared to be
  corrupted and has been reset to defaults. A backup of the original
  file was saved to: <path(s)>" — one dialog even if both files were
  corrupt in the same run, per the session brief.
- **Verification (2026-07-25)**: offscreen-Qt script — genuine first run
  (no `library.json` at all) → `library_corrupt=False`, no dialog;
  library corrupted → `library_corrupt=True`, library reseeded with all
  119 preloaded devices, a second immediate run no longer flags
  corruption (already-valid file); custom_categories.json corrupted
  independently → flagged the same way. Directly exercised
  `_notify_if_library_was_reset()` with both flags set → confirmed a
  single dialog mentioning both files and both backup paths, and
  confirmed no dialog at all when neither flag is set. Also ran the
  **real** `main.py` startup sequence twice end-to-end, offscreen, each
  in a fresh throwaway `%APPDATA%`: once with a genuinely empty appdata
  (silent seed, `MainWindow` shown, zero dialogs) and once with a
  pre-corrupted `library.json` (seed happens, `MainWindow` shown, then
  exactly one "Library reset" dialog with the correct backup path in the
  message) — confirms the fix holds through the actual startup
  sequence, not just at the function level.
- **Files modified**: `app/preloaded_library.py`
  (`seed_library_if_empty()`), `main.py` (new
  `_notify_if_library_was_reset()`, call site after `window.show()`).

### 46. [done] Preloaded-library device/doc count mismatch (informational)
- **File**: `app/preloaded_library.py`
- **Detail**: some project docs describe a "20-device" preloaded library;
  the file actually contains 119 `DeviceDefinition` entries, none with
  `image_front`/`image_rear` populated. Not a functional bug (`""` is the
  normal no-image sentinel elsewhere in the codebase) — documentation
  accuracy only, flagged per the audit brief.
- **Severity**: real-but-minor (doc accuracy).
- **Fixed 2026-07-29 (Session 15), documentation-only.** Grepped
  `docs/*.md` for `"20 device"`/`"20-device"` (case-insensitive) — found
  it in three places, all corrected to the confirmed real count (119,
  reconfirmed via a fresh grep-count of `DeviceDefinition(` in the live
  `preloaded_library.py`): `folder_structure.md`'s module comment,
  `design.md`'s module-map table row, and `status.md`'s "What works"
  summary (which also got a short pointer back to this item, since it's
  the one place the correction itself is explained rather than just
  the number being swapped).
- **Files modified**: `docs/folder_structure.md`, `docs/design.md`,
  `docs/status.md`. No code changes (this item is documentation-only).

### 47. [done] Pasting/cross-rack-dragging a tray uses the wrong height, causing overlap
- **File**: `app/rack_canvas.py`, `_kb_paste()` (~558–559) and
  `dropEvent()` cross-rack branch (~311–312):
  `u_height = snap.get("u_height", 1) if snap else data.get("u_height", 1)`
- **Detail**: for a tray-type source slot, `device_snapshot` is always
  `{}` (falsy), so this falls back to `data.get("u_height", 1)` — but
  `RackSlot.to_dict()` never has a top-level `"u_height"` key, so the
  value used for placement/collision math is always `1`, regardless of
  the tray's real height (`tray_u_height()`, which can be 2U+).
- **Trigger**: copy/cut a tray slot whose tallest device needs ≥2U, paste
  (or cross-rack-drag) it into a rack with only a 1U-tall gap near other
  occupied slots.
- **Live-reproduced**: yes — pasting a 3U-tall tray produced a slot that
  geometrically overlaps an existing 1U slot in the same bay.
- **Severity**: likely-real-and-impactful — silent data corruption (two
  slots occupying the same U range), also corrupts rendering and any
  U-based math/exports downstream.
- **Fixed 2026-07-28 (Session 10)**. Both call sites now build the
  `RackSlot` first (`RackSlot.from_dict(data)` /
  `RackSlot.from_dict(slot_data)`) and read `u_height` off that instance's
  existing `RackSlot.u_height` property, instead of manually re-deriving it
  from `device_snapshot`/top-level dict keys. `RackSlot.u_height` already
  branches correctly on `is_tray` (delegating to `tray_u_height()`), so this
  reuses existing, correct logic rather than adding new logic — the
  top-level `"u_height"` fallback that always evaluated to `1` for a tray is
  gone entirely. `_kb_paste()`'s `new_slot` and `dropEvent()`'s `new_slot`
  are each now constructed once, reused for both the height lookup and the
  final `rack.slots.append(...)` (previously `dropEvent()` and `_kb_paste()`
  built the `RackSlot` a second, separate time after placement math).
- **Verification (2026-07-28)**: offscreen-Qt script — pasted a 3U-tall
  tray (two non-rack-native devices, tallest needing 3U) next to a 1U
  "blocker" slot positioned so a correct 3U-height placement must route
  around it while an (incorrect) 1U-height placement would not: confirmed
  the pasted slot reports `u_height == 3` and overlaps neither the blocker
  nor the original tray. Directly confirmed
  `RackSlot.from_dict(tray.to_dict()).u_height == 3` (the exact expression
  now used in `dropEvent()`'s cross-rack branch). **Sanity check**:
  reproduced the pre-fix value by evaluating the old
  `snap.get(...)/data.get(...)` fallback expression directly against the
  same tray data — confirmed it yields `1`, matching the bug description,
  before trusting the fix.
- **Files modified**: `app/rack_canvas.py` (`dropEvent()`'s cross-rack
  branch, `_kb_paste()`).

### 48. [done] Context-menu "Paste here" ignores the right-clicked cell, uses stale selection
- **File**: `app/rack_canvas.py`, `_context_menu()` (~894–924)
- **Detail**: computes `b, u = self._point_to_bay_u(pos)` for the
  right-clicked cell and uses it correctly for "Insert blank panel," but
  "Paste here" never forwards `b`/`u` into `_selected_bay`/`_selected_u`
  before calling `self._kb_paste()`, which reads whatever was
  selected/clicked previously.
- **Trigger**: select/click one cell, then right-click a different empty
  cell and choose "Paste here."
- **Live-reproduced**: yes — right-clicked at U15 with stale selection at
  U5; paste landed at U6 (near the stale U5), not U15.
- **Severity**: likely-real-and-impactful — visible, easily-triggered
  menu action silently does something other than what it says.
- **Fixed 2026-07-28 (Session 10)**. The "Paste here" branch of
  `_context_menu()` now sets `self._selected_slot = None`,
  `self._selected_u = u`, `self._selected_bay = b` (the right-clicked
  cell's coordinates, already computed a few lines above for "Insert blank
  panel") immediately before calling `self._kb_paste()`. Clearing
  `_selected_slot` as well as setting `_selected_u`/`_selected_bay` was
  necessary, not just the two coordinates named in the finding: `_kb_paste()`
  prefers a non-`None` `_selected_slot` over `_selected_u`/`_selected_bay`
  when choosing where to paste, so if the stale selection was an occupied
  slot (not just an empty cell) rather than clearing it first, `_kb_paste()`
  would still have targeted next to that stale slot regardless of the
  newly-set `u`/`b`.
- **Verification (2026-07-28)**: offscreen-Qt script — pre-selected a slot
  at U5, right-clicked an empty cell at U15, invoked `_context_menu()` with
  `QMenu.exec` monkeypatched to auto-select the "Paste here" action:
  confirmed the pasted slot lands at U15, not near the stale U5 selection.
  **Sanity check**: called `_kb_paste()` directly without the forwarding
  (the exact pre-fix call sequence) against the same stale-selection setup
  — confirmed the paste lands near U5 (not U15), reproducing the bug
  before trusting the fix.
- **Files modified**: `app/rack_canvas.py` (`_context_menu()`).

### 49. [done] Duplicate action ignores the source's own bay
- **File**: `app/rack_canvas.py`, `_kb_duplicate()` (~610–621),
  `_kb_paste()`'s target-resolution logic (~562–579)
- **Detail**: `_kb_duplicate` sets the clipboard to the selected slot,
  then blanks `_selected_u`/`_selected_bay` to `-1` before calling
  `_kb_paste()`. Inside `_kb_paste`, this makes `selected_is_source`
  always `True` (skipping the "paste after selected slot" branch) while
  the blanked selection also skips the `elif` branch — duplication always
  falls through to the last-resort `bay=0, target_u=1` search.
- **Trigger**: select a device in bay 2 or 3 of a multi-bay rack (with
  bay 0 having free space), press Ctrl+D or use "Duplicate."
- **Live-reproduced**: yes — source in bay 2, duplicate landed in bay 1
  (first bay with free space from a bay-0 scan), ignoring the source bay
  entirely.
- **Severity**: likely-real-and-impactful.
- **Fixed 2026-07-28 (Session 10)**. Instead of blanking
  `_selected_u`/`_selected_bay` to `-1`, `_kb_duplicate()` now sets them to
  `source.position_u + source.u_height` / `source.bay` (right after the
  source, in its own bay) before calling `_kb_paste()`. `_selected_slot`
  still equals the source (unchanged — `selected_is_source` is still
  `True`, so `_kb_paste()`'s "paste after a *different* selected slot"
  branch is still correctly skipped), but the `elif self._selected_u > 0
  and self._selected_bay >= 0:` branch — previously unreachable here
  because both were blanked — now fires with the source's own bay,
  and `_kb_paste()`'s existing `is_slot_occupied`/`_free_near` occupancy
  logic (unchanged) finds the actual nearest free position starting from
  there. `_kb_paste()`'s own last-resort "scan every bay from bay 0"
  fallback (unchanged, already existed) still applies if — and only if —
  no room is found in the source's own bay, satisfying the brief's
  "falling back to the existing bay=0 search only if there's no room
  there" without any new code for that part.
- **Verification (2026-07-28)**: offscreen-Qt script — 3-bay rack, source
  slot in bay 2, `Ctrl+D`-equivalent `_kb_duplicate()` call: confirmed
  exactly one new slot, in bay 2 (not bay 0/1). Also re-run against a real
  `MainWindow`/`RackCanvas` with a real `QTest.keyClick(canvas, Key_D,
  ControlModifier)` (not a direct method call) — same result. **Sanity
  check**: reproduced the pre-fix behavior directly (blank
  `_selected_u`/`_selected_bay` to `-1` the way the old code did, then call
  `_kb_paste()`) against the same bay-2 source — confirmed the duplicate
  falls through to bay 0, reproducing the bug before trusting the fix.
- **Files modified**: `app/rack_canvas.py` (`_kb_duplicate()`).

### 50. [done] Drag state doesn't check which mouse button was released
- **File**: `app/rack_canvas.py`, `mouseReleaseEvent()` (~493–506)
- **Detail**: only checks `if self._drag_slot:`, never `event.button()`.
  Any button-release event during an in-progress left-button drag (e.g. a
  chord: right-press+release while left is still held) clears
  `_drag_slot`/`_drag_moved` and ends the drag prematurely.
- **Trigger**: left-press on a slot, move (drag begins), then a
  right-button press+release while left is still down.
- **Live-reproduced**: yes (synthetic `QMouseEvent`s) — after the
  right-button release, `_drag_slot` became `None` and a subsequent
  left-button move was silently ignored, leaving the slot stuck.
- **Severity**: real-but-minor — needs an unusual input sequence, but a
  genuine state-consistency bug.
- **Fixed 2026-07-29 (Session 17)**. `mouseReleaseEvent()`'s guard is now
  `if self._drag_slot and event.button() == Qt.MouseButton.LeftButton:`
  — a drag (which can only ever start on a left-button press, per
  `mousePressEvent()`) is now only ever cleared by the matching
  left-button release; a right-button release/click during an
  in-progress left-drag is ignored by this handler entirely.
- **Verification (2026-07-29)**: offscreen-Qt script — started a
  synthetic in-progress drag, dispatched a synthetic right-button
  `mouseReleaseEvent`: confirmed `_drag_slot` is unaffected (still set);
  a subsequent left-button release then correctly clears it (regression
  check). **Sanity check**: reproduced the pre-fix unconditional
  `if self._drag_slot:` body directly against the same in-progress-drag
  state — confirmed it clears `_drag_slot` regardless of button,
  reproducing the bug before trusting the fix.
- **Files modified**: `app/rack_canvas.py` (`mouseReleaseEvent()`).

### 51. [done] Cross-rack drop onto an existing tray never merges
- **File**: `app/rack_canvas.py`, `dropEvent()` cross-rack
  "application/x-rackslot" branch (~303–335)
- **Detail**: unlike the library-device-drop branch just below it (which
  calls `_can_add_to_tray`/`_add_to_tray`), the cross-rack slot-drop
  branch never attempts a tray merge — it only checks
  `is_slot_occupied`/`_free_near` and appends a new slot. Dropping a
  non-rack-native device (dragged from another rack/canvas) onto an
  existing tray with room is treated as "occupied."
- **Trigger**: cross-rack-drag a narrow non-rack-native device onto a
  target rack that's otherwise full except for spare width in an
  existing tray.
- **Live-reproduced**: yes (synthetic `QDropEvent`) — rejected with "Not
  enough free space in this rack" despite 382mm of 482mm free in the
  target tray.
- **Severity**: likely-real-and-impactful — a documented data-model
  feature (trays) silently doesn't work for this input path, with an
  incorrect user-facing error.
- **Fixed 2026-07-29 (Session 14)**. Before falling through to the
  existing occupied/free-space check, the cross-rack branch now attempts
  the same tray-merge logic the library-device-drop branch already uses:
  if the dropped slot is a single device (not itself a tray) and its
  snapshot is non-rack-native with a `width_mm`, it builds a
  `DeviceDefinition` from that snapshot, looks up whatever slot currently
  occupies the drop target (`self.rack.slot_at(target_u, bay)`), and — if
  that slot exists and `_can_add_to_tray()` says it fits — merges via
  `_add_to_tray()` and returns, exactly mirroring the library-drop
  branch's own merge block (same undo push, same post-merge
  signals/repaint, no new behavior invented). Only when a merge isn't
  applicable (target isn't a tray-eligible slot, no room, or the dropped
  item is itself a tray/rack-native) does it fall through to the
  pre-existing append-as-new-slot logic, unchanged.
- **Verification (2026-07-29)**: offscreen script — direct calls to
  `RackCanvas.dropEvent()` with a lightweight fake mime-data/drop-event
  (duck-typed, not a real `QDropEvent` — same style as prior sessions'
  direct-call tests) against a target rack fully occupied everywhere
  *except* one tray slot with spare width: confirmed the drop is
  accepted, no "no space" warning fires, the tray ends up with both
  devices, and no new slot is appended. Confirmed a genuinely full rack
  (no tray anywhere, no room) still correctly rejects the same kind of
  drop with the warning and `event.ignore()`. **Sanity check**:
  reproduced the pre-fix cross-rack logic (no tray-merge attempt)
  directly against the identical oversubscribed-except-tray rack setup —
  confirmed it finds no free position anywhere, reproducing the bug
  before trusting the fix.
- **Files modified**: `app/rack_canvas.py` (`dropEvent()`'s cross-rack
  branch).

### 52. [done] Library-device drop "no space" doesn't ignore the drop event
- **File**: `app/rack_canvas.py`, `dropEvent()` library-device-drop
  branch, "no space" case (~362–365)
- **Detail**: when `_free_near` returns `None`, shows the warning and
  `return`s without `event.ignore()` — inconsistent with the cross-rack
  branch above it, which does call `event.ignore()` in the same
  situation. An unaccepted-but-not-ignored `QDropEvent` defaults to
  "accepted," telling Qt's DnD machinery the drop succeeded when nothing
  was added.
- **Trigger**: drag a device from the library onto a completely full bay.
- **Severity**: real-but-minor — no data corruption (library drag uses
  `CopyAction`, no source-side removal), but a real accept/reject
  inconsistency.
- **Fixed 2026-07-29 (Session 17)**. Added `event.ignore()` to the
  library-device-drop branch's "no space" case, matching the cross-rack
  branch's existing behavior in the same situation.
- **Verification (2026-07-29)**: offscreen-Qt script — a fully-occupied
  target rack, a duck-typed fake drop event: confirmed `dropEvent()` now
  calls `.ignore()` (and not `.acceptProposedAction()`) when there's no
  room.
- **Files modified**: `app/rack_canvas.py` (`dropEvent()`'s
  library-device-drop branch).

### 53. [done] Hover-preview highlight not clamped to rack bounds
- **File**: `app/rack_canvas.py`, `paintEvent()` hover-preview block
  (~681–686), `_hover_u`/`_hover_u_height` via `dragMoveEvent`/
  `_point_to_bay_u` (~182–194, 283–290)
- **Detail**: never clamped against `self.rack.u_size`, so hovering a
  multi-U drag payload near the bottom rows draws the highlight rectangle
  extending past the rack frame into the stats-bar area. Visual only —
  actual drop placement (`_free_near`) is correctly bounds-checked.
- **Trigger**: drag a 2U+ device and hover near the rack's last row.
- **Severity**: real-but-minor.
- **Fixed 2026-07-29 (Session 17)**. `paintEvent()`'s hover-preview block
  now computes `hover_top = max(1, self._hover_u)` and `hover_bottom =
  min(self.rack.u_size, self._hover_u + self._hover_u_height - 1)`
  before drawing, and only draws the rectangle at all if `hover_bottom
  >= hover_top` — so the highlight's U range is always clamped to
  `[1, rack.u_size]`, and a hover state that's entirely out of range
  (rather than just partially overflowing) draws nothing instead of a
  nonsensical rectangle. Actual drop placement (`_free_near`) was
  already correctly bounds-checked and is unaffected — this is a
  drawing-only fix.
- **Verification (2026-07-29)**: offscreen-Qt script — set a hover state
  that would extend 3U past a 3U rack's bottom edge: confirmed the
  clamped range computed the same way `paintEvent()` now does is `[2,
  3]`, not `[2, 6]`; confirmed a real `paintEvent()` call with this
  out-of-range hover state completes without raising.
- **Files modified**: `app/rack_canvas.py` (`paintEvent()`'s
  hover-preview block).

### 54. [done] Editing a tray slot's name is silently discarded
- **File**: `app/rack_canvas.py`, `_edit_slot()` (~928–958)
- **Detail**: `SlotEditDialog` lets the user type a new name for a tray
  slot, but the tray branch is `if slot.is_tray: pass` — the typed name
  is silently discarded, while the method still pushes an undo entry,
  emits `slot_moved`, and repaints as if something changed.
- **Trigger**: right-click a tray slot → "Edit slot…" → type a name → OK.
- **Severity**: real-but-minor — misleading UX, no actual data loss since
  there was nothing to lose.
- **Fixed 2026-07-29 (Session 17), per the decided fix direction (no new
  "tray label" data field, out of scope).** `SlotEditDialog` no longer
  builds a name field for a tray slot at all — instead of a `QLineEdit`
  that silently discarded whatever was typed into it, a tray now shows a
  short explanatory `QLabel` ("This is a tray — each device inside has
  its own name.") in its place; `get_name()` returns `None` for a tray
  (there being no field to read). `_edit_slot()` now returns immediately
  after the dialog closes if `slot.is_tray` — since nothing in the
  dialog is editable for a tray (no name field, and the U-height row was
  already conditionally hidden for trays before this fix), nothing could
  have changed, so no undo entry is pushed and `slot_moved` is not
  emitted. The non-tray path is otherwise unchanged, just no longer
  nested under an `if/else` that no longer needs to exist.
- **Verification (2026-07-29)**: offscreen-Qt script — constructed
  `SlotEditDialog` for a tray slot: confirmed `name_edit is None` and
  `get_name() is None`. Called the real `_edit_slot()` on a tray slot
  (dialog auto-accepted): confirmed the undo stack length and a
  `slot_moved` listener's fire count are both unchanged. **Sanity
  check**: reconstructed the pre-fix flow (unconditional undo-push +
  `if slot.is_tray: pass` + unconditional emit, given a typed name) —
  confirmed it would have pushed undo and emitted despite discarding the
  name, reproducing the bug before trusting the fix.
- **Files modified**: `app/rack_canvas.py` (`SlotEditDialog.__init__()`,
  `.get_name()`; `RackCanvas._edit_slot()`).

### 55. [done] PDF device-list shows wrong per-unit specs when same-named devices differ
- **File**: `app/pdf_export.py`, `export_pdf()` (~302–309, ~342–349)
- **Detail**: device-list rows group solely by device *name*; the "each"
  Watts/Weight/Category shown come only from the *first*-encountered slot
  with that name (`if name not in seen: seen[name] = {...}`), then
  multiplied by count — while the project-summary total
  (`rack.total_watts()`) correctly sums every slot's real value.
- **Trigger**: two slots share a device name but differ in spec (e.g. an
  older `device_snapshot` from before a library edit): device list shows
  "Qty 2 · 500W each" (implying 1000W) while the summary correctly shows
  1050W — a directly conflicting, silently-wrong number in the same
  document.
- **Live-reproduced**: yes.
- **Severity**: likely-real-and-impactful.
- **Fixed 2026-07-28 (Session 12)**. `export_pdf()`'s grouping now keys
  on `(name, watts, weight_kg, category)` instead of `name` alone —
  `counts`/`seen`/`notes_list` are all keyed by this 4-tuple. Devices that
  genuinely match on all four still collapse into one row with a
  multiplied qty, unchanged for the common case; devices sharing a name
  but differing in any of those fields now get their own row with its own
  accurate qty/spec, matching the per-slot reality the project-total
  already reflected. No name-disambiguation suffix was added (e.g. no
  "(v1)"/"(v2)") — the brief was explicit that the same name appearing on
  two rows is fine, only the numbers needed to be right. Rows are sorted
  by `(name, category, watts, weight_kg)` — with `None` watts/weight_kg
  sorting after real values — rather than by name alone, so multiple rows
  sharing a name stay adjacent and the ordering doesn't raise on a
  `None`-vs-`float` comparison.
- **Verification (2026-07-28)**: offscreen script — a rack with 3 slots
  named "Same Name Device" (two an exact spec match, one differing only
  in watts): confirmed exactly 2 groups, the matching pair's qty is 2, the
  mismatched slot has its own qty-1 row; ran the real `export_pdf()` on
  this rack with no error. **Sanity check**: reproduced the old
  name-only grouping directly against the same 3 slots — confirmed all 3
  collapse into one row with qty 3, reproducing the bug before trusting
  the fix.
- **Files modified**: `app/pdf_export.py` (`export_pdf()`'s device-list
  grouping and sort).

### 56. [done] Zero watts/weight renders as "—" (indistinguishable from unset)
- **File**: `app/pdf_export.py`, `export_pdf()`, lines ~346, ~349:
  `f"{w:.0f}" if w else "—"` / `f"{kg:.2f}" if kg else "—"`
- **Detail**: `0` is falsy in Python — a legitimately zero-watt/weight
  device (e.g. a passive patch bay) renders as "—", indistinguishable
  from a device that never had the field set.
- **Live-reproduced**: yes.
- **Severity**: real-but-minor.
- **Fixed 2026-07-28 (Session 12)**. Both device-list "each" expressions
  now check `is not None` instead of truthiness: `f"{w:.0f}" if w is not
  None else "—"` / `f"{kg:.2f}" if kg is not None else "—"`. A genuine
  `0` now prints as `"0"`/`"0.00"`; only a field that's actually `None`
  (never set) prints `"—"`. Scoped exactly to the two literal patterns
  named in the finding (both in the device-list "each" columns) — the
  project-summary totals and `rack_info` line use a different, already
  more-explicit `> 0` comparison that wasn't named in this finding and
  was left untouched.
- **Verification (2026-07-28)**: confirmed `f"{0:.0f}" if 0 is not None
  else "—"` → `"0"` and same for weight; confirmed `None` still produces
  `"—"`; ran the real `export_pdf()` on a device with `watts=0,
  weight_kg=0` with no error. **Sanity check**: reproduced the old
  truthiness check directly against `0` — confirmed it produces `"—"`,
  reproducing the bug before trusting the fix.
- **Files modified**: `app/pdf_export.py` (`export_pdf()`'s device-list
  row-building).

### 57. [done] Long device/category/rack names overflow PDF table cells with no wrapping
- **File**: `app/pdf_export.py`, `export_pdf()`, device-list `Device`/
  `Category` cells (~342–343) and project-summary `Rack` name cell
  (~402–403)
- **Detail**: added as plain strings into fixed-width `Table` columns
  (60mm/28mm/44mm) with no `Paragraph` wrapping — unlike the `Notes`
  column, which deliberately uses `Paragraph`. A long name doesn't wrap
  or truncate; it overflows into neighboring columns, producing
  overlapping, unreadable text.
- **Live-reproduced**: yes — visually confirmed overlap onto
  Category/W/kg columns and onto Size/Used/Free/Devices.
- **Severity**: likely-real-and-impactful.
- **Fixed 2026-07-28 (Session 12)**. Device-list `Device` and `Category`
  cells, and the project-summary `Rack` name cell, are now wrapped in a
  `Paragraph` — same technique the `Notes` column already used. Added a
  `cell_wrap` `ParagraphStyle` (renamed from the old, notes-only
  `cell_notes` now that it's shared across Device/Category/Notes, same
  7pt Helvetica look) and a `summary_cell` style at 8pt (matching the
  project-summary table's own font size) for the Rack name cell. Long
  text now wraps to multiple lines within its own column/row instead of
  overflowing into neighbours.
- **Verification (2026-07-28)**: offscreen script — confirmed a long
  device name and a long category name, each wrapped at their real
  column width via `Paragraph.wrap()`, produce a multi-line height (not a
  single unbroken line); ran the real `export_pdf()` with very long
  device/rack names and rendered the page to PNG — visually confirmed the
  Device cell wraps to 4 lines within its own column with Category/W/kg
  unaffected, and the Rack name cell in the project summary wraps to 3
  lines with Size/Used/Free/Devices unaffected — no overlap anywhere.
  **Sanity check**: confirmed a bare Python string (the pre-fix cell
  type) has no `.wrap()`/column-aware reflow concept at all, i.e. the old
  code had no mechanism to avoid overflow.
- **Files modified**: `app/pdf_export.py` (new `cell_wrap`/`summary_cell`
  styles; device-list and project-summary row-building).

### 58. [done] Long device names overflow the rack diagram itself
- **File**: `app/pdf_export.py`, `RackDrawing.draw()`, ~line 175
  (`c.drawString(text_x, text_y, slot.name)`) and ~line 180 (U-size badge)
- **Detail**: no truncation, ellipsis, or font-size reduction for long
  device names — a name overruns the slot's 120mm width, runs past the
  rack's right border, and continues into the page margin.
- **Live-reproduced**: yes.
- **Severity**: likely-real-and-impactful.
- **Fixed 2026-07-28 (Session 12)**. Added a module-level
  `_truncate_text(c, text, font, size, max_width)` helper: measures
  `text`'s width via `c.stringWidth()` and, if it exceeds `max_width`,
  trims characters off the end and re-measures `text + "…"` until it fits
  (longest fitting prefix + ellipsis), rather than shrinking font size.
  `RackDrawing.draw()` now computes the actual available width for the
  name — the U-size badge's own measured width (via `stringWidth`, not
  guessed) subtracted from the slot's right edge, minus a small gap — and
  truncates the name into whatever's left before drawing it; the badge
  itself is unchanged/never truncated (it's always short and
  fixed-format).
- **Verification (2026-07-28)**: offscreen script — directly against
  `_truncate_text()` with a deliberately narrow `max_width`: confirmed a
  too-long name truncates (shorter than the original, ends with "…", and
  the truncated result's measured width is `<= max_width`), and confirmed
  a name that already fits is left byte-for-byte untouched. Ran two real
  `export_pdf()`s and rendered both to PNG: a doubled, guaranteed-oversized
  string ("Extremely Long Device Model Name That Would Never Fit In A
  Narrow Column" ×2, used for #57's table-wrap test rack, which also has
  a diagram) visibly truncates to "…Extremely Long Device Mo…" fully
  within the slot with the U-badge intact and unobscured; a second,
  shorter (but still long) name used for this item's own dedicated test
  rack happened to fit within a real 120mm slot without needing
  truncation at all — both outcomes are correct given each string's
  actual measured width, confirming the mechanism only truncates when
  genuinely necessary. **Sanity check**: confirmed the raw (untruncated)
  doubled string's measured width genuinely exceeds the available slot
  width, i.e. it would have overflowed before the fix.
- **Files modified**: `app/pdf_export.py` (new `_truncate_text()`;
  `RackDrawing.draw()`'s device-name drawing).

### 59. [done] Shrunk rack with out-of-bounds slots renders detached, bleeding into other content
- **File**: `app/pdf_export.py`, `RackDrawing.__init__()`/`draw()`,
  slot-y computation (~line 130: `sy = ry + (self.rack.u_size -
  slot.position_u - slot.u_height + 1) * SLOT_H`) and `self.height` (~76)
- **Detail**: neither validates that a slot's `position_u`/`u_height`
  actually fits within `rack.u_size`. Reachable through ordinary UI
  usage: `EditRackDialog` lets a user shrink `u_size` with no check
  against existing occupied positions (see #16's related but distinct
  off-by-one in the *bay-count* shrink-guard path — this is the *U-size*
  shrink path, which has no guard check at all in `RackDrawing`). Once
  `u_size` < an occupied U, `sy` goes negative — ReportLab doesn't clip a
  flowable's own canvas drawing, so the device box renders detached from
  the (now-empty-looking) rack diagram, overlapping the device-list table
  header, the divider, and the "Project summary" heading below it.
- **Live-reproduced**: yes — confirmed severe: the rack diagram appeared
  completely empty while the device box floated below it, overlapping
  three unrelated page elements.
- **Severity**: likely-real-and-impactful.
- **Fixed 2026-07-28 (Session 12)**. `RackDrawing.__init__()` now
  computes `self._draw_u_size = max(rack.u_size, occupied_top)`, where
  `occupied_top` is the highest `position_u + u_height - 1` among the
  rack's own slots (0 if empty) — deliberately not relying on #16's guard
  existing/working, per the session brief, since #16 itself isn't fixed.
  Every geometry computation in `draw()` that previously used
  `self.rack.u_size` (grid-line count, U-label loop, each slot's `sy`,
  and `rh`/the outer rack border) now uses `self._draw_u_size` instead.
  `rack.u_size` itself, and everything derived from it elsewhere
  (`used_u()`/`free_u()`/the "5U rack · Xu used" text), is untouched — this
  is purely a rendering-geometry fix, not a data-model change. A rack
  with no overflow keeps `_draw_u_size == rack.u_size`, so normal racks
  are unaffected.
- **Verification (2026-07-28)**: offscreen script — a `u_size=5` rack
  with a 2U slot at `position_u=8` (occupying U8–U9, well beyond the
  nominal 5U): confirmed `_draw_u_size == 9` and `drawing.height` reflects
  the enlarged geometry; confirmed a normal (non-overflowing) rack keeps
  `_draw_u_size == rack.u_size`. Ran the real `export_pdf()` and rendered
  to PNG — visually confirmed the diagram now draws 9 numbered U rows
  (not 5), the device box (correctly labeled "Overflowing Device", U8–U9)
  sits fully inside the rack's own border at the top of the frame, and
  nothing overlaps the device-list table or "Project summary" heading
  below it. **Sanity check**: confirmed `rack.u_size` (5) alone is less
  than the real occupied extent (9) — i.e. trusting it blindly would
  produce geometry too small to contain the slot, reproducing the root
  cause before trusting the fix.
- **Files modified**: `app/pdf_export.py` (`RackDrawing.__init__()`,
  `RackDrawing.draw()`).

### 60. [done] Tall racks can leave the prior PDF page mostly blank — decided not to fix
- **File**: `app/pdf_export.py`, `export_pdf()` line ~292
  (`story.append(KeepTogether(rack_block))`), `MAX_RACK_H` (~22)
- **Detail**: `MAX_RACK_H`'s 30mm buffer only budgets for the rack's own
  title+info overhead, not content already consumed earlier on the
  current page (project header: title, client/venue/date, notes,
  divider). Since `rack_block` is atomic (`KeepTogether`), a rack near
  the max page height (common: 42U/44U/45U full studio racks) gets pushed
  entirely to a fresh page, leaving the previous page mostly blank.
- **Trigger**: an ordinary 44U rack with ~15 devices and a normal project
  header.
- **Live-reproduced**: yes — page 1 was ~85% blank, all rack content
  moved to page 2.
- **Severity**: real-but-minor — cosmetic/wasteful, no data loss, but
  very easily triggered by common rack sizes.
- **Investigated 2026-07-28 (Session 12), per the session brief's
  "investigate first, propose the least invasive fix, stop and report
  back if every option is a bigger restructure than this is worth"
  instruction. Not fixed — stop condition hit; see reasoning below.**
  - **What ReportLab actually exposes.** Platypus builds `story` as a
    flat Python list *before* any layout happens — nothing in that phase
    knows how much vertical space is left on a page, because pagination
    only happens once, later, inside `doc.build(story, ...)`. The *only*
    place "how much space is actually left in the current frame" becomes
    knowable is the Flowable protocol's `wrap(availWidth, availHeight)`
    method, which the Platypus frame-filling engine calls on each
    flowable at real build time — `availHeight` genuinely is the true
    remaining space, not a guess. `RackDrawing` doesn't override `wrap()`
    today; it just returns `self.width`/`self.height`, fixed once in
    `__init__()` from the static `MAX_RACK_H`/`MAX_RACK_W` budget (an
    assumption of "starting fresh at the top of a page"). There is no
    "pre-flight" API to query remaining space before `doc.build()` runs —
    confirmed by reading ReportLab's Platypus flowable/frame model, not
    assumed.
  - **Is `KeepTogether` actually the cause?** No — verified this isn't
    just an `KeepTogether`-grouping problem. `RackDrawing` is a
    non-splittable custom `Flowable` (no `.split()`), so even *without*
    `KeepTogether`, the diagram alone would independently defer to a new
    frame the moment it doesn't fit in whatever's left — `KeepTogether`
    only decides whether the *title* goes with it. Removing/loosening
    `KeepTogether` doesn't reduce the blank space at all (the diagram is
    still what's actually too big to fit); it would just let the title
    land on the mostly-empty page while the diagram appears alone on the
    next one — title and diagram visually disconnected across a page
    boundary, arguably a worse defect than the one being fixed.
  - **Options actually considered, each with a real trade-off, none
    "free":**
    1. **Make `RackDrawing.wrap()` adaptive** — override it to recompute
       `self._scale`/`self.width`/`self.height` from the *real*
       `availHeight` passed in at build time, instead of the static
       `MAX_RACK_H` assumption, shrinking the diagram to whatever
       actually remains rather than deferring it. This is the only option
       that would genuinely eliminate the blank-space symptom, and it's
       mechanically compatible with the existing Flowable model (this is
       exactly how ReportLab's own `Table` adapts to a frame). Its cost:
       the *same* rack (same U-size, same devices) could render at a
       different physical scale depending purely on what precedes it in
       the document (project header length, notes text, a previous
       rack's device list) — today, by contrast, a rack's rendered scale
       depends only on its own U-size/bay-count, so two identically-sized
       racks always print at an identical scale regardless of position.
       That consistency is arguably valuable for a technical/production
       document a crew reads and compares pages from, and losing it is a
       real, user-visible behavior change, not a pure improvement — it
       would need a sensible minimum-scale floor too (else a rack landing
       with almost no room left could shrink to illegibility instead of
       reasonably deferring).
    2. **Drop/narrow `KeepTogether`** around the diagram specifically.
       Confirmed above this doesn't reduce blank space at all (the
       diagram itself is the actual constraint) and risks a worse-looking
       disconnect between a rack's title and its own diagram.
    3. **Force every rack onto its own fresh page** unconditionally
       (e.g. an explicit page break before each `rack_block`). This
       *would* work deterministically and never depends on surrounding
       content — but it changes page count/layout for **every** export,
       including the common case of several small racks that currently
       pack multiple-per-page just fine; that's a bigger, more broadly
       visible change than the reported bug (an occasional near-max-height
       rack) justifies.
    4. **Shrink `MAX_RACK_H`'s budget** further. Doesn't address the
       actual root cause (available space varies by *page position*, not
       by a fixed global constant) and would penalize legitimate large
       racks that render fine today when they land at the top of a fresh
       page.
  - **Recommendation**: none of the above is a clean, no-downside fix —
    every option trades one imperfection for another (visual scale
    consistency across racks, vs. title/diagram cohesion, vs. page count
    for all exports, vs. penalizing large racks that work fine today).
    This is a genuine "stop and report back" case per the session brief.
    If a fix is wanted despite the trade-off, option 1 (adaptive `wrap()`
    with a sensible minimum-scale floor, e.g. never shrink below ~70-80%
    of the fresh-page scale, else fall back to today's defer-to-next-page
    behavior) is the one that actually addresses the reported symptom —
    but the scale-consistency trade-off is a product decision, not a
    technical one, and deserves an explicit go-ahead rather than being
    baked in silently.
- **Decided 2026-07-28 (Session 13)**: project owner reviewed the
  Session 12 trade-off analysis above and chose to accept the occasional
  cosmetic blank-page behavior rather than trade away the export's
  consistent-scale guarantee (option 1's downside). No code change — this
  item is now closed as **decided-not-to-fix**, not merely unfixed/open.
  If the underlying constraint ever changes (e.g. scale consistency stops
  mattering, or ReportLab gains a cleaner API for this), the analysis
  above remains valid and can be revisited.

### 61. [done] Grayscale PDF export loses all category color differentiation
- **File**: `app/pdf_export.py`, `RackDrawing.draw()`, `use_color=False`
  branch (~152–155); dead `_to_gray()` helper (~43)
- **Detail**: every occupied slot is drawn with the same hardcoded
  neutral colors regardless of device category. A `_to_gray()`
  luminance-based helper exists in the module but is never called
  anywhere — suggesting grayscale mode was meant to preserve per-category
  distinction via gray-shade mapping and doesn't.
- **Live-reproduced**: yes — a rack with Video/Audio/Lighting slots
  rendered three visually-identical gray boxes under `use_color=False`.
- **Severity**: real-but-minor.
- **Fixed 2026-07-28 (Session 12)**. Added `_slot_colors(raw_hex,
  grayscale=False)`: derives the (accent, slot_bg, border) hex triple
  from a slot's raw category/device colour using the same lighten
  (82% toward white)/darken (×0.7) blend as before — but when
  `grayscale=True`, it first runs the raw colour through the
  previously-unused `_to_gray()` before blending, so different
  categories still map to different (if muted) gray shades instead of
  one flat neutral. `RackDrawing.draw()`'s `if self.use_color: ... else:
  ...` branch (which duplicated the blend logic once per mode) was
  replaced with a single `_slot_colors(raw, grayscale=not
  self.use_color)` call — a simplification as a direct side effect of
  routing both modes through one function, not a separate refactor. The
  now-dead `COL_SLOT_OCC`/`COL_STRIPE_NEUTRAL` constants (the flat
  neutrals this replaces) were removed; `COL_GRID` is unaffected (still
  used for the grid lines).
- **Verification (2026-07-28)**: offscreen script — confirmed
  `_slot_colors()` with `grayscale=True` gives Video/Audio/Lighting's
  default colors three distinct accent shades (not one shared neutral),
  confirmed each is genuinely monochrome (R==G==B), and confirmed the
  grayscale accent differs from the raw color (proving `_to_gray()` is
  actually being invoked). Ran the real `export_pdf()` with `use_color=
  False` on a rack with Video/Audio/Lighting slots and rendered to PNG —
  visually confirmed three visibly different gray-shade stripes/fills,
  correctly distinguishable by category. **Sanity check**: confirmed the
  old hardcoded-neutral behavior gives Video and Audio the exact same
  accent (`#999999`) regardless of category, reproducing the bug before
  trusting the fix.
- **Files modified**: `app/pdf_export.py` (new `_slot_colors()`;
  `RackDrawing.draw()`'s per-slot color derivation; removed
  `COL_SLOT_OCC`/`COL_STRIPE_NEUTRAL`).

### 62. [done] Exception during first-run library seeding kills the app before it ever appears
- **File**: `main.py`, `main()` — `seed_library_if_empty()` call (~line
  51), relative to `sys.excepthook` installation (~lines 41–48) and
  `app.exec()` (~55)
- **Detail**: `seed_library_if_empty()` (unguarded file I/O via
  `storage.save_library()`/`storage.add_custom_category()`) runs before
  `app.exec()` starts. An exception here still fires the crash-log +
  `MsgBox.error` dialog (the excepthook is already installed by this
  point), but the process then terminates immediately afterward —
  `MainWindow` is never created, `window.show()`/`app.exec()` never run.
  Materially worse than an exception inside the running event loop, which
  the excepthook mechanism was verified (in a prior session) to survive.
- **Trigger**: first run (or any reseed-from-corrupt-library run, see
  #45) on a machine where the `%APPDATA%\RackDesigner` write fails —
  disk full, permission denied, AV lock, OneDrive-synced APPDATA — all
  realistic on real Windows installs.
- **Live-reproduced**: yes (simulated the same call sequence).
- **Severity**: likely-real-and-impactful. Bonus: the generic crash
  dialog text ("you can keep working, consider saving your project now")
  is actively misleading in this exact scenario, since the app is about
  to exit.
- **Fixed 2026-07-29 (Session 16)**. `main()`'s `seed_library_if_empty()`
  call is now wrapped in its own `try/except`: on failure, the traceback
  is logged via a new shared `_log_crash()` helper (factored out of
  `_excepthook`'s existing logging code, per the brief's "reuse, don't
  duplicate" instruction — `_excepthook` now calls the same function),
  and a `seed_failed` flag is set — but execution continues into
  constructing and showing `MainWindow` regardless of the failure, rather
  than propagating and terminating the process. Only *after*
  `window.show()` does a new `_notify_seed_failed(window)` show a themed
  `MsgBox.error` explaining library initialization failed, the error was
  logged, and the library may be empty/incomplete this session —
  deliberately a distinct dialog/message from the existing
  `_notify_if_library_was_reset()` (which covers "found and quarantined a
  corrupt file," not "failed to seed at all"), per the brief.
- **Verification (2026-07-29)**: offscreen-Qt script — forced
  `seed_library_if_empty()` to raise: confirmed `MainWindow` still
  constructs and `.show()`s, confirmed exactly one `MsgBox.error` call
  with the new "Library initialization failed" title/message, confirmed
  `crash.log` contains the simulated traceback. Confirmed the unchanged
  happy path (no exception) still seeds all 119 devices with zero
  dialogs. **Sanity check**: reproduced the exact pre-fix sequence
  (unguarded `seed_library_if_empty()` call directly followed by
  `MainWindow()` construction, no try/except) against the same forced
  failure — confirmed the exception propagates and `MainWindow` is never
  constructed, reproducing the bug before trusting the fix.
- **Files modified**: `main.py` (`_log_crash()` new, factored out of
  `_excepthook`; new `_notify_seed_failed()`; `main()`'s
  `seed_library_if_empty()` call wrapped in `try/except`).

### 63. [done] A pre-`QApplication` startup exception is completely silent
- **File**: `main.py`, lines ~4–9 (top-of-file imports) through ~48
  (`sys.excepthook` installed only after `QApplication` construction +
  `setApplicationName`/`setStyle`/`setStyleSheet`/`setFont`)
- **Detail**: any exception in that window (e.g. `QApplication()` failing
  due to a broken/missing Qt platform plugin or driver issue, or an
  `ImportError` from a broken install) falls through to Python's raw
  default excepthook — for a windowed launch with no attached console,
  this is completely silent: the app just fails to appear, no log entry,
  no dialog.
- **Trigger**: broken Qt platform plugin/graphics driver at startup, or a
  corrupted/incomplete install causing an import-time failure.
- **Severity**: real-but-minor — narrower trigger conditions than #62
  (`QApplication()` rarely fails on a working install), but structurally
  confirmed.
- **Fixed 2026-07-29 (Session 16)**. `main.py`'s top-of-file imports
  (`PyQt6.QtWidgets`, `app.main_window`, etc.) are now wrapped in a
  module-level `try/except`, and `QApplication(sys.argv)` inside `main()`
  is wrapped the same way — both call a new `_log_pre_qt_crash()` then
  `raise` (the process still exits either way; the point is making sure
  something reaches `crash.log` first, since no dialog is possible this
  early — no `QApplication` exists yet for one to attach to, stated
  plainly per the brief rather than attempting to force a UI that can't
  exist). `_log_pre_qt_crash()` is deliberately self-contained: plain
  `os`/`pathlib`/`datetime`/`traceback` only, duplicating
  `get_app_data_dir()`'s two-line path logic instead of importing it —
  since at this stage either PyQt6 or the `app` package itself could be
  exactly what's broken, the logger can't depend on either still working.
- **Verification (2026-07-29)**: as-best-as-testable given the "no Qt
  yet" constraint (documented explicitly, per the brief) — a real,
  literal `import main` in a fresh interpreter with `app.main_window`'s
  import forced to fail via a `sys.meta_path` finder/loader (Python
  3.12's real import-failure mechanism, not a simulated call): confirmed
  the `ImportError` still propagates out of `import main` (not silently
  swallowed) **and** `crash.log` received the full traceback, even though
  no `QApplication`/window/dialog ever existed in that process. Also
  confirmed `_log_pre_qt_crash()`'s own code (excluding its docstring)
  references only `os`/`Path`/`datetime`/`traceback`/builtins — no
  `QApplication`, `MsgBox`, or `get_app_data_dir` symbol anywhere in its
  body. **What's not directly testable**: a genuinely broken Qt platform
  plugin/driver at the OS level (this environment's Qt install is
  working, `QT_QPA_PLATFORM=offscreen` notwithstanding) — covered instead
  by exercising the identical code path (`_log_pre_qt_crash` called from
  an `except` block, then re-raise) via the import-failure scenario
  above, which goes through the same `try/except` structure `main.py`
  wraps around `QApplication(sys.argv)`. **Sanity check**: re-ran the
  identical real-import-failure scenario against a reconstructed
  pre-fix `main.py` (unguarded imports, no `_log_pre_qt_crash`) — the
  `ImportError` still propagated (unchanged), but zero files were written
  under the fake `%APPDATA%` at all, confirming the silence described by
  the finding before trusting the fix.
- **Files modified**: `main.py` (new `_log_pre_qt_crash()`; top-of-file
  imports wrapped in `try/except`; `QApplication(sys.argv)` in `main()`
  wrapped in `try/except`).

### 64. [done] `MsgBox`/`_MsgDialog` isn't defensive against non-string arguments
- **File**: `app/dialogs.py`, `_MsgDialog.__init__()` (title/message
  widgets ~lines 39, 68, 73, 88), consumed by `MsgBox.error()`
  (~189–193) — which is exactly what `main.py`'s crash handler calls
- **Detail**: no type-coercion applied to `title`/`message` before
  handing them to Qt widgets. Passing a non-`str`, non-`None` value (e.g.
  an `int`, or an `Exception` instance directly instead of `str(e)`)
  raises `TypeError`, so the dialog itself fails to display. Grepped
  every `MsgBox.*` call site in the repo (`main.py`, `main_window.py`,
  `rack_canvas.py`) — all currently pass hardcoded strings, f-strings, or
  explicit `str(e)`, so this isn't triggered anywhere today. Flagged
  because `MsgBox.error` is exactly what the crash handler's own
  error-reporting path calls — a future call site regression here (e.g.
  `MsgBox.error(self, "Error", e)` instead of `str(e)`) would make the
  dialog call itself raise. That secondary exception would still be
  caught by the crash handler's own `try/except` around the `MsgBox.error(...)`
  call (confirmed in a prior session), so it wouldn't cause a second
  unhandled crash — just a silently-swallowed error dialog.
- **Live-reproduced**: yes (confirmed `TypeError` on non-str args).
- **Severity**: real-but-minor — latent robustness gap, no current
  trigger path in the codebase.
- **Fixed 2026-07-29 (Session 16)**. `_MsgDialog.__init__()` now coerces
  `title = str(title)` / `message = str(message)` at the very top, before
  either is handed to `setWindowTitle()`/`QLabel(...)`. Grepped every
  `MsgBox.*` call site in the live tree first to confirm none currently
  pass `None` (an unconditional `str()` turns `None` into the literal
  text `"None"` rather than an empty string) — all pass real strings
  today, so the coercion is a pure safety net with no behavior change for
  any existing caller, including Session 16's own new
  `_notify_seed_failed()` call (Task 1, #62).
- **Verification (2026-07-29)**: offscreen-Qt script — constructed
  `_MsgDialog` directly with a non-string title (`int`) and a non-string
  message (an `Exception` instance): confirmed `windowTitle()` shows the
  stringified value and the message `QLabel` shows the exception's
  `str()` text, no `TypeError`. Also called the real public
  `MsgBox.error()` (not a direct `_MsgDialog` construction) with a
  non-string title and message — confirmed it displays without raising.
  **Sanity check**: reproduced the pre-fix constructor logic directly
  (`setWindowTitle(title)`/`QLabel(title)` with no `str()` coercion)
  against the same non-string title — confirmed `TypeError` (Qt's own:
  `setWindowTitle(self, a0: str|None): argument 1 has unexpected type
  'int'`), reproducing the bug before trusting the fix.
- **Files modified**: `app/dialogs.py` (`_MsgDialog.__init__()`).

## Session 8 (2026-07-25) — Storage durability

Scoped, project-owner-approved fix session covering exactly six Session 7
backlog items — the "storage durability" cluster: #33 (atomic writes),
#34/#45 (corrupt-vs-missing distinction on load, one fix across both
items), #35 (CSV encoding fallback), #38 (partial project-load recovery),
#39 (save_project no longer mutates the caller's object). Design
decisions for all six were specified in the session brief rather than
left open; nothing here is an invention beyond what was asked, aside from
`os.fsync()` in the atomic-write helper (a one-line durability
strengthening directly in scope of "atomic writes... crash/kill
mid-write," not a redesign) and checking `custom_categories.json`
corruption on every startup rather than only when the library is empty
(needed for #45's "same treatment... if it's also found corrupt" to
actually fire independently of library state).

See each item's own entry above (#33, #34, #35, #38, #39, #45) for full
implementation and verification detail, and `changelog.md`'s Session 8
entry for the consolidated file list and verification summary.

**Not in this session's scope** (flagged during investigation, left
untouched per the ground rule against opportunistic fixes):
- **#62** (`main.py`'s `seed_library_if_empty()` call happens before
  `MainWindow` is constructed — an exception there kills the app with no
  window ever shown). This session's `_notify_if_library_was_reset()`
  call was deliberately placed *after* `window.show()`, but the
  pre-existing `seed_library_if_empty()` call site itself was not moved
  — #62 is a separate, not-yet-approved finding about that ordering and
  is unaffected by this session's changes either way.
- **#32** (`mm_to_u()` over-allocating a U for exact-multiple heights)
  and the rest of the Session 7 backlog remain `[todo]`, unchanged.

## Session 9 (2026-07-25) — Dirty-flag / data-loss cluster

Scoped, project-owner-approved fix session covering exactly three
Session 7 backlog items — the "dirty-flag / data-loss" cluster: #12
(Project Info fields never marked the project dirty), #25 (racks added
before the first Save could be silently discarded), #26 (dirty flag
cleared before a save was confirmed to succeed). All three live in
`app/main_window.py`, no other files touched.

For #25, the session brief specified a preferred direction (one shared
`Project()` at startup instead of two independent objects) but asked for
investigation first, with an explicit "stop and report back" condition
if that approach looked unsafe — it didn't (see #25's entry above for
the full investigation), so it was implemented as specified. For #26,
the brief specified the minimal fix (restore `_dirty = True` in the
`except` block) over the larger alternative (reordering when
`project_loaded` fires) and noted #26 touches code Session 8 already
changed — re-read first, confirmed the premature clear is unrelated to
Session 8's changes and still present exactly as described.

See each item's own entry above (#12, #25, #26) for full implementation
and verification detail, and `changelog.md`'s Session 9 entry for the
consolidated file list and verification summary.

**Not in this session's scope**: the remaining 44 Session 7 backlog
items are unchanged, still `[todo]`. `ExportSection`'s own independent
`Project()` at construction (noted while investigating #25) was left
alone — it's synced explicitly on tab-switch and on project-load, is
never itself edited, and isn't part of #25's failure mode.

## Session 10 (2026-07-28) — Rack canvas interaction cluster

Scoped, project-owner-approved fix session covering exactly six Session 7
backlog items — the "rack canvas interaction" cluster: #15 (rack reorder
collapses same-named racks), #14 + #17 (sidebar rack selection never
updates the "active" canvas, and the active canvas dangles on an orphaned
widget after add/remove/edit/reorder — same root cause, fixed together),
#47 (tray paste/cross-rack-drag uses the wrong height), #48 (context-menu
"Paste here" ignores the right-clicked cell), #49 (Duplicate ignores the
source's own bay). All in `app/main_window.py` (#14/#15/#17) and
`app/rack_canvas.py` (#47/#48/#49) — no other files touched.

The brief opened with an investigation step (Task 1) ahead of #15: does
`Rack` already have a stable identity independent of `name`, since the
preferred fix for #15 is matching by id rather than name, and adding an
id field would have been a data-model change requiring a stop-and-report
if it looked unsafe. It didn't need one — `app/models.py`'s `Rack` already
had `id: str = field(default_factory=lambda: str(uuid.uuid4()))`, already
serialized in `to_dict()`/`from_dict()` with backward-compatible id
generation for pre-existing `.rackproj` files missing the field. #15's fix
is therefore purely a matching-logic change (`name` → `id`) in
`_on_rack_reordered()`, no model change.

For #14/#17, the brief specified the direction: (a) wire the sidebar
`rack_list`'s row-selection signal to also update `_active_canvas`, and
(b) after every canvas-rebuilding rack operation, explicitly re-point
`_active_canvas` at the rebuilt rack (matched by the same `Rack.id` used
for #15), falling back to the first canvas or `None` if that rack no
longer exists. Both were implemented as specified — (a) reuses the
existing `_on_canvas_active()` handler rather than duplicating its logic,
(b) is a new `_restore_active_canvas()` helper called from all four
rebuild sites (`_add_rack`/`_remove_rack`/`_edit_rack`/
`_on_rack_reordered`).

See each item's own entry above (#14, #15, #17, #47, #48, #49) for full
implementation and verification detail, and `changelog.md`'s Session 10
entry for the consolidated file list and verification summary.

**Not in this session's scope**: the remaining 38 Session 7 backlog items
are unchanged, still `[todo]`.

## Session 11 (2026-07-28) — Form/dialog + import/categorie cluster

Scoped, project-owner-approved fix session covering five Session 7
backlog items — the "form/dialog + import/categorie" cluster: #20 + #30
(unrecognized category silently falls back instead of being registered —
one shared mechanism, both fixed together), #21 (JSON merge-import can
create duplicate device ids), #27 (rack-size spinner arrows discard
uncommitted typed text), #29 (rack_native toggle leaves a stale
`height_mm`). Touches `app/storage.py`, `app/library_dialog.py`, and
`app/main_window.py` — no other files.

For #20/#30, the brief specified the shared mechanism directly: a helper
that registers an unknown category and returns it unchanged, used at both
`DeviceForm.load()` and JSON import. Added `storage.
register_category_if_unknown()`; CSV import's own inline
`add_custom_category()` call was also switched to it for consistency
(behavior-preserving, since `add_custom_category()` is already
idempotent) so the mechanism is now genuinely shared across all three
places that can encounter an unrecognized category, matching the note
added to `design.md`.

For #29, the brief asked to also check whether `width_mm` has the same
gap rather than assuming. It doesn't: `width_mm_spin` is never
`setEnabled(False)` by `_on_rack_native_changed()` in either direction,
so there's no "disabled-but-stale" value to clear — see #29's entry above
for the full reasoning. No code change was made for `width_mm`.

See each item's own entry above (#20, #21, #27, #29, #30) for full
implementation and verification detail, and `changelog.md`'s Session 11
entry for the consolidated file list and verification summary.

**Not in this session's scope**: the remaining 33 Session 7 backlog items
are unchanged, still `[todo]`.

## Session 12 (2026-07-28) — PDF export cluster

Scoped, project-owner-approved fix session covering seven Session 7
backlog items, all in `app/pdf_export.py` — the PDF export cluster: #55
(wrong per-unit specs for same-named devices), #56 (zero renders as
"—"), #57 (long names overflow table cells), #58 (long names overflow
the rack diagram), #59 (shrunk rack with out-of-bounds slots renders
detached), #60 (tall racks leave the previous page blank — investigated,
not fixed), #61 (grayscale loses category differentiation).

Six of the seven (#55, #56, #57, #58, #59, #61) were fixed as specified
in the brief — see each item's own entry above for full implementation
and verification detail (including PNG-rendered visual inspection for
the visual findings #57/#58/#59/#61), and `changelog.md`'s Session 12
entry for the consolidated file list.

#60 was investigated first per the brief's explicit instruction, and hit
the brief's own stop condition: every fix that would actually eliminate
the reported blank-space symptom (only genuinely possible via an adaptive
`RackDrawing.wrap()` reacting to real remaining frame space, which
ReportLab's Platypus model only exposes at real build time, not during
story construction) carries a real trade-off — trading away the current
guarantee that a rack's rendered scale depends only on its own spec, not
on surrounding content/page position. See #60's entry above for the full
option-by-option reasoning and recommendation. Not fixed this session,
per the brief's own instruction to stop and report back rather than
force a fix with new page-layout risk.

**Not in this session's scope**: the remaining 27 Session 7 backlog
items (including #60, still open) are unchanged, still `[todo]`.

## Session 13 (2026-07-28) — Close #60, then math/validation cluster

**Task 0**: closed `task.md` #60 as **decided-not-to-fix**, no code
change — the project owner reviewed Session 12's trade-off analysis
(every real fix requires either accepting a rack-scale-consistency loss
or a bigger restructure) and chose to accept the occasional cosmetic
blank-page behavior rather than trade that guarantee away. See #60's
entry above for the closing note.

Then a scoped, project-owner-approved fix session covering five more
Session 7 backlog items — the "math/validation" cluster: #32 (`mm_to_u()`
over-allocates a U on exact multiples), #36 (CSV category normalization
only uppercases the first char, missing case-insensitive matches), #37
(CSV integer parsing uses banker's rounding instead of ceiling), #31
(loaded numeric fields bypass the range clamps manual edits enforce),
#40 (`Rack` bay-scoped helpers don't validate `bay`). Touches
`app/models.py`, `app/storage.py`, and `app/library_dialog.py`.

Two items had explicit investigate-first conditions in the brief:
- **#37**: checked every call site of `_parse_int()` in the live tree
  (not just `storage.py`) — there's exactly one, the CSV `Height (U)`
  column, where ceiling is unambiguously correct. No other use exists
  that a blanket change could break, so the fix was applied directly
  rather than needing to stop and report back.
- **#40**: considered clamping `bay` in every bay-scoped helper vs.
  normalizing once in `Rack.from_dict()`. Concluded the latter is
  cleaner — the only realistic path to an out-of-range `bay` is a
  corrupted/hand-edited project file loaded via `from_dict()` (nothing
  in the live UI can produce one), so fixing the data at its entry point
  covers every current and future reader, instead of adding
  easy-to-forget bounds-checks to each of the four helpers individually.

See each item's own entry above (#31, #32, #36, #37, #40) for full
implementation and verification detail, and `changelog.md`'s Session 13
entry for the consolidated file list and verification summary.

**Not in this session's scope**: the remaining 21 Session 7 backlog
items are unchanged, still `[todo]`.

## Session 14 (2026-07-29) — Two missed likely-real-and-impactful items

Scoped, project-owner-approved fix session covering two Session 7
backlog items that had been triaged `likely-real-and-impactful` but not
yet picked up in Sessions 8–13: #16 (rack-shrink off-by-one falsely
blocks legal operations, `app/main_window.py`) and #51 (cross-rack drop
onto an existing tray never merges, `app/rack_canvas.py`). No
investigate-first conditions in this brief — both had a specified fix
direction.

See each item's own entry above (#16, #51) for full implementation and
verification detail, and `changelog.md`'s Session 14 entry for the
consolidated file list and verification summary.

**Not in this session's scope**: the remaining 19 Session 7 backlog
items are unchanged, still `[todo]`.

## Session 15 (2026-07-29) — Preloaded library data cluster

Scoped, project-owner-approved fix session covering four Session 7
backlog items, all data-only corrections in `app/preloaded_library.py`
(plus one documentation-only item) — no logic changes: #41 (redundant
"Lighting" custom category on fresh installs), #42 + #43 (two
copy-pasted `model` strings), #44 (two implausible `depth_mm` values),
#46 (docs said "20-device" library, actually 119 — documentation-only).

#41 was scoped to fresh installs only, per the brief — existing installs
that already wrote a redundant `"Lighting"` custom category are not
retroactively cleaned up. #42/#43/#44 are explicitly flagged as
best-estimate internal-consistency corrections (sibling-device
cross-comparison), not verified against actual vendor spec sheets, per
the brief's instruction to state that assumption. #46 was resolved by
grepping `docs/*.md` for the stale "20-device" claim and correcting it
in all three places it appeared, plus reconfirming the real count (119)
via a fresh grep-count of the live source rather than trusting the
already-cited figure.

See each item's own entry above (#41, #42, #43, #44, #46) for full
implementation and verification detail, and `changelog.md`'s Session 15
entry for the consolidated file list and verification summary.

**Not in this session's scope**: the remaining 15 Session 7 backlog
items are unchanged, still `[todo]`.

## Session 16 (2026-07-29) — Startup robustness cluster

Scoped, project-owner-approved fix session covering three Session 7
backlog items, all in `main.py` plus one in `app/dialogs.py` — the
"startup robustness" cluster: #62 (an exception during first-run library
seeding kills the app before the window ever appears), #63 (a
pre-`QApplication` startup exception is completely silent), #64
(`MsgBox`/`_MsgDialog` isn't defensive against non-string arguments —
exactly the path #62's new error-reporting call goes through).

The brief specified the fix direction for all three directly, with no
investigate-first conditions. For #62, it also specified reusing
`_excepthook`'s existing crash-log logging rather than duplicating it —
done by factoring that logging into a new shared `_log_crash()`, called
by both `_excepthook` and the new seeding guard. For #63, the brief was
explicit that no dialog is possible this early (no `QApplication` yet)
and that disk logging is the ceiling — `_log_pre_qt_crash()` is
deliberately self-contained (no Qt or `app.storage` dependency) since
either could be exactly what's broken at that stage. #64 was picked up
in the same session since #62's new `_notify_seed_failed()` call is a
new caller of `MsgBox.error()`, making the latent gap newly relevant
rather than purely theoretical.

See each item's own entry above (#62, #63, #64) for full implementation
and verification detail — including #63's explicit note on what is and
isn't testable without a genuinely broken Qt install — and
`changelog.md`'s Session 16 entry for the consolidated file list and
verification summary. `design.md` gained a new "Startup error handling
(three layers, `main.py`)" section describing how Layers 1 (Session 3),
2, and 3 (both this session) fit together as one coherent model.

**Not in this session's scope**: the remaining 12 Session 7 backlog
items are unchanged, still `[todo]`.

## Session 17 (2026-07-29) — Final cleanup: 11 minor/cosmetic items

Scoped, project-owner-approved fix session covering the last 11 Session 7
backlog items — all `real-but-minor` or informational, explicitly framed
as low-risk in the brief: #13 (failed recent-project load leaves wrong
row selected), #18 (Designer category filter never refreshes), #19
(misleading 0-rack message), #22 (merge-import dedup set stale within
the same import), #23 (CSV export silently drops images, no warning),
#24 (empty-library category-scope export dead-end), #28 (rack-size
preset combobox doesn't stay in sync), #50 (drag state ignores which
mouse button was released), #52 (library-device drop "no space" doesn't
ignore the event), #53 (hover-preview highlight not clamped to rack
bounds), #54 (editing a tray slot's name is silently discarded). Touches
`app/main_window.py` (#13/#18/#19/#22/#23/#24/#28) and
`app/rack_canvas.py` (#50/#52/#53/#54).

The brief specified the fix direction for all 11 directly, with no
investigate-first conditions, and explicitly allowed skipping
sanity-reverts for the most trivial fixes to avoid busywork. Reverts
were done anyway for the three where the fix involved real logic
restructuring rather than a one-line addition — #22 (dedup loop
restructuring), #50 (mouse-button guard), #54 (dialog field removal +
early-return) — since those were judged non-obvious enough to be worth
confirming; the more mechanical one-line fixes (#13, #18, #19, #23, #24,
#28, #52, #53) were verified with direct before/after behavioral checks
instead, per the brief's own discretion clause.

See each item's own entry above (#13, #18, #19, #22, #23, #24, #28,
#50, #52, #53, #54) for full implementation and verification detail,
and `changelog.md`'s Session 17 entry for the consolidated file list and
verification summary.

**This closes out the Session 7 audit backlog**: all 53 original
findings are now either fixed or explicitly decided-not-to-fix (#60).
No further Session 7 items remain open.

## Features

New work items, numbered fresh starting at #65 (not a continuation of
the Session 7 audit's #1–#64 range, which is fully closed as of Session
17 above) — this section is for new functionality, not bug fixes.

### 65. [done] Export rack diagrams as PNG
- **Files**: `app/pdf_export.py` (`RackDrawing.__init__()`'s new
  `page_fit` parameter, new `export_rack_png()`), `app/main_window.py`
  (`ExportSection`: new `export_png_btn`, `_sanitize_filename()`,
  `_do_export_png()`), `requirements.txt` (new `PyMuPDF>=1.24.0`),
  `rack_designer.spec` (PyMuPDF PyInstaller bundling).
- **What**: a new "EXPORT RACKS AS PNG" button in the Export tab,
  alongside the existing PDF export controls. Exports one PNG per rack
  in the project, at natural (uncapped) size, to a user-chosen folder —
  see `changelog.md`'s Session 18 entry and `design.md`'s new "PNG
  export" section for full mechanism detail (why it reuses `RackDrawing`
  instead of a second renderer, the page_fit=False rendering pipeline,
  filename sanitization/dedup, PyInstaller bundling notes).
- **Done 2026-07-29 (Session 18)**, four tasks:
  1. **PyMuPDF dependency investigated and added**: confirmed already
     informally available (used ad-hoc in prior sessions' own
     verification scripts). Added `PyMuPDF>=1.24.0` to
     `requirements.txt`. Researched the PyInstaller bundling gotcha
     (PyMuPDF's compiled extensions/DLL aren't reliably found by plain
     static import analysis) and added `collect_all('pymupdf')`/
     `collect_all('fitz')` to `rack_designer.spec`, merged into
     `Analysis()`'s `binaries`/`datas`/`hiddenimports` — equivalent to
     `pyinstaller --collect-all pymupdf --collect-all fitz`. **Not
     exercised by an actual PyInstaller build this session**, per the
     task's explicit scope — believed correct, but untested until the
     next real build.
  2. **`RackDrawing` gained `page_fit: bool = True`**: defaults `True`
     so `export_pdf()`'s existing behavior is unchanged byte-for-byte.
     `page_fit=False` skips the page-fit scale computation entirely,
     forces `_scale = 1.0`, sets `width`/`height` to the natural
     uncapped size.
  3. **New `export_rack_png(rack, filepath, use_color=True, dpi=300)`**:
     builds `RackDrawing(rack, use_color, page_fit=False)`, renders it
     via its own `drawOn()`/`draw()` onto a single-page in-memory
     ReportLab PDF sized exactly to the drawing's natural dimensions,
     then rasterizes that page to PNG via PyMuPDF (`fitz`) at the given
     DPI (`zoom = dpi / 72.0`, since PDF points are natively 72/inch).
     `fitz` is imported lazily inside the function, not at module level,
     so a broken/missing PyMuPDF install only breaks this one feature
     when used, not the whole app at startup.
  4. **UI**: `ExportSection._do_export_png()` — folder picker, per-rack
     filename sanitization reusing `storage.save_project()`'s exact
     character-filter pattern (duplicated locally as
     `_sanitize_filename()`, not imported — `storage.py`'s version isn't
     exposed as a reusable helper), collision dedup via the same
     `" (2)"`/`" (3)"` suffix pattern (checked against both same-batch
     racks and pre-existing files in the destination folder — never a
     silent overwrite), the existing "Use device colours" checkbox
     state, fixed 300 DPI, per-rack failure isolation (one rack's
     exception is recorded and the batch continues), and a completion
     summary dialog (success count, destination folder, per-rack
     failures by name).
- **Verification (2026-07-29)**: see `changelog.md`'s Session 18 entry
  for the full breakdown. Summary: Task 2's page_fit=True path was
  confirmed numerically identical (direct float comparison, not just
  visual) to the pre-Session-18 formula across four regression racks
  (1-bay/2-bay/3-bay/45U-3-bay), plus a full `export_pdf()` run in both
  color and grayscale. Task 3's PNG output was confirmed pixel-dimension
  -correct against the DPI×natural-size math (within 1px rounding
  tolerance) for a large and a small rack at two DPIs, confirmed
  `page_fit=False` truly ignores `MAX_RACK_H`/`MAX_RACK_W`, and — via
  direct visual inspection of the rendered PNGs — confirmed long-name
  truncation, out-of-bounds-slot self-containment, and grayscale
  per-category shading all carry over from the Session 12 PDF-export
  fixes automatically (same `RackDrawing.draw()` code path). Task 4 was
  driven both directly (`_do_export_png()` called with mocked file
  dialog/MsgBox) and through a real `QTest.mouseClick` on an actual
  `MainWindow`'s button: two same-named racks produced two distinct,
  non-colliding PNGs; a second export into the same folder didn't
  collide with the first run's files either; a 0-rack project showed a
  clear message with no folder dialog opened; a simulated per-rack
  failure was isolated (the other rack still exported, the failure named
  in the summary dialog). Full-app-launch smoke test re-run clean
  afterward.
- **Addendum, fixed 2026-07-29 (Session 19)**: Session 18 deliberately
  exported *every* rack in the project regardless of the Export tab's
  "RACKS TO INCLUDE" checkboxes (flagged at the time as a scope note,
  since the brief said "for each rack in the project" and the PDF export
  next to it already had its own distinct "selected racks" concept it
  didn't reuse). The project owner confirmed the checkboxes should apply
  to PNG export too, for consistency between the two export actions.
  `ExportSection._do_export_png()` now filters to
  `[r for r, c in self._rack_checkboxes if c.isChecked()]` — the exact
  same expression `_do_export()` (PDF) already used — instead of
  iterating `self.project.racks` directly. The 0-selected case (project
  non-empty, but nothing checked) now also matches `_do_export()`
  exactly: "Select at least one rack.", distinct from the
  genuinely-empty-project case's "No racks in project." (previously
  `_do_export_png()` only had the latter message, since it never had a
  0-selected-but-non-empty case to distinguish). See `changelog.md`'s
  Session 19 entry for verification detail.

## Session 18 (2026-07-29) — New feature: export rack diagrams as PNG

Project-owner-approved feature session, the first since the Session 7
audit backlog closed out completely in Session 17 — new work, not bug
fixes, hence the fresh `## Features` section and #65 numbering above
rather than a continuation of #1–#64. Four tasks, all in one session: (1)
investigate/add the PyMuPDF dependency, (2) a natural-size rendering mode
for `RackDrawing`, (3) the actual `export_rack_png()` function reusing
that mode, (4) the Export-tab UI wired to it. See #65's entry above for
full implementation detail and `changelog.md`'s Session 18 entry for the
consolidated file list and verification summary.

**Not in this session's scope**: an actual PyInstaller build/exe
(explicitly deferred — the `.spec` changes are believed correct but
untested until the next real build); respecting the Export tab's
per-rack "RACKS TO INCLUDE" checkboxes for the new PNG export (the task
brief said "for each rack in the project," which — read literally, and
matching the neighboring PDF export's own distinct "selected racks"
terminology it deliberately didn't reuse — this session interpreted as
*all* racks regardless of that checkbox state, not just the checked
ones; flagging in case the project owner actually wanted the checkboxes
respected, which would be a one-line change to filter by `_rack_checkboxes`
instead of `self.project.racks`).

**Resolved 2026-07-29 (Session 19)**: the project owner confirmed the
checkboxes should apply to PNG export too — see #65's addendum above
and `## Session 19` below.

## Session 19 (2026-07-29) — PNG export respects "RACKS TO INCLUDE"

Small, scoped fix session resolving the one open question Session 18
flagged: `ExportSection._do_export_png()` now filters to only the
checked racks, using the identical `[r for r, c in self._rack_checkboxes
if c.isChecked()]` expression `_do_export()` (PDF) already used, instead
of iterating `self.project.racks` (every rack) directly. The 0-selected
(but non-empty-project) case now shows the same "Select at least one
rack." message `_do_export()` already shows for that case, distinct from
the genuinely-empty-project "No racks in project." message — investigated
first per the brief's "check first" instruction, confirmed `_do_export()`
does use two distinct messages for its two distinct 0-rack scenarios, so
`_do_export_png()` now mirrors both rather than collapsing them into one.

See #65's addendum entry above for the full detail, and `changelog.md`'s
Session 19 entry for verification.
