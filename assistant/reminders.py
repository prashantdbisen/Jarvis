"""
reminders.py - Reminders, timers and alarms.

Things you can say:
    "remind me in 10 minutes to drink water"
    "remind me to call mom at 6:30 pm"
    "set a timer for 5 minutes"
    "set an alarm for 7 am"   /   "wake me up at 6 tomorrow"
    "what are my reminders"   /   "cancel all reminders"

Note: reminders live in memory, so they are cleared when you close Jarvis.
"""

import datetime
import re
import threading

import config

_lock = threading.Lock()
_items = []  # Each: {"due": datetime, "label": str, "announce": str}

_NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40,
    "forty five": 45, "fifty": 50, "sixty": 60,
}
_UNIT_SECONDS = {"sec": 1, "second": 1, "min": 60, "minute": 60, "hr": 3600, "hour": 3600}

_NUMBER = r"\d+(?:\.\d+)?|" + "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True))
_UNIT = r"seconds?|secs?|minutes?|mins?|hours?|hrs?"
_DURATION = re.compile(rf"\b({_NUMBER})\s*({_UNIT})\b")
_RELATIVE_START = re.compile(rf"\b(?:in|for|after)\s+(?:{_NUMBER})\s*(?:{_UNIT})\b")
_HALF_HOUR = re.compile(r"\b(?:in|for|after)\s+half an hour\b")
_CLOCK = re.compile(r"\b(?:at|for|by|to)\s+(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|o'clock)?\b")
_CLOCK_LOOSE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b|\b(\d{1,2}):(\d{2})\b")


def _to_number(word: str) -> float:
    return float(word) if word[0].isdigit() else float(_NUMBER_WORDS[word])


def _unit_seconds(unit: str) -> int:
    for key, seconds in _UNIT_SECONDS.items():
        if unit.startswith(key):
            return seconds
    return 60


def _describe_duration(seconds: int) -> str:
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs and not hours:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    return " and ".join(parts) or "0 seconds"


def _clock_text(moment: datetime.datetime) -> str:
    text = moment.strftime("%I:%M %p").lstrip("0")
    if moment.date() > datetime.date.today():
        text += " tomorrow"
    return text


def _next_time(hour: int, minute: int, ampm, tomorrow: bool) -> datetime.datetime:
    now = datetime.datetime.now()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if ampm in ("am", "pm") or hour > 12:
        hours_to_try = [hour]
    else:  # "at 7" -> whichever of 7 AM / 7 PM comes next
        hours_to_try = [hour % 12, hour % 12 + 12]
    candidates = []
    for h in hours_to_try:
        moment = now.replace(hour=h, minute=minute, second=0, microsecond=0)
        if moment <= now or tomorrow:
            moment += datetime.timedelta(days=1)
        candidates.append(moment)
    return min(candidates)


def _personalise(message: str) -> str:
    """'call my mom' -> 'call your mom' (sounds natural when Jarvis says it back)."""
    swaps = {"my": "your", "me": "you", "i": "you", "i'm": "you're", "myself": "yourself", "mine": "yours"}
    return " ".join(swaps.get(word, word) for word in message.split())


def parse(command: str):
    """Work out when and what from a sentence. Returns dict or None if no time found."""
    text = " ".join(command.lower().replace("a.m.", "am").replace("p.m.", "pm").split())
    now = datetime.datetime.now()
    due = None
    duration = None
    span = None

    match = _HALF_HOUR.search(text)
    if match:
        duration, span = 1800, match.span()
    elif _RELATIVE_START.search(text):
        start = _RELATIVE_START.search(text).start()
        pairs = list(_DURATION.finditer(text, start))
        duration = sum(_to_number(m.group(1)) * _unit_seconds(m.group(2)) for m in pairs)
        span = (start, pairs[-1].end())
    else:
        match = _CLOCK.search(text) or _CLOCK_LOOSE.search(text)
        if match:
            groups = [g for g in match.groups()]
            if match.re is _CLOCK_LOOSE and groups[0] is None:
                hour, minute, ampm = groups[3], groups[4], None
            else:
                hour, minute, ampm = groups[0], groups[1], groups[2]
            hour, minute = int(hour), int(minute or 0)
            ampm = None if ampm == "o'clock" else ampm
            if hour <= 23 and minute <= 59:
                due = _next_time(hour, minute, ampm, tomorrow="tomorrow" in text)
                span = match.span()

    if duration:
        due = now + datetime.timedelta(seconds=duration)
    if due is None or due <= now:
        return None

    # Whatever is left (after removing the time) holds the message
    rest = (text[:span[0]] + " " + text[span[1]:]).replace("tomorrow", " ")
    found = re.search(r"\b(to|about|that)\s+(.+)$", rest)
    message = found.group(2).strip() if found else ""
    if found and found.group(1) == "about":
        message = "about " + message  # "remind me about the meeting" -> "about the meeting"
    message = re.sub(r"\b(please|jarvis)\b", "", message).strip(" .,")

    if "timer" in text:
        kind = "timer"
    elif "alarm" in text or "wake me" in text:
        kind = "alarm"
    else:
        kind = "reminder"
    return {"due": due, "duration": duration, "kind": kind, "message": _personalise(message)}


def add_from_command(command: str):
    """Create a reminder/timer/alarm from what you said.
    Returns Jarvis's confirmation sentence, or None if no time was understood."""
    info = parse(command)
    if not info:
        return None
    due, kind, message, duration = info["due"], info["kind"], info["message"], info["duration"]
    user = config.USER_NAME
    when = f"in {_describe_duration(duration)}" if duration else f"at {_clock_text(due)}"

    if kind == "timer":
        length = _describe_duration(duration) if duration else f"until {_clock_text(due)}"
        label = f"a timer ending at {_clock_text(due)}"
        announce = f"{user}, your {length} timer is done."
        confirm = f"Timer set for {length}."
    elif kind == "alarm":
        label = f"an alarm at {_clock_text(due)}"
        announce = f"Wake up {user}! It's {due.strftime('%I:%M %p').lstrip('0')}."
        confirm = f"Alarm set for {_clock_text(due)}." if not duration else f"Alarm set {when}."
    else:
        label = f"{message or 'a reminder'} at {_clock_text(due)}"
        joiner = "" if message.startswith("about ") else "to "
        announce = f"{user}, this is your reminder {joiner}{message}." if message else f"{user}, here's your reminder."
        confirm = f"Okay, I'll remind you {joiner}{message} {when}." if message else f"Okay, I'll remind you {when}."

    with _lock:
        _items.append({"due": due, "label": label, "announce": announce})
    return confirm


def pop_due() -> list:
    """Return announcements for everything that is due now (and remove them)."""
    now = datetime.datetime.now()
    with _lock:
        due = sorted((item for item in _items if item["due"] <= now), key=lambda i: i["due"])
        for item in due:
            _items.remove(item)
    return [item["announce"] for item in due]


def describe() -> str:
    with _lock:
        items = sorted(_items, key=lambda i: i["due"])
    if not items:
        return "You have no reminders right now."
    labels = [item["label"] for item in items]
    if len(labels) == 1:
        return f"You have one reminder: {labels[0]}."
    return f"You have {len(labels)} reminders: " + ", ".join(labels[:-1]) + f", and {labels[-1]}."


def clear() -> int:
    with _lock:
        count = len(_items)
        _items.clear()
    return count
