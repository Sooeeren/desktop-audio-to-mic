"""
Automated Test Suite for Discord Desktop Audio Mic
Verifies device discovery, audio pipeline, and GUI instantiation.
"""

import sys
import time
from PySide6.QtWidgets import QApplication
from device_manager import DeviceManager, load_config, save_config
from audio_engine import AudioEngine, resample_audio, adjust_channels
import numpy as np


def test_device_discovery():
    print("Testing device discovery...")
    dm = DeviceManager()
    desktop_sources = dm.get_desktop_sources()
    target_mics = dm.get_target_microphones()
    real_mics = dm.get_real_microphones()

    assert len(desktop_sources) > 0, "Failed to discover desktop audio sources"
    assert len(target_mics) > 0, "Failed to discover target virtual microphones"
    print(f"  Discovered {len(desktop_sources)} desktop sources.")
    print(f"  Discovered {len(target_mics)} target virtual mics.")
    print(f"  Discovered {len(real_mics)} real mics.")
    dm.terminate()
    print("[PASS] Device discovery successful!")


def test_audio_resampling():
    print("Testing audio resampling and channel conversions...")
    # 96kHz 8ch -> 48kHz 2ch
    audio_96k = np.ones((960, 8), dtype=np.float32) * 0.5
    resampled = resample_audio(audio_96k, 96000, 48000)
    assert resampled.shape == (480, 8), f"Unexpected resampled shape: {resampled.shape}"

    stereo = adjust_channels(resampled, 8, 2)
    assert stereo.shape == (480, 2), f"Unexpected stereo shape: {stereo.shape}"
    print("[PASS] Audio resampling successful!")


def test_streaming_pipeline():
    print("Testing streaming pipeline...")
    dm = DeviceManager()
    desktop_sources = dm.get_desktop_sources()
    target_mics = dm.get_target_microphones()

    source = desktop_sources[0]
    target = target_mics[0]

    engine = AudioEngine()
    engine.start(source, target)
    assert engine.is_running(), "Engine failed to report running state"

    time.sleep(1.0)
    levels = engine.get_meter_levels()
    assert isinstance(levels, tuple) and len(levels) == 3, "Invalid meter level tuple"

    # Test volume and mute changes
    engine.set_desktop_volume(1.5)
    engine.set_desktop_muted(True)
    engine.set_desktop_muted(False)

    engine.stop()
    assert not engine.is_running(), "Engine failed to stop"
    dm.terminate()
    print("[PASS] Streaming pipeline test successful!")


def test_gui_initialization():
    print("Testing GUI initialization...")
    app = QApplication.instance() or QApplication(sys.argv)
    from gui import MainWindow
    window = MainWindow()
    assert window is not None, "Failed to instantiate MainWindow"
    assert window.combo_desktop.count() > 0, "Desktop combobox is empty"
    assert window.combo_target.count() > 0, "Target combobox is empty"

    # Test stream toggle
    window._start_stream()
    assert window.engine.is_running(), "GUI failed to start engine stream"
    time.sleep(0.5)
    window._stop_stream()
    assert not window.engine.is_running(), "GUI failed to stop engine stream"

    window.close()
    print("[PASS] GUI initialization and controls test successful!")


if __name__ == "__main__":
    test_device_discovery()
    test_audio_resampling()
    test_streaming_pipeline()
    test_gui_initialization()
    print("\nALL AUTOMATED TESTS COMPLETED SUCCESSFULLY!")
