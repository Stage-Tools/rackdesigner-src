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


class RackDrawing(Flowable):
    """
    Rack diagram:
    - U1 at bottom, U_n at top (matching canvas).
    - Auto-scales if taller than available page height.
    - No stats line below (shown above as paragraph instead).
    - No notes/pencil icon.
    - Optional color vs grayscale.
    """
    def __init__(self, rack: Rack, use_color=True):
        super().__init__()
        self.rack      = rack
        self.use_color = use_color

        natural_h = rack.u_size * SLOT_H
        natural_w = RACK_W + LABEL_W + 4 * mm

        if natural_h > MAX_RACK_H:
            self._scale = MAX_RACK_H / natural_h
        else:
            self._scale = 1.0

        self.width  = natural_w * self._scale
        self.height = natural_h * self._scale

    def draw(self):
        c = self.canv
        s = self._scale

        if s != 1.0:
            c.saveState()
            c.transform(s, 0, 0, s, 0, 0)

        rx = LABEL_W
        ry = 0
        rw = RACK_W
        rh = self.rack.u_size * SLOT_H

        # Background
        c.setFillColor(HexColor("#111111"))
        c.rect(rx, ry, rw, rh, fill=1, stroke=0)

        # Grid lines
        c.setStrokeColor(HexColor("#2a2a2a"))
        c.setLineWidth(0.3)
        for i in range(self.rack.u_size + 1):
            y = ry + i * SLOT_H
            c.line(rx, y, rx + rw, y)

        # U labels: U1 at bottom (i=0), U_n at top
        c.setFont("Helvetica", 5)
        c.setFillColor(HexColor("#555555"))
        for i in range(self.rack.u_size):
            label_num = i + 1
            y = ry + i * SLOT_H
            c.drawRightString(rx - 1 * mm, y + SLOT_H * 0.3, str(label_num))

        # ReportLab: y=0 at bottom.
        # In the Qt canvas, position_u=1 is at the TOP (y=0). We must mirror:
        # sy = ry + (u_size - position_u - u_height + 1) * SLOT_H
        for slot in self.rack.slots:
            sy = ry + (self.rack.u_size - slot.position_u - slot.u_height + 1) * SLOT_H
            sh = slot.u_height * SLOT_H

            raw  = slot.effective_color
            if self.use_color:
                eff  = raw
                dark = _darken(eff, 0.35)
            else:
                eff  = "#555555"
                dark = "#1c1c1c"

            c.setFillColor(HexColor(dark))
            c.rect(rx + 1, sy + 0.5, rw - 2, sh - 1, fill=1, stroke=0)
            c.setFillColor(HexColor(eff))
            c.rect(rx + 1, sy + 0.5, 3 * mm, sh - 1, fill=1, stroke=0)
            c.setStrokeColor(HexColor(eff))
            c.setLineWidth(0.5)
            c.rect(rx + 1, sy + 0.5, rw - 2, sh - 1, fill=0, stroke=1)

            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 6)
            text_x = rx + 5 * mm
            text_y = sy + sh * 0.5 - 2
            c.drawString(text_x, text_y, slot.name)

            c.setFont("Helvetica", 5)
            c.setFillColor(HexColor("#aaaaaa"))
            c.drawRightString(rx + rw - 2 * mm, text_y, f"{slot.u_height}U")
            # Notes icon omitted intentionally

        # Rack border
        c.setStrokeColor(HexColor("#444444"))
        c.setLineWidth(1.5)
        c.rect(rx, ry, rw, rh, fill=0, stroke=1)
        # No stats line below — shown in the Paragraph above the drawing

        if s != 1.0:
            c.restoreState()


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
    cell_notes = ParagraphStyle("CellNotes", fontSize=7, fontName="Helvetica",
                                textColor=HexColor("#333333"), leading=9,
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

            # Group devices by name, collecting all distinct notes
            counts: dict[str, int]       = {}
            seen:   dict[str, dict]      = {}
            notes_list: dict[str, list]  = {}   # name → list of non-empty notes

            def _register(name, category, watts, weight_kg, note):
                counts[name] = counts.get(name, 0) + 1
                if name not in seen:
                    seen[name] = {"category": category,
                                  "watts": watts, "weight_kg": weight_kg}
                    notes_list[name] = []
                if note:
                    notes_list[name].append(note)

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

            table_data = [cols]
            for name in sorted(seen.keys()):
                info  = seen[name]
                notes = notes_list[name]

                # Build notes cell: deduplicate, convert newlines to <br/> for ReportLab
                unique_notes = list(dict.fromkeys(notes))
                formatted = ["<br/>".join(n.splitlines()) for n in unique_notes]
                notes_cell = "<br/>".join(formatted) if formatted else ""

                row = [str(counts[name]), name]
                if inc_cat:    row.append(info["category"])
                if inc_power:
                    w = info["watts"]
                    row.append(f"{w:.0f}" if w else "—")
                if inc_weight:
                    kg = info["weight_kg"]
                    row.append(f"{kg:.2f}" if kg else "—")
                if inc_notes:
                    if notes_cell:
                        from reportlab.platypus import Paragraph as _P
                        row.append(_P(notes_cell, cell_notes))
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
            row = [rack.name, f"{rack.u_size}U", f"{rack.used_u()}U",
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
