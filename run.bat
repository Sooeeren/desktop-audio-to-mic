@echo off
title Discord Desktop Audio Mic
cd /d "%~dp0"

echo Starting Discord Desktop Audio Mic...
python -c "import PySide6, pyaudiowpatch, sounddevice, numpy" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing required packages...
    python -m pip install -r requirements.txt
)

start "" pythonw main.py
if %ERRORLEVEL% NEQ 0 (
    python main.py
)
exit
