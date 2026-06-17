from __future__ import annotations

import re
from typing import Any, Dict

# Web / live-data phrasing — triggers visible browser agent loop.
_WEB_TRIGGERS = (
    "go to ",
    "visit ",
    "browse ",
    "navigate to ",
    "open http",
    "open https",
    "open www.",
    "wikipedia",
    "http://",
    "https://",
    "www.",
    "website",
    "web page",
    "webpage",
    "on google",
    "google it",
    "search the web",
    "search online",
    "search for ",
    "look up ",
    "look online",
    "find out ",
    "find on ",
    "who invented",
    "who created",
    "what is the current",
    "current price",
    "live data",
    "log in to",
    "login to",
    "sign in to",
    "fill in ",
    "click ",
    "extract from",
    "read the page",
    "check the site",
    "check this site",
    "on the internet",
    "online about",
    "research ",
    "duckduckgo",
)

# Pure conversation — skip browser even if substring matches.
_CHAT_ONLY = (
    "how are you",
    "who are you",
    "what are you",
    "thank you",
    "hello",
    "hi glados",
    "are you learning",
    "are you there",
)


def should_use_browser_agent(text: str, cfg: Dict[str, Any]) -> bool:
    if not bool(cfg.get("browser_agent_enabled", True)):
        return False
    raw = (text or "").strip()
    if len(raw) < 4:
        return False
    low = raw.lower()
    if any(p in low for p in _CHAT_ONLY) and not any(
        w in low for w in ("search", "website", "http", "wikipedia", "browse", "go to")
    ):
        return False
    if re.search(r"https?://\S+", raw, re.I):
        return True
    if any(p in low for p in _WEB_TRIGGERS):
        return True
    # Questions that imply live facts (not memory-only chit-chat)
    if low.endswith("?") and any(
        w in low
        for w in (
            "when did",
            "when was",
            "who is",
            "who was",
            "what year",
            "how much does",
            "how many ",
            "latest ",
            "today's",
            "right now",
        )
    ):
        return True
    return False
