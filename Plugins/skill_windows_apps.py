# DESCRIPTION: Direct Windows app open/close — no LLM, no Open Interpreter.
"""Reliable local app launch and terminate on Windows."""

from __future__ import annotations

import glob
import os
import re
import subprocess
import webbrowser
import winreg
from typing import Optional, Tuple

APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "discord": "discord",
    "spotify": "spotify",
    "steam": "steam",
    "autocad": "autocad",
    "vs code": "code",
    "code": "code",
    "cursor": "cursor",
}

WEB_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "canvas": "https://canvas.instructure.com",
}

PROCESS_MAP = {
    "chrome": "chrome.exe",
    "discord": "Discord.exe",
    "spotify": "Spotify.exe",
    "steam": "steam.exe",
    "code": "Code.exe",
    "cursor": "Cursor.exe",
    "notepad": "notepad.exe",
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
}


def find_app_path(app_name: str) -> str:
    """Resolve an app name to an executable path on Windows."""
    common_paths = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "firefox": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ],
        "discord": [os.path.expandvars(r"%APPDATA%\Discord\Update.exe --processStart Discord.exe")],
        "spotify": [os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")],
        "steam": [
            r"C:\Program Files (x86)\Steam\steam.exe",
            r"C:\Program Files\Steam\steam.exe",
        ],
        "autocad": [
            r"C:\Program Files\Autodesk\AutoCAD 2026\acad.exe",
            r"C:\Program Files\Autodesk\AutoCAD 2025\acad.exe",
            r"C:\Program Files\Autodesk\AutoCAD 2024\acad.exe",
        ],
        "code": [
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
        ],
        "cursor": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\cursor\Cursor.exe"),
            r"C:\Program Files\Cursor\Cursor.exe",
        ],
        "edge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
    }

    if app_name in common_paths:
        for path in common_paths[app_name]:
            if os.path.exists(path):
                return path

    if app_name == "autocad":
        for base in (r"C:\Program Files\Autodesk", r"C:\Program Files (x86)\Autodesk"):
            hits = sorted(glob.glob(os.path.join(base, "AutoCAD *", "acad.exe")))
            if hits:
                return hits[-1]

    try:
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as registry_key:
            subkeys = winreg.QueryInfoKey(registry_key)[0]
            for i in range(subkeys):
                subkey_name = winreg.EnumKey(registry_key, i)
                if app_name.lower() in subkey_name.lower():
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, f"{reg_path}\\{subkey_name}"
                    ) as subkey:
                        path, _ = winreg.QueryValueEx(subkey, "")
                        if os.path.exists(path):
                            return path
    except OSError:
        pass

    return app_name


def extract_app_name(text: str, *, close: bool = False) -> str:
    """Pull the app name from natural language (uses the last open/close verb)."""
    low = (text or "").lower()
    if close:
        pattern = r"\b(?:close|quit|kill|terminate|stop|exit)\s+(?:the\s+)?(.+?)(?:\?|\.|$)"
    else:
        pattern = (
            r"\b(?:open(?:\s+up)?|launch|start|fire up|boot up|run)\s+(?:the\s+)?(.+?)(?:\?|\.|$)"
        )
    matches = list(re.finditer(pattern, low))
    if matches:
        name = matches[-1].group(1).strip(" .!?")
    else:
        verbs = (
            r"\b(close|quit|kill|terminate|stop|exit)\b"
            if close
            else r"\b(open(?:\s+up)?|start|launch|fire up|boot up|run)\b"
        )
        name = re.sub(verbs, "", low).strip()
        name = re.sub(r"^(can you|could you|please|would you|hey|hi|hello)\s+", "", name)
        name = name.strip(" .!?")
    name = re.sub(r"^(the|a|an)\s+", "", name)
    # Drop trailing polite / purpose clauses: "steam for me", "notepad please", etc.
    name = re.split(
        r"\s+(?:so|because|and then|once|for me|for us|please|thanks|thank you)\b",
        name,
        maxsplit=1,
    )[0].strip(" .!?")
    name = re.sub(r"\s+(?:for me|for us|please)$", "", name).strip(" .!?")
    # Prefer known aliases when the phrase contains one (e.g. "steam for me" → steam)
    for alias in sorted(APP_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", name):
            return alias
    return name.strip(" .!?")


def wants_app_open(text: str) -> bool:
    low = (text or "").lower()
    return bool(re.search(r"\b(open(?:\s+up)?|launch|start|fire up|boot up)\s+", low))


def wants_app_close(text: str) -> bool:
    low = (text or "").lower()
    return bool(re.search(r"\b(close|quit|kill|terminate|stop|exit)\s+", low))


def is_vague_app_request(text: str) -> bool:
    low = (text or "").lower()
    return any(p in low for p in ("random app", "some app", "any app", "a random", "open up a random"))


def try_app_action(text: str) -> Optional[Tuple[str, bool, str]]:
    """Return (action, ok, detail) if this is an app open/close request, else None."""
    if not text or is_vague_app_request(text):
        return None
    low = text.lower()
    if not wants_app_open(text) and not wants_app_close(text):
        return None
    if any(
        p in low
        for p in ("github", "git push", "git commit", "deploy", "script", "protocol", "teach yourself")
    ):
        return None

    if wants_app_close(text):
        app = extract_app_name(text, close=True)
        ok, detail = close_app(app)
        return ("close", ok, detail or app)

    app = extract_app_name(text, close=False)
    ok, detail = open_app(app)
    return ("open", ok, detail or app)


def open_app(app_name: str) -> Tuple[bool, str]:
    app_name = (app_name or "").strip().lower()
    if not app_name:
        return False, "No application name given."

    if app_name in WEB_SITES:
        webbrowser.open(WEB_SITES[app_name])
        return True, app_name

    folder_map = {
        "downloads": "Downloads",
        "download": "Downloads",
        "desktop": "Desktop",
        "documents": "Documents",
        "pictures": "Pictures",
        "music": "Music",
        "videos": "Videos",
    }
    folder_key = app_name.replace(" folder", "").strip()
    if folder_key in folder_map:
        path = os.path.join(os.path.expanduser("~"), folder_map[folder_key])
        if os.path.isdir(path):
            os.startfile(path)
            return True, folder_map[folder_key]

    app_key = APP_ALIASES.get(app_name, app_name)
    exe_path = find_app_path(app_key)
    try:
        if exe_path and os.path.isdir(exe_path):
            os.startfile(exe_path)
            return True, app_name
        candidates = []
        for c in (exe_path, app_key, f"{app_key}.exe"):
            if c and c not in candidates:
                candidates.append(c)
        for candidate in candidates:
            if os.path.isfile(candidate):
                if " --processStart " in candidate:
                    parts = candidate.split(" --processStart ")
                    subprocess.Popen([parts[0], "--processStart", parts[1]], shell=False)
                else:
                    subprocess.Popen([candidate], shell=False)
                return True, app_name
        return False, f"Could not find executable for '{app_name}'."
    except Exception as exc:
        return False, str(exc)


def close_app(app_name: str) -> Tuple[bool, str]:
    app_name = (app_name or "").strip().lower()
    if not app_name:
        return False, "No application name given."
    process_name = PROCESS_MAP.get(app_name, f"{app_name}.exe")
    if not process_name.lower().endswith(".exe"):
        process_name = f"{process_name}.exe"
    try:
        proc = subprocess.run(
            ["taskkill", "/f", "/im", process_name],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return True, app_name
        return False, (proc.stderr or proc.stdout or "Process not running.").strip()
    except Exception as exc:
        return False, str(exc)
