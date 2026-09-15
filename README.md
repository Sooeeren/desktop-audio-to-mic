# 🎙️ Discord Desktop Audio Mic

[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-blue.svg)](https://microsoft.com)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![UI](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt-41CD52.svg?logo=qt&logoColor=white)](https://qt.io)

> [!NOTE]
> **Made with AI**: This entire application, low-latency Windows WASAPI loopback engine, and dark Discord-style user interface were designed, developed, and optimized with AI (Google Antigravity & Google DeepMind agentic coding).

Stream your desktop audio (music, YouTube, game sounds, browser audio) directly into Discord as a virtual microphone input. Friends in your Discord voice channel will hear your desktop sound in uncompressed, full-fidelity stereo!

---

## ✨ Key Features

- **Direct WASAPI Loopback**: Captures crystal-clear digital audio directly from Windows Core Audio without muting your normal headphones or speakers.
- **Works Out of the Box**: Automatically detects and pairs with your existing virtual audio device (`SteelSeries Sonar Virtual Audio Device`, `VB-Audio Virtual Cable`, or `AudioRelay`).
- **High-Contrast Toggle Switches**: Eye-catching custom toggle switches clearly displaying `[ ✓ ON ]` (vibrant green) or `[ OFF ]` (slate gray).
- **Pro Audio Visualizer Graph**: 32-band log-frequency equalizer bars with neon gradients (`#5865F2` -> `#23A55A` -> `#F0B232` -> `#F23F43`), floating white peak caps, oscilloscope waveform overlay, and real-time dB volume readout.
- **Windows System Input Source**: Option to set the virtual microphone as the Windows default input device with 1 click, allowing any application across Windows (OBS, Zoom, browser) to receive desktop audio as a microphone.
- **Optional Voice Mixing**: Mix your physical headset microphone together with desktop audio so friends hear both your voice and your game/music simultaneously.
- **Independent Volume & Mute**: Sliders to adjust desktop volume and voice volume independently (from 0% to 200%), plus instant mute buttons.
- **Discord Optimized**: Clean dark UI matching Discord's look and feel with instant Studio profile setup.
- **System Tray Support**: Minimizes to system tray so it can run unobtrusively in the background while gaming.
- **1-Click VB-Cable Installer**: Built-in helper to download and install VB-Audio Virtual Cable if your system doesn't have a virtual audio cable yet.

---

## 🚀 Download & Installation

### Option 1: Standalone Executable (No Python Required)
1. Head over to the [**Releases**](../../releases) tab.
2. Download **`DiscordDesktopAudioMic.exe`**.
3. Double-click to run!
   - **No Python or libraries required**: Everything is self-contained in the executable.
   - **Virtual Audio Driver**: If your PC already has a virtual audio device (like *SteelSeries Sonar*), it works instantly. If you don't have one yet, click **"Install Dedicated VB-Cable Driver"** right inside the app to install VB-Cable in 10 seconds.

### Option 2: Run from Source
1. Clone the repository:
   ```bash
   git clone https://github.com/Sooeeren/desktop-mic-converter.git
   cd desktop-mic-converter
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python main.py
   # or double-click run.bat on Windows
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

1. In the app under **"2. Target Virtual Microphone"**, check the blue box right below your selection — it shows the exact device name to choose!
   - Examples: `CABLE Output (VB-Audio Virtual Cable)`, `SteelSeries Sonar - Microphone`, or whichever virtual cable you selected.
2. In Discord, go to **User Settings ⚙️** (bottom left) -> **Voice & Video**.
3. Under **Input Device**, select that exact matching virtual microphone name.
4. Set **Input Profile** (or Audio Profile) to **Studio**.
   - ✨ **That's it!** Studio profile transmits full-fidelity, uncompressed stereo sound directly into the voice channel without Krisp or voice filters cutting out game sound, music, or bass.

---

## 🌐 Windows System Input Source

Want other Windows applications (browsers, OBS, Zoom, Windows Sound Recorder) to hear desktop audio as a microphone?
- In the program's **"Windows System Input Source"** card:
  - Click **"Set Virtual Mic as Windows Default Input"**: Instantly sets your virtual mic as the system-wide default recording endpoint in Windows.
  - Click **"Restore Headset Mic as Default"**: Instantly reverts back to your physical microphone whenever needed.
  - Click **"Open Windows Sound Settings"**: Opens Windows Sound and Recording settings directly.

---

## 📁 File Structure

```text
desktop-mic-converter/
├── src/
│   ├── audio/
│   │   └── audio_engine.py       # WASAPI loopback capture, resampling, keep-alive, queues
│   ├── devices/
│   │   ├── device_manager.py     # Device discovery, virtual cable pairing, IPolicyConfig
│   │   └── virtual_driver.py     # 1-click VB-Audio Cable installer utility
│   └── ui/
│       └── gui.py                # Discord dark UI, toggle switches, Pro visualizer
├── assets/                       # Visual assets and icons
├── main.py                       # Application entry point & high-DPI scaling
├── run.bat                       # Double-clickable Windows launcher
├── test_suite.py                 # Automated testing suite
├── requirements.txt              # Dependency specifications
├── config.json                   # User settings persistence
├── LICENSE                       # MIT License
└── README.md
```

---

## 🔨 Building the Standalone .exe

You can bundle the entire application into a standalone Windows `.exe` using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "DiscordDesktopAudioMic" main.py
```

The compiled binary will be placed in the `dist/` directory:
```
dist/DiscordDesktopAudioMic.exe
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## Made with AI

This project was developed with the assistance of AI (Google Antigravity & Google DeepMind agentic coding). All code, architecture, and documentation were generated, reviewed, and tested collaboratively.
