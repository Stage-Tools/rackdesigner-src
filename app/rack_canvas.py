import copy
from collections import deque

from PyQt6.QtWidgets import (
    QWidget, QMenu, QDialog, QTextEdit,
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QWheelEvent, QKeySequence, QPixmap
from app.models import Rack, RackSlot, DeviceDefinition
from app.style import ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BG3, BG4, FONT_BODY
from app.dialogs import MsgBox

# Layout constants (logical, pre-scale)
SLOT_H  = 30
LABEL_W = 40
BAY_W   = 460
BAY_SEP = 8

NAME_FONT_SIZE = 9
U_FONT_SIZE    = 7

UNDO_LIMIT = 10
ZOOM_MIN   = 0.4
ZOOM_MAX   = 2.5
ZOOM_STEP  = 0.1


class SlotNoteDialog(QDialog):
    def __init__(self, slot, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Slot notes")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Device: {slot.name}"))
        self.edit = QTextEdit(slot.notes)
        self.edit.setMinimumHeight(80)
        layout.addWidget(self.edit)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_notes(self):
        return self.edit.toPlainText()


class SlotEditDialog(QDialog):
    """Minimal edit dialog for custom/in-rack slots: name + U height."""
    def __init__(self, slot, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit slot")
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        if not slot.is_tray:
            self.name_edit = QLineEdit(slot.name)
            self.name_edit.setPlaceholderText("Slot name")
        else:
            # Trays don't have a single editable name -- each device inside
            # has its own. No name field is shown at all for a tray, rather
            # than one that silently discarded whatever was typed into it
            # while still acting as if a real change had been made
            # (task.md #54). Not inventing a new "tray label" field, per
            # the task's explicit scope.
            self.name_edit = None

        self._u_val = slot.u_height
        u_row = QWidget()
        u_row.setStyleSheet("background:transparent;")
        ur = QHBoxLayout(u_row)
        ur.setContentsMargins(0, 0, 0, 0)
        ur.setSpacing(4)
        self._u_lbl = QLineEdit(str(self._u_val))
        self._u_lbl.setFixedWidth(50)
        up = QPushButton("▲"); up.setFixedSize(22, 14)
        dn = QPushButton("▼"); dn.setFixedSize(22, 14)
        up.clicked.connect(self._u_up)
        dn.clicked.connect(self._u_dn)
        ur.addWidget(self._u_lbl)
        ur.addWidget(up)
        ur.addWidget(dn)
        ur.addStretch()

        if not slot.is_tray:
            form.addRow("Name:", self.name_edit)
            form.addRow("Height (U):", u_row)
        else:
            note = QLabel("This is a tray — each device inside has its own name.")
            note.setWordWrap(True)
            form.addRow(note)
        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _u_up(self):
        self._u_val = min(20, self._u_val + 1)
        self._u_lbl.setText(str(self._u_val))

    def _u_dn(self):
        self._u_val = max(1, self._u_val - 1)
        self._u_lbl.setText(str(self._u_val))

    def get_name(self) -> str:
        return self.name_edit.text().strip() if self.name_edit is not None else None

    def get_u(self) -> int:
        try:
            return max(1, min(20, int(self._u_lbl.text())))
        except ValueError:
            return self._u_val


class RackCanvas(QWidget):
    slot_removed  = pyqtSignal()
    slot_moved    = pyqtSignal()
    slot_selected = pyqtSignal(object)
    became_active = pyqtSignal(object)
    zoom_changed  = pyqtSignal(float)   # emette il nuovo scale factor

    # Clipboard condivisa tra tutte le istanze
    _clipboard = None

    def __init__(self, rack: Rack, parent=None):
        super().__init__(parent)
        self.rack = rack
        self._scale = 1.0

        self._drag_slot   = None
        self._drag_offset = 0
        self._drag_moved  = False
        self._hover_bay      = -1
        self._hover_u        = -1
        self._hover_u_height = 1
        self._selected_slot = None
        self._selected_u    = -1
        self._selected_bay  = -1

        self._undo_stack: deque = deque(maxlen=UNDO_LIMIT)

        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self._update_size()

    # ── Scale helpers ─────────────────────────────────────────────────────────

    def set_scale(self, factor: float):
        new_scale = max(ZOOM_MIN, min(ZOOM_MAX, factor))
        if abs(new_scale - self._scale) < 0.001:
            return   # nessuna variazione reale, evita loop
        self._scale = new_scale
        self._update_size()
        self.update()
        self.zoom_changed.emit(self._scale)

    def get_scale(self) -> float:
        return self._scale

    def _logical_w(self):
        return LABEL_W + self.rack.bays * BAY_W + (self.rack.bays - 1) * BAY_SEP

    def _logical_h(self):
        return self.rack.u_size * SLOT_H + 24

    def _canvas_width(self):
        return int(self._logical_w() * self._scale)

    def _canvas_height(self):
        return int(self._logical_h() * self._scale)

    def _update_size(self):
        self.setFixedWidth(self._canvas_width())
        self.setFixedHeight(self._canvas_height())

    # Convert widget pos → logical pos (unscaled)
    def _to_logical(self, pos: QPoint) -> QPoint:
        return QPoint(int(pos.x() / self._scale), int(pos.y() / self._scale))

    def _bay_left(self, bay):
        return LABEL_W + bay * (BAY_W + BAY_SEP)

    def _point_to_bay_u(self, pos):
        """Accepts widget-space pos, returns (bay, u) in logical coords."""
        lp = self._to_logical(pos)
        x, y = lp.x(), lp.y()
        rack_h = self.rack.u_size * SLOT_H
        if y < 0 or y >= rack_h:
            return -1, -1
        for bay in range(self.rack.bays):
            bx = self._bay_left(bay)
            if bx <= x < bx + BAY_W:
                u = int(y // SLOT_H) + 1
                return bay, u
        return -1, -1

    # ── Undo ──────────────────────────────────────────────────────────────────

    def _push_undo(self):
        snapshot = copy.deepcopy([s.to_dict() for s in self.rack.slots])
        self._undo_stack.append(snapshot)

    def undo(self):
        if not self._undo_stack:
            return
        snapshot = self._undo_stack.pop()
        self.rack.slots = [RackSlot.from_dict(d) for d in snapshot]
        if self._selected_slot is not None:
            ids = {s.id for s in self.rack.slots}
            if self._selected_slot.id not in ids:
                self._selected_slot = None
                self.slot_selected.emit(None)
        self.slot_moved.emit()
        self.update()

    # ── Focus / active tracking ───────────────────────────────────────────────

    def focusInEvent(self, event):
        self.became_active.emit(self)
        super().focusInEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        self.became_active.emit(self)
        if event.button() == Qt.MouseButton.LeftButton:
            slot, bay = self._slot_at(event.position().toPoint())
            if slot:
                lp = self._to_logical(event.position().toPoint())
                u_clicked = int(lp.y() // SLOT_H) + 1
                self._drag_slot    = slot
                self._drag_bay     = bay
                self._drag_offset  = u_clicked - slot.position_u
                self._drag_moved   = False
                self._selected_u   = slot.position_u
                self._selected_bay = bay
            else:
                click_bay, click_u = self._point_to_bay_u(event.position().toPoint())
                self._selected_slot = None
                self._selected_u    = click_u
                self._selected_bay  = click_bay
                self.slot_selected.emit(None)
                self.update()

    # ── Wheel zoom (Ctrl+Scroll) ──────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Propaga alla scroll area parent che gestisce lo zoom globale
            event.ignore()
        elif event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Propaga alla scroll area per lo scroll orizzontale
            event.ignore()
        else:
            # Scroll verticale: propaga al parent
            event.ignore()

    # ── Drag from library ─────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if (event.mimeData().hasText() or
                event.mimeData().hasFormat("application/x-rackslot")):
            self.setFocus()
            self.became_active.emit(self)
            # Calcola u_height dell'oggetto in drag una volta sola
            if event.mimeData().hasFormat("application/x-rackslot"):
                import json
                try:
                    raw       = event.mimeData().data("application/x-rackslot").data()
                    slot_data = json.loads(raw.decode("utf-8"))
                    snap      = slot_data.get("device_snapshot", {})
                    self._hover_u_height = snap.get("u_height", 1) if snap else 1
                except Exception:
                    self._hover_u_height = 1
            elif event.mimeData().hasText():
                dev_id    = event.mimeData().text()
                inspector = self._find_inspector()
                if inspector:
                    dev = next((d for d in inspector.library if d.id == dev_id), None)
                    self._hover_u_height = dev.u_height if dev else 1
                else:
                    self._hover_u_height = 1
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if (event.mimeData().hasText() or
                event.mimeData().hasFormat("application/x-rackslot")):
            bay, u = self._point_to_bay_u(event.position().toPoint())
            self._hover_bay = bay
            self._hover_u   = u
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._hover_bay      = -1
        self._hover_u        = -1
        self._hover_u_height = 1
        self.update()

    def dropEvent(self, event):
        self._hover_bay      = -1
        self._hover_u        = -1
        self._hover_u_height = 1

        # ── Cross-rack slot drop ──────────────────────────────────────────────
        if event.mimeData().hasFormat("application/x-rackslot"):
            import json, uuid as _uuid
            raw       = event.mimeData().data("application/x-rackslot").data()
            slot_data = json.loads(raw.decode("utf-8"))
            bay, target_u = self._point_to_bay_u(event.position().toPoint())
            if bay < 0:
                bay, target_u = 0, 1
            new_slot = RackSlot.from_dict(slot_data)
            new_slot.id = str(_uuid.uuid4())

            # Tray merge: a dropped non-rack-native single-device slot can
            # merge into an existing tray with room, the same way the
            # library-device-drop branch below already does — previously
            # this branch never attempted it and always fell through to the
            # occupied/free-space check, incorrectly rejecting the drop as
            # "no space" even when the target tray had room (task.md #51).
            if not new_slot.is_tray:
                snap = new_slot.device_snapshot
                if not snap.get("rack_native", True) and snap.get("width_mm") is not None:
                    dev_obj = DeviceDefinition.from_dict(snap)
                    existing = self.rack.slot_at(target_u, bay)
                    if existing is not None and self._can_add_to_tray(existing, dev_obj):
                        self._push_undo()
                        self._add_to_tray(existing, dev_obj)
                        self.slot_moved.emit()
                        self.update()
                        event.acceptProposedAction()
                        return

            # RackSlot.u_height branches correctly on is_tray (tray_u_height()) —
            # a top-level "u_height" in slot_data never exists, so falling back
            # to it (as before) always produced 1 for a tray source (task.md #47)
            u_height = new_slot.u_height
            if (not self.rack.is_slot_occupied(target_u, u_height, bay) and
                    target_u + u_height - 1 <= self.rack.u_size):
                pos = target_u
            else:
                pos = self._free_near(target_u, u_height, bay)
            if pos is None:
                MsgBox.warn(self, "No space", "Not enough free space in this rack.")
                event.ignore()
                return
            self._push_undo()
            new_slot.position_u = pos
            new_slot.bay        = bay
            self.rack.slots.append(new_slot)
            self._selected_slot = new_slot
            self._selected_u    = pos
            self._selected_bay  = bay
            self.slot_selected.emit(new_slot)
            self.slot_moved.emit()
            self.update()
            event.acceptProposedAction()
            return

        # ── Library device drop ───────────────────────────────────────────────
        if not event.mimeData().hasText():
            return
        dev_id = event.mimeData().text()
        inspector = self._find_inspector()
        if not inspector:
            return
        dev = next((d for d in inspector.library if d.id == dev_id), None)
        if not dev:
            return
        bay, target_u = self._point_to_bay_u(event.position().toPoint())
        if bay < 0:
            bay, target_u = 0, 1

        if not dev.rack_native and dev.width_mm is not None:
            existing = self.rack.slot_at(target_u, bay)
            if existing is not None and self._can_add_to_tray(existing, dev):
                self._push_undo()
                self._add_to_tray(existing, dev)
                self.slot_moved.emit()
                self.update()
                event.acceptProposedAction()
                return

        pos = self._free_near(target_u, dev.u_height, bay)
        if pos is None:
            MsgBox.warn(self, "No space", "Not enough free space in this bay.")
            self.update()
            event.ignore()
            return
        self._push_undo()
        self.rack.slots.append(RackSlot(
            device_id=dev.id,
            device_snapshot=dev.to_dict(),
            position_u=pos,
            bay=bay,
        ))
        self.slot_moved.emit()
        self.update()
        event.acceptProposedAction()

    # ── Tray helpers ──────────────────────────────────────────────────────────

    def _can_add_to_tray(self, slot: RackSlot, dev) -> bool:
        snap = slot.device_snapshot
        if slot.is_tray:
            return slot.tray_can_fit(dev.width_mm)
        if snap.get("rack_native", True):
            return False
        slot_w = snap.get("width_mm")
        if slot_w is None:
            return False
        return (slot_w + dev.width_mm) <= 482.0

    def _add_to_tray(self, slot: RackSlot, dev) -> None:
        if not slot.is_tray:
            slot.tray_devices = [dict(slot.device_snapshot)]
            slot.device_snapshot = {}
        slot.tray_devices.append(dev.to_dict())

    def _find_inspector(self):
        w = self.parent()
        while w:
            if hasattr(w, 'library'):
                return w
            w = w.parent()
        return None

    def _free_near(self, target_u, u_height, bay):
        for start in range(target_u, self.rack.u_size + 1):
            if start + u_height - 1 > self.rack.u_size:
                break
            if not self.rack.is_slot_occupied(start, u_height, bay):
                return start
        for start in range(target_u - 1, 0, -1):
            if start + u_height - 1 > self.rack.u_size:
                continue
            if not self.rack.is_slot_occupied(start, u_height, bay):
                return start
        return None

    # ── Internal drag to reorder ──────────────────────────────────────────────

    def mouseMoveEvent(self, event):
        if not (self._drag_slot and (event.buttons() & Qt.MouseButton.LeftButton)):
            return

        bay, u_raw = self._point_to_bay_u(event.position().toPoint())

        # Cursore ancora dentro questo canvas → reorder interno
        if bay >= 0:
            new_u = max(1, u_raw - self._drag_offset)
            new_u = min(new_u, self.rack.u_size - self._drag_slot.u_height + 1)
            others = [s for s in self.rack.slots
                      if s.id != self._drag_slot.id and s.bay == bay]
            collision = any(
                not (new_u + self._drag_slot.u_height <= s.position_u or
                     new_u >= s.position_u + s.u_height)
                for s in others
            )
            if not collision:
                if new_u != self._drag_slot.position_u or bay != self._drag_slot.bay:
                    if not self._drag_moved:
                        self._push_undo()
                    self._drag_moved = True
                self._drag_slot.position_u = new_u
                self._drag_slot.bay = bay
                self.update()
        else:
            # Cursore uscito → avvia QDrag cross-rack
            slot = self._drag_slot
            self._drag_slot  = None
            self._drag_moved = False

            import json
            from PyQt6.QtGui import QDrag
            from PyQt6.QtCore import QMimeData, QByteArray

            slot_data = json.dumps(slot.to_dict()).encode("utf-8")
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData("application/x-rackslot", QByteArray(slot_data))
            drag.setMimeData(mime)

            # Pixmap drag
            pm = QPixmap(max(160, len(slot.name) * 7), 24)
            pm.fill(QColor("#1a1200"))
            from PyQt6.QtGui import QPainter
            painter = QPainter(pm)
            painter.setPen(QPen(QColor("#E8A020"), 1))
            painter.drawRect(0, 0, pm.width()-1, 23)
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#E8A020"))
            painter.drawText(8, 0, pm.width()-16, 24,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             slot.name)
            painter.end()
            drag.setPixmap(pm)
            drag.setHotSpot(pm.rect().center())

            # Rimuove lo slot dal rack sorgente
            if slot in self.rack.slots:
                self._push_undo()
                self.rack.slots.remove(slot)
                self._selected_slot = None
                self._selected_u    = -1
                self._selected_bay  = -1
                self.slot_removed.emit()
                self.update()

            result = drag.exec(Qt.DropAction.MoveAction)
            # Se non accettato da nessun canvas, ripristina
            if result == Qt.DropAction.IgnoreAction:
                self.undo()
                self.slot_moved.emit()
                self.update()

    def mouseReleaseEvent(self, event):
        if self._drag_slot and event.button() == Qt.MouseButton.LeftButton:
            slot     = self._drag_slot
            moved    = self._drag_moved
            self._drag_slot  = None
            self._drag_moved = False
            if moved:
                self.slot_moved.emit()
            else:
                self._selected_slot = slot
                self._selected_u    = slot.position_u
                self._selected_bay  = slot.bay
                self.slot_selected.emit(slot)
            self.update()

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key  = event.key()
        mods = event.modifiers()
        ctrl = Qt.KeyboardModifier.ControlModifier

        if mods & ctrl and key == Qt.Key.Key_C:
            self._kb_copy()
        elif mods & ctrl and key == Qt.Key.Key_X:
            self._kb_cut()
        elif mods & ctrl and key == Qt.Key.Key_V:
            self._kb_paste()
        elif mods & ctrl and key == Qt.Key.Key_D:
            self._kb_duplicate()
        elif mods & ctrl and key == Qt.Key.Key_Z:
            self.undo()
        elif mods & ctrl and key == Qt.Key.Key_Equal:
            self._request_set_all_zoom(self._scale + ZOOM_STEP)
        elif mods & ctrl and key == Qt.Key.Key_Minus:
            self._request_set_all_zoom(self._scale - ZOOM_STEP)
        elif mods & ctrl and key == Qt.Key.Key_0:
            self._request_fit_all()
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._kb_delete()
        else:
            super().keyPressEvent(event)

    def _kb_copy(self):
        if self._selected_slot is None:
            return
        RackCanvas._clipboard = copy.deepcopy(self._selected_slot.to_dict())

    def _kb_cut(self):
        if self._selected_slot is None:
            return
        RackCanvas._clipboard = copy.deepcopy(self._selected_slot.to_dict())
        self._push_undo()
        self.rack.slots.remove(self._selected_slot)
        self._selected_slot = None
        self.slot_selected.emit(None)
        self.slot_removed.emit()
        self.update()

    def _kb_paste(self):
        if RackCanvas._clipboard is None:
            return
        import uuid
        data     = copy.deepcopy(RackCanvas._clipboard)
        new_slot = RackSlot.from_dict(data)
        # RackSlot.u_height branches correctly on is_tray (tray_u_height()) —
        # a top-level "u_height" in data never exists, so falling back to it
        # (as before) always produced 1 for a tray source (task.md #47)
        u_height = new_slot.u_height
        clip_id  = data.get("id", "")

        # Se _selected_slot è lo stesso oggetto nel clipboard (Ctrl+C senza
        # aver cambiato selezione), non usarlo come target — evita sovrapposizione
        selected_is_source = (
            self._selected_slot is not None and
            self._selected_slot.id == clip_id
        )

        if self._selected_slot is not None and not selected_is_source:
            # Slot selezionato diverso dalla sorgente → incolla dopo di esso
            bay      = self._selected_slot.bay
            target_u = self._selected_slot.position_u + self._selected_slot.u_height
        elif self._selected_u > 0 and self._selected_bay >= 0:
            # Cella vuota selezionata
            bay      = self._selected_bay
            target_u = self._selected_u
        else:
            bay      = 0
            target_u = 1

        # Usa target_u se libera e ci sta, altrimenti _free_near
        if (1 <= target_u <= self.rack.u_size and
                not self.rack.is_slot_occupied(target_u, u_height, bay) and
                target_u + u_height - 1 <= self.rack.u_size):
            pos = target_u
        else:
            pos = self._free_near(target_u, u_height, bay)
            if pos is None:
                for b in range(self.rack.bays):
                    pos = self._free_near(1, u_height, b)
                    if pos is not None:
                        bay = b
                        break
        if pos is None:
            MsgBox.warn(self, "No space", "Not enough free space in this rack.")
            return
        self._push_undo()
        new_slot.id         = str(uuid.uuid4())
        new_slot.position_u = pos
        new_slot.bay        = bay
        self.rack.slots.append(new_slot)
        self._selected_slot = new_slot
        self._selected_u    = pos
        self._selected_bay  = bay
        self.slot_selected.emit(new_slot)
        self.slot_moved.emit()
        self.update()

    def _kb_duplicate(self):
        if self._selected_slot is None:
            return
        source = self._selected_slot
        RackCanvas._clipboard = copy.deepcopy(source.to_dict())
        saved_u   = self._selected_u
        saved_bay = self._selected_bay
        # Punta subito dopo la sorgente, nel suo stesso bay: _kb_paste() la
        # userà come target (selected_is_source salta il ramo "incolla dopo
        # lo slot selezionato", ma questo elif lo copre) invece di ricadere
        # sempre sulla ricerca da bay=0 (task.md #49)
        self._selected_u   = source.position_u + source.u_height
        self._selected_bay = source.bay
        self._kb_paste()
        if self._selected_slot is None:
            self._selected_u   = saved_u
            self._selected_bay = saved_bay

    def _kb_delete(self):
        if self._selected_slot is None:
            return
        slot = self._selected_slot
        self.setEnabled(False)
        confirmed = MsgBox.question_danger(self, "Remove slot",
                                           f"Remove '{slot.name}' from rack?")
        self.setEnabled(True)
        self.setFocus()
        if not confirmed:
            return
        if slot not in self.rack.slots:
            return
        self._push_undo()
        self.rack.slots.remove(slot)
        self._selected_slot = None
        self._selected_u    = -1
        self._selected_bay  = -1
        self.slot_selected.emit(None)
        self.slot_removed.emit()
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)

        lw = self._logical_w()
        lh = self._logical_h()
        rack_h = self.rack.u_size * SLOT_H

        p.fillRect(0, 0, lw, lh, QColor("#1E1E1E"))

        for bay in range(self.rack.bays):
            bx = self._bay_left(bay)

            if bay > 0:
                p.fillRect(bx - BAY_SEP, 0, BAY_SEP, rack_h, QColor("#1E1E1E"))

            p.fillRect(bx, 0, BAY_W, rack_h, QColor("#222222"))

            p.setPen(QPen(QColor("#2a2a2a"), 1))
            for u in range(self.rack.u_size + 1):
                y = u * SLOT_H
                p.drawLine(bx, y, bx + BAY_W, y)

            if bay == 0:
                f = QFont("Consolas", U_FONT_SIZE)
                p.setFont(f)
                p.setPen(QColor("#484848"))
                for u in range(self.rack.u_size):
                    y = u * SLOT_H
                    p.drawText(0, y, LABEL_W - 6, SLOT_H,
                               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                               str(u + 1))

            if self._hover_bay == bay and self._hover_u > 0:
                # Clamp the preview's U range to [1, rack.u_size] so hovering
                # a multi-U drag payload near the bottom rows doesn't draw
                # the highlight extending past the rack frame (task.md #53).
                hover_top    = max(1, self._hover_u)
                hover_bottom = min(self.rack.u_size, self._hover_u + self._hover_u_height - 1)
                if hover_bottom >= hover_top:
                    hy = (hover_top - 1) * SLOT_H
                    hover_h = (hover_bottom - hover_top + 1) * SLOT_H
                    p.setPen(QPen(QColor(ACCENT), 2))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawRect(bx + 1, hy + 1, BAY_W - 2, hover_h - 2)

            # Evidenzia cella vuota selezionata
            if (self._selected_slot is None and
                    self._selected_bay == bay and
                    1 <= self._selected_u <= self.rack.u_size and
                    not self.rack.slot_at(self._selected_u, bay)):
                sy_sel = (self._selected_u - 1) * SLOT_H
                p.save()
                p.setPen(QPen(QColor(ACCENT), 1))
                p.setBrush(QBrush(QColor(40, 30, 5, 40)))
                p.drawRect(bx + 1, sy_sel + 1, BAY_W - 2, SLOT_H - 2)
                p.restore()

            for slot in sorted(
                [s for s in self.rack.slots if s.bay == bay],
                key=lambda s: s.position_u
            ):
                u0 = slot.position_u - 1
                sx = bx + 1
                sy = u0 * SLOT_H + 1
                sw = BAY_W - 2
                sh = slot.u_height * SLOT_H - 2

                is_selected = (
                    (self._selected_slot is not None and self._selected_slot.id == slot.id) or
                    (self._drag_slot is not None and self._drag_slot.id == slot.id)
                )

                if slot.is_tray:
                    p.fillRect(sx, sy, sw, sh, QColor("#222222"))
                    total_mm  = sum(d.get("width_mm") or 482.0 for d in slot.tray_devices)
                    px_per_mm = sw / max(total_mm, 482.0)
                    cur_x     = sx
                    for i, dev_snap in enumerate(slot.tray_devices):
                        dev_mm  = dev_snap.get("width_mm") or 482.0
                        dev_px  = int(dev_mm * px_per_mm)
                        if i == len(slot.tray_devices) - 1:
                            dev_px = sx + sw - cur_x
                        from app.models import category_color
                        color_hex = dev_snap.get("color") or category_color(dev_snap.get("category", "Other"))
                        dev_color = QColor(color_hex)
                        p.fillRect(cur_x + 1, sy + 1, dev_px - 2, sh - 2, QColor("#222222"))
                        p.fillRect(cur_x + 1, sy + 1, 3, sh - 2, dev_color)
                        if i > 0:
                            p.setPen(QPen(QColor("#0a0a0a"), 1))
                            p.drawLine(cur_x, sy, cur_x, sy + sh)
                        name_font = QFont("Segoe UI", NAME_FONT_SIZE)
                        name_font.setWeight(QFont.Weight.Medium)
                        p.setFont(name_font)
                        p.setPen(QColor("#d0c8b8"))
                        name_rect = QRect(cur_x + 6, sy, dev_px - 8, sh)
                        p.drawText(name_rect,
                                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                   dev_snap.get("name", "?"))
                        cur_x += dev_px

                    if is_selected:
                        p.setPen(QPen(QColor(ACCENT), 1))
                    else:
                        p.setPen(QPen(QColor("#303030"), 1))
                    p.drawRect(sx, sy, sw, sh)

                else:
                    p.fillRect(sx, sy, sw, sh, QColor("#222222"))
                    left_bar_color = QColor(ACCENT) if slot.notes else QColor("#363636")
                    p.fillRect(sx, sy, 4, sh, left_bar_color)
                    if is_selected:
                        p.setPen(QPen(QColor(ACCENT), 1))
                    else:
                        p.setPen(QPen(QColor("#303030"), 1))
                    p.drawRect(sx, sy, sw, sh)

                    name_font = QFont("Segoe UI", NAME_FONT_SIZE)
                    name_font.setWeight(QFont.Weight.Medium)
                    p.setFont(name_font)
                    p.setPen(QColor("#d0c8b8"))
                    pad_l     = 10
                    name_rect = QRect(sx + pad_l, sy, sw - pad_l - 40, sh)
                    p.drawText(name_rect,
                               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                               slot.name)

                    u_font = QFont("Consolas", U_FONT_SIZE)
                    p.setFont(u_font)
                    p.setPen(QColor("#505050"))
                    u_rect = QRect(sx + sw - 38, sy, 34, sh)
                    p.drawText(u_rect,
                               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                               f"{slot.u_height}U")

            p.setPen(QPen(QColor("#363636"), 1))
            p.drawRect(bx, 0, BAY_W, rack_h)

        # Stats bar
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor("#606060"))
        used   = self.rack.used_u()
        free   = self.rack.free_u()
        watts  = self.rack.total_watts()
        weight = self.rack.total_weight()
        bays_s = f" · {self.rack.bays} bays" if self.rack.bays > 1 else ""
        stats  = f"  {used}U used · {free}U free{bays_s}"
        if watts  > 0: stats += f" · {watts:.0f} W"
        if weight > 0: stats += f" · {weight:.1f} kg"
        p.drawText(0, rack_h + 4, lw, 18,
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, stats)

    # ── Hit test ──────────────────────────────────────────────────────────────

    def _slot_at(self, pos):
        bay, u = self._point_to_bay_u(pos)
        if bay < 0:
            return None, -1
        for slot in self.rack.slots:
            if slot.bay == bay and slot.position_u <= u < slot.position_u + slot.u_height:
                return slot, bay
        return None, -1

    # ── Context menu ──────────────────────────────────────────────────────────

    def _context_menu(self, pos):
        slot, bay = self._slot_at(pos)
        MENU_SS = """
            QMenu { background:#2e2e2e; color:#ede8dc; border:1px solid #444; }
            QMenu::item { padding:7px 20px; font-size:12px; }
            QMenu::item:selected { background:#363636; color:#e8a020; }
            QMenu::separator { height:1px; background:#444; }
        """
        menu = QMenu(self)
        menu.setStyleSheet(MENU_SS)

        if slot:
            self._selected_slot = slot
            self.slot_selected.emit(slot)
            self.update()

            note_act   = menu.addAction("Edit notes…")
            edit_act   = menu.addAction("Edit slot…")
            menu.addSeparator()
            copy_act   = menu.addAction("Copy\tCtrl+C")
            cut_act    = menu.addAction("Cut\tCtrl+X")
            dup_act    = menu.addAction("Duplicate\tCtrl+D")
            menu.addSeparator()
            up_act     = menu.addAction("Move up  ↑")
            down_act   = menu.addAction("Move down  ↓")
            menu.addSeparator()
            if slot.is_tray:
                tray_menu = menu.addMenu("Remove device from tray…")
                tray_menu.setStyleSheet(MENU_SS)
                tray_acts = []
                for i, dev_snap in enumerate(slot.tray_devices):
                    act = tray_menu.addAction(dev_snap.get("name", f"Device {i+1}"))
                    tray_acts.append((i, act))
            remove_act = menu.addAction("Remove from rack\tDel")
            menu.addSeparator()
            fit_rack_act = menu.addAction("Fit this rack to window")
            fit_all_act  = menu.addAction("Fit all racks to window")
            zoom_reset   = menu.addAction("Reset zoom  (100%)")

            action = menu.exec(self.mapToGlobal(pos))
            if action == remove_act:
                self._push_undo()
                self.rack.slots.remove(slot)
                self._selected_slot = None
                self.slot_selected.emit(None)
                self.slot_removed.emit()
                self.update()
            elif action == note_act:
                dlg = SlotNoteDialog(slot, self)
                if dlg.exec():
                    self._push_undo()
                    slot.notes = dlg.get_notes()
                    self.update()
            elif action == edit_act:
                self._edit_slot(slot)
            elif action == copy_act:
                self._kb_copy()
            elif action == cut_act:
                self._kb_cut()
            elif action == dup_act:
                self._kb_duplicate()
            elif action == up_act:
                self._move_step(slot, -1)
            elif action == down_act:
                self._move_step(slot, +1)
            elif action == fit_rack_act:
                self.fit_to_view()
            elif action == fit_all_act:
                self._request_fit_all()
            elif action == zoom_reset:
                self._request_set_all_zoom(1.0)
            elif slot.is_tray:
                for i, act in tray_acts:
                    if action == act:
                        self._push_undo()
                        slot.tray_devices.pop(i)
                        if len(slot.tray_devices) == 1:
                            slot.device_snapshot = slot.tray_devices[0]
                            slot.tray_devices = []
                        elif len(slot.tray_devices) == 0:
                            self.rack.slots.remove(slot)
                            self._selected_slot = None
                            self.slot_selected.emit(None)
                            self.slot_removed.emit()
                        self.slot_moved.emit()
                        self.update()
                        break
        else:
            b, u = self._point_to_bay_u(pos)
            # Fit actions always available
            fit_rack_act = menu.addAction("Fit this rack to window")
            fit_all_act  = menu.addAction("Fit all racks to window")
            zoom_reset   = menu.addAction("Reset zoom  (100%)")

            if b >= 0 and 1 <= u <= self.rack.u_size:
                menu.addSeparator()
                blank_act = menu.addAction(
                    f"Insert blank panel at U{u}" +
                    (f" (Bay {b+1})" if self.rack.bays > 1 else ""))
                paste_act = None
                if RackCanvas._clipboard is not None:
                    paste_act = menu.addAction("Paste here\tCtrl+V")
            else:
                blank_act = None
                paste_act = None

            action = menu.exec(self.mapToGlobal(pos))

            if action == fit_rack_act:
                self.fit_to_view()
            elif action == fit_all_act:
                self._request_fit_all()
            elif action == zoom_reset:
                self._request_set_all_zoom(1.0)
            elif blank_act and action == blank_act:
                self._insert_blank(u, b)
            elif paste_act and action == paste_act:
                # Forza il target sulla cella cliccata col tasto destro,
                # invece di lasciare che _kb_paste() usi una selezione
                # precedente/stale (task.md #48)
                self._selected_slot = None
                self._selected_u    = u
                self._selected_bay  = b
                self._kb_paste()

    # ── Slot editing ──────────────────────────────────────────────────────────

    def _edit_slot(self, slot: RackSlot):
        dlg = SlotEditDialog(slot, self)
        if not dlg.exec():
            return
        if slot.is_tray:
            # Nothing in the dialog is editable for a tray (no name field,
            # no U-height field) -- nothing could have changed, so don't
            # push an undo entry or emit slot_moved as if something did
            # (task.md #54).
            return
        new_name = dlg.get_name()
        new_u    = dlg.get_u()
        if not new_name:
            return
        self._push_undo()
        # Check if new U height fits without collision
        if new_u != slot.u_height:
            end_u = slot.position_u + new_u - 1
            if end_u > self.rack.u_size:
                MsgBox.warn(self, "No space",
                            f"U height {new_u} exceeds rack size at position {slot.position_u}.")
                return
            others = [s for s in self.rack.slots if s.id != slot.id and s.bay == slot.bay]
            for test_u in range(slot.position_u, slot.position_u + new_u):
                for s in others:
                    if s.position_u <= test_u < s.position_u + s.u_height:
                        MsgBox.warn(self, "No space",
                                    f"U height {new_u} would overlap '{s.name}'.")
                        return
            slot.device_snapshot["u_height"] = new_u
        slot.device_snapshot["name"] = new_name
        self.slot_moved.emit()
        self.update()

    # ── Fit helpers ───────────────────────────────────────────────────────────

    def fit_to_view(self):
        """Scale this canvas so the full rack fits the parent scroll area viewport."""
        scroll = self._find_scroll_area()
        if scroll is None:
            return
        vp = scroll.viewport()
        vw = vp.width()  - 60   # padding
        vh = vp.height() - 60
        scale_w = vw / self._logical_w()
        scale_h = vh / self._logical_h()
        self.set_scale(min(scale_w, scale_h))

    def _request_fit_all(self):
        """Ask the parent DesignerSection to fit all canvases."""
        w = self.parent()
        while w:
            if hasattr(w, 'fit_all_racks'):
                w.fit_all_racks()
                return
            w = w.parent()

    def _request_set_all_zoom(self, scale: float):
        """Ask the parent DesignerSection to set zoom on all canvases."""
        w = self.parent()
        while w:
            if hasattr(w, '_set_all_zoom'):
                w._set_all_zoom(scale)
                return
            w = w.parent()
        # fallback: agisce solo su se stesso
        self.set_scale(scale)

    def _find_scroll_area(self):
        from PyQt6.QtWidgets import QScrollArea
        w = self.parent()
        while w:
            if isinstance(w, QScrollArea):
                return w
            w = w.parent()
        return None

    # ── Move step ─────────────────────────────────────────────────────────────

    def _move_step(self, slot, direction):
        new_pos = slot.position_u + direction
        if new_pos < 1 or new_pos + slot.u_height - 1 > self.rack.u_size:
            return
        others = [s for s in self.rack.slots
                  if s.id != slot.id and s.bay == slot.bay]
        for u in range(new_pos, new_pos + slot.u_height):
            for s in others:
                if s.position_u <= u < s.position_u + s.u_height:
                    return
        self._push_undo()
        slot.position_u = new_pos
        self.slot_moved.emit()
        self.update()

    # ── Blank panel ───────────────────────────────────────────────────────────

    def _insert_blank(self, u, bay=0):
        import uuid
        snapshot = {
            "id": str(uuid.uuid4()), "name": "Blank Panel", "category": "Other",
            "u_height": 1, "color": "#1e1e1e", "manufacturer": "", "model": "",
            "watts": None, "weight_kg": None, "depth_mm": None, "notes": "",
            "image_front": "", "image_rear": "",
        }
        if not self.rack.is_slot_occupied(u, 1, bay):
            self._push_undo()
            self.rack.slots.append(RackSlot(device_snapshot=snapshot, position_u=u, bay=bay))
            self.slot_moved.emit()
            self.update()

    # ── Add device (called from sidebar double-click or custom slot) ──────────

    def add_device(self, device: DeviceDefinition, bay: int = 0,
                   at_u: int = None) -> bool:
        """
        Add device to rack.
        - at_u: if given, try exactly that position; fail if occupied.
        - otherwise: find first free slot near U1.
        """
        if at_u is not None:
            if self.rack.is_slot_occupied(at_u, device.u_height, bay):
                return False
            if at_u + device.u_height - 1 > self.rack.u_size:
                return False
            self._push_undo()
            self.rack.slots.append(RackSlot(
                device_id=device.id,
                device_snapshot=device.to_dict(),
                position_u=at_u,
                bay=bay,
            ))
            self.update()
            return True

        for b in [bay] + [i for i in range(self.rack.bays) if i != bay]:
            pos = self._free_near(1, device.u_height, b)
            if pos is not None:
                self._push_undo()
                self.rack.slots.append(RackSlot(
                    device_id=device.id,
                    device_snapshot=device.to_dict(),
                    position_u=pos,
                    bay=b,
                ))
                self.update()
                return True
        return False
