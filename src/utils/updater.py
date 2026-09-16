"""
GitHub Version Checker for Desktop Audio to Mic.
Checks remote version.txt from GitHub asynchronously.
"""

import re
import urllib.request
import urllib.error
from PySide6.QtCore import QThread, Signal

CURRENT_VERSION = "1.5.0"
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Sooeeren/desktop-audio-to-mic/main/version.txt"
RELEASES_URL = "https://github.com/Sooeeren/desktop-audio-to-mic/releases/latest"


def parse_version_tuple(v_str: str) -> tuple:
    """Extracts integer version tuple from string (e.g. 'v1.5.0' -> (1, 5, 0))."""
    nums = re.findall(r"\d+", v_str.strip())
    return tuple(int(n) for n in nums) if nums else (0, 0, 0)


def is_version_newer(latest_str: str, current_str: str = CURRENT_VERSION) -> bool:
    """Returns True if latest_str is strictly newer than current_str."""
    return parse_version_tuple(latest_str) > parse_version_tuple(current_str)


def check_github_version(timeout: float = 3.5) -> tuple[bool, str, str, str | None]:
    """
    Synchronously fetches remote version from GitHub.
    Returns: (has_update, latest_version, releases_url, error_message)
    """
    try:
        req = urllib.request.Request(
            REMOTE_VERSION_URL,
            headers={"User-Agent": "DesktopAudioToMic-Updater/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                raw_text = response.read().decode("utf-8").strip()
                latest = raw_text.splitlines()[0].strip().lstrip("v")
                newer = is_version_newer(latest, CURRENT_VERSION)
                return newer, latest, RELEASES_URL, None
            return False, CURRENT_VERSION, RELEASES_URL, f"HTTP {response.status}"
    except Exception as e:
        return False, CURRENT_VERSION, RELEASES_URL, str(e)


class UpdateCheckWorker(QThread):
    """Background worker thread for non-blocking startup and manual checks."""
    # (has_update: bool, latest_version: str, release_url: str, error_msg: str or None)
    result_ready = Signal(bool, str, str, str)

    def __init__(self, timeout: float = 3.5, parent=None):
        super().__init__(parent)
        self.timeout = timeout

    def run(self):
        has_update, latest, url, err = check_github_version(self.timeout)
        self.result_ready.emit(has_update, latest, url, err or "")
