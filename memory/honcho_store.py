"""
Honcho-backed memory — persistent peer profiles instead of raw Chroma chunks.

Peers:
  operator  — the human (preferences, habits, identity)
  glados    — the assistant
  computer  — this PC (hardware, network, software, facility scan)

Honcho reasons in the background (deriver) and exposes:
  representation()  — low-latency profile snapshot
  session.context() — prompt-ready recent history + summaries
  peer.chat()       — dialectic Q&A over the learned profile
"""
from __future__ import annotations

import os
import threading
import time
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

try:
    from honcho import Honcho  # type: ignore
except ImportError:  # pragma: no cover
    Honcho = None  # type: ignore


_DIALECTIC_HINTS = (
    "remember",
    "prefer",
    "i like",
    "i use",
    "my name",
    "who am i",
    "about me",
    "my computer",
    "this pc",
    "this machine",
    "hardware",
    "network",
    "gpu",
    "ram",
    "what do you know",
    "learn about me",
    "my setup",
    "proxmox",
    "hostname",
)

_CACHE_TTL_SEC = 45.0
_CHAT_TIMEOUT_SEC = 12.0


def _truthy(val: Any, default: bool = True) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _wants_dialectic(query: str) -> bool:
    low = (query or "").lower()
    if not low or len(low) < 8:
        return False
    return any(h in low for h in _DIALECTIC_HINTS)


class HonchoMemoryStore:
    """Thin, failure-tolerant wrapper around the honcho-ai SDK."""

    def __init__(self, cfg: Dict[str, Any]) -> None:
        self._cfg = cfg
        self._enabled = _truthy(cfg.get("memory_enable_honcho"), True)
        self.last_error: str = ""
        self._client = None
        self._user = None
        self._glados = None
        self._computer = None
        self._lock = threading.Lock()
        self._cache: Dict[str, Any] = {}
        self._cache_ts: Dict[str, float] = {}
        self._ready = False
        self._down_until = 0.0

        self.workspace_id = str(cfg.get("honcho_workspace") or "glados").strip() or "glados"
        self.user_id = str(cfg.get("honcho_user_peer") or "operator").strip() or "operator"
        self.glados_id = str(cfg.get("honcho_glados_peer") or "glados").strip() or "glados"
        self.computer_id = str(cfg.get("honcho_computer_peer") or "computer").strip() or "computer"
        self.base_url = self._resolve_base_url(cfg)
        self.api_key = (
            str(cfg.get("honcho_api_key") or os.environ.get("HONCHO_API_KEY") or "").strip()
        )

        if not self._enabled:
            self.last_error = "Honcho disabled in config"
            return
        if Honcho is None:
            self.last_error = "honcho-ai is not installed (pip install honcho-ai)"
            return
        self._connect()

    @staticmethod
    def _resolve_base_url(cfg: Dict[str, Any]) -> str:
        for name in ("HONCHO_URL", "HONCHO_BASE_URL", "HONCHO_API_URL"):
            val = (os.environ.get(name) or "").strip()
            if val:
                return val.rstrip("/")
        yaml_url = str(cfg.get("honcho_url") or "").strip()
        if yaml_url:
            return yaml_url.rstrip("/")
        key = str(cfg.get("honcho_api_key") or os.environ.get("HONCHO_API_KEY") or "").strip()
        if key:
            return "https://api.honcho.dev"
        return "http://127.0.0.1:8000"

    @property
    def enabled(self) -> bool:
        return self._enabled and self._ready

    def _connect(self) -> None:
        kwargs: Dict[str, Any] = {
            "workspace_id": self.workspace_id,
            "base_url": self.base_url,
            "timeout": 4.0,
            "max_retries": 0,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        try:
            client = Honcho(**kwargs)
            user = client.peer(self.user_id)
            glados = client.peer(self.glados_id)
            computer = client.peer(self.computer_id)
            self._client = client
            self._user = user
            self._glados = glados
            self._computer = computer
            self._ready = True
            self.last_error = ""
            self._down_until = 0.0
        except Exception as exc:
            self.last_error = f"Honcho unreachable at {self.base_url}: {exc}"
            self._ready = False
            self._client = None
            self._down_until = time.time() + 30.0

    def ping(self) -> bool:
        if not self._enabled:
            return False
        if self._ready:
            return True
        if time.time() < self._down_until:
            return False
        self._connect()
        return self._ready

    def _session(self, name: str):
        assert self._client is not None
        return self._client.session(name)

    def _daily_session(self):
        return self._session(f"glados-{date.today().isoformat()}")

    def _computer_session(self):
        return self._session("computer-state")

    def _cache_get(self, key: str) -> Optional[str]:
        ts = self._cache_ts.get(key)
        if ts is None or (time.time() - ts) > _CACHE_TTL_SEC:
            return None
        val = self._cache.get(key)
        return val if isinstance(val, str) else None

    def _cache_set(self, key: str, value: str) -> None:
        self._cache[key] = value
        self._cache_ts[key] = time.time()

    def _safe_repr(self, peer: Any, *, search_query: Optional[str] = None) -> str:
        cache_key = f"repr:{getattr(peer, 'id', '?')}:{(search_query or '')[:80]}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            kwargs: Dict[str, Any] = {"max_conclusions": 24, "include_most_frequent": True}
            if search_query:
                kwargs["search_query"] = search_query[:400]
                kwargs["search_top_k"] = 8
            text = peer.representation(**kwargs)
            out = (text or "").strip()
        except Exception as exc:
            self.last_error = f"representation failed: {exc}"
            out = ""
        if out:
            self._cache_set(cache_key, out)
        return out

    def _safe_card(self, peer: Any) -> str:
        cache_key = f"card:{getattr(peer, 'id', '?')}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            getter = getattr(peer, "get_card", None) or getattr(peer, "card", None)
            if getter is None:
                return ""
            card = getter()
            if isinstance(card, list):
                out = "\n".join(f"- {c}" for c in card if c)
            else:
                out = str(card or "").strip()
        except Exception:
            out = ""
        if out:
            self._cache_set(cache_key, out)
        return out

    def _format_session_context(self, ctx: Any) -> str:
        parts: List[str] = []
        card = getattr(ctx, "peer_card", None)
        if isinstance(card, list) and card:
            parts.append("Peer card:\n" + "\n".join(f"- {c}" for c in card if c))
        elif card:
            parts.append(str(card))
        rep = getattr(ctx, "peer_representation", None)
        if rep:
            parts.append(str(rep).strip()[:4000])
        summary = getattr(ctx, "summary", None)
        if summary:
            content = getattr(summary, "content", None) or str(summary)
            if content:
                parts.append(f"Session summary: {content}")
        messages = getattr(ctx, "messages", None) or []
        for msg in list(messages)[-10:]:
            pid = getattr(msg, "peer_id", None) or getattr(msg, "role", "") or ""
            content = str(getattr(msg, "content", "") or "").strip()
            if content:
                parts.append(f"{pid}: {content[:600]}")
        return "\n".join(p for p in parts if p).strip()

    def retrieve(
        self,
        query: str,
        *,
        conversational: bool = False,
        top_k: int = 5,
    ) -> str:
        """Prompt-ready Honcho block, or empty string if the server is down."""
        _ = top_k
        if not self.ping():
            return ""
        parts: List[str] = []
        q = (query or "").strip()

        user_card = self._safe_card(self._user)
        if user_card:
            parts.append("*** HONCHO USER CARD ***\n" + user_card)

        user_rep = self._safe_repr(self._user, search_query=q or None)
        if user_rep:
            parts.append("*** HONCHO USER PROFILE ***\n" + user_rep[:3500])

        computer_rep = self._safe_repr(self._computer, search_query=q or None)
        if computer_rep:
            parts.append("*** HONCHO COMPUTER PROFILE ***\n" + computer_rep[:3500])

        if not conversational:
            try:
                ctx = self._daily_session().context(
                    summary=True,
                    tokens=2500,
                    peer_target=self.user_id,
                    search_query=q or None,
                )
                formatted = self._format_session_context(ctx)
                if formatted:
                    parts.append("*** HONCHO SESSION ***\n" + formatted[:3500])
            except Exception as exc:
                self.last_error = f"session.context failed: {exc}"

        if (not conversational) and _wants_dialectic(q):
            try:
                answer = self._user.chat(
                    (
                        "What do you know about this operator and their computer that is "
                        f"relevant to: {q[:400]}\n"
                        "Cover preferences, hardware, network architecture, and past requests. "
                        "If you do not know, say so."
                    ),
                    reasoning_level="low",
                    timeout=_CHAT_TIMEOUT_SEC,
                )
                text = (answer if isinstance(answer, str) else str(answer or "")).strip()
                if text:
                    parts.append("*** HONCHO DIALECTIC ***\n" + text[:2500])
            except Exception as exc:
                self.last_error = f"dialectic failed: {exc}"

        return "\n\n".join(parts).strip()

    def record_turn(self, user_text: str, assistant_text: str) -> None:
        if not self.ping():
            return
        user_text = (user_text or "").strip()
        assistant_text = (assistant_text or "").strip()
        if not user_text and not assistant_text:
            return

        def _write() -> None:
            try:
                session = self._daily_session()
                msgs = []
                if user_text:
                    msgs.append(self._user.message(user_text[:8000], metadata={"event": "turn"}))
                if assistant_text:
                    msgs.append(
                        self._glados.message(assistant_text[:8000], metadata={"event": "turn"})
                    )
                if msgs:
                    session.add_messages(msgs)
            except Exception as exc:
                self.last_error = f"record_turn failed: {exc}"

        threading.Thread(target=_write, daemon=True, name="honcho-turn").start()

    def add_event(self, event: Dict[str, Any]) -> None:
        if not self.ping():
            return
        text = str(event.get("text") or "").strip()
        if not text:
            return
        source = str(event.get("source") or event.get("event_type") or "event").lower()

        def _write() -> None:
            try:
                session = self._daily_session()
                if source in ("user", "heard"):
                    msg = self._user.message(text[:8000], metadata={"event": source})
                elif source in ("glados", "assistant"):
                    msg = self._glados.message(text[:8000], metadata={"event": source})
                else:
                    msg = self._computer.message(text[:8000], metadata={"event": source})
                    session = self._computer_session()
                session.add_messages([msg])
            except Exception as exc:
                self.last_error = f"add_event failed: {exc}"

        threading.Thread(target=_write, daemon=True, name="honcho-event").start()

    def ingest_computer_facts(self, facts: Sequence[Dict[str, Any]]) -> int:
        """Push facility-scan facts to the computer peer (deduped by content hash)."""
        if not self.ping():
            return 0
        texts: List[str] = []
        by_cat: Dict[str, List[str]] = {}
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            text = str(fact.get("text") or "").strip()
            if not text:
                continue
            cat = str(fact.get("category") or "computer")
            by_cat.setdefault(cat, []).append(text)
            texts.append(text)
        if not texts:
            return 0

        import hashlib
        import json

        fingerprint = hashlib.sha1("\n".join(texts).encode("utf-8", errors="ignore")).hexdigest()
        state_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "honcho_computer_ingest.json",
        )
        try:
            if os.path.isfile(state_path):
                with open(state_path, encoding="utf-8") as fh:
                    prev = json.loads(fh.read() or "{}")
                if isinstance(prev, dict) and prev.get("fingerprint") == fingerprint:
                    return 0
        except Exception:
            pass

        chunks: List[str] = []
        for cat, lines in by_cat.items():
            body = "\n".join(f"- {ln}" for ln in lines[:40])
            chunks.append(f"Facility scan ({cat}):\n{body}"[:7000])

        def _write() -> None:
            try:
                session = self._computer_session()
                msgs = [
                    self._computer.message(chunk, metadata={"event": "facility_scan", "category": "ingest"})
                    for chunk in chunks
                ]
                # Also tell the operator peer about identity/profile facts.
                profile_lines = by_cat.get("profile") or by_cat.get("host") or []
                if profile_lines:
                    msgs.append(
                        self._user.message(
                            "Facts about me and this PC:\n" + "\n".join(f"- {x}" for x in profile_lines[:20]),
                            metadata={"event": "profile_seed"},
                        )
                    )
                session.add_messages(msgs)
                os.makedirs(os.path.dirname(state_path), exist_ok=True)
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "fingerprint": fingerprint,
                            "count": len(texts),
                            "ts": time.time(),
                        },
                        f,
                    )
            except Exception as exc:
                self.last_error = f"computer ingest failed: {exc}"

        threading.Thread(target=_write, daemon=True, name="honcho-ingest").start()
        return len(chunks)

    def profile_snapshot(self) -> Dict[str, Any]:
        """HUD / API payload — never raises."""
        out: Dict[str, Any] = {
            "enabled": self._enabled,
            "ready": self._ready,
            "url": self.base_url,
            "workspace": self.workspace_id,
            "error": self.last_error,
            "user_card": "",
            "user_profile": "",
            "computer_profile": "",
        }
        if not self.ping():
            return out
        out["user_card"] = self._safe_card(self._user)
        out["user_profile"] = self._safe_repr(self._user)[:4000]
        out["computer_profile"] = self._safe_repr(self._computer)[:4000]
        return out


_STORE: Optional[HonchoMemoryStore] = None
_STORE_LOCK = threading.Lock()


def get_honcho_store(cfg: Dict[str, Any]) -> HonchoMemoryStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = HonchoMemoryStore(cfg)
        return _STORE
