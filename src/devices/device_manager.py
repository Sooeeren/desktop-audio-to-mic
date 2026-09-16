"""
Device Manager for Desktop Audio to Discord Microphone
Enumerates Windows WASAPI and Linux PulseAudio/PipeWire playback, loopback, and recording devices,
identifies virtual audio cables/sinks, and persists user device configurations.
"""

import json
import os
import shutil
import subprocess
import sys

pyaudio = None
if sys.platform == "win32":
    try:
        import pyaudiowpatch as pyaudio
    except ImportError:
        try:
            import pyaudio
        except ImportError:
            pyaudio = None
else:
    try:
        import pyaudio
    except ImportError:
        pyaudio = None


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
    "discordaudiomic",
    "discordvirtualmic",
    "discord_desktop_audio_mic",
    "discord_virtual_microphone",
    "null output",
    "null-sink",
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
        self.p = pyaudio.PyAudio() if pyaudio is not None else None
        self.is_windows = (sys.platform == "win32")
        self.wasapi_api_index = None
        if self.is_windows and self.p is not None:
            self._init_wasapi()

    def _init_wasapi(self):
        try:
            if hasattr(pyaudio, "paWASAPI"):
                wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
                self.wasapi_api_index = wasapi_info["index"]
            else:
                self.wasapi_api_index = None
        except (OSError, KeyError, AttributeError):
            self.wasapi_api_index = None

    # -------------------------------------------------------------
    # Desktop Audio Sources (Loopback)
    # -------------------------------------------------------------

    def get_desktop_sources(self):
        """Returns desktop audio capture sources (WASAPI loopback on Windows, monitor sources on Linux)."""
        if self.is_windows:
            return self._get_windows_desktop_sources()
        else:
            return self._get_linux_desktop_sources()

    def _get_windows_desktop_sources(self):
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
        if hasattr(self.p, "get_loopback_device_info_generator"):
            for dev in self.p.get_loopback_device_info_generator():
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
            is_virtual = any(kw in name.lower() for kw in VIRTUAL_CABLE_KEYWORDS)

            matching_loopback = loopback_devices.get(name)
            if not matching_loopback:
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

        desktop_sources.sort(key=lambda x: (not x["is_default"], x["is_virtual"], x["name"]))
        return desktop_sources

    def _get_linux_desktop_sources(self):
        """Discovers Linux PulseAudio / PipeWire monitor sources for capturing desktop output."""
        if self.p is None:
            return []

        default_sink_name = ""
        pactl_bin = shutil.which("pactl")
        if pactl_bin:
            try:
                res = subprocess.run([pactl_bin, "get-default-sink"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    default_sink_name = res.stdout.strip()
            except Exception:
                pass

        desktop_sources = []
        num_devices = self.p.get_device_count()

        for idx in range(num_devices):
            try:
                info = self.p.get_device_info_by_index(idx)
            except Exception:
                continue

            # On Linux, monitor sources are recording/input endpoints
            if info.get("maxInputChannels", 0) <= 0:
                continue

            name = info.get("name", "")
            lower_name = name.lower()

            # Identify if this is a monitor/loopback source
            is_monitor = (
                "monitor" in lower_name or
                lower_name.endswith(".monitor") or
                lower_name == "pulse" or
                lower_name == "default"
            )
            if not is_monitor:
                continue

            is_virtual = any(kw in lower_name for kw in VIRTUAL_CABLE_KEYWORDS)
            # Check if this monitor belongs to the default output sink
            is_default = False
            if default_sink_name and default_sink_name.lower() in lower_name:
                is_default = True
            elif lower_name in ["pulse", "default"] and not default_sink_name:
                is_default = True

            clean_name = name
            if clean_name.startswith("Monitor of "):
                clean_name = clean_name[len("Monitor of "):]

            display_name = f"{clean_name} (Desktop Loopback){' (System Default)' if is_default else ''}"

            desktop_sources.append({
                "id": idx,
                "name": name,
                "display_name": display_name,
                "loopback_info": info,
                "output_info": info,
                "is_default": is_default,
                "is_virtual": is_virtual
            })

        desktop_sources.sort(key=lambda x: (not x["is_default"], x["is_virtual"], x["name"]))
        return desktop_sources

    # -------------------------------------------------------------
    # Target Microphones (Virtual Cable / Virtual Sink Output)
    # -------------------------------------------------------------

    def get_target_microphones(self):
        """Returns playback endpoints routing to virtual microphone (VB-Cable / Sonar on Win, DiscordAudioMic on Linux)."""
        if self.is_windows:
            return self._get_windows_target_microphones()
        else:
            return self._get_linux_target_microphones()

    def _get_windows_target_microphones(self):
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
                display_name = "SteelSeries Sonar - Microphone (Detected & Ready)"
                discord_name = "SteelSeries Sonar - Microphone (Virtual Audio Device)"
                recommended = True
            elif "cable input" in name.lower():
                display_name = "VB-Audio Virtual Cable (CABLE Input)"
                discord_name = "CABLE Output (VB-Audio Virtual Cable)"
                recommended = True
            elif "virtual speakers" in name.lower():
                display_name = "AudioRelay (Virtual Speakers)"
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

        virtual_targets = [t for t in targets if t["recommended"] or t["is_virtual"]]
        if virtual_targets:
            virtual_targets.sort(key=lambda x: (not x["recommended"], x["name"]))
            return virtual_targets

        targets.sort(key=lambda x: (not x["recommended"], not x["is_virtual"], x["name"]))
        return targets

    def _get_linux_target_microphones(self):
        """Discovers Linux virtual audio sinks (DiscordAudioMic or null-sinks) for output routing."""
        if self.p is None:
            return []

        targets = []
        num_devices = self.p.get_device_count()

        for idx in range(num_devices):
            try:
                info = self.p.get_device_info_by_index(idx)
            except Exception:
                continue

            if info.get("maxOutputChannels", 0) <= 0:
                continue

            name = info.get("name", "")
            lower_name = name.lower()
            is_virtual = any(kw in lower_name for kw in VIRTUAL_CABLE_KEYWORDS)

            recommended = False
            display_name = name
            discord_name = name

            if "discordaudiomic" in lower_name or "discord_desktop_audio_mic" in lower_name:
                display_name = "Discord Virtual Mic (DiscordAudioMic - Ready ✨)"
                discord_name = "Discord_Virtual_Microphone (or DiscordAudioMic.monitor)"
                recommended = True
                is_virtual = True
            elif "null" in lower_name:
                display_name = f"Virtual Null Sink ({name})"
                discord_name = f"{name}.monitor"
                is_virtual = True

            targets.append({
                "id": idx,
                "name": name,
                "display_name": display_name,
                "discord_name": discord_name,
                "device_info": info,
                "is_virtual": is_virtual,
                "recommended": recommended
            })

        virtual_targets = [t for t in targets if t["recommended"] or t["is_virtual"]]
        if virtual_targets:
            virtual_targets.sort(key=lambda x: (not x["recommended"], x["name"]))
            return virtual_targets

        targets.sort(key=lambda x: (not x["recommended"], not x["is_virtual"], x["name"]))
        return targets

    # -------------------------------------------------------------
    # Real Voice Microphones
    # -------------------------------------------------------------

    def get_real_microphones(self):
        """Returns physical recording microphones."""
        if self.is_windows:
            return self._get_windows_real_microphones()
        else:
            return self._get_linux_real_microphones()

    def _get_windows_real_microphones(self):
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

        mics.sort(key=lambda x: (x["is_virtual"], not x["is_default"], x["name"]))
        return mics

    def _get_linux_real_microphones(self):
        """Discovers physical microphones on Linux, filtering out monitor loopbacks."""
        if self.p is None:
            return []

        default_source_name = ""
        pactl_bin = shutil.which("pactl")
        if pactl_bin:
            try:
                res = subprocess.run([pactl_bin, "get-default-source"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    default_source_name = res.stdout.strip()
            except Exception:
                pass

        mics = []
        num_devices = self.p.get_device_count()

        for idx in range(num_devices):
            try:
                info = self.p.get_device_info_by_index(idx)
            except Exception:
                continue

            if info.get("maxInputChannels", 0) <= 0:
                continue

            name = info.get("name", "")
            lower_name = name.lower()

            # Filter out monitor loopbacks from voice microphone choices
            if "monitor" in lower_name or lower_name.endswith(".monitor"):
                continue

            is_virtual = any(kw in lower_name for kw in VIRTUAL_CABLE_KEYWORDS)
            is_default = False
            if default_source_name and default_source_name.lower() in lower_name:
                is_default = True

            mics.append({
                "id": idx,
                "name": name,
                "display_name": f"{name}{' (Default)' if is_default else ''}",
                "device_info": info,
                "is_default": is_default,
                "is_virtual": is_virtual
            })

        mics.sort(key=lambda x: (x["is_virtual"], not x["is_default"], x["name"]))
        return mics

    def terminate(self):
        if self.p:
            try:
                self.p.terminate()
            except Exception:
                pass


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
        "auto_start": False
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


# -------------------------------------------------------------
# Cross-Platform System-Wide Input Helpers
# -------------------------------------------------------------

IPolicyConfig = None
if sys.platform == "win32":
    try:
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
    except ImportError:
        IPolicyConfig = None


def get_windows_default_input_name() -> str:
    """Returns the FriendlyName of the current Windows default recording device."""
    if sys.platform != "win32":
        return get_linux_default_input_name()

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
        return "Default Microphone"


def set_windows_default_input_device(device_name_substring: str) -> bool:
    """Sets the Windows default input/recording endpoint by matching substring of friendly name."""
    if sys.platform != "win32":
        return set_linux_default_input_device(device_name_substring)

    if IPolicyConfig is None:
        return False

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
        policy.SetDefaultEndpoint(target_id, 0)
        policy.SetDefaultEndpoint(target_id, 1)
        policy.SetDefaultEndpoint(target_id, 2)
        return True
    except Exception as e:
        print(f"Error setting default endpoint: {e}", file=sys.stderr)
        return False


def get_linux_default_input_name() -> str:
    """Returns the current default audio input/recording source on Linux via pactl."""
    pactl_bin = shutil.which("pactl")
    if not pactl_bin:
        return "Default System Input"
    try:
        res = subprocess.run([pactl_bin, "get-default-source"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            source = res.stdout.strip()
            if "DiscordVirtualMic" in source or "DiscordAudioMic" in source:
                return "Discord_Virtual_Microphone"
            return source
    except Exception:
        pass
    return "Default Microphone"


def set_linux_default_input_device(device_name_substring: str) -> bool:
    """Sets the Linux default input/recording source using pactl."""
    pactl_bin = shutil.which("pactl")
    if not pactl_bin:
        return False
    try:
        if any(k in device_name_substring.lower() for k in ["discord", "virtual", "cable", "null"]):
            res = subprocess.run([pactl_bin, "list", "short", "sources"], capture_output=True, text=True, timeout=2)
            target = "DiscordVirtualMic"
            if "DiscordVirtualMic" not in res.stdout and "DiscordAudioMic.monitor" in res.stdout:
                target = "DiscordAudioMic.monitor"
            r = subprocess.run([pactl_bin, "set-default-source", target], capture_output=True, timeout=2)
            return r.returncode == 0
        else:
            res = subprocess.run([pactl_bin, "list", "short", "sources"], capture_output=True, text=True, timeout=2)
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    src_name = parts[1]
                    if device_name_substring.lower() in src_name.lower():
                        r = subprocess.run([pactl_bin, "set-default-source", src_name], capture_output=True, timeout=2)
                        return r.returncode == 0
    except Exception as e:
        print(f"Error setting Linux default source: {e}", file=sys.stderr)
    return False


def get_system_default_input_name() -> str:
    """Unified cross-platform helper to retrieve default recording device name."""
    if sys.platform == "win32":
        return get_windows_default_input_name()
    else:
        return get_linux_default_input_name()


def set_system_default_input_device(device_name_substring: str) -> bool:
    """Unified cross-platform helper to set system default recording device."""
    if sys.platform == "win32":
        return set_windows_default_input_device(device_name_substring)
    else:
        return set_linux_default_input_device(device_name_substring)


