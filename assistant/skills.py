"""
skills.py - Extra abilities: weather, news, volume, screenshots and power controls.

Weather uses Open-Meteo and news uses Google News RSS: both free, no API key.
"""

import datetime
import json
import os
import platform
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import config

OS_NAME = platform.system()  # "Windows", "Darwin" (macOS) or "Linux"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Jarvis voice assistant)"}


def _get(url: str, timeout: int = 8) -> bytes:
    request = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _get_json(url: str):
    return json.loads(_get(url).decode("utf-8"))


def _run(command: list) -> bool:
    try:
        subprocess.run(command, check=True, capture_output=True)
        return True
    except Exception as error:
        print(f"[Command failed: {' '.join(command)} -> {error}]")
        return False


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------
_WEATHER_CODES = {
    0: "clear skies", 1: "mostly clear skies", 2: "partly cloudy skies", 3: "overcast skies",
    45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "freezing drizzle", 61: "light rain", 63: "rain",
    65: "heavy rain", 66: "freezing rain", 67: "freezing rain", 71: "light snow",
    73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers", 81: "showers",
    82: "heavy showers", 85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with heavy hail",
}


def get_weather(city: str):
    """Return a spoken weather report for the city, or None."""
    try:
        geo = _get_json(
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urllib.parse.urlencode({"name": city, "count": 1, "language": "en", "format": "json"})
        )
        places = geo.get("results") or []
        if not places:
            return None
        place = places[0]
        params = {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,apparent_temperature,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 1,
            "temperature_unit": config.TEMPERATURE_UNIT,
        }
        data = _get_json("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params))
        now, today = data["current"], data["daily"]
        condition = _WEATHER_CODES.get(now.get("weather_code"), "mixed conditions")
        report = (
            f"In {place['name']}, it's {round(now['temperature_2m'])} degrees with {condition}, "
            f"feeling like {round(now['apparent_temperature'])}. "
            f"Today's high is {round(today['temperature_2m_max'][0])} "
            f"and the low is {round(today['temperature_2m_min'][0])}"
        )
        rain = (today.get("precipitation_probability_max") or [None])[0]
        if rain is not None:
            report += f", with a {rain} percent chance of rain"
        return report + "."
    except Exception as error:
        print(f"[Weather error: {error}]")
        return None


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------
def get_news(topic: str = "", count: int = 0) -> list:
    """Return a list of headline strings (empty list if unavailable)."""
    count = count or config.NEWS_COUNT
    if topic:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(topic)}&{config.NEWS_REGION}"
    else:
        url = f"https://news.google.com/rss?{config.NEWS_REGION}"
    try:
        root = ET.fromstring(_get(url))
        headlines = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]  # Remove " - Source Name"
            if title:
                headlines.append(title)
            if len(headlines) >= count:
                break
        return headlines
    except Exception as error:
        print(f"[News error: {error}]")
        return []


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------
_VK_MUTE, _VK_DOWN, _VK_UP = 0xAD, 0xAE, 0xAF  # Windows media keys (each step = 2%)


def _press_key(key: int, times: int = 1) -> None:
    import ctypes

    for _ in range(times):
        ctypes.windll.user32.keybd_event(key, 0, 0, 0)  # key down
        ctypes.windll.user32.keybd_event(key, 0, 2, 0)  # key up
        time.sleep(0.01)


def change_volume(amount: int) -> bool:
    """Raise (positive) or lower (negative) the volume by a percentage."""
    try:
        if OS_NAME == "Windows":
            _press_key(_VK_UP if amount > 0 else _VK_DOWN, max(1, abs(amount) // 2))
            return True
        if OS_NAME == "Darwin":
            return _run(["osascript", "-e",
                         f"set volume output volume ((output volume of (get volume settings)) + {amount})"])
        sign = "+" if amount > 0 else "-"
        return _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{sign}{abs(amount)}%"])
    except Exception as error:
        print(f"[Volume error: {error}]")
        return False


def set_volume(level: int) -> bool:
    """Set the volume to an exact percentage (0-100)."""
    level = max(0, min(100, level))
    try:
        if OS_NAME == "Windows":
            _press_key(_VK_DOWN, 50)          # Go to 0
            if level:
                _press_key(_VK_UP, round(level / 2))
            return True
        if OS_NAME == "Darwin":
            return _run(["osascript", "-e", f"set volume output volume {level}"])
        return _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"])
    except Exception as error:
        print(f"[Volume error: {error}]")
        return False


def mute(on: bool = True) -> bool:
    try:
        if OS_NAME == "Windows":
            _press_key(_VK_UP)    # Pressing a volume key always unmutes...
            _press_key(_VK_DOWN)  # ...and this keeps the level the same
            if on:
                _press_key(_VK_MUTE)
            return True
        if OS_NAME == "Darwin":
            state = "with" if on else "without"
            return _run(["osascript", "-e", f"set volume {state} output muted"])
        return _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if on else "0"])
    except Exception as error:
        print(f"[Volume error: {error}]")
        return False


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------
def take_screenshot():
    """Save a screenshot and return its file path (or None)."""
    try:
        from PIL import ImageGrab

        os.makedirs(config.SCREENSHOT_FOLDER, exist_ok=True)
        name = datetime.datetime.now().strftime("screenshot_%Y-%m-%d_%H-%M-%S.png")
        path = os.path.join(config.SCREENSHOT_FOLDER, name)
        image = ImageGrab.grab(all_screens=True) if OS_NAME == "Windows" else ImageGrab.grab()
        image.save(path)
        return path
    except Exception as error:
        print(f"[Screenshot error: {error}]")
        return None


# ---------------------------------------------------------------------------
# Lock / shutdown / restart
# ---------------------------------------------------------------------------
def lock_computer() -> bool:
    try:
        if OS_NAME == "Windows":
            import ctypes
            return bool(ctypes.windll.user32.LockWorkStation())
        if OS_NAME == "Darwin":
            return _run(["pmset", "displaysleepnow"])
        return _run(["loginctl", "lock-session"])
    except Exception as error:
        print(f"[Lock error: {error}]")
        return False


def power_off(restart: bool = False) -> bool:
    """Shut down or restart after config.SHUTDOWN_DELAY_SECONDS."""
    delay = config.SHUTDOWN_DELAY_SECONDS
    if OS_NAME == "Windows":
        return _run(["shutdown", "/r" if restart else "/s", "/t", str(delay)])
    if OS_NAME == "Darwin":
        action = "restart" if restart else "shut down"
        return _run(["osascript", "-e", f'tell app "System Events" to {action}'])
    return _run(["shutdown", "-r" if restart else "-h", f"+{max(1, round(delay / 60))}"])


def cancel_power_off() -> bool:
    if OS_NAME == "Windows":
        return _run(["shutdown", "/a"])
    if OS_NAME == "Linux":
        return _run(["shutdown", "-c"])
    return False
