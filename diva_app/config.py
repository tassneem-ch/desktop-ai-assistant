"""DIVA configuration.

Runs on top of jarvis_app.config, which (thanks to the JARVIS_APPDATA_DIR
env var set in diva_app.__init__) stores DIVA's settings in
%APPDATA%/DivaAssistant/config.json — fully separate from JARVIS.

On first run, AI credentials (provider + API keys + model) are copied once
from the JARVIS config so DIVA works immediately without re-entering the
key; after that the two configs evolve independently.
"""

import json
import os

from jarvis_app.config import load_config, save_config, detect_provider

from diva_app import identity

_JARVIS_DIRNAME = "JarvisAssistant"  # read-only source for one-time seeding
_SEED_KEYS = ("provider", "nvidia_api_key", "openrouter_api_key", "model")


def get(key, default=None):
    return load_config().get(key, default)


def set(**kwargs):
    return save_config(**kwargs)


def ensure_seeded():
    """One-time: copy AI credentials from the JARVIS config if DIVA has none."""
    cfg = load_config()
    if any(cfg.get(k) for k in ("nvidia_api_key", "openrouter_api_key")):
        return False  # already has a key
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    jarvis_cfg_path = os.path.join(appdata, _JARVIS_DIRNAME, "config.json")
    try:
        with open(jarvis_cfg_path, "r", encoding="utf-8") as f:
            jc = json.load(f)
    except (OSError, ValueError):
        return False
    seed = {k: jc[k] for k in _SEED_KEYS if jc.get(k)}
    if not seed:
        return False
    save_config(**seed)
    return True


# ── DIVA-specific settings with validated defaults ─────────────────────

def get_intensity():
    v = get("personality_intensity", identity.DEFAULT_INTENSITY)
    return v if v in identity.INTENSITY_LEVELS else identity.DEFAULT_INTENSITY


def set_intensity(level):
    if level not in identity.INTENSITY_LEVELS:
        level = identity.DEFAULT_INTENSITY
    save_config(personality_intensity=level)
    return level


def get_voice():
    return get("tts_voice", os.environ.get("JARVIS_TTS_VOICE", identity.DEFAULT_VOICE)) or identity.DEFAULT_VOICE


def set_voice(name):
    name = (name or "").strip() or identity.DEFAULT_VOICE
    # mirror env so VoiceEngine (and any child synth) picks it up instantly
    os.environ["JARVIS_TTS_VOICE"] = name
    save_config(tts_voice=name)
    return name


def get_name():
    return (get("assistant_name", "") or identity.DEFAULT_NAME).strip() or identity.DEFAULT_NAME


def set_name(name):
    name = (name or "").strip() or identity.DEFAULT_NAME
    os.environ["DIVA_NAME"] = name
    save_config(assistant_name=name)
    return name


def get_wake_words():
    v = get("wake_words", "")
    if not v:
        return [w.strip() for w in identity.DEFAULT_WAKE_WORDS.split(",") if w.strip()]
    return [w.strip() for w in v.split(",") if w.strip()]


def set_wake_words(text):
    text = (text or "").strip()
    save_config(wake_words=text)  # empty -> reset to defaults
    return [w.strip() for w in (text or identity.DEFAULT_WAKE_WORDS).split(",") if w.strip()]


__all__ = ["get", "set", "ensure_seeded", "detect_provider",
           "get_intensity", "set_intensity", "get_voice", "set_voice",
           "get_name", "set_name", "get_wake_words", "set_wake_words"]
