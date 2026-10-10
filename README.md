# J.A.R.V.I.S

> Fully autonomous AI desktop assistant with voice, vision, and **200 tools**.

## 🚀 One-Command Setup

```bash
# Windows (open Command Prompt as Admin):
python setup.py

# Kali Linux / Debian:
python3 setup.py
```

**That's it.** The API key is built-in — it works immediately after setup.

---

## Manual Setup

### Windows
```
requirements.bat
python -m jarvis_app.main
```

### Kali Linux
```
chmod +x requirements.sh && sudo ./requirements.sh
python3 run_jarvis.py
```

## Use your own API key (from the GUI)

**File → Settings → "PROVIDER API KEY"** — paste an NVIDIA or OpenRouter key,
hit **SAVE KEY**, done. The provider is auto-detected from the key shape:

| Key starts with | Provider | Endpoint |
|---|---|---|
| `nvapi-…` | **NVIDIA NIM** (free tier) | `integrate.api.nvidia.com` |
| `sk-or-…` | OpenRouter | `openrouter.ai` |

The key is **saved automatically** to `%APPDATA%\JarvisAssistant\config.json`
(outside the repo, never committed) and reloaded on every launch. You can also
type **any model id** directly into the Settings model box — it is saved the
moment you type it. "Remove saved key" reverts to the built-in key.

Prefer files? Set `NVIDIA_API_KEY=` or `OPENROUTER_API_KEY=` in `.env`
(GUI-saved keys win over `.env`). Get free keys at
[NVIDIA build.nvidia.com](https://build.nvidia.com) /
[openrouter.ai/keys](https://openrouter.ai/keys).

---

## What it does

- **Talk to it** — British male JARVIS voice, listens and responds
- **Sees your screen** — Real-time vision, frame change detection
- **Controls your PC** — Mouse, keyboard, windows, volume, media, files, browser
- **200 tools** — web search, calculator, weather, forecast, currency, stock, movie, recipe, email, calendar, timer, alarms, text manipulation, regex, diff, sort, UUID, base64, Hacker News, Reddit, Wikipedia, lyrics, facts, image info, ping, DNS, public IP, stopwatch, confirm/prompt dialogs, show window, alert, CSV table, JSON format, brightness, screen res, counter, chart, progress bar, encode/decode, markdown render, color picker.
  **Student & Teacher (73):** flashcard, quiz, study_set, grade_calc, gpa, assignment, study_timer, attendance, essay_outline, citation, thesaurus, statistics, prime, matrix, periodic_table, physics_ref, formula, doi_lookup, arxiv, vocab, mnemonic, note_summarize, conjugation, spell_check, group_picker, rubric, syllabus, practice_problem, science_fact, study_plan, note_organizer, bibliography, equation_solve, lesson_plan, worksheet, exam, progress_report, seating_chart, icebreaker, discussion, learning_objectives, activity, feedback, reading_list, study_guide, timeline, mind_map, thesis_statement, abstract, flashcard_import, cheat_sheet, concept_map, quiz_me, plagiarism_check, peer_review, lab_report, research_proposal, book_report, presentation_outline, debate_topic, writing_prompt, math_word_problem, project_planner, self_assessment, homework_helper, flashcard_review, test_review, classroom_game, goal_setter, field_trip, case_study, note_template, study_break.
  **Cybersecurity (20):** port_scanner, subdomain_scan, whois_lookup, ssl_inspector, http_headers, url_analyzer, ip_reputation, cve_search, dns_enum, mac_vendor, file_analyzer, cipher, log_parser, network_map, user_enum, exploit_search, phishing_detector, hash_id, password_audit, threat_intel.

> See [`TOOLS.md`](TOOLS.md) for a full reference — every tool with its parameters and a ~3-line description.
- **Iron Man HUD** — Animated eye with radar sweep, targeting reticle, data readouts

## 💜 DIVA — the feminine edition

DIVA is a **second, independently runnable edition** of the same assistant: identical
engines (AI, STT/TTS, 200 tools, security, memory) with her own identity, voice and UI.
Both editions run from the same checkout and never touch each other's settings.

```bash
python -m diva_app.main     # or: python run_diva.py
python wake_word.py         # JARVIS listener (unchanged)
python -m diva_app.wake     # DIVA listener ("hey diva" / "ديفا" launches run_diva.py)
```

| | DIVA | JARVIS |
|---|---|---|
| **Voice** | `en-GB-SoniaNeural` (warm female), rate −3 %, pitch +0 Hz, female SAPI fallback | `en-GB-RyanNeural` (male) |
| **Personality** | Witty diva persona, 3 intensities: **Soft Glam / Diva Mode (default) / Full Diva** | Standard JARVIS prompt |
| **UI** | Midnight-plum theme, glowing lavender orb, rose/mint status, chime sounds | Cyan HUD, eye, beeps |
| **Settings** | Extra sections: personality, voice + preview, name, wake words | API key + model |
| **Data** | `%APPDATA%\DivaAssistant\` (AI key auto-seeded once from JARVIS) | `%APPDATA%\JarvisAssistant\` |
| **Wake words** | `diva, hey diva, ok diva, hello diva, ديفا, …` | `jarvis, hey jarvis, أفق, …` |

The persona lives in one auditable module (`diva_app/identity.py`): the style layer sits
**above** the unchanged tool/security instructions, so personality can never override
governance. All intensity levels keep the same honesty rules (never claim success that
didn't happen; distinguish planned / attempted / completed). Full details: [`DIVA.md`](DIVA.md).

## 🎙️ Voice (STT + TTS)

| | |
|---|---|
| **STT** | Google speech API, **en-US and ar-SA are queried in parallel** (~1 s) and the higher-confidence transcript wins. End-of-phrase detection uses voiced-sample counting, so noise blips are ignored. |
| **TTS** | `edge-tts` **en-GB-RyanNeural** (the JARVIS voice). Every sentence of a reply is synthesized in **parallel** on a warm, shared connection (first audio ≈ 0.6 s) and played back through the Windows MCI API. If the network is down it automatically switches to the offline Windows (SAPI) voice. |
| **Never blocks** | `speak()` queues audio on a worker thread, so the UI never freezes and two voices can never overlap. `Esc` / the stop button cuts speech instantly. |
| **Mic** | Uses the Windows **default input device** at its native rate (no more hard-coded device index or 16 kHz mismatch), with a 0.4 s noise-floor calibration. |

### Voice settings (`.env`)

```bash
JARVIS_TTS=auto          # auto | edge | sapi   (sapi = offline & instant)
JARVIS_TTS_VOICE=en-GB-RyanNeural
JARVIS_STT_LANG=en-US    # primary language, ar-SA always tried in parallel
JARVIS_MIC_DEVICE=1      # omit to use the Windows default microphone
```

List microphones:
```
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### Wake word listener (optional)

```
python wake_word.py                 # say "hey jarvis" / "أفق" to launch JARVIS
python wake_word.py --install-service
```

## Default model

**NVIDIA NIM** `nvidia/nemotron-3-super-120b-a12b` — measured ~1.6 s first token
with correct JSON tool calls (free `nvapi-` key, seeded in Settings).

Failover: if a model is rate-limited, removed or returns an empty reply,
JARVIS tries the next model, then crosses over to the free OpenRouter pool and
remembers whichever one worked:

```
nemotron-3-super-120b-a12b → nemotron-3-nano-omni-30b-a3b-reasoning
→ llama-3.1-nemotron-70b-instruct → [OpenRouter free]: nemotron-3-super:free
→ apodex-1.1-mini:free → openrouter/free → north-mini-code:free → laguna-xs-2.1:free
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| No mic / wrong mic | Set `JARVIS_MIC_DEVICE=<index>` in `.env` (list shown above) |
| Robotic voice | `JARVIS_TTS=auto` needs the network for the neural voice — `JARVIS_TTS=sapi` forces the offline voice |
| No audio at all | Check the Windows volume mixer; MCI playback is used for MP3 output |
| "all free models are busy" | Wait a few seconds (free tier rate limits) or paste your own key in **File → Settings** |
| Wrong language recognised | Set `JARVIS_STT_LANG=ar-SA` (or `en-US`) in `.env` |
| Key not remembered | It saves to `%APPDATA%\JarvisAssistant\config.json` — check that file exists and isn't read-only |

### Debug hooks

```bash
# open the Settings dialog right after startup
JARVIS_OPEN_SETTINGS=1 python -m jarvis_app.main

# drive the Settings dialog end-to-end (detect/save/persist/model) and print
# PASS/FAIL lines + a dialog screenshot to %TEMP%\opencode\settings_capture.png
JARVIS_OPEN_SETTINGS=1 JARVIS_SETTINGS_SELFTEST=1 python -m jarvis_app.main

# DIVA accepts the same hooks, plus branded aliases:
#   DIVA_OPEN_SETTINGS=1 / DIVA_SETTINGS_SELFTEST=1 python -m diva_app.main
# (adds personality/voice/name/wake-word checks on top of the 12 base ones)
```

## License

MIT
