"""
Desktop Audio to Mic - Linux Edition
Main Application Entry Point
"""

import os
import sys
import traceback

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from src.ui.gui import MainWindow
from src.ui.splash import ModernSplashScreen


def excepthook(exc_type, exc_value, exc_tb):
    """Global unhandled exception hook to write to crash.log and show an alert."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(app_dir, "crash.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- LINUX CRASH REPORT ---\n{err_msg}\n")
    except Exception:
        pass

    print(f"CRASH: {err_msg}", file=sys.stderr)
    try:
        QMessageBox.critical(
            None,
            "Unexpected Application Error",
            f"An error occurred:\n{exc_value}\n\nDetails saved to crash.log."
        )
    except Exception:
        pass


def main():
    sys.excepthook = excepthook

    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Audio to Mic")
    app.setDesktopFileName("desktop-audio-to-mic.desktop")
    app.setQuitOnLastWindowClosed(False)

    splash = ModernSplashScreen()
    splash.show()
    app.processEvents()

    window = MainWindow(splash=splash)
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
