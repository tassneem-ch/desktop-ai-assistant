"""JARVIS - Main entry point with full integration"""

import json
import os
import sys
import threading

from jarvis_app.ai import AIEngine
from jarvis_app.memory import MemoryStore
from jarvis_app.security import Governance
from jarvis_app.tools import create_default_registry
from jarvis_app.core import AgentOrchestrator
from jarvis_app.gui import JarvisGUI
from jarvis_app.voice import VoiceEngine


def load_env(path=".env"):
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key and val:
                os.environ.setdefault(key, val)


class JarvisApp:
    def __init__(self):
        load_env()

        self.ai = AIEngine()
        self.memory = MemoryStore()
        self.governance = Governance()
        self.tools = create_default_registry()

        gov_level = int(os.environ.get("JARVIS_GOVERNANCE_LEVEL", "1"))
        self.governance.set_level(gov_level)

        self.voice = VoiceEngine()

        self.orchestrator = AgentOrchestrator(
            self.ai, self.tools, self.memory, self.governance
        )

        self.gui = JarvisGUI(self.orchestrator, self.voice, self.voice.stop_speech)
        self._setup_callbacks()

    def _setup_callbacks(self):
        _streaming_text = []
        _tool_response = False
        g = self.gui

        def on_partial(chunk):
            nonlocal _streaming_text, _tool_response
            if chunk.strip().startswith('{'):
                _tool_response = True
                _streaming_text = []
                return
            if _tool_response:
                return
            _streaming_text.append(chunk)
            text = ''.join(_streaming_text)
            g.after_safe(lambda t=text: g.show_response(t, "ai"))
            g.after_safe(lambda: g.set_viz_state("speaking"))

        def on_response(response):
            nonlocal _streaming_text, _tool_response
            _streaming_text = []
            is_tool = False
            try:
                obj = json.loads(response.strip())
                if isinstance(obj, dict) and "tool" in obj and "params" in obj:
                    is_tool = True
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
            _tool_response = False
            g.after_safe(lambda: g._set_status("◆ READY"))
            g.after_safe(lambda: g.play_sound("done"))
            if is_tool:
                g.after_safe(lambda: g.set_viz_state("idle"))
                g.after_safe(lambda: g.clear_response())
                return
            self.voice.speak(response)
            g.after_safe(lambda r=response: g.add_message("ai", r))

        def on_thinking(thought):
            g = self.gui
            g.after_safe(lambda: g.add_message("thinking", thought))
            g.after_safe(lambda: g.set_viz_state("thinking"))
            g.after_safe(lambda: g.play_sound("thinking"))

        def on_tool_result(tool, result):
            self.gui.after_safe(lambda: self.gui.add_message("tool", f"{tool} → {result[:120]}"))

        def on_error(error):
            g = self.gui
            g.after_safe(lambda: g.add_message("error", error))
            g.after_safe(lambda: g.play_sound("error"))

        def on_mode_change(mode):
            self.gui.after_safe(lambda: self.gui._set_status(f"Mode: {mode.upper()}", "#ff8800" if mode == "plan" else "#00ff88"))

        self.orchestrator.on("partial", on_partial)
        self.orchestrator.on("response", on_response)
        self.orchestrator.on("thinking", on_thinking)
        self.orchestrator.on("tool_result", on_tool_result)
        self.orchestrator.on("error", on_error)
        self.orchestrator.on("mode_change", on_mode_change)

    def run(self):
        self.gui.run()


def main():
    import tkinter as tk
    app = JarvisApp()
    app.run()


if __name__ == "__main__":
    main()
