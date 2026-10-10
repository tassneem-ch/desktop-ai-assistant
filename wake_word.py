"""
JARVIS Wake Word Listener - Uses sounddevice (no PyAudio needed)
"""
import os
import sys
import time
import threading
import subprocess
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from pathlib import Path

# Wake word matching reuses the shared (parallel, en+ar) recognizer
try:
    from jarvis_app.voice import VoiceEngine
except ImportError:                       # running from another working dir
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from jarvis_app.voice import VoiceEngine


DEFAULT_WAKE_WORDS = [
    # Arabic - exact
    "أفق", "أفق يا جارفيس", "يا جارفيس", "جارفيس",
    "لفق", "لفق يا جارفيس", "يا جارفيس لفق",
    # Arabic - phonetic (what Google STT actually hears)
    "أفغ", "أفك", "أفوق", "أفاك", "أفواق", "افاق",
    "أفاج", "أفج", "أفح", "أفخ", "آفاق", "أفاكس",
    "لفغ", "لفك", "لفاك", "لفاج", "لفج", "لفخ",
    "ل فق", "لأفق", "لفاغ", "لفوق", "لافق", "لافاك",
    "يا جرفيس", "يا جار فيس", "يا جارافيس", "يا كرافيس",
    "جار فيس", "جارافيس", "جارفيز", "جرفيس", "كرافيس",
    # English
    "hey jarvis", "jarvis", "ok jarvis", "hello jarvis",
    "hey jarvus", "hey jarviz", "hey jahvis",
    "jarvus", "jarviz", "j.arvis", "j arvis",
    # Mixed
    "أفق jarvis", "jarvis أقف", "jarvis أفق",
    "هي jarvis", "هي جارفيس",
]


class WakeWordListener:
    def __init__(self, wake_words=None, launch_script="run_jarvis.py",
                 display_name="JARVIS"):
        # wake_words/launch_script/display_name let another edition (e.g. DIVA)
        # reuse this listener unchanged; defaults keep JARVIS behaviour identical.
        self._callbacks = {}
        self._listening = False
        self._thread = None
        self._wake_words = [w.strip().lower() for w in (wake_words or DEFAULT_WAKE_WORDS) if w.strip()]
        self._launch_script = launch_script
        self._display_name = display_name
        self._last_trigger = 0
        self._cooldown = 3.0
        self._sample_rate = 16000
        self._device = None
        
    def on(self, event, callback):
        self._callbacks[event] = callback
        
    def _emit(self, event, *args):
        cb = self._callbacks.get(event)
        if cb:
            try:
                cb(*args)
            except Exception:
                pass
    
    def _listen_loop(self):
        try:
            self._emit("listening", "Wake word listening...")

            recognizer = sr.Recognizer()
            # Use sounddevice directly instead of sr.Microphone
            # This avoids PyAudio dependency

            # Resolve the default microphone and its native rate (16 kHz is not
            # supported by most built-in mics, opening the stream would fail).
            device, rate = self._resolve_device()
            self._device = device
            self._sample_rate = rate
            chunk = max(int(self._sample_rate * 0.1), 1)

            # Calibrate noise level
            self._emit("listening", "Calibrating... stay silent")
            with sd.InputStream(samplerate=self._sample_rate, channels=1,
                                dtype='int16', device=device) as stream:
                # Record 1 second for calibration
                audio_data, _ = stream.read(int(self._sample_rate * 1))
                # Convert to AudioData for recognizer
                audio_np = audio_data.flatten()
                # Calculate noise floor - use lower multiplier for quiet mic
                noise_rms = np.sqrt(np.mean(audio_np.astype(np.float64) ** 2))
                recognizer.energy_threshold = max(noise_rms * 1.5, 80)

            first_word = self._wake_words[0] if self._wake_words else "the wake word"
            self._emit("listening", f"Ready. Say '{first_word}'")

            while self._listening:
                try:
                    # Record audio using sounddevice
                    with sd.InputStream(samplerate=self._sample_rate, channels=1,
                                        dtype='int16', device=device) as stream:
                        # Listen for up to 4 seconds
                        frames = []
                        start_time = time.time()
                        silence_threshold = recognizer.energy_threshold
                        silence_duration = 0
                        min_speech_duration = 0.3
                        max_silence = 0.6

                        while self._listening and (time.time() - start_time) < 4:
                            audio_chunk, _ = stream.read(chunk)  # 100ms chunks
                            frames.append(audio_chunk.flatten())

                            # Check energy
                            rms = np.sqrt(np.mean(audio_chunk.astype(np.float64) ** 2))
                            if rms > silence_threshold:
                                silence_duration = 0
                            else:
                                silence_duration += 0.1

                            # If we had speech and then silence, stop
                            total_audio = len(np.concatenate(frames)) / self._sample_rate
                            if total_audio > min_speech_duration and silence_duration > max_silence:
                                break

                        if not frames:
                            continue

                        audio_np = np.concatenate(frames)

                        # Boost quiet audio for better STT
                        audio_np = self._boost_audio(audio_np)

                        # Raw PCM (a WAV header would corrupt the first samples)
                        audio_data = sr.AudioData(
                            audio_np.astype(np.int16).tobytes(), self._sample_rate, 2
                        )

                    # en-US and ar-SA are requested **in parallel** (~1.1 s total
                    # instead of ~2.3 s for the old Arabic-then-English chain)
                    try:
                        text = VoiceEngine._recognize(audio_data).lower()
                        if text:
                            print(f"  heard: {text}")
                    except RuntimeError as e:
                        self._emit("error", f"STT API: {e}")
                        time.sleep(2)
                        continue
                    except Exception as e:
                        print(f"  STT error: {e}")
                        text = ""

                    # Check for wake words
                    for wake in self._wake_words:
                        if wake in text:
                            now = time.time()
                            if now - self._last_trigger > self._cooldown:
                                self._last_trigger = now
                                self._emit("wake_word", wake)
                                self._launch_jarvis()
                                break

                except Exception as e:
                    self._emit("error", f"Recording error: {e}")
                    time.sleep(0.5)
                    
        except Exception as e:
            self._emit("error", f"Wake word error: {e}")
        finally:
            self._listening = False
            self._emit("stopped")
    
    def _resolve_device(self):
        """Default input device and its native sample rate (never guess 16 kHz)."""
        try:
            default_in = sd.default.device
            try:
                device = int(default_in[0])
            except Exception:
                device = int(default_in)
            if device < 0:
                device = None
                for i, dev in enumerate(sd.query_devices()):
                    if dev.get("max_input_channels", 0) > 0:
                        device = i
                        break
            rate = 16000
            if device is not None:
                rate = int(sd.query_devices(device).get("default_samplerate") or 16000)
            return device, rate
        except Exception:
            return None, self._sample_rate

    def _boost_audio(self, audio_np, target_rms=3000):
        """Amplify quiet audio to improve STT accuracy"""
        rms = np.sqrt(np.mean(audio_np.astype(np.float64) ** 2))
        if rms < 1:
            return audio_np
        gain = min(target_rms / rms, 10.0)
        if gain > 1.2:
            audio_np = (audio_np.astype(np.float64) * gain)
            audio_np = np.clip(audio_np, -32768, 32767).astype(np.int16)
        return audio_np

    def _launch_jarvis(self):
        """Launch the main assistant app (JARVIS by default, DIVA if configured)"""
        try:
            script_dir = Path(__file__).parent
            run_script = script_dir / self._launch_script
            
            if run_script.exists():
                if sys.platform == "win32":
                    subprocess.Popen(
                        [sys.executable, str(run_script)],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        cwd=str(script_dir)
                    )
                else:
                    subprocess.Popen(
                        [sys.executable, str(run_script)],
                        cwd=str(script_dir)
                    )
                self._emit("launched", f"{self._display_name} started")
            else:
                self._emit("error", f"{self._launch_script} not found")
        except Exception as e:
            self._emit("error", f"Launch failed: {e}")
    
    def start(self):
        if self._listening:
            return
        self._listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._listening = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None


def main():
    """Run as standalone wake word listener"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS Wake Word Listener")
    parser.add_argument("--install-service", action="store_true", 
                       help="Install as Windows startup service")
    args = parser.parse_args()
    
    if args.install_service:
        install_startup_service()
        return
    
    listener = WakeWordListener()
    
    def on_wake(word):
        print(f"Wake word detected: {word}")
    
    def on_launched(msg):
        print(msg)
    
    def on_error(err):
        print(f"Error: {err}")
    
    listener.on("wake_word", on_wake)
    listener.on("launched", on_launched)
    listener.on("error", on_error)
    listener.on("listening", lambda msg: print(f"Status: {msg}"))
    
    print("Starting wake word listener...")
    print("Say 'hey jarvis' to launch JARVIS")
    print("Press Ctrl+C to stop")
    
    listener.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        listener.stop()


def install_startup_service():
    """Install as Windows startup task"""
    if sys.platform != "win32":
        print("Service install only for Windows")
        return
    
    import winreg
    
    try:
        script_path = Path(__file__).resolve()
        python_exe = sys.executable
        
        # Add to Windows startup registry
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "JarvisWakeWord", 0, winreg.REG_SZ,
                         f'"{python_exe}" "{script_path}"')
        winreg.CloseKey(key)
        
        print("Wake word listener installed to startup")
        print("It will run automatically on next login")
    except Exception as e:
        print(f"Install failed: {e}")


if __name__ == "__main__":
    main()