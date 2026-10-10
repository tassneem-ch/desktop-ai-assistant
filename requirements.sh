#!/bin/bash
# JARVIS - Kali Linux / Debian Dependencies
set -e

echo "========================================"
echo " JARVIS - Installing Dependencies"
echo "========================================"
echo ""

# System packages
echo "[1/3] Installing system packages..."
sudo apt update -qq
sudo apt install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    espeak \
    ffmpeg \
    portaudio19-dev \
    libasound2-dev \
    tesseract-ocr

# Upgrade pip
echo "[2/3] Upgrading pip..."
python3 -m pip install --upgrade pip --quiet

# Python packages
echo "[3/3] Installing Python packages..."
python3 -m pip install --quiet \
    requests \
    urllib3 \
    ddgs \
    edge-tts \
    pyttsx3 \
    numpy \
    sounddevice \
    SpeechRecognition \
    psutil \
    pyautogui \
    pyperclip \
    Pillow \
    qrcode \
    dnspython \
    jsonpath-ng \
    mss

echo ""
echo "========================================"
echo " Installation complete!"
echo ""
echo " Run: python3 run_jarvis.py"
echo " (API key built-in - File > Settings to add your own"
echo "  NVIDIA nvapi-... or OpenRouter sk-or-... key, saved automatically)"
echo ""
echo " Voice settings (optional, in .env):"
echo "   JARVIS_TTS=auto|edge|sapi   TTS engine (sapi = offline/instant)"
echo "   JARVIS_STT_LANG=en-US       primary speech-recognition language"
echo "   JARVIS_MIC_DEVICE=0         microphone device index"
echo "========================================"
