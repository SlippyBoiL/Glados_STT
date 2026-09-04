from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

_CHAT_NOISE = re.compile(
    r"^(?:hi|hello|hey|how are you|what'?s up|good (?:morning|night)|"
    r"thanks|thank you|ok|okay|yes|no|test(?:\s+one|\s+two)?|ping)[\s!?.]*$",
    re.IGNORECASE,
)

_STATUS_CHATTER = re.compile(
    r"\b(are you learning|ready to learn|not responding|aren'?t responding|"
    r"looks like you|assume you'?re ready|you there|still there|no response)\b",
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
    "learn about",
    "learn how",
    "organize",
)

_REJECT_FACT = re.compile(
    r"anonymous|remains anonymous|did not provide any personal|"
    r"user(?:'s)? name (?:is|remains) glados|referred to as .?glados|"
    r"user is glados|genetic lifeform|"
    r"no permanent actions|does not take any permanent|nothing permanent|"
    r"preference is evident in their action of asking|"
    r"automated name generation|represented by the system|"
    r"notification sound|interaction event|explicit user preference",
    re.IGNORECASE,
)


def worth_consolidating(user_input: str, system_logs: str, glados_response: str) -> bool:
    """Fast filter — skip obvious chatter before spending an LLM call."""
    logs = (system_logs or "").strip()
    ui = (user_input or "").strip()
    if not ui or _CHAT_NOISE.match(ui):
        return False
    low = ui.lower()
    if ui.endswith("?") and not logs:
        return False
    if _STATUS_CHATTER.search(low) and not logs:
        return False
    if logs:
        return True
    if any(h in low for h in _SUBSTANTIVE_HINTS):
        return True
    return False


def _rule_based_fact(user_input: str, system_logs: str) -> Optional[str]:
    """Deterministic facts from known OS actions — avoids 1B model hallucinations."""
    ui = (user_input or "").strip()
    low = ui.lower()
    logs = (system_logs or "").strip()
    logs_low = logs.lower()

    if "git push succeeded" in logs_low or ("push" in low and "github" in low and "succeeded" in logs_low):
        return "User asked Glados to commit and push the Glados project to GitHub."

    m = re.search(r"\bopened\s+([a-z0-9 _.-]+)", logs_low)
    if m and "could not" not in logs_low:
        target = m.group(1).strip(" .")
        if target and target not in ("the application", "that target"):
            return f"User asked Glados to open {target} on this PC."

    if "could not open" in logs_low or "could not find" in logs_low:
        m = re.search(r"could not (?:open|find)\s+([a-z0-9 _.-]+)", logs_low)
        if m:
            return f"User tried to open {m.group(1).strip()} but it was not found on this PC."

    if any(p in low for p in ("learn about", "learn how", "learn to", "want you to learn", "lets learn")):
        topic = re.sub(
            r"^.*?(?:learn(?:\s+about|\s+how\s+to|\s+to)?|want you to learn)\s+",
            "",
            low,
            count=1,
        ).strip(" .?!")
        if topic and len(topic) > 8:
            return f"User asked Glados to learn about: {topic[:200]}."

    if "learned" in logs_low or "protocol" in logs_low or "skill_learned" in logs_low:
        if any(p in low for p in ("learn how", "learn about", "learn to")):
            topic = re.sub(
                r"^.*?(?:learn(?:\s+about|\s+how\s+to|\s+to)?)\s+",
                "",
                low,
                count=1,
            ).strip(" .?!")
            if topic and len(topic) > 8:
                return f"Glados completed a learn task for: {topic[:200]}."

    if "organize" in low and ("download" in low or "folder" in low):
        return "User asked Glados to organize their Downloads folder(s)."

    return None


def _accept_fact(fact: str) -> bool:
    if not fact or len(fact) < 10:
        return False
    if "IGNORE" in fact.upper():
        return False
    if _REJECT_FACT.search(fact):
        return False
    return True


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
    Extract a single declarative fact from a completed turn and commit to Honcho
    (and Chroma if still enabled). Returns the stored fact text, or None if discarded.
    """
    if not bool(cfg.get("memory_consolidation_enabled", True)):
        return None
    if not bool(cfg.get("memory_enable_chroma")) and not bool(
        cfg.get("memory_enable_honcho", True)
    ):
        return None
    if not worth_consolidating(user_input, system_logs, glados_response):
        return None

    min_len = int(cfg.get("memory_consolidation_min_fact_len") or 10)
    rule_fact = _rule_based_fact(user_input, system_logs)
    if rule_fact and _accept_fact(rule_fact) and len(rule_fact) >= min_len:
        from memory.interface import add_memory_event

        add_memory_event(
            {
                "event_type": "episodic_fact",
                "text": rule_fact,
                "source": "self_evolution",
                "ts": time.time(),
            },
            cfg,
        )
        print(f"[BRAIN] Integrated memory: {rule_fact}")
        return rule_fact
    context = (
        "Interaction Event:\n"
        f"- User Said: {(user_input or '')[:500]}\n"
        f"- System Actions Taken: {(system_logs or 'none')[:1500]}\n"
        f"- GLaDOS Response: {(glados_response or '')[:800]}"
    )
    prompt = (
        "Extract ONE permanent fact about the human user or a concrete system event.\n"
        "Rules:\n"
        "- The assistant is GLaDOS; never call the user GLaDOS.\n"
        "- Do not invent names, preferences, or psychology.\n"
        "- Prefer facts like apps opened, folders opened, git pushes, or explicit user preferences.\n"
        "- If nothing concrete happened, reply exactly: IGNORE\n\n"
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
    if not _accept_fact(fact) or len(fact) < min_len:
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
