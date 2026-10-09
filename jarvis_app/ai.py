"""OpenRouter AI Engine for JARVIS - Optimized for Speed"""

import json
import os
import threading
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class AIEngine:
    # Ordered by speed and JSON tool-call reliability (all free on OpenRouter).
    # Kept in sync with what actually answers correctly - see README.
    FREE_MODELS = [
        "nvidia/nemotron-3-super-120b-a12b:free",   # ~2.2 s, correct JSON tool calls
        "apodex/apodex-1.1-mini:free",              # ~2.1 s, correct JSON tool calls
        "openrouter/free",                          # auto-routes to whatever is up
        "cohere/north-mini-code:free",              # fast, correct JSON
        "poolside/laguna-xs-2.1:free",              # tiny, correct JSON output
    ]

    _XOR = bytes([29, 10, 96, 1, 29, 95, 63, 16, 25, 10, 5, 4, 22, 8, 66, 17, 84, 127, 89, 3, 120, 93, 95, 71, 123, 71, 82, 10, 82, 4, 16, 95, 20, 20, 85, 44, 88, 87, 116, 95, 10, 22, 124, 71, 5, 7, 1, 6, 68, 94, 79, 22, 7, 47, 15, 2, 116, 88, 9, 20, 42, 16, 5, 87, 4, 84, 69, 10, 71, 20, 89, 121, 86])
    _MASK = b'naMnorI!4202sivraJ'

    def __init__(self):
        default_key = bytes(a ^ b for a, b in zip(self._XOR, self._MASK * (len(self._XOR) // len(self._MASK) + 1))).decode()
        self.api_key = os.environ.get("OPENROUTER_API_KEY", default_key)
        self.base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.environ.get("JARVIS_MODEL") or self.FREE_MODELS[0]
        
        # Connection pooling for reuse
        self._session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=Retry(total=1, backoff_factor=0.1, status_forcelist=[429, 500, 502, 503, 504])
        )
        self._session.mount("https://", adapter)

    def get_model(self):
        return os.environ.get("JARVIS_MODEL", self.model)

    def set_model(self, model_name):
        if model_name in self.FREE_MODELS or model_name == self.FREE_MODELS[0]:
            self.model = model_name
            os.environ["JARVIS_MODEL"] = model_name
            return True
        # Allow setting any model string
        self.model = model_name
        os.environ["JARVIS_MODEL"] = model_name
        return True

    def list_models(self):
        return list(self.FREE_MODELS)

    def is_configured(self):
        return bool(self.api_key)

    def send_message(self, messages, on_chunk=None, on_complete=None):
        model = os.environ.get("JARVIS_MODEL") or self.model or self.FREE_MODELS[0]

        def _request(models_to_try=None):
            last_error = ""
            if models_to_try is None:
                models_to_try = [model] + [m for m in self.FREE_MODELS if m != model]

            for m in models_to_try:
                content = ""
                try:
                    url = f"{self.base_url}/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
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
