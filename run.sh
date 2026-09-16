#!/usr/bin/env bash
# Discord Desktop Audio Mic - Linux Launcher Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎙️  Discord Desktop Audio Mic - Linux Launcher"
echo "-----------------------------------------------"

# Detect Python 3 command
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3 was not found. Please install Python 3."
    exit 1
fi

# Check for required python modules
$PYTHON_CMD -c "import PySide6, sounddevice, numpy" >/dev/null 2>&1 || {
    echo "⚠️  Missing required Python packages. Attempting to install from requirements.txt..."
    if [ -f "requirements.txt" ]; then
        $PYTHON_CMD -m pip install -r requirements.txt
    else
        echo "❌ requirements.txt not found!"
        exit 1
    fi
}

# Check for pactl (PulseAudio / PipeWire)
if ! command -v pactl &>/dev/null; then
    echo "⚠️  Note: 'pactl' utility was not found."
    echo "   For automatic virtual microphone creation, please install:"
    echo "   - Debian/Ubuntu/Mint: sudo apt install pulseaudio-utils"
    echo "   - Fedora: sudo dnf install pulseaudio-utils"
    echo "   - Arch Linux: sudo pacman -S libpulse"
fi

echo "🚀 Launching Discord Desktop Audio Mic..."
exec $PYTHON_CMD main.py "$@"
