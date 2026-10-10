"""DIVA GUI — JARVIS's HUD re-dressed as a feminine, futuristic interface.

Reuses JarvisGUI (menus, sessions, streaming, settings plumbing, self-test)
via subclassing and replaces: theme palette, brand strings, the canvas
avatar (glowing lavender orb), sound accents and the Settings sections for
personality intensity / voice / name / wake words.
"""

import os
import random
import threading
import tkinter as tk
import tkinter.ttk as ttk

from jarvis_app.gui import JarvisGUI, HudSounds

from diva_app import config as dcfg
from diva_app import identity


# ── colour helpers ─────────────────────────────────────────────────────

def _hx(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        v = 0
    return f"{max(0, min(255, v)):02x}"


def _rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _blend(a, b, t):
    """Mix colours a -> b (t in 0..1)."""
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    t = max(0.0, min(1.0, t))
    return f"#{_hx(ra + (rb - ra) * t)}{_hx(ga + (gb - ga) * t)}{_hx(ba + (bb - ba) * t)}"


# ── theme ──────────────────────────────────────────────────────────────

DIVA_THEME = {
    "bg":      "#12081f",   # midnight purple
    "fg":      "#f0e6ff",   # soft white-lilac
    "accent":  "#c084fc",   # lavender
    "accent2": "#1c0f30",   # deep plum panel
    "accent3": "#2a1548",   # dark violet
    "border":  "#a855f7",   # violet
    "status_color": "#b39ddb",
    "success": "#7dffc4",   # soft mint
    "warn":    "#ffb86b",   # champagne
    "error":   "#ff6b9d",   # dusty rose
    "field":   "#1a0b2e",
    "plan_bg": "#2a1548",
    "plan_fg": "#7dffc4",
    "plan_active_bg": "#4a2a3d",
    "plan_active_fg": "#ffb86b",
    "search_highlight": "#4a2d6b",
}


# ── sounds ─────────────────────────────────────────────────────────────

class DivaSounds(HudSounds):
    """Softer, chime-like accents built on the shared WAV playback."""

    def play(self, sound_name):
        if not self.enabled:
            return
        try:
            if sound_name == "startup":     # rising sparkle arpeggio
                buf = (self._gen_beep(880, 70)
                       + self._gen_beep(1108, 70)[35:]
                       + self._gen_beep(1318, 90)[45:])
            elif sound_name == "message":   # single soft ping
                buf = self._gen_beep(1108, 55)
            elif sound_name == "thinking":  # gentle two-note
                buf = self._gen_beep(740, 45) + self._gen_beep(932, 45)[22:]
            elif sound_name == "error":     # warm, not harsh
                buf = self._gen_beep(392, 110)
            elif sound_name == "done":      # high sparkle pair
                buf = self._gen_beep(1318, 50) + self._gen_beep(1760, 60)[30:]
            elif sound_name == "alert":
                buf = self._gen_beep(1108, 55) + self._gen_beep(880, 55)[30:]
            else:
                buf = self._gen_beep(988, 50)
            self._play_buf(buf)
        except Exception:
            pass


# ── avatar: glowing orb ────────────────────────────────────────────────

class DivaOrbVisualizer:
    """Animated lavender/violet orb with feminine, state-driven motion.

    Same interface as WaveformVisualizer: (canvas, w, h), .w/.h/.state,
    set_state(), push_amplitude(), draw().
    """

    STATE_COLORS = {
        "idle":      "#c084fc",  # lavender
        "listening": "#ff6b9d",  # rose
        "thinking":  "#ffb86b",  # champagne
        "speaking":  "#a78bfa",  # violet
        "error":     "#ff4d6d",
    }

    def __init__(self, canvas, width, height):
        self.canvas = canvas
        self.w = width
        self.h = height
        self.cx = width // 2
        self.cy = height // 2
        self.state = "idle"
        self.phase = 0.0
        self._amp = 0.0
        self._buffer = [0.0] * 40
        self.bg = DIVA_THEME["bg"]
        # fixed twinkle field (deterministic — no per-frame reseed)
        rng = random.Random(7)
        self._stars = [(rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0, 6.28))
                       for _ in range(14)]

    # ── interface ──

    def set_state(self, state):
        if state in self.STATE_COLORS or state == "idle":
            self.state = state

    def push_amplitude(self, amp):
        try:
            amp = float(amp)
        except (TypeError, ValueError):
            amp = 0.0
        self._buffer.append(amp)
        self._buffer = self._buffer[-40:]
        self._amp = amp

    # ── drawing ──

    def draw(self):
        c = self.canvas
        c.delete("all")
        speed = {"speaking": 0.12, "listening": 0.10, "thinking": 0.16}.get(self.state, 0.05)
        self.phase += speed

        self._draw_wash()
        self._draw_stars()
        self._draw_orb()
        self._draw_state_motion()
        self._draw_satellites()
        self._draw_labels()

    def _color(self):
        return self.STATE_COLORS.get(self.state, self.STATE_COLORS["idle"])

    def _draw_wash(self):
        """Deep radial wash so the panel feels glassy, not flat."""
        c, col = self.canvas, self.bg
        R = max(self.w, self.h) * 0.75
        steps = 7
        for i in range(steps, 0, -1):
            r = R * i / steps
            shade = _blend(col, self.STATE_COLORS["idle"], 0.05 * (1 - i / steps))
            self.canvas.create_oval(self.cx - r, self.cy - r, self.cx + r, self.cy + r,
                                    fill=shade, outline="")

    def _draw_stars(self):
        for sx, sy, ph in self._stars:
            tw = 0.5 + 0.5 * math_sin(self.phase * 0.8 + ph)
            a = int(30 + 60 * tw)
            x, y = sx * self.w, sy * self.h
            r = 1 + (1 if tw > 0.75 else 0)
            self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                    fill=f"#{_hx(a + 100)}{_hx(a)}{_hx(a + 160)}", outline="")

    def _draw_orb(self):
        c = self.canvas
        col = self._color()
        base = min(self.w, self.h) * 0.11
        breathe = 1.0 + 0.06 * math_sin(self.phase * 1.4)
        if self.state == "speaking":
            breathe += min(self._amp * 1.6, 0.5)
        r_core = base * breathe

        # soft glow layers (Tk has no alpha -> blend toward bg)
        layers = 9
        for i in range(layers, 0, -1):
            r = r_core * (1.0 + 0.85 * i / layers)
            t = i / layers
            shade = _blend(col, self.bg, 0.55 + 0.4 * t)
            c.create_oval(self.cx - r, self.cy - r, self.cx + r, self.cy + r,
                          fill=shade, outline="")
        # luminous core
        c.create_oval(self.cx - r_core, self.cy - r_core, self.cx + r_core, self.cy + r_core,
                      fill=_blend(col, "#ffffff", 0.55), outline="")
        c.create_oval(self.cx - r_core * 0.55, self.cy - r_core * 0.55,
                      self.cx + r_core * 0.55, self.cy + r_core * 0.55,
                      fill="#fdf7ff", outline="")
        # rim
        c.create_oval(self.cx - r_core * 1.35, self.cy - r_core * 1.35,
                      self.cx + r_core * 1.35, self.cy + r_core * 1.35,
                      outline=_blend(col, "#ffffff", 0.25), width=1)

    def _draw_state_motion(self):
        c, col = self.canvas, self._color()
        base = min(self.w, self.h) * 0.11

        if self.state == "listening":
            # expanding wave rings
            for k in range(3):
                t = (self.phase * 0.7 + k / 3) % 1.0
                r = base * (1.4 + 2.2 * t)
                a = int(160 * (1 - t))
                c.create_oval(self.cx - r, self.cy - r, self.cx + r, self.cy + r,
                              outline=f"#{_hx(a + 60)}{_hx(a // 2)}{_hx(a)}", width=1)
        elif self.state == "thinking":
            # orbiting arc segments
            import math
            for k in range(3):
                start = self.phase * 2.2 + k * 2.09
                r = base * (1.7 + 0.25 * k)
                for s in range(10):
                    a0 = start + s * 0.06
                    x = self.cx + r * math.cos(a0)
                    y = self.cy + r * math.sin(a0)
                    fade = 1 - s / 10
                    c.create_oval(x - 2 * fade, y - 2 * fade, x + 2 * fade, y + 2 * fade,
                                  fill=_blend(col, self.bg, 1 - fade * 0.9), outline="")
        elif self.state == "speaking":
            # amplitude-reactive halo ring
            import math
            n = 48
            r_base = base * 1.7
            pts = []
            avg = sum(self._buffer) / max(len(self._buffer), 1)
            for i in range(n + 1):
                a = (i / n) * 2 * math.pi
                r = r_base + (self._buffer[i % len(self._buffer)] * base * 2.2
                              + avg * base)
                pts.extend([self.cx + r * math.cos(a), self.cy + r * math.sin(a)])
            if len(pts) >= 4:
                c.create_line(*pts, fill=_blend(col, "#ffffff", 0.3), width=2, smooth=True)

    def _draw_satellites(self):
        import math
        col = self._color()
        base = min(self.w, self.h) * 0.11
        for k, (speed, rad, size) in enumerate(((0.9, 2.5, 3), (-0.55, 3.1, 2))):
            a = self.phase * speed + k * 3.14
            r = base * rad
            x = self.cx + r * math.cos(a)
            y = self.cy + r * 0.62 * math.sin(a)   # tilted orbit -> depth
            c = self.canvas
            c.create_oval(x - size * 2, y - size * 2, x + size * 2, y + size * 2,
                          fill=_blend(col, self.bg, 0.82), outline="")
            c.create_oval(x - size, y - size, x + size, y + size,
                          fill=_blend(col, "#ffffff", 0.45), outline="")

    def _draw_labels(self):
        pulse = 90 + 50 * math_sin(self.phase)
        dim = f"#{_hx(int(pulse * 0.7))}{_hx(int(pulse * 0.55))}{_hx(int(pulse))}"
        bright = _blend(self._color(), "#ffffff", 0.3)
        self.canvas.create_text(10, 10, text="D . I . V . A", font=("Consolas", 6),
                                fill=dim, anchor="nw")
        self.canvas.create_text(self.w - 10, 10, text="v1.0", font=("Consolas", 6),
                                fill=dim, anchor="ne")
        self.canvas.create_text(10, self.h - 16, text=f"◆ {self.state.upper()}",
                                font=("Consolas", 6), fill=bright, anchor="sw")
        self.canvas.create_text(self.w - 10, self.h - 16,
                                text=f"{int(self.phase * 10) % 100:02d}%",
                                font=("Consolas", 6), fill=dim, anchor="se")


def math_sin(x):
    import math
    return math.sin(x)


# ── main window ────────────────────────────────────────────────────────

GREETINGS = {
    "soft_glam": [
        "Hello. I'm DIVA — at your service.",
        "Good to see you. I'm ready when you are.",
    ],
    "diva": [
        "Well, well, well… look who needs their favorite diva. I'm listening, darling.",
        "You called? DIVA is online, gorgeous — what's first?",
        "Darling, the day officially got better. What are we doing?",
    ],
    "full_diva": [
        "You summoned the best, darling — DIVA is online. Speak freely, I can take it.",
        "Finally, someone with taste. DIVA reporting for duty, babe.",
    ],
}


class DivaGUI(JarvisGUI):
    THEME = DIVA_THEME
    WINDOW_TITLE = "DIVA"
    TITLE_TEXT = "◈ D.I.V.A"
    AI_NAME = "DIVA"
    HELP_TITLE = "DIVA Commands:"
    FILE_DIALOG_TITLE = "Upload file to DIVA"
    SETTINGS_TITLE = "Settings — DIVA"
    SETTINGS_HEADER = "◈ D . I . V . A   SETTINGS"
    SETTINGS_GEOMETRY = "440x725"
    SOUNDS_CLS = DivaSounds

    def _make_visualizer(self, canvas, w, h):
        return DivaOrbVisualizer(canvas, w, h)

    # ── greeting ──

    def show_greeting(self):
        """Varied startup greeting (text only — no surprise audio)."""
        level = dcfg.get_intensity()
        name = dcfg.get_name()
        line = random.choice(GREETINGS.get(level, GREETINGS["diva"]))
        line = line.replace("DIVA", name)
        self.add_message("ai", line)
        self._set_status(f"◆ {name.upper()} ONLINE", self.colors["success"])

    # ── settings: personality / voice / identity / wake words ──────────

    def _settings_extra(self, win, set_status):
        C = self.colors
        voice = self.voice
        orch = self.orchestrator

        # ── PERSONALITY ──
        tk.Label(win, text="PERSONALITY", font=("Consolas", 9, "bold"),
                 fg=C["status_color"], bg=C["bg"]).pack(anchor="w", padx=18, pady=(12, 0))
        pers_frame = tk.Frame(win, bg=C["accent2"], highlightbackground=C["border"],
                              highlightthickness=1, bd=0)
        pers_frame.pack(fill=tk.X, padx=16, pady=4)

        intensity_var = tk.StringVar(value=dcfg.get_intensity())
        for level in identity.INTENSITY_LEVELS:
            tk.Radiobutton(pers_frame, text=identity.INTENSITY_LABELS[level],
                           variable=intensity_var, value=level,
                           font=("Consolas", 8), fg=C["fg"], bg=C["accent2"],
                           selectcolor=C["field"], activebackground=C["accent2"],
                           activeforeground=C["accent"], anchor="w"
                           ).pack(fill=tk.X, padx=10, pady=1)

        def on_intensity(*_):
            level = dcfg.set_intensity(intensity_var.get())
            if hasattr(orch, "set_intensity"):
                orch.intensity = level
            set_status(f"✓ personality: {identity.INTENSITY_LABELS[level]} (auto-saved)",
                       C["success"])

        intensity_var.trace("w", on_intensity)

        # ── VOICE ──
        tk.Label(win, text="VOICE", font=("Consolas", 9, "bold"),
                 fg=C["status_color"], bg=C["bg"]).pack(anchor="w", padx=18, pady=(10, 0))
        voice_row = tk.Frame(win, bg=C["bg"])
        voice_row.pack(fill=tk.X, padx=16, pady=4)
        voice_var = tk.StringVar(value=dcfg.get_voice())
        voice_box = ttk.Combobox(voice_row, textvariable=voice_var, font=("Consolas", 8),
                                 values=identity.FEMALE_VOICES, state="normal")
        voice_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def on_voice(*_):
            v = dcfg.set_voice(voice_var.get())
            if voice:
                voice.set_edge_voice(v)
            set_status(f"✓ voice: {v} (auto-saved)", C["success"])

        voice_var.trace("w", on_voice)

        def preview():
            if voice:
                voice.speak(f"Hello, darling. This is {dcfg.get_name()} — how do I sound?")
                set_status("♪ previewing voice…", C["accent"])

        tk.Button(voice_row, text="♪ preview", font=("Consolas", 8),
                  bg=C["accent3"], fg=C["fg"], relief="flat", padx=8,
                  command=preview).pack(side=tk.LEFT, padx=(6, 0))

        # ── IDENTITY ──
        tk.Label(win, text="ASSISTANT NAME", font=("Consolas", 9, "bold"),
                 fg=C["status_color"], bg=C["bg"]).pack(anchor="w", padx=18, pady=(10, 0))
        name_row = tk.Frame(win, bg=C["bg"])
        name_row.pack(fill=tk.X, padx=16, pady=4)
        name_var = tk.StringVar(value=dcfg.get_name())
        tk.Entry(name_row, textvariable=name_var, font=("Consolas", 9),
                 bg=C["field"], fg=C["fg"], insertbackground=C["fg"],
                 relief="solid", bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def on_name(*_):
            n = dcfg.set_name(name_var.get())
            if hasattr(orch, "assistant_name"):
                orch.assistant_name = n
            try:
                self.root.title(n)
                self.title_lbl.configure(text=f"◈ {'. '.join(n.upper())}")
            except Exception:
                pass
            set_status(f"✓ name: {n} (auto-saved)", C["success"])

        name_var.trace("w", on_name)

        # ── WAKE WORDS ──
        tk.Label(win, text="WAKE WORDS (comma-separated)", font=("Consolas", 9, "bold"),
                 fg=C["status_color"], bg=C["bg"]).pack(anchor="w", padx=18, pady=(10, 0))
        wake_row = tk.Frame(win, bg=C["bg"])
        wake_row.pack(fill=tk.X, padx=16, pady=4)
        wake_var = tk.StringVar(value=", ".join(dcfg.get_wake_words()))
        tk.Entry(wake_row, textvariable=wake_var, font=("Consolas", 8),
                 bg=C["field"], fg=C["fg"], insertbackground=C["fg"],
                 relief="solid", bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def on_wake(*_):
            words = dcfg.set_wake_words(wake_var.get())
            set_status(f"✓ wake words saved — {len(words)} active (used by diva_app.wake)",
                       C["success"])

        wake_var.trace("w", on_wake)

        # ── DIVA self-test additions ──
        if os.environ.get("JARVIS_SETTINGS_SELFTEST"):
            self.root.after(1400, lambda: self._diva_selftest(
                intensity_var, voice_var, name_var, wake_var, orch, voice))

    def _diva_selftest(self, intensity_var, voice_var, name_var, wake_var, orch, voice):
        """Extra DIVA checks layered on top of the inherited self-test."""
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        results = []

        def check(name, cond, extra=""):
            results.append(bool(cond))
            print(f"{'PASS' if cond else 'FAIL'}: {name} {extra}", flush=True)

        orig_intensity = dcfg.get_intensity()
        orig_voice = dcfg.get_voice()
        orig_name = dcfg.get_name()
        orig_words = ", ".join(dcfg.get_wake_words())
        try:
            # intensity persists and reaches the orchestrator
            intensity_var.set("full_diva")
            check("intensity persisted", dcfg.get_intensity() == "full_diva")
            check("orchestrator picked up intensity", getattr(orch, "intensity", "") == "full_diva")
            prompt = orch._get_system_prompt()
            check("prompt carries DIVA persona", "You are DIVA" in prompt)
            check("prompt reflects Full Diva", "Full Diva" in prompt)
            check("tool guide intact in DIVA prompt", "calculator" in prompt and "input_control" in prompt)

            # voice persists and reaches the engine
            voice_var.set("en-US-JennyNeural")
            check("voice persisted", dcfg.get_voice() == "en-US-JennyNeural")
            check("engine switched voice", voice and voice.get_edge_voice() == "en-US-JennyNeural")

            # name persists
            name_var.set("Astra")
            check("name persisted", dcfg.get_name() == "Astra")
            check("prompt uses custom name", "You are Astra" in orch._get_system_prompt())

            # wake words persist and parse
            wake_var.set("nova, hey nova")
            check("wake words persisted", dcfg.get_wake_words() == ["nova", "hey nova"])
        except Exception as e:
            check("diva selftest completed without exception", False, f"error={e}")
        finally:
            # restore the user's real settings
            try:
                intensity_var.set(orig_intensity)
                voice_var.set(orig_voice)
                name_var.set(orig_name)
                wake_var.set(orig_words)
            except Exception:
                pass
        passed = sum(results)
        print(f"DIVA SELFTEST {'PASSED' if passed == len(results) and results else 'FAILED'} "
              f"({passed}/{len(results)})", flush=True)
