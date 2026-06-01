from __future__ import annotations

import os
from typing import Any, Dict, List

from .chroma_store import ChromaMemoryStore
from .static_store import StaticMemoryStore


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def retrieve_memory_context(user_input: str, cfg: Dict[str, Any], top_k: int = 3) -> str:
    """
    Returns a formatted memory context string to inject into the system prompt.

    Phase 0:
      - Static store is fully implemented.
      - Chroma store is optional and currently query-only stub (returns empty).
    """
    facts_path = os.path.join(_repo_root(), "configs", "static_memory.json")
    static_store = StaticMemoryStore(facts_path)
    static_hits = static_store.retrieve(user_input, top_k=top_k)

    parts: List[str] = []
    for score, text in static_hits:
        _ = score
        parts.append(f"- {text}")

    # Optional Chroma retrieval
    try:
        if bool(cfg.get("memory_enable_chroma")):
            chroma_store = ChromaMemoryStore(cfg)
            chroma_hits = chroma_store.query(user_input, top_k=top_k)
            for hit in chroma_hits:
                parts.append(f"- {hit}")
    except Exception:
        # Memory should never break the kernel.
        pass

    if not parts:
        return "No relevant static/dynamic memory found."
    return "\n".join(parts)


def add_memory_event(event: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """
    Placeholder for Phase 0 dynamic-memory ingestion.
    Called later slices (telemetry) can persist to Chroma.
    """
    _ = event
    _ = cfg


# Backwards-friendly names
retrieve_memory = retrieve_memory_context

