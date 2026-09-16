"""
Discord Desktop Audio Mic - Main Entry Point
"""

import os
import sys
import ctypes
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
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH REPORT ---\n{err_msg}\n")
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

    # Enable crisp font rendering and high DPI support
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

        # Windows taskbar grouping ID so the app has its own distinct taskbar icon
        try:
            app_id = "discord.desktop.audio.mic.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    if sys.platform.startswith("linux"):
        app.setDesktopFileName("discord-desktop-audio-mic")

    splash = ModernSplashScreen()
    splash.show()
    app.processEvents()

    # Close PyInstaller native bootloader splash once Qt splash is displayed
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    window = MainWindow(splash=splash)
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
