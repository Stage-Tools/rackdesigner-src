import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from app.main_window import MainWindow
from app.style import APP_STYLESHEET

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Rack Designer")
    app.setOrganizationName("StageTools")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    app.setFont(QFont("Segoe UI", 10))

    from app.preloaded_library import seed_library_if_empty
    seed_library_if_empty()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
