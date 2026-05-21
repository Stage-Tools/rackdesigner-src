from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QScrollArea,
    QStatusBar, QFileDialog, QInputDialog,
    QDialog, QFormLayout, QLineEdit, QTextEdit,
    QSpinBox, QFrame, QComboBox, QStackedWidget, QTabWidget,
    QCheckBox, QSizePolicy, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QColor, QFont, QKeySequence, QDrag, QPixmap, QShortcut
from app.dialogs import MsgBox
from app.models import Project, Rack, DeviceDefinition, get_categories
from app.rack_canvas import RackCanvas
from app import storage
from app.style import (ACCENT, ACCENT_DARK, BG0, BG1, BG2, BG3, BG4,
                        TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, DANGER,
                        FONT_TITLE, FONT_BODY)


# ── Helpers ───────────────────────────────────────────────────────────────────

def h_sep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{BG4}; margin:0;")
    return f


def lbl(text, size=11, bold=False, color=TEXT_SECONDARY, spacing=1.0):
    l = QLabel(text)
    f = QFont(FONT_BODY, size)
    f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet(f"color:{color}; letter-spacing:{spacing}px;")
    return l


def section_lbl(text):
    l = QLabel(text)
    l.setFont(QFont(FONT_TITLE, 14))
    l.setStyleSheet(f"color:{TEXT_PRIMARY}; letter-spacing:3px; padding:14px 20px 10px;")
    return l


def ghost_push(text, danger=False, small=False, amber=False):
    b = QPushButton(text)
    if amber:
        color, hover_bg, hover_color = ACCENT, "#1a1200", ACCENT
        border = "#2a1e00"
    elif danger:
        color, hover_bg, hover_color = "#cc4444", "#1e0f0f", "#e05555"
        border = "#3a1515"
    else:
        color, hover_bg, hover_color = TEXT_MUTED, BG4, TEXT_SECONDARY
        border = BG4
    pad = "4px 8px" if small else "5px 14px"
    b.setStyleSheet(f"""
        QPushButton {{
            background:{BG2}; color:{color}; border:1px solid {border};
            border-radius:3px; font-size:9px; font-weight:700;
            letter-spacing:1px; padding:{pad};
        }}
        QPushButton:hover {{ background:{hover_bg}; color:{hover_color}; }}
        QPushButton:disabled {{ color:{BG4}; border-color:{BG3}; }}
    """)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def sidebar_label(text):
    l = QLabel(text)
    l.setStyleSheet(f"color:#606060; font-size:9px; font-weight:700; letter-spacing:1.5px; padding:10px 12px 4px;")
    return l


class DraggableLibList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)

    def mousePressEvent(self, event):
        # Select the item under the cursor immediately on press
        item = self.itemAt(event.pos())
        if item:
            self.setCurrentItem(item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        item = self.itemAt(event.pos())
        if not item:
            item = self.currentItem()
        if not item or not item.data(Qt.ItemDataRole.UserRole):
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(item.data(Qt.ItemDataRole.UserRole))
        drag.setMimeData(mime)

        # Build a drag pixmap large enough to cover the Windows system icon
        label = item.text().split("  ·  ")[0]  # just the device name
        fm_w = max(180, len(label) * 7)
        pm = QPixmap(fm_w, 24)
        pm.fill(QColor("#1a1200"))
        from PyQt6.QtGui import QPainter, QPen
        painter = QPainter(pm)
        painter.setPen(QPen(QColor("#E8A020"), 1))
        painter.drawRect(0, 0, fm_w - 1, 23)
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#E8A020"))
        painter.drawText(8, 0, fm_w - 16, 24,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         label)
        painter.end()

        drag.setPixmap(pm)
        drag.setHotSpot(pm.rect().center())
        drag.exec(Qt.DropAction.CopyAction)


# ── Top nav bar ───────────────────────────────────────────────────────────────

class NavBar(QWidget):
    section_changed = pyqtSignal(int)
    NAV = ["PROJECT", "DESIGNER", "EXPORT", "LIBRARY", "ABOUT"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"background:{BG0}; border-bottom:1px solid #2a2a2a;")
        self._btns = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for i, name in enumerate(self.NAV):
            btn = QPushButton(name)
            btn.setFixedHeight(44)
            btn.setMinimumWidth(100)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._style(False))
            btn.clicked.connect(lambda _, idx=i: self._select(idx))
            self._btns.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        self.proj_chip = QLabel("")
        self.proj_chip.setStyleSheet(f"""
            QLabel {{
                color:{TEXT_MUTED}; font-size:10px; letter-spacing:0.5px;
                background:transparent; border:none;
                padding:0px 10px 0px 0px; margin-right:8px;
            }}
        """)
        layout.addWidget(self.proj_chip)

        self.save_btn = QPushButton("SAVE")
        self.save_btn.setFixedSize(64, 26)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{TEXT_MUTED};
                border:1px solid #444; border-radius:3px;
                font-size:9px; font-weight:700; letter-spacing:1px;
            }}
            QPushButton:hover {{ color:{ACCENT}; border-color:{ACCENT}; }}
        """)
        layout.addWidget(self.save_btn)
        layout.addSpacing(14)

        self._select(0)

    def _style(self, active):
        if active:
            return f"""QPushButton {{
                background:transparent; color:{ACCENT};
                border:none; border-bottom:2px solid {ACCENT};
                font-size:10px; font-weight:700; letter-spacing:1.5px; padding:0 18px;
            }}"""
        return f"""QPushButton {{
                background:transparent; color:#707070;
                border:none; border-bottom:2px solid transparent;
                font-size:10px; font-weight:700; letter-spacing:1.5px; padding:0 18px;
            }}
            QPushButton:hover {{ color:#a8a8a0; border-bottom:2px solid #444; }}"""

    def _select(self, idx):
        for i, btn in enumerate(self._btns):
            btn.setStyleSheet(self._style(i == idx))
        self.section_changed.emit(idx)

    def set_project(self, name, dirty=False):
        dot = "● " if dirty else ""
        self.proj_chip.setText(f"{dot}{name}")
        col = '#c8902a' if dirty else TEXT_MUTED
        self.proj_chip.setStyleSheet(f"""
            QLabel {{
                color:{col}; font-size:10px; letter-spacing:0.5px;
                background:transparent; border:none;
                padding:0px 10px 0px 0px;
            }}
        """)


# ── PROJECT section ───────────────────────────────────────────────────────────

class ProjectSection(QWidget):
    project_loaded = pyqtSignal(object)
    save_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filepath = None
        self.project = Project()
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar: recent projects ──────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background:#1a1a1a; border-right:1px solid #2a2a2a;")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        sb.addWidget(sidebar_label("RECENT PROJECTS"))

        self.recent_list = QListWidget()
        self.recent_list.setStyleSheet(f"""
            QListWidget {{ background:#1a1a1a; border:none; outline:none; }}
            QListWidget::item {{ padding:8px 12px; border-bottom:1px solid #242424; color:{TEXT_SECONDARY}; }}
            QListWidget::item:hover {{ background:#222; color:{TEXT_PRIMARY}; }}
            QListWidget::item:selected {{
                background:#222; color:{TEXT_PRIMARY};
                border-left:2px solid {ACCENT}; padding-left:10px;
            }}
        """)
        self.recent_list.itemClicked.connect(self._open_recent)
        sb.addWidget(self.recent_list)

        bottom = QWidget()
        bottom.setStyleSheet(f"background:#1a1a1a; border-top:1px solid #2a2a2a;")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(8, 8, 8, 8)
        bl.setSpacing(4)
        new_btn = ghost_push("NEW PROJECT", amber=True)
        new_btn.clicked.connect(self._new)
        open_btn = ghost_push("OPEN FILE…")
        open_btn.clicked.connect(self._open)
        del_btn = ghost_push("DELETE PROJECT", danger=True)
        del_btn.clicked.connect(self._delete_project)
        bl.addWidget(new_btn)
        bl.addWidget(open_btn)
        bl.addWidget(del_btn)
        sb.addWidget(bottom)

        # ── Main: project info form ───────────────────────────────────────────
        main = QWidget()
        main.setStyleSheet(f"background:{BG1};")
        ml = QVBoxLayout(main)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # Hero
        self.hero_widget = QWidget()
        self.hero_widget.setStyleSheet(f"background:{BG1}; border-bottom:1px solid #2a2a2a;")
        hl = QVBoxLayout(self.hero_widget)
        hl.setContentsMargins(20, 14, 20, 12)
        hl.setSpacing(3)
        self.hero_name = QLabel("New Project")
        self.hero_name.setFont(QFont(FONT_BODY, 16))
        self.hero_name.setStyleSheet(f"color:{TEXT_PRIMARY}; font-weight:700;")
        self.hero_sub = QLabel("")
        self.hero_sub.setStyleSheet(f"color:#707070; font-size:10px;")
        hl.addWidget(self.hero_name)
        hl.addWidget(self.hero_sub)
        ml.addWidget(self.hero_widget)

        # Form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background:{BG1}; border:none;")
        form_w = QWidget()
        form_w.setStyleSheet(f"background:{BG1};")
        fl = QVBoxLayout(form_w)
        fl.setContentsMargins(20, 16, 20, 16)
        fl.setSpacing(0)

        fl.addWidget(lbl("PROJECT INFO", 9, True, "#606060", 2))
        fl.addSpacing(12)

        FIELD_STYLE = """
            QLineEdit {
                background:#252525; color:#e8e0cc;
                border:1px solid #333333; border-radius:3px;
                padding:6px 10px; font-size:12px;
            }
            QLineEdit:focus { border:1px solid #e8a020; }
        """
        NOTE_STYLE = """
            QTextEdit {
                background:#252525; color:#e8e0cc;
                border:1px solid #333333; border-radius:3px;
                padding:6px 10px; font-size:12px;
            }
            QTextEdit:focus { border:1px solid #e8a020; }
        """
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Project name")
        self.name_edit.setStyleSheet(FIELD_STYLE)
        self.name_edit.setFixedHeight(34)
        self.commessa_edit = QLineEdit()
        self.commessa_edit.setPlaceholderText("Project number")
        self.commessa_edit.setStyleSheet(FIELD_STYLE)
        self.commessa_edit.setFixedHeight(34)
        self.venue_edit = QLineEdit()
        self.venue_edit.setPlaceholderText("Venue or location")
        self.venue_edit.setStyleSheet(FIELD_STYLE)
        self.venue_edit.setFixedHeight(34)
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("e.g. 2025-06-01")
        self.date_edit.setStyleSheet(FIELD_STYLE)
        self.date_edit.setFixedHeight(34)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Notes…")
        self.notes_edit.setStyleSheet(NOTE_STYLE)
        form.addRow(lbl("Project name", 10, color="#808080"), self.name_edit)
        form.addRow(lbl("Project number",     10, color="#808080"), self.commessa_edit)
        form.addRow(lbl("Venue",        10, color="#808080"), self.venue_edit)
        form.addRow(lbl("Date", 10, color="#808080"), self.date_edit)
        form.addRow(lbl("Notes", 10, color="#808080"), self.notes_edit)
        fl.addLayout(form)
        fl.addStretch()
        scroll.setWidget(form_w)
        ml.addWidget(scroll)

        # File actions footer
        footer = QWidget()
        footer.setStyleSheet(f"background:{BG1}; border-top:1px solid #2a2a2a;")
        ftl = QHBoxLayout(footer)
        ftl.setContentsMargins(20, 8, 20, 8)
        ftl.setSpacing(6)
        save_btn = ghost_push("SAVE", amber=True)
        save_btn.clicked.connect(self._apply_and_save)
        saveas_btn = ghost_push("SAVE AS…")
        saveas_btn.clicked.connect(self._save_as)
        del_proj_btn = ghost_push("DELETE", danger=True)
        del_proj_btn.clicked.connect(self._delete_project)
        ftl.addWidget(save_btn)
        ftl.addWidget(saveas_btn)
        ftl.addStretch()
        ftl.addWidget(del_proj_btn)
        ml.addWidget(footer)

        root.addWidget(sidebar)
        root.addWidget(main)
        self._refresh_recent()

    def _refresh_recent(self):
        self.recent_list.clear()
        import os, json
        for path in storage.list_recent_projects():
            # Legge il nome dal JSON; fallback al filename
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                name = data.get("name") or os.path.splitext(os.path.basename(path))[0].replace("_", " ")
            except Exception:
                name = os.path.splitext(os.path.basename(path))[0].replace("_", " ")
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.recent_list.addItem(item)
        # Ripristina la selezione sul progetto corrente
        if self._filepath:
            for i in range(self.recent_list.count()):
                if self.recent_list.item(i).data(Qt.ItemDataRole.UserRole) == self._filepath:
                    self.recent_list.setCurrentRow(i)
                    break

    def set_dirty_check(self, fn):
        """Inietta un callable che restituisce True se si può procedere (dirty check)."""
        self._dirty_check_fn = fn

    def _can_proceed(self) -> bool:
        """Chiama il dirty check esterno se presente. True = si può caricare."""
        fn = getattr(self, "_dirty_check_fn", None)
        return fn() if fn else True

    def _open_recent(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        if not self._can_proceed():
            # Ripristina la selezione sul progetto corrente nella lista
            self._refresh_recent()
            return
        try:
            p = storage.load_project(path)
            self._filepath = path
            self.load_project(p, path)
            self.project_loaded.emit(p)
        except Exception as e:
            MsgBox.error(self, "Error", str(e))

    def _delete_project(self):
        item = self.recent_list.currentItem()
        if not item:
            MsgBox.info(self, "Delete project", "Select a project from the list first.")
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        name = item.text()
        msg = f"Delete '{name}' from disk?\n\nThis cannot be undone."
        if not MsgBox.question_danger(self, "Delete project", msg):
            return
        import os
        try:
            os.remove(path)
        except Exception as e:
            MsgBox.error(self, "Error", str(e))
            return
        self._refresh_recent()
        # If deleted project was current, reset
        if path == self._filepath:
            self._filepath = None
            self.project = Project()
            self.load_project(self.project)
            self.project_loaded.emit(self.project)

    def load_project(self, project: Project, filepath=None):
        self.project = project
        self._filepath = filepath
        self.name_edit.setText(project.name)
        self.commessa_edit.setText(project.client)
        self.venue_edit.setText(project.venue)
        self.date_edit.setText(project.date)
        self.notes_edit.setPlainText(project.notes)
        self._update_hero()
        self._refresh_recent()

    def _update_hero(self):
        self.hero_name.setText(self.project.name)
        parts = [x for x in [self.project.client, self.project.venue, self.project.date] if x]
        self.hero_sub.setText("  ·  ".join(parts))

    def _apply(self):
        """Applica le modifiche del form al progetto in memoria."""
        self.project.name = self.name_edit.text().strip() or self.project.name
        self.project.client = self.commessa_edit.text().strip()
        self.project.venue = self.venue_edit.text().strip()
        self.project.date = self.date_edit.text().strip()
        self.project.notes = self.notes_edit.toPlainText().strip()
        self.name_edit.setText(self.project.name)
        self._update_hero()
        self.project_loaded.emit(self.project)

    def _apply_and_save(self):
        """Applica le modifiche del form e salva su disco."""
        self._apply()
        self.save_requested.emit()
        self._refresh_recent()

    def _new(self):
        if not self._can_proceed():
            return
        self.project = Project()
        self._filepath = None
        self.load_project(self.project)
        self.project_loaded.emit(self.project)
        # Non salva su disco: appare nella lista solo dopo il primo SAVE esplicito

    def _open(self):
        if not self._can_proceed():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open project", str(storage.get_projects_dir()), "Rack project (*.rackproj)")
        if not path:
            return
        try:
            p = storage.load_project(path)
            self._filepath = path
            self.load_project(p, path)
            self.project_loaded.emit(p)
        except Exception as e:
            MsgBox.error(self, "Error", str(e))

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save as", str(storage.get_projects_dir()), "Rack project (*.rackproj)")
        if path:
            if not path.endswith(".rackproj"):
                path += ".rackproj"
            self._filepath = path
            self.save_requested.emit()

    def get_filepath(self): return self._filepath
    def set_filepath(self, p):
        self._filepath = p
        self._refresh_recent()


# ── DESIGNER section ──────────────────────────────────────────────────────────

class DesignerSection(QWidget):
    project_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = Project()
        self._canvases: list[RackCanvas] = []
        self._active_canvas: RackCanvas = None
        self.library: list[DeviceDefinition] = storage.load_library()
        self._build()
        self._refresh()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Splitter: sidebar resizable
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{ background:#141414; }}
            QSplitter::handle:hover {{ background:#2a2a2a; }}
        """)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setMinimumWidth(240)
        sidebar.setMaximumWidth(420)
        sidebar.setStyleSheet(f"background:#1a1a1a;")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        # ── Manual tab bar (two buttons + QStackedWidget) ────────────────────
        tab_bar = QWidget()
        tab_bar.setStyleSheet(f"background:#1a1a1a; border-bottom:1px solid #2a2a2a;")
        tab_bar.setFixedHeight(36)
        tbl = QHBoxLayout(tab_bar)
        tbl.setContentsMargins(0, 0, 0, 0)
        tbl.setSpacing(0)

        def _tab_btn_style(active):
            if active:
                return f"""QPushButton {{
                    background:#1a1a1a; color:{TEXT_SECONDARY};
                    border:none; border-bottom:2px solid #666;
                    font-size:9px; font-weight:700; letter-spacing:1.5px; padding:0;
                }}"""
            return f"""QPushButton {{
                background:#1a1a1a; color:#707070;
                border:none; border-bottom:2px solid transparent;
                font-size:9px; font-weight:700; letter-spacing:1.5px; padding:0;
            }}
            QPushButton:hover {{ color:#a8a8a0; }}"""

        self._tab_racks_btn = QPushButton("RACKS")
        self._tab_lib_btn   = QPushButton("LIBRARY")
        for b in (self._tab_racks_btn, self._tab_lib_btn):
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tab_racks_btn.setStyleSheet(_tab_btn_style(True))
        self._tab_lib_btn.setStyleSheet(_tab_btn_style(False))

        self._tab_stack = QStackedWidget()
        self._tab_stack.setStyleSheet("background:#1a1a1a;")

        def _switch_tab(idx):
            self._tab_stack.setCurrentIndex(idx)
            self._tab_racks_btn.setStyleSheet(_tab_btn_style(idx == 0))
            self._tab_lib_btn.setStyleSheet(_tab_btn_style(idx == 1))

        self._tab_racks_btn.clicked.connect(lambda: _switch_tab(0))
        self._tab_lib_btn.clicked.connect(lambda: _switch_tab(1))

        tbl.addWidget(self._tab_racks_btn)
        tbl.addWidget(self._tab_lib_btn)
        sb.addWidget(tab_bar)
        sb.addWidget(self._tab_stack)

        # Tab 1: RACKS
        racks_tab = QWidget()
        racks_tab.setStyleSheet(f"background:#1a1a1a;")
        rt = QVBoxLayout(racks_tab)
        rt.setContentsMargins(0, 0, 0, 0)
        rt.setSpacing(0)

        self.rack_list = QListWidget()
        self.rack_list.setStyleSheet(f"""
            QListWidget {{ background:#1a1a1a; border:none; outline:none; font-size:11px; }}
            QListWidget::item {{ padding:8px 12px; border-bottom:1px solid #242424; color:{TEXT_SECONDARY}; }}
            QListWidget::item:hover {{ background:#222; color:{TEXT_PRIMARY}; }}
            QListWidget::item:selected {{
                background:#222; color:{TEXT_PRIMARY};
                border-left:2px solid {ACCENT}; padding-left:10px;
            }}
        """)
        rt.addWidget(self.rack_list)

        # Slot info panel
        self._slot_info_panel = QWidget()
        self._slot_info_panel.setStyleSheet(
            f"background:#111; border-top:1px solid #2a2a2a;")
        self._slot_info_panel.setVisible(False)
        sip_l = QVBoxLayout(self._slot_info_panel)
        sip_l.setContentsMargins(10, 8, 10, 8)
        sip_l.setSpacing(3)
        self._sip_name = QLabel("")
        self._sip_name.setFont(QFont(FONT_BODY, 12, QFont.Weight.Bold))
        self._sip_name.setStyleSheet(f"color:{TEXT_PRIMARY};")
        self._sip_name.setWordWrap(True)
        self._sip_meta = QLabel("")
        self._sip_meta.setFont(QFont(FONT_BODY, 10))
        self._sip_meta.setStyleSheet(f"color:{TEXT_MUTED};")
        self._sip_notes = QLabel("")
        self._sip_notes.setFont(QFont(FONT_BODY, 12))
        self._sip_notes.setStyleSheet(f"color:#a09070; font-style:italic;")
        self._sip_notes.setWordWrap(True)
        self._sip_notes.setVisible(False)
        sip_l.addWidget(self._sip_name)
        sip_l.addWidget(self._sip_meta)
        sip_l.addWidget(self._sip_notes)
        rt.addWidget(self._slot_info_panel)

        # Rack bottom actions
        rack_foot = QWidget()
        rack_foot.setStyleSheet(f"background:#1a1a1a; border-top:1px solid #2a2a2a;")
        rfl = QVBoxLayout(rack_foot)
        rfl.setContentsMargins(8, 8, 8, 8)
        rfl.setSpacing(4)
        rack_row = QHBoxLayout()
        self.ren_btn = ghost_push("EDIT", small=True)
        self.ren_btn.clicked.connect(self._edit_rack)
        self.rem_btn = ghost_push("REMOVE", danger=True, small=True)
        self.rem_btn.clicked.connect(self._remove_rack)
        rack_row.addWidget(self.ren_btn)
        rack_row.addWidget(self.rem_btn)
        add_rack_btn = ghost_push("+ ADD RACK", amber=True)
        add_rack_btn.clicked.connect(self._add_rack)
        rfl.addLayout(rack_row)
        rfl.addWidget(add_rack_btn)
        rt.addWidget(rack_foot)

        self._tab_stack.addWidget(racks_tab)

        # Tab 2: LIBRARY
        lib_tab = QWidget()
        lib_tab.setStyleSheet(f"background:#1a1a1a;")
        lt = QVBoxLayout(lib_tab)
        lt.setContentsMargins(0, 0, 0, 0)
        lt.setSpacing(0)

        # Filter + search
        fs = QWidget()
        fs.setStyleSheet(f"background:#1a1a1a;")
        fsl = QVBoxLayout(fs)
        fsl.setContentsMargins(8, 6, 8, 4)
        fsl.setSpacing(4)

        self.cat_filter = QComboBox()
        self.cat_filter.setStyleSheet(f"""
            QComboBox {{ background:#111; color:{TEXT_MUTED}; border:1px solid #1a1a1a;
                border-radius:3px; font-size:10px; padding:3px 6px; }}
            QComboBox QAbstractItemView {{ background:{BG2}; color:{TEXT_PRIMARY};
                border:1px solid {BG4}; selection-background-color:{BG3}; }}
        """)
        self.cat_filter.addItem("All categories")
        self.cat_filter.addItems(get_categories())
        self.cat_filter.currentTextChanged.connect(self._refresh_lib)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search…")
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{ background:#222; color:{TEXT_PRIMARY}; border:1px solid #1a1a1a;
                border-radius:3px; font-size:11px; padding:4px 8px; }}
            QLineEdit:focus {{ border-color:#333; }}
        """)
        self.search_edit.textChanged.connect(self._refresh_lib)
        fsl.addWidget(self.cat_filter)
        fsl.addWidget(self.search_edit)
        lt.addWidget(fs)
        lt.addWidget(h_sep())

        self.lib_list = DraggableLibList()
        self.lib_list.setStyleSheet(f"""
            QListWidget {{ background:#1a1a1a; border:none; outline:none; font-size:11px; }}
            QListWidget::item {{ padding:6px 12px; border-bottom:1px solid #242424; color:{TEXT_SECONDARY}; }}
            QListWidget::item:hover {{ background:#222; color:{TEXT_PRIMARY}; }}
            QListWidget::item:selected {{ background:#222; color:{TEXT_PRIMARY}; }}
        """)
        self.lib_list.itemDoubleClicked.connect(self._add_device_dbl)
        lt.addWidget(self.lib_list)

        hint = QLabel("  Drag into rack  ·  Double-click to append")
        hint.setStyleSheet(f"color:#555; font-size:9px; padding:3px 0 2px;")
        lt.addWidget(hint)

        # Custom slot at bottom of library tab
        lt.addWidget(h_sep())
        custom_w = QWidget()
        custom_w.setStyleSheet(f"background:#1a1a1a;")
        cvl = QVBoxLayout(custom_w)
        cvl.setContentsMargins(8, 8, 8, 8)
        cvl.setSpacing(5)
        cvl.addWidget(lbl("CUSTOM SLOT", 9, True, "#2a2a2a", 1.5))
        cr = QHBoxLayout()
        self.custom_name = self.custom_name = QLineEdit()
        self.custom_name.setPlaceholderText("Label…")
        self.custom_name.setStyleSheet(f"""
            QLineEdit {{ background:#222; color:{TEXT_PRIMARY}; border:1px solid #1a1a1a;
                border-radius:3px; font-size:11px; padding:4px 6px; }}
        """)

        # U spinner manuale — QSpinBox non renderizza le frecce correttamente
        self._custom_u_val = 1
        spin_w = QWidget()
        spin_w.setFixedWidth(62)
        spin_w.setStyleSheet("background:transparent;")
        spin_layout = QHBoxLayout(spin_w)
        spin_layout.setContentsMargins(0, 0, 0, 0)
        spin_layout.setSpacing(0)

        self._custom_u_lbl = QLabel("1")
        self._custom_u_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._custom_u_lbl.setFixedWidth(28)
        self._custom_u_lbl.setStyleSheet(f"""
            QLabel {{ background:#222; color:{TEXT_PRIMARY}; border:1px solid #333;
                border-right:none; border-radius:0; font-size:11px; padding:3px 0; }}
        """)

        btn_col = QWidget()
        btn_col.setFixedWidth(18)
        btn_col_l = QVBoxLayout(btn_col)
        btn_col_l.setContentsMargins(0, 0, 0, 0)
        btn_col_l.setSpacing(0)

        btn_style = f"""
            QPushButton {{
                background:#2a2a2a; color:{TEXT_SECONDARY};
                border:1px solid #333; border-radius:0;
                font-size:8px; padding:0; min-height:12px; max-height:12px;
            }}
            QPushButton:hover {{ background:#383838; color:{TEXT_PRIMARY}; }}
            QPushButton:pressed {{ background:#1a1a1a; }}
        """
        up_btn = QPushButton("▲")
        up_btn.setFixedSize(18, 12)
        up_btn.setStyleSheet(btn_style)
        dn_btn = QPushButton("▼")
        dn_btn.setFixedSize(18, 12)
        dn_btn.setStyleSheet(btn_style)

        def _u_up():
            self._custom_u_val = min(20, self._custom_u_val + 1)
            self._custom_u_lbl.setText(str(self._custom_u_val))

        def _u_dn():
            self._custom_u_val = max(1, self._custom_u_val - 1)
            self._custom_u_lbl.setText(str(self._custom_u_val))

        up_btn.clicked.connect(_u_up)
        dn_btn.clicked.connect(_u_dn)
        btn_col_l.addWidget(up_btn)
        btn_col_l.addWidget(dn_btn)

        spin_layout.addWidget(self._custom_u_lbl)
        spin_layout.addWidget(btn_col)

        u_lbl = QLabel("U")
        u_lbl.setStyleSheet(f"color:#606060; font-size:9px; padding-left:2px;")
        cr.addWidget(self.custom_name)
        cr.addWidget(spin_w)
        cr.addWidget(u_lbl)
        cvl.addLayout(cr)
        add_custom_btn = ghost_push("Add to selected rack", small=True)
        add_custom_btn.clicked.connect(self._add_custom)
        cvl.addWidget(add_custom_btn)
        lt.addWidget(custom_w)

        self._tab_stack.addWidget(lib_tab)
        

        # ── Canvas ────────────────────────────────────────────────────────────
        canvas_w = QWidget()
        canvas_w.setStyleSheet(f"background:#181818;")
        cw = QVBoxLayout(canvas_w)
        cw.setContentsMargins(0, 0, 0, 0)
        cw.setSpacing(0)

        # Info bar
        info_bar = QWidget()
        info_bar.setFixedHeight(34)
        info_bar.setStyleSheet(f"background:#1a1a1a; border-bottom:1px solid #2a2a2a;")
        ibl = QHBoxLayout(info_bar)
        ibl.setContentsMargins(16, 0, 16, 0)
        self.info_lbl = QLabel("")
        self.info_lbl.setStyleSheet(f"color:#606060; font-size:10px;")
        ibl.addWidget(self.info_lbl)
        ibl.addStretch()
        cw.addWidget(info_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background:{BG0}; border:none;")
        scroll.setAcceptDrops(True)
        self.rack_container = QWidget()
        self.rack_container.setStyleSheet(f"background:#181818;")
        self.rack_container.setAcceptDrops(True)
        self.rack_area = QHBoxLayout(self.rack_container)
        self.rack_area.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.rack_area.setContentsMargins(28, 28, 28, 28)
        self.rack_area.setSpacing(36)
        scroll.setWidget(self.rack_container)
        cw.addWidget(scroll)

        splitter.addWidget(sidebar)
        splitter.addWidget(canvas_w)
        splitter.setSizes([260, 1100])
        splitter.setCollapsible(0, False)
        root.addWidget(splitter)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def _refresh(self):
        self._refresh_rack_view()
        self._refresh_lib()

    def _refresh_rack_view(self):
        self._clear_racks()
        for rack in self.project.racks:
            canvas = RackCanvas(rack)
            canvas.slot_removed.connect(self._on_changed)
            canvas.slot_moved.connect(self._on_changed)
            canvas.slot_selected.connect(self._on_slot_selected)
            canvas.became_active.connect(self._on_canvas_active)

            wrapper = QWidget()
            wrapper.setStyleSheet(f"background:#181818;")
            wrapper.setAcceptDrops(True)
            wl = QVBoxLayout(wrapper)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(0)

            # Rack header: name centrato sopra il canvas
            wl.addStretch()   # spinge nome+canvas in basso → allineati al fondo
            nl = QLabel(rack.name.upper())
            nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nl.setStyleSheet(f"color:#505050; font-size:8px; font-weight:700; letter-spacing:2px; padding-bottom:6px; padding-left:40px;")
            wl.addWidget(nl)
            wl.addWidget(canvas)
            self.rack_area.addWidget(wrapper)
            self._canvases.append(canvas)

        self._refresh_rack_list()
        self._update_info()

    def _clear_racks(self):
        for c in self._canvases:
            c.setParent(None)
        self._canvases.clear()
        while self.rack_area.count():
            item = self.rack_area.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _refresh_rack_list(self):
        self.rack_list.clear()
        for rack in self.project.racks:
            item = QListWidgetItem(f"{rack.name}\n{rack.used_u()}U / {rack.u_size}U")
            item.setToolTip(f"{rack.free_u()}U free · {rack.total_watts():.0f}W · {rack.total_weight():.1f}kg")
            self.rack_list.addItem(item)

    def _refresh_lib(self):
        self.lib_list.clear()
        cat = self.cat_filter.currentText()
        query = self.search_edit.text().strip().lower()
        for dev in sorted(self.library, key=lambda d: (d.category, d.name)):
            if cat not in ("All categories",) and dev.category != cat:
                continue
            if query and query not in dev.name.lower() and query not in dev.manufacturer.lower() \
                    and query not in dev.model.lower() \
                    and query not in getattr(dev, 'description', '').lower():
                continue
            item = QListWidgetItem(f"{dev.name}  ·  {dev.u_height}U")
            item.setData(Qt.ItemDataRole.UserRole, dev.id)
            item.setForeground(QColor(dev.effective_color()))
            item.setToolTip(f"{dev.category}  |  {dev.manufacturer}  |  {dev.u_height}U")
            self.lib_list.addItem(item)

    def _update_info(self):
        if not self.project.racks:
            self.info_lbl.setText("No racks — add one from the Racks tab")
            return
        total_dev = sum(len(r.slots) for r in self.project.racks)
        used = sum(r.used_u() for r in self.project.racks)
        total = sum(r.u_size for r in self.project.racks)
        watts = sum(r.total_watts() for r in self.project.racks)
        s = f"{len(self.project.racks)} rack{'s' if len(self.project.racks)>1 else ''}  ·  {total_dev} devices  ·  {used}/{total}U"
        if watts > 0:
            s += f"  ·  {watts:.0f}W total"
        self.info_lbl.setText(s)

    def _on_canvas_active(self, canvas: RackCanvas):
        self._active_canvas = canvas

    def undo(self):
        if self._active_canvas is not None:
            self._active_canvas.undo()

    def reload_library(self):
        self.library = storage.load_library()
        self._refresh_lib()

    def set_project(self, project):
        self.project = project
        self._refresh()

    def _on_slot_selected(self, slot):
        if slot is None:
            self._slot_info_panel.setVisible(False)
            return
        # Name
        self._sip_name.setText(slot.name)
        # Meta line: category · dims · watts · weight
        parts = []
        parts.append(slot.category)
        if slot.is_tray:
            used = slot.tray_used_width_mm()
            parts.append(f"{used:.0f}/{482}mm wide")
        else:
            snap = slot.device_snapshot
            dims = []
            if snap.get("width_mm"):  dims.append(f"W {snap['width_mm']:.0f}mm")
            if snap.get("height_mm"): dims.append(f"H {snap['height_mm']:.0f}mm")
            if snap.get("depth_mm"):  dims.append(f"D {snap['depth_mm']:.0f}mm")
            if dims: parts.append(" · ".join(dims))
        if slot.watts:  parts.append(f"{slot.watts:.0f} W")
        if slot.weight_kg: parts.append(f"{slot.weight_kg:.1f} kg")
        self._sip_meta.setText("  ·  ".join(parts))
        # Notes
        if slot.notes:
            self._sip_notes.setText(f"Note: {slot.notes}")
            self._sip_notes.setVisible(True)
        else:
            self._sip_notes.setVisible(False)
        self._slot_info_panel.setVisible(True)

    def _on_changed(self):
        self._update_info()
        self._refresh_rack_list()
        self.project_changed.emit()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_rack(self):
        dlg = AddRackDialog(self)
        if dlg.exec():
            rack = Rack(name=dlg.name_edit.text().strip() or "New Rack",
                        u_size=dlg.size_spin.value(),
                        bays=dlg.bays_spin.value())
            self.project.racks.append(rack)
            self._clear_racks()
            self._refresh_rack_view()
            self._on_changed()

    def _remove_rack(self):
        row = self.rack_list.currentRow()
        if row < 0 or row >= len(self.project.racks):
            MsgBox.info(self, "Remove rack", "Select a rack first.")
            return
        rack = self.project.racks[row]
        if not MsgBox.question_danger(self, "Remove rack", f"Remove '{rack.name}' and all its contents?"):
            return
        self.project.racks.pop(row)
        self._clear_racks()
        self._refresh_rack_view()
        self._on_changed()

    def _edit_rack(self):
        row = self.rack_list.currentRow()
        if row < 0 or row >= len(self.project.racks):
            return
        rack = self.project.racks[row]
        dlg = EditRackDialog(rack, self)
        if not dlg.exec():
            return

        new_name = dlg.name_edit.text().strip() or rack.name
        new_size = dlg.size_spin.value()
        delta    = new_size - rack.u_size   # >0 aggiunge U in cima, <0 rimuove

        if delta < 0:
            # Controlla se ci sono slot occupati nelle U che verrebbero rimosse in cima
            removed_rows = range(1, 1 - delta + 1)   # U 1..abs(delta) verranno eliminate
            colliding = [
                s for s in rack.slots
                if any(s.position_u <= u < s.position_u + s.u_height for u in removed_rows)
            ]
            if colliding:
                names = ", ".join(s.name for s in colliding[:3])
                if len(colliding) > 3:
                    names += f" e altri {len(colliding)-3}"
                MsgBox.warn(self, "Units in use",
                    f"Cannot remove {-delta}U: the following units at the top are occupied:\n{names}")
                return
            # Shift verso l'alto degli slot rimasti
            for s in rack.slots:
                s.position_u += delta   # delta è negativo → shift su

        elif delta > 0:
            # Shift verso il basso: le U aggiunte vanno in cima
            for s in rack.slots:
                s.position_u += delta

        rack.name   = new_name
        rack.u_size = new_size
        self._clear_racks()
        self._refresh_rack_view()
        self._on_changed()

    def _add_device_dbl(self, item):
        dev_id = item.data(Qt.ItemDataRole.UserRole)
        dev = next((d for d in self.library if d.id == dev_id), None)
        if not dev:
            return
        row = self.rack_list.currentRow()
        if row < 0:
            if len(self.project.racks) == 1:
                row = 0
            else:
                MsgBox.info(self, "Add device", "Select a rack first.")
                return
        if not self._canvases[row].add_device(dev):
            MsgBox.warn(self, "No space", f"Not enough free space in '{self.project.racks[row].name}'.")
        else:
            self._on_changed()

    def _add_custom(self):
        name = self.custom_name.text().strip()
        if not name:
            MsgBox.info(self, "Custom slot", "Enter a label first.")
            return
        row = self.rack_list.currentRow()
        if row < 0:
            if len(self.project.racks) == 0:
                MsgBox.info(self, "Custom slot", "No racks in project.")
                return
            elif len(self.project.racks) == 1:
                row = 0
            else:
                rack_names = [r.name for r in self.project.racks]
                from PyQt6.QtWidgets import QInputDialog
                choice, ok = QInputDialog.getItem(
                    self, "Select rack", "Add custom slot to:", rack_names, 0, False)
                if not ok:
                    return
                row = rack_names.index(choice)
        import uuid
        dev = DeviceDefinition(id=str(uuid.uuid4()), name=name, category="Other",
                               u_height=self._custom_u_val, color="#555555")
        if not self._canvases[row].add_device(dev):
            MsgBox.warn(self, "No space", "Not enough free space.")
        else:
            self.custom_name.clear()
            self._on_changed()


# ── EXPORT section ────────────────────────────────────────────────────────────

class ExportSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = Project()
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:#181818;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content = QWidget()
        content.setStyleSheet("background:#181818;")
        cl = QHBoxLayout(content)
        cl.setContentsMargins(28, 24, 28, 24)
        cl.setSpacing(40)
        cl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # RACKS column
        rack_col_w = QWidget()
        rack_col_w.setMinimumWidth(180)
        rack_col_w.setStyleSheet("background:transparent;")
        rack_col_l = QVBoxLayout(rack_col_w)
        rack_col_l.setContentsMargins(0, 0, 0, 0)
        rack_col_l.setSpacing(0)
        rack_title = QLabel("RACKS TO INCLUDE")
        rack_title.setStyleSheet("color:#606060; font-size:9px; font-weight:700; letter-spacing:2px; padding-bottom:10px;")
        rack_col_l.addWidget(rack_title)
        # Inner widget for checkboxes only — so clear() doesnt delete the title
        self._rack_inner = QWidget()
        self._rack_inner.setStyleSheet("background:transparent;")
        self.rack_checks_layout = QVBoxLayout(self._rack_inner)
        self.rack_checks_layout.setContentsMargins(0, 0, 0, 0)
        self.rack_checks_layout.setSpacing(0)
        rack_col_l.addWidget(self._rack_inner)
        rack_col_l.addStretch()
        cl.addWidget(rack_col_w)

        # CONTENT column
        cont_col_w = QWidget()
        cont_col_w.setMinimumWidth(240)
        cont_col_w.setStyleSheet("background:transparent;")
        cont_col_l = QVBoxLayout(cont_col_w)
        cont_col_l.setContentsMargins(0, 0, 0, 0)
        cont_col_l.setSpacing(0)
        cont_title = QLabel("CONTENT")
        cont_title.setStyleSheet("color:#606060; font-size:9px; font-weight:700; letter-spacing:2px; padding-bottom:10px;")
        cont_col_l.addWidget(cont_title)

        self.chk_diagram     = self._chk("Rack diagram", False)
        self.chk_color       = self._chk_sub("Color (uncheck for B&&W)", False)
        self.chk_devlist     = self._chk("Device list per rack", False)
        self.chk_devlist_cat = self._chk_sub("Include category column", False)
        self.chk_power       = self._chk("Power totals", False)
        self.chk_weight      = self._chk("Weight totals", False)
        self.chk_summary     = self._chk("Project summary", False)
        self.chk_notes       = self._chk("Slot notes", False)

        # Sub-options start disabled; enabled when parent is checked
        self.chk_color.setEnabled(False)
        self.chk_devlist_cat.setEnabled(False)
        self.chk_diagram.stateChanged.connect(
            lambda s: self.chk_color.setEnabled(bool(s)))
        self.chk_devlist.stateChanged.connect(
            lambda s: self.chk_devlist_cat.setEnabled(bool(s)))

        for c in [self.chk_diagram, self.chk_color,
                  self.chk_devlist, self.chk_devlist_cat,
                  self.chk_power, self.chk_weight,
                  self.chk_summary, self.chk_notes]:
            c.stateChanged.connect(self._update_summary)
            cont_col_l.addWidget(c)
        cont_col_l.addStretch()
        cl.addWidget(cont_col_w)

        root.addWidget(content)
        root.addStretch()

        # Footer
        footer = QWidget()
        footer.setFixedHeight(44)
        footer.setStyleSheet("background:#111; border-top:1px solid #1e1e1e;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(28, 0, 28, 0)
        fl.setSpacing(14)
        self.export_btn = ghost_push("EXPORT PDF", amber=True)
        self.export_btn.clicked.connect(self._do_export)
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("color:#707070; font-size:10px;")
        fl.addWidget(self.export_btn)
        fl.addWidget(self.summary_lbl)
        fl.addStretch()
        root.addWidget(footer)

    def _chk(self, text, checked=False):
        c = QCheckBox(text)
        c.setChecked(checked)
        c.setCursor(Qt.CursorShape.PointingHandCursor)
        c.setStyleSheet("""
            QCheckBox {
                color:#909090; font-size:12px; spacing:10px;
                padding:8px 0; border-bottom:1px solid #232323;
                min-width:180px;
            }
            QCheckBox:hover { color:#c8c0ac; }
            QCheckBox:disabled { color:#404040; }
            QCheckBox::indicator {
                width:14px; height:14px;
                background:#232323; border:1px solid #404040; border-radius:3px;
            }
            QCheckBox::indicator:checked {
                background:#e8a020; border:1px solid #e8a020;
            }
            QCheckBox::indicator:disabled {
                background:#1a1a1a; border:1px solid #2a2a2a;
            }
            QCheckBox::indicator:checked:disabled {
                background:#3a2e10; border:1px solid #3a2e10;
            }
        """)
        return c

    def _chk_sub(self, text, checked=False):
        """Sub-option checkbox: indented, smaller, fully invisible when disabled."""
        c = QCheckBox(text)
        c.setChecked(checked)
        c.setCursor(Qt.CursorShape.PointingHandCursor)
        c.setStyleSheet("""
            QCheckBox {
                color:#555555; font-size:11px; spacing:10px;
                padding:5px 0 5px 20px; border-bottom:1px solid #1e1e1e;
                min-width:200px;
            }
            QCheckBox:enabled { color:#909090; }
            QCheckBox:hover:enabled { color:#c8c0ac; }
            QCheckBox:disabled { color:#2a2a2a; }
            QCheckBox::indicator {
                width:12px; height:12px;
                background:#1e1e1e; border:1px solid #2a2a2a; border-radius:2px;
            }
            QCheckBox::indicator:enabled {
                background:#232323; border:1px solid #404040;
            }
            QCheckBox::indicator:checked:enabled {
                background:#e8a020; border:1px solid #e8a020;
            }
            QCheckBox::indicator:disabled {
                background:#181818; border:1px solid #181818;
            }
            QCheckBox::indicator:checked:disabled {
                background:#181818; border:1px solid #181818;
            }
        """)
        return c

    def set_project(self, project):
        self.project = project
        self._rebuild_rack_checks()
        self._update_summary()

    def _rebuild_rack_checks(self):
        while self.rack_checks_layout.count():
            item = self.rack_checks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rack_checkboxes = []
        for rack in self.project.racks:
            c = self._chk(rack.name, True)
            self.rack_checks_layout.addWidget(c)
            self._rack_checkboxes.append((rack, c))
        self._update_summary()

    def _update_summary(self):
        selected = sum(1 for _, c in getattr(self, '_rack_checkboxes', []) if c.isChecked())
        self.summary_lbl.setText(f"{selected} rack{'s' if selected != 1 else ''}")

    def _do_export(self):
        if not self.project.racks:
            MsgBox.info(self, "Export", "No racks in project.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", f"{self.project.name}.pdf", "PDF (*.pdf)")
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        selected_racks = [r for r, c in getattr(self, '_rack_checkboxes', []) if c.isChecked()]
        if not selected_racks:
            MsgBox.info(self, "Export", "Select at least one rack.")
            return
        options = {
            "include_front":            True,
            "include_diagram":          self.chk_diagram.isChecked(),
            "use_color":                self.chk_color.isChecked() and self.chk_diagram.isChecked(),
            "include_devlist":          self.chk_devlist.isChecked(),
            "include_devlist_category": self.chk_devlist_cat.isChecked() and self.chk_devlist.isChecked(),
            "include_power":            self.chk_power.isChecked(),
            "include_weight":           self.chk_weight.isChecked(),
            "include_summary":          self.chk_summary.isChecked(),
            "include_notes":            self.chk_notes.isChecked(),
        }
        try:
            from app.pdf_export import export_pdf
            import dataclasses
            export_project = dataclasses.replace(self.project, racks=selected_racks)
            export_pdf(export_project, path, options=options)
            MsgBox.info(self, "Export PDF", f"PDF saved:\n{path}")
        except Exception as e:
            MsgBox.error(self, "Export error", str(e))


# ── LIBRARY section ───────────────────────────────────────────────────────────

class LibrarySection(QWidget):
    library_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.devices: list[DeviceDefinition] = []
        self._current_id = None
        self._build()
        self.reload()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tb = QWidget()
        tb.setFixedHeight(44)
        tb.setStyleSheet(f"background:#1a1a1a; border-bottom:1px solid #2a2a2a;")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(16, 0, 16, 0)
        tbl.setSpacing(8)
        self.cat_filter = QComboBox()
        self.cat_filter.setFixedWidth(150)
        self.cat_filter.setStyleSheet(f"""
            QComboBox {{ background:#111; color:{TEXT_MUTED}; border:1px solid #1a1a1a;
                border-radius:3px; font-size:10px; padding:3px 6px; }}
            QComboBox QAbstractItemView {{ background:{BG2}; color:{TEXT_PRIMARY};
                border:1px solid {BG4}; selection-background-color:{BG3}; }}
        """)
        self.cat_filter.addItem("All categories")
        self.cat_filter.addItems(get_categories())
        self.cat_filter.currentTextChanged.connect(self._apply_filter)
        tbl.addWidget(self.cat_filter)
        self.lib_search_edit = QLineEdit()
        self.lib_search_edit.setPlaceholderText("Search…")
        self.lib_search_edit.setFixedWidth(180)
        self.lib_search_edit.setStyleSheet(f"""
            QLineEdit {{ background:#222; color:{TEXT_PRIMARY}; border:1px solid #1a1a1a;
                border-radius:3px; font-size:11px; padding:3px 8px; }}
            QLineEdit:focus {{ border-color:#333; }}
        """)
        self.lib_search_edit.textChanged.connect(self._apply_filter)
        tbl.addWidget(self.lib_search_edit)
        tbl.addStretch()
        imp_btn = ghost_push("IMPORT", small=True)
        imp_btn.clicked.connect(self._import_dialog)
        exp_btn = ghost_push("EXPORT", small=True)
        exp_btn.clicked.connect(self._export_dialog)
        tbl.addWidget(imp_btn)
        tbl.addWidget(exp_btn)
        root.addWidget(tb)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet(f"QSplitter::handle {{ background:#141414; }}")

        list_w = QWidget()
        list_w.setStyleSheet(f"background:#181818;")
        ll = QVBoxLayout(list_w)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        self.dev_list = QListWidget()
        self.dev_list.setStyleSheet(f"""
            QListWidget {{ background:{BG0}; border:none; outline:none; font-size:11px; }}
            QListWidget::item {{ padding:9px 14px; border-bottom:1px solid #0f0f0f; color:{TEXT_SECONDARY}; }}
            QListWidget::item:hover {{ background:#0f0f0f; color:{TEXT_SECONDARY}; }}
            QListWidget::item:selected {{ background:#0f0f0f; color:{TEXT_PRIMARY};
                border-left:2px solid {ACCENT}; padding-left:12px; }}
        """)
        self.dev_list.currentRowChanged.connect(self._on_select)
        ll.addWidget(self.dev_list)

        footer = QWidget()
        footer.setStyleSheet(f"background:#1a1a1a; border-top:1px solid #2a2a2a;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(10, 7, 10, 7)
        fl.setSpacing(6)
        new_btn = ghost_push("+ NEW", amber=True, small=True)
        new_btn.clicked.connect(self._new)
        dup_btn = ghost_push("DUPLICATE", small=True)
        dup_btn.clicked.connect(self._duplicate)
        del_btn = ghost_push("DELETE", danger=True, small=True)
        del_btn.clicked.connect(self._delete)
        fl.addWidget(new_btn)
        fl.addWidget(dup_btn)
        fl.addStretch()
        fl.addWidget(del_btn)
        ll.addWidget(footer)

        form_w = QWidget()
        form_w.setStyleSheet(f"background:{BG1};")
        fw = QVBoxLayout(form_w)
        fw.setContentsMargins(0, 0, 0, 0)
        fw.setSpacing(0)

        fh = QWidget()
        fh.setFixedHeight(44)
        fh.setStyleSheet(f"background:#1a1a1a; border-bottom:1px solid #2a2a2a;")
        fhl = QHBoxLayout(fh)
        fhl.setContentsMargins(16, 0, 16, 0)
        self.form_title = QLabel("Select a device to edit")
        self.form_title.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:12px; font-weight:600;")
        fhl.addWidget(self.form_title)
        fhl.addStretch()
        self.save_btn = ghost_push("SAVE", amber=True)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        fhl.addWidget(self.save_btn)
        fw.addWidget(fh)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background:{BG1}; border:none;")
        from app.library_dialog import DeviceForm
        self.form = DeviceForm()
        self.form.setEnabled(False)
        self.form.setStyleSheet(f"background:{BG1};")
        scroll.setWidget(self.form)
        fw.addWidget(scroll)

        splitter.addWidget(list_w)
        splitter.addWidget(form_w)
        splitter.setSizes([320, 720])
        root.addWidget(splitter)

    def reload(self):
        self.devices = storage.load_library()
        cats = ["All categories"] + get_categories()
        current = self.cat_filter.currentText()
        self.cat_filter.blockSignals(True)
        self.cat_filter.clear()
        self.cat_filter.addItems(cats)
        idx = self.cat_filter.findText(current)
        self.cat_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.cat_filter.blockSignals(False)
        self._apply_filter()

    def _apply_filter(self):
        cat = self.cat_filter.currentText()
        query = self.lib_search_edit.text().strip().lower()
        self.dev_list.clear()
        for dev in sorted(self.devices, key=lambda d: (d.category, d.name)):
            if cat != "All categories" and dev.category != cat:
                continue
            if query:
                haystack = " ".join([
                    dev.name.lower(),
                    dev.manufacturer.lower(),
                    dev.model.lower(),
                    getattr(dev, 'description', '').lower(),
                ])
                if query not in haystack:
                    continue
            item = QListWidgetItem(f"{dev.name}   [{dev.category}]   {dev.u_height}U")
            item.setData(Qt.ItemDataRole.UserRole, dev.id)
            item.setForeground(QColor(dev.effective_color()))
            self.dev_list.addItem(item)

    def _on_select(self, row):
        if row < 0:
            self._current_id = None
            self.form.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.form_title.setText("Select a device to edit")
            return
        dev_id = self.dev_list.item(row).data(Qt.ItemDataRole.UserRole)
        dev = next((d for d in self.devices if d.id == dev_id), None)
        if dev:
            self._current_id = dev.id
            self.form.load(dev)
            self.form.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.form_title.setText(dev.name)

    def _new(self):
        dev = DeviceDefinition(name="New Device")
        self.devices.append(dev)
        storage.save_library(self.devices)
        self._apply_filter()
        for i in range(self.dev_list.count()):
            if self.dev_list.item(i).data(Qt.ItemDataRole.UserRole) == dev.id:
                self.dev_list.setCurrentRow(i)
                break
        self.library_changed.emit()

    def _duplicate(self):
        if not self._current_id:
            return
        src = next((d for d in self.devices if d.id == self._current_id), None)
        if not src:
            return
        import dataclasses, uuid
        dup = dataclasses.replace(src, id=str(uuid.uuid4()), name=src.name + " (copy)")
        self.devices.append(dup)
        storage.save_library(self.devices)
        self._apply_filter()
        self.library_changed.emit()

    def _delete(self):
        if not self._current_id:
            return
        dev = next((d for d in self.devices if d.id == self._current_id), None)
        if not dev:
            return
        if not MsgBox.question_danger(self, "Delete",
                                      f"Delete '{dev.name}'?\nExisting projects are not affected."):
            return
        self.devices = [d for d in self.devices if d.id != self._current_id]
        self._current_id = None
        storage.save_library(self.devices)
        self._apply_filter()
        self.form.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.library_changed.emit()

    def _save(self):
        if not self._current_id:
            return
        data = self.form.collect()
        if not data["name"]:
            MsgBox.warn(self, "Validation", "Device name is required.")
            return
        for dev in self.devices:
            if dev.id == self._current_id:
                for k, v in data.items():
                    setattr(dev, k, v)
                break
        storage.save_library(self.devices)
        self._apply_filter()
        self.form_title.setText(data["name"])
        self.library_changed.emit()

    def _export_dialog(self):
        """Export: scope (all / per category / selected device) then format (JSON / CSV)."""
        import json, csv as _csv

        # ── Step 1: scope type ────────────────────────────────────────────────
        from PyQt6.QtWidgets import QInputDialog

        scope_items = ["Entire library", "Category", "Selected device"]
        if not self._current_id:
            scope_items.remove("Selected device")

        scope, ok = QInputDialog.getItem(
            self, "Export — scope", "What to export:", scope_items, 0, False)
        if not ok:
            return

        if scope == "Entire library":
            devs = list(self.devices)

        elif scope == "Category":
            all_cats = sorted({d.category for d in self.devices})
            cat_name, ok = QInputDialog.getItem(
                self, "Export — category", "Select category:", all_cats, 0, False)
            if not ok:
                return
            devs = [d for d in self.devices if d.category == cat_name]

        else:  # Selected device
            devs = [d for d in self.devices if d.id == self._current_id]

        if not devs:
            MsgBox.info(self, "Export", "Nothing to export.")
            return

        # ── Step 2: format ────────────────────────────────────────────────────
        fmt, ok = QInputDialog.getItem(
            self, "Export — format", "File format:", ["JSON (.json)", "CSV (.csv)"], 0, False)
        if not ok:
            return

        if fmt.startswith("JSON"):
            default_name = "library.json" if len(devs) > 1 else f"{devs[0].name.replace(' ','_')}.json"
            path, _ = QFileDialog.getSaveFileName(
                self, "Export library", default_name, "JSON (*.json)")
            if not path:
                return
            if not path.endswith(".json"):
                path += ".json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump([d.to_dict() for d in devs], f, indent=2, ensure_ascii=False)
        else:
            default_name = "library.csv" if len(devs) > 1 else f"{devs[0].name.replace(' ','_')}.csv"
            path, _ = QFileDialog.getSaveFileName(
                self, "Export library", default_name, "CSV (*.csv)")
            if not path:
                return
            if not path.endswith(".csv"):
                path += ".csv"
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = _csv.writer(f, delimiter=";")
                writer.writerow([
                    "Name", "Manufacturer", "Model", "Description", "Category",
                    "Power (W)", "Height (U)", "W", "H", "D", "Weight (kg)", "Notes"
                ])
                for d in devs:
                    writer.writerow([
                        d.name, d.manufacturer, d.model,
                        getattr(d, "description", ""),
                        d.category,
                        str(d.watts).replace(".", ",") if d.watts is not None else "",
                        str(d.u_height) if d.rack_native else "",
                        str(d.width_mm).replace(".", ",") if d.width_mm is not None else "",
                        str(d.height_mm).replace(".", ",") if d.height_mm is not None else "",
                        str(d.depth_mm).replace(".", ",") if d.depth_mm is not None else "",
                        str(d.weight_kg).replace(".", ",") if d.weight_kg is not None else "",
                        d.notes,
                    ])

        MsgBox.info(self, "Export", f"Exported {len(devs)} device(s).")

    def _import_dialog(self):
        """Import: pick file (JSON or CSV), then merge or replace."""
        import json

        path, _ = QFileDialog.getOpenFileName(
            self, "Import library", "",
            "Library files (*.json *.csv);;JSON (*.json);;CSV (*.csv)")
        if not path:
            return

        # ── Parse ─────────────────────────────────────────────────────────────
        try:
            if path.lower().endswith(".csv"):
                imported, new_cats, warnings = storage.import_library_csv(path)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                imported = [DeviceDefinition.from_dict(d) for d in data]
                new_cats, warnings = [], []
        except Exception as e:
            MsgBox.error(self, "Import error", str(e))
            return

        if not imported:
            msg = "No devices found in the file."
            if warnings:
                msg += "\n\n" + "\n".join(warnings)
            MsgBox.warn(self, "Import", msg)
            return

        # ── Summary + merge/replace ───────────────────────────────────────────
        info = f"{len(imported)} device(s) found."
        if new_cats:
            info += f"\nNew categories: {', '.join(new_cats)}."
        if warnings:
            info += f"\n\nWarnings ({len(warnings)}):\n" + "\n".join(warnings)

        from app.dialogs import _MsgDialog
        dlg = _MsgDialog(self, "Import", info, "question",
                         [("Cancel", "cancel"), ("Replace", "replace"), ("Merge", "accept")])
        dlg.exec()
        result = dlg.get_result()

        if result is None or result == "cancel":
            return

        if result == "accept":  # Merge
            existing = {(d.name, d.category) for d in self.devices}
            to_add = [d for d in imported if (d.name, d.category) not in existing]
            self.devices += to_add
            MsgBox.info(self, "Import",
                        f"Merged: {len(to_add)} new device(s) added.\n"
                        f"{len(imported) - len(to_add)} duplicate(s) skipped.")
        else:  # Replace
            self.devices = imported
            MsgBox.info(self, "Import", f"Library replaced: {len(imported)} device(s).")

        storage.save_library(self.devices)
        self.reload()
        self.library_changed.emit()


# ── ABOUT section ─────────────────────────────────────────────────────────────

class AboutSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:#181818;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background:{BG0}; border:none;")
        container = QWidget()
        container.setStyleSheet(f"background:#181818;")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(72, 56, 72, 56)
        cl.setSpacing(0)

        product = QLabel("RACK DESIGNER")
        product.setFont(QFont(FONT_TITLE, 48))
        product.setStyleSheet(f"color:{TEXT_PRIMARY}; letter-spacing:5px;")
        cl.addWidget(product)

        ver = QLabel("v0.1.18")
        ver.setStyleSheet(f"color:#505050; font-size:12px; letter-spacing:1px; margin-top:6px;")
        cl.addWidget(ver)

        cl.addSpacing(36)
        cl.addWidget(h_sep())
        cl.addSpacing(28)

        desc = QLabel(
            "Professional rack layout tool for live events, tours,\n"
            "installations and productions.\n\n"
            "Design your rig, document your gear, export your rider.")
        desc.setStyleSheet(f"color:{TEXT_MUTED}; font-size:13px; line-height:1.6;")
        desc.setWordWrap(True)
        cl.addWidget(desc)

        cl.addSpacing(32)
        link = QLabel(f'<a href="https://stage-tools.github.io/stagetools/" style="color:{ACCENT}; text-decoration:none;">stage-tools.github.io/stagetools</a>')
        link.setOpenExternalLinks(True)
        link.setStyleSheet("font-size:12px;")
        cl.addWidget(link)
        cl.addSpacing(8)
        author = QLabel("Made by Riccardo Nessi")
        author.setStyleSheet(f"color:#505050; font-size:11px;")
        cl.addWidget(author)
        cl.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll)


# ── Add Rack dialog ───────────────────────────────────────────────────────────

class AddRackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add rack")
        self.resize(320, 240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(lbl("NEW RACK", 9, True, "#606060", 2))
        form = QFormLayout()
        form.setSpacing(8)
        self.name_edit = QLineEdit("New Rack")

        COMMON = [4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 42, 44, 48]
        preset = QComboBox()
        preset.addItem("Custom")
        for s in COMMON:
            preset.addItem(f"{s}U")

        self._size_val = 20
        self._bays_val = 1
        size_w, self._size_lbl, size_up, size_dn = self._make_spin()
        bays_w, self._bays_lbl, bays_up, bays_dn = self._make_spin()
        self._size_lbl.setText("20")
        self._bays_lbl.setText("1")

        # Commit manuale (testo digitato a mano)
        self._size_lbl._commit_fn = lambda: self._commit_spin("_size_val", self._size_lbl, 1, 60)
        self._bays_lbl._commit_fn = lambda: self._commit_spin("_bays_val", self._bays_lbl, 1, 3)

        size_up.clicked.connect(lambda: self._set("_size_val", self._size_lbl, self._size_val + 1, 1, 60))
        size_dn.clicked.connect(lambda: self._set("_size_val", self._size_lbl, self._size_val - 1, 1, 60))
        bays_up.clicked.connect(lambda: self._set("_bays_val", self._bays_lbl, self._bays_val + 1, 1, 3))
        bays_dn.clicked.connect(lambda: self._set("_bays_val", self._bays_lbl, self._bays_val - 1, 1, 3))

        preset.currentIndexChanged.connect(
            lambda i: self._set("_size_val", self._size_lbl, COMMON[i-1], 1, 60) if i > 0 else None)

        form.addRow(lbl("Name",     10, color="#808080"), self.name_edit)
        form.addRow(lbl("Preset",   10, color="#808080"), preset)
        form.addRow(lbl("Size (U)", 10, color="#808080"), size_w)
        form.addRow(lbl("Bays",     10, color="#808080"), bays_w)
        layout.addLayout(form)
        btns = QHBoxLayout()
        cancel = ghost_push("Cancel")
        cancel.setAutoDefault(False)
        cancel.setDefault(False)
        cancel.clicked.connect(self.reject)
        ok = ghost_push("ADD RACK", amber=True)
        ok.setAutoDefault(False)
        ok.setDefault(False)
        ok.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addStretch()
        btns.addWidget(ok)
        layout.addLayout(btns)

        # Invio nei field numerici: committa e chiude
        self._size_lbl.returnPressed.connect(lambda: (self._commit_spin("_size_val", self._size_lbl, 1, 60), self.accept()))
        self._bays_lbl.returnPressed.connect(lambda: (self._commit_spin("_bays_val", self._bays_lbl, 1, 3), self.accept()))

    def _make_spin(self):
        """Campo numerico editabile con frecce laterali."""
        FIELD_H = 28
        BTN_W   = 20
        BTN_H   = FIELD_H // 2

        field_ss = f"""
            QLineEdit {{
                background:{BG3}; color:{TEXT_PRIMARY};
                border:1px solid {BG4};
                border-right:none;
                border-top-left-radius:3px;
                border-bottom-left-radius:3px;
                font-size:13px;
                padding:0 8px;
            }}
            QLineEdit:focus {{
                border:1px solid {ACCENT};
                border-right:none;
            }}
        """
        btn_ss = f"""
            QPushButton {{
                background:{BG4}; color:{TEXT_SECONDARY};
                border:1px solid {BG4}; border-left:none;
                font-size:7px; padding:0; margin:0;
            }}
            QPushButton:hover {{ background:#484848; color:{TEXT_PRIMARY}; }}
            QPushButton:pressed {{ background:{BG2}; }}
        """
        btn_top_ss    = btn_ss + " QPushButton { border-top-right-radius:3px; }"
        btn_bottom_ss = btn_ss + " QPushButton { border-bottom-right-radius:3px; }"

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        container.setFixedHeight(FIELD_H)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        value_edit = QLineEdit("1")
        value_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        value_edit.setFixedHeight(FIELD_H)
        value_edit.setStyleSheet(field_ss)
        # Il commit viene gestito da _set via editingFinished;
        # il riferimento all'attr e ai limiti viene collegato dall'esterno.
        value_edit._commit_fn = None
        value_edit.editingFinished.connect(lambda: value_edit._commit_fn and value_edit._commit_fn())

        btn_col = QWidget()
        btn_col.setFixedSize(BTN_W, FIELD_H)
        btn_col.setStyleSheet("background:transparent;")
        btn_col_l = QVBoxLayout(btn_col)
        btn_col_l.setContentsMargins(0, 0, 0, 0)
        btn_col_l.setSpacing(0)

        up = QPushButton("▲")
        up.setFixedSize(BTN_W, BTN_H)
        up.setStyleSheet(btn_top_ss)
        up.setAutoDefault(False)
        up.setDefault(False)
        dn = QPushButton("▼")
        dn.setFixedSize(BTN_W, BTN_H)
        dn.setStyleSheet(btn_bottom_ss)
        dn.setAutoDefault(False)
        dn.setDefault(False)

        btn_col_l.addWidget(up)
        btn_col_l.addWidget(dn)
        row.addWidget(value_edit, 1)
        row.addWidget(btn_col)

        return container, value_edit, up, dn

    def _set(self, attr, field, value, min_val, max_val):
        value = max(min_val, min(max_val, value))
        setattr(self, attr, value)
        field.setText(str(value))

    def _commit_spin(self, attr, field, min_val, max_val):
        """Normalizza il testo digitato a mano e aggiorna _size_val / _bays_val."""
        text = field.text().strip()
        try:
            v = int(text) if text else getattr(self, attr)
        except ValueError:
            v = getattr(self, attr)
        self._set(attr, field, v, min_val, max_val)

    # Compatibilità con DesignerSection._add_rack() che chiama .value()
    class _Proxy:
        def __init__(self, dialog, attr):
            self._d = dialog; self._a = attr
        def value(self):
            return getattr(self._d, self._a)

    @property
    def size_spin(self): return self._Proxy(self, "_size_val")
    @property
    def bays_spin(self): return self._Proxy(self, "_bays_val")


# ── Edit Rack dialog ──────────────────────────────────────────────────────────

class EditRackDialog(QDialog):
    def __init__(self, rack, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit rack")
        self.resize(320, 180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(lbl("EDIT RACK", 9, True, "#606060", 2))
        form = QFormLayout()
        form.setSpacing(8)
        self.name_edit = QLineEdit(rack.name)

        self._size_val = rack.u_size
        size_w, self._size_lbl, size_up, size_dn = self._make_spin(rack.u_size)

        self._size_lbl._commit_fn = lambda: self._commit_spin("_size_val", self._size_lbl, 1, 60)
        size_up.clicked.connect(lambda: self._set("_size_val", self._size_lbl, self._size_val + 1, 1, 60))
        size_dn.clicked.connect(lambda: self._set("_size_val", self._size_lbl, self._size_val - 1, 1, 60))

        form.addRow(lbl("Name",     10, color="#808080"), self.name_edit)
        form.addRow(lbl("Size (U)", 10, color="#808080"), size_w)
        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel = ghost_push("Cancel")
        cancel.setAutoDefault(False)
        cancel.setDefault(False)
        cancel.clicked.connect(self.reject)
        ok = ghost_push("APPLY", amber=True)
        ok.setAutoDefault(False)
        ok.setDefault(False)
        ok.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addStretch()
        btns.addWidget(ok)
        layout.addLayout(btns)

        # Invio su qualsiasi field → commit + accept
        self.name_edit.returnPressed.connect(self.accept)
        self._size_lbl.returnPressed.connect(
            lambda: (self._commit_spin("_size_val", self._size_lbl, 1, 60), self.accept()))

    def _make_spin(self, initial=1):
        FIELD_H = 28
        BTN_W   = 20
        BTN_H   = FIELD_H // 2

        field_ss = f"""
            QLineEdit {{
                background:{BG3}; color:{TEXT_PRIMARY};
                border:1px solid {BG4};
                border-right:none;
                border-top-left-radius:3px;
                border-bottom-left-radius:3px;
                font-size:13px;
                padding:0 8px;
            }}
            QLineEdit:focus {{
                border:1px solid {ACCENT};
                border-right:none;
            }}
        """
        btn_ss = f"""
            QPushButton {{
                background:{BG4}; color:{TEXT_SECONDARY};
                border:1px solid {BG4}; border-left:none;
                font-size:7px; padding:0; margin:0;
            }}
            QPushButton:hover {{ background:#484848; color:{TEXT_PRIMARY}; }}
            QPushButton:pressed {{ background:{BG2}; }}
        """
        btn_top_ss    = btn_ss + " QPushButton { border-top-right-radius:3px; }"
        btn_bottom_ss = btn_ss + " QPushButton { border-bottom-right-radius:3px; }"

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        container.setFixedHeight(FIELD_H)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        value_edit = QLineEdit(str(initial))
        value_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        value_edit.setFixedHeight(FIELD_H)
        value_edit.setStyleSheet(field_ss)
        value_edit._commit_fn = None
        value_edit.editingFinished.connect(
            lambda: value_edit._commit_fn and value_edit._commit_fn())

        btn_col = QWidget()
        btn_col.setFixedSize(BTN_W, FIELD_H)
        btn_col.setStyleSheet("background:transparent;")
        btn_col_l = QVBoxLayout(btn_col)
        btn_col_l.setContentsMargins(0, 0, 0, 0)
        btn_col_l.setSpacing(0)

        up = QPushButton("▲")
        up.setFixedSize(BTN_W, BTN_H)
        up.setStyleSheet(btn_top_ss)
        up.setAutoDefault(False)
        up.setDefault(False)
        dn = QPushButton("▼")
        dn.setFixedSize(BTN_W, BTN_H)
        dn.setStyleSheet(btn_bottom_ss)
        dn.setAutoDefault(False)
        dn.setDefault(False)

        btn_col_l.addWidget(up)
        btn_col_l.addWidget(dn)
        row.addWidget(value_edit, 1)
        row.addWidget(btn_col)

        return container, value_edit, up, dn

    def _set(self, attr, field, value, min_val, max_val):
        value = max(min_val, min(max_val, value))
        setattr(self, attr, value)
        field.setText(str(value))

    def _commit_spin(self, attr, field, min_val, max_val):
        text = field.text().strip()
        try:
            v = int(text) if text else getattr(self, attr)
        except ValueError:
            v = getattr(self, attr)
        self._set(attr, field, v, min_val, max_val)

    class _Proxy:
        def __init__(self, dialog, attr):
            self._d = dialog; self._a = attr
        def value(self):
            return getattr(self._d, self._a)

    @property
    def size_spin(self): return self._Proxy(self, "_size_val")


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rack Designer — Stage Tools")
        self.resize(1400, 860)
        self._dirty = False
        self._build()
        self._build_status()
        self._update_title()
        self.menuBar().setVisible(False)

    def _build(self):
        self.navbar = NavBar()
        self.navbar.section_changed.connect(self._switch)
        self.navbar.save_btn.clicked.connect(self._save)

        self.proj_section = ProjectSection()
        self.proj_section.project_loaded.connect(self._on_project_loaded)
        self.proj_section.save_requested.connect(self._save)
        self.proj_section.set_dirty_check(self._dirty_check)

        self.designer = DesignerSection()
        self.designer.project_changed.connect(self._on_changed)

        self.export_section = ExportSection()

        self.library = LibrarySection()
        self.library.library_changed.connect(self.designer.reload_library)

        self.about = AboutSection()

        self.stack = QStackedWidget()
        self.stack.addWidget(self.proj_section)   # 0 PROJECT
        self.stack.addWidget(self.designer)        # 1 DESIGNER
        self.stack.addWidget(self.export_section)  # 2 EXPORT
        self.stack.addWidget(self.library)         # 3 LIBRARY
        self.stack.addWidget(self.about)           # 4 ABOUT

        container = QWidget()
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(self.navbar)
        cl.addWidget(self.stack)
        self.setCentralWidget(container)

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.proj_section._open)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.proj_section._new)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._undo)

    def _undo(self):
        """Delega l'undo al designer solo se è la sezione attiva."""
        if self.stack.currentWidget() is self.designer:
            self.designer.undo()

    def _build_status(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready  —  Rack Designer v0.1.18  ·  Stage Tools")

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        # Sync export section when switching to it
        if idx == 2:
            self.export_section.set_project(self.designer.project)
            self.export_section._rebuild_rack_checks()

    def _on_project_loaded(self, project):
        self.designer.set_project(project)
        self.export_section.set_project(project)
        self._dirty = False
        self._update_title()
        self._status.showMessage(f"Project: {project.name}")

    def _on_changed(self):
        self._dirty = True
        self._update_title()
        self._status.showMessage("Unsaved changes")

    def _update_title(self):
        proj = self.designer.project
        dot = "● " if self._dirty else ""
        self.setWindowTitle(f"{dot}{proj.name} — Rack Designer · Stage Tools")
        self.navbar.set_project(proj.name, self._dirty)

    def _dirty_check(self) -> bool:
        """Chiede se salvare prima di caricare un altro progetto.
        Restituisce True se si può procedere, False se l'utente ha scelto Cancel."""
        if not self._dirty:
            return True
        r = MsgBox.question3(self, "Unsaved changes",
                             f"'{self.designer.project.name}' has unsaved changes.\nSave before opening another project?")
        if r == "cancel":
            return False
        if r == "yes":
            self._save()
        return True

    def _save(self):
        # Applica sempre il form prima di salvare (Ctrl+S o navbar SAVE)
        self.proj_section._apply()
        project = self.designer.project
        try:
            filepath = storage.save_project(project, self.proj_section.get_filepath())
            self.proj_section.set_filepath(filepath)
            # Risincronizza il form se save_project ha modificato project.name (suffisso)
            self.proj_section.load_project(project, filepath)
            self.proj_section._refresh_recent()
            self._dirty = False
            self._update_title()
            self._status.showMessage(f"Saved: {filepath}")
        except Exception as e:
            MsgBox.error(self, "Error", str(e))

    def closeEvent(self, event):
        if self._dirty:
            r = MsgBox.question3(self, "Unsaved changes", "Save before closing?")
            if r == "cancel":
                event.ignore()
                return
            if r == "yes":
                self._save()
        event.accept()
