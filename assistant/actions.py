"""
actions.py - Things Jarvis can DO on your computer (open browser, apps, etc.).

These functions don't speak; they just perform the action.
"""

import os
import platform
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import webbrowser

import config
from assistant import browser

OS_NAME = platform.system()  # "Windows", "Darwin" (macOS) or "Linux"


def _find_chrome():
    """Return the command/path to start Chrome, or None if not found."""
    if OS_NAME == "Windows":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
    elif OS_NAME == "Darwin":
        path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(path):
            return path
    else:  # Linux
        for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
            found = shutil.which(name)
            if found:
                return found
    return None


def open_chrome(url: str = "") -> bool:
    """Open Google Chrome (optionally at a URL). Returns True if Chrome was used."""
    chrome = _find_chrome()
    if chrome:
        args = [chrome] + ([url] if url else [])
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    # Chrome not installed: fall back to the default browser
    webbrowser.open(url or "https://www.google.com")
    return False


def open_browser_home() -> bool:
    """Open the browser at Google. Returns False if Chrome isn't installed."""
    if config.USE_JARVIS_BROWSER and browser.open("https://www.google.com"):
        return True
    return open_chrome()


def open_url(url: str) -> None:
    """Open a link: in Jarvis's own browser (reusing tabs), else Chrome / default browser."""
    if config.USE_JARVIS_BROWSER and browser.open(url):
        return
    if config.USE_CHROME:
        open_chrome(url)
    else:
        webbrowser.open(url)


def google_search(query: str) -> None:
    open_url("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))


def youtube_search(query: str) -> None:
    open_url("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query))


def play_on_youtube(query: str) -> None:
    """Open the first YouTube video for the query (falls back to search results)."""
    search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    try:
        request = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=6) as response:
            html = response.read().decode("utf-8", errors="ignore")
        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        if video_ids:
            open_url(f"https://www.youtube.com/watch?v={video_ids[0]}")
            return
    except Exception as error:
        print(f"[Couldn't fetch first video, opening search instead: {error}]")
    open_url(search_url)


def open_app(name: str) -> bool:
    """Launch a desktop app listed in config.APPS. Returns True on success."""
    commands = config.APPS.get(name, {})
    command = commands.get(OS_NAME)
    if not command:
        return False
    try:
        subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as error:
        print(f"[Couldn't open {name}: {error}]")
        return False


def close_app(name: str) -> bool:
    """Close a desktop app listed in config.APP_PROCESSES. Returns True on success."""
    processes = config.APP_PROCESSES.get(name, {}).get(OS_NAME, [])
    closed = False
    for process in processes:
        if OS_NAME == "Windows":
            commands = [["taskkill", "/IM", process], ["taskkill", "/F", "/IM", process]]  # polite, then forced
        elif OS_NAME == "Darwin":
            commands = [["osascript", "-e", f'quit app "{process}"']]
        else:
            commands = [["pkill", "-f", process]]
        for command in commands:
            result = subprocess.run(command, capture_output=True)
            if result.returncode == 0:
                closed = True
                break
    return closed
