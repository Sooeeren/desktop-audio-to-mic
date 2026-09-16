"""
Linux User Interface for Desktop Audio to Mic.
Features a widescreen horizontal studio dashboard with gradient volume sliders,
live VU meters, native PulseAudio/PipeWire virtual microphone creation, and 48-band visualizer.
"""

import os
import sys
import threading
import numpy as np

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QPointF
from PySide6.QtGui import (
    QIcon, QFont, QColor, QPainter, QLinearGradient, QPen,
    QBrush, QPainterPath, QAction
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QFrame,
    QProgressBar, QSystemTrayIcon, QMenu, QMessageBox, QDialog
)

from src.devices.device_manager import DeviceManager, load_config, save_config
from src.audio.audio_engine import AudioEngine
from src.devices import virtual_mic


DARK_STYLE = """
QMainWindow, QWidget#centralWidget {
    background-color: #1e1f22;
    color: #f2f3f5;
    font-family: 'Ubuntu', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QFrame.card {
    background-color: #2b2d31;
    border-radius: 10px;
    border: 1px solid #35373c;
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

QPushButton {
    background-color: #4e5058;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #6d6f78;
}
QPushButton:pressed {
    background-color: #3b3c42;
}

QPushButton.muteBtn {
    background-color: #35373c;
    color: #dbdee1;
    padding: 5px 8px;
    font-size: 11px;
    font-weight: bold;
    border-radius: 4px;
}
QPushButton.muteBtn:checked {
    background-color: #da373c;
    color: #ffffff;
    font-weight: bold;
}
"""


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._checked = False
        self._text = text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.btn_badge = QPushButton("[ OFF ]")
        self.btn_badge.setCheckable(True)
        self.btn_badge.setCursor(Qt.PointingHandCursor)
        self.btn_badge.setFixedHeight(26)
        self._update_badge_style()
        self.btn_badge.clicked.connect(self._on_clicked)
        layout.addWidget(self.btn_badge)

        if self._text:
            self.lbl_text = QLabel(self._text)
            self.lbl_text.setStyleSheet("color: #dbdee1; font-size: 13px; font-weight: 500;")
            layout.addWidget(self.lbl_text)

        layout.addStretch()

    def _on_clicked(self):
        self._checked = not self._checked
        self._update_badge_style()
        self.toggled.emit(self._checked)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool):
        if self._checked != val:
            self._checked = val
            self._update_badge_style()
            self.toggled.emit(self._checked)

    def _update_badge_style(self):
        self.btn_badge.setChecked(self._checked)
        if self._checked:
            self.btn_badge.setText("[ ✓ ON ]")
            self.btn_badge.setStyleSheet("""
                QPushButton {
                    background-color: #23a55a;
                    color: #ffffff;
                    border: 2px solid #2dc76d;
                    border-radius: 13px;
                    padding: 2px 12px;
                    font-weight: 800;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #2dc76d; }
            """)
        else:
            self.btn_badge.setText("[ OFF ]")
            self.btn_badge.setStyleSheet("""
                QPushButton {
                    background-color: #383a40;
                    color: #949ba4;
                    border: 1px solid #4e5058;
                    border-radius: 13px;
                    padding: 2px 10px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #4e5058; color: #dbdee1; }
            """)


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class GradientSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFixedHeight(26)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def wheelEvent(self, event):
        event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            track_margin = 10
            usable_w = self.width() - 2 * track_margin
            if usable_w > 0:
                pos = max(0, min(event.position().x() - track_margin, usable_w))
                ratio = pos / usable_w
                new_val = int(self.minimum() + ratio * (self.maximum() - self.minimum()))
                self.setValue(new_val)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        track_margin = 10
        track_h = 6
        track_y = (h - track_h) / 2.0
        usable_w = w - 2 * track_margin

        # Background track
        groove_path = QPainterPath()
        groove_path.addRoundedRect(track_margin, track_y, usable_w, track_h, 3, 3)
        painter.fillPath(groove_path, QColor("#1e1f22"))

        # Filled active track
        span = self.maximum() - self.minimum()
        val = self.value() - self.minimum()
        ratio = val / span if span > 0 else 0.0
        handle_x = track_margin + ratio * usable_w

        if handle_x > track_margin:
            filled_path = QPainterPath()
            filled_path.addRoundedRect(track_margin, track_y, handle_x - track_margin, track_h, 3, 3)

            grad = QLinearGradient(track_margin, 0, w - track_margin, 0)
            grad.setColorAt(0.0, QColor("#5865f2"))  # Blurple
            grad.setColorAt(0.5, QColor("#23a55a"))  # Emerald Green (100%)
            grad.setColorAt(0.8, QColor("#f0b232"))  # Amber (boost)
            grad.setColorAt(1.0, QColor("#f23f43"))  # Red (200%)

            painter.fillPath(filled_path, grad)

        # Thumb
        thumb_r = 8 if self._hover else 7
        if self._hover:
            halo = QPainterPath()
            halo.addEllipse(handle_x - thumb_r - 3, h / 2.0 - thumb_r - 3, (thumb_r + 3) * 2, (thumb_r + 3) * 2)
            painter.fillPath(halo, QColor(88, 101, 242, 60))

        thumb = QPainterPath()
        thumb.addEllipse(handle_x - thumb_r, h / 2.0 - thumb_r, thumb_r * 2, thumb_r * 2)
        painter.fillPath(thumb, QColor("#ffffff"))

        inner = QPainterPath()
        inner_r = thumb_r - 3
        inner.addEllipse(handle_x - inner_r, h / 2.0 - inner_r, inner_r * 2, inner_r * 2)
        inner_color = QColor("#5865f2") if ratio < 0.5 else QColor("#23a55a") if ratio < 0.8 else QColor("#f0b232")
        painter.fillPath(inner, inner_color)

        painter.end()


class VUMeter(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setRange(0, 100)
        self.setFixedHeight(10)
        self.setStyleSheet("""
            QProgressBar {
                background-color: #1e1f22;
                border-radius: 4px;
                border: 1px solid #35373c;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #23a55a, stop:0.75 #f0b232, stop:0.95 #f23f43);
                border-radius: 3px;
            }
        """)

    def set_level(self, level: float):
        val = int(min(1.0, max(0.0, level)) * 100)
        self.setValue(val)


class ProAudioVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.num_bars = 48
        self.bar_values = np.zeros(self.num_bars, dtype=np.float32)
        self.peak_values = np.zeros(self.num_bars, dtype=np.float32)
        self.decay = 0.82
        self.peak_decay = 0.94
        self.recent_wave = np.zeros(128, dtype=np.float32)
        self.current_db = -60.0

        self.setFixedHeight(125)
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
                        if len(slice_vals) > 0:
                            val = float(np.mean(slice_vals))
                            norm = float(np.clip((val / (n / 7.0)) * 2.8, 0.0, 1.0))
                        else:
                            norm = 0.0

                        if norm > self.bar_values[i]:
                            self.bar_values[i] = norm
                        else:
                            self.bar_values[i] = self.bar_values[i] * self.decay + norm * (1.0 - self.decay)

                        if self.bar_values[i] > self.peak_values[i]:
                            self.peak_values[i] = self.bar_values[i]
                        else:
                            self.peak_values[i] = max(self.bar_values[i], self.peak_values[i] * self.peak_decay)
            self.update()
        except Exception:
            pass

    def paintEvent(self, event):
        painter = QPainter()
        if not painter.begin(self):
            return

        try:
            painter.setRenderHint(QPainter.Antialiasing)
            w = self.width()
            h = self.height()
            if w <= 30 or h <= 30:
                return

            painter.setBrush(QBrush(QColor("#111214")))
            painter.setPen(QPen(QColor("#232428"), 1))
            painter.drawRoundedRect(0, 0, w, h, 6, 6)

            margin_x = 12
            margin_y = 12
            usable_w = w - 2 * margin_x
            usable_h = h - 2 * margin_y

            # Draw 48 Equalizer bars
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

                # Floating peak cap
                peak_norm = max(0.0, min(1.0, float(self.peak_values[i])))
                peak_y = (h - margin_y) - (peak_norm * usable_h) - 2.0
                painter.setBrush(QBrush(QColor("#ffffff")))
                painter.drawRoundedRect(x, max(float(margin_y), peak_y), bar_w, 2.0, 1.0, 1.0)

            # Oscilloscope waveform overlay
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
        finally:
            painter.end()


class SignalBridge(QObject):
    error_signal = Signal(str)
    driver_status_signal = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self, splash=None):
        super().__init__()
        self.splash = splash
        self.setWindowTitle("Desktop Audio to Mic (Linux)")
        self.resize(1040, 680)
        self.setMinimumSize(980, 620)

        if self.splash:
            self.splash.set_progress(25, "Initializing Linux audio engine...")

        self.bridge = SignalBridge()
        self.bridge.error_signal.connect(self._show_error)

        self.dm = DeviceManager()
        self.engine = AudioEngine(on_error=self.bridge.error_signal.emit)
        self.config = load_config()

        if self.splash:
            self.splash.set_progress(50, "Loading user interface...")

        self._init_ui()
        self._init_tray()

        if self.splash:
            self.splash.set_progress(75, "Detecting PipeWire / PulseAudio endpoints...")

        self._load_devices()

        if self.splash:
            self.splash.set_progress(90, "Applying configuration...")

        self._apply_config()
        self._refresh_default_source_label()

        self.meter_timer = QTimer(self)
        self.meter_timer.timeout.connect(self._update_meters)
        self.meter_timer.start(33)

    def _init_ui(self):
        self.setStyleSheet(DARK_STYLE)

        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root = QVBoxLayout(central_widget)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        # ----------------- 1. HEADER BAR -----------------
        header_card = QFrame()
        header_card.setProperty("class", "card")
        hl = QHBoxLayout(header_card)
        hl.setContentsMargins(14, 8, 14, 8)

        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        t_row = QHBoxLayout()
        title = QLabel("🎙️ Desktop Audio to Mic")
        title.setProperty("class", "title")
        ver = QLabel("Linux v1.3.0")
        ver.setStyleSheet("color: #5865f2; font-size: 11px; font-weight: bold; background: #1e1f22; padding: 2px 8px; border-radius: 4px;")
        t_row.addWidget(title)
        t_row.addWidget(ver)
        t_row.addStretch()
        t_col.addLayout(t_row)

        sub = QLabel("Stream Linux desktop audio into Discord with uncompressed studio-grade fidelity (PipeWire & PulseAudio)")
        sub.setProperty("class", "subtitle")
        t_col.addWidget(sub)
        hl.addLayout(t_col)

        hl.addStretch()

        self.status_pill = QLabel("● OFFLINE")
        self.status_pill.setStyleSheet("""
            background-color: #383a40;
            color: #949ba4;
            padding: 6px 14px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
        """)
        hl.addWidget(self.status_pill)

        self.btn_toggle_stream = QPushButton("▶  START STREAMING TO DISCORD")
        self.btn_toggle_stream.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_stream.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 22px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
        """)
        self.btn_toggle_stream.clicked.connect(self._toggle_stream)
        hl.addWidget(self.btn_toggle_stream)
        root.addWidget(header_card)

        # ----------------- 2. TWO-COLUMN DASHBOARD GRID -----------------
        grid = QHBoxLayout()
        grid.setSpacing(10)

        # === LEFT COLUMN: AUDIO INPUTS & MIXER ===
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        # Card 1: Desktop Channel
        c1 = QFrame()
        c1.setProperty("class", "card")
        c1_v = QVBoxLayout(c1)
        c1_v.setContentsMargins(14, 12, 14, 12)
        c1_v.setSpacing(8)

        head_row1 = QHBoxLayout()
        t1 = QLabel("1. Desktop Audio Source (.monitor)")
        t1.setProperty("class", "sectionHeading")
        head_row1.addWidget(t1)
        head_row1.addStretch()
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet("background-color: #35373c; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        btn_refresh.clicked.connect(self._load_devices)
        head_row1.addWidget(btn_refresh)
        c1_v.addLayout(head_row1)

        self.combo_desktop = NoWheelComboBox()
        self.combo_desktop.currentIndexChanged.connect(self._on_device_selection_changed)
        c1_v.addWidget(self.combo_desktop)

        s1_row = QHBoxLayout()
        s1_row.setSpacing(8)
        s1_lbl = QLabel("Volume:")
        s1_lbl.setStyleSheet("color: #949ba4; font-size: 12px; font-weight: bold;")
        s1_row.addWidget(s1_lbl)

        self.slider_desktop_vol = GradientSlider()
        self.slider_desktop_vol.setRange(0, 200)
        self.slider_desktop_vol.setValue(100)
        self.slider_desktop_vol.valueChanged.connect(self._on_desktop_vol_changed)
        s1_row.addWidget(self.slider_desktop_vol, 1)

        self.lbl_desktop_vol_val = QLabel("100%")
        self.lbl_desktop_vol_val.setFixedWidth(44)
        self.lbl_desktop_vol_val.setAlignment(Qt.AlignCenter)
        self.lbl_desktop_vol_val.setStyleSheet("color: #23a55a; font-weight: bold; font-size: 12px;")
        s1_row.addWidget(self.lbl_desktop_vol_val)

        self.btn_desktop_mute = QPushButton("Mute")
        self.btn_desktop_mute.setCheckable(True)
        self.btn_desktop_mute.setFixedWidth(60)
        self.btn_desktop_mute.setProperty("class", "muteBtn")
        self.btn_desktop_mute.clicked.connect(self._on_desktop_mute_clicked)
        s1_row.addWidget(self.btn_desktop_mute)
        c1_v.addLayout(s1_row)

        vu1_row = QHBoxLayout()
        vu1_row.setSpacing(8)
        vu1_lbl = QLabel("Signal:")
        vu1_lbl.setStyleSheet("color: #949ba4; font-size: 11px; font-weight: bold;")
        vu1_lbl.setFixedWidth(s1_lbl.sizeHint().width())
        vu1_row.addWidget(vu1_lbl)
        self.meter_desktop = VUMeter()
        vu1_row.addWidget(self.meter_desktop, 1)
        c1_v.addLayout(vu1_row)

        left_col.addWidget(c1)

        # Card 2: Voice Mic Channel
        c2 = QFrame()
        c2.setProperty("class", "card")
        c2_v = QVBoxLayout(c2)
        c2_v.setContentsMargins(14, 12, 14, 12)
        c2_v.setSpacing(8)

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
        self.combo_real_mic.currentIndexChanged.connect(self._on_device_selection_changed)
        self.combo_real_mic.setEnabled(False)
        c2_v.addWidget(self.combo_real_mic)

        s2_row = QHBoxLayout()
        s2_row.setSpacing(8)
        s2_lbl = QLabel("Volume:")
        s2_lbl.setStyleSheet("color: #949ba4; font-size: 12px; font-weight: bold;")
        s2_row.addWidget(s2_lbl)

        self.slider_mic_vol = GradientSlider()
        self.slider_mic_vol.setRange(0, 200)
        self.slider_mic_vol.setValue(100)
        self.slider_mic_vol.setEnabled(False)
        self.slider_mic_vol.valueChanged.connect(self._on_mic_vol_changed)
        s2_row.addWidget(self.slider_mic_vol, 1)

        self.lbl_mic_vol_val = QLabel("100%")
        self.lbl_mic_vol_val.setFixedWidth(44)
        self.lbl_mic_vol_val.setAlignment(Qt.AlignCenter)
        self.lbl_mic_vol_val.setStyleSheet("color: #23a55a; font-weight: bold; font-size: 12px;")
        s2_row.addWidget(self.lbl_mic_vol_val)

        self.btn_mic_mute = QPushButton("Mute")
        self.btn_mic_mute.setCheckable(True)
        self.btn_mic_mute.setFixedWidth(60)
        self.btn_mic_mute.setEnabled(False)
        self.btn_mic_mute.setProperty("class", "muteBtn")
        self.btn_mic_mute.clicked.connect(self._on_mic_mute_clicked)
        s2_row.addWidget(self.btn_mic_mute)
        c2_v.addLayout(s2_row)

        vu2_row = QHBoxLayout()
        vu2_row.setSpacing(8)
        vu2_lbl = QLabel("Signal:")
        vu2_lbl.setStyleSheet("color: #949ba4; font-size: 11px; font-weight: bold;")
        vu2_lbl.setFixedWidth(s2_lbl.sizeHint().width())
        vu2_row.addWidget(vu2_lbl)
        self.meter_mic = VUMeter()
        vu2_row.addWidget(self.meter_mic, 1)
        c2_v.addLayout(vu2_row)

        left_col.addWidget(c2)
        grid.addLayout(left_col, 5)

        # === RIGHT COLUMN: OUTPUT ROUTING & HUBS ===
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Card 3: Target Virtual Mic & Output Signal
        c3 = QFrame()
        c3.setProperty("class", "card")
        c3_v = QVBoxLayout(c3)
        c3_v.setContentsMargins(14, 12, 14, 12)
        c3_v.setSpacing(8)

        t3 = QLabel("3. Target Virtual Sink (Output to Discord)")
        t3.setProperty("class", "sectionHeading")
        c3_v.addWidget(t3)

        t3_row = QHBoxLayout()
        self.combo_target = NoWheelComboBox()
        self.combo_target.currentIndexChanged.connect(self._on_target_sink_changed)
        t3_row.addWidget(self.combo_target, 1)

        self.btn_setup_virtual = QPushButton("Setup Virtual Mic")
        self.btn_setup_virtual.setCursor(Qt.PointingHandCursor)
        self.btn_setup_virtual.setStyleSheet("background-color: #35373c; font-size: 11px; padding: 6px 10px; border-radius: 4px;")
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

        out_lbl = QLabel("Master Discord Output Signal:")
        out_lbl.setStyleSheet("color: #949ba4; font-size: 11px; font-weight: bold;")
        c3_v.addWidget(out_lbl)
        self.meter_out = VUMeter()
        c3_v.addWidget(self.meter_out)

        right_col.addWidget(c3)

        # Mini Cards: Discord Setup & Linux Audio Hub Side-by-Side
        hubs_row = QHBoxLayout()
        hubs_row.setSpacing(10)

        # Discord Mini Card
        cd = QFrame()
        cd.setProperty("class", "card")
        cd_v = QVBoxLayout(cd)
        cd_v.setContentsMargins(12, 10, 12, 10)
        cd_v.setSpacing(5)
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
        cw_v.setSpacing(5)
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
        btn_set_def.setCursor(Qt.PointingHandCursor)
        btn_set_def.setStyleSheet("background-color: #35373c; font-size: 11px; padding: 4px 6px; border-radius: 4px;")
        btn_set_def.clicked.connect(self._set_virtual_as_default)

        btn_rst = QPushButton("Restore")
        btn_rst.setCursor(Qt.PointingHandCursor)
        btn_rst.setStyleSheet("background-color: #35373c; font-size: 11px; padding: 4px 6px; border-radius: 4px;")
        btn_rst.clicked.connect(self._restore_default_source)

        btn_pavu = QPushButton("⚙️ Pavucontrol")
        btn_pavu.setCursor(Qt.PointingHandCursor)
        btn_pavu.setToolTip("Open PulseAudio / PipeWire Volume Control")
        btn_pavu.setStyleSheet("background-color: #35373c; font-size: 11px; padding: 4px 6px; border-radius: 4px;")
        btn_pavu.clicked.connect(self._open_sound_control)

        cw_btns.addWidget(btn_set_def)
        cw_btns.addWidget(btn_rst)
        cw_btns.addWidget(btn_pavu)
        cw_v.addLayout(cw_btns)
        hubs_row.addWidget(cw, 1)

        right_col.addLayout(hubs_row)
        grid.addLayout(right_col, 5)

        root.addLayout(grid)

        # ----------------- 3. FULL-WIDTH LIVE AUDIO VISUALIZER DOCK -----------------
        vis_card = QFrame()
        vis_card.setProperty("class", "card")
        vl = QVBoxLayout(vis_card)
        vl.setContentsMargins(14, 10, 14, 10)
        vl.setSpacing(6)

        vh_row = QHBoxLayout()
        vh_title = QLabel("📊 Real-Time Audio Visualizer & Frequency Spectrum")
        vh_title.setProperty("class", "sectionHeading")
        vh_row.addWidget(vh_title)
        vh_row.addStretch()

        self.lbl_vis_db = QLabel("OFFLINE")
        self.lbl_vis_db.setStyleSheet("color: #23a55a; font-weight: bold; font-size: 12px; background: #1e1f22; padding: 2px 8px; border-radius: 4px;")
        vh_row.addWidget(self.lbl_vis_db)
        vl.addLayout(vh_row)

        self.visualizer = ProAudioVisualizer()
        self.visualizer.setFixedHeight(125)
        vl.addWidget(self.visualizer)

        root.addWidget(vis_card)

        # ----------------- 4. FOOTER OPTIONS -----------------
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
        foot_hint = QLabel("Linux PipeWire & PulseAudio Edition • Single View")
        foot_hint.setStyleSheet("color: #949ba4; font-size: 11px;")
        foot.addWidget(foot_hint)
        root.addLayout(foot)

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
        self.tray_icon.hide()
        QApplication.quit()

    def _load_devices(self):
        was_running = self.engine.is_running()
        if was_running:
            self._stop_stream()

        self.combo_desktop.blockSignals(True)
        self.combo_target.blockSignals(True)
        self.combo_real_mic.blockSignals(True)

        self.combo_desktop.clear()
        self.combo_target.clear()
        self.combo_real_mic.clear()

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
        for m in real_mics:
            self.combo_real_mic.addItem(m["display_name"], m)

        self.combo_desktop.blockSignals(False)
        self.combo_target.blockSignals(False)
        self.combo_real_mic.blockSignals(False)

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
        self.lbl_desktop_vol_val.setText(f"{d_vol}%")
        self.engine.set_desktop_volume(d_vol / 100.0)

        d_muted = self.config.get("desktop_muted", False)
        self.btn_desktop_mute.setChecked(d_muted)
        self.btn_desktop_mute.setText("MUTED" if d_muted else "Mute")
        self.engine.set_desktop_muted(d_muted)

        m_vol = int(self.config.get("mic_volume", 1.0) * 100)
        self.slider_mic_vol.setValue(m_vol)
        self.lbl_mic_vol_val.setText(f"{m_vol}%")
        self.engine.set_mic_volume(m_vol / 100.0)

        m_muted = self.config.get("mic_muted", False)
        self.btn_mic_mute.setChecked(m_muted)
        self.btn_mic_mute.setText("MUTED" if m_muted else "Mute")
        self.engine.set_mic_muted(m_muted)

        mix_enabled = self.config.get("mix_mic_enabled", False)
        self.switch_mix_mic.setChecked(mix_enabled)
        self.combo_real_mic.setEnabled(mix_enabled)
        self.slider_mic_vol.setEnabled(mix_enabled)
        self.btn_mic_mute.setEnabled(mix_enabled)

    def _save_current_config(self):
        cur_desk = self.combo_desktop.currentText()
        cur_tgt = self.combo_target.currentText()
        cur_mic = self.combo_real_mic.currentText()

        self.config["desktop_source_name"] = cur_desk
        self.config["target_mic_name"] = cur_tgt
        self.config["real_mic_name"] = cur_mic
        self.config["mix_mic_enabled"] = self.switch_mix_mic.isChecked()
        self.config["desktop_volume"] = self.slider_desktop_vol.value() / 100.0
        self.config["mic_volume"] = self.slider_mic_vol.value() / 100.0
        self.config["desktop_muted"] = self.btn_desktop_mute.isChecked()
        self.config["mic_muted"] = self.btn_mic_mute.isChecked()
        self.config["minimize_to_tray"] = self.switch_tray.isChecked()

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
        self.lbl_desktop_vol_val.setText(f"{val}%")
        color = "#23a55a" if val <= 100 else "#f0b232" if val <= 150 else "#f23f43"
        self.lbl_desktop_vol_val.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        self.engine.set_desktop_volume(val / 100.0)
        self._save_current_config()

    def _on_desktop_mute_clicked(self, checked):
        self.btn_desktop_mute.setText("MUTED" if checked else "Mute")
        self.engine.set_desktop_muted(checked)
        self._save_current_config()

    def _on_mix_mic_toggled(self, checked):
        self.combo_real_mic.setEnabled(checked)
        self.slider_mic_vol.setEnabled(checked)
        self.btn_mic_mute.setEnabled(checked)
        self._save_current_config()
        if self.engine.is_running():
            self._start_stream()

    def _on_mic_vol_changed(self, val):
        self.lbl_mic_vol_val.setText(f"{val}%")
        color = "#23a55a" if val <= 100 else "#f0b232" if val <= 150 else "#f23f43"
        self.lbl_mic_vol_val.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        self.engine.set_mic_volume(val / 100.0)
        self._save_current_config()

    def _on_mic_mute_clicked(self, checked):
        self.btn_mic_mute.setText("MUTED" if checked else "Mute")
        self.engine.set_mic_muted(checked)
        self._save_current_config()

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
            if hasattr(self, 'lbl_vis_db'):
                db = self.visualizer.current_db
                self.lbl_vis_db.setText(f"{db:.1f} dB" if db > -58.0 else "SILENT")
        else:
            self.visualizer.update_audio(None)
            if hasattr(self, 'lbl_vis_db'):
                self.lbl_vis_db.setText("OFFLINE")

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
