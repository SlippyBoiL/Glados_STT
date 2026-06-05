from __future__ import annotations

import contextlib
import json
import os
import threading
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional

from glados_paths import resolve_plugins_dir

_lock = threading.Lock()


@contextlib.contextmanager
def _inbox_exclusive(path: str) -> Iterator[None]:
    """Lock shared by brain_server and KernelLamma — threading.Lock is per-process only."""
    lock_path = path + ".lock"
    fd: Optional[int] = None
    for _ in range(600):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.01)
    else:
        raise TimeoutError(f"inbox lock timeout: {path}")
    try:
        with _lock:
            yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            os.unlink(lock_path)
        except OSError:
            pass


def _plugins_dir(cfg: Optional[Dict[str, Any]] = None) -> str:
    return resolve_plugins_dir(cfg)


def inbox_path(cfg: Optional[Dict[str, Any]] = None) -> str:
    return os.path.join(_plugins_dir(cfg), "hud_chat_inbox.jsonl")


def history_path(cfg: Optional[Dict[str, Any]] = None) -> str:
    return os.path.join(_plugins_dir(cfg), "hud_chat_history.jsonl")


def enqueue_user_message(text: str, cfg: Optional[Dict[str, Any]] = None) -> str:
    """HUD → kernel: queue a message for Glados to process."""
    msg_id = str(uuid.uuid4())[:12]
    line = {
        "id": msg_id,
        "role": "user",
        "text": (text or "").strip(),
        "ts": time.time(),
        "status": "pending",
        "source": "hud",
    }
    if not line["text"]:
        return ""
    path = inbox_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _inbox_exclusive(path):
        _release_stuck_processing(path, max_age_sec=15.0)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        _append_history_unlocked(line, cfg)
    return msg_id


def _release_stuck_processing(path: str, *, max_age_sec: float = 15.0) -> int:
    """If the kernel died mid-turn, unblock the inbox so new HUD messages can be picked."""
    if not os.path.isfile(path):
        return 0
    now = time.time()
    n = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    except Exception:
        return 0
    out: List[str] = []
    for ln in lines:
        try:
            obj = json.loads(ln)
        except Exception:
            out.append(ln)
            continue
        if obj.get("status") == "processing":
            age = now - float(obj.get("ts") or 0)
            if age >= max_age_sec:
                obj["status"] = "pending"
                n += 1
        out.append(json.dumps(obj, ensure_ascii=False))
    if n:
        with open(path, "w", encoding="utf-8") as f:
            for ln in out:
                f.write(ln + "\n")
    return n


def recover_inbox_on_startup(cfg: Optional[Dict[str, Any]] = None) -> int:
    """Reset stuck 'processing' rows so HUD messages work after a crash or restart."""
    path = inbox_path(cfg)
    if not os.path.isfile(path):
        return 0
    n = 0
    with _inbox_exclusive(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        except Exception:
            return 0
        out: List[str] = []
        for ln in lines:
            try:
                obj = json.loads(ln)
            except Exception:
                out.append(ln)
                continue
            if obj.get("status") == "processing":
                obj["status"] = "pending"
                n += 1
            out.append(json.dumps(obj, ensure_ascii=False))
        with open(path, "w", encoding="utf-8") as f:
            for ln in out:
                f.write(ln + "\n")
    return n


def mark_message_done(msg_id: str, cfg: Optional[Dict[str, Any]] = None) -> None:
    if not msg_id:
        return
    path = inbox_path(cfg)
    if not os.path.isfile(path):
        return
    with _inbox_exclusive(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        except Exception:
            return
        out: List[str] = []
        for ln in lines:
            try:
                obj = json.loads(ln)
            except Exception:
                out.append(ln)
                continue
            if obj.get("id") == msg_id:
                obj["status"] = "done"
            if obj.get("status") == "done":
                continue
            out.append(json.dumps(obj, ensure_ascii=False))
        with open(path, "w", encoding="utf-8") as f:
            for ln in out:
                f.write(ln + "\n")


def pop_pending_message(
    cfg: Optional[Dict[str, Any]] = None,
    *,
    stale_processing_sec: float = 600.0,
) -> tuple[Optional[str], Optional[str]]:
    """Kernel: take oldest pending (or stale processing) HUD message. Returns (text, msg_id)."""
    path = inbox_path(cfg)
    if not os.path.isfile(path):
        return None, None
    now = time.time()
    with _inbox_exclusive(path):
        _release_stuck_processing(path, max_age_sec=15.0)
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        except Exception:
            return None, None
        objs: List[dict] = []
        for ln in lines:
            try:
                o = json.loads(ln)
                if isinstance(o, dict):
                    objs.append(o)
            except Exception:
                continue

        pick_idx: Optional[int] = None
        for i, obj in enumerate(objs):
            if obj.get("role") != "user":
                continue
            st = obj.get("status")
            if st == "pending":
                pick_idx = i
                break
            if st == "processing":
                age = now - float(obj.get("ts") or 0)
                if age >= stale_processing_sec:
                    pick_idx = i
                    break

        if pick_idx is None:
            return None, None

        chosen = objs[pick_idx]
        chosen["status"] = "processing"
        chosen["ts"] = now
        text = str(chosen.get("text") or "").strip()
        msg_id = str(chosen.get("id") or "")
        remaining: List[str] = []
        for j, obj in enumerate(objs):
            if j == pick_idx:
                remaining.append(json.dumps(chosen, ensure_ascii=False))
            elif obj.get("status") != "done":
                remaining.append(json.dumps(obj, ensure_ascii=False))
        with open(path, "w", encoding="utf-8") as f:
            for ln in remaining:
                f.write(ln + "\n")
    return (text if text else None), (msg_id if msg_id else None)


def append_user_message(text: str, cfg: Optional[Dict[str, Any]] = None, *, source: str = "terminal") -> None:
    line = {
        "id": str(uuid.uuid4())[:12],
        "role": "user",
        "text": (text or "").strip(),
        "ts": time.time(),
        "source": source,
    }
    if line["text"]:
        _append_history(line, cfg)


def append_assistant_message(text: str, cfg: Optional[Dict[str, Any]] = None) -> None:
    line = {
        "id": str(uuid.uuid4())[:12],
        "role": "assistant",
        "text": (text or "").strip(),
        "ts": time.time(),
    }
    if line["text"]:
        _append_history(line, cfg)


def _append_history_unlocked(line: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> None:
    path = history_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def _append_history(line: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> None:
    with _lock:
        _append_history_unlocked(line, cfg)


def read_history(limit: int = 200, cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    path = history_path(cfg)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for raw in lines[-max(1, limit) :]:
        try:
            obj = json.loads(raw.strip())
            if not isinstance(obj, dict):
                continue
            role = str(obj.get("role") or "")
            text = str(obj.get("text") or "").strip()
            if role not in ("user", "assistant") or not text:
                continue
            out.append(obj)
        except Exception:
            continue
    return out
