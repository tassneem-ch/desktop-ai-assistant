"""JARVIS Tools - 35+ tools for web, file, system, utilities"""

import json
import os
import socket
import struct
import sys
import subprocess
import ssl
import urllib.request
import urllib.parse
import re
import random
import string
import math
import time
import tempfile
import datetime
import threading
import hashlib
import hmac
import mimetypes
import textwrap
import base64
import urllib.error

_XOR = bytes([29, 10, 96, 1, 29, 95, 63, 16, 25, 10, 5, 4, 22, 8, 66, 17, 84, 127, 89, 3, 120, 93, 95, 71, 123, 71, 82, 10, 82, 4, 16, 95, 20, 20, 85, 44, 88, 87, 116, 95, 10, 22, 124, 71, 5, 7, 1, 6, 68, 94, 79, 22, 7, 47, 15, 2, 116, 88, 9, 20, 42, 16, 5, 87, 4, 84, 69, 10, 71, 20, 89, 121, 86])
_MASK = b'naMnorI!4202sivraJ'
DEFAULT_API_KEY = bytes(a ^ b for a, b in zip(_XOR, _MASK * (len(_XOR) // len(_MASK) + 1))).decode()


class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._history = []

    def register(self, name, tool):
        self._tools[name] = tool

    def get(self, name):
        return self._tools.get(name)

    def list_tools(self):
        return list(self._tools.keys())

    def add_history(self, entry):
        self._history.append(entry)
        if len(self._history) > 50:
            self._history.pop(0)

    def get_history(self, tool=None):
        if tool:
            return [h for h in self._history if h.get("tool") == tool]
        return self._history


class BaseTool:
    def execute(self, params):
        raise NotImplementedError


class WebSearchTool(BaseTool):
    def execute(self, params):
        query = params.get("query", "")
        if not query:
            return {"success": False, "result": "No query provided"}
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=6))
            if not results:
                return {"success": True, "result": "No results found"}
            lines = []
            for r in results:
                title = r.get("title", "")
                href = r.get("href", "")
                body = r.get("body", "")
                if title and href:
                    lines.append(f"• [{title}]({href})\n  {body[:150]}")
            return {"success": True, "result": f"Results for '{query}':\n" + "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"Search error: {e}"}


class FileIOTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "read")
        path = params.get("path", "")
        content = params.get("content", "")
        if not path:
            return {"success": False, "result": "No path provided"}
        try:
            if action == "read":
                with open(path, "r", encoding="utf-8") as f:
                    data = f.read()
                return {"success": True, "result": data[:5000]}
            elif action == "write":
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"success": True, "result": f"Saved to {os.path.basename(path)}"}
            elif action == "list":
                entries = os.listdir(path)
                files = [e for e in entries if os.path.isfile(os.path.join(path, e))]
                dirs = [e + "/" for e in entries if os.path.isdir(os.path.join(path, e))]
                return {"success": True, "result": f"Dirs: {', '.join(dirs[:20])}\nFiles: {', '.join(files[:30])}"}
            elif action == "info":
                stat = os.stat(path)
                return {"success": True, "result":
                    f"Size: {_format_size(stat.st_size)}, Modified: {_format_time(stat.st_mtime)}"}
            elif action == "delete":
                os.remove(path)
                return {"success": True, "result": f"Deleted {path}"}
            else:
                return {"success": False, "result": f"Unknown action: {action}"}
        except Exception as e:
            return {"success": False, "result": f"File error: {e}"}


class SystemControlTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "")
        command = params.get("command", "")
        try:
            if action == "run" and command:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                output = result.stdout[:2000] + ("\n" + result.stderr[:500] if result.stderr else "")
                return {"success": True, "result": output or "Done (no output)"}
            elif action == "open":
                target = params.get("target", "")
                if hasattr(os, "startfile"):
                    os.startfile(target)
                else:
                    subprocess.Popen(["xdg-open", target])
                return {"success": True, "result": f"Opened {target}"}
            else:
                return {"success": False, "result": f"Unknown action: {action}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "result": "Command timed out"}
        except Exception as e:
            return {"success": False, "result": f"System error: {e}"}


class CalculatorTool(BaseTool):
    def __init__(self):
        self.history = []

    def execute(self, params):
        expr = params.get("expression", "") or params.get("expr", "")
        if not expr:
            return {"success": False, "result": "No expression"}
        try:
            safe = re.sub(r"[^0-9+\-*/.()% eE ]", "", expr)
            result = eval(safe, {"__builtins__": {}}, {"math": math})
            entry = {"expr": expr, "result": result}
            self.history.append(entry)
            return {"success": True, "result": f"{expr} = {result}"}
        except Exception as e:
            return {"success": False, "result": f"Calc error: {e}"}


class WeatherTool(BaseTool):
    def execute(self, params):
        location = params.get("location", params.get("query", ""))
        if not location:
            return {"success": False, "result": "No location"}
        try:
            encoded = urllib.parse.quote(location)
            url = f"https://wttr.in/{encoded}?format=%C+%t+%w+%h&lang=en"
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read().decode().strip()
            data = data.encode('ascii', 'replace').decode()
            return {"success": True, "result": f"Weather in {location}: {data}"}
        except Exception as e:
            return {"success": False, "result": f"Weather error: {e}"}


class TimeTool(BaseTool):
    def execute(self, params):
        tz_name = params.get("timezone", params.get("tz", ""))
        try:
            now = datetime.datetime.now(datetime.timezone.utc).astimezone()
            result = now.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")
            utc = datetime.datetime.now(datetime.timezone.utc)
            return {"success": True, "result": f"Local time: {result}\nUTC: {utc.strftime('%Y-%m-%d %H:%M:%S UTC')}"}
        except Exception as e:
            return {"success": False, "result": f"Time error: {e}"}


class SystemInfoTool(BaseTool):
    def execute(self, params):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            boot = datetime.datetime.fromtimestamp(psutil.boot_time())
            info = (
                f"CPU: {cpu}% ({psutil.cpu_count()} cores)\n"
                f"RAM: {_format_size(mem.used)} / {_format_size(mem.total)} ({mem.percent}%)\n"
                f"Disk: {_format_size(disk.used)} / {_format_size(disk.total)} ({disk.percent}%)\n"
                f"Boot: {boot.strftime('%Y-%m-%d %H:%M')}\n"
                f"Processes: {len(psutil.pids())}"
            )
            return {"success": True, "result": info}
        except ImportError:
            import platform
            uname = platform.uname()
            return {"success": True, "result":
                f"OS: {uname.system} {uname.release}\n"
                f"Node: {uname.node}\n"
                f"Arch: {uname.machine}"}
        except Exception as e:
            return {"success": False, "result": f"Error: {e}"}


class ScreenshotTool(BaseTool):
    def execute(self, params):
        try:
            import pyautogui
            path = os.path.join(tempfile.gettempdir(), "jarvis_screenshot.png")
            img = pyautogui.screenshot(path)
            return {"success": True, "result": f"Screenshot saved: {path} ({img.width}x{img.height})"}
        except ImportError:
            return {"success": False, "result": "pyautogui not installed"}
        except Exception as e:
            return {"success": False, "result": f"Screenshot error: {e}"}


class VisionTool(BaseTool):
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY", DEFAULT_API_KEY)
        self.base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = "nvidia/nemotron-nano-12b-v2-vl:free"

    def _image_to_base64(self, image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def execute(self, params):
        action = params.get("action", "analyze")
        prompt = params.get("prompt", "Describe what you see in this image")
        image_path = params.get("image", params.get("path", ""))
        
        try:
            if action == "analyze":
                if not image_path:
                    # Take screenshot
                    import pyautogui
                    path = os.path.join(tempfile.gettempdir(), f"vision_{int(time.time())}.png")
                    img = pyautogui.screenshot(path)
                    image_path = path
                
                if not os.path.exists(image_path):
                    return {"success": False, "result": "Image not found"}
                
                # Encode image
                b64 = self._image_to_base64(image_path)
                mime = mimetypes.guess_type(image_path)[0] or "image/png"
                
                # Call vision model
                import requests
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
                payload = {
                    "model": self.model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                        ]
                    }],
                    "max_tokens": 512,
                    "stream": False,
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code != 200:
                    return {"success": False, "result": f"API error: {resp.status_code} {resp.text[:200]}"}
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return {"success": True, "result": content}
                return {"success": False, "result": "No response from vision model"}
            
            elif action == "screenshot":
                import pyautogui
                path = os.path.join(tempfile.gettempdir(), f"vision_{int(time.time())}.png")
                img = pyautogui.screenshot(path)
                return {"success": True, "result": f"Screenshot saved: {path}"}
            
            return {"success": False, "result": "Actions: analyze, screenshot"}
        except ImportError:
            return {"success": False, "result": "pyautogui not installed"}
        except Exception as e:
            return {"success": False, "result": f"Vision error: {e}"}


class NotesTool(BaseTool):
    def __init__(self):
        self.notes_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "JarvisAssistant", "notes")
        os.makedirs(self.notes_dir, exist_ok=True)

    def execute(self, params):
        action = params.get("action", "list")
        title = params.get("title", params.get("name", "note"))
        content = params.get("content", params.get("text", ""))
        try:
            if action == "save":
                path = os.path.join(self.notes_dir, f"{title}.txt")
                with open(path, "w") as f:
                    f.write(content)
                return {"success": True, "result": f"Note saved: {title}"}
            elif action == "read":
                path = os.path.join(self.notes_dir, f"{title}.txt")
                if not os.path.exists(path):
                    return {"success": False, "result": f"Note '{title}' not found"}
                with open(path, "r") as f:
                    return {"success": True, "result": f"**{title}**:\n{f.read()[:2000]}"}
            elif action == "list":
                notes = [f.replace(".txt", "") for f in os.listdir(self.notes_dir) if f.endswith(".txt")]
                return {"success": True, "result": f"Notes ({len(notes)}): {', '.join(notes) or 'None'}"}
            elif action == "delete":
                path = os.path.join(self.notes_dir, f"{title}.txt")
                if os.path.exists(path):
                    os.remove(path)
                    return {"success": True, "result": f"Deleted note: {title}"}
                return {"success": False, "result": f"Note not found: {title}"}
            else:
                return {"success": False, "result": "Actions: save, read, list, delete"}
        except Exception as e:
            return {"success": False, "result": f"Notes error: {e}"}


class TodoTool(BaseTool):
    def __init__(self):
        self.todo_file = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "JarvisAssistant", "todos.json")
        os.makedirs(os.path.dirname(self.todo_file), exist_ok=True)
        if not os.path.exists(self.todo_file):
            with open(self.todo_file, "w") as f:
                json.dump([], f)

    def _load(self):
        with open(self.todo_file, "r") as f:
            return json.load(f)

    def _save(self, todos):
        with open(self.todo_file, "w") as f:
            json.dump(todos, f, indent=2)

    def execute(self, params):
        action = params.get("action", "list")
        try:
            todos = self._load()
            
            if action == "add":
                task = params.get("task", params.get("title", ""))
                if not task:
                    return {"success": False, "result": "Task required"}
                priority = params.get("priority", "medium")
                todos.append({
                    "id": str(time.time()),
                    "task": task,
                    "priority": priority,
                    "done": False,
                    "created": datetime.datetime.now().isoformat()
                })
                self._save(todos)
                return {"success": True, "result": f"Added: {task}"}
            
            elif action == "list":
                filter_done = params.get("filter")
                if filter_done == "active":
                    todos = [t for t in todos if not t["done"]]
                elif filter_done == "done":
                    todos = [t for t in todos if t["done"]]
                
                if not todos:
                    return {"success": True, "result": "No tasks"}
                
                lines = []
                for t in todos:
                    status = "✓" if t["done"] else "☐"
                    pri = t.get("priority", "medium")[0].upper()
                    lines.append(f"{status} [{pri}] {t['task']}")
                return {"success": True, "result": "\n".join(lines)}
            
            elif action == "done":
                task_id = params.get("id")
                for t in todos:
                    if t["id"] == task_id:
                        t["done"] = True
                        self._save(todos)
                        return {"success": True, "result": f"Completed: {t['task']}"}
                return {"success": False, "result": "Task not found"}
            
            elif action == "remove":
                task_id = params.get("id")
                todos = [t for t in todos if t["id"] != task_id]
                self._save(todos)
                return {"success": True, "result": "Removed"}
            
            elif action == "clear":
                self._save([t for t in todos if not t["done"]])
                return {"success": True, "result": "Cleared completed"}
            
            return {"success": False, "result": "Actions: add, list, done, remove, clear"}
        except Exception as e:
            return {"success": False, "result": f"Todo error: {e}"}


class ClipboardTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "get")
        text = params.get("text", "")
        try:
            import pyperclip
            if action == "get":
                content = pyperclip.paste()
                return {"success": True, "result": f"Clipboard: {content[:500]}"}
            elif action == "set":
                pyperclip.copy(text)
                return {"success": True, "result": f"Copied: {text[:100]}"}
            else:
                return {"success": False, "result": "Actions: get, set"}
        except ImportError:
            return {"success": False, "result": "pyperclip not installed"}


class DictTool(BaseTool):
    def execute(self, params):
        word = params.get("word", params.get("query", ""))
        if not word:
            return {"success": False, "result": "No word"}
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())[0]
            meanings = data.get("meanings", [])
            parts = []
            for m in meanings[:3]:
                defs = m.get("definitions", [])[:2]
                def_texts = [f"  - {d.get('definition', '')}" for d in defs]
                parts.append(f"*{m.get('partOfSpeech', '?')}*:\n" + "\n".join(def_texts))
            phonetic = data.get("phonetic", data.get("phonetics", [{}])[0].get("text", ""))
            result = f"**{word}** {phonetic}\n" + "\n".join(parts)
            return {"success": True, "result": result}
        except urllib.error.HTTPError as e:
            return {"success": False, "result": f"Word not found" if e.code == 404 else f"Error: {e}"}
        except Exception as e:
            return {"success": False, "result": f"Dict error: {e}"}


class JokesTool(BaseTool):
    def execute(self, params):
        try:
            url = "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,racist,sexist&format=txt"
            req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                joke = resp.read().decode().strip()
            return {"success": True, "result": joke}
        except Exception as e:
            return {"success": False, "result": f"Joke error: {e}"}


class QuoteTool(BaseTool):
    FALLBACKS = [
        '"The only way to do great work is to love what you do." — Steve Jobs',
        '"In the middle of every difficulty lies opportunity." — Albert Einstein',
        '"Be yourself; everyone else is already taken." — Oscar Wilde',
        '"Two things are infinite: the universe and human stupidity." — Albert Einstein',
        '"The best time to plant a tree was 20 years ago. The second best time is now." — Chinese Proverb',
    ]

    def execute(self, params):
        for url in [
            "https://zenquotes.io/api/random",
            "https://api.quotable.io/random",
            "https://quotes.rest/qod",
        ]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/1.0"})
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                    data = json.loads(resp.read())
                    if isinstance(data, list) and data:
                        q = data[0]
                        return {"success": True, "result": f'"{q.get("q", q.get("content", ""))}"\n— {q.get("a", q.get("author", ""))}'}
                    if isinstance(data, dict):
                        quotes = data.get("quotes", [data])
                        if quotes:
                            q = quotes[0]
                            return {"success": True, "result": f'"{q.get("quote", q.get("content", ""))}"\n— {q.get("author", q.get("title", ""))}'}
            except Exception:
                continue
        return {"success": True, "result": random.choice(self.FALLBACKS)}


class PasswordTool(BaseTool):
    def execute(self, params):
        length = params.get("length", 16)
        include_symbols = params.get("symbols", True)
        try:
            length = max(4, min(128, int(length)))
            chars = string.ascii_letters + string.digits
            if include_symbols:
                chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
            pwd = "".join(random.choice(chars) for _ in range(length))
            return {"success": True, "result": f"Password ({length} chars): `{pwd}`"}
        except Exception as e:
            return {"success": False, "result": f"Error: {e}"}


class ConvertTool(BaseTool):
    UNITS = {
        "length": {"m": 1, "km": 1000, "cm": 0.01, "mm": 0.001, "mi": 1609.34, "ft": 0.3048, "in": 0.0254},
        "mass": {"kg": 1, "g": 0.001, "lb": 0.453592, "oz": 0.0283495, "t": 1000},
        "temp": {"c": "c", "f": "f", "k": "k"},
        "speed": {"m/s": 1, "km/h": 0.277778, "mph": 0.44704, "knot": 0.514444},
    }

    def execute(self, params):
        value = params.get("value")
        from_unit = params.get("from", "")
        to_unit = params.get("to", "")
        category = params.get("category", self._detect_category(from_unit, to_unit))
        if value is None or not from_unit or not to_unit:
            return {"success": False, "result": "Usage: value=X, from=unit, to=unit"}
        try:
            value = float(value)
            if category == "temp":
                if from_unit == "c" and to_unit == "f":
                    result = value * 9/5 + 32
                elif from_unit == "f" and to_unit == "c":
                    result = (value - 32) * 5/9
                elif from_unit == "c" and to_unit == "k":
                    result = value + 273.15
                elif from_unit == "k" and to_unit == "c":
                    result = value - 273.15
                else:
                    return {"success": False, "result": "Unsupported temp conversion"}
            else:
                units = self.UNITS.get(category, {})
                if from_unit not in units or to_unit not in units:
                    return {"success": False, "result": f"Unknown units. Available: {list(units.keys())}"}
                result = value * units[from_unit] / units[to_unit]
            return {"success": True, "result": f"{value} {from_unit} = {result:.4f} {to_unit}"}
        except Exception as e:
            return {"success": False, "result": f"Convert error: {e}"}

    def _detect_category(self, a, b):
        for cat, units in self.UNITS.items():
            if a in units or b in units:
                return cat
        return "length"


class FileSearchTool(BaseTool):
    def execute(self, params):
        pattern = params.get("pattern", "")
        root = params.get("path", os.path.expanduser("~"))
        if not pattern:
            return {"success": False, "result": "No search pattern"}
        try:
            results = []
            for dirpath, dirnames, filenames in os.walk(root):
                for f in filenames:
                    if pattern.lower() in f.lower():
                        results.append(os.path.join(dirpath, f))
                        if len(results) >= 30:
                            break
                if len(results) >= 30:
                    break
            if results:
                return {"success": True, "result": f"Found {len(results)}:\n" + "\n".join(results[:20])}
            return {"success": True, "result": "No files found"}
        except Exception as e:
            return {"success": False, "result": f"Search error: {e}"}


class BatteryTool(BaseTool):
    def execute(self, params):
        try:
            import psutil
            batt = psutil.sensors_battery()
            if not batt:
                return {"success": True, "result": "No battery detected"}
            pct = batt.percent
            plugged = "Charging" if batt.power_plugged else "On battery"
            secs = batt.secsleft
            time_left = f"{secs // 3600}h {secs % 3600 // 60}m" if secs != -1 else "Unknown"
            return {"success": True, "result": f"Battery: {pct}% ({plugged})\nTime left: {time_left}"}
        except ImportError:
            return {"success": False, "result": "psutil not installed"}
        except Exception as e:
            return {"success": False, "result": f"Battery error: {e}"}


class ProcessTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "list")
        name = params.get("name", "")
        try:
            import psutil
            if action == "list":
                procs = []
                for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                    try:
                        procs.append(f"{p.info['pid']:6d} {p.info['name'][:30]:30s} "
                                     f"CPU:{p.info['cpu_percent'] or 0:5.1f}% MEM:{p.info['memory_percent'] or 0:5.1f}%")
                    except:
                        pass
                return {"success": True, "result": "Processes:\n" + "\n".join(procs[:30])}
            elif action == "kill" and name:
                for p in psutil.process_iter(["pid", "name"]):
                    if name.lower() in p.info["name"].lower():
                        p.kill()
                        return {"success": True, "result": f"Killed {p.info['name']} (PID {p.info['pid']})"}
                return {"success": False, "result": f"No process matching '{name}'"}
            else:
                return {"success": False, "result": "Actions: list, kill"}
        except ImportError:
            return {"success": False, "result": "psutil not installed"}
        except Exception as e:
            return {"success": False, "result": f"Error: {e}"}


class RandomTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "number")
        try:
            if action == "number":
                min_n = int(params.get("min", 1))
                max_n = int(params.get("max", 100))
                return {"success": True, "result": f"Random number between {min_n} and {max_n}: {random.randint(min_n, max_n)}"}
            elif action == "coin":
                return {"success": True, "result": f"Coin flip: {random.choice(['Heads', 'Tails'])}"}
            elif action == "dice":
                sides = int(params.get("sides", 6))
                return {"success": True, "result": f"D{sides} roll: {random.randint(1, sides)}"}
            elif action == "choice":
                options = params.get("options", "")
                items = [x.strip() for x in options.split(",") if x.strip()]
                if items:
                    return {"success": True, "result": f"Chose: {random.choice(items)}"}
                return {"success": False, "result": "No options provided (comma-separated)"}
            elif action == "uuid":
                import uuid
                return {"success": True, "result": f"UUID: {uuid.uuid4()}"}
            else:
                return {"success": False, "result": "Actions: number, coin, dice, choice, uuid"}
        except Exception as e:
            return {"success": False, "result": f"Error: {e}"}


class NewsTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", params.get("query", ""))
        try:
            import xml.etree.ElementTree as ET
            if topic:
                url = f"https://news.google.com/rss/search?q={urllib.parse.quote(topic)}&hl=en-US&gl=US&ceid=US:en"
            else:
                url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                tree = ET.parse(resp)
            root = tree.getroot()
            items = root.findall(".//item")[:8]
            if not items:
                return {"success": False, "result": "No news found. Try a different topic."}
            lines = []
            for item in items:
                title = item.findtext("title", "")
                source = item.findtext("source", "")
                if source:
                    lines.append(f"• [{source}] {title[:150]}")
                else:
                    lines.append(f"• {title[:150]}")
            return {"success": True, "result": (f"News about '{topic}':\n" if topic else "Top headlines:\n") + "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"News error: {e}"}


class ShortenTool(BaseTool):
    def execute(self, params):
        url = params.get("url", "")
        if not url:
            return {"success": False, "result": "No URL provided"}
        try:
            data = urllib.parse.urlencode({"url": url}).encode()
            req = urllib.request.Request("https://is.gd/create.php?format=simple",
                                         data=data,
                                         headers={"User-Agent": "Jarvis/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                short = resp.read().decode().strip()
            if short and not short.startswith("Error"):
                return {"success": True, "result": f"Shortened: {short}"}
            return {"success": False, "result": f"Shorten failed: {short}"}
        except Exception as e:
            return {"success": False, "result": f"Error: {e}"}


class IPGeoTool(BaseTool):
    def execute(self, params):
        ip = params.get("ip", params.get("query", ""))
        try:
            if ip:
                url = f"http://ip-api.com/json/{urllib.parse.quote(ip)}"
            else:
                url = "http://ip-api.com/json/"
            req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            if data.get("status") == "success":
                return {"success": True, "result":
                    f"IP: {data.get('query', 'N/A')}\n"
                    f"Location: {data.get('city', '')}, {data.get('regionName', '')}, {data.get('country', '')}\n"
                    f"ISP: {data.get('isp', 'N/A')}\n"
                    f"Lat/Lon: {data.get('lat', 'N/A')}, {data.get('lon', 'N/A')}"}
            return {"success": False, "result": "Could not determine location"}
        except Exception as e:
            return {"success": False, "result": f"Error: {e}"}


class EmailTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "send")
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            smtp_server = params.get("smtp_server", "smtp.gmail.com")
            smtp_port = int(params.get("smtp_port", 587))
            username = params.get("username", "")
            password = params.get("password", "")
            
            if action == "send":
                to = params.get("to", "")
                subject = params.get("subject", "")
                body = params.get("body", "")
                if not all([to, subject, body, username, password]):
                    return {"success": False, "result": "Missing: to, subject, body, username, password"}
                
                msg = MIMEMultipart()
                msg["From"] = username
                msg["To"] = to
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))
                
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(username, password)
                    server.send_message(msg)
                return {"success": True, "result": f"Email sent to {to}"}
            
            elif action == "check":
                import imaplib
                mail = imaplib.IMAP4_SSL(params.get("imap_server", "imap.gmail.com"))
                mail.login(username, password)
                mail.select("inbox")
                _, data = mail.search(None, "UNSEEN")
                count = len(data[0].split()) if data[0] else 0
                mail.logout()
                return {"success": True, "result": f"Unread emails: {count}"}
            
            return {"success": False, "result": "Actions: send, check"}
        except Exception as e:
            return {"success": False, "result": f"Email error: {e}"}


class CalendarTool(BaseTool):
    def __init__(self):
        self.events_file = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "JarvisAssistant", "calendar.json")
        os.makedirs(os.path.dirname(self.events_file), exist_ok=True)
        if not os.path.exists(self.events_file):
            with open(self.events_file, "w") as f:
                json.dump([], f)
    
    def _load(self):
        with open(self.events_file, "r") as f:
            return json.load(f)
    
    def _save(self, events):
        with open(self.events_file, "w") as f:
            json.dump(events, f, indent=2)
    
    def execute(self, params):
        action = params.get("action", "list")
        try:
            events = self._load()
            now = datetime.datetime.now().isoformat()
            
            if action == "add":
                title = params.get("title", "")
                start = params.get("start", now)
                end = params.get("end", "")
                desc = params.get("description", "")
                if not title:
                    return {"success": False, "result": "Title required"}
                event = {"id": str(time.time()), "title": title, "start": start, "end": end, "description": desc}
                events.append(event)
                self._save(events)
                return {"success": True, "result": f"Event added: {title} at {start}"}
            
            elif action == "list":
                days = int(params.get("days", 7))
                cutoff = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
                upcoming = [e for e in events if e["start"] <= cutoff]
                upcoming.sort(key=lambda x: x["start"])
                if not upcoming:
                    return {"success": True, "result": "No upcoming events"}
                lines = [f"{e['start'][:16]} - {e['title']}" for e in upcoming[:20]]
                return {"success": True, "result": f"Upcoming ({len(upcoming)}):\n" + "\n".join(lines)}
            
            elif action == "delete":
                eid = params.get("id", "")
                events = [e for e in events if e["id"] != eid]
                self._save(events)
                return {"success": True, "result": f"Event {eid} deleted"}
            
            return {"success": False, "result": "Actions: add, list, delete"}
        except Exception as e:
            return {"success": False, "result": f"Calendar error: {e}"}


class ReminderTool(BaseTool):
    def __init__(self):
        self.reminders_file = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "JarvisAssistant", "reminders.json")
        os.makedirs(os.path.dirname(self.reminders_file), exist_ok=True)
        if not os.path.exists(self.reminders_file):
            with open(self.reminders_file, "w") as f:
                json.dump([], f)
        self._running = False
        self._thread = None
    
    def _load(self):
        with open(self.reminders_file, "r") as f:
            return json.load(f)
    
    def _save(self, reminders):
        with open(self.reminders_file, "w") as f:
            json.dump(reminders, f, indent=2)
    
    def execute(self, params):
        action = params.get("action", "list")
        try:
            reminders = self._load()
            
            if action == "add":
                text = params.get("text", "")
                when = params.get("when", "")
                if not text or not when:
                    return {"success": False, "result": "Need text and when (ISO datetime or seconds)"}
                try:
                    if when.isdigit():
                        trigger = datetime.datetime.now() + datetime.timedelta(seconds=int(when))
                    else:
                        trigger = datetime.datetime.fromisoformat(when)
                except:
                    return {"success": False, "result": "Invalid time format. Use seconds or ISO datetime"}
                reminder = {"id": str(time.time()), "text": text, "trigger": trigger.isoformat(), "done": False}
                reminders.append(reminder)
                self._save(reminders)
                self._start_monitor()
                return {"success": True, "result": f"Reminder set for {trigger.strftime('%Y-%m-%d %H:%M')}: {text}"}
            
            elif action == "list":
                pending = [r for r in reminders if not r["done"]]
                if not pending:
                    return {"success": True, "result": "No pending reminders"}
                lines = [f"{r['trigger'][:16]} - {r['text']}" for r in pending]
                return {"success": True, "result": f"Reminders ({len(pending)}):\n" + "\n".join(lines)}
            
            elif action == "clear":
                self._save([r for r in reminders if r["done"]])
                return {"success": True, "result": "Completed reminders cleared"}
            
            return {"success": False, "result": "Actions: add, list, clear"}
        except Exception as e:
            return {"success": False, "result": f"Reminder error: {e}"}
    
    def _start_monitor(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()
    
    def _notify(self, title, message):
        """Toast notification with graceful fallbacks (winotify -> win10toast -> beep)."""
        try:
            from winotify import Notification, audio
            toast = Notification(app_id="JARVIS", title=title, msg=message)
            toast.set_audio(audio.Default, loop=False)
            toast.show()
            return True
        except Exception:
            pass
        try:
            import win10toast
            win10toast.ToastNotifier().show_toast(title, message, duration=10)
            return True
        except Exception:
            pass
        try:
            import winsound
            winsound.Beep(880, 300)
        except Exception:
            pass
        print(f"[reminder] {title}: {message}")
        return False

    def _monitor(self):
        while self._running:
            time.sleep(10)
            reminders = self._load()
            now = datetime.datetime.now()
            changed = False
            for r in reminders:
                if not r["done"]:
                    trigger = datetime.datetime.fromisoformat(r["trigger"])
                    if now >= trigger:
                        try:
                            self._notify("JARVIS Reminder", r["text"])
                        except Exception:
                            pass
                        r["done"] = True
                        changed = True
            if changed:
                self._save(reminders)


class TimerTool(BaseTool):
    def __init__(self):
        self.timers = {}
    
    def execute(self, params):
        action = params.get("action", "start")
        name = params.get("name", "default")
        try:
            if action == "start":
                seconds = int(params.get("seconds", params.get("duration", 60)))
                end_time = time.time() + seconds
                self.timers[name] = {"end": end_time, "paused": False, "elapsed": 0}
                return {"success": True, "result": f"Timer '{name}' started for {seconds}s"}
            
            elif action == "pause":
                if name in self.timers and not self.timers[name]["paused"]:
                    self.timers[name]["elapsed"] += time.time() - self.timers[name]["end"] + self.timers[name]["elapsed"]
                    self.timers[name]["paused"] = True
                    return {"success": True, "result": f"Timer '{name}' paused"}
                return {"success": False, "result": "Timer not running"}
            
            elif action == "resume":
                if name in self.timers and self.timers[name]["paused"]:
                    self.timers[name]["end"] = time.time() + (self.timers[name]["elapsed"] - time.time())
                    self.timers[name]["paused"] = False
                    return {"success": True, "result": f"Timer '{name}' resumed"}
                return {"success": False, "result": "Timer not paused"}
            
            elif action == "stop":
                if name in self.timers:
                    elapsed = self.timers[name].get("elapsed", 0) + (time.time() - self.timers[name]["end"]) + self.timers[name].get("elapsed", 0)
                    del self.timers[name]
                    return {"success": True, "result": f"Timer '{name}' stopped after {int(elapsed)}s"}
                return {"success": False, "result": "Timer not found"}
            
            elif action == "status":
                if name in self.timers:
                    t = self.timers[name]
                    if t["paused"]:
                        remaining = t["elapsed"]
                    else:
                        remaining = t["end"] - time.time() + t.get("elapsed", 0)
                    return {"success": True, "result": f"Timer '{name}': {int(max(0, remaining))}s remaining"}
                return {"success": False, "result": "Timer not found"}
            
            elif action == "list":
                if not self.timers:
                    return {"success": True, "result": "No active timers"}
                lines = []
                for n, t in self.timers.items():
                    rem = t.get("elapsed", 0) + (t["end"] - time.time()) if not t["paused"] else t.get("elapsed", 0)
                    lines.append(f"{n}: {int(max(0, rem))}s {'(paused)' if t['paused'] else ''}")
                return {"success": True, "result": "Timers:\n" + "\n".join(lines)}
            
            return {"success": False, "result": "Actions: start, pause, resume, stop, status, list"}
        except Exception as e:
            return {"success": False, "result": f"Timer error: {e}"}


class TranslatorTool(BaseTool):
    def execute(self, params):
        text = params.get("text", "")
        target = params.get("target", "en")
        source = params.get("source", "en")
        if source == "auto":
            source = "en"
        if target == "auto":
            target = "en"
        if not text:
            return {"success": False, "result": "No text to translate"}
        try:
            url = "https://api.mymemory.translated.net/get"
            data = urllib.parse.urlencode({"q": text, "langpair": f"{source}|{target}"}).encode()
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "Jarvis/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            translated = result.get("responseData", {}).get("translatedText", "")
            if not translated:
                return {"success": False, "result": "Translation failed"}
            return {"success": True, "result": f"Translated ({source}→{target}):\n{translated}"}
        except Exception as e:
            return {"success": False, "result": f"Translation error: {e}"}


class CryptoTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "hash")
        data = params.get("data", "")
        algorithm = params.get("algorithm", "sha256")
        key = params.get("key", "")
        try:
            if action == "hash":
                h = hashlib.new(algorithm)
                h.update(data.encode())
                return {"success": True, "result": f"{algorithm.upper()}: {h.hexdigest()}"}
            
            elif action == "hmac":
                if not key:
                    return {"success": False, "result": "Key required for HMAC"}
                h = hmac.new(key.encode(), data.encode(), getattr(hashlib, algorithm))
                return {"success": True, "result": f"HMAC-{algorithm.upper()}: {h.hexdigest()}"}
            
            elif action == "encode":
                encoded = base64.b64encode(data.encode()).decode()
                return {"success": True, "result": f"Base64: {encoded}"}
            
            elif action == "decode":
                decoded = base64.b64decode(data).decode()
                return {"success": True, "result": f"Decoded: {decoded}"}
            
            elif action == "file_hash":
                if not os.path.exists(data):
                    return {"success": False, "result": "File not found"}
                h = hashlib.new(algorithm)
                with open(data, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                return {"success": True, "result": f"{algorithm.upper()}({os.path.basename(data)}): {h.hexdigest()}"}
            
            return {"success": False, "result": "Actions: hash, hmac, encode, decode, file_hash"}
        except Exception as e:
            return {"success": False, "result": f"Crypto error: {e}"}


class QRCodeTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "generate")
        data = params.get("data", "")
        try:
            import qrcode
            if action == "generate":
                if not data:
                    return {"success": False, "result": "No data provided"}
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(data)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                path = os.path.join(tempfile.gettempdir(), f"qrcode_{int(time.time())}.png")
                img.save(path)
                return {"success": True, "result": f"QR code saved: {path}"}
            
            elif action == "decode":
                from PIL import Image
                import pyzbar.pyzbar as pyzbar
                img_path = data
                if not os.path.exists(img_path):
                    return {"success": False, "result": "Image file not found"}
                img = Image.open(img_path)
                decoded = pyzbar.decode(img)
                if decoded:
                    return {"success": True, "result": f"Decoded: {decoded[0].data.decode()}"}
                return {"success": False, "result": "No QR code found in image"}
            
            return {"success": False, "result": "Actions: generate, decode"}
        except ImportError:
            return {"success": False, "result": "Install: pip install qrcode[pil] pyzbar"}
        except Exception as e:
            return {"success": False, "result": f"QR error: {e}"}


class WindowTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "list")
        try:
            import win32gui
            import win32con
            
            if action == "list":
                windows = []
                def enum_handler(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            windows.append(f"{hwnd}: {title[:80]}")
                win32gui.EnumWindows(enum_handler, None)
                return {"success": True, "result": f"Windows ({len(windows)}):\n" + "\n".join(windows[:30])}
            
            elif action == "get_rect":
                hwnd = int(params.get("hwnd", 0))
                if not hwnd:
                    return {"success": False, "result": "Need hwnd"}
                rect = win32gui.GetWindowRect(hwnd)
                l, t, r, b = rect
                return {"success": True, "result":
                    f"Window rect: left={l}, top={t}, right={r}, bottom={b}, "
                    f"width={r-l}, height={b-t}, center=({(l+r)//2}, {(t+b)//2})"}
            
            elif action == "maximize":
                hwnd = int(params.get("hwnd", 0))
                name = params.get("name", "").lower()
                if not hwnd and name:
                    hwnd = self._find_window(name)
                if not hwnd:
                    return {"success": False, "result": "Specify hwnd or window name"}
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                win32gui.SetForegroundWindow(hwnd)
                return {"success": True, "result": "Window maximized"}
            
            elif action == "minimize":
                hwnd = int(params.get("hwnd", 0))
                name = params.get("name", "").lower()
                if not hwnd and name:
                    hwnd = self._find_window(name)
                if not hwnd:
                    return {"success": False, "result": "Specify hwnd or window name"}
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return {"success": True, "result": "Window minimized"}
            
            elif action == "restore":
                hwnd = int(params.get("hwnd", 0))
                name = params.get("name", "").lower()
                if not hwnd and name:
                    hwnd = self._find_window(name)
                if not hwnd:
                    return {"success": False, "result": "Specify hwnd or window name"}
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return {"success": True, "result": "Window restored"}
            
            elif action == "focus":
                hwnd = int(params.get("hwnd", 0))
                name = params.get("name", "").lower()
                if not hwnd and name:
                    hwnd = self._find_window(name)
                if not hwnd:
                    return {"success": False, "result": "Specify hwnd or window name"}
                win32gui.SetForegroundWindow(hwnd)
                return {"success": True, "result": "Window focused"}
            
            elif action == "close":
                hwnd = int(params.get("hwnd", 0))
                name = params.get("name", "").lower()
                if not hwnd and name:
                    hwnd = self._find_window(name)
                if not hwnd:
                    return {"success": False, "result": "Specify hwnd or window name"}
                win32gui.SendMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                return {"success": True, "result": "Window close sent"}
            
            elif action == "move":
                hwnd = int(params.get("hwnd", 0))
                name = params.get("name", "").lower()
                if not hwnd and name:
                    hwnd = self._find_window(name)
                if not hwnd:
                    return {"success": False, "result": "Specify hwnd or window name"}
                x = int(params.get("x", 0))
                y = int(params.get("y", 0))
                w = int(params.get("width", params.get("w", 800)))
                h = int(params.get("height", params.get("h", 600)))
                win32gui.SetWindowPos(hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER)
                return {"success": True, "result": f"Window moved to ({x},{y}) size {w}x{h}"}
            
            return {"success": False, "result": "Actions: list, get_rect, maximize, minimize, restore, focus, close, move [name/hwnd]"}
        except ImportError:
            return {"success": False, "result": "pywin32 not installed"}
        except Exception as e:
            return {"success": False, "result": f"Window error: {e}"}

    def _find_window(self, name):
        import win32gui
        targets = []
        def enum_handler(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if name in title:
                    targets.append(hwnd)
        win32gui.EnumWindows(enum_handler, None)
        if targets:
            return targets[0]
        return 0


class AudioTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "volume")
        try:
            from pycaw.pycaw import AudioUtilities
            
            device = AudioUtilities.GetSpeakers()
            volume = device.EndpointVolume
            
            if action == "volume":
                level = params.get("level")
                if level is not None:
                    vol = max(0.0, min(1.0, float(level) / 100))
                    volume.SetMasterVolumeLevelScalar(vol, None)
                    return {"success": True, "result": f"Volume set to {level}%"}
                else:
                    current = int(volume.GetMasterVolumeLevelScalar() * 100)
                    return {"success": True, "result": f"Current volume: {current}%"}
            
            elif action == "mute":
                mute = params.get("mute", True)
                volume.SetMute(1 if mute else 0, None)
                return {"success": True, "result": f"Muted: {mute}"}
            
            elif action == "list_devices":
                devs = AudioUtilities.GetAllDevices()
                return {"success": True, "result": "Devices: " + ", ".join([d.FriendlyName for d in devs])}
            
            return {"success": False, "result": "Actions: volume, mute, list_devices"}
        except ImportError:
            return {"success": False, "result": "pycaw not installed: pip install pycaw comtypes"}
        except Exception as e:
            return {"success": False, "result": f"Audio error: {e}"}


class NetworkTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "info")
        try:
            import psutil
            if action == "info":
                addrs = psutil.net_if_addrs()
                stats = psutil.net_if_stats()
                io = psutil.net_io_counters()
                lines = [f"Interfaces: {len(addrs)}", f"Bytes sent: {_format_size(io.bytes_sent)}", f"Bytes recv: {_format_size(io.bytes_recv)}"]
                for name, addrs_list in addrs.items():
                    for addr in addrs_list:
                        if addr.family == 2:
                            lines.append(f"{name}: {addr.address}")
                return {"success": True, "result": "\n".join(lines)}
            
            elif action == "connections":
                conns = psutil.net_connections(kind="inet")
                lines = [f"{c.laddr.ip}:{c.laddr.port} -> {c.raddr.ip if c.raddr else '*'}:{c.raddr.port if c.raddr else '*'} [{c.status}]" for c in conns[:30]]
                return {"success": True, "result": "Connections:\n" + "\n".join(lines)}
            
            elif action == "ping":
                host = params.get("host", "8.8.8.8")
                import platform
                param = "-n" if platform.system().lower() == "windows" else "-c"
                cmd = ["ping", param, "4", host]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                return {"success": True, "result": result.stdout[-500:]}
            
            elif action == "speed":
                return {"success": False, "result": "Speed test not implemented (requires external API)"}
            
            return {"success": False, "result": "Actions: info, connections, ping, speed"}
        except ImportError:
            return {"success": False, "result": "psutil not installed"}
        except Exception as e:
            return {"success": False, "result": f"Network error: {e}"}


class ArchiveTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "create")
        paths = params.get("paths", [])
        archive = params.get("archive", "")
        try:
            import shutil
            import zipfile
            import tarfile
            
            if not paths:
                return {"success": False, "result": "No paths provided"}
            if not archive:
                return {"success": False, "result": "No archive name"}
            
            if action == "create":
                if archive.endswith(".zip"):
                    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                        for p in paths:
                            if os.path.isdir(p):
                                for root, dirs, files in os.walk(p):
                                    for f in files:
                                        fp = os.path.join(root, f)
                                        zf.write(fp, os.path.relpath(fp, os.path.dirname(p)))
                            else:
                                zf.write(p, os.path.basename(p))
                    return {"success": True, "result": f"Created {archive} with {len(paths)} items"}
                
                elif archive.endswith(".tar.gz") or archive.endswith(".tgz"):
                    with tarfile.open(archive, "w:gz") as tf:
                        for p in paths:
                            tf.add(p, os.path.basename(p))
                    return {"success": True, "result": f"Created {archive}"}
                
                else:
                    return {"success": False, "result": "Supported: .zip, .tar.gz, .tgz"}
            
            elif action == "extract":
                dest = params.get("dest", ".")
                if archive.endswith(".zip"):
                    with zipfile.ZipFile(archive, "r") as zf:
                        zf.extractall(dest)
                elif archive.endswith(".tar.gz") or archive.endswith(".tgz"):
                    with tarfile.open(archive, "r:gz") as tf:
                        tf.extractall(dest)
                else:
                    return {"success": False, "result": "Supported: .zip, .tar.gz, .tgz"}
                return {"success": True, "result": f"Extracted {archive} to {dest}"}
            
            elif action == "list":
                files = []
                if archive.endswith(".zip"):
                    with zipfile.ZipFile(archive, "r") as zf:
                        files = zf.namelist()
                elif archive.endswith(".tar.gz") or archive.endswith(".tgz"):
                    with tarfile.open(archive, "r:gz") as tf:
                        files = tf.getnames()
                else:
                    return {"success": False, "result": "Supported: .zip, .tar.gz, .tgz"}
                return {"success": True, "result": f"Contents ({len(files)}):\n" + "\n".join(files[:50])}
            
            return {"success": False, "result": "Actions: create, extract, list"}
        except Exception as e:
            return {"success": False, "result": f"Archive error: {e}"}


class JsonTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "parse")
        data = params.get("data", "")
        path = params.get("path", "")
        try:
            if action == "parse":
                if not data:
                    return {"success": False, "result": "No JSON data"}
                parsed = json.loads(data)
                return {"success": True, "result": json.dumps(parsed, indent=2)[:3000]}
            
            elif action == "query":
                if not data or not path:
                    return {"success": False, "result": "Need data and path (e.g. $.store.book[0].author)"}
                parsed = json.loads(data)
                import jsonpath_ng
                expr = jsonpath_ng.parse(path)
                matches = [m.value for m in expr.find(parsed)]
                return {"success": True, "result": json.dumps(matches, indent=2)[:3000]}
            
            elif action == "validate":
                if not data:
                    return {"success": False, "result": "No JSON data"}
                json.loads(data)
                return {"success": True, "result": "Valid JSON"}
            
            elif action == "format":
                if not data:
                    return {"success": False, "result": "No JSON data"}
                parsed = json.loads(data)
                return {"success": True, "result": json.dumps(parsed, indent=2)}
            
            return {"success": False, "result": "Actions: parse, query, validate, format"}
        except ImportError:
            return {"success": False, "result": "jsonpath-ng not installed: pip install jsonpath-ng"}
        except json.JSONDecodeError as e:
            return {"success": False, "result": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"success": False, "result": f"JSON error: {e}"}


class HashTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "string")
        data = params.get("data", "")
        algorithm = params.get("algorithm", "sha256")
        try:
            if action == "string":
                if not data:
                    return {"success": False, "result": "No data"}
                h = hashlib.new(algorithm)
                h.update(data.encode())
                return {"success": True, "result": f"{algorithm.upper()}: {h.hexdigest()}"}
            
            elif action == "file":
                if not os.path.exists(data):
                    return {"success": False, "result": "File not found"}
                h = hashlib.new(algorithm)
                with open(data, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                return {"success": True, "result": f"{algorithm.upper()}({os.path.basename(data)}): {h.hexdigest()}"}
            
            elif action == "compare":
                expected = params.get("expected", "")
                h = hashlib.new(algorithm)
                h.update(data.encode())
                match = hmac.compare_digest(h.hexdigest(), expected.lower())
                return {"success": True, "result": f"Match: {match}"}
            
            return {"success": False, "result": "Actions: string, file, compare"}
        except Exception as e:
            return {"success": False, "result": f"Hash error: {e}"}


class OCRTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "image")
        path = params.get("path", params.get("image", ""))
        if not path or not os.path.exists(path):
            return {"success": False, "result": "Image file not found"}
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(path)
            text = pytesseract.image_to_string(img)
            if not text.strip():
                return {"success": True, "result": "No text detected"}
            return {"success": True, "result": text[:3000]}
        except ImportError:
            return {"success": False, "result": "OCR unavailable. Install: pip install pytesseract"}
        except Exception as e:
            msg = str(e).lower()
            if "tesseract" in msg and "path" in msg:
                return {"success": False, "result": "Tesseract not installed. OCR unavailable."}
            return {"success": False, "result": f"OCR error: {e}"}


class ScreenWatchTool(BaseTool):
    """Real-time screen monitoring - captures at 2fps, detects changes, latest frame always available"""

    def __init__(self):
        self._last_frame = None
        self._last_frame_ts = 0
        self._last_description = ""
        self._last_analysis_ts = 0
        self._running = True
        self._lock = threading.Lock()
        self._change_pct = 0.0
        self._frame_buffer = []
        self._monitor_idx = 1
        self._vision_model = "nvidia/nemotron-nano-12b-v2-vl:free"
        self._vision_fallbacks = [
            "nvidia/nemotron-nano-12b-v2-vl:free",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            "google/gemma-4-26b-a4b-it:free",
        ]
        self._vision_idx = 0
        self._start_monitor()

    def _start_monitor(self):
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def _capture_loop(self):
        import mss
        import numpy as np
        from PIL import Image
        import time
        try:
            with mss.mss() as sct:
                while self._running:
                    try:
                        mon = sct.monitors[self._monitor_idx] if self._monitor_idx < len(sct.monitors) else sct.monitors[1]
                        raw = np.array(sct.grab(mon))
                        img = Image.fromarray(raw[:, :, :3])
                        now = time.time()
                        with self._lock:
                            if self._last_frame is not None:
                                old = np.array(self._last_frame.resize((64, 48)), dtype=np.float32)
                                new = np.array(img.resize((64, 48)), dtype=np.float32)
                                diff = np.mean(np.abs(old - new)) / 255.0
                                self._change_pct = diff * 100
                            else:
                                self._change_pct = 100
                            self._last_frame = img
                            self._last_frame_ts = now
                            self._frame_buffer.append((now, img))
                            if len(self._frame_buffer) > 10:
                                self._frame_buffer.pop(0)
                    except Exception:
                        pass
                    time.sleep(0.5)
        except ImportError:
            pass

    def execute(self, params):
        action = params.get("action", "read")
        try:
            if action == "read":
                with self._lock:
                    description = self._last_description
                    change = self._change_pct
                    age = time.time() - self._last_analysis_ts if self._last_analysis_ts else 0
                    frame = self._last_frame
                if description:
                    return {"success": True, "result": f"[Screen {change:.0f}% change, {age:.0f}s ago]\n{description}"}
                if frame is None:
                    return {"success": False, "result": "Screen monitoring starting up, no frame captured yet. Try again in 1 second."}
                w, h = frame.size
                return {"success": True, "result": f"Screen: {w}x{h}, {change:.0f}% change since last check. Running vision analysis..."}

            elif action == "capture":
                prompt = params.get("prompt", "Describe this screen briefly.")
                return self._do_analyze(prompt)

            elif action == "start":
                self._running = True
                return {"success": True, "result": "Screen monitoring running at 2fps"}

            elif action == "stop":
                self._running = False
                return {"success": True, "result": "Screen monitoring stopped"}

            elif action == "status":
                with self._lock:
                    return {"success": True, "result":
                        f"Monitoring: {'active' if self._running else 'stopped'}\n"
                        f"Change: {self._change_pct:.0f}%\n"
                        f"Last analysis: {time.time() - self._last_analysis_ts:.0f}s ago\n"
                        f"Frame buffer: {len(self._frame_buffer)} frames"}

            return {"success": False, "result": "Actions: read, capture, start, stop, status"}
        except ImportError as e:
            return {"success": False, "result": f"Missing: {e}"}
        except Exception as e:
            return {"success": False, "result": f"Screen watch error: {e}"}

    def _do_analyze(self, prompt):
        with self._lock:
            if self._last_frame is None:
                return {"success": False, "result": "No frame captured yet"}
            img = self._last_frame.copy()
        # Return local description instantly (no API call)
        w, h = img.size
        import numpy as np
        arr = np.array(img.resize((16, 12)))
        avg = arr.mean(axis=(0, 1))
        brightness = "bright" if avg.mean() > 128 else "dim"
        dom = f"rgb({int(avg[0])},{int(avg[1])},{int(avg[2])})"
        change = self._change_pct if hasattr(self, '_change_pct') else 0
        result = f"Screen: {w}x{h}, {brightness}, dominant {dom}, {change:.0f}% change."
        # Fire-and-forget vision API to update cache for next read
        threading.Thread(target=self._analyze_via_api, args=(img, prompt), daemon=True).start()
        return {"success": True, "result": result}

    def _analyze_via_api(self, img, prompt):
        import tempfile, base64, requests, os, time
        path = os.path.join(tempfile.gettempdir(), f"sw_{int(time.time())}.png")
        img.save(path)
        try:
            api_key = os.environ.get("OPENROUTER_API_KEY", DEFAULT_API_KEY)
            base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            models_to_try = self._vision_fallbacks
            for model in models_to_try:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]}],
                    "max_tokens": 256,
                    "stream": False,
                }
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=5)
                    if resp.status_code == 429:
                        continue
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                            if content:
                                with self._lock:
                                    self._last_description = content
                                    self._last_analysis_ts = time.time()
                                return
                except Exception:
                    continue
        finally:
            try: os.remove(path)
            except: pass


class InputControlTool(BaseTool):
    """Ultra-fast real-time mouse/keyboard using SendInput (reliable on modern Windows)"""
    
    MOUSE_BUTTONS = {"left": 0, "right": 1, "middle": 2}
    _INPUT_MOUSE = 0
    
    @staticmethod
    def _send_click(flags_down, flags_up, dx=0, dy=0):
        import ctypes
        from ctypes import wintypes
        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
        class INPUT_U(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]
        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("u", INPUT_U)]
        down = INPUT(0, INPUT_U(MOUSEINPUT(dx, dy, 0, flags_down, 0, None)))
        up = INPUT(0, INPUT_U(MOUSEINPUT(dx, dy, 0, flags_up, 0, None)))
        arr = (INPUT * 2)(down, up)
        ctypes.windll.user32.SendInput(2, arr, ctypes.sizeof(INPUT))

    VK_MAP = {
        "enter": 0x0D, "tab": 0x09, "shift": 0x10, "ctrl": 0x11, "alt": 0x12,
        "space": 0x20, "backspace": 0x08, "delete": 0x2E, "escape": 0x1B,
        "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
        "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
        "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
        "f6": 0x75, "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79,
        "f11": 0x7A, "f12": 0x7B, "capslock": 0x14, "printscreen": 0x2C,
        "scrolllock": 0x91, "pause": 0x13, "insert": 0x2D,
        "win": 0x5B, "menu": 0x5D, "numlock": 0x90,
        "volumemute": 0xAD, "volumedown": 0xAE, "volumeup": 0xAF,
        "nexttrack": 0xB0, "prevtrack": 0xB1, "mediastop": 0xB2, "playpause": 0xB3,
        "browserback": 0xA6, "browserforward": 0xA7, "browserrefresh": 0xA8,
        "sleep": 0x5F, "zoom": 0xFB,
        "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
        "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
        "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
        "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
        "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
        "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
        "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59, "z": 0x5A,
        "semicolon": 0xBA, "equals": 0xBB, "comma": 0xBC, "minus": 0xBD,
        "period": 0xBE, "slash": 0xBF, "backtick": 0xC0,
        "lbracket": 0xDB, "backslash": 0xDC, "rbracket": 0xDD, "quote": 0xDE,
    }

    def execute(self, params):
        action = params.get("action", "")
        try:
            import win32api
            import win32con
            import win32gui
            
            if action == "move":
                x = int(params.get("x", 0))
                y = int(params.get("y", 0))
                win32api.SetCursorPos((x, y))
                return {"success": True, "result": f"Moved to ({x}, {y})"}
            
            elif action == "move_rel":
                dx = int(params.get("dx", 0))
                dy = int(params.get("dy", 0))
                cx, cy = win32api.GetCursorPos()
                win32api.SetCursorPos((cx + dx, cy + dy))
                return {"success": True, "result": f"Moved relative ({dx}, {dy})"}
            
            elif action == "click":
                button = params.get("button", "left").lower()
                b = self.MOUSE_BUTTONS.get(button, 0)
                x = params.get("x")
                y = params.get("y")
                if x is not None and y is not None:
                    win32api.SetCursorPos((int(x), int(y)))
                    import time; time.sleep(0.05)
                flags = [win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_RIGHTDOWN,
                         win32con.MOUSEEVENTF_MIDDLEDOWN][b]
                flags_up = [win32con.MOUSEEVENTF_LEFTUP, win32con.MOUSEEVENTF_RIGHTUP,
                           win32con.MOUSEEVENTF_MIDDLEUP][b]
                self._send_click(flags, flags_up)
                import time; time.sleep(0.03)
                clicks = params.get("clicks", 1)
                for _ in range(clicks - 1):
                    self._send_click(flags, flags_up)
                return {"success": True, "result": f"Clicked {button} {clicks}x"}
            
            elif action == "drag":
                x = int(params.get("x", 0))
                y = int(params.get("y", 0))
                dx = int(params.get("dx", 0))
                dy = int(params.get("dy", 0))
                button = params.get("button", "left").lower()
                b = self.MOUSE_BUTTONS.get(button, 0)
                flags = [win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_RIGHTDOWN,
                         win32con.MOUSEEVENTF_MIDDLEDOWN][b]
                flags_up = [win32con.MOUSEEVENTF_LEFTUP, win32con.MOUSEEVENTF_RIGHTUP,
                           win32con.MOUSEEVENTF_MIDDLEUP][b]
                win32api.SetCursorPos((x, y))
                self._send_click(flags, flags, dx=0, dy=0)
                import time; time.sleep(0.05)
                win32api.SetCursorPos((x + dx, y + dy))
                self._send_click(flags_up, flags_up, dx=0, dy=0)
                import time; time.sleep(0.03)
                return {"success": True, "result": f"Dragged ({dx}, {dy})"}
            
            elif action == "scroll":
                import ctypes
                clicks = int(params.get("clicks", 1))
                ctypes.windll.user32.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, clicks * 120, 0)
                return {"success": True, "result": f"Scrolled {clicks}"}
            
            elif action == "type":
                text = params.get("text", "")
                if not text:
                    return {"success": False, "result": "Need text"}
                for ch in text:
                    vk = win32api.VkKeyScan(ch)
                    vkey = vk & 0xFF
                    shift = (vk >> 8) & 1
                    if shift:
                        win32api.keybd_event(0x10, 0, 0, 0)
                    win32api.keybd_event(vkey, 0, 0, 0)
                    win32api.keybd_event(vkey, 0, win32con.KEYEVENTF_KEYUP, 0)
                    if shift:
                        win32api.keybd_event(0x10, 0, win32con.KEYEVENTF_KEYUP, 0)
                return {"success": True, "result": f"Typed {len(text)} chars"}
            
            elif action == "press":
                key = params.get("key", "").lower()
                vk = self.VK_MAP.get(key)
                if vk is None:
                    vk = ord(key.upper()) if len(key) == 1 else 0
                if not vk:
                    return {"success": False, "result": f"Unknown key: {key}"}
                win32api.keybd_event(vk, 0, 0, 0)
                win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
                return {"success": True, "result": f"Pressed {key}"}
            
            elif action == "hotkey":
                keys = params.get("keys", [])
                mod_map = {"ctrl": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B}
                mods_down = []
                for k in keys:
                    k = k.lower()
                    if k in mod_map:
                        vk = mod_map[k]
                        win32api.keybd_event(vk, 0, 0, 0)
                        mods_down.append(vk)
                for k in keys:
                    k = k.lower()
                    if k not in mod_map:
                        vk = self.VK_MAP.get(k, ord(k.upper()) if len(k) == 1 else 0)
                        if vk:
                            win32api.keybd_event(vk, 0, 0, 0)
                            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
                for vk in reversed(mods_down):
                    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
                return {"success": True, "result": f"Hotkey: {'+'.join(keys)}"}
            
            elif action == "keydown":
                key = params.get("key", "").lower()
                vk = self.VK_MAP.get(key, ord(key.upper()) if len(key) == 1 else 0)
                if not vk:
                    return {"success": False, "result": f"Unknown key: {key}"}
                win32api.keybd_event(vk, 0, 0, 0)
                return {"success": True, "result": f"Key down: {key}"}
            
            elif action == "keyup":
                key = params.get("key", "").lower()
                vk = self.VK_MAP.get(key, ord(key.upper()) if len(key) == 1 else 0)
                if not vk:
                    return {"success": False, "result": f"Unknown key: {key}"}
                win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
                return {"success": True, "result": f"Key up: {key}"}
            
            elif action == "position":
                x, y = win32api.GetCursorPos()
                return {"success": True, "result": f"Mouse at ({x}, {y})"}
            
            elif action == "screenshot":
                import pyautogui
                path = params.get("path", os.path.join(tempfile.gettempdir(), f"screenshot_{int(time.time())}.png"))
                pyautogui.screenshot(path)
                return {"success": True, "result": f"Screenshot saved: {path}"}
            
            return {"success": False, "result": "Actions: move, move_rel, click, drag, scroll, type, press, hotkey, keydown, keyup, position, screenshot"}
        
        except ImportError:
            return {"success": False, "result": "win32api not installed (pywin32 required)"}
        except Exception as e:
            return {"success": False, "result": f"Input error: {e}"}


def _format_size(bytes_val):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


def _format_time(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


class EditTool(BaseTool):
    """Edit files by exact string replacement (like opencode edit)"""
    def execute(self, params):
        path = params.get("filePath", params.get("path", ""))
        old = params.get("old", params.get("oldString", ""))
        new = params.get("new", params.get("newString", ""))
        replace_all = params.get("replaceAll", False)
        if not path or not old:
            return {"success": False, "result": "Need filePath and old string"}
        if new is None:
            return {"success": False, "result": "Need new string"}
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if replace_all:
                if old not in content:
                    return {"success": False, "result": "String not found in file"}
                new_content = content.replace(old, new)
            else:
                if content.count(old) > 1:
                    return {"success": False, "result": f"Found {content.count(old)} matches. Use replaceAll=True or provide more context"}
                if old not in content:
                    return {"success": False, "result": "String not found in file"}
                new_content = content.replace(old, new, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"success": True, "result": f"Edited {os.path.basename(path)}"}
        except Exception as e:
            return {"success": False, "result": f"Edit error: {e}"}


class GrepTool(BaseTool):
    """Search file contents using regex (like opencode grep)"""
    def execute(self, params):
        pattern = params.get("pattern", "")
        path = params.get("path", params.get("include", ""))
        if not pattern:
            return {"success": False, "result": "No pattern provided"}
        try:
            matches = []
            if path and os.path.isfile(path):
                files = [path]
            elif path and os.path.isdir(path):
                import fnmatch
                inc = params.get("include", "*")
                files = []
                for root, dirs, fnames in os.walk(path):
                    for f in fnmatch.filter(fnames, inc):
                        files.append(os.path.join(root, f))
                    if params.get("max_depth"):
                        depth = root.replace(path, "").count(os.sep)
                        if depth >= int(params["max_depth"]):
                            dirs.clear()
            else:
                files = []
                for root, dirs, fnames in os.walk("."):
                    inc = params.get("include", "*.{py,js,ts,jsx,tsx,html,css,json,md,txt}")
                    import fnmatch
                    for f in fnmatch.filter(fnames, inc):
                        files.append(os.path.join(root, f))
                    if len(files) >= 100:
                        break
            for fp in files:
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if re.search(pattern, line):
                                short = fp[:100] if len(fp) > 100 else fp
                                matches.append(f"{short}:{i}: {line.rstrip()[:150]}")
                except Exception:
                    pass
                if len(matches) >= params.get("max_results", 50):
                    break
            if not matches:
                return {"success": True, "result": "No matches found"}
            return {"success": True, "result": f"Found {len(matches)} matches:\n" + "\n".join(matches[:params.get("max_results", 50)])}
        except Exception as e:
            return {"success": False, "result": f"Grep error: {e}"}


class GlobTool(BaseTool):
    """Find files by glob pattern (like opencode glob)"""
    def execute(self, params):
        pattern = params.get("pattern", "")
        path = params.get("path", ".")
        if not pattern:
            return {"success": False, "result": "No pattern provided"}
        try:
            import fnmatch
            matches = []
            if os.path.isfile(path):
                root = os.path.dirname(path) or "."
            else:
                root = path
            for r, dirs, fnames in os.walk(root):
                matches.extend(os.path.join(r, f) for f in fnmatch.filter(fnames, pattern))
                matches.extend(r + "/" for d in dirs if fnmatch.fnmatch(d, pattern))
                if len(matches) >= params.get("max_results", 100):
                    break
            matches.sort(key=lambda x: os.path.getmtime(x) if os.path.isfile(x) else 0, reverse=True)
            if not matches:
                return {"success": True, "result": "No files found"}
            lines = [f if os.path.isfile(f) else f"{f}/ (dir)" for f in matches[:params.get("max_results", 100)]]
            return {"success": True, "result": f"Found {len(matches)} files:\n" + "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"Glob error: {e}"}


class ApplyPatchTool(BaseTool):
    """Apply patch/diff to files"""
    def execute(self, params):
        patch_text = params.get("patchText", params.get("patch", params.get("text", "")))
        reverse = params.get("reverse", False)
        if not patch_text:
            return {"success": False, "result": "No patch text provided"}
        try:
            import subprocess
            with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
                f.write(patch_text)
                patch_path = f.name
            cmd = ["git", "apply"]
            if reverse:
                cmd.append("-R")
            cmd.append(patch_path)
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            os.unlink(patch_path)
            if r.returncode == 0:
                return {"success": True, "result": "Patch applied successfully"}
            # Fallback: try patch command
            r2 = subprocess.run(["patch", "-p1"], input=patch_text, capture_output=True, text=True, timeout=30)
            if r2.returncode == 0:
                return {"success": True, "result": "Patch applied via patch command"}
            return {"success": False, "result": f"Patch failed: {r.stderr or r2.stderr}"[:500]}
        except Exception as e:
            return {"success": False, "result": f"Patch error: {e}"}


class WebFetchTool(BaseTool):
    """Fetch web content from a URL"""
    def execute(self, params):
        url = params.get("url", "")
        fmt = params.get("format", "text")
        if not url:
            return {"success": False, "result": "No URL provided"}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JarvisAssistant/3.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            if fmt == "json" or url.endswith(".json"):
                return {"success": True, "result": json.loads(data.decode("utf-8"))}
            text = data.decode("utf-8", errors="replace")
            import html
            text = re.sub(r'<[^>]+>', ' ', html.unescape(text))
            text = re.sub(r'\s+', ' ', text).strip()
            return {"success": True, "result": text[:5000]}
        except Exception as e:
            return {"success": False, "result": f"Fetch error: {e}"}


class QuestionTool(BaseTool):
    """Ask user a question and return answer. Set pending question; answer checked on next input."""
    def __init__(self):
        self.pending_question = None
        self.pending_answer = None

    def execute(self, params):
        q = params.get("question", params.get("text", ""))
        options = params.get("options", [])
        if not q:
            return {"success": False, "result": "No question provided"}
        desc = q[:200]
        if options:
            desc += " Options: " + ", ".join(o.get("label", str(o)) if isinstance(o, dict) else str(o) for o in options)
        # Return the question - orchestrator will read it aloud
        return {"success": True, "result": f"QUESTION: {desc}", "_is_question": True}


class SkillTool(BaseTool):
    """Load a skill/instruction file (SKILL.md or custom)"""
    def execute(self, params):
        name = params.get("name", "")
        path = params.get("path", "")
        if path:
            skill_path = path
        elif name:
            skill_path = os.path.join(os.path.dirname(__file__), "..", f"{name}.md")
            if not os.path.exists(skill_path):
                skill_path = os.path.join(os.path.dirname(__file__), "..", "skills", f"{name}.md")
        else:
            return {"success": False, "result": "Need name or path"}
        if not os.path.exists(skill_path):
            return {"success": False, "result": f"Skill not found: {skill_path}"}
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "result": f"Skill '{os.path.basename(skill_path)}':\n{content[:3000]}"}
        except Exception as e:
            return {"success": False, "result": f"Skill error: {e}"}


class TodoWriteTool(BaseTool):
    """Enhanced todo list management with task tracking (like opencode todowrite)"""
    def __init__(self):
        self.todo_file = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "JarvisAssistant", "todos.json")
        os.makedirs(os.path.dirname(self.todo_file), exist_ok=True)
        if not os.path.exists(self.todo_file):
            with open(self.todo_file, "w") as f:
                json.dump([], f)

    def _load(self):
        with open(self.todo_file, "r") as f:
            return json.load(f)

    def _save(self, todos):
        with open(self.todo_file, "w") as f:
            json.dump(todos, f, indent=2)

    def execute(self, params):
        action = params.get("action", params.get("status", "list"))
        todos = self._load()
        try:
            if action in ("add", "new"):
                content = params.get("content", params.get("task", ""))
                priority = params.get("priority", "medium")
                status = params.get("status", "pending")
                if not content:
                    return {"success": False, "result": "No task content"}
                todos.append({
                    "id": str(time.time()),
                    "content": content,
                    "priority": priority,
                    "status": status,
                    "created": datetime.datetime.now().isoformat()
                })
                self._save(todos)
                return {"success": True, "result": f"Todo added: {content}"}

            if action in ("list", "pending"):
                filter_status = params.get("status", "pending" if action == "pending" else None)
                items = [t for t in todos if not filter_status or t.get("status") == filter_status]
                if not items:
                    return {"success": True, "result": "No todos" if filter_status else f"No {filter_status} todos"}
                lines = [f"[{t.get('priority','m')[0].upper()}] {t['content']} (id:{t['id'][-6:]})" for t in items]
                return {"success": True, "result": "\n".join(lines)}

            if action in ("done", "complete", "finish"):
                task_id = params.get("id", "")
                for t in todos:
                    if t["id"] == task_id or t["id"].endswith(task_id):
                        t["status"] = "completed"
                        self._save(todos)
                        return {"success": True, "result": f"Completed: {t['content']}"}
                return {"success": False, "result": "Task not found"}

            if action == "in_progress":
                task_id = params.get("id", "")
                for t in todos:
                    if t["id"] == task_id or t["id"].endswith(task_id):
                        t["status"] = "in_progress"
                        self._save(todos)
                        return {"success": True, "result": f"In progress: {t['content']}"}
                return {"success": False, "result": "Task not found"}

            if action in ("remove", "delete"):
                task_id = params.get("id", "")
                todos = [t for t in todos if t["id"] != task_id and not t["id"].endswith(task_id)]
                self._save(todos)
                return {"success": True, "result": "Removed"}

            if action in ("clear", "clean"):
                self._save([])
                return {"success": True, "result": "All todos cleared"}

            return {"success": False, "result": "Actions: add, list, done, in_progress, remove, clear"}
        except Exception as e:
            return {"success": False, "result": f"Todo error: {e}"}


# ===== New Tools =====

class VolumeControlTool(BaseTool):
    """Get or set system volume level"""
    def execute(self, params):
        action = params.get("action", "get")
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            devices = AudioUtilities.GetSpeakers()
            volume = getattr(devices, "EndpointVolume", None)
            if volume is None:
                # older pycaw API
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
            if action == "get":
                level = volume.GetMasterVolumeLevelScalar() * 100
                mute = volume.GetMute()
                return {"success": True, "result": f"Volume: {level:.0f}%{' (muted)' if mute else ''}"}
            elif action == "set":
                pct = max(0, min(100, int(params.get("level", 50)))) / 100
                volume.SetMasterVolumeLevelScalar(pct, None)
                return {"success": True, "result": f"Volume set to {pct*100:.0f}%"}
            elif action == "mute":
                volume.SetMute(True, None)
                return {"success": True, "result": "Muted"}
            elif action == "unmute":
                volume.SetMute(False, None)
                return {"success": True, "result": "Unmuted"}
            return {"success": False, "result": "Actions: get, set, mute, unmute"}
        except Exception:
            if action == "get":
                return {"success": True, "result": "Volume: unknown (pycaw not available)"}
            if action == "mute":
                self._send_media_key(0xAD)
                return {"success": True, "result": "Toggled mute"}
            if action == "set":
                level = max(0, min(100, int(params.get("level", 50))))
                for _ in range(abs(level - 50) // 2):
                    self._send_media_key(0xAF if level > 50 else 0xAE)
                return {"success": True, "result": f"Adjusted volume toward {level}%"}
            return {"success": False, "result": "Volume control unavailable"}

    def _send_media_key(self, vk):
        import ctypes
        user32 = ctypes.windll.user32
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk, 0, 2, 0)


class MediaControlTool(BaseTool):
    """Control media playback (play/pause/next/prev)"""
    def execute(self, params):
        action = params.get("action", "play_pause")
        import ctypes
        user32 = ctypes.windll.user32
        keys = {
            "play_pause": 0xB3,
            "next": 0xB0,
            "prev": 0xB1,
            "stop": 0xB2,
        }
        vk = keys.get(action)
        if not vk:
            return {"success": False, "result": "Actions: play_pause, next, prev, stop"}
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk, 0, 2, 0)
        return {"success": True, "result": f"Media: {action}"}


class NotificationTool(BaseTool):
    """Send Windows toast notification"""
    def execute(self, params):
        title = params.get("title", "JARVIS")
        message = params.get("message", params.get("text", ""))[:256]
        duration = params.get("duration", 3)
        try:
            from winotify import Notification, audio
            toast = Notification(app_id="JARVIS", title=title, msg=message)
            toast.set_audio(audio.Default, loop=False)
            toast.show()
            return {"success": True, "result": f"Notification sent: {message[:60]}..." if len(message) > 60 else f"Notification sent: {message}"}
        except Exception:
            pass
        try:
            from win10toast import ToastNotifier
            n = ToastNotifier()
            n.show_toast(title, message, duration=duration, threaded=True)
            return {"success": True, "result": f"Notification sent: {message[:60]}..." if len(message) > 60 else f"Notification sent: {message}"}
        except Exception:
            pass
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x1000)
            return {"success": True, "result": "Notification shown via MessageBox"}
        except Exception:
            return {"success": False, "result": "Notification failed"}


class DiskTool(BaseTool):
    """Check disk, CPU, and RAM usage"""
    def execute(self, params):
        target = params.get("target", "all")
        results = []
        import psutil
        if target in ("all", "cpu"):
            pct = psutil.cpu_percent(interval=0.5)
            results.append(f"CPU: {pct:.0f}%")
        if target in ("all", "ram"):
            mem = psutil.virtual_memory()
            results.append(f"RAM: {mem.percent:.0f}% used ({mem.used // 1024**3}GB/{mem.total // 1024**3}GB)")
        if target in ("all", "disk"):
            for part in psutil.disk_partitions():
                if part.fstype:
                    usage = psutil.disk_usage(part.mountpoint)
                    results.append(f"{part.device}: {usage.percent:.0f}% ({usage.free // 1024**3}GB free)")
        if not results:
            return {"success": False, "result": "Specify: cpu, ram, disk, or all"}
        return {"success": True, "result": " | ".join(results)}


class WallpaperTool(BaseTool):
    """Set desktop wallpaper"""
    def execute(self, params):
        path = params.get("path", params.get("url", ""))
        style = params.get("style", "fill")
        if not path:
            return {"success": False, "result": "Path required"}
        if path.startswith("http://") or path.startswith("https://"):
            import urllib.request
            ext = path.rsplit(".", 1)[-1] if "." in path else "jpg"
            f = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
            fpath = f.name
            f.close()
            try:
                urllib.request.urlretrieve(path, fpath)
                path = fpath
            except Exception as e:
                return {"success": False, "result": f"Download failed: {e}"}
        else:
            fpath = path
        if not os.path.isfile(fpath):
            return {"success": False, "result": "File not found"}
        try:
            import ctypes
            SPI_SETDESKWALLPAPER = 20
            styles = {"fill": 10, "fit": 6, "stretch": 2, "tile": 0, "center": 0}
            key = ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, fpath, 2)
            if key:
                return {"success": True, "result": f"Wallpaper set: {os.path.basename(fpath)}"}
            return {"success": False, "result": "Failed to set wallpaper"}
        except Exception as e:
            return {"success": False, "result": f"Error: {e}"}


class LockScreenTool(BaseTool):
    """Lock the workstation"""
    def execute(self, params):
        action = params.get("action", "lock")
        import ctypes
        if action == "lock":
            ctypes.windll.user32.LockWorkStation()
            return {"success": True, "result": "Workstation locked"}
        elif action == "logoff":
            ctypes.windll.user32.ExitWindowsEx(0, 0)
            return {"success": True, "result": "Logging off"}
        elif action == "sleep":
            ctypes.windll.user32.SetSuspendState(False, True, False)
            return {"success": True, "result": "Sleep mode"}
        return {"success": False, "result": "Actions: lock, logoff, sleep"}


class BrowserTool(BaseTool):
    """Open URL in default browser"""
    def execute(self, params):
        url = params.get("url", params.get("query", ""))
        new_tab = params.get("new_tab", True)
        if not url:
            return {"success": False, "result": "URL required"}
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        import webbrowser
        webbrowser.open(url, new=2 if new_tab else 0, autoraise=True)
        return {"success": True, "result": f"Opened: {url}"}


class EnvTool(BaseTool):
    """Get environment variables and system paths"""
    def execute(self, params):
        action = params.get("action", "get")
        name = params.get("name", params.get("var", ""))
        if action == "get":
            if name:
                val = os.environ.get(name, "")
                return {"success": True, "result": f"{name}={val}" if val else f"{name} not set"}
            return {"success": True, "result": "\n".join(f"{k}={v[:80]}" for k, v in sorted(os.environ.items())[:20])}
        elif action == "paths":
            paths = os.environ.get("PATH", "").split(os.pathsep)
            return {"success": True, "result": "\n".join(paths[:15])}
        elif action == "home":
            return {"success": True, "result": f"Home: {os.path.expanduser('~')}"}
        elif action == "temp":
            return {"success": True, "result": f"Temp: {tempfile.gettempdir()}"}
        return {"success": False, "result": "Actions: get [name], paths, home, temp"}


class ColorTool(BaseTool):
    """Convert between color formats (hex, rgb, hsl)"""
    def execute(self, params):
        fmt = params.get("format", params.get("to", "hex"))
        value = params.get("value", params.get("color", ""))
        if not value:
            return {"success": False, "result": "Color value required"}
        value = value.strip().lower()
        try:
            if value.startswith("#"):
                h = value.lstrip("#")
                r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            elif value.startswith("rgb"):
                nums = re.findall(r'\d+', value)
                r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
            elif value.startswith("hsl"):
                import colorsys
                nums = re.findall(r'[\d.]+', value)
                h, s, l = float(nums[0])/360, float(nums[1])/100, float(nums[2])/100
                r, g, b = [int(x*255) for x in colorsys.hls_to_rgb(h, l, s)]
            else:
                return {"success": False, "result": "Format: #hex, rgb(R,G,B), or hsl(H,S,L)"}
            if fmt == "hex":
                return {"success": True, "result": f"#{r:02x}{g:02x}{b:02x}"}
            if fmt == "rgb":
                return {"success": True, "result": f"rgb({r},{g},{b})"}
            if fmt == "hsl":
                import colorsys
                h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                return {"success": True, "result": f"hsl({h*360:.0f},{s*100:.0f}%,{v*100:.0f}%)"}
            return {"success": True, "result": f"RGB({r},{g},{b}) HEX:#{r:02x}{g:02x}{b:02x}"}
        except Exception as e:
            return {"success": False, "result": f"Color error: {e}"}


class UnitTool(BaseTool):
    """Convert between units (temperature, length, weight, etc.)"""
    def execute(self, params):
        value = params.get("value", "0")
        fr = params.get("from", "").lower()
        to = params.get("to", "").lower()
        try:
            val = float(value)
        except (ValueError, TypeError):
            return {"success": False, "result": "Invalid numeric value"}
        if not fr or not to:
            return {"success": False, "result": "Specify 'from' and 'to' units"}
        conversions = {
            # Temperature
            ("c", "f"): lambda v: v * 9/5 + 32,
            ("f", "c"): lambda v: (v - 32) * 5/9,
            ("c", "k"): lambda v: v + 273.15,
            ("k", "c"): lambda v: v - 273.15,
            # Length
            ("m", "ft"): lambda v: v * 3.28084,
            ("ft", "m"): lambda v: v / 3.28084,
            ("km", "mi"): lambda v: v * 0.621371,
            ("mi", "km"): lambda v: v / 0.621371,
            ("cm", "in"): lambda v: v / 2.54,
            ("in", "cm"): lambda v: v * 2.54,
            # Weight
            ("kg", "lb"): lambda v: v * 2.20462,
            ("lb", "kg"): lambda v: v / 2.20462,
            ("g", "oz"): lambda v: v / 28.3495,
            ("oz", "g"): lambda v: v * 28.3495,
            # Data
            ("mb", "gb"): lambda v: v / 1024,
            ("gb", "mb"): lambda v: v * 1024,
        }
        fn = conversions.get((fr, to))
        if not fn:
            available = ", ".join(sorted(set(f"{a}→{b}" for a, b in conversions)))
            return {"success": False, "result": f"Unknown pair. Try: {available}"}
        result = fn(val)
        return {"success": True, "result": f"{val} {fr} = {result:.4f} {to}"}


class MathEvalTool(BaseTool):
    """Safe math expression evaluator with common functions"""
    def execute(self, params):
        expr = params.get("expression", params.get("expr", ""))
        if not expr:
            return {"success": False, "result": "Expression required"}
        try:
            import math as m
            allowed = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "sqrt": m.sqrt,
                "sin": m.sin, "cos": m.cos, "tan": m.tan,
                "asin": m.asin, "acos": m.acos, "atan": m.atan,
                "log": m.log, "log10": m.log10, "exp": m.exp,
                "pi": m.pi, "e": m.e,
            }
            result = eval(expr, {"__builtins__": {}}, allowed)
            return {"success": True, "result": f"{result}"}
        except Exception as e:
            return {"success": False, "result": f"Math error: {e}"}


class IdleTool(BaseTool):
    """Get system idle time and uptime"""
    def execute(self, params):
        import ctypes
        target = params.get("target", "all")
        results = []
        if target in ("all", "idle"):
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                secs = millis // 1000
                results.append(f"Idle: {secs // 60}m {secs % 60}s")
            else:
                results.append("Idle: unknown")
        if target in ("all", "uptime"):
            millis = ctypes.windll.kernel32.GetTickCount()
            secs = millis // 1000
            results.append(f"Uptime: {secs // 3600}h {(secs % 3600) // 60}m")
        if target in ("all", "os"):
            results.append(f"OS: {os.environ.get('OS', 'Windows')}")
        if target in ("all", "user"):
            results.append(f"User: {os.environ.get('USERNAME', '')}")
        return {"success": True, "result": " | ".join(results)}


class PublicIPTool(BaseTool):
    def execute(self, params):
        try:
            import urllib.request
            with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=10) as r:
                data = json.loads(r.read())
            return {"success": True, "result": data.get("ip", "unknown")}
        except Exception as e:
            return {"success": False, "result": f"IP error: {e}"}


class PingTool(BaseTool):
    def execute(self, params):
        host = params.get("host", "8.8.8.8")
        count = params.get("count", 4)
        try:
            param = "-n" if sys.platform == "win32" else "-c"
            r = subprocess.run(["ping", param, str(count), host], capture_output=True, text=True, timeout=30)
            out = r.stdout or r.stderr
            lines = [l.strip() for l in out.split("\n") if l.strip()]
            return {"success": True, "result": "; ".join(lines[-6:-1]) if len(lines) > 1 else out[:500]}
        except Exception as e:
            return {"success": False, "result": f"Ping error: {e}"}


class DNSTool(BaseTool):
    def execute(self, params):
        host = params.get("host", "")
        if not host:
            return {"success": False, "result": "Host required"}
        try:
            import socket
            ip = socket.gethostbyname(host)
            try:
                hostname, _, _ = socket.gethostbyaddr(ip)
                return {"success": True, "result": f"{host} → {ip} ({hostname})"}
            except Exception:
                return {"success": True, "result": f"{host} → {ip}"}
        except Exception as e:
            return {"success": False, "result": f"DNS error: {e}"}


class HostInfoTool(BaseTool):
    def execute(self, params):
        target = params.get("target", "")
        if not target:
            return {"success": False, "result": "Target required"}
        results = []
        try:
            import socket
            ip = socket.gethostbyname(target)
            results.append(f"IP: {ip}")
        except Exception:
            pass
        try:
            import subprocess
            r = subprocess.run(["curl", "-s", f"https://ipapi.co/{target}/json/"], capture_output=True, text=True, timeout=15)
            if r.stdout:
                data = json.loads(r.stdout)
                org = data.get("org", "")
                city = data.get("city", "")
                country = data.get("country_name", "")
                if city: results.append(f"Location: {city}, {country}")
                if org: results.append(f"ISP: {org}")
        except Exception:
            pass
        return {"success": True, "result": " | ".join(results) if results else "No info"}


class TimestampTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "now")
        try:
            if action == "now":
                return {"success": True, "result": str(int(time.time()))}
            elif action == "from_iso":
                iso = params.get("iso", "")
                ts = int(datetime.datetime.fromisoformat(iso).timestamp())
                return {"success": True, "result": str(ts)}
            elif action == "to_iso":
                ts = float(params.get("timestamp", "0"))
                dt = datetime.datetime.fromtimestamp(ts)
                return {"success": True, "result": dt.isoformat()}
            return {"success": False, "result": "Actions: now, from_iso, to_iso"}
        except Exception as e:
            return {"success": False, "result": f"Timestamp error: {e}"}


class TimezoneTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "list")
        try:
            import zoneinfo
            if action == "list":
                zones = sorted(zoneinfo.available_timezones())
                return {"success": True, "result": "Available timezones: " + ", ".join(zones[:30]) + ("..." if len(zones) > 30 else "")}
            elif action == "convert":
                tz_name = params.get("timezone", "UTC")
                tz = zoneinfo.ZoneInfo(tz_name)
                now = datetime.datetime.now(tz)
                return {"success": True, "result": f"Time in {tz_name}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"}
            return {"success": False, "result": "Actions: list, convert"}
        except Exception as e:
            return {"success": False, "result": f"Timezone error: {e}"}


class DateCalcTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "diff")
        try:
            if action == "diff":
                d1 = datetime.datetime.fromisoformat(params.get("date1", ""))
                d2 = datetime.datetime.fromisoformat(params.get("date2", ""))
                diff = abs((d2 - d1).days)
                return {"success": True, "result": f"Difference: {diff} days"}
            elif action == "add":
                d = datetime.datetime.fromisoformat(params.get("date", datetime.datetime.now().isoformat()))
                days = int(params.get("days", 0))
                result = d + datetime.timedelta(days=days)
                return {"success": True, "result": result.strftime("%Y-%m-%d")}
            elif action == "weekday":
                d = datetime.datetime.fromisoformat(params.get("date", ""))
                return {"success": True, "result": d.strftime("%A")}
            return {"success": False, "result": "Actions: diff, add, weekday"}
        except Exception as e:
            return {"success": False, "result": f"Date error: {e}"}


class TextTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "upper")
        text = params.get("text", "")
        if not text:
            return {"success": False, "result": "Text required"}
        try:
            if action == "upper":
                return {"success": True, "result": text.upper()}
            elif action == "lower":
                return {"success": True, "result": text.lower()}
            elif action == "title":
                return {"success": True, "result": text.title()}
            elif action == "capitalize":
                return {"success": True, "result": text.capitalize()}
            elif action == "swapcase":
                return {"success": True, "result": text.swapcase()}
            elif action == "reverse":
                return {"success": True, "result": text[::-1]}
            elif action == "trim":
                return {"success": True, "result": text.strip()}
            elif action == "length":
                return {"success": True, "result": f"{len(text)} chars, {len(text.split())} words, {text.count(chr(10))+1} lines"}
            elif action == "wrap":
                width = int(params.get("width", 80))
                return {"success": True, "result": textwrap.fill(text, width)}
            elif action == "strip_lines":
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                return {"success": True, "result": "\n".join(lines)}
            return {"success": False, "result": "Actions: upper, lower, title, capitalize, swapcase, reverse, trim, length, wrap, strip_lines"}
        except Exception as e:
            return {"success": False, "result": f"Text error: {e}"}


class DiffTool(BaseTool):
    def execute(self, params):
        text1 = params.get("text1", "")
        text2 = params.get("text2", "")
        if not text1 or not text2:
            return {"success": False, "result": "Need text1 and text2"}
        try:
            import difflib
            lines1 = text1.splitlines(keepends=True)
            lines2 = text2.splitlines(keepends=True)
            diff = list(difflib.unified_diff(lines1, lines2, n=2))
            result = "".join(diff[:100])
            return {"success": True, "result": result or "No differences"}
        except Exception as e:
            return {"success": False, "result": f"Diff error: {e}"}


class SortTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "alpha")
        text = params.get("text", "")
        if not text:
            return {"success": False, "result": "Text required"}
        try:
            lines = text.split("\n")
            if action in ("alpha", "asc"):
                lines.sort()
            elif action == "desc":
                lines.sort(reverse=True)
            elif action == "numeric":
                nums = [float(l.strip()) for l in lines if l.strip()]
                nums.sort()
                return {"success": True, "result": "\n".join(str(n) for n in nums)}
            elif action == "length":
                lines.sort(key=len)
            elif action in ("unique", "uniq"):
                seen = []
                [seen.append(l) for l in lines if l not in seen]
                lines = seen
            elif action == "shuffle":
                random.shuffle(lines)
            elif action == "reverse":
                lines.reverse()
            return {"success": True, "result": "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"Sort error: {e}"}


class RegexTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "find")
        pattern = params.get("pattern", "")
        text = params.get("text", "")
        if not pattern or not text:
            return {"success": False, "result": "Need pattern and text"}
        try:
            if action == "find":
                matches = re.findall(pattern, text)
                return {"success": True, "result": f"Found {len(matches)}: " + ", ".join(str(m) for m in matches[:50])}
            elif action == "match":
                m = re.match(pattern, text)
                return {"success": True, "result": f"Match: {m.group()}" if m else "No match"}
            elif action == "search":
                m = re.search(pattern, text)
                return {"success": True, "result": f"Found: {m.group()}" if m else "Not found"}
            elif action == "replace":
                replacement = params.get("replacement", "")
                result = re.sub(pattern, replacement, text)
                return {"success": True, "result": result[:2000]}
            elif action == "split":
                parts = re.split(pattern, text)
                return {"success": True, "result": "\n".join(parts[:50])}
            return {"success": False, "result": "Actions: find, match, search, replace, split"}
        except Exception as e:
            return {"success": False, "result": f"Regex error: {e}"}


class UUIDTool(BaseTool):
    def execute(self, params):
        import uuid
        count = min(int(params.get("count", 1)), 50)
        results = [str(uuid.uuid4()) for _ in range(count)]
        return {"success": True, "result": "\n".join(results)}


class Base64Tool(BaseTool):
    def execute(self, params):
        action = params.get("action", "encode")
        text = params.get("text", "")
        if not text:
            return {"success": False, "result": "Text required"}
        try:
            if action == "encode":
                return {"success": True, "result": base64.b64encode(text.encode()).decode()}
            elif action == "decode":
                return {"success": True, "result": base64.b64decode(text).decode()}
            return {"success": False, "result": "Actions: encode, decode"}
        except Exception as e:
            return {"success": False, "result": f"Base64 error: {e}"}


class ConfirmTool(BaseTool):
    def execute(self, params):
        message = params.get("message", "Are you sure?")
        default = params.get("default", "yes")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            result = messagebox.askyesno("JARVIS", message)
            root.destroy()
            return {"success": True, "result": "yes" if result else "no"}
        except Exception:
            return {"success": True, "result": default}


class PromptTool(BaseTool):
    def execute(self, params):
        message = params.get("message", "Enter text:")
        default = params.get("default", "")
        try:
            import tkinter as tk
            from tkinter import simpledialog
            root = tk.Tk()
            root.withdraw()
            result = simpledialog.askstring("JARVIS", message, initialvalue=default)
            root.destroy()
            return {"success": True, "result": result or default}
        except Exception as e:
            return {"success": False, "result": f"Prompt error: {e}"}


class ChooseTool(BaseTool):
    def execute(self, params):
        message = params.get("message", "Choose:")
        options = params.get("options", [])
        if isinstance(options, str):
            options = [o.strip() for o in options.split(",")]
        if not options:
            return {"success": False, "result": "No options provided"}
        try:
            import tkinter as tk
            from tkinter import simpledialog
            root = tk.Tk()
            root.withdraw()
            result = simpledialog.askstring("JARVIS", f"{message}\nOptions: {', '.join(options)}", initialvalue=options[0])
            root.destroy()
            return {"success": True, "result": result or options[0]}
        except Exception:
            return {"success": True, "result": options[0]}


class BeepTool(BaseTool):
    def execute(self, params):
        freq = int(params.get("frequency", params.get("freq", 880)))
        duration = int(params.get("duration", 200))
        try:
            import winsound
            winsound.Beep(freq, duration)
            return {"success": True, "result": f"Beep at {freq}Hz for {duration}ms"}
        except ImportError:
            try:
                print(f"\a", end="", flush=True)
                return {"success": True, "result": "Beep sent"}
            except Exception:
                return {"success": False, "result": "Beep not available"}


class SleepTool(BaseTool):
    def execute(self, params):
        seconds = float(params.get("seconds", params.get("duration", 1)))
        if seconds > 300:
            return {"success": False, "result": "Max 300 seconds"}
        time.sleep(seconds)
        return {"success": True, "result": f"Slept for {seconds}s"}


class AlarmTool(BaseTool):
    def __init__(self):
        self._alarms = []

    def execute(self, params):
        action = params.get("action", "set")
        try:
            if action == "set":
                seconds = int(params.get("seconds", 10))
                def _alarm(sec):
                    time.sleep(sec)
                    try:
                        import winsound
                        for _ in range(5):
                            winsound.Beep(880, 200)
                            time.sleep(0.2)
                    except Exception:
                        print("\a" * 5, end="", flush=True)
                threading.Thread(target=_alarm, args=(seconds,), daemon=True).start()
                return {"success": True, "result": f"Alarm set for {seconds}s"}
            return {"success": False, "result": "Actions: set"}
        except Exception as e:
            return {"success": False, "result": f"Alarm error: {e}"}


class StopwatchTool(BaseTool):
    def __init__(self):
        self._start = 0
        self._running = False

    def execute(self, params):
        action = params.get("action", "start")
        try:
            if action == "start":
                self._start = time.time()
                self._running = True
                return {"success": True, "result": "Stopwatch started"}
            elif action == "stop":
                if not self._running:
                    return {"success": True, "result": "Not running"}
                elapsed = time.time() - self._start
                self._running = False
                return {"success": True, "result": f"Stopped: {elapsed:.2f}s"}
            elif action == "lap":
                if not self._running:
                    return {"success": True, "result": "Not running"}
                elapsed = time.time() - self._start
                return {"success": True, "result": f"Lap: {elapsed:.2f}s"}
            elif action == "reset":
                self._start = 0
                self._running = False
                return {"success": True, "result": "Stopwatch reset"}
            return {"success": False, "result": "Actions: start, stop, lap, reset"}
        except Exception as e:
            return {"success": False, "result": f"Stopwatch error: {e}"}


class FileInfoTool(BaseTool):
    def execute(self, params):
        path = params.get("path", "")
        if not path:
            return {"success": False, "result": "Path required"}
        try:
            st = os.stat(path)
            info = f"Size: {st.st_size:,} bytes"
            info += f"\nModified: {datetime.datetime.fromtimestamp(st.st_mtime)}"
            info += f"\nCreated: {datetime.datetime.fromtimestamp(st.st_ctime)}"
            info += f"\nPermissions: {oct(st.st_mode)[-3:]}"
            if os.path.isdir(path):
                count = len(os.listdir(path))
                info += f"\nDirectory with {count} items"
            else:
                ext = os.path.splitext(path)[1]
                info += f"\nType: {ext.upper() if ext else 'Unknown'}"
            return {"success": True, "result": info}
        except Exception as e:
            return {"success": False, "result": f"File info error: {e}"}


class DirListTool(BaseTool):
    def execute(self, params):
        path = params.get("path", ".")
        pattern = params.get("pattern", "*")
        max_items = int(params.get("max", 200))
        try:
            items = sorted(os.listdir(path))
            if pattern != "*":
                import fnmatch
                items = [i for i in items if fnmatch.fnmatch(i, pattern)]
            items = items[:max_items]
            dirs = [i + "/" for i in items if os.path.isdir(os.path.join(path, i))]
            files = [i for i in items if not os.path.isdir(os.path.join(path, i))]
            result = f"Directory: {os.path.abspath(path)}\n"
            if dirs:
                result += "Dirs: " + ", ".join(dirs) + "\n"
            if files:
                result += "Files: " + ", ".join(files)
            return {"success": True, "result": result or "(empty)"}
        except Exception as e:
            return {"success": False, "result": f"Dir list error: {e}"}


class ImageInfoTool(BaseTool):
    def execute(self, params):
        path = params.get("path", "")
        if not path:
            return {"success": False, "result": "Path required"}
        try:
            from PIL import Image
            img = Image.open(path)
            info = f"Format: {img.format}"
            info += f"\nSize: {img.size[0]}x{img.size[1]}px"
            info += f"\nMode: {img.mode}"
            info += f"\nFile: {os.path.getsize(path):,} bytes"
            if hasattr(img, 'info') and img.info:
                exif = {k: str(v)[:80] for k, v in img.info.items()}
                info += f"\nMetadata: {json.dumps(exif, ensure_ascii=False)}"
            return {"success": True, "result": info}
        except Exception as e:
            return {"success": False, "result": f"Image error: {e}"}


class FactTool(BaseTool):
    def execute(self, params):
        try:
            import urllib.request
            with urllib.request.urlopen("https://uselessfacts.jsph.pl/api/v2/facts/random", timeout=10) as r:
                data = json.loads(r.read())
            return {"success": True, "result": data.get("text", "No fact found")}
        except Exception:
            try:
                facts = [
                    "A day on Venus is longer than a year on Venus.",
                    "Honey never spoils. Archaeologists found 3000-year-old honey in Egyptian tombs.",
                    "Octopuses have three hearts and blue blood.",
                    "Bananas are berries, but strawberries aren't.",
                    "A group of flamingos is called a 'flamboyance'.",
                    "The Eiffel Tower can be 15 cm taller during summer.",
                    "Wombat poop is cube-shaped.",
                    "The human nose can remember 50,000 different scents.",
                    "There are more trees on Earth than stars in the Milky Way.",
                    "The speed of light is about 299,792,458 m/s.",
                ]
                return {"success": True, "result": random.choice(facts)}
            except Exception as e:
                return {"success": False, "result": f"Fact error: {e}"}


class LyricTool(BaseTool):
    def execute(self, params):
        artist = params.get("artist", "")
        title = params.get("title", "")
        if not artist and not title:
            return {"success": False, "result": "Need artist or title"}
        try:
            q = urllib.parse.quote(f"{artist} {title}")
            with urllib.request.urlopen(f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(title)}", timeout=10) as r:
                data = json.loads(r.read())
            lyrics = data.get("lyrics", "")
            return {"success": True, "result": lyrics[:2000]}
        except Exception:
            return {"success": False, "result": "Lyrics not found"}


class HNReaderTool(BaseTool):
    def execute(self, params):
        category = params.get("category", "top")
        count = min(int(params.get("count", 10)), 30)
        try:
            import urllib.request
            ids_url = f"https://hacker-news.firebaseio.com/v0/{category}stories.json"
            with urllib.request.urlopen(ids_url, timeout=10) as r:
                ids = json.loads(r.read())[:count]
            stories = []
            for sid in ids:
                with urllib.request.urlopen(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10) as r:
                    item = json.loads(r.read())
                stories.append(f"[{item.get('score', 0)}] {item.get('title', '')} ({item.get('url', 'no url')[:60]})")
            return {"success": True, "result": f"HN {category} stories:\n" + "\n".join(stories)}
        except Exception as e:
            return {"success": False, "result": f"HN error: {e}"}


class RedditTool(BaseTool):
    def execute(self, params):
        subreddit = params.get("subreddit", "programming")
        category = params.get("category", "hot")
        count = min(int(params.get("count", 10)), 30)
        try:
            import urllib.request
            url = f"https://www.reddit.com/r/{subreddit}/{category}.json?limit={count}&raw_json=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            posts = data.get("data", {}).get("children", [])
            lines = []
            for p in posts:
                d = p.get("data", {})
                lines.append(f"[{d.get('score', 0)}] {d.get('title', '')}")
            return {"success": True, "result": f"r/{subreddit} {category}:\n" + "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"Reddit error: {e}"}


class WikipediaTool(BaseTool):
    def execute(self, params):
        query = params.get("query", "")
        if not query:
            return {"success": False, "result": "Query required"}
        try:
            import urllib.request, urllib.parse
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(query)
            req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/2.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            extract = data.get("extract", "")
            title = data.get("title", query)
            if not extract or "may refer to" in extract.lower()[:50]:
                return {"success": False, "result": f"'{query}' is ambiguous. Try a more specific query."}
            return {"success": True, "result": f"**{title}**\n{extract[:2000]}"}
        except urllib.error.HTTPError:
            return {"success": False, "result": f"No Wikipedia page found for '{query}'"}
        except Exception as e:
            return {"success": False, "result": f"Wikipedia error: {e}"}


class WeatherForecastTool(BaseTool):
    def execute(self, params):
        city = params.get("city", "")
        days = min(int(params.get("days", 3)), 7)
        if not city:
            return {"success": False, "result": "City required"}
        try:
            import urllib.request, urllib.parse
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
            with urllib.request.urlopen(geo_url, timeout=10) as r:
                geo = json.loads(r.read())
            if not geo.get("results"):
                return {"success": False, "result": f"City '{city}' not found"}
            loc = geo["results"][0]
            lat, lon = loc["latitude"], loc["longitude"]
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode&timezone=auto&forecast_days={days}"
            with urllib.request.urlopen(w_url, timeout=10) as r:
                w = json.loads(r.read())
            daily = w.get("daily", {})
            dates = daily.get("time", [])
            tmax = daily.get("temperature_2m_max", [])
            tmin = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_sum", [])
            codes = daily.get("weathercode", [])
            weather_names = {0:"Clear",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Foggy",51:"Drizzle",61:"Rain",71:"Snow",80:"Showers",95:"Thunderstorm"}
            result = f"Forecast for {city}:\n"
            for i in range(len(dates)):
                wc = weather_names.get(codes[i] if i < len(codes) else 0, "Unknown")
                result += f"  {dates[i]}: {tmin[i]}-{tmax[i]}C, {wc}, {precip[i]}mm rain\n"
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "result": f"Forecast error: {e}"}


class CurrencyTool(BaseTool):
    def execute(self, params):
        amount = float(params.get("amount", 1))
        from_cur = params.get("from", params.get("from_currency", "USD")).upper()
        to_cur = params.get("to", params.get("to_currency", "EUR")).upper()
        try:
            import urllib.request
            req = urllib.request.Request(f"https://api.exchangerate-api.com/v4/latest/{from_cur}",
                                          headers={"User-Agent": "Jarvis/2.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            rates = data.get("rates", {})
            if to_cur not in rates:
                return {"success": False, "result": f"No rate for {to_cur}"}
            rate = rates[to_cur]
            converted = amount * rate
            return {"success": True, "result": f"{amount} {from_cur} = {converted:.2f} {to_cur} (rate: {rate:.4f})"}
        except Exception as e:
            return {"success": False, "result": f"Currency error: {e}"}


class StockTool(BaseTool):
    def execute(self, params):
        symbol = params.get("symbol", "").upper()
        if not symbol:
            return {"success": False, "result": "Symbol required (e.g. AAPL)"}
        try:
            import urllib.request
            req = urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                                          headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            result = data.get("chart", {}).get("result", [{}])[0]
            meta = result.get("meta", {})
            price = meta.get("regularMarketPrice", meta.get("previousClose", "N/A"))
            name = meta.get("exchangeName", "")
            currency = meta.get("currency", "USD")
            return {"success": True, "result": f"{symbol} ({name}): ${price} {currency}"}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return {"success": False, "result": "Stock API rate limited. Try again later."}
            return {"success": False, "result": f"Stock API error: {e.code}"}
        except Exception as e:
            return {"success": False, "result": f"Stock error: {e}"}


class MovieTool(BaseTool):
    def execute(self, params):
        title = params.get("title", "")
        if not title:
            return {"success": False, "result": "Title required"}
        try:
            q = urllib.parse.quote(title)
            req = urllib.request.Request(f"https://www.omdbapi.com/?t={q}&apikey=2c9d2e0e",
                                          headers={"User-Agent": "Jarvis/2.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            if data.get("Response") == "True":
                return {"success": True, "result": f"**{data.get('Title')}** ({data.get('Year')})\nRating: {data.get('imdbRating')}/10\nGenre: {data.get('Genre')}\nDirector: {data.get('Director')}\nPlot: {data.get('Plot', '')[:500]}"}
            return {"success": False, "result": data.get("Error", "Movie not found")}
        except Exception as e:
            return {"success": False, "result": f"Movie error: API unavailable. Try: {title}"}


class RecipeTool(BaseTool):
    def execute(self, params):
        query = params.get("query", "")
        if not query:
            return {"success": False, "result": "Query required"}
        try:
            q = urllib.parse.quote(query)
            with urllib.request.urlopen(f"https://www.themealdb.com/api/json/v1/1/search.php?s={q}", timeout=10) as r:
                data = json.loads(r.read())
            meals = data.get("meals", [])
            if not meals:
                return {"success": False, "result": "No recipes found"}
            meal = meals[0]
            ingredients = []
            for i in range(1, 21):
                ing = meal.get(f"strIngredient{i}")
                meas = meal.get(f"strMeasure{i}")
                if ing and ing.strip():
                    ingredients.append(f"{meas} {ing}".strip())
            result = f"**{meal['strMeal']}** ({meal.get('strArea', '')} - {meal.get('strCategory', '')})\n"
            result += f"Ingredients: {', '.join(ingredients[:15])}\n"
            result += f"Instructions: {meal.get('strInstructions', '')[:500]}"
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "result": f"Recipe error: {e}"}


class RDJokeTool(BaseTool):
    def execute(self, params):
        try:
            import urllib.request
            with urllib.request.urlopen("https://official-joke-api.appspot.com/random_joke", timeout=10) as r:
                data = json.loads(r.read())
            return {"success": True, "result": f"{data.get('setup', '')} - {data.get('punchline', '')}"}
        except Exception:
            try:
                import urllib.request
                with urllib.request.urlopen("https://v2.jokeapi.dev/joke/Any?type=twopart", timeout=10) as r:
                    data = json.loads(r.read())
                return {"success": True, "result": f"{data.get('setup', '')} - {data.get('delivery', '')}"}
            except Exception as e:
                return {"success": False, "result": f"Joke error: {e}"}


class ShowTool(BaseTool):
    """Display text in a scrollable popup window"""
    def execute(self, params):
        text = params.get("text", params.get("content", ""))
        title = params.get("title", "JARVIS Viewer")
        if not text:
            return {"success": False, "result": "Text required"}
        try:
            import tkinter as tk
            from tkinter import scrolledtext
            top = tk.Toplevel()
            top.title(title)
            top.geometry("600x400")
            top.configure(bg="#060618")
            txt = scrolledtext.ScrolledText(top, wrap=tk.WORD, bg="#0a0a2e", fg="#c8e6ff",
                                            insertbackground="#00ddff", font=("Consolas", 10))
            txt.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            txt.insert("1.0", text)
            txt.config(state=tk.DISABLED)
            return {"success": True, "result": f"Opened window: {title}"}
        except Exception as e:
            return {"success": True, "result": text[:2000]}


class AlertTool(BaseTool):
    """Show notification alert with custom title/message/icon"""
    def execute(self, params):
        title = params.get("title", "JARVIS")
        message = params.get("message", params.get("text", ""))
        icon = params.get("icon", "info")
        try:
            icons = {"info": 0x40, "warn": 0x30, "error": 0x10, "question": 0x20}
            flags = icons.get(icon, 0x40) | 0x1000
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, flags)
            return {"success": True, "result": f"Alert shown: {title}"}
        except Exception:
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(title, message, duration=5, threaded=True)
                return {"success": True, "result": f"Notification: {title}"}
            except Exception:
                return {"success": True, "result": f"[{icon.upper()}] {title}: {message[:200]}"}


class CsvTool(BaseTool):
    """Format CSV data as aligned table"""
    def execute(self, params):
        data = params.get("data", "")
        if not data:
            return {"success": False, "result": "CSV data required"}
        try:
            import csv, io
            reader = csv.reader(io.StringIO(data))
            rows = [row for row in reader if any(c.strip() for c in row)]
            if not rows:
                return {"success": False, "result": "Empty CSV"}
            col_widths = [max(len(cell) for cell in col) for col in zip(*rows)]
            lines = []
            for i, row in enumerate(rows):
                padded = [cell.ljust(col_widths[j]) for j, cell in enumerate(row)]
                lines.append(" | ".join(padded))
                if i == 0:
                    lines.append("-|-".join("-" * w for w in col_widths))
            return {"success": True, "result": "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"CSV error: {e}"}


class JsonFormatTool(BaseTool):
    """Format, validate, or query JSON data"""
    def execute(self, params):
        action = params.get("action", "format")
        data = params.get("data", "")
        if not data:
            return {"success": False, "result": "JSON data required"}
        try:
            parsed = json.loads(data)
            if action == "format":
                return {"success": True, "result": json.dumps(parsed, indent=2, ensure_ascii=False)[:5000]}
            elif action == "validate":
                return {"success": True, "result": "Valid JSON"}
            elif action == "minify":
                return {"success": True, "result": json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)}
            elif action == "query":
                import jsonpath_ng
                path = params.get("path", "$")
                expr = jsonpath_ng.parse(path)
                matches = [m.value for m in expr.find(parsed)]
                return {"success": True, "result": json.dumps(matches, indent=2, ensure_ascii=False)[:3000]}
            return {"success": False, "result": "Actions: format, validate, minify, query"}
        except json.JSONDecodeError as e:
            return {"success": False, "result": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"success": False, "result": f"JSON error: {e}"}


class BrightnessTool(BaseTool):
    """Get/set screen brightness"""
    def execute(self, params):
        action = params.get("action", "get")
        import subprocess
        try:
            if action == "get":
                r = subprocess.run(["powershell", "-c", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"],
                                   capture_output=True, text=True, timeout=5)
                val = r.stdout.strip()
                return {"success": True, "result": f"Brightness: {val}%" if val else "N/A"}
            elif action == "set":
                pct = max(0, min(100, int(params.get("percent", params.get("value", 50)))))
                subprocess.run(["powershell", "-c", f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{pct})"],
                               capture_output=True, text=True, timeout=5)
                return {"success": True, "result": f"Brightness set to {pct}%"}
            return {"success": False, "result": "Actions: get, set"}
        except Exception as e:
            return {"success": False, "result": f"Brightness error: {e}"}


class EncodeTool(BaseTool):
    """Encode/decode various formats"""
    def execute(self, params):
        action = params.get("action", "rot13")
        text = params.get("text", "")
        if not text:
            return {"success": False, "result": "Text required"}
        try:
            if action == "rot13":
                return {"success": True, "result": text.translate(str.maketrans(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"))}
            elif action == "binary":
                return {"success": True, "result": " ".join(format(ord(c), "08b") for c in text)}
            elif action == "hex":
                return {"success": True, "result": text.encode().hex()}
            elif action == "octal":
                return {"success": True, "result": " ".join(format(ord(c), "03o") for c in text)}
            elif action == "morse":
                morse = {"A":".-","B":"-...","C":"-.-.","D":"-..","E":".","F":"..-.","G":"--.","H":"....","I":"..","J":".---",
                         "K":"-.-","L":".-..","M":"--","N":"-.","O":"---","P":".--.","Q":"--.-","R":".-.","S":"...","T":"-",
                         "U":"..-","V":"...-","W":".--","X":"-..-","Y":"-.--","Z":"--..","0":"-----","1":".----","2":"..---",
                         "3":"...--","4":"....-","5":".....","6":"-....","7":"--...","8":"---..","9":"----."}
                encoded = " ".join(morse.get(c.upper(), c) for c in text)
                return {"success": True, "result": encoded[:2000]}
            return {"success": False, "result": "Actions: rot13, binary, hex, octal, morse"}
        except Exception as e:
            return {"success": False, "result": f"Encode error: {e}"}


class ChartTool(BaseTool):
    """Generate ASCII bar chart from numbers"""
    def execute(self, params):
        data = params.get("data", "")
        if isinstance(data, str):
            try:
                entries = json.loads(data)
            except Exception:
                pairs = [p.split(":") for p in data.split(",") if ":" in p]
                entries = {k.strip(): float(v.strip()) for k, v in pairs}
        else:
            entries = data if isinstance(data, dict) else {}
        if not entries:
            return {"success": False, "result": "Data required (e.g. {'A':10,'B':20})"}
        max_val = max(entries.values()) or 1
        bar_width = 30
        lines = []
        for label, val in sorted(entries.items(), key=lambda x: -x[1]):
            bar_len = max(1, int((val / max_val) * bar_width))
            bar = "█" * bar_len
            lines.append(f"{str(label)[:10]:>10} | {bar} {val}")
        return {"success": True, "result": "\n".join(lines)}


class MarkdownRenderTool(BaseTool):
    """Strip markdown formatting to clean text"""
    def execute(self, params):
        text = params.get("text", "")
        if not text:
            return {"success": False, "result": "Text required"}
        try:
            text = re.sub(r'#{1,6}\s+', '', text)
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
            text = re.sub(r'\*([^*]+)\*', r'\1', text)
            text = re.sub(r'`([^`]+)`', r'\1', text)
            text = re.sub(r'```.*?\n', '\n', text, flags=re.DOTALL)
            text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
            text = re.sub(r'>\s+', '', text)
            text = re.sub(r'[-*+]\s+', '', text)
            text = re.sub(r'\d+\.\s+', '', text)
            text = re.sub(r'\|', '', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return {"success": True, "result": text.strip()[:3000]}
        except Exception as e:
            return {"success": False, "result": f"Render error: {e}"}


class ScreenResTool(BaseTool):
    """Get screen resolution and info"""
    def execute(self, params):
        try:
            import tkinter as tk
            root = tk.Tk()
            w = root.winfo_screenwidth()
            h = root.winfo_screenheight()
            root.destroy()
            return {"success": True, "result": f"Screen: {w}x{h}"}
        except Exception:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                return {"success": True, "result": f"Screen: {user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}"}
            except Exception:
                return {"success": False, "result": "Screen info unavailable"}


class CounterTool(BaseTool):
    """Simple increment/decrement/reset counter"""
    def __init__(self):
        self._counters = {}

    def execute(self, params):
        name = params.get("name", "default")
        action = params.get("action", "get")
        if name not in self._counters:
            self._counters[name] = 0
        try:
            if action == "get":
                return {"success": True, "result": f"Counter '{name}': {self._counters[name]}"}
            elif action == "inc":
                self._counters[name] += 1
                return {"success": True, "result": f"Counter '{name}': {self._counters[name]}"}
            elif action == "dec":
                self._counters[name] -= 1
                return {"success": True, "result": f"Counter '{name}': {self._counters[name]}"}
            elif action == "add":
                self._counters[name] += int(params.get("value", params.get("amount", 1)))
                return {"success": True, "result": f"Counter '{name}': {self._counters[name]}"}
            elif action == "reset":
                self._counters[name] = 0
                return {"success": True, "result": f"Counter '{name}' reset"}
            elif action == "list":
                if not self._counters:
                    return {"success": True, "result": "No counters"}
                return {"success": True, "result": "\n".join(f"{k}: {v}" for k, v in sorted(self._counters.items()))}
            return {"success": False, "result": "Actions: get, inc, dec, add, reset, list"}
        except Exception as e:
            return {"success": False, "result": f"Counter error: {e}"}


class ProgressTool(BaseTool):
    """Show a simple text progress bar"""
    def execute(self, params):
        current = int(params.get("current", params.get("value", 0)))
        total = int(params.get("total", params.get("max", 100)))
        width = int(params.get("width", params.get("size", 30)))
        label = params.get("label", "")
        if total <= 0:
            total = 100
        pct = min(100, max(0, (current / total) * 100))
        filled = int((current / total) * width)
        bar = "█" * filled + "░" * (width - filled)
        result = f"{label + ': ' if label else ''}[{bar}] {pct:.0f}% ({current}/{total})"
        return {"success": True, "result": result}


class ColorPickerTool(BaseTool):
    """Show a color picker dialog or convert between color formats"""
    def execute(self, params):
        action = params.get("action", "pick")
        try:
            if action == "pick":
                import tkinter as tk
                from tkinter import colorchooser
                root = tk.Tk()
                root.withdraw()
                color = colorchooser.askcolor(title="Pick a color", initialcolor="#00ddff")
                root.destroy()
                if color and color[0]:
                    r, g, b = [int(c) for c in color[0]]
                    return {"success": True, "result": f"RGB({r},{g},{b})  Hex: #{r:02x}{g:02x}{b:02x}"}
                return {"success": True, "result": "No color selected"}
            elif action == "rgb_to_hex":
                r, g, b = int(params.get("r", 0)), int(params.get("g", 0)), int(params.get("b", 0))
                return {"success": True, "result": f"#{r:02x}{g:02x}{b:02x}"}
            elif action == "hex_to_rgb":
                h = params.get("hex", "#000").lstrip("#")
                if len(h) == 3:
                    h = "".join(c*2 for c in h)
                r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                return {"success": True, "result": f"rgb({r},{g},{b})"}
            return {"success": False, "result": "Actions: pick, rgb_to_hex, hex_to_rgb"}
        except Exception as e:
            return {"success": False, "result": f"Color pick error: {e}"}


class BibliographyTool(BaseTool):
    def execute(self, params):
        style = params.get("style", "mla").lower()
        sources_str = params.get("sources", params.get("items", ""))
        if not sources_str:
            return {"success": False, "result": "Provide sources separated by | (author|title|publisher|year)"}
        entries = [s.strip() for s in sources_str.split("|") if s.strip()]
        lines = [f"Bibliography ({style.upper()}):"]
        for i in range(0, len(entries), 4):
            author = entries[i] if i < len(entries) else ""
            title = entries[i + 1] if i + 1 < len(entries) else ""
            publisher = entries[i + 2] if i + 2 < len(entries) else ""
            year = entries[i + 3] if i + 3 < len(entries) else ""
            if not title:
                continue
            if style == "mla":
                lines.append(f"  {author}. *{title}*. {publisher}, {year}." if author else f"  *{title}*. {publisher}, {year}.")
            elif style == "apa":
                lines.append(f"  {author} ({year}). *{title}*. {publisher}." if author else f"  ({year}). *{title}*. {publisher}.")
            elif style == "chicago":
                lines.append(f"  {author}. *{title}*. {publisher}, {year}." if author else f"  *{title}*. {publisher}, {year}.")
            else:
                lines.append(f"  {author} ({year}), {title}, {publisher}")
        return {"success": True, "result": "\n".join(lines)}


class EquationSolveTool(BaseTool):
    def execute(self, params):
        equation = params.get("equation", "").strip()
        if not equation:
            return {"success": False, "result": "Provide equation (e.g., 2x+3=7 or x^2-4=0)"}
        try:
            eq = re.sub(r'\^', '**', equation)
            eq = eq.replace("=", "-(") + ")" if "=" in eq else eq + "=0"
            eq = eq.replace("=0", "") if not eq.endswith(")") else eq
            # Linear: ax + b = 0
            if "x" in eq and "**" not in eq:
                # Parse as linear: solve for x
                expr = eq.replace("=0", "-0") if "=0" not in eq else eq
                expr = expr.replace("=0", "") if expr.endswith("=0") else expr.replace("=", "-(") + ")" if "=" in expr else expr
                # Try simple linear: ax + b = 0 -> x = -b/a
                simplified = expr.replace(" ", "").replace("x", "").replace("(", "").replace(")", "")
                return {"success": True, "result": f"To solve '{equation}':\n  Isolate x on one side\n  Use inverse operations\n  Solution format: x = value"}
            # Quadratic: ax^2 + bx + c = 0
            if "**2" in eq or "x^2" in equation:
                return {"success": True, "result": f"Quadratic equation: {equation}\n  Use the quadratic formula:\n  x = (-b ± √(b² - 4ac)) / 2a\n  First identify a, b, c from your equation"}
            return {"success": True, "result": f"Equation: {equation}\n  Solve step by step:\n  1. Simplify both sides\n  2. Use inverse operations\n  3. Check your answer"}
        except Exception as e:
            return {"success": False, "result": f"Equation error: {e}"}


# ════════════════════════════════════════════
# Student & Teacher Tools (73 tools)
# ════════════════════════════════════════════

_STUDY_DIR = os.path.join(os.path.expanduser("~"), ".jarvis_study")
os.makedirs(_STUDY_DIR, exist_ok=True)


class FlashcardTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "add")
        path = os.path.join(_STUDY_DIR, "flashcards.json")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    cards = json.load(f)
            else:
                cards = []
            if action == "add":
                q, a = params.get("question", ""), params.get("answer", "")
                if not q or not a:
                    return {"success": False, "result": "Add: provide question + answer"}
                deck = params.get("deck", "default")
                cards.append({"question": q, "answer": a, "deck": deck, "box": 0})
                with open(path, "w") as f:
                    json.dump(cards, f)
                return {"success": True, "result": f"Added: {q[:50]}"}
            elif action == "quiz":
                deck = params.get("deck", "default")
                pool = [c for c in cards if c.get("deck", "default") == deck]
                if not pool:
                    return {"success": True, "result": "No cards in that deck"}
                random.shuffle(pool)
                n = min(int(params.get("count", 5)), len(pool))
                lines = [f"Flashcard Quiz ({n} questions):"]
                for c in pool[:n]:
                    lines.append(f"\nQ: {c['question']}\nA: ||{c['answer']}||")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "list":
                deck = params.get("deck", "")
                pool = [c for c in cards if c.get("deck", "default") == deck] if deck else cards
                if not pool:
                    return {"success": True, "result": "No cards found"}
                lines = [f"Flashcards ({len(pool)} cards):"]
                for i, c in enumerate(pool, 1):
                    lines.append(f"{i}. [{c.get('deck','default')}] {c['question'][:60]}")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "delete":
                deck = params.get("deck", "default")
                cards = [c for c in cards if c.get("deck", "default") != deck]
                with open(path, "w") as f:
                    json.dump(cards, f)
                return {"success": True, "result": f"Deleted deck: {deck}"}
            elif action == "stats":
                deck = params.get("deck", "default")
                pool = [c for c in cards if c.get("deck", "default") == deck]
                return {"success": True, "result": f"Deck '{deck}': {len(pool)} cards"}
            return {"success": False, "result": "Actions: add, quiz, list, delete, stats"}
        except Exception as e:
            return {"success": False, "result": f"Flashcard error: {e}"}


class QuizTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", params.get("subject", ""))
        count = min(int(params.get("count", 5)), 20)
        if not topic:
            return {"success": False, "result": "Provide a topic/subject"}
        questions = {
            "math": [
                ("What is the derivative of x²?", "2x"),
                ("What is π to 4 decimal places?", "3.1416"),
                ("What is the Pythagorean theorem?", "a² + b² = c²"),
                ("What is the quadratic formula?", "x = (-b ± √(b²-4ac))/2a"),
                ("What is sin²θ + cos²θ equal to?", "1"),
                ("What is log₁₀(100)?", "2"),
                ("What is the area of a circle?", "πr²"),
                ("What is 7! (7 factorial)?", "5040"),
            ],
            "science": [
                ("What is the chemical symbol for gold?", "Au"),
                ("What planet is closest to the sun?", "Mercury"),
                ("What gas do plants absorb?", "CO₂ (carbon dioxide)"),
                ("What is the speed of light?", "~3×10⁸ m/s"),
                ("What organ pumps blood?", "Heart"),
                ("What is H₂O?", "Water"),
                ("What element has atomic number 6?", "Carbon"),
                ("What force keeps planets in orbit?", "Gravity"),
            ],
            "history": [
                ("What year did WW2 end?", "1945"),
                ("Who discovered America in 1492?", "Christopher Columbus"),
                ("What empire was ruled by Julius Caesar?", "Roman Empire"),
                ("What wall separated Berlin?", "Berlin Wall"),
                ("Who wrote the Declaration of Independence?", "Thomas Jefferson"),
                ("What ancient wonder was in Giza?", "The Great Pyramid"),
            ],
            "english": [
                ("What is a synonym for 'happy'?", "Joyful"),
                ("What tense describes ongoing action?", "Present continuous"),
                ("What is a metaphor?", "Comparison without 'like/as'"),
                ("What is a protagonist?", "Main character"),
                ("What is alliteration?", "Same starting sound repetition"),
            ],
        }
        topic_lower = topic.lower()
        for key in questions:
            if key in topic_lower or topic_lower in key:
                pool = questions[key]
                random.shuffle(pool)
                n = min(count, len(pool))
                lines = [f"Quiz: {key.title()} ({n} questions)"]
                for i, (q, a) in enumerate(pool[:n], 1):
                    lines.append(f"{i}. {q}\n   → {a}")
                return {"success": True, "result": "\n\n".join(lines)}
        # Generate generic quiz
        lines = [f"Quiz: {topic} ({count} questions)\n"]
        for i in range(count):
            lines.append(f"{i+1}. What is a key concept in {topic}?")
        return {"success": True, "result": "\n".join(lines) + "\n\n(Add specific quiz topics: math, science, history, english)"}


class StudySetTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "create")
        path = os.path.join(_STUDY_DIR, "studysets.json")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    sets = json.load(f)
            else:
                sets = {}
            if action == "create":
                name = params.get("name", "").strip()
                items_str = params.get("items", "")
                if not name or not items_str:
                    return {"success": False, "result": "Provide name + items (comma-separated)"}
                items = [i.strip() for i in items_str.split(",") if i.strip()]
                sets[name] = {"items": items, "created": time.time()}
                with open(path, "w") as f:
                    json.dump(sets, f)
                return {"success": True, "result": f"Study set '{name}' with {len(items)} items"}
            elif action == "list":
                if not sets:
                    return {"success": True, "result": "No study sets"}
                lines = [f"Study Sets ({len(sets)}):"]
                for name, data in sets.items():
                    lines.append(f"  • {name} ({len(data['items'])} items)")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "view":
                name = params.get("name", "")
                if name not in sets:
                    return {"success": False, "result": f"Set '{name}' not found"}
                items = sets[name]["items"]
                lines = [f"Study Set: {name}\n"]
                for i, item in enumerate(items, 1):
                    lines.append(f"{i}. {item}")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "delete":
                name = params.get("name", "")
                if name in sets:
                    del sets[name]
                    with open(path, "w") as f:
                        json.dump(sets, f)
                    return {"success": True, "result": f"Deleted: {name}"}
                return {"success": False, "result": f"Set '{name}' not found"}
            return {"success": False, "result": "Actions: create, list, view, delete"}
        except Exception as e:
            return {"success": False, "result": f"StudySet error: {e}"}


class GradeCalcTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "needed")
        if action == "needed":
            try:
                current = float(params.get("current", params.get("grade", 0)))
                desired = float(params.get("desired", params.get("target", 0)))
                weight = float(params.get("weight", params.get("exam_weight", 0)))
                if not (0 <= weight <= 100):
                    return {"success": False, "result": "Weight must be 0-100"}
                w = weight / 100.0
                needed = (desired - current * (1 - w)) / w
                if needed > 100:
                    return {"success": True, "result": f"Need {needed:.1f}% — impossible even with 100%"}
                elif needed < 0:
                    return {"success": True, "result": "You already have the grade locked in!"}
                return {"success": True, "result": f"Need {needed:.1f}% on the final to get {desired}%"}
            except (ValueError, ZeroDivisionError):
                return {"success": False, "result": "Provide: current, desired, weight"}
        elif action == "final":
            try:
                grades_str = params.get("grades", "")
                weights_str = params.get("weights", "")
                if not grades_str or not weights_str:
                    return {"success": False, "result": "Provide comma-separated grades and weights"}
                grades = [float(g.strip()) for g in grades_str.split(",")]
                weights = [float(w.strip()) for w in weights_str.split(",")]
                if len(grades) != len(weights):
                    return {"success": False, "result": "Same number of grades and weights required"}
                total = sum(g * w / 100 for g, w in zip(grades, weights))
                return {"success": True, "result": f"Grade: {total:.1f}%"}
            except Exception:
                return {"success": False, "result": "Grades and weights must be numbers"}
        return {"success": False, "result": "Actions: needed (what-if), final (weighted total)"}


class GPATool(BaseTool):
    def execute(self, params):
        action = params.get("action", "calculate")
        scale = float(params.get("scale", 4.0))
        if action == "calculate":
            grades_str = params.get("grades", "")
            hours_str = params.get("hours", params.get("credits", ""))
            if not grades_str:
                return {"success": False, "result": "Provide grades (letter or 0-4 values, comma-separated)"}
            grade_map = {"A+": 4.0, "A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7,
                         "C+": 2.3, "C": 2.0, "C-": 1.7, "D+": 1.3, "D": 1.0, "F": 0.0}
            parts = [g.strip() for g in grades_str.split(",")]
            grades = []
            for g in parts:
                if g.upper() in grade_map:
                    grades.append(grade_map[g.upper()])
                else:
                    try:
                        grades.append(float(g))
                    except ValueError:
                        return {"success": False, "result": f"Invalid grade: {g}"}
            if hours_str:
                hours = [float(h.strip()) for h in hours_str.split(",")]
                if len(grades) != len(hours):
                    return {"success": False, "result": "Same number of grades and credit hours required"}
                total = sum(g * h for g, h in zip(grades, hours)) / sum(hours) * scale / 4.0
                return {"success": True, "result": f"GPA: {total:.2f} / {scale:.1f}"}
            else:
                total = sum(grades) / len(grades) * scale / 4.0
                return {"success": True, "result": f"GPA: {total:.2f} / {scale:.1f}"}
        elif action == "target":
            try:
                current_gpa = float(params.get("current_gpa", 0))
                target_gpa = float(params.get("target_gpa", 0))
                credits_so_far = float(params.get("credits_so_far", 0))
                new_credits = float(params.get("new_credits", 0))
                needed = (target_gpa * (credits_so_far + new_credits) - current_gpa * credits_so_far) / new_credits
                return {"success": True, "result": f"Need avg GPA of {needed:.2f} in {new_credits:.0f} new credits to reach {target_gpa:.2f}"}
            except (ValueError, ZeroDivisionError):
                return {"success": False, "result": "Provide: current_gpa, target_gpa, credits_so_far, new_credits"}
        return {"success": False, "result": "Actions: calculate, target"}


class AssignmentTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "add")
        path = os.path.join(_STUDY_DIR, "assignments.json")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    assignments = json.load(f)
            else:
                assignments = []
            if action == "add":
                name = params.get("name", params.get("title", ""))
                due = params.get("due", params.get("due_date", ""))
                course = params.get("course", params.get("class", "General"))
                if not name or not due:
                    return {"success": False, "result": "Provide name + due date"}
                assignments.append({"name": name, "due": due, "course": course,
                                    "status": "pending", "created": time.time()})
                with open(path, "w") as f:
                    json.dump(assignments, f)
                return {"success": True, "result": f"Added: {name} (due {due})"}
            elif action == "list":
                if not assignments:
                    return {"success": True, "result": "No assignments"}
                course = params.get("course", "")
                pool = [a for a in assignments if not course or a.get("course") == course]
                pending = [a for a in pool if a.get("status") != "done"]
                done = [a for a in pool if a.get("status") == "done"]
                lines = [f"Assignments ({len(pool)} total, {len(pending)} pending):"]
                if pending:
                    lines.append("\nPending:")
                    for a in sorted(pending, key=lambda x: x.get("due", "")):
                        lines.append(f"  • {a['name']} — due {a['due']} [{a.get('course','General')}]")
                if done:
                    lines.append(f"\nCompleted ({len(done)}):")
                    for a in done:
                        lines.append(f"  ✓ {a['name']}")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "done":
                name = params.get("name", params.get("title", ""))
                for a in assignments:
                    if a["name"].lower() == name.lower():
                        a["status"] = "done"
                        with open(path, "w") as f:
                            json.dump(assignments, f)
                        return {"success": True, "result": f"Completed: {a['name']}"}
                return {"success": False, "result": f"Assignment not found: {name}"}
            elif action == "delete":
                name = params.get("name", params.get("title", ""))
                assignments = [a for a in assignments if a["name"].lower() != name.lower()]
                with open(path, "w") as f:
                    json.dump(assignments, f)
                return {"success": True, "result": f"Deleted: {name}"}
            return {"success": False, "result": "Actions: add, list, done, delete"}
        except Exception as e:
            return {"success": False, "result": f"Assignment error: {e}"}


class StudyTimerTool(BaseTool):
    def __init__(self):
        self._timer_thread = None
        self._running = False
        self._remaining = 0

    def execute(self, params):
        action = params.get("action", "start")
        if action == "start":
            minutes = int(params.get("minutes", params.get("duration", 25)))
            self._remaining = minutes * 60
            self._running = True
            if not self._timer_thread or not self._timer_thread.is_alive():
                self._timer_thread = threading.Thread(target=self._run, daemon=True)
                self._timer_thread.start()
            return {"success": True, "result": f"Study timer: {minutes} min (Pomodoro). Focus!"}
        elif action == "stop":
            self._running = False
            return {"success": True, "result": "Timer stopped"}
        elif action == "status":
            if self._running:
                mins, secs = divmod(self._remaining, 60)
                return {"success": True, "result": f"Time remaining: {mins}:{secs:02d}"}
            return {"success": True, "result": "Timer not running"}

    def _run(self):
        while self._running and self._remaining > 0:
            time.sleep(1)
            self._remaining -= 1
        if self._running:
            self._running = False
            try:
                if os.name == 'nt':
                    import winsound
                    winsound.Beep(880, 500)
                    winsound.Beep(660, 500)
                else:
                    print("\a")
            except Exception:
                pass


class AttendanceTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "record")
        path = os.path.join(_STUDY_DIR, "attendance.json")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
            else:
                data = {"students": {}, "records": []}
            if action == "add_student":
                name = params.get("name", "").strip()
                if not name:
                    return {"success": False, "result": "Provide student name"}
                sid = params.get("id", name.lower().replace(" ", "_"))
                if sid in data["students"]:
                    return {"success": False, "result": f"Student '{name}' already exists"}
                data["students"][sid] = {"name": name, "added": time.time()}
                with open(path, "w") as f:
                    json.dump(data, f)
                return {"success": True, "result": f"Added student: {name}"}
            elif action == "record":
                sid = params.get("id", params.get("student", ""))
                date = params.get("date", datetime.date.today().isoformat())
                present = params.get("present", True)
                if isinstance(present, str):
                    present = present.lower() in ("true", "yes", "1", "present")
                if sid not in data["students"]:
                    return {"success": False, "result": f"Student not found. Use add_student first."}
                data["records"].append({"student_id": sid, "date": date, "present": present})
                with open(path, "w") as f:
                    json.dump(data, f)
                return {"success": True, "result": f"Recorded {'present' if present else 'absent'} for {data['students'][sid]['name']} on {date}"}
            elif action == "report":
                sid = params.get("id", params.get("student", ""))
                if sid:
                    if sid not in data["students"]:
                        return {"success": False, "result": f"Student not found: {sid}"}
                    records = [r for r in data["records"] if r["student_id"] == sid]
                    total = len(records)
                    present = sum(1 for r in records if r["present"])
                    pct = (present / total * 100) if total else 0
                    return {"success": True, "result": f"{data['students'][sid]['name']}: {present}/{total} ({pct:.0f}%)"}
                lines = ["Attendance Report:"]
                for sid, s in data["students"].items():
                    records = [r for r in data["records"] if r["student_id"] == sid]
                    total = len(records)
                    present = sum(1 for r in records if r["present"])
                    pct = (present / total * 100) if total else 0
                    lines.append(f"  {s['name']}: {present}/{total} ({pct:.0f}%)")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "students":
                lines = [f"Students ({len(data['students'])}):"]
                for sid, s in data["students"].items():
                    lines.append(f"  {s['name']} ({sid})")
                return {"success": True, "result": "\n".join(lines)}
            return {"success": False, "result": "Actions: add_student, record, report, students"}
        except Exception as e:
            return {"success": False, "result": f"Attendance error: {e}"}


class EssayOutlineTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "")
        style = params.get("style", "argumentative")
        paragraphs = min(int(params.get("paragraphs", params.get("count", 5))), 15)
        if not topic:
            return {"success": False, "result": "Provide essay topic"}
        templates = {
            "argumentative": [
                "I. Introduction", "   A. Hook / attention grabber",
                f"   B. Background on {topic}", "   C. Thesis statement (your position)",
                "II. Body Paragraph 1 — Main Argument",
                "   A. Topic sentence", "   B. Evidence / example", "   C. Analysis",
                "II/III. Body Paragraph 2 — Supporting Argument",
                "   A. Topic sentence", "   B. Evidence / example", "   C. Analysis",
                "III/IV. Body Paragraph 3 — Counterargument & Rebuttal",
                "   A. Opposing view", "   B. Rebuttal with evidence",
                "V. Conclusion", "   A. Restate thesis", "   B. Summarize main points",
                "   C. Closing thought / call to action",
            ],
            "expository": [
                "I. Introduction", "   A. Hook", f"   B. Context for {topic}",
                "   C. Thesis / main idea",
                "II. Body Paragraph 1 — Key Point 1",
                "   A. Explanation", "   B. Evidence", "   C. Connection",
                "III. Body Paragraph 2 — Key Point 2",
                "   A. Explanation", "   B. Evidence", "   C. Connection",
                "IV. Body Paragraph 3 — Key Point 3",
                "   A. Explanation", "   B. Evidence", "   C. Connection",
                "V. Conclusion", "   A. Summary", "   B. Significance / implications",
            ],
            "narrative": [
                "I. Introduction", "   A. Setting / scene setup",
                "   B. Characters involved", "   C. Thesis / central theme",
                "II. Rising Action / Events",
                "   A. Event 1", "   B. Event 2", "   C. Event 3",
                "III. Climax / Turning Point",
                "   A. Key moment", "   B. Emotional impact",
                "IV. Falling Action", "   A. Consequences", "   B. Resolution begins",
                "V. Conclusion", "   A. Reflection / lesson learned",
                "   B. Closing image or thought",
            ],
        }
        lines = [f"Essay Outline: {topic}", f"Style: {style}", "=" * 40]
        if style.lower() in templates:
            lines.extend(templates[style.lower()])
        else:
            lines.append(f"I. Introduction (on {topic})")
            for i in range(2, paragraphs):
                lines.append(f"{chr(64+i)}. Body Paragraph {i-1}")
                lines.append(f"   A. Main point / evidence")
            lines.append(f"{chr(64+paragraphs)}. Conclusion")
        return {"success": True, "result": "\n".join(lines)}


class CitationTool(BaseTool):
    def execute(self, params):
        style = params.get("style", "mla").lower()
        source_type = params.get("type", "book").lower()
        author = params.get("author", "")
        title = params.get("title", "")
        publisher = params.get("publisher", "")
        year = params.get("year", params.get("date", ""))
        pages = params.get("pages", params.get("page", ""))
        url = params.get("url", "")
        journal = params.get("journal", params.get("publication", ""))
        volume = params.get("volume", "")
        issue = params.get("issue", params.get("number", ""))
        website = params.get("website", publisher)
        if not title:
            return {"success": False, "result": "At minimum, provide the title"}
        auth_part = f"{author}. " if author else ""
        title_part = f"\"{title}.\" " if source_type in ("article", "webpage", "chapter") else f"*{title}.* "
        if style == "mla":
            if source_type == "book":
                citation = f"{auth_part}*{title}.* {publisher}{', ' + year if year else ''}."
            elif source_type == "article":
                citation = f"{auth_part}\"{title}.\" *{journal}*{', vol. ' + volume if volume else ''}{', no. ' + issue if issue else ''}{' (' + year + ')' if year else ''}{': ' + pages if pages else ''}."
            elif source_type == "website":
                citation = f"{auth_part}\"{title}.\" *{website}*{', ' + year if year else ''}{', ' + url if url else ''}."
            else:
                citation = f"{auth_part}*{title}.* {publisher if publisher else 'n.p.'}, {year if year else 'n.d.'}."
        elif style == "apa":
            year_part = f"({year})" if year else "(n.d.)"
            if source_type == "book":
                citation = f"{author}{', ' if author else ''}{year_part}. *{title}*. {publisher}."
            elif source_type == "article":
                citation = f"{author}{', ' if author else ''}{year_part}. {title}. *{journal}*{', ' + volume if volume else ''}{'(' + issue + ')' if issue else ''}{', ' + pages if pages else ''}.{'' + url if url else ''}"
            elif source_type == "website":
                citation = f"{author}{', ' if author else ''}{year_part}. {title}. {website}. {url}"
            else:
                citation = f"{author}{', ' if author else ''}{year_part}. *{title}*. {publisher if publisher else 'n.p.'}."
        elif style == "chicago":
            if source_type == "book":
                citation = f"{author}. *{title}*. {publisher}, {year}."
            elif source_type == "article":
                citation = f"{author}. \"{title}.\" *{journal}* {volume}, no. {issue} ({year}): {pages}."
            elif source_type == "website":
                citation = f"{author}. \"{title}.\" {website}. {url}."
            else:
                citation = f"{author}. *{title}*. {publisher}, {year}."
        else:
            return {"success": False, "result": "Styles: mla, apa, chicago"}
        return {"success": True, "result": citation}


class ThesaurusTool(BaseTool):
    _DATA = {
        "good": {"synonyms": ["excellent", "fine", "satisfactory", "superb", "quality"],
                 "antonyms": ["bad", "poor", "inferior", "terrible"]},
        "bad": {"synonyms": ["poor", "terrible", "awful", "inferior", "substandard"],
                "antonyms": ["good", "excellent", "superb"]},
        "big": {"synonyms": ["large", "huge", "enormous", "massive", "vast", "immense"],
                "antonyms": ["small", "tiny", "minute"]},
        "small": {"synonyms": ["tiny", "minute", "compact", "petite", "minor"],
                  "antonyms": ["big", "large", "huge", "enormous"]},
        "happy": {"synonyms": ["joyful", "cheerful", "delighted", "elated", "glad"],
                  "antonyms": ["sad", "unhappy", "miserable", "gloomy"]},
        "sad": {"synonyms": ["unhappy", "miserable", "gloomy", "melancholy", "sorrowful"],
                "antonyms": ["happy", "joyful", "elated", "cheerful"]},
        "smart": {"synonyms": ["intelligent", "clever", "brilliant", "bright", "sharp"],
                  "antonyms": ["stupid", "dull", "dumb"]},
        "beautiful": {"synonyms": ["gorgeous", "stunning", "lovely", "attractive", "magnificent"],
                      "antonyms": ["ugly", "hideous", "plain"]},
        "fast": {"synonyms": ["quick", "rapid", "swift", "speedy", "hasty"],
                 "antonyms": ["slow", "sluggish", "leisurely"]},
        "slow": {"synonyms": ["sluggish", "leisurely", "unhurried", "gradual"],
                 "antonyms": ["fast", "quick", "rapid", "swift"]},
        "important": {"synonyms": ["significant", "crucial", "vital", "essential", "key"],
                      "antonyms": ["unimportant", "trivial", "minor"]},
        "difficult": {"synonyms": ["hard", "challenging", "tough", "complex", "demanding"],
                      "antonyms": ["easy", "simple", "effortless"]},
        "easy": {"synonyms": ["simple", "effortless", "straightforward", "basic"],
                 "antonyms": ["difficult", "hard", "challenging", "complex"]},
        "interesting": {"synonyms": ["engaging", "fascinating", "captivating", "intriguing"],
                        "antonyms": ["boring", "dull", "tedious"]},
        "new": {"synonyms": ["fresh", "novel", "modern", "recent", "innovative"],
                "antonyms": ["old", "ancient", "outdated"]},
        "old": {"synonyms": ["ancient", "aged", "elderly", "antique", "outdated"],
                "antonyms": ["new", "young", "fresh", "modern"]},
        "strong": {"synonyms": ["powerful", "robust", "sturdy", "resilient", "tough"],
                   "antonyms": ["weak", "fragile", "feeble"]},
        "weak": {"synonyms": ["fragile", "feeble", "delicate", "frail"],
                 "antonyms": ["strong", "powerful", "robust", "sturdy"]},
        "funny": {"synonyms": ["humorous", "amusing", "comical", "hilarious", "witty"],
                  "antonyms": ["serious", "solemn", "grave"]},
        "brave": {"synonyms": ["courageous", "fearless", "bold", "valiant", "heroic"],
                  "antonyms": ["cowardly", "timid", "fearful"]},
    }

    def execute(self, params):
        word = params.get("word", "").strip().lower()
        action = params.get("action", "synonyms")
        if not word:
            return {"success": False, "result": "Provide a word"}
        if word in self._DATA:
            entry = self._DATA[word]
            if action == "synonyms":
                return {"success": True, "result": f"Synonyms for '{word}': {', '.join(entry['synonyms'])}"}
            elif action == "antonyms":
                return {"success": True, "result": f"Antonyms for '{word}': {', '.join(entry['antonyms'])}"}
            elif action == "all":
                return {"success": True, "result":
                        f"'{word}'\nSynonyms: {', '.join(entry['synonyms'])}\nAntonyms: {', '.join(entry['antonyms'])}"}
        return {"success": True, "result": f"No thesaurus entry for '{word}'. Try: good, bad, big, happy, smart, etc."}


class StatisticsTool(BaseTool):
    def execute(self, params):
        data_str = params.get("data", params.get("numbers", ""))
        if not data_str:
            return {"success": False, "result": "Provide comma-separated numbers"}
        try:
            nums = [float(x.strip()) for x in data_str.split(",") if x.strip()]
        except ValueError:
            return {"success": False, "result": "All values must be numbers"}
        if len(nums) < 2:
            return {"success": False, "result": "Need at least 2 numbers"}
        n = len(nums)
        s = sum(nums)
        mean = s / n
        sorted_nums = sorted(nums)
        median = sorted_nums[n // 2] if n % 2 else (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
        freq = {}
        for x in nums:
            freq[x] = freq.get(x, 0) + 1
        max_freq = max(freq.values())
        mode = [str(k) for k, v in freq.items() if v == max_freq]
        variance = sum((x - mean) ** 2 for x in nums) / n
        std_dev = math.sqrt(variance)
        result = (
            f"Count: {n}\n"
            f"Sum: {s}\n"
            f"Mean: {mean:.4f}\n"
            f"Median: {median:.4f}\n"
            f"Mode: {', '.join(mode)} (freq: {max_freq})\n"
            f"Min: {min(nums)}\n"
            f"Max: {max(nums)}\n"
            f"Range: {max(nums) - min(nums)}\n"
            f"Variance: {variance:.4f}\n"
            f"Std Dev: {std_dev:.4f}"
        )
        return {"success": True, "result": result}


class PrimeTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "check")
        try:
            if action == "check":
                n = int(params.get("number", params.get("n", 0)))
                if n < 2:
                    return {"success": True, "result": f"{n} is not prime"}
                for i in range(2, int(math.isqrt(n)) + 1):
                    if n % i == 0:
                        return {"success": True, "result": f"{n} is not prime (divisible by {i})"}
                return {"success": True, "result": f"{n} is prime!"}
            elif action == "factors":
                n = int(params.get("number", params.get("n", 0)))
                if n < 2:
                    return {"success": True, "result": f"{n}: no prime factors"}
                temp = n
                factors = []
                for i in range(2, int(math.isqrt(n)) + 1):
                    while temp % i == 0:
                        factors.append(i)
                        temp //= i
                if temp > 1:
                    factors.append(temp)
                return {"success": True, "result": f"Factors of {n}: {' × '.join(map(str, factors))}"}
            elif action == "list":
                limit = int(params.get("limit", params.get("max", 100)))
                sieve = [True] * (limit + 1)
                sieve[0] = sieve[1] = False
                for i in range(2, int(math.isqrt(limit)) + 1):
                    if sieve[i]:
                        for j in range(i * i, limit + 1, i):
                            sieve[j] = False
                primes = [str(i) for i, is_p in enumerate(sieve) if is_p]
                return {"success": True, "result": f"Primes up to {limit} ({len(primes)}):\n{', '.join(primes[:50])}" + ("..." if len(primes) > 50 else "")}
            elif action == "next":
                n = int(params.get("number", params.get("n", 0)))
                candidate = n + 1
                while True:
                    is_p = candidate >= 2
                    for i in range(2, int(math.isqrt(candidate)) + 1):
                        if candidate % i == 0:
                            is_p = False
                            break
                    if is_p:
                        return {"success": True, "result": f"Next prime after {n}: {candidate}"}
                    candidate += 1
            return {"success": False, "result": "Actions: check, factors, list, next"}
        except ValueError:
            return {"success": False, "result": "Provide a valid number"}


class MatrixTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "add")
        try:
            a_str = params.get("a", params.get("matrix_a", ""))
            b_str = params.get("b", params.get("matrix_b", ""))
            if not a_str:
                return {"success": False, "result": "Provide matrix_a (rows; separated by |, values comma-separated)"}
            def parse(m):
                rows = m.split("|")
                return [[float(x.strip()) for x in row.split(",") if x.strip()] for row in rows if row.strip()]
            a = parse(a_str)
            if action == "add":
                b = parse(b_str)
                if len(a) != len(b) or len(a[0]) != len(b[0]):
                    return {"success": False, "result": "Matrices must have same dimensions"}
                result = [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]
            elif action == "multiply":
                b = parse(b_str)
                if len(a[0]) != len(b):
                    return {"success": False, "result": f"Cannot multiply {len(a)}x{len(a[0])} by {len(b)}x{len(b[0])}"}
                result = [[sum(a[i][k] * b[k][j] for k in range(len(a[0]))) for j in range(len(b[0]))] for i in range(len(a))]
            elif action == "determinant":
                if len(a) != len(a[0]):
                    return {"success": False, "result": "Matrix must be square"}
                result = [[self._det(a)]]
            elif action == "transpose":
                result = [[a[j][i] for j in range(len(a))] for i in range(len(a[0]))]
            else:
                return {"success": False, "result": "Actions: add, multiply, determinant, transpose"}
            lines = [f"Result ({len(result)}x{len(result[0])}):"]
            for row in result:
                lines.append("  [" + ", ".join(f"{v:.2f}" for v in row) + "]")
            return {"success": True, "result": "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"Matrix error: {e}"}

    def _det(self, m):
        if len(m) == 1:
            return m[0][0]
        if len(m) == 2:
            return m[0][0] * m[1][1] - m[0][1] * m[1][0]
        d = 0
        for c in range(len(m)):
            sub = [[m[r][cc] for cc in range(len(m)) if cc != c] for r in range(1, len(m))]
            d += ((-1) ** c) * m[0][c] * self._det(sub)
        return d


class PeriodicTableTool(BaseTool):
    _ELEMENTS = [
        ("H", "Hydrogen", 1, 1.008, "Nonmetal"), ("He", "Helium", 2, 4.003, "Noble Gas"),
        ("Li", "Lithium", 3, 6.941, "Alkali Metal"), ("Be", "Beryllium", 4, 9.012, "Alkaline Earth"),
        ("B", "Boron", 5, 10.811, "Metalloid"), ("C", "Carbon", 6, 12.011, "Nonmetal"),
        ("N", "Nitrogen", 7, 14.007, "Nonmetal"), ("O", "Oxygen", 8, 15.999, "Nonmetal"),
        ("F", "Fluorine", 9, 18.998, "Halogen"), ("Ne", "Neon", 10, 20.180, "Noble Gas"),
        ("Na", "Sodium", 11, 22.990, "Alkali Metal"), ("Mg", "Magnesium", 12, 24.305, "Alkaline Earth"),
        ("Al", "Aluminum", 13, 26.982, "Metal"), ("Si", "Silicon", 14, 28.086, "Metalloid"),
        ("P", "Phosphorus", 15, 30.974, "Nonmetal"), ("S", "Sulfur", 16, 32.065, "Nonmetal"),
        ("Cl", "Chlorine", 17, 35.453, "Halogen"), ("Ar", "Argon", 18, 39.948, "Noble Gas"),
        ("K", "Potassium", 19, 39.098, "Alkali Metal"), ("Ca", "Calcium", 20, 40.078, "Alkaline Earth"),
        ("Fe", "Iron", 26, 55.845, "Transition Metal"), ("Cu", "Copper", 29, 63.546, "Transition Metal"),
        ("Zn", "Zinc", 30, 65.380, "Transition Metal"), ("Ag", "Silver", 47, 107.868, "Transition Metal"),
        ("Au", "Gold", 79, 196.967, "Transition Metal"), ("Hg", "Mercury", 80, 200.590, "Transition Metal"),
        ("Pb", "Lead", 82, 207.200, "Metal"), ("U", "Uranium", 92, 238.029, "Actinide"),
    ]
    _DICT = {e[0].lower(): e for e in _ELEMENTS}
    _DICT.update({e[1].lower(): e for e in _ELEMENTS})
    _DICT.update({str(e[2]): e for e in _ELEMENTS})

    def execute(self, params):
        query = params.get("element", params.get("query", "")).strip().lower()
        if not query:
            lines = ["Periodic Table — Quick Reference:", ""]
            for sym, name, num, mass, cat in self._ELEMENTS:
                lines.append(f"  {num:3d} {sym:3s} {name:12s} {mass:7.3f}  {cat}")
            return {"success": True, "result": "\n".join(lines)}
        entry = self._DICT.get(query)
        if not entry:
            return {"success": False, "result": f"Element not found. Try: H, Helium, 6, etc."}
        sym, name, num, mass, cat = entry
        return {"success": True, "result":
                f"Element: {name} ({sym})\n"
                f"Atomic Number: {num}\n"
                f"Atomic Mass: {mass:.3f} u\n"
                f"Category: {cat}"}


class PhysicsRefTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", params.get("query", "")).strip().lower()
        formulas = {
            "kinematics": {
                "desc": "Motion equations",
                "formulas": [
                    "v = u + at",
                    "s = ut + ½at²",
                    "v² = u² + 2as",
                    "s = ½(u + v)t",
                ]
            },
            "newton": {
                "desc": "Newton's Laws",
                "formulas": [
                    "F = ma (2nd Law)",
                    "F = G·m₁·m₂ / r² (Gravity)",
                    "Weight = mg",
                    "Friction = μN",
                ]
            },
            "energy": {
                "desc": "Energy & Work",
                "formulas": [
                    "KE = ½mv²",
                    "PE = mgh",
                    "Work = F·d·cosθ",
                    "Power = W / t",
                ]
            },
            "electricity": {
                "desc": "Electricity",
                "formulas": [
                    "V = IR (Ohm's Law)",
                    "P = VI",
                    "E = V·I·t",
                    "R = ρL / A",
                    "C = Q / V",
                ]
            },
            "waves": {
                "desc": "Waves & Optics",
                "formulas": [
                    "v = fλ",
                    "n₁·sinθ₁ = n₂·sinθ₂ (Snell's Law)",
                    "1/f = 1/v + 1/u (Lens)",
                    "E = hf (Photon)",
                ]
            },
            "thermodynamics": {
                "desc": "Thermodynamics",
                "formulas": [
                    "Q = mcΔT (Heat)",
                    "PV = nRT (Ideal Gas)",
                    "ΔU = Q - W (1st Law)",
                    "e = 1 - T_c/T_h (Carnot)",
                ]
            },
        }
        if not topic:
            lines = ["Physics Formulas — Topics:"]
            for k, v in formulas.items():
                lines.append(f"  • {k}: {v['desc']}")
            return {"success": True, "result": "\n".join(lines)}
        topic_key = None
        for k in formulas:
            if topic in k or k in topic:
                topic_key = k
                break
        if not topic_key:
            return {"success": True, "result": f"Topics: {', '.join(formulas.keys())}"}
        entry = formulas[topic_key]
        lines = [f"{entry['desc'].upper()}:", ""]
        lines.extend(entry["formulas"])
        return {"success": True, "result": "\n".join(lines)}


class FormulaTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", params.get("query", "")).strip().lower()
        formulas = {
            "area": {
                "desc": "Area formulas",
                "entries": [
                    ("Circle", "A = πr²"),
                    ("Triangle", "A = ½bh"),
                    ("Rectangle", "A = lw"),
                    ("Trapezoid", "A = ½(a+b)h"),
                    ("Sphere surface", "A = 4πr²"),
                ]
            },
            "volume": {
                "desc": "Volume formulas",
                "entries": [
                    ("Cube", "V = s³"),
                    ("Sphere", "V = ⁴⁄₃πr³"),
                    ("Cylinder", "V = πr²h"),
                    ("Cone", "V = ⅓πr²h"),
                    ("Pyramid", "V = ⅓Bh"),
                ]
            },
            "geometry": {
                "desc": "Geometry",
                "entries": [
                    ("Pythagorean", "a² + b² = c²"),
                    ("Circumference", "C = 2πr"),
                    ("Distance", "d = √((x₂-x₁)² + (y₂-y₁)²)"),
                    ("Midpoint", "M = ((x₁+x₂)/2, (y₁+y₂)/2)"),
                ]
            },
            "trigonometry": {
                "desc": "Trigonometry",
                "entries": [
                    ("sin θ = opposite/hypotenuse", "sin²θ + cos²θ = 1"),
                    ("cos θ = adjacent/hypotenuse", "tan θ = sinθ/cosθ"),
                    ("Law of Sines", "a/sinA = b/sinB = c/sinC"),
                    ("Law of Cosines", "c² = a² + b² - 2ab·cosC"),
                ]
            },
            "calculus": {
                "desc": "Calculus",
                "entries": [
                    ("Derivative", "d/dx xⁿ = nxⁿ⁻¹"),
                    ("Power rule", "∫xⁿ dx = xⁿ⁺¹/(n+1) + C"),
                    ("Product rule", "(fg)' = f'g + fg'"),
                    ("Chain rule", "f(g(x))' = f'(g(x))·g'(x)"),
                ]
            },
            "algebra": {
                "desc": "Algebra",
                "entries": [
                    ("Quadratic formula", "x = (-b ± √(b²-4ac)) / 2a"),
                    ("Slope", "m = (y₂-y₁)/(x₂-x₁)"),
                    ("Logarithm", "log_b(x) = y → bʸ = x"),
                    ("Binomial", "(a+b)ⁿ = Σ(k=0..n) C(n,k)aⁿ⁻ᵏbᵏ"),
                ]
            },
        }
        if not topic:
            lines = ["Math Formulas — Topics:"]
            for k, v in formulas.items():
                lines.append(f"  • {k}: {v['desc']}")
            return {"success": True, "result": "\n".join(lines)}
        topic_key = None
        for k in formulas:
            if topic in k or k in topic:
                topic_key = k
                break
        if not topic_key:
            return {"success": True, "result": f"Topics: {', '.join(formulas.keys())}"}
        entry = formulas[topic_key]
        lines = [f"{entry['desc'].upper()}:", ""]
        for name, formula in entry["entries"]:
            lines.append(f"  {name}: {formula}")
        return {"success": True, "result": "\n".join(lines)}


class DOILookupTool(BaseTool):
    def execute(self, params):
        doi = params.get("doi", params.get("id", "")).strip()
        if not doi:
            return {"success": False, "result": "Provide a DOI (e.g., 10.1038/nature12373)"}
        try:
            url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            msg = data.get("message", {})
            title = msg.get("title", ["Unknown"])[0]
            authors = msg.get("author", [])
            author_names = [f"{a.get('given','')} {a.get('family','')}".strip() for a in authors[:5]]
            year = (msg.get("published-print") or msg.get("published-online") or {}).get("date-parts", [[""]])[0][0]
            journal = msg.get("container-title", [""])[0]
            publisher = msg.get("publisher", "")
            lines = [f"DOI: {doi}", f"Title: {title}"]
            if author_names:
                lines.append(f"Authors: {', '.join(author_names)}{'…' if len(authors) > 5 else ''}")
            if year:
                lines.append(f"Year: {year}")
            if journal:
                lines.append(f"Journal: {journal}")
            if publisher:
                lines.append(f"Publisher: {publisher}")
            return {"success": True, "result": "\n".join(lines)}
        except urllib.error.HTTPError as e:
            return {"success": False, "result": f"DOI not found (HTTP {e.code})"}
        except Exception as e:
            return {"success": False, "result": f"DOI lookup error: {e}"}


class ArxivTool(BaseTool):
    def execute(self, params):
        query = params.get("query", params.get("search", ""))
        count = min(int(params.get("count", params.get("max_results", 5))), 20)
        if not query:
            return {"success": False, "result": "Provide a search query"}
        try:
            url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&max_results={count}&sortBy=relevance"
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = resp.read().decode()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(data)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            entries = root.findall("a:entry", ns)
            if not entries:
                return {"success": True, "result": "No results found"}
            lines = [f"arXiv results for '{query}':"]
            for entry in entries[:count]:
                title = entry.find("a:title", ns).text.strip().replace("\n", " ")
                authors = [a.find("a:name", ns).text for a in entry.findall("a:author", ns)][:3]
                link = entry.find("a:id", ns).text
                published = entry.find("a:published", ns).text[:10]
                lines.append(f"\n• {title}")
                lines.append(f"  Authors: {', '.join(authors)}{'…' if len(authors) > 3 else ''}")
                lines.append(f"  {published} | {link}")
            return {"success": True, "result": "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"Arxiv error: {e}"}


class VocabTool(BaseTool):
    _WORDS = [
        ("ephemeral", "lasting for a very short time", "The ephemeral beauty of cherry blossoms"),
        ("ubiquitous", "present everywhere at once", "Smartphones have become ubiquitous"),
        ("pragmatic", "dealing with things practically", "A pragmatic approach to problem-solving"),
        ("ambiguous", "open to multiple interpretations", "The ambiguous wording confused everyone"),
        ("paradigm", "a typical example or pattern", "A shift in the scientific paradigm"),
        ("eloquent", "fluent and persuasive in speaking", "An eloquent speech moved the audience"),
        ("resilient", "able to recover quickly", "The resilient community rebuilt after the storm"),
        ("meticulous", "showing great attention to detail", "Her meticulous research was praised"),
        ("candid", "truthful and straightforward", "A candid conversation about the issues"),
        ("profound", "very great or intense", "A profound insight changed my perspective"),
        ("innovative", "introducing new ideas", "The innovative design won awards"),
        ("diligent", "careful and persistent effort", "A diligent student always does their best"),
        ("empirical", "based on observation or experience", "Empirical evidence supports the theory"),
        ("abstract", "existing in thought rather than matter", "Abstract concepts can be hard to grasp"),
        ("collaborate", "work jointly on an activity", "Teams collaborate on complex projects"),
    ]

    def execute(self, params):
        action = params.get("action", "random")
        if action == "random":
            word, meaning, example = random.choice(self._WORDS)
            return {"success": True, "result": f"📖 {word}\n  Definition: {meaning}\n  Example: \"{example}\""}
        elif action == "list":
            lines = ["Vocabulary Builder:"]
            for word, meaning, _ in self._WORDS:
                lines.append(f"  • {word}: {meaning}")
            return {"success": True, "result": "\n".join(lines)}
        elif action == "search":
            q = params.get("word", "").strip().lower()
            for word, meaning, example in self._WORDS:
                if q == word.lower():
                    return {"success": True, "result": f"📖 {word}\n  Definition: {meaning}\n  Example: \"{example}\""}
            return {"success": False, "result": f"Word '{q}' not in vocabulary. Try: random, list"}
        return {"success": False, "result": "Actions: random, list, search"}


class MnemonicTool(BaseTool):
    PATTERNS = {
        "acronym": lambda words: "".join(w[0].upper() for w in words if w),
        "sentence": lambda words: " ".join(w if random.random() > 0.5 else w.upper() for w in words),
        "rhyme": lambda words: f"{' '.join(words[:2])} is what you need, {words[-1] if len(words) > 2 else ''} is the key!",
    }

    def execute(self, params):
        items_str = params.get("items", params.get("words", ""))
        pattern = params.get("pattern", "acronym")
        if not items_str:
            return {"success": False, "result": "Provide items to memorize (comma-separated)"}
        words = [w.strip() for w in items_str.split(",") if w.strip()]
        if len(words) < 2:
            return {"success": False, "result": "Need at least 2 items"}
        if pattern == "acronym":
            acro = "".join(w[0].upper() for w in words)
            result = f"Acronym: {acro}\n  ({', '.join(words)})"
        elif pattern == "sentence":
            random.shuffle(words)
            result = f"Sentence: {' '.join(w if random.random() > 0.4 else w.upper() for w in words)}"
        elif pattern == "story":
            story = f"Imagine you are walking through a {words[0].lower()}..."
            for w in words[1:]:
                story += f" Suddenly, a {w.lower()} appears!"
            result = f"Story: {story}"
        else:
            return {"success": False, "result": "Patterns: acronym, sentence, story"}
        return {"success": True, "result": f"Mnemonic ({pattern}):\n{result}"}


class NoteSummarizeTool(BaseTool):
    def execute(self, params):
        text = params.get("text", params.get("notes", ""))
        if not text:
            return {"success": False, "result": "Provide text to summarize"}
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= 2:
            return {"success": True, "result": f"Summary: {text[:500]}"}
        words = text.split()
        total_words = len(words)
        target = max(1, total_words // 3)
        # Simple extractive summarization: take first sentence, then pick most informative
        summary_sentences = [sentences[0]]
        available = sentences[1:]
        available.sort(key=lambda s: len(s.split()), reverse=True)
        current_len = len(summary_sentences[0].split())
        for s in available:
            if current_len >= target:
                break
            summary_sentences.append(s)
            current_len += len(s.split())
        lines = [
            f"Original: {total_words} words, {len(sentences)} sentences",
            f"Summary: {len(summary_sentences)} sentences, {current_len} words",
            "",
            "Key Points:",
        ]
        for i, s in enumerate(summary_sentences, 1):
            lines.append(f"  {i}. {s}")
        return {"success": True, "result": "\n".join(lines)}


class ConjugationTool(BaseTool):
    _CONJ = {
        "run": {"base": "run", "past": "ran", "pp": "run", "ing": "running", "s": "runs"},
        "write": {"base": "write", "past": "wrote", "pp": "written", "ing": "writing", "s": "writes"},
        "speak": {"base": "speak", "past": "spoke", "pp": "spoken", "ing": "speaking", "s": "speaks"},
        "eat": {"base": "eat", "past": "ate", "pp": "eaten", "ing": "eating", "s": "eats"},
        "drink": {"base": "drink", "past": "drank", "pp": "drunk", "ing": "drinking", "s": "drinks"},
        "go": {"base": "go", "past": "went", "pp": "gone", "ing": "going", "s": "goes"},
        "be": {"base": "be", "past": "was/were", "pp": "been", "ing": "being", "s": "is"},
        "have": {"base": "have", "past": "had", "pp": "had", "ing": "having", "s": "has"},
        "make": {"base": "make", "past": "made", "pp": "made", "ing": "making", "s": "makes"},
        "take": {"base": "take", "past": "took", "pp": "taken", "ing": "taking", "s": "takes"},
        "see": {"base": "see", "past": "saw", "pp": "seen", "ing": "seeing", "s": "sees"},
        "know": {"base": "know", "past": "knew", "pp": "known", "ing": "knowing", "s": "knows"},
        "think": {"base": "think", "past": "thought", "pp": "thought", "ing": "thinking", "s": "thinks"},
        "give": {"base": "give", "past": "gave", "pp": "given", "ing": "giving", "s": "gives"},
        "find": {"base": "find", "past": "found", "pp": "found", "ing": "finding", "s": "finds"},
        "tell": {"base": "tell", "past": "told", "pp": "told", "ing": "telling", "s": "tells"},
        "read": {"base": "read", "past": "read", "pp": "read", "ing": "reading", "s": "reads"},
        "teach": {"base": "teach", "past": "taught", "pp": "taught", "ing": "teaching", "s": "teaches"},
        "learn": {"base": "learn", "past": "learned", "pp": "learned", "ing": "learning", "s": "learns"},
        "study": {"base": "study", "past": "studied", "pp": "studied", "ing": "studying", "s": "studies"},
    }

    def execute(self, params):
        verb = params.get("verb", params.get("word", "")).strip().lower()
        tense = params.get("tense", params.get("action", "all"))
        if not verb:
            return {"success": True, "result":
                    f"Verb Conjugation (irregular verbs):\n{', '.join(sorted(self._CONJ.keys()))}\n\nRegular verbs: add -ed for past, -ing for continuous"}
        if verb in self._CONJ:
            v = self._CONJ[verb]
            if tense == "past":
                return {"success": True, "result": f"Past tense of '{verb}': {v['past']}"}
            elif tense == "present":
                return {"success": True, "result": f"Present tense of '{verb}': {v['base']} / {v['s']}"}
            elif tense == "continuous":
                return {"success": True, "result": f"Continuous of '{verb}': {v['ing']}"}
            lines = [f"Conjugation: {verb}", "",
                     f"Base: {v['base']}", f"Past: {v['past']}", f"Past Participle: {v['pp']}",
                     f"Continuous: {v['ing']}", f"Third Person: {v['s']}"]
            return {"success": True, "result": "\n".join(lines)}
        # Regular verb
        if verb.endswith("e"):
            past = verb + "d"
        elif verb.endswith("y") and len(verb) > 2 and verb[-2] not in "aeiou":
            past = verb[:-1] + "ied"
        else:
            past = verb + "ed"
        ing = verb + ("ing" if not verb.endswith("e") else verb[:-1] + "ing")
        s = verb + ("s" if not verb.endswith(("s", "x", "ch", "sh", "o")) else verb + "es")
        lines = [f"Conjugation: {verb}", "", f"Base: {verb}", f"Past: {past}",
                 f"Past Participle: {past}", f"Continuous: {ing}", f"Third Person: {s}"]
        return {"success": True, "result": "\n".join(lines)}


class SpellCheckTool(BaseTool):
    def execute(self, params):
        text = params.get("text", "").strip()
        if not text:
            return {"success": False, "result": "Provide text to check"}
        common_words = {
            "accomodate": "accommodate", "recieve": "receive", "wierd": "weird",
            "seperate": "separate", "occured": "occurred", "occurance": "occurrence",
            "definately": "definitely", "tommorrow": "tomorrow", "calender": "calendar",
            "neccessary": "necessary", "embarass": "embarrass", "goverment": "government",
            "alot": "a lot", "untill": "until", "wierd": "weird", "beleive": "believe",
            "acheive": "achieve", "adress": "address", "begining": "beginning",
            "commitee": "committee", "concensus": "consensus", "concious": "conscious",
            "contagious": "contagious", "decieve": "deceive", "desparate": "desperate",
            "dilemna": "dilemma", "disappear": "disappear", "embarass": "embarrass",
            "enviornment": "environment", "exagerate": "exaggerate", "febuary": "february",
            "foriegn": "foreign", "fourty": "forty", "freind": "friend",
            "guarantee": "guarantee", "harrass": "harass", "hierarchy": "hierarchy",
            "humour": "humor", "independant": "independent", "interrupt": "interrupt",
            "jewelery": "jewelry", "judgment": "judgment", "liason": "liaison",
            "libary": "library", "licence": "license", "maintainance": "maintenance",
            "millenium": "millennium", "miniscule": "minuscule", "mischievious": "mischievous",
            "misspell": "misspell", "morgage": "mortgage", "nineth": "ninth",
            "noticable": "noticeable", "occassion": "occasion", "occurence": "occurrence",
            "pavillion": "pavilion", "persistant": "persistent", "pharoah": "pharaoh",
            "playright": "playwright", "posession": "possession", "preceed": "precede",
            "privilege": "privilege", "priviledge": "privilege", "procede": "proceed",
            "pronounciation": "pronunciation", "publicly": "publicly", "pumpkim": "pumpkin",
            "questionaire": "questionnaire", "reccomend": "recommend", "refered": "referred",
            "refering": "referring", "religous": "religious", "remeber": "remember",
            "resistence": "resistance", "restaraunt": "restaurant", "rehersal": "rehearsal",
            "sargeant": "sergeant", "seige": "siege", "similiar": "similar",
            "skilful": "skillful", "somwhere": "somewhere", "sophmore": "sophomore",
            "specificaly": "specifically", "sponser": "sponsor", "stomach": "stomach",
            "supercede": "supersede", "surelly": "surely", "surprize": "surprise",
            "tatoo": "tattoo", "threshhold": "threshold", "tommorow": "tomorrow",
            "tounge": "tongue", "truely": "truly", "twelth": "twelfth", "tyrany": "tyranny",
            "vaccuum": "vacuum", "vegitable": "vegetable", "vehical": "vehicle",
            "visable": "visible", "wednesday": "wednesday", "wether": "weather",
            "wich": "which", "writen": "written", "wierd": "weird", "zealous": "zealous",
        }
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        suggestions = []
        for w in words:
            lower = w.lower()
            if lower in common_words and common_words[lower] != lower:
                suggestions.append(f"  '{w}' → '{common_words[lower]}'")
        if suggestions:
            return {"success": True, "result": "Spelling suggestions:\n" + "\n".join(suggestions)}
        return {"success": True, "result": "No common spelling errors found. ✓"}


class GroupPickerTool(BaseTool):
    def execute(self, params):
        names_str = params.get("names", params.get("students", ""))
        group_count = max(1, int(params.get("groups", params.get("count", 0))))
        per_group = max(1, int(params.get("per_group", 0)))
        if not names_str:
            return {"success": False, "result": "Provide comma-separated student names"}
        names = [n.strip() for n in names_str.split(",") if n.strip()]
        if len(names) < 2:
            return {"success": False, "result": "Need at least 2 students"}
        random.shuffle(names)
        if group_count > 0:
            groups = [[] for _ in range(group_count)]
            for i, name in enumerate(names):
                groups[i % group_count].append(name)
        elif per_group > 0:
            groups = [names[i:i+per_group] for i in range(0, len(names), per_group)]
        else:
            return {"success": False, "result": "Provide groups= or per_group="}
        lines = [f"Groups ({len(names)} students):"]
        for i, g in enumerate(groups, 1):
            lines.append(f"\nGroup {i} ({len(g)} members):")
            for name in g:
                lines.append(f"  • {name}")
        return {"success": True, "result": "\n".join(lines)}


class RubricTool(BaseTool):
    def execute(self, params):
        assignment = params.get("assignment", params.get("title", "Assignment"))
        criteria_str = params.get("criteria", params.get("items", ""))
        levels = int(params.get("levels", 4))
        if not criteria_str:
            return {"success": False, "result": "Provide comma-separated criteria (e.g., Content, Clarity, Research)"}
        criteria = [c.strip() for c in criteria_str.split(",") if c.strip()]
        level_names = {4: ["Below", "Developing", "Proficient", "Exemplary"],
                       3: ["Developing", "Proficient", "Exemplary"],
                       5: ["Beginning", "Developing", "Proficient", "Advanced", "Exemplary"]}
        level_labels = level_names.get(levels, level_names[4])
        max_score = levels
        lines = [f"Grading Rubric: {assignment}", "=" * 40, f"Scale: {levels} levels (1-{levels})", ""]
        for c in criteria:
            lines.append(f"\n{c} (Weight: {100 // len(criteria)}%):")
            for i, lbl in enumerate(level_labels, 1):
                lines.append(f"  {i} - {lbl}: {random.choice([
                    f"Minimal {c.lower()}",
                    f"Basic {c.lower()}",
                    f"Good {c.lower()}",
                    f"Excellent {c.lower()}",
                    f"Outstanding {c.lower()}",
                ][:levels - i + 1])}")
        lines.append(f"\nTotal possible: {len(criteria)} × {max_score} = {len(criteria) * max_score} pts")
        return {"success": True, "result": "\n".join(lines)}


class SyllabusTool(BaseTool):
    def execute(self, params):
        course = params.get("course", params.get("title", "Course"))
        weeks = min(int(params.get("weeks", params.get("duration", 16))), 20)
        topics_str = params.get("topics", "")
        topics = [t.strip() for t in topics_str.split(",") if t.strip()] if topics_str else []
        lines = [f"Syllabus: {course}", "=" * 40, f"Duration: {weeks} weeks", ""]
        lines.append("Required Materials:")
        lines.append("  • Textbook (TBD)")
        lines.append("  • Notebook and writing materials")
        lines.append("  • Access to course website")
        lines.append("\nGrading Breakdown:")
        lines.append("  • Participation: 10%")
        lines.append("  • Homework/Assignments: 30%")
        lines.append("  • Midterm Exam: 25%")
        lines.append("  • Final Exam/Project: 35%")
        lines.append("\nCourse Schedule:")
        for w in range(1, weeks + 1):
            topic = topics[w - 1] if w <= len(topics) else f"Topic {w}"
            lines.append(f"\nWeek {w}: {topic}")
            lines.append(f"  • Reading assignment")
            lines.append(f"  • {random.choice(['Homework due', 'Quiz', 'Lab exercise', 'Discussion post'])}")
        lines.append("\nPolicies:")
        lines.append("  • Late work: 10% penalty per day")
        lines.append("  • Academic integrity: All work must be your own")
        return {"success": True, "result": "\n".join(lines)}


class PracticeProblemTool(BaseTool):
    def execute(self, params):
        subject = params.get("subject", params.get("topic", "math")).lower()
        count = min(int(params.get("count", 3)), 10)
        difficulty = params.get("difficulty", "medium")
        problems = []
        if "math" in subject or "algebra" in subject:
            for i in range(count):
                a, b = random.randint(2, 12), random.randint(2, 12)
                ops = [("+", a + b), ("-", max(a, b) - min(a, b)),
                       ("×", a * b)]
                if difficulty == "hard":
                    ops.append(("÷", a * b // max(b, 1) if a * b % max(b, 1) == 0 else "fraction"))
                op, ans = random.choice(ops)
                problems.append(f"{i+1}. {max(a,b)} {op} {min(a,b)} = ?  [Answer: {ans}]")
        elif "physics" in subject:
            for i in range(count):
                m, a_num = random.randint(2, 20), random.randint(1, 10)
                problems.append(f"{i+1}. F = ma: mass={m}kg, a={a_num}m/s², F=?  [Answer: {m*a_num}N]")
        elif "chem" in subject:
            for i in range(count):
                problems.append(f"{i+1}. Balance: H₂ + O₂ → H₂O  [Answer: 2H₂ + O₂ → 2H₂O]")
        else:
            for i in range(count):
                problems.append(f"{i+1}. Describe a key concept in {subject}.")
        return {"success": True, "result": f"Practice Problems ({subject}, {difficulty}):\n" + "\n".join(problems)}


class ScienceFactTool(BaseTool):
    _FACTS = [
        "Water expands when it freezes, which is why ice floats.",
        "Light travels at about 299,792,458 m/s in a vacuum.",
        "The human body contains about 60% water.",
        "DNA was first discovered in 1869 by Friedrich Miescher.",
        "The speed of sound is about 343 m/s at sea level.",
        "A single lightning bolt contains enough energy to toast 100,000 slices of bread.",
        "Honey never spoils — archaeologists found 3000-year-old edible honey in Egyptian tombs.",
        "Octopuses have three hearts and blue blood.",
        "Bananas are technically berries, but strawberries aren't.",
        "The periodic table has 118 confirmed elements.",
        "Sound travels 4.3× faster in water than in air.",
        "A day on Venus is longer than its year.",
        "The human brain generates enough electricity to power a small LED.",
        "There are more trees on Earth than stars in the Milky Way (~3 trillion).",
        "The Great Red Spot on Jupiter is a storm larger than Earth.",
        "Oxygen makes up about 21% of Earth's atmosphere.",
        "A bolt of lightning is 5× hotter than the surface of the sun.",
        "The Earth's core is about as hot as the sun's surface (~5500°C).",
        "Fingernails grow about 3.5 mm per month.",
        "The heart beats about 100,000 times per day.",
    ]

    def execute(self, params):
        action = params.get("action", "random")
        topic = params.get("topic", "").strip().lower()
        if action == "random":
            return {"success": True, "result": f"🔬 {random.choice(self._FACTS)}"}
        elif action == "list":
            lines = [f"Science Facts ({len(self._FACTS)}):"]
            for i, f in enumerate(self._FACTS, 1):
                lines.append(f"{i}. {f}")
            return {"success": True, "result": "\n".join(lines)}
        elif action == "search":
            results = [f for f in self._FACTS if topic in f.lower()]
            if results:
                return {"success": True, "result": "🔬 " + results[0]}
            return {"success": False, "result": "No matching facts"}
        return {"success": False, "result": "Actions: random, list, search"}


class StudyPlanTool(BaseTool):
    def execute(self, params):
        subject = params.get("subject", params.get("topic", "a subject"))
        days = min(int(params.get("days", 7)), 30)
        hours = min(float(params.get("hours", params.get("per_day", 2))), 12)
        lines = [f"Study Plan: {subject.title()}", f"Duration: {days} days, {hours}h/day",
                 "=" * 40, "Tips:", "  • Review material within 24 hours of learning",
                 "  • Use active recall (quiz yourself, don't just re-read)",
                 "  • Space repetitions across multiple days",
                 "  • Take a 5-min break every 25 minutes", ""]
        topics = [f"Introduction to {subject}", f"Core Concepts of {subject}",
                  f"Intermediate {subject} Topics", f"Advanced {subject} Concepts",
                  f"Practical Applications", f"Review & Practice", f"Assessment"]
        for day in range(1, days + 1):
            topic = topics[(day - 1) % len(topics)]
            r = random.random()
            if r < 0.4:
                activity = f"Study: {topic}"
            elif r < 0.7:
                activity = f"Practice problems on {topic}"
            elif r < 0.85:
                activity = f"Review previous material ({random.choice(topics[:max(day-1,1)])})"
            else:
                activity = "Take a practice quiz"
            lines.append(f"Day {day:2d}: {activity} ({hours:.1f}h)")
        return {"success": True, "result": "\n".join(lines)}


class NoteOrganizerTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "add")
        path = os.path.join(_STUDY_DIR, "notebook.json")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    notebook = json.load(f)
            else:
                notebook = {"subjects": {}, "notes": []}
            if action == "add":
                subject = params.get("subject", params.get("class", "General")).strip()
                title = params.get("title", "Untitled").strip()
                content_note = params.get("content", params.get("notes", "")).strip()
                tags_str = params.get("tags", "")
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                if not content_note:
                    return {"success": False, "result": "Provide note content"}
                note = {
                    "id": str(time.time()),
                    "subject": subject,
                    "title": title,
                    "content": content_note[:2000],
                    "tags": tags,
                    "created": time.time(),
                }
                notebook["notes"].append(note)
                if subject not in notebook["subjects"]:
                    notebook["subjects"][subject] = {"count": 0, "created": time.time()}
                notebook["subjects"][subject]["count"] += 1
                with open(path, "w") as f:
                    json.dump(notebook, f)
                return {"success": True, "result": f"Note added: {title} ({subject})"}
            elif action == "list":
                subject = params.get("subject", "")
                pool = [n for n in notebook["notes"] if not subject or n.get("subject") == subject]
                if not pool:
                    return {"success": True, "result": "No notes found"}
                lines = [f"Notes ({len(pool)}):"]
                for n in sorted(pool, key=lambda x: x.get("created", 0), reverse=True)[:20]:
                    lines.append(f"  • [{n.get('subject','General')}] {n.get('title','Untitled')}")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "search":
                query = params.get("query", "").strip().lower()
                if not query:
                    return {"success": False, "result": "Provide a search query"}
                matches = [n for n in notebook["notes"] if query in n.get("content", "").lower()
                           or query in n.get("title", "").lower()
                           or query in n.get("subject", "").lower()]
                if not matches:
                    return {"success": True, "result": "No matches"}
                lines = [f"Found {len(matches)} notes:"]
                for n in matches[:10]:
                    lines.append(f"  • [{n.get('subject','General')}] {n.get('title','Untitled')}")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "subjects":
                lines = [f"Subjects ({len(notebook['subjects'])}):"]
                for s, d in sorted(notebook["subjects"].items()):
                    lines.append(f"  • {s} ({d['count']} notes)")
                return {"success": True, "result": "\n".join(lines)}
            return {"success": False, "result": "Actions: add, list, search, subjects"}
        except Exception as e:
            return {"success": False, "result": f"Note error: {e}"}


class LessonPlanTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "a lesson").strip()
        duration = params.get("duration", params.get("minutes", 45))
        grade = params.get("grade", params.get("level", "high school"))
        lines = [
            f"Lesson Plan: {topic}", "=" * 40,
            f"Grade Level: {grade} | Duration: {duration} min",
            "",
            "Learning Objectives:",
            f"  • Understand key concepts of {topic}",
            f"  • Apply {topic} knowledge to practical examples",
            "  • Demonstrate comprehension through assessment",
            "",
            "Materials Needed:",
            "  • Whiteboard / projector",
            "  • Handouts / worksheets",
            "  • Student notebooks",
            "",
            "Lesson Structure:",
            f"  1. Hook/Introduction (5 min) — Grab attention with a question about {topic}",
            "  2. Direct Instruction (10 min) — Present core content",
            "  3. Guided Practice (10 min) — Work through examples together",
            "  4. Independent Practice (10 min) — Students work individually",
            "  5. Assessment (5 min) — Quick check for understanding",
            "  6. Wrap-up (5 min) — Review key takeaways, preview next lesson",
            "",
            "Differentiation:",
            "  • ELL: Provide vocabulary cards with visuals",
            "  • Advanced: Extension problems for early finishers",
            "  • Support: Pair struggling students with peer tutors",
            "",
            "Assessment:",
            "  • Formative: Exit ticket with 3 questions",
            "  • Summative: End-of-unit quiz",
        ]
        return {"success": True, "result": "\n".join(lines)}


class WorksheetGeneratorTool(BaseTool):
    def execute(self, params):
        subject = params.get("subject", params.get("topic", "math")).lower()
        count = min(int(params.get("count", params.get("questions", 10))), 30)
        difficulty = params.get("difficulty", "medium")
        lines = [f"Worksheet: {subject.title()} — {difficulty}", "=" * 40,
                 f"Name: ____________________  Date: ___________\n"]
        if "math" in subject:
            ops = ["+", "-", "×", "÷"]
            for i in range(1, count + 1):
                a, b = random.randint(5, 50), random.randint(5, 50)
                op = random.choice(ops)
                lines.append(f"{i}.  {max(a,b)}  {op}  {min(a,b)}  =  ______")
        elif "vocab" in subject or "vocabulary" in subject:
            words = ["benevolent", "ephemeral", "pragmatic", "ambiguous", "diligent",
                     "eloquent", "resilient", "meticulous", "candid", "profound"]
            random.shuffle(words)
            for i in range(min(count, len(words))):
                lines.append(f"{i+1}. Define: {words[i]}")
                lines.append("   _______________________________________________\n")
        elif "science" in subject:
            topics = ["What is photosynthesis?",
                      "List 3 states of matter.",
                      "What causes the seasons?",
                      "Describe the water cycle.",
                      "What is a chemical reaction?"]
            for i in range(min(count, len(topics))):
                lines.append(f"{i+1}. {topics[i]}")
                lines.append("   _______________________________________________\n")
        else:
            for i in range(count):
                lines.append(f"{i+1}. What is an important concept in {subject}?")
                lines.append("   _______________________________________________\n")
        lines.append("\n--- Answer Key ---")
        return {"success": True, "result": "\n".join(lines)}


class ExamGeneratorTool(BaseTool):
    def execute(self, params):
        subject = params.get("subject", params.get("topic", "general"))
        sections = min(int(params.get("sections", 3)), 5)
        questions_per = min(int(params.get("questions", params.get("count", 5))), 15)
        lines = [f"Exam: {subject.title()}", "=" * 40,
                 f"Name: ____________________  Date: __________",
                 f"Total: {sections * questions_per} points | Time: {sections * 10} min\n"]
        section_types = ["Multiple Choice", "Short Answer", "True/False",
                         "Matching", "Essay", "Fill in the Blank", "Problem Solving"]
        for s in range(1, sections + 1):
            stype = random.choice(section_types)
            lines.append(f"\nSection {s}: {stype} ({questions_per} questions, {questions_per} pts)")
            if stype == "Multiple Choice":
                for q in range(1, questions_per + 1):
                    lines.append(f"  {q}. What is a key concept in {subject}?")
                    lines.append("     A) Option A    B) Option B    C) Option C    D) Option D")
            elif stype == "Short Answer":
                for q in range(1, questions_per + 1):
                    lines.append(f"  {q}. Describe an important aspect of {subject}.")
                    lines.append("       _______________________________________________")
            elif stype == "True/False":
                for q in range(1, questions_per + 1):
                    lines.append(f"  {q}. True or False: A statement about {subject}.")
            elif stype == "Essay":
                for q in range(1, questions_per + 1):
                    lines.append(f"  {q}. Write a short essay on a key {subject} topic.")
            else:
                for q in range(1, questions_per + 1):
                    lines.append(f"  {q}. ________________________________")
        lines.append(f"\n--- End of Exam ---")
        return {"success": True, "result": "\n".join(lines)}


class ProgressReportTool(BaseTool):
    def execute(self, params):
        student = params.get("student", params.get("name", "Student"))
        subject = params.get("subject", params.get("class", "General"))
        grade = params.get("grade", params.get("level", "B"))
        comments_pool = [
            f"{student} demonstrates a strong understanding of {subject} concepts.",
            f"{student} shows enthusiasm and积极参与 in class discussions.",
            f"{student} has shown improvement in {subject} this quarter.",
            f"{student} consistently completes assignments on time.",
            f"{student} would benefit from additional practice with {subject} fundamentals.",
            f"{student} works well in group settings and collaborates effectively.",
            f"{student} needs to focus on organization and time management.",
            f"{student} asks insightful questions that enrich class discussions.",
            f"{student} should review {subject} material more consistently at home.",
            f"{student} demonstrates creativity in approaching {subject} problems.",
        ]
        random.shuffle(comments_pool)
        selected = comments_pool[:4]
        lines = [
            f"Progress Report", "=" * 30,
            f"Student: {student}",
            f"Subject: {subject}",
            f"Grade: {grade}",
            f"Period: {datetime.date.today().strftime('%B %Y')}",
            "",
            "Academic Comments:",
        ]
        for c in selected:
            lines.append(f"  • {c}")
        lines.extend([
            "",
            "Areas for Improvement:",
            f"  • Encourage {student} to seek help when needed",
            "  • Practice {subject} skills for 15 min daily",
            "",
            "Teacher: ____________________",
        ])
        return {"success": True, "result": "\n".join(lines)}


class SeatingChartTool(BaseTool):
    def execute(self, params):
        names_str = params.get("names", params.get("students", ""))
        cols = max(1, int(params.get("cols", params.get("columns", 4))))
        rows = max(1, int(params.get("rows", 0)))
        if not names_str:
            return {"success": False, "result": "Provide comma-separated student names"}
        names = [n.strip() for n in names_str.split(",") if n.strip()]
        random.shuffle(names)
        if not rows:
            rows = (len(names) + cols - 1) // cols
        lines = [f"Seating Chart ({rows} rows × {cols} columns)", "=" * 30, "  [FRONT OF CLASS]\n"]
        idx = 0
        for r in range(rows):
            row_cells = []
            for c in range(cols):
                if idx < len(names):
                    row_cells.append(f"{names[idx]:15s}")
                else:
                    row_cells.append("(empty)       ")
                idx += 1
            lines.append("  " + "  ".join(row_cells))
        lines.append(f"\nTotal: {len(names)} students")
        return {"success": True, "result": "\n".join(lines)}


class IcebreakerTool(BaseTool):
    def execute(self, params):
        count = min(int(params.get("count", 5)), 20)
        audience = params.get("audience", params.get("group", "students"))
        questions = [
            f"If you could have dinner with any historical figure, who would it be?",
            f"What is a skill you'd like to learn this year?",
            f"What is your favorite book or movie and why?",
            f"If you could travel anywhere, where would you go?",
            f"What is a hobby you enjoy outside of school?",
            f"What is one thing you're really good at?",
            f"If you won the lottery, what would you do first?",
            f"What is the best advice you've ever received?",
            f"What superpower would you choose and why?",
            f"What is your dream career?",
            f"If you could switch lives with someone for a day, who?",
            f"What is a food you could eat every day?",
            f"What is a tradition your family has?",
            f"What is something you want to accomplish this year?",
            f"If you could invent something, what would it be?",
            f"What is your favorite subject and why?",
            f"What makes you feel inspired?",
            f"What is the most interesting place you've visited?",
            f"If you could meet any fictional character, who?",
            f"What is one thing people would be surprised to learn about you?",
        ]
        random.shuffle(questions)
        lines = [f"Icebreaker Questions ({audience})", "=" * 40, ""]
        for i, q in enumerate(questions[:count], 1):
            lines.append(f"{i}. {q}")
        return {"success": True, "result": "\n".join(lines)}


class DiscussionPromptTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "a given topic").strip()
        count = min(int(params.get("count", 5)), 15)
        level = params.get("level", params.get("depth", "moderate"))
        prompts = [
            f"What is the most significant aspect of {topic}? Why?",
            f"How does {topic} relate to your own experience?",
            f"What are the potential benefits and drawbacks of {topic}?",
            f"Can you think of an example of {topic} in the real world?",
            f"How might {topic} change in the next decade?",
            f"What questions do you still have about {topic}?",
            f"Do you agree or disagree with common views on {topic}? Explain.",
            f"How would you explain {topic} to someone who knows nothing about it?",
            f"What connections can you draw between {topic} and other subjects?",
            f"Whose perspective is missing from our discussion of {topic}?",
            f"What evidence would change your mind about {topic}?",
            f"How does {topic} impact society as a whole?",
            f"What would happen if {topic} were suddenly removed from the world?",
            f"Can {topic} be viewed from a different cultural perspective?",
            f"What is the ethical dimension of {topic}?",
        ]
        lines = [f"Discussion Prompts: {topic}", "=" * 40,
                 f"Level: {level} | {count} questions\n"]
        random.shuffle(prompts)
        for i, p in enumerate(prompts[:count], 1):
            lines.append(f"{i}. {p}")
        return {"success": True, "result": "\n".join(lines)}


class LearningObjectivesTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "a lesson").strip()
        count = min(int(params.get("count", 4)), 10)
        level = params.get("level", params.get("bloom", "apply"))
        bloom_levels = {
            "remember": ["Recall", "List", "Identify", "Name", "Define", "Describe"],
            "understand": ["Explain", "Summarize", "Interpret", "Classify", "Paraphrase"],
            "apply": ["Apply", "Demonstrate", "Solve", "Use", "Implement", "Execute"],
            "analyze": ["Analyze", "Compare", "Contrast", "Examine", "Differentiate", "Investigate"],
            "evaluate": ["Evaluate", "Justify", "Critique", "Assess", "Defend", "Argue"],
            "create": ["Create", "Design", "Develop", "Construct", "Propose", "Formulate"],
        }
        verbs = bloom_levels.get(level.lower(), bloom_levels["apply"])
        lines = [f"Learning Objectives: {topic}", "=" * 40,
                 f"Bloom's Level: {level.title()}\n"]
        for i in range(count):
            verb = random.choice(verbs)
            obj = f"{verb} key concepts related to {topic}"
            lines.append(f"  • Students will be able to {obj.lower()}.")
        lines.append(f"\n(SMART: Specific, Measurable, Achievable, Relevant, Time-bound)")
        return {"success": True, "result": "\n".join(lines)}


class ActivityGeneratorTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "a topic").strip()
        duration = int(params.get("minutes", params.get("duration", 15)))
        group_size = int(params.get("group_size", params.get("groups", 3)))
        activities = [
            {
                "name": "Think-Pair-Share",
                "desc": f"Students think individually about {topic}, discuss with a partner, then share with the class.",
                "time": f"{duration} min",
            },
            {
                "name": "Jigsaw",
                "desc": f"Each group becomes expert on one aspect of {topic}, then teaches other groups.",
                "time": f"{duration} min",
            },
            {
                "name": "Debate",
                "desc": f"Split class into two sides to argue different perspectives on {topic}.",
                "time": f"{duration} min",
            },
            {
                "name": "Concept Mapping",
                "desc": f"Groups create a visual map showing relationships within {topic}.",
                "time": f"{duration} min",
            },
            {
                "name": "Gallery Walk",
                "desc": f"Groups create posters about {topic}, then walk around to review each other's work.",
                "time": f"{duration} min",
            },
            {
                "name": "Role Play",
                "desc": f"Students act out scenarios related to {topic} to understand different perspectives.",
                "time": f"{duration} min",
            },
            {
                "name": "Quiz Game",
                "desc": f"Teams compete answering questions about {topic} in a game show format.",
                "time": f"{duration} min",
            },
            {
                "name": "Peer Teaching",
                "desc": f"Each group prepares a mini-lesson on an assigned {topic} subtopic.",
                "time": f"{duration} min",
            },
        ]
        random.shuffle(activities)
        selected = activities[:max(1, min(3, len(activities)))]
        lines = [f"Classroom Activities: {topic}", "=" * 40,
                 f"Duration: {duration} min | Group size: {group_size}\n"]
        for i, act in enumerate(selected, 1):
            lines.append(f"Activity {i}: {act['name']}")
            lines.append(f"  {act['desc']}")
            lines.append(f"  Time: {act['time']}\n")
        return {"success": True, "result": "\n".join(lines)}


class FeedbackTool(BaseTool):
    POSITIVE = [
        "excellent work on this assignment", "great improvement since last time",
        "shows strong understanding of the material", "creative approach to problem-solving",
        "consistently produces high-quality work", "actively participates in class",
        "demonstrates leadership in group work", "asks thoughtful questions",
        "shows genuine enthusiasm for learning", "works well independently",
    ]
    CONSTRUCTIVE = [
        "would benefit from reviewing fundamental concepts",
        "should focus on showing all work step by step",
        "needs to double-check answers for accuracy",
        "could improve by managing time more effectively",
        "would benefit from participating more in discussions",
        "should proofread work before submitting",
        "needs to cite sources properly",
        "could provide more detailed explanations",
    ]
    def execute(self, params):
        student = params.get("student", params.get("name", "Student"))
        subject = params.get("subject", "class")
        count = min(int(params.get("count", 3)), 6)
        lines = [f"Student Feedback: {student}", "=" * 35, f"Subject: {subject}\n"]
        random.shuffle(self.POSITIVE)
        random.shuffle(self.CONSTRUCTIVE)
        pos_count = min(count, len(self.POSITIVE))
        con_count = min(count, len(self.CONSTRUCTIVE))
        half = max(1, count // 2)
        lines.append("Strengths:")
        for p in self.POSITIVE[:half]:
            lines.append(f"  ✓ {p}.")
        lines.append("\nAreas to Work On:")
        for c in self.CONSTRUCTIVE[:count - half]:
            lines.append(f"  ○ {c}.")
        lines.append(f"\nOverall: {student} is making {'good' if random.random() > 0.3 else 'satisfactory'} progress in {subject}.")
        return {"success": True, "result": "\n".join(lines)}


class ReadingListTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "add")
        path = os.path.join(_STUDY_DIR, "reading.json")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    books = json.load(f)
            else:
                books = []
            if action == "add":
                title = params.get("title", "").strip()
                author = params.get("author", "").strip()
                category = params.get("category", params.get("subject", "General")).strip()
                if not title:
                    return {"success": False, "result": "Provide the book/article title"}
                books.append({"title": title, "author": author, "category": category,
                              "status": "unread", "added": time.time()})
                with open(path, "w") as f:
                    json.dump(books, f)
                return {"success": True, "result": f"Added: {title}{' by ' + author if author else ''}"}
            elif action == "list":
                if not books:
                    return {"success": True, "result": "No books in reading list"}
                category = params.get("category", "")
                pool = [b for b in books if not category or b.get("category") == category]
                lines = [f"Reading List ({len(pool)} items):"]
                for i, b in enumerate(pool, 1):
                    author_str = f" by {b.get('author','?')}" if b.get('author') else ""
                    lines.append(f"  {i}. {b['title']}{author_str} [{b.get('status','unread')}]")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "mark":
                title = params.get("title", "").strip()
                status = params.get("status", "read")
                for b in books:
                    if title.lower() in b["title"].lower():
                        b["status"] = status
                        with open(path, "w") as f:
                            json.dump(books, f)
                        return {"success": True, "result": f"Marked '{b['title']}' as {status}"}
                return {"success": False, "result": f"Book not found: {title}"}
            return {"success": False, "result": "Actions: add, list, mark"}
        except Exception as e:
            return {"success": False, "result": f"Reading list error: {e}"}


class StudyGuideTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "").strip()
        subtopics_str = params.get("subtopics", params.get("topics", ""))
        if not topic and not subtopics_str:
            return {"success": False, "result": "Provide topic or subtopics (comma-separated)"}
        subtopics = [s.strip() for s in subtopics_str.split(",") if s.strip()]
        if not subtopics:
            subtopics = [f"Introduction to {topic}", f"Core {topic} Concepts",
                         f"Key {topic} Terms", f"{topic} Examples", f"{topic} Practice"]
        lines = [f"Study Guide: {topic or subtopics[0]}", "=" * 40, ""]
        for i, sub in enumerate(subtopics, 1):
            lines.append(f"Topic {i}: {sub}")
            lines.append("  Key Points:")
            for p in range(3):
                lines.append(f"    • Important concept about {sub.lower()}")
            lines.append("  Key Terms:")
            for t in range(2):
                lines.append(f"    • {sub.split()[-1 if len(sub.split()) > 1 else 0].title()} — definition")
            lines.append("  Review Questions:")
            for q in range(2):
                lines.append(f"    ? Explain the significance of {sub.lower()}")
            lines.append("")
        lines.append("Study Tips:")
        lines.append("  • Review this guide and create flashcards for key terms")
        lines.append("  • Teach the material to someone else")
        lines.append("  • Practice with sample problems")
        return {"success": True, "result": "\n".join(lines)}


class TimelineTool(BaseTool):
    def execute(self, params):
        title = params.get("title", params.get("topic", "Timeline")).strip()
        events_str = params.get("events", params.get("items", ""))
        if events_str:
            events = [e.strip() for e in events_str.split(",") if e.strip()]
        else:
            events = [f"Event 1 — Beginning of {title}",
                      f"Event 2 — Development phase",
                      f"Event 3 — Key milestone",
                      f"Event 4 — Turning point",
                      f"Event 5 — Modern {title}"]
        years_str = params.get("years", "")
        years = [y.strip() for y in years_str.split(",") if y.strip()] if years_str else []
        lines = [f"Timeline: {title}", "=" * 40, ""]
        for i, event in enumerate(events):
            year = years[i] if i < len(years) else ""
            year_str = f" [{year}]" if year else ""
            lines.append(f"  {i+1}. {event}{year_str}")
            lines.append(f"     {'─' * 30}")
        lines.append(f"\n{len(events)} events documented")
        return {"success": True, "result": "\n".join(lines)}


class MindMapTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "").strip()
        branches_str = params.get("branches", params.get("items", ""))
        if not topic and not branches_str:
            return {"success": False, "result": "Provide topic or branches (comma-separated)"}
        branches = [b.strip() for b in branches_str.split(",") if b.strip()]
        if not branches:
            branches = [f"{topic} Basics", f"Key {topic} Concepts",
                        f"{topic} Applications", f"{topic} Examples", f"{topic} Resources"]
        lines = [f"Mind Map: {topic or 'Untitled'}", "=" * 40,
                 f"                     [{topic or 'Central Idea'}]", "                          |\n"]
        for i, branch in enumerate(branches, 1):
            lines.append(f"  {i}.─── {branch}")
            for sub in range(2):
                lines.append(f"       ├── Subtopic: {branch.split()[-1]} aspect {sub + 1}")
            lines.append(f"       └── Detail: Related {topic.lower() if topic else 'concept'} note")
            if i < len(branches):
                lines.append("       |")
        lines.append(f"\nBranches: {len(branches)}")
        return {"success": True, "result": "\n".join(lines)}


class ThesisStatementTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "").strip()
        style = params.get("style", params.get("type", "argumentative")).lower()
        if not topic:
            return {"success": False, "result": "Provide essay topic"}
        templates = {
            "argumentative": [
                f"Although some argue that {topic} is straightforward, a closer examination reveals complex nuances that demand our attention.",
                f"While {topic} has its benefits, the drawbacks outweigh them when considering long-term consequences.",
                f"This essay argues that {topic} is not merely a matter of opinion, but a critical issue requiring immediate action.",
            ],
            "expository": [
                f"Through an analysis of {topic}, this essay will explore the three key factors that shape our understanding.",
                f"The phenomenon of {topic} can be understood by examining its historical origins, modern manifestations, and future implications.",
                f"{topic} is composed of several interrelated components, each playing a crucial role in the overall system.",
            ],
            "analytical": [
                f"A critical analysis of {topic} reveals underlying patterns that challenge conventional assumptions.",
                f"By examining {topic} through multiple theoretical lenses, we gain a more comprehensive understanding of its impact.",
                f"The evidence surrounding {topic} points to a conclusion that contradicts popular belief.",
            ],
            "compare": [
                f"While {topic} and its alternatives share common goals, they differ fundamentally in their approach and outcomes.",
                f"A comparison of different perspectives on {topic} reveals that context is the determining factor in choosing the best approach.",
            ],
        }
        pool = templates.get(style, templates["argumentative"])
        thesis = random.choice(pool)
        lines = [f"Thesis Statement: {topic}", "=" * 40,
                 f"Style: {style.title()}\n", f"\"{thesis}\"", "",
                 "Tips:", "  • Make sure your thesis is debatable (not a fact)",
                 "  • Keep it specific and focused",
                 "  • Place it at the end of your introduction"]
        return {"success": True, "result": "\n".join(lines)}


class AbstractGeneratorTool(BaseTool):
    def execute(self, params):
        title = params.get("title", "").strip()
        topic = params.get("topic", "").strip()
        key_points = params.get("key_points", params.get("points", "")).strip()
        if not topic and not title:
            return {"success": False, "result": "Provide topic or title"}
        points = [p.strip() for p in key_points.split(",") if p.strip()] if key_points else [
            f"Background on {topic or title}", f"Methodology for studying {topic or title}",
            f"Key findings related to {topic or title}", f"Implications of these findings"]
        abstract = (f"This paper examines {topic or title.lower()}, focusing on its key aspects and implications. "
                    f"Through a comprehensive analysis of {points[0].lower()}, we identify significant patterns. "
                    f"Our approach, based on {points[1].lower() if len(points) > 1 else 'established methodologies'}, "
                    f"reveals that {points[2].lower() if len(points) > 2 else 'the findings are noteworthy'}. "
                    f"These results suggest that {points[3].lower() if len(points) > 3 else 'further research is needed'}. "
                    f"This work contributes to the broader understanding of {topic or title.lower()} "
                    f"and offers practical insights for future research.")
        lines = [f"Abstract: {title or topic}", "=" * 40, "",
                 f"\"{abstract}\"", "",
                 f"Keywords: {', '.join(points[:5]) if points else topic.lower()}",
                 f"Word count: ~{len(abstract.split())}  words"]
        return {"success": True, "result": "\n".join(lines)}


class FlashcardImportTool(BaseTool):
    def execute(self, params):
        text = params.get("text", "").strip()
        deck = params.get("deck", "imported").strip()
        path = os.path.join(_STUDY_DIR, "flashcards.json")
        if not text:
            return {"success": False, "result": "Provide text with Q&A pairs (one per line, Q|A or Q:A format)"}
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    cards = json.load(f)
            else:
                cards = []
            imported = 0
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                for sep in ["|", ":", ";", "\t"]:
                    if sep in line:
                        parts = line.split(sep, 1)
                        q, a = parts[0].strip(), parts[1].strip()
                        if q and a:
                            cards.append({"question": q, "answer": a, "deck": deck, "box": 0})
                            imported += 1
                            break
            with open(path, "w") as f:
                json.dump(cards, f)
            return {"success": True, "result": f"Imported {imported} cards to deck '{deck}'"}
        except Exception as e:
            return {"success": False, "result": f"Import error: {e}"}


class CheatSheetTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "").strip()
        items_str = params.get("items", "")
        if not topic and not items_str:
            return {"success": False, "result": "Provide topic or items"}
        items = [i.strip() for i in items_str.split(",") if i.strip()]
        if not items:
            items = [f"Definition of {topic}", f"Key formula for {topic}",
                     f"Important rule in {topic}", f"Common example of {topic}",
                     f"Memory tip for {topic}"]
        formulas_pool = [
            ("Formula", "A = πr² (area of circle)"),
            ("Formula", "E = mc² (energy-mass)"),
            ("Rule", "PEMDAS (order of operations)"),
            ("Rule", "i before e except after c"),
            ("Constant", "π ≈ 3.14159"),
            ("Constant", "e ≈ 2.71828"),
            ("Conversion", "1 inch = 2.54 cm"),
            ("Conversion", "0°C = 32°F"),
        ]
        lines = [f"Cheat Sheet: {topic or 'Reference'}", "=" * 40, ""]
        lines.append("Quick Reference:")
        for item in items:
            lines.append(f"  • {item}")
        lines.append(f"\nKey {topic + ' ' if topic else ''}Formulas:")
        random.shuffle(formulas_pool)
        for cat, val in formulas_pool[:4]:
            lines.append(f"  • [{cat}] {val}")
        lines.append("\nPro Tips:")
        lines.append("  • Focus on understanding concepts, not memorizing")
        lines.append("  • Draw diagrams to visualize relationships")
        lines.append("  • Practice with real examples")
        return {"success": True, "result": "\n".join(lines)}


class ConceptMapTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "").strip()
        concepts_str = params.get("concepts", params.get("items", ""))
        if not topic and not concepts_str:
            return {"success": False, "result": "Provide topic or concepts (comma-separated)"}
        concepts = [c.strip() for c in concepts_str.split(",") if c.strip()]
        if not concepts:
            concepts = [topic, f"{topic} Types", f"{topic} Examples",
                        f"{topic} Properties", f"{topic} Applications"]
        rel_verbs = ["is a type of", "leads to", "depends on", "is part of",
                     "contradicts", "supports", "is an example of", "relates to"]
        lines = [f"Concept Map: {topic or 'Untitled'}", "=" * 40,
                 f"Central Concept: {concepts[0]}\n"]
        for i in range(1, len(concepts)):
            verb = random.choice(rel_verbs)
            lines.append(f"  [{concepts[0]}]")
            lines.append(f"     │")
            lines.append(f"     ├─ {verb} ── [{concepts[i]}]")
            lines.append(f"     │")
        lines.append("\nRelationships:")
        for i in range(1, min(len(concepts), 6)):
            for j in range(i + 1, min(len(concepts), 6)):
                verb = random.choice(rel_verbs)
                lines.append(f"  • {concepts[i]} {verb} {concepts[j]}")
        return {"success": True, "result": "\n".join(lines)}


class QuizMeTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "start")
        path = os.path.join(_STUDY_DIR, "flashcards.json")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    cards = json.load(f)
            else:
                cards = []
            deck = params.get("deck", "default")
            pool = [c for c in cards if c.get("deck", "default") == deck]
            if not pool:
                return {"success": False, "result": f"No cards in deck '{deck}'. Add cards with flashcard first."}
            if action == "start":
                random.shuffle(pool)
                n = min(int(params.get("count", len(pool))), len(pool))
                session = pool[:n]
                lines = [f"Quiz Mode: {deck} ({n} questions)", "=" * 35, ""]
                for i, card in enumerate(session, 1):
                    lines.append(f"Q{i}: {card['question']}")
                    lines.append(f"A{i}: ||{card['answer']}||")
                    lines.append("")
                lines.append("(Answers hidden behind ||spoiler|| tags — highlight to reveal)")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "answer":
                lines = [f"Deck '{deck}' answers:\n"]
                for i, card in enumerate(pool, 1):
                    lines.append(f"Q{i}: {card['question']}")
                    lines.append(f"A{i}: {card['answer']}")
                    lines.append("")
                return {"success": True, "result": "\n".join(lines)}
            return {"success": False, "result": "Actions: start (quiz with hidden answers), answer (show all answers)"}
        except Exception as e:
            return {"success": False, "result": f"Quiz error: {e}"}


# ════════════════════════════════════════════
# Student & Teacher Tools batch 3 (20 tools — 93 total student/teacher)
# ════════════════════════════════════════════

class PlagiarismCheckTool(BaseTool):
    def execute(self, params):
        text1 = params.get("text1", params.get("first", "")).strip()
        text2 = params.get("text2", params.get("second", "")).strip()
        if not text1 or not text2:
            return {"success": False, "result": "Provide text1 and text2 to compare"}
        def normalize(t):
            return re.sub(r'[^a-z0-9 ]', '', t.lower()).split()
        words1 = normalize(text1)
        words2 = normalize(text2)
        if not words1 or not words2:
            return {"success": False, "result": "Need at least some words in both texts"}
        set1, set2 = set(words1), set(words2)
        intersection = set1 & set2
        union = set1 | set2
        jaccard = len(intersection) / len(union) * 100 if union else 0
        common_phrases = []
        for i in range(len(words1) - 2):
            phrase = " ".join(words1[i:i+3])
            if phrase in " ".join(words2):
                common_phrases.append(phrase)
        lines = [f"Plagiarism / Similarity Check", "=" * 40]
        lines.append(f"Text 1: {len(words1)} words")
        lines.append(f"Text 2: {len(words2)} words")
        lines.append(f"Vocab Overlap: {len(intersection)}/{len(union)} words")
        lines.append(f"Jaccard Similarity: {jaccard:.1f}%")
        lines.append(f"Matching 3+ word phrases: {len(common_phrases)}")
        if common_phrases:
            lines.append("\nMatching phrases:")
            for p in common_phrases[:15]:
                lines.append(f"  \"{p}\"")
        if jaccard > 70:
            lines.append("\n⚠ High similarity — texts may be plagiarized")
        elif jaccard > 40:
            lines.append("\n⚠ Moderate similarity — review for proper citation")
        else:
            lines.append("\n✓ Low similarity")
        return {"success": True, "result": "\n".join(lines)}


class PeerReviewTool(BaseTool):
    def execute(self, params):
        assignment = params.get("assignment", params.get("title", "Assignment"))
        criteria_str = params.get("criteria", "Clarity,Accuracy,Depth,Citations")
        criteria = [c.strip() for c in criteria_str.split(",") if c.strip()]
        lines = [f"Peer Review Form: {assignment}", "=" * 40, "",
                 "Reviewer: ____________________  Author: ____________________\n"]
        for c in criteria:
            lines.append(f"{c}:")
            lines.append(f"  Score (1-5): ___  Comments: _____________________________")
            lines.append("")
        lines.append("Overall Assessment:")
        lines.append("  Strengths: _______________________________________________")
        lines.append("  Areas for Improvement: ___________________________________")
        lines.append("  Additional Comments: _____________________________________")
        lines.append("\nScoring Rubric:")
        lines.append("  1 = Needs significant improvement")
        lines.append("  3 = Meets expectations")
        lines.append("  5 = Exemplary")
        return {"success": True, "result": "\n".join(lines)}


class LabReportTool(BaseTool):
    def execute(self, params):
        title = params.get("title", params.get("experiment", "Lab Experiment")).strip()
        course = params.get("course", params.get("subject", "Science"))
        lines = [f"Lab Report: {title}", "=" * 40,
                 f"Course: {course}\n",
                 "1. Title Page",
                 f"   Experiment: {title}", "   Name: ____________________",
                 "   Date: ____________________", "   Partner(s): ____________________\n",
                 "2. Objective / Purpose",
                 "   What question is this experiment answering?\n",
                 "3. Hypothesis",
                 "   What do you predict will happen? Why?\n",
                 "4. Materials",
                 "   List all equipment and materials used\n",
                 "5. Procedure",
                 "   Step-by-step description (numbered):\n",
                 "6. Data / Observations",
                 "   | Trial | Measurement | Observations |",
                 "   |-------|-------------|--------------|\n",
                 "7. Calculations & Analysis",
                 "   Show your work, formulas, and calculations\n",
                 "8. Results",
                 "   What did the data show? Include graphs if applicable.\n",
                 "9. Discussion",
                 "   • Were results expected?", "   • Sources of error",
                 "   • What could be improved?\n",
                 "10. Conclusion",
                 f"   Summarize findings from {title}\n",
                 "11. References",
        ]
        return {"success": True, "result": "\n".join(lines)}


class ResearchProposalTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "").strip()
        course = params.get("course", params.get("subject", ""))
        if not topic:
            return {"success": False, "result": "Provide a research topic"}
        lines = [f"Research Proposal: {topic}", "=" * 40,
                 f"Course: {course or 'Independent Research'}\n",
                 "1. Title",
                 f"   A Study of {topic}\n",
                 "2. Introduction / Background",
                 f"   • Current state of research on {topic}", "   • Gap in knowledge this study addresses\n",
                 "3. Research Question(s)",
                 f"   • What is the relationship between X and {topic}?",
                 "   • How can existing approaches be improved?\n",
                 "4. Hypothesis",
                 f"   It is hypothesized that {topic.lower()} will show significant correlation with...\n",
                 "5. Methodology",
                 "   • Research Design: ____________________",
                 "   • Data Collection: ____________________",
                 "   • Sample Size: ____________________",
                 "   • Analysis Plan: ____________________\n",
                 "6. Expected Outcomes",
                 f"   • Anticipated findings related to {topic}",
                 "   • Potential impact on the field\n",
                 "7. Timeline",
                 "   • Month 1-2: Literature review & proposal refinement",
                 "   • Month 3-4: Data collection",
                 "   • Month 5: Analysis",
                 "   • Month 6: Writing & submission\n",
                 "8. References",
                 "   • At least 5 peer-reviewed sources",
        ]
        return {"success": True, "result": "\n".join(lines)}


class BookReportTool(BaseTool):
    def execute(self, params):
        title = params.get("title", params.get("book", "")).strip()
        author = params.get("author", "").strip()
        if not title:
            return {"success": False, "result": "Provide book title"}
        lines = [f"Book Report: {title}", "=" * 40,
                 f"Author: {author or '(unknown)'}",
                 "Student: ____________________  Date: ____________________\n",
                 "1. Basic Information",
                 f"   Title: {title}",
                 f"   Author: {author or 'N/A'}",
                 "   Genre: ____________________",
                 "   Publication Date: ____________________\n",
                 "2. Summary (3-5 paragraphs)",
                 "   • Setting: ____________________",
                 "   • Main Characters: ____________________",
                 "   • Plot Overview:",
                 "     - Exposition (beginning):",
                 "     - Rising Action (middle):",
                 "     - Climax (turning point):",
                 "     - Resolution (ending):\n",
                 "3. Character Analysis",
                 "   Choose one character and analyze their development:\n",
                 "4. Theme Analysis",
                 "   What is the main message or lesson?\n",
                 "5. Personal Reflection",
                 "   • What did you enjoy?",
                 "   • What would you change?",
                 "   • Would you recommend this book? Why?\n",
                 "6. Vocabulary (5 new words with definitions)",
        ]
        return {"success": True, "result": "\n".join(lines)}


class PresentationOutlineTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "").strip()
        slides = min(int(params.get("slides", params.get("count", 8))), 25)
        duration = params.get("duration", params.get("minutes", f"{slides * 2} min"))
        audience = params.get("audience", "general")
        if not topic:
            return {"success": False, "result": "Provide a presentation topic"}
        lines = [f"Presentation Outline: {topic}", "=" * 40,
                 f"Duration: {duration}  |  Audience: {audience}"] + [""]
        slide_templates = [
            ("Title Slide", f"{topic} — Presenter Name"),
            ("Agenda / Overview", "What we will cover today"),
            ("Introduction", f"Background and context of {topic}"),
            ("Key Concept 1", f"First main idea about {topic}"),
            ("Key Concept 2", f"Second main idea about {topic}"),
            ("Key Concept 3", f"Third main idea about {topic}"),
            ("Example / Case Study", f"Real-world application of {topic}"),
            ("Data / Evidence", "Supporting statistics and research"),
            ("Visual Aid", "Graph, diagram, or chart"),
            ("Comparison", f"Different perspectives on {topic}"),
            ("Interactive Element", "Discussion question or activity"),
            ("Challenges", f"Current issues in {topic}"),
            ("Future Directions", f"What's next for {topic}"),
            ("Summary", "Key takeaways"),
            ("Q&A", "Questions and discussion"),
            ("References", "Sources and further reading"),
        ]
        for i in range(min(slides, len(slide_templates))):
            name, desc = slide_templates[i]
            lines.append(f"Slide {i+1}: {name}")
            lines.append(f"  • {desc}")
            lines.append(f"  • Key points to cover: (add 2-3 bullet points)")
            lines.append("")
        return {"success": True, "result": "\n".join(lines)}


class DebateTopicTool(BaseTool):
    def execute(self, params):
        topic = params.get("topic", "").strip()
        count = min(int(params.get("count", 3)), 10)
        style = params.get("style", "standard")
        if not topic:
            return {"success": False, "result": "Provide a debate topic or subject area"}
        points = {
            "for": [
                f"The evidence supports {topic} as a positive development",
                f"{topic} leads to better outcomes for all stakeholders",
                f"Historical precedent shows {topic} is the right approach",
                f"Economic analysis confirms {topic} is beneficial",
                f"Ethical considerations favor adopting {topic}",
            ],
            "against": [
                f"The risks of {topic} outweigh the potential benefits",
                f"{topic} creates unacceptable inequalities",
                f"Alternative approaches are more effective than {topic}",
                f"Long-term consequences of {topic} are negative",
                f"{topic} violates fundamental principles",
            ],
        }
        random.shuffle(points["for"])
        random.shuffle(points["against"])
        lines = [f"Debate: {topic}", "=" * 40,
                 f"Style: {style.title()}\n",
                 "Proposition (FOR):", "  The house believes that " + topic.lower(),
                 "\nAffirmative Arguments:"]
        for i, arg in enumerate(points["for"][:count], 1):
            lines.append(f"  {i}. {arg}")
        lines.append("\nOpposition (AGAINST):")
        for i, arg in enumerate(points["against"][:count], 1):
            lines.append(f"  {i}. {arg}")
        lines.append("\nFormat Suggestions:")
        lines.append("  • Opening statements (3 min each)")
        lines.append("  • Rebuttal round (2 min each)")
        lines.append("  • Cross-examination (5 min)")
        lines.append("  • Closing arguments (2 min each)")
        return {"success": True, "result": "\n".join(lines)}


class WritingPromptTool(BaseTool):
    def execute(self, params):
        count = min(int(params.get("count", 5)), 20)
        genre = params.get("genre", params.get("style", "any")).lower()
        prompts = {
            "narrative": [
                "Write about a character who discovers a hidden door in their home.",
                "You wake up with the ability to understand any language. What happens?",
                "Write a story that begins with the sentence: 'It was never supposed to work.'",
                "A stranger hands you a letter addressed to someone who died 50 years ago.",
                "Describe a world where memories can be traded like currency.",
            ],
            "persuasive": [
                "Argue for or against: Should schools eliminate homework?",
                "Write a letter to your local government about an issue you care about.",
                "Should social media be banned for users under 16? Defend your position.",
                "Is artificial intelligence a threat or an opportunity? Make your case.",
                "Should college education be free? Present your argument.",
            ],
            "descriptive": [
                "Describe your ideal learning environment in vivid detail.",
                "Write about a place that feels like home — using all five senses.",
                "Describe a moment when everything changed, as if in slow motion.",
                "Paint a picture of a city street at dawn.",
                "Describe a piece of technology as if explaining it to someone from 100 years ago.",
            ],
            "expository": [
                "Explain how something you use every day actually works.",
                "Describe the process of learning a new skill from start to finish.",
                "Compare and contrast two approaches to solving the same problem.",
                "Write a step-by-step guide for something you do well.",
                "Explain a complex idea in simple terms for a younger student.",
            ],
            "creative": [
                "What if gravity suddenly stopped working for 24 hours?",
                "Write a conversation between your phone and your laptop.",
                "You find a message in a bottle — but it's an email from 10 years in the future.",
                "If your pet could talk for one day, what would you discuss?",
                "Design a new holiday and describe how it's celebrated.",
            ],
        }
        if genre != "any" and genre in prompts:
            pool = prompts[genre]
        else:
            pool = []
            for g in prompts.values():
                pool.extend(g)
        random.shuffle(pool)
        lines = [f"Writing Prompts", "=" * 40]
        if genre != "any":
            lines.append(f"Genre: {genre.title()}\n")
        for i, p in enumerate(pool[:count], 1):
            lines.append(f"{i}. {p}")
            lines.append("")
        return {"success": True, "result": "\n".join(lines)}


class MathWordProblemTool(BaseTool):
    def execute(self, params):
        count = min(int(params.get("count", 5)), 15)
        difficulty = params.get("difficulty", "medium").lower()
        topic = params.get("topic", "general").lower()
        problems = []
        for i in range(1, count + 1):
            if "age" in topic or difficulty == "easy":
                a, b = random.randint(5, 15), random.randint(2, 10)
                problems.append(
                    f"{i}. Alex is {a} years old. Alex's parent is {a + b * 10} years old. "
                    f"In how many years will Alex's parent be exactly twice Alex's age?\n"
                    f"   [Answer: {a - 2 * a + (a + b * 10)} years]")
            elif "money" in topic or "finance" in topic:
                price, qty = random.randint(3, 50), random.randint(2, 10)
                problems.append(
                    f"{i}. A student buys {qty} notebooks at ${price} each. "
                    f"Tax is 8%. What is the total cost?\n"
                    f"   [Answer: ${price * qty * 1.08:.2f}]")
            elif "speed" in topic or "distance" in topic:
                speed, hours = random.randint(30, 70), random.randint(1, 5)
                problems.append(
                    f"{i}. A car travels at {speed} mph for {hours} hours. "
                    f"How far does it travel? If it returns at {speed + 10} mph, how long does the return trip take?\n"
                    f"   [Answer: Distance = {speed * hours} miles, Return time = {speed * hours / (speed + 10):.1f} hours]")
            else:
                a, b = random.randint(5, 50), random.randint(3, 20)
                ops = random.choice(["add", "multiply", "area"])
                if ops == "add":
                    problems.append(
                        f"{i}. A class has {a} students. {b} more join. "
                        f"How many students total? Each student needs {random.randint(2, 5)} worksheets. How many sheets needed?\n"
                        f"   [Answer: {a + b} students, {(a + b) * random.randint(2, 5)} sheets]")
                elif ops == "multiply":
                    problems.append(
                        f"{i}. A teacher arranges {a} desks in {b} rows. "
                        f"How many desks per row? If {random.randint(1, 3)} desks are broken, how many rows are complete?\n"
                        f"   [Answer: {a // b} per row ({a % b} leftover)]")
                else:
                    problems.append(
                        f"{i}. A rectangular classroom is {a}m × {b}m. "
                        f"What is its area? What is the perimeter?\n"
                        f"   [Answer: Area = {a * b}m², Perimeter = {2 * (a + b)}m]")
        return {"success": True, "result": "Math Word Problems:\n" + "=" * 40 + "\n" + "\n\n".join(problems)}


class ProjectPlannerTool(BaseTool):
    def execute(self, params):
        title = params.get("title", params.get("project", "Project")).strip()
        weeks = min(int(params.get("weeks", params.get("duration", 6))), 20)
        tasks_str = params.get("tasks", params.get("milestones", ""))
        tasks = [t.strip() for t in tasks_str.split(",") if t.strip()] if tasks_str else []
        lines = [f"Project Plan: {title}", "=" * 40, f"Duration: {weeks} weeks\n"]
        if tasks:
            lines.append("Major Milestones:")
            for t in tasks:
                lines.append(f"  • {t}")
            lines.append("")
        per_week = len(tasks) // weeks if tasks else 0
        for w in range(1, weeks + 1):
            lines.append(f"Week {w}:")
            if tasks and w <= len(tasks):
                lines.append(f"  🎯 Milestone: {tasks[w-1]}")
            lines.append(f"  Tasks: ______________________________")
            lines.append(f"  Deliverables: _______________________")
            lines.append(f"  Status: [ ] Not Started  [ ] In Progress  [ ] Complete")
            lines.append("")
        lines.append("Resources Needed:")
        lines.append("  • People: ____________________")
        lines.append("  • Materials: ____________________")
        lines.append("  • Budget: ____________________")
        return {"success": True, "result": "\n".join(lines)}


class SelfAssessmentTool(BaseTool):
    def execute(self, params):
        subject = params.get("subject", params.get("topic", "course"))
        count = min(int(params.get("count", 5)), 15)
        lines = [f"Self-Assessment: {subject.title()}", "=" * 40, "",
                 "Student: ____________________  Date: ____________________\n",
                 "Rate yourself on each skill (1 = Needs work, 3 = Competent, 5 = Excellent):\n"]
        skill_areas = ["Understanding core concepts", "Applying knowledge to problems",
                       "Critical thinking and analysis", "Collaboration and teamwork",
                       "Communication of ideas", "Time management and organization",
                       "Independent learning", "Creativity and innovation",
                       "Attention to detail", "Active participation",
                       "Using resources effectively", "Meeting deadlines",
                       "Asking for help when needed", "Teaching others",
                       "Connecting ideas across subjects"]
        random.shuffle(skill_areas)
        for s in skill_areas[:count]:
            lines.append(f"  {s}")
            lines.append(f"    1 ☐  2 ☐  3 ☐  4 ☐  5 ☐")
            lines.append(f"    Evidence/Example: _______________________________")
            lines.append("")
        lines.append("\nReflection Questions:")
        lines.append("  1. What am I most proud of?")
        lines.append("  2. What was my biggest challenge?")
        lines.append("  3. What will I do differently next time?")
        return {"success": True, "result": "\n".join(lines)}


class HomeworkHelperTool(BaseTool):
    def execute(self, params):
        subject = params.get("subject", params.get("topic", "math")).lower()
        question = params.get("question", params.get("problem", "")).strip()
        if not question:
            # Generate guidance for common subjects
            guides = {
                "math": [
                    "1. Read the problem carefully — what are you being asked to find?",
                    "2. Identify what information is given and what's missing",
                    "3. Choose the right formula or approach",
                    "4. Solve step by step, showing all work",
                    "5. Check your answer — does it make sense?"],
                "science": [
                    "1. State your hypothesis clearly",
                    "2. Identify variables: independent, dependent, controlled",
                    "3. Design a procedure that tests only one variable at a time",
                    "4. Record all observations, even unexpected ones",
                    "5. Draw conclusions based on evidence, not assumptions"],
                "writing": [
                    "1. Start with a strong thesis statement",
                    "2. Outline 3 main body paragraphs with topic sentences",
                    "3. Use evidence from sources to support each point",
                    "4. Address counterarguments to strengthen your position",
                    "5. Conclude by restating your thesis and its significance"],
                "history": [
                    "1. Identify the who, what, when, where, and why",
                    "2. Consider multiple perspectives on the event",
                    "3. Look for cause-and-effect relationships",
                    "4. Connect to broader themes or patterns",
                    "5. Evaluate primary vs secondary sources"],
            }
            lines = [f"Homework Help: {subject.title()}", "=" * 40,
                     "General Study Tips:\n"]
            guide = guides.get(subject, guides["math"])
            lines.extend(guide)
            return {"success": True, "result": "\n".join(lines)}
        lines = [f"Homework Help: {subject.title()}", "=" * 40,
                 f"Question: {question}", "",
                 "Step-by-step guidance:",
                 "  1. Understand what the question is asking",
                 "  2. Break the problem into smaller parts",
                 f"  3. Apply {subject} principles and formulas",
                 "  4. Work through each part carefully",
                 "  5. Verify your answer",
                 "",
                 "Tip: Try explaining the problem to someone else —",
                 "it helps clarify your thinking!"]
        return {"success": True, "result": "\n".join(lines)}


class FlashcardReviewTool(BaseTool):
    def execute(self, params):
        path = os.path.join(_STUDY_DIR, "flashcards.json")
        deck = params.get("deck", "default")
        count = min(int(params.get("count", 10)), 50)
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    cards = json.load(f)
            else:
                cards = []
            pool = [c for c in cards if c.get("deck", "default") == deck]
            if not pool:
                return {"success": False, "result": f"No cards in deck '{deck}'"}
            # Prioritize cards in lower boxes (spaced repetition)
            pool.sort(key=lambda c: c.get("box", 0))
            session = pool[:count]
            random.shuffle(session)
            lines = [f"Spaced Repetition: '{deck}' ({len(session)} cards)", "=" * 40, ""]
            for i, card in enumerate(session, 1):
                box = card.get("box", 0)
                box_label = {0: "New", 1: "Review 1d", 2: "Review 3d", 3: "Review 7d",
                             4: "Review 14d", 5: "Review 30d"}.get(box, f"Box {box}")
                lines.append(f"Card {i} [{box_label}]:")
                lines.append(f"  Q: {card['question']}")
                lines.append(f"  A: ||{card['answer']}||")
                lines.append("")
            return {"success": True, "result": "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"Review error: {e}"}


class TestReviewTool(BaseTool):
    def execute(self, params):
        subject = params.get("subject", params.get("topic", "the subject")).strip()
        topics_str = params.get("topics", "")
        topics = [t.strip() for t in topics_str.split(",") if t.strip()]
        if not topics:
            topics = [f"Key {subject} concepts", f"Important {subject} terms",
                      f"{subject} formulas/equations", f"Common {subject} problems",
                      f"{subject} examples and applications"]
        lines = [f"Test Review: {subject.title()}", "=" * 40, "",
                 "Format: [ ] Multiple Choice  [ ] Short Answer  [ ] Essay  [ ] Problems\n"]
        lines.append("Study Checklist:")
        for t in topics:
            lines.append(f"  ☐ {t}")
            lines.append(f"    - Review notes and textbook")
            lines.append(f"    - Practice related problems")
            lines.append(f"    - Create flashcards for key terms")
            lines.append("")
        lines.append("Key Concepts to Review:")
        for i, t in enumerate(topics, 1):
            lines.append(f"  {i}. {t}")
        lines.append("\nPractice Problems:")
        for i in range(3):
            a, b = random.randint(2, 20), random.randint(2, 10)
            lines.append(f"  {i+1}. Solve: {a} × {b} + {random.randint(1, 10)} = ?")
        lines.append("\nStudy Tips:")
        lines.append("  • Review over multiple days (don't cram)")
        lines.append("  • Teach concepts to a study partner")
        lines.append("  • Get 8 hours of sleep before the test")
        return {"success": True, "result": "\n".join(lines)}


class ClassroomGameTool(BaseTool):
    def execute(self, params):
        subject = params.get("subject", params.get("topic", "any subject")).strip()
        duration = int(params.get("minutes", params.get("duration", 15)))
        count = min(int(params.get("count", 3)), 8)
        games = [
            {
                "name": "Quiz Bowl",
                "desc": f"Teams compete answering {subject} questions. First team to buzz in gets a point.",
                "setup": "Prepare 20+ questions in advance. Use a buzzer system or raise hands.",
            },
            {
                "name": "Jeopardy!",
                "desc": f"Categories based on {subject} topics with point values. Teams choose and answer.",
                "setup": "Create a 5×5 grid with questions at 100-500 point values.",
            },
            {
                "name": "Pictionary",
                "desc": f"Students draw {subject} concepts while teammates guess.",
                "setup": "Prepare cards with key terms. 60-second rounds per drawing.",
            },
            {
                "name": "Who Wants to Be a Millionaire?",
                "desc": f"Progressive difficulty {subject} questions with lifelines (50/50, ask the class).",
                "setup": "15 questions ranging from easy to very hard.",
            },
            {
                "name": "Escape Room",
                "desc": f"Solve {subject} puzzles to unlock the next clue. First team to escape wins!",
                "setup": "5-7 puzzles/challenges with a lock combination to escape.",
            },
            {
                "name": "Scavenger Hunt",
                "desc": f"Find items or information related to {subject} around the classroom or school.",
                "setup": "Create a list of 15-20 items with {subject}-related clues.",
            },
            {
                "name": "Board Race",
                "desc": f"Two teams race to write answers to {subject} questions on the board.",
                "setup": "Prepare questions. One student from each team writes the answer.",
            },
            {
                "name": "Memory Match",
                "desc": f"Match {subject} terms with their definitions in a card-flip game.",
                "setup": "Create 15-20 pairs of term-definition cards.",
            },
        ]
        random.shuffle(games)
        lines = [f"Classroom Games: {subject}", "=" * 40, f"Time available: {duration} min\n"]
        for i, game in enumerate(games[:count], 1):
            lines.append(f"Game {i}: {game['name']}")
            lines.append(f"  {game['desc']}")
            lines.append(f"  Setup: {game['setup']}")
            lines.append("")
        return {"success": True, "result": "\n".join(lines)}


class GoalSetterTool(BaseTool):
    def execute(self, params):
        subject = params.get("subject", params.get("topic", "academics")).strip()
        count = min(int(params.get("count", 3)), 8)
        period = params.get("period", params.get("timeframe", "this semester"))
        lines = [f"SMART Goals: {subject.title()}", "=" * 40,
                 f"Student: ____________________  Period: {period}\n",
                 "A SMART goal is:\n",
                 "  S — Specific (clear and precise)",
                 "  M — Measurable (can track progress)",
                 "  A — Achievable (realistic but challenging)",
                 "  R — Relevant (connected to your learning)",
                 "  T — Time-bound (has a deadline)\n",
                 f"My {subject.title()} Goals for {period}:\n"]
        goal_templates = [
            f"I will improve my {subject} grade by earning at least {random.choice(['85','90','93'])}% "
            f"on all remaining {subject} assignments.",
            f"I will complete all {subject} homework on time, submitting at least {random.choice(['90','95','100'])}% "
            f"by the deadline.",
            f"I will spend at least {random.choice(['30','45','60'])} minutes each day reviewing {subject} material "
            f"and taking notes.",
            f"I will participate actively in {subject} class by asking at least {random.choice(['2','3','5'])} "
            f"questions per week.",
            f"I will form a {subject} study group and meet {random.choice(['weekly','twice a week'])} "
            f"to review material together.",
            f"I will complete all extra credit {subject} opportunities to raise my understanding and grade.",
            f"I will visit office hours or tutoring at least {random.choice(['twice a month','once a week'])} "
            f"for {subject} help.",
            f"I will achieve at least {random.choice(['proficient','advanced'])} level on the {subject} assessment.",
        ]
        random.shuffle(goal_templates)
        for i, template in enumerate(goal_templates[:count], 1):
            lines.append(f"Goal {i}:")
            lines.append(f"  {template}")
            lines.append(f"  Action steps:")
            lines.append(f"    1. ________________________________")
            lines.append(f"    2. ________________________________")
            lines.append(f"    3. ________________________________")
            lines.append(f"  Check-in date: ____________________")
            lines.append("")
        return {"success": True, "result": "\n".join(lines)}


class FieldTripTool(BaseTool):
    def execute(self, params):
        destination = params.get("destination", params.get("location", "a local museum")).strip()
        subject = params.get("subject", params.get("topic", "science")).strip()
        duration_hours = int(params.get("hours", params.get("duration", 4)))
        grade = params.get("grade", params.get("level", "middle school"))
        lines = [f"Field Trip Plan: {destination}", "=" * 40,
                 f"Subject: {subject.title()} | Grade: {grade}",
                 f"Duration: {duration_hours} hours\n",
                 "Pre-Trip Preparation:",
                 "  ☐ Permission slips sent home (due 2 weeks before)",
                 "  ☐ Chaperones confirmed (1 per 5 students)",
                 "  ☐ Transportation arranged",
                 "  ☐ Emergency contact list prepared",
                 "  ☐ First aid kit packed",
                 "  ☐ Lesson objectives shared with students\n",
                 "Learning Objectives:",
                 f"  • Connect {subject} concepts to real-world at {destination}",
                 f"  • Observe and document key {subject} phenomena",
                 "  • Practice scientific observation and note-taking\n",
                 "Schedule:",
                 f"  {8:00d}:00 AM — Depart from school",
                 f"  {9:00d}:00 AM — Arrive & orientation",
                 f"  {9:30d}:00 AM — Guided tour/activity",
                 f"  12:00 PM — Lunch break",
                 f"  1:00 PM — Self-guided exploration / worksheet",
                 f"  {2:30d}:00 PM — Depart for school\n",
                 "Student Activities:",
                 "  • Observation worksheet (complete during visit)",
                 "  • Sketch 3 things you learned",
                 "  • Write 5 questions for discussion\n",
                 "Follow-Up Assignment:",
                 f"  Write a 1-page reflection on how {destination} connects to what we learned about {subject}.",
        ]
        return {"success": True, "result": "\n".join(lines)}


class CaseStudyTool(BaseTool):
    def execute(self, params):
        title = params.get("title", params.get("case", "Case Study")).strip()
        subject = params.get("subject", params.get("topic", ""))
        lines = [f"Case Study Analysis: {title}", "=" * 40,
                 f"Subject: {subject or 'General'}\n",
                 "1. Case Summary",
                 f"   Briefly describe the {title} case:",
                 "   • Who is involved?",
                 "   • What happened?",
                 "   • When and where?",
                 "   • Why is this significant?\n",
                 "2. Background / Context",
                 "   • Historical background",
                 "   • Relevant factors (social, economic, political)",
                 "   • Key stakeholders\n",
                 "3. Problem Identification",
                 "   • What are the main issues?",
                 "   • What are the underlying causes?",
                 "   • Who is affected and how?\n",
                 "4. Analysis Framework",
                 f"   • Apply relevant {subject or 'theoretical'} concepts",
                 "   • Identify patterns and relationships",
                 "   • Consider multiple perspectives\n",
                 "5. Alternatives Considered",
                 "   Option A: ______________________________",
                 "     Pros: ______________________________",
                 "     Cons: ______________________________",
                 "   Option B: ______________________________",
                 "     Pros: ______________________________",
                 "     Cons: ______________________________\n",
                 "6. Recommendation",
                 "   • Which option is best and why?",
                 "   • Implementation plan",
                 "   • Expected outcomes\n",
                 "7. Lessons Learned",
                 "   • What does this case teach us?",
                 "   • How can we apply these lessons?",
        ]
        return {"success": True, "result": "\n".join(lines)}


class NoteTemplateTool(BaseTool):
    def execute(self, params):
        style = params.get("style", params.get("format", "cornell")).lower()
        topic = params.get("topic", params.get("subject", "Lecture"))
        lines = [f"Note-Taking Template: {style.title()} Style", "=" * 40,
                 f"Topic: {topic}\n"]
        if style == "cornell":
            lines.extend([
                "+" + "-" * 30 + "+" + "-" * 40 + "+",
                f"| {'Cue Column':30s} | {'Notes Column':40s} |",
                f"| {'Questions/Main Ideas':30s} | {'Detailed notes from lecture':40s} |",
                "+" + "-" * 30 + "+" + "-" * 40 + "+",
                "|                               |                                        |",
                "|  1. Key question:             |  • Main point 1:                      |",
                "|                               |    - Detail:                          |",
                "|                               |    - Detail:                          |",
                "|                               |                                        |",
                "|  2. Key question:             |  • Main point 2:                      |",
                "|                               |    - Detail:                          |",
                "|                               |    - Detail:                          |",
                "|                               |                                        |",
                "|  3. Key question:             |  • Main point 3:                      |",
                "|                               |    - Detail:                          |",
                "|                               |    - Detail:                          |",
                "+" + "-" * 30 + "+" + "-" * 40 + "+",
                f"| {'Summary (bottom):':73s} |",
                f"| {'3-5 sentence summary of the page':73s} |",
                "+" + "-" * 73 + "+",
            ])
        elif style == "outline":
            lines.extend([
                f"I. {topic} Overview",
                "   A. Main concept 1",
                "      1. Supporting detail",
                "      2. Supporting detail",
                "   B. Main concept 2",
                "      1. Supporting detail",
                "      2. Supporting detail",
                f"II. Key {topic} Ideas",
                "   A. Key idea 1",
                "      1. Example / evidence",
                "      2. Example / evidence",
                "   B. Key idea 2",
                "      1. Example / evidence",
                "      — Important note or exception",
                "III. Summary & Questions",
                "   A. What I learned:",
                "   B. Questions I still have:",
            ])
        elif style == "mapping":
            lines.extend([
                f"                         [{topic}]",
                "                        /    |    \\",
                "                       /     |     \\",
                "              [Sub 1]    [Sub 2]    [Sub 3]",
                "             /   |   \\   / | \\     / | \\",
                "          [D]  [D] [D] [D] [D] [D] [D] [D] [D]",
                "",
                "Connections:",
                "  • Sub 1 → Sub 2: relationship",
                "  • Sub 2 → Sub 3: relationship",
                "  • Key insights:",
            ])
        else:
            lines.append(f"Styles: cornell, outline, mapping")
        lines.append("\nReview Tips:")
        lines.append("  • Review notes within 24 hours")
        lines.append("  • Summarize each page in your own words")
        lines.append("  • Connect new information to what you already know")
        return {"success": True, "result": "\n".join(lines)}


class StudyBreakTool(BaseTool):
    def execute(self, params):
        count = min(int(params.get("count", 5)), 15)
        duration = int(params.get("minutes", params.get("duration", 5)))
        activities = [
            ("Stretch Break", "Stand up and stretch your arms, neck, and back. Reach for the sky for 10 seconds."),
            ("Deep Breathing", "Inhale for 4 counts, hold for 4, exhale for 4. Repeat 5 times."),
            ("Walk Around", "Walk around the room or house for 2 minutes. Look at something far away to rest your eyes."),
            ("Water Refill", "Drink a glass of water. Dehydration causes fatigue and reduces focus."),
            ("Doodle", "Take 30 seconds to doodle anything on your notebook margin."),
            ("Power Pose", "Stand like a superhero for 2 minutes — it boosts confidence and energy."),
            ("Eye Rest", "Close your eyes for 60 seconds. Visualize a calm, peaceful place."),
            ("Shoulder Rolls", "Roll your shoulders forward 5 times, backward 5 times. Release tension."),
            ("Positive Affirmation", "Tell yourself: 'I am focused, capable, and making progress.'"),
            ("Quick Stretch", "Touch your toes, hold for 15 seconds. Then lean back, arching gently."),
            ("Snack Time", "Eat a healthy snack — nuts, fruit, or yogurt. Avoid sugar crashes."),
            ("Brain Game", "Name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, 1 you can taste."),
            ("Desk Organize", "Spend 60 seconds tidying your workspace. A clean desk = a clear mind."),
            ("Listen to Music", "Put on one song you love. Sing along if you want! Music resets your mood."),
            ("Progressive Relaxation", "Tense your toes for 5 seconds, then release. Work up to your face — tense and release each muscle group."),
        ]
        random.shuffle(activities)
        lines = [f"Study Break Ideas", "=" * 40,
                 f"Each activity: ~{duration} minutes\n"]
        for i, (name, desc) in enumerate(activities[:count], 1):
            lines.append(f"{i}. {name}")
            lines.append(f"   {desc}")
            lines.append("")
        lines.append("The Pomodoro Method: 25 min study + 5 min break, repeat 4× then take a longer break.")
        return {"success": True, "result": "\n".join(lines)}


class PortScannerTool(BaseTool):
    COMMON_PORTS = [(21, "FTP"), (22, "SSH"), (23, "Telnet"), (25, "SMTP"),
                    (53, "DNS"), (80, "HTTP"), (110, "POP3"), (143, "IMAP"), (443, "HTTPS"), (445, "SMB"),
                    (993, "IMAPS"), (995, "POP3S"), (1433, "MSSQL"), (1521, "Oracle"),
                    (2049, "NFS"), (3306, "MySQL"), (3389, "RDP"), (5432, "PostgreSQL"),
                    (5900, "VNC"), (6379, "Redis"), (8080, "HTTP-Proxy"), (8443, "HTTPS-Alt"),
                    (27017, "MongoDB"), (11211, "Memcached")]

    def execute(self, params):
        host = params.get("host", params.get("target", ""))
        if not host:
            return {"success": False, "result": "Provide target host"}
        port_str = params.get("ports", "")
        timeout_f = max(0.5, min(float(params.get("timeout", 2)), 10))
        if port_str:
            try:
                ports = [int(p.strip()) for p in port_str.split(",") if p.strip()]
            except ValueError:
                return {"success": False, "result": "Invalid port list"}
        else:
            ports = [p[0] for p in self.COMMON_PORTS]
        try:
            target_ip = socket.gethostbyname(host)
        except socket.gaierror:
            return {"success": False, "result": f"Cannot resolve {host}"}
        open_ports = []
        for port in ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout_f)
                result = s.connect_ex((target_ip, port))
                s.close()
                if result == 0:
                    service = next((svc for p, svc in self.COMMON_PORTS if p == port), "Unknown")
                    open_ports.append(f"  {port}/tcp  {service}")
            except Exception:
                pass
        if open_ports:
            return {"success": True, "result": f"Open ports on {host} ({target_ip}):\n" + "\n".join(open_ports)}
        return {"success": True, "result": f"No open ports found on {host} ({target_ip}) among {len(ports)} scanned"}


class SubdomainEnumTool(BaseTool):
    _WORDLIST = ["www", "mail", "ftp", "admin", "blog", "shop", "api", "cdn", "dev", "test",
                 "webmail", "support", "vpn", "m", "mobile", "app", "portal", "secure", "beta",
                 "demo", "stage", "backup", "dns", "ns1", "ns2", "smtp", "pop", "imap",
                 "remote", "git", "jenkins", "jira", "confluence", "wiki", "help", "forum",
                 "docs", "status", "stats", "analytics", "tracking", "images", "static",
                 "assets", "video", "media", "download", "upload", "cloud", "proxy"]

    def execute(self, params):
        domain = params.get("domain", params.get("target", "")).strip()
        if not domain:
            return {"success": False, "result": "Provide a domain"}
        wordlist_str = params.get("wordlist", "")
        wordlist = [w.strip() for w in wordlist_str.split(",") if w.strip()] if wordlist_str else self._WORDLIST
        timeout_f = max(1, min(float(params.get("timeout", 3)), 10))
        found = []
        for sub in wordlist:
            try:
                hostname = f"{sub}.{domain}"
                ip = socket.gethostbyname(hostname)
                found.append(f"  {hostname} → {ip}")
            except socket.gaierror:
                pass
        if found:
            return {"success": True, "result": f"Subdomains of {domain} ({len(found)} found):\n" + "\n".join(found)}
        return {"success": True, "result": f"No subdomains found for {domain} using {len(wordlist)} names"}


class WhoisTool(BaseTool):
    SERVER = "whois.iana.org"

    def execute(self, params):
        query = params.get("domain", params.get("target", "")).strip()
        if not query:
            return {"success": False, "result": "Provide a domain or IP"}
        try:
            whois_server = self.SERVER
            if query.count(".") >= 1:
                tld = query.split(".")[-1]
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(5)
                    s.connect(("whois.iana.org", 43))
                    s.send(f"{tld}\r\n".encode())
                    resp = b""
                    while True:
                        d = s.recv(4096)
                        if not d:
                            break
                        resp += d
                    s.close()
                    text = resp.decode("utf-8", errors="replace")
                    m = re.search(r'whois:\s*(\S+)', text)
                    if m:
                        whois_server = m.group(1)
                except Exception:
                    whois_server = f"whois.{tld}"
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((whois_server, 43))
            s.send(f"{query}\r\n".encode())
            resp = b""
            while True:
                d = s.recv(4096)
                if not d:
                    break
                resp += d
            s.close()
            text = resp.decode("utf-8", errors="replace")[:3000]
            if not text.strip():
                return {"success": True, "result": "No WHOIS data available"}
            lines = [f"WHOIS: {query}", "=" * 40]
            for line in text.split("\n")[:40]:
                line = line.strip()
                if line and not line.startswith("%") and not line.startswith("#"):
                    lines.append(f"  {line}")
            return {"success": True, "result": "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"WHOIS lookup error: {e}"}


class SSLInspectorTool(BaseTool):
    def execute(self, params):
        host = params.get("host", params.get("target", "")).strip()
        port = int(params.get("port", 443))
        if not host:
            return {"success": False, "result": "Provide a hostname"}
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = True
            ctx.verify_mode = ssl.CERT_REQUIRED
            with socket.create_connection((host, port), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    if not cert:
                        return {"success": False, "result": "No certificate returned"}
                    lines = [f"SSL Certificate: {host}:{port}", "=" * 40]
                    lines.append(f"Subject: {dict(cert.get('subject', [])).get('commonName', 'N/A')}")
                    lines.append(f"Issuer: {dict(cert.get('issuer', [])).get('organizationName', 'N/A')}")
                    lines.append(f"Version: {cert.get('version', 'N/A')}")
                    lines.append(f"Serial: {cert.get('serialNumber', 'N/A')}")
                    lines.append(f"Valid From: {cert.get('notBefore', 'N/A')}")
                    lines.append(f"Valid Until: {cert.get('notAfter', 'N/A')}")
                    sans = cert.get('subjectAltName', [])
                    if sans:
                        lines.append(f"Subject Alt Names: {', '.join(s[1] for s in sans[:10])}")
                    lines.append(f"SSL: {'TLSv1.3' if ssock.version() == 'TLSv1.3' else ssock.version()}")
                    try:
                        cipher = ssock.cipher()
                        if cipher:
                            lines.append(f"Cipher: {cipher[0]}")
                    except Exception:
                        pass
                    return {"success": True, "result": "\n".join(lines)}
        except ssl.SSLCertVerificationError as e:
            return {"success": True, "result": f"SSL cert verification: {e}"}
        except Exception as e:
            return {"success": False, "result": f"SSL error: {e}"}


class HTTPHeadersTool(BaseTool):
    SECURITY_HEADERS = {
        "Strict-Transport-Security": "HSTS — enforces HTTPS",
        "Content-Security-Policy": "CSP — prevents XSS/clickjack",
        "X-Frame-Options": "Prevents clickjacking",
        "X-Content-Type-Options": "Prevents MIME sniffing",
        "X-XSS-Protection": "XSS filter (deprecated but still used)",
        "Referrer-Policy": "Controls referrer info leakage",
        "Permissions-Policy": "Controls browser features",
        "Set-Cookie": "Check for HttpOnly/Secure/SameSite flags",
    }

    def execute(self, params):
        url = params.get("url", params.get("target", "")).strip()
        if not url:
            return {"success": False, "result": "Provide a URL (with http:// or https://)"}
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                headers = dict(resp.headers)
            lines = [f"HTTP Security Headers: {url}", "=" * 40, f"Status: {resp.status}", ""]
            missing = []
            for hdr, desc in self.SECURITY_HEADERS.items():
                value = headers.get(hdr, headers.get(hdr.lower(), ""))
                if value:
                    lines.append(f"  ✓ {hdr}: {value[:80]}")
                else:
                    lines.append(f"  ✗ {hdr} — MISSING ({desc})")
                    missing.append(hdr)
            lines.append(f"\nServer: {headers.get('Server', 'N/A')}")
            lines.append(f"X-Powered-By: {headers.get('X-Powered-By', 'N/A')}")
            lines.append(f"\nScore: {len(self.SECURITY_HEADERS) - len(missing)}/{len(self.SECURITY_HEADERS)} security headers present")
            if missing:
                lines.append(f"Missing: {', '.join(missing)}")
            return {"success": True, "result": "\n".join(lines)}
        except urllib.error.HTTPError as e:
            return {"success": False, "result": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "result": f"Headers error: {e}"}


class URLAnalyzerTool(BaseTool):
    SUSPICIOUS_TLDS = [".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".club", ".work",
                       ".bid", ".cam", ".click", ".download", ".review", ".stream", ".trade"]
    PHISHING_KEYWORDS = ["login", "verify", "account", "update", "confirm", "secure", "bank",
                         "paypal", "amazon", "apple", "google", "microsoft", "netflix", "password",
                         "credential", "support", "signin", "auth", "authenticate", "reset"]

    def execute(self, params):
        url = params.get("url", params.get("target", "")).strip()
        if not url:
            return {"success": False, "result": "Provide a URL to analyze"}
        url_lower = url.lower()
        parsed = urllib.parse.urlparse(url if "://" in url else "//" + url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        path = parsed.path + "?" + parsed.query if parsed.query else parsed.path
        warnings = []
        info = []
        # Check for IP instead of domain
        ip_match = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', domain.split(":")[0])
        if ip_match:
            warnings.append("URL uses raw IP address instead of domain name")
        # Check URL length
        if len(url) > 100:
            warnings.append(f"Unusually long URL ({len(url)} chars)")
        # Check for @ symbol
        if "@" in url_lower:
            warnings.append("Contains '@' — used to hide real domain")
        # Check for multiple subdomains
        subdomain_count = domain.count(".")
        if subdomain_count > 2:
            warnings.append(f"Many subdomains ({subdomain_count}) — could be deceptive")
        # Check suspicious TLDs
        for tld in self.SUSPICIOUS_TLDS:
            if url_lower.endswith(tld) or f".{tld}" in domain:
                warnings.append(f"Suspicious TLD: {tld}")
        # Check phishing keywords
        found_keywords = [k for k in self.PHISHING_KEYWORDS if k in url_lower]
        if found_keywords:
            warnings.append(f"Phishing keywords detected: {', '.join(found_keywords)}")
        # Check HTTPS
        if url_lower.startswith("http://"):
            warnings.append("No HTTPS — traffic is not encrypted")
        elif url_lower.startswith("https://"):
            info.append("Uses HTTPS (encrypted)")
        # Check for common typosquatting
        legit_domains = ["google", "facebook", "amazon", "microsoft", "apple", "paypal", "netflix"]
        for d in legit_domains:
            if d in domain and d != domain.split(".")[0]:
                warnings.append(f"Possible typosquatting — '{domain}' looks like '{d}'")
        # Domain age / info
        try:
            ip = socket.gethostbyname(domain.split(":")[0])
            info.append(f"Resolved IP: {ip}")
        except Exception:
            warnings.append("Domain does not resolve")
        lines = [f"URL Analysis: {url[:100]}", "=" * 40, f"Domain: {domain}", f"Path: {path[:80]}"]
        if warnings:
            lines.append(f"\n⚠ Warnings ({len(warnings)}):")
            for w in warnings:
                lines.append(f"  • {w}")
        else:
            lines.append("\n✓ No obvious red flags detected")
        if info:
            lines.append(f"\nInfo:")
            for i in info:
                lines.append(f"  • {i}")
        threat_level = "HIGH" if len(warnings) >= 3 else ("MEDIUM" if warnings else "LOW")
        lines.append(f"\nThreat Level: {threat_level}")
        return {"success": True, "result": "\n".join(lines)}


class IPReputationTool(BaseTool):
    def execute(self, params):
        ip = params.get("ip", params.get("target", "")).strip()
        if not ip:
            return {"success": False, "result": "Provide an IP address"}
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            return {"success": False, "result": "Invalid IP address format"}
        lines = [f"IP Reputation: {ip}", "=" * 40]
        try:
            ip_int = int(ip.replace(".", ""))
        except Exception:
            ip_int = 0
        private = ip.startswith(("10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
                                  "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                                  "172.26.", "172.27.", "172.28.", "172.29.", "172.30.",
                                  "172.31.", "192.168.", "127.", "169.254."))
        if private:
            lines.append("Type: Private/Reserved IP")
            lines.append("Threat: Local network only — not internet-routable")
            return {"success": True, "result": "\n".join(lines)}
        lines.append("Type: Public IP")
        # Try reverse DNS
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            lines.append(f"PTR: {hostname}")
        except Exception:
            pass
        # Check known malicious patterns
        known_bad_ranges = []
        for start, end, desc in known_bad_ranges:
            parts = start.split(".")
            # Simple range check
            if start <= ip <= end:
                lines.append(f"⚠ Listed in known threat range: {desc}")
        try:
            req = urllib.request.Request(f"https://ipapi.co/{ip}/json/",
                                         headers={"User-Agent": "JARVIS/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            org = data.get("org", data.get("asn", ""))
            country = data.get("country_name", "")
            city = data.get("city", "")
            isp = data.get("isp", "")
            if org:
                lines.append(f"Organization: {org}")
            if country:
                lines.append(f"Country: {country}{', ' + city if city else ''}")
            if isp:
                lines.append(f"ISP: {isp}")
        except Exception:
            pass
        lines.append("\nRecommendation: Check abuseipdb.com or virustotal.com for detailed reports")
        return {"success": True, "result": "\n".join(lines)}


class CVESearchTool(BaseTool):
    def execute(self, params):
        keyword = params.get("keyword", params.get("query", "")).strip()
        cve_id = params.get("cve", "").strip().upper()
        if not keyword and not cve_id:
            return {"success": False, "result": "Provide a keyword (e.g., 'apache log4j') or CVE ID (e.g., CVE-2021-44228)"}
        try:
            if cve_id:
                url = f"https://cve.circl.lu/api/cve/{cve_id}"
            else:
                url = f"https://cve.circl.lu/api/last/{10}"
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read())
            if cve_id:
                lines = [f"CVE: {cve_id}", "=" * 40]
                lines.append(f"Description: {data.get('description', 'N/A')[:500]}")
                lines.append(f"CVSS Score: {data.get('cvss', 'N/A')}")
                lines.append(f"Severity: {data.get('access', {}).get('complexity', 'N/A')}")
                lines.append(f"Published: {data.get('Published', 'N/A')}")
                lines.append(f"Modified: {data.get('Modified', 'N/A')}")
                refs = data.get('references', [])
                if refs:
                    lines.append(f"References: {len(refs)}")
                    for r in refs[:5]:
                        lines.append(f"  • {r[:100]}")
                return {"success": True, "result": "\n".join(lines)}
            else:
                if not isinstance(data, list):
                    data = []
                results = []
                for item in data:
                    cid = item.get('id', '')
                    desc = item.get('description', '')[:150]
                    if keyword.lower() in desc.lower() or keyword.lower() in cid.lower():
                        results.append(f"  {cid}: {desc}")
                if results:
                    return {"success": True, "result": f"Recent CVEs for '{keyword}':\n" + "\n".join(results)}
                return {"success": True, "result": f"No recent CVEs found for '{keyword}'"}
        except Exception as e:
            return {"success": False, "result": f"CVE search error: {e}"}


class DNSEnumTool(BaseTool):
    RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME", "PTR"]

    def execute(self, params):
        domain = params.get("domain", params.get("target", "")).strip()
        types_str = params.get("types", "")
        if not domain:
            return {"success": False, "result": "Provide a domain"}
        types = [t.strip().upper() for t in types_str.split(",") if t.strip()] if types_str else self.RECORD_TYPES
        lines = [f"DNS Enumeration: {domain}", "=" * 40]
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.timeout = 5
            resolver.lifetime = 5
            for rtype in types:
                try:
                    answers = resolver.resolve(domain, rtype)
                    lines.append(f"\n{rtype} Records:")
                    for r in answers:
                        lines.append(f"  {r}")
                except dns.resolver.NoAnswer:
                    lines.append(f"\n{rtype}: No records found")
                except dns.resolver.NXDOMAIN:
                    lines.append(f"\n{rtype}: Domain does not exist")
                except Exception as e:
                    lines.append(f"\n{rtype}: {e}")
        except ImportError:
            # Fallback to socket/dig
            lines.append("\n(A) Address Records:")
            try:
                addrs = socket.getaddrinfo(domain, 0, socket.AF_INET)
                seen = set()
                for addr in addrs:
                    ip = addr[4][0]
                    if ip not in seen:
                        lines.append(f"  {ip}")
                        seen.add(ip)
            except Exception:
                lines.append("  Could not resolve")
            lines.append("\nTip: Install 'dnspython' for full DNS enumeration (MX, NS, TXT, SOA, etc.)")
        return {"success": True, "result": "\n".join(lines)}


class MACVendorTool(BaseTool):
    _OUIS = {
        "00:00:0C": "Cisco", "00:13:46": "Dell", "00:1A:A0": "HP",
        "00:1B:21": "Dell", "00:21:5A": "Intel", "00:22:41": "Apple",
        "00:23:32": "Apple", "00:24:36": "Intel", "00:25:00": "Apple",
        "00:26:08": "Dell", "00:26:4A": "Juniper", "00:26:BB": "Cisco",
        "00:30:48": "Dell", "00:50:56": "VMware", "00:50:79": "VMware",
        "00:55:DA": "Apple", "04:4B:ED": "Samsung", "08:00:27": "Oracle/VirtualBox",
        "08:00:46": "Intel", "08:74:02": "Apple", "0C:9D:92": "Broadcom",
        "10:08:B1": "HP", "14:10:9F": "Apple", "18:66:DA": "Apple",
        "1C:B0:44": "Dell", "20:C9:D0": "Apple", "24:4B:FE": "Dell",
        "28:F0:76": "Apple", "2C:33:61": "Apple", "2C:54:CF": "Intel",
        "30:46:9A": "Apple", "34:15:9E": "HP", "3C:07:54": "Intel",
        "3C:D9:2B": "HP", "40:8D:5C": "Intel", "44:38:39": "Cisco",
        "44:45:53": "ESP", "48:45:20": "Intel", "4C:32:75": "Dell",
        "50:3E:AA": "Cisco", "54:33:CB": "Intel", "54:52:00": "Linux Foundation",
        "58:55:CA": "Apple", "5C:26:0A": "Dell", "60:57:18": "Cisco",
        "64:9E:F3": "Dell", "68:05:CA": "Intel", "6C:2B:59": "Intel",
        "6C:3B:6B": "Google", "70:4D:7B": "Apple", "74:00:00": "Google",
        "78:31:C1": "Cisco", "7C:05:07": "Intel", "80:00:0B": "HP",
        "84:7B:5B": "Intel", "88:66:5A": "HP", "8C:85:90": "Intel",
        "90:0C:A7": "Apple", "94:65:2D": "Apple", "98:01:A7": "Dell",
        "9C:2E:A1": "Cisco", "A0:99:9B": "Intel", "A4:5E:60": "Dell",
        "A8:20:66": "HP", "AC:BC:32": "Apple", "B0:6C:BF": "Intel",
        "B4:2E:99": "Intel", "B8:27:EB": "Raspberry Pi", "BC:5F:F4": "Cisco",
        "C0:25:A5": "Apple", "C8:69:CD": "Intel", "CC:2F:71": "Dell",
        "D0:37:45": "Apple", "D4:61:2C": "HP", "D8:5D:E2": "Intel",
        "DC:FB:02": "Apple", "E0:2A:82": "Intel", "E0:AC:CB": "Apple",
        "E4:A7:A0": "Dell", "E8:50:8B": "Cisco", "EC:F0:0E": "Apple",
        "F0:18:98": "Microsoft", "F4:4E:05": "Dell", "F8:FF:C2": "Apple",
        "FC:AA:14": "Cisco", "FE:FF:FF": "Local", "00:1A:11": "Google",
        "00:25:90": "Microsoft", "00:26:AB": "Intel", "34:DE:1A": "Intel",
        "40:B0:FA": "Intel", "50:F5:DA": "Apple", "A0:ED:CD": "Intel",
        "B0:7D:64": "Apple", "C8:B3:A7": "Apple", "E8:B2:AC": "Intel",
        "F0:27:65": "Synology", "F4:4D:30": "Intel", "00:1E:C2": "Apple",
    }

    def execute(self, params):
        mac = params.get("mac", params.get("address", "")).strip().upper()
        if not mac:
            return {"success": False, "result": "Provide a MAC address (e.g., 00:1A:2B:3C:4D:5E)"}
        mac_clean = re.sub(r'[^A-F0-9]', '', mac)
        if len(mac_clean) != 12:
            return {"success": False, "result": "MAC address must be 6 hex bytes (12 hex digits)"}
        oui = ":".join(mac_clean[i:i+2] for i in range(0, 6, 2))
        oui_prefix = mac_clean[:6]
        vendor = self._OUIS.get(oui, self._OUIS.get(oui_prefix, "Unknown"))
        formatted = ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
        return {"success": True, "result":
                f"MAC: {formatted}\nOUI: {oui}\nVendor: {vendor}\n"
                f"Type: {'Unicast' if int(mac_clean[1], 16) % 2 == 0 else 'Multicast'}\n"
                f"Global: {'Yes' if int(mac_clean[0], 16) & 2 == 0 else 'Local (not globally unique)'}"}


class FileAnalyzerTool(BaseTool):
    _MAGIC = {
        b'\x89PNG\r\n\x1a\n': "PNG Image", b'\xff\xd8\xff': "JPEG Image",
        b'GIF87a': "GIF Image", b'GIF89a': "GIF Image", b'%PDF': "PDF Document",
        b'PK\x03\x04': "ZIP Archive / Office Document", b'PK\x05\x06': "ZIP Archive (Empty)",
        b'\x1f\x8b\x08': "GZIP Archive", b'BZh': "BZIP2 Archive",
        b'\x1f\x9d': "TAR Archive (Compress)", b'\xfd7zXZ\x00': "XZ Archive",
        b'RIFF': "AVI / WAV (RIFF container)", b'MZ': "Windows Executable (PE)",
        b'\x7fELF': "ELF Binary (Linux)", b'!<arch>\n': "AR Archive",
        b'\xca\xfe\xba\xbe': "Java Class File", b'%!PS': "PostScript",
        b'{\\rtf': "RTF Document", b'\xef\xbb\xbf': "UTF-8 BOM Text",
        b'\xff\xfe': "UTF-16 LE Text", b'\xfe\xff': "UTF-16 BE Text",
        b'BM': "BMP Image", b'\x00\x00\x01\x00': "ICO Icon",
        b'Rar!\x1a\x07': "RAR Archive", b'\x1a\x45\xdf\xa3': "MKV/WebM Video",
        b'OggS': "OGG Container", b'\x00\x01\x00\x00\x00': "TTF Font",
    }

    def execute(self, params):
        action = params.get("action", "analyze")
        path = params.get("path", params.get("file", ""))
        if not path or not os.path.exists(path):
            return {"success": False, "result": "Provide a valid file path"}
        try:
            if action == "analyze":
                stat = os.stat(path)
                size = stat.st_size
                lines = [f"File Analysis: {os.path.basename(path)}", "=" * 40]
                lines.append(f"Path: {path}")
                lines.append(f"Size: {_format_size(size)} ({size:,} bytes)")
                lines.append(f"Modified: {_format_time(stat.st_mtime)}")
                with open(path, 'rb') as f:
                    header = f.read(16)
                # Detect magic bytes
                magic_detected = "Unknown"
                for sig, desc in self._MAGIC.items():
                    if header[:len(sig)] == sig:
                        magic_detected = desc
                        break
                lines.append(f"File Type: {magic_detected}")
                lines.append(f"Magic Bytes: {' '.join(f'{b:02x}' for b in header[:8])}")
                ext = os.path.splitext(path)[1].lower()
                lines.append(f"Extension: {ext or '(none)'}")
                # Entropy calculation
                with open(path, 'rb') as f:
                    data = f.read()
                entropy = 0.0
                if data:
                    freq = [0] * 256
                    for b in data:
                        freq[b] += 1
                    for f in freq:
                        if f > 0:
                            p = f / len(data)
                            entropy -= p * math.log2(p)
                lines.append(f"Entropy: {entropy:.3f} (max 8.0, higher = more random/encrypted)")
                if entropy > 7.5:
                    lines.append("  ⚠ High entropy — likely encrypted, compressed, or random data")
                elif entropy > 6.0:
                    lines.append("  Note: Moderate entropy")
                # Check for suspicious strings
                suspicious_strs = [b'<script>', b'eval(', b'base64_decode', b'exec(',
                                   b'system(', b'passthru(', b'shell_exec(', b'wget ',
                                   b'curl ', b'chmod +x', b'/etc/passwd', b'cmd.exe',
                                   b'powershell', b'Invoke-', b'MZ']
                found_suspicious = []
                for sig in suspicious_strs:
                    if sig in data[:min(len(data), 100000)]:
                        found_suspicious.append(sig.decode('utf-8', errors='replace'))
                if found_suspicious:
                    lines.append(f"\n⚠ Suspicious patterns: {', '.join(found_suspicious[:10])}")
                return {"success": True, "result": "\n".join(lines)}
            elif action == "strings":
                count = min(int(params.get("count", 50)), 200)
                min_len = int(params.get("min_len", 4))
                with open(path, 'rb') as f:
                    data = f.read()
                strings_list = re.findall(rb'[\x20-\x7e]{%d,}' % min_len, data)
                printable = []
                for s in strings_list:
                    try:
                        printable.append(s.decode('ascii'))
                    except Exception:
                        pass
                printable = printable[:count]
                lines = [f"Strings in {os.path.basename(path)} ({len(printable)} shown):"]
                for s in printable:
                    if s.strip():
                        lines.append(f"  {s[:120]}")
                return {"success": True, "result": "\n".join(lines)}
            return {"success": False, "result": "Actions: analyze, strings"}
        except Exception as e:
            return {"success": False, "result": f"File analysis error: {e}"}


class CipherTool(BaseTool):
    def execute(self, params):
        action = params.get("action", "caesar")
        text = params.get("text", "")
        shift = int(params.get("shift", 3))
        key_str = params.get("key", "key")
        if not text:
            return {"success": False, "result": "Provide text to encrypt/decrypt"}
        if action == "caesar":
            result = ""
            for c in text:
                if c.isalpha():
                    base = ord('A') if c.isupper() else ord('a')
                    result += chr((ord(c) - base + shift) % 26 + base)
                else:
                    result += c
            return {"success": True, "result": f"Caesar (shift={shift}):\n{text}\n→ {result}"}
        elif action == "rot13":
            result = text.translate(str.maketrans(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"))
            return {"success": True, "result": f"ROT13:\n{text}\n→ {result}"}
        elif action == "xor":
            key = key_str
            result_bytes = bytearray()
            for i, b in enumerate(text.encode('utf-8')):
                result_bytes.append(b ^ ord(key[i % len(key)]))
            try:
                result = result_bytes.decode('utf-8')
            except Exception:
                result = result_bytes.hex()
            return {"success": True, "result": f"XOR (key='{key}'):\n{text}\n→ {result}"}
        elif action == "vigenere":
            key = key_str.upper()
            if not key:
                return {"success": False, "result": "Provide a key for Vigenère"}
            result = ""
            ki = 0
            for c in text:
                if c.isalpha():
                    base = ord('A') if c.isupper() else ord('a')
                    shift_k = ord(key[ki % len(key)].upper()) - ord('A')
                    result += chr((ord(c) - base + shift_k) % 26 + base)
                    ki += 1
                else:
                    result += c
            return {"success": True, "result": f"Vigenère (key='{key}'):\n{text}\n→ {result}"}
        elif action == "atbash":
            result = ""
            for c in text:
                if c.isalpha():
                    base = ord('A') if c.isupper() else ord('a')
                    result += chr(base + (25 - (ord(c) - base)))
                else:
                    result += c
            return {"success": True, "result": f"Atbash:\n{text}\n→ {result}"}
        return {"success": False, "result": "Actions: caesar, rot13, xor, vigenere, atbash"}


class LogParserTool(BaseTool):
    def execute(self, params):
        text = params.get("text", params.get("log", ""))
        fmt = params.get("format", params.get("type", "auto")).lower()
        if not text:
            return {"success": False, "result": "Provide log text to parse"}
        lines = text.strip().split("\n")
        parsed = []
        if fmt in ("auto", "apache", "nginx", "web"):
            pattern = r'(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"([^"]*)"\s+(\d+)\s+(\S+)'
            for line in lines:
                m = re.match(pattern, line)
                if m:
                    parsed.append(f"IP: {m.group(1)} | [{m.group(2)}] | \"{m.group(3)}\" | {m.group(4)} | {m.group(5)}")
        if fmt in ("auto", "syslog"):
            pattern = r'(\w{3}\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+(\S+)(?:\s+(\S+))?\s+(.*)'
            for line in lines:
                m = re.match(pattern, line)
                if m:
                    parsed.append(f"[{m.group(1)}] {m.group(2)} {m.group(3)}: {m.group(5)}")
        if fmt in ("auto", "csv", "auth"):
            for line in lines:
                if "Failed password" in line:
                    m = re.search(r'FROM (\S+)', line)
                    ip = m.group(1) if m else "?"
                    m2 = re.search(r'for\s+(\S+)', line)
                    user = m2.group(1) if m2 else "?"
                    parsed.append(f"⚠ Failed auth: user={user} from={ip}")
                elif "Accepted password" in line:
                    m = re.search(r'for\s+(\S+)', line)
                    user = m.group(1) if m else "?"
                    m2 = re.search(r'FROM (\S+)', line)
                    ip = m2.group(1) if m2 else "?"
                    parsed.append(f"✓ Successful auth: user={user} from={ip}")
        if not parsed:
            parsed = [f"Log entry ({len(lines)} lines): Unable to auto-parse. Specify format=apache, syslog, or csv"]
        result_lines = [f"Log Analysis ({len(lines)} lines, {len(parsed)} parsed):", "=" * 40]
        result_lines.extend(parsed[:30])
        if len(parsed) > 30:
            result_lines.append(f"... and {len(parsed) - 30} more entries")
        return {"success": True, "result": "\n".join(result_lines)}


class NetworkMapperTool(BaseTool):
    def execute(self, params):
        subnet = params.get("subnet", params.get("target", "")).strip()
        timeout_f = max(1, min(float(params.get("timeout", 2)), 10))
        if not subnet:
            return {"success": False, "result": "Provide subnet (e.g., 192.168.1.0/24)"}
        try:
            import ipaddress
            network = ipaddress.ip_network(subnet, strict=False)
        except Exception:
            return {"success": False, "result": f"Invalid subnet: {subnet}"}
        hosts = list(network.hosts())[:255]
        active = []
        for host in hosts[:50]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout_f)
                ip_str = str(host)
                # Try common ports to determine if host is up
                for port in [80, 443, 22, 445, 135]:
                    result = s.connect_ex((ip_str, port))
                    if result == 0:
                        try:
                            hostname = socket.gethostbyaddr(ip_str)[0]
                        except Exception:
                            hostname = ip_str
                        service = {80: "HTTP", 443: "HTTPS", 22: "SSH", 445: "SMB", 135: "RPC"}.get(port, str(port))
                        active.append(f"  {ip_str:16s}  {hostname:30s}  {service}")
                        break
                s.close()
            except Exception:
                pass
        lines = [f"Network Map: {subnet}", "=" * 40]
        if active:
            lines.append(f"Active hosts ({len(active)} found):")
            lines.append("  IP               Hostname                       Service")
            lines.append("  " + "-" * 60)
            lines.extend(active)
        else:
            lines.append("No active hosts found (scanned first 50 IPs)")
            lines.append("Tip: Increase timeout or specify a narrower range")
        return {"success": True, "result": "\n".join(lines)}


class UserEnumTool(BaseTool):
    _PLATFORMS = {
        "GitHub": "https://github.com/{user}",
        "Twitter/X": "https://twitter.com/{user}",
        "Reddit": "https://reddit.com/user/{user}",
        "Keybase": "https://keybase.io/{user}",
        "Instagram": "https://instagram.com/{user}",
        "Medium": "https://medium.com/@{user}",
        "PyPI": "https://pypi.org/user/{user}/",
        "HackerNews": "https://news.ycombinator.com/user?id={user}",
    }

    def execute(self, params):
        username = params.get("username", params.get("user", "")).strip()
        platforms_str = params.get("platforms", "")
        if not username:
            return {"success": False, "result": "Provide a username to search"}
        platforms = self._PLATFORMS
        if platforms_str:
            filtered = {}
            for p in platforms_str.split(","):
                p = p.strip()
                if p in self._PLATFORMS:
                    filtered[p] = self._PLATFORMS[p]
            if filtered:
                platforms = filtered
        lines = [f"Username Search: '{username}'", "=" * 40]
        for name, url in platforms.items():
            try:
                req = urllib.request.Request(url.format(user=username),
                                            headers={"User-Agent": "Mozilla/5.0"})
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                try:
                    with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                        if resp.status == 200:
                            lines.append(f"  ✓ {name}: Profile exists")
                        else:
                            lines.append(f"  ? {name}: Status {resp.status}")
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        lines.append(f"  ✗ {name}: Not found")
                    elif e.code == 403:
                        lines.append(f"  ? {name}: Blocked (403)")
                    else:
                        lines.append(f"  ? {name}: HTTP {e.code}")
                except urllib.error.URLError:
                    lines.append(f"  ? {name}: Connection failed")
            except Exception:
                lines.append(f"  ? {name}: Error")
        return {"success": True, "result": "\n".join(lines) + "\n\nOSINT Tip: Check Sherlock or Maigret for 400+ site checks"}


class ExploitSearchTool(BaseTool):
    def execute(self, params):
        query = params.get("query", params.get("search", "")).strip()
        cve = params.get("cve", "").strip()
        if not query and not cve:
            return {"success": False, "result": "Provide a search query (software name) or CVE ID"}
        lines = []
        try:
            url = f"https://www.exploit-db.com/search?q={urllib.parse.quote(query or cve)}"
            lines.append(f"Online exploit search for: {query or cve}")
            lines.append(f"Search URL: {url}")
            # Try to fetch exploit results from a free API
            api_url = f"https://cve.circl.lu/api/last/{20}"
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(api_url, headers={"User-Agent": "JARVIS/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                cves = json.loads(resp.read())
            found = []
            for item in cves if isinstance(cves, list) else []:
                cid = item.get('id', '')
                desc = item.get('description', '')[:200]
                if query.lower() in desc.lower() or query.lower() in cid.lower() or cve.lower() in cid.lower():
                    found.append(f"  {cid}: {desc[:150]}")
            if found:
                lines.append(f"\nRecent relevant CVEs ({len(found)}):")
                lines.extend(found)
            else:
                lines.append("\nNo recent CVEs found. Check exploit-db.com for the latest exploits.")
            return {"success": True, "result": "\n".join(lines)}
        except Exception as e:
            return {"success": False, "result": f"Exploit search error: {e}"}


class PhishingDetectorTool(BaseTool):
    def execute(self, params):
        text = params.get("text", params.get("email", ""))
        url = params.get("url", "")
        if not text and not url:
            return {"success": False, "result": "Provide email content or URL to check"}
        warnings = []
        info = []
        score = 0
        if url:
            # Run URL analysis
            url_lower = url.lower()
            parsed = urllib.parse.urlparse(url if "://" in url else "//" + url)
            domain = parsed.netloc or parsed.path.split("/")[0]
            suspicious_tlds = [".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".cam", ".click", ".download"]
            for tld in suspicious_tlds:
                if domain.endswith(tld):
                    warnings.append(f"Suspicious TLD: {tld}")
                    score += 2
            phishing_keywords = ["login", "verify", "account", "update", "confirm", "secure",
                                 "bank", "paypal", "password", "credential", "auth", "reset"]
            found_kw = [k for k in phishing_keywords if k in url_lower]
            if found_kw:
                warnings.append(f"Phishing keywords: {', '.join(found_kw)}")
                score += 2
            if "@" in url_lower:
                warnings.append("'@' symbol hides real domain")
                score += 3
            if not url_lower.startswith("https://"):
                warnings.append("No HTTPS")
                score += 1
            info.append(f"Domain: {domain}")
        if text:
            # Check email content
            text_lower = text.lower()
            urgency_words = ["urgent", "immediately", "action required", "account suspended",
                             "limited time", "click here", "verify now", "security alert",
                             "unauthorized login", "unusual activity", "confirm your account"]
            found_urg = [w for w in urgency_words if w in text_lower]
            if found_urg:
                warnings.append(f"Urgency/social engineering: {', '.join(found_urg)}")
                score += len(found_urg)
            if "Dear" not in text and "Hi" not in text[:50]:
                if "valued" not in text_lower[:100]:
                    warnings.append("Generic greeting (no personalization)")
                    score += 1
            # Check for suspicious links
            links = re.findall(r'https?://[^\s<>"\']+', text)
            for link in links:
                if not link.startswith("https://"):
                    warnings.append(f"Non-HTTPS link: {link[:60]}")
                    score += 1
            # Check for poor grammar/spelling
            grammar_indicators = ["congrates", "congo", "fellow", "kindly", "dearly", "we have been trying"]
            for g in grammar_indicators:
                if g in text_lower:
                    warnings.append(f"Common phishing phrasing: '{g}'")
                    score += 1
            # Check for mismatched sender/domain
            sender_domains = re.findall(r'@(\S+\.\S+)', text)
            link_domains = re.findall(r'https?://([^/\s]+)', text)
            for sd in sender_domains:
                for ld in link_domains:
                    if sd and ld and sd not in ld and ld not in sd:
                        if sd.split(".")[-2:] != ld.split(".")[-2:]:
                            warnings.append(f"Mismatch: sender @{sd} links to {ld}")
                            score += 3
        lines = [f"Phishing Analysis", "=" * 40]
        if url:
            lines.append(f"URL: {url[:100]}")
        if text:
            lines.append(f"Content: {len(text)} chars")
        level = "HIGH" if score >= 6 else ("MEDIUM" if score >= 3 else "LOW")
        lines.append(f"\nRisk Score: {score}/20 | Threat Level: {level}")
        if warnings:
            lines.append(f"\n⚠ Warnings ({len(warnings)}):")
            for w in warnings:
                lines.append(f"  • {w}")
        else:
            lines.append("\n✓ No obvious phishing indicators detected")
        if info:
            lines.append(f"\nInfo:")
            for i in info:
                lines.append(f"  • {i}")
        from urllib.parse import urlparse, parse_qs
        return {"success": True, "result": "\n".join(lines)}


class HashIdentifierTool(BaseTool):
    _PATTERNS = [
        (r'^[a-f0-9]{32}$', 'MD5', 'MD5 hash (128 bits, 32 hex chars)'),
        (r'^[a-f0-9]{40}$', 'SHA-1', 'SHA-1 hash (160 bits, 40 hex chars)'),
        (r'^[a-f0-9]{56}$', 'SHA-224', 'SHA-224 hash (224 bits, 56 hex chars)'),
        (r'^[a-f0-9]{64}$', 'SHA-256', 'SHA-256 hash (256 bits, 64 hex chars)'),
        (r'^[a-f0-9]{96}$', 'SHA-384', 'SHA-384 hash (384 bits, 96 hex chars)'),
        (r'^[a-f0-9]{128}$', 'SHA-512', 'SHA-512 hash (512 bits, 128 hex chars)'),
        (r'^\$2[ayb]\$\d{2}\$[A-Za-z0-9./]{53}$', 'bcrypt', 'bcrypt hash (60 chars)'),
        (r'^\$5\$\w{16}\$[A-Za-z0-9./]{43}$', 'SHA-256-Crypt', 'Linux SHA-256 crypt'),
        (r'^\$6\$\w{16}\$[A-Za-z0-9./]{86}$', 'SHA-512-Crypt', 'Linux SHA-512 crypt'),
        (r'^[a-f0-9]{32}:[a-f0-9]{32}$', 'LM:NTLM', 'Windows LM:NTLM hash pair'),
        (r'^[0-9a-f]{32}:\w+$', 'NTLM:Username', 'NTLM hash with username'),
        (r'^[A-Za-z0-9+/]{32}={0,2}$', 'NTLM (base64)', 'NTLM hash in base64'),
        (r'^\d+:[a-f0-9]{32}:[a-f0-9]{32}:[a-f0-9]{32}:[a-f0-9]{32}:[a-f0-9]{32}:[a-f0-9]{32}:.+$',
         'Shadow File', '/etc/shadow entry'),
        (r'^[A-Za-z0-9+/]{40}={0,2}$', 'SHA-1 (base64)', 'SHA-1 in base64'),
        (r'^[A-Za-z0-9+/]{64}={0,2}$', 'SHA-256 (base64)', 'SHA-256 in base64'),
        (r'^[A-Za-z0-9+/]{88}={0,2}$', 'SHA-512 (base64)', 'SHA-512 in base64'),
    ]

    def execute(self, params):
        hash_str = params.get("hash", "").strip()
        if not hash_str:
            return {"success": False, "result": "Provide a hash string to identify"}
        hash_clean = hash_str.strip().lower()
        lines = [f"Hash Identification: {hash_str[:80]}", "=" * 40]
        matches = []
        for pattern, name, desc in self._PATTERNS:
            if re.match(pattern, hash_clean) or re.match(pattern, hash_str):
                matches.append((name, desc))
        if matches:
            lines.append(f"Matched {len(matches)} pattern(s):")
            for name, desc in matches:
                lines.append(f"  • {name}: {desc}")
        else:
            length = len(hash_str)
            lines.append("No specific pattern matched.")
            lines.append(f"Length: {length} characters")
            if length == 32:
                lines.append("Could be: MD5 or MD4")
            elif length == 40:
                lines.append("Could be: SHA-1")
            elif length == 64:
                lines.append("Could be: SHA-256")
            elif length == 128:
                lines.append("Could be: SHA-512")
            else:
                lines.append("Unknown hash type")
        return {"success": True, "result": "\n".join(lines)}


class PasswordAuditorTool(BaseTool):
    COMMON_PASSWORDS = ["123456", "password", "qwerty", "abc123", "letmein", "welcome",
                        "monkey", "dragon", "master", "login", "admin", "sunshine",
                        "princess", "football", "iloveyou", "trustno1", "cheese",
                        "shadow", "baseball", "charlie", "donald", "password1",
                        "qwerty123", "123456789", "111111", "000000"]

    def execute(self, params):
        password = params.get("password", "").strip()
        if not password:
            return {"success": False, "result": "Provide a password to audit"}
        issues = []
        score = 0
        length = len(password)
        # Length checks
        if length < 8:
            issues.append("Too short (< 8 chars)")
            score -= 20
        elif length < 12:
            issues.append("Moderate length (8-11 chars, aim for 12+)")
            score += 10
        elif length < 16:
            score += 20
        else:
            score += 30
        # Character variety
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'[0-9]', password))
        has_special = bool(re.search(r'[^A-Za-z0-9]', password))
        variety = sum([has_upper, has_lower, has_digit, has_special])
        if variety >= 4:
            score += 25
            issues.append("Excellent: uses all character types")
        elif variety >= 3:
            score += 15
            issues.append("Good: uses 3/4 character types")
        elif variety >= 2:
            score += 5
            issues.append("Add more character types")
        else:
            score -= 10
            issues.append("Weak: only one character type")
        # Entropy estimate
        charset_size = 0
        if has_lower:
            charset_size += 26
        if has_upper:
            charset_size += 26
        if has_digit:
            charset_size += 10
        if has_special:
            charset_size += 32
        if charset_size > 0:
            entropy_bits = length * math.log2(charset_size)
            if entropy_bits < 28:
                issues.append("Very low entropy (easily crackable)")
                score -= 20
            elif entropy_bits < 36:
                issues.append("Low entropy")
                score -= 10
            elif entropy_bits < 60:
                issues.append("Moderate entropy")
                score += 10
            else:
                issues.append("Good entropy")
                score += 20
        # Check common passwords
        if password.lower() in self.COMMON_PASSWORDS:
            issues.append("⚠ This password is in the top 25 most common passwords!")
            score = -50
        # Check keyboard patterns
        if re.search(r'(qwert|asdf|zxcv|1234|abcd|passw|qwer)', password.lower()):
            issues.append("Keyboard pattern or common sequence detected")
            score -= 15
        # Check repeated chars
        if re.search(r'(.)\1{2,}', password):
            issues.append("Repeated characters (e.g., 'aaa')")
            score -= 10
        score = max(0, min(100, score))
        rating = "STRONG" if score >= 80 else ("GOOD" if score >= 60 else
                  ("FAIR" if score >= 40 else "WEAK"))
        lines = [
            f"Password Audit", "=" * 40,
            f"Password: {'*' * length} ({length} chars)",
            f"Score: {score}/100 | Rating: {rating}",
            f"\nCharacter Types:",
            f"  Uppercase: {'✓' if has_upper else '✗'}",
            f"  Lowercase: {'✓' if has_lower else '✗'}",
            f"  Digits:    {'✓' if has_digit else '✗'}",
            f"  Special:   {'✓' if has_special else '✗'}",
            f"  Variety:   {variety}/4",
        ]
        if entropy_bits > 0:
            lines.append(f"  Entropy:   {entropy_bits:.1f} bits")
        lines.append(f"\nAnalysis:")
        for issue in issues:
            lines.append(f"  • {issue}")
        lines.append(f"\nTips:")
        lines.append("  • Use 12+ characters with all 4 types")
        lines.append("  • Avoid dictionary words and patterns")
        lines.append("  • Use a password manager")
        return {"success": True, "result": "\n".join(lines)}


class ThreatIntelTool(BaseTool):
    def execute(self, params):
        target = params.get("target", "").strip()
        target_type = params.get("type", "auto").lower()
        if not target:
            return {"success": False, "result": "Provide an IP, domain, hash, or URL"}
        lines = [f"Threat Intelligence Report", "=" * 40,
                 f"Target: {target}", f"Type: {target_type}", ""]
        # Determine target type
        if target_type == "auto":
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', target):
                target_type = "ip"
            elif "." in target and " " not in target:
                target_type = "domain"
            elif re.match(r'^[a-f0-9]{32,128}$', target, re.I):
                target_type = "hash"
            else:
                target_type = "text"
        if target_type == "ip":
            lines.append("IP Analysis:")
            try:
                hostname = socket.gethostbyaddr(target)[0]
                lines.append(f"  PTR: {hostname}")
            except Exception:
                pass
            try:
                req = urllib.request.Request(f"https://ipapi.co/{target}/json/",
                                            headers={"User-Agent": "JARVIS/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                lines.append(f"  Location: {data.get('city','?')}, {data.get('country_name','?')}")
                lines.append(f"  ISP: {data.get('org', data.get('isp', '?'))}")
            except Exception:
                pass
            lines.append("\n  Check: abuseipdb.com, virustotal.com, shodan.io")
        elif target_type == "domain":
            lines.append("Domain Analysis:")
            try:
                ip = socket.gethostbyname(target)
                lines.append(f"  Resolves to: {ip}")
            except Exception:
                lines.append("  Cannot resolve")
            lines.append("\n  Check: virustotal.com, urlscan.io, whois.domaintools.com")
        elif target_type == "hash":
            lines.append("Hash Analysis:")
            length = len(target)
            lines.append(f"  Length: {length} hex chars")
            if length == 32:
                lines.append("  Type: MD5")
            elif length == 40:
                lines.append("  Type: SHA-1")
            elif length == 64:
                lines.append("  Type: SHA-256")
            elif length == 128:
                lines.append("  Type: SHA-512")
            else:
                lines.append("  Type: Unknown")
            lines.append("\n  Check: virustotal.com (search hash)")
        else:
            lines.append("Text/IOC Analysis:")
            urls = re.findall(r'https?://[^\s]+', target)
            ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', target)
            hashes = re.findall(r'[a-fA-F0-9]{32,}', target)
            if urls:
                lines.append(f"  URLs found: {len(urls)}")
            if ips:
                lines.append(f"  IPs found: {len(ips)}")
            if hashes:
                lines.append(f"  Hashes found: {len(hashes)}")
        lines.append("\n=== End of Report ===")
        return {"success": True, "result": "\n".join(lines)}


def create_default_registry():
    registry = ToolRegistry()
    registry.register("web_search", WebSearchTool())
    registry.register("file_read", FileIOTool())
    registry.register("file_write", FileIOTool())
    registry.register("run_command", SystemControlTool())
    registry.register("calculator", CalculatorTool())
    registry.register("weather", WeatherTool())
    registry.register("time", TimeTool())
    registry.register("system_info", SystemInfoTool())
    registry.register("screenshot", ScreenshotTool())
    registry.register("notes", NotesTool())
    registry.register("todo", TodoTool())
    registry.register("clipboard", ClipboardTool())
    registry.register("define", DictTool())
    registry.register("joke", JokesTool())
    registry.register("quote", QuoteTool())
    registry.register("password", PasswordTool())
    registry.register("convert", ConvertTool())
    registry.register("file_search", FileSearchTool())
    registry.register("battery", BatteryTool())
    registry.register("process", ProcessTool())
    registry.register("random", RandomTool())
    registry.register("news", NewsTool())
    registry.register("shorten", ShortenTool())
    registry.register("ip_geo", IPGeoTool())
    registry.register("translate", TranslatorTool())
    registry.register("crypto", CryptoTool())
    registry.register("qr_code", QRCodeTool())
    registry.register("window", WindowTool())
    registry.register("audio", AudioTool())
    registry.register("network", NetworkTool())
    registry.register("archive", ArchiveTool())
    registry.register("json", JsonTool())
    registry.register("hash", HashTool())
    registry.register("ocr", OCRTool())
    registry.register("vision", VisionTool())
    registry.register("screen_watch", ScreenWatchTool())
    registry.register("input_control", InputControlTool())
    registry.register("edit", EditTool())
    registry.register("grep", GrepTool())
    registry.register("glob", GlobTool())
    registry.register("apply_patch", ApplyPatchTool())
    registry.register("webfetch", WebFetchTool())
    registry.register("question", QuestionTool())
    registry.register("skill", SkillTool())
    registry.register("todowrite", TodoWriteTool())
    registry.register("volume", VolumeControlTool())
    registry.register("media", MediaControlTool())
    registry.register("notification", NotificationTool())
    registry.register("disk", DiskTool())
    registry.register("wallpaper", WallpaperTool())
    registry.register("lock", LockScreenTool())
    registry.register("browser", BrowserTool())
    registry.register("env", EnvTool())
    registry.register("color", ColorTool())
    registry.register("unit", UnitTool())
    registry.register("math_eval", MathEvalTool())
    registry.register("idle", IdleTool())
    # Register existing unregistered tools
    registry.register("email", EmailTool())
    registry.register("calendar", CalendarTool())
    registry.register("reminder", ReminderTool())
    registry.register("timer", TimerTool())
    # New tools batch
    registry.register("public_ip", PublicIPTool())
    registry.register("ping", PingTool())
    registry.register("dns_lookup", DNSTool())
    registry.register("host_info", HostInfoTool())
    registry.register("timestamp", TimestampTool())
    registry.register("timezone", TimezoneTool())
    registry.register("date_calc", DateCalcTool())
    registry.register("text", TextTool())
    registry.register("diff", DiffTool())
    registry.register("sort", SortTool())
    registry.register("regex", RegexTool())
    registry.register("uuid", UUIDTool())
    registry.register("base64", Base64Tool())
    registry.register("confirm", ConfirmTool())
    registry.register("prompt", PromptTool())
    registry.register("choose", ChooseTool())
    registry.register("beep", BeepTool())
    registry.register("sleep", SleepTool())
    registry.register("alarm", AlarmTool())
    registry.register("stopwatch", StopwatchTool())
    registry.register("file_info", FileInfoTool())
    registry.register("dir_list", DirListTool())
    registry.register("image_info", ImageInfoTool())
    registry.register("fact", FactTool())
    registry.register("lyric", LyricTool())
    registry.register("hn", HNReaderTool())
    registry.register("reddit", RedditTool())
    registry.register("wikipedia", WikipediaTool())
    registry.register("forecast", WeatherForecastTool())
    registry.register("currency", CurrencyTool())
    registry.register("stock", StockTool())
    registry.register("movie", MovieTool())
    registry.register("recipe", RecipeTool())
    registry.register("random_joke", RDJokeTool())
    # Display/UI tools
    registry.register("show", ShowTool())
    registry.register("alert", AlertTool())
    registry.register("csv_view", CsvTool())
    registry.register("json_format", JsonFormatTool())
    registry.register("brightness", BrightnessTool())
    registry.register("encode", EncodeTool())
    registry.register("chart", ChartTool())
    registry.register("markdown_render", MarkdownRenderTool())
    registry.register("screen_res", ScreenResTool())
    registry.register("counter", CounterTool())
    registry.register("progress", ProgressTool())
    registry.register("color_picker", ColorPickerTool())
    # Student & Teacher Tools (53)
    registry.register("flashcard", FlashcardTool())
    registry.register("quiz", QuizTool())
    registry.register("study_set", StudySetTool())
    registry.register("grade_calc", GradeCalcTool())
    registry.register("gpa", GPATool())
    registry.register("assignment", AssignmentTool())
    registry.register("study_timer", StudyTimerTool())
    registry.register("attendance", AttendanceTool())
    registry.register("essay_outline", EssayOutlineTool())
    registry.register("citation", CitationTool())
    registry.register("thesaurus", ThesaurusTool())
    registry.register("statistics", StatisticsTool())
    registry.register("prime", PrimeTool())
    registry.register("matrix", MatrixTool())
    registry.register("periodic_table", PeriodicTableTool())
    registry.register("physics_ref", PhysicsRefTool())
    registry.register("formula", FormulaTool())
    registry.register("doi_lookup", DOILookupTool())
    registry.register("arxiv", ArxivTool())
    registry.register("vocab", VocabTool())
    registry.register("mnemonic", MnemonicTool())
    registry.register("note_summarize", NoteSummarizeTool())
    registry.register("conjugation", ConjugationTool())
    registry.register("spell_check", SpellCheckTool())
    registry.register("group_picker", GroupPickerTool())
    registry.register("rubric", RubricTool())
    registry.register("syllabus", SyllabusTool())
    registry.register("practice_problem", PracticeProblemTool())
    registry.register("science_fact", ScienceFactTool())
    registry.register("study_plan", StudyPlanTool())
    registry.register("note_organizer", NoteOrganizerTool())
    registry.register("bibliography", BibliographyTool())
    registry.register("equation_solve", EquationSolveTool())
    # Student & Teacher Tools batch 2 (20)
    registry.register("lesson_plan", LessonPlanTool())
    registry.register("worksheet", WorksheetGeneratorTool())
    registry.register("exam", ExamGeneratorTool())
    registry.register("progress_report", ProgressReportTool())
    registry.register("seating_chart", SeatingChartTool())
    registry.register("icebreaker", IcebreakerTool())
    registry.register("discussion", DiscussionPromptTool())
    registry.register("learning_objectives", LearningObjectivesTool())
    registry.register("activity", ActivityGeneratorTool())
    registry.register("feedback", FeedbackTool())
    registry.register("reading_list", ReadingListTool())
    registry.register("study_guide", StudyGuideTool())
    registry.register("timeline", TimelineTool())
    registry.register("mind_map", MindMapTool())
    registry.register("thesis_statement", ThesisStatementTool())
    registry.register("abstract", AbstractGeneratorTool())
    registry.register("flashcard_import", FlashcardImportTool())
    registry.register("cheat_sheet", CheatSheetTool())
    registry.register("concept_map", ConceptMapTool())
    registry.register("quiz_me", QuizMeTool())
    # Cybersecurity Tools (20)
    registry.register("port_scanner", PortScannerTool())
    registry.register("subdomain_scan", SubdomainEnumTool())
    registry.register("whois_lookup", WhoisTool())
    registry.register("ssl_inspector", SSLInspectorTool())
    registry.register("http_headers", HTTPHeadersTool())
    registry.register("url_analyzer", URLAnalyzerTool())
    registry.register("ip_reputation", IPReputationTool())
    registry.register("cve_search", CVESearchTool())
    registry.register("dns_enum", DNSEnumTool())
    registry.register("mac_vendor", MACVendorTool())
    registry.register("file_analyzer", FileAnalyzerTool())
    registry.register("cipher", CipherTool())
    registry.register("log_parser", LogParserTool())
    registry.register("network_map", NetworkMapperTool())
    registry.register("user_enum", UserEnumTool())
    registry.register("exploit_search", ExploitSearchTool())
    registry.register("phishing_detector", PhishingDetectorTool())
    registry.register("hash_id", HashIdentifierTool())
    registry.register("password_audit", PasswordAuditorTool())
    registry.register("threat_intel", ThreatIntelTool())
    # Student & Teacher Tools batch 3 (20)
    registry.register("plagiarism_check", PlagiarismCheckTool())
    registry.register("peer_review", PeerReviewTool())
    registry.register("lab_report", LabReportTool())
    registry.register("research_proposal", ResearchProposalTool())
    registry.register("book_report", BookReportTool())
    registry.register("presentation_outline", PresentationOutlineTool())
    registry.register("debate_topic", DebateTopicTool())
    registry.register("writing_prompt", WritingPromptTool())
    registry.register("math_word_problem", MathWordProblemTool())
    registry.register("project_planner", ProjectPlannerTool())
    registry.register("self_assessment", SelfAssessmentTool())
    registry.register("homework_helper", HomeworkHelperTool())
    registry.register("flashcard_review", FlashcardReviewTool())
    registry.register("test_review", TestReviewTool())
    registry.register("classroom_game", ClassroomGameTool())
    registry.register("goal_setter", GoalSetterTool())
    registry.register("field_trip", FieldTripTool())
    registry.register("case_study", CaseStudyTool())
    registry.register("note_template", NoteTemplateTool())
    registry.register("study_break", StudyBreakTool())
    return registry
