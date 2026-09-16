"""
Linux User Interface for Desktop Audio to Mic.
Features a widescreen horizontal studio dashboard with gradient volume sliders,
live VU meters, native PulseAudio/PipeWire virtual microphone creation,
multi-page navigation, 7-band Equalizer, "Troll" Mode, Themes, and GitHub update checking.
"""

import os
import sys
import threading
import numpy as np

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QPointF, QUrl
from PySide6.QtGui import (
    QIcon, QFont, QColor, QPainter, QLinearGradient, QPen,
    QBrush, QPainterPath, QAction, QDesktopServices
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QFrame,
    QProgressBar, QSystemTrayIcon, QMenu, QMessageBox, QDialog,
    QStackedWidget, QRadioButton, QButtonGroup, QScrollArea, QSizePolicy,
    QPlainTextEdit, QFileDialog
)

try:
    from linux.src.devices.device_manager import (
        DeviceManager, load_config, save_config, open_linux_volume_control,
        mute_default_speakers, is_default_speakers_muted
    )
    from linux.src.audio.audio_engine import AudioEngine, EQ_FREQUENCIES
    from linux.src.devices import virtual_mic
    from linux.src.utils.updater import UpdateCheckWorker, CURRENT_VERSION, RELEASES_URL
except ImportError:
    try:
        from src.devices.device_manager import (
            DeviceManager, load_config, save_config, open_linux_volume_control,
            mute_default_speakers, is_default_speakers_muted
        )
        from src.audio.audio_engine import AudioEngine, EQ_FREQUENCIES
        from src.devices import virtual_mic
        from src.utils.updater import UpdateCheckWorker, CURRENT_VERSION, RELEASES_URL
    except ImportError:
        from device_manager import (
            DeviceManager, load_config, save_config, open_linux_volume_control,
            mute_default_speakers, is_default_speakers_muted
        )
        from audio_engine import AudioEngine, EQ_FREQUENCIES
        import virtual_mic
        from updater import UpdateCheckWorker, CURRENT_VERSION, RELEASES_URL


DARK_STYLE = """
QMainWindow, QWidget#centralWidget {
    background-color: #1e1f22;
    color: #f2f3f5;
    font-family: 'Ubuntu', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
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
    border: 1px solid #383a40;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
}
QComboBox:hover {
    border: 1px solid #5865f2;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #949ba4;
    width: 0;
    height: 0;
}
QComboBox QAbstractItemView {
    background-color: #1e1f22;
    color: #f2f3f5;
    selection-background-color: #5865f2;
    selection-color: #ffffff;
    border: 1px solid #383a40;
    border-radius: 6px;
    padding: 4px;
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
    font-family: 'Ubuntu', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
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
    border: 1px solid #5865f2;
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
    background-color: #e3e5e8;
    color: #4e5058;
    border: 1px solid #c4c9ce;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton.nav_tab:hover {
    background-color: #d1d5db;
    color: #060607;
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
    """Custom toggle switch widget."""
    toggled = Signal(bool)

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.text = text
        self._checked = False
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._update_geometry()

    def _update_geometry(self):
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self.text) if self.text else 0
        total_w = 46 + (text_w + 10 if self.text else 0)
        self.setFixedSize(total_w, 26)

    def setText(self, text: str):
        self.text = text
        self._update_geometry()
        self.update()

    def sizeHint(self):
        return self.size()

    def minimumSizeHint(self):
        return self.size()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)
            event.accept()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = 38
        h = 20
        y = (self.height() - h) // 2

        bg_color = QColor("#23a55a") if self._checked else QColor("#4e5058")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, y, w, h, h // 2, h // 2)

        thumb_size = 16
        thumb_x = (w - thumb_size - 2) if self._checked else 2
        thumb_y = y + 2
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(thumb_x, thumb_y, thumb_size, thumb_size)

        if self.text:
            painter.setPen(QColor("#dbdee1"))
            font = painter.font()
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(w + 10, y + h - 5, self.text)


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class GradientSlider(QSlider):
    """Modern slider with multi-color neon gradient and click-to-position."""
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
        r = h / 2.0

        painter.setBrush(QBrush(QColor("#1e1f22")))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, r, r)

        fill_w = int(w * self.level)
        if fill_w > 0:
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0.0, QColor("#5865F2"))
            grad.setColorAt(0.65, QColor("#23A55A"))
            grad.setColorAt(0.85, QColor("#F0B232"))
            grad.setColorAt(1.0, QColor("#F23F43"))

            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(0, 0, fill_w, h, r, r)

        if self.peak > 0.02:
            pk_x = min(w - 3, int(w * self.peak))
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawRoundedRect(pk_x, 1, 2, h - 2, 1, 1)


class ProAudioVisualizer(QWidget):
    """48-band FFT spectral analyzer with oscilloscope waveform overlay."""
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


class StudioFader(QWidget):
    valueChanged = Signal(int)

    def __init__(self, min_val=-12, max_val=12, init_val=0, freq_label="1 kHz", role_label="MIDS", parent=None):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._val = init_val
        self.freq_label = freq_label
        self.role_label = role_label
        self.meter_level = 0.0
        self.peak_level = 0.0
        self.is_hovered = False
        self.is_dragging = False

        self.setFixedWidth(74)
        self.setFixedHeight(216)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def minimum(self) -> int:
        return self._min

    def maximum(self) -> int:
        return self._max

    def value(self) -> int:
        return self._val

    def setValue(self, val: int):
        clamped = max(self._min, min(self._max, int(val)))
        if clamped != self._val:
            self._val = clamped
            self.update()
            self.valueChanged.emit(self._val)

    def set_meter_level(self, lvl: float):
        lvl = max(0.0, min(1.0, float(lvl)))
        self.meter_level = max(lvl, self.meter_level * 0.85)
        self.peak_level = max(self.meter_level, self.peak_level * 0.95)
        self.update()

    def blockSignals(self, b: bool):
        super().blockSignals(b)

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setValue(0)
            event.accept()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        step = 1 if delta > 0 else -1
        self.setValue(self._val + step)
        event.accept()

    def _val_to_y(self, val: float, track_top: float, track_bottom: float) -> float:
        pct = (val - self._min) / float(self._max - self._min)
        return track_bottom - pct * (track_bottom - track_top)

    def _y_to_val(self, y: float, track_top: float, track_bottom: float) -> int:
        pct = (track_bottom - y) / float(track_bottom - track_top)
        pct = max(0.0, min(1.0, pct))
        return int(round(self._min + pct * (self._max - self._min)))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            track_top = 34.0
            track_bottom = 162.0
            val = self._y_to_val(event.position().y(), track_top, track_bottom)
            self.setValue(val)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            track_top = 34.0
            track_bottom = 162.0
            val = self._y_to_val(event.position().y(), track_top, track_bottom)
            self.setValue(val)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.update()
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()

        # 1. Metallic Faceplate Background
        plate_grad = QLinearGradient(0, 0, w, 0)
        plate_grad.setColorAt(0.0, QColor("#1e2025"))
        plate_grad.setColorAt(0.15, QColor("#282b33"))
        plate_grad.setColorAt(0.85, QColor("#282b33"))
        plate_grad.setColorAt(1.0, QColor("#1c1e22"))

        painter.setBrush(QBrush(plate_grad))
        painter.setPen(QPen(QColor("#383c46"), 1))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)

        # Subtle chassis screws
        screw_pen = QPen(QColor("#15161a"), 1)
        screw_brush = QBrush(QColor("#3a3e47"))
        for sx, sy in [(5, 5), (w - 8, 5), (5, h - 8), (w - 8, h - 8)]:
            painter.setPen(screw_pen)
            painter.setBrush(screw_brush)
            painter.drawEllipse(sx, sy, 3, 3)

        track_top = 34.0
        track_bottom = 162.0
        track_h = track_bottom - track_top
        track_center_x = w / 2.0

        # 2. Calibration dB Scale Ticks & Text
        db_marks = [
            (12, "+12", True),
            (9, "", False),
            (6, "+6", True),
            (3, "", False),
            (0, " 0", True),
            (-3, "", False),
            (-6, "-6", True),
            (-9, "", False),
            (-12, "-12", True),
        ]

        font = painter.font()
        font.setPointSize(6)
        font.setBold(True)
        painter.setFont(font)

        for db_val, label, is_major in db_marks:
            y = self._val_to_y(db_val, track_top, track_bottom)
            is_zero = (db_val == 0)

            if is_zero:
                tick_color = QColor("#5865f2")
                text_color = QColor("#8593ff")
                tick_len = 7
            elif is_major:
                tick_color = QColor("#8e929b")
                text_color = QColor("#949ba4")
                tick_len = 5
            else:
                tick_color = QColor("#464952")
                text_color = QColor("#5c6068")
                tick_len = 3

            # Left ticks & label
            painter.setPen(QPen(tick_color, 1.4 if is_zero else 1))
            painter.drawLine(int(track_center_x - 14 - tick_len), int(y), int(track_center_x - 14), int(y))
            if label:
                painter.setPen(text_color)
                painter.drawText(QRectF(1, y - 5, 16, 10), Qt.AlignRight | Qt.AlignVCenter, label.strip())

            # Right ticks
            painter.setPen(QPen(tick_color, 1.4 if is_zero else 1))
            painter.drawLine(int(track_center_x + 14), int(y), int(track_center_x + 14 + tick_len), int(y))

        # 3. Center Track Slot
        slot_w = 4.0
        slot_x = track_center_x - slot_w / 2.0
        painter.setBrush(QBrush(QColor("#0d0e10")))
        painter.setPen(QPen(QColor("#15161a"), 1))
        painter.drawRoundedRect(QRectF(slot_x, track_top - 2, slot_w, track_h + 4), 2, 2)

        # 4. Mini LED Level Meter Column alongside track
        led_x = track_center_x + 17.0
        num_leds = 14
        led_gap = 1.5
        total_led_h = track_h
        led_item_h = (total_led_h - (num_leds - 1) * led_gap) / float(num_leds)
        active_leds = int(self.meter_level * num_leds)

        for li in range(num_leds):
            ly = track_bottom - (li + 1) * led_item_h - li * led_gap
            pct = li / float(num_leds)
            if pct < 0.65:
                on_c = QColor("#23a55a")
            elif pct < 0.88:
                on_c = QColor("#f0b232")
            else:
                on_c = QColor("#f23f43")

            if li < active_leds:
                painter.setBrush(QBrush(on_c))
                painter.setPen(Qt.NoPen)
            else:
                dim_c = QColor(on_c.red(), on_c.green(), on_c.blue(), 30)
                painter.setBrush(QBrush(dim_c))
                painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(led_x, ly, 2.5, led_item_h), 0.5, 0.5)

        # 5. Contoured 3D Fader Knob (Thumb Cap)
        knob_y = self._val_to_y(self._val, track_top, track_bottom)
        kw = 40.0
        kh = 24.0
        kx = track_center_x - kw / 2.0
        ky = knob_y - kh / 2.0

        # Drop shadow underneath knob
        painter.setBrush(QBrush(QColor(0, 0, 0, 110)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(kx - 1, ky + 2, kw + 2, kh + 2), 3, 3)

        # Knob cap metallic gradient body
        knob_grad = QLinearGradient(kx, ky, kx, ky + kh)
        if self.is_hovered or self.is_dragging:
            knob_grad.setColorAt(0.0, QColor("#6c727d"))
            knob_grad.setColorAt(0.25, QColor("#464952"))
            knob_grad.setColorAt(0.5, QColor("#30333a"))
            knob_grad.setColorAt(0.75, QColor("#464952"))
            knob_grad.setColorAt(1.0, QColor("#1e2024"))
            knob_border = QColor("#8593ff")
        else:
            knob_grad.setColorAt(0.0, QColor("#545862"))
            knob_grad.setColorAt(0.25, QColor("#383b42"))
            knob_grad.setColorAt(0.5, QColor("#25272c"))
            knob_grad.setColorAt(0.75, QColor("#383b42"))
            knob_grad.setColorAt(1.0, QColor("#1a1b1e"))
            knob_border = QColor("#4a4f5a")

        painter.setBrush(QBrush(knob_grad))
        painter.setPen(QPen(knob_border, 1.2 if (self.is_hovered or self.is_dragging) else 1))
        painter.drawRoundedRect(QRectF(kx, ky, kw, kh), 3, 3)

        # Tactile grip ridges (horizontal grooves on top and bottom slope)
        ridge_pen = QPen(QColor(255, 255, 255, 45), 1)
        ridge_shadow = QPen(QColor(0, 0, 0, 90), 1)
        # Top ridges
        for roff in [3.5, 6.0]:
            painter.setPen(ridge_shadow)
            painter.drawLine(int(kx + 5), int(ky + roff + 1), int(kx + kw - 5), int(ky + roff + 1))
            painter.setPen(ridge_pen)
            painter.drawLine(int(kx + 5), int(ky + roff), int(kx + kw - 5), int(ky + roff))
        # Bottom ridges
        for roff in [kh - 6.0, kh - 3.5]:
            painter.setPen(ridge_shadow)
            painter.drawLine(int(kx + 5), int(ky + roff + 1), int(kx + kw - 5), int(ky + roff + 1))
            painter.setPen(ridge_pen)
            painter.drawLine(int(kx + 5), int(ky + roff), int(kx + kw - 5), int(ky + roff))

        # Center concave finger groove & high-visibility indicator line
        groove_y = ky + kh / 2.0
        center_color = QColor("#ffffff") if not self.is_dragging else QColor("#5865f2")
        painter.setPen(QPen(center_color, 2))
        painter.drawLine(int(kx + 2), int(groove_y), int(kx + kw - 2), int(groove_y))

        # 6. Current dB Readout (Header Badge)
        val_str = f"+{self._val} dB" if self._val > 0 else (f"{self._val} dB" if self._val < 0 else "0 dB")
        val_color = QColor("#23a55a") if self._val > 0 else (QColor("#f23f43") if self._val < 0 else QColor("#5865f2"))

        painter.setBrush(QBrush(QColor("#151619")))
        painter.setPen(QPen(val_color, 1))
        painter.drawRoundedRect(QRectF(7, 6, w - 14, 16), 3, 3)

        val_font = painter.font()
        val_font.setPointSize(7)
        val_font.setBold(True)
        painter.setFont(val_font)
        painter.setPen(val_color)
        painter.drawText(QRectF(7, 6, w - 14, 16), Qt.AlignCenter, val_str)

        # 7. Frequency & Role Label (Bottom Footer)
        foot_font = painter.font()
        foot_font.setPointSize(7)
        foot_font.setBold(True)
        painter.setFont(foot_font)
        painter.setPen(QColor("#f2f3f5"))
        painter.drawText(QRectF(2, h - 38, w - 4, 16), Qt.AlignCenter, self.freq_label)

        role_font = painter.font()
        role_font.setPointSize(6)
        role_font.setBold(False)
        painter.setFont(role_font)
        painter.setPen(QColor("#949ba4"))
        painter.drawText(QRectF(2, h - 22, w - 4, 14), Qt.AlignCenter, self.role_label)


class DiagnosticsDialog(QDialog):
    def __init__(self, dm, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Diagnostics & Linux Audio Report")
        self.resize(760, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header
        t_row = QHBoxLayout()
        title_lbl = QLabel("📋  Linux Audio Hardware & System Diagnostics")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #f2f3f5;")
        t_row.addWidget(title_lbl)
        t_row.addStretch()
        layout.addLayout(t_row)

        desc_lbl = QLabel(
            "Complete log of Linux ALSA/PulseAudio/PipeWire endpoints, virtual sinks, and configuration. "
            "Share this report if you or a friend encounter setup or driver issues."
        )
        desc_lbl.setStyleSheet("color: #949ba4; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        # Text area
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        font = QFont("Monospace", 10)
        font.setStyleHint(QFont.Monospace)
        self.text_edit.setFont(font)
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #111214;
                color: #dbdee1;
                border: 1px solid #35373c;
                border-radius: 6px;
                padding: 10px;
                line-height: 1.4;
            }
        """)

        # Generate report
        self.report_text = dm.generate_diagnostic_report(config)
        self.text_edit.setPlainText(self.report_text)
        layout.addWidget(self.text_edit, 1)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_copy = QPushButton("📋 Copy to Clipboard")
        self.btn_copy.setProperty("class", "primary")
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self.btn_copy)

        self.btn_save = QPushButton("💾 Save as Text File (.txt)...")
        self.btn_save.setProperty("class", "secondary")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._save_to_file)
        btn_row.addWidget(self.btn_save)

        btn_row.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.setProperty("class", "ghost")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)

        layout.addLayout(btn_row)

    def _copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.report_text)
        self.btn_copy.setText("✅ Copied to Clipboard!")
        QTimer.singleShot(2500, lambda: self.btn_copy.setText("📋 Copy to Clipboard"))

    def _save_to_file(self):
        default_path = os.path.join(os.path.expanduser("~"), "desktop_audio_diagnostics.txt")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Diagnostic Report", default_path, "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.report_text)
                QMessageBox.information(
                    self, "Report Saved",
                    f"Diagnostic report successfully saved to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")


class MainWindow(QMainWindow):
    def __init__(self, splash=None):
        super().__init__()
        self.splash = splash
        self.setWindowTitle(f"Desktop Audio to Mic (Linux Edition v{CURRENT_VERSION})")
        self.resize(1080, 680)
        self.setMinimumSize(960, 600)

        if self.splash:
            self.splash.set_progress(25, "Initializing Linux audio engine...")

        self.bridge = SignalBridge()
        self.bridge.error_signal.connect(self._show_error)

        self.dm = DeviceManager()
        self.engine = AudioEngine(on_error=self.bridge.error_signal.emit)
        self.config = load_config()

        self.current_theme = self.config.get("theme", "dark")
        self.eq_bands = list(self.config.get("eq_bands", [0.0] * 7))
        self.troll_mode = bool(self.config.get("troll_mode", False))
        self.troll_bass = float(self.config.get("troll_bass", 28.0))
        self.troll_drive = float(self.config.get("troll_drive", 3.5))

        self.engine.set_eq_bands(self.eq_bands)
        self.engine.set_troll_mode(self.troll_mode, self.troll_bass, self.troll_drive)

        if self.splash:
            self.splash.set_progress(50, "Loading multi-page user interface...")

        self._init_ui()
        self._init_tray()

        if self.splash:
            self.splash.set_progress(75, "Detecting PipeWire / PulseAudio endpoints...")

        self._load_devices()

        if self.splash:
            self.splash.set_progress(90, "Applying configuration & checking updates...")

        self._apply_config()
        self._refresh_default_source_label()

        if self.config.get("check_updates", True):
            self._start_update_check(silent=True)

        self.meter_timer = QTimer(self)
        self.meter_timer.timeout.connect(self._update_meters)
        self.meter_timer.start(33)

    def _update_mute_button_style(self, btn, is_muted: bool, vol_slider=None, vol_label=None):
        if is_muted:
            btn.setChecked(True)
            btn.setText("🔇 MUTED")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #da373c;
                    color: #ffffff;
                    border: 1px solid #f23f43;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 5px 8px;
                }
                QPushButton:hover {
                    background-color: #a1282c;
                }
            """)
            if vol_label:
                vol_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #80848e;")
        else:
            btn.setChecked(False)
            btn.setText("🔊 Active")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2b2d31;
                    color: #23a55a;
                    border: 1px solid #35373c;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 5px 8px;
                }
                QPushButton:hover {
                    background-color: #35373c;
                    border: 1px solid #23a55a;
                }
            """)
            if vol_label:
                vol_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #23a55a;")

    def _show_diagnostics_dialog(self):
        diag = DiagnosticsDialog(self.dm, self.config, self)
        diag.exec()

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

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        t_row = QHBoxLayout()
        title = QLabel("🎙️ Desktop Audio to Mic")
        title.setProperty("class", "title")
        self.ver_lbl = QLabel(f"Linux v{CURRENT_VERSION}")
        self.ver_lbl.setStyleSheet("color: #5865f2; font-size: 11px; font-weight: bold; background: rgba(88, 101, 242, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(88, 101, 242, 0.4);")
        t_row.addWidget(title)
        t_row.addWidget(self.ver_lbl)
        t_row.addStretch()
        t_col.addLayout(t_row)

        sub = QLabel("Stream Linux desktop audio into Discord with uncompressed studio-grade fidelity (PipeWire & PulseAudio)")
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

        # Row 2: Navigation Bar Tabs (Full width)
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
        foot_hint = QLabel("PipeWire & PulseAudio • 48 kHz Stereo")
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
        t1 = QLabel("1. Desktop Audio Source (.monitor)")
        t1.setProperty("class", "sectionHeading")
        head_row1.addWidget(t1)
        badge1 = QLabel("PULSE / PIPEWIRE")
        badge1.setStyleSheet("background: rgba(88, 101, 242, 0.15); color: #5865f2; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(88, 101, 242, 0.4);")
        head_row1.addWidget(badge1)
        head_row1.addStretch()
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setProperty("class", "ghost")
        btn_refresh.clicked.connect(self._load_devices)
        head_row1.addWidget(btn_refresh)
        c1_v.addLayout(head_row1)

        self.combo_desktop = NoWheelComboBox()
        self.combo_desktop_source = self.combo_desktop
        self.combo_desktop.currentIndexChanged.connect(self._on_device_selection_changed)
        c1_v.addWidget(self.combo_desktop)

        v_row1 = QHBoxLayout()
        v_row1.setSpacing(10)
        self.slider_desktop_vol = GradientSlider(Qt.Horizontal)
        self.slider_desktop_vol.setRange(0, 200)
        self.slider_desktop_vol.setValue(100)
        self.slider_desktop_vol.valueChanged.connect(self._on_desktop_vol_changed)
        v_row1.addWidget(self.slider_desktop_vol, 1)

        self.lbl_desktop_vol = QLabel("100%")
        self.lbl_desktop_vol_val = self.lbl_desktop_vol
        self.lbl_desktop_vol.setFixedWidth(44)
        self.lbl_desktop_vol.setStyleSheet("font-size: 12px; font-weight: bold; color: #23a55a;")
        v_row1.addWidget(self.lbl_desktop_vol)

        self.btn_desktop_mute = QPushButton("🔊 Active")
        self.btn_desktop_mute.setFixedWidth(78)
        self.btn_desktop_mute.setCheckable(True)
        self.btn_desktop_mute.clicked.connect(self._on_desktop_mute_clicked)
        self._update_mute_button_style(self.btn_desktop_mute, False, self.slider_desktop_vol, self.lbl_desktop_vol)
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

        c2_top = QHBoxLayout()
        t2 = QLabel("2. Voice Microphone (Optional)")
        t2.setProperty("class", "sectionHeading")
        c2_top.addWidget(t2)
        c2_top.addStretch()

        self.switch_mix_mic = ToggleSwitch("Include Voice")
        self.switch_mix_mic.setChecked(False)
        self.switch_mix_mic.toggled.connect(self._on_mix_mic_toggled)
        c2_top.addWidget(self.switch_mix_mic)
        c2_v.addLayout(c2_top)

        self.combo_real_mic = NoWheelComboBox()
        self.combo_mic = self.combo_real_mic
        self.combo_real_mic.currentIndexChanged.connect(self._on_real_mic_selected)
        c2_v.addWidget(self.combo_real_mic)

        v_row2 = QHBoxLayout()
        v_row2.setSpacing(10)
        self.slider_mic_vol = GradientSlider(Qt.Horizontal)
        self.slider_mic_vol.setRange(0, 200)
        self.slider_mic_vol.setValue(100)
        self.slider_mic_vol.setEnabled(False)
        self.slider_mic_vol.valueChanged.connect(self._on_mic_vol_changed)
        v_row2.addWidget(self.slider_mic_vol, 1)

        self.lbl_mic_vol = QLabel("100%")
        self.lbl_mic_vol_val = self.lbl_mic_vol
        self.lbl_mic_vol.setFixedWidth(44)
        self.lbl_mic_vol.setStyleSheet("font-size: 12px; font-weight: bold; color: #23a55a;")
        v_row2.addWidget(self.lbl_mic_vol)

        self.btn_mic_mute = QPushButton("🔊 Active")
        self.btn_mic_mute.setFixedWidth(78)
        self.btn_mic_mute.setCheckable(True)
        self.btn_mic_mute.setEnabled(False)
        self.btn_mic_mute.clicked.connect(self._on_mic_mute_clicked)
        self._update_mute_button_style(self.btn_mic_mute, False, self.slider_mic_vol, self.lbl_mic_vol)
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

        # Card 2b: Headset Audio Monitor & Silent Room Mode
        c_headset = QFrame()
        c_headset.setProperty("class", "card")
        ch_v = QVBoxLayout(c_headset)
        ch_v.setContentsMargins(14, 10, 14, 10)
        ch_v.setSpacing(6)

        head_row_h = QHBoxLayout()
        t_h = QLabel("🎧 Headset Monitor & Silent Room Mode")
        t_h.setProperty("class", "sectionHeading")
        head_row_h.addWidget(t_h)
        badge_h = QLabel("LOCAL PLAYBACK")
        badge_h.setStyleSheet("background: rgba(35, 165, 90, 0.15); color: #23a55a; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(35, 165, 90, 0.4);")
        head_row_h.addWidget(badge_h)
        head_row_h.addStretch()
        self.switch_headset = ToggleSwitch("Headset Audio")
        self.switch_headset.toggled.connect(self._on_headset_toggled)
        head_row_h.addWidget(self.switch_headset)
        ch_v.addLayout(head_row_h)

        self.combo_headset_device = NoWheelComboBox()
        self.combo_headset = self.combo_headset_device
        self.combo_headset_device.currentIndexChanged.connect(self._on_headset_device_changed)
        ch_v.addWidget(self.combo_headset_device)

        v_row_h = QHBoxLayout()
        v_row_h.setSpacing(10)
        self.slider_headset_vol = GradientSlider(Qt.Horizontal)
        self.slider_headset_vol.setRange(0, 150)
        self.slider_headset_vol.setValue(100)
        self.slider_headset_vol.valueChanged.connect(self._on_headset_vol_changed)
        v_row_h.addWidget(self.slider_headset_vol, 1)

        self.lbl_headset_vol = QLabel("100%")
        self.lbl_headset_vol.setFixedWidth(44)
        self.lbl_headset_vol.setStyleSheet("font-size: 12px; font-weight: bold; color: #23a55a;")
        v_row_h.addWidget(self.lbl_headset_vol)

        self.btn_headset_mute = QPushButton("🔊 Active")
        self.btn_headset_mute.setFixedWidth(78)
        self.btn_headset_mute.setCheckable(True)
        self.btn_headset_mute.clicked.connect(self._on_headset_mute_toggled)
        self._update_mute_button_style(self.btn_headset_mute, False, self.slider_headset_vol, self.lbl_headset_vol)
        v_row_h.addWidget(self.btn_headset_mute)
        ch_v.addLayout(v_row_h)

        # Silent Room Mode Controls Row
        sr_row = QHBoxLayout()
        sr_row.setSpacing(8)
        self.btn_silent_room = QPushButton("🔇 Silent Room: Mute PC Speakers")
        self.btn_silent_room.setCheckable(True)
        self.btn_silent_room.setProperty("class", "ghost")
        self.btn_silent_room.setToolTip("Mutes external PC speakers so audio is only heard through your headphones.")
        self.btn_silent_room.clicked.connect(self._on_silent_room_toggled)
        sr_row.addWidget(self.btn_silent_room, 1)

        self.btn_sound_settings = QPushButton("⚙️ Sound Mixer")
        self.btn_sound_settings.setProperty("class", "ghost")
        self.btn_sound_settings.setToolTip("Open Volume Control (pavucontrol)")
        self.btn_sound_settings.clicked.connect(open_linux_volume_control)
        sr_row.addWidget(self.btn_sound_settings)
        ch_v.addLayout(sr_row)

        left_col.addWidget(c_headset)

        grid.addLayout(left_col, 1)

        # === RIGHT COLUMN: OUTPUT TARGET & DISCORD SETUP ===
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        # Card 3: Target Virtual Sink
        c3 = QFrame()
        c3.setProperty("class", "card")
        c3_v = QVBoxLayout(c3)
        c3_v.setContentsMargins(14, 10, 14, 10)
        c3_v.setSpacing(6)

        head_row3 = QHBoxLayout()
        t3 = QLabel("3. Target Virtual Sink (Output to Discord)")
        t3.setProperty("class", "sectionHeading")
        head_row3.addWidget(t3)
        badge3 = QLabel("TRANSMIT")
        badge3.setStyleSheet("background: rgba(35, 165, 90, 0.15); color: #23a55a; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(35, 165, 90, 0.4);")
        head_row3.addWidget(badge3)
        head_row3.addStretch()
        c3_v.addLayout(head_row3)

        t3_row = QHBoxLayout()
        self.combo_target = NoWheelComboBox()
        self.combo_target_mic = self.combo_target
        self.combo_target.currentIndexChanged.connect(self._on_target_sink_changed)
        t3_row.addWidget(self.combo_target, 1)

        self.btn_setup_virtual = QPushButton("Setup Virtual Mic")
        self.btn_setup_virtual.setProperty("class", "secondary")
        self.btn_setup_virtual.clicked.connect(self._setup_virtual_mic)
        t3_row.addWidget(self.btn_setup_virtual)
        c3_v.addLayout(t3_row)

        self.lbl_discord_hint = QLabel("Select 'DiscordDesktopMic' in Discord Voice Settings")
        self.lbl_discord_hint.setStyleSheet("""
            background-color: #2b3d5b;
            color: #5865f2;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.lbl_discord_hint.setWordWrap(True)
        c3_v.addWidget(self.lbl_discord_hint)
        right_col.addWidget(c3)

        # Discord Mini Card & Linux Audio Hub Mini Card
        hubs_row = QHBoxLayout()
        hubs_row.setSpacing(8)

        # Discord Mini Card
        cd = QFrame()
        cd.setProperty("class", "card")
        cd_v = QVBoxLayout(cd)
        cd_v.setContentsMargins(12, 10, 12, 10)
        cd_v.setSpacing(4)
        cdt = QLabel("📖 Discord Setup")
        cdt.setStyleSheet("font-size: 12px; font-weight: bold; color: #f2f3f5;")
        cd_v.addWidget(cdt)
        cd_info = QLabel("1. Set <b>Input Device</b> to <b>DiscordDesktopMic</b><br>2. Set <b>Input Profile</b> to <b>Studio ✨</b>")
        cd_info.setStyleSheet("color: #dbdee1; font-size: 11px; line-height: 1.4;")
        cd_v.addWidget(cd_info)
        hubs_row.addWidget(cd, 1)

        # Linux Audio Hub Mini Card
        cw = QFrame()
        cw.setProperty("class", "card")
        cw_v = QVBoxLayout(cw)
        cw_v.setContentsMargins(12, 10, 12, 10)
        cw_v.setSpacing(4)
        cwt = QLabel("🐧 Linux Audio Hub")
        cwt.setStyleSheet("font-size: 12px; font-weight: bold; color: #f2f3f5;")
        cw_v.addWidget(cwt)

        self.lbl_default_source = QLabel("Default: Checking...")
        self.lbl_default_source.setStyleSheet("color: #949ba4; font-size: 11px;")
        self.lbl_default_source.setWordWrap(True)
        cw_v.addWidget(self.lbl_default_source)

        cw_btns = QHBoxLayout()
        cw_btns.setSpacing(6)
        btn_set_def = QPushButton("Set Default")
        btn_set_def.setProperty("class", "ghost")
        btn_set_def.clicked.connect(self._set_virtual_as_default)

        btn_rst = QPushButton("Restore")
        btn_rst.setProperty("class", "ghost")
        btn_rst.clicked.connect(self._restore_default_source)

        btn_pavu = QPushButton("⚙️ Pavucontrol")
        btn_pavu.setProperty("class", "ghost")
        btn_pavu.setToolTip("Open PulseAudio / PipeWire Volume Control")
        btn_pavu.clicked.connect(self._open_sound_control)

        cw_btns.addWidget(btn_set_def)
        cw_btns.addWidget(btn_rst)
        cw_btns.addWidget(btn_pavu)
        cw_v.addLayout(cw_btns)
        hubs_row.addWidget(cw, 1)

        right_col.addLayout(hubs_row)
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

        self.visualizer = ProAudioVisualizer()
        vis_l.addWidget(self.visualizer)
        layout.addWidget(vis_card)

        return page

    def _create_profiles_page(self) -> QWidget:
        """Page 1: App Routing & Audio Profiles (Firefox / per-app streaming)."""
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

        # Linux Per-App Routing Info Card
        guide_card = QFrame()
        guide_card.setProperty("class", "card")
        gc_l = QVBoxLayout(guide_card)
        gc_l.setContentsMargins(16, 14, 16, 14)
        gc_l.setSpacing(10)

        gc_top = QHBoxLayout()
        g_info_title = QLabel("💡 Per-Application Routing on Linux (PipeWire / PulseAudio)")
        g_info_title.setProperty("class", "title")
        gc_top.addWidget(g_info_title)
        gc_top.addStretch()

        btn_open_pavu = QPushButton("🎛️ Open Pavucontrol Mixer")
        btn_open_pavu.setProperty("class", "primary")
        btn_open_pavu.clicked.connect(self._open_sound_control)
        gc_top.addWidget(btn_open_pavu)
        gc_l.addLayout(gc_top)

        instructions = QLabel(
            "<b>How to stream ONLY Firefox or a specific app into Discord on Linux:</b><br><br>"
            "1. Click the button above to launch <b>PulseAudio / PipeWire Volume Control (Pavucontrol)</b>.<br>"
            "2. Switch to the <b>Playback</b> tab while your app (e.g. Firefox) is playing audio.<br>"
            "3. Click the dropdown next to the app's name and choose <b>DiscordDesktopAudio</b> (Virtual Sink).<br>"
            "4. That's it! Only that application's sound will be streamed into Discord, leaving your games and voice chat private."
        )
        instructions.setStyleSheet("color: #dbdee1; font-size: 13px; line-height: 1.5;")
        instructions.setWordWrap(True)
        gc_l.addWidget(instructions)

        layout.addWidget(guide_card, 1)
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

        # Studio Console Faders Row
        band_defs = [
            ("60 Hz", "SUB"),
            ("150 Hz", "BASS"),
            ("400 Hz", "LOW MID"),
            ("1 kHz", "MIDS"),
            ("2.5 kHz", "PRES"),
            ("6 kHz", "HIGHS"),
            ("15 kHz", "AIR"),
        ]
        sliders_row = QHBoxLayout()
        sliders_row.setSpacing(12)
        sliders_row.setAlignment(Qt.AlignCenter)

        self.eq_sliders = []
        self.eq_val_labels = []

        for i, (freq, role) in enumerate(band_defs):
            init_v = int(self.eq_bands[i]) if i < len(self.eq_bands) else 0
            fader = StudioFader(
                min_val=-12,
                max_val=12,
                init_val=init_v,
                freq_label=freq,
                role_label=role
            )
            fader.valueChanged.connect(self._on_eq_slider_changed)
            self.eq_sliders.append(fader)
            sliders_row.addWidget(fader)

        eq_l.addLayout(sliders_row)
        layout.addWidget(eq_card)

        # "TROLL" MODE CARD
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

        t_desc = QLabel("Injects extreme sub-bass boost (+28 dB) with analog soft-saturation overdrive for hilarious blown-out speaker sound. Built-in brickwall limiter guarantees zero audio crashes.")
        t_desc.setStyleSheet("color: #f87171; font-size: 11px;")
        tc_l.addWidget(t_desc)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(16)

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
        u_row.addWidget(QLabel(f"Installed Version: <b>Linux v{CURRENT_VERSION}</b>"))
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

        self.btn_export_diag = QPushButton("📋 Export Full Diagnostic Report & Logs")
        self.btn_export_diag.setProperty("class", "primary")
        self.btn_export_diag.setCursor(Qt.PointingHandCursor)
        self.btn_export_diag.clicked.connect(self._show_diagnostics_dialog)
        ab_row.addWidget(self.btn_export_diag)

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
    # NAVIGATION & THEME HANDLERS
    # =========================================================================

    def _switch_page(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == idx)

    def _apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        self.config["theme"] = theme_name
        save_config(self.config)
        if theme_name == "light":
            self.setStyleSheet(LIGHT_STYLE)
        else:
            self.setStyleSheet(DARK_STYLE)

    def _set_active_profile(self, key: str):
        self.config["active_profile"] = key
        save_config(self.config)
        self._update_profile_button_ui()

    def _update_profile_button_ui(self):
        active = self.config.get("active_profile", "full_desktop")
        for k, btn in self.profile_buttons.items():
            is_act = (k == active)
            btn.setChecked(is_act)
            if is_act:
                btn.setStyleSheet("background-color: #5865f2; color: #ffffff; border: 1px solid #5865f2; font-weight: bold;")
            else:
                btn.setStyleSheet("")

    def _on_auto_update_toggled(self, checked: bool):
        self.config["check_updates"] = checked
        save_config(self.config)

    def _start_update_check(self, silent: bool = False):
        if not silent:
            self.lbl_update_status.setText("Checking GitHub for newer releases...")
            self.lbl_update_status.setStyleSheet("color: #5865f2; font-size: 12px;")
            self.btn_check_now.setEnabled(False)

        self.updater_worker = UpdateCheckWorker(timeout=4.0)
        self.updater_worker.result_ready.connect(
            lambda newer, latest, url, err: self._on_update_check_finished(newer, latest, url, err, silent)
        )
        self.updater_worker.start()

    def _on_update_check_finished(self, is_newer: bool, latest_ver: str, url: str, err: str, silent: bool):
        self.btn_check_now.setEnabled(True)
        if err:
            if not silent:
                self.lbl_update_status.setText(f"Update check failed: {err}")
                self.lbl_update_status.setStyleSheet("color: #da373c; font-size: 12px;")
            return

        if is_newer:
            msg = f"🎉 Update available: v{latest_ver} is now available on GitHub!"
            self.lbl_update_status.setText(msg)
            self.lbl_update_status.setStyleSheet("color: #23a55a; font-weight: bold; font-size: 12px;")
            self.btn_download_update.setVisible(True)
            self.ver_lbl.setText(f"v{CURRENT_VERSION} (Update: v{latest_ver})")
            self.ver_lbl.setStyleSheet("color: #23a55a; font-size: 11px; font-weight: bold; background: rgba(35, 165, 90, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(35, 165, 90, 0.4);")
            if not silent:
                QMessageBox.information(self, "Update Available", f"A newer version of Desktop Audio to Mic is available: v{latest_ver}\n\nClick 'Download Update' to open the GitHub release.")
        else:
            self.lbl_update_status.setText(f"You are running the latest version (v{CURRENT_VERSION}).")
            self.lbl_update_status.setStyleSheet("color: #23a55a; font-size: 12px;")
            self.btn_download_update.setVisible(False)

    # =========================================================================
    # EQUALIZER & TROLL MODE HANDLERS
    # =========================================================================

    def _on_eq_slider_changed(self):
        new_bands = [float(s.value()) for s in self.eq_sliders]
        self.eq_bands = new_bands
        self.engine.set_eq_bands(new_bands)
        self._update_eq_labels()
        self.config["eq_bands"] = new_bands
        save_config(self.config)

    def _update_eq_labels(self):
        if hasattr(self, 'eq_val_labels') and len(self.eq_val_labels) == len(self.eq_sliders):
            for i, slider in enumerate(self.eq_sliders):
                v = slider.value()
                txt = f"+{v} dB" if v > 0 else f"{v} dB"
                self.eq_val_labels[i].setText(txt)
                if v > 0:
                    self.eq_val_labels[i].setStyleSheet("font-size: 11px; font-weight: bold; color: #23a55a;")
                elif v < 0:
                    self.eq_val_labels[i].setStyleSheet("font-size: 11px; font-weight: bold; color: #f0b232;")
                else:
                    self.eq_val_labels[i].setStyleSheet("font-size: 11px; font-weight: bold; color: #5865f2;")

    def _apply_eq_preset(self, values: list):
        for i, val in enumerate(values):
            if i < len(self.eq_sliders):
                self.eq_sliders[i].setValue(int(val))
        self._on_eq_slider_changed()

    def _on_troll_mode_toggled(self, checked: bool):
        self.troll_mode = checked
        self.config["troll_mode"] = checked
        save_config(self.config)
        self.engine.set_troll_mode(self.troll_mode, self.troll_bass, self.troll_drive)

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
        self.config["troll_bass"] = self.troll_bass
        self.config["troll_drive"] = self.troll_drive
        save_config(self.config)
        self.engine.set_troll_mode(self.troll_mode, self.troll_bass, self.troll_drive)

    # =========================================================================
    # AUDIO STREAMING & DEVICE MANAGEMENT
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
        act_quit.triggered.connect(self._force_quit)
        tray_menu.addAction(act_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()

    def closeEvent(self, event):
        if self.switch_tray.isChecked():
            event.ignore()
            self.hide()
        else:
            self._force_quit()

    def _force_quit(self):
        self._stop_stream()
        if hasattr(self, 'updater_worker') and self.updater_worker.isRunning():
            self.updater_worker.quit()
            self.updater_worker.wait(500)
        self.tray_icon.hide()
        QApplication.quit()

    def _load_devices(self):
        was_running = self.engine.is_running()
        if was_running:
            self._stop_stream()

        self.combo_desktop.blockSignals(True)
        self.combo_target.blockSignals(True)
        self.combo_real_mic.blockSignals(True)
        self.combo_headset_device.blockSignals(True)

        self.combo_desktop.clear()
        self.combo_target.clear()
        self.combo_real_mic.clear()
        self.combo_headset_device.clear()

        self.dm.terminate()
        self.dm = DeviceManager()

        desktop_sources = self.dm.get_desktop_sources()
        for s in desktop_sources:
            self.combo_desktop.addItem(s["display_name"], s)

        target_sinks = self.dm.get_target_sinks()
        if not target_sinks:
            self.combo_target.addItem("⚠️ Click 'Setup Virtual Mic' to create Discord sink", None)
        else:
            for t in target_sinks:
                self.combo_target.addItem(t["display_name"], t)

        real_mics = self.dm.get_real_microphones()
        self.combo_real_mic.addItem("🚫 No Microphone (Disabled)", None)
        for m in real_mics:
            self.combo_real_mic.addItem(m["display_name"], m)

        playbacks = self.dm.get_playback_devices()
        self.combo_headset_device.addItem("🚫 Headset Monitoring Disabled", None)
        for pb in playbacks:
            self.combo_headset_device.addItem(pb["display_name"], pb)

        self.combo_desktop.blockSignals(False)
        self.combo_target.blockSignals(False)
        self.combo_real_mic.blockSignals(False)
        self.combo_headset_device.blockSignals(False)

        saved_desk = self.config.get("desktop_source_name", "")
        if saved_desk:
            idx = self.combo_desktop.findText(saved_desk)
            if idx >= 0:
                self.combo_desktop.setCurrentIndex(idx)

        saved_tgt = self.config.get("target_mic_name", "")
        if saved_tgt:
            idx = self.combo_target.findText(saved_tgt)
            if idx >= 0:
                self.combo_target.setCurrentIndex(idx)

        saved_mic = self.config.get("real_mic_name", "")
        if saved_mic:
            idx = self.combo_real_mic.findText(saved_mic)
            if idx >= 0:
                self.combo_real_mic.setCurrentIndex(idx)

        self._on_target_sink_changed()
        self._refresh_default_source_label()

    def _apply_config(self):
        d_vol = int(self.config.get("desktop_volume", 1.0) * 100)
        self.slider_desktop_vol.setValue(d_vol)
        self.lbl_desktop_vol.setText(f"{d_vol}%")
        self.engine.set_desktop_volume(d_vol / 100.0)

        d_muted = self.config.get("desktop_muted", False)
        self._update_mute_button_style(self.btn_desktop_mute, d_muted, self.slider_desktop_vol, self.lbl_desktop_vol)
        self.engine.set_desktop_muted(d_muted)

        m_vol = int(self.config.get("mic_volume", 1.0) * 100)
        self.slider_mic_vol.setValue(m_vol)
        self.lbl_mic_vol.setText(f"{m_vol}%")
        self.engine.set_mic_volume(m_vol / 100.0)

        m_muted = self.config.get("mic_muted", False)
        self._update_mute_button_style(self.btn_mic_mute, m_muted, self.slider_mic_vol, self.lbl_mic_vol)
        self.engine.set_mic_muted(m_muted)

        mix_enabled = self.config.get("mix_mic_enabled", False)
        saved_mic = self.config.get("real_mic_name", "")
        matched_mic = False
        if saved_mic:
            for i in range(self.combo_real_mic.count()):
                d = self.combo_real_mic.itemData(i)
                if d and saved_mic.lower() in d.get("name", "").lower():
                    self.combo_real_mic.blockSignals(True)
                    self.combo_real_mic.setCurrentIndex(i)
                    self.combo_real_mic.blockSignals(False)
                    matched_mic = True
                    break

        if not matched_mic or not mix_enabled:
            self.combo_real_mic.blockSignals(True)
            self.combo_real_mic.setCurrentIndex(0)
            self.combo_real_mic.blockSignals(False)
            self.switch_mix_mic.setChecked(False)
            self.slider_mic_vol.setEnabled(False)
            self.btn_mic_mute.setEnabled(False)
        else:
            self.switch_mix_mic.setChecked(True)
            self.slider_mic_vol.setEnabled(True)
            self.btn_mic_mute.setEnabled(True)

        # Headset Monitor Configuration
        h_enabled = self.config.get("headset_monitor_enabled", False)
        h_name = self.config.get("headset_monitor_device_name", "")
        matched_headset = False
        if h_name:
            for i in range(self.combo_headset_device.count()):
                d = self.combo_headset_device.itemData(i)
                if d and h_name.lower() in d.get("name", "").lower():
                    self.combo_headset_device.blockSignals(True)
                    self.combo_headset_device.setCurrentIndex(i)
                    self.combo_headset_device.blockSignals(False)
                    matched_headset = True
                    break

        if not matched_headset or not h_enabled:
            self.combo_headset_device.blockSignals(True)
            self.combo_headset_device.setCurrentIndex(0)
            self.combo_headset_device.blockSignals(False)
            self.switch_headset.setChecked(False)
            self.slider_headset_vol.setEnabled(False)
            self.btn_headset_mute.setEnabled(False)
        else:
            self.switch_headset.setChecked(True)
            self.slider_headset_vol.setEnabled(True)
            self.btn_headset_mute.setEnabled(True)

        h_vol = int(self.config.get("headset_monitor_volume", 1.0) * 100)
        self.slider_headset_vol.setValue(h_vol)
        self.lbl_headset_vol.setText(f"{h_vol}%")
        self.engine.set_headset_monitor(
            enabled=h_enabled if matched_headset else False,
            device=self.combo_headset_device.currentData(),
            volume=h_vol / 100.0
        )

        # Silent Room Status
        sr_enabled = self.config.get("silent_room_enabled", False)
        if is_default_speakers_muted():
            sr_enabled = True
        self._update_silent_room_button_style(sr_enabled)

    def _save_current_config(self):
        cur_desk = self.combo_desktop.currentText()
        cur_tgt = self.combo_target.currentText()
        cur_mic_data = self.combo_real_mic.currentData()
        cur_mic = cur_mic_data.get("name", "") if cur_mic_data else ""

        h_data = self.combo_headset_device.currentData()
        self.config["headset_monitor_device_name"] = h_data.get("name", "") if h_data else ""
        self.config["headset_monitor_enabled"] = self.switch_headset.isChecked() and (h_data is not None)
        self.config["headset_monitor_volume"] = self.slider_headset_vol.value() / 100.0
        self.config["desktop_source_name"] = cur_desk
        self.config["target_mic_name"] = cur_tgt
        self.config["real_mic_name"] = cur_mic
        self.config["mix_mic_enabled"] = self.switch_mix_mic.isChecked()
        self.config["desktop_volume"] = self.slider_desktop_vol.value() / 100.0
        self.config["mic_volume"] = self.slider_mic_vol.value() / 100.0
        self.config["desktop_muted"] = self.btn_desktop_mute.isChecked()
        self.config["mic_muted"] = self.btn_mic_mute.isChecked()
        self.config["minimize_to_tray"] = self.switch_tray.isChecked()
        self.config["auto_start"] = self.switch_auto_start.isChecked() if hasattr(self, 'switch_auto_start') else False

        save_config(self.config)

    def _on_target_sink_changed(self):
        target_data = self.combo_target.currentData()
        if target_data:
            discord_name = target_data.get("discord_name", "DiscordDesktopMic")
            self.lbl_discord_hint.setText(
                f"ℹ️ <b>In Discord:</b> Select <b>{discord_name}</b> as your Input Device (Profile: <b>Studio ✨</b>)"
            )
            self.lbl_discord_hint.setStyleSheet("""
                background-color: #2b3d5b;
                color: #5865f2;
                padding: 6px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            self.lbl_discord_hint.setText(
                "⚠️ <b>Virtual sink not found.</b> Click <b>'Setup Virtual Mic'</b> to create it with pactl."
            )
            self.lbl_discord_hint.setStyleSheet("""
                background-color: #2b2314;
                color: #f0b232;
                padding: 6px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            """)
        self._on_device_selection_changed()

    def _on_device_selection_changed(self):
        self._save_current_config()
        if self.engine.is_running():
            self._start_stream()

    def _on_desktop_vol_changed(self, val):
        self.lbl_desktop_vol.setText(f"{val}%")
        color = "#23a55a" if val <= 100 else "#f0b232" if val <= 150 else "#f23f43"
        self.lbl_desktop_vol.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        self.engine.set_desktop_volume(val / 100.0)
        self._save_current_config()

    def _on_desktop_mute_clicked(self, checked):
        self._update_mute_button_style(self.btn_desktop_mute, checked, self.slider_desktop_vol, self.lbl_desktop_vol)
        self.engine.set_desktop_muted(checked)
        self._save_current_config()

    def _on_real_mic_selected(self, index: int):
        data = self.combo_real_mic.itemData(index)
        if data is None:
            self.switch_mix_mic.blockSignals(True)
            self.switch_mix_mic.setChecked(False)
            self.switch_mix_mic.blockSignals(False)
            self.slider_mic_vol.setEnabled(False)
            self.btn_mic_mute.setEnabled(False)
            self.config["mix_mic_enabled"] = False
            self.config["real_mic_name"] = ""
            self.engine.set_mic_volume(0.0)
        else:
            self.switch_mix_mic.blockSignals(True)
            self.switch_mix_mic.setChecked(True)
            self.switch_mix_mic.blockSignals(False)
            self.slider_mic_vol.setEnabled(True)
            self.btn_mic_mute.setEnabled(True)
            self.config["mix_mic_enabled"] = True
            self.config["real_mic_name"] = data.get("name", "")
            self.engine.set_mic_volume(self.slider_mic_vol.value() / 100.0)
        self._save_current_config()
        if self.engine.is_running():
            self._start_stream()

    def _on_mix_mic_toggled(self, checked):
        if not checked:
            self.combo_real_mic.setCurrentIndex(0)
        else:
            if self.combo_real_mic.currentIndex() == 0 and self.combo_real_mic.count() > 1:
                self.combo_real_mic.setCurrentIndex(1)
        self.combo_real_mic.setEnabled(True)
        self.slider_mic_vol.setEnabled(checked)
        self.btn_mic_mute.setEnabled(checked)
        self._save_current_config()
        if self.engine.is_running():
            self._start_stream()

    def _on_mic_vol_changed(self, val):
        self.lbl_mic_vol.setText(f"{val}%")
        color = "#23a55a" if val <= 100 else "#f0b232" if val <= 150 else "#f23f43"
        self.lbl_mic_vol.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        self.engine.set_mic_volume(val / 100.0)
        self._save_current_config()

    def _on_mic_mute_clicked(self, checked):
        self._update_mute_button_style(self.btn_mic_mute, checked, self.slider_mic_vol, self.lbl_mic_vol)
        self.engine.set_mic_muted(checked)
        self._save_current_config()

    def _on_headset_toggled(self, checked: bool):
        if not checked:
            self.combo_headset_device.blockSignals(True)
            self.combo_headset_device.setCurrentIndex(0)
            self.combo_headset_device.blockSignals(False)
            self.slider_headset_vol.setEnabled(False)
            self.btn_headset_mute.setEnabled(False)
            self.engine.set_headset_monitor(enabled=False)
            self.config["headset_monitor_enabled"] = False
        else:
            if self.combo_headset_device.currentIndex() == 0 and self.combo_headset_device.count() > 1:
                best_idx = 1
                for i in range(1, self.combo_headset_device.count()):
                    d = self.combo_headset_device.itemData(i)
                    if d and any(k in d.get("name", "").lower() for k in ["headphone", "headset", "earphone"]):
                        best_idx = i
                        break
                self.combo_headset_device.blockSignals(True)
                self.combo_headset_device.setCurrentIndex(best_idx)
                self.combo_headset_device.blockSignals(False)
            dev = self.combo_headset_device.currentData()
            self.slider_headset_vol.setEnabled(True)
            self.btn_headset_mute.setEnabled(True)
            vol = self.slider_headset_vol.value() / 100.0
            self.engine.set_headset_monitor(enabled=True, device=dev, volume=vol)
            self.config["headset_monitor_enabled"] = True
            if dev:
                self.config["headset_monitor_device_name"] = dev.get("name", "")
        save_config(self.config)

    def _on_headset_device_changed(self, index: int = None):
        dev = self.combo_headset_device.currentData()
        if dev is None:
            self.switch_headset.blockSignals(True)
            self.switch_headset.setChecked(False)
            self.switch_headset.blockSignals(False)
            self.slider_headset_vol.setEnabled(False)
            self.btn_headset_mute.setEnabled(False)
            self.config["headset_monitor_enabled"] = False
            self.config["headset_monitor_device_name"] = ""
            self.engine.set_headset_monitor(enabled=False)
        else:
            self.switch_headset.blockSignals(True)
            self.switch_headset.setChecked(True)
            self.switch_headset.blockSignals(False)
            self.slider_headset_vol.setEnabled(True)
            self.btn_headset_mute.setEnabled(True)
            self.config["headset_monitor_enabled"] = True
            self.config["headset_monitor_device_name"] = dev.get("name", "")
            vol = self.slider_headset_vol.value() / 100.0
            self.engine.set_headset_monitor(enabled=True, device=dev, volume=vol)
        save_config(self.config)

    def _on_headset_vol_changed(self, val):
        self.lbl_headset_vol.setText(f"{val}%")
        self.engine.set_headset_volume(val / 100.0)
        self.config["headset_monitor_volume"] = val / 100.0
        save_config(self.config)

    def _on_headset_mute_toggled(self):
        muted = self.btn_headset_mute.isChecked()
        self._update_mute_button_style(self.btn_headset_mute, muted, self.slider_headset_vol, self.lbl_headset_vol)
        if muted:
            self.engine.set_headset_volume(0.0)
        else:
            self.engine.set_headset_volume(self.slider_headset_vol.value() / 100.0)

    def _on_silent_room_toggled(self, checked: bool):
        mute_default_speakers(checked)
        self._update_silent_room_button_style(checked)
        self.config["silent_room_enabled"] = checked
        save_config(self.config)

    def _update_silent_room_button_style(self, muted: bool):
        if not hasattr(self, 'btn_silent_room'):
            return
        if muted:
            self.btn_silent_room.blockSignals(True)
            self.btn_silent_room.setChecked(True)
            self.btn_silent_room.blockSignals(False)
            self.btn_silent_room.setText("🔇 Silent Room ACTIVE (Speakers Muted)")
            self.btn_silent_room.setStyleSheet("""
                QPushButton {
                    background-color: #da373c;
                    color: #ffffff;
                    font-weight: bold;
                    border: 1px solid #da373c;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #a1282c;
                }
            """)
        else:
            self.btn_silent_room.blockSignals(True)
            self.btn_silent_room.setChecked(False)
            self.btn_silent_room.blockSignals(False)
            self.btn_silent_room.setText("🔊 Silent Room OFF (Speakers Active)")
            self.btn_silent_room.setStyleSheet("""
                QPushButton {
                    background-color: #2b2d31;
                    color: #949ba4;
                    font-weight: normal;
                    border: 1px solid #3f4147;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #35373c;
                    color: #f2f3f5;
                }
            """)

    def _toggle_stream(self):
        self.btn_toggle_stream.setEnabled(False)
        try:
            if self.engine.is_running():
                self._stop_stream()
            else:
                self._start_stream()
        finally:
            self.btn_toggle_stream.setEnabled(True)

    def _start_stream(self):
        desktop_data = self.combo_desktop.currentData()
        target_data = self.combo_target.currentData()
        mix_mic = self.switch_mix_mic.isChecked()
        real_mic_data = self.combo_real_mic.currentData() if mix_mic else None

        if not desktop_data:
            QMessageBox.warning(self, "Device Error", "No desktop audio source selected.")
            return
        if not target_data:
            QMessageBox.warning(self, "Device Error", "No target virtual sink selected. Please click 'Setup Virtual Mic' first.")
            return

        try:
            self.engine.start(desktop_data, target_data, real_mic=real_mic_data, mix_mic=mix_mic)
            self._update_running_ui(True)
        except Exception as e:
            self._update_running_ui(False)
            QMessageBox.critical(self, "Audio Error", f"Failed to start audio stream:\n{e}")

    def _stop_stream(self):
        self.engine.stop()
        self._update_running_ui(False)

    def _update_running_ui(self, running: bool):
        if running:
            self.status_pill.setText("● BROADCASTING LIVE")
            self.status_pill.setStyleSheet("""
                background-color: #23a55a;
                color: #ffffff;
                padding: 6px 14px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            """)
            self.btn_toggle_stream.setText("⏹  STOP STREAMING")
            self.btn_toggle_stream.setStyleSheet("""
                background-color: #da373c;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 22px;
                border-radius: 6px;
                border: none;
            """)
            self.act_stream_toggle.setText("Stop Streaming")
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
                background-color: #5865f2;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 22px;
                border-radius: 6px;
                border: none;
            """)
            self.act_stream_toggle.setText("Start Streaming")
            self.meter_desktop.set_level(0.0)
            self.meter_mic.set_level(0.0)
            self.meter_out.set_level(0.0)
            self.visualizer.update_audio(None)

    def _update_meters(self):
        if self.engine.is_running():
            d, m, o = self.engine.get_meter_levels()
            self.meter_desktop.set_level(d)
            self.meter_mic.set_level(m)
            self.meter_out.set_level(o)

            samples = self.engine.get_latest_samples()
            self.visualizer.update_audio(samples)

            # Update per-band LED meters on the Studio Equalizer faders
            if hasattr(self, 'eq_sliders') and len(self.eq_sliders) == 7:
                bars = self.visualizer.bar_values
                if len(bars) >= 48:
                    band_slices = [
                        (0, 3),    # 60 Hz Sub
                        (3, 7),    # 150 Hz Bass
                        (7, 14),   # 400 Hz Low Mid
                        (14, 23),  # 1 kHz Mids
                        (23, 31),  # 2.5 kHz Presence
                        (31, 39),  # 6 kHz Highs
                        (39, 48),  # 15 kHz Air
                    ]
                    for idx, (s, e) in enumerate(band_slices):
                        lvl = float(np.max(bars[s:e])) if e > s else 0.0
                        self.eq_sliders[idx].set_meter_level(lvl)
        else:
            self.visualizer.update_audio(None)
            if hasattr(self, 'eq_sliders'):
                for fader in self.eq_sliders:
                    fader.set_meter_level(0.0)

    def _setup_virtual_mic(self):
        ok, msg = virtual_mic.create_virtual_mic()
        if ok:
            QMessageBox.information(self, "Virtual Microphone Ready", msg)
            self._load_devices()
        else:
            QMessageBox.critical(self, "Virtual Microphone Error", msg)

    def _refresh_default_source_label(self):
        def_name = virtual_mic.get_default_source()
        self.lbl_default_source.setText(f"Default: <b>{def_name}</b>")

    def _set_virtual_as_default(self):
        ok = virtual_mic.set_default_source(virtual_mic.SOURCE_NAME)
        self._refresh_default_source_label()
        if ok:
            QMessageBox.information(
                self, "Default Input",
                f"Set '{virtual_mic.SOURCE_NAME}' as default system input!"
            )
        else:
            QMessageBox.warning(self, "Error", "Could not set default source.")

    def _restore_default_source(self):
        real_mic = self.combo_real_mic.currentData()
        if real_mic:
            name = real_mic["name"]
            ok = virtual_mic.set_default_source(name)
            self._refresh_default_source_label()
            if ok:
                QMessageBox.information(self, "Default Input", f"Restored default input to: {name}")
                return
        self._open_sound_control()

    def _open_sound_control(self):
        if not virtual_mic.open_sound_control():
            QMessageBox.information(
                self, "Sound Settings",
                "Please run 'pavucontrol' in terminal to view audio routing."
            )

    def _show_error(self, msg):
        QMessageBox.critical(self, "Streaming Error", msg)
        self._stop_stream()
