"""Telegram bot inbox + replies for GLaDOS.

Voice AI cannot talk to Telegram itself. GLaDOS owns the bot:
  - Operator (or a mirrored Voice AI task) texts the bot → kernel prompt
  - After a turn, GLaDOS replies in that Telegram chat

Token is read from the environment or Hermes ``%LOCALAPPDATA%\\hermes\\.env``.
Never print the token.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from typing import Any, Dict, List, Optional, Set

_API = "https://api.telegram.org"
_daemon_lock = threading.Lock()
_daemon_thread: Optional[threading.Thread] = None
_daemon_stop = threading.Event()


def _state_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "telegram_inbox_state.json")


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_state(state: Dict[str, Any]) -> None:
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = dict(state)
    tmp["updated_at"] = time.time()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tmp, f)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def telegram_config(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or {}
    try:
        from glados_phone.inkbox_call import load_hermes_env

        load_hermes_env("TELEGRAM_")
    except Exception:
        pass
    raw_users = str(
        os.environ.get("TELEGRAM_ALLOWED_USERS")
        or cfg.get("telegram_allowed_users")
        or ""
    )
    allowed: Set[int] = set()
    for part in raw_users.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            allowed.add(int(part))
    home = str(
        os.environ.get("TELEGRAM_HOME_CHANNEL")
        or cfg.get("telegram_home_channel")
        or ""
    ).strip()
    home_id: Optional[int] = None
    if home.lstrip("-").isdigit():
        home_id = int(home)
        allowed.add(home_id)
    return {
        "token": str(
            os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.get("telegram_bot_token") or ""
        ).strip(),
        "allowed_users": allowed,
        "allow_all": _truthy(
            os.environ.get("TELEGRAM_ALLOW_ALL_USERS")
            or cfg.get("telegram_allow_all_users")
            or False
        ),
        "home_chat_id": home_id,
    }


def _api(token: str, method: str, payload: Optional[Dict[str, Any]] = None, *, timeout: int = 30) -> Dict[str, Any]:
    url = f"{_API}/bot{token}/{method}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        obj = json.loads(raw)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def send_telegram_message(
    text: str,
    *,
    chat_id: Optional[int] = None,
    reply_to_message_id: Optional[int] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> bool:
    conf = telegram_config(cfg)
    token = conf["token"]
    dest = chat_id or conf["home_chat_id"]
    body = (text or "").strip()
    if not token or dest is None or not body:
        return False
    if len(body) > 3900:
        body = body[:3890] + "…"
    payload: Dict[str, Any] = {
        "chat_id": dest,
        "text": body,
        "disable_web_page_preview": True,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = int(reply_to_message_id)
    try:
        obj = _api(token, "sendMessage", payload, timeout=20)
        return bool(obj.get("ok"))
    except Exception as exc:
        print(f"[!] Telegram send failed: {exc}")
        return False


def deliver_glados_reply(
    text: str,
    meta: Optional[Dict[str, Any]] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> bool:
    """Send GLaDOS's spoken/HUD reply back to the Telegram chat that tasked her."""
    meta = meta or {}
    chat_id = meta.get("telegram_chat_id")
    try:
        chat_id = int(chat_id) if chat_id is not None and str(chat_id).lstrip("-").isdigit() else None
    except Exception:
        chat_id = None
    mid = meta.get("telegram_message_id")
    try:
        mid_i = int(mid) if mid is not None else None
    except Exception:
        mid_i = None
    if chat_id is None:
        source = str(meta.get("source") or "")
        if source in ("telegram", "voice-ai", "inkbox"):
            chat_id = telegram_config(cfg).get("home_chat_id")
    if chat_id is None:
        return False
    return send_telegram_message(
        text,
        chat_id=chat_id,
        reply_to_message_id=mid_i,
        cfg=cfg,
    )


def _sender_allowed(conf: Dict[str, Any], user_id: Optional[int], chat_id: Optional[int]) -> bool:
    if conf["allow_all"]:
        return True
    allowed: Set[int] = conf["allowed_users"]
    if not allowed:
        return False
    if user_id is not None and user_id in allowed:
        return True
    if chat_id is not None and chat_id in allowed:
        return True
    return False


def _message_text(msg: Dict[str, Any]) -> str:
    if not isinstance(msg, dict):
        return ""
    for key in ("text", "caption"):
        val = msg.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def poll_telegram_commands(
    cfg: Optional[Dict[str, Any]] = None,
    *,
    enqueue: bool = True,
) -> List[Dict[str, Any]]:
    conf = telegram_config(cfg)
    token = conf["token"]
    if not token:
        return []
    state = _load_state()
    offset = int(state.get("offset") or 0)
    primed = bool(state.get("primed"))
    try:
        obj = _api(
            token,
            "getUpdates",
            {
                "offset": offset,
                "timeout": 0 if not primed else 20,
                "allowed_updates": ["message", "edited_message"],
            },
            timeout=25,
        )
    except Exception as exc:
        print(f"[!] Telegram poll failed: {exc}")
        return []
    if not obj.get("ok"):
        desc = str(obj.get("description") or "getUpdates failed")
        print(f"[!] Telegram API: {desc}")
        return []
    results = obj.get("result") or []
    out: List[Dict[str, Any]] = []
    max_id = offset
    for upd in results:
        if not isinstance(upd, dict):
            continue
        uid = int(upd.get("update_id") or 0)
        if uid >= max_id:
            max_id = uid + 1
        if not primed:
            continue
        msg = upd.get("message") or upd.get("edited_message") or {}
        if not isinstance(msg, dict):
            continue
        text = _message_text(msg)
        if not text:
            continue
        chat = msg.get("chat") or {}
        sender = msg.get("from") or {}
        try:
            chat_id = int(chat.get("id"))
        except Exception:
            continue
        try:
            user_id = int(sender.get("id")) if sender.get("id") is not None else None
        except Exception:
            user_id = None
        if not _sender_allowed(conf, user_id, chat_id):
            print("[!] Telegram ignored a message from an unauthorized sender")
            continue
        item = {
            "text": text,
            "telegram_chat_id": chat_id,
            "telegram_message_id": msg.get("message_id"),
            "source": "telegram",
        }
        out.append(item)
        if enqueue:
            _enqueue(item, cfg)
    state["offset"] = max_id
    state["primed"] = True
    _save_state(state)
    return out


def _enqueue(item: Dict[str, Any], cfg: Optional[Dict[str, Any]]) -> Optional[str]:
    text = str(item.get("text") or "").strip()
    if not text:
        return None
    try:
        from glados_hud.chat_bridge import enqueue_user_message
    except Exception:
        return None
    mid = enqueue_user_message(
        text,
        cfg,
        source=str(item.get("source") or "telegram"),
        telegram_chat_id=item.get("telegram_chat_id"),
        telegram_message_id=item.get("telegram_message_id"),
    )
    if mid:
        print(f"[*] Telegram → GLaDOS: {text[:120]}")
    return mid


def start_telegram_inbox_daemon(cfg: Optional[Dict[str, Any]] = None) -> bool:
    global _daemon_thread
    cfg = cfg or {}
    env = str(os.environ.get("TELEGRAM_INBOX_ENABLED") or "").strip().lower()
    enabled = bool(cfg.get("telegram_inbox_enabled", True))
    if env in ("0", "false", "no", "off"):
        enabled = False
    if env in ("1", "true", "yes", "on"):
        enabled = True
    if not enabled:
        return False
    conf = telegram_config(cfg)
    if not conf["token"]:
        print("[!] Telegram inbox skipped — no TELEGRAM_BOT_TOKEN in env or Hermes .env")
        return False
    if not conf["allow_all"] and not conf["allowed_users"]:
        print("[!] Telegram inbox skipped — set TELEGRAM_ALLOWED_USERS")
        return False

    with _daemon_lock:
        if _daemon_thread and _daemon_thread.is_alive():
            return True
        _daemon_stop.clear()

        def _loop() -> None:
            print(
                "[*] Telegram inbox online — Voice AI / you can text GLaDOS here. "
                "Do not also run the Hermes Telegram gateway on this same bot."
            )
            try:
                poll_telegram_commands(cfg, enqueue=False)
            except Exception as exc:
                print(f"[!] Telegram prime failed: {exc}")
            while not _daemon_stop.is_set():
                try:
                    poll_telegram_commands(cfg, enqueue=True)
                except Exception as exc:
                    print(f"[!] Telegram inbox error: {exc}")
                    if _daemon_stop.wait(5.0):
                        break

        _daemon_thread = threading.Thread(target=_loop, name="telegram-inbox", daemon=True)
        _daemon_thread.start()
        return True
