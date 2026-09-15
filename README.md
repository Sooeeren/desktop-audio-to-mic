# 🎙️ Discord Desktop Audio Mic

[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-blue.svg)](https://microsoft.com)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![UI](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt-41CD52.svg?logo=qt&logoColor=white)](https://qt.io)
[![Made with AI](https://img.shields.io/badge/Made%20with-AI%20%F0%9F%A4%96-8A2BE2.svg)](#-made-with-ai)

> [!NOTE]
> 🤖 **Made with AI**: This entire application, low-latency Windows WASAPI loopback engine, and dark Discord-style user interface were designed, developed, and optimized with **AI** (Google Antigravity & Google DeepMind agentic coding).

Stream your desktop audio (music, YouTube, game sounds, browser audio) directly into Discord as a virtual microphone input. Friends in your Discord voice channel will hear your desktop sound in uncompressed, full-fidelity stereo!

---

## ✨ Key Features

- **Direct WASAPI Loopback**: Captures crystal-clear digital audio directly from Windows Core Audio without muting your normal headphones or speakers.
- **Works Out of the Box**: Automatically detects and pairs with your existing virtual audio device (`SteelSeries Sonar Virtual Audio Device`) or `VB-Audio Virtual Cable`.
- **High-Contrast Toggle Switches**: Eye-catching custom toggle switches clearly displaying `[ ✓ ON ]` (vibrant green) or `[ OFF ]` (slate gray).
- **Pro Audio Visualizer Graph**: 32-band log-frequency equalizer bars with neon gradients (`#5865F2` -> `#23A55A` -> `#F0B232` -> `#F23F43`), floating white peak caps, oscilloscope waveform overlay, and real-time dB volume readout.
- **Windows System Input Source**: Option to set the virtual microphone as the Windows default input device with 1 click, allowing any application across Windows (OBS, Zoom, browser) to receive desktop audio as a microphone.
- **Optional Voice Mixing**: Mix your physical headset microphone together with desktop audio so friends hear both your voice and your game/music simultaneously.
- **Independent Volume & Mute**: Sliders to adjust desktop volume and voice volume independently (from 0% to 200%), plus instant mute buttons.
- **Discord Optimized**: Clean dark UI matching Discord's look and feel with instant Studio profile setup.
- **System Tray Support**: Minimizes to system tray so it can run unobtrusively in the background while gaming.
- **1-Click VB-Cable Installer**: Built-in helper to download and install VB-Audio Virtual Cable if you prefer a dedicated cable.

---

## 🚀 Download & Installation

### Option 1: Standalone Executable (No Python Required)
1. Head over to the [**Releases**](../../releases) tab.
2. Download **`DiscordDesktopAudioMic.exe`**.
3. Double-click to run! No installation or setup needed.

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

## 🎧 Discord Settings (Quick & Simple!)

To stream with full studio fidelity without voice filters cutting out game sound or music:

1. In Discord, click **User Settings ⚙️** (bottom left) -> **Voice & Video**.
2. Set **Input Device** to:
   - `SteelSeries Sonar - Microphone (SteelSeries Sonar Virtual Audio Device)` *(or `CABLE Output`)*.
3. Change **Input Profile** (or Audio Profile) to **Studio**.
   - ✨ **That's it!** Studio mode automatically bypasses Krisp and compression filters, transmitting full-fidelity stereo audio into your voice channel.

---

## 🌐 Windows System Input Source

Want other Windows applications (browsers, OBS, Zoom, Windows Sound Recorder) to hear desktop audio as a microphone?
- In the program's **"Windows System Input Source"** card:
  - Click **"Set Virtual Mic as Windows Default Input"**: Instantly sets your virtual mic as the system-wide default recording endpoint in Windows.
  - Click **"Restore Headset Mic as Default"**: Instantly reverts back to your physical microphone whenever needed.
  - Click **"Open Windows Sound Settings"**: Opens Windows Sound and Recording settings directly.

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

## 📁 File Structure

- `main.py`: Entry point and high-DPI application startup.
- `gui.py`: Modern Qt/PySide6 interface with high-contrast toggle switches, Pro Audio visualizer graph, and wheel-safe scroll area.
- `audio_engine.py`: WASAPI loopback capture, resampling, keep-alive stream, thread-safe queuing, and mixing engine.
- `device_manager.py`: Audio device enumeration, virtual cable auto-discovery, and Windows default endpoint switching (`IPolicyConfig`).
- `virtual_driver.py`: 1-click installer utility for VB-Audio Virtual Cable.
- `config.json`: Automatically remembers your selected devices and volume levels.
- `run.bat`: Double-clickable Windows launcher.
- `requirements.txt`: Python dependencies.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🤖 Made with AI

This project was developed with the assistance of AI (Google Antigravity & Google DeepMind agentic coding). All code, architecture, and documentation were generated, reviewed, and tested collaboratively.
