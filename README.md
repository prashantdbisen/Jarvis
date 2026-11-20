# 🤖 Jarvis – Python Voice Assistant

A realistic, easy-to-extend voice assistant written in Python.
Wake it with "Jarvis", then open Chrome, YouTube, websites and apps, play songs,
check the weather and news, set reminders, control the volume, and ask anything.

## ✨ Features

| Say this…                                   | Jarvis does…                                  |
|---------------------------------------------|-----------------------------------------------|
| "Jarvis"                                    | Wakes up and beeps, ready for a command       |
| "Hey Jarvis, open YouTube"                  | Wake word + command in one sentence           |
| "open chrome" / "open github"               | Opens Chrome / the website                    |
| "play believer on youtube"                  | Plays in the same YouTube tab (no new tabs)   |
| "pause" / "resume" / "next song"            | Controls the YouTube video                    |
| "close youtube" / "close tab" / "close browser" | Closes tabs or Jarvis's browser           |
| "close notepad" / "close calculator"        | Closes desktop apps                           |
| "I'm bored, put on some music" *            | Understands natural speech (needs API key)    |
| "search python tutorials"                   | Google search                                 |
| "what's the weather" / "weather in Mumbai"  | Live weather report                           |
| "tell me the news" / "news about cricket"   | Reads top headlines                           |
| "remind me in 10 minutes to drink water"    | Sets a reminder                               |
| "set a timer for 5 minutes"                 | Sets a timer                                  |
| "set an alarm for 7 am"                     | Sets an alarm                                 |
| "what are my reminders" / "cancel all reminders" | Lists / clears them                      |
| "volume up" / "set volume to 40" / "mute"   | Controls system volume                        |
| "take a screenshot"                         | Saves to Pictures → Jarvis Screenshots        |
| "lock the computer"                         | Locks your PC                                 |
| "shut down the computer" / "restart"        | Asks to confirm, then shuts down in 30 s      |
| "cancel shutdown"                           | Stops a pending shutdown                      |
| "who is APJ Abdul Kalam" → "tell me more"   | Answers, and remembers follow-ups             |
| "forget everything"                         | Clears conversation memory                    |
| "stop" (while Jarvis is talking)            | Stops talking, listens for next command       |
| "go to sleep"                               | Waits quietly for "Jarvis" again              |
| "exit" / "bye"                              | Closes Jarvis                                 |

\* With an `ANTHROPIC_API_KEY`, Jarvis understands natural, human-like sentences.
Without it, it works with clear trigger words like "open", "play", "close".

## 📁 Project Structure

```
Jarvis/
├── main.py              # Start here - wake word & main loop
├── config.py            # ALL settings (voice, wake word, city, websites, apps...)
├── assistant/
│   ├── speech.py        # speak(), listen(), beep() + "stop" interrupt
│   ├── commands.py      # Maps what you say -> what Jarvis does
│   ├── actions.py       # Opens/closes websites and apps, YouTube
│   ├── browser.py       # Jarvis's own Chrome window (reuse/close tabs, pause/skip)
│   ├── skills.py        # Weather, news, volume, screenshot, lock/shutdown
│   ├── reminders.py     # Reminders, timers, alarms
│   └── brain.py         # AI understanding, answers, memory, Wikipedia
├── requirements.txt
├── .env.example         # Template for your optional API key
└── .gitignore           # Keeps secrets & junk out of Git
```

### How it flows

```
            ┌──────────── waiting quietly ◄──────────────────────┐
            ▼                                                    │
 hears "Jarvis" ──> beep ──> listen() ──> process_command() ──> speak()
                                  ▲          │ no match?           │
                                  │          └─> brain.answer() ───┤
                                  └──── follow-up window (12 s) ◄──┘
```

## 🚀 Setup (Windows, step by step)

### 1. Install Python (skip if `py list` already shows 3.12)
Python **3.10 – 3.12** recommended (3.13 also works). Download from https://python.org.
On Windows, tick **"Add Python to PATH"** during install.

```bash
py install 3.12
```

### 2. Put the project in `C:\Users\<you>\Projects\Jarvis` and open PowerShell there:
```bash
# git clone https://github.com/<your-username>/Jarvis.git
# cd Jarvis

cd C:\Users\<you>\Projects\Jarvis
```
### 3. Create a virtual environment
```bash
# Windows
py -3.12 -m venv venv   # OR python -m venv venv
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # Allow activation (one time) and activate
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install system audio libraries (macOS / Linux only)
```bash
# macOS
brew install portaudio

# Ubuntu / Debian
sudo apt install portaudio19-dev python3-dev espeak-ng
```
then use `python3` and
`source venv/bin/activate`.

Windows needs nothing extra.

### 5. Install Python packages
```bash
pip install -r requirements.txt

```

### 6. (Optional) Smarter answers with Claude AI
Without this step, Jarvis answers questions from Wikipedia (free).
For smarter answers:
1. Copy `.env.example` to `.env`
2. Paste your key from https://console.anthropic.com:
   `ANTHROPIC_API_KEY=your-key-here`

### 7. Run Jarvis 🎉
```bash
python main.py          # voice mode
python main.py --text   # text mode (type commands, no mic needed)
```


### Every time you come back later, you only need:
```bash
cd C:\Users\admin\Projects\Jarvis     // Your Project Directory
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # Allow activation (one time) and activate
venv\Scripts\activate
python main.py          # voice mode
python main.py --text   # text mode (type commands, no mic needed)
```

## 🎙️ Using Jarvis

- After the greeting, Jarvis listens for a few seconds. Then it shows **[Standing by]**
  and waits for its name.
- Say **"Jarvis"** → it beeps → say your command. Or say it all at once:
  **"Jarvis, what's the weather?"**
- After answering, it keeps listening for **12 seconds** for follow-ups, no wake word needed.
- **Interrupt:** say **"stop"** while it's talking, or press **Ctrl+C**.
- **Quit:** say **"exit"**, or press **Ctrl+C** while it's listening.
- 🎧 Headphones make "stop" and the wake word more reliable.

## 🛠️ Customising (all in `config.py`)

| Setting | What it does |
|---|---|
| `EDGE_VOICE`, `EDGE_RATE`, `EDGE_PITCH` | Realistic voice, speed, depth (voice list in the file) |
| `TTS_ENGINE = "pyttsx3"` | Use the offline voice instead |
| `USE_WAKE_WORD`, `WAKE_WORDS`, `FOLLOW_UP_SECONDS` | Wake word behaviour |
| `LISTEN_BEEP` | Turn the listening beep on/off |
| `HOME_CITY`, `TEMPERATURE_UNIT` | Default weather location |
| `NEWS_REGION`, `NEWS_COUNT` | News country & number of headlines |
| `STOP_WORDS`, `VOICE_INTERRUPT` | Interrupt words |
| `WEBSITES`, `APPS` | Add your own sites and apps |
| `MEMORY_TURNS` | How much conversation Jarvis remembers |
| `USE_JARVIS_BROWSER` | `False` = use your normal browser (no tab closing / video control) |
| `APP_PROCESSES` | Apps Jarvis can close |

**Add a brand-new command** in `assistant/commands.py`:
```python
def handle_coffee(command):
    speak("Brewing virtual coffee, sir.")

COMMANDS = [
    ...
    (["coffee"], handle_coffee),
]
```

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| `[Realistic voice unavailable ...]` | No internet; Jarvis uses the offline voice automatically and retries after a minute |
| `pip install PyAudio` fails | Use Python 3.12 (`py -3.12 -m venv venv`) |
| Jarvis doesn't react to its name | Check the console: if it hears e.g. "jervis", add that to `WAKE_WORDS` |
| Jarvis hears TV / other people | Lower `FOLLOW_UP_SECONDS`, or use headphones |
| Volume commands do nothing (Linux) | Install `pulseaudio-utils` (`pactl`) |
| Reminders disappear after closing | Expected: they're kept while Jarvis is running |
| In text mode, reminders announce late | They're announced when you next press Enter |
| "Can't reach the speech service" | Speech recognition needs internet |
| Jarvis's browser takes a few seconds the first time | Normal: Selenium downloads the matching ChromeDriver once |
| Google sign-in blocked in Jarvis's browser | Google sometimes blocks logins in automated windows; YouTube works fine without login |
| Jarvis's browser closed when Jarvis closed | Expected: Jarvis owns that window |
| `[Wikipedia error ...]` | Check internet; Jarvis uses Wikipedia's official API directly |

## 📤 Upload to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Jarvis voice assistant"
git branch -M main
git remote add origin https://github.com/<your-username>/Jarvis.git
git push -u origin main
```
`.env` (your API key) and `venv/` are in `.gitignore`, so they won't be uploaded.

## 📜 License
MIT – free to use and modify.
