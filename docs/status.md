# RackDesigner — Status

_Last updated: 2026-07-30 (Session 22)._

## Declared version
**`v0.1.20`**, as of 2026-07-24 (Session 5) — bumped from `v0.1.19`.
Sourced from a single new constant, `app.APP_VERSION` (`app/__init__.py`),
which `app/main_window.py`'s About tab and status bar both read from.
`rack_designer.spec` (`name=`) and `rack_designer_installer.iss`
(`AppVersion=`, `OutputBaseFilename=`) were updated by hand to match — see
`task.md` #7.

**Update (2026-07-24, Session 6)**: the working-folder/version mismatch
noted here previously is resolved — the live tree was duplicated to a new
`RackDesigner_v0.1.20/` sibling folder this session (`build/`, `dist/`,
`__pycache__` excluded from the copy). `RackDesigner_v0.1.19/` is now a
frozen snapshot as of 2026-07-24, not edited further. See
`folder_structure.md` and `task.md` (Build/release process) for detail.

**Update (2026-07-30, Session 20) — v0.1.20 has now actually been built,
not just coded.** Everything above described the *declared* version
(`app.APP_VERSION`, source tree naming) — from Session 5 through Session
19, no real PyInstaller/Inno Setup build of v0.1.20 had been produced;
`installer_output/` still only held `v0.1.17`–`v0.1.19` installers. This
session: fixed the last 6 stale `v0.1.19` references in
`rack_designer_installer.iss` (`task.md` #66, closing out #4/#10), ran a
real `pyinstaller rack_designer.spec` build (confirmed PyMuPDF's
`collect_all()` bundling from Session 18 actually works — `mupdfcpp64.dll`
etc. present in the built exe, not just "believed correct"), smoke-tested
the built exe (clean startup, no crash log), zipped it as
`installer_output/RackDesigner_v0.1.20_Portable.zip`, and compiled
`installer_output/RackDesigner_v0.1.20_Setup.exe` via Inno Setup. No
interactive/functional UI QA was performed on the build — startup smoke
test only. See `changelog.md` Session 20 for full verification detail.

**Update (2026-07-30, Session 21) — end-user manual updated for
v0.1.20.** The manual (`Manual/v0.1.X/RackDesigner..._UserManual.docx` +
`.pdf`) had been stuck at v0.1.19 and documented none of Sessions 18-20's
user-facing changes. New `Manual/v0.1.20/RackDesigner_v0.1.20_UserManual.docx`
+ `.pdf`. `Manual/v0.1.19/` untouched. See `task.md` #67 and
`changelog.md` Session 21 for the 8 content edits and verification
detail.

**Update (2026-07-30, Session 22)**: the two new manual files were
originally named with an underscore-separated version
(`RackDesigner_v0_1_20_UserManual...`, per Session 21's literal brief) —
flagged at the time as inconsistent with every prior version's
dot-separated naming (`RackDesigner_v0.1.17-19_UserManual...`). Renamed
this session to `RackDesigner_v0.1.20_UserManual.docx`/`.pdf`, matching
that convention. Rename only; both files confirmed to still open cleanly
afterward. See `task.md` #67 (Session 22 addendum) and `changelog.md`
Session 22.

## ⚠️ Documentation drift (confirmed by project owner)
The codebase contains features **not present in `Changelog.txt`** at any
version, meaning the log is behind the real state of the code by an unknown
number of undocumented changes:

- `RackSlot.tray_devices` — tray system for side-by-side non-rack-native
  devices (`app/models.py`, `app/rack_canvas.py`)
- `DeviceDefinition.rack_native` / `width_mm` / `height_mm` — non-19"
  device support (`app/models.py`)
- `storage.import_library_csv()` — CSV library import (`app/storage.py`)

**Action needed** (tracked in `task.md`): confirm what the real current
version number should be, and either backfill changelog entries for the
above or open the `changelog.md` "Unreleased" section explicitly acknowledging
the gap (current approach — see `changelog.md`).

## Known open bugs

| # | Summary | Confidence | Detail |
|---|---|---|---|
| 1 | ~~PDF export: multi-bay racks render with all bays overlapping in one column~~ — **fixed 2026-07-22 (Session 2)** | — | `changelog.md` Unreleased — Session 2 fixes |
| 2 | ~~App crashes when a device drag leaves the rack canvas bounds (cross-rack move, or any in-rack drag that overshoots the U range)~~ — **fixed 2026-07-24 (Session 3)**, both the crash (missing `QPixmap` import) and the related stale-bay UI defect | — | `design.md` § Known architectural gaps, item 2; `changelog.md` Session 3 |
| 5 | ~~Editing a device in the Library tab silently wipes its images~~ — **fixed 2026-07-24 (Session 4)** | — | `design.md` § Known architectural gaps, item 3; `changelog.md` Session 4 |

Bug #2 turned out to be two distinct issues, both now fixed: the
crash itself (`QPixmap` used in `rack_canvas.py` without being imported,
raised on the first mouse-move after a drag leaves the canvas bounds —
silent process abort with no custom `sys.excepthook` in place), and a
separate, non-crashing UI/data-consistency defect (`RackSlot.bay` not
updated when a same-canvas drag crosses bay columns, so the dragged slot
stayed rendered in its original bay). See `design.md` for full detail and
verification. A top-level `sys.excepthook` was also added in `main.py`
this session as a safety net for future unhandled exceptions (logs to
`crash.log`, shows an error dialog, app keeps running) — new mechanism,
not itself a bug fix.

Bug #5: `ImagePickerWidget` was fully built in `library_dialog.py` but
never instantiated by `DeviceForm`, so device images were silently wiped
on every Library-tab save (and could never be added via the UI at all).
Fixed 2026-07-24 (Session 4) — see `design.md` for detail. The live
`library.json` (119 devices) currently has zero devices with any image
data, and the seed library never shipped images either — consistent with
prior silent data loss but not conclusive proof of it (no way to
distinguish "never had one" from "lost it" after the fact). Images lost
before this fix cannot be recovered by it.

## What works (per `Changelog.txt`, v0.1.0 → v0.1.19)
Full detail in `Changelog.txt` (kept as historical archive). Summary of
stable, documented functionality:
- Project management (create/open/save/save as/delete, recent list, dirty-state guard)
- Multi-rack, multi-bay (1–3) canvas with drag & drop from library, internal
  reordering, cut/copy/paste/duplicate, 10-level per-rack undo, keyboard
  shortcuts, cartesian pan/zoom/fit
- Device library: full edit form, images (front/rear, base64), custom
  categories, faceplate + patch-panel connector/port config, JSON
  import/export (merge/replace)
- PDF export: rack diagrams (color or B&W-ready via "Use device colours"),
  grouped device lists, power/weight totals, project summary, configurable
  sections
- **PNG export (new, Session 18, 2026-07-29 — not part of the pre-v0.1.19
  baseline this section otherwise describes)**: "EXPORT RACKS AS PNG" in
  the Export tab, one PNG per rack at natural (uncapped) size via
  `app.pdf_export.export_rack_png()`, reusing the same `RackDrawing`
  class/fixes as PDF export. See `task.md` #65 and `design.md`'s "PNG
  export" section. New runtime dependency: PyMuPDF (`fitz`). The
  PyInstaller `.spec` bundling for it is believed correct but **not yet
  exercised by an actual build**.
- 119-device preloaded library (see `task.md` #46 — earlier docs said "20
  devices," corrected 2026-07-29, Session 15). (The 15 procedural
  faceplate templates
  documented historically in `Changelog.txt` were already dead code by
  the time of Session 1's audit — unused by the actual rack canvas
  renderer — and the file was deleted in Session 5; see `task.md` #6.)

## Confirmed by Claude Code (2026-07-22, folder-structure pass)
- Real on-disk layout corrected — live tree is nested one level under the
  project root (originally `RackDesigner_v0.1.19/`; since Session 6,
  2026-07-24, the live tree is `RackDesigner_v0.1.20/` — see
  `folder_structure.md`).
- **No `.git` repository anywhere.** `project.md`'s earlier "local repo
  pushed to GitHub" description was wrong — corrected.
- `RarckDesigner History/RackDesigner_v0.1.19/` (archived snapshot) was
  byte-identical to `RackDesigner_v0.1.19/` (live tree) — not diverged, as
  of this check. **No longer true as of 2026-07-24 — see the divergence
  note further down.**
- `app/` is a proper Python package (`__init__.py` present).
- `preloaded_library.py` device images are fully inline/base64, no
  separate assets folder.

## Confirmed by project owner (2026-07-22)
- **Live/edited tree is `RackDesigner_v0.1.19/` (top level).**
  `RarckDesigner History/` is a pure archive of past-version snapshots, not
  a working copy.
  **Superseded 2026-07-24 (Session 6): live/edited tree is now
  `RackDesigner_v0.1.20/`** (duplicated from `RackDesigner_v0.1.19/` this
  session; the latter is now frozen, not a working copy either — see
  `folder_structure.md`).

## ⚠️ Live tree and archived History copy have now diverged (2026-07-24)
Confirmed via `diff -rq` on `app/`: as of Session 5, `RackDesigner_v0.1.19/`
(live) and `RarckDesigner History/RackDesigner_v0.1.19/` (archive) are
**no longer byte-identical** — expected, since Sessions 2–5 only ever
edited the live tree (`app/library_dialog.py`, `app/main_window.py`,
`app/pdf_export.py`, `app/rack_canvas.py`, `app/__init__.py`, plus
`app/faceplates.py` deleted from the live tree but still present in
History). This was flagged as a *future* risk in earlier sessions ("not
an active problem today only because the two trees still happen to be
byte-identical") — that condition no longer holds. This makes the
installer-path fix below more than a hygiene fix: had it not been fixed,
the installer would now be silently building from stale, pre-Session-2
code. `RarckDesigner History/` was correctly left untouched (it's a
frozen archive, not something to re-mirror into automatically) — noting
the divergence here for visibility, not as something to reconcile.

**2026-07-24, Session 6 addendum**: `RackDesigner_v0.1.19/` (containing
all of the above) was duplicated to `RackDesigner_v0.1.20/` this session,
then frozen. The `.iss` installer was deliberately **not** repointed at
`RackDesigner_v0.1.20/` this session (see `task.md` #4), so the
divergence described above is now between three trees, not two: the live
`RackDesigner_v0.1.20/`, the frozen `RackDesigner_v0.1.19/` (identical to
`RackDesigner_v0.1.20/` as of the copy, and to what the `.iss` currently
still builds from), and the older `RarckDesigner History/` archive
(furthest behind, missing Sessions 2–5 entirely).

## Fixed 2026-07-24 (Session 5)
- **Installer path** (`task.md` #4): `rack_designer_installer.iss`'s
  `[Files]` source was pointing at the archived
  `RarckDesigner History/RackDesigner_v0.1.19/dist/...` copy instead of
  the live tree's `RackDesigner_v0.1.19/dist/...` — corrected. Two related
  loose ends flagged, not fixed: `SetupIconFile=` still points at the
  History copy's icon, and the `.iss`'s hardcoded exe filename
  (`RackDesigner_v0.1.19.exe`, in `[Files]`/`[Icons]`/`[Run]`) no longer
  matches what `rack_designer.spec` will actually produce
  (`RackDesigner_v0.1.20.exe`) now that the version bumped. See `task.md`
  #4 and #10.
- **Dead code removed**: `app/faceplates.py` (unused faceplate renderer,
  15 templates) and a dead duplicate color-picker block in
  `DeviceForm.__init__` (`app/library_dialog.py`) — see `task.md` #6, #9.

## Full code audit (Session 7, 2026-07-24) — 53 new findings, none fixed yet
A full read-through audit of every module (10 parallel review passes,
each with targeted offscreen-Qt reproduction where practical) found 53
new, real defects beyond the three previously fixed. **None have been
fixed — this was an audit-only session, per explicit scope.** Full detail
per finding (file, function, trigger, live-repro status, severity) is in
`task.md`'s "Session 7 — Full code audit findings" section (items #12–64).
27 are assessed `likely-real-and-impactful`, 24 `real-but-minor`, 2
`needs-live-reproduction-to-confirm`.

Headline items most likely to affect real usage:
- **Silent data loss**: unsaved Project Info form edits (name/notes/etc.)
  discarded on New/Open with no prompt (#12); racks added in the Designer
  tab before the first Save can be silently wiped by a startup
  reference-swap bug (#25); the dirty flag is cleared before a save is
  confirmed to succeed, so a failed save can still let the app close/open
  a new project as if it worked (#26).
- **Data corruption via ordinary UI use**: reordering two same-named
  racks duplicates one and drops the other (#15); pasting/cross-rack
  dragging a multi-U tray uses the wrong height and creates overlapping
  slots (#47); the `rack_native` toggle can silently corrupt `height_mm`
  (#29); an unrecognized device category (reachable via JSON library
  import, #20) silently gets overwritten on next save (#30).
- **PDF export correctness**: device-list rows can show wrong per-unit
  watts/weight when same-named devices differ in spec, directly
  contradicting the correctly-summed project total in the same document
  (#55); long device/rack names overflow table cells and the rack diagram
  itself with no wrapping (#57, #58); a shrunk rack with now-out-of-range
  slots renders detached, bleeding into unrelated page content (#59).
- ~~**Storage layer**: `mm_to_u()` over-allocates a U for exact-multiple
  heights (#32); library/project saves aren't atomic and load failures
  are silently swallowed as "empty," a combination that can permanently
  destroy real data on a crash-mid-write (#33, #34, #45); CSV import has
  no non-UTF-8 fallback and aborts entirely on one bad byte (#35).~~ —
  **all but `mm_to_u()` (#32) fixed 2026-07-25 (Session 8)**, see below.
  #32 itself remains open (was not in Session 8's approved scope).
- ~~**Silent data loss**: unsaved Project Info form edits (name/notes/etc.)
  discarded on New/Open with no prompt (#12); racks added in the Designer
  tab before the first Save can be silently wiped by a startup
  reference-swap bug (#25); the dirty flag is cleared before a save is
  confirmed to succeed, so a failed save can still let the app close/open
  a new project as if it worked (#26).~~ — **all three fixed 2026-07-25
  (Session 9)**, see below.
- ~~**Rack canvas interaction**: rack reorder collapses two same-named
  racks into a duplicate (#15); sidebar rack selection never updated the
  "active" canvas, and the active canvas dangled on an orphaned widget
  after add/remove/edit/reorder (#14, #17); pasting/cross-rack-dragging a
  tray used the wrong height, causing overlap (#47); context-menu "Paste
  here" ignored the right-clicked cell (#48); Duplicate ignored the
  source's own bay (#49).~~ — **all six fixed 2026-07-28 (Session 10)**,
  see below.
- ~~**Form/dialog + import/categorie**: unrecognized device category
  silently falls back instead of being registered, both on load (#30)
  and via JSON import (#20); JSON merge-import can create duplicate
  device ids (#21); rack-size spinner arrows discard uncommitted typed
  text (#27); the rack_native toggle leaves a stale `height_mm`
  (#29).~~ — **all five fixed 2026-07-28 (Session 11)**, see below.
- ~~**PDF export**: device-list rows show wrong per-unit specs when
  same-named devices differ (#55); zero watts/weight renders as "—"
  (#56); long names overflow table cells (#57) and the rack diagram
  itself (#58); a shrunk rack with out-of-bounds slots renders detached
  (#59); grayscale export loses category differentiation (#61).~~ —
  **all six fixed 2026-07-28 (Session 12)**, see below. #60 (tall racks
  can leave the previous page blank) was investigated in Session 12 and
  **closed 2026-07-28 (Session 13) as decided-not-to-fix** — the project
  owner accepted the occasional cosmetic blank page rather than trade
  away the export's same-U-size-same-scale consistency guarantee; see
  `task.md` #60 for the full analysis.
- ~~**Math/validation**: `mm_to_u()` over-allocates a U on exact
  multiples (#32); CSV category normalization only uppercases the first
  character, missing case-insensitive matches (#36); CSV integer parsing
  used banker's rounding instead of ceiling (#37); loaded numeric fields
  bypassed the range clamps manual edits enforce (#31); `Rack`
  bay-scoped helpers didn't validate `bay` (#40).~~ — **all five fixed
  2026-07-28 (Session 13)**, see below.
- ~~**Two missed likely-real-and-impactful items**: rack-shrink
  off-by-one falsely blocked legal resizes (#16); cross-rack drop onto an
  existing tray never merged, rejected as "no space" instead (#51).~~ —
  **both fixed 2026-07-29 (Session 14)**, see below.

See `task.md`'s triage summary for the full sorted list. Not yet decided:
which of the remaining 19 items to fix next session, and in what order.

## Fixed 2026-07-25 (Session 8) — storage durability

Six Session 7 findings, all in `app/storage.py` (plus the call sites that
had to change alongside it): #33 (atomic writes for
library/categories/project saves — temp file + `os.replace()`), #34/#45
(load failures now distinguish "file doesn't exist" from "file is
corrupt" — a corrupt `library.json`/`custom_categories.json` is
quarantined aside, never deleted, and triggers a one-time "your library
was reset" notice instead of a silent reseed), #35 (CSV import now falls
back from `utf-8-sig` to `cp1252` instead of aborting on the first
non-UTF-8 byte), #38 (a corrupted/`null` slot inside an otherwise-valid
project file is now skipped with a summary dialog, instead of the whole
project failing to load), #39 (`save_project()` no longer mutates the
caller's in-memory `Project.name` as a save side effect — the caller now
applies the resolved deduped name explicitly).

Full detail per item in `task.md` (#33/#34/#35/#38/#39/#45, all now
`[done]`), the storage-layer error-handling model in `design.md`, and
verification detail (38 direct checks + 2 full app-launch runs + 2
real-widget UI flows, all offscreen-Qt) in `changelog.md`'s Session 8
entry.

`task.md` #32 (`mm_to_u()` exact-multiple rounding) and the rest of the
Session 7 backlog remain open — not in this session's approved scope.

## Fixed 2026-07-25 (Session 9) — dirty-flag / data-loss cluster

Three Session 7 findings, all in `app/main_window.py`: #12 (Project Info
form fields — name/number/venue/date/notes — now mark
`MainWindow._dirty`, via a new `ProjectSection.project_changed` signal
wired the same way `DesignerSection.project_changed` already was; typing
unsaved text and then choosing New/Open/Open-Recent/Ctrl+N/Ctrl+O now
correctly prompts instead of silently discarding it), #25 (`MainWindow`
now constructs one shared `Project()` at startup and passes it to both
`ProjectSection` and `DesignerSection`, instead of each building its own
independent object that got destructively swapped away on first save —
a rack added in the Designer tab before ever saving now survives the
first Save), #26 (`MainWindow._save()`'s `except` block now explicitly
restores `self._dirty = True` before showing the error dialog, so a
failed `storage.save_project()` no longer leaves the app thinking the
project was saved).

Full detail per item in `task.md` (#12/#25/#26, all now `[done]`), and
verification detail (23 direct checks including real `QTest`-driven
field edits and dialog-mocked end-to-end flows, sanity-reverts on #25/#26
confirming the tests catch the bugs, plus a real `main.py` startup-through-show
run) in `changelog.md`'s Session 9 entry.

`task.md`'s remaining 44 Session 7 backlog items are unchanged, still
`[todo]` — not in this session's approved scope.

## Fixed 2026-07-28 (Session 10) — rack canvas interaction cluster

Six Session 7 findings: #15 (rack reorder matched racks by `name`,
collapsing two same-named racks into a duplicate — fixed by matching on
`Rack.id`, which already existed in the data model and needed no schema
change), #14 + #17 (sidebar rack-row selection never updated
`DesignerSection._active_canvas`, and every add/remove/edit/reorder
rebuild left it pointing at a discarded widget — fixed together via a new
`_on_rack_row_selected()` and `_restore_active_canvas()`, both matching by
`Rack.id`), #47 (tray paste/cross-rack-drag always used `u_height=1`
regardless of the tray's real height, since `RackSlot.to_dict()` has no
top-level `u_height` key to fall back to — fixed by reading
`RackSlot.u_height` off the already-constructed slot instead), #48
(context-menu "Paste here" never forwarded the right-clicked cell into
the selection state, so it pasted near a stale selection instead — fixed
by setting `_selected_slot`/`_selected_u`/`_selected_bay` from the
right-clicked cell first), #49 (Duplicate blanked the selection to `-1`
before pasting, which — combined with `_kb_paste()`'s existing
"selected-is-source" guard — always fell through to a bay-0 search
regardless of the source's actual bay — fixed by targeting the source's
own bay/position instead of blanking).

Full detail per item in `task.md` (#14/#15/#17/#47/#48/#49, all now
`[done]`), the rack-identity and active-canvas-tracking model in
`design.md`, and verification detail (26 direct/sanity-revert checks plus
2 real `QTest`-driven end-to-end flows on an actual `MainWindow`, all
offscreen-Qt) in `changelog.md`'s Session 10 entry.

`task.md`'s remaining 38 Session 7 backlog items are unchanged, still
`[todo]` — not in this session's approved scope.

## Fixed 2026-07-28 (Session 11) — form/dialog + import/categorie cluster

Five Session 7 findings: #20 + #30 (unrecognized device category
silently fell back instead of being registered, on both JSON import and
`DeviceForm.load()` — fixed together via one new shared helper,
`storage.register_category_if_unknown()`, also now used by the
pre-existing CSV import path for consistency), #21 (JSON merge-import
could create duplicate device ids — merge dedup now also checks/repairs
`id` collisions, assigning a fresh uuid to the incoming device rather
than ever touching the existing one), #27 (rack-size spinner arrows
discarded uncommitted typed text — arrow clicks now commit the typed
value first, same parse+clamp as `editingFinished`, before applying the
step), #29 (the `rack_native` toggle left a stale `height_mm` — toggling
back to rack-native now clears it; `width_mm` was checked for the same
gap per the brief and found not to have one, since it was never disabled
in the first place).

Full detail per item in `task.md` (#20/#21/#27/#29/#30, all now
`[done]`), the new shared category-registration mechanism in
`design.md`, and verification detail (20 direct/sanity-revert checks
plus a real `QTest.mouseClick` on an actual spinner button, all
offscreen-Qt) in `changelog.md`'s Session 11 entry.

`task.md`'s remaining 33 Session 7 backlog items are unchanged, still
`[todo]` — not in this session's approved scope.

## Fixed 2026-07-28 (Session 12) — PDF export cluster

Six Session 7 findings, all in `app/pdf_export.py`: #55 (device-list
rows now group by `(name, watts, weight_kg, category)`, not name alone,
so same-named devices with different specs get their own accurate row),
#56 (0 watts/kg now renders as a real zero, not "—"), #57 (long
device/category/rack names now wrap within their table cell via
`Paragraph`, instead of overflowing into neighboring columns), #58 (long
device names in the rack diagram now truncate with an ellipsis to fit,
measured via real font metrics), #59 (a shrunk rack with out-of-bounds
slots now renders fully self-contained — drawing geometry uses the
greater of `rack.u_size` and the actual occupied extent), #61 (grayscale
export now runs each slot's category color through the previously-dead
`_to_gray()` helper, so categories stay visually distinguishable instead
of one flat neutral).

#60 (tall racks can leave the previous PDF page mostly blank) was
investigated per the session brief but **not fixed** — every fix that
would genuinely eliminate the blank-space symptom requires
`RackDrawing` to react to the real remaining page space, which
ReportLab's Platypus model only exposes at real build time (not while
`story` is being constructed), and the one option that would actually
work (an adaptive `wrap()`) trades away the export's current guarantee
that a rack's rendered scale depends only on its own spec, not on
surrounding page content. Hit the brief's own stop condition; see
`task.md` #60 for the full option-by-option analysis and
recommendation, pending a project-owner decision on that trade-off.

Full detail per item in `task.md` (#55/#56/#57/#58/#59/#61, all now
`[done]`; #60 investigated, still `[todo]`), the updated "PDF export"
section in `design.md`, and verification detail (33 direct/sanity-revert
checks plus PyMuPDF-rendered PNG visual inspection for the four visual
findings #57/#58/#59/#61) in `changelog.md`'s Session 12 entry.

`task.md`'s remaining 27 Session 7 backlog items (including #60) are
unchanged, still `[todo]` — not in this session's approved scope.

## Closed 2026-07-28 (Session 13) — #60 decided-not-to-fix

No code change. Project owner reviewed Session 12's trade-off analysis
for `task.md` #60 (tall racks can leave the previous PDF page mostly
blank) and chose to accept the occasional cosmetic blank-page behavior
rather than trade away the export's guarantee that a rack's rendered
scale depends only on its own spec, not on surrounding page content.
Marked `[done]`/decided-not-to-fix in `task.md` — closed, not merely
left open.

## Fixed 2026-07-28 (Session 13) — math/validation cluster

Five Session 7 findings: #32 (`mm_to_u()` now subtracts a `1e-9` epsilon
before ceiling, so an exact multiple of `RACK_U_MM` no longer
over-allocates a U), #36 (CSV category import now matches
case-insensitively against the known set first, reusing the existing
category's casing, before falling back to Title-Case-and-register for a
genuinely new one), #37 (CSV `Height (U)` parsing now ceilings instead
of using Python's banker's-rounding `round()` — confirmed via grep this
is the only call site `_parse_int()` has), #31 (`DeviceForm.load()`'s
numeric fields now clamp to their declared range the same way manual
typing/arrow-stepping already does — fixed at the shared spin-widget
`.setValue()` implementation, covering every caller), #40 (`Rack`
bay-scoped helpers' assumption that every slot's `bay` is in-range is now
enforced once, in `Rack.from_dict()`, rather than patched into each
helper individually).

Two items had explicit investigate-first conditions in the brief:
- **#37**: confirmed via grep that `_parse_int()` has exactly one call
  site anywhere in the live tree (the CSV `Height (U)` column), so the
  ceiling fix was safe to apply directly.
- **#40**: chose to normalize `bay` once in `Rack.from_dict()` rather
  than validate it in all four bay-scoped helpers, since the only
  realistic path to an out-of-range `bay` is a corrupted `.rackproj` file
  (nothing in the live UI can produce one) — see `task.md` #40 for the
  full reasoning.

Full detail per item in `task.md` (#31/#32/#36/#37/#40, all now
`[done]`), the updated "Multi-bay racks"/"Non-rack-native devices"/
"Category registration" sections in `design.md`, and verification detail
(38 direct/sanity-revert checks) in `changelog.md`'s Session 13 entry.

`task.md`'s remaining 21 Session 7 backlog items are unchanged, still
`[todo]` — not in this session's approved scope.

## Fixed 2026-07-29 (Session 14) — two missed likely-real-and-impactful items

Two Session 7 findings that had been triaged `likely-real-and-impactful`
but not yet picked up in Sessions 8-13: #16 (`DesignerSection._edit_rack()`'s
rack-shrink occupancy check off-by-one — `range(1, 1 - delta + 1)` covered
one row too many, falsely blocking legal shrinks; now
`range(1, -delta + 1)`), #51 (`RackCanvas.dropEvent()`'s cross-rack branch
never attempted a tray merge the way the library-device-drop branch
already did — a non-rack-native device dragged from another rack onto an
existing tray with room was rejected as "no space"; it now attempts the
same `_can_add_to_tray()`/`_add_to_tray()` merge first).

Full detail per item in `task.md` (#16/#51, both now `[done]`), the
updated "Non-rack-native devices / trays" section in `design.md`, and
verification detail (14 direct/sanity-revert checks) in `changelog.md`'s
Session 14 entry.

`task.md`'s remaining 19 Session 7 backlog items are unchanged, still
`[todo]` — not in this session's approved scope.

## Fixed 2026-07-29 (Session 15) — preloaded library data cluster

Four Session 7 findings, all data-only corrections in
`app/preloaded_library.py` (no logic changes), plus one
documentation-only item: #41 (fresh installs no longer register a
redundant "Lighting" custom category — `_EXTRA_CATEGORIES` emptied;
existing installs' already-written duplicate is not retroactively
cleaned up), #42/#43 (two copy-pasted `model` strings corrected —
"Disguise GX 3" → `"GX 3"`, "Barco E2" → `"E2"` — internal-consistency
corrections, not verified against vendor spec sheets), #44 (two
implausible `depth_mm` values corrected via sibling-device
cross-comparison — "Blackmagic MultiView 16" → `170.0`, "UPS 5P 1150" →
`438.0` — also not vendor-verified), #46 (docs' stale "20-device" claim
corrected to the real, reconfirmed count of 119 in
`folder_structure.md`/`design.md`/`status.md`).

Full detail per item in `task.md` (#41/#42/#43/#44/#46, all now
`[done]`) and verification detail (offscreen-Qt library reseed + real
`MainWindow` construction, plus a fresh device-count grep) in
`changelog.md`'s Session 15 entry.

`task.md`'s remaining 15 Session 7 backlog items are unchanged, still
`[todo]` — not in this session's approved scope.

## Fixed 2026-07-29 (Session 16) — startup robustness cluster

Three Session 7 findings, in `main.py` (#62, #63) and `app/dialogs.py`
(#64): #62 (an exception during first-run library seeding no longer
kills the app before the window appears — `main()` now wraps the
`seed_library_if_empty()` call in `try/except`, logs via a new shared
`_log_crash()`, and still constructs/shows `MainWindow` regardless,
with a new `_notify_seed_failed()` dialog explaining the situation
afterward), #63 (a pre-`QApplication` startup exception — broken Qt
platform plugin, or an import-time failure — no longer vanishes
silently; a new, deliberately Qt/`app`-package-independent
`_log_pre_qt_crash()` now guards `main.py`'s top-of-file imports and
the `QApplication(sys.argv)` call itself, writing to `crash.log` before
re-raising; no dialog is possible at this stage, so disk logging is the
explicit ceiling), #64 (`MsgBox`/`_MsgDialog` now coerces
`title`/`message` to `str()`, so a future non-string call site — #62's
own new `_notify_seed_failed()` being the first to matter — can't make
the error-reporting dialog itself raise `TypeError`).

`main.py`'s startup error handling is now a documented three-layer
model (`design.md`): Layer 1 (Session 3) covers the running event loop,
Layer 2 (this session) covers first-run seeding, Layer 3 (this session)
covers everything before `QApplication` exists.

Full detail per item in `task.md` (#62/#63/#64, all now `[done]`,
including #63's explicit note on what is and isn't testable without a
genuinely broken Qt install) and verification detail in `changelog.md`'s
Session 16 entry.

`task.md`'s remaining 12 Session 7 backlog items are unchanged, still
`[todo]` — not in this session's approved scope.

## Fixed 2026-07-29 (Session 17) — final cleanup, 11 minor/cosmetic items

The last 11 Session 7 findings, all `real-but-minor` or informational:
#13 (failed recent-project load leaves the wrong row selected), #18
(Designer category filter never refreshed), #19 (misleading 0-rack
message), #22 (merge-import dedup set stale within the same import),
#23 (CSV export silently dropped images, no warning), #24 (empty-library
category-scope export dead-end), #28 (rack-size preset combobox didn't
stay in sync), #50 (drag state ignored which mouse button was
released), #52 (library-device drop "no space" didn't ignore the
event), #53 (hover-preview highlight not clamped to rack bounds), #54
(editing a tray slot's name was silently discarded — fixed by removing
the name field entirely for trays, not by inventing a new "tray label"
data field).

**This closes out the Session 7 audit backlog.** All 53 original
findings from the Session 7 full code audit (2026-07-24) are now
resolved — fixed across Sessions 8–17, or explicitly decided-not-to-fix
in #60's case (Session 13, tall-rack PDF page-break trade-off).

Full detail per item in `task.md` (#13/#18/#19/#22/#23/#24/#28/#50/#52/
#53/#54, all now `[done]`) and verification detail (one bundled
offscreen-Qt script covering all 11 items, with sanity-reverts for the
three non-trivial fixes) in `changelog.md`'s Session 17 entry.

## Added 2026-07-29 (Session 18) — new feature: export rack diagrams as PNG

First new-feature session since the Session 7 audit backlog closed out
completely (Session 17). "EXPORT RACKS AS PNG" in the Export tab exports
one PNG per rack, at natural (uncapped) size, via a new
`app.pdf_export.export_rack_png()` — built on a new `RackDrawing(...,
page_fit=False)` mode (default `page_fit=True` keeps existing PDF export
behavior byte-for-byte unchanged) rendered through an in-memory PDF and
rasterized via PyMuPDF. New runtime dependency: `PyMuPDF>=1.24.0`
(`requirements.txt`); `rack_designer.spec` gained `collect_all()`-based
PyInstaller bundling for it (a known gotcha for this package) — **not
yet exercised by an actual build**.

Full detail in `task.md` #65 (new "Features" section — fresh numbering,
the Session 7 audit's #1–#64 range is fully closed), the new "PNG
export" section in `design.md` (mechanism, and why it reuses
`RackDrawing` instead of a second renderer), and verification detail
(page_fit=True regression confirmed numerically identical to the
pre-Session-18 formula; PNG pixel dimensions confirmed against the DPI
math; visual confirmation that the Session 12 PDF-export fixes — name
truncation, out-of-bounds containment, grayscale shading — carry over
automatically; real `QTest.mouseClick`-driven UI verification including
same-name-collision dedup and per-rack failure isolation) in
`changelog.md`'s Session 18 entry.

**Resolved 2026-07-29 (Session 19)**: the scope note above was the one
open question from Session 18. The project owner confirmed PNG export
should respect the Export tab's "RACKS TO INCLUDE" checkboxes, the same
as PDF export already does — `ExportSection._do_export_png()` now
filters to only the checked racks via the identical expression
`_do_export()` (PDF) already used, and shows the same "Select at least
one rack." message for the 0-selected case. See `task.md` #65's
addendum and `changelog.md`'s Session 19 entry for full detail.

## Not yet verified in this pass
- Full code audit now complete (see above) — the three previously-fixed
  bugs are very likely not the only ones, confirmed.
- **Update 2026-07-25 (Session 8)**: 6 of the 53 findings (#33, #34, #35,
  #38, #39, #45 — the storage-durability cluster) are now fixed and
  verified — see above.
- **Update 2026-07-25 (Session 9)**: 3 more findings (#12, #25, #26 —
  the dirty-flag/data-loss cluster) are now fixed and verified — see
  above.
- **Update 2026-07-28 (Session 10)**: 6 more findings (#14, #15, #17,
  #47, #48, #49 — the rack canvas interaction cluster) are now fixed and
  verified — see above.
- **Update 2026-07-28 (Session 11)**: 5 more findings (#20, #21, #27,
  #29, #30 — the form/dialog + import/categorie cluster) are now fixed
  and verified — see above.
- **Update 2026-07-28 (Session 12)**: 6 more findings (#55, #56, #57,
  #58, #59, #61 — the PDF export cluster) are now fixed and verified —
  see above. #60 was investigated, not fixed (stop condition hit, see
  `task.md` #60).
- **Update 2026-07-28 (Session 13)**: #60 closed as decided-not-to-fix
  (no code change). 5 more findings (#31, #32, #36, #37, #40 — the
  math/validation cluster) are now fixed and verified — see above.
- **Update 2026-07-29 (Session 14)**: 2 more findings (#16, #51 — two
  previously-missed likely-real-and-impactful items) are now fixed and
  verified — see above.
- **Update 2026-07-29 (Session 15)**: 4 more findings (#41, #42, #43,
  #44 — the preloaded library data cluster) plus 1 documentation-only
  item (#46) are now fixed/corrected and verified — see above.
- **Update 2026-07-29 (Session 16)**: 3 more findings (#62, #63, #64 —
  the startup robustness cluster) are now fixed and verified — see
  above.
- **Update 2026-07-29 (Session 17)**: the final 11 findings (#13, #18,
  #19, #22, #23, #24, #28, #50, #52, #53, #54) are now fixed and
  verified — see above. **All 53 of the original Session 7 findings are
  now resolved** — 52 fixed, 1 (#60) explicitly decided-not-to-fix. No
  Session 7 backlog items remain open.
