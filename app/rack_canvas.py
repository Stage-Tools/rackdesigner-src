from PyQt6.QtWidgets import (
    QWidget, QMenu, QDialog, QTextEdit,
    QDialogButtonBox, QVBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from app.models import Rack, RackSlot, DeviceDefinition
from app.style import ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED
from app.dialogs import MsgBox

# Layout constants
SLOT_H  = 30    # pixels per U
LABEL_W = 40    # width of U-number column
BAY_W   = 460   # width of each bay
BAY_SEP = 8     # separator between bays

# Typography rendering constants
NAME_FONT_SIZE = 9
CAT_FONT_SIZE  = 7
U_FONT_SIZE    = 7


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


class RackCanvas(QWidget):
    slot_removed = pyqtSignal()
    slot_moved   = pyqtSignal()
    slot_selected = pyqtSignal(object)   # emits RackSlot or None

    def __init__(self, rack: Rack, parent=None):
        super().__init__(parent)
        self.rack = rack
        self._drag_slot   = None
        self._drag_offset = 0
        self._hover_bay   = -1
        self._selected_slot = None
        self._hover_u     = -1
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self._update_size()

    def _canvas_width(self):
        return LABEL_W + self.rack.bays * BAY_W + (self.rack.bays - 1) * BAY_SEP

    def _canvas_height(self):
        return self.rack.u_size * SLOT_H + 24  # +24 for stats bar

    def _update_size(self):
        self.setFixedWidth(self._canvas_width())
        self.setFixedHeight(self._canvas_height())

    def _bay_left(self, bay):
        """Left edge of bay content (excluding U label column)."""
        return LABEL_W + bay * (BAY_W + BAY_SEP)

    def _point_to_bay_u(self, pos):
        """Returns (bay, u) from mouse position. u is 1-based. Returns (-1,-1) if outside."""
        x, y = pos.x(), pos.y()
        rack_h = self.rack.u_size * SLOT_H
        if y < 0 or y >= rack_h:
            return -1, -1
        for bay in range(self.rack.bays):
            bx = self._bay_left(bay)
            if bx <= x < bx + BAY_W:
                u = int(y // SLOT_H) + 1
                return bay, u
        return -1, -1

    # ── Drag from library ─────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            bay, u = self._point_to_bay_u(event.position().toPoint())
            self._hover_bay = bay
            self._hover_u   = u
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._hover_bay = -1
        self._hover_u   = -1
        self.update()

    def dropEvent(self, event):
        self._hover_bay = -1
        self._hover_u   = -1
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

        # ── Tray logic: try to merge with existing slot at target_u ───────────
        if not dev.rack_native and dev.width_mm is not None:
            existing = self.rack.slot_at(target_u, bay)
            if existing is not None and self._can_add_to_tray(existing, dev):
                self._add_to_tray(existing, dev)
                self.slot_moved.emit()
                self.update()
                event.acceptProposedAction()
                return

        # ── Normal drop ───────────────────────────────────────────────────────
        pos = self._free_near(target_u, dev.u_height, bay)
        if pos is None:
            MsgBox.warn(self, "No space", "Not enough free space in this bay.")
            self.update()
            return
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

    def _can_add_to_tray(self, slot: RackSlot, dev: "DeviceDefinition") -> bool:
        """True if dev can join slot as a tray member."""
        snap = slot.device_snapshot
        # Slot must itself be non-rack-native (has a defined width_mm < full rack)
        if slot.is_tray:
            return slot.tray_can_fit(dev.width_mm)
        # Single non-tray slot: eligible only if it is also non-rack-native
        if snap.get("rack_native", True):
            return False
        slot_w = snap.get("width_mm")
        if slot_w is None:
            return False
        return (slot_w + dev.width_mm) <= 482.0

    def _add_to_tray(self, slot: RackSlot, dev: "DeviceDefinition") -> None:
        """Convert slot to tray (if needed) and append dev."""
        if not slot.is_tray:
            # Promote existing single device to tray_devices list
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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            slot, bay = self._slot_at(event.position().toPoint())
            if slot:
                u_clicked = int(event.position().toPoint().y() // SLOT_H) + 1
                self._drag_slot   = slot
                self._drag_bay    = bay
                self._drag_offset = u_clicked - slot.position_u
                self._drag_moved  = False
            else:
                # Click on empty area — deselect
                self._selected_slot = None
                self.slot_selected.emit(None)
                self.update()

    def mouseMoveEvent(self, event):
        if self._drag_slot and (event.buttons() & Qt.MouseButton.LeftButton):
            bay, u_raw = self._point_to_bay_u(event.position().toPoint())
            if bay < 0:
                return
            new_u = max(1, u_raw - self._drag_offset)
            new_u = min(new_u, self.rack.u_size - self._drag_slot.u_height + 1)
            others = [s for s in self.rack.slots
                      if s.id != self._drag_slot.id and s.bay == self._drag_bay]
            collision = any(
                not (new_u + self._drag_slot.u_height <= s.position_u or
                     new_u >= s.position_u + s.u_height)
                for s in others
            )
            if not collision:
                if new_u != self._drag_slot.position_u:
                    self._drag_moved = True
                self._drag_slot.position_u = new_u
                self.update()

    def mouseReleaseEvent(self, event):
        if self._drag_slot:
            slot = self._drag_slot
            moved = getattr(self, '_drag_moved', False)
            self._drag_slot = None
            if moved:
                self.slot_moved.emit()
            else:
                # It was a click, not a drag — select the slot
                self._selected_slot = slot
                self.slot_selected.emit(slot)
            self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rack_h = self.rack.u_size * SLOT_H

        # Fill entire widget background (U-label column + stats bar area)
        # to prevent ghosting from underlying widgets bleeding through.
        p.fillRect(0, 0, self._canvas_width(), self._canvas_height(), QColor("#181818"))

        for bay in range(self.rack.bays):
            bx = self._bay_left(bay)

            # Bay separator
            if bay > 0:
                p.fillRect(bx - BAY_SEP, 0, BAY_SEP, rack_h, QColor("#0d0d0d"))

            # Bay background
            p.fillRect(bx, 0, BAY_W, rack_h, QColor("#141414"))

            # U grid lines (very subtle)
            p.setPen(QPen(QColor("#1e1e1e"), 1))
            for u in range(self.rack.u_size + 1):
                y = u * SLOT_H
                p.drawLine(bx, y, bx + BAY_W, y)

            # U labels — leftmost bay only
            if bay == 0:
                f = QFont("Consolas", U_FONT_SIZE)
                p.setFont(f)
                p.setPen(QColor("#3a3a3a"))
                for u in range(self.rack.u_size):
                    y = u * SLOT_H
                    p.drawText(0, y, LABEL_W - 6, SLOT_H,
                               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                               str(u + 1))

            # Drop hover highlight
            if self._hover_bay == bay and self._hover_u > 0:
                hy = (self._hover_u - 1) * SLOT_H
                p.setPen(QPen(QColor(ACCENT), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(bx + 1, hy + 1, BAY_W - 2, SLOT_H - 2)

            # ── Draw slots ────────────────────────────────────────────────────
            for slot in sorted(
                [s for s in self.rack.slots if s.bay == bay],
                key=lambda s: s.position_u
            ):
                u0 = slot.position_u - 1
                sx = bx + 1
                sy = u0 * SLOT_H + 1
                sw = BAY_W - 2
                sh = slot.u_height * SLOT_H - 2

                is_selected = (self._selected_slot is not None and
                               self._selected_slot.id == slot.id)

                if slot.is_tray:
                    # ── Tray: draw sub-devices side by side ───────────────────
                    p.fillRect(sx, sy, sw, sh, QColor("#141414"))

                    total_mm = sum(d.get("width_mm") or 482.0 for d in slot.tray_devices)
                    px_per_mm = sw / max(total_mm, 482.0)
                    cur_x = sx
                    for i, dev_snap in enumerate(slot.tray_devices):
                        dev_mm  = dev_snap.get("width_mm") or 482.0
                        dev_px  = int(dev_mm * px_per_mm)
                        # Last device gets any rounding remainder
                        if i == len(slot.tray_devices) - 1:
                            dev_px = sx + sw - cur_x

                        from app.models import category_color
                        color_hex = dev_snap.get("color") or category_color(dev_snap.get("category", "Other"))
                        dev_color = QColor(color_hex)

                        # Sub-device background — same neutral as normal slots
                        p.fillRect(cur_x + 1, sy + 1, dev_px - 2, sh - 2,
                                   QColor("#1c1c1c"))

                        # Left color stripe per sub-device
                        p.fillRect(cur_x + 1, sy + 1, 3, sh - 2, dev_color)

                        # Separator between sub-devices
                        if i > 0:
                            p.setPen(QPen(QColor("#0a0a0a"), 1))
                            p.drawLine(cur_x, sy, cur_x, sy + sh)

                        # Sub-device name
                        name_font = QFont("Segoe UI", NAME_FONT_SIZE)
                        name_font.setWeight(QFont.Weight.Medium)
                        p.setFont(name_font)
                        p.setPen(QColor("#c8c0b0"))
                        name_rect = QRect(cur_x + 6, sy, dev_px - 8, sh)
                        p.drawText(name_rect,
                                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                   dev_snap.get("name", "?"))

                        cur_x += dev_px

                    # Outer tray border
                    if is_selected:
                        p.setPen(QPen(QColor(ACCENT), 1))
                    else:
                        p.setPen(QPen(QColor("#282828"), 1))
                    p.drawRect(sx, sy, sw, sh)

                else:
                    # ── Normal single-device slot ─────────────────────────────
                    # Slot background
                    p.fillRect(sx, sy, sw, sh, QColor("#1c1c1c"))

                    # Left accent bar — amber if slot has notes, else dim
                    left_bar_color = QColor(ACCENT) if slot.notes else QColor("#2a2a2a")
                    p.fillRect(sx, sy, 4, sh, left_bar_color)

                    # Slot border — highlight if selected
                    if is_selected:
                        p.setPen(QPen(QColor(ACCENT), 1))
                    else:
                        p.setPen(QPen(QColor("#282828"), 1))
                    p.drawRect(sx, sy, sw, sh)

                    # ── Name ──────────────────────────────────────────────────
                    name_font = QFont("Segoe UI", NAME_FONT_SIZE)
                    name_font.setWeight(QFont.Weight.Medium)
                    p.setFont(name_font)
                    p.setPen(QColor("#c8c0b0"))

                    pad_l = 10
                    name_rect = QRect(sx + pad_l, sy, sw - pad_l - 40, sh)
                    p.drawText(name_rect,
                               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                               slot.name)

                    # ── U height badge (right) ─────────────────────────────
                    u_font = QFont("Consolas", U_FONT_SIZE)
                    p.setFont(u_font)
                    p.setPen(QColor("#383838"))
                    u_rect = QRect(sx + sw - 38, sy, 34, sh)
                    p.drawText(u_rect,
                               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                               f"{slot.u_height}U")

            # Bay outer border
            p.setPen(QPen(QColor("#2a2a2a"), 1))
            p.drawRect(bx, 0, BAY_W, rack_h)

        # ── Stats bar ─────────────────────────────────────────────────────────
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor("#444"))
        used   = self.rack.used_u()
        free   = self.rack.free_u()
        watts  = self.rack.total_watts()
        weight = self.rack.total_weight()
        bays_s = f" · {self.rack.bays} bays" if self.rack.bays > 1 else ""
        stats  = f"  {used}U used · {free}U free{bays_s}"
        if watts  > 0: stats += f" · {watts:.0f} W"
        if weight > 0: stats += f" · {weight:.1f} kg"
        p.drawText(0, rack_h + 4, self._canvas_width(), 18,
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, stats)

    # ── Hit test ──────────────────────────────────────────────────────────────

    def _slot_at(self, pos):
        """Returns (slot, bay) or (None, -1)."""
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
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background:#222; color:#e8e0cc; border:1px solid #333; }
            QMenu::item { padding:7px 20px; font-size:12px; }
            QMenu::item:selected { background:#2a2a2a; color:#e8a020; }
            QMenu::separator { height:1px; background:#333; }
        """)
        if slot:
            note_act   = menu.addAction("Edit notes…")
            menu.addSeparator()
            up_act     = menu.addAction("Move up  ↑")
            down_act   = menu.addAction("Move down  ↓")
            menu.addSeparator()
            if slot.is_tray:
                tray_menu = menu.addMenu("Remove device from tray…")
                tray_menu.setStyleSheet("""
                    QMenu { background:#222; color:#e8e0cc; border:1px solid #333; }
                    QMenu::item { padding:7px 20px; font-size:12px; }
                    QMenu::item:selected { background:#2a2a2a; color:#e8a020; }
                """)
                tray_acts = []
                for i, dev_snap in enumerate(slot.tray_devices):
                    act = tray_menu.addAction(dev_snap.get("name", f"Device {i+1}"))
                    tray_acts.append((i, act))
            remove_act = menu.addAction("Remove from rack")
            action = menu.exec(self.mapToGlobal(pos))
            if action == remove_act:
                self.rack.slots.remove(slot)
                self.slot_removed.emit()
                self.update()
            elif action == note_act:
                dlg = SlotNoteDialog(slot, self)
                if dlg.exec():
                    slot.notes = dlg.get_notes()
                    self.update()
            elif action == up_act:
                self._move_step(slot, -1)
            elif action == down_act:
                self._move_step(slot, +1)
            elif slot.is_tray:
                for i, act in tray_acts:
                    if action == act:
                        slot.tray_devices.pop(i)
                        # If only one device left, demote tray back to normal slot
                        if len(slot.tray_devices) == 1:
                            slot.device_snapshot = slot.tray_devices[0]
                            slot.tray_devices = []
                        elif len(slot.tray_devices) == 0:
                            self.rack.slots.remove(slot)
                            self.slot_removed.emit()
                        self.slot_moved.emit()
                        self.update()
                        break
        else:
            b, u = self._point_to_bay_u(pos)
            if b >= 0 and 1 <= u <= self.rack.u_size:
                blank_act = menu.addAction(
                    f"Insert blank panel at U{u}" +
                    (f" (Bay {b+1})" if self.rack.bays > 1 else ""))
                action = menu.exec(self.mapToGlobal(pos))
                if action == blank_act:
                    self._insert_blank(u, b)

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
        slot.position_u = new_pos
        self.slot_moved.emit()
        self.update()

    def _insert_blank(self, u, bay=0):
        import uuid
        snapshot = {
            "id": str(uuid.uuid4()), "name": "Blank Panel", "category": "Other",
            "u_height": 1, "color": "#1e1e1e", "manufacturer": "", "model": "",
            "watts": None, "weight_kg": None, "depth_mm": None, "notes": "",
            "image_front": "", "image_rear": "",
        }
        if not self.rack.is_slot_occupied(u, 1, bay):
            self.rack.slots.append(RackSlot(device_snapshot=snapshot, position_u=u, bay=bay))
            self.slot_moved.emit()
            self.update()

    def add_device(self, device: DeviceDefinition, bay: int = 0) -> bool:
        """Add device to specified bay, or first bay with space.
        Uses _free_near to find the first position with enough consecutive free U."""
        for b in [bay] + [i for i in range(self.rack.bays) if i != bay]:
            pos = self._free_near(1, device.u_height, b)
            if pos is not None:
                self.rack.slots.append(RackSlot(
                    device_id=device.id,
                    device_snapshot=device.to_dict(),
                    position_u=pos,
                    bay=b,
                ))
                self.update()
                return True
        return False
