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
                    "Check OpenClaw gateway + agents.defaults.memorySearch in ~/.openclaw/openclaw.json. "
                    f"Details: {chroma_store.last_error})"
                )
    except Exception:
        # Memory should never break the kernel.
        pass

    if not parts:
        pass  # may still get shared brain hits below

    # Shared swarm brain (cross-agent Chroma insights)
    try:
        from plugins.shared_memory import query_brain_context  # type: ignore
    except Exception:
        try:
            from shared_memory import query_brain_context  # type: ignore
        except Exception:
            query_brain_context = None  # type: ignore
    if query_brain_context:
        shared_block = query_brain_context(user_input, limit=top_k)
        if shared_block:
            parts.append(shared_block)

    if not parts:
        return "No relevant memory found. Run a facility scan to populate the computer brain."
    return "\n".join(parts)


def build_sandwich_user_prompt(user_input: str, memory_context: str) -> str:
    """
    Force small models (e.g. llama3.2:1b) to attend to retrieved memory by placing it
    immediately before the user query in the same user message.
    """
    mem = (memory_context or "").strip() or "No relevant memory found."
    query = (user_input or "").strip()
    return (
        "You are GLaDOS. You must use the following strictly accurate local data "
        "to formulate your response. Do not ignore it.\n\n"
        "[CRITICAL LOCAL MEMORY]\n"
        f"{mem}\n"
        "[END OF MEMORY]\n\n"
        f"User Input: {query}\n"
        "Response:"
    )


def remember_os_action(
    user_input: str,
    command_type: str,
    target: str,
    output: str,
    cfg: Dict[str, Any],
) -> None:
    """Persist OS command results into Chroma so Glados recalls what she did."""
    text = (
        f"OS action ({command_type}) on '{target}' for user request "
        f"'{(user_input or '')[:200]}': {(output or '')[:2000]}"
    )
    add_memory_event(
        {
            "event_type": "os_action",
            "text": text,
            "source": "system",
            "command_type": command_type,
            "target": target,
        },
        cfg,
    )


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

