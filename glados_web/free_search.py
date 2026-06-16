from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

_BLOCKED_HOSTS = (
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "tiktok.com",
    "pinterest.com",
)

_USER_AGENT = "Mozilla/5.0 (compatible; Glados/1.0; +https://github.com/SlippyBoiL/Glados_STT)"


def _blocked_url(url: str) -> bool:
    try:
        host = (urlparse(url).netloc or "").lower().lstrip("www.")
        return any(host == b or host.endswith("." + b) for b in _BLOCKED_HOSTS)
    except Exception:
        return True


def check_internet(timeout: float = 6.0) -> bool:
    """Quick connectivity probe — no API keys."""
    try:
        r = requests.head(
            "https://duckduckgo.com/",
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
            allow_redirects=True,
        )
        return r.status_code < 500
    except Exception:
        return False


def _url_score(url: str) -> int:
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").strip("/")
        score = len(path.split("/")) if path else 0
        if "wikipedia.org" in host:
            score += 8
        if host.endswith(".edu") or host.endswith(".gov"):
            score += 4
        if any(x in host for x in ("stackoverflow.com", "microsoft.com", "mozilla.org", "python.org")):
            score += 3
        if not path or path in ("", "index.html", "home"):
            score -= 4
        if "?" in url and len(path) < 2:
            score -= 3
        return score
    except Exception:
        return 0


def _duckduckgo_urls(query: str, max_results: int = 8) -> List[str]:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return []
    q = (query or "").strip()
    if not q:
        return []
    rows: List[str] = []
    for attempt in range(3):
        try:
            with DDGS() as ddgs:
                for row in ddgs.text(q, max_results=max_results):
                    href = str(row.get("href") or "").strip()
                    if href.startswith("http") and not _blocked_url(href):
                        rows.append(href)
        except Exception:
            rows = []
        if rows:
            break
        time.sleep(1.2 * (attempt + 1))
    if not rows:
        return []
    rows.sort(key=_url_score, reverse=True)
    seen: set = set()
    out: List[str] = []
    for u in rows:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _scrape_paragraphs(url: str, *, timeout: float = 12.0, max_paragraphs: int = 4) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "(beautifulsoup4 not installed — run: pip install beautifulsoup4)"

    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
    except requests.Timeout:
        return f"(Timeout fetching {url})"
    except requests.RequestException as e:
        return f"(Could not fetch page: {e})"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()

    paragraphs: List[str] = []
    for p in soup.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
        if len(text) < 40:
            continue
        if text.lower() in {t.lower() for t in paragraphs}:
            continue
        paragraphs.append(text)
        if len(paragraphs) >= max_paragraphs:
            break

    if not paragraphs:
        title = soup.title.get_text(strip=True) if soup.title else ""
        if title:
            return f"Page title: {title}\n(No readable paragraphs found.)"
        return "(No readable paragraphs on that page.)"
    return "\n\n".join(paragraphs)


def search_and_read_web(
    query: str,
    *,
    cfg: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    max_paragraphs: int = 4,
) -> str:
    """
    Free web research: DuckDuckGo text search → top result URL → scrape <p> paragraphs.
    No API keys. Returns a single string for the LLM.
    """
    cfg = cfg or {}
    q = (query or "").strip()
    if not q:
        return "(Empty search query.)"

    to = float(timeout if timeout is not None else cfg.get("web_scrape_timeout_sec") or 12.0)
    urls = _duckduckgo_urls(q)
    errors: List[str] = []
    for url in urls[:5]:
        body = _scrape_paragraphs(url, timeout=to, max_paragraphs=max_paragraphs)
        if body.startswith("(Could not fetch") or body.startswith("(Timeout"):
            errors.append(body)
            continue
        if body.startswith("(No readable"):
            errors.append(body)
            continue
        return f"Query: {q}\nURL: {url}\n\n{body}"[:6000]

    # Fallback: DuckDuckGo instant answer API (still free, no key)
    try:
        from glados_skills.research import fetch_web_summary

        summary = fetch_web_summary(q, timeout=min(to, 8.0))
        if summary:
            return f"Query: {q}\n\nDuckDuckGo summary (page scrape failed):\n{summary}"
    except Exception:
        pass
    if errors:
        return f"(No readable page for: {q}. Last error: {errors[-1][:200]})"
    return f"(No search results for: {q})"
