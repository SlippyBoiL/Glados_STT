from __future__ import annotations

import hashlib
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple


try:
    import chromadb  # type: ignore
except ImportError:  # pragma: no cover
    chromadb = None  # type: ignore


class ChromaMemoryStore:
    """
    Optional ChromaDB-backed memory.

    Embeddings route through OpenClaw /v1/embeddings when llm_provider is openclaw
    (or embedding_backend: openclaw). Legacy direct Ollama is kept for ollama-only setups.

    Config keys (from `glados_config.py`):
      - memory_enable_chroma: bool
      - chroma_persist_dir: str
      - chroma_collection: str
      - embedding_backend: "openclaw" | "ollama"
      - embedding_model: e.g. "openclaw/default"
      - llm_provider: "openclaw" (default)
    """

    def __init__(self, cfg: Dict[str, Any]) -> None:
        self._cfg = cfg
        self._enabled = bool(cfg.get("memory_enable_chroma"))
        self._persist_dir = str(cfg.get("chroma_persist_dir") or "chroma_db")
        self._collection_name = str(cfg.get("chroma_collection") or "glados_memories")
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
        except BaseException as exc:  # noqa: BLE001
            # chromadb's Rust backend raises pyo3 PanicException (a BaseException, not
            # Exception) on an incompatible on-disk store — must not crash the kernel.
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            self.last_error = f"Chroma unavailable: {exc}"
            self._client = None
            self._collection = None

    def _embed_one(self, text: str) -> Optional[List[float]]:
        from glados_llm import embed_texts

        results = embed_texts(self._cfg, [text])
        emb = results[0] if results else None
        if emb is None:
            from glados_llm import is_openclaw, use_openclaw_embeddings

            if use_openclaw_embeddings(self._cfg) or is_openclaw(self._cfg):
                self.last_error = (
                    "OpenClaw embeddings failed. Check gateway is running and "
                    "agents.defaults.memorySearch is configured in ~/.openclaw/openclaw.json "
                    "(e.g. provider: local with @openclaw/llama-cpp-provider)."
                )
            else:
                self.last_error = (
                    "Ollama embeddings failed. Check ollama serve and embedding_model is pulled."
                )
        else:
            self.last_error = ""
        return emb

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

