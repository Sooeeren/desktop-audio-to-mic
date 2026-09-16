"""
Linux Audio Device Manager for PulseAudio and PipeWire.
Discovers desktop loopback monitors, virtual audio sinks, and physical microphones.
"""

import json
import logging
import os
import sys

logger = logging.getLogger("DeviceManagerLinux")

CONFIG_DIR = os.path.expanduser("~/.config/desktop-audio-to-mic")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_config() -> dict:
    """Load user settings from config.json with fallback defaults."""
    default_config = {
        "desktop_source_name": "",
        "target_mic_name": "",
        "real_mic_name": "",
        "mix_mic_enabled": False,
        "desktop_volume": 1.0,
        "mic_volume": 1.0,
        "desktop_muted": False,
        "mic_muted": False,
        "minimize_to_tray": False,
        "auto_start": False,
        "theme": "dark",
        "check_updates": True,
        "eq_bands": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "troll_mode": False,
        "troll_bass": 28.0,
        "troll_drive": 3.5,
        "active_profile": "full_desktop",
        "headset_monitor_enabled": False,
        "headset_monitor_device_name": "",
        "headset_monitor_volume": 1.0
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_config.update(saved)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
    elif os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_config.update(saved)
        except Exception:
            pass
    return default_config


def save_config(config: dict):
    """Save user settings to config.json."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.warning(f"Failed to save config: {e}")


def open_linux_volume_control() -> bool:
    """Launch Linux audio control panel (pavucontrol or system settings)."""
    import shutil
    import subprocess
    for cmd in ["pavucontrol", "gnome-control-center sound", "systemsettings5 sound", "pavucontrol-qt"]:
        parts = cmd.split()
        if shutil.which(parts[0]):
            try:
                subprocess.Popen(parts)
                return True
            except Exception:
                pass
    return False


class DeviceManager:
    def __init__(self):
        self.p = None
        self._init_pyaudio()

    def _init_pyaudio(self):
        try:
            try:
                import pyaudio
            except ImportError:
                import pyaudiowpatch as pyaudio
            self.p = pyaudio.PyAudio()
        except Exception as e:
            logger.error(f"PyAudio initialization error: {e}")
            self.p = None

    def terminate(self):
        if self.p:
            try:
                self.p.terminate()
            except Exception:
                pass
            self.p = None

    def get_audio_endpoints(self) -> list[dict]:
        """Enumerate all available audio devices from PyAudio/ALSA/Pulse."""
        if not self.p:
            self._init_pyaudio()
        if not self.p:
            return []

        devices = []
        try:
            count = self.p.get_device_count()
            for i in range(count):
                try:
                    info = self.p.get_device_info_by_index(i)
                    devices.append(info)
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Failed to query audio devices: {e}")
        return devices

    def get_desktop_sources(self) -> list[dict]:
        """
        On Linux (PulseAudio/PipeWire), desktop audio loopback is captured via
        '.monitor' sources (e.g. alsa_output.*.monitor or PulseAudio default monitor).
        """
        all_devs = self.get_audio_endpoints()
        sources = []

        # Find input devices that have 'monitor' in their name or default pulse device
        for d in all_devs:
            if d.get("maxInputChannels", 0) > 0:
                name = d.get("name", "")
                name_lower = name.lower()
                # Prioritize monitor devices
                if "monitor" in name_lower:
                    clean_name = name.replace(".monitor", " [Monitor]")
                    sources.append({
                        "name": name,
                        "display_name": f"🖥️ {clean_name}",
                        "index": d["index"],
                        "channels": d["maxInputChannels"],
                        "rate": int(d.get("defaultSampleRate", 48000)),
                        "info": d
                    })

        # If no explicit monitor device found, list general stereo input sources
        if not sources:
            for d in all_devs:
                if d.get("maxInputChannels", 0) >= 2:
                    sources.append({
                        "name": d["name"],
                        "display_name": f"🔊 {d['name']}",
                        "index": d["index"],
                        "channels": d["maxInputChannels"],
                        "rate": int(d.get("defaultSampleRate", 48000)),
                        "info": d
                    })

        return sources

    def get_target_sinks(self) -> list[dict]:
        """
        Find output sinks suitable for routing desktop audio to Discord.
        Prioritizes 'DiscordDesktopAudio' null sink if created.
        """
        all_devs = self.get_audio_endpoints()
        targets = []

        for d in all_devs:
            if d.get("maxOutputChannels", 0) > 0:
                name = d.get("name", "")
                name_lower = name.lower()

                if "discorddesktopaudio" in name_lower:
                    targets.insert(0, {
                        "name": name,
                        "display_name": f"✨ DiscordDesktopAudio (Virtual Sink - Ready)",
                        "index": d["index"],
                        "channels": d["maxOutputChannels"],
                        "rate": int(d.get("defaultSampleRate", 48000)),
                        "info": d,
                        "discord_name": "DiscordDesktopMic"
                    })
                elif "null" in name_lower or "virtual" in name_lower or "remap" in name_lower:
                    targets.append({
                        "name": name,
                        "display_name": f"🎙️ {name} (Virtual Sink)",
                        "index": d["index"],
                        "channels": d["maxOutputChannels"],
                        "rate": int(d.get("defaultSampleRate", 48000)),
                        "info": d,
                        "discord_name": name
                    })

        return targets

    def get_real_microphones(self) -> list[dict]:
        """
        Find physical recording microphones (excludes monitors and DiscordDesktopMic).
        """
        all_devs = self.get_audio_endpoints()
        mics = []

        for d in all_devs:
            if d.get("maxInputChannels", 0) > 0:
                name = d.get("name", "")
                name_lower = name.lower()

                # Skip monitors and our virtual microphone
                if "monitor" in name_lower or "discorddesktop" in name_lower or "null" in name_lower:
                    continue

                mics.append({
                    "name": name,
                    "display_name": f"🎤 {name}",
                    "index": d["index"],
                    "channels": d["maxInputChannels"],
                    "rate": int(d.get("defaultSampleRate", 48000)),
                    "info": d
                })

        return mics

    def get_playback_devices(self) -> list[dict]:
        """Find physical playback sinks (headphones, speakers) for headset monitoring."""
        all_devs = self.get_audio_endpoints()
        playbacks = []
        for d in all_devs:
            if d.get("maxOutputChannels", 0) > 0:
                name = d.get("name", "")
                name_lower = name.lower()
                if "discorddesktop" in name_lower or "null" in name_lower or "virtual" in name_lower:
                    continue
                playbacks.append({
                    "name": name,
                    "display_name": f"🎧 {name}",
                    "index": d["index"],
                    "channels": d["maxOutputChannels"],
                    "rate": int(d.get("defaultSampleRate", 48000)),
                    "info": d
                })
        return playbacks

    def generate_diagnostic_report(self, config: dict = None) -> str:
        """Generates a comprehensive Linux diagnostic report."""
        import platform
        import datetime
        lines = []
        lines.append("=" * 60)
        lines.append("  DESKTOP AUDIO TO MIC - LINUX DIAGNOSTIC REPORT")
        lines.append(f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")
        lines.append("[1. SYSTEM ENVIRONMENT]")
        lines.append(f"OS: Linux {platform.release()} ({platform.version()})")
        lines.append(f"Machine: {platform.machine()}")
        lines.append(f"Python: {platform.python_version()} ({sys.executable})")
        lines.append("")
        lines.append("[2. AUDIO ENDPOINTS]")
        all_devs = self.get_audio_endpoints()
        lines.append(f"Total Detected Endpoints: {len(all_devs)}")
        for d in all_devs:
            lines.append(f"  [{d.get('index')}] {d.get('name')} | In:{d.get('maxInputChannels',0)} Out:{d.get('maxOutputChannels',0)} | {d.get('defaultSampleRate',0)}Hz")
        lines.append("")
        lines.append("[3. PULSEAUDIO / PIPEWIRE STATUS]")
        try:
            from linux.src.devices import virtual_mic
        except ImportError:
            try:
                from src.devices import virtual_mic
            except ImportError:
                import virtual_mic
        pactl_avail = virtual_mic.is_pactl_available()
        lines.append(f"pactl Available: {pactl_avail}")
        if pactl_avail:
            ok, out = virtual_mic._run_pactl("info")
            if ok:
                lines.append(out)
            ok, sources = virtual_mic._run_pactl("list", "short", "sources")
            if ok:
                lines.append("\nSources:\n" + sources)
            ok, sinks = virtual_mic._run_pactl("list", "short", "sinks")
            if ok:
                lines.append("\nSinks:\n" + sinks)
        lines.append("")
        lines.append("[4. CONFIGURATION]")
        lines.append(json.dumps(load_config(), indent=2))
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)
