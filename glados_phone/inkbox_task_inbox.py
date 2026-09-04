"""Poll Inkbox SMS / iMessage / mail / call action items for Voice AI PC tasks.

Inkbox Voice AI cannot send Telegram. It texts or emails a ``GLADOS_TASK:``
command. This daemon turns those messages into GLaDOS prompts and mirrors
them onto Telegram so the operator sees the same request there.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

_daemon_lock = threading.Lock()
_daemon_thread: Optional[threading.Thread] = None
_daemon_stop = threading.Event()

_PREFIX_RE = re.compile(
    r"^\s*(?:\[?glados_task\]?|glados\s*task|glados)\s*[:\-]\s*",
    re.IGNORECASE,
)
_SUBJECT_RE = re.compile(r"glados", re.IGNORECASE)


def _state_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "inkbox_task_inbox_state.json")


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"seen": [], "recent": [], "primed": False}


def _save_state(state: Dict[str, Any]) -> None:
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    seen = list(state.get("seen") or [])[-500:]
    recent = list(state.get("recent") or [])[-80:]
    payload = {
        "seen": seen,
        "recent": recent,
        "primed": bool(state.get("primed")),
        "updated_at": time.time(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def extract_task_text(*parts: str) -> str:
    """Return a PC command if the Voice AI tagged it for GLaDOS."""
    chunks = [str(p or "").strip() for p in parts if str(p or "").strip()]
    if not chunks:
        return ""
    blob = "\n".join(chunks)
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        if _PREFIX_RE.match(line):
            return _PREFIX_RE.sub("", line, count=1).strip()
    subject = chunks[0]
    if _SUBJECT_RE.search(subject) and len(chunks) > 1:
        rest = "\n".join(chunks[1:]).strip()
        return _PREFIX_RE.sub("", rest, count=1).strip() or rest
    return ""


def _task_key(text: str) -> str:
    norm = re.sub(r"\s+", " ", (text or "").strip().lower())
    return hashlib.sha1(norm.encode("utf-8", errors="replace")).hexdigest()[:16]


def _remember(state: Dict[str, Any], seen_id: str, task_key: str) -> bool:
    """True if this id/text is new enough to execute."""
    seen: List[str] = list(state.setdefault("seen", []))
    if seen_id in seen:
        return False
    seen.append(seen_id)
    state["seen"] = seen[-500:]
    now = time.time()
    recent = [
        row
        for row in (state.get("recent") or [])
        if isinstance(row, dict) and now - float(row.get("ts") or 0) < 120
    ]
    if any(row.get("key") == task_key for row in recent):
        state["recent"] = recent
        return False
    recent.append({"key": task_key, "ts": now})
    state["recent"] = recent[-80:]
    return True


def _collect_tasks(identity: Any) -> List[Dict[str, str]]:
    found: List[Dict[str, str]] = []
    try:
        for msg in identity.list_texts(limit=20) or []:
            body = str(getattr(msg, "text", "") or "")
            task = extract_task_text(body)
            if not task:
                continue
            found.append(
                {"id": f"sms:{getattr(msg, 'id', '')}", "text": task, "via": "sms"}
            )
    except Exception:
        pass
    try:
        for msg in identity.list_imessages(limit=20) or []:
            body = str(getattr(msg, "content", "") or "")
            task = extract_task_text(body)
            if not task:
                continue
            found.append(
                {
                    "id": f"imsg:{getattr(msg, 'id', '')}",
                    "text": task,
                    "via": "imessage",
                }
            )
    except Exception:
        pass
    try:
        n = 0
        for msg in identity.iter_emails(page_size=20) or []:
            n += 1
            if n > 20:
                break
            subject = str(getattr(msg, "subject", "") or "")
            snippet = str(getattr(msg, "snippet", "") or "")
            task = extract_task_text(subject, snippet)
            if not task:
                continue
            found.append(
                {
                    "id": f"mail:{getattr(msg, 'id', '')}",
                    "text": task,
                    "via": "email",
                }
            )
    except Exception:
        pass
    try:
        for call in identity.list_calls(limit=8) or []:
            items = getattr(call, "post_call_action_items", None) or []
            for item in items:
                action = str(getattr(item, "action", "") or "")
                details = str(getattr(item, "details", "") or "")
                task = extract_task_text(action, details)
                if not task:
                    continue
                found.append(
                    {
                        "id": f"callitem:{getattr(item, 'id', '')}",
                        "text": task,
                        "via": "call-action",
                    }
                )
    except Exception:
        pass
    return found


def _dispatch(task: Dict[str, str], cfg: Optional[Dict[str, Any]]) -> Optional[str]:
    text = str(task.get("text") or "").strip()
    if not text:
        return None
    via = str(task.get("via") or "inkbox")
    notice = f"Voice AI asked me to: {text}"
    chat_id = None
    try:
        from glados_phone.telegram_bridge import send_telegram_message, telegram_config

        conf = telegram_config(cfg)
        chat_id = conf.get("home_chat_id")
        send_telegram_message(notice, chat_id=chat_id, cfg=cfg)
    except Exception:
        chat_id = None
    try:
        from glados_hud.chat_bridge import enqueue_user_message
    except Exception:
        return None
    mid = enqueue_user_message(
        text,
        cfg,
        source="voice-ai",
        telegram_chat_id=chat_id,
    )
    if mid:
        print(f"[*] Voice AI ({via}) → GLaDOS: {text[:120]}")
    return mid


def poll_inkbox_tasks(cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    from glados_phone.inkbox_call import DEFAULT_INKBOX_API, inkbox_config
    from inkbox import Inkbox

    state = _load_state()
    primed = bool(state.get("primed"))
    conf = inkbox_config(cfg)
    if not conf.get("api_key"):
        return []
    kwargs: Dict[str, Any] = {"api_key": conf["api_key"]}
    if conf["base_url"] and conf["base_url"] != DEFAULT_INKBOX_API:
        kwargs["base_url"] = conf["base_url"]
    dispatched: List[Dict[str, str]] = []
    try:
        with Inkbox(**kwargs) as client:
            identity = client.get_identity(conf["handle"])
            try:
                identity.refresh()
            except Exception:
                pass
            tasks = _collect_tasks(identity)
            for task in tasks:
                sid = str(task.get("id") or "")
                text = str(task.get("text") or "").strip()
                if not sid or not text:
                    continue
                if not primed:
                    seen = list(state.setdefault("seen", []))
                    if sid not in seen:
                        seen.append(sid)
                        state["seen"] = seen[-500:]
                    continue
                if not _remember(state, sid, _task_key(text)):
                    continue
                if _dispatch(task, cfg):
                    dispatched.append(task)
            state["primed"] = True
            _save_state(state)
            return dispatched
    except Exception as exc:
        print(f"[!] Inkbox task inbox error: {exc}")
        return []


def start_inkbox_task_inbox_daemon(cfg: Optional[Dict[str, Any]] = None) -> bool:
    global _daemon_thread
    cfg = cfg or {}
    env = str(os.environ.get("INKBOX_TASK_INBOX_ENABLED") or "").strip().lower()
    enabled = bool(cfg.get("inkbox_task_inbox_enabled", True))
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

        def _loop() -> None:
            poll_sec = float(
                os.environ.get("INKBOX_TASK_INBOX_POLL_SEC")
                or cfg.get("inkbox_task_inbox_poll_sec")
                or 6
            )
            poll_sec = max(3.0, poll_sec)
            try:
                from glados_phone.inkbox_call import apply_voice_ai_dispatch_config

                apply_voice_ai_dispatch_config(cfg)
            except Exception as exc:
                print(f"[!] Voice AI dispatch config: {exc}")
            print(
                f"[*] Voice AI → GLaDOS inbox online. "
                f"On a call, ask it to text GLaDOS the PC task. Poll every {poll_sec:.0f}s."
            )
            if _daemon_stop.wait(2.0):
                return
            while not _daemon_stop.is_set():
                try:
                    poll_inkbox_tasks(cfg)
                except Exception as exc:
                    print(f"[!] Inkbox task poll failed: {exc}")
                if _daemon_stop.wait(poll_sec):
                    break

        _daemon_thread = threading.Thread(
            target=_loop, name="inkbox-task-inbox", daemon=True
        )
        _daemon_thread.start()
        return True
