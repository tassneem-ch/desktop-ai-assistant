"""JARVIS Voice-First UI - Waveform visualizer with text input"""

import math
import random
import re
import struct
import threading
import tkinter as tk
from jarvis_app.todo_overlay import show_todo_overlay, hide_todo_overlay, toggle_todo_overlay


def handle_direct_mouse(text, voice):
    """Execute mouse commands directly, bypassing AI for instant response"""
    try:
        import win32api, win32con
    except ImportError:
        return False
    t = text.lower().strip()

    # mouse position
    if re.search(r'(?:mouse|cursor)\s*(?:position|location|where|status)', t) or re.search(r'where\s*(?:is|are)\s*(?:the|)\s*(?:mouse|cursor)', t):
        x, y = win32api.GetCursorPos()
        voice.speak(f"Mouse at {x}, {y}")
        return True

    # move to X Y or move X Y
    m = re.search(r'(?:move|go)\s*(?:mouse|to|the|)\s*(?:to|at|)\s*(\d{1,5})\s*[,\s]\s*(\d{1,5})', t)
    if m:
        x, y = int(m.group(1)), int(m.group(2))
        win32api.SetCursorPos((x, y))
        voice.speak(f"Moved to {x} {y}")
        return True

    # move left/right/up/down N pixels
    m = re.search(r'move\s*(left|right|up|down)\s*(\d{1,4})', t)
    if m:
        cx, cy = win32api.GetCursorPos()
        d = int(m.group(2))
        dirs = {"left": (-d, 0), "right": (d, 0), "up": (0, -d), "down": (0, d)}
        dx, dy = dirs[m.group(1)]
        win32api.SetCursorPos((cx + dx, cy + dy))
        voice.speak(f"Moved {m.group(1)} {d}")
        return True

    # click [left|right|middle|double] [at] X Y
    m = re.search(r'(?:left|right|middle|double)?\s*click\s*(?:at|)\s*(\d{1,5})\s*[,\s]\s*(\d{1,5})', t)
    if m:
        x, y = int(m.group(1)), int(m.group(2))
        if "double" in t:
            win32api.SetCursorPos((x, y))
            for _ in range(2):
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            voice.speak(f"Double clicked {x} {y}")
        elif "right" in t:
            win32api.SetCursorPos((x, y))
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            voice.speak(f"Right clicked {x} {y}")
        else:
            win32api.SetCursorPos((x, y))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            voice.speak(f"Clicked {x} {y}")
        return True

    # click (at current position, no digits in command)
    if re.search(r'\bclick\b', t) and not re.search(r'\d', t):
        if "right" in t:
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            voice.speak("Right clicked")
        elif "double" in t:
            for _ in range(2):
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            voice.speak("Double clicked")
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            voice.speak("Clicked")
        return True

    # scroll up/down N
    m = re.search(r'scroll\s*(up|down|left|right|)\s*(\d{0,3})', t)
    if m:
        clicks = int(m.group(2)) if m.group(2) else 1
        if m.group(1) == "down":
            clicks = -clicks
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, clicks * 120, 0)
        voice.speak(f"Scrolled {m.group(1) or ''} {abs(clicks)}")
        return True

    return False


def _hx(value):
    """Format a colour channel as exactly two hex digits.

    Tkinter has no idea about #RRGGBBAA and raises
    ``invalid color name`` as soon as a channel exceeds 0xFF
    (e.g. ``f"#{al:02x}{al:02x}ff"`` with ``al = 256`` -> "#100100ff"),
    which used to kill the animation loop.
    """
    try:
        v = int(value)
    except (TypeError, ValueError):
        v = 0
    if v < 0:
        v = 0
    elif v > 255:
        v = 255
    return f"{v:02x}"

class HudSounds:
    """Minimal HUD sound effects using winsound (synthesized WAV pulses)"""

    def __init__(self, enabled=True):
        self.enabled = enabled
        self._cache = {}

    def _gen_beep(self, freq=880, dur=80):
        key = (freq, dur)
        if key in self._cache:
            return self._cache[key]
        import array
        sr = 22050
        n = int(sr * dur / 1000)
        data = bytearray()
        for i in range(n):
            t = i / sr
            val = int(127 * math.sin(2 * math.pi * freq * t) * max(0, 1 - t / (dur / 1000)))
            data.extend(struct.pack('B', val + 128))
        buf = bytearray()
        buf.extend(b'RIFF')
        nf = 36 + len(data)
        buf.extend(struct.pack('<I', nf))
        buf.extend(b'WAVE')
        buf.extend(b'fmt ')
        buf.extend(struct.pack('<I', 16))
        buf.extend(struct.pack('<H', 1))
        buf.extend(struct.pack('<H', 1))
        buf.extend(struct.pack('<I', sr))
        buf.extend(struct.pack('<I', sr * 1))
        buf.extend(struct.pack('<H', 1))
        buf.extend(struct.pack('<H', 8))
        buf.extend(b'data')
        buf.extend(struct.pack('<I', len(data)))
        buf.extend(data)
        self._cache[key] = buf
        return buf

    def play(self, sound_name):
        if not self.enabled:
            return
        try:
            if sound_name == "startup":
                buf = self._gen_beep(440, 100) + self._gen_beep(660, 80)[44:]
            elif sound_name == "message":
                buf = self._gen_beep(880, 60)
            elif sound_name == "thinking":
                buf = self._gen_beep(600, 40) + self._gen_beep(400, 40)[20:]
            elif sound_name == "error":
                buf = self._gen_beep(220, 120)
            elif sound_name == "done":
                buf = self._gen_beep(990, 50) + self._gen_beep(1320, 50)[25:]
            elif sound_name == "alert":
                buf = self._gen_beep(880, 60) + self._gen_beep(660, 60)[30:]
            else:
                buf = self._gen_beep(660, 50)
            import tempfile, winsound
            f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            fpath = f.name
            f.close()
            with open(fpath, "wb") as wf:
                wf.write(buf)
            winsound.PlaySound(fpath, winsound.SND_FILENAME | winsound.SND_NODEFAULT | winsound.SND_ASYNC)
            import atexit
            atexit.register(lambda: (__import__('os').unlink(fpath) if __import__('os').path.exists(fpath) else None))
        except Exception:
            pass


THEMES = {
    "hud": {
        "bg": "#060618",
        "fg": "#c8e6ff",
        "accent": "#00ddff",
        "accent2": "#0d0d2b",
        "accent3": "#001a33",
        "border": "#00ddff",
        "status_color": "#5588aa",
        "success": "#00ff88",
        "warn": "#ff8800",
        "error": "#ff3355",
    },
}


class WaveformVisualizer:
    STATE_COLORS = {
        "idle": "#00ddff",
        "listening": "#00ff88",
        "speaking": "#dd44ff",
        "thinking": "#ff8800",
    }

    def __init__(self, canvas, width, height):
        self.canvas = canvas
        self.w = width
        self.h = height
        self.cx = width // 2
        self.cy = height // 2
        self.buffer = [0.0] * 80
        self.particles = []
        self.ambient_particles = []
        self.data_stream = []
        self.satellites = []
        self.phase = 0.0
        self.state = "idle"
        self._voice_rings = []
        self._prev_amp = 0.0
        self._init_ambient()
        self._init_satellites()

    def _init_ambient(self):
        for _ in range(30):
            self.ambient_particles.append({
                "x": random.uniform(0, self.w),
                "y": random.uniform(0, self.h),
                "vx": random.uniform(-0.2, 0.2),
                "vy": random.uniform(-0.3, -0.05),
                "size": random.uniform(0.5, 1.5),
                "alpha": random.uniform(0.1, 0.4),
                "phase_offset": random.uniform(0, 6.28),
            })

    def _init_satellites(self):
        for i in range(4):
            self.satellites.append({
                "angle_offset": (i / 4) * 2 * math.pi,
                "speed": 0.5 + random.uniform(-0.1, 0.1),
                "radius": 0,
                "size": random.uniform(1.5, 2.5),
            })

    def set_state(self, state):
        self.state = state

    def push_amplitude(self, amp):
        self.buffer.pop(0)
        self.buffer.append(min(amp / 2000.0, 1.0))

    def _voice_level(self):
        if not self.buffer:
            return 0.0
        return sum(self.buffer[-8:]) / min(len(self.buffer), 8)

    def _color(self):
        return self.STATE_COLORS.get(self.state, "#00ddff")

    def draw(self):
        self.canvas.delete("all")
        self.phase += 0.05
        self._update_voice_rings()
        self._draw_background()
        self._draw_data_stream()
        self._draw_ambient_particles()
        self._draw_hud_rings()
        self._draw_scanlines()

        if self.state == "listening":
            self._draw_waveform_bars()
            self._spawn_particles(2)
            self._draw_particles()
        elif self.state == "speaking":
            self._draw_waveform_circular()
            self._spawn_particles(1)
            self._draw_particles()
        elif self.state == "thinking":
            self._draw_thinking()
        else:
            self._draw_idle()

        self._draw_satellites()
        self._draw_voice_rings()
        self._draw_center_eye()
        self._draw_corner_brackets()
        self._draw_data_readouts()
        self._draw_targeting_reticle()

    def _draw_background(self):
        w, h, cx, cy = self.w, self.h, self.cx, self.cy
        r = min(w, h) * 0.4
        for i in range(20, 0, -1):
            t = i / 20
            a = min(int(i * 1.2), 255)
            a_r = max(a // 4, 0)
            a_g = max(a // 2, 0)
            a_b = min(a, 255)
            self.canvas.create_oval(
                cx - r * t, cy - r * t, cx + r * t, cy + r * t,
                outline=f"#{_hx(a_r)}{_hx(a_g)}{_hx(a_b)}", width=1
            )

    def _draw_data_stream(self):
        if len(self.data_stream) < 20:
            self.data_stream.append({
                "x": random.uniform(0, self.w),
                "y": -10,
                "speed": random.uniform(1, 4),
                "length": random.uniform(10, 40),
                "alpha": random.uniform(0.05, 0.15),
            })
        alive = []
        col = self._color()
        for d in self.data_stream:
            d["y"] += d["speed"]
            alpha = int(d["alpha"] * 255)
            self.canvas.create_line(d["x"], d["y"], d["x"], d["y"] + d["length"],
                                     fill=f"#00{_hx(alpha)}{_hx(alpha)}", width=1)
            if d["y"] < self.h + d["length"]:
                alive.append(d)
        self.data_stream = alive

    def _draw_ambient_particles(self):
        for p in self.ambient_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["y"] < -5: p["y"] = self.h + 5
            if p["x"] < -5: p["x"] = self.w + 5
            if p["x"] > self.w + 5: p["x"] = -5
            a = int(p["alpha"] * (0.6 + 0.4 * math.sin(self.phase + p["phase_offset"])) * 255)
            self.canvas.create_oval(
                p["x"] - p["size"], p["y"] - p["size"],
                p["x"] + p["size"], p["y"] + p["size"],
                fill=f"#00{_hx(a)}ff", outline=""
            )

    def _draw_hud_rings(self):
        cx, cy = self.cx, self.cy
        col = self._color()
        r = min(self.w, self.h) * 0.38
        for i in range(3):
            dr = 6 * math.sin(self.phase * 1.2 + i * 2.1)
            a = int(15 + 12 * math.sin(self.phase + i))
            self.canvas.create_oval(
                cx - r - dr, cy - r - dr, cx + r + dr, cy + r + dr,
                outline=f"#00{_hx(a)}{_hx(a+20)}", width=1
            )
        n_ticks = 40
        for i in range(n_ticks):
            angle = (i / n_ticks) * 2 * math.pi + self.phase * 0.15
            is_major = i % 10 == 0
            is_minor = i % 5 == 0
            inner_r = r + (6 if is_major else (4 if is_minor else 2))
            outer_r = r + (18 if is_major else (10 if is_minor else 5))
            a = int(60 + 40 * math.sin(self.phase + i * 0.4)) if is_major else (35 if is_minor else 18)
            w = 2 if is_major else (1 if is_minor else 1)
            x1 = cx + inner_r * math.cos(angle)
            y1 = cy + inner_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle)
            y2 = cy + outer_r * math.sin(angle)
            self.canvas.create_line(x1, y1, x2, y2, fill=f"#00{_hx(a)}ff", width=w)

        # Radar sweep wedge
        sweep_angle = self.phase * 0.8
        sweep_width = 0.3 + 0.15 * math.sin(self.phase * 0.5)
        sa = int(20 + 15 * math.sin(self.phase))
        for s in range(12):
            a = sweep_angle - sweep_width / 2 + (s / 12) * sweep_width
            sx = cx + (r - 4) * math.cos(a)
            sy = cy + (r - 4) * math.sin(a)
            self.canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2,
                                    fill=f"#00{_hx(sa)}ff", outline="")

        # Energy arcs
        arc_alpha = int(40 + 30 * math.sin(self.phase * 2))
        for i in range(4):
            start = (i / 4) * 2 * math.pi + self.phase * 0.5
            end = start + 0.3 + 0.2 * math.sin(self.phase + i)
            steps = 20
            for s in range(steps):
                a = start + (s / steps) * (end - start)
                x = cx + (r - 2) * math.cos(a)
                y = cy + (r - 2) * math.sin(a)
                self.canvas.create_oval(x - 1, y - 1, x + 1, y + 1,
                                        fill=f"#{_hx(arc_alpha)}{_hx(arc_alpha+30)}ff" if self.state == "idle" else col,
                                        outline="")

    def _draw_scanlines(self):
        h = self.h
        for i in range(0, int(h), 3):
            a = int(2 + 2 * math.sin(i * 0.05 + self.phase * 3))
            self.canvas.create_line(0, i, self.w, i, fill=f"#0000{_hx(a)}", width=1)

    def _draw_corner_brackets(self):
        w, h, bw = self.w, self.h, 26
        pulse = int(180 + 75 * math.sin(self.phase * 1.5))
        c = f"#00{_hx(pulse)}ff"
        self.canvas.create_line(5, 5 + bw, 5, 5, 5 + bw, 5, fill=c, width=2)
        self.canvas.create_text(8, 10, text="J.A.R.V.I.S", font=("Consolas", 6),
                                fill=f"#00{_hx(int(pulse*0.5))}ff", anchor="nw")
        self.canvas.create_line(w - 6 - bw, 5, w - 6, 5, w - 6, 5 + bw, fill=c, width=2)
        self.canvas.create_text(w - 10, 10, text="v4.0", font=("Consolas", 6),
                                fill=f"#00{_hx(int(pulse*0.5))}ff", anchor="ne")
        self.canvas.create_line(5, h - 6 - bw, 5, h - 6, 5 + bw, h - 6, fill=c, width=2)
        self.canvas.create_text(8, h - 18, text=f"ARC {self.state.upper()}", font=("Consolas", 6),
                                fill=f"#00{_hx(int(pulse*0.4))}ff", anchor="nw")
        self.canvas.create_line(w - 6 - bw, h - 6, w - 6, h - 6, w - 6, h - 6 - bw, fill=c, width=2)
        self.canvas.create_text(w - 10, h - 18, text=f"{int(self.phase*10)%100:02d}%", font=("Consolas", 6),
                                fill=f"#00{_hx(int(pulse*0.4))}ff", anchor="ne")

    def _draw_idle(self):
        cx, cy, w = self.cx, self.cy, self.w
        points = []
        for i in range(0, w + 1, 3):
            x = i
            y = cy + math.sin(i * 0.015 + self.phase) * 6 * self._glow()
            points.extend([x, y])
        if len(points) >= 4:
            self.canvas.create_line(*points, fill="#003366", width=2, smooth=True)

    def _glow(self):
        return 0.5 + 0.5 * math.sin(self.phase * 2)

    def _draw_waveform_bars(self):
        cx, cy, w, h = self.cx, self.cy, self.w, self.h
        bar_w = w / len(self.buffer)
        for i, amp in enumerate(self.buffer):
            bar_h = max(amp * h * 0.35, 1)
            x = i * bar_w
            y0 = cy - bar_h / 2
            y1 = cy + bar_h / 2
            intensity = int(min(amp * 200 + 80, 255))
            self.canvas.create_rectangle(x, y0, x + bar_w - 1, y1,
                                         fill=f"#00{_hx(intensity)}ff", outline="")

    def _draw_waveform_circular(self):
        cx, cy = self.cx, self.cy
        n = len(self.buffer)
        col = self._color()
        r_base = min(self.w, self.h) * 0.25
        points = []
        for i, amp in enumerate(self.buffer):
            angle = (i / n) * 2 * math.pi - math.pi / 2
            r = r_base + amp * r_base * 0.5
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.extend([x, y])
        if len(points) >= 4:
            self.canvas.create_line(*points, fill=col, width=3, smooth=True)
            inner = []
            for i, amp in enumerate(self.buffer):
                angle = (i / n) * 2 * math.pi - math.pi / 2
                r = r_base * 0.55 + amp * r_base * 0.25
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                inner.extend([x, y])
            self.canvas.create_line(*inner, fill="#0088bb", width=2, smooth=True)

    def _draw_thinking(self):
        cx, cy = self.cx, self.cy
        for i in range(14):
            angle = (i / 14) * 2 * math.pi + self.phase
            dist = 28 + 22 * math.sin(self.phase * 1.8 + i * 0.6)
            x = cx + dist * math.cos(angle)
            y = cy + dist * math.sin(angle)
            size = 2 + 4 * math.sin(self.phase * 3 + i * 0.7)
            b = int(120 + 135 * (0.5 + 0.5 * math.sin(self.phase + i)))
            c = f"#{_hx(b//3)}{_hx(b)}{_hx(b//2)}"
            self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=c, outline="")
            # Connection lines between dots
            if i > 0:
                pa = ((i - 1) / 14) * 2 * math.pi + self.phase
                pd = 28 + 22 * math.sin(self.phase * 1.8 + (i - 1) * 0.6)
                px = cx + pd * math.cos(pa)
                py = cy + pd * math.sin(pa)
                self.canvas.create_line(px, py, x, y, fill=f"#{_hx(b//6)}{_hx(b//3)}{_hx(b//4)}", width=1)

    def _spawn_particles(self, count):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 2.5)
            life = random.uniform(15, 40)
            self.particles.append({
                "x": self.cx, "y": self.cy,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": life, "max_life": life,
                "size": random.uniform(1, 3),
            })

    def _draw_particles(self):
        alive = []
        for p in self.particles:
            p["x"] += p["vx"]; p["y"] += p["vy"]
            p["vx"] *= 0.96; p["vy"] *= 0.96
            p["life"] -= 1
            life_ratio = p["life"] / p["max_life"]
            if life_ratio > 0:
                b = int(min(255 * life_ratio, 180))
                self.canvas.create_oval(
                    p["x"] - p["size"], p["y"] - p["size"],
                    p["x"] + p["size"], p["y"] + p["size"],
                    fill=f"#00{_hx(b)}ff", outline="#00ffff"
                )
                alive.append(p)
        self.particles = alive

    def _update_voice_rings(self):
        amp = self._voice_level()
        peak = amp > 0.15 and self._prev_amp <= 0.15
        self._prev_amp = amp
        if peak:
            self._voice_rings.append({
                "r": 3,
                "max_r": 15 + amp * 30,
                "alpha": 0.8,
                "speed": 0.6 + amp * 1.5,
            })
        alive = []
        for vr in self._voice_rings:
            vr["r"] += vr["speed"]
            vr["alpha"] *= 0.92
            if vr["alpha"] > 0.02 and vr["r"] < vr["max_r"]:
                alive.append(vr)
        self._voice_rings = alive

    def _draw_voice_rings(self):
        cx, cy = self.cx, self.cy
        col = self._color()
        for vr in self._voice_rings:
            a = int(vr["alpha"] * 255)
            c = f"#{_hx(a)}{_hx(a)}ff" if col == "#dd44ff" else f"#00{_hx(a)}ff"
            self.canvas.create_oval(
                cx - vr["r"], cy - vr["r"], cx + vr["r"], cy + vr["r"],
                outline=c, width=1
            )

    def _draw_satellites(self):
        cx, cy = self.cx, self.cy
        r = min(self.w, self.h) * 0.28
        col = self._color()
        amp = self._voice_level()
        for s in self.satellites:
            pulse = 1.0 + amp * 0.8
            s["radius"] = r + 8 * math.sin(self.phase * 1.5 + s["angle_offset"])
            angle = self.phase * s["speed"] + s["angle_offset"]
            x = cx + s["radius"] * math.cos(angle)
            y = cy + s["radius"] * math.sin(angle)
            trail_len = max(3, int(5 + amp * 12))
            trail = [(cx + s["radius"] * math.cos(angle - t * 0.05),
                      cy + s["radius"] * math.sin(angle - t * 0.05)) for t in range(trail_len)]
            for ti, (tx, ty) in enumerate(trail):
                a = int(60 * (1 - ti / trail_len) * (0.5 + 0.5 * amp))
                self.canvas.create_oval(tx - 1, ty - 1, tx + 1, ty + 1,
                                        fill=f"#00{_hx(a)}ff", outline="")
            sz = s["size"] * pulse
            self.canvas.create_oval(x - sz, y - sz, x + sz, y + sz,
                                    fill=col, outline="#4488aa")

    def _draw_center_eye(self):
        cx, cy = self.cx, self.cy
        col = self._color()
        t = self.phase
        amp = self._voice_level()

        # --- Outer rotating ring with tick marks ---
        outer_r = 24 + 3 * math.sin(t * 1.5) + amp * 6
        self.canvas.create_oval(cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r,
                                outline=f"#004466", width=1)
        tick_pulse = int(80 + 100 * amp)
        for i in range(24):
            a = (i / 24) * 2 * math.pi + t * 0.6
            is_major = i % 6 == 0
            ir = outer_r - (5 if is_major else 3)
            ox = cx + ir * math.cos(a); oy = cy + ir * math.sin(a)
            ix = cx + (outer_r - (2 if is_major else 1)) * math.cos(a); iy = cy + (outer_r - (2 if is_major else 1)) * math.sin(a)
            a_v = int(max(80, tick_pulse) if is_major else 80)
            self.canvas.create_line(ox, oy, ix, iy, fill=f"#00{_hx(a_v)}ff", width=2 if is_major else 1)

        # --- Middle rotating hexagon (faster with voice) ---
        speed_boost = 1.0 + amp * 2.0
        hex_r = 14 + 2 * math.sin(t * 1.7) + amp * 4
        hex_pts = []
        for i in range(6):
            a = (i / 6) * 2 * math.pi - math.pi / 6 + t * 0.35 * speed_boost
            rr = hex_r + 3 * math.sin(t * 2.3 + i * 1.05) + amp * 2
            hex_pts.extend([cx + rr * math.cos(a), cy + rr * math.sin(a)])
        self.canvas.create_polygon(*hex_pts, fill="#001a33", outline=col, width=2)
        # Inner hex ring (counter-rotating, faster with voice)
        inner_hex_r = 9 + 1.5 * math.sin(t * 2.1) + amp * 3
        inner_hex_pts = []
        for i in range(6):
            a = (i / 6) * 2 * math.pi + math.pi / 6 - t * 0.25 * speed_boost
            rr = inner_hex_r + 2 * math.sin(t * 1.9 + i * 1.05) + amp * 2
            inner_hex_pts.extend([cx + rr * math.cos(a), cy + rr * math.sin(a)])
        self.canvas.create_polygon(*inner_hex_pts, outline="#0088bb", width=1, fill="")

        # --- Rotating cross / diamond inside ---
        cross_r = 10 + 1.5 * math.sin(t * 2.5) + amp * 5
        for i in range(4):
            a = (i / 4) * 2 * math.pi + t * 0.5
            x = cx + cross_r * math.cos(a); y = cy + cross_r * math.sin(a)
            self.canvas.create_line(cx, cy, x, y, fill="#0066aa", width=1)

        # --- Concentric pulsing rings (amplitude modulates pulse depth) ---
        for ring in range(3):
            ring_amp = ring + 1 + amp * 3
            rr_inner = inner_hex_r * ring_amp / 3 + 2 * math.sin(t * 2 * (1 + amp) + ring * 1.2)
            a = max(0, int(60 - 20 * ring + 30 * math.sin(t * 1.5 + ring)) + int(80 * amp))
            self.canvas.create_oval(cx - rr_inner, cy - rr_inner, cx + rr_inner, cy + rr_inner,
                                    outline=f"#00{_hx(a)}ff", width=1)

        # --- Scanning arc (180° sweep back and forth) ---
        scan_angle = t * 0.7
        sweep = abs(math.sin(t * 0.5 * (1 + amp))) * math.pi
        for s in range(15):
            a = scan_angle - sweep / 2 + (s / 15) * sweep
            sa = int(120 * (1 - s / 15) + 80 * amp)
            sx = cx + inner_hex_r * math.cos(a)
            sy = cy + inner_hex_r * math.sin(a)
            self.canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2,
                                    fill=f"#{_hx(sa)}{_hx(sa)}ff" if sa > 60 else f"#00{_hx(sa)}ff",
                                    outline="")

        # --- Bright inner core (dilates with voice) ---
        core_r = 3 + 2.5 * math.sin(t * 3) + amp * 5
        alpha = int(180 + 75 * math.sin(t * 2.5) + 75 * amp)
        self.canvas.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                                fill=col, outline="")
        # White-hot center dot (dilates with voice)
        dot_r = 1.2 + 0.8 * math.sin(t * 4) + amp * 2.5
        self.canvas.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                                fill="white", outline="")

        # --- Radial glow rays (extend with voice) ---
        for i in range(8):
            a = (i / 8) * 2 * math.pi + t * 0.2
            ray_len = 3 + 5 * math.sin(t * 1.8 + i * 0.8) + amp * 12
            rx = cx + (core_r + ray_len) * math.cos(a)
            ry = cy + (core_r + ray_len) * math.sin(a)
            al = int(100 + 80 * math.sin(t * 2 + i) + 100 * amp)
            self.canvas.create_line(
                cx + core_r * math.cos(a), cy + core_r * math.sin(a),
                rx, ry, fill=f"#{_hx(al)}{_hx(al)}ff", width=1
            )

        # --- Amplitude glow halo ---
        if amp > 0.05:
            halo_r = 6 + amp * 20
            ha = int(40 + 120 * amp)
            self.canvas.create_oval(cx - halo_r, cy - halo_r, cx + halo_r, cy + halo_r,
                                    fill=f"#{_hx(ha)}{_hx(ha)}ff" if self.state == "speaking" else f"#00{_hx(ha)}ff",
                                    outline="")

    def _draw_targeting_reticle(self):
        cx, cy = self.cx, self.cy
        col = self._color()
        r = 36 + 8 * math.sin(self.phase * 1.3)
        a = int(120 + 80 * math.sin(self.phase * 1.5))
        c = f"#00{_hx(a)}ff"
        # Four crosshair arms
        for angle in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
            gap_start = r * 0.3
            gap_end = r * 0.5
            # Outer arm
            x1 = cx + r * math.cos(angle)
            y1 = cy + r * math.sin(angle)
            x2 = cx + gap_end * math.cos(angle)
            y2 = cy + gap_end * math.sin(angle)
            self.canvas.create_line(x1, y1, x2, y2, fill=c, width=1)
            # Inner arm
            x3 = cx + gap_start * math.cos(angle)
            y3 = cy + gap_start * math.sin(angle)
            self.canvas.create_line(cx, cy, x3, y3, fill=c, width=1)
        # Small circles on crosshair ends
        for angle in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, outline=c, width=1)

    def _draw_data_readouts(self):
        cx, cy, w = self.cx, self.cy, self.w
        col = self._color()
        pulse = int(100 + 80 * math.sin(self.phase * 1.2))
        c = f"#00{_hx(pulse)}ff"
        dim = f"#00{_hx(pulse//2)}ff"
        # Left side readouts
        labels_left = [
            (cx - w * 0.38, cy - w * 0.12, "SYS", f"{97 + int(3 * math.sin(self.phase * 0.3)):02d}%"),
            (cx - w * 0.38, cy - w * 0.06, "PWR", f"{88 + int(12 * math.sin(self.phase * 0.5)):02d}%"),
            (cx - w * 0.38, cy + w * 0.0, "SIG", f"{int(40 + 30 * abs(math.sin(self.phase * 0.7))):02d}%"),
        ]
        for lx, ly, label, val in labels_left:
            self.canvas.create_text(lx, ly, text=label, font=("Consolas", 6),
                                    fill=dim, anchor="w")
            self.canvas.create_text(lx + 30, ly, text=val, font=("Consolas", 7),
                                    fill=c, anchor="w")

        # Right side readouts
        labels_right = [
            (cx + w * 0.32, cy - w * 0.12, "AZM", f"{int((self.phase * 30) % 360):03d}°"),
            (cx + w * 0.32, cy - w * 0.06, "ALT", f"{int(50 + 30 * math.sin(self.phase * 0.4)):03d}m"),
            (cx + w * 0.32, cy + w * 0.0, "VEL", f"{int(20 + 15 * abs(math.sin(self.phase * 0.6))):02d}Kt"),
        ]
        for rx, ry, label, val in labels_right:
            self.canvas.create_text(rx, ry, text=label, font=("Consolas", 6),
                                    fill=dim, anchor="e")
            self.canvas.create_text(rx - 28, ry, text=val, font=("Consolas", 7),
                                    fill=c, anchor="e")


class JarvisGUI:
    COMMANDS = {
        "/help": "Show commands",
        "/clear": "Clear conversation",
        "/new": "New session",
        "/save [name]": "Save session",
        "/load [name]": "Load session",
        "/sessions": "List saved sessions",
        "/plan": "Switch to plan mode",
        "/build": "Switch to build mode",
        "/model [name]": "Show/set model",
        "/mode": "Show current mode",
        "/undo": "Undo last action",
    }

    def __init__(self, orchestrator, voice_engine=None, stop_speech_cb=None):
        self.orchestrator = orchestrator
        self.voice = voice_engine
        self._stop_speech = stop_speech_cb or (lambda: None)
        self.colors = THEMES["hud"]
        self.listening = False
        self.sounds = HudSounds(enabled=True)

        self.root = tk.Tk()
        self.root.title("JARVIS")
        self.root.geometry("700x680")
        self.root.minsize(500, 500)
        self.root.configure(bg=self.colors["bg"])
        try:
            self.root.attributes("-alpha", 0.95)
        except Exception:
            pass

        self._build_ui()
        self._bind_events()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        if self.voice:
            self._setup_voice_callbacks()
        self._anim_running = True
        self.root.after(200, lambda: self.play_sound("startup"))
        self._anim_loop()

    def play_sound(self, name):
        threading.Thread(target=lambda: self.sounds.play(name), daemon=True).start()

    def _build_ui(self):
        C = self.colors
        main = tk.Frame(self.root, bg=C["bg"])
        main.pack(fill=tk.BOTH, expand=True)

        # ── HUD Top Bar ──
        top_bar = tk.Frame(main, bg=C["bg"], height=28)
        top_bar.pack(fill=tk.X, padx=0, pady=0)
        top_bar.pack_propagate(False)

        # JARVIS title with scan effect
        self.title_lbl = tk.Label(top_bar, text="⚡ J.A.R.V.I.S", font=("Consolas", 11, "bold"),
                                   fg=C["accent"], bg=C["bg"], anchor="w")
        self.title_lbl.pack(side=tk.LEFT, padx=(12, 0))

        # HUD status indicators
        self.hud_status = tk.Label(top_bar, text="◆ SYSTEM ONLINE", font=("Consolas", 8),
                                    fg=C["success"], bg=C["bg"])
        self.hud_status.pack(side=tk.LEFT, padx=(15, 0))

        # Model display
        self.model_display = tk.Label(top_bar, text="", font=("Consolas", 8),
                                       fg=C["status_color"], bg=C["bg"])
        self.model_display.pack(side=tk.RIGHT, padx=(0, 12))
        # Update model display
        if hasattr(self.orchestrator, 'ai'):
            self.model_display.configure(text=f"MODEL: {self.orchestrator.ai.get_model()}")

        # ── HUD Toolbar ──
        toolbar = tk.Frame(main, bg=C["accent2"], height=32,
                           highlightbackground=C["border"], highlightthickness=1, bd=0)
        toolbar.pack(fill=tk.X, padx=0, pady=0)
        toolbar.pack_propagate(False)

        # Model dropdown
        tk.Label(toolbar, text="MODEL:", font=("Consolas", 8, "bold"),
                 fg=C["status_color"], bg=C["accent2"]).pack(side=tk.LEFT, padx=(8, 2))
        models = self.orchestrator.ai.list_models() if hasattr(self.orchestrator, 'ai') else []
        current_model = self.orchestrator.ai.get_model() if hasattr(self.orchestrator, 'ai') else "tencent/hy3:free"
        self.model_var = tk.StringVar(value=current_model)
        self.model_var.trace("w", lambda *a: self._on_model_change(self.model_var.get()))
        self.model_dropdown = tk.OptionMenu(toolbar, self.model_var, *models)
        self.model_dropdown.configure(bg="#080820", fg=C["fg"], activebackground=C["accent3"],
                                       activeforeground=C["accent"], bd=0, font=("Consolas", 8),
                                       highlightthickness=0, padx=4, relief="flat")
        self.model_dropdown["menu"].configure(bg="#080820", fg=C["fg"], activebackground=C["accent"])
        self.model_dropdown.pack(side=tk.LEFT, padx=(2, 6))

        # Separator
        tk.Frame(toolbar, bg=C["border"], width=1).pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=4)

        # Plan mode toggle
        self.plan_mode = tk.BooleanVar(value=False)
        self.plan_btn = tk.Label(toolbar, text="[ BUILD ]", font=("Consolas", 8, "bold"),
                                  bg="#002211", fg=C["success"], cursor="hand2", padx=6, pady=2)
        self.plan_btn.pack(side=tk.LEFT, padx=(4, 6))
        self.plan_btn.bind("<Button-1>", lambda e: self._toggle_plan_mode())

        # Separator
        tk.Frame(toolbar, bg=C["border"], width=1).pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=4)

        # Search bar
        tk.Label(toolbar, text="🔍", font=("Consolas", 8),
                 fg=C["status_color"], bg=C["accent2"]).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self._on_search())
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var, font=("Consolas", 8),
                                      bg="#080820", fg=C["fg"], insertbackground=C["accent"],
                                      bd=0, highlightthickness=0, width=12, relief="flat")
        self.search_entry.pack(side=tk.LEFT, padx=(2, 4), fill=tk.X, expand=True)
        self.search_entry.insert(0, "search...")
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.delete(0, tk.END) if self.search_entry.get() == "search..." else None)
        self.search_entry.bind("<FocusOut>", lambda e: self.search_entry.insert(0, "search...") if not self.search_entry.get() else None)
        self.search_entry.bind("<Return>", lambda e: self._on_search())

        # Session buttons
        self.save_btn = tk.Label(toolbar, text="💾", font=("Consolas", 12),
                                  bg=C["accent2"], fg=C["accent"], cursor="hand2")
        self.save_btn.pack(side=tk.RIGHT, padx=(0, 6))
        self.save_btn.bind("<Button-1>", lambda e: self._save_session())
        self.load_btn = tk.Label(toolbar, text="📂", font=("Consolas", 12),
                                  bg=C["accent2"], fg=C["accent"], cursor="hand2")
        self.load_btn.pack(side=tk.RIGHT, padx=(0, 4))
        self.load_btn.bind("<Button-1>", lambda e: self._load_session_dialog())

        # Session indicator
        self.session_lbl = tk.Label(toolbar, text="", font=("Consolas", 7),
                                     fg=C["status_color"], bg=C["accent2"])
        self.session_lbl.pack(side=tk.RIGHT, padx=(0, 2))

        # ── HUD Canvas Area ──
        canvas_frame = tk.Frame(main, bg=C["bg"],
                                highlightbackground=C["border"], highlightthickness=1, bd=0)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 4))

        self.canvas = tk.Canvas(canvas_frame, bg=C["bg"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.viz = None

        # ── HUD Response Panel ──
        self.response_frame = tk.Frame(main, bg=C["accent2"],
                                       highlightbackground=C["border"], highlightthickness=1, bd=0,
                                       height=140)
        self.response_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.response_frame.pack_propagate(False)

        self.response_text = tk.Text(self.response_frame, font=("Consolas", 10),
                                      fg=C["accent"], bg=C["accent2"],
                                      wrap=tk.WORD, relief="flat", bd=0,
                                      highlightthickness=0, padx=10, pady=6,
                                      state=tk.DISABLED)
        self.response_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        response_scroll = tk.Scrollbar(self.response_frame, orient=tk.VERTICAL,
                                        command=self.response_text.yview, bg=C["accent2"],
                                        troughcolor=C["bg"], activebackground=C["accent"])
        response_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.response_text.configure(yscrollcommand=response_scroll.set)

        self.response_text.tag_configure("user", foreground=C["fg"])
        self.response_text.tag_configure("ai", foreground=C["accent"])
        self.response_text.tag_configure("tool", foreground=C["status_color"])
        self.response_text.tag_configure("error", foreground=C["error"])
        self.response_text.tag_configure("thinking", foreground=C["warn"])
        self.response_text.tag_configure("bold", font=("Consolas", 10, "bold"))

        # ── HUD Input Area ──
        input_frame = tk.Frame(main, bg=C["bg"])
        input_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        entry_frame = tk.Frame(input_frame, bg=C["accent2"],
                               highlightbackground=C["border"], highlightthickness=1, bd=0)
        entry_frame.pack(fill=tk.X, pady=(0, 4))

        self.input_field = tk.Text(entry_frame, height=1, font=("Consolas", 11),
                                   bg="#080820", fg=C["fg"], insertbackground=C["accent"],
                                   bd=0, padx=10, pady=5, wrap=tk.WORD, relief="flat")
        self.input_field.pack(fill=tk.X, side=tk.LEFT, expand=True)

        self.send_btn = tk.Label(entry_frame, text="▶", font=("Consolas", 13),
                                 fg=C["accent"], bg="#080820", cursor="hand2", padx=10)
        self.send_btn.pack(side=tk.RIGHT)
        self.send_btn.bind("<Button-1>", lambda e: self._send_message())

        # ── HUD Button Bar ──
        btn_row = tk.Frame(input_frame, bg=C["bg"])
        btn_row.pack(fill=tk.X)

        # Voice button with HUD styling
        self.voice_btn = tk.Label(btn_row, text="🎤", font=("Segoe UI", 18),
                                  bg=C["bg"], fg=C["accent"], cursor="hand2")
        self.voice_btn.pack(side=tk.LEFT, padx=(0, 12))

        # Stop button
        self.stop_btn = tk.Label(btn_row, text="⏹", font=("Segoe UI", 16),
                                 bg=C["bg"], fg=C["error"], cursor="hand2")
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 12))
        self.stop_btn.bind("<Button-1>", lambda e: self._stop_speech())

        # Upload button
        self.upload_btn = tk.Label(btn_row, text="📎", font=("Segoe UI", 16),
                                   bg=C["bg"], fg=C["accent"], cursor="hand2")
        self.upload_btn.pack(side=tk.LEFT, padx=(0, 12))
        self.upload_btn.bind("<Button-1>", lambda e: self._upload_file())

        # Status
        self.status_label = tk.Label(btn_row, text="◆ READY", font=("Consolas", 9),
                                     fg=C["success"], bg=C["bg"], anchor="w")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Version
        tk.Label(btn_row, text="v4.0", font=("Consolas", 8),
                 fg=C["status_color"], bg=C["bg"]).pack(side=tk.RIGHT, padx=(0, 4))

        # ── Menu bar ──
        menu_bar = tk.Menu(self.root, bg=C["accent2"], fg=C["fg"],
                           activebackground=C["accent"], activeforeground="white")
        self.root.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0, bg=C["accent2"], fg=C["fg"],
                            activebackground=C["accent"], activeforeground="white")
        file_menu.add_command(label="New Session (Ctrl+N)", command=self._new_session)
        file_menu.add_command(label="Save Session (Ctrl+S)", command=self._save_session)
        file_menu.add_command(label="Load Session (Ctrl+O)", command=self._load_session_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self._open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu_bar, tearoff=0, bg=C["accent2"], fg=C["fg"],
                            activebackground=C["accent"], activeforeground="white")
        edit_menu.add_command(label="Clear Log (Ctrl+L)", command=lambda: self.clear_response())
        edit_menu.add_command(label="Toggle Plan Mode (Tab)", command=self._toggle_plan_mode)
        edit_menu.add_separator()
        edit_menu.add_command(label="Commands...", command=lambda: self._show_help())
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

    # ── Toolbar events ──

    def _on_model_change(self, model_name):
        if hasattr(self.orchestrator, 'ai'):
            self.orchestrator.ai.set_model(model_name)
        if hasattr(self, "model_display"):
            self.model_display.configure(text=f"MODEL: {model_name}")
        self._set_status(f"◆ MODEL: {model_name}", "#00ccff")

    def _toggle_plan_mode(self):
        new_mode = not self.plan_mode.get()
        self.plan_mode.set(new_mode)
        if new_mode:
            self.plan_btn.configure(text="[ PLAN ]", bg="#442200", fg="#ff8800")
            self.orchestrator.set_mode("plan")
            self._set_status("◆ PLAN MODE", "#ff8800")
        else:
            self.plan_btn.configure(text="[ BUILD ]", bg="#002211", fg="#00ff88")
            self.orchestrator.set_mode("build")
            self._set_status("◆ BUILD MODE", "#00ff88")

    def _on_search(self):
        if not hasattr(self, "response_text"):
            return
        C = self.colors
        query = self.search_var.get().strip().lower()
        if not query or query == "search...":
            return
        self.response_text.configure(state=tk.NORMAL)
        self.response_text.tag_remove("search_highlight", "1.0", tk.END)
        self.response_text.tag_configure("search_highlight", background="#335566", foreground=C["accent"])
        idx = "1.0"
        count = 0
        while True:
            idx = self.response_text.search(query, idx, tk.END, nocase=True)
            if not idx:
                break
            end = f"{idx}+{len(query)}c"
            self.response_text.tag_add("search_highlight", idx, end)
            idx = end
            count += 1
        self.response_text.configure(state=tk.DISABLED)
        self._set_status(f"Found {count} matches" if count else "No matches", C["warn"] if count else C["error"])

    # ── Session management ──

    def _new_session(self):
        if hasattr(self.orchestrator, 'memory'):
            sid = self.orchestrator.memory.new_session()
            self.clear_response()
            if hasattr(self, "session_lbl"):
                self.session_lbl.configure(text=f"SID:{sid}")
            self._set_status("◆ NEW SESSION", "#00ff88")

    def _save_session(self):
        if hasattr(self.orchestrator, 'memory'):
            path = self.orchestrator.memory.save_session()
            self._set_status(f"◆ SESSION SAVED", "#00ff88")

    def _load_session_dialog(self):
        if not hasattr(self.orchestrator, 'memory'):
            return
        sessions = self.orchestrator.memory.list_sessions()
        if not sessions:
            self._set_status("No saved sessions", "#ff4444")
            return
        win = tk.Toplevel(self.root)
        win.title("Load Session")
        win.geometry("350x300")
        win.configure(bg=self.colors["bg"])
        tk.Label(win, text="Saved Sessions", font=("Segoe UI", 12, "bold"),
                 fg=self.colors["accent"], bg=self.colors["bg"]).pack(pady=8)
        frame = tk.Frame(win, bg=self.colors["bg"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        canvas = tk.Canvas(frame, bg=self.colors["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.colors["bg"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        for s in sessions:
            f = tk.Frame(inner, bg=self.colors["accent2"], cursor="hand2")
            f.pack(fill=tk.X, pady=2, padx=4)
            tk.Label(f, text=s["name"], font=("Segoe UI", 10),
                     fg=self.colors["fg"], bg=self.colors["accent2"]).pack(anchor="w", padx=8, pady=2)
            tk.Label(f, text=f"{s['messages']} msgs | {s['saved_at'][:10]}",
                     font=("Segoe UI", 8), fg=self.colors["status_color"],
                     bg=self.colors["accent2"]).pack(anchor="w", padx=8, pady=(0, 4))
            f.bind("<Button-1>", lambda e, name=s["name"]: self._do_load_session(name, win))

    def _do_load_session(self, name, win):
        if hasattr(self.orchestrator, 'memory'):
            ok, msg = self.orchestrator.memory.load_session(name)
            self._set_status(msg, "#00ff88" if ok else "#ff4444")
            self.clear_response()
            self.append_response(msg)
        win.destroy()

    # ── Commands help ──

    def _show_help(self):
        lines = [f"  {cmd:16s} {desc}" for cmd, desc in self.COMMANDS.items()]
        text = "JARVIS Commands:\n" + "\n".join(lines)
        text += "\n\nShortcuts:\n"
        text += "  Tab            Toggle plan/build mode\n"
        text += "  Enter          Send message\n"
        text += "  Shift+Enter    New line\n"
        text += "  Ctrl+N         New session\n"
        text += "  Ctrl+S         Save session\n"
        text += "  Ctrl+O         Load session\n"
        text += "  Ctrl+L         Clear response\n"
        text += "  Escape         Stop speech\n"
        text += "  /help          Show this help"
        self.show_response(text)

    # ── Events ──

    def _bind_events(self):
        self.root.bind("<Return>", self._on_enter)
        self.root.bind("<Shift-Return>", lambda e: None)
        self.root.bind("<Tab>", self._on_tab)
        self.root.bind("<Escape>", lambda e: self._stop_speech())
        self.root.bind("<Control-n>", lambda e: self._new_session())
        self.root.bind("<Control-s>", lambda e: self._save_session())
        self.root.bind("<Control-o>", lambda e: self._load_session_dialog())
        self.root.bind("<Control-l>", lambda e: self.clear_response())
        self.voice_btn.bind("<Button-1>", lambda e: self._toggle_voice())

    def _on_enter(self, event):
        # Only trigger from input_field
        focused = self.root.focus_get()
        if focused == self.input_field:
            self._send_message()
        return "break"

    def _on_tab(self, event):
        self._toggle_plan_mode()
        return "break"

    def _send_message(self):
        text = self.input_field.get("1.0", tk.END).strip()
        if not text:
            return
        self.input_field.delete("1.0", tk.END)
        self.add_message("user", text)
        self.play_sound("message")
        self._set_status("◆ PROCESSING", "#ffaa00")
        if self.viz:
            self.viz.set_state("thinking")
        self._stop_speech()
        if self.listening:
            self.voice.stop_listening()
            self.listening = False
            self.voice_btn.configure(text="🎤")
        threading.Thread(target=self.orchestrator.process_input, args=(text,), daemon=True).start()

    def _upload_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(title="Upload file to JARVIS")
        if not path:
            return
        self._set_status(f"Uploaded: {path.split('/')[-1]}", "#00ff88")
        threading.Thread(target=self.orchestrator.process_input,
                         args=(f"File uploaded: {path}. Process it.",), daemon=True).start()

    def _toggle_voice(self):
        if not self.voice:
            self._set_status("Voice not available", "#ff4444")
            return
        if self.listening:
            self.voice.stop_listening()
            self.listening = False
            self.voice_btn.configure(text="🎤")
            self._set_status("◆ READY")
            if self.viz:
                self.viz.set_state("idle")
        else:
            self._stop_speech()
            self.listening = True
            self.voice_btn.configure(text="🔴")
            self._set_status("◆ LISTENING", "#00ff88")
            if self.viz:
                self.viz.set_state("listening")
            self.voice.start_listening()

    def _setup_voice_callbacks(self):
        def on_result(text):
            if text:
                self.root.after(0, lambda: self._process_voice(text))

        def on_error(err):
            self.root.after(0, lambda: self._set_status(f"Voice: {err}", "#ff4444"))
            self.root.after(0, self._reset_voice_btn)

        def on_stop():
            self.root.after(0, self._reset_voice_btn)

        self.voice.on("stt_result", on_result)
        self.voice.on("stt_error", on_error)
        self.voice.on("listening_stopped", on_stop)

    def _process_voice(self, text):
        # The mic keeps running (continuous conversation) - state stays in sync
        # with the engine, which is the source of truth for the button icon.
        if self.voice and handle_direct_mouse(text, self.voice):
            self._reset_voice_btn()
            self._set_status("")
            self.play_sound("done")
            return
        self.add_message("user", text)
        self.play_sound("message")
        if self.viz:
            self.viz.set_state("thinking")
        self._set_status("◆ PROCESSING", "#ffaa00")
        self._stop_speech()
        threading.Thread(target=self.orchestrator.process_input, args=(text,), daemon=True).start()

    def _reset_voice_btn(self):
        # Keep the UI in sync with what the microphone is actually doing.
        listening = bool(self.voice and self.voice.is_listening())
        self.listening = listening
        self.voice_btn.configure(text="🔴" if listening else "🎤")
        if not listening and getattr(self.viz, "state", None) == "listening":
            self.viz.set_state("idle")

    def after_safe(self, callback):
        self.root.after(0, callback)

    def _set_status(self, text, color=None):
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text=text, fg=color or self.colors["status_color"])

    def set_viz_state(self, state):
        if self.viz:
            self.viz.set_state(state)

    def append_response(self, text, tag="ai"):
        """Real-time streaming append"""
        if hasattr(self, "response_text") and self.response_text.winfo_exists():
            self.response_text.configure(state=tk.NORMAL)
            self.response_text.insert(tk.END, text, tag)
            self.response_text.see(tk.END)
            self.response_text.configure(state=tk.DISABLED)

    def show_response(self, text, tag="ai"):
        if hasattr(self, "response_text") and self.response_text.winfo_exists():
            self.response_text.configure(state=tk.NORMAL)
            self.response_text.delete("1.0", tk.END)
            self.response_text.insert(tk.END, text + "\n", tag)
            self.response_text.see(tk.END)
            self.response_text.configure(state=tk.DISABLED)

    def add_message(self, sender, text):
        """Add a labeled message to the log"""
        if hasattr(self, "response_text") and self.response_text.winfo_exists():
            tag = {"user": "user", "ai": "ai", "tool": "tool", "error": "error", "thinking": "thinking"}.get(sender, "ai")
            label = {"user": "YOU", "ai": "JARVIS", "tool": "TOOL", "error": "ERROR", "thinking": "THINK"}.get(sender, "AI")
            self.response_text.configure(state=tk.NORMAL)
            self.response_text.insert(tk.END, f"▸ {label} ", "bold")
            self.response_text.insert(tk.END, f"{text}\n", tag)
            self.response_text.see(tk.END)
            self.response_text.configure(state=tk.DISABLED)

    def clear_response(self):
        if hasattr(self, "response_text") and self.response_text.winfo_exists():
            self.response_text.configure(state=tk.NORMAL)
            self.response_text.delete("1.0", tk.END)
            self.response_text.configure(state=tk.DISABLED)

    def _anim_loop(self):
        if not self._anim_running:
            return
        try:
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            if w > 10 and h > 10:
                if not self.viz or self.viz.w != w or self.viz.h != h:
                    self.viz = WaveformVisualizer(self.canvas, w, h)

                # Determine amplitude source and manage speaking state
                is_tts = getattr(self.voice, '_tts_active', False) if self.voice else False
                if is_tts:
                    if self.viz.state != "speaking":
                        self.viz.set_state("speaking")
                    amp = getattr(self.voice, 'speaking_amplitude', 0.0)
                    self.viz.push_amplitude(amp)
                elif self.viz.state == "speaking":
                    self.viz.set_state("idle")
                elif self.listening and self.voice:
                    amp = getattr(self.voice, "current_amplitude", 0)
                    self.viz.push_amplitude(amp)

                self.viz.draw()
        except Exception:
            # a bad frame must never stop the animation loop
            pass
        finally:
            if self._anim_running:
                try:
                    self.root.after(33, self._anim_loop)
                except Exception:
                    pass

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("350x250")
        win.configure(bg=self.colors["bg"])
        tk.Label(win, text="JARVIS", font=("Segoe UI", 14, "bold"),
                 fg=self.colors["accent"], bg=self.colors["bg"]).pack(pady=10)
        tk.Label(win, text=f"Model: {self.orchestrator.ai.get_model() if hasattr(self.orchestrator, 'ai') else 'N/A'}",
                 fg=self.colors["fg"], bg=self.colors["bg"]).pack()
        tk.Label(win, text=f"Mode: {self.orchestrator.get_mode().upper()}",
                 fg=self.colors["fg"], bg=self.colors["bg"]).pack()
        tk.Label(win, text=f"Tools: {len(self.orchestrator.tools.list_tools()) if hasattr(self.orchestrator, 'tools') else 0}",
                 fg=self.colors["fg"], bg=self.colors["bg"]).pack(pady=(0, 10))
        tk.Button(win, text="Close", bg=self.colors["accent"],
                  fg="white", command=win.destroy).pack(pady=10)

    def _on_close(self):
        self._anim_running = False
        if self.voice:
            try:
                self.voice.stop_listening()
                self.voice.stop_speech()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()
