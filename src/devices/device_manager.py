"""
Device Manager for Desktop Audio to Discord Microphone
Enumerates Windows WASAPI playback, loopback, and recording devices,
identifies virtual audio cables, and persists user device configurations.
"""

import json
import os
import sys
import pyaudiowpatch as pyaudio


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")

# Keywords that indicate a virtual microphone playback input
VIRTUAL_CABLE_KEYWORDS = [
    "sonar - microphone",
    "cable input",
    "vb-audio point",
    "virtual audio cable",
    "line 1 (virtual audio cable)",
    "virtual speakers",
]


class DeviceInfo:
    def __init__(self, index, name, host_api, channels, sample_rate, is_loopback=False, is_input=False):
        self.index = index
        self.name = name
        self.host_api = host_api
        self.channels = channels
        self.sample_rate = int(sample_rate)
        self.is_loopback = is_loopback
        self.is_input = is_input

    def to_dict(self):
        return {
            "index": self.index,
            "name": self.name,
            "channels": self.channels,
            "sample_rate": self.sample_rate,
            "is_loopback": self.is_loopback,
            "is_input": self.is_input,
        }


class DeviceManager:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.wasapi_api_index = None
        self._init_wasapi()

    def _init_wasapi(self):
        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            self.wasapi_api_index = wasapi_info["index"]
        except (OSError, KeyError):
            self.wasapi_api_index = None

    def get_desktop_sources(self):
        """
        Returns a list of output devices that have WASAPI loopback capabilities.
        Each item is a tuple: (display_name, loopback_device_info, output_device_info, is_default)
        """
        if self.wasapi_api_index is None:
            return []

        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out_idx = wasapi_info["defaultOutputDevice"]
            default_out_name = self.p.get_device_info_by_index(default_out_idx)["name"]
        except Exception:
            default_out_idx = -1
            default_out_name = ""

        loopback_devices = {}
        for dev in self.p.get_loopback_device_info_generator():
            # Dev name typically ends with [Loopback]
            base_name = dev["name"].replace(" [Loopback]", "").strip()
            loopback_devices[base_name] = dev

        desktop_sources = []
        num_devices = self.p.get_device_count()
        for idx in range(num_devices):
            try:
                info = self.p.get_device_info_by_index(idx)
            except Exception:
                continue

            if info["hostApi"] != self.wasapi_api_index:
                continue
            if info["maxOutputChannels"] <= 0:
                continue

            name = info["name"]
            # Exclude virtual cable inputs from desktop sources unless user has nothing else
            is_virtual = any(kw in name.lower() for kw in VIRTUAL_CABLE_KEYWORDS)

            matching_loopback = loopback_devices.get(name)
            if not matching_loopback:
                # Try fuzzy matching
                for lb_name, lb_dev in loopback_devices.items():
                    if name in lb_name or lb_name in name:
                        matching_loopback = lb_dev
                        break

            if matching_loopback:
                is_default = (idx == default_out_idx or name == default_out_name)
                desktop_sources.append({
                    "id": idx,
                    "name": name,
                    "display_name": f"{name}{' (Windows Default)' if is_default else ''}",
                    "loopback_info": matching_loopback,
                    "output_info": info,
                    "is_default": is_default,
                    "is_virtual": is_virtual
                })

        # Sort so default is first, then real outputs, then virtual
        desktop_sources.sort(key=lambda x: (not x["is_default"], x["is_virtual"], x["name"]))
        return desktop_sources

    def get_target_microphones(self):
        """
        Returns a list of playback endpoints that route to a virtual microphone
        (e.g., SteelSeries Sonar - Microphone, CABLE Input).
        """
        if self.wasapi_api_index is None:
            return []

        targets = []
        num_devices = self.p.get_device_count()
        for idx in range(num_devices):
            try:
                info = self.p.get_device_info_by_index(idx)
            except Exception:
                continue

            if info["hostApi"] != self.wasapi_api_index:
                continue
            if info["maxOutputChannels"] <= 0:
                continue

            name = info["name"]
            is_virtual = any(kw in name.lower() for kw in VIRTUAL_CABLE_KEYWORDS)

            display_name = name
            recommended = False
            discord_name = name

            if "sonar - microphone" in name.lower():
                display_name = f"SteelSeries Sonar - Microphone (Detected & Ready)"
                discord_name = "SteelSeries Sonar - Microphone (Virtual Audio Device)"
                recommended = True
            elif "cable input" in name.lower():
                display_name = f"VB-Audio Virtual Cable (CABLE Input)"
                discord_name = "CABLE Output (VB-Audio Virtual Cable)"
                recommended = True
            elif "virtual speakers" in name.lower():
                display_name = f"AudioRelay (Virtual Speakers)"
                discord_name = "Virtual Mic (Virtual Mic for AudioRelay)"

            targets.append({
                "id": idx,
                "name": name,
                "display_name": display_name,
                "discord_name": discord_name,
                "device_info": info,
                "is_virtual": is_virtual,
                "recommended": recommended
            })

        # Prioritize recommended virtual cables first
        virtual_targets = [t for t in targets if t["recommended"] or t["is_virtual"]]
        if virtual_targets:
            virtual_targets.sort(key=lambda x: (not x["recommended"], x["name"]))
            return virtual_targets

        targets.sort(key=lambda x: (not x["recommended"], not x["is_virtual"], x["name"]))
        return targets

    def get_real_microphones(self):
        """
        Returns physical recording microphones (e.g., Logitech PRO X, Arctis Nova Pro).
        Excludes loopback devices and virtual mic outputs.
        """
        if self.wasapi_api_index is None:
            return []

        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_in_idx = wasapi_info.get("defaultInputDevice", -1)
        except Exception:
            default_in_idx = -1

        mics = []
        num_devices = self.p.get_device_count()
        for idx in range(num_devices):
            try:
                info = self.p.get_device_info_by_index(idx)
            except Exception:
                continue

            if info["hostApi"] != self.wasapi_api_index:
                continue
            if info["maxInputChannels"] <= 0:
                continue
            if info.get("isLoopbackDevice", False):
                continue

            name = info["name"]
            is_virtual = any(kw in name.lower() for kw in VIRTUAL_CABLE_KEYWORDS) or "virtual mic" in name.lower()

            is_default = (idx == default_in_idx)
            mics.append({
                "id": idx,
                "name": name,
                "display_name": f"{name}{' (Default)' if is_default else ''}",
                "device_info": info,
                "is_default": is_default,
                "is_virtual": is_virtual
            })

        # Sort: physical mics first, default first
        mics.sort(key=lambda x: (x["is_virtual"], not x["is_default"], x["name"]))
        return mics

    def get_playback_devices(self):
        """
        Returns physical playback devices (headphones, headsets, speakers)
        suitable for user headset monitoring.
        """
        if self.wasapi_api_index is None:
            return []

        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out_idx = wasapi_info.get("defaultOutputDevice", -1)
        except Exception:
            default_out_idx = -1

        playbacks = []
        num_devices = self.p.get_device_count()
        for idx in range(num_devices):
            try:
                info = self.p.get_device_info_by_index(idx)
            except Exception:
                continue

            if info["hostApi"] != self.wasapi_api_index:
                continue
            if info["maxOutputChannels"] <= 0:
                continue

            name = info["name"]
            is_virtual = any(kw in name.lower() for kw in VIRTUAL_CABLE_KEYWORDS)
            is_default = (idx == default_out_idx)

            playbacks.append({
                "id": idx,
                "name": name,
                "display_name": f"{name}{' (Windows Default)' if is_default else ''}",
                "device_info": info,
                "is_default": is_default,
                "is_virtual": is_virtual
            })

        # Physical devices first, then default
        playbacks.sort(key=lambda x: (x["is_virtual"], not x["is_default"], x["name"]))
        return playbacks

    def generate_diagnostic_report(self, config: dict = None) -> str:
        """
        Generates a comprehensive diagnostic report of the system, audio hardware,
        drivers, audio sessions, and configuration for troubleshooting.
        """
        import platform
        import datetime
        lines = []
        lines.append("=" * 60)
        lines.append("  DESKTOP AUDIO TO MIC - DIAGNOSTIC & HARDWARE REPORT")
        lines.append(f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")

        # 1. Environment Info
        lines.append("[1. SYSTEM ENVIRONMENT]")
        lines.append(f"OS: {platform.system()} {platform.release()} (Version {platform.version()})")
        lines.append(f"Architecture: {platform.machine()} ({platform.architecture()[0]})")
        lines.append(f"Python: {platform.python_version()} ({sys.executable})")
        lines.append(f"Frozen Executable: {getattr(sys, 'frozen', False)}")
        lines.append("")

        # 2. Audio Subsystem
        lines.append("[2. WASAPI AUDIO HOST API]")
        if not self.p:
            lines.append("ERROR: PyAudio instance is not initialized!")
        else:
            try:
                count = self.p.get_host_api_count()
                lines.append(f"Total Host APIs: {count}")
                for i in range(count):
                    api_info = self.p.get_host_api_info_by_index(i)
                    is_target = (i == self.wasapi_api_index)
                    lines.append(f"  - [{i}] {api_info.get('name')} (devices: {api_info.get('deviceCount')}) {'<-- ACTIVE WASAPI' if is_target else ''}")
            except Exception as e:
                lines.append(f"Error querying host APIs: {e}")
        lines.append("")

        # 3. Audio Endpoints Enumeration
        lines.append("[3. DISCOVERED AUDIO ENDPOINTS]")
        if self.p:
            try:
                num_devs = self.p.get_device_count()
                lines.append(f"Total PyAudio Devices: {num_devs}")
                for i in range(num_devs):
                    try:
                        d = self.p.get_device_info_by_index(i)
                        api = d.get('hostApi')
                        if api == self.wasapi_api_index:
                            in_ch = d.get('maxInputChannels', 0)
                            out_ch = d.get('maxOutputChannels', 0)
                            rate = int(d.get('defaultSampleRate', 0))
                            is_lb = d.get('isLoopbackDevice', False)
                            type_str = "Loopback" if is_lb else ("Input/Mic" if in_ch > 0 else "Output/Playback")
                            lines.append(f"  [{i:2d}] {d.get('name')} | {type_str} | In:{in_ch} Out:{out_ch} | {rate}Hz")
                    except Exception as dev_err:
                        lines.append(f"  [{i:2d}] Error: {dev_err}")
            except Exception as e:
                lines.append(f"Error enumerating devices: {e}")
        lines.append("")

        # 4. Virtual Audio Cables Status
        lines.append("[4. VIRTUAL AUDIO DRIVERS]")
        targets = self.get_target_microphones()
        if targets:
            for t in targets:
                lines.append(f"  ✓ {t['display_name']} (Device ID: {t['id']})")
        else:
            lines.append("  ⚠️ No virtual microphone endpoints detected!")
            lines.append("     Install VB-Audio Virtual Cable or SteelSeries Sonar.")
        lines.append("")

        # 5. Active Applications Audio Sessions
        lines.append("[5. ACTIVE APPLICATION SESSIONS (pycaw)]")
        try:
            sessions = get_active_audio_sessions()
            if sessions:
                for s in sessions:
                    st = "MUTED" if s.get('is_muted') else "ACTIVE"
                    lines.append(f"  - {s.get('name')} (PID {s.get('pid')}): {int(s.get('volume', 1.0)*100)}% [{st}]")
            else:
                lines.append("  No active audio sessions currently playing sound.")
        except Exception as e:
            lines.append(f"  Could not inspect audio sessions: {e}")
        lines.append("")

        # 6. Current Configuration
        lines.append("[6. SAVED CONFIGURATION (config.json)]")
        try:
            cfg = config if config is not None else load_config()
            lines.append(json.dumps(cfg, indent=2))
        except Exception as e:
            lines.append(f"  Error reading config: {e}")
        lines.append("")

        # 7. Recent Crash / Log History
        lines.append("[7. RECENT LOG HISTORY]")
        log_file = os.path.join(ROOT_DIR, "crash.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    log_tail = f.readlines()[-40:]
                    lines.extend([l.rstrip() for l in log_tail])
            except Exception as e:
                lines.append(f"Error reading crash.log: {e}")
        else:
            lines.append("  No crash.log found (clean run).")
        lines.append("")
        lines.append("=" * 60)
        lines.append("  END OF DIAGNOSTIC REPORT")
        lines.append("=" * 60)

        return "\n".join(lines)

    def terminate(self):
        if self.p:
            self.p.terminate()


def load_config():
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
        except Exception:
            pass
    return default_config


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)


# --- Windows Audio System-Wide Input Helpers ---
import ctypes
from comtypes import GUID, COMMETHOD, IUnknown
import comtypes.client


class IPolicyConfig(IUnknown):
    _iid_ = GUID('{f8679f50-850a-41cf-9c72-430f290290c8}')
    _methods_ = [
        COMMETHOD([], ctypes.HRESULT, 'GetMixFormat', (['in'], ctypes.c_wchar_p, 'pwstrDeviceId'), (['out'], ctypes.c_void_p, 'ppFormat')),
        COMMETHOD([], ctypes.HRESULT, 'GetDeviceFormat'),
        COMMETHOD([], ctypes.HRESULT, 'ResetDeviceFormat'),
        COMMETHOD([], ctypes.HRESULT, 'SetDeviceFormat'),
        COMMETHOD([], ctypes.HRESULT, 'GetProcessingPeriod'),
        COMMETHOD([], ctypes.HRESULT, 'SetProcessingPeriod'),
        COMMETHOD([], ctypes.HRESULT, 'GetShareMode'),
        COMMETHOD([], ctypes.HRESULT, 'SetShareMode'),
        COMMETHOD([], ctypes.HRESULT, 'GetPropertyValue'),
        COMMETHOD([], ctypes.HRESULT, 'SetPropertyValue'),
        COMMETHOD([], ctypes.HRESULT, 'SetDefaultEndpoint', (['in'], ctypes.c_wchar_p, 'pwstrDeviceId'), (['in'], ctypes.c_uint, 'eRole')),
        COMMETHOD([], ctypes.HRESULT, 'SetEndpointVisibility'),
    ]


def get_windows_default_input_name() -> str:
    """Returns the FriendlyName of the current Windows default recording device."""
    try:
        from pycaw.pycaw import AudioUtilities
        from pycaw.constants import EDataFlow, ERole
        enum = AudioUtilities.GetDeviceEnumerator()
        def_capture = enum.GetDefaultAudioEndpoint(EDataFlow.eCapture.value, ERole.eConsole.value)
        def_id = def_capture.GetId()
        for d in AudioUtilities.GetAllDevices():
            if getattr(d, 'id', '') == def_id:
                return getattr(d, 'FriendlyName', 'Default Microphone')
        return "Default Microphone"
    except Exception:
        return "Unknown Device"


def set_windows_default_input_device(device_name_substring: str) -> bool:
    """Sets the Windows default input/recording endpoint by matching substring of friendly name."""
    try:
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetAllDevices()
        target_id = None
        for d in devices:
            name = getattr(d, 'FriendlyName', '')
            dev_id = getattr(d, 'id', '')
            if '{0.0.1.' in dev_id and device_name_substring.lower() in name.lower():
                target_id = dev_id
                break
        if not target_id:
            return False

        policy = comtypes.client.CreateObject(
            GUID('{870af99c-171d-4f9e-af0d-e63df40c2bc9}'),
            interface=IPolicyConfig
        )
        # Roles: 0 = Console (Default), 1 = Multimedia, 2 = Communications
        policy.SetDefaultEndpoint(target_id, 0)
        policy.SetDefaultEndpoint(target_id, 1)
        policy.SetDefaultEndpoint(target_id, 2)
        return True
    except Exception as e:
        print(f"Error setting default endpoint: {e}", file=sys.stderr)
        return False


def get_active_audio_sessions() -> list[dict]:
    """
    Returns active Windows audio sessions (processes playing audio).
    Returns list of dicts: {'pid': int, 'name': str, 'display_name': str, 'volume': float, 'muted': bool}
    """
    results = []
    seen_pids = set()
    try:
        from pycaw.pycaw import AudioUtilities
        sessions = AudioUtilities.GetAllSessions()
        for s in sessions:
            if not s.Process or s.ProcessId in seen_pids:
                continue
            seen_pids.add(s.ProcessId)
            p_name = s.Process.name()
            # Beautify display name
            display = p_name.replace(".exe", "").capitalize()
            if "firefox" in p_name.lower():
                display = "Firefox"
            elif "chrome" in p_name.lower():
                display = "Google Chrome"
            elif "spotify" in p_name.lower():
                display = "Spotify"
            elif "discord" in p_name.lower():
                display = "Discord"
            elif "steam" in p_name.lower():
                display = "Steam"

            vol_ctl = s.SimpleAudioVolume
            vol = float(vol_ctl.GetMasterVolume())
            muted = bool(vol_ctl.GetMute())

            results.append({
                "pid": s.ProcessId,
                "name": p_name,
                "display_name": display,
                "volume": vol,
                "muted": muted
            })
    except Exception as e:
        print(f"Error enumerating audio sessions: {e}", file=sys.stderr)
    return results


def set_session_volume(pid: int, volume: float) -> bool:
    """Sets volume (0.0 to 1.0) for a given process ID."""
    try:
        from pycaw.pycaw import AudioUtilities
        for s in AudioUtilities.GetAllSessions():
            if s.Process and s.ProcessId == pid:
                s.SimpleAudioVolume.SetMasterVolume(float(max(0.0, min(1.0, volume))), None)
                return True
    except Exception as e:
        print(f"Error setting session volume: {e}", file=sys.stderr)
    return False


def set_session_mute(pid: int, mute: bool) -> bool:
    """Sets mute state for a given process ID."""
    try:
        from pycaw.pycaw import AudioUtilities
        for s in AudioUtilities.GetAllSessions():
            if s.Process and s.ProcessId == pid:
                s.SimpleAudioVolume.SetMute(int(mute), None)
                return True
    except Exception as e:
        print(f"Error setting session mute: {e}", file=sys.stderr)
    return False


def solo_session(target_pid: int) -> bool:
    """Mutes all other audio applications except the target PID."""
    try:
        from pycaw.pycaw import AudioUtilities
        for s in AudioUtilities.GetAllSessions():
            if s.Process:
                if s.ProcessId == target_pid:
                    s.SimpleAudioVolume.SetMute(0, None)
                else:
                    s.SimpleAudioVolume.SetMute(1, None)
        return True
    except Exception as e:
        print(f"Error soloing session: {e}", file=sys.stderr)
    return False


def unmute_all_sessions() -> bool:
    """Unmutes all application audio sessions."""
    try:
        from pycaw.pycaw import AudioUtilities
        for s in AudioUtilities.GetAllSessions():
            if s.Process:
                s.SimpleAudioVolume.SetMute(0, None)
        return True
    except Exception as e:
        print(f"Error unmuting all sessions: {e}", file=sys.stderr)
    return False


def open_windows_app_volume_settings():
    """Opens Windows Settings > System > Sound > Volume mixer (App volume and device preferences)."""
    import subprocess
    try:
        subprocess.Popen("start ms-settings:apps-volume", shell=True)
    except Exception as e:
        print(f"Error opening settings: {e}", file=sys.stderr)


