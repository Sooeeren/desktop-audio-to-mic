# 🎙️ Discord Desktop Audio Mic

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue.svg)](https://github.com/Sooeeren/desktop-audio-to-mic)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![UI](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt-41CD52.svg?logo=qt&logoColor=white)](https://qt.io)

> [!NOTE]
> **Made with AI**: This entire application, low-latency audio capture & mixing engine, and dark Discord-style user interface were designed, developed, and optimized with AI (Google Antigravity & Google DeepMind agentic coding).

Stream your desktop audio (music, YouTube, game sounds, browser audio) directly into Discord as a virtual microphone input. Friends in your Discord voice channel will hear your desktop sound in uncompressed, full-fidelity stereo!

---

## ✨ Key Features

- **Cross-Platform Audio Capture**:
  - **Windows**: Direct WASAPI Loopback captures crystal-clear digital audio directly from Windows Core Audio without muting your normal headphones or speakers.
  - **Linux**: Native PulseAudio & PipeWire monitor capture routes desktop output directly with zero quality loss.
- **Zero Configuration Virtual Microphones**:
  - **Windows**: Pairs with SteelSeries Sonar, VB-Audio Virtual Cable, or AudioRelay. Includes a 1-click VB-Cable installer if needed.
  - **Linux**: Native 1-click virtual microphone creation via `pactl` (`module-null-sink` & `module-remap-source`) — **no 3rd-party drivers needed!**
- **High-Contrast Toggle Switches**: Eye-catching custom toggle switches clearly displaying `[ ✓ ON ]` (vibrant green) or `[ OFF ]` (slate gray).
- **Pro Audio Visualizer Graph**: 32-band log-frequency equalizer bars with neon gradients (`#5865F2` -> `#23A55A` -> `#F0B232` -> `#F23F43`), floating white peak caps, oscilloscope waveform overlay, and real-time dB volume readout.
- **System-Wide Input Source Switching**: Option to set the virtual microphone as your default input device with 1 click on Windows and Linux, allowing any application (OBS, Zoom, browser) to receive desktop audio as a microphone.
- **Optional Voice Mixing**: Mix your physical headset microphone together with desktop audio so friends hear both your voice and your game/music simultaneously.
- **Independent Volume & Mute**: Sliders to adjust desktop volume and voice volume independently (from 0% to 200%), plus instant mute buttons.
- **Discord Optimized**: Clean dark UI matching Discord's look and feel with instant Studio profile setup.
- **System Tray Support**: Minimizes to system tray so it can run unobtrusively in the background while gaming.

---

## 🚀 Download & Installation

### Option 1: Standalone Executable (Windows)
1. Head over to the [**Releases**](../../releases) tab.
2. Download **`DiscordDesktopAudioMic.exe`**.
3. Double-click to run!
   - **No Python or libraries required**: Everything is self-contained in the executable.
   - **Virtual Audio Driver**: If your PC already has a virtual audio device (like *SteelSeries Sonar*), it works instantly. If you don't have one yet, click **"Install VB-Cable"** right inside the app to install VB-Cable in seconds.

### Option 2: Run from Source (Windows & Linux)

#### 1. Clone the repository:
```bash
git clone https://github.com/Sooeeren/desktop-audio-to-mic.git
cd desktop-audio-to-mic
```

#### 2. Install dependencies:

**On Linux (Debian / Ubuntu / Linux Mint / Pop!_OS):**
```bash
sudo apt update
sudo apt install python3-pyside6 libportaudio2 portaudio19-dev pulseaudio-utils
pip install -r requirements.txt
```

**On Linux (Fedora):**
```bash
sudo dnf install python3-pyside6 portaudio-devel pulseaudio-utils
pip install -r requirements.txt
```

**On Linux (Arch Linux):**
```bash
sudo pacman -S python-pyside6 portaudio libpulse
pip install -r requirements.txt
```

**On Windows:**
```bash
pip install -r requirements.txt
```

#### 3. Run the app:

**On Linux:**
```bash
chmod +x run.sh
./run.sh
# or python3 main.py
```

**On Windows:**
```bash
run.bat
# or python main.py
```

---

## 🛡️ Windows SmartScreen Note ("Windows protected your PC")

When downloading and launching `DiscordDesktopAudioMic.exe` for the first time, Windows Defender SmartScreen may display a blue popup saying *"Windows protected your PC"*:

- **Why this appears**: Microsoft Defender SmartScreen displays this prompt for any newly uploaded `.exe` from the internet that does not have an expensive commercial EV Code Signing Certificate ($400+/year).
- **How to launch**: Simply click **"More info"** and then click **"Run anyway"**. Windows will remember your choice and won't ask again.
- **100% Safe & Open Source**: This software is completely free, open-source, and does not collect any data or contain telemetry. You can inspect every line of code directly in this repository.

---

## 🎧 Discord Settings (Quick & Simple!)

To stream full-fidelity stereo sound without voice filters cutting out game sound or music:

1. In the app under **"3. Target Virtual Microphone"**:
   - **On Windows**: Check the blue box showing the device to select (e.g. `CABLE Output (VB-Audio Virtual Cable)` or `SteelSeries Sonar - Microphone`).
   - **On Linux**: Click **"Setup Virtual Mic"** if not yet created. The app creates `Discord_Virtual_Microphone` in PulseAudio/PipeWire.
2. In Discord, go to **User Settings ⚙️** (bottom left) -> **Voice & Video**.
3. Under **Input Device**, select:
   - **Windows**: `CABLE Output (VB-Audio Virtual Cable)` (or `SteelSeries Sonar - Microphone`).
   - **Linux**: `Discord_Virtual_Microphone` (or `Monitor of Discord_Desktop_Audio_Mic`).
4. Set **Input Profile** (or Audio Profile) to **Studio**.
   - ✨ **That's it!** Studio profile transmits full-fidelity, uncompressed stereo sound directly into the voice channel without Krisp or voice filters cutting out game sound, music, or bass.

---

## 🌐 System Input Source

Want other applications (browsers, OBS, Zoom, audio recorders) across your system to hear desktop audio as a microphone?
- In the program's **"System Input"** card:
  - Click **"Set Default"**: Instantly sets your virtual mic as the system-wide default recording input on Windows or Linux.
  - Click **"Restore"**: Instantly reverts back to your physical microphone whenever needed.
  - Click **"⚙️"**: Opens system audio and sound settings directly (`mmsys.cpl` on Windows; `pavucontrol` or desktop settings on Linux).

---

## 📁 File Structure

```text
desktop-audio-to-mic/
├── src/
│   ├── audio/
│   │   └── audio_engine.py       # Cross-platform capture, resampling, keep-alive, queues
│   ├── devices/
│   │   ├── device_manager.py     # WASAPI & PulseAudio/PipeWire device discovery & default switching
│   │   └── virtual_driver.py     # Windows VB-Cable installer & Linux native virtual mic setup
│   └── ui/
│       └── gui.py                # Discord dark UI, toggle switches, Pro visualizer
├── assets/                       # Visual assets and icons
├── main.py                       # Application entry point & High-DPI scaling
├── run.bat                       # Double-clickable Windows launcher
├── run.sh                        # Executable Linux launcher script
├── test_suite.py                 # Automated testing suite
├── requirements.txt              # Cross-platform dependency specifications
├── config.json                   # User settings persistence
├── LICENSE                       # MIT License
└── README.md
```

---

## 🔨 Building Standalone Binaries

You can bundle the entire application into a standalone executable using PyInstaller:

**On Windows:**
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "DiscordDesktopAudioMic" main.py
# Output binary: dist/DiscordDesktopAudioMic.exe
```

**On Linux:**
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "DiscordDesktopAudioMic" main.py
# Output binary: dist/DiscordDesktopAudioMic
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## Made with AI

This project was developed with the assistance of AI (Google Antigravity & Google DeepMind agentic coding). All code, architecture, and documentation were generated, reviewed, and tested collaboratively.
