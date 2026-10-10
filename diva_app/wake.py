"""DIVA Wake Word Listener.

Reuses the JARVIS listener (sounddevice + shared parallel recognizer) with
DIVA's own wake words; when heard, it launches run_diva.py (the DIVA app).

Usage:
    python -m diva_app.wake               # default DIVA wake words
    python -m diva_app.wake --words "astra, hey astra"
"""

import argparse
import sys
from pathlib import Path

# make the repo importable when launched as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from diva_app import config as dcfg          # noqa: E402  (env bootstrap)
from wake_word import WakeWordListener       # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="DIVA Wake Word Listener")
    parser.add_argument("--words", default=None,
                        help="Comma-separated wake words (default: saved DIVA setting)")
    parser.add_argument("--install-service", action="store_true",
                        help="Install as Windows startup service (JARVIS helper)")
    args = parser.parse_args()

    if args.install_service:
        from wake_word import install_startup_service
        install_startup_service()
        return

    if args.words:
        words = [w.strip() for w in args.words.split(",") if w.strip()]
    else:
        words = dcfg.get_wake_words()

    listener = WakeWordListener(wake_words=words,
                                launch_script="run_diva.py",
                                display_name=dcfg.get_name())

    listener.on("wake_word", lambda w: print(f"Wake word detected: {w}"))
    listener.on("launched", lambda m: print(m))
    listener.on("error", lambda e: print(f"Error: {e}"))
    listener.on("listening", lambda m: print(f"Status: {m}"))

    print("Starting DIVA wake word listener...")
    print(f"Say one of: {', '.join(words[:6])}{'…' if len(words) > 6 else ''}")
    print("Press Ctrl+C to stop")

    listener.start()
    try:
        import time
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
        listener.stop()


if __name__ == "__main__":
    main()
