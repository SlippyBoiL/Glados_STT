from __future__ import annotations

import os
import platform
import re
import urllib.parse
import webbrowser
from typing import Tuple

DEFAULT_ENGINE = "google"


def extract_search_query(text: str) -> str:
    """Pull search terms from natural language."""
    low = (text or "").lower().strip()
    patterns = [
        r"(?:search(?:\s+the\s+web)?\s+for|google|look\s+up|find)\s+(.+)",
        r"(?:what\s+is|who\s+is|where\s+is)\s+(.+)",
        r"(?:browse|research)\s+(.+)",
    ]
    for pat in patterns:
        m = re.search(pat, low, re.IGNORECASE)
        if m:
            q = m.group(1).strip()
            q = re.sub(r"\s+(online|on the web|for me)\s*$", "", q, flags=re.IGNORECASE)
            return q.strip("?. ")
    return ""


def search_url(query: str, engine: str = DEFAULT_ENGINE) -> str:
    q = urllib.parse.quote_plus((query or "").strip())
    eng = (engine or DEFAULT_ENGINE).lower()
    if eng == "duckduckgo":
        return f"https://duckduckgo.com/?q={q}"
    if eng == "bing":
        return f"https://www.bing.com/search?q={q}"
    return f"https://www.google.com/search?q={q}"


def open_browser_search(query: str, engine: str = DEFAULT_ENGINE, browser: str = "default") -> Tuple[bool, str]:
    if not (query or "").strip():
        return False, "No search query found. Try: search the web for weather in Seattle."

    url = search_url(query, engine)
    opened = False
    browser_key = (browser or "default").lower()

    # Prefer explicit browser binary on Windows when configured
    if platform.system() == "Windows" and browser_key not in ("default", ""):
        paths = {
            "chrome": [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ],
            "edge": [
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            ],
            "firefox": [
                os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
            ],
        }
        for exe in paths.get(browser_key, []):
            if exe and os.path.isfile(exe):
                os.spawnl(os.P_NOWAIT, exe, exe, url)
                opened = True
                break

    if not opened:
        webbrowser.open(url, new=2)

    return True, f"Opened browser — searching for: {query}"
