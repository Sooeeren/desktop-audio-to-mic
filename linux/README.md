# Desktop Audio to Mic (Linux Edition) 🐧🎙️

A dedicated Linux edition of **Desktop Audio to Mic** engineered specifically for **PipeWire** and **PulseAudio**. Stream high-fidelity desktop sound and your microphone together into Discord, OBS, or any voice channel with zero audio quality loss and sub-20ms latency.

---

## ✨ Features

- **No Third-Party Virtual Cable Drivers Needed**: Leverages native Linux audio server modules (`module-null-sink` and `module-remap-source`) via `pactl`.
- **Full Studio Fidelity**: Mixes 48 kHz stereo desktop audio and your microphone without distortion.
- **PipeWire & PulseAudio Ready**: Seamlessly works on modern Linux distributions (Ubuntu 22.04+, Fedora 38+, Arch Linux, Linux Mint, Debian 12+, Pop!_OS, etc.).
- **Live 48-Band Audio Visualizer**: Real-time FFT spectrum visualizer and oscilloscope overlay.
- **Widescreen Dashboard**: All controls, gradient sliders, VU meters, and endpoints visible in one screen.
- **One-Click Native Setup**: Creates and activates virtual devices directly from the UI, with shortcuts to `pavucontrol` (Volume Control) and system audio settings.
- **System Tray Support**: Minimize to tray with global shortcut toggles.

---

## 🚀 Quick Start

### 1. Prerequisites

Ensure you have Python 3 and standard audio utilities installed:

#### Ubuntu / Debian / Pop!_OS / Linux Mint
```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip pulseaudio-utils portaudio19-dev pavucontrol
```

#### Fedora
```bash
sudo dnf install python3 python3-pip pulseaudio-utils portaudio-devel pavucontrol
```

#### Arch Linux / Manjaro
```bash
sudo pacman -S python python-pip libpulse portaudio pavucontrol
```

> [!NOTE]
> Modern distributions using PipeWire (like Ubuntu 23+, Fedora, Arch) already provide `pactl` compatibility via `pipewire-pulse`.

### 2. Run the App

From the `linux/` folder:

```bash
chmod +x run.sh
./run.sh
```

`run.sh` will automatically create a local virtual environment (`.venv`), install dependencies from `requirements.txt`, verify system endpoints, and launch the application.

---

## 🎧 Discord Setup Guide

To stream music, game audio, and your voice into Discord with studio fidelity:

1. **In the Desktop Audio to Mic UI**:
   - Click **"Create / Enable Virtual Mic"** (or it will create automatically on launch).
   - Select your **Desktop Audio Capture** device (e.g., your default output `.monitor` or specific sink).
   - Select your **Microphone** (or choose *None* if you only want to stream game/desktop audio).
   - Click **"Start Streaming"**.

2. **In Discord**:
   - Open **User Settings** ⚙️ *(bottom left)* -> **Voice & Video**.
   - Set **Input Device** to:
     ```
     Virtual Discord Stream Mic (DiscordDesktopMic)
     ```
   - Change **Audio Profile** (or Input Profile) to:
     ```
     Studio
     ```
   - Disable **Krisp / Noise Suppression** and **Echo Cancellation** in Discord (Studio mode handles this automatically).

> ✨ **Done!** Your voice channel will receive crystal-clear, full-frequency stereo sound directly from your Linux desktop alongside your voice.

---

## 🛠️ How It Works Internally

Unlike Windows which requires kernel virtual audio drivers (such as VB-CABLE or SteelSeries Sonar), Linux audio servers (PipeWire and PulseAudio) have built-in virtual routing:

1. **Null Sink (`DiscordDesktopAudio`)**: An in-memory audio sink created via `pactl load-module module-null-sink`. The audio engine routes mixed audio here.
2. **Remap Source (`DiscordDesktopMic`)**: Created via `pactl load-module module-remap-source`, mapping the monitor stream of the null sink to a virtual recording device.
3. Applications like Discord and OBS recognize `DiscordDesktopMic` as a standard hardware microphone.

To inspect your audio routing visually, click the **"Open pavucontrol (Volume Control)"** button in the app or run `pavucontrol` in a terminal.

---

## ❓ Troubleshooting

- **`pactl: command not found`**:
  Install `pulseaudio-utils` (Debian/Ubuntu/Fedora) or `libpulse` (Arch).
- **Virtual device already exists or needs reset**:
  Click **"Unload Virtual Device"** in the app, or manually run:
  ```bash
  pactl unload-module $(pactl list short modules | grep DiscordDesktop | awk '{print $1}')
  ```
- **Wayland scaling / UI rendering**:
  If your desktop environment has issues with Wayland scaling, launch with:
  ```bash
  QT_QPA_PLATFORM=xcb ./run.sh
  ```
