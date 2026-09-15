"""
Modern PySide6 User Interface for Desktop Audio to Discord Microphone
Features:
- High-contrast custom toggle switches (clearly showing ON/OFF state).
- Simplified Discord Setup guide with 'Studio' Input Profile recommendation.
- Windows System-Wide Input Source configuration (set as default, restore, open settings).
- Pro Audio visualizer graph at the bottom (FFT frequency spectrum + oscilloscope wave).
"""

import os
import sys
import threading
import numpy as np

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QRectF
from PySide6.QtGui import (
    QIcon, QFont, QColor, QPainter, QLinearGradient, QPen,
    QBrush, QPainterPath, QAction
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QFrame,
    QProgressBar, QSystemTrayIcon, QMenu, QScrollArea,
    QMessageBox
)

try:
    from src.devices.device_manager import (
        DeviceManager, load_config, save_config,
        get_windows_default_input_name, set_windows_default_input_device
    )
    from src.audio.audio_engine import AudioEngine
    from src.devices import virtual_driver
except ImportError:
    from device_manager import (
        DeviceManager, load_config, save_config,
        get_windows_default_input_name, set_windows_default_input_device
    )
    from audio_engine import AudioEngine
    import virtual_driver


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

QScrollBar::handle:horizontal,
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
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

QScrollBar::handle:vertical:pressed {
    background: #4752c4;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    width: 0px;
    background: transparent;
    border: none;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    border: none;
}

QFrame.card {
    background-color: #2b2d31;
    border-radius: 10px;
    border: 1px solid #35373c;
    padding: 12px;
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
    border: 1px solid #3f4147;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 24px;
}
QComboBox:hover {
    border-color: #5865f2;
}
QComboBox:focus {
    border-color: #5865f2;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #2b2d31;
    color: #f2f3f5;
    selection-background-color: #5865f2;
    selection-color: #ffffff;
    border: 1px solid #3f4147;
    border-radius: 4px;
    outline: none;
}

QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #1e1f22;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #5865f2;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #5865f2;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #e0e2ff;
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

QPushButton.primary {
    background-color: #5865f2;
    font-weight: bold;
    font-size: 15px;
    padding: 12px 24px;
}
QPushButton.primary:hover {
    background-color: #4752c4;
}
QPushButton.primary:pressed {
    background-color: #3c45a5;
}

QPushButton.stopButton {
    background-color: #da373c;
    font-weight: bold;
    font-size: 15px;
    padding: 12px 24px;
}
QPushButton.stopButton:hover {
    background-color: #c02e34;
}
QPushButton.stopButton:pressed {
    background-color: #a1282d;
}

QPushButton.muteBtn {
    background-color: #383a40;
    color: #dbdee1;
    padding: 5px 12px;
    font-size: 12px;
}
QPushButton.muteBtn:checked {
    background-color: #da373c;
    color: #ffffff;
    font-weight: bold;
}
"""


class ToggleSwitch(QWidget):
    """
    High-contrast, very obvious toggle switch with an illuminated pill badge
    showing '[ ✓ ON ]' in vibrant green or '[ OFF ]' in slate gray.
    """
    toggled = Signal(bool)

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._checked = False
        self._text = text
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)

        # Status Pill Badge
        self.pill = QLabel("[ OFF ]")
        self.pill.setAlignment(Qt.AlignCenter)
        self.pill.setFixedWidth(64)
        self.pill.setFixedHeight(24)
        self._update_pill_style()
        layout.addWidget(self.pill)

        # Label Text
        self.label = QLabel(self._text)
        self.label.setStyleSheet("font-size: 13px; font-weight: 500; color: #f2f3f5;")
        layout.addWidget(self.label)
        layout.addStretch()

    def _update_pill_style(self):
        if self._checked:
            self.pill.setText("✓ ON")
            self.pill.setStyleSheet("""
                background-color: #23a55a;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border-radius: 12px;
                padding: 2px 8px;
                border: 1px solid #2dc76d;
            """)
        else:
            self.pill.setText("OFF")
            self.pill.setStyleSheet("""
                background-color: #383a40;
                color: #80848e;
                font-weight: bold;
                font-size: 11px;
                border-radius: 12px;
                padding: 2px 8px;
                border: 1px solid #4e5058;
            """)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != bool(checked):
            self._checked = bool(checked)
            self._update_pill_style()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)


class NoWheelComboBox(QComboBox):
    """QComboBox that ignores mouse wheel events so scrolling the parent view doesn't accidentally change items."""
    def wheelEvent(self, event):
        event.ignore()


class NoWheelSlider(QSlider):
    """QSlider that ignores mouse wheel events so scrolling the parent view doesn't accidentally change values."""
    def wheelEvent(self, event):
        event.ignore()


class VUMeter(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setRange(0, 100)
        self.setFixedHeight(8)
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
    """
    Real-time audio visualizer displaying:
    1. Log-spaced multi-band frequency spectrum bars with neon gradient & floating peak caps.
    2. Oscilloscope waveform line overlay.
    3. Instantaneous dB volume level.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.num_bars = 32
        self.bar_values = np.zeros(self.num_bars, dtype=np.float32)
        self.peak_values = np.zeros(self.num_bars, dtype=np.float32)
        self.decay = 0.82
        self.peak_decay = 0.94
        self.recent_wave = np.zeros(128, dtype=np.float32)
        self.current_db = -60.0

        self.setFixedHeight(125)
        self.setMinimumWidth(360)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)

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

            # Peak dB
            peak = float(np.max(np.abs(mono))) if len(mono) > 0 else 0.0
            if peak > 0.0001:
                self.current_db = float(np.clip(20.0 * np.log10(peak), -60.0, 6.0))
            else:
                self.current_db = -60.0

            # Subsample for waveform
            step = max(1, len(mono) // 128)
            wave_sub = mono[::step][:128]
            if len(wave_sub) < 128:
                self.recent_wave = np.pad(wave_sub, (0, 128 - len(wave_sub)))
            else:
                self.recent_wave = wave_sub

            # FFT for frequency bars
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

            # Background card
            painter.setBrush(QBrush(QColor("#111214")))
            painter.setPen(QPen(QColor("#2b2d31"), 1))
            painter.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)

            # Subtle horizontal guide grid
            painter.setPen(QPen(QColor("#1e2024"), 1, Qt.DashLine))
            for frac in [0.25, 0.5, 0.75]:
                painter.drawLine(12, int(h * frac), w - 12, int(h * frac))

            # 1. Frequency Spectrum Bars
            margin_x = 14
            margin_b = 14
            avail_w = max(10, w - (2 * margin_x))
            gap = 2
            bar_w = max(2.0, float((avail_w - (self.num_bars - 1) * gap) / self.num_bars))
            max_bar_h = float(max(10, h - 28))

            for i in range(self.num_bars):
                val = float(np.clip(self.bar_values[i], 0.0, 1.0))
                peak = float(np.clip(self.peak_values[i], 0.0, 1.0))
                x = float(margin_x + i * (bar_w + gap))

                bar_h = float(max(2.0, min(max_bar_h, val * max_bar_h)))
                y = float(max(2.0, h - margin_b - bar_h))

                grad = QLinearGradient(x, float(h - margin_b), x, y)
                grad.setColorAt(0.0, QColor("#5865F2"))  # Blurple
                grad.setColorAt(0.55, QColor("#23A55A")) # Green
                grad.setColorAt(0.85, QColor("#F0B232")) # Amber
                grad.setColorAt(1.0, QColor("#F23F43"))  # Red peak

                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 2, 2)

                # Floating peak dot/cap
                if peak > 0.04:
                    py = float(max(4.0, h - margin_b - (peak * max_bar_h)))
                    painter.setBrush(QBrush(QColor("#FFFFFF")))
                    painter.drawRoundedRect(QRectF(x, py - 2.0, bar_w, 2.0), 1, 1)

            # 2. Oscilloscope Waveform Overlay
            if len(self.recent_wave) > 1:
                wave_path = QPainterPath()
                mid_y = float(h / 2.0)
                wave_scale = float(h * 0.35)

                xs = np.linspace(margin_x, w - margin_x, len(self.recent_wave))
                first_y = float(mid_y - (np.clip(self.recent_wave[0], -1.0, 1.0) * wave_scale))
                wave_path.moveTo(float(xs[0]), first_y)
                for i in range(1, len(self.recent_wave)):
                    sample_val = float(np.clip(self.recent_wave[i], -1.0, 1.0))
                    wave_path.lineTo(float(xs[i]), float(mid_y - (sample_val * wave_scale)))

                pen = QPen(QColor(255, 255, 255, 110), 1.5)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(wave_path)

            # 3. Text Overlay: dB readout
            painter.setPen(QPen(QColor("#949BA4")))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            db_text = f"{self.current_db:.1f} dB" if self.current_db > -55 else "SILENT"
            painter.drawText(w - 75, 20, db_text)
        except Exception:
            pass
        finally:
            painter.end()


class SignalBridge(QObject):
    error_signal = Signal(str)
    driver_status_signal = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discord Desktop Audio Mic")
        self.resize(650, 880)
        self.setMinimumWidth(520)

        self.bridge = SignalBridge()
        self.bridge.error_signal.connect(self._show_error)
        self.bridge.driver_status_signal.connect(self._update_driver_status)

        self.dm = DeviceManager()
        self.engine = AudioEngine(on_error=self.bridge.error_signal.emit)
        self.config = load_config()

        self._init_ui()
        self._init_tray()
        self._load_devices()
        self._apply_config()
        self._refresh_windows_default_input_label()

        # Timer for live VU meter and Audio Visualizer animation (~30 FPS)
        self.meter_timer = QTimer(self)
        self.meter_timer.timeout.connect(self._update_meters)
        self.meter_timer.start(33)

    def _init_ui(self):
        self.setStyleSheet(DARK_STYLE)

        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(16, 16, 6, 16)
        main_vbox.setSpacing(12)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.viewport().setAttribute(Qt.WA_AcceptTouchEvents, False)

        content_widget = QWidget()
        content_vbox = QVBoxLayout(content_widget)
        content_vbox.setSpacing(12)
        content_vbox.setContentsMargins(0, 0, 10, 0)

        # ----------------- HEADER CARD -----------------
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_layout = QHBoxLayout(header_card)

        title_col = QVBoxLayout()
        app_title = QLabel("🎙️ Discord Desktop Audio Mic")
        app_title.setProperty("class", "title")
        app_sub = QLabel("Stream your game, music & desktop sound into Discord voice chat")
        app_sub.setProperty("class", "subtitle")
        app_sub.setWordWrap(True)
        title_col.addWidget(app_title)
        title_col.addWidget(app_sub)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        self.status_pill = QLabel("● OFFLINE")
        self.status_pill.setStyleSheet("""
            background-color: #383a40;
            color: #949ba4;
            padding: 6px 14px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
        """)
        header_layout.addWidget(self.status_pill)
        content_vbox.addWidget(header_card)

        # ----------------- MAIN TOGGLE BUTTON -----------------
        self.btn_toggle_stream = QPushButton("▶  START STREAMING TO DISCORD")
        self.btn_toggle_stream.setProperty("class", "primary")
        self.btn_toggle_stream.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_stream.clicked.connect(self._toggle_stream)
        content_vbox.addWidget(self.btn_toggle_stream)

        # ----------------- CARD 1: AUDIO ROUTING -----------------
        routing_card = QFrame()
        routing_card.setProperty("class", "card")
        routing_vbox = QVBoxLayout(routing_card)
        routing_vbox.setSpacing(10)

        sec1_header = QHBoxLayout()
        sec1_title = QLabel("📡 Audio Device Routing")
        sec1_title.setProperty("class", "sectionHeading")
        btn_refresh = QPushButton("🔄 Refresh Devices")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self._load_devices)
        sec1_header.addWidget(sec1_title)
        sec1_header.addStretch()
        sec1_header.addWidget(btn_refresh)
        routing_vbox.addLayout(sec1_header)

        # Desktop Sound Source
        lbl_desktop = QLabel("1. Desktop Audio Source (What you hear in headphones):")
        self.combo_desktop = NoWheelComboBox()
        self.combo_desktop.currentIndexChanged.connect(self._on_device_selection_changed)
        routing_vbox.addWidget(lbl_desktop)
        routing_vbox.addWidget(self.combo_desktop)

        # Virtual Mic Target
        lbl_target = QLabel("2. Target Virtual Microphone (Sends to Discord):")
        self.combo_target = NoWheelComboBox()
        self.combo_target.currentIndexChanged.connect(self._on_target_mic_changed)
        routing_vbox.addWidget(lbl_target)
        routing_vbox.addWidget(self.combo_target)

        # Discord Hint Badge
        self.lbl_discord_hint = QLabel("ℹ️ In Discord: Select this device as your Input Device")
        self.lbl_discord_hint.setStyleSheet("""
            background-color: #1e1f22;
            color: #5865f2;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px dashed #5865f2;
            font-size: 12px;
            font-weight: 500;
        """)
        self.lbl_discord_hint.setWordWrap(True)
        routing_vbox.addWidget(self.lbl_discord_hint)

        content_vbox.addWidget(routing_card)

        # ----------------- CARD 2: AUDIO MIXING & VOLUMES -----------------
        mix_card = QFrame()
        mix_card.setProperty("class", "card")
        mix_vbox = QVBoxLayout(mix_card)
        mix_vbox.setSpacing(12)

        sec2_title = QLabel("🎚️ Audio Levels & Microphone Mixing")
        sec2_title.setProperty("class", "sectionHeading")
        mix_vbox.addWidget(sec2_title)

        # --- Desktop Sound Control ---
        desktop_row = QHBoxLayout()
        desktop_lbl = QLabel("Desktop Audio:")
        desktop_lbl.setFixedWidth(110)
        self.slider_desktop_vol = NoWheelSlider(Qt.Horizontal)
        self.slider_desktop_vol.setRange(0, 200)
        self.slider_desktop_vol.setValue(100)
        self.slider_desktop_vol.valueChanged.connect(self._on_desktop_vol_changed)

        self.lbl_desktop_vol_val = QLabel("100%")
        self.lbl_desktop_vol_val.setFixedWidth(45)

        self.btn_desktop_mute = QPushButton("Mute")
        self.btn_desktop_mute.setCheckable(True)
        self.btn_desktop_mute.setProperty("class", "muteBtn")
        self.btn_desktop_mute.clicked.connect(self._on_desktop_mute_clicked)

        desktop_row.addWidget(desktop_lbl)
        desktop_row.addWidget(self.slider_desktop_vol)
        desktop_row.addWidget(self.lbl_desktop_vol_val)
        desktop_row.addWidget(self.btn_desktop_mute)
        mix_vbox.addLayout(desktop_row)

        self.meter_desktop = VUMeter()
        mix_vbox.addWidget(self.meter_desktop)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #35373c; max-height: 1px;")
        mix_vbox.addWidget(sep)

        # --- Obvious Toggle Switch for Voice Mixing ---
        self.switch_mix_mic = ToggleSwitch("Include My Voice (Mix Headset Microphone into Stream)")
        self.switch_mix_mic.toggled.connect(self._on_mix_mic_toggled)
        mix_vbox.addWidget(self.switch_mix_mic)

        self.mic_container = QWidget()
        mic_vbox = QVBoxLayout(self.mic_container)
        mic_vbox.setContentsMargins(0, 0, 0, 0)
        mic_vbox.setSpacing(8)

        self.combo_real_mic = NoWheelComboBox()
        self.combo_real_mic.currentIndexChanged.connect(self._on_device_selection_changed)
        mic_vbox.addWidget(self.combo_real_mic)

        mic_row = QHBoxLayout()
        mic_lbl = QLabel("Voice Volume:")
        mic_lbl.setFixedWidth(110)

        self.slider_mic_vol = NoWheelSlider(Qt.Horizontal)
        self.slider_mic_vol.setRange(0, 200)
        self.slider_mic_vol.setValue(100)
        self.slider_mic_vol.valueChanged.connect(self._on_mic_vol_changed)

        self.lbl_mic_vol_val = QLabel("100%")
        self.lbl_mic_vol_val.setFixedWidth(45)

        self.btn_mic_mute = QPushButton("Mute")
        self.btn_mic_mute.setCheckable(True)
        self.btn_mic_mute.setProperty("class", "muteBtn")
        self.btn_mic_mute.clicked.connect(self._on_mic_mute_clicked)

        mic_row.addWidget(mic_lbl)
        mic_row.addWidget(self.slider_mic_vol)
        mic_row.addWidget(self.lbl_mic_vol_val)
        mic_row.addWidget(self.btn_mic_mute)
        mic_vbox.addLayout(mic_row)

        self.meter_mic = VUMeter()
        mic_vbox.addWidget(self.meter_mic)

        mix_vbox.addWidget(self.mic_container)
        self.mic_container.setEnabled(False)

        # Separator line
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #35373c; max-height: 1px;")
        mix_vbox.addWidget(sep2)

        # --- Master Output VU ---
        master_row = QHBoxLayout()
        master_lbl = QLabel("Discord Output Signal:")
        master_lbl.setStyleSheet("color: #949ba4; font-size: 12px; font-weight: bold;")
        master_row.addWidget(master_lbl)
        master_row.addStretch()
        mix_vbox.addLayout(master_row)

        self.meter_out = VUMeter()
        mix_vbox.addWidget(self.meter_out)

        content_vbox.addWidget(mix_card)

        # ----------------- CARD 3: DISCORD SETUP GUIDE -----------------
        guide_card = QFrame()
        guide_card.setProperty("class", "card")
        guide_vbox = QVBoxLayout(guide_card)
        guide_vbox.setSpacing(10)

        guide_title = QLabel("📖 Discord Setup (Quick & Easy)")
        guide_title.setProperty("class", "sectionHeading")
        guide_vbox.addWidget(guide_title)

        instructions = QLabel(
            "1. Open Discord and go to <b>User Settings ⚙️ > Voice & Video</b>.<br>"
            "2. Under <b>Input Device</b>, choose the device name shown in the blue hint box above (e.g. <i>CABLE Output</i>, <i>Sonar - Microphone</i>, or your chosen virtual mic).<br>"
            "3. Set <b>Input Profile</b> (or Audio Profile) to <b>Studio</b>.<br>"
            "<font color='#23a55a'><b>✨ That's it!</b></font> Studio profile transmits full-fidelity uncompressed stereo audio without voice filters cutting out game sounds or music."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #dbdee1; line-height: 1.5; font-size: 13px;")
        guide_vbox.addWidget(instructions)

        content_vbox.addWidget(guide_card)

        # ----------------- CARD 4: WINDOWS SYSTEM INPUT SOURCE -----------------
        win_card = QFrame()
        win_card.setProperty("class", "card")
        win_vbox = QVBoxLayout(win_card)
        win_vbox.setSpacing(10)

        win_title = QLabel("🌐 Windows System Input Source")
        win_title.setProperty("class", "sectionHeading")
        win_vbox.addWidget(win_title)

        self.lbl_win_default_status = QLabel("Current Windows Default Input: Checking...")
        self.lbl_win_default_status.setStyleSheet("color: #949ba4; font-size: 12px; font-weight: 500;")
        self.lbl_win_default_status.setWordWrap(True)
        win_vbox.addWidget(self.lbl_win_default_status)

        win_btns_row = QHBoxLayout()
        btn_set_win_default = QPushButton("Set Virtual Mic as Windows Default Input")
        btn_set_win_default.setCursor(Qt.PointingHandCursor)
        btn_set_win_default.setToolTip("Makes any app across Windows receive desktop audio as its microphone")
        btn_set_win_default.clicked.connect(self._set_virtual_mic_as_windows_default)

        btn_restore_win_default = QPushButton("Restore Headset Mic as Default")
        btn_restore_win_default.setCursor(Qt.PointingHandCursor)
        btn_restore_win_default.clicked.connect(self._restore_headset_mic_as_windows_default)

        win_btns_row.addWidget(btn_set_win_default)
        win_btns_row.addWidget(btn_restore_win_default)
        win_vbox.addLayout(win_btns_row)

        tools_row = QHBoxLayout()
        btn_open_sound_cp = QPushButton("⚙️ Open Windows Sound Settings")
        btn_open_sound_cp.setCursor(Qt.PointingHandCursor)
        btn_open_sound_cp.clicked.connect(self._open_sound_control_panel)

        self.btn_install_vbcable = QPushButton("📥 Install Dedicated VB-Cable Driver")
        self.btn_install_vbcable.setCursor(Qt.PointingHandCursor)
        self.btn_install_vbcable.clicked.connect(self._install_vbcable_driver)

        tools_row.addWidget(btn_open_sound_cp)
        tools_row.addWidget(self.btn_install_vbcable)
        win_vbox.addLayout(tools_row)

        self.lbl_install_status = QLabel("")
        self.lbl_install_status.setStyleSheet("color: #23a55a; font-size: 12px;")
        win_vbox.addWidget(self.lbl_install_status)

        content_vbox.addWidget(win_card)

        # ----------------- CARD 5: PRO AUDIO VISUALIZER GRAPH -----------------
        vis_card = QFrame()
        vis_card.setProperty("class", "card")
        vis_vbox = QVBoxLayout(vis_card)
        vis_vbox.setSpacing(8)

        vis_header = QVBoxLayout()
        vis_header.setSpacing(2)
        vis_title = QLabel("📊 Live Desktop Audio Graph")
        vis_title.setProperty("class", "sectionHeading")
        vis_sub = QLabel("Real-time Frequency Spectrum & Oscilloscope Waveform")
        vis_sub.setProperty("class", "subtitle")
        vis_sub.setWordWrap(True)
        vis_header.addWidget(vis_title)
        vis_header.addWidget(vis_sub)
        vis_vbox.addLayout(vis_header)

        self.visualizer = ProAudioVisualizer()
        vis_vbox.addWidget(self.visualizer)

        content_vbox.addWidget(vis_card)

        # ----------------- FOOTER OPTIONS -----------------
        footer_layout = QHBoxLayout()
        self.switch_tray = ToggleSwitch("Minimize to System Tray on close")
        self.switch_tray.setChecked(self.config.get("minimize_to_tray", False))
        self.switch_tray.toggled.connect(self._save_current_config)
        footer_layout.addWidget(self.switch_tray)
        footer_layout.addStretch()

        content_vbox.addLayout(footer_layout)

        scroll_area.setWidget(content_widget)
        main_vbox.addWidget(scroll_area)

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
                self.activateWindow()

    def closeEvent(self, event):
        if self.switch_tray.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Discord Desktop Audio Mic",
                "App is running quietly in the system tray.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self._force_quit()

    def _force_quit(self):
        self.engine.stop()
        self.dm.terminate()
        self._save_current_config()
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

        target_mics = self.dm.get_target_microphones()
        if not target_mics:
            self.combo_target.addItem("⚠️ No Virtual Mic Found - Click 'Install VB-Cable' Below", None)
        else:
            for t in target_mics:
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

        self._on_target_mic_changed()
        self._refresh_windows_default_input_label()

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
        self.mic_container.setEnabled(mix_enabled)

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

    def _on_target_mic_changed(self):
        target_data = self.combo_target.currentData()
        if target_data:
            discord_name = target_data.get("discord_name", target_data["name"])
            self.lbl_discord_hint.setText(
                f"ℹ️ <b>In Discord:</b> Go to User Settings > Voice & Video and select: <b>{discord_name}</b> as your Input Device."
            )
            self.lbl_discord_hint.setStyleSheet("""
                background-color: #1e1f22;
                color: #5865f2;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px dashed #5865f2;
                font-size: 12px;
                font-weight: 500;
            """)
        else:
            self.lbl_discord_hint.setText(
                "⚠️ <b>No virtual audio device selected.</b><br>"
                "Windows needs a virtual cable to route desktop sound into Discord as a microphone.<br>"
                "Scroll down and click <b>'📥 Install Dedicated VB-Cable Driver'</b> to install it in 10 seconds!"
            )
            self.lbl_discord_hint.setStyleSheet("""
                background-color: #2b2314;
                color: #f0b232;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px dashed #f0b232;
                font-size: 12px;
                font-weight: 500;
            """)
        self._on_device_selection_changed()

    def _on_device_selection_changed(self):
        self._save_current_config()
        if self.engine.is_running():
            self._start_stream()

    def _on_desktop_vol_changed(self, val):
        self.lbl_desktop_vol_val.setText(f"{val}%")
        self.engine.set_desktop_volume(val / 100.0)
        self._save_current_config()

    def _on_desktop_mute_clicked(self, checked):
        self.btn_desktop_mute.setText("MUTED" if checked else "Mute")
        self.engine.set_desktop_muted(checked)
        self._save_current_config()

    def _on_mix_mic_toggled(self, checked):
        self.mic_container.setEnabled(checked)
        self._save_current_config()
        if self.engine.is_running():
            self._start_stream()

    def _on_mic_vol_changed(self, val):
        self.lbl_mic_vol_val.setText(f"{val}%")
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
            QMessageBox.warning(self, "Device Error", "No target virtual microphone selected.")
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
                font-size: 15px;
                padding: 12px 24px;
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
                font-size: 15px;
                padding: 12px 24px;
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

            # Update live visualizer with latest audio buffer
            samples = self.engine.get_latest_samples()
            self.visualizer.update_audio(samples)
        else:
            self.visualizer.update_audio(None)

    def _refresh_windows_default_input_label(self):
        def_name = get_windows_default_input_name()
        self.lbl_win_default_status.setText(f"Current Windows Default Input: <b>{def_name}</b>")

    def _set_virtual_mic_as_windows_default(self):
        target_data = self.combo_target.currentData()
        if not target_data:
            return
        # Match substring e.g. "Sonar - Microphone" or "CABLE Output"
        target_name = target_data["name"]
        search_key = "Sonar - Microphone" if "sonar" in target_name.lower() else "CABLE Output" if "cable" in target_name.lower() else target_name

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
        if not real_mic_data:
            search_key = "Microphone"
        else:
            search_key = real_mic_data["name"]

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
        self.lbl_install_status.setText("Downloading VB-Audio Virtual Cable...")

        def worker():
            def cb(status):
                self.bridge.driver_status_signal.emit(status)
            ok = virtual_driver.install_vbcable(progress_callback=cb)
            if ok:
                self.bridge.driver_status_signal.emit("VB-Cable installer launched! Refresh devices after installing.")
            else:
                self.bridge.driver_status_signal.emit("VB-Cable installation could not be completed.")

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _update_driver_status(self, msg):
        self.lbl_install_status.setText(msg)
        self.btn_install_vbcable.setEnabled(True)
        self._load_devices()

    def _show_error(self, msg):
        QMessageBox.critical(self, "Streaming Error", msg)
        self._stop_stream()
