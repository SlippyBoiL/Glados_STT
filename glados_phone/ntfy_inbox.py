"""Poll ntfy topic for inbound operator commands (free phone → GLaDOS).

Publish a message to your NTFY_TOPIC from the ntfy app (or share sheet).
GLaDOS treats the body as a chat command — e.g. text/publish: call me
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Set

from glados_phone.ntfy_alert import ntfy_config

_daemon_lock = threading.Lock()
_daemon_thread: Optional[threading.Thread] = None
_daemon_stop = threading.Event()
_seen: Set[str] = set()
_since: str = "1h"  # first poll: last hour only


def _state_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "ntfy_inbox_state.json")


def _load_state() -> None:
    global _since, _seen
    path = _state_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _since = str(data.get("since") or _since)
        _seen = set(str(x) for x in (data.get("seen") or []) if x)
    except Exception:
        pass


def _save_state() -> None:
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"since": _since, "seen": list(_seen)[-300:], "updated_at": time.time()},
            f,
        )


def _is_outbound_glados(title: str, message: str) -> bool:
    """Ignore alerts GLaDOS herself published (keep operator publishes)."""
    m = (message or "").strip().lower()
    # Bodies we emit on outbound alerts — never treat as operator commands
    markers = (
        "i am dialing you now",
        "cannot hear the phone line",
        "tap open call",
        "facility critical",
        "google voice is dialing",
        "urgent push sent",
        "your phone should light up",
        "publish to this ntfy topic",
    )
    return any(x in m for x in markers)


def poll_ntfy_commands(cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Fetch recent ntfy messages; return new inbound operator commands."""
    cfg = cfg or {}
    conf = ntfy_config(cfg)
    topic = conf["topic"]
    server = conf["server"]
    if not topic:
        return []

    global _since
    qs = urllib.parse.urlencode({"poll": "1", "since": _since})
    url = f"{server}/{topic}/json?{qs}"
    headers = {"Accept": "application/x-ndjson"}
    if conf["token"]:
        headers["Authorization"] = f"Bearer {conf['token']}"

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        print(f"[!] ntfy inbox HTTP {exc.code}")
        return []
    except Exception as exc:
        print(f"[!] ntfy inbox poll failed: {exc}")
        return []

    out: List[Dict[str, Any]] = []
    latest_id = ""
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("event") in ("open", "keepalive", "poll_request"):
            continue
        # Default event for published messages is "message" (or absent in some poll shapes)
        if obj.get("event") not in (None, "message"):
            continue
        mid = str(obj.get("id") or "")
        if mid:
            latest_id = mid
        if not mid or mid in _seen:
            continue
        title = str(obj.get("title") or "")
        message = str(obj.get("message") or "").strip()
        if not message:
            _seen.add(mid)
            continue
        if _is_outbound_glados(title, message):
            _seen.add(mid)
            continue
        _seen.add(mid)
        out.append({"id": mid, "title": title, "text": message})

    if latest_id:
        _since = latest_id
    if out or latest_id:
        _save_state()
    return out


def handle_ntfy_command(cfg: Dict[str, Any], text: str) -> Optional[str]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        from glados_hud.chat_bridge import enqueue_user_message
    except Exception:
        return None
    mid = enqueue_user_message(text, cfg, source="ntfy")
    if mid:
        print(f"[*] ntfy → GLaDOS: {text[:120]}")
    return mid


def start_ntfy_inbox_daemon(cfg: Optional[Dict[str, Any]] = None) -> bool:
    global _daemon_thread
    cfg = cfg or {}
    conf = ntfy_config(cfg)
    if not conf["topic"]:
        return False
    env = str(os.environ.get("NTFY_INBOX_ENABLED") or "").strip().lower()
    enabled = bool(cfg.get("ntfy_inbox_enabled", True))
    if env in ("0", "false", "no", "off"):
        enabled = False
    if env in ("1", "true", "yes", "on"):
        enabled = True
    if not enabled:
        return False

    with _daemon_lock:
        if _daemon_thread and _daemon_thread.is_alive():
            return True
        _daemon_stop.clear()
        _load_state()

        def _loop() -> None:
            poll_sec = float(
                os.environ.get("NTFY_INBOX_POLL_SEC")
                or cfg.get("ntfy_inbox_poll_sec")
                or 8
            )
            poll_sec = max(4.0, poll_sec)
            print(
                f"[*] ntfy inbox online — publish to '{conf['topic']}' from the ntfy app "
                f"(e.g. call me). Poll every {poll_sec:.0f}s."
            )
            if _daemon_stop.wait(5.0):
                return
            while not _daemon_stop.is_set():
                try:
                    for msg in poll_ntfy_commands(cfg):
                        handle_ntfy_command(cfg, msg.get("text") or "")
                except Exception as exc:
                    print(f"[!] ntfy inbox error: {exc}")
                if _daemon_stop.wait(poll_sec):
                    break

        _daemon_thread = threading.Thread(target=_loop, name="ntfy-inbox", daemon=True)
        _daemon_thread.start()
        return True
