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

import sys
import os
import traceback
from datetime import datetime
from pathlib import Path


def _log_pre_qt_crash(exc_type, exc_value, exc_tb):
    """
    Logs a startup failure that happens before QApplication exists — a
    broken Qt platform plugin/driver during QApplication() construction, or
    an import-time failure in any of this module's own top-level imports
    (task.md #63). Plain file I/O only, no Qt or app-package dependency,
    since either could be exactly what's broken: duplicates
    storage.get_app_data_dir()'s path logic instead of importing it, so
    logging still works even if app.storage itself fails to import.
    No dialog is possible this early (no QApplication yet) — disk logging
    is the ceiling at this stage.
    """
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        log_path = Path(base) / "RackDesigner" / "crash.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] (startup failure before the app could initialize)\n{tb_text}\n")
    except Exception:
        pass  # logging must never itself raise a second exception


try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    from app.main_window import MainWindow
    from app.style import APP_STYLESHEET
    from app.storage import get_app_data_dir
    from app.dialogs import MsgBox
except Exception:
    _log_pre_qt_crash(*sys.exc_info())
    raise


def _log_crash(exc_type, exc_value, exc_tb):
    """Appends a timestamped traceback to crash.log. The one logging
    implementation, shared by _excepthook (anything escaping the running
    event loop) and main()'s seeding guard (task.md #62) — Qt/app.storage
    are already known-good by the time either caller runs, so this can use
    the real get_app_data_dir() (unlike _log_pre_qt_crash above, which
    can't assume that yet)."""
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        log_path = get_app_data_dir() / "crash.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}]\n{tb_text}\n")
    except Exception:
        pass  # logging must never itself take the app down


def _excepthook(exc_type, exc_value, exc_tb):
    # Let Ctrl+C / sys.exit() behave normally instead of logging/dialoging them.
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    _log_crash(exc_type, exc_value, exc_tb)

    try:
        MsgBox.error(
            QApplication.activeWindow(),
            "Unexpected error",
            "Something went wrong. Details were saved to the log file so the "
            "issue can be investigated. You can keep working, but consider "
            "saving your project now.",
        )
    except Exception:
        pass  # showing the dialog must never itself take the app down


def _notify_if_library_was_reset(parent, seed_info: dict):
    """Shown once at startup if seed_library_if_empty() found library.json
    and/or custom_categories.json corrupt (as opposed to a genuine first-run
    empty state) — see app.preloaded_library.seed_library_if_empty()."""
    reset = []
    if seed_info.get("library_corrupt"):
        reset.append(("device library", seed_info.get("library_backup")))
    if seed_info.get("categories_corrupt"):
        reset.append(("custom categories", seed_info.get("categories_backup")))
    if not reset:
        return

    names = " and ".join(n for n, _ in reset)
    backup_lines = "\n".join(b for _, b in reset if b)
    message = (
        f"Your {names} file appeared to be corrupted and has been reset to "
        f"defaults. A backup of the original file was saved to:\n{backup_lines}"
    )
    try:
        MsgBox.info(parent, "Library reset", message)
    except Exception:
        pass  # a failure showing this notice must not take the app down


def _notify_seed_failed(parent):
    """Shown once at startup if seed_library_if_empty() itself raised
    (task.md #62) — distinct from _notify_if_library_was_reset above, which
    covers "found and quarantined a corrupt file," not "failed to seed at
    all." The exception itself was already logged via _log_crash before
    this is called."""
    try:
        MsgBox.error(
            parent,
            "Library initialization failed",
            "The device library could not be set up, and the error has been "
            "saved to the log file. The app is still usable, but the device "
            "library may be empty or incomplete this session.",
        )
    except Exception:
        pass  # showing this notice must not take the app down


def main():
    try:
        app = QApplication(sys.argv)
    except Exception:
        _log_pre_qt_crash(*sys.exc_info())
        raise
    app.setApplicationName("Rack Designer")
    app.setOrganizationName("StageTools")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    app.setFont(QFont("Segoe UI", 10))

    sys.excepthook = _excepthook

    from app.preloaded_library import seed_library_if_empty
    seed_info = {}
    seed_failed = False
    try:
        seed_info = seed_library_if_empty()
    except Exception:
        _log_crash(*sys.exc_info())
        seed_failed = True

    window = MainWindow()
    window.show()
    if seed_failed:
        _notify_seed_failed(window)
    else:
        _notify_if_library_was_reset(window, seed_info)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
