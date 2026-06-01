from __future__ import annotations

import sys
import time
from typing import Any, Dict, List, Tuple

SITE_WINDOW_HINTS: Dict[str, List[str]] = {
    "gemini": ["gemini", "google chrome", "chrome"],
    "perplexity": ["perplexity", "google chrome", "chrome"],
}


def _activate_window(title: str) -> bool:
    try:
        import pygetwindow as gw

        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return False
        w = wins[0]
        if w.isMinimized:
            w.restore()
        w.activate()
        return True
    except Exception:
        return False


def focus_glados_browser(site_key: str) -> bool:
    """Bring Glados Chrome (Gemini / Perplexity tab) to foreground — facility admin."""
    hints = SITE_WINDOW_HINTS.get(site_key, ["chrome", "google chrome"])
    try:
        import pygetwindow as gw

        titles = gw.getAllTitles()
        for hint in hints:
            for title in titles:
                if not title or not title.strip():
                    continue
                if hint in title.lower():
                    if _activate_window(title):
                        time.sleep(0.5)
                        return True
    except Exception:
        pass
    if sys.platform == "win32":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            found = []

            def _enum(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    ln = ctypes.create_unicode_buffer(512)
                    user32.GetWindowTextW(hwnd, ln, 512)
                    t = ln.value.lower()
                    if any(h in t for h in hints):
                        found.append(hwnd)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(_enum), 0)
            if found:
                user32.SetForegroundWindow(found[0])
                time.sleep(0.5)
                return True
        except Exception:
            pass
    return False


def desktop_admin_type(
    prompt: str,
    site_key: str,
    cfg: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Physical keyboard control: focus browser, click prompt area, paste, Enter.
    Used when CDP cannot reach shadow-DOM editors (Gemini).
    """
    if not (prompt or "").strip():
        return False, "empty prompt"

    try:
        import pyautogui
        import pyperclip
    except ImportError:
        return False, "Install pyautogui and pyperclip for desktop admin typing."

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = float(cfg.get("skills_learn_desktop_pause") or 0.08)

    if not focus_glados_browser(site_key):
        return False, "Could not focus Glados browser window."

    time.sleep(float(cfg.get("skills_learn_browser_after_nav_sec") or 1.0))

    click_x = click_y = None
    try:
        import pygetwindow as gw

        hints = SITE_WINDOW_HINTS.get(site_key, ["chrome"])
        for title in gw.getAllTitles():
            if title and any(h in title.lower() for h in hints):
                wins = gw.getWindowsWithTitle(title)
                if wins:
                    w = wins[0]
                    click_x = int(w.left + w.width * 0.5)
                    click_y = int(w.top + max(w.height * 0.82, w.height - 140))
                    break
    except Exception:
        pass

    if click_x is None:
        sw, sh = pyautogui.size()
        click_x, click_y = sw // 2, int(sh * 0.88)

    pyautogui.click(click_x, click_y)
    time.sleep(0.35)
    pyautogui.click(click_x, click_y, clicks=3, interval=0.12)
    time.sleep(0.25)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.15)
    pyperclip.copy(prompt[:12000])
    pyautogui.hotkey("ctrl", "v")
    time.sleep(float(cfg.get("skills_learn_browser_after_type_sec") or 2.5))
    pyautogui.press("enter")
    return True, f"Desktop admin typed into {site_key} (clicked {click_x},{click_y})"
