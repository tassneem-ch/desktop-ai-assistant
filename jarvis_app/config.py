"""Persistent JARVIS configuration (API key, provider, model).

Stored as JSON in %APPDATA%/JarvisAssistant/config.json so secrets never
touch the repo. Values are mirrored into os.environ so every module
(ai.py, tools.py, main.py) picks them up transparently.
"""

import json
import os
import threading

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "JarvisAssistant")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

_lock = threading.RLock()  # re-entrant: save_config calls load_config under the same lock
_cache = None

# env var mirrored for each config key (config.json wins over .env)
_ENV_MAP = {
    "nvidia_api_key": "NVIDIA_API_KEY",
    "openrouter_api_key": "OPENROUTER_API_KEY",
    "model": "JARVIS_MODEL",
    "provider": "JARVIS_PROVIDER",
}


def load_config():
    """Read config.json (cached). Missing file -> {}."""
    global _cache
    with _lock:
        if _cache is not None:
            return dict(_cache)
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
        except (OSError, ValueError):
            data = {}
        _cache = data
        return dict(data)


def save_config(**kwargs):
    """Merge keys into config.json and mirror them into os.environ."""
    global _cache
    with _lock:
        if _cache is None:
            load_config()  # must read the file first or we'd wipe existing keys
        data = dict(_cache or {})
        data.update({k: v for k, v in kwargs.items() if v is not None})
        # remove explicitly-nulled keys
        for k, v in kwargs.items():
            if v == "":
                data.pop(k, None)
        try:
            os.makedirs(APP_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass
        _cache = data
    apply_to_env()
    return dict(data)


def apply_to_env():
    """Push stored config into os.environ (config.json wins over .env)."""
    cfg = load_config()
    for ckey, ekey in _ENV_MAP.items():
        val = cfg.get(ckey)
        if val:
            os.environ[ekey] = val


def detect_provider(api_key):
    """Guess the provider from the key shape."""
    key = (api_key or "").strip()
    if key.startswith("nvapi-"):
        return "nvidia"
    if key.startswith("sk-or-") or key.startswith("sk-or-v1"):
        return "openrouter"
    return None
