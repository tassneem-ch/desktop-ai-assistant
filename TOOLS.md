# JARVIS Tool Reference — 200 Tools

## Core Tools (107)

| Tool | Params | Description |
|------|--------|-------------|
| `web_search` | `query` | Searches DuckDuckGo and returns up to 6 results with title, URL, and snippet. |
| `file_read` | `path`, `action` | Reads file content (up to 5K chars), lists directory entries, or returns file info/size. |
| `file_write` | `path`, `content`, `action` | Writes text content to file (auto-creates parent dirs) or deletes a file. |
| `run_command` | `command`, `action` | Executes a shell command with 30s timeout and returns stdout/stderr. |
| `calculator` | `expression`/`expr` | Safely evaluates math expressions using a restricted subset of Python math. |
| `weather` | `location`/`query` | Fetches current weather from wttr.in: conditions, temperature, wind, humidity. |
| `time` | — | Shows local time with timezone and UTC time in readable format. |
| `system_info` | — | Reports CPU%, RAM usage, disk usage, boot time, and process count via psutil. |
| `screenshot` | — | Captures full screen to PNG in temp folder using pyautogui. |
| `notes` | `action`, `title`, `content` | Saves, reads, lists, or deletes text notes in a persistent local folder. |
| `todo` | `action`, `task`, `priority` | Manages to-do list: add, list (with filter), mark done, remove, clear completed. |
| `clipboard` | `action`, `text` | Gets clipboard contents or sets new text via pyperclip. |
| `define` | `word`/`query` | Looks up word definition, phonetic, and part-of-speech from Free Dictionary API. |
| `joke` | — | Returns a random joke from JokeAPI (no NSFW/racist/sexist). |
| `quote` | — | Fetches random inspirational quote from zenquotes/quotable with fallbacks. |
| `password` | `length`, `symbols` | Generates a cryptographically random password with configurable length and symbols. |
| `convert` | `value`, `from`, `to` | Converts between units: length, mass, temperature, speed. |
| `file_search` | `pattern`, `path` | Walks a directory tree and returns filenames matching a substring pattern. |
| `battery` | — | Reports battery percentage, charging status, and estimated time remaining via psutil. |
| `process` | `action`, `name` | Lists running processes with CPU/MEM% or kills a process by name. |
| `random` | `action`, `min`/`max` | Generates random number, coin flip, dice roll, choice from list, or UUID. |
| `news` | `topic`/`query` | Fetches top headlines or topic-specific news from Google News RSS. |
| `shorten` | `url` | Shortens a URL using is.gd API and returns the shortened link. |
| `ip_geo` | `ip`/`query` | Geolocates an IP address: city, region, country, ISP, lat/lon via ip-api.com. |
| `translate` | `text`, `target`, `source` | Translates text between languages via MyMemory translation API. |
| `crypto` | `action`, `data`, `algorithm` | Computes hash, HMAC, Base64 encode/decode, or file hash. |
| `qr_code` | `action`, `data` | Generates a QR code PNG image or decodes a QR from an image file. |
| `window` | `action`, `hwnd`/`name` | Lists, maximizes, minimizes, restores, focuses, closes, or moves windows. |
| `audio` | `action`, `level`/`mute` | Gets/sets system volume level, toggles mute, lists audio devices. |
| `network` | `action`, `host` | Shows network interfaces, active connections, or pings a host. |
| `archive` | `action`, `paths`, `archive` | Creates or extracts zip/tar.gz archives, or lists archive contents. |
| `json` | `action`, `data`, `path` | Parses, queries (JSONPath), validates, or pretty-prints JSON data. |
| `hash` | `action`, `data`, `algorithm` | Hashes a string or file, or compares hash against expected value. |
| `ocr` | `path`/`image` | Extracts text from image file using Tesseract OCR engine. |
| `vision` | `action`, `image`, `prompt` | Analyzes an image or screenshot via vision LLM, or takes a screenshot. |
| `screen_watch` | `action`, `prompt` | Continuously monitors the screen at 2fps, detects changes, returns descriptions. |
| `input_control` | `action`, `x`/`y`/`text`/`key` | Full mouse/keyboard control: move, click, drag, scroll, type, press, hotkeys, screenshot. |
| `edit` | `filePath`, `old`, `new`, `replaceAll` | Edits a file by exact string replacement (like opencode edit). |
| `grep` | `pattern`, `path`, `include` | Searches file contents with regex, returns matching lines with line numbers. |
| `glob` | `pattern`, `path` | Finds files matching a glob pattern, sorted by modification time. |
| `apply_patch` | `patchText`, `reverse` | Applies a git diff/patch to files, with fallback to patch command. |
| `webfetch` | `url`, `format` | Fetches URL content and returns as text, JSON, or stripped HTML. |
| `question` | `question`, `options` | Presents a question to the user for interactive feedback. |
| `skill` | `name`/`path` | Loads and executes a skill/instruction file (SKILL.md). |
| `todowrite` | `action`, `content`, `priority` | Enhanced todo manager with pending/in_progress/completed status tracking. |
| `volume` | `action`, `level` | Gets/sets system volume, mute/unmute via pycaw or keyboard fallback. |
| `media` | `action` | Controls media playback: play/pause, next, prev, stop via virtual key codes. |
| `notification` | `title`, `message`, `duration` | Sends Windows toast notification via win10toast or MessageBox. |
| `disk` | `target` | Reports CPU%, RAM usage, and disk partition usage with free space. |
| `wallpaper` | `path`/`url`, `style` | Sets desktop wallpaper from local file or downloaded URL. |
| `lock` | `action` | Locks workstation, logs off, or puts system to sleep. |
| `browser` | `url`, `new_tab` | Opens a URL in the default web browser. |
| `env` | `action`, `name` | Gets environment variables, lists PATH, or returns home/temp directories. |
| `color` | `format`/`to`, `value`/`color` | Converts between hex, RGB, and HSL color formats. |
| `unit` | `value`, `from`, `to` | Converts between common unit pairs: temperature, length, weight, data size. |
| `math_eval` | `expression`/`expr` | Evaluates math expressions with trig, log, exp, sqrt, and constants. |
| `idle` | `target` | Returns system idle time, uptime, OS, and current user. |
| `email` | `action`, `to`, `subject`, `body` | Sends email via SMTP or checks unread count via IMAP. |
| `calendar` | `action`, `title`, `start` | Adds, lists upcoming, or deletes calendar events in local JSON store. |
| `reminder` | `action`, `text`, `when` | Sets timed reminders with toast notification popup when triggered. |
| `timer` | `action`, `name`, `seconds` | Starts, pauses, resumes, stops, or checks status of named countdown timers. |
| `public_ip` | — | Returns the machine's public IP address via ipify.org. |
| `ping` | `host`, `count` | Pings a host with configurable count and returns latency results. |
| `dns_lookup` | `host` | Resolves a hostname to IP and performs reverse DNS lookup. |
| `host_info` | `target` | Returns IP, geolocation, and ISP info for a hostname or IP. |
| `timestamp` | `action`, `iso`/`timestamp` | Gets current Unix timestamp, converts ISO to timestamp, or timestamp to ISO. |
| `timezone` | `action`, `timezone` | Lists available timezones or converts current time to a specified timezone. |
| `date_calc` | `action`, `date1`, `date2` | Calculates date difference in days, adds days to a date, or returns weekday. |
| `text` | `action`, `text` | Transforms text: upper, lower, title, capitalize, swapcase, reverse, trim, length, wrap. |
| `diff` | `text1`, `text2` | Shows unified diff between two text strings using difflib. |
| `sort` | `action`, `text` | Sorts lines alphabetically, numerically, by length, unique, shuffle, or reverse. |
| `regex` | `action`, `pattern`, `text` | Finds, matches, searches, replaces, or splits text using regex. |
| `uuid` | `count` | Generates one or more UUID4 identifiers. |
| `base64` | `action`, `text` | Encodes or decodes Base64 text. |
| `confirm` | `message`, `default` | Shows a yes/no dialog box and returns the user's choice. |
| `prompt` | `message`, `default` | Shows a text input dialog and returns the user's input. |
| `choose` | `message`, `options` | Shows a dialog with options and returns the user's selection. |
| `beep` | `frequency`/`freq`, `duration` | Plays a beep sound at given frequency/duration via winsound. |
| `sleep` | `seconds`/`duration` | Pauses execution for a given number of seconds (max 300). |
| `alarm` | `action`, `seconds` | Sets a countdown alarm that beeps 5 times when time expires. |
| `stopwatch` | `action` | Starts, stops, records lap, or resets a stopwatch timer. |
| `file_info` | `path` | Returns file size, modified/created dates, permissions, type info. |
| `dir_list` | `path`, `pattern` | Lists directory contents with optional glob filter, up to 200 items. |
| `image_info` | `path` | Returns image format, dimensions, mode, file size, and metadata. |
| `fact` | — | Fetches a random useless fact from an API with built-in fallbacks. |
| `lyric` | `artist`, `title` | Looks up song lyrics by artist and title via lyrics.ovh. |
| `hn` | `category`, `count` | Returns top/new/best Hacker News stories with scores and URLs. |
| `reddit` | `subreddit`, `category`, `count` | Returns hot/new/top posts from a subreddit with scores. |
| `wikipedia` | `query` | Fetches Wikipedia summary for a topic via REST API. |
| `forecast` | `city`, `days` | Gets multi-day weather forecast for any city via Open-Meteo API. |
| `currency` | `amount`, `from`/`to` | Converts between currencies using exchangerate-api.com. |
| `stock` | `symbol` | Looks up current stock price and exchange info via Yahoo Finance. |
| `movie` | `title` | Returns movie details: year, IMDb rating, genre, director, plot via OMDb. |
| `recipe` | `query` | Searches for recipes with ingredients and instructions via TheMealDB. |
| `random_joke` | — | Returns a random two-part joke from official-joke-api with fallback. |
| `show` | `text`/`content`, `title` | Displays text in a scrollable tkinter popup window. |
| `alert` | `title`, `message`, `icon` | Shows a MessageBox or toast notification with info/warn/error icon. |
| `csv_view` | `data` | Formats CSV data as an aligned text table with header separator. |
| `json_format` | `action`, `data` | Formats, validates, minifies, or queries JSON with JSONPath. |
| `brightness` | `action`, `percent`/`value` | Gets or sets screen brightness via WMI on Windows. |
| `encode` | `action`, `text` | Encodes/decodes text: ROT13, binary, hex, octal, or Morse code. |
| `chart` | `data` | Generates an ASCII bar chart from key:value data. |
| `markdown_render` | `text` | Strips Markdown formatting to return clean plain text. |
| `screen_res` | — | Returns screen width and height in pixels. |
| `counter` | `name`, `action` | Simple named counter: get, increment, decrement, add, reset, list all. |
| `progress` | `current`/`value`, `total`/`max` | Shows a text progress bar with percentage and fraction. |
| `color_picker` | `action`, `r`/`g`/`b` | Opens a color picker dialog or converts between RGB and hex. |

## Student & Teacher Tools (73)

| Tool | Params | Description |
|------|--------|-------------|
| `flashcard` | `action`, `question`, `answer`, `deck` | Manages flashcards: add, quiz (with spoiler answers), list, delete deck, stats. |
| `quiz` | `topic`/`subject`, `count` | Generates a topic quiz from built-in question banks (math, science, history, english). |
| `study_set` | `action`, `name`, `items` | Creates and manages named study sets with comma-separated item lists. |
| `grade_calc` | `action`, `current`, `desired`, `weight` | Calculates needed exam score or weighted final grade. |
| `gpa` | `action`, `grades`, `hours`/`credits` | Computes GPA from letter/numeric grades, optional credit hours or target GPA. |
| `assignment` | `action`, `name`, `due`, `course` | Tracks assignments: add with due date, list by course, mark done, delete. |
| `study_timer` | `action`, `minutes`/`duration` | Pomodoro-style timer: starts a countdown and beeps when time is up. |
| `attendance` | `action`, `name`, `id`, `date` | Records student attendance, adds students, generates individual/class reports. |
| `essay_outline` | `topic`, `style`, `paragraphs` | Generates essay outline templates: argumentative, expository, or narrative. |
| `citation` | `style`, `type`, `author`, `title` | Generates citations in MLA, APA, or Chicago style for books/articles/websites. |
| `thesaurus` | `word`, `action` | Returns synonyms and/or antonyms for 20 common English words. |
| `statistics` | `data`/`numbers` | Computes count, sum, mean, median, mode, min, max, range, variance, std dev. |
| `prime` | `action`, `number`/`n`, `limit` | Checks primality, finds prime factors, lists primes up to N, or finds next prime. |
| `matrix` | `action`, `a`/`matrix_a`, `b` | Matrix operations: add, multiply, determinant, transpose. |
| `periodic_table` | `element`/`query` | Looks up element by symbol, name, or atomic number; lists all elements. |
| `physics_ref` | `topic`/`query` | Shows physics formulas for kinematics, Newton's laws, energy, electricity, waves, thermo. |
| `formula` | `topic`/`query` | Shows math formulas for area, volume, geometry, trigonometry, calculus, algebra. |
| `doi_lookup` | `doi`/`id` | Looks up academic paper by DOI via CrossRef API. |
| `arxiv` | `query`/`search`, `count` | Searches arXiv for papers matching a query. |
| `vocab` | `action`, `word` | Vocabulary builder: random word with definition/example, list all, or search. |
| `mnemonic` | `items`/`words`, `pattern` | Creates memory aids: acronym, sentence, or story for a list of items. |
| `note_summarize` | `text`/`notes` | Extractive text summarization — picks most informative sentences. |
| `conjugation` | `verb`/`word`, `tense` | Conjugates irregular and regular English verbs into all tenses. |
| `spell_check` | `text` | Checks text against a dictionary of 80+ commonly misspelled words. |
| `group_picker` | `names`/`students`, `groups` | Randomly splits student names into groups by count or size. |
| `rubric` | `assignment`/`title`, `criteria`/`items` | Generates a grading rubric with criteria, level descriptions, and scoring. |
| `syllabus` | `course`/`title`, `weeks`, `topics` | Creates a course syllabus with weekly schedule, grading breakdown, policies. |
| `practice_problem` | `subject`/`topic`, `count`, `difficulty` | Generates practice problems for math, physics, or chemistry with answers. |
| `science_fact` | `action`, `topic` | Returns random science facts, lists all, or searches by topic. |
| `study_plan` | `subject`/`topic`, `days`, `hours` | Creates a multi-day study plan with daily activities and tips. |
| `note_organizer` | `action`, `subject`, `title`, `content` | Organizes notes by subject with tags, search, and listing. |
| `bibliography` | `style`, `sources`/`items` | Formats bibliography entries from pipe-separated author\|title\|publisher\|year. |
| `equation_solve` | `equation` | Guides through solving linear and quadratic equations step by step. |
| `lesson_plan` | `topic`, `duration`/`minutes`, `grade` | Generates a complete lesson plan with objectives, structure, differentiation, assessment. |
| `worksheet` | `subject`/`topic`, `count`, `difficulty` | Creates printable worksheets for math, vocabulary, or science with answer key. |
| `exam` | `subject`/`topic`, `sections`, `questions` | Generates a formatted exam with multiple sections and question types. |
| `progress_report` | `student`/`name`, `subject`, `grade` | Generates a student progress report with academic comments and improvement areas. |
| `seating_chart` | `names`/`students`, `cols`/`columns` | Creates a randomized seating chart grid from student names. |
| `icebreaker` | `count`, `audience`/`group` | Generates icebreaker questions for classroom or group settings. |
| `discussion` | `topic`, `count`, `level`/`depth` | Creates discussion prompts for any topic with adjustable depth. |
| `learning_objectives` | `topic`, `count`, `level`/`bloom` | Generates SMART learning objectives at specified Bloom's taxonomy level. |
| `activity` | `topic`, `minutes`, `group_size` | Suggests classroom activities (Think-Pair-Share, Jigsaw, Debate, etc.). |
| `feedback` | `student`/`name`, `subject`, `count` | Generates student feedback with strengths and areas for improvement. |
| `reading_list` | `action`, `title`, `author`, `category` | Manages a reading list: add books/articles, list by category, mark status. |
| `study_guide` | `topic`, `subtopics`/`topics` | Creates a study guide with key points, terms, review questions, and tips. |
| `timeline` | `title`/`topic`, `events`/`items`, `years` | Generates a visual timeline from events and optional years. |
| `mind_map` | `topic`, `branches`/`items` | Creates an ASCII mind map with central topic and branching subtopics. |
| `thesis_statement` | `topic`, `style`/`type` | Generates thesis statement templates: argumentative, expository, analytical, compare. |
| `abstract` | `title`, `topic`, `key_points`/`points` | Writes a structured academic abstract with background, methods, findings, implications. |
| `flashcard_import` | `text`, `deck` | Bulk-imports flashcards from delimited text (Q\|A, Q:A, Q;A, or tab-separated). |
| `cheat_sheet` | `topic`, `items` | Generates a quick-reference cheat sheet with formulas, rules, and pro tips. |
| `concept_map` | `topic`, `concepts`/`items` | Creates a concept map showing relationships between concepts. |
| `quiz_me` | `action`, `deck`, `count` | Interactive quiz mode from flashcard decks with spoiler-hidden answers. |
| `plagiarism_check` | `text1`, `text2` | Compares two texts using Jaccard similarity and phrase matching. |
| `peer_review` | `assignment`/`title`, `criteria` | Generates a peer review form with scoring rubric and comment fields. |
| `lab_report` | `title`/`experiment`, `course` | Generates a structured lab report template with all standard sections. |
| `research_proposal` | `topic`, `course`/`subject` | Creates a research proposal outline with questions, hypothesis, methodology, timeline. |
| `book_report` | `title`/`book`, `author` | Generates a book report template with summary, character analysis, theme, reflection. |
| `presentation_outline` | `topic`, `slides`/`count`, `duration` | Creates a slide-by-slide presentation outline with content suggestions. |
| `debate_topic` | `topic`, `count`, `style` | Generates debate arguments for/against a topic with format suggestions. |
| `writing_prompt` | `count`, `genre`/`style` | Generates writing prompts for narrative, persuasive, descriptive, expository, creative. |
| `math_word_problem` | `count`, `difficulty`, `topic` | Creates real-world math word problems (age, money, speed, area) with answers. |
| `project_planner` | `title`/`project`, `weeks`, `tasks` | Generates a project plan with milestones, weekly tasks, and resource tracking. |
| `self_assessment` | `subject`/`topic`, `count` | Creates a self-assessment form with skill ratings and reflection questions. |
| `homework_helper` | `subject`/`topic`, `question`/`problem` | Provides step-by-step study guidance for math, science, writing, or history. |
| `flashcard_review` | `deck`, `count` | Spaced repetition review: prioritizes cards in lower boxes for efficient studying. |
| `test_review` | `subject`/`topic`, `topics` | Creates a test prep checklist with review topics, practice problems, and tips. |
| `classroom_game` | `subject`/`topic`, `minutes`, `count` | Suggests classroom games (Quiz Bowl, Jeopardy, Pictionary, Escape Room). |
| `goal_setter` | `subject`/`topic`, `count`, `period` | Generates SMART academic goals with action steps and check-in dates. |
| `field_trip` | `destination`, `subject`, `hours`, `grade` | Plans a field trip with schedule, learning objectives, activities, and follow-up. |
| `case_study` | `title`/`case`, `subject`/`topic` | Creates a case study analysis framework with sections for each step. |
| `note_template` | `style`/`format`, `topic`/`subject` | Generates note-taking templates: Cornell, outline, or concept mapping styles. |
| `study_break` | `count`, `minutes`/`duration` | Suggests brain break activities (stretch, breathing, walk, doodle) with Pomodoro tips. |

## Cybersecurity Tools (20)

| Tool | Params | Description |
|------|--------|-------------|
| `port_scanner` | `host`/`target`, `ports`, `timeout` | Scans common TCP ports (21-3389, 8080, etc.) on a target host and reports open ones. |
| `subdomain_scan` | `domain`/`target`, `wordlist` | Brute-forces subdomains using a 50-name wordlist and DNS resolution. |
| `whois_lookup` | `domain`/`target` | Performs WHOIS lookup via raw TCP connection to discover domain registration details. |
| `ssl_inspector` | `host`/`target`, `port` | Retrieves and displays SSL certificate details: issuer, subject, validity, SANs, cipher. |
| `http_headers` | `url`/`target` | Checks HTTP security headers (HSTS, CSP, X-Frame-Options, etc.) and scores them. |
| `url_analyzer` | `url`/`target` | Analyzes URL for phishing indicators: suspicious TLDs, typosquatting, IP, length, keywords. |
| `ip_reputation` | `ip`/`target` | Checks if IP is private/public, performs reverse DNS, and looks up ISP/location. |
| `cve_search` | `keyword`/`query`, `cve` | Searches for CVEs by keyword or fetches details for a specific CVE ID. |
| `dns_enum` | `domain`/`target`, `types` | Enumerates DNS records (A, AAAA, MX, NS, TXT, SOA, CNAME) via dnspython. |
| `mac_vendor` | `mac`/`address` | Looks up MAC address OUI to identify the hardware vendor. |
| `file_analyzer` | `action`, `path`/`file` | Analyzes file: detects type via magic bytes, calculates entropy, finds suspicious strings. |
| `cipher` | `action`, `text`, `shift`/`key` | Encrypts/decrypts text with Caesar, ROT13, XOR, Vigenère, or Atbash ciphers. |
| `log_parser` | `text`/`log`, `format`/`type` | Parses Apache/nginx/syslog/auth log formats and extracts structured entries. |
| `network_map` | `subnet`/`target`, `timeout` | Scans a subnet (first 50 IPs) for active hosts and open common ports. |
| `user_enum` | `username`/`user`, `platforms` | Checks if a username exists on GitHub, Twitter, Reddit, Keybase, Instagram, etc. |
| `exploit_search` | `query`/`search`, `cve` | Searches for recent exploits and CVEs related to a software name or CVE ID. |
| `phishing_detector` | `text`/`email`, `url` | Analyzes email/URL for phishing: urgency, spoofed links, poor grammar, threat score. |
| `hash_id` | `hash` | Identifies hash type (MD5, SHA-1/256/512, bcrypt, NTLM, LM) by pattern matching. |
| `password_audit` | `password` | Audits password strength: length, character variety, entropy, common word checks, score. |
| `threat_intel` | `target`, `type` | Generates a threat intelligence report for IP, domain, hash, or text with IOC extraction. |
