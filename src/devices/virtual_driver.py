"""
Virtual Audio Driver Helper
Provides 1-click virtual audio device setup:
- On Windows: Downloads and installs VB-Audio Virtual Cable with UAC elevation.
- On Linux: Creates a native virtual microphone via PulseAudio / PipeWire (pactl).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

if sys.platform == "win32":
    import ctypes

VB_CABLE_URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip"
LINUX_SINK_NAME = "DiscordAudioMic"
LINUX_SINK_DESC = "Discord_Desktop_Audio_Mic"
LINUX_SOURCE_NAME = "DiscordVirtualMic"
LINUX_SOURCE_DESC = "Discord_Virtual_Microphone"


def is_admin():
    if sys.platform == "win32":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        try:
            return os.geteuid() == 0
        except Exception:
            return False


def install_vbcable(progress_callback=None):
    """
    Downloads and launches the VB-Audio CABLE installer with UAC prompt (Windows only).
    """
    if sys.platform != "win32":
        return create_linux_virtual_mic(progress_callback)

    try:
        if progress_callback:
            progress_callback("Downloading VB-Audio Virtual Cable...")

        temp_dir = tempfile.mkdtemp(prefix="vbcable_")
        zip_path = os.path.join(temp_dir, "vbcable.zip")

        # Download zip
        urllib.request.urlretrieve(VB_CABLE_URL, zip_path)

        if progress_callback:
            progress_callback("Extracting installer...")

        extract_dir = os.path.join(temp_dir, "extracted")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Look for 64-bit installer
        setup_exe = os.path.join(extract_dir, "VBCABLE_Setup_x64.exe")
        if not os.path.exists(setup_exe):
            setup_exe = os.path.join(extract_dir, "VBCABLE_Setup.exe")

        if not os.path.exists(setup_exe):
            raise FileNotFoundError("VBCABLE_Setup.exe not found in downloaded package.")

        if progress_callback:
            progress_callback("Launching installer (Please accept Windows UAC prompt)...")

        # Launch with runas for administrator elevation
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            setup_exe,
            None,
            extract_dir,
            1  # SW_SHOWNORMAL
        )

        if ret <= 32:
            raise RuntimeError(f"Failed to elevate installer (Error code {ret}).")

        if progress_callback:
            progress_callback("Installer launched! Complete installation and reboot if prompted.")
        return True

    except Exception as e:
        if progress_callback:
            progress_callback(f"Installation error: {e}")
        return False


def is_linux_virtual_mic_active() -> bool:
    """Checks whether the Linux virtual audio sink exists via pactl."""
    if not shutil.which("pactl"):
        return False
    try:
        res = subprocess.run(["pactl", "list", "short", "sinks"], capture_output=True, text=True, timeout=3)
        return LINUX_SINK_NAME.lower() in res.stdout.lower()
    except Exception:
        return False


def create_linux_virtual_mic(progress_callback=None) -> bool:
    """
    Creates a native virtual audio null-sink and remapped virtual microphone
    using PulseAudio / PipeWire (pactl).
    """
    pactl_bin = shutil.which("pactl")
    if not pactl_bin:
        msg = "'pactl' utility not found. Please install pulseaudio-utils or pipewire-pulse."
        if progress_callback:
            progress_callback(msg)
        return False

    try:
        if is_linux_virtual_mic_active():
            if progress_callback:
                progress_callback("Virtual microphone is already active in PulseAudio/PipeWire.")
            return True

        if progress_callback:
            progress_callback(f"Creating virtual sink '{LINUX_SINK_NAME}'...")

        # 1. Create Null Sink for desktop audio playback destination
        sink_cmd = [
            pactl_bin, "load-module", "module-null-sink",
            f"sink_name={LINUX_SINK_NAME}",
            f"sink_properties=device.description={LINUX_SINK_DESC}"
        ]
        res_sink = subprocess.run(sink_cmd, capture_output=True, text=True, timeout=5)
        if res_sink.returncode != 0:
            err = res_sink.stderr.strip() or "Unknown pactl error"
            if progress_callback:
                progress_callback(f"Failed to create virtual sink: {err}")
            return False

        if progress_callback:
            progress_callback(f"Creating virtual microphone input '{LINUX_SOURCE_NAME}'...")

        # 2. Remap null sink monitor to a friendly virtual microphone source
        source_cmd = [
            pactl_bin, "load-module", "module-remap-source",
            f"source_name={LINUX_SOURCE_NAME}",
            f"master={LINUX_SINK_NAME}.monitor",
            f"source_properties=device.description={LINUX_SOURCE_DESC}"
        ]
        subprocess.run(source_cmd, capture_output=True, text=True, timeout=5)

        if progress_callback:
            progress_callback("Virtual microphone ready! Select 'Discord_Virtual_Microphone' in Discord.")
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error creating virtual mic: {e}")
        return False


def remove_linux_virtual_mic(progress_callback=None) -> bool:
    """
    Unloads the virtual sink and virtual microphone modules from PulseAudio/PipeWire.
    """
    pactl_bin = shutil.which("pactl")
    if not pactl_bin:
        return False

    try:
        res = subprocess.run([pactl_bin, "list", "short", "modules"], capture_output=True, text=True, timeout=3)
        unloaded = 0
        for line in res.stdout.splitlines():
            if LINUX_SINK_NAME in line or LINUX_SOURCE_NAME in line:
                parts = line.split()
                if parts:
                    mod_id = parts[0]
                    subprocess.run([pactl_bin, "unload-module", mod_id], capture_output=True, timeout=3)
                    unloaded += 1

        if progress_callback:
            progress_callback(f"Removed {unloaded} virtual microphone module(s).")
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error removing virtual mic: {e}")
        return False


def install_or_create_virtual_driver(progress_callback=None) -> bool:
    """Cross-platform helper to set up virtual microphone."""
    if sys.platform == "win32":
        return install_vbcable(progress_callback)
    else:
        return create_linux_virtual_mic(progress_callback)

