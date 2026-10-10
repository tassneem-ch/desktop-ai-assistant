"""DIVA — the feminine counterpart to JARVIS.

Separate, independently runnable edition. It reuses every JARVIS engine
(ai, voice, tools, security, memory, config) and only replaces identity,
personality, voice defaults and visuals.

IMPORTANT: this module must stay import-light. diva_app.main sets a few
environment defaults here BEFORE jarvis_app modules are imported so that
config.py/voice.py pick them up at import time.
"""

import os

# ── environment defaults (must precede any jarvis_app import) ──────────
# Own data/config directory -> DIVA never clobbers JARVIS settings.
os.environ.setdefault("JARVIS_APPDATA_DIR", "DivaAssistant")
# Natural female voice for DIVA (JARVIS keeps en-GB-RyanNeural).
os.environ.setdefault("JARVIS_TTS_VOICE", "en-GB-SoniaNeural")
# Slightly quicker, unshifted pitch: feminine and crisp, not robotic.
os.environ.setdefault("JARVIS_TTS_RATE", "-3%")
os.environ.setdefault("JARVIS_TTS_PITCH", "+0Hz")
# offline SAPI fallback must also be a woman's voice
os.environ.setdefault("JARVIS_TTS_SAPI_GENDER", "female")

APP_NAME = "DIVA"
DATA_DIRNAME = "DivaAssistant"
