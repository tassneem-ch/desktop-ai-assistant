"""DIVA — Main entry point.

Reuses every JARVIS engine (AI, voice, tools, security, memory, config)
and swaps in DIVA's identity: personality prompt, female voice, feminine
GUI. Runs independently from JARVIS with its own config directory.
"""

import os

from diva_app import config as dcfg          # noqa: E402  (env bootstrap in __init__)
from diva_app.core import DivaOrchestrator
from diva_app.gui import DivaGUI
from jarvis_app.main import JarvisApp, load_env


class DivaApp(JarvisApp):
    ORCHESTRATOR_CLS = DivaOrchestrator
    GUI_CLS = DivaGUI

    def __init__(self):
        # debug hooks: DIVA_* aliases for the shared JARVIS_* automation vars
        if os.environ.pop("DIVA_OPEN_SETTINGS", None):
            os.environ["JARVIS_OPEN_SETTINGS"] = "1"
        if os.environ.pop("DIVA_SETTINGS_SELFTEST", None):
            os.environ["JARVIS_SETTINGS_SELFTEST"] = "1"

        dcfg.ensure_seeded()   # inherit AI credentials from JARVIS once
        super().__init__()     # load_env -> engines -> orchestrator -> GUI

        # personalized startup greeting (text only; no surprise audio)
        self.gui.root.after(700, self.gui.show_greeting)


def main():
    app = DivaApp()
    app.run()


if __name__ == "__main__":
    main()
