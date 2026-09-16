"""
Modern Discord-themed Splash Screen for Linux Edition.
"""

import time
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class ModernSplashScreen(QWidget):
    def __init__(self, version: str = "v1.5.0"):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(500, 250)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(15, 15, 15, 15)

        self.container = QWidget(self)
        self.container.setObjectName("splashContainer")
        self.container.setStyleSheet("""
            #splashContainer {
                background-color: #1e1f22;
                border: 1px solid #35373c;
                border-radius: 16px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(14)

        icon_lbl = QLabel("🎙️")
        icon_lbl.setStyleSheet("font-size: 38px; background: transparent;")
        header_row.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)

        title_lbl = QLabel("Desktop Audio to Mic (Linux)")
        title_lbl.setStyleSheet("color: #f2f3f5; font-size: 20px; font-weight: 800; background: transparent;")
        title_vbox.addWidget(title_lbl)

        subtitle_lbl = QLabel("PipeWire & PulseAudio Low-Latency Streamer")
        subtitle_lbl.setStyleSheet("color: #949ba4; font-size: 13px; font-weight: 500; background: transparent;")
        title_vbox.addWidget(subtitle_lbl)

        header_row.addLayout(title_vbox)
        header_row.addStretch()
        layout.addLayout(header_row)

        layout.addSpacing(6)

        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(8)
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(10)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2b2d31;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5865f2, stop:1 #23a55a);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.prog_bar)

        status_row = QHBoxLayout()
        self.lbl_status = QLabel("Starting Linux audio engine...")
        self.lbl_status.setStyleSheet("color: #b5bac1; font-size: 12px; background: transparent;")
        status_row.addWidget(self.lbl_status)

        status_row.addStretch()

        self.lbl_version = QLabel(version)
        self.lbl_version.setStyleSheet("color: #5865f2; font-size: 11px; font-weight: bold; background: transparent;")
        status_row.addWidget(self.lbl_version)

        layout.addLayout(status_row)
        outer_layout.addWidget(self.container)

        self._center_on_screen()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def set_progress(self, val: int, message: str = None):
        self.prog_bar.setValue(val)
        if message:
            self.lbl_status.setText(message)
        QApplication.processEvents()

    def finish(self, main_window):
        self.set_progress(100, "Ready!")
        QApplication.processEvents()
        time.sleep(0.2)
        main_window.show()
        self.close()
