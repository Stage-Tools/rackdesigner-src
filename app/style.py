# StageTools design system — official palette from design guidelines
# Font: Bebas Neue (titles/logo), Segoe UI (body)
# Accent: #E8A020 (amber), darker: #C87A10
# Background: #090A0A base, text: #E8E0CC

ACCENT       = "#E8A020"
ACCENT_DARK  = "#C87A10"
ACCENT_DIM   = "#3A2808"

BG0 = "#1E1E1E"
BG1 = "#272727"
BG2 = "#2E2E2E"
BG3 = "#363636"
BG4 = "#444444"

TEXT_PRIMARY   = "#EDE8DC"
TEXT_SECONDARY = "#C0BEB4"
TEXT_MUTED     = "#909088"
DANGER         = "#E53935"

FONT_TITLE = "Bebas Neue"
FONT_BODY  = "Segoe UI"

APP_STYLESHEET = f"""
QMainWindow, QDialog, QWidget {{
    background-color: {BG1};
    color: {TEXT_PRIMARY};
    font-family: "{FONT_BODY}", sans-serif;
    font-size: 13px;
}}

QMenuBar {{ background:{BG0}; color:{TEXT_SECONDARY}; border-bottom:1px solid {BG4}; }}
QMenuBar::item {{ padding:5px 12px; background:transparent; }}
QMenuBar::item:selected {{ background:{BG3}; color:{TEXT_PRIMARY}; }}
QMenu {{ background:{BG2}; color:{TEXT_PRIMARY}; border:1px solid {BG4}; padding:4px 0; }}
QMenu::item {{ padding:7px 28px 7px 16px; font-size:12px; }}
QMenu::item:selected {{ background:{BG4}; color:{ACCENT}; }}
QMenu::separator {{ height:1px; background:{BG4}; margin:4px 0; }}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background:{BG3}; color:{TEXT_PRIMARY};
    border:1px solid {BG4}; border-radius:3px;
    padding:5px 8px; font-size:13px;
    selection-background-color:{ACCENT_DIM}; selection-color:{TEXT_PRIMARY};
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border:1px solid {ACCENT};
}}
QComboBox QAbstractItemView {{
    background:{BG2}; color:{TEXT_PRIMARY}; border:1px solid {BG4};
    selection-background-color:{BG4}; selection-color:{ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background:{BG4}; border:none; width:18px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background:{BG3};
}}

QPushButton {{
    background:{BG3}; color:{TEXT_PRIMARY};
    border:1px solid {BG4}; border-radius:3px;
    padding:6px 16px; font-size:12px; font-weight:500; letter-spacing:0.3px;
}}
QPushButton:hover {{ background:{BG4}; border-color:#444; }}
QPushButton:pressed {{ background:{BG0}; }}

QListWidget {{
    background:{BG2}; color:{TEXT_PRIMARY};
    border:1px solid {BG4}; border-radius:3px; outline:none; font-size:12px;
}}
QListWidget::item {{ padding:7px 10px; border-bottom:1px solid {BG3}; }}
QListWidget::item:hover {{ background:{BG3}; }}
QListWidget::item:selected {{
    background:{ACCENT_DIM}; color:{ACCENT}; border-left:2px solid {ACCENT};
}}

QScrollBar:vertical {{ background:{BG1}; width:6px; border:none; }}
QScrollBar::handle:vertical {{ background:{BG4}; border-radius:3px; min-height:30px; }}
QScrollBar::handle:vertical:hover {{ background:#444; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QScrollBar:horizontal {{ background:{BG1}; height:6px; border:none; }}
QScrollBar::handle:horizontal {{ background:{BG4}; border-radius:3px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}

QTabWidget::pane {{ border:1px solid {BG4}; background:{BG1}; top:-1px; }}
QTabBar::tab {{
    background:{BG2}; color:{TEXT_SECONDARY};
    padding:8px 18px; border:1px solid {BG4}; border-bottom:none;
    font-size:10px; font-weight:700; letter-spacing:1px; margin-right:2px;
}}
QTabBar::tab:selected {{ background:{BG1}; color:{ACCENT}; border-top:2px solid {ACCENT}; }}
QTabBar::tab:hover:!selected {{ background:{BG3}; color:{TEXT_PRIMARY}; }}

QFormLayout QLabel {{ color:{TEXT_SECONDARY}; font-size:11px; letter-spacing:0.5px; }}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color:{BG4}; }}

QStatusBar {{
    background:{BG0}; color:{TEXT_MUTED};
    border-top:1px solid {BG4}; font-size:11px; padding:0 8px;
}}
QSplitter::handle {{ background:{BG4}; width:1px; height:1px; }}
QMessageBox {{ background:{BG2}; }}
QMessageBox QLabel {{ color:{TEXT_PRIMARY}; font-size:13px; }}
QToolTip {{
    background:{BG3}; color:{TEXT_PRIMARY};
    border:1px solid {BG4}; font-size:11px; padding:4px 8px;
}}
*[acceptDrops="true"] {{ border: none; outline: none; }}
"""
