"""
browser.py - Jarvis's own Chrome window, which Jarvis can fully control.

Why: a normal Python "open link" always creates a NEW tab and can never close it.
So Jarvis opens its own Chrome window (using Selenium). Because Jarvis controls
this window, it can reuse the YouTube tab, close tabs, and pause/resume/skip videos.

Notes:
    * Logins/cookies in this window are remembered (config.BROWSER_PROFILE_DIR).
    * The window closes when you close Jarvis.
    * If anything here fails, Jarvis falls back to your normal browser.
"""

import tempfile
import urllib.parse

import config

_driver = None

_BLANK_PREFIXES = ("data:", "about:", "chrome://new-tab-page", "chrome://newtab")

_MEDIA_SCRIPTS = {
    "pause": "const v=document.querySelector('video'); if(!v) return false; v.pause(); return true;",
    "resume": "const v=document.querySelector('video'); if(!v) return false; v.play(); return true;",
    "next": "const b=document.querySelector('.ytp-next-button'); if(!b) return false; b.click(); return true;",
}


# ---------------------------------------------------------------------------
# Starting / checking the browser
# ---------------------------------------------------------------------------
def _options(profile_dir: str):
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--autoplay-policy=no-user-gesture-required")  # Let videos start by themselves
    options.add_argument("--start-maximized")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Hide the "automated" banner
    return options


def _start():
    from selenium import webdriver

    print("[Starting Jarvis browser...]")
    try:
        return webdriver.Chrome(options=_options(config.BROWSER_PROFILE_DIR))
    except Exception as error:
        # Usually means the saved profile is still in use by another Jarvis window
        print(f"[Saved browser profile unavailable ({type(error).__name__}) - using a fresh one]")
        return webdriver.Chrome(options=_options(tempfile.mkdtemp(prefix="jarvis_chrome_")))


def _alive() -> bool:
    try:
        return _driver is not None and len(_driver.window_handles) > 0
    except Exception:
        return False  # You closed the window yourself


def _get_driver():
    global _driver
    if not _alive():
        quit()
        _driver = _start()
    return _driver


def _show() -> None:
    """Bring the current tab to the front so you can see it."""
    try:
        _driver.execute_cdp_cmd("Page.bringToFront", {})
    except Exception:
        pass


def _domain(url: str) -> str:
    netloc = urllib.parse.urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def _find_tab(match) -> str:
    """Switch to the first tab whose URL passes match(url). Returns its handle or None."""
    for handle in _driver.window_handles:
        _driver.switch_to.window(handle)
        if match(_driver.current_url.lower()):
            return handle
    return None


def _visible_tab():
    """The tab you are looking at right now (or None)."""
    return _find_tab(lambda url: _driver.execute_script("return document.visibilityState") == "visible")


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------
def open(url: str) -> bool:
    """Open a URL, reusing a tab of the same website if one is already open."""
    try:
        driver = _get_driver()
        domain = _domain(url)
        handle = _find_tab(lambda current: domain and domain in current)
        if handle is None:
            handle = _find_tab(lambda current: current.startswith(_BLANK_PREFIXES))
        if handle is None:
            driver.switch_to.new_window("tab")
        driver.get(url)
        _show()
        return True
    except Exception as error:
        print(f"[Jarvis browser error: {error}]")
        return False


def close_site(site: str) -> int:
    """Close every tab whose address contains `site`. Returns how many were closed."""
    if not _alive():
        return 0
    closed = 0
    try:
        for handle in list(_driver.window_handles):
            _driver.switch_to.window(handle)
            if site in _driver.current_url.lower():
                if len(_driver.window_handles) == 1:
                    quit()  # Last tab - close the whole window
                    return closed + 1
                _driver.close()
                closed += 1
        _driver.switch_to.window(_driver.window_handles[-1])
        _show()
    except Exception as error:
        print(f"[Jarvis browser error: {error}]")
    return closed


def close_current_tab() -> bool:
    if not _alive():
        return False
    try:
        handle = _visible_tab() or _driver.current_window_handle
        _driver.switch_to.window(handle)
        if len(_driver.window_handles) == 1:
            quit()
            return True
        _driver.close()
        _driver.switch_to.window(_driver.window_handles[-1])
        _show()
        return True
    except Exception as error:
        print(f"[Jarvis browser error: {error}]")
        return False


def media(action: str) -> bool:
    """Control the YouTube video: action is "pause", "resume" or "next"."""
    if not _alive():
        return False
    try:
        visible = _visible_tab()
        if visible is None or "youtube.com" not in _driver.current_url.lower():
            if _find_tab(lambda url: "youtube.com" in url) is None:
                return False
        return bool(_driver.execute_script(_MEDIA_SCRIPTS[action]))
    except Exception as error:
        print(f"[Jarvis browser error: {error}]")
        return False


def is_open() -> bool:
    return _alive()


def quit() -> None:
    """Close Jarvis's browser window completely."""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
    _driver = None
