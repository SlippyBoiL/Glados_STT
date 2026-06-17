from __future__ import annotations

import re
import time
from typing import Any, Dict, Tuple
from urllib.parse import quote_plus


def initial_navigation_url(user_input: str) -> str:
    m = re.search(r"https?://[^\s\"']+", user_input or "", re.I)
    if m:
        return m.group(0).rstrip(".,)")

    low = (user_input or "").lower()
    query = _search_query_from_text(user_input)

    if "wikipedia" in low:
        return f"https://en.wikipedia.org/wiki/Special:Search?search={quote_plus(query)}"
    if "duckduckgo" in low:
        return f"https://duckduckgo.com/?q={quote_plus(query)}"
    return f"https://www.google.com/search?q={quote_plus(query)}"


def _search_query_from_text(text: str) -> str:
    raw = (text or "").strip()
    for prefix in (
        r"^glados[,:\s]+",
        r"^hey glados[,:\s]+",
        r"^can you ",
        r"^could you ",
        r"^please ",
        r"^go to ",
        r"^visit ",
        r"^browse ",
        r"^search for ",
        r"^look up ",
        r"^find out ",
        r"^research ",
    ):
        raw = re.sub(prefix, "", raw, flags=re.I).strip()
    return raw[:200] or "search"


def execute_action(page: Any, action: Dict[str, Any]) -> Tuple[bool, str]:
    """Run one browser action. Returns (ok, message)."""
    kind = str(action.get("action") or "").strip().lower()
    if not kind:
        return False, "Missing action field"

    if kind == "navigate":
        url = str(action.get("url") or "").strip()
        if not url:
            return False, "navigate requires url"
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        return True, f"Navigated to {url[:80]}"

    if kind == "click":
        target = str(action.get("element") or action.get("text") or "").strip()
        if not target:
            return False, "click requires element text"
        try:
            page.get_by_text(target, exact=False).first.click(timeout=8000)
            return True, f"Clicked '{target[:60]}'"
        except Exception:
            try:
                page.click(f"text={target}", timeout=8000)
                return True, f"Clicked '{target[:60]}'"
            except Exception as e:
                return False, f"Click failed: {e}"

    if kind == "type":
        target = str(action.get("element") or "").strip()
        text = str(action.get("text") or "")
        if not text:
            return False, "type requires text"
        try:
            if target:
                loc = page.get_by_label(target, exact=False)
                if loc.count() == 0:
                    loc = page.get_by_placeholder(target, exact=False)
                if loc.count() == 0:
                    loc = page.get_by_role("textbox", name=target)
                loc.first.fill(text, timeout=8000)
            else:
                page.keyboard.type(text)
            return True, f"Typed into '{target or 'focus'}'"
        except Exception as e:
            try:
                page.keyboard.type(text)
                return True, "Typed at focus"
            except Exception as e2:
                return False, f"Type failed: {e}; {e2}"

    if kind == "press":
        key = str(action.get("key") or "Enter")
        page.keyboard.press(key)
        return True, f"Pressed {key}"

    if kind == "scroll":
        page.mouse.wheel(0, 600)
        return True, "Scrolled down"

    if kind == "wait":
        sec = float(action.get("seconds") or 2)
        time.sleep(min(sec, 10))
        return True, f"Waited {sec}s"

    if kind == "finish":
        answer = str(action.get("text") or action.get("answer") or "").strip()
        return True, answer or "Task complete."

    return False, f"Unknown action: {kind}"
