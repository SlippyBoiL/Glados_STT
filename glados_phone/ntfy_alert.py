"""Free phone wake-up via ntfy.sh (priority push — no PSTN fees)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


DEFAULT_NTFY_SERVER = "https://ntfy.sh"


def ntfy_config(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    cfg = cfg or {}
    topic = str(
        os.environ.get("NTFY_TOPIC")
        or cfg.get("ntfy_topic")
        or ""
    ).strip()
    server = str(
        os.environ.get("NTFY_SERVER")
        or cfg.get("ntfy_server")
        or DEFAULT_NTFY_SERVER
    ).rstrip("/")
    token = str(os.environ.get("NTFY_TOKEN") or cfg.get("ntfy_token") or "").strip()
    return {"topic": topic, "server": server, "token": token}


def push_ntfy_alert(
    cfg: Optional[Dict[str, Any]] = None,
    *,
    title: str = "GLaDOS",
    message: str = "",
    priority: str = "urgent",
    tags: str = "rotating_light,telephone_receiver",
    click_url: str = "",
    action_label: str = "Open call",
) -> Dict[str, Any]:
    """
    Send a high-priority push to the operator's phone via ntfy.

    Setup (100% free):
      1. Install the ntfy app (Android/iOS)
      2. Subscribe to a private topic name (e.g. glados-slippy-7f3a)
      3. Set NTFY_TOPIC=that-topic in .env

    If click_url is set (GLaDOS live /call page), tapping the notification
    opens a free voice/text session — not a carrier PSTN call.
    """
    cfg = cfg or {}
    conf = ntfy_config(cfg)
    topic = conf["topic"]
    server = conf["server"]
    if not topic:
        return {
            "ok": False,
            "provider": "ntfy",
            "detail": (
                "ntfy not configured. Install the free ntfy app, subscribe to a topic, "
                "then set NTFY_TOPIC=your-secret-topic in .env"
            ),
        }

    if not click_url:
        try:
            from brain_server.call_routes import call_page_url

            click_url = call_page_url(cfg)
        except Exception:
            click_url = ""

    body = (message or "GLaDOS is calling. Tap to open the live line.").strip()[:2000]
    if click_url and click_url not in body:
        body = f"{body}\n\nTap Open call → {click_url}"[:2000]

    url = f"{server}/{topic}"
    # HTTP header values must be latin-1 — keep titles ASCII-safe.
    safe_title = (
        (title or "GLaDOS")
        .replace("—", "-")
        .replace("–", "-")
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        or "GLaDOS"
    )[:120]
    headers = {
        "Title": safe_title,
        "Priority": priority or "urgent",
        "Tags": tags,
        "Content-Type": "text/plain; charset=utf-8",
    }
    if click_url:
        # ntfy: Click opens URL; Actions adds a button
        headers["Click"] = click_url
        safe_label = (
            (action_label or "Open call")
            .encode("ascii", "ignore")
            .decode("ascii")
            .strip()
            or "Open call"
        )
        headers["Actions"] = f"view, {safe_label}, {click_url}, clear=true"
    if conf["token"]:
        headers["Authorization"] = f"Bearer {conf['token']}"

    try:
        req = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw.strip().startswith("{") else {"raw": raw}
            except Exception:
                payload = {"raw": raw[:200]}
            return {
                "ok": True,
                "provider": "ntfy",
                "detail": f"urgent push sent to {server}/{topic}",
                "response": payload,
                "topic": topic,
                "click_url": click_url or None,
            }
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:300]
        return {"ok": False, "provider": "ntfy", "detail": f"HTTP {exc.code}: {err}"}
    except Exception as exc:
        return {"ok": False, "provider": "ntfy", "detail": str(exc)}
