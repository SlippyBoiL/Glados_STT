from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, Tuple

from facility_brain.web_search import extract_search_query, search_url


def infer_search_query(user_input: str) -> str:
    q = extract_search_query(user_input)
    if q:
        return q
    low = (user_input or "").lower()
    for prefix in (
        "can you ",
        "could you ",
        "would you ",
        "please ",
        "i need you to ",
        "i want you to ",
        "help me ",
        "learn how to ",
        "learn to ",
        "hey glados ",
        "glados ",
    ):
        if low.startswith(prefix):
            return user_input[len(prefix) :].strip()[:200]
    return (user_input or "").strip()[:200]


def fetch_web_summary(query: str, timeout: float = 8.0) -> str:
    if not (query or "").strip():
        return ""
    q = urllib.parse.quote_plus(query.strip())
    url = f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&skip_disambig=1"
    lines = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Glados/1.0 (skill-learning)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        if isinstance(data, dict):
            abstract = str(data.get("AbstractText") or "").strip()
            if abstract:
                lines.append(f"Summary: {abstract}")
            ans = str(data.get("Answer") or "").strip()
            if ans:
                lines.append(f"Answer: {ans}")
            for topic in (data.get("RelatedTopics") or [])[:6]:
                if isinstance(topic, dict) and topic.get("Text"):
                    lines.append(f"- {topic['Text'][:200]}")
    except Exception as e:
        lines.append(f"(Web lookup unavailable: {e})")
    return "\n".join(lines)[:2500]


def research_for_learning(
    user_input: str,
    *,
    open_browser: bool = True,
    engine: str = "google",
    browser: str = "default",
    search_query: str | None = None,
    cfg: Dict[str, Any] | None = None,
) -> Tuple[str, str]:
    cfg = cfg or {}
    query = (search_query or infer_search_query(user_input)).strip()
    parts = [f"Search query: {query}"]

    skip_tabs = bool(cfg.get("skills_learn_skip_search_tabs", True)) and bool(
        cfg.get("skills_learn_use_browser_ai", True)
    )
    if open_browser and query and not skip_tabs:
        url = search_url(query, engine)
        reuse = bool(cfg.get("skills_learn_reuse_browser", True))
        if reuse:
            from glados_skills.browser_session import open_in_glados_browser

            b = str(browser or cfg.get("preferred_browser") or "chrome")
            if b == "default":
                b = "chrome"
            ok, msg = open_in_glados_browser(
                url,
                browser=b,
                profile_dir=cfg.get("browser_profile_dir"),
                debug_port=cfg.get("browser_debug_port"),
                site_key="search",
                url_hint="google.com/search",
            )
            parts.append(msg if ok else f"Browser: {msg}")
        else:
            from facility_brain.web_search import open_browser_search

            ok, msg = open_browser_search(query, engine=engine, browser=browser)
            parts.append(msg if ok else "Browser search skipped.")
    elif open_browser and skip_tabs:
        parts.append("(Skipping extra Google tabs — Gemini/Perplexity only.)")

    summary = fetch_web_summary(query)
    if summary:
        parts.append("Online research:\n" + summary)
    return query, "\n".join(parts)
