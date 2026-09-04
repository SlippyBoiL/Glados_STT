from __future__ import annotations

import contextlib
import json
import os
import sys
import threading
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional

from glados_paths import resolve_plugins_dir

_lock = threading.Lock()
_POPPED_META: Dict[str, Dict[str, Any]] = {}

# Cross-process inbox lock (brain_server + kernel). Held briefly; stale locks are reclaimed.
_INBOX_LOCK_STALE_SEC = 4.0
_INBOX_LOCK_WAIT_SEC = 8.0


def _pid_alive(pid: int) -> bool:
    """Return True if ``pid`` is a running process (Windows-safe)."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def clear_inbox_lock_file(cfg: Optional[Dict[str, Any]] = None) -> bool:
    """Drop orphan inbox lock (safe at kernel boot)."""
    lock_path = inbox_path(cfg) + ".lock"
    return _clear_stale_inbox_lock(lock_path, max_age_sec=0)


def _clear_stale_inbox_lock(lock_path: str, max_age_sec: float = _INBOX_LOCK_STALE_SEC) -> bool:
    """Remove orphan .lock files from crashed processes or force-clear when stuck."""
    if not os.path.isfile(lock_path):
        return False
    try:
        age = time.time() - os.path.getmtime(lock_path)
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                raw = (f.read() or "").strip()
        except Exception:
            raw = ""
        if not raw:
            os.unlink(lock_path)
            return True
        if raw.isdigit():
            pid = int(raw)
            if _pid_alive(pid) and max_age_sec > 0 and age < max_age_sec:
                return False
        if max_age_sec > 0 and age < max_age_sec:
            return False
        os.unlink(lock_path)
        return True
    except OSError:
        return False


def _acquire_inbox_lock_fd(lock_path: str) -> int:
    """Cross-process mutex using the lock file (Windows-safe; no O_EXCL orphans)."""
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
    except Exception:
        pass
    if sys.platform == "win32":
        import msvcrt

        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            os.close(fd)
            raise
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _release_inbox_lock_fd(fd: Optional[int]) -> None:
    if fd is None:
        return
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass


@contextlib.contextmanager
def _inbox_exclusive(path: str) -> Iterator[None]:
    """File lock shared by brain_server and KernelLamma (separate processes)."""
    lock_path = path + ".lock"
    fd: Optional[int] = None
    deadline = time.time() + _INBOX_LOCK_WAIT_SEC
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        _clear_stale_inbox_lock(lock_path)
        try:
            fd = _acquire_inbox_lock_fd(lock_path)
            break
        except OSError as exc:
            last_err = exc
            if fd is not None:
                _release_inbox_lock_fd(fd)
                fd = None
            time.sleep(0.03)
    else:
        _clear_stale_inbox_lock(lock_path, max_age_sec=0)
        try:
            fd = _acquire_inbox_lock_fd(lock_path)
        except OSError as exc:
            raise TimeoutError(f"inbox lock timeout: {path}") from (last_err or exc)
    try:
        with _lock:
            yield
    finally:
        _release_inbox_lock_fd(fd)


def _plugins_dir(cfg: Optional[Dict[str, Any]] = None) -> str:
    return resolve_plugins_dir(cfg)


def inbox_path(cfg: Optional[Dict[str, Any]] = None) -> str:
    return os.path.join(_plugins_dir(cfg), "hud_chat_inbox.jsonl")


def history_path(cfg: Optional[Dict[str, Any]] = None) -> str:
    return os.path.join(_plugins_dir(cfg), "hud_chat_history.jsonl")


def session_path(cfg: Optional[Dict[str, Any]] = None) -> str:
    return os.path.join(_plugins_dir(cfg), "hud_chat_session.json")


def read_session(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Current chat session marker (set on each kernel boot)."""
    path = session_path(cfg)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def clear_chat_on_startup(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Fresh chat UI each boot — clears HUD inbox/history files only.
    Does NOT touch ChromaDB, shared brain, skills, or static memory.
    """
    cfg = cfg or {}
    session_ts = time.time()
    boot_id = str(uuid.uuid4())[:8]
    cleared_history = 0
    cleared_inbox = 0

    hist = history_path(cfg)
    inb = inbox_path(cfg)
    os.makedirs(os.path.dirname(hist), exist_ok=True)

    if os.path.isfile(hist):
        try:
            with open(hist, "r", encoding="utf-8") as f:
                cleared_history = sum(1 for ln in f if ln.strip())
        except Exception:
            pass
    with open(hist, "w", encoding="utf-8"):
        pass

    # Boot-time only — drop stale inbox lock from a crashed process, then truncate.
    lock_path = inb + ".lock"
    try:
        if os.path.isfile(lock_path):
            os.unlink(lock_path)
    except OSError:
        pass
    if os.path.isfile(inb):
        try:
            with open(inb, "r", encoding="utf-8") as f:
                cleared_inbox = sum(1 for ln in f if ln.strip())
        except Exception:
            pass
    with open(inb, "w", encoding="utf-8"):
        pass

    sess = {
        "session_started_at": session_ts,
        "boot_id": boot_id,
        "cleared_history_lines": cleared_history,
        "cleared_inbox_lines": cleared_inbox,
    }
    with _lock:
        with open(session_path(cfg), "w", encoding="utf-8") as f:
            json.dump(sess, f, ensure_ascii=False)

    return sess

def enqueue_user_message(
    text: str,
    cfg: Optional[Dict[str, Any]] = None,
    *,
    source: str = "hud",
    telegram_chat_id: Any = None,
    telegram_message_id: Any = None,
) -> str:
    """HUD / SMS / Telegram / Voice AI → kernel: queue a message for Glados to process."""
    msg_id = str(uuid.uuid4())[:12]
    line = {
        "id": msg_id,
        "role": "user",
        "text": (text or "").strip(),
        "ts": time.time(),
        "status": "pending",
        "source": (source or "hud").strip() or "hud",
    }
    if telegram_chat_id is not None and str(telegram_chat_id).strip() != "":
        line["telegram_chat_id"] = telegram_chat_id
    if telegram_message_id is not None and str(telegram_message_id).strip() != "":
        line["telegram_message_id"] = telegram_message_id
    if not line["text"]:
        return ""
    path = inbox_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with _inbox_exclusive(path):
            _release_stuck_processing(path, max_age_sec=15.0)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
            _append_history_unlocked(line, cfg)
    except TimeoutError:
        print(f"[!] HUD inbox busy — could not queue message (lock timeout on {path})")
        return ""
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
    clear_inbox_lock_file(cfg)
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
    stale_processing_sec: float = 45.0,
) -> tuple[Optional[str], Optional[str]]:
    """Kernel: take oldest pending (or stale processing) HUD message. Returns (text, msg_id)."""
    path = inbox_path(cfg)
    if not os.path.isfile(path):
        return None, None
    now = time.time()
    try:
        with _inbox_exclusive(path):
            _release_stuck_processing(path, max_age_sec=20.0)
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
            if msg_id:
                _POPPED_META[msg_id] = {
                    "source": str(chosen.get("source") or "hud"),
                    "telegram_chat_id": chosen.get("telegram_chat_id"),
                    "telegram_message_id": chosen.get("telegram_message_id"),
                }
                if len(_POPPED_META) > 40:
                    extra = list(_POPPED_META.keys())[:-20]
                    for key in extra:
                        _POPPED_META.pop(key, None)
            return (text if text else None), (msg_id if msg_id else None)
    except TimeoutError:
        print(f"[!] HUD inbox lock timeout while reading {path}")
        return None, None


def get_popped_meta(msg_id: Optional[str]) -> Dict[str, Any]:
    """Reply routing for the inbox row the kernel just claimed."""
    if not msg_id:
        return {}
    meta = _POPPED_META.get(msg_id) or {}
    return dict(meta)


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


def append_assistant_message(text: str, cfg: Optional[Dict[str, Any]] = None) -> str:
    msg_id = str(uuid.uuid4())[:12]
    line = {
        "id": msg_id,
        "role": "assistant",
        "text": (text or "").strip(),
        "ts": time.time(),
    }
    if line["text"]:
        _append_history(line, cfg)
        return msg_id
    return ""


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
