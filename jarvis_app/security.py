"""Governance & Security for JARVIS"""


class Governance:
    LOW = 0
    MEDIUM = 1
    HIGH = 2

    def __init__(self):
        self.level = self.MEDIUM
        self._always_blocked = {
            "format_drive", "shutdown_force", "delete_system_file",
            "modify_registry", "rmdir_force"
        }

    def set_level(self, level):
        self.level = max(0, min(2, level))

    def is_action_allowed(self, tool_name, params=None):
        if params is None:
            params = {}

        if tool_name in self._always_blocked:
            return False, "Tool is always blocked for security"

        action = params.get("action", "")
        path = params.get("path", "")

        if self.level >= self.HIGH:
            if tool_name in ("file_write", "file_io", "run_command"):
                return False, "Blocked at High governance level"

        if self.level >= self.MEDIUM:
            if action in ("delete", "shutdown", "restart"):
                return False, f"Action '{action}' requires user confirmation"
            if "\\Windows\\" in path.upper() or "\\System32\\" in path.upper():
                return False, "System directory access blocked"

        return True, ""

    def get_description(self):
        return {0: "Low - All tools allowed",
                1: "Medium - Destructive actions blocked",
                2: "High - Read-only, system commands blocked"}.get(self.level, "Unknown")
