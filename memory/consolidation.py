from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

_CHAT_NOISE = re.compile(
    r"^(?:hi|hello|hey|how are you|what'?s up|good (?:morning|night)|"
    r"thanks|thank you|ok|okay|yes|no|test(?:\s+one|\s+two)?|ping)[\s!?.]*$",
    re.IGNORECASE,
)

_SUBSTANTIVE_HINTS = (
    "prefer",
    "remember",
    "battery",
    "steam",
    "open ",
    "close ",
    "file",
    "path",
    "install",
    "config",
    "github",
    "password",
    "email",
    "name is",
    "i use",
    "i like",
    "my ",
)


def worth_consolidating(user_input: str, system_logs: str, glados_response: str) -> bool:
    """Fast filter — skip obvious chatter before spending an LLM call."""
    logs = (system_logs or "").strip()
    if logs:
        return True
    ui = (user_input or "").strip()
    if not ui or _CHAT_NOISE.match(ui):
        return False
    low = ui.lower()
    if any(h in low for h in _SUBSTANTIVE_HINTS):
        return True
    if len(ui) < 18:
        return False
    resp = (glados_response or "").strip()
    return len(resp) > 40


def _clean_extracted_fact(raw: str) -> str:
    fact = (raw or "").strip()
    fact = re.sub(r"^(?:fact:\s*)", "", fact, flags=re.IGNORECASE)
    fact = fact.strip("\"' ")
    fact = re.sub(r"\s+", " ", fact)
    return fact


def consolidate_episodic_memory(
    user_input: str,
    system_logs: str,
    glados_response: str,
    *,
    cfg: Dict[str, Any],
    client: Any,
    model_name: str,
    completion_kwargs: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Extract a single declarative fact from a completed turn and commit to ChromaDB.
    Returns the stored fact text, or None if discarded.
    """
    if not bool(cfg.get("memory_consolidation_enabled", True)):
        return None
    if not bool(cfg.get("memory_enable_chroma")):
        return None
    if not worth_consolidating(user_input, system_logs, glados_response):
        return None

    min_len = int(cfg.get("memory_consolidation_min_fact_len") or 10)
    context = (
        "Interaction Event:\n"
        f"- User Said: {(user_input or '')[:500]}\n"
        f"- System Actions Taken: {(system_logs or 'none')[:1500]}\n"
        f"- GLaDOS Response: {(glados_response or '')[:800]}"
    )
    prompt = (
        "Analyze this interaction and extract any permanent facts about the user, "
        "their preferences, or system states.\n"
        "Format as a single concise declarative sentence. "
        "If nothing permanent occurred, reply with exactly: IGNORE\n\n"
        f"Context:\n{context}\n\nFact:"
    )

    try:
        kw = dict(completion_kwargs or {})
        kw["max_tokens"] = min(int(kw.get("max_tokens") or 64), 64)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            **kw,
        )
        raw = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"[!] Memory consolidation skipped: {exc}")
        return None

    fact = _clean_extracted_fact(raw)
    if not fact or "IGNORE" in fact.upper() or len(fact) < min_len:
        return None

    from memory.interface import add_memory_event

    add_memory_event(
        {
            "event_type": "episodic_fact",
            "text": fact,
            "source": "self_evolution",
            "ts": time.time(),
        },
        cfg,
    )
    print(f"[BRAIN] Integrated memory: {fact}")
    return fact
