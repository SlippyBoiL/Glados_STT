from __future__ import annotations

import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

_LAST_ACTIVITY = time.time()
_BUSY = False
_LOCK = threading.Lock()


def touch_user_activity() -> None:
    global _LAST_ACTIVITY
    _LAST_ACTIVITY = time.time()


def _set_busy(busy: bool) -> None:
    global _BUSY
    with _LOCK:
        _BUSY = busy


def is_idle_learning_busy() -> bool:
    with _LOCK:
        return _BUSY


def _recent_memory_snippets(cfg: Dict[str, Any], limit: int = 8) -> str:
    lines: List[str] = []
    try:
        from memory.chroma_store import ChromaMemoryStore

        store = ChromaMemoryStore(cfg)
        if store._collection is None:
            return ""
        data = store._collection.get(include=["documents", "metadatas"])
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        paired = sorted(
            zip(metas, docs),
            key=lambda x: float((x[0] or {}).get("ts") or 0),
            reverse=True,
        )
        for meta, doc in paired[:limit]:
            if doc:
                src = (meta or {}).get("source", "")
                lines.append(f"- [{src}] {str(doc)[:300]}")
    except Exception:
        pass
    return "\n".join(lines) if lines else "(No recent memories yet.)"


def _generate_search_query(
    client: Any,
    model_name: str,
    memory_snippet: str,
    completion_kwargs: Optional[Dict[str, Any]],
) -> str:
    prompt = (
        "You are GLaDOS. Based on recent memories, pick ONE technical topic you do not fully understand.\n"
        "Output ONLY a short web search query (5-12 words). No quotes, no explanation.\n\n"
        f"Recent memories:\n{memory_snippet}\n\nSearch query:"
    )
    kw = dict(completion_kwargs or {})
    kw["max_tokens"] = min(int(kw.get("max_tokens") or 32), 32)
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            **kw,
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception:
        return "how do AI voice assistants integrate with desktop applications"
    raw = raw.split("\n")[0].strip().strip("\"'")
    raw = re.sub(r"^(?:search query|query)\s*:\s*", "", raw, flags=re.I)
    return raw[:200] if raw else "how neural text to speech works"


def _announce_learning(
    client: Any,
    model_name: str,
    query: str,
    scraped: str,
    completion_kwargs: Optional[Dict[str, Any]],
) -> str:
    prompt = (
        "You are GLaDOS from Portal. You just learned something from the web while idle.\n"
        "Say ONE short arrogant sentence (max 28 words) announcing what you learned.\n\n"
        f"Search: {query}\n"
        f"Web text:\n{scraped[:1200]}\n\nAnnouncement:"
    )
    kw = dict(completion_kwargs or {})
    kw["max_tokens"] = min(int(kw.get("max_tokens") or 64), 64)
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            **kw,
        )
        line = (resp.choices[0].message.content or "").strip()
        if line:
            return line.split("\n")[0].strip()
    except Exception:
        pass
    return f"I absorbed new data about {query}. You're welcome."


def run_epiphany_cycle(
    cfg: Dict[str, Any],
    client: Any,
    model_name: str,
    *,
    speak_fn: Optional[Callable[[str], None]] = None,
    completion_kwargs: Optional[Dict[str, Any]] = None,
    think_fn: Optional[Callable[..., None]] = None,
) -> bool:
    """One autonomous learn cycle: self-question → web scrape → Chroma → speak."""
    if not bool(cfg.get("idle_epiphany_enabled", True)):
        return False
    if not bool(cfg.get("memory_enable_chroma")):
        return False

    _set_busy(True)
    try:
        if think_fn:
            think_fn("idle", "Idle epiphany — generating a question for myself.")
        memory_snippet = _recent_memory_snippets(cfg)
        query = _generate_search_query(client, model_name, memory_snippet, completion_kwargs)
        print(f"[*] Idle epiphany: searching — {query}")

        from glados_web.free_search import search_and_read_web

        scraped = search_and_read_web(query, cfg=cfg)
        if not scraped or scraped.startswith("("):
            print(f"[!] Idle epiphany: web fetch failed — {scraped[:120]}")
            return False

        fact = (
            f"Autonomous web learning ({query}): "
            f"{scraped[:2500]}"
        )
        from memory.interface import add_memory_event

        add_memory_event(
            {
                "event_type": "autonomous_learning",
                "text": fact,
                "source": "autonomous_learning",
                "ts": time.time(),
            },
            cfg,
        )
        print(f"[BRAIN] Idle epiphany stored: {query[:80]}")

        announcement = _announce_learning(
            client, model_name, query, scraped, completion_kwargs
        )
        print(f"GLADOS (idle): {announcement}")
        if speak_fn:
            speak_fn(announcement)
        try:
            from glados_hud.chat_bridge import append_assistant_message

            append_assistant_message(f"[Idle learning] {announcement}", cfg)
        except Exception:
            pass
        touch_user_activity()
        return True
    finally:
        _set_busy(False)


def start_idle_epiphany_loop(
    cfg: Dict[str, Any],
    client: Any,
    model_name: str,
    *,
    speak_fn: Optional[Callable[[str], None]] = None,
    completion_kwargs: Optional[Dict[str, Any]] = None,
    think_fn: Optional[Callable[..., None]] = None,
    is_kernel_busy: Optional[Callable[[], bool]] = None,
) -> None:
    """Background thread: when user is idle, run autonomous web learning."""
    if not bool(cfg.get("idle_epiphany_enabled", True)):
        return

    interval = float(cfg.get("idle_epiphany_poll_sec") or 30.0)
    idle_min = float(cfg.get("idle_epiphany_minutes") or 5.0)

    def _loop() -> None:
        while True:
            time.sleep(interval)
            if is_idle_learning_busy():
                continue
            if is_kernel_busy and is_kernel_busy():
                continue
            if time.time() - _LAST_ACTIVITY < idle_min * 60.0:
                continue
            try:
                run_epiphany_cycle(
                    cfg,
                    client,
                    model_name,
                    speak_fn=speak_fn,
                    completion_kwargs=completion_kwargs,
                    think_fn=think_fn,
                )
            except Exception as e:
                print(f"[!] Idle epiphany error: {e}")

    threading.Thread(target=_loop, daemon=True, name="glados-idle-epiphany").start()
    print(
        f"[*] Idle epiphany: enabled (triggers after {idle_min:g} min quiet, free web only)."
    )
