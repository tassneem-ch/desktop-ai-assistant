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

## Use your own API key

Edit `.env` and set:
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```
Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys).

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

`nvidia/nemotron-3-super-120b-a12b:free` — ~2.2 s first token, correct JSON tool
calls. If a model is rate-limited, removed or returns an empty reply, JARVIS
automatically fails over to the next working free model and remembers the one
that worked:

`nvidia/nemotron-3-super-120b-a12b:free` → `apodex/apodex-1.1-mini:free` →
`openrouter/free` → `cohere/north-mini-code:free` → `poolside/laguna-xs-2.1:free`

## Troubleshooting

| Symptom | Fix |
|---|---|
| No mic / wrong mic | Set `JARVIS_MIC_DEVICE=<index>` in `.env` (list shown above) |
| Robotic voice | `JARVIS_TTS=auto` needs the network for the neural voice — `JARVIS_TTS=sapi` forces the offline voice |
| No audio at all | Check the Windows volume mixer; MCI playback is used for MP3 output |
| "all free models are busy" | Wait a few seconds (free tier rate limits) or set your own `OPENROUTER_API_KEY` |
| Wrong language recognised | Set `JARVIS_STT_LANG=ar-SA` (or `en-US`) in `.env` |

## License

MIT
