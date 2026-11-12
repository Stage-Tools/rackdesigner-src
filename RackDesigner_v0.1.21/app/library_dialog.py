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

import base64
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QFormLayout, QLineEdit,
    QComboBox, QTextEdit, QLabel, QWidget,
    QFrame, QFileDialog, QScrollArea, QInputDialog, QMessageBox,
    QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPixmap
from app.models import (
    DeviceDefinition, DEFAULT_CATEGORIES, category_color,
    IMAGE_WIDTH_PX, IMAGE_U_HEIGHT_PX,
)
from app import storage
from app.style import BG2, BG3, BG4, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, DANGER, FONT_BODY


class ColorButton(QPushButton):
    color_changed = pyqtSignal(str)

    def __init__(self, color="", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(32, 24)
        self.clicked.connect(self._pick)
        self._update_style()

    def _pick(self):
        from PyQt6.QtWidgets import QColorDialog
        initial = QColor(self._color) if self._color else QColor("#2563EB")
        c = QColorDialog.getColor(initial, self)
        if c.isValid():
            self._color = c.name()
            self._update_style()
            self.color_changed.emit(self._color)

    def _update_style(self):
        if self._color:
            self.setStyleSheet(f"background:{self._color}; border:1px solid #555; font-size:0px;")
        else:
            self.setStyleSheet(f"background:{BG4}; border:1px solid #555; color:{TEXT_MUTED}; font-size:9px;")
            self.setText("auto")

    def set_color(self, c):
        self._color = c
        self._update_style()

    def get_color(self):
        return self._color

    def clear_color(self):
        self._color = ""
        self._update_style()


class ImagePickerWidget(QWidget):
    def __init__(self, label="Front", u_height=1, parent=None):
        super().__init__(parent)
        self._b64 = ""
        self._u = u_height
        self._label = label
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(5)

        header = QHBoxLayout()
        lbl = QLabel(self._label.upper())
        lbl.setStyleSheet(f"color:#707070; font-size:9px; font-weight:700; letter-spacing:1px;")
        header.addWidget(lbl)
        header.addStretch()
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedSize(40, 18)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{TEXT_MUTED}; border:1px solid {BG4};
                border-radius:2px; font-size:9px; padding:0; }}
            QPushButton:hover {{ color:{DANGER}; border-color:{DANGER}; }}
        """)
        self.clear_btn.clicked.connect(self._clear)
        header.addWidget(self.clear_btn)
        layout.addLayout(header)

        self.preview = QLabel("No image")
        self.preview.setFixedHeight(44)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet(
            f"background:{BG3}; border:1px dashed {BG4}; color:{TEXT_MUTED}; font-size:9px;")
        layout.addWidget(self.preview)

        self.size_hint = QLabel()
        self.size_hint.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px;")
        self._update_hint()
        layout.addWidget(self.size_hint)

        load_btn = QPushButton(f"Load {self._label} image…")
        load_btn.setStyleSheet(f"""
            QPushButton {{ background:{BG3}; color:{TEXT_SECONDARY}; border:1px solid {BG4};
                border-radius:3px; font-size:10px; padding:5px 10px; }}
            QPushButton:hover {{ color:{TEXT_PRIMARY}; border-color:{ACCENT}; }}
        """)
        load_btn.clicked.connect(self._load)
        layout.addWidget(load_btn)

    def _update_hint(self):
        self.size_hint.setText(
            f"Recommended: {IMAGE_WIDTH_PX} × {self._u * IMAGE_U_HEIGHT_PX} px  "
            f"({self._u}U × {IMAGE_U_HEIGHT_PX}px/U)")

    def update_u_height(self, u):
        self._u = u
        self._update_hint()

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Load {self._label} image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        with open(path, "rb") as f:
            data = f.read()
        self._b64 = base64.b64encode(data).decode("utf-8")
        self._show(data)

    def _show(self, data: bytes):
        pm = QPixmap()
        pm.loadFromData(data)
        self.preview.setPixmap(pm.scaledToHeight(42, Qt.TransformationMode.SmoothTransformation))
        self.preview.setStyleSheet(f"background:{BG3}; border:1px solid {BG4};")

    def _clear(self):
        self._b64 = ""
        self.preview.setPixmap(QPixmap())
        self.preview.setText("No image")
        self.preview.setStyleSheet(
            f"background:{BG3}; border:1px dashed {BG4}; color:{TEXT_MUTED}; font-size:9px;")

    def get_b64(self): return self._b64

    def set_b64(self, b64):
        self._b64 = b64
        if b64:
            try:
                self._show(base64.b64decode(b64))
            except Exception:
                self._clear()
        else:
            self._clear()


class CategoryCombo(QComboBox):
    """Combo that includes default + custom categories with an 'Add category…' option."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self.reload()
        self.currentTextChanged.connect(self._on_changed)

    def reload(self):
        self._loading = True
        current = self.currentText()
        self.clear()
        from app.models import get_categories
        cats = get_categories()
        self.addItems(cats)
        self.addItem("＋ Add category…")
        idx = self.findText(current)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(0)
        self._loading = False

    def _on_changed(self, text):
        if self._loading:
            return
        if text == "＋ Add category…":
            name, ok = QInputDialog.getText(self, "New category", "Category name:")
            if ok and name.strip():
                name = name.strip()
                storage.add_custom_category(name)
                self.reload()
                idx = self.findText(name)
                if idx >= 0:
                    self.setCurrentIndex(idx)
            else:
                self.setCurrentIndex(0)

    def current_category(self) -> str:
        t = self.currentText()
        if t == "＋ Add category…":
            return "Other"
        return t


class DeviceForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        _outer = QVBoxLayout(self)
        _outer.setContentsMargins(0, 0, 0, 0)
        _outer.setSpacing(0)
        _form_container = QWidget()
        _form_container.setStyleSheet("background:transparent;")
        layout = QFormLayout(_form_container)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(12)
        _outer.addWidget(_form_container)
        _outer.addStretch()

        self.name_edit = QLineEdit()
        self.manufacturer_edit = QLineEdit()
        self.model_edit = QLineEdit()

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Short description of the device…")

        self.category_combo = CategoryCombo()

        # ── U height spinner — editabile a mano ───────────────────────────────
        self._u_height_val = 1
        FIELD_H = 24
        BTN_W   = 18

        u_spin_w = QWidget()
        u_spin_w.setFixedHeight(FIELD_H)
        u_spin_w.setFixedWidth(80)
        u_spin_w.setStyleSheet("background:transparent;")
        u_spin_layout = QHBoxLayout(u_spin_w)
        u_spin_layout.setContentsMargins(0, 0, 0, 0)
        u_spin_layout.setSpacing(0)

        self._u_height_lbl = QLineEdit("1")
        self._u_height_lbl.setFixedHeight(FIELD_H)
        self._u_height_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._u_height_lbl.setStyleSheet(f"""
            QLineEdit {{
                background:{BG3}; color:{TEXT_PRIMARY};
                border:1px solid {BG4}; border-right:none;
                border-top-left-radius:3px; border-bottom-left-radius:3px;
                font-size:12px; padding:0 8px;
            }}
            QLineEdit:focus {{ border:1px solid {ACCENT}; border-right:none; }}
        """)

        def _u_commit():
            text = self._u_height_lbl.text().strip()
            try:
                v = int(text) if text else 1
                self._u_height_val = max(1, min(20, v))
            except ValueError:
                self._u_height_val = max(1, min(20, self._u_height_val))
            self._u_height_lbl.setText(str(self._u_height_val))
            self.img_front.update_u_height(self._u_height_val)
            self.img_rear.update_u_height(self._u_height_val)

        self._u_height_lbl.editingFinished.connect(_u_commit)

        u_btn_col = QWidget()
        u_btn_col.setFixedSize(BTN_W, FIELD_H)
        u_btn_col.setStyleSheet("background:transparent;")
        u_btn_col_l = QVBoxLayout(u_btn_col)
        u_btn_col_l.setContentsMargins(0, 0, 0, 0)
        u_btn_col_l.setSpacing(0)

        _ubtn_style = f"""
            QPushButton {{
                background:{BG4}; color:{TEXT_SECONDARY};
                border:1px solid {BG4}; border-left:none;
                font-size:7px; padding:0; margin:0;
            }}
            QPushButton:hover {{ background:#444; color:{TEXT_PRIMARY}; }}
        """
        u_up = QPushButton("▲"); u_up.setFixedSize(BTN_W, FIELD_H//2)
        u_up.setStyleSheet(_ubtn_style + f"QPushButton {{ border-top-right-radius:3px; }}")
        u_dn = QPushButton("▼"); u_dn.setFixedSize(BTN_W, FIELD_H//2)
        u_dn.setStyleSheet(_ubtn_style + f"QPushButton {{ border-bottom-right-radius:3px; }}")

        def _u_up():
            self._u_height_val = min(20, self._u_height_val + 1)
            self._u_height_lbl.setText(str(self._u_height_val))
            self.img_front.update_u_height(self._u_height_val)
            self.img_rear.update_u_height(self._u_height_val)

        def _u_dn():
            self._u_height_val = max(1, self._u_height_val - 1)
            self._u_height_lbl.setText(str(self._u_height_val))
            self.img_front.update_u_height(self._u_height_val)
            self.img_rear.update_u_height(self._u_height_val)

        u_up.clicked.connect(_u_up)
        u_dn.clicked.connect(_u_dn)
        u_btn_col_l.addWidget(u_up)
        u_btn_col_l.addWidget(u_dn)
        u_spin_layout.addWidget(self._u_height_lbl)
        u_spin_layout.addWidget(u_btn_col)

        # ── rack_native checkbox ───────────────────────────────────────────────
        self.rack_native_chk = QCheckBox("Rack-native (standard 19\")")
        self.rack_native_chk.setChecked(True)
        self.rack_native_chk.setStyleSheet(f"""
            QCheckBox {{ color:{TEXT_SECONDARY}; font-size:11px; spacing:8px; background:transparent; }}
            QCheckBox::indicator {{ width:14px; height:14px;
                background:#2e2e2e; border:1px solid #505050; }}
            QCheckBox::indicator:checked {{ background:{ACCENT}; border:1px solid {ACCENT}; }}
        """)
        self.rack_native_chk.stateChanged.connect(self._on_rack_native_changed)

        # ── Spinner helper ────────────────────────────────────────────────────
        def _make_spin_widget(default_val, decimals=1, max_val=99999):
            """Campo numerico editabile con frecce laterali. Nessun validator inline
            per evitare blocco input: la normalizzazione avviene su editingFinished."""
            FIELD_H = 24
            BTN_W   = 18

            container = QWidget()
            container.setFixedHeight(FIELD_H)
            container.setStyleSheet("background:transparent;")
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)

            val_holder = [float(default_val)]

            edit = QLineEdit()
            edit.setFixedHeight(FIELD_H)
            edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            edit.setStyleSheet(f"""
                QLineEdit {{
                    background:{BG3}; color:{TEXT_PRIMARY};
                    border:1px solid {BG4}; border-right:none;
                    border-top-left-radius:3px; border-bottom-left-radius:3px;
                    font-size:12px; padding:0 8px; min-width:70px;
                }}
                QLineEdit:focus {{ border:1px solid {ACCENT}; border-right:none; }}
            """)

            def _val_to_text(v):
                if v <= 0:
                    return ""
                if decimals == 0:
                    return str(int(round(v)))
                return f"{v:.{decimals}f}"

            edit.setText(_val_to_text(float(default_val)))

            def _commit():
                text = edit.text().strip().replace(",", ".")
                try:
                    v = float(text) if text else 0.0
                    v = max(0.0, min(float(max_val), v))
                except ValueError:
                    v = val_holder[0]
                val_holder[0] = round(v, decimals)
                edit.setText(_val_to_text(val_holder[0]))

            edit.editingFinished.connect(_commit)

            btn_col = QWidget()
            btn_col.setFixedSize(BTN_W, FIELD_H)
            btn_col.setStyleSheet("background:transparent;")
            btn_col_l = QVBoxLayout(btn_col)
            btn_col_l.setContentsMargins(0, 0, 0, 0)
            btn_col_l.setSpacing(0)

            _bs = f"""
                QPushButton {{
                    background:{BG4}; color:{TEXT_SECONDARY};
                    border:1px solid {BG4}; border-left:none;
                    font-size:7px; padding:0; margin:0;
                }}
                QPushButton:hover {{ background:#484848; color:{TEXT_PRIMARY}; }}
                QPushButton:pressed {{ background:{BG2}; }}
            """
            up = QPushButton("▲"); up.setFixedSize(BTN_W, FIELD_H//2)
            up.setStyleSheet(_bs + f"QPushButton {{ border-top-right-radius:3px; }}")
            dn = QPushButton("▼"); dn.setFixedSize(BTN_W, FIELD_H//2)
            dn.setStyleSheet(_bs + f"QPushButton {{ border-bottom-right-radius:3px; }}")

            step = 1.0 if decimals == 0 else 10 ** (-decimals)

            def _up():
                val_holder[0] = min(float(max_val), round(val_holder[0] + step, decimals))
                edit.setText(_val_to_text(val_holder[0]))

            def _dn():
                val_holder[0] = max(0.0, round(val_holder[0] - step, decimals))
                edit.setText(_val_to_text(val_holder[0]))

            up.clicked.connect(_up)
            dn.clicked.connect(_dn)
            btn_col_l.addWidget(up)
            btn_col_l.addWidget(dn)
            row.addWidget(edit, 1)
            row.addWidget(btn_col)

            def _get_value():
                text = edit.text().replace(",", ".")
                try:
                    return float(text) if text else 0.0
                except ValueError:
                    return val_holder[0]

            def _set_value(v):
                # Same clamp _commit() applies to manually-typed/arrow-stepped
                # values — without it, DeviceForm.load() populating this field
                # via .setValue() let an out-of-range stored value (e.g. from
                # unclamped CSV import, or old data) round-trip untouched
                # through load()+collect() indefinitely (task.md #31).
                v = float(v) if v else 0.0
                v = max(0.0, min(float(max_val), v))
                val_holder[0] = round(v, decimals)
                edit.setText(_val_to_text(val_holder[0]))

            container.value = _get_value
            container.setValue = _set_value

            return container

        # ── Physical dimensions — W × H × D ───────────────────────────────────
        self._dims_widget = QWidget()
        self._dims_widget.setStyleSheet("background:transparent;")
        self._dims_widget.setFixedHeight(26)
        dims_row = QHBoxLayout(self._dims_widget)
        dims_row.setContentsMargins(0, 0, 0, 0)
        dims_row.setSpacing(6)

        _dim_lbl_style = "color:#606060; font-size:9px;"

        self.width_mm_spin  = _make_spin_widget(0, decimals=1, max_val=482)
        self.height_mm_spin = _make_spin_widget(0, decimals=1, max_val=600)
        self.depth_mm_spin  = _make_spin_widget(0, decimals=1, max_val=1200)
        self.width_mm_spin.setFixedWidth(110)
        self.height_mm_spin.setFixedWidth(110)
        self.depth_mm_spin.setFixedWidth(110)

        for abbr, spin in [("W", self.width_mm_spin),
                            ("H", self.height_mm_spin),
                            ("D", self.depth_mm_spin)]:
            lbl_abbr = QLabel(abbr)
            lbl_abbr.setStyleSheet(_dim_lbl_style)
            dims_row.addWidget(lbl_abbr)
            dims_row.addWidget(spin)
        dims_row.addStretch()

        # ── Color ─────────────────────────────────────────────────────────────
        color_row = QHBoxLayout()
        self.color_btn = ColorButton()
        clear_col = QPushButton("Use category color")
        clear_col.setStyleSheet(
            f"background:{BG3}; color:{TEXT_MUTED}; border:1px solid {BG4}; border-radius:3px; font-size:10px; padding:4px 8px;")
        clear_col.clicked.connect(self.color_btn.clear_color)
        color_row.addWidget(self.color_btn)
        color_row.addWidget(clear_col)
        color_row.addStretch()

        # ── Power / weight (spinner manuali) ──────────────────────────────────
        self.watts_spin  = _make_spin_widget(0, decimals=0, max_val=99999)
        self.weight_spin = _make_spin_widget(0, decimals=2, max_val=9999)
        self.watts_spin.setFixedWidth(160)
        self.weight_spin.setFixedWidth(160)

        _watts_row = QWidget(); _watts_row.setStyleSheet("background:transparent;")
        _watts_rl = QHBoxLayout(_watts_row); _watts_rl.setContentsMargins(0,0,0,0); _watts_rl.setSpacing(0)
        _watts_rl.addWidget(self.watts_spin); _watts_rl.addStretch()

        _weight_row = QWidget(); _weight_row.setStyleSheet("background:transparent;")
        _weight_rl = QHBoxLayout(_weight_row); _weight_rl.setContentsMargins(0,0,0,0); _weight_rl.setSpacing(0)
        _weight_rl.addWidget(self.weight_spin); _weight_rl.addStretch()

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)

        self.img_front = ImagePickerWidget(label="Front", u_height=self._u_height_val)
        self.img_rear  = ImagePickerWidget(label="Rear",  u_height=self._u_height_val)
        images_row = QWidget()
        images_row.setStyleSheet("background:transparent;")
        images_layout = QHBoxLayout(images_row)
        images_layout.setContentsMargins(0, 0, 0, 0)
        images_layout.setSpacing(16)
        images_layout.addWidget(self.img_front)
        images_layout.addWidget(self.img_rear)

        def sep():
            f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
            f.setStyleSheet(f"color:{BG4};"); return f

        # ── Form rows ─────────────────────────────────────────────────────────
        layout.addRow("Name",           self.name_edit)
        layout.addRow("Manufacturer",   self.manufacturer_edit)
        layout.addRow("Model",          self.model_edit)
        layout.addRow("Description",    self.description_edit)
        layout.addRow("Category",       self.category_combo)
        layout.addRow(sep())
        layout.addRow("Mounting",       self.rack_native_chk)
        layout.addRow("Height (U)",     u_spin_w)
        layout.addRow("Dimensions",     self._dims_widget)
        layout.addRow("Color",          color_row)
        layout.addRow(sep())
        layout.addRow("Power (W)",      _watts_row)
        layout.addRow("Weight (kg)",    _weight_row)
        layout.addRow("Images",         images_row)
        layout.addRow("Notes",          self.notes_edit)

        # Initial state
        self._on_rack_native_changed()

    # ── Visibility / state helpers ────────────────────────────────────────────

    def _on_rack_native_changed(self):
        native = self.rack_native_chk.isChecked()
        self.height_mm_spin.setEnabled(not native)
        if native:
            # Disabling the field alone leaves its stale typed value sitting
            # in val_holder — collect() reads .value() regardless of enabled
            # state, so a height typed while non-rack-native survived
            # untouched through a rack_native re-check + save (task.md #29).
            self.height_mm_spin.setValue(0)

    def _on_u_changed(self, u):
        pass

    # ── Load / collect ────────────────────────────────────────────────────────

    def load(self, device: DeviceDefinition):
        self.name_edit.setText(device.name)
        self.manufacturer_edit.setText(device.manufacturer)
        self.model_edit.setText(device.model)
        self.description_edit.setPlainText(getattr(device, 'description', ''))
        self.category_combo.reload()
        idx = self.category_combo.findText(device.category)
        if idx < 0 and device.category:
            # Unrecognized category (e.g. from a JSON import predating this
            # device's category, or a custom category since deleted) — register
            # it instead of silently falling back to whatever the combo
            # defaults to (task.md #30), so the real value is shown and a
            # no-op save doesn't overwrite it.
            storage.register_category_if_unknown(device.category)
            self.category_combo.reload()
            idx = self.category_combo.findText(device.category)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        self.color_btn.set_color(device.color)
        self.watts_spin.setValue(device.watts if device.watts is not None else 0)
        self.weight_spin.setValue(device.weight_kg if device.weight_kg is not None else 0)
        self.notes_edit.setPlainText(device.notes)

        # Same [1,20] clamp _u_commit()/_u_up()/_u_dn() already enforce on
        # manual edits — without it, an out-of-range stored u_height (e.g.
        # from unclamped CSV import) round-tripped through load()+collect()
        # untouched (task.md #31).
        self._u_height_val = max(1, min(20, device.u_height))
        self._u_height_lbl.setText(str(self._u_height_val))

        self.rack_native_chk.setChecked(device.rack_native)
        self.width_mm_spin.setValue(device.width_mm if device.width_mm is not None else 0)
        self.height_mm_spin.setValue(device.height_mm if device.height_mm is not None else 0)
        self.depth_mm_spin.setValue(device.depth_mm if device.depth_mm is not None else 0)
        self._on_rack_native_changed()

        self.img_front.update_u_height(self._u_height_val)
        self.img_rear.update_u_height(self._u_height_val)
        self.img_front.set_b64(device.image_front)
        self.img_rear.set_b64(device.image_rear)

    def collect(self) -> dict:
        return {
            "name":         self.name_edit.text().strip(),
            "manufacturer": self.manufacturer_edit.text().strip(),
            "model":        self.model_edit.text().strip(),
            "description":  self.description_edit.toPlainText().strip(),
            "category":     self.category_combo.current_category(),
            "u_height":     self._u_height_val,
            "color":        self.color_btn.get_color(),
            "rack_native":  self.rack_native_chk.isChecked(),
            "width_mm":     self.width_mm_spin.value()  if self.width_mm_spin.value()  > 0 else None,
            "height_mm":    self.height_mm_spin.value() if self.height_mm_spin.value() > 0 else None,
            "depth_mm":     self.depth_mm_spin.value()  if self.depth_mm_spin.value()  > 0 else None,
            "watts":        self.watts_spin.value()      if self.watts_spin.value()      > 0 else None,
            "weight_kg":    self.weight_spin.value()     if self.weight_spin.value()     > 0 else None,
            "notes":        self.notes_edit.toPlainText().strip(),
            "image_front":  self.img_front.get_b64(),
            "image_rear":   self.img_rear.get_b64(),
        }
