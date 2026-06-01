from __future__ import annotations

import argparse
import os
import time
from typing import List


def _parse_hotkey(hotkey: str) -> List[str]:
    """
    Parses simple hotkey strings like:
      "ctrl+shift+p"
    into ["ctrl", "shift", "p"] for pyautogui.hotkey.
    """
    return [p.strip().lower() for p in hotkey.split("+") if p.strip()]


def inject_prompt(markdown: str, mode: str = "clipboard_only") -> None:
    """
    Safe Cursor prompt injection MVP.

    mode:
      - clipboard_only: always copies to clipboard; no UI automation.
      - hotkey_paste: uses pyautogui to open a target input and paste (requires hotkeys to be correct).
    """
    try:
        import pyperclip  # type: ignore
    except ImportError:
        print("[cursor] pyperclip not installed; cannot inject.")
        return

    pyperclip.copy(markdown)

    if mode == "clipboard_only":
        return

    if mode != "hotkey_paste":
        return

    try:
        import pyautogui  # type: ignore
    except ImportError:
        print("[cursor] pyautogui not installed; cannot inject UI.")
        return

    # Defaults are generic VS Code/Cursor-ish shortcuts. You should tune if needed.
    target_hotkey = os.environ.get("CURSOR_INJECT_TARGET_HOTKEY", "ctrl+shift+p")
    time.sleep(0.2)

    keys = _parse_hotkey(target_hotkey)
    if keys:
        pyautogui.hotkey(*keys)
    time.sleep(0.4)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.1)
    pyautogui.press("enter")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject a markdown prompt into Cursor.")
    parser.add_argument("--mode", default=os.environ.get("CURSOR_INJECT_MODE", "clipboard_only"))
    parser.add_argument("--prompt", default="")
    args = parser.parse_args()

    inject_prompt(args.prompt, mode=args.mode)


if __name__ == "__main__":
    main()

