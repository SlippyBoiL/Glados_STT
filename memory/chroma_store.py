from __future__ import annotations

import hashlib
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests


try:
    import chromadb  # type: ignore
except ImportError:  # pragma: no cover
    chromadb = None  # type: ignore


class ChromaMemoryStore:
    """
    Optional ChromaDB-backed memory.

    Uses Ollama embeddings (local-first) and a persisted ChromaDB collection.

    Config keys (from `glados_config.py`):
      - memory_enable_chroma: bool
      - chroma_persist_dir: str
      - chroma_collection: str
      - embedding_backend: "ollama" (only supported backend in this implementation)
      - embedding_model: e.g. "nomic-embed-text"
      - ollama_base_url: e.g. "http://127.0.0.1:11434/v1"
    """

    def __init__(self, cfg: Dict[str, Any]) -> None:
        self._enabled = bool(cfg.get("memory_enable_chroma"))
        self._persist_dir = str(cfg.get("chroma_persist_dir") or "chroma_db")
        self._collection_name = str(cfg.get("chroma_collection") or "glados_memories")
        self._embed_backend = str(cfg.get("embedding_backend") or "ollama").strip().lower()
        self._embed_model = str(cfg.get("embedding_model") or "nomic-embed-text").strip()
        self._ollama_base_url = str(cfg.get("ollama_base_url") or "http://127.0.0.1:11434/v1").strip()
        self.last_error: str = ""

        self._client = None
        self._collection = None

        if not self._enabled or chromadb is None:
            return

        try:
            self._client = chromadb.PersistentClient(path=self._persist_dir)  # type: ignore[attr-defined]
            try:
                self._collection = self._client.get_collection(self._collection_name)
            except Exception:
                self._collection = self._client.create_collection(self._collection_name)
        except Exception:
            # Collection may not exist yet; treat as empty.
            self._client = None
            self._collection = None

    def _ollama_api_root(self) -> str:
        # Config uses OpenAI-compat /v1. Embeddings use Ollama native /api/embeddings.
        root = self._ollama_base_url.rstrip("/")
        if root.endswith("/v1"):
            root = root[: -len("/v1")]
        return root

    def _embed_one(self, text: str) -> Optional[List[float]]:
        if not text:
            return None
        if self._embed_backend != "ollama":
            self.last_error = f"Unsupported embedding backend: {self._embed_backend}"
            return None
        try:
            url = self._ollama_api_root() + "/api/embeddings"
            resp = requests.post(
                url,
                json={"model": self._embed_model, "prompt": text},
                timeout=20,
            )
            if resp.status_code != 200:
                self.last_error = f"Ollama embeddings HTTP {resp.status_code}: {resp.text[:200]}"
                return None
            data = resp.json() or {}
            emb = data.get("embedding")
            if isinstance(emb, list) and emb and isinstance(emb[0], (int, float)):
                self.last_error = ""
                return [float(x) for x in emb]
            self.last_error = "Ollama embeddings response missing 'embedding' vector"
            return None
        except Exception:
            self.last_error = "Ollama embeddings request failed"
            return None

    def embed_many(self, texts: Sequence[str]) -> List[Optional[List[float]]]:
        return [self._embed_one(t) for t in texts]

    def add_events(self, events: Sequence[Dict[str, Any]]) -> int:
        """
        Upsert a batch of memory events into Chroma.

        Each event should have:
          - text: str (required)
          - event_type/source/ts metadata optional
        """
        if self._collection is None:
            return 0
        docs: List[str] = []
        metas: List[Dict[str, Any]] = []
        ids: List[str] = []

        for ev in events:
            text = str(ev.get("text") or "").strip()
            if not text:
                continue
            ts = ev.get("ts")
            if ts is None:
                ts = time.time()
            meta = {
                "event_type": str(ev.get("event_type") or ev.get("type") or "event"),
                "source": str(ev.get("source") or "kernel"),
                "ts": float(ts),
            }
            # Stable-ish ID: content hash + ts bucket
            h = hashlib.sha1((text + "|" + meta["event_type"]).encode("utf-8", errors="ignore")).hexdigest()[:16]
            ids.append(f"{int(meta['ts'])}-{h}")
            docs.append(text)
            metas.append(meta)

        if not docs:
            return 0

        embeddings = self.embed_many(docs)
        # Filter out any docs that failed to embed.
        f_docs: List[str] = []
        f_metas: List[Dict[str, Any]] = []
        f_ids: List[str] = []
        f_embs: List[List[float]] = []
        for i, emb in enumerate(embeddings):
            if emb is None:
                continue
            f_docs.append(docs[i])
            f_metas.append(metas[i])
            f_ids.append(ids[i])
            f_embs.append(emb)

        if not f_docs:
            return 0

        try:
            self._collection.upsert(  # type: ignore[union-attr]
                ids=f_ids,
                documents=f_docs,
                metadatas=f_metas,
                embeddings=f_embs,
            )
            return len(f_docs)
        except Exception:
            return 0

    def query(self, query: str, top_k: int = 3) -> List[str]:
        if self._collection is None or not query:
            return []
        emb = self._embed_one(query)
        if emb is None:
            return []
        try:
            res = self._collection.query(  # type: ignore[union-attr]
                query_embeddings=[emb],
                n_results=max(1, int(top_k)),
                include=["documents", "metadatas", "distances"],
            )
            docs = (res.get("documents") or [[]])[0]
            out: List[str] = []
            for d in docs:
                if d:
                    out.append(str(d))
            return out
        except Exception:
            return []

