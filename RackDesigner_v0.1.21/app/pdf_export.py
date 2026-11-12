# Rack Designer
# Copyright (C) 2026 Riccardo Nessi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable
from reportlab.lib.colors import HexColor, white
from app.models import Project, Rack, RackSlot
from datetime import date as Date

SLOT_H  = 7 * mm
RACK_W  = 120 * mm
LABEL_W = 12 * mm

PAGE_W, PAGE_H = A4
LEFT_M = RIGHT_M = 18 * mm
TOP_M  = 18 * mm
BOT_M  = 26 * mm
# Conservative usable height per page for rack diagram
MAX_RACK_H = PAGE_H - TOP_M - BOT_M - 30 * mm
# Usable width per page for rack diagram (multi-bay racks can exceed this)
MAX_RACK_W = PAGE_W - LEFT_M - RIGHT_M


def hex_to_color(h):
    try:
        return HexColor(h)
    except Exception:
        return HexColor("#6B7280")


def _darken(hex_color, factor):
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"
    except Exception:
        return "#1a1a1a"


def _to_gray(hex_color):
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lum = int(0.299 * r + 0.587 * g + 0.114 * b)
        return f"#{lum:02x}{lum:02x}{lum:02x}"
    except Exception:
        return "#555555"


def _slot_colors(raw_hex, grayscale=False):
    """Derives (accent, slot_bg, border) hex strings for one occupied slot
    from its raw category/device colour: the accent is the colour itself
    (lightened 82% toward white for the body fill, darkened 30% for the
    border) — the same blend used regardless of mode. When grayscale=True,
    the raw colour is first run through _to_gray() so different categories
    still map to different (distinguishable) gray shades instead of every
    slot sharing one flat neutral fill (task.md #61) — `_to_gray()` existed
    but was never called anywhere before this fix."""
    base = _to_gray(raw_hex) if grayscale else raw_hex
    try:
        h = base.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        def _blend(ch):
            return int(ch + (255 - ch) * 0.82)
        slot_bg = f"#{_blend(r):02x}{_blend(g):02x}{_blend(b):02x}"
        border  = f"#{int(r*0.7):02x}{int(g*0.7):02x}{int(b*0.7):02x}"
    except Exception:
        slot_bg = "#eeeeee"
        border  = "#aaaaaa"
    return base, slot_bg, border


def _truncate_text(c, text, font, size, max_width):
    """Truncates `text` to the longest prefix (plus an ellipsis) that fits
    within `max_width` at the given font/size, measured via
    c.stringWidth() — instead of letting a long device name overflow past
    its slot's available width with no limit (task.md #58)."""
    if not text or max_width <= 0:
        return ""
    if c.stringWidth(text, font, size) <= max_width:
        return text
    ellipsis = "…"
    truncated = text
    while truncated and c.stringWidth(truncated + ellipsis, font, size) > max_width:
        truncated = truncated[:-1]
    return (truncated + ellipsis) if truncated else ellipsis


class RackDrawing(Flowable):
    """
    Rack diagram:
    - U1 at bottom, U_n at top (matching canvas).
    - Auto-scales if taller than available page height.
    - No stats line below (shown above as paragraph instead).
    - No notes/pencil icon.
    - Optional color vs grayscale.
    """
    def __init__(self, rack: Rack, use_color=True, page_fit: bool = True):
        super().__init__()
        self.rack      = rack
        self.use_color = use_color
        self.bays      = max(1, rack.bays)

        # Don't trust rack.u_size blindly for geometry: a shrunk rack can
        # still have occupied slots whose position_u + u_height exceeds it
        # (reachable despite task.md #16's guard, which has its own bug and
        # isn't fixed) — use whichever is larger so the diagram always
        # contains every slot it draws instead of rendering some of them
        # detached below the frame (task.md #59).
        occupied_top = max(
            (s.position_u + s.u_height - 1 for s in rack.slots), default=0)
        self._draw_u_size = max(rack.u_size, occupied_top)

        natural_h = self._draw_u_size * SLOT_H
        natural_w = LABEL_W + self.bays * RACK_W + 4 * mm

        if page_fit:
            scale_h = MAX_RACK_H / natural_h if natural_h > MAX_RACK_H else 1.0
            scale_w = MAX_RACK_W / natural_w if natural_w > MAX_RACK_W else 1.0
            self._scale = min(scale_h, scale_w)

            self.width  = natural_w * self._scale
            self.height = natural_h * self._scale
        else:
            # Natural-size rendering (task.md #65) — used by
            # export_rack_png(), which renders one rack per page at its own
            # true size rather than fitting it onto an A4 page. No
            # MAX_RACK_H/MAX_RACK_W involvement at all: the drawing is
            # exactly as large as the rack actually is, at any U-size/bay
            # count, with no upper bound.
            self._scale = 1.0
            self.width  = natural_w
            self.height = natural_h

    def draw(self):
        c = self.canv
        s = self._scale

        if s != 1.0:
            c.saveState()
            c.transform(s, 0, 0, s, 0, 0)

        rx = LABEL_W
        ry = 0
        rw = RACK_W                      # width of a single bay column
        bays = self.bays
        rw_total = bays * rw             # width of all bays combined
        u_size = self._draw_u_size       # see __init__ — may exceed rack.u_size
        rh = u_size * SLOT_H

        # ── Light theme palette ───────────────────────────────────────────────
        COL_BG        = HexColor("#ffffff")   # rack background
        COL_GRID      = HexColor("#d8d8d8")   # grid lines
        COL_U_LABEL   = HexColor("#888888")   # U number labels
        COL_SLOT_BG   = HexColor("#f4f4f4")   # empty-slot fill
        COL_TEXT      = HexColor("#1a1a1a")   # device name text
        COL_U_TEXT    = HexColor("#888888")   # U-size badge text
        COL_BORDER    = HexColor("#aaaaaa")   # rack outer border

        # Rack white background (spans all bays)
        c.setFillColor(COL_BG)
        c.rect(rx, ry, rw_total, rh, fill=1, stroke=0)

        # Grid lines (span all bays)
        c.setStrokeColor(COL_GRID)
        c.setLineWidth(0.3)
        for i in range(u_size + 1):
            y = ry + i * SLOT_H
            c.line(rx, y, rx + rw_total, y)

        # U labels — once, on the far left only (matches the live canvas convention)
        c.setFont("Helvetica", 5)
        c.setFillColor(COL_U_LABEL)
        for i in range(u_size):
            label_num = i + 1
            y = ry + i * SLOT_H
            c.drawRightString(rx - 1 * mm, y + SLOT_H * 0.3, str(label_num))

        # Slots — positioned within their own bay column
        # ReportLab y=0 at bottom; Qt position_u=1 at top → mirror:
        # sy = ry + (u_size - position_u - u_height + 1) * SLOT_H
        for slot in self.rack.slots:
            bay_idx = max(0, min(bays - 1, slot.bay))
            bay_rx = rx + bay_idx * rw

            sy = ry + (u_size - slot.position_u - slot.u_height + 1) * SLOT_H
            sh = slot.u_height * SLOT_H

            raw = slot.effective_color
            accent_hex, slot_bg, border_col = _slot_colors(raw, grayscale=not self.use_color)
            accent_color  = HexColor(accent_hex)
            slot_bg_color = HexColor(slot_bg)
            border_color  = HexColor(border_col)

            # Slot body
            c.setFillColor(slot_bg_color)
            c.rect(bay_rx + 1, sy + 0.5, rw - 2, sh - 1, fill=1, stroke=0)

            # Left colour stripe (3 mm)
            c.setFillColor(accent_color)
            c.rect(bay_rx + 1, sy + 0.5, 3 * mm, sh - 1, fill=1, stroke=0)

            # Slot border
            c.setStrokeColor(border_color)
            c.setLineWidth(0.4)
            c.rect(bay_rx + 1, sy + 0.5, rw - 2, sh - 1, fill=0, stroke=1)

            # Device name — dark text, truncated with an ellipsis if it would
            # otherwise overflow into the U-size badge / past the slot's
            # right edge (task.md #58) — measured, not just eyeballed, via
            # the real font metrics for the font/size actually drawn below.
            NAME_FONT, NAME_SIZE = "Helvetica-Bold", 6
            BADGE_FONT, BADGE_SIZE = "Helvetica", 5
            c.setFillColor(COL_TEXT)
            c.setFont(NAME_FONT, NAME_SIZE)
            text_x = bay_rx + 5 * mm
            text_y = sy + sh * 0.5 - 2
            badge_text = f"{slot.u_height}U"
            badge_w = c.stringWidth(badge_text, BADGE_FONT, BADGE_SIZE)
            badge_left_x = (bay_rx + rw - 2 * mm) - badge_w
            max_name_w = badge_left_x - 2 * mm - text_x
            name = _truncate_text(c, slot.name, NAME_FONT, NAME_SIZE, max_name_w)
            c.drawString(text_x, text_y, name)

            # U-size badge — muted
            c.setFont(BADGE_FONT, BADGE_SIZE)
            c.setFillColor(COL_U_TEXT)
            c.drawRightString(bay_rx + rw - 2 * mm, text_y, badge_text)

        # Thin vertical separators between bays
        if bays > 1:
            c.setStrokeColor(COL_BORDER)
            c.setLineWidth(0.6)
            for b in range(1, bays):
                x = rx + b * rw
                c.line(x, ry, x, ry + rh)

        # Rack outer border (spans all bays)
        c.setStrokeColor(COL_BORDER)
        c.setLineWidth(1.2)
        c.rect(rx, ry, rw_total, rh, fill=0, stroke=1)

        if s != 1.0:
            c.restoreState()


def export_rack_png(rack: Rack, filepath: str, use_color: bool = True, dpi: int = 300) -> None:
    """
    Renders a single rack diagram to a standalone PNG file at its natural
    (uncapped) size — no A4 page-fit scaling — via an in-memory single-page
    PDF rasterized through PyMuPDF (task.md #65).

    Deliberately reuses RackDrawing.draw() (the exact same code export_pdf()
    calls for every rack in a full document) via page_fit=False, rather than
    a separate PNG-specific renderer: every PDF-export correctness fix that
    lives in that one drawing routine (device-name truncation, out-of-bounds
    -slot containment, grayscale per-category shading, etc. — see the
    Session 12 audit cluster) applies to this path automatically, with
    nothing to keep in sync by hand.

    `fitz` (PyMuPDF) is imported lazily here, not at module level — a
    missing/broken PyMuPDF install should only break this one optional
    feature when actually used, not prevent the whole app (including plain
    PDF export, which doesn't need it) from starting.
    """
    from reportlab.pdfgen import canvas as pdf_canvas
    import fitz

    drawing = RackDrawing(rack, use_color=use_color, page_fit=False)

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=(drawing.width, drawing.height))
    drawing.drawOn(c, 0, 0)
    c.showPage()
    c.save()

    pdf_doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
    try:
        page = pdf_doc[0]
        zoom = dpi / 72.0  # PDF points are natively 72/inch
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        png_bytes = pix.tobytes("png")
    finally:
        pdf_doc.close()

    with open(filepath, "wb") as f:
        f.write(png_bytes)


def _build_footer(canvas, doc):
    """Footer: two-line credit left, page number right."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#aaaaaa"))
    y_top = doc.bottomMargin - 6 * mm
    y_bot = doc.bottomMargin - 10 * mm
    canvas.drawString(doc.leftMargin, y_top, "Created with Rack Designer")
    canvas.drawString(doc.leftMargin, y_bot, "stage-tools.github.io/stagetools/")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, y_bot, f"Page {doc.page}")
    canvas.restoreState()


def export_pdf(project: Project, filepath: str, options: dict = None) -> None:
    if options is None:
        options = {
            "include_front":            True,
            "include_diagram":          True,
            "use_color":                True,
            "include_devlist":          True,
            "include_devlist_category": True,
            "include_power":            True,
            "include_weight":           True,
            "include_summary":          True,
            "include_notes":            False,
        }

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=LEFT_M, rightMargin=RIGHT_M,
        topMargin=TOP_M, bottomMargin=BOT_M,
    )

    h1 = ParagraphStyle("H1", fontSize=14, fontName="Helvetica-Bold",
                         spaceBefore=6*mm, spaceAfter=2*mm,
                         textColor=HexColor("#e8a020"))
    h2 = ParagraphStyle("H2", fontSize=10, fontName="Helvetica-Bold",
                         spaceBefore=6*mm, spaceAfter=3*mm,
                         textColor=HexColor("#444444"))
    meta = ParagraphStyle("Meta", fontSize=8, fontName="Helvetica",
                           textColor=HexColor("#666666"), spaceAfter=1*mm)
    # Used for any device-list cell that needs to wrap instead of overflowing
    # into a neighbouring column (task.md #57) — Device/Category, and Notes
    # (which already wrapped before this fix).
    cell_wrap = ParagraphStyle("CellWrap", fontSize=7, fontName="Helvetica",
                                textColor=HexColor("#333333"), leading=9,
                                allowWidows=1, allowOrphans=1)
    # Same purpose, for the project-summary table's Rack name cell — its
    # table renders at fontSize 8, not 7.
    summary_cell = ParagraphStyle("SummaryCell", fontSize=8, fontName="Helvetica",
                                   textColor=HexColor("#1a1a1a"), leading=10,
                                   allowWidows=1, allowOrphans=1)

    use_color = options.get("use_color", True)
    story = []

    # ── Document header ───────────────────────────────────────────────────────
    story.append(Paragraph(f"Rack Design — {project.name}", h1))
    story.append(Spacer(1, 2*mm))
    if project.client:
        story.append(Paragraph(f"Client: {project.client}", meta))
    if project.venue:
        story.append(Paragraph(f"Venue: {project.venue}", meta))
    if project.date:
        story.append(Paragraph(f"Date: {project.date}", meta))
    story.append(Paragraph(f"Generated: {Date.today().strftime('%d %B %Y')}", meta))
    if project.notes:
        story.append(Paragraph(f"Notes: {project.notes}", meta))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=HexColor("#333333"), spaceAfter=4*mm))

    # ── Racks ─────────────────────────────────────────────────────────────────
    for rack in project.racks:
        rack_block = []

        rack_block.append(Paragraph(rack.name, h1))

        rack_info = f"{rack.u_size}U rack · {rack.used_u()}U used · {rack.free_u()}U free"
        if options.get("include_power") and rack.total_watts() > 0:
            rack_info += f" · {rack.total_watts():.0f}W"
        if options.get("include_weight") and rack.total_weight() > 0:
            rack_info += f" · {rack.total_weight():.1f}kg"
        rack_block.append(Paragraph(rack_info, meta))
        rack_block.append(Spacer(1, 2*mm))

        if options.get("include_diagram"):
            drawing = RackDrawing(rack, use_color=use_color)
            # Wrap in a 1-cell table to center horizontally on the page
            usable_w = PAGE_W - LEFT_M - RIGHT_M
            wrapper = Table([[drawing]], colWidths=[usable_w])
            wrapper.setStyle(TableStyle([
                ("ALIGN",   (0,0), (-1,-1), "CENTER"),
                ("VALIGN",  (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING",   (0,0), (-1,-1), 0),
                ("RIGHTPADDING",  (0,0), (-1,-1), 0),
                ("TOPPADDING",    (0,0), (-1,-1), 0),
                ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ]))
            rack_block.append(wrapper)

        # Name + info + diagram always stay together on the same page
        story.append(KeepTogether(rack_block))

        # ── Device list ───────────────────────────────────────────────────────
        if options.get("include_devlist") and rack.slots:

            # Group devices by (name, watts, weight_kg, category), not name
            # alone — two slots that merely share a name but differ in any of
            # those fields (e.g. an older device_snapshot predating a library
            # edit) used to collapse into one row whose displayed per-unit
            # watts/weight came only from whichever slot was encountered
            # first, silently wrong for the others despite the project-total
            # elsewhere correctly summing every slot's real value (task.md
            # #55). Devices that genuinely match on all four still collapse
            # into one row with a multiplied qty, same as before.
            counts: dict[tuple, int]      = {}
            seen:   dict[tuple, dict]     = {}
            notes_list: dict[tuple, list] = {}   # key → list of non-empty notes

            def _register(name, category, watts, weight_kg, note):
                key = (name, watts, weight_kg, category)
                counts[key] = counts.get(key, 0) + 1
                if key not in seen:
                    seen[key] = {"name": name, "category": category,
                                 "watts": watts, "weight_kg": weight_kg}
                    notes_list[key] = []
                if note:
                    notes_list[key].append(note)

            for slot in rack.slots:
                if slot.is_tray:
                    for dev in slot.tray_devices:
                        _register(dev.get("name", "?"), dev.get("category", ""),
                                  dev.get("watts"), dev.get("weight_kg"),
                                  dev.get("notes", ""))
                else:
                    _register(slot.name, slot.category,
                               slot.watts, slot.weight_kg, slot.notes)

            inc_cat    = options.get("include_devlist_category", True)
            inc_power  = options.get("include_power", False)
            inc_weight = options.get("include_weight", False)
            inc_notes  = options.get("include_notes", False)

            cols = ["Qty", "Device"]
            if inc_cat:    cols.append("Category")
            if inc_power:  cols.append("W (each)")
            if inc_weight: cols.append("kg (each)")
            if inc_notes:  cols.append("Notes")

            def _sort_key(key):
                # Group by name first (matches the previous sort), then by
                # the remaining fields — None-valued watts/weight_kg sort
                # after real values rather than raising on a None/float
                # comparison.
                name, watts, weight_kg, category = key
                return (name, category, watts is None, watts or 0,
                        weight_kg is None, weight_kg or 0)

            table_data = [cols]
            for key in sorted(seen.keys(), key=_sort_key):
                info  = seen[key]
                notes = notes_list[key]

                # Build notes cell: deduplicate, convert newlines to <br/> for ReportLab
                unique_notes = list(dict.fromkeys(notes))
                formatted = ["<br/>".join(n.splitlines()) for n in unique_notes]
                notes_cell = "<br/>".join(formatted) if formatted else ""

                # Device/Category wrapped in a Paragraph so a long name/value
                # wraps within its column instead of overflowing into the
                # next one (task.md #57), same as Notes already did.
                row = [str(counts[key]), Paragraph(info["name"], cell_wrap)]
                if inc_cat:    row.append(Paragraph(info["category"], cell_wrap))
                if inc_power:
                    w = info["watts"]
                    # 0 is a legitimate value (e.g. a passive patch bay) —
                    # only a genuinely unset (None) field shows "—" (task.md #56)
                    row.append(f"{w:.0f}" if w is not None else "—")
                if inc_weight:
                    kg = info["weight_kg"]
                    row.append(f"{kg:.2f}" if kg is not None else "—")
                if inc_notes:
                    if notes_cell:
                        row.append(Paragraph(notes_cell, cell_wrap))
                    else:
                        row.append("")
                table_data.append(row)

            col_w = [10*mm, 60*mm]
            if inc_cat:    col_w.append(28*mm)
            if inc_power:  col_w.append(16*mm)
            if inc_weight: col_w.append(16*mm)
            if inc_notes:  col_w.append(45*mm)

            t = Table(table_data, colWidths=col_w, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND",     (0,0), (-1,0),  HexColor("#1a1a2a")),
                ("TEXTCOLOR",      (0,0), (-1,0),  white),
                ("FONTNAME",       (0,0), (-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",       (0,0), (-1,-1), 7),
                ("FONTNAME",       (0,1), (-1,-1), "Helvetica"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1),  [HexColor("#f5f5f5"), white]),
                ("GRID",           (0,0), (-1,-1),  0.4, HexColor("#cccccc")),
                ("VALIGN",         (0,0), (-1,-1),  "MIDDLE"),
                ("TOPPADDING",     (0,0), (-1,-1),  3),
                ("BOTTOMPADDING",  (0,0), (-1,-1),  3),
                ("LEFTPADDING",    (0,0), (-1,-1),  3),
                ("ALIGN",          (0,0), (0,-1),   "CENTER"),

            ]))
            # KeepTogether for title + table header (at least first 3 rows)
            story.append(KeepTogether([
                Paragraph("Device list", h2),
                Spacer(1, 2*mm),
                t,
            ]))

        story.append(Spacer(1, 8*mm))

    # ── Project summary ───────────────────────────────────────────────────────
    if options.get("include_summary"):
        story.append(HRFlowable(width="100%", thickness=1,
                                color=HexColor("#333333"), spaceAfter=3*mm))

        sum_cols = ["Rack", "Size", "Used", "Free", "Devices"]
        if options.get("include_power"):  sum_cols.append("W total")
        if options.get("include_weight"): sum_cols.append("kg total")

        summary_data = [sum_cols]
        for rack in project.racks:
            w  = rack.total_watts()
            kg = rack.total_weight()
            # Rack name wrapped in a Paragraph so a long name wraps within
            # its column instead of overflowing into Size/Used/Free/Devices
            # (task.md #57), same fix as the device-list table.
            row = [Paragraph(rack.name, summary_cell), f"{rack.u_size}U", f"{rack.used_u()}U",
                   f"{rack.free_u()}U", str(len(rack.slots))]
            if options.get("include_power"):  row.append(f"{w:.0f}"  if w  > 0 else "—")
            if options.get("include_weight"): row.append(f"{kg:.1f}" if kg > 0 else "—")
            summary_data.append(row)

        base_w = [44*mm, 14*mm, 14*mm, 14*mm, 18*mm]
        if options.get("include_power"):  base_w.append(18*mm)
        if options.get("include_weight"): base_w.append(18*mm)

        st = Table(summary_data, colWidths=base_w, repeatRows=1)
        st.setStyle(TableStyle([
            ("BACKGROUND",     (0,0), (-1,0),  HexColor("#1a1a2a")),
            ("TEXTCOLOR",      (0,0), (-1,0),  white),
            ("FONTNAME",       (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTNAME",       (0,1), (-1,-1), "Helvetica"),
            ("FONTSIZE",       (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),  [HexColor("#f5f5f5"), white]),
            ("GRID",           (0,0), (-1,-1),  0.4, HexColor("#cccccc")),
            ("VALIGN",         (0,0), (-1,-1),  "MIDDLE"),
            ("TOPPADDING",     (0,0), (-1,-1),  3),
            ("BOTTOMPADDING",  (0,0), (-1,-1),  3),
        ]))
        story.append(KeepTogether([
            Paragraph("Project summary", h1),
            Spacer(1, 2*mm),
            st,
        ]))

    doc.build(story, onFirstPage=_build_footer, onLaterPages=_build_footer)
