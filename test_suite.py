"""
Automated Test Suite for Discord Desktop Audio Mic
Verifies device discovery, audio pipeline, cross-platform helpers, and GUI instantiation.
"""

import os
import sys
import time
import numpy as np

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.devices.device_manager import (
    DeviceManager, load_config, save_config,
    get_system_default_input_name, set_system_default_input_device
)
from src.audio.audio_engine import AudioEngine, resample_audio, adjust_channels
from src.devices import virtual_driver


def test_device_discovery():
    print("Testing device discovery...")
    dm = DeviceManager()
    desktop_sources = dm.get_desktop_sources()
    target_mics = dm.get_target_microphones()
    real_mics = dm.get_real_microphones()

    print(f"  Discovered {len(desktop_sources)} desktop source(s).")
    print(f"  Discovered {len(target_mics)} target virtual mic(s).")
    print(f"  Discovered {len(real_mics)} real mic(s).")
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


def test_cross_platform_helpers():
    print("Testing cross-platform default audio device helpers...")
    def_name = get_system_default_input_name()
    assert isinstance(def_name, str) and len(def_name) > 0, "Invalid default input name"
    print(f"  System default recording device: {def_name}")

    if sys.platform != "win32":
        active = virtual_driver.is_linux_virtual_mic_active()
        print(f"  Linux virtual mic active: {active}")

    print("[PASS] Cross-platform helpers successful!")


def test_config_persistence():
    print("Testing config load and save...")
    cfg = load_config()
    assert isinstance(cfg, dict), "Config must be a dictionary"
    assert "desktop_volume" in cfg, "Missing desktop_volume key"
    original_vol = cfg.get("desktop_volume", 1.0)
    cfg["desktop_volume"] = 1.25
    save_config(cfg)
    reloaded = load_config()
    assert reloaded.get("desktop_volume") == 1.25, "Failed to persist config update"
    # Restore original
    cfg["desktop_volume"] = original_vol
    save_config(cfg)
    print("[PASS] Config persistence successful!")


def test_streaming_pipeline():
    print("Testing streaming pipeline...")
    dm = DeviceManager()
    desktop_sources = dm.get_desktop_sources()
    target_mics = dm.get_target_microphones()

    if not desktop_sources or not target_mics:
        print("  [SKIP] Skipping active stream test (no playback loopback or target mic available in test environment).")
        dm.terminate()
        return

    source = desktop_sources[0]
    target = target_mics[0]

    engine = AudioEngine()
    engine.start(source, target)
    assert engine.is_running(), "Engine failed to report running state"

    time.sleep(0.5)
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
    try:
        from PySide6.QtWidgets import QApplication
        from src.ui.gui import MainWindow
    except ImportError:
        print("  [SKIP] PySide6 not installed in current test python environment.")
        return

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    assert window is not None, "Failed to instantiate MainWindow"

    # Test stream toggle if devices present
    if window.combo_desktop.count() > 0 and window.combo_target.count() > 0:
        window._start_stream()
        assert window.engine.is_running(), "GUI failed to start engine stream"
        time.sleep(0.3)
        window._stop_stream()
        assert not window.engine.is_running(), "GUI failed to stop engine stream"

    window.close()
    print("[PASS] GUI initialization and controls test successful!")


if __name__ == "__main__":
    test_device_discovery()
    test_audio_resampling()
    test_cross_platform_helpers()
    test_config_persistence()
    test_streaming_pipeline()
    test_gui_initialization()
    print("\nALL AUTOMATED TESTS COMPLETED SUCCESSFULLY!")

