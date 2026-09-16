#!/usr/bin/env bash
# ==============================================================================
# Desktop Audio to Mic - Linux Launcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================="
echo "  Desktop Audio to Mic (Linux Edition)"
echo "  PipeWire & PulseAudio Low-Latency Audio Streamer"
echo "========================================================="

# 1. Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 is not installed or not found in PATH."
    echo "Please install Python 3 (e.g., sudo apt install python3 python3-venv python3-pip)"
    exit 1
fi

# 2. Check pactl (PipeWire / PulseAudio CLI)
if ! command -v pactl &>/dev/null; then
    echo "[WARNING] 'pactl' command was not found."
    echo "This app uses pactl to automatically create virtual mic endpoints."
    echo "Install it via:"
    echo "  Debian/Ubuntu: sudo apt install pulseaudio-utils (or pipewire-pulse)"
    echo "  Fedora:        sudo dnf install pulseaudio-utils"
    echo "  Arch Linux:    sudo pacman -S libpulse (or pipewire-pulse)"
    echo ""
fi

# 3. Virtual environment setup
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[SETUP] Creating virtual environment in .venv..."
    python3 -m venv "$VENV_DIR" || {
        echo "[ERROR] Failed to create virtual environment."
        echo "Try: sudo apt install python3-venv"
        exit 1
    }
fi

source "$VENV_DIR/bin/activate"

# 4. Check dependencies
if ! python3 -c "import PySide6, pyaudio, numpy" &>/dev/null; then
    echo "[SETUP] Installing Python dependencies from requirements.txt..."
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt || {
        echo ""
        echo "[ERROR] Failed to install Python dependencies."
        echo "If PyAudio installation failed, install PortAudio development headers:"
        echo "  Debian/Ubuntu: sudo apt install portaudio19-dev python3-pyaudio"
        echo "  Fedora:        sudo dnf install portaudio-devel"
        echo "  Arch Linux:    sudo pacman -S portaudio"
        exit 1
    }
fi

# 5. Launch application
echo "[LAUNCH] Starting Desktop Audio to Mic..."
python3 main.py "$@"
