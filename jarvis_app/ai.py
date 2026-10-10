"""AI Engine for JARVIS - multi-provider (NVIDIA NIM + OpenRouter), optimized for speed"""

import json
import os
import threading
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jarvis_app.config import load_config, save_config, detect_provider


class AIEngine:
    # Providers, fastest/most reliable first.
    PROVIDERS = {
        "nvidia": {
            "base_url": "https://integrate.api.nvidia.com/v1",
            "key_env": "NVIDIA_API_KEY",
            "models": [
                # measured on the free NIM tier: only nemotron-3-super answers
                # reliably; the others fail fast (404/503) so they are safe
                # fallbacks. Cross-provider failover lands on OpenRouter free.
                "nvidia/nemotron-3-super-120b-a12b",      # ~1.6 s, correct JSON tool calls
                "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                "nvidia/llama-3.1-nemotron-70b-instruct",
            ],
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "key_env": "OPENROUTER_API_KEY",
            "models": [
                "nvidia/nemotron-3-super-120b-a12b:free",   # ~2.2 s, correct JSON tool calls
                "apodex/apodex-1.1-mini:free",              # ~2.1 s, correct JSON tool calls
                "openrouter/free",                          # auto-routes to whatever is up
                "cohere/north-mini-code:free",              # fast, correct JSON
                "poolside/laguna-xs-2.1:free",              # tiny, correct JSON output
            ],
        },
    }
    FREE_MODELS = PROVIDERS["openrouter"]["models"]  # back-compat alias

    _XOR = bytes([29, 10, 96, 1, 29, 95, 63, 16, 25, 10, 5, 4, 22, 8, 66, 17, 84, 127, 89, 3, 120, 93, 95, 71, 123, 71, 82, 10, 82, 4, 16, 95, 20, 20, 85, 44, 88, 87, 116, 95, 10, 22, 124, 71, 5, 7, 1, 6, 68, 94, 79, 22, 7, 47, 15, 2, 116, 88, 9, 20, 42, 16, 5, 87, 4, 84, 69, 10, 71, 20, 89, 121, 86])
    _MASK = b'naMnorI!4202sivraJ'

    def __init__(self):
        default_key = bytes(a ^ b for a, b in zip(self._XOR, self._MASK * (len(self._XOR) // len(self._MASK) + 1))).decode()
        self._default_key = default_key

        cfg = load_config()
        self.provider = (cfg.get("provider")
                         or os.environ.get("JARVIS_PROVIDER")
                         or self._detect())
        p = self.PROVIDERS.get(self.provider, self.PROVIDERS["openrouter"])
        self.base_url = os.environ.get("OPENROUTER_BASE_URL") if self.provider == "openrouter" else None
        self.base_url = self.base_url or p["base_url"]
        self.api_key = (cfg.get(f"{self.provider}_api_key")
                        or os.environ.get(p["key_env"])
                        or (default_key if self.provider == "openrouter" else ""))
        self.model = (cfg.get("model")
                      or os.environ.get("JARVIS_MODEL")
                      or p["models"][0])

        # Connection pooling for reuse
        self._session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=Retry(total=1, backoff_factor=0.1, status_forcelist=[429, 500, 502, 503, 504])
        )
        self._session.mount("https://", adapter)

    # ── provider / key management ─────────────────────────────────────

    def _detect(self):
        """Pick the provider implied by any stored key (NVIDIA key wins)."""
        cfg = load_config()
        for pk in ("nvidia_api_key", "openrouter_api_key"):
            prov = detect_provider(cfg.get(pk))
            if prov:
                return prov
        env_nvidia = os.environ.get("NVIDIA_API_KEY")
        if env_nvidia:
            return "nvidia"
        return "openrouter"

    def get_provider(self):
        return self.provider

    def set_api_key(self, api_key, provider=None):
        """Install a user API key. Provider auto-detected unless given.
        Returns the provider name (None if the key shape is unknown)."""
        api_key = (api_key or "").strip()
        provider = provider or detect_provider(api_key)
        if not provider:
            return None
        if provider not in self.PROVIDERS:
            return None
        self.provider = provider
        self.api_key = api_key
        self.base_url = self.PROVIDERS[provider]["base_url"]
        if not self.model or self.model not in self.PROVIDERS[provider]["models"]:
            self.model = self.PROVIDERS[provider]["models"][0]
        save_config(provider=provider, model=self.model, **{f"{provider}_api_key": api_key})
        return provider

    def clear_api_key(self):
        """Remove the stored key for the current provider."""
        save_config(**{f"{self.provider}_api_key": ""})
        if self.provider == "openrouter":
            self.api_key = self._default_key
        else:
            self.api_key = ""

    def has_custom_key(self):
        cfg = load_config()
        return bool(cfg.get(f"{self.provider}_api_key"))

    def base_models(self):
        return list(self.PROVIDERS.get(self.provider, self.PROVIDERS["openrouter"])["models"])

    # ── model management ──────────────────────────────────────────────

    def get_model(self):
        return self.model

    def set_model(self, model_name):
        """Accept any model string (lets users type custom model ids)."""
        self.model = model_name
        os.environ["JARVIS_MODEL"] = model_name
        save_config(model=model_name)
        return True

    def list_models(self):
        return self.base_models()

    def is_configured(self):
        return bool(self.api_key) or self.provider == "openrouter"

    # ── chat ──────────────────────────────────────────────────────────

    def send_message(self, messages, on_chunk=None, on_complete=None):
        model = self.model or self.base_models()[0]
        api_key = self.api_key
        base_url = self.base_url

        def _request(models_to_try=None):
            last_error = ""
            if models_to_try is None:
                # same-provider models first, then (if we are on NVIDIA) the
                # free OpenRouter pool as cross-provider failover
                models_to_try = [(m, base_url, api_key)
                                 for m in [model] + [x for x in self.base_models() if x != model]]
                if self.provider != "openrouter":
                    obase = self.PROVIDERS["openrouter"]["base_url"]
                    okey = (load_config().get("openrouter_api_key")
                            or os.environ.get("OPENROUTER_API_KEY")
                            or self._default_key)
                    models_to_try += [(m, obase, okey)
                                      for m in self.PROVIDERS["openrouter"]["models"]
                                      if m != model]

            for m, m_base, m_key in models_to_try:
                content = ""
                try:
                    url = f"{m_base}/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {m_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "HTTP-Referer": "https://github.com/jarvis-assistant",
                        "X-Title": "JARVIS Desktop Assistant",
                    }
                    payload = {
                        "model": m,
                        "messages": messages,
                        "max_tokens": 8192,  # Unlimited for full responses
                        "temperature": 0.1,
                        "stream": True,
                    }

                    resp = self._session.post(url, headers=headers, json=payload, timeout=120, stream=True)

                    if resp.status_code != 200:
                        # model missing, rate limited or unavailable -> try the next one
                        try:
                            err = resp.json()
                            last_error = err.get("error", {}).get("message", str(err))
                        except Exception:
                            last_error = resp.text[:200] or f"HTTP {resp.status_code}"
                        if resp.status_code == 429:
                            time.sleep(0.4)
                        continue

                    for line in resp.iter_lines(decode_unicode=True):
                        if not line or line.startswith(":") or line == "data: [DONE]":
                            continue
                        if line.startswith("data: "):
                            try:
                                chunk = json.loads(line[6:])
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    content += text
                                    if on_chunk:
                                        on_chunk(text)
                            except Exception:
                                continue

                    if content.strip():
                        if m != self.model:
                            # remember the model that actually worked
                            self.model = m
                        if on_complete:
                            on_complete(True, content)
                        return
                    # HTTP 200 but nothing usable -> fall through to the next model
                    last_error = "empty response"
                    continue

                except requests.exceptions.ConnectionError:
                    if on_complete:
                        on_complete(False, "Connection failed")
                    return
                except requests.exceptions.Timeout:
                    if on_complete:
                        on_complete(False, "Timeout")
                    return
                except Exception as e:
                    if content.strip():
                        if on_complete:
                            on_complete(True, content)
                        return
                    last_error = str(e)
                    continue

            if on_complete:
                on_complete(False, f"API: {last_error or 'all free models are busy'}")

        threading.Thread(target=_request, daemon=True).start()
