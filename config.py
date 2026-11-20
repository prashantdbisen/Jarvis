"""
config.py - All Jarvis settings live here.

Change anything in this file to customise Jarvis without touching the logic.
"""

import os

from dotenv import load_dotenv

# Load secrets (like API keys) from a local .env file, if it exists.
load_dotenv()

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
ASSISTANT_NAME = "Jarvis"
USER_NAME = "Sir"            # How Jarvis addresses you

# ---------------------------------------------------------------------------
# Voice (text-to-speech)
# ---------------------------------------------------------------------------
# "edge"    = realistic, movie-like neural voice (free, needs internet)
# "pyttsx3" = offline robotic voice (also used automatically if internet fails)
TTS_ENGINE = "edge"

# Realistic voice options (try them!):
#   "en-GB-RyanNeural"     British male  (closest to movie Jarvis)
#   "en-GB-ThomasNeural"   British male, calmer
#   "en-US-GuyNeural"      American male
#   "en-IN-PrabhatNeural"  Indian English male
#   "en-GB-SoniaNeural"    British female
#   "hi-IN-MadhurNeural"   Hindi male
EDGE_VOICE = "en-GB-RyanNeural"
EDGE_RATE = "+5%"            # Speed, e.g. "-10%" slower, "+15%" faster
EDGE_PITCH = "-3Hz"          # Lower = deeper voice, e.g. "-8Hz"

# Offline voice settings (pyttsx3)
VOICE_RATE = 175             # Speaking speed (words per minute)
VOICE_VOLUME = 1.0           # 0.0 to 1.0
VOICE_INDEX = 0              # 0 is usually male, 1 usually female (depends on your OS)

# ---------------------------------------------------------------------------
# Listening (speech-to-text)
# ---------------------------------------------------------------------------
LANGUAGE = "en-IN"           # e.g. "en-US", "en-GB", "hi-IN"
LISTEN_TIMEOUT = 5           # Seconds to wait for you to START speaking
PHRASE_TIME_LIMIT = 10       # Max seconds for one sentence
AMBIENT_NOISE_DURATION = 1   # Seconds used once to calibrate background noise
LISTEN_BEEP = True           # Play a beep when Jarvis starts listening to you

# ---------------------------------------------------------------------------
# Wake word
# ---------------------------------------------------------------------------
USE_WAKE_WORD = True         # True = Jarvis only responds after hearing its name
# Speech recognition sometimes mishears "Jarvis", so similar words count too.
WAKE_WORDS = ["jarvis", "jarvi", "javis", "jervis", "jarves", "jarvish", "jarwis"]
FOLLOW_UP_SECONDS = 12       # After answering, keep listening this long without the wake word

# ---------------------------------------------------------------------------
# Interrupting Jarvis while it speaks
# ---------------------------------------------------------------------------
VOICE_INTERRUPT = True       # True = say a stop word to make Jarvis stop talking
STOP_WORDS = ["stop", "quiet", "enough", "silence", "cancel", "shut up"]

# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------
# Jarvis's own Chrome window: lets Jarvis reuse tabs, close tabs and control videos.
# False = use your normal browser (Jarvis then can't close tabs or pause videos).
USE_JARVIS_BROWSER = True
BROWSER_PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".jarvis_browser_profile")

USE_CHROME = True            # Fallback: open links in Chrome (if installed), else default browser

# Say "open <name>" to open any of these. Add your own!
WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "linkedin": "https://www.linkedin.com",
    "instagram": "https://www.instagram.com",
    "whatsapp": "https://web.whatsapp.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
}

# Say "open <name>" to launch any of these desktop apps.
# Commands differ per operating system: Windows / Darwin (macOS) / Linux.
APPS = {
    "notepad": {"Windows": "notepad", "Darwin": "open -a TextEdit", "Linux": "gedit"},
    "calculator": {"Windows": "calc", "Darwin": "open -a Calculator", "Linux": "gnome-calculator"},
    "file explorer": {"Windows": "explorer", "Darwin": "open .", "Linux": "xdg-open ."},
    "command prompt": {"Windows": "start cmd", "Darwin": "open -a Terminal", "Linux": "gnome-terminal"},
    "vs code": {"Windows": "code", "Darwin": "open -a 'Visual Studio Code'", "Linux": "code"},
}

# Say "close <name>" to close these apps (process names per operating system).
APP_PROCESSES = {
    "notepad": {"Windows": ["notepad.exe"], "Darwin": ["TextEdit"], "Linux": ["gedit"]},
    "calculator": {"Windows": ["CalculatorApp.exe", "Calculator.exe"], "Darwin": ["Calculator"],
                   "Linux": ["gnome-calculator"]},
    "vs code": {"Windows": ["Code.exe"], "Darwin": ["Visual Studio Code"], "Linux": ["code"]},
}

# ---------------------------------------------------------------------------
# Answering questions, understanding & memory
# ---------------------------------------------------------------------------
# Optional: put ANTHROPIC_API_KEY in your .env file. Then Jarvis understands
# natural, human-like sentences ("I'm bored, put on some music") and answers smartly.
# Without a key, Jarvis uses trigger words for commands and Wikipedia for questions (free).
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
AI_MODEL = "claude-haiku-5-5"      # Change to any Claude model you like
AI_MAX_TOKENS = 300
WIKIPEDIA_SENTENCES = 2
MEMORY_TURNS = 6             # How many recent question/answer pairs Jarvis remembers

# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
HOME_CITY = "Delhi"          # Used when you just say "what's the weather"
TEMPERATURE_UNIT = "celsius" # "celsius" or "fahrenheit"

NEWS_REGION = "hl=en-IN&gl=IN&ceid=IN:en"   # US: "hl=en-US&gl=US&ceid=US:en"
NEWS_COUNT = 5               # Headlines read out each time

VOLUME_STEP = 10             # Percent change for "volume up" / "volume down"

SCREENSHOT_FOLDER = os.path.join(os.path.expanduser("~"), "Pictures", "Jarvis Screenshots")

SHUTDOWN_DELAY_SECONDS = 30  # Time you get to say "cancel shutdown"
