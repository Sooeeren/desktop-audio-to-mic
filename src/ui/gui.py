"""
Modern PySide6 User Interface for Desktop Audio to Discord Microphone
Features:
- Multi-page navigation (Studio, App Profiles & Routing, Equalizer & FX, Settings).
- High-contrast custom toggle switches.
- Gradient volume sliders with glowing thumbs and click-seeking.
- Pro Audio visualizer graph (48-band FFT spectrum + oscilloscope wave).
- Per-application session mixer and soloing (Firefox, Spotify, games, etc.).
- 7-band parametric/graphic Equalizer with studio presets.
- "Troll" Mode with extreme sub-bass boost, analog saturation overdrive, and limiter.
- Light and Dark themes with instantaneous switching.
- Startup and on-demand GitHub version checking.
"""

import os
import sys
import threading
import numpy as np

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QRectF, QUrl
from PySide6.QtGui import (
    QIcon, QFont, QColor, QPainter, QLinearGradient, QPen,
    QBrush, QPainterPath, QAction, QDesktopServices
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QFrame,
    QProgressBar, QSystemTrayIcon, QMenu, QScrollArea,
    QMessageBox, QDialog, QStackedWidget, QRadioButton, QButtonGroup,
    QGridLayout, QSizePolicy
)

try:
    from src.devices.device_manager import (
        DeviceManager, load_config, save_config,
        get_windows_default_input_name, set_windows_default_input_device,
        get_active_audio_sessions, set_session_volume, set_session_mute,
        solo_session, unmute_all_sessions, open_windows_app_volume_settings
    )
    from src.audio.audio_engine import AudioEngine, EQ_FREQUENCIES
    from src.devices import virtual_driver
    from src.utils.updater import UpdateCheckWorker, CURRENT_VERSION, RELEASES_URL
except ImportError:
    from device_manager import (
        DeviceManager, load_config, save_config,
        get_windows_default_input_name, set_windows_default_input_device,
        get_active_audio_sessions, set_session_volume, set_session_mute,
        solo_session, unmute_all_sessions, open_windows_app_volume_settings
    )
    from audio_engine import AudioEngine, EQ_FREQUENCIES
    import virtual_driver
    from updater import UpdateCheckWorker, CURRENT_VERSION, RELEASES_URL


DARK_STYLE = """
QMainWindow, QWidget#centralWidget {
    background-color: #1e1f22;
    color: #f2f3f5;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QScrollBar:horizontal {
    height: 0px;
    width: 0px;
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 4px 2px 4px 0px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #3b3e45;
    min-height: 36px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #5865f2;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QFrame.card {
    background-color: #2b2d31;
    border-radius: 10px;
    border: 1px solid #35373c;
    padding: 0px;
}

QFrame.hazard_card {
    background-color: #2b1f20;
    border-radius: 10px;
    border: 1px solid #da373c;
    padding: 0px;
}

QLabel {
    color: #dbdee1;
    font-size: 13px;
}

QLabel.title {
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
}

QLabel.subtitle {
    color: #949ba4;
    font-size: 12px;
}

QLabel.sectionHeading {
    color: #f2f3f5;
    font-size: 14px;
    font-weight: bold;
}

QComboBox {
    background-color: #1e1f22;
    color: #f2f3f5;
    border: 1px solid #35373c;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}

QComboBox:hover {
    border: 1px solid #5865f2;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #2b2d31;
    color: #f2f3f5;
    selection-background-color: #5865f2;
    selection-color: #ffffff;
    border: 1px solid #35373c;
    outline: none;
}

QPushButton.primary {
    background-color: #5865f2;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton.primary:hover {
    background-color: #4752c4;
}

QPushButton.secondary {
    background-color: #383a40;
    color: #f2f3f5;
    border: 1px solid #4e5058;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
}
QPushButton.secondary:hover {
    background-color: #404249;
    border: 1px solid #949ba4;
}

QPushButton.ghost {
    background-color: transparent;
    color: #dbdee1;
    border: 1px solid #35373c;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}
QPushButton.ghost:hover {
    background-color: #35373c;
    color: #ffffff;
}

QPushButton.danger {
    background-color: #da373c;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton.danger:hover {
    background-color: #a1282c;
}

QPushButton.nav_tab {
    background-color: #1e1f22;
    color: #949ba4;
    border: 1px solid #35373c;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton.nav_tab:hover {
    background-color: #35373c;
    color: #f2f3f5;
    border: 1px solid #4e5058;
}
QPushButton.nav_tab:checked {
    background-color: #5865f2;
    color: #ffffff;
    border: 1px solid #5865f2;
}

QRadioButton {
    color: #dbdee1;
    font-size: 13px;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
}
"""

LIGHT_STYLE = """
QMainWindow, QWidget#centralWidget {
    background-color: #f2f3f5;
    color: #2e3338;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QScrollBar:horizontal {
    height: 0px;
    width: 0px;
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 4px 2px 4px 0px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #c4c9ce;
    min-height: 36px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #5865f2;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QFrame.card {
    background-color: #ffffff;
    border-radius: 10px;
    border: 1px solid #d1d5db;
    padding: 0px;
}

QFrame.hazard_card {
    background-color: #fff1f2;
    border-radius: 10px;
    border: 1px solid #f87171;
    padding: 0px;
}

QLabel {
    color: #2e3338;
    font-size: 13px;
}

QLabel.title {
    color: #060607;
    font-size: 18px;
    font-weight: bold;
}

QLabel.subtitle {
    color: #5c6570;
    font-size: 12px;
}

QLabel.sectionHeading {
    color: #060607;
    font-size: 14px;
    font-weight: bold;
}

QComboBox {
    background-color: #f2f3f5;
    color: #060607;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}

QComboBox:hover {
    border: 1px solid #5865f2;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #060607;
    selection-background-color: #5865f2;
    selection-color: #ffffff;
    border: 1px solid #d1d5db;
    outline: none;
}

QPushButton.primary {
    background-color: #5865f2;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton.primary:hover {
    background-color: #4752c4;
}

QPushButton.secondary {
    background-color: #e3e5e8;
    color: #2e3338;
    border: 1px solid #c4c9ce;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
}
QPushButton.secondary:hover {
    background-color: #d1d5db;
}

QPushButton.ghost {
    background-color: transparent;
    color: #4e5058;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}
QPushButton.ghost:hover {
    background-color: #e3e5e8;
    color: #060607;
}

QPushButton.danger {
    background-color: #da373c;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton.danger:hover {
    background-color: #a1282c;
}

QPushButton.nav_tab {
    background-color: #f2f3f5;
    color: #4e5058;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton.nav_tab:hover {
    background-color: #e3e5e8;
    color: #060607;
    border: 1px solid #c4c9ce;
}
QPushButton.nav_tab:checked {
    background-color: #5865f2;
    color: #ffffff;
    border: 1px solid #5865f2;
}

QRadioButton {
    color: #2e3338;
    font-size: 13px;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
}
"""


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.text = text
        self._checked = False
        self.setFixedHeight(30)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = 44
        h = 22
        y = (self.height() - h) // 2

        bg_color = QColor("#5865f2") if self._checked else QColor("#35373c")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, y, w, h, h // 2, h // 2)

        thumb_color = QColor("#ffffff")
        thumb_size = h - 4
        thumb_x = (w - thumb_size - 2) if self._checked else 2
        thumb_y = y + 2
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(thumb_x, thumb_y, thumb_size, thumb_size)

        if self.text:
            painter.setPen(QColor("#dbdee1"))
            font = painter.font()
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(w + 10, y + h - 5, self.text)


class GradientSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self.is_hovered = False

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.orientation() == Qt.Horizontal:
                val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / float(max(1, self.width()))
            else:
                val = self.maximum() - ((self.maximum() - self.minimum()) * event.position().y()) / float(max(1, self.height()))
            self.setValue(int(round(val)))
            event.accept()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        val_pct = (self.value() - self.minimum()) / float(max(1, self.maximum() - self.minimum()))
        val_pct = max(0.0, min(1.0, val_pct))

        if self.orientation() == Qt.Horizontal:
            track_h = 6
            track_y = (h - track_h) // 2
            margin_x = 10
            usable_w = w - 2 * margin_x

            painter.setBrush(QBrush(QColor("#1e1f22")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(margin_x, track_y, usable_w, track_h, track_h // 2, track_h // 2)

            fill_w = int(usable_w * val_pct)
            if fill_w > 0:
                grad = QLinearGradient(margin_x, track_y, margin_x + usable_w, track_y)
                grad.setColorAt(0.0, QColor("#5865F2"))
                grad.setColorAt(0.5, QColor("#23A55A"))
                grad.setColorAt(0.8, QColor("#F0B232"))
                grad.setColorAt(1.0, QColor("#F23F43"))
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(margin_x, track_y, fill_w, track_h, track_h // 2, track_h // 2)

            thumb_x = margin_x + int(usable_w * val_pct)
            thumb_y = h // 2
            thumb_r = 8 if self.is_hovered else 7

            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(QColor("#1e1f22"), 2))
            painter.drawEllipse(thumb_x - thumb_r, thumb_y - thumb_r, thumb_r * 2, thumb_r * 2)
        else:
            track_w = 6
            track_x = (w - track_w) // 2
            margin_y = 10
            usable_h = h - 2 * margin_y

            painter.setBrush(QBrush(QColor("#1e1f22")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(track_x, margin_y, track_w, usable_h, track_w // 2, track_w // 2)

            fill_h = int(usable_h * val_pct)
            fill_y = margin_y + (usable_h - fill_h)
            if fill_h > 0:
                grad = QLinearGradient(track_x, margin_y + usable_h, track_x, margin_y)
                grad.setColorAt(0.0, QColor("#5865F2"))
                grad.setColorAt(0.6, QColor("#23A55A"))
                grad.setColorAt(1.0, QColor("#F23F43"))
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(track_x, fill_y, track_w, fill_h, track_w // 2, track_w // 2)

            thumb_x = w // 2
            thumb_y = margin_y + int(usable_h * (1.0 - val_pct))
            thumb_r = 7

            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(QColor("#1e1f22"), 2))
            painter.drawEllipse(thumb_x - thumb_r, thumb_y - thumb_r, thumb_r * 2, thumb_r * 2)


class LiveVUMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0.0
        self.peak = 0.0
        self.decay = 0.88
        self.setMinimumWidth(80)
        self.setFixedHeight(14)

    def set_level(self, lvl: float):
        lvl = max(0.0, min(1.0, lvl))
        self.level = max(lvl, self.level * self.decay)
        if lvl > self.peak:
            self.peak = lvl
        else:
            self.peak = max(self.level, self.peak * 0.96)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        painter.setBrush(QBrush(QColor("#1e1f22")))
        painter.setPen(QPen(QColor("#35373c"), 1))
        painter.drawRoundedRect(0, 0, w, h, 3, 3)

        num_segments = 24
        gap = 2
        seg_w = max(2, (w - (num_segments + 1) * gap) // num_segments)
        active_count = int(self.level * num_segments)

        for i in range(num_segments):
            x = gap + i * (seg_w + gap)
            pct = i / float(num_segments)

            if pct < 0.65:
                color = QColor("#23A55A")
            elif pct < 0.85:
                color = QColor("#F0B232")
            else:
                color = QColor("#F23F43")

            if i < active_count:
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(x, 2, seg_w, h - 4, 1, 1)
            else:
                dim = QColor(color.red(), color.green(), color.blue(), 35)
                painter.setBrush(QBrush(dim))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(x, 2, seg_w, h - 4, 1, 1)

        if self.peak > 0.02:
            peak_idx = min(num_segments - 1, int(self.peak * num_segments))
            px = gap + peak_idx * (seg_w + gap)
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(px, 2, 2, h - 4, 1, 1)


class AudioVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.num_bars = 48
        self.bar_values = np.zeros(self.num_bars, dtype=np.float32)
        self.peak_values = np.zeros(self.num_bars, dtype=np.float32)
        self.decay = 0.82
        self.peak_decay = 0.94
        self.recent_wave = np.zeros(128, dtype=np.float32)
        self.current_db = -60.0

        self.setFixedHeight(115)
        self.setMinimumWidth(360)

    def update_audio(self, samples: np.ndarray):
        try:
            if samples is None or len(samples) < 32:
                self.bar_values *= self.decay
                self.peak_values *= self.peak_decay
                self.recent_wave *= 0.8
                self.current_db = max(-60.0, self.current_db - 2.0)
                self.update()
                return

            clean_samples = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
            if clean_samples.ndim > 1:
                mono = np.mean(clean_samples, axis=1)
            else:
                mono = clean_samples

            peak = float(np.max(np.abs(mono))) if len(mono) > 0 else 0.0
            if peak > 0.0001:
                self.current_db = float(np.clip(20.0 * np.log10(peak), -60.0, 6.0))
            else:
                self.current_db = -60.0

            step = max(1, len(mono) // 128)
            wave_sub = mono[::step][:128]
            if len(wave_sub) < 128:
                self.recent_wave = np.pad(wave_sub, (0, 128 - len(wave_sub)))
            else:
                self.recent_wave = wave_sub

            n = min(len(mono), 1024)
            if n >= 64:
                chunk = mono[:n] * np.hanning(n)
                fft_vals = np.abs(np.fft.rfft(chunk))[:n // 2]
                if len(fft_vals) >= self.num_bars:
                    indices = np.linspace(1, len(fft_vals), self.num_bars + 1, dtype=int)
                    for i in range(self.num_bars):
                        start = max(0, min(len(fft_vals) - 1, indices[i]))
                        end = max(start + 1, min(len(fft_vals), indices[i + 1]))
                        slice_vals = fft_vals[start:end]
                        val = float(np.max(slice_vals)) if len(slice_vals) > 0 else 0.0
                        norm = min(1.0, val * 0.18)
                        self.bar_values[i] = self.bar_values[i] * self.decay + norm * (1.0 - self.decay)

                        if self.bar_values[i] > self.peak_values[i]:
                            self.peak_values[i] = self.bar_values[i]
                        else:
                            self.peak_values[i] = max(self.bar_values[i], self.peak_values[i] * self.peak_decay)
            self.update()
        except Exception:
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        if w <= 30 or h <= 30:
            return

        painter.setBrush(QBrush(QColor("#111214")))
        painter.setPen(QPen(QColor("#232428"), 1))
        painter.drawRoundedRect(0, 0, w, h, 6, 6)

        margin_x = 12
        margin_y = 10
        usable_w = w - 2 * margin_x
        usable_h = h - 2 * margin_y

        total_gaps = (self.num_bars - 1) * 3
        bar_w = max(2.0, (usable_w - total_gaps) / float(self.num_bars))

        for i in range(self.num_bars):
            x = margin_x + i * (bar_w + 3.0)
            norm_h = max(0.0, min(1.0, float(self.bar_values[i])))
            bar_h = norm_h * usable_h
            bar_y = (h - margin_y) - bar_h

            grad = QLinearGradient(x, h - margin_y, x, margin_y)
            grad.setColorAt(0.0, QColor("#5865F2"))
            grad.setColorAt(0.55, QColor("#23A55A"))
            grad.setColorAt(0.85, QColor("#F0B232"))
            grad.setColorAt(1.0, QColor("#F23F43"))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, bar_y, bar_w, max(2.0, bar_h), 2.0, 2.0)

            peak_norm = max(0.0, min(1.0, float(self.peak_values[i])))
            peak_y = (h - margin_y) - (peak_norm * usable_h) - 2.0
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawRoundedRect(x, max(float(margin_y), peak_y), bar_w, 2.0, 1.0, 1.0)

        if len(self.recent_wave) > 1:
            mid_y = h / 2.0
            wave_scale = usable_h * 0.35
            step_x = usable_w / float(len(self.recent_wave) - 1)

            wave_path = QPainterPath()
            wave_path.moveTo(margin_x, mid_y - float(self.recent_wave[0]) * wave_scale)
            for i in range(1, len(self.recent_wave)):
                wx = margin_x + i * step_x
                wy = mid_y - float(self.recent_wave[i]) * wave_scale
                wave_path.lineTo(wx, wy)

            wave_pen = QPen(QColor(255, 255, 255, 120), 1.5)
            painter.strokePath(wave_path, wave_pen)


class SignalBridge(QObject):
    error_signal = Signal(str)
    driver_status_signal = Signal(str)
    driver_finished_signal = Signal(bool, str)


class DriverInstallDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Installing Virtual Audio Driver")
        self.setFixedSize(440, 170)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.title_lbl = QLabel("Setting up VB-Audio Virtual Cable...")
        self.title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f2f3f5;")
        layout.addWidget(self.title_lbl)

        self.status_lbl = QLabel("Initializing download...")
        self.status_lbl.setStyleSheet("font-size: 12px; color: #949ba4;")
        layout.addWidget(self.status_lbl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)

        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close)

    def set_status(self, msg: str, finished: bool = False, success: bool = True):
        self.status_lbl.setText(msg)
        if finished:
            self.progress.setRange(0, 100)
            self.progress.setValue(100 if success else 0)
            self.title_lbl.setText("Installation Finished" if success else "Installation Failed")
            self.btn_close.setEnabled(True)


class MainWindow(QMainWindow):
    def __init__(self, splash=None):
        super().__init__()
        self.splash = splash
        self.setWindowTitle("Desktop Audio to Mic")
        self.resize(1040, 690)
        self.setMinimumSize(980, 640)

        if self.splash:
            self.splash.set_progress(25, "Initializing audio streaming engine...")

        self.bridge = SignalBridge()
        self.bridge.error_signal.connect(self._show_error)
        self.bridge.driver_status_signal.connect(self._update_driver_status)
        self.bridge.driver_finished_signal.connect(self._on_driver_finished)

        self.dm = DeviceManager()
        self.engine = AudioEngine(on_error=self.bridge.error_signal.emit)
        self.config = load_config()

        # Load persisted DSP / UI configurations
        self.current_theme = self.config.get("theme", "dark")
        self.eq_bands = list(self.config.get("eq_bands", [0.0] * 7))
        self.troll_mode = bool(self.config.get("troll_mode", False))
        self.troll_bass = float(self.config.get("troll_bass", 28.0))
        self.troll_drive = float(self.config.get("troll_drive", 3.5))
        self.active_profile = self.config.get("active_profile", "full_desktop")

        # Sync DSP state to engine
        self.engine.set_eq_bands(self.eq_bands)
        self.engine.set_troll_mode(self.troll_mode, self.troll_bass, self.troll_drive)

        if self.splash:
            self.splash.set_progress(50, "Loading multi-page user interface...")

        self._init_ui()
        self._init_tray()

        if self.splash:
            self.splash.set_progress(75, "Scanning Windows audio endpoints...")

        self._load_devices()

        if self.splash:
            self.splash.set_progress(90, "Applying configuration & checking updates...")

        self._apply_config()
        self._refresh_windows_default_input_label()

        # Startup update check
        if self.config.get("check_updates", True):
            self._start_update_check(silent=True)

        # Timer for live VU meter and Audio Visualizer animation (~30 FPS)
        self.meter_timer = QTimer(self)
        self.meter_timer.timeout.connect(self._update_meters)
        self.meter_timer.start(33)

    def _init_ui(self):
        self._apply_theme(self.current_theme)

        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root = QVBoxLayout(central_widget)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(8)

        # ----------------- 1. HEADER & TOP NAV BAR -----------------
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_v = QVBoxLayout(header_card)
        header_v.setContentsMargins(16, 8, 16, 8)
        header_v.setSpacing(8)

        # Row 1: Title, Subtitle, Status, Stream Toggle
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        t_row = QHBoxLayout()
        title = QLabel("🎙️ Desktop Audio to Mic")
        title.setProperty("class", "title")
        self.ver_lbl = QLabel(f"v{CURRENT_VERSION}")
        self.ver_lbl.setStyleSheet("color: #5865f2; font-size: 11px; font-weight: bold; background: rgba(88, 101, 242, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(88, 101, 242, 0.4);")
        t_row.addWidget(title)
        t_row.addWidget(self.ver_lbl)
        t_row.addStretch()
        t_col.addLayout(t_row)

        sub = QLabel("Stream your PC audio directly into Discord with uncompressed studio-grade fidelity")
        sub.setProperty("class", "subtitle")
        t_col.addWidget(sub)
        top_row.addLayout(t_col)

        top_row.addStretch()

        self.status_pill = QLabel("● OFFLINE")
        self.status_pill.setStyleSheet("""
            background-color: #383a40;
            color: #949ba4;
            padding: 6px 14px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
        """)
        top_row.addWidget(self.status_pill)

        self.btn_toggle_stream = QPushButton("▶  START STREAMING TO DISCORD")
        self.btn_toggle_stream.setProperty("class", "primary")
        self.btn_toggle_stream.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_stream.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
        """)
        self.btn_toggle_stream.clicked.connect(self._toggle_stream)
        top_row.addWidget(self.btn_toggle_stream)
        header_v.addLayout(top_row)

        # Row 2: Navigation Bar Tabs (Full width, spacious!)
        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)

        self.btn_nav_studio = QPushButton("🎙️  Studio Dashboard")
        self.btn_nav_profiles = QPushButton("🎛️  App Profiles & Routing")
        self.btn_nav_eq = QPushButton("🎚️  7-Band Equalizer & Troll Mode")
        self.btn_nav_settings = QPushButton("⚙️  Settings & Updates")

        self.nav_buttons = [
            self.btn_nav_studio,
            self.btn_nav_profiles,
            self.btn_nav_eq,
            self.btn_nav_settings
        ]

        for idx, btn in enumerate(self.nav_buttons):
            btn.setProperty("class", "nav_tab")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            btn.clicked.connect(lambda checked=False, i=idx: self._switch_page(i))
            nav_row.addWidget(btn, 1)

        self.btn_nav_studio.setChecked(True)
        header_v.addLayout(nav_row)
        root.addWidget(header_card)

        # ----------------- 2. MULTI-PAGE STACKED CONTAINER -----------------
        self.stack = QStackedWidget()
        self.page_studio = self._create_studio_page()
        self.page_profiles = self._create_profiles_page()
        self.page_eq = self._create_eq_page()
        self.page_settings = self._create_settings_page()

        self.stack.addWidget(self.page_studio)
        self.stack.addWidget(self.page_profiles)
        self.stack.addWidget(self.page_eq)
        self.stack.addWidget(self.page_settings)

        root.addWidget(self.stack, 1)

        # ----------------- 3. FOOTER BAR -----------------
        foot = QHBoxLayout()
        foot.setContentsMargins(4, 0, 4, 0)
        self.switch_tray = ToggleSwitch("Minimize to System Tray on close")
        self.switch_tray.setChecked(self.config.get("minimize_to_tray", False))
        self.switch_tray.toggled.connect(self._save_current_config)
        foot.addWidget(self.switch_tray)

        self.lbl_install_status = QLabel("")
        self.lbl_install_status.setStyleSheet("color: #23a55a; font-size: 11px; font-weight: bold; margin-left: 12px;")
        foot.addWidget(self.lbl_install_status)

        foot.addStretch()
        foot_hint = QLabel("Low-Latency Audio Streamer • 48 kHz Stereo")
        foot_hint.setStyleSheet("color: #949ba4; font-size: 11px;")
        foot.addWidget(foot_hint)
        root.addLayout(foot)

    # =========================================================================
    # PAGE CREATORS
    # =========================================================================

    def _create_studio_page(self) -> QWidget:
        """Page 0: Main Studio Dashboard with live mixing channels and visualizer."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        grid = QHBoxLayout()
        grid.setSpacing(10)

        # === LEFT COLUMN: AUDIO INPUTS & MIXER ===
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        # Card 1: Desktop Channel
        c1 = QFrame()
        c1.setProperty("class", "card")
        c1_v = QVBoxLayout(c1)
        c1_v.setContentsMargins(14, 10, 14, 10)
        c1_v.setSpacing(6)

        head_row1 = QHBoxLayout()
        head_row1.addWidget(QLabel("🖥️  Desktop Audio Capture"))
        badge1 = QLabel("WASAPI LOOPBACK")
        badge1.setStyleSheet("background: rgba(88, 101, 242, 0.15); color: #5865f2; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(88, 101, 242, 0.4);")
        head_row1.addWidget(badge1)
        head_row1.addStretch()
        c1_v.addLayout(head_row1)

        self.combo_desktop_source = QComboBox()
        self.combo_desktop = self.combo_desktop_source
        self.combo_desktop_source.currentIndexChanged.connect(self._save_current_config)
        c1_v.addWidget(self.combo_desktop_source)

        v_row1 = QHBoxLayout()
        v_row1.setSpacing(10)
        self.slider_desktop_vol = GradientSlider(Qt.Horizontal)
        self.slider_desktop_vol.setRange(0, 200)
        self.slider_desktop_vol.setValue(100)
        self.slider_desktop_vol.valueChanged.connect(self._on_desktop_vol_changed)
        v_row1.addWidget(self.slider_desktop_vol, 1)

        self.lbl_desktop_vol = QLabel("100%")
        self.lbl_desktop_vol.setFixedWidth(44)
        self.lbl_desktop_vol.setStyleSheet("font-size: 12px; font-weight: bold; color: #23a55a;")
        v_row1.addWidget(self.lbl_desktop_vol)

        self.btn_desktop_mute = QPushButton("Mute")
        self.btn_desktop_mute.setProperty("class", "ghost")
        self.btn_desktop_mute.setFixedWidth(54)
        self.btn_desktop_mute.setCheckable(True)
        self.btn_desktop_mute.clicked.connect(self._on_desktop_mute_toggled)
        v_row1.addWidget(self.btn_desktop_mute)
        c1_v.addLayout(v_row1)

        meter_box1 = QHBoxLayout()
        meter_box1.setSpacing(8)
        lbl_m1 = QLabel("Level")
        lbl_m1.setStyleSheet("font-size: 11px; color: #949ba4;")
        meter_box1.addWidget(lbl_m1)
        self.meter_desktop = LiveVUMeter()
        meter_box1.addWidget(self.meter_desktop, 1)
        c1_v.addLayout(meter_box1)
        left_col.addWidget(c1)

        # Card 2: Voice Microphone Channel
        c2 = QFrame()
        c2.setProperty("class", "card")
        c2_v = QVBoxLayout(c2)
        c2_v.setContentsMargins(14, 10, 14, 10)
        c2_v.setSpacing(6)

        head_row2 = QHBoxLayout()
        head_row2.addWidget(QLabel("🎤  Voice Microphone (Optional)"))
        head_row2.addStretch()
        self.switch_mix_mic = ToggleSwitch("Mix Mic into Stream")
        self.switch_mix_mic.toggled.connect(self._on_mix_mic_toggled)
        head_row2.addWidget(self.switch_mix_mic)
        c2_v.addLayout(head_row2)

        self.combo_real_mic = QComboBox()
        self.combo_mic = self.combo_real_mic
        self.combo_real_mic.currentIndexChanged.connect(self._save_current_config)
        c2_v.addWidget(self.combo_real_mic)

        v_row2 = QHBoxLayout()
        v_row2.setSpacing(10)
        self.slider_mic_vol = GradientSlider(Qt.Horizontal)
        self.slider_mic_vol.setRange(0, 200)
        self.slider_mic_vol.setValue(100)
        self.slider_mic_vol.valueChanged.connect(self._on_mic_vol_changed)
        v_row2.addWidget(self.slider_mic_vol, 1)

        self.lbl_mic_vol = QLabel("100%")
        self.lbl_mic_vol.setFixedWidth(44)
        self.lbl_mic_vol.setStyleSheet("font-size: 12px; font-weight: bold; color: #23a55a;")
        v_row2.addWidget(self.lbl_mic_vol)

        self.btn_mic_mute = QPushButton("Mute")
        self.btn_mic_mute.setProperty("class", "ghost")
        self.btn_mic_mute.setFixedWidth(54)
        self.btn_mic_mute.setCheckable(True)
        self.btn_mic_mute.clicked.connect(self._on_mic_mute_toggled)
        v_row2.addWidget(self.btn_mic_mute)
        c2_v.addLayout(v_row2)

        meter_box2 = QHBoxLayout()
        meter_box2.setSpacing(8)
        lbl_m2 = QLabel("Level")
        lbl_m2.setStyleSheet("font-size: 11px; color: #949ba4;")
        meter_box2.addWidget(lbl_m2)
        self.meter_mic = LiveVUMeter()
        meter_box2.addWidget(self.meter_mic, 1)
        c2_v.addLayout(meter_box2)
        left_col.addWidget(c2)

        grid.addLayout(left_col, 1)

        # === RIGHT COLUMN: OUTPUT TARGET & DISCORD SETUP ===
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        # Card 3: Virtual Microphone Target
        c3 = QFrame()
        c3.setProperty("class", "card")
        c3_v = QVBoxLayout(c3)
        c3_v.setContentsMargins(14, 10, 14, 10)
        c3_v.setSpacing(6)

        head_row3 = QHBoxLayout()
        head_row3.addWidget(QLabel("🎯  Discord Virtual Microphone Target"))
        badge3 = QLabel("TRANSMIT")
        badge3.setStyleSheet("background: rgba(35, 165, 90, 0.15); color: #23a55a; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(35, 165, 90, 0.4);")
        head_row3.addWidget(badge3)
        head_row3.addStretch()
        c3_v.addLayout(head_row3)

        self.combo_target_mic = QComboBox()
        self.combo_target = self.combo_target_mic
        self.combo_target_mic.currentIndexChanged.connect(self._save_current_config)
        c3_v.addWidget(self.combo_target_mic)

        r3_sub = QHBoxLayout()
        r3_sub.setSpacing(8)
        self.lbl_target_status = QLabel("Select SteelSeries Sonar - Microphone or CABLE Input")
        self.lbl_target_status.setStyleSheet("color: #949ba4; font-size: 11px;")
        r3_sub.addWidget(self.lbl_target_status, 1)

        self.btn_refresh = QPushButton("🔄 Refresh Devices")
        self.btn_refresh.setProperty("class", "ghost")
        self.btn_refresh.clicked.connect(self._load_devices)
        r3_sub.addWidget(self.btn_refresh)

        self.btn_install_vbcable = QPushButton("📦 Install VB-Cable")
        self.btn_install_vbcable.setProperty("class", "ghost")
        self.btn_install_vbcable.clicked.connect(self._install_vbcable_driver)
        r3_sub.addWidget(self.btn_install_vbcable)
        c3_v.addLayout(r3_sub)
        right_col.addWidget(c3)

        # Card 4: Discord Setup Guide
        c4 = QFrame()
        c4.setProperty("class", "card")
        c4_v = QVBoxLayout(c4)
        c4_v.setContentsMargins(14, 8, 14, 8)
        c4_v.setSpacing(4)

        g_title = QLabel("🎧  Discord Setup Guide")
        g_title.setStyleSheet("font-weight: bold; color: #5865f2; font-size: 13px;")
        c4_v.addWidget(g_title)

        guide_txt = QLabel(
            "1. In Discord, go to <b>User Settings ⚙️ → Voice & Video</b>.<br>"
            "2. Set <b>Input Device</b> to match your selected Target Virtual Microphone above.<br>"
            "3. Change <b>Audio Profile</b> to <b>Studio</b> (transmits full-fidelity stereo without Krisp filter cutoff)."
        )
        guide_txt.setStyleSheet("color: #dbdee1; font-size: 11px; line-height: 1.3;")
        c4_v.addWidget(guide_txt)
        right_col.addWidget(c4)

        # Card 5: Windows Default Recording Endpoint
        c5 = QFrame()
        c5.setProperty("class", "card")
        c5_v = QVBoxLayout(c5)
        c5_v.setContentsMargins(14, 8, 14, 8)
        c5_v.setSpacing(4)

        w_title = QLabel("🌐  Windows System-Wide Default Input Device")
        w_title.setStyleSheet("font-weight: bold; color: #f2f3f5; font-size: 12px;")
        c5_v.addWidget(w_title)

        self.lbl_windows_default = QLabel("Current Windows Default Input: Detecting...")
        self.lbl_windows_default.setStyleSheet("color: #949ba4; font-size: 11px;")
        c5_v.addWidget(self.lbl_windows_default)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_set_default = QPushButton("Set Target as Default")
        self.btn_set_default.setProperty("class", "ghost")
        self.btn_set_default.clicked.connect(self._set_as_windows_default_input)
        btn_row.addWidget(self.btn_set_default)

        self.btn_restore_default = QPushButton("Restore Headset Mic")
        self.btn_restore_default.setProperty("class", "ghost")
        self.btn_restore_default.clicked.connect(self._restore_headset_mic_as_windows_default)
        btn_row.addWidget(self.btn_restore_default)

        self.btn_open_sound = QPushButton("Sound Settings")
        self.btn_open_sound.setProperty("class", "ghost")
        self.btn_open_sound.clicked.connect(self._open_sound_control_panel)
        btn_row.addWidget(self.btn_open_sound)
        c5_v.addLayout(btn_row)
        right_col.addWidget(c5)

        grid.addLayout(right_col, 1)
        layout.addLayout(grid)

        # Bottom Visualizer Dock
        vis_card = QFrame()
        vis_card.setProperty("class", "card")
        vis_l = QVBoxLayout(vis_card)
        vis_l.setContentsMargins(14, 8, 14, 8)
        vis_l.setSpacing(4)

        vis_header = QHBoxLayout()
        vis_header.addWidget(QLabel("📊  Real-Time Studio Equalizer Spectrum & Oscilloscope Waveform"))
        vis_header.addStretch()
        lbl_out_meter = QLabel("Master Output")
        lbl_out_meter.setStyleSheet("font-size: 11px; color: #949ba4;")
        vis_header.addWidget(lbl_out_meter)
        self.meter_out = LiveVUMeter()
        self.meter_out.setFixedWidth(120)
        vis_header.addWidget(self.meter_out)
        vis_l.addLayout(vis_header)

        self.visualizer = AudioVisualizer()
        vis_l.addWidget(self.visualizer)
        layout.addWidget(vis_card)

        return page

    def _create_profiles_page(self) -> QWidget:
        """Page 1: App Routing & Audio Profiles (Firefox / per-app streaming & solo)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Profile selection card
        prof_card = QFrame()
        prof_card.setProperty("class", "card")
        pc_l = QVBoxLayout(prof_card)
        pc_l.setContentsMargins(16, 12, 16, 12)
        pc_l.setSpacing(8)

        p_title = QLabel("🎛️  Audio Routing Profiles")
        p_title.setProperty("class", "title")
        pc_l.addWidget(p_title)

        p_desc = QLabel("Quickly isolate or stream specific applications (e.g., stream Firefox exclusively without game or discord sound).")
        p_desc.setProperty("class", "subtitle")
        pc_l.addWidget(p_desc)

        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(10)

        self.btn_prof_full = QPushButton("🌐  Full Desktop Sound")
        self.btn_prof_browser = QPushButton("🦊  Browser Only (Firefox / Chrome)")
        self.btn_prof_game = QPushButton("🎮  Game Sound Focus")
        self.btn_prof_custom = QPushButton("🎧  Custom Filter")

        self.profile_buttons = {
            "full_desktop": self.btn_prof_full,
            "browser": self.btn_prof_browser,
            "game": self.btn_prof_game,
            "custom": self.btn_prof_custom
        }

        for key, btn in self.profile_buttons.items():
            btn.setProperty("class", "secondary")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self._set_active_profile(k))
            btn_grid.addWidget(btn)

        self._update_profile_button_ui()
        pc_l.addLayout(btn_grid)
        layout.addWidget(prof_card)

        # Active Applications Mixer
        app_card = QFrame()
        app_card.setProperty("class", "card")
        ac_l = QVBoxLayout(app_card)
        ac_l.setContentsMargins(16, 12, 16, 12)
        ac_l.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("📱  Active Applications Mixer (Windows Core Audio Sessions)"))
        top_row.addStretch()

        btn_refresh_apps = QPushButton("🔄 Refresh Apps")
        btn_refresh_apps.setProperty("class", "ghost")
        btn_refresh_apps.clicked.connect(self._refresh_app_sessions)
        top_row.addWidget(btn_refresh_apps)

        btn_unmute_all = QPushButton("🔊 Unmute All Apps")
        btn_unmute_all.setProperty("class", "ghost")
        btn_unmute_all.clicked.connect(self._unmute_all_apps)
        top_row.addWidget(btn_unmute_all)
        ac_l.addLayout(top_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.session_container = QWidget()
        self.session_layout = QVBoxLayout(self.session_container)
        self.session_layout.setContentsMargins(0, 0, 0, 0)
        self.session_layout.setSpacing(6)
        scroll.setWidget(self.session_container)
        scroll.setMinimumHeight(180)
        ac_l.addWidget(scroll, 1)
        layout.addWidget(app_card, 1)

        # Windows Routing Assistant Card
        guide_card = QFrame()
        guide_card.setProperty("class", "card")
        gc_l = QHBoxLayout(guide_card)
        gc_l.setContentsMargins(16, 12, 16, 12)

        g_info = QVBoxLayout()
        g_info.setSpacing(2)
        g_info_title = QLabel("💡 Direct Per-App Windows Routing")
        g_info_title.setStyleSheet("font-weight: bold; color: #f2f3f5; font-size: 13px;")
        g_info.addWidget(g_info_title)
        g_info_txt = QLabel("To route Firefox or a game permanently to your virtual stream cable, open Windows App Volume Preferences and set its Output Device directly.")
        g_info_txt.setStyleSheet("color: #949ba4; font-size: 11px;")
        g_info.addWidget(g_info_txt)
        gc_l.addLayout(g_info, 1)

        btn_open_app_routing = QPushButton("🎛️ Open Windows App Volume Mixer")
        btn_open_app_routing.setProperty("class", "primary")
        btn_open_app_routing.clicked.connect(open_windows_app_volume_settings)
        gc_l.addWidget(btn_open_app_routing)
        layout.addWidget(guide_card)

        # Initial load of sessions
        QTimer.singleShot(200, self._refresh_app_sessions)
        return page

    def _create_eq_page(self) -> QWidget:
        """Page 2: 7-Band Graphic Equalizer and Troll Mode (Insanely Bass Boosted)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 7-Band Studio Equalizer Card
        eq_card = QFrame()
        eq_card.setProperty("class", "card")
        eq_l = QVBoxLayout(eq_card)
        eq_l.setContentsMargins(16, 12, 16, 12)
        eq_l.setSpacing(10)

        eq_top = QHBoxLayout()
        eq_title = QLabel("🎚️  7-Band Studio Graphic Equalizer")
        eq_title.setProperty("class", "title")
        eq_top.addWidget(eq_title)
        eq_top.addStretch()

        # Presets
        lbl_pre = QLabel("Presets:")
        lbl_pre.setStyleSheet("color: #949ba4; font-size: 12px;")
        eq_top.addWidget(lbl_pre)

        presets = [
            ("Flat", [0, 0, 0, 0, 0, 0, 0]),
            ("Bass Boost", [6, 4, 1, 0, 0, 1, 2]),
            ("Vocal Clarity", [-3, -1, 2, 4, 3, 1, 0]),
            ("Podcast Warmth", [2, 3, 1, 0, 2, 1, 0]),
            ("Bright Treble", [-2, -1, 0, 1, 3, 5, 6]),
        ]
        for name, values in presets:
            btn_pre = QPushButton(name)
            btn_pre.setProperty("class", "ghost")
            btn_pre.setCursor(Qt.PointingHandCursor)
            btn_pre.clicked.connect(lambda checked=False, v=values: self._apply_eq_preset(v))
            eq_top.addWidget(btn_pre)

        btn_reset_eq = QPushButton("Reset EQ")
        btn_reset_eq.setProperty("class", "ghost")
        btn_reset_eq.clicked.connect(lambda: self._apply_eq_preset([0, 0, 0, 0, 0, 0, 0]))
        eq_top.addWidget(btn_reset_eq)
        eq_l.addLayout(eq_top)

        # Vertical Sliders Row
        sliders_row = QHBoxLayout()
        sliders_row.setSpacing(18)

        self.eq_sliders = []
        self.eq_val_labels = []
        labels = ["60 Hz\n(Sub)", "150 Hz\n(Bass)", "400 Hz\n(Low Mid)", "1 kHz\n(Mids)", "2.5 kHz\n(Pres)", "6 kHz\n(High)", "15 kHz\n(Air)"]

        for i in range(7):
            band_v = QVBoxLayout()
            band_v.setSpacing(4)
            band_v.setAlignment(Qt.AlignCenter)

            val_lbl = QLabel("0 dB")
            val_lbl.setAlignment(Qt.AlignCenter)
            val_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #5865f2;")
            self.eq_val_labels.append(val_lbl)
            band_v.addWidget(val_lbl)

            slider = GradientSlider(Qt.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(int(self.eq_bands[i]))
            slider.setFixedHeight(120)
            slider.setCursor(Qt.PointingHandCursor)
            slider.valueChanged.connect(self._on_eq_slider_changed)
            self.eq_sliders.append(slider)
            band_v.addWidget(slider, 1, Qt.AlignCenter)

            f_lbl = QLabel(labels[i])
            f_lbl.setAlignment(Qt.AlignCenter)
            f_lbl.setStyleSheet("font-size: 11px; color: #949ba4;")
            band_v.addWidget(f_lbl)

            sliders_row.addLayout(band_v)

        eq_l.addLayout(sliders_row)
        self._update_eq_labels()
        layout.addWidget(eq_card)

        # ----------------- "TROLL" MODE CARD -----------------
        troll_card = QFrame()
        troll_card.setProperty("class", "hazard_card")
        tc_l = QVBoxLayout(troll_card)
        tc_l.setContentsMargins(16, 12, 16, 12)
        tc_l.setSpacing(8)

        t_head = QHBoxLayout()
        t_head.addWidget(QLabel("👹  TROLL MODE — INSANELY BASS BOOSTED (EARRAPE / MEME STREAMING)"))
        t_head.addStretch()

        self.switch_troll = ToggleSwitch("ACTIVATE TROLL MODE")
        self.switch_troll.setChecked(self.troll_mode)
        self.switch_troll.toggled.connect(self._on_troll_mode_toggled)
        t_head.addWidget(self.switch_troll)
        tc_l.addLayout(t_head)

        t_desc = QLabel("Injects extreme sub-bass boost (+28 dB) with analog soft-saturation overdrive for hilarious blown-out speaker sound. Built-in brickwall limiter guarantees zero driver crashes.")
        t_desc.setStyleSheet("color: #f87171; font-size: 11px;")
        tc_l.addWidget(t_desc)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(16)

        # Bass intensity
        bass_box = QVBoxLayout()
        bass_box.setSpacing(2)
        self.lbl_troll_bass = QLabel(f"Sub-Bass Overdrive: +{int(self.troll_bass)} dB")
        self.lbl_troll_bass.setStyleSheet("font-size: 11px; font-weight: bold; color: #f2f3f5;")
        bass_box.addWidget(self.lbl_troll_bass)

        self.slider_troll_bass = GradientSlider(Qt.Horizontal)
        self.slider_troll_bass.setRange(10, 40)
        self.slider_troll_bass.setValue(int(self.troll_bass))
        self.slider_troll_bass.valueChanged.connect(self._on_troll_params_changed)
        bass_box.addWidget(self.slider_troll_bass)
        ctrl_row.addLayout(bass_box, 1)

        # Saturation Crunch
        crunch_box = QVBoxLayout()
        crunch_box.setSpacing(2)
        self.lbl_troll_drive = QLabel(f"Saturation Crunch: {self.troll_drive:.1f}x")
        self.lbl_troll_drive.setStyleSheet("font-size: 11px; font-weight: bold; color: #f2f3f5;")
        crunch_box.addWidget(self.lbl_troll_drive)

        self.slider_troll_drive = GradientSlider(Qt.Horizontal)
        self.slider_troll_drive.setRange(10, 80)
        self.slider_troll_drive.setValue(int(self.troll_drive * 10))
        self.slider_troll_drive.valueChanged.connect(self._on_troll_params_changed)
        crunch_box.addWidget(self.slider_troll_drive)
        ctrl_row.addLayout(crunch_box, 1)

        tc_l.addLayout(ctrl_row)

        self.lbl_troll_status = QLabel("● TROLL MODE ACTIVE: Extreme bass overdrive transmitting" if self.troll_mode else "○ Troll Mode Disabled")
        self.lbl_troll_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;" if self.troll_mode else "color: #949ba4; font-size: 11px;")
        tc_l.addWidget(self.lbl_troll_status)

        layout.addWidget(troll_card)
        return page

    def _create_settings_page(self) -> QWidget:
        """Page 3: Theme selection (Light/Dark), startup GitHub version checking, and preferences."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Appearance & Theme Card
        theme_card = QFrame()
        theme_card.setProperty("class", "card")
        tc_l = QVBoxLayout(theme_card)
        tc_l.setContentsMargins(16, 12, 16, 12)
        tc_l.setSpacing(8)

        t_title = QLabel("🎨  Appearance & Theme")
        t_title.setProperty("class", "title")
        tc_l.addWidget(t_title)

        th_row = QHBoxLayout()
        th_row.setSpacing(20)

        self.rb_dark = QRadioButton("🌙  Dark Theme (Discord Dark)")
        self.rb_light = QRadioButton("☀️  Light Theme (Modern Studio Light)")

        if self.current_theme == "light":
            self.rb_light.setChecked(True)
        else:
            self.rb_dark.setChecked(True)

        self.theme_group = QButtonGroup(self)
        self.theme_group.addButton(self.rb_dark)
        self.theme_group.addButton(self.rb_light)

        self.rb_dark.toggled.connect(lambda checked: self._apply_theme("dark") if checked else None)
        self.rb_light.toggled.connect(lambda checked: self._apply_theme("light") if checked else None)

        th_row.addWidget(self.rb_dark)
        th_row.addWidget(self.rb_light)
        th_row.addStretch()
        tc_l.addLayout(th_row)
        layout.addWidget(theme_card)

        # 2. Version & Updates Card
        up_card = QFrame()
        up_card.setProperty("class", "card")
        uc_l = QVBoxLayout(up_card)
        uc_l.setContentsMargins(16, 12, 16, 12)
        uc_l.setSpacing(8)

        u_title = QLabel("🚀  Version & GitHub Updates")
        u_title.setProperty("class", "title")
        uc_l.addWidget(u_title)

        u_row = QHBoxLayout()
        u_row.addWidget(QLabel(f"Installed Version: <b>v{CURRENT_VERSION}</b>"))
        u_row.addStretch()

        self.switch_auto_update = ToggleSwitch("Check for updates on startup")
        self.switch_auto_update.setChecked(self.config.get("check_updates", True))
        self.switch_auto_update.toggled.connect(self._on_auto_update_toggled)
        u_row.addWidget(self.switch_auto_update)
        uc_l.addLayout(u_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.btn_check_now = QPushButton("🔄 Check for Updates Now")
        self.btn_check_now.setProperty("class", "primary")
        self.btn_check_now.clicked.connect(lambda: self._start_update_check(silent=False))
        action_row.addWidget(self.btn_check_now)

        self.lbl_update_status = QLabel("Ready to check GitHub")
        self.lbl_update_status.setStyleSheet("color: #949ba4; font-size: 12px;")
        action_row.addWidget(self.lbl_update_status, 1)

        self.btn_download_update = QPushButton("⬇️ Download Update")
        self.btn_download_update.setProperty("class", "secondary")
        self.btn_download_update.setVisible(False)
        self.btn_download_update.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(RELEASES_URL)))
        action_row.addWidget(self.btn_download_update)
        uc_l.addLayout(action_row)
        layout.addWidget(up_card)

        # 3. Preferences Card
        pref_card = QFrame()
        pref_card.setProperty("class", "card")
        pr_l = QVBoxLayout(pref_card)
        pr_l.setContentsMargins(16, 12, 16, 12)
        pr_l.setSpacing(8)

        p_title = QLabel("⚙️  Application Preferences")
        p_title.setProperty("class", "title")
        pr_l.addWidget(p_title)

        p_row1 = QHBoxLayout()
        self.switch_auto_start = ToggleSwitch("Automatically start streaming on launch")
        self.switch_auto_start.setChecked(self.config.get("auto_start", False))
        self.switch_auto_start.toggled.connect(self._save_current_config)
        p_row1.addWidget(self.switch_auto_start)
        p_row1.addStretch()
        pr_l.addLayout(p_row1)
        layout.addWidget(pref_card)

        # 4. About & Diagnostics Card
        about_card = QFrame()
        about_card.setProperty("class", "card")
        ab_l = QVBoxLayout(about_card)
        ab_l.setContentsMargins(16, 12, 16, 12)
        ab_l.setSpacing(8)

        ab_title = QLabel("ℹ️  About & Diagnostics")
        ab_title.setProperty("class", "title")
        ab_l.addWidget(ab_title)

        ab_row = QHBoxLayout()
        ab_row.setSpacing(10)

        btn_open_crash = QPushButton("📄 View Crash Log")
        btn_open_crash.setProperty("class", "ghost")
        btn_open_crash.clicked.connect(self._open_crash_log)
        ab_row.addWidget(btn_open_crash)

        btn_github = QPushButton("🌐 GitHub Repository")
        btn_github.setProperty("class", "ghost")
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/Sooeeren/desktop-audio-to-mic")))
        ab_row.addWidget(btn_github)

        btn_releases = QPushButton("📦 Release Notes")
        btn_releases.setProperty("class", "ghost")
        btn_releases.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(RELEASES_URL)))
        ab_row.addWidget(btn_releases)

        ab_row.addStretch()
        ab_l.addLayout(ab_row)
        layout.addWidget(about_card)

        layout.addStretch()
        return page

    # =========================================================================
    # NAVIGATION & THEMES
    # =========================================================================

    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        self.config["theme"] = theme_name
        save_config(self.config)

        if theme_name == "light":
            self.setStyleSheet(LIGHT_STYLE)
        else:
            self.setStyleSheet(DARK_STYLE)

    # =========================================================================
    # AUDIO PROFILES & SESSION MIXER
    # =========================================================================

    def _set_active_profile(self, profile_key: str):
        self.active_profile = profile_key
        self.config["active_profile"] = profile_key
        save_config(self.config)
        self._update_profile_button_ui()

        if profile_key == "full_desktop":
            unmute_all_sessions()
            self._refresh_app_sessions()
        elif profile_key == "browser":
            # Auto-solo firefox/chrome
            sessions = get_active_audio_sessions()
            target = next((s for s in sessions if "firefox" in s["name"].lower() or "chrome" in s["name"].lower()), None)
            if target:
                solo_session(target["pid"])
                self._refresh_app_sessions()
            else:
                QMessageBox.information(self, "Browser Profile", "No active browser audio detected. Start playing sound in Firefox or Chrome, then click Refresh.")

    def _update_profile_button_ui(self):
        for key, btn in self.profile_buttons.items():
            btn.setChecked(key == self.active_profile)

    def _refresh_app_sessions(self):
        # Clear existing rows
        while self.session_layout.count():
            item = self.session_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        sessions = get_active_audio_sessions()
        if not sessions:
            empty_lbl = QLabel("No active audio applications detected. Play audio in Firefox, Spotify, or a game to see them here.")
            empty_lbl.setStyleSheet("color: #949ba4; font-style: italic; padding: 10px;")
            self.session_layout.addWidget(empty_lbl)
            return

        for s in sessions:
            row_card = QFrame()
            row_card.setProperty("class", "card")
            row_card.setStyleSheet("background-color: #1e1f22; border-radius: 6px; padding: 4px;")
            rl = QHBoxLayout(row_card)
            rl.setContentsMargins(10, 4, 10, 4)
            rl.setSpacing(10)

            # Icon/Name
            name_lbl = QLabel(f"<b>{s['display_name']}</b> <span style='color: #949ba4;'>({s['name']} - PID {s['pid']})</span>")
            name_lbl.setMinimumWidth(180)
            rl.addWidget(name_lbl)

            # Volume slider
            slider = GradientSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(int(s['volume'] * 100))
            slider.setFixedWidth(140)
            slider.setCursor(Qt.PointingHandCursor)

            vol_lbl = QLabel(f"{int(s['volume'] * 100)}%")
            vol_lbl.setFixedWidth(36)
            vol_lbl.setStyleSheet("color: #23a55a; font-weight: bold;")

            slider.valueChanged.connect(lambda v, p=s['pid'], l=vol_lbl: (
                set_session_volume(p, v / 100.0),
                l.setText(f"{v}%")
            ))
            rl.addWidget(slider)
            rl.addWidget(vol_lbl)

            # Mute button
            btn_mute = QPushButton("Unmute" if s['muted'] else "Mute")
            btn_mute.setProperty("class", "ghost")
            btn_mute.setFixedWidth(60)
            btn_mute.setCheckable(True)
            btn_mute.setChecked(s['muted'])
            btn_mute.clicked.connect(lambda checked, p=s['pid'], b=btn_mute: (
                set_session_mute(p, checked),
                b.setText("Unmute" if checked else "Mute")
            ))
            rl.addWidget(btn_mute)

            # Solo button
            btn_solo = QPushButton("⭐ Solo")
            btn_solo.setProperty("class", "primary")
            btn_solo.setFixedWidth(65)
            btn_solo.clicked.connect(lambda checked=False, p=s['pid']: self._solo_app(p))
            rl.addWidget(btn_solo)

            self.session_layout.addWidget(row_card)

    def _solo_app(self, pid: int):
        solo_session(pid)
        self._refresh_app_sessions()

    def _unmute_all_apps(self):
        unmute_all_sessions()
        self._refresh_app_sessions()

    # =========================================================================
    # EQUALIZER & TROLL MODE
    # =========================================================================

    def _on_eq_slider_changed(self):
        new_bands = [slider.value() for slider in self.eq_sliders]
        self.eq_bands = new_bands
        self.engine.set_eq_bands(self.eq_bands)
        self.config["eq_bands"] = self.eq_bands
        save_config(self.config)
        self._update_eq_labels()

    def _update_eq_labels(self):
        for i, val in enumerate(self.eq_bands):
            prefix = "+" if val > 0 else ""
            self.eq_val_labels[i].setText(f"{prefix}{int(val)} dB")
            color = "#23a55a" if val > 0 else ("#f23f43" if val < 0 else "#5865f2")
            self.eq_val_labels[i].setStyleSheet(f"font-size: 11px; font-weight: bold; color: {color};")

    def _apply_eq_preset(self, values: list):
        for i in range(min(7, len(values))):
            self.eq_sliders[i].blockSignals(True)
            self.eq_sliders[i].setValue(int(values[i]))
            self.eq_sliders[i].blockSignals(False)
        self._on_eq_slider_changed()

    def _on_troll_mode_toggled(self, checked: bool):
        self.troll_mode = checked
        self.engine.set_troll_mode(self.troll_mode, self.troll_bass, self.troll_drive)
        self.config["troll_mode"] = self.troll_mode
        save_config(self.config)

        if self.troll_mode:
            self.lbl_troll_status.setText("● TROLL MODE ACTIVE: Extreme bass overdrive transmitting")
            self.lbl_troll_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_troll_status.setText("○ Troll Mode Disabled")
            self.lbl_troll_status.setStyleSheet("color: #949ba4; font-size: 11px;")

    def _on_troll_params_changed(self):
        self.troll_bass = float(self.slider_troll_bass.value())
        self.troll_drive = float(self.slider_troll_drive.value()) / 10.0
        self.lbl_troll_bass.setText(f"Sub-Bass Overdrive: +{int(self.troll_bass)} dB")
        self.lbl_troll_drive.setText(f"Saturation Crunch: {self.troll_drive:.1f}x")

        self.engine.set_troll_mode(self.troll_mode, self.troll_bass, self.troll_drive)
        self.config["troll_bass"] = self.troll_bass
        self.config["troll_drive"] = self.troll_drive
        save_config(self.config)

    # =========================================================================
    # UPDATER LOGIC
    # =========================================================================

    def _start_update_check(self, silent: bool = False):
        self.update_silent = silent
        if not silent:
            self.lbl_update_status.setText("Connecting to GitHub...")
            self.btn_check_now.setEnabled(False)

        self.worker = UpdateCheckWorker(timeout=3.5)
        self.worker.result_ready.connect(self._on_update_check_result)
        self.worker.start()

    def _on_update_check_result(self, has_update: bool, latest_version: str, url: str, err: str):
        self.btn_check_now.setEnabled(True)
        if has_update:
            self.lbl_update_status.setText(f"🚀 New version available: <b>v{latest_version}</b>!")
            self.lbl_update_status.setStyleSheet("color: #23a55a; font-size: 12px; font-weight: bold;")
            self.btn_download_update.setVisible(True)
            self.btn_nav_settings.setText("⚙️  Settings  🔴")
            if not self.update_silent:
                QMessageBox.information(
                    self, "Update Available",
                    f"A new version of Desktop Audio to Mic is available: v{latest_version}!\n\n"
                    f"Installed: v{CURRENT_VERSION}\nLatest: v{latest_version}\n\n"
                    "Click 'Download Update' to get the latest release from GitHub."
                )
        elif err:
            if not self.update_silent:
                self.lbl_update_status.setText(f"Could not check updates: {err}")
                self.lbl_update_status.setStyleSheet("color: #f23f43; font-size: 11px;")
        else:
            self.lbl_update_status.setText(f"✅ You are running the latest version (v{CURRENT_VERSION}).")
            self.lbl_update_status.setStyleSheet("color: #23a55a; font-size: 12px;")
            self.btn_download_update.setVisible(False)

    def _on_auto_update_toggled(self, checked: bool):
        self.config["check_updates"] = checked
        save_config(self.config)

    def _open_crash_log(self):
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "crash.log")
        if os.path.exists(log_path):
            os.system(f'notepad.exe "{log_path}"')
        else:
            QMessageBox.information(self, "Crash Log", "No crashes recorded. The crash log is empty.")

    # =========================================================================
    # AUDIO STREAMING & CONTROLS
    # =========================================================================

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        tray_menu = QMenu()

        act_show = QAction("Show Window", self)
        act_show.triggered.connect(self.showNormal)
        tray_menu.addAction(act_show)

        self.act_stream_toggle = QAction("Start Streaming", self)
        self.act_stream_toggle.triggered.connect(self._toggle_stream)
        tray_menu.addAction(self.act_stream_toggle)

        tray_menu.addSeparator()
        act_quit = QAction("Exit", self)
        act_quit.triggered.connect(self._exit_app)
        tray_menu.addAction(act_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _load_devices(self):
        self.combo_desktop_source.blockSignals(True)
        self.combo_target_mic.blockSignals(True)
        self.combo_real_mic.blockSignals(True)

        self.combo_desktop_source.clear()
        self.combo_target_mic.clear()
        self.combo_real_mic.clear()

        desktop_sources = self.dm.get_desktop_sources()
        for dev in desktop_sources:
            self.combo_desktop_source.addItem(dev["display_name"], userData=dev)

        target_mics = self.dm.get_target_microphones()
        for dev in target_mics:
            self.combo_target_mic.addItem(dev["display_name"], userData=dev)

        real_mics = self.dm.get_real_microphones()
        self.combo_real_mic.addItem("None (Do not mix real microphone)", userData=None)
        for dev in real_mics:
            self.combo_real_mic.addItem(dev["display_name"], userData=dev)

        self.combo_desktop_source.blockSignals(False)
        self.combo_target_mic.blockSignals(False)
        self.combo_real_mic.blockSignals(False)

        if not target_mics:
            self.lbl_target_status.setText("⚠️ No virtual mic found. Click 'Install VB-Cable' below.")
            self.lbl_target_status.setStyleSheet("color: #f23f43; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_target_status.setText(f"Found {len(target_mics)} compatible virtual microphone(s). Ready!")
            self.lbl_target_status.setStyleSheet("color: #23a55a; font-size: 11px;")

    def _apply_config(self):
        target_name = self.config.get("target_mic_name", "")
        if target_name:
            for i in range(self.combo_target_mic.count()):
                data = self.combo_target_mic.itemData(i)
                if data and target_name.lower() in data["name"].lower():
                    self.combo_target_mic.setCurrentIndex(i)
                    break

        desktop_name = self.config.get("desktop_source_name", "")
        if desktop_name:
            for i in range(self.combo_desktop_source.count()):
                data = self.combo_desktop_source.itemData(i)
                if data and desktop_name.lower() in data["name"].lower():
                    self.combo_desktop_source.setCurrentIndex(i)
                    break

        real_mic_name = self.config.get("real_mic_name", "")
        if real_mic_name:
            for i in range(self.combo_real_mic.count()):
                data = self.combo_real_mic.itemData(i)
                if data and real_mic_name.lower() in data["name"].lower():
                    self.combo_real_mic.setCurrentIndex(i)
                    break

        mix_mic = self.config.get("mix_mic_enabled", False)
        self.switch_mix_mic.setChecked(mix_mic)
        self.combo_real_mic.setEnabled(mix_mic)
        self.slider_mic_vol.setEnabled(mix_mic)
        self.btn_mic_mute.setEnabled(mix_mic)

        d_vol = int(self.config.get("desktop_volume", 1.0) * 100)
        self.slider_desktop_vol.setValue(d_vol)
        self.lbl_desktop_vol.setText(f"{d_vol}%")
        self.engine.set_desktop_volume(d_vol / 100.0)

        m_vol = int(self.config.get("mic_volume", 1.0) * 100)
        self.slider_mic_vol.setValue(m_vol)
        self.lbl_mic_vol.setText(f"{m_vol}%")
        self.engine.set_mic_volume(m_vol / 100.0)

        d_muted = self.config.get("desktop_muted", False)
        self.btn_desktop_mute.setChecked(d_muted)
        self.btn_desktop_mute.setText("Unmute" if d_muted else "Mute")
        self.engine.set_desktop_muted(d_muted)

        m_muted = self.config.get("mic_muted", False)
        self.btn_mic_mute.setChecked(m_muted)
        self.btn_mic_mute.setText("Unmute" if m_muted else "Mute")
        self.engine.set_mic_muted(m_muted)

    def _save_current_config(self):
        d_data = self.combo_desktop_source.currentData()
        if d_data:
            self.config["desktop_source_name"] = d_data["name"]

        t_data = self.combo_target_mic.currentData()
        if t_data:
            self.config["target_mic_name"] = t_data["name"]

        r_data = self.combo_real_mic.currentData()
        self.config["real_mic_name"] = r_data["name"] if r_data else ""

        self.config["mix_mic_enabled"] = self.switch_mix_mic.isChecked()
        self.config["desktop_volume"] = self.slider_desktop_vol.value() / 100.0
        self.config["mic_volume"] = self.slider_mic_vol.value() / 100.0
        self.config["desktop_muted"] = self.btn_desktop_mute.isChecked()
        self.config["mic_muted"] = self.btn_mic_mute.isChecked()
        self.config["minimize_to_tray"] = self.switch_tray.isChecked()
        self.config["auto_start"] = self.switch_auto_start.isChecked()
        self.config["theme"] = self.current_theme
        self.config["eq_bands"] = self.eq_bands
        self.config["troll_mode"] = self.troll_mode
        self.config["troll_bass"] = self.troll_bass
        self.config["troll_drive"] = self.troll_drive
        self.config["active_profile"] = self.active_profile

        save_config(self.config)

    def _toggle_stream(self):
        if self.engine.is_running():
            self._stop_stream()
        else:
            self._start_stream()

    def _start_stream(self):
        d_source = self.combo_desktop_source.currentData()
        t_mic = self.combo_target_mic.currentData()
        r_mic = self.combo_real_mic.currentData()
        mix_mic = self.switch_mix_mic.isChecked()

        if not d_source:
            QMessageBox.warning(self, "No Desktop Source", "Please select a desktop audio capture device.")
            return
        if not t_mic:
            QMessageBox.warning(self, "No Virtual Mic", "Please select a target virtual microphone device.")
            return

        try:
            self.engine.start(
                desktop_source=d_source,
                target_mic=t_mic,
                real_mic=r_mic,
                mix_mic=mix_mic
            )
            self._update_stream_ui(True)
        except Exception as e:
            QMessageBox.critical(self, "Streaming Error", f"Failed to start audio engine:\n{e}")
            self._update_stream_ui(False)

    def _stop_stream(self):
        self.engine.stop()
        self._update_stream_ui(False)

    def _update_stream_ui(self, is_running: bool):
        if is_running:
            self.status_pill.setText("● LIVE STREAMING")
            self.status_pill.setStyleSheet("""
                background-color: #1e3a29;
                color: #23a55a;
                padding: 6px 14px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #23a55a;
            """)
            self.btn_toggle_stream.setText("⏹  STOP STREAMING")
            self.btn_toggle_stream.setStyleSheet("""
                QPushButton {
                    background-color: #da373c;
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 8px 18px;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #a1282c;
                }
            """)
            self.act_stream_toggle.setText("Stop Streaming")
            self.combo_desktop_source.setEnabled(False)
            self.combo_target_mic.setEnabled(False)
            self.combo_real_mic.setEnabled(False)
        else:
            self.status_pill.setText("● OFFLINE")
            self.status_pill.setStyleSheet("""
                background-color: #383a40;
                color: #949ba4;
                padding: 6px 14px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            """)
            self.btn_toggle_stream.setText("▶  START STREAMING TO DISCORD")
            self.btn_toggle_stream.setStyleSheet("""
                QPushButton {
                    background-color: #5865f2;
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 8px 18px;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #4752c4;
                }
            """)
            self.act_stream_toggle.setText("Start Streaming")
            self.combo_desktop_source.setEnabled(True)
            self.combo_target_mic.setEnabled(True)
            self.combo_real_mic.setEnabled(self.switch_mix_mic.isChecked())

    def _update_meters(self):
        d, m, o = self.engine.get_meter_levels()
        self.meter_desktop.set_level(d)
        self.meter_mic.set_level(m)
        self.meter_out.set_level(o)

        samples = self.engine.get_latest_samples()
        self.visualizer.update_audio(samples)

    def _on_desktop_vol_changed(self, val):
        self.lbl_desktop_vol.setText(f"{val}%")
        self.engine.set_desktop_volume(val / 100.0)
        self._save_current_config()

    def _on_mic_vol_changed(self, val):
        self.lbl_mic_vol.setText(f"{val}%")
        self.engine.set_mic_volume(val / 100.0)
        self._save_current_config()

    def _on_desktop_mute_toggled(self):
        muted = self.btn_desktop_mute.isChecked()
        self.btn_desktop_mute.setText("Unmute" if muted else "Mute")
        self.engine.set_desktop_muted(muted)
        self._save_current_config()

    def _on_mic_mute_toggled(self):
        muted = self.btn_mic_mute.isChecked()
        self.btn_mic_mute.setText("Unmute" if muted else "Mute")
        self.engine.set_mic_muted(muted)
        self._save_current_config()

    def _on_mix_mic_toggled(self, checked):
        self.combo_real_mic.setEnabled(checked)
        self.slider_mic_vol.setEnabled(checked)
        self.btn_mic_mute.setEnabled(checked)
        self._save_current_config()

    def _refresh_windows_default_input_label(self):
        cur_name = get_windows_default_input_name()
        self.lbl_windows_default.setText(f"Current Windows Default Input: <b>{cur_name}</b>")

    def _set_as_windows_default_input(self):
        target_data = self.combo_target_mic.currentData()
        if not target_data:
            QMessageBox.warning(self, "No Target Selected", "Please select a virtual microphone target first.")
            return

        name = target_data["name"]
        search_key = "Sonar - Microphone" if "sonar" in name.lower() else ("CABLE Output" if "cable" in name.lower() else name)
        ok = set_windows_default_input_device(search_key)
        self._refresh_windows_default_input_label()

        if ok:
            QMessageBox.information(
                self, "Windows Input Source",
                f"Successfully set '{search_key}' as your Windows default input device!\n\n"
                "Any application in Windows will now receive your desktop audio stream."
            )
        else:
            QMessageBox.warning(
                self, "Windows Input Source",
                f"Could not automatically switch endpoint for '{search_key}'.\n"
                "You can select it manually in Windows Sound Settings."
            )

    def _restore_headset_mic_as_windows_default(self):
        real_mic_data = self.combo_real_mic.currentData()
        search_key = real_mic_data["name"] if real_mic_data else "Microphone"

        ok = set_windows_default_input_device(search_key)
        self._refresh_windows_default_input_label()
        if ok:
            QMessageBox.information(
                self, "Windows Input Source",
                f"Successfully restored '{search_key}' as your Windows default microphone."
            )
        else:
            self._open_sound_control_panel()

    def _open_sound_control_panel(self):
        try:
            os.system("start ms-settings:sound")
            os.system("start mmsys.cpl 0 1")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open sound settings: {e}")

    def _install_vbcable_driver(self):
        self.btn_install_vbcable.setEnabled(False)
        self.lbl_install_status.setText("Opening installation dialog...")

        dialog = DriverInstallDialog(self)
        self.driver_dialog = dialog

        def worker():
            def cb(status):
                self.bridge.driver_status_signal.emit(status)

            ok = virtual_driver.install_vbcable(progress_callback=cb)
            if ok:
                self.bridge.driver_finished_signal.emit(
                    True,
                    "VB-Cable installer launched! Complete the Windows setup wizard, then refresh devices."
                )
            else:
                self.bridge.driver_finished_signal.emit(
                    False,
                    "VB-Cable download or installation could not be completed."
                )

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        dialog.exec()

    def _update_driver_status(self, msg):
        self.lbl_install_status.setText(msg)
        if hasattr(self, 'driver_dialog') and self.driver_dialog and self.driver_dialog.isVisible():
            self.driver_dialog.set_status(msg)

    def _on_driver_finished(self, success, msg):
        self.lbl_install_status.setText(msg)
        self.btn_install_vbcable.setEnabled(True)
        if hasattr(self, 'driver_dialog') and self.driver_dialog and self.driver_dialog.isVisible():
            self.driver_dialog.set_status(msg, finished=True, success=success)
        self._load_devices()

    def _show_error(self, msg):
        QMessageBox.critical(self, "Streaming Error", msg)
        self._stop_stream()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def closeEvent(self, event):
        if self.switch_tray.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Desktop Audio to Mic",
                "App minimized to system tray. Streaming continues in background.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self._exit_app()

    def _exit_app(self):
        self._stop_stream()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(500)
        self.meter_timer.stop()
        self.dm.terminate()
        self.tray_icon.hide()
        QApplication.instance().quit()
