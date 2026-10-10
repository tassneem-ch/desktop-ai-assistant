"""DIVA orchestrator — JARVIS's agent loop with DIVA's personality prompt."""

import os

from jarvis_app.core import AgentOrchestrator

from diva_app import config as dcfg
from diva_app import identity


class DivaOrchestrator(AgentOrchestrator):
    """Same ReAct loop, tools and governance as JARVIS; only the system
    prompt (persona + shared tool guide) differs, driven by DIVA settings."""

    def __init__(self, ai_engine, tool_registry, memory_store, governance):
        super().__init__(ai_engine, tool_registry, memory_store, governance)
        self.intensity = dcfg.get_intensity()
        self.assistant_name = dcfg.get_name()

    def _get_system_prompt(self):
        base = identity.build_prompt(self.intensity, self.assistant_name)
        if self.mode == "plan":
            base += identity.plan_extra()
        return base

    def set_intensity(self, level):
        """Change personality intensity live and persist it."""
        self.intensity = dcfg.set_intensity(level)
        return self.intensity

    def set_assistant_name(self, name):
        self.assistant_name = dcfg.set_name(name)
        return self.assistant_name
