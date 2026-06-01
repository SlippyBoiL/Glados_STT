from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROFILE = os.path.join(REPO_ROOT, "data", "glados_browser_profile")
SESSION_FILE = os.path.join(REPO_ROOT, "data", "glados_browser_session.json")
DEFAULT_DEBUG_PORT = 9222


def debug_port_from_cfg(cfg: dict | None) -> int:
    if cfg:
        try:
            return int(cfg.get("browser_debug_port") or DEFAULT_DEBUG_PORT)
        except (TypeError, ValueError):
            pass
    return DEFAULT_DEBUG_PORT


def _chrome_paths() -> list[str]:
    return [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]


def _edge_paths() -> list[str]:
    return [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ]


def _find_exe(browser: str) -> Optional[str]:
    key = (browser or "chrome").lower()
    paths = _edge_paths() if key == "edge" else _chrome_paths()
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return None


def _load_session() -> dict:
    if not os.path.isfile(SESSION_FILE):
        return {}
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_session(data: dict) -> None:
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_cdp_targets(port: int) -> List[dict]:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/json/list", method="GET")
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _cdp_alive(port: int) -> bool:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/json/version", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _activate_tab(port: int, tab_id: str) -> bool:
    try:
        url = f"http://127.0.0.1:{port}/json/activate/{tab_id}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def _create_tab(port: int, url: str) -> Optional[dict]:
    try:
        q = urllib.parse.quote(url, safe="")
        nav_url = f"http://127.0.0.1:{port}/json/new?{q}"
        req = urllib.request.Request(nav_url, method="PUT")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def ensure_browser_tab(
    url: str,
    *,
    site_key: str,
    url_hint: str,
    browser: str = "chrome",
    profile_dir: str | None = None,
    debug_port: int | None = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Reuse one tab per site_key (gemini / perplexity / search).
    Navigates the existing tab in place — does not spam new tabs.
    Returns (ok, message, webSocketDebuggerUrl).
    """
    if not url or not url.strip():
        return False, "No URL.", None

    profile = profile_dir or DEFAULT_PROFILE
    port = int(debug_port or DEFAULT_DEBUG_PORT)
    exe = _find_exe(browser)
    if not exe:
        return False, f"Browser executable not found for {browser}.", None

    os.makedirs(profile, exist_ok=True)
    sess = _load_session()
    site_tabs: Dict[str, str] = dict(sess.get("site_tabs") or {})
    hint = (url_hint or "").lower()

    if not _cdp_alive(port):
        args = [
            exe,
            f"--user-data-dir={profile}",
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
            url,
        ]
        try:
            subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        except Exception as e:
            return False, f"Failed to start browser: {e}", None
        sess.update(
            {
                "browser": browser,
                "profile_dir": profile,
                "debug_port": port,
            }
        )
        _save_session(sess)
        return True, f"Started Glados browser — {url[:70]}", None

    targets = list_cdp_targets(port)
    chosen: Optional[dict] = None

    stored_id = site_tabs.get(site_key)
    if stored_id:
        for tab in targets:
            if tab.get("id") == stored_id and tab.get("webSocketDebuggerUrl"):
                chosen = tab
                break

    if not chosen and hint:
        for tab in targets:
            tab_url = str(tab.get("url") or "").lower()
            if hint in tab_url and tab.get("type") == "page" and tab.get("webSocketDebuggerUrl"):
                chosen = tab
                break

    if chosen:
        tab_id = str(chosen.get("id") or "")
        ws = str(chosen.get("webSocketDebuggerUrl") or "")
        if tab_id:
            _activate_tab(port, tab_id)
        site_tabs[site_key] = tab_id
        sess["site_tabs"] = site_tabs
        sess["last_url"] = url
        _save_session(sess)
        return True, f"Reusing tab for {site_key}", ws

    new_tab = _create_tab(port, url)
    if new_tab and new_tab.get("webSocketDebuggerUrl"):
        tab_id = str(new_tab.get("id") or "")
        site_tabs[site_key] = tab_id
        sess["site_tabs"] = site_tabs
        sess["last_url"] = url
        _save_session(sess)
        return True, f"Opened one tab for {site_key}", str(new_tab["webSocketDebuggerUrl"])

    return False, "Could not attach to browser tab.", None


def open_in_glados_browser(
    url: str,
    browser: str = "chrome",
    profile_dir: str | None = None,
    debug_port: int | None = None,
    *,
    site_key: str = "search",
    url_hint: str = "",
) -> Tuple[bool, str]:
    """Backward-compatible wrapper — prefers tab reuse."""
    hint = url_hint or _url_hint_from_url(url)
    ok, msg, _ws = ensure_browser_tab(
        url,
        site_key=site_key,
        url_hint=hint,
        browser=browser,
        profile_dir=profile_dir,
        debug_port=debug_port,
    )
    return ok, msg


def _url_hint_from_url(url: str) -> str:
    low = (url or "").lower()
    if "gemini.google" in low:
        return "gemini.google"
    if "perplexity.ai" in low:
        return "perplexity.ai"
    if "google.com/search" in low:
        return "google.com/search"
    return low.split("/")[2] if "://" in low else low
