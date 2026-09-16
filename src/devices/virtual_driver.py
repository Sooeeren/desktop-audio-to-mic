"""
Virtual Audio Driver Helper
Checks for virtual audio devices and provides a 1-click installer for VB-Audio Virtual Cable.
"""

import ctypes
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

VB_CABLE_URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def install_vbcable(progress_callback=None):
    """
    Downloads and launches the VB-Audio CABLE installer with UAC prompt.
    """
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
