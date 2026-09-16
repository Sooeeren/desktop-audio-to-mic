"""
Linux Virtual Audio Device Helper for PulseAudio & PipeWire.
Creates and manages native null sinks and remap sources via pactl.
"""

import shutil
import subprocess
import logging
import os

logger = logging.getLogger("VirtualMicLinux")

SINK_NAME = "DiscordDesktopAudio"
SOURCE_NAME = "DiscordDesktopMic"
MODULE_TRACK_FILE = os.path.expanduser("~/.config/desktop-audio-to-mic/loaded_modules.txt")


def is_pactl_available() -> bool:
    """Check if the pactl CLI tool is installed and accessible."""
    return shutil.which("pactl") is not None


def _run_pactl(*args) -> tuple[bool, str]:
    """Execute a pactl command and return (success, output)."""
    if not is_pactl_available():
        return False, "pactl command not found. Please install pulseaudio-utils or pipewire-pulse."
    try:
        res = subprocess.run(
            ["pactl", *args],
            capture_output=True,
            text=True,
            check=True
        )
        return True, res.stdout.strip()
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        return False, err
    except Exception as e:
        return False, str(e)


def is_virtual_mic_active() -> bool:
    """Check if DiscordDesktopMic source already exists in PulseAudio/PipeWire."""
    ok, out = _run_pactl("list", "short", "sources")
    if not ok:
        return False
    return SOURCE_NAME in out or SINK_NAME in out


def create_virtual_mic() -> tuple[bool, str]:
    """
    Create a native null sink and remap source via pactl:
    1. Null sink 'DiscordDesktopAudio' (receives stream from this app)
    2. Remap source 'DiscordDesktopMic' (mastered to DiscordDesktopAudio.monitor)
    Discord will see 'DiscordDesktopMic' as a standard microphone input!
    """
    if not is_pactl_available():
        return False, "pactl is not installed. Please install pulseaudio-utils or pipewire-pulse."

    if is_virtual_mic_active():
        return True, "Virtual microphone is already active and ready in Discord!"

    # 1. Load null-sink
    ok1, out1 = _run_pactl(
        "load-module", "module-null-sink",
        f"sink_name={SINK_NAME}",
        'sink_properties=device.description="Discord_Desktop_Audio_Sink"'
    )
    if not ok1:
        return False, f"Failed to create null-sink: {out1}"

    sink_mod_id = out1.strip()

    # 2. Load remap-source
    ok2, out2 = _run_pactl(
        "load-module", "module-remap-source",
        f"master={SINK_NAME}.monitor",
        f"source_name={SOURCE_NAME}",
        'source_properties=device.description="Discord_Desktop_Audio_Mic"'
    )
    if not ok2:
        # Clean up null sink if remap fails
        _run_pactl("unload-module", sink_mod_id)
        return False, f"Failed to create remap-source: {out2}"

    source_mod_id = out2.strip()

    # Track module IDs for clean unloading later
    try:
        os.makedirs(os.path.dirname(MODULE_TRACK_FILE), exist_ok=True)
        with open(MODULE_TRACK_FILE, "w", encoding="utf-8") as f:
            f.write(f"{sink_mod_id}\n{source_mod_id}\n")
    except Exception:
        pass

    return True, f"Virtual microphone '{SOURCE_NAME}' created successfully! Select it in Discord."


def remove_virtual_mic() -> tuple[bool, str]:
    """Unload the created virtual modules."""
    if not is_pactl_available():
        return False, "pactl not found."

    removed = 0
    # Try reading tracked module IDs
    if os.path.exists(MODULE_TRACK_FILE):
        try:
            with open(MODULE_TRACK_FILE, "r", encoding="utf-8") as f:
                mod_ids = [line.strip() for line in f if line.strip()]
            for mid in mod_ids:
                ok, _ = _run_pactl("unload-module", mid)
                if ok:
                    removed += 1
            os.remove(MODULE_TRACK_FILE)
        except Exception:
            pass

    # Also search by module list if track file was missing or outdated
    ok, out = _run_pactl("list", "short", "modules")
    if ok:
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                mid, mod_name = parts[0], parts[1]
                if SINK_NAME in line or SOURCE_NAME in line:
                    _run_pactl("unload-module", mid)
                    removed += 1

    return True, f"Removed {removed} virtual audio module(s)."


def get_default_source() -> str:
    """Get the name of the current default recording source."""
    ok, out = _run_pactl("get-default-source")
    return out if ok else "Unknown"


def set_default_source(source_name: str) -> bool:
    """Set the system-wide default input source."""
    ok, _ = _run_pactl("set-default-source", source_name)
    return ok


def open_sound_control() -> bool:
    """Open pavucontrol or desktop sound settings."""
    for cmd in ["pavucontrol", "gnome-control-center sound", "systemsettings sound"]:
        exe = cmd.split()[0]
        if shutil.which(exe):
            try:
                subprocess.Popen(cmd.split())
                return True
            except Exception:
                pass
    return False
