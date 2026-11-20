"""
commands.py - Decides WHAT to do with each thing you say.

HOW TO ADD A NEW COMMAND (3 steps):
    1. Write a function:   def handle_xyz(command): ...
    2. Add it to COMMANDS:  (["trigger words"], handle_xyz),
    3. Done! Commands higher in the list are checked first.

Trigger words match whole words anywhere in the sentence.
A trigger starting with "=" must be the WHOLE sentence (e.g. "=stop").

A handler can return:
    "exit"  -> Jarvis shuts down
    "sleep" -> Jarvis goes quiet until it hears the wake word again
    None    -> carry on as normal
"""

import datetime
import random
import re

import config
from assistant import actions, brain, browser, reminders, skills
from assistant.speech import speak, was_interrupted

_ask_user = None  # Function that gets your reply (voice or keyboard), set by main.py


def set_input(function) -> None:
    global _ask_user
    _ask_user = function


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _remove_words(command: str, words) -> str:
    """Remove trigger words from a command to get the useful part.
    e.g. 'play believer on youtube' -> 'believer'"""
    text = f" {command} "
    for word in sorted(words, key=len, reverse=True):
        text = text.replace(f" {word} ", " ")
    return " ".join(text.split())


# Polite / filler words people add when talking naturally
_FILLERS = ["jarvis", "please", "can you", "could you", "would you", "will you", "for me",
            "i want to", "i want", "i'd like to", "let's", "just", "now", "quickly"]


def _first_number(command: str):
    match = re.search(r"\d+", command)
    return int(match.group()) if match else None


def _confirm(question: str) -> bool:
    """Ask a yes/no question and return True for yes."""
    speak(question)
    if was_interrupted():
        return False
    reply = f" {_ask_user() if _ask_user else ''} "
    return any(f" {word} " in reply for word in
               ["yes", "yeah", "yep", "yup", "sure", "confirm", "do it", "go ahead", "haan", "ha"])


def strip_wake_word(text: str):
    """Find the wake word and return (found, rest_of_command).
    'hey jarvis open youtube' -> (True, 'open youtube')
    'open youtube jarvis'     -> (True, 'open youtube')"""
    words = text.lower().split()
    for i, word in enumerate(words):
        if word.strip(",.!?") in config.WAKE_WORDS:
            after = words[i + 1:]
            before = [w for w in words[:i] if w not in ("hey", "hi", "ok", "okay", "hello", "yo")]
            return True, " ".join(after or before).strip(" ,.!?")
    return False, text


# ---------------------------------------------------------------------------
# Handlers - each receives the full command text you spoke
# ---------------------------------------------------------------------------
def handle_exit(command):
    speak(f"Goodbye {config.USER_NAME}. Shutting down all systems.")
    return "exit"


def handle_sleep(command):
    speak(f"Going quiet. Just say {config.ASSISTANT_NAME} when you need me.")
    return "sleep"


def handle_never_mind(command):
    speak("Okay.")
    return "sleep"


def handle_silence(command):
    return None  # You said "stop" while Jarvis was already quiet - do nothing


def handle_forget(command):
    brain.reset_memory()
    speak("Done. I've cleared our conversation from memory.")


def handle_greeting(command):
    speak(random.choice([
        f"Hello {config.USER_NAME}, how can I help?",
        f"Hi {config.USER_NAME}! What can I do for you?",
        "At your service.",
    ]))


def handle_small_talk(command):
    if "how are you" in command:
        speak(f"All systems running at full capacity, {config.USER_NAME}. How can I help?")
    elif "who made you" in command or "who created you" in command or "who built you" in command:
        speak(f"I was built in Python by you, {config.USER_NAME}.")
    elif "thank" in command:
        speak(random.choice(["You're welcome.", f"Anytime, {config.USER_NAME}.", "Happy to help."]))
    else:
        speak(f"I am {config.ASSISTANT_NAME}, your personal assistant.")


def handle_help(command):
    speak(
        "I can open and close websites and apps, play, pause and skip songs on YouTube, search Google, "
        "tell you the weather and news, set reminders, timers and alarms, control the volume, "
        "take screenshots, lock or shut down the computer, tell jokes, and answer your questions. "
        "Say stop to interrupt me, or go to sleep when you're done."
    )


def handle_play_youtube(command):
    song = _remove_words(command, _FILLERS + ["play", "on youtube", "youtube", "song", "video",
                                              "listen to", "put on", "the"])
    if not song:
        speak("What should I play?")
        return
    speak(f"Playing {song} on YouTube.")
    actions.play_on_youtube(song)


def handle_search(command):
    if "youtube" in command:
        query = _remove_words(command, ["jarvis", "please", "search", "for", "on youtube", "youtube"])
        if query:
            speak(f"Searching YouTube for {query}.")
            actions.youtube_search(query)
            return
    query = _remove_words(command, ["jarvis", "please", "search", "for", "google", "on google"])
    if not query:
        speak("What should I search for?")
        return
    speak(f"Searching Google for {query}.")
    actions.google_search(query)


def handle_open(command):
    target = _remove_words(command, _FILLERS + ["open", "launch", "start", "the", "app", "website"])
    if not target:
        speak("What should I open?")
        return

    if target in ("chrome", "google chrome", "browser"):
        speak("Opening Google Chrome.")
        if not actions.open_browser_home():
            speak("Chrome isn't installed, so I opened your default browser.")
    elif target in config.WEBSITES:
        speak(f"Opening {target}.")
        actions.open_url(config.WEBSITES[target])
    elif target in config.APPS:
        speak(f"Opening {target}.")
        if not actions.open_app(target):
            speak(f"Sorry, I couldn't open {target} on this computer.")
    else:
        # Unknown name: guess it's a website, e.g. "open amazon" -> amazon.com
        site = target.replace(" ", "")
        speak(f"Opening {target}.")
        actions.open_url(f"https://www.{site}.com")


def handle_close(command):
    target = _remove_words(command, _FILLERS + ["close", "the", "app", "website", "window", "this", "current"])
    if target in ("", "tab"):
        ok = browser.close_current_tab()
        speak("Tab closed." if ok else "There's no tab of mine open to close.")
    elif target in ("browser", "chrome", "google chrome", "all tabs", "everything"):
        if browser.is_open():
            browser.quit()
            speak("Browser closed.")
        else:
            speak("My browser isn't open.")
    elif target in config.APP_PROCESSES:
        speak(f"Closing {target}." if actions.close_app(target) else f"{target} doesn't seem to be open.")
    else:
        url = config.WEBSITES.get(target, f"https://www.{target.replace(' ', '')}.com")
        site = browser._domain(url) if target in config.WEBSITES else target.replace(" ", "") + "."
        closed = browser.close_site(site)
        if closed:
            speak(f"Closed {target}.")
        elif not config.USE_JARVIS_BROWSER:
            speak("I can only close tabs when USE_JARVIS_BROWSER is turned on in my settings.")
        else:
            speak(f"I don't have {target} open.")


def _media(action: str, done: str):
    if not browser.media(action):
        speak("There's no YouTube video open in my browser.")
    elif done:
        speak(done)


def handle_pause(command):
    _media("pause", "Paused.")


def handle_resume(command):
    _media("resume", "")


def handle_next(command):
    _media("next", "Next one.")


def handle_time(command):
    speak(f"It's {datetime.datetime.now().strftime('%I:%M %p').lstrip('0')}.")


def handle_date(command):
    speak(f"Today is {datetime.datetime.now().strftime('%A, %d %B %Y')}.")


def handle_joke(command):
    try:
        import pyjokes
        speak(pyjokes.get_joke())
    except Exception:
        speak("Why do programmers prefer dark mode? Because light attracts bugs.")


# --- Weather & news --------------------------------------------------------
def handle_weather(command):
    city = ""
    match = re.search(r"\b(?:in|at|for)\s+(.+)$", command)
    if match:
        city = _remove_words(match.group(1), ["today", "tomorrow", "now", "right now", "currently",
                                              "please", "jarvis", "this week", "outside"])
    city = city or config.HOME_CITY
    report = skills.get_weather(city)
    speak(report or f"Sorry, I couldn't get the weather for {city} right now.")


def handle_news(command):
    topic = _remove_words(command, [
        "jarvis", "please", "tell", "me", "the", "latest", "news", "headlines", "today's", "today",
        "top", "read", "what's", "what", "is", "are", "about", "on", "give", "any", "some", "for",
    ])
    headlines = skills.get_news(topic)
    if not headlines:
        speak("Sorry, I couldn't fetch the news right now.")
        return
    intro = f"Here's the latest on {topic}." if topic else "Here are today's top headlines."
    ordinals = ["First", "Next", "Also", "Then", "And finally"]
    lines = []
    for i, headline in enumerate(headlines):
        word = "And finally" if i == len(headlines) - 1 and i > 0 else ordinals[min(i, 3)]
        lines.append(f"{word}, {headline}.")
    speak(intro + " " + " ".join(lines))  # Say "stop" any time to cut it short


# --- Reminders -------------------------------------------------------------
def handle_set_reminder(command):
    confirmation = reminders.add_from_command(command)
    if confirmation:
        speak(confirmation)
    else:
        speak("When should I remind you? For example, say: remind me in 10 minutes to drink water.")


def handle_list_reminders(command):
    speak(reminders.describe())


def handle_cancel_reminders(command):
    count = reminders.clear()
    speak(f"Cancelled {count} reminder{'s' if count != 1 else ''}." if count else "You have no reminders to cancel.")


# --- Volume & screenshot ---------------------------------------------------
def handle_volume(command):
    words = f" {command} "
    number = _first_number(command)
    up = any(f" {w} " in words for w in ["up", "increase", "louder", "raise", "higher"])
    down = any(f" {w} " in words for w in ["down", "decrease", "lower", "reduce", "softer"])

    if " unmute " in words:
        ok, reply = skills.mute(False), "Sound is back on."
    elif " mute " in words:
        ok, reply = skills.mute(True), "Muted."
    elif " max " in words or " maximum " in words or " full " in words:
        ok, reply = skills.set_volume(100), "Volume at maximum."
    elif up:
        ok, reply = skills.change_volume(number or config.VOLUME_STEP), "Volume up."
    elif down:
        ok, reply = skills.change_volume(-(number or config.VOLUME_STEP)), "Volume down."
    elif number is not None:
        ok, reply = skills.set_volume(number), f"Volume set to {min(number, 100)} percent."
    else:
        speak("Say volume up, volume down, mute, or set volume to a number.")
        return
    speak(reply if ok else "Sorry, I couldn't change the volume.")


def handle_screenshot(command):
    path = skills.take_screenshot()
    if path:
        speak("Screenshot saved in your Pictures folder, under Jarvis Screenshots.")
    else:
        speak("Sorry, I couldn't take a screenshot.")


# --- Power -----------------------------------------------------------------
def handle_lock(command):
    speak("Locking the computer.")
    if not skills.lock_computer():
        speak("Sorry, I couldn't lock the computer.")


def _power(restart: bool):
    action = "restart" if restart else "shut down"
    if not _confirm(f"Are you sure you want me to {action} the computer?"):
        speak("Okay, cancelled.")
        return
    if skills.power_off(restart):
        speak(f"Okay. The computer will {action} in {config.SHUTDOWN_DELAY_SECONDS} seconds. "
              f"Say cancel shutdown to stop it.")
    else:
        speak(f"Sorry, I couldn't {action} the computer.")


def handle_shutdown(command):
    _power(restart=False)


def handle_restart(command):
    _power(restart=True)


def handle_cancel_shutdown(command):
    if skills.cancel_power_off():
        speak("Shutdown cancelled.")
    else:
        speak("There was nothing to cancel, or I couldn't cancel it.")


def handle_question(command):
    """Offline fallback: anything else is treated as a question for Wikipedia."""
    speak("Let me think...")
    reply = brain.answer(command)
    if reply:
        speak(reply)
    else:
        speak("Sorry, I couldn't find an answer. Say search, followed by your question, "
              "and I'll look it up on Google.")


# ---------------------------------------------------------------------------
# Command table: (trigger words, handler). ORDER MATTERS - first match wins.
# ---------------------------------------------------------------------------
COMMANDS = [
    (["=exit", "=quit", "goodbye", "good bye", "bye", "shut yourself down", "turn yourself off"], handle_exit),
    (["cancel shutdown", "cancel the shutdown", "abort shutdown", "cancel restart", "cancel the restart"],
     handle_cancel_shutdown),
    (["cancel reminder", "cancel reminders", "cancel all reminders", "cancel my reminders",
      "clear reminders", "clear all reminders", "delete reminders", "delete all reminders",
      "cancel timer", "cancel the timer", "stop the timer", "cancel alarm", "cancel the alarm",
      "stop the alarm"], handle_cancel_reminders),
    (["my reminders", "list reminders", "show reminders", "any reminders", "what reminders"],
     handle_list_reminders),
    (["remind me", "reminder", "timer", "alarm", "wake me up"], handle_set_reminder),
    (["=never mind", "=nevermind", "=cancel", "=nothing", "=forget it", "=no"], handle_never_mind),
    (["=stop", "=quiet", "=enough", "=silence", "=shut up", "=be quiet"], handle_silence),
    (["go to sleep", "=sleep", "sleep now", "sleep mode", "take a rest", "that's all", "that is all"],
     handle_sleep),
    (["forget everything", "clear memory", "clear your memory", "forget our conversation",
      "new conversation", "start over"], handle_forget),
    (["what can you do", "=help"], handle_help),
    (["shut down the computer", "shut down my computer", "shutdown the computer", "shutdown my computer",
      "=shut down", "=shutdown", "power off", "turn off the computer", "turn off my computer"], handle_shutdown),
    (["restart the computer", "restart my computer", "=restart", "reboot"], handle_restart),
    (["lock the computer", "lock my computer", "lock the screen", "lock screen", "lock my pc", "=lock"],
     handle_lock),
    (["pause", "stop the music", "stop the song", "stop the video", "stop music"], handle_pause),
    (["resume", "unpause", "=play", "continue the video", "continue the song", "resume video"], handle_resume),
    (["next song", "next video", "skip", "=next", "play next", "play the next"], handle_next),
    (["close"], handle_close),
    (["play"], handle_play_youtube),
    (["weather", "temperature", "forecast", "raining", "umbrella"], handle_weather),
    (["news", "headlines"], handle_news),
    (["volume", "mute", "unmute", "louder", "softer"], handle_volume),
    (["screenshot", "screen shot", "capture the screen", "capture screen"], handle_screenshot),
    (["search"], handle_search),
    (["open", "launch"], handle_open),
    (["time"], handle_time),
    (["date", "what day", "day is it"], handle_date),
    (["joke", "make me laugh"], handle_joke),
    (["how are you", "your name", "who are you", "who made you", "who created you", "who built you",
      "thank you", "thanks"], handle_small_talk),
    (["hello", "hi", "hey", "good morning", "good afternoon", "good evening"], handle_greeting),
]


def _matches(command: str, trigger: str) -> bool:
    if trigger.startswith("="):
        return command.strip(" .!?") == trigger[1:]
    return f" {trigger} " in f" {command} "  # Whole words only, so 'hi' won't match 'which'


def _find(command: str):
    """Return (handler, trigger) for the first matching row in COMMANDS, or (None, None)."""
    for triggers, handler in COMMANDS:
        for trigger in triggers:
            if _matches(command, trigger):
                return handler, trigger
    return None, None


def _is_direct(command: str, trigger: str) -> bool:
    """True for clear, short commands like 'open youtube' or 'volume up' that start
    with their trigger word. These run instantly without asking the AI."""
    return trigger.startswith("=") or command.startswith(trigger)


def process_command(command: str, use_ai: bool = True, original: str = ""):
    """Run the right handler. Returns "exit", "sleep" or None.

    1. Clear commands ("open youtube") run instantly.
    2. Anything else goes to the AI (if you have an API key), which turns natural
       speech ("I'm bored, put on some music") into a clear command, or answers it.
    3. Without AI, trigger words are matched anywhere, and questions go to Wikipedia.
    """
    command = command.lower().strip(" .!?")
    if not command:
        return None

    handler, trigger = _find(command)
    if use_ai and brain.ai_available() and not (handler and _is_direct(command, trigger)):
        print("(thinking...)")
        result = brain.understand(command)
        if result:
            kind, text = result
            if kind == "answer":
                speak(text)
                return None
            print(f"(understood as: {text})")
            return process_command(text, use_ai=False, original=command)

    if handler:
        return handler(command)
    handle_question(original or command)
    return None
