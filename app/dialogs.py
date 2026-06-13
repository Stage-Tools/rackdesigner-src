"""
Custom styled message dialogs — replaces QMessageBox throughout the app.

Usage:
    from app.dialogs import MsgBox

    MsgBox.info(parent, "Title", "Message")
    MsgBox.warn(parent, "Title", "Message")
    MsgBox.error(parent, "Title", "Message")
    MsgBox.question(parent, "Title", "Message")          → True / False
    MsgBox.question3(parent, "Title", "Message")         → "yes" / "no" / "cancel"
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from app.style import (
    ACCENT, BG0, BG1, BG2, BG3, BG4,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, DANGER, FONT_BODY
)

# ── Variant palette ───────────────────────────────────────────────────────────
_VARIANTS = {
    "info":     {"icon": "ℹ",  "color": "#5B9BD5"},
    "warn":     {"icon": "⚠",  "color": ACCENT},
    "error":    {"icon": "✕",  "color": DANGER},
    "question": {"icon": "?",  "color": TEXT_SECONDARY},
}


class _MsgDialog(QDialog):
    def __init__(self, parent, title: str, message: str, variant: str,
                 buttons: list[tuple[str, str]]):
        """
        buttons: list of (label, role)
            role in: "accept", "reject", "cancel", "danger"
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setMaximumWidth(520)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self._result = None

        v = _VARIANTS.get(variant, _VARIANTS["info"])

        self.setStyleSheet(f"""
            QDialog {{
                background:{BG1};
                border:1px solid {BG4};
                border-radius:6px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(44)
        header.setStyleSheet(f"background:{BG0}; border-bottom:1px solid {BG4};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.setSpacing(10)

        icon_lbl = QLabel(v["icon"])
        icon_lbl.setFont(QFont(FONT_BODY, 14, QFont.Weight.Bold))
        icon_lbl.setStyleSheet(f"color:{v['color']}; background:transparent;")
        icon_lbl.setFixedWidth(20)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont(FONT_BODY, 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent; letter-spacing:0.5px;")

        hl.addWidget(icon_lbl)
        hl.addWidget(title_lbl)
        hl.addStretch()
        root.addWidget(header)

        # ── Body ──────────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background:{BG1};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 20, 24, 20)

        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont(FONT_BODY, 11))
        msg_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent;")
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bl.addWidget(msg_lbl)
        root.addWidget(body)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setStyleSheet(f"background:{BG0}; border-top:1px solid {BG4};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 10, 16, 10)
        fl.setSpacing(8)
        fl.addStretch()

        # Il primo bottone con ruolo "accept" o "danger" diventa il default (Enter)
        _default_roles = {"accept", "danger"}
        _has_default = False

        for label, role in buttons:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setMinimumWidth(72)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            if role == "accept":
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background:{ACCENT}; color:#0a0a0a;
                        border:1px solid {ACCENT}; border-radius:3px;
                        font-size:10px; font-weight:700; letter-spacing:1px; padding:0 14px;
                    }}
                    QPushButton:hover {{ background:#d49018; border-color:#d49018; }}
                    QPushButton:pressed {{ background:#b87010; }}
                """)
            elif role == "danger":
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background:transparent; color:{DANGER};
                        border:1px solid #3a1a1a; border-radius:3px;
                        font-size:10px; font-weight:700; letter-spacing:1px; padding:0 14px;
                    }}
                    QPushButton:hover {{ background:#1e0f0f; border-color:{DANGER}; }}
                    QPushButton:pressed {{ background:#2a0a0a; }}
                """)
            else:  # "reject" / "cancel"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background:transparent; color:{TEXT_MUTED};
                        border:1px solid {BG4}; border-radius:3px;
                        font-size:10px; font-weight:700; letter-spacing:1px; padding:0 14px;
                    }}
                    QPushButton:hover {{ color:{TEXT_SECONDARY}; border-color:#555; }}
                    QPushButton:pressed {{ background:{BG3}; }}
                """)

            # Il primo bottone "accetta/danger" cattura Enter
            if role in _default_roles and not _has_default:
                btn.setDefault(True)
                btn.setAutoDefault(True)
                _has_default = True
            else:
                btn.setDefault(False)
                btn.setAutoDefault(False)

            _role = role
            _label = label
            btn.clicked.connect(lambda _, r=_role, l=_label: self._on_click(r, l))
            fl.addWidget(btn)

        root.addWidget(footer)
        self.adjustSize()

    def _on_click(self, role, label):
        self._result = role
        if role in ("accept", "danger"):
            self.accept()
        else:
            self.reject()

    def get_result(self):
        return self._result


# ── Public API ────────────────────────────────────────────────────────────────

class MsgBox:

    @staticmethod
    def info(parent, title: str, message: str) -> None:
        dlg = _MsgDialog(parent, title, message, "info",
                         [("OK", "accept")])
        dlg.exec()

    @staticmethod
    def warn(parent, title: str, message: str) -> None:
        dlg = _MsgDialog(parent, title, message, "warn",
                         [("OK", "accept")])
        dlg.exec()

    @staticmethod
    def error(parent, title: str, message: str) -> None:
        dlg = _MsgDialog(parent, title, message, "error",
                         [("OK", "accept")])
        dlg.exec()

    @staticmethod
    def question(parent, title: str, message: str) -> bool:
        """Returns True if Yes, False if No."""
        dlg = _MsgDialog(parent, title, message, "question",
                         [("No", "reject"), ("Yes", "accept")])
        dlg.exec()
        return dlg.get_result() == "accept"

    @staticmethod
    def question3(parent, title: str, message: str) -> str:
        """Returns 'yes', 'no', or 'cancel'."""
        dlg = _MsgDialog(parent, title, message, "question",
                         [("Cancel", "cancel"), ("No", "reject"), ("Yes", "accept")])
        result = dlg.exec()
        r = dlg.get_result()
        if r == "accept":
            return "yes"
        if r == "reject":
            return "no"
        return "cancel"

    @staticmethod
    def question_danger(parent, title: str, message: str) -> bool:
        """Yes/No con Yes stilizzato come azione distruttiva."""
        dlg = _MsgDialog(parent, title, message, "question",
                         [("Cancel", "cancel"), ("Delete", "danger")])
        dlg.exec()
        return dlg.get_result() == "danger"
