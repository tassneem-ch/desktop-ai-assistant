# 💜 DIVA — the feminine counterpart to JARVIS

DIVA is a **second, independently runnable edition** of the assistant in this repo.
Same engines — NVIDIA/OpenRouter AI, parallel Google STT, edge-tts playback, the
200-tool registry, governance, memory — with her own identity, personality, voice
and visuals. JARVIS and DIVA run side by side from the same checkout and their
settings never clash.

```bash
python -m diva_app.main      # run DIVA
python run_diva.py           # same thing (launcher, mirrors run_jarvis.py)
python -m diva_app.wake      # DIVA wake-word listener ("hey diva", "ديفا", …)
```

## Identity & personality

The persona lives in **one module**: `diva_app/identity.py`. It is built as a
*style layer placed above the unchanged tool guide*, so personality can never
weaken tool instructions or security/governance rules — that ordering is
structural, not a promise.

Three intensities, selectable in **Settings → PERSONALITY** (auto-saves,
applies to the very next message — no restart):

| Intensity | Character |
|---|---|
| **Soft Glam** | Elegant, composed, warmly professional. Minimal sass. |
| **Diva Mode** *(default)* | Confident, playful, witty. Sass that helps, never distracts. |
| **Full Diva** | Extra theatrical flair — bolder reactions, same precision. |

Every intensity shares the same non-negotiables:

1. Usefulness first; simple confirmations stay short.
2. **Never claim success without evidence** — planned vs attempted vs completed
   are always distinguished.
3. Precise and professional on technical tasks; pet names are used sparingly,
   never forced.
4. No emoji, spoken or displayed; plain text only.
5. Conversational context and follow-ups are maintained.
6. The style layer **never overrides** system-level safety rules, tool
   permissions or governance checks.

Greeting examples vary per run so she never repeats herself mechanically —
e.g. *"Well, well, well… look who needs their favorite diva. I'm listening,
darling."*

## Voice

| Setting | DIVA default |
|---|---|
| edge-tts voice | **`en-GB-SoniaNeural`** (warm, elegant British female) |
| Rate / pitch | `-3%` / `+0Hz` (crisp and natural) |
| Offline fallback | Windows SAPI — automatically picks a **female** voice (Zira) |
| Preview | Settings → VOICE → ♪ preview speaks a line instantly |

The voice is configurable at runtime (Settings → VOICE, combobox + preview)
from a curated list of verified female edge-tts voices:

```
en-GB-SoniaNeural   en-GB-LibbyNeural   en-US-JennyNeural   en-US-AriaNeural
en-US-MichelleNeural  en-AU-NatashaNeural  en-IN-NeerjaNeural
```

If edge-tts is unreachable (Microsoft occasionally waves 403s), the engine
falls back to the offline female voice after 3 failures and **re-probes every
5 minutes**, so the premium voice returns automatically when service resumes.

Environment overrides (set in `diva_app/__init__.py` via `setdefault`, so an
explicit value in your shell or `.env` still wins):

```bash
JARVIS_TTS_VOICE=en-GB-SoniaNeural
JARVIS_TTS_RATE=-3%
JARVIS_TTS_PITCH=+0Hz
JARVIS_TTS_SAPI_GENDER=female    # offline fallback stays a woman's voice
```

## Interface

Feminine, futuristic — built on the same Tk HUD (no heavy 3D engine):

- **Midnight-plum palette** with lavender / violet / rose / mint accents
  (`DIVA_THEME` in `diva_app/gui.py`)
- **Animated orb** replacing the eye: luminous lavender core with layered glow,
  twinkle field, tilted orbit ring and two orbiting satellites
- **State-driven animation** — `idle` (slow breathing), `listening` (expanding
  rose wave rings), `thinking` (champagne orbit arcs), `speaking`
  (amplitude-reactive halo ring), `error` (red-rose)
- **Chime sounds** replacing the HUD beeps (soft arpeggio on startup, sparkles
  on completion, warm — not harsh — error tone)
- Greeting shown in chat at startup (text only; no surprise audio)

## Settings

`File > Settings` contains everything JARVIS has (provider API key + self-test,
model picker, governance, TTS engine) **plus DIVA sections**:

- **PERSONALITY** — three intensity radios
- **VOICE** — voice picker + ♪ preview
- **ASSISTANT NAME** — her name (updates window, title label and persona)
- **WAKE WORDS** — comma-separated list used by `python -m diva_app.wake`

All four auto-save to `%APPDATA%\DivaAssistant\config.json` as you type.

## Configuration separation

| | JARVIS | DIVA |
|---|---|---|
| Config/data dir | `%APPDATA%\JarvisAssistant\` | `%APPDATA%\DivaAssistant\` |
| Wake words | `jarvis, hey jarvis, أفق, …` | `diva, hey diva, ok diva, hello diva, ديفا, …` |
| Launcher | `run_jarvis.py` | `run_diva.py` |

On **first run** DIVA copies the AI credentials (provider + API key + model)
from the JARVIS config once, so she works immediately without re-entering the
key; after that the two configs evolve independently. Changing a key in one
edition never touches the other.

The separation is driven by a single backward-compatible seam:
`JARVIS_APPDATA_DIR` (default `JarvisAssistant`) is read by the shared config,
memory and tools modules — DIVA sets it to `DivaAssistant` **before** importing
any shared engine.

## Wake word listener

```bash
python -m diva_app.wake                 # uses the saved wake words
python -m diva_app.wake --words "astra, hey astra"
python -m diva_app.wake --install-service   # Windows startup (shared helper)
```

When a wake word is heard (English or Arabic, case-insensitive), the listener
launches `run_diva.py` — it never launches JARVIS, and the original
`python wake_word.py` still launches only JARVIS.

## Debug hooks

```bash
# open the DIVA Settings dialog right after startup
DIVA_OPEN_SETTINGS=1 python -m diva_app.main

# full self-test: the 12 base checks + 10 DIVA checks (intensity persistence,
# persona prompt, voice switch, name, wake words) + real NVIDIA tool pipeline
DIVA_OPEN_SETTINGS=1 DIVA_SETTINGS_SELFTEST=1 python -m diva_app.main
```

(The classic `JARVIS_OPEN_SETTINGS` / `JARVIS_SETTINGS_SELFTEST` hooks work for
DIVA too — the `DIVA_*` names are aliases.)

## Architecture

```
diva_app/
  __init__.py   env bootstrap (data dir, female voice, rate/pitch) — runs FIRST
  identity.py   name, 3 intensity personas, prompt builder, curated voices
  config.py     settings accessors + one-time credential seeding from JARVIS
  core.py       DivaOrchestrator = AgentOrchestrator with DIVA system prompt
  gui.py        DIVA_THEME, DivaOrbVisualizer, DivaSounds, DivaGUI (+ settings)
  main.py       DivaApp (reuses JarvisApp wiring via ORCHESTRATOR_CLS/GUI_CLS)
  wake.py       DIVA wake-word listener
run_diva.py     launcher (mirrors run_jarvis.py)
```

Reused **unchanged** from `jarvis_app`: AI engine, tools, security, memory,
voice engine (via env-configurable voice/pitch/rate), config store (via the
data-dir seam). The shared code only gained backward-compatible hooks —
class-level branding attributes, a visualizer factory, a Settings-section
hook, parameterized wake words and env-driven voice settings — so JARVIS
behaves exactly as before (verified: 12/12 settings self-test, unchanged UI).
