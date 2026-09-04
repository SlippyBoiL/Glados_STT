# DESCRIPTION: Central ChromaDB semantic memory shared across all swarm agents.
# --- GLADOS PLUGIN: shared_memory.py ---

from __future__ import annotations

import hashlib
import os
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

try:
    import chromadb  # type: ignore
except ImportError:
    chromadb = None  # type: ignore

SHARED_COLLECTION = "glados_shared_brain"

SHARED_BRAIN_DIRECTIVE = (
    "Before executing any code, script, or configuration, you MUST use `query_brain` "
    "to check if another agent has recorded insights or fixes regarding this task. "
    "Upon completing a successful fix or learning a new system attribute, you MUST use "
    "`remember_insight` to log it for the swarm."
)

_lock = threading.Lock()
_store: Optional["SharedBrain"] = None
_cfg: Optional[Dict[str, Any]] = None
_telemetry_path: str = ""
_telemetry_log_fn: Optional[Callable[..., None]] = None


class SharedBrain:
    """ChromaDB vector store for cross-agent swarm insights."""

    def __init__(self, cfg: Dict[str, Any]) -> None:
        self._cfg = cfg
        self._enabled = bool(cfg.get("memory_enable_chroma", True))
        self._persist_dir = str(cfg.get("chroma_persist_dir") or "chroma_db")
        self._collection_name = str(
            cfg.get("shared_brain_collection") or SHARED_COLLECTION
        )
        self.last_error: str = ""
        self._client = None
        self._collection = None

        if not self._enabled or chromadb is None:
            if chromadb is None:
                self.last_error = "chromadb not installed"
            return

        try:
            os.makedirs(self._persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self._persist_dir)  # type: ignore[attr-defined]
            try:
                self._collection = self._client.get_collection(self._collection_name)
            except Exception:
                self._collection = self._client.create_collection(self._collection_name)
        except BaseException as exc:  # noqa: BLE001
            # chromadb's Rust backend raises pyo3 PanicException (a BaseException) on an
            # incompatible on-disk store; degrade instead of crashing the swarm brain.
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            self.last_error = str(exc)
            self._client = None
            self._collection = None

    def _embed_one(self, text: str) -> Optional[List[float]]:
        from glados_llm import embed_texts

        results = embed_texts(self._cfg, [text])
        emb = results[0] if results else None
        if emb is None:
            self.last_error = "embedding failed"
        else:
            self.last_error = ""
        return emb

    def remember_insight(
        self,
        insight_text: str,
        tags: Optional[Union[Sequence[str], str]] = None,
        *,
        sender_agent: str = "MANAGER",
    ) -> Dict[str, Any]:
        text = (insight_text or "").strip()
        if not text:
            return {"ok": False, "error": "insight_text is required"}

        tag_list = _normalize_tags(tags)
        ts = time.time()
        meta = {
            "sender_agent": str(sender_agent or "MANAGER"),
            "tags": ",".join(tag_list),
            "ts": float(ts),
            "timestamp": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
        }

        if self._collection is None:
            return {"ok": False, "error": self.last_error or "shared brain unavailable"}

        emb = self._embed_one(text)
        if emb is None:
            return {"ok": False, "error": self.last_error or "embedding failed"}

        doc_id = f"{int(ts)}-{hashlib.sha1(text.encode('utf-8', errors='ignore')).hexdigest()[:12]}"
        try:
            self._collection.upsert(  # type: ignore[union-attr]
                ids=[doc_id],
                documents=[text],
                metadatas=[meta],
                embeddings=[emb],
            )
            return {
                "ok": True,
                "id": doc_id,
                "sender_agent": meta["sender_agent"],
                "tags": tag_list,
                "timestamp": meta["timestamp"],
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def query_brain(self, query_string: str, limit: int = 3) -> List[Dict[str, Any]]:
        query = (query_string or "").strip()
        if not query or self._collection is None:
            return []

        emb = self._embed_one(query)
        if emb is None:
            return []

        try:
            res = self._collection.query(  # type: ignore[union-attr]
                query_embeddings=[emb],
                n_results=max(1, int(limit)),
                include=["documents", "metadatas", "distances"],
            )
            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]
            out: List[Dict[str, Any]] = []
            for i, doc in enumerate(docs):
                if not doc:
                    continue
                meta = metas[i] if i < len(metas) else {}
                out.append(
                    {
                        "text": str(doc),
                        "sender_agent": str(meta.get("sender_agent") or "UNKNOWN"),
                        "tags": _tags_from_meta(meta),
                        "timestamp": meta.get("timestamp") or meta.get("ts"),
                        "distance": dists[i] if i < len(dists) else None,
                    }
                )
            return out
        except Exception:
            return []


def _normalize_tags(tags: Optional[Union[Sequence[str], str]]) -> List[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    return [str(t).strip() for t in tags if str(t).strip()]


def _tags_from_meta(meta: Dict[str, Any]) -> List[str]:
    raw = meta.get("tags") or ""
    if isinstance(raw, list):
        return [str(t) for t in raw]
    return [t.strip() for t in str(raw).split(",") if t.strip()]


def _get_store() -> SharedBrain:
    global _store, _cfg
    with _lock:
        if _store is None:
            if _cfg is None:
                try:
                    from glados_config import load_config

                    _cfg = load_config()
                except Exception:
                    _cfg = {"memory_enable_chroma": True, "chroma_persist_dir": "chroma_db"}
            _store = SharedBrain(_cfg)
        return _store


def configure_shared_brain(
    cfg: Dict[str, Any],
    telemetry_path: str = "",
    telemetry_log_fn: Optional[Callable[..., None]] = None,
) -> None:
    """Kernel/bootstrap hook — sets config, telemetry, and resets the singleton."""
    global _cfg, _store, _telemetry_path, _telemetry_log_fn
    with _lock:
        _cfg = dict(cfg)
        _telemetry_path = telemetry_path or ""
        _telemetry_log_fn = telemetry_log_fn
        _store = SharedBrain(_cfg)


def enrich_prompt_with_shared_brain(base_prompt: str) -> str:
    """Append mandatory shared-brain tool directive to an agent system prompt."""
    base = (base_prompt or "").strip()
    if SHARED_BRAIN_DIRECTIVE in base:
        return base
    return f"{base}\n\n*** SHARED SWARM BRAIN ***\n{SHARED_BRAIN_DIRECTIVE}"


def format_brain_hits(hits: List[Dict[str, Any]]) -> str:
    if not hits:
        return ""
    lines = ["*** SHARED SWARM BRAIN (cross-agent insights) ***"]
    for hit in hits:
        agent = hit.get("sender_agent", "?")
        tags = hit.get("tags") or []
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        lines.append(f"- [{agent}]{tag_str} {hit.get('text', '')}")
    return "\n".join(lines)


def _emit_brain_update(
    result: Dict[str, Any],
    insight_text: str,
    sender_agent: str,
    tags: List[str],
) -> None:
    if not _telemetry_log_fn or not _telemetry_path:
        return
    try:
        _telemetry_log_fn(
            _telemetry_path,
            "brain_update",
            {
                "action": "remember_insight",
                "ok": bool(result.get("ok")),
                "sender_agent": sender_agent,
                "tags": tags,
                "insight_preview": insight_text[:300],
                "insight_id": result.get("id"),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            },
        )
    except Exception:
        pass


def remember_insight(
    insight_text: str,
    tags: Optional[Union[Sequence[str], str]] = None,
    *,
    sender_agent: str = "MANAGER",
) -> Dict[str, Any]:
    """
    Store a cross-agent insight in ``glados_shared_brain``.
    Broadcasts ``brain_update`` telemetry for the HUD when configured.
    """
    tag_list = _normalize_tags(tags)
    result = _get_store().remember_insight(
        insight_text,
        tag_list,
        sender_agent=sender_agent,
    )
    if result.get("ok"):
        _emit_brain_update(result, insight_text, sender_agent, tag_list)
    return result


def query_brain(query_string: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Semantic search across all agents' stored insights."""
    return _get_store().query_brain(query_string, limit=limit)


def query_brain_context(query_string: str, limit: int = 3) -> str:
    """Formatted prompt block from shared brain hits."""
    return format_brain_hits(query_brain(query_string, limit=limit))
