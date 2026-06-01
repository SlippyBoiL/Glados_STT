from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


try:
    import chromadb  # type: ignore
except ImportError:  # pragma: no cover
    chromadb = None  # type: ignore


class ChromaMemoryStore:
    """
    Optional ChromaDB-backed memory.

    Phase 0 MVP keeps it as a query-only stub:
    - If `chromadb` is not installed or no persisted collection exists, returns no matches.
    - Adding new memories/events comes in a later slice.
    """

    def __init__(self, cfg: Dict[str, Any]) -> None:
        self._enabled = bool(cfg.get("memory_enable_chroma"))
        self._persist_dir = str(cfg.get("chroma_persist_dir") or "chroma_db")
        self._collection_name = str(cfg.get("chroma_collection") or "glados_memories")

        self._client = None
        self._collection = None

        if not self._enabled or chromadb is None:
            return

        try:
            self._client = chromadb.PersistentClient(path=self._persist_dir)  # type: ignore[attr-defined]
            self._collection = self._client.get_collection(self._collection_name)
        except Exception:
            # Collection may not exist yet; treat as empty.
            self._client = None
            self._collection = None

    def query(self, query: str, top_k: int = 3) -> List[str]:
        if self._collection is None or not query:
            return []
        try:
            # Without implementing embeddings in Phase 0, we cannot reliably query.
            # Return empty and keep the integration points ready.
            _ = query
            _ = top_k
            return []
        except Exception:
            return []

