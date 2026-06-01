from __future__ import annotations

import os
from typing import Any, Dict, List

from .chroma_store import ChromaMemoryStore
from .computer_brain_store import ComputerBrainStore
from .static_store import StaticMemoryStore


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def computer_brain_memory_path(cfg: Dict[str, Any] | None = None) -> str:
    _ = cfg
    return os.path.join(_repo_root(), "data", "computer_brain_memory.json")


def retrieve_computer_brain_context(
    user_input: str,
    cfg: Dict[str, Any],
    top_k: int = 5,
) -> str:
    """Always-on computer knowledge from the facility scan (Glados brain)."""
    if not bool(cfg.get("facility_brain_enabled", True)):
        return ""
    store = ComputerBrainStore(computer_brain_memory_path(cfg))
    if not store.fact_count:
        return ""

    seen: set = set()
    parts: List[str] = []
    for _, text in store.baseline():
        if text not in seen:
            seen.add(text)
            parts.append(f"- {text}")

    for _, text in store.retrieve(user_input, top_k=top_k):
        if text not in seen:
            seen.add(text)
            parts.append(f"- {text}")

    low = (user_input or "").lower()
    if any(
        w in low
        for w in (
            "file",
            "files",
            "folder",
            "document",
            "where is",
            "find my",
            "path",
            "desktop",
            "download",
        )
    ):
        try:
            from facility_brain.file_scan import search_file_index

            hits = search_file_index(user_input, top_k=8)
            for path in hits:
                line = f"- File on this PC: {path}"
                if line not in seen:
                    seen.add(line)
                    parts.append(line)
        except Exception:
            pass

    if not parts:
        return ""
    return "*** COMPUTER BRAIN (local PC scan) ***\n" + "\n".join(parts)


def retrieve_memory_context(
    user_input: str,
    cfg: Dict[str, Any],
    top_k: int = 3,
    *,
    include_static: bool = True,
    include_chroma: bool = True,
    include_computer_brain: bool = True,
) -> str:
    """
    Returns a formatted memory context string to inject into the system prompt.

    Computer brain (facility scan) is always merged when enabled.
    """
    parts: List[str] = []

    if include_computer_brain:
        computer_block = retrieve_computer_brain_context(user_input, cfg, top_k=max(top_k, 5))
        if computer_block:
            parts.append(computer_block)

    if include_static:
        facts_path = os.path.join(_repo_root(), "configs", "static_memory.json")
        static_store = StaticMemoryStore(facts_path)
        for score, text in static_store.retrieve(user_input, top_k=top_k):
            _ = score
            parts.append(f"- {text}")

    # Optional Chroma retrieval
    try:
        if include_chroma and bool(cfg.get("memory_enable_chroma")):
            chroma_store = ChromaMemoryStore(cfg)
            chroma_hits = chroma_store.query(user_input, top_k=top_k)
            for hit in chroma_hits:
                parts.append(f"- {hit}")
            if not chroma_hits and chroma_store.last_error:
                parts.append(
                    "- (Chroma enabled, but embeddings are not working. "
                    f\"Check `embedding_model` in config and that Ollama has it pulled. Details: {chroma_store.last_error})\"
                )
    except Exception:
        # Memory should never break the kernel.
        pass

    if not parts:
        return "No relevant memory found. Run a facility scan to populate the computer brain."
    return "\n".join(parts)


def add_memory_event(event: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """
    Persist a dynamic memory event to Chroma (if enabled).
    """
    try:
        if not bool(cfg.get("memory_enable_chroma")):
            return
        chroma_store = ChromaMemoryStore(cfg)
        chroma_store.add_events([event])
    except Exception:
        return


# Backwards-friendly names
retrieve_memory = retrieve_memory_context

