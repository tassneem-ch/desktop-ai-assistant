"""JARVIS Voice Pipeline - Real-time STT + edge-tts (JARVIS voice) + MCI/SAPI fallback

Design notes
------------
* STT: the microphone buffer is resampled to 16 kHz and sent to Google STT in
  **two languages in parallel** (en-US + ar-SA) so the total latency is the
  time of the slowest request instead of the sum of both.
* TTS: ``speak()`` never blocks the caller (the Tk thread used to freeze).
  Utterances are queued and spoken by a single worker thread, so voices can
  never overlap.  edge-tts synthesizes every sentence of a reply **in parallel**
  and the audio is played back with the Windows MCI API (no 1 s WMP polling
  loop any more) - first audio arrives in ~0.6 s and long answers keep playing
  without gaps.
"""

import math
import os
import queue
import random
import re
import threading
import time

DEFAULT_SAMPLE_RATE = 16000


def _resample(audio, orig_sr, target_sr):
    import numpy as np
    if orig_sr == target_sr:
        return audio
    ratio = target_sr / orig_sr
    new_len = int(len(audio) * ratio)
    indices = np.arange(new_len) / ratio
    return np.interp(indices, np.arange(len(audio)), audio).astype(np.int16)


def _com_init():
    """Every thread that touches win32 COM must call this first."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass


def clean_transcript(text):
    """Strip RTL marks / zero-width chars Google injects into Arabic results."""
    return re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', text).strip()


def _make_shared_connector():
    """One aiohttp pool reused by every edge-tts request.

    ``aiohttp.ClientSession`` closes the connector it is given, so we hide the
    real ``close()`` - that keeps the DNS cache (and any reusable socket) alive
    and cuts the synthesis latency from ~2.5 s to ~0.8 s.
    """
    import aiohttp

    class _SharedConnector(aiohttp.TCPConnector):
        async def close(self):
            return None

    return _SharedConnector(limit=0, ttl_dns_cache=600, enable_cleanup_closed=True)


class VoiceEngine:
    def __init__(self):
        self._callbacks = {}
        self._listening = False
        self._recording_thread = None
        self._audio_queue = queue.Queue()
        self._sample_rate = DEFAULT_SAMPLE_RATE
        self._native_rate = 44100
        self._channels = 1
        self._dtype = "int16"
        self._silence_threshold = 100
        self._min_phrase_duration = 0.25
        self._min_voiced = 0.25
        self._max_silence = 0.5
        self._max_phrase = 6
        self._tts_available = False
        self._tts_fallback = None
        self._stream_buffer = ""
        self._stream_lock = threading.Lock()
        self._speaking = threading.Event()
        self.current_amplitude = 0.0
        self.speaking_amplitude = 0.0
        self._tts_active = False
        self._speak_token = 0
        self._device = None          # resolved lazily -> system default mic
        self._edge_voice = os.environ.get("JARVIS_TTS_VOICE", "en-GB-RyanNeural")
        self._speaker = None
        self._sapi_rate = 1
        self._edge_available = False
        self._edge_failures = 0
        self._edge_retry_at = 0.0
        self._tts_engine = os.environ.get("JARVIS_TTS", "auto").strip().lower()

        # speech worker (single consumer => voices never overlap)
        self._speech_queue = queue.Queue()
        self._worker_lock = threading.Lock()
        self._speech_thread = None
        self._stop_event = threading.Event()
        self._current_alias = None
        self._alias_counter = 0

        # dedicated event loop + shared connection for edge-tts
        self._tts_loop_lock = threading.Lock()
        self._tts_loop_thread = None
        self._tts_loop = None
        self._tts_connector = None

        self._init_tts()

    # ------------------------------------------------------------------ events
    def on(self, event, callback):
        self._callbacks[event] = callback

    def _emit(self, event, *args):
        cb = self._callbacks.get(event)
        if cb:
            try:
                cb(*args)
            except Exception:
                pass

    # -------------------------------------------------------------------- TTS
    def _init_tts(self):
        """Detect engines without touching the network (startup stays instant)."""
        self._speaker = None
        self._tts_fallback = None
        self._edge_available = False
        self._tts_available = False

        if self._tts_engine in ("auto", "edge"):
            try:
                import edge_tts  # noqa: F401
                self._edge_available = True
            except Exception:
                self._edge_available = False

        if self._tts_engine == "edge" and not self._edge_available:
            self._tts_engine = "auto"

        # SAPI5 - offline and instant, used as fallback (or primary if asked for)
        try:
            _com_init()
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            self._select_sapi_voice(speaker)
            self._speaker = speaker
            self._tts_available = True
        except Exception:
            self._speaker = None

        if not self._tts_available and self._edge_available:
            self._tts_available = True

        if not self._tts_available:
            try:
                import pyttsx3
                self._tts_fallback = pyttsx3.init()
                self._tts_fallback.setProperty("rate", 180)
                self._tts_fallback.setProperty("volume", 1.0)
                self._tts_available = True
            except Exception:
                pass

        if self._edge_available:
            threading.Thread(target=self._warm_tts, daemon=True).start()

    @staticmethod
    def _select_sapi_voice(speaker):
        """Prefer a natural English voice, fall back to whatever exists.

        JARVIS_TTS_SAPI_GENDER=female|male biases the pick (used by DIVA so
        the offline fallback stays a woman's voice). Default keeps JARVIS's
        original david/zira preference.
        """
        try:
            gender = os.environ.get("JARVIS_TTS_SAPI_GENDER", "").strip().lower()
            voices = speaker.GetVoices()
            selected = None
            if gender == "female":
                female_hints = ("zira", "hazel", "susan", "sabina",
                                "female", "aria", "jenny", "sonia")
                male_hints = ("david", "mark", "male", "richard")
            else:
                female_hints = ("david", "zira", "natural")  # original order
                male_hints = ()
            for i in range(voices.Count):
                desc = voices.Item(i).GetDescription().lower()
                if any(h in desc for h in female_hints) and \
                        not any(m in desc for m in male_hints):
                    selected = voices.Item(i)
                    break
            if selected is None and voices.Count > 0:
                selected = voices.Item(0)
            if selected is not None:
                speaker.Voice = selected
            speaker.Rate = 1
            speaker.Volume = 100
        except Exception:
            pass

    @staticmethod
    def _clean_for_speech(text):
        t = text
        t = re.sub(r'\*+', '', t)
        t = re.sub(r'`[^`]*`', '', t)
        t = re.sub(r'_{2,}', '', t)
        t = re.sub(r'~~(.*?)~~', r'\1', t)
        t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
        t = re.sub(r'^[#*>\-|]\s*', '', t, flags=re.MULTILINE)
        t = re.sub(r'```[\s\S]*?```', ' code block. ', t)
        t = re.sub(r'[(){}\[\]<>]', '', t)
        t = re.sub(r'["\']', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        t = t.replace(' - ', ', ').replace('...', ', ')
        return t[:2000]

    def speak(self, text):
        """Non-blocking: the text is queued and spoken by the worker thread."""
        if not self._tts_available or not text:
            return
        cleaned = self._clean_for_speech(text)
        if not cleaned:
            return
        self._speech_queue.put(cleaned)
        self._start_speech_worker()

    def set_edge_voice(self, name):
        """Switch the edge-tts voice at runtime (e.g. from Settings)."""
        name = (name or "").strip()
        if name:
            self._edge_voice = name

    def get_edge_voice(self):
        return self._edge_voice

    def speak_stream(self, chunk, is_final=False):
        """Speak streamed text as complete sentences (fast first audio)."""
        if not self._tts_available or not chunk:
            return
        with self._stream_lock:
            self._stream_buffer += chunk
            buf = self._stream_buffer
            if is_final:
                rest = buf.strip()
                self._stream_buffer = ""
            else:
                # speak every sentence that is already complete
                m = list(re.finditer(r'[^.!?\n]+[.!?](?=\s|$)', buf))
                if len(m) < 1 or len(buf) < 60:
                    return
                cut = m[-1].end()
                rest = buf[:cut]
                self._stream_buffer = buf[cut:]
        if rest:
            self.speak(rest)

    def stop_speech(self):
        """Stop whatever is being spoken right now and drop queued text."""
        self._stop_event.set()
        self._tts_active = False
        self.speaking_amplitude = 0.0
        with self._stream_lock:
            self._stream_buffer = ""
        try:
            while True:
                self._speech_queue.get_nowait()
        except queue.Empty:
            pass
        alias = self._current_alias
        if alias:
            try:
                import ctypes
                ctypes.windll.winmm.mciSendStringW(f"stop {alias}", None, 0, None)
            except Exception:
                pass
        if self._speaker is not None:
            try:
                _com_init()
                self._speaker.Speak("", 2)   # SVSFPurgeBeforeSpeak
            except Exception:
                pass

    def _start_speech_worker(self):
        with self._worker_lock:
            if self._speech_thread is not None and self._speech_thread.is_alive():
                return
            self._speech_thread = threading.Thread(
                target=self._speech_loop, name="jarvis-tts", daemon=True
            )
            self._speech_thread.start()

    def _speech_loop(self):
        while True:
            text = self._speech_queue.get()
            self._speak_now(text)

    def _speak_now(self, text):
        self._stop_event.clear()
        self._tts_active = True
        self._speak_token += 1
        token = self._speak_token
        threading.Thread(
            target=self._simulate_speech_amplitude,
            args=(len(text), token),
            daemon=True,
        ).start()

        ok = False
        try:
            # periodic re-probe after a transient edge outage (403 waves etc.)
            if (not self._edge_available and self._tts_engine in ("auto", "edge")
                    and self._edge_retry_at and time.time() >= self._edge_retry_at):
                try:
                    import edge_tts  # noqa: F401
                    self._edge_available = True
                    self._edge_failures = 0
                    self._edge_retry_at = 0.0
                    self._emit("tts_error", "edge-tts voice restored")
                except Exception:
                    pass
            if self._edge_available and self._tts_engine != "sapi":
                ok = self._edge_speak(text)
                if not ok:
                    self._edge_failures += 1
                    if self._edge_failures >= 3:
                        self._edge_available = False
                        # transient outages (e.g. Microsoft 403 waves) resolve
                        # on their own -> keep probing so the premium voice
                        # returns automatically instead of never coming back
                        self._edge_retry_at = time.time() + 300
                        self._emit("tts_error", "edge-tts unreachable, using offline voice")
                else:
                    self._edge_failures = 0
            if not ok and not self._stop_event.is_set():
                ok = self._sapi_speak(text)
            if not ok and not self._stop_event.is_set():
                self._pyttsx3_speak(text)
        except Exception as e:
            self._emit("tts_error", f"TTS: {e}")
        finally:
            if token == self._speak_token:
                self._tts_active = False
                self.speaking_amplitude = 0.0

    # ----------------------------------------------------------- edge-tts path
    @staticmethod
    def _split_sentences(text, max_len=220):
        parts = re.split(r'(?<=[.!?…])\s+|\n+', text)
        out = []
        for part in parts:
            part = part.strip()
            while len(part) > max_len:
                cut = part.rfind(' ', 0, max_len)
                if cut <= 0:
                    cut = max_len
                out.append(part[:cut].strip())
                part = part[cut:].strip()
            if part:
                out.append(part)
        return out or [text]

    def _synth_chunk(self, text):
        """Synthesize one sentence to a temp mp3. Returns path or None.

        All requests share one aiohttp connector living on a dedicated event
        loop, so DNS + TLS are negotiated once and every later request reuses
        the warm connection (first audio ~2.5 s cold, ~0.7 s warm).
        """
        try:
            import asyncio
            self._start_tts_loop()
            if self._tts_loop is None or self._tts_loop.is_closed():
                return None
            future = asyncio.run_coroutine_threadsafe(
                self._synth_async(text), self._tts_loop
            )
            return future.result(timeout=30)
        except Exception:
            return None

    def _start_tts_loop(self):
        with self._tts_loop_lock:
            if self._tts_loop_thread is not None and self._tts_loop_thread.is_alive():
                return
            ready = threading.Event()

            def runner():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._tts_loop = loop
                ready.set()
                loop.run_forever()

            self._tts_loop_thread = threading.Thread(
                target=runner, name="jarvis-edge-tts", daemon=True
            )
            self._tts_loop_thread.start()
            ready.wait(timeout=5)

    async def _synth_async(self, text):
        import asyncio
        import tempfile

        try:
            import aiohttp
            import edge_tts
        except Exception:
            return None

        if self._tts_connector is None or getattr(self._tts_connector, "closed", False):
            self._tts_connector = _make_shared_connector()

        fpath = None
        try:
            communicate = edge_tts.Communicate(
                text, self._edge_voice,
                rate=os.environ.get("JARVIS_TTS_RATE", "-5%"),
                pitch=os.environ.get("JARVIS_TTS_PITCH", "-5Hz"),
                connector=self._tts_connector,
            )
            f = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            fpath = f.name
            f.close()
            await communicate.save(fpath)
            if not os.path.exists(fpath) or os.path.getsize(fpath) < 512:
                return None
            return fpath
        except Exception:
            # start fresh next time (the pool may be in a bad state)
            try:
                if self._tts_connector is not None and not self._tts_connector.closed:
                    await self._tts_connector.close()
            except Exception:
                pass
            self._tts_connector = None
            if fpath:
                try:
                    os.unlink(fpath)
                except Exception:
                    pass
            return None

    def _warm_tts(self):
        """Pre-establish DNS/TLS to the speech service so the first reply is fast."""
        path = self._synth_chunk("Systems online.")
        if path:
            try:
                os.unlink(path)
            except Exception:
                pass

    def _edge_speak(self, text):
        """Synthesize all sentences in parallel, play them back to back."""
        from concurrent.futures import ThreadPoolExecutor

        chunks = self._split_sentences(text)
        futures = []
        played = False
        try:
            workers = max(1, min(3, len(chunks)))
            pool = ThreadPoolExecutor(max_workers=workers)
            futures = [pool.submit(self._synth_chunk, c) for c in chunks]
            for fut in futures:
                if self._stop_event.is_set():
                    break
                path = fut.result()
                if path is None:
                    break
                try:
                    if not self._play_mp3(path):
                        break
                    played = True
                finally:
                    try:
                        os.unlink(path)
                    except Exception:
                        pass
            return played
        except Exception as e:
            self._emit("tts_error", f"Edge TTS failed: {e}")
            return False
        finally:
            # make sure every synthesised temp file is cleaned up
            for fut in futures:
                try:
                    path = fut.result(timeout=10)
                except Exception:
                    path = None
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        pass

    def _play_mp3(self, path):
        """Play an mp3 through the Windows MCI API and block until finished."""
        try:
            import ctypes
            winmm = ctypes.windll.winmm
        except Exception:
            return False

        self._alias_counter += 1
        alias = f"jarvis{os.getpid()}_{self._alias_counter}"
        buf = ctypes.create_unicode_buffer(512)
        try:
            err = winmm.mciSendStringW(
                f'open "{path}" type mpegvideo alias {alias}', buf, 512, None
            )
            if err != 0:
                return False
            self._current_alias = alias
            if self._stop_event.is_set():
                return False
            start = time.time()
            winmm.mciSendStringW(f"play {alias} wait", buf, 512, None)
            return not self._stop_event.is_set() and (time.time() - start) > 0.05
        except Exception:
            return False
        finally:
            self._current_alias = None
            try:
                winmm.mciSendStringW(f"close {alias}", None, 0, None)
            except Exception:
                pass

    # ------------------------------------------------------------ offline path
    def _sapi_speak(self, text, block=True):
        try:
            _com_init()
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            self._select_sapi_voice(speaker)
            speaker.Speak(text, 0 if block else 1)
            return True
        except Exception:
            return False

    def _pyttsx3_speak(self, text):
        try:
            if self._tts_fallback is None:
                import pyttsx3
                self._tts_fallback = pyttsx3.init()
                self._tts_fallback.setProperty("rate", 180)
                self._tts_fallback.setProperty("volume", 1.0)
            self._tts_fallback.say(text)
            self._tts_fallback.runAndWait()
            return True
        except Exception as e:
            self._emit("tts_error", str(e))
            return False

    def _simulate_speech_amplitude(self, char_count, token=None):
        duration = max(char_count / 13.0, 0.4)
        start = time.time()
        while self._tts_active and time.time() - start < duration + 2:
            if token is not None and token != self._speak_token:
                return
            elapsed = time.time() - start
            if elapsed > duration:
                self.speaking_amplitude *= 0.92
                if self.speaking_amplitude < 1:
                    break
                time.sleep(0.03)
                continue
            syllable = 0.5 + 0.5 * math.sin(elapsed * 10 * math.pi + math.sin(elapsed * 3) * 2)
            micro = 0.7 + 0.3 * random.random()
            env = min(elapsed / 0.1, 1.0) * max(0, 1 - elapsed / duration)
            self.speaking_amplitude = max(50, syllable * micro * env * 800)
            time.sleep(0.03)
        if token is None or token == self._speak_token:
            self.speaking_amplitude = 0.0

    # -------------------------------------------------------------------- STT
    def _rms(self, frame):
        import numpy as np
        samples = np.frombuffer(frame, dtype=np.int16).astype(np.float64)
        if len(samples) == 0:
            return 0
        return np.sqrt(np.mean(samples ** 2))

    @staticmethod
    def _recognize(audio_data):
        """Ask Google for en-US and ar-SA **in parallel**, keep the best match."""
        import speech_recognition as sr
        from concurrent.futures import ThreadPoolExecutor

        recognizer = sr.Recognizer()
        languages = ["en-US", "ar-SA"]
        if os.environ.get("JARVIS_STT_LANG"):
            languages = [os.environ["JARVIS_STT_LANG"]] + [
                l for l in languages if l != os.environ["JARVIS_STT_LANG"]
            ]

        def ask(lang):
            try:
                res = recognizer.recognize_google(audio_data, language=lang, show_all=True)
            except sr.UnknownValueError:
                return lang, "", 0.0
            except sr.RequestError:
                return lang, "", -1.0
            except Exception:
                return lang, "", -1.0
            if isinstance(res, dict):
                alts = res.get("alternative") or []
                if not alts:
                    return lang, "", 0.0
                text = clean_transcript(str(alts[0].get("transcript", "")))
                conf = float(alts[0].get("confidence", 0.5))
                return lang, text, conf
            if isinstance(res, list) and res:
                text = clean_transcript(str(res[0].get("transcript", "")))
                return lang, text, float(res[0].get("confidence", 0.5))
            return lang, "", 0.0

        with ThreadPoolExecutor(max_workers=len(languages)) as pool:
            results = list(pool.map(ask, languages))

        usable = [(l, t, c) for l, t, c in results if t]
        if not usable:
            # surface a real network problem instead of a silent miss
            if any(c == -1.0 for _, _, c in results):
                raise RuntimeError("Speech service unreachable")
            return ""

        usable.sort(key=lambda r: r[2], reverse=True)
        if len(usable) == 1:
            return usable[0][1]

        best, second = usable[0], usable[1]
        if abs(best[2] - second[2]) > 0.05:
            return best[1]
        # near tie: trust the script that was actually recognised
        for lang, text, _ in usable:
            if lang == "ar-SA" and re.search(r'[\u0600-\u06FF]', text):
                return text
        return best[1]

    def _record_loop(self):
        try:
            import sounddevice as sd
        except Exception as e:
            self._emit("stt_error", f"sounddevice not available: {e}")
            self._listening = False
            self._emit("listening_stopped")
            return

        chunk_duration = 0.1
        chunk_samples = max(int(self._native_rate * chunk_duration), 1)

        try:
            self._emit("listening", "Initializing microphone...")
            buffer = bytearray()
            silence_start = None
            voiced_start = None
            voiced_samples = 0
            samples_per_chunk = 0

            def audio_callback(indata, frames, t, status):
                self._audio_queue.put(indata.copy())

            stream = sd.InputStream(
                samplerate=self._native_rate,
                channels=self._channels,
                dtype=self._dtype,
                blocksize=chunk_samples,
                device=self._device,
                callback=audio_callback,
            )
            stream.start()

            self._emit("listening_started")
            self._emit("listening", "Listening...")

            while self._listening:
                try:
                    chunk = self._audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                raw = chunk.tobytes()
                rms = self._rms(raw)
                self.current_amplitude = rms

                # never transcribe the assistant's own voice
                if self._tts_active:
                    buffer.clear()
                    voiced_start = None
                    silence_start = None
                    continue

                if rms > self._silence_threshold:
                    buffer.extend(raw)
                    samples_per_chunk = len(chunk)
                    voiced_samples += samples_per_chunk
                    if voiced_start is None:
                        voiced_start = time.time()
                        self._emit("listening", "Speak...")
                    silence_start = None
                else:
                    if voiced_start is not None and silence_start is None:
                        silence_start = time.time()

                    if silence_start is not None and voiced_start is not None:
                        phrase_dur = time.time() - voiced_start
                        silence_dur = time.time() - silence_start
                        voiced_dur = voiced_samples / max(self._native_rate, 1)

                        finished = (
                            voiced_dur >= self._min_phrase_duration
                            and silence_dur > self._max_silence
                        ) or phrase_dur > self._max_phrase

                        if finished:
                            # ignore blips/noise: we need real speech in the buffer
                            if voiced_dur >= self._min_voiced and len(buffer) >= 3200:
                                audio_bytes = bytes(buffer)
                                buffer.clear()
                                voiced_start = None
                                silence_start = None
                                voiced_samples = 0
                                self._emit("listening", "Processing...")
                                threading.Thread(
                                    target=self._transcribe,
                                    args=(audio_bytes,),
                                    daemon=True,
                                ).start()
                                if self._listening and not self._tts_active:
                                    self._emit("listening", "Listening...")
                            else:
                                buffer.clear()
                                voiced_start = None
                                silence_start = None
                                voiced_samples = 0
                                if self._listening and not self._tts_active:
                                    self._emit("listening", "Listening...")

            stream.stop()
            stream.close()

        except Exception as e:
            self._emit("stt_error", f"Recording error: {e}")
        finally:
            self._listening = False
            self.current_amplitude = 0.0
            self._emit("listening_stopped")

    def _transcribe(self, audio_bytes):
        try:
            import speech_recognition as sr
            import numpy as np
        except ImportError as e:
            self._emit("stt_error", f"speech_recognition not installed: {e}")
            return

        try:
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            if audio_np.size == 0:
                return

            # boost quiet audio so Google gets a usable signal
            rms = float(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))
            if 1 < rms < 500:
                gain = min(3000.0 / max(rms, 1), 8.0)
                audio_np = np.clip(audio_np.astype(np.float64) * gain, -32768, 32767).astype(np.int16)

            audio_16k = _resample(audio_np, self._native_rate, self._sample_rate)
            audio_data = sr.AudioData(audio_16k.tobytes(), self._sample_rate, 2)

            text = self._recognize(audio_data)
            if text:
                self._emit("stt_result", text)
        except RuntimeError as e:
            self._emit("stt_error", f"STT API: {e}")
        except Exception as e:
            self._emit("stt_error", f"Transcribe error: {e}")

    # ----------------------------------------------------------- device/config
    def _resolve_audio_config(self):
        """Pick the system default microphone (and its native rate)."""
        env_device = os.environ.get("JARVIS_MIC_DEVICE")
        try:
            import sounddevice as sd
            if env_device not in (None, ""):
                device = int(env_device)
            else:
                default_in = sd.default.device
                try:
                    device = int(default_in[0])   # sounddevice returns a pair
                except Exception:
                    device = int(default_in)
                if device < 0:
                    device = None
                    for i, dev in enumerate(sd.query_devices()):
                        if dev.get("max_input_channels", 0) > 0:
                            device = i
                            break
            if device is None:
                return None, self._native_rate
            info = sd.query_devices(device)
            rate = int(info.get("default_samplerate") or self._native_rate)
            if rate <= 0:
                rate = self._native_rate
            return device, rate
        except Exception:
            return self._device, self._native_rate

    def start_listening(self, device=None):
        if self._listening:
            return
        if device is not None:
            self._device = device
        resolved_device, resolved_rate = self._resolve_audio_config()
        if resolved_device is not None:
            self._device = resolved_device
        if resolved_rate:
            self._native_rate = resolved_rate
        self._listening = True

        # short noise-floor calibration (0.4 s) - keeps the mic quiet-aware
        try:
            import sounddevice as sd
            frames = int(self._native_rate * 0.4)
            rec = sd.rec(frames, samplerate=self._native_rate,
                         channels=self._channels, dtype=self._dtype, device=self._device)
            sd.wait()
            rms_vals = []
            chunk_size = max(int(self._native_rate * 0.1), 1)
            for i in range(0, len(rec) - chunk_size, chunk_size):
                rms_vals.append(self._rms(rec[i:i + chunk_size].tobytes()))
            if rms_vals:
                median_rms = sorted(rms_vals)[len(rms_vals) // 2]
                self._silence_threshold = max(median_rms * 1.5, 100)
        except Exception:
            if self._silence_threshold < 100:
                self._silence_threshold = 100

        self._recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._recording_thread.start()

    def stop_listening(self):
        self._listening = False
        self._recording_thread = None

    def is_listening(self):
        return self._listening

    def calibrate(self):
        try:
            import sounddevice as sd
        except Exception as e:
            self._emit("stt_error", f"Calibration: {e}")
            return

        self._emit("listening", "Calibrating... stay silent")
        try:
            if self._device is None:
                device, rate = self._resolve_audio_config()
                if device is not None:
                    self._device = device
                if rate:
                    self._native_rate = rate
            recording = sd.rec(int(self._native_rate * 2),
                               samplerate=self._native_rate,
                               channels=self._channels,
                               dtype=self._dtype,
                               device=self._device)
            sd.wait()
            rms_vals = []
            chunk_size = int(self._native_rate * 0.1)
            for i in range(0, len(recording) - chunk_size, chunk_size):
                chunk = recording[i:i + chunk_size]
                rms_vals.append(self._rms(chunk.tobytes()))
            if rms_vals:
                median_rms = sorted(rms_vals)[len(rms_vals) // 2]
                self._silence_threshold = max(median_rms * 1.8, 120)
                self._emit("listening",
                           f"Calibrated threshold: {self._silence_threshold:.0f}")
        except Exception as e:
            self._emit("stt_error", f"Calibration: {e}")
