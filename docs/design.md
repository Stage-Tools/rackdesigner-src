# RackDesigner — Design

> **Path note (updated 2026-07-24, Session 6):** paths below are given
> relative to the live source tree — now `RackDesigner_v0.1.20/`, not the
> project root. `RackDesigner_v0.1.19/` (the previous live tree) was
> duplicated into `RackDesigner_v0.1.20/` this session and is now a frozen
> snapshot as of 2026-07-24; all further edits happen in
> `RackDesigner_v0.1.20/`. See `folder_structure.md` for the full layout,
> including the archived `RarckDesigner History/` mirror.

## Module map

| Module | Responsibility |
|---|---|
| `main.py` | Entry point. Creates `QApplication`, applies stylesheet/font, installs the top-level `sys.excepthook` (see below), seeds the preloaded library if empty, shows `MainWindow`. |
| `app/models.py` | Data model: `DeviceDefinition`, `RackSlot`, `Rack`, `Project`. Dataclasses with `to_dict`/`from_dict` for JSON (de)serialization. Category/color helpers, mm↔U conversion. |
| `app/storage.py` | Persistence layer: library, custom categories, project files (`.rackproj`), CSV library import. All reads/writes to `%APPDATA%\RackDesigner\`. |
| `app/style.py` | Global QSS stylesheet, palette constants. |
| `app/dialogs.py` | Generic message dialogs (`MsgBox`) replacing default Qt dialogs, styled to match the app theme. |
| `app/library_dialog.py` | Device library editing widgets: color picker, image picker, category combo, full device edit form. |
| `app/rack_canvas.py` | The interactive rack canvas: painting, drag & drop (from library, between slots, between racks), keyboard shortcuts, per-canvas undo, context menu, zoom/fit. This is the most complex and highest-risk module. |
| `app/pdf_export.py` | PDF generation via ReportLab: `RackDrawing` (rack diagram flowable), device list tables, project summary, footer. |
| `app/preloaded_library.py` | Seed data for the default 119-device library, loaded on first run only. |
| `app/main_window.py` | All UI sections/tabs (`ProjectSection`, `DesignerSection`, `ExportSection`, `LibrarySection`, `AboutSection`), top nav bar, add/edit rack dialogs, `MainWindow` shell. ~2250 lines — largest module by far. |

## Data model

```
Project
 └── racks: list[Rack]
      └── slots: list[RackSlot]
           ├── device_snapshot: dict   (copy of DeviceDefinition at insert time)
           └── tray_devices: list[dict] (present only when the slot is a tray)
```

Key design decision: **`RackSlot` stores a snapshot, not a live reference**,
of the device (`device_snapshot`). Once a device is placed in a rack, editing
or deleting it from the library does not retroactively change existing
projects. `device_id` is kept for traceability but is not resolved at
render/export time.

### Multi-bay racks
`Rack.bays` (1–3) — side-by-side columns within one rack frame, each with its
own independent slot numbering. `RackSlot.bay` (0-indexed) identifies which
column a slot belongs to. Occupancy checks (`is_slot_occupied`,
`next_free_position`, `slot_at`) are all bay-scoped and assume every slot's
`bay` is already within `[0, bays)` — they don't validate it themselves.
That assumption is enforced once, at the data's entry point:
`Rack.from_dict()` clamps every loaded slot's `bay` into range (added
2026-07-28, Session 13 — see `task.md` #40) immediately after
construction, rather than each helper re-checking it individually. The
only realistic way to get an out-of-range `bay` is a corrupted/
hand-edited `.rackproj` — nothing in the live UI can produce one (every
UI path derives `bay` from `_point_to_bay_u()`, already clamped, and
`EditRackDialog` has no bays-editing field at all).

### Rack identity
`Rack.id` (a UUID, `default_factory=uuid4`, present since before this
documentation was written) is the stable identity for a rack across UI
operations — serialized in `to_dict()`/`from_dict()`, with `from_dict()`
generating a fresh id for any `.rackproj` written before the field
existed, so old project files load safely. `Rack.name` is *not* unique
(`AddRackDialog` defaults every new rack to the literal "New Rack" with
no uniqueness check) and must never be used to re-associate a `Rack`
object with its sidebar row/UI representation after a rebuild — doing so
was the root cause of `task.md` #15 (two same-named racks collapsing into
one on reorder), fixed 2026-07-28 (Session 10) by switching
`DesignerSection`'s reorder/active-canvas matching from `name` to `id`.
`app/main_window.py`'s `rack_list` items now carry `rack.id` via
`Qt.ItemDataRole.UserRole` for this reason.

### Non-rack-native devices / trays
`DeviceDefinition.rack_native` (bool):
- `True` — standard 19" device, height given directly in `u_height`.
- `False` — device with physical `width_mm` / `height_mm`; effective U height
  is derived via `mm_to_u()`. Devices narrower than full rack width
  (`RACK_INNER_WIDTH = 482mm`) can share a slot with others, forming a
  **tray** (`RackSlot.tray_devices`, non-empty list). A slot is either a
  normal single-device slot or a tray — `RackSlot.is_tray` distinguishes the
  two, and most `RackSlot` properties (`name`, `watts`, `weight_kg`,
  `effective_color`, `u_height`) branch on this.

Merging into an existing tray (`_can_add_to_tray()`/`_add_to_tray()` in
`rack_canvas.py`) is now attempted from both drop sources that can
deliver a non-rack-native device onto an occupied slot — the
library-device drag (always could) and the cross-rack slot drag (added
2026-07-29, Session 14 — see `task.md` #51; previously this path always
fell through to the occupied/free-space check and rejected a
tray-eligible drop as "no space"). The cross-rack path builds a
`DeviceDefinition` from the dropped `RackSlot.device_snapshot` to reuse
the same merge helpers, since they're written against a `DeviceDefinition`
object, not a raw snapshot dict.

`mm_to_u()` subtracts a `1e-9` epsilon before `math.ceil()` (added
2026-07-28, Session 13 — see `task.md` #32) so a `height_mm` that's an
*exact* multiple of `RACK_U_MM` (44.45) doesn't over-allocate a full extra
U from floating-point division error (`3*44.45` used to compute to 4U,
not 3U). Non-exact heights round up exactly as before.

**Note:** none of this (`rack_native`, `width_mm`/`height_mm`, trays, CSV
library import) appears in `Changelog.txt` up to v0.1.19. See
`status.md` / `changelog.md` for the documentation gap.

### Category registration
`app.models.get_categories()` is the single source of truth for "which
categories currently exist" (`DEFAULT_CATEGORIES` + whatever's in
`custom_categories.json`). Three separate places can encounter a category
string that isn't in that set yet — a CSV import row, a JSON-imported
device, or opening an existing device whose category was since
deleted/renamed/never-registered locally — and all three now go through
one shared decision point, `storage.register_category_if_unknown()`
(added 2026-07-28, Session 11 — see `task.md` #20/#30): if the category
isn't known, register it via `add_custom_category()`; return it unchanged
either way. Before this, only the CSV path registered unknown categories;
JSON import silently dropped them and `DeviceForm.load()` silently fell
back to whatever the category combo defaulted to (not even the model's
own `"Other"` fallback) — in both cases, a subsequent no-op save would
overwrite the device's real category via the blind `setattr(dev, k, v)`
loop in `LibrarySection._save()`, the same failure shape as the
previously-fixed image-wipe bug (#5).

**CSV import matches case-insensitively before normalizing** (added
2026-07-28, Session 13 — see `task.md` #36): `import_library_csv()`
checks an imported category against the known set ignoring case first,
reusing the existing category's real casing on a match (`"AUDIO"` →
`"Audio"`, not a new near-duplicate category). Only a genuinely new
category (no case-insensitive match at all) gets Title-Cased and
registered via `register_category_if_unknown()`.

### Faceplates (removed)
`app/faceplates.py` (15 `fp_*(painter, x, y, w, h, slot)` template
functions + a `draw_faceplate()` dispatcher, purely procedural QPainter
rendering) was already dead code — unreferenced by `main_window.py` or
`rack_canvas.py`, per `Changelog.txt` v0.1.10's note that the canvas
renderer had stopped using it. Deleted 2026-07-24 (Session 5, `task.md`
#6) after re-confirming zero references anywhere in the live tree.
Device rendering on the actual rack canvas does not use faceplates —
see `rack_canvas.py`'s `paintEvent()`.

### Undo
Per-`RackCanvas` instance, `deque(maxlen=UNDO_LIMIT)` of full-slot-list JSON
snapshots (`_push_undo` / `undo` in `rack_canvas.py`). **Undo is local to one
rack's canvas** — there is no cross-rack/global undo. A cross-rack move
therefore pushes two independent, uncoordinated undo entries (one per
canvas).

Ctrl+Z is dispatched by `DesignerSection.undo()` to whichever
`RackCanvas` is currently `DesignerSection._active_canvas` — so undo
correctness depends on `_active_canvas` actually pointing at the
on-screen canvas the user is looking at. Two things keep it that way
(both added/fixed 2026-07-28, Session 10, `task.md` #14/#17):
- `RackCanvas.became_active` (clicking inside a canvas) and
  `rack_list.currentRowChanged` (clicking a rack's sidebar row) both
  route through `_on_canvas_active()`, so either interaction updates
  `_active_canvas` identically.
- Every operation that discards and rebuilds all `RackCanvas` widgets
  (`_add_rack`/`_remove_rack`/`_edit_rack`/`_on_rack_reordered`, all via
  `_clear_racks()` + `_refresh_rack_view()`) captures the previously-active
  rack's `id` beforehand and calls `_restore_active_canvas(prev_rack_id)`
  afterward, which finds the matching rack's *new* canvas (falling back to
  the first canvas, or `None`, if that rack no longer exists). Before this,
  `_active_canvas` was left pointing at the just-discarded widget after
  any of those four operations — Ctrl+Z still mutated the right `Rack`
  data (the data object survives the rebuild) but repainted an invisible,
  orphaned widget instead of the visible one.

### Project object lifecycle (changed Session 9, 2026-07-25)

`MainWindow` owns exactly one `Project()` instance, constructed once in
`_build()` and passed by reference to both `ProjectSection` and
`DesignerSection` at construction time (`ProjectSection(project=...)`,
`DesignerSection(project=...)`) — both classes accept an optional
`project=` parameter, defaulting to a fresh `Project()` if omitted so
each remains independently constructible. Because `Project` is mutable
and both sections hold the *same* object, a rack added directly via
`DesignerSection` (e.g. before the user ever visits the Project tab) is
immediately visible through `proj_section.project` too — there is no
window where the two tabs disagree about which project is open.

Before this, each section constructed its own independent default
`Project()`; they were unified only when something (any Save,
New/Open/Open-Recent) fired `ProjectSection.project_loaded`, which
`MainWindow._on_project_loaded()` handles by reassigning
`self.designer.project = project` — a destructive full-reference swap,
not a merge. Any racks added directly in the Designer tab before that
first unifying event were silently discarded along with the
now-orphaned old object (`task.md` #25). New/Open/Open-Recent/Save still
go through that same reassignment today — it's harmless now (both
references already point at the same object, so reassigning is a no-op
in practice) and was left as-is rather than removed, since it's also how
a *different* project (opened from disk, or a fresh one from New)
correctly becomes the one both sections share going forward.

`ExportSection` still constructs its own independent `Project()` and is
**not** part of this shared-reference change — it's read-only (never
mutated directly) and is explicitly re-synced both on tab-switch
(`MainWindow._switch()`) and on every `project_loaded` event, so it never
has a window where it could diverge and cause data loss the way
`ProjectSection`/`DesignerSection` could.

## PDF export
`RackDrawing` (a ReportLab `Flowable`) draws one rack per call: grid, slots
(with category-derived or custom color), U labels, auto-scaling if the
natural height exceeds the printable page height. Device list is grouped by
`(name, watts, weight_kg, category)` (changed Session 12, 2026-07-28 — was
`name` alone, see `task.md` #55), so devices that merely share a name but
differ in spec get their own row instead of silently reporting the first
match's numbers for all of them; devices matching on all four still
collapse into one row with a multiplied qty (quantity + concatenated
distinct notes).

**Drawing geometry doesn't trust `rack.u_size` blindly** (Session 12):
`RackDrawing.__init__()` computes `self._draw_u_size =
max(rack.u_size, occupied_top)`, where `occupied_top` is the highest
`position_u + u_height - 1` among the rack's own slots — a rack shrunk
below an already-occupied position (reachable since `EditRackDialog`'s
U-size shrink path has no occupancy guard, `task.md` #16/#59) still
renders fully self-contained instead of drawing part of a slot outside
the frame. `rack.u_size` itself, and everything derived from it elsewhere
(`Rack.used_u()`/`free_u()`, the "NU rack · used · free" text), is
unaffected — this only changes `RackDrawing`'s own drawing geometry.

**Slot colors, in both color and grayscale mode, go through one function**
(`_slot_colors()`, Session 12): the accent/background/border blend is
computed identically in both modes, starting from either the slot's raw
category/device color (`use_color=True`) or that same color run through
`_to_gray()` first (`use_color=False`) — so grayscale exports still
visually distinguish categories by gray shade, instead of every slot
sharing one flat neutral fill (`task.md` #61). Long device names are
truncated to fit their slot (measured via `c.stringWidth()`, ellipsis
appended) rather than overflowing past the rack's border (`task.md`
#58); the same wrap-instead-of-overflow treatment was applied to the
device-list and project-summary tables' free-text cells via
`Paragraph`-wrapped cells (`task.md` #57).

**Known limitation, investigated not fixed (`task.md` #60):** a rack
whose diagram is close to the page-height budget can get pushed entirely
to a fresh page even when the current page has room for everything but
the diagram, leaving the current page mostly blank. Actually eliminating
this would require `RackDrawing` to react to the real remaining frame
height — only knowable via the Flowable `wrap()` protocol at real
`doc.build()` time, not during `story` construction — which would make a
rack's rendered scale depend on surrounding page content instead of only
its own U-size/bay-count, a real trade-off against the export's current
size-consistency guarantee. See `task.md` #60 for the full per-option
analysis; not fixed pending a product decision on that trade-off.

## PNG export (added Session 18, 2026-07-29)

`app.pdf_export.export_rack_png(rack, filepath, use_color=True, dpi=300)`
renders one rack diagram to a standalone PNG file, reachable from the
Export tab's new "EXPORT RACKS AS PNG" button (`ExportSection._do_export_png()`,
`app/main_window.py`). See `task.md` #65.

**Deliberately reuses `RackDrawing` instead of a second renderer.** The
obvious alternative — a PNG-specific drawing routine, or driving
`RackDrawing` through QPainter/Qt directly instead of ReportLab — was
rejected: `RackDrawing.draw()` already contains every PDF-export
correctness fix from the Session 12 audit cluster (device-name truncation
via `_truncate_text()`, out-of-bounds-slot self-containment via
`_draw_u_size`, grayscale per-category shading via `_slot_colors()`). A
second renderer would either have to duplicate all of that logic (with
every future fix needing to land twice, one being trivially easy to
forget) or would launch already missing it. Instead, PNG export is a
*rendering pipeline* wrapped around the exact same `RackDrawing.draw()`
call `export_pdf()` already makes — one drawing routine, two output
formats.

**The pipeline**: `RackDrawing` gained a third constructor parameter,
`page_fit: bool = True` (default preserves the existing `export_pdf()`
behavior byte-for-byte — nothing about the multi-rack PDF document path
changed this session). `export_pdf()` never passes `page_fit=False`, so
every rack in a full PDF document is still scaled down to fit
`MAX_RACK_H`/`MAX_RACK_W` exactly as before. `export_rack_png()` is the
only caller that passes `page_fit=False`: `RackDrawing.__init__()` then
skips the `scale_h`/`scale_w` computation entirely, forces `self._scale =
1.0`, and sets `self.width`/`self.height` directly to the natural
(uncapped) drawing size — a 45U/3-bay rack renders at its own true size,
never shrunk to fit an A4 page, since there's no page to fit onto.
`export_rack_png()` then:
1. Builds `RackDrawing(rack, use_color, page_fit=False)`.
2. Opens a bare ReportLab `Canvas` (not a `SimpleDocTemplate` — there's no
   document structure to build, just one drawing) sized exactly to
   `drawing.width`/`drawing.height`, writing into an in-memory
   `io.BytesIO()` rather than a file — the PDF never touches disk.
3. Calls `drawing.drawOn(c, 0, 0)` — the standard `Flowable` method that
   binds `self.canv` and invokes `draw()` — followed by `showPage()`/
   `save()`.
4. Opens that in-memory single-page PDF via PyMuPDF (`fitz.open(stream=...,
   filetype="pdf")`), rasterizes page 0 through `get_pixmap(matrix=
   fitz.Matrix(zoom, zoom))` where `zoom = dpi / 72.0` (PDF points are
   natively 72/inch, so this is the same math a "300 DPI" export means
   anywhere else), and writes the resulting `pix.tobytes("png")` to
   `filepath`.

**Why PyMuPDF, and why imported lazily.** ReportLab can produce PDF but
has no built-in PDF→raster rasterizer; PyMuPDF (imported as `fitz`) was
already informally relied on in prior sessions' own scratchpad
verification scripts (rendering PDF pages to PNG for visual inspection of
the Session 2/12 audit fixes) before this session made it a real runtime
dependency (`requirements.txt`; see `task.md` #65 for the PyInstaller
`collect_all('pymupdf')`/`collect_all('fitz')` bundling note in
`rack_designer.spec` — PyMuPDF's compiled extensions and `mupdfcpp64.dll`
are a known static-analysis gotcha for PyInstaller, not reliably picked
up without it). `export_rack_png()` imports `fitz` (and
`reportlab.pdfgen.canvas`) locally, inside the function, rather than at
`pdf_export.py`'s module level — a broken/missing PyMuPDF install should
only break this one optional feature the moment a user actually clicks
"Export racks as PNG," not prevent the whole app (including ordinary
rack design and plain PDF export, neither of which need it) from
starting at all. This mirrors the same failure-isolation principle
behind the three-layer startup error handling above (`main.py`).

**UI-level filename handling** (`ExportSection._do_export_png()`,
`app/main_window.py`): the destination is a folder (`QFileDialog.
getExistingDirectory`), not a single file, since this exports one PNG per
rack — one per *checked* rack in the Export tab's "RACKS TO INCLUDE"
list, the same `[r for r, c in self._rack_checkboxes if c.isChecked()]`
selection the PDF export ("EXPORT PDF") already uses, not unconditionally
every rack in the project (Session 18 originally always exported every
rack regardless of that checkbox state; corrected in Session 19 —
`task.md` #65's addendum — for consistency between the two export
actions). Each rack's filename is sanitized with the exact same character
filter `storage.save_project()` already uses for project→filename
sanitization (alnum + space/underscore/hyphen only, spaces → underscores),
duplicated locally as `ExportSection._sanitize_filename()` rather than
imported, since `storage.py`'s version is inlined at its one call site and
not exposed as a reusable helper. Collisions — two racks sharing a name,
two different names that happen to sanitize to the same string, or a
same-named file already sitting in the destination folder from a prior
export run — are all resolved the same way `storage.save_project()`
resolves a project-name collision: append `" (2)"`, `" (3)"`, etc.,
checked against both the other racks already placed in this batch and
the filesystem, so a batch export never silently overwrites anything. A
per-rack export failure (caught around each individual
`export_rack_png()` call) doesn't abort the batch — it's recorded and the
next rack is attempted — and the completion dialog reports how many
succeeded, the destination folder, and every per-rack failure by name.

## Storage layer error handling (added Session 8, 2026-07-25)

`app/storage.py` is the only module that touches disk (library, custom
categories, project files, CSV import) and, as of Session 8, follows one
consistent model across all of it:

**Writes are atomic.** `save_library()`, `save_custom_categories()`, and
`save_project()` all go through `_atomic_write_json()`: write to a
sibling `<target>.tmp`, `flush()` + `os.fsync()`, then `os.replace()`
onto the real target. `os.replace()` is atomic on the same filesystem
(always true here — the tmp file is always written next to its target),
so a crash or kill at any point during a save leaves either the
untouched old file or the fully-written new one — never a
truncated/corrupt in-between state.

**Reads distinguish "doesn't exist" from "exists but is corrupt," and
treat app-owned files differently from user-owned ones:**
- `load_library()` / `load_custom_categories()` (app-owned — the app
  fully controls this file's format and can regenerate it) return a
  `LoadResult` (`.items`, `.was_corrupt`, `.backup_path`) instead of a
  bare list. A missing file is the legitimate empty case
  (`was_corrupt=False`). A file that exists but fails to parse is
  **quarantined** — renamed to `<name>.corrupt-<timestamp>.json` in the
  same directory, original bytes never deleted — a warning is appended
  to `%APPDATA%\RackDesigner\crash.log` (reusing the same log file/format
  `main.py`'s `sys.excepthook` writes to), and `was_corrupt=True` is
  returned so a caller that cares (currently only
  `preloaded_library.seed_library_if_empty()`) can react differently
  from a genuine first run. Callers that just want the data read
  `.items` and ignore the rest — of the 7 call sites in the live tree,
  only `seed_library_if_empty()` inspects `.was_corrupt`.
- `load_project()` (user-owned — a `.rackproj` the app doesn't get to
  silently rewrite the user's data out from under) is handled
  differently on purpose: a fully-invalid top-level JSON file raises
  cleanly and is **never** touched or renamed — the existing
  `try/except ... MsgBox.error(...)` at both call sites
  (`ProjectSection._open()`/`._open_recent()`) already surfaces that. But
  a *partially* bad file — one unparseable slot inside an otherwise-valid
  project (e.g. a `null` entry in a rack's `slots` list, from a partial
  write) — no longer aborts the whole load: that slot is skipped, the
  rest of the project loads normally, and `load_project()` returns
  `(project, skip_warnings)` where `skip_warnings` is a list of
  `"N slot(s) in '<rack>' could not be loaded and were skipped."`
  messages, one per affected rack, shown via `MsgBox.warn`.

**CSV import has an encoding fallback.** `import_library_csv()` reads
the file as raw bytes and tries `utf-8-sig` first, `cp1252` second
(Excel's default "ANSI" export encoding on many Windows locales) —
`_read_text_with_encoding_fallback()`. If neither decodes, it raises a
`ValueError` naming both encodings tried, instead of a raw
`UnicodeDecodeError` surfacing from partway through `csv.DictReader`
iteration.

**`save_project()` doesn't mutate its input.** When auto-naming a new
save that collides with an existing project's name on disk, the
deduplicated name (`"<name> (N)"`) is computed locally and returned
(`(filepath, resolved_name)`) rather than being written onto the caller's
`Project.name` in place. `MainWindow._save()` (the only caller that hits
this path) applies `resolved_name` to its live project explicitly, so the
open project's displayed name still updates after a dedup — same
user-visible result as before, but as a visible assignment at the call
site rather than a hidden side effect inside `storage.py`.

See `task.md` #33/#34/#35/#38/#39/#45 for the full per-item detail this
model replaced, and `changelog.md` Session 8 for file-by-file changes and
verification.

## Known architectural gaps (source of current bugs — see `task.md`)

1. ~~`RackDrawing.draw()` (`pdf_export.py`) ignores `Rack.bays` and
   `RackSlot.bay` entirely.~~ **Fixed 2026-07-22 (Session 2).**
   `RackDrawing` now takes a per-bay horizontal offset (`bay_rx = rx +
   bay_idx * RACK_W`), filters/positions the slot-drawing loop by
   `slot.bay`, and draws a thin vertical separator between bay columns.
   The auto-scale factor (previously height-only) now also accounts for
   width, since multi-bay diagrams can exceed the page's usable width.
   See `changelog.md` Unreleased — Session 2 fixes.

2. ~~Two distinct bugs were previously conflated under "crash moving
   devices between racks/bays."~~ **Both fixed 2026-07-24 (Session 3).**
   Investigated 2026-07-22 (Session 2) by actually running the app
   (offscreen Qt, both direct handler calls and real `QTest`-driven event
   dispatch) — findings and fixes below.

   **2a. Stale `RackSlot.bay` during same-canvas bay-crossing — fixed.**
   `RackCanvas.mouseMoveEvent()`'s internal-reorder branch (cursor stays
   within the canvas, `_point_to_bay_u()` returns `bay >= 0`) had the
   collision check filtering `others` by `s.bay == self._drag_bay` (the
   *starting* bay, captured once in `mousePressEvent` and never updated),
   and never reassigned `self._drag_slot.bay` when the cursor crossed
   into a different bay column — only `position_u` changed, so a slot
   dragged from bay 0 into bay 1 stayed rendered in bay 0's column, only
   moving vertically, regardless of which bay the cursor was actually
   over. Confirmed real via 4 direct-call scenarios (single device,
   back-and-forth crossings, a target bay with a colliding slot, and a
   tray slot) — zero exceptions, zero data corruption, but a real
   UI/data-consistency defect.

   **Fix**: the collision check (`others = [...]`) now filters by the
   *current* `bay` (the value `_point_to_bay_u()` just returned for this
   move event) instead of the stale `self._drag_bay`. When the move isn't
   blocked by a collision, `self._drag_slot.bay = bay` is assigned
   alongside `position_u`, so the slot's data model bay updates in lock
   step with what's rendered. The undo-snapshot trigger (`if new_u !=
   self._drag_slot.position_u`) was extended to `or bay !=
   self._drag_slot.bay`, so a pure bay-change (no vertical move) still
   gets its own undo entry. `self._drag_bay` (set in `mousePressEvent`)
   is now unused by this branch — left in place, harmless.

   **2b. `QPixmap` NameError crash — fixed.**
   `RackCanvas.mouseMoveEvent()`'s *other* branch — when the cursor
   leaves the canvas bounds entirely (`_point_to_bay_u()` returns
   `bay < 0`), which starts a real cross-rack `QDrag` — references
   `QPixmap` without it ever being imported anywhere in `rack_canvas.py`
   (the module imported `QPainter, QColor, QFont, QPen, QBrush,
   QWheelEvent, QKeySequence` from `PyQt6.QtGui`, plus a redundant local
   `QPainter` re-import a few lines later — but never `QPixmap`). This
   raised `NameError: name 'QPixmap' is not defined` on the very first
   mouse-move event after the cursor exits the canvas — the **only
   mechanism the app has for moving a device to a different rack**
   (confirmed by reading `dropEvent`'s "Cross-rack slot drop" branch,
   which only ever receives data via this same `QDrag`), and also
   trivially easy to trigger by accident on an ordinary in-rack drag that
   overshoots the vertical U range (canvas height is exactly `u_size *
   SLOT_H`, no buffer margin).

   Session 2 confirmed two ways this manifested: (1) calling
   `mouseMoveEvent()` directly with a synthetic out-of-bounds
   `QMouseEvent` raised a normal, catchable Python `NameError`. (2)
   Driving the same scenario through `QTest.mouseMove()` — the real
   Qt/C++ event dispatch, matching live usage — was far worse: with no
   custom `sys.excepthook` installed, PyQt6's default handling of an
   exception escaping an overridden virtual method **aborted the process
   immediately and silently** — no traceback, no dialog, nothing on
   stdout/stderr.

   **Fix**: added `QPixmap` to the `from PyQt6.QtGui import (...)` line.

   **Verification (Session 3, 2026-07-24)**: standalone offscreen-Qt
   script covering both bugs — 2a's four scenarios (bay-cross follows
   cursor, back-and-forth, target-bay collision correctly blocks the
   move, tray slot) all end with correct `bay`/`position_u`; 2b's
   cross-rack-drag-start path (direct call and real `QTest.mouseMove`)
   raises no exception and the process does not abort. As a sanity check
   that the test harness actually exercises the bug, the `QPixmap` import
   was temporarily reverted and the same script re-run: the direct call
   reproduced the `NameError` and the `QTest`-driven path reproduced the
   exact silent abort (process exit 127, no output) described above,
   before the fix was restored.

   **Files modified**: `app/rack_canvas.py` — `QPixmap` added to the
   `PyQt6.QtGui` import line; `mouseMoveEvent()`'s internal-reorder
   branch (`bay >= 0` case).

3. ~~`DeviceForm` (`app/library_dialog.py`) never actually used
   `ImagePickerWidget`, so every Library-tab save wiped device
   images.~~ **Fixed 2026-07-24 (Session 4).** `ImagePickerWidget` was
   fully implemented (load/clear/preview/base64 get-set) but `DeviceForm`
   only ever set `self.img_front = None` / `self.img_rear = None` —
   never instantiated the widget, never added it to the form layout. As
   a direct consequence, `DeviceForm.collect()` had no picker to read
   from and unconditionally returned `"image_front": ""` /
   `"image_rear": ""`; `LibrarySection._save()`'s `for k, v in
   data.items(): setattr(dev, k, v)` then wrote those empty strings onto
   the device on *every* save — silently destroying any existing image
   data (from JSON import, since the seed library and the UI itself
   never produced any).

   **Fix**: `DeviceForm.__init__` now creates real `ImagePickerWidget`
   instances for `self.img_front`/`self.img_rear` and adds them to the
   form as an "Images" row. `DeviceForm.load(device)` pre-populates both
   pickers from the device's existing `image_front`/`image_rear` before
   the form is ever shown — necessary because without this half of the
   fix, simply opening an unmodified device and saving would still wipe
   its images (an empty picker correctly reflects "no image" back
   through `collect()`). `DeviceForm.collect()` now reads
   `self.img_front.get_b64()` / `self.img_rear.get_b64()` instead of the
   hardcoded empties. `LibrarySection._save()` needed no change — its
   blind `setattr` loop is correct once its input (`collect()`) is
   correct.

   A second, smaller bug was uncovered as a direct prerequisite:
   `ImagePickerWidget._update_hint()` references `IMAGE_WIDTH_PX` /
   `IMAGE_U_HEIGHT_PX` (from `app.models`) without either ever being
   imported in `library_dialog.py` — invisible until the widget was
   actually instantiated for the first time, which this fix now does.
   Added both to the existing `app.models` import line. Also wired the
   previously-unused `ImagePickerWidget.update_u_height()` into the U
   height spinner's commit/up/down handlers and into `load()`, so the
   picker's "recommended size" hint reflects the device's real U height.

   **Verification (Session 4, 2026-07-24)**: two offscreen-Qt scripts —
   one exercising `DeviceForm`/`storage` directly across all 4 required
   scenarios (new device, existing-with-images + unrelated-field save
   [the exact bug], existing-with-images + replace/clear an image,
   existing-without-images + no-op save), and a second driving the real
   `LibrarySection` widget end-to-end (real list-row selection, real
   `QTest.mouseClick` on the Save button) to confirm the fix holds
   through the actual UI signal chain, not just at the method level.
   Reverting the `collect()` fix and re-running reproduced 3 failing
   checks (including the bug-scenario one), confirming the harness
   actually exercises the bug.

   **Files modified**: `app/library_dialog.py` only
   (`DeviceForm.__init__`, `.load()`, `.collect()`, the `app.models`
   import line).

### Startup error handling (three layers, `main.py`)

`main.py`'s startup sequence runs through three distinct failure domains,
each with a different ceiling on what recovery is even possible — no
single mechanism can cover all three, since the tools available (Qt, the
app's own dialogs, a constructed window) don't exist yet at the earlier
stages. Layer 1 was added Session 3 (2026-07-24); layers 2 and 3 were
added Session 16 (2026-07-29, `task.md` #63/#62) as a direct consequence
of auditing what Layer 1 doesn't cover.

**Layer 1 — the running event loop (`sys.excepthook` → `_excepthook`,
Session 3).** Added as a direct follow-up to bug 2 (item 2 above): the app
previously had zero protection against unhandled exceptions escaping Qt
event handlers — PyQt6's default behavior in that case is a silent,
traceback-less process abort. `main.py` installs `sys.excepthook =
_excepthook` right after `QApplication` is constructed:
- `KeyboardInterrupt` / `SystemExit` are passed straight through to
  `sys.__excepthook__` unchanged — not intercepted.
- Any other uncaught exception: the full traceback is logged via
  `_log_crash()` (below), then a themed `MsgBox.error(...)` dialog (from
  `app/dialogs.py`, not a raw `QMessageBox` — see `task.md` #8 for the
  reasoning) tells the user something went wrong and was logged.
  Execution continues afterward; the app does not force-quit.
- Both the log write and the dialog call are individually wrapped in
  `try/except` so a failure inside the handler itself (e.g. disk full)
  can't cause a second, unhandled crash.

This layer does not change how exceptions are handled *within*
application logic (no new `try/except` blocks were added elsewhere) — it
only adds a last-resort net at the top level so an escaped exception
degrades to "app shows an error and keeps running" instead of "app
vanishes with no diagnostic trace." Critically, `sys.excepthook` firing
does **not** resume execution past the exception's origin point — it only
reports it, then the interpreter still unwinds and terminates whatever
called the code that raised. That distinction is exactly why Layers 2 and
3 exist: `sys.excepthook` alone was already enough to *log and show a
dialog for* an exception during startup, before either fix — the app
still failed to come up afterward, just no longer completely silently.

`_log_crash(exc_type, exc_value, exc_tb)` is the one shared logging
implementation: appends a timestamped traceback to
`%APPDATA%\RackDesigner\crash.log` via `storage.get_app_data_dir()`.
`_excepthook` and Layer 2's seeding guard (below) both call it — the
guard reuses this function rather than duplicating its body, since by the
time either runs, `app.storage` and Qt are already known to import/work.

**Layer 2 — first-run library seeding (`main()`'s `try/except` around
`seed_library_if_empty()`, Session 16, `task.md` #62).**
`seed_library_if_empty()` runs before `MainWindow` is ever constructed —
an unguarded exception there (disk full, permission denied, AV lock,
OneDrive lock — all realistic on real Windows installs) used to propagate
all the way to the top of the program: `sys.excepthook` still logged it
and showed the generic Layer-1 dialog, but then the process terminated
anyway, since a hook firing doesn't undo the fact that nothing downstream
of the raise point ever ran — `MainWindow()`, `.show()`, and `app.exec()`
were all skipped. `main()` now wraps the `seed_library_if_empty()` call
itself: on failure, `_log_crash()` records the traceback (reusing Layer
1's logging, not duplicating it) and a `seed_failed` flag is set, but
execution continues into constructing and showing `MainWindow` regardless
— the app comes up with whatever library state exists (likely empty)
rather than not coming up at all. Only *after* `window.show()` does
`_notify_seed_failed(window)` show a themed dialog explaining
initialization failed, the error was logged, and the library may be
empty/incomplete — deliberately a different dialog from
`_notify_if_library_was_reset()` (which covers "found and quarantined a
corrupt file," a materially different situation from "failed to seed at
all").

**Layer 3 — pre-`QApplication` startup (`_log_pre_qt_crash()`, Session
16, `task.md` #63).** Everything before `QApplication` is constructed —
`main.py`'s own top-level imports (`PyQt6.QtWidgets`, `app.main_window`,
etc.) and the `QApplication(sys.argv)` call itself — previously fell
through to Python's raw default excepthook if anything went wrong there
(a broken Qt platform plugin/driver, or an import-time failure from a
corrupted/incomplete install). For a windowed launch with no attached
console, that's completely silent: no log, no dialog, the app just never
appears. **No dialog is possible at this stage — there is no
`QApplication` yet for one to attach to.** Disk logging is the ceiling:
`main.py`'s top-level imports are now wrapped in `try/except`, and
`QApplication(sys.argv)` inside `main()` is wrapped the same way; both
call `_log_pre_qt_crash()` then re-raise (the process still exits either
way — this layer's entire job is making sure *something* survives to
`crash.log` before it does). `_log_pre_qt_crash()` is deliberately
self-contained: plain `os`/`pathlib`/`datetime`/`traceback` only, no Qt
import and no `app.storage` import, duplicating `get_app_data_dir()`'s
two-line path logic rather than calling it — because at this stage,
either PyQt6 or the `app` package itself could be exactly what's broken,
so the logger can't depend on either still working.
