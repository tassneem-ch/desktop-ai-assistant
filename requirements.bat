@echo off
title Installing JARVIS Dependencies
echo ========================================
echo  JARVIS - Installing Dependencies
echo ========================================
echo.

:: Ensure pip is up to date
python -m pip install --upgrade pip

:: Core dependencies
echo [1/4] Installing core packages...
pip install requests urllib3 ddgs

:: Voice: TTS (edge-tts JARVIS voice, SAPI fallback) + STT (Google)
echo [2/4] Installing voice (STT + TTS) packages...
pip install edge-tts pyttsx3 SpeechRecognition numpy sounddevice

:: Optional: System monitoring, UI and Windows integration
echo [3/4] Installing system, UI and Windows packages...
pip install psutil pyautogui pyperclip qrcode[pil] Pillow mss pycaw winotify

:: Optional: Wake word listener + misc
echo [4/4] Installing wake word & misc...
pip install comtypes pywin32 dnspython jsonpath-ng

echo.
echo ========================================
echo  Installation complete!
echo.
echo  Run: python -m jarvis_app.main
echo  (API key built-in - File ^> Settings to add your own
echo   NVIDIA nvapi-... or OpenRouter sk-or-... key, saved automatically)
echo.
echo  Voice settings (optional, in .env):
echo    JARVIS_TTS=auto|edge|sapi   TTS engine (sapi = offline/instant)
echo    JARVIS_STT_LANG=en-US       primary speech-recognition language
echo    JARVIS_MIC_DEVICE=1         microphone device index
echo ========================================
pause
