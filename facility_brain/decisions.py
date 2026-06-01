from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

Decision = Dict[str, Any]


def _norm(text: str) -> str:
    return (text or "").lower().strip()


def _match_keywords(text: str, keywords: List[str]) -> bool:
    low = _norm(text)
    return any(k.lower() in low for k in keywords)


def _rule_override(text: str, rules: List[Dict[str, Any]]) -> Optional[str]:
    for rule in rules or []:
        kws = rule.get("keywords") or []
        if _match_keywords(text, kws):
            return str(rule.get("action") or "").strip()
    return None


def decide(user_input: str, state: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[Decision]:
    """
    Map user text + facility brain state → action dict.
    Returns None if brain has no confident decision (caller should use LLM).
    """
    text = _norm(user_input)
    if not text:
        return None

    min_conf = float(cfg.get("min_decision_confidence") or 0.55)
    aliases = {str(k).lower(): str(v).lower() for k, v in (cfg.get("app_aliases") or {}).items()}
    rules = cfg.get("decision_rules") or []

    override = _rule_override(text, rules)
    if override and override != "web_search":
        return _make_decision(override, text, state, cfg, confidence=0.95)

    # Status / report
    if _match_keywords(text, ["status", "system report", "brain report", "how is the computer", "full scan report"]):
        return _make_decision("report_status", text, state, cfg, confidence=0.9)

    if _match_keywords(text, ["rescan", "scan computer", "update brain", "refresh brain", "rescan computer"]):
        return _make_decision("rescan", text, state, cfg, confidence=0.95)

    # Network repair
    if _match_keywords(text, ["flush dns", "fix dns", "fix internet", "fix wifi", "repair network", "network fix"]):
        return _make_decision("network_repair", text, state, cfg, confidence=0.88)

    # Open app
    m = re.search(r"\b(open|launch|start|run|boot)\s+(?:up\s+)?(?:the\s+)?([a-z0-9 ._-]+)", text)
    if m:
        app = m.group(2).strip().rstrip(".")
        app = aliases.get(app, app)
        return _make_decision("open_app", text, state, cfg, confidence=0.85, params={"app": app})

    # Close app
    m = re.search(r"\b(close|quit|kill|terminate|stop|exit)\s+(?:the\s+)?([a-z0-9 ._-]+)", text)
    if m:
        app = m.group(2).strip().rstrip(".")
        return _make_decision("close_app", text, state, cfg, confidence=0.85, params={"app": app})

    # Server / SSH by name from brain
    servers = state.get("servers") or []
    for srv in servers:
        name = str(srv.get("name") or "").lower()
        if name and name in text:
            if _match_keywords(text, ["check", "status", "monitor", "health", "ssh"]):
                return _make_decision(
                    "server_check",
                    text,
                    state,
                    cfg,
                    confidence=0.82,
                    params={"device": name},
                )

    # Learned skill by id from skills brain
    skills = state.get("skills") or []
    for sk in skills:
        sid = str(sk.get("id") or sk.get("stem") or "")
        if sid and sid.replace("_", " ") in text.replace("_", " "):
            if _match_keywords(text, ["run", "execute", "use", "skill", "protocol"]):
                return _make_decision(
                    "run_skill",
                    text,
                    state,
                    cfg,
                    confidence=0.8,
                    params={"skill_file": sid},
                )

    # Alerts proactive
    alerts = state.get("alerts") or []
    if alerts and _match_keywords(text, ["what's wrong", "any problems", "alerts", "issues"]):
        return _make_decision("report_alerts", text, state, cfg, confidence=0.75)

    # Web search — open real browser (no LLM)
    if _match_keywords(
        text,
        [
            "search the web",
            "search online",
            "google ",
            "look up online",
            "look up on the web",
            "browse the web",
            "search for ",
        ],
    ):
        from facility_brain.web_search import extract_search_query

        query = extract_search_query(text)
        if query:
            return _make_decision(
                "web_search",
                text,
                state,
                cfg,
                confidence=0.9,
                params={"query": query},
            )

    # Low confidence chat — brain defers to LLM
    return None


def _make_decision(
    action: str,
    text: str,
    state: Dict[str, Any],
    cfg: Dict[str, Any],
    confidence: float,
    params: Optional[Dict[str, Any]] = None,
) -> Decision:
    return {
        "action": action,
        "confidence": confidence,
        "params": params or {},
        "source": "facility_brain",
        "user_input": text,
    }


def format_status_report(state: Dict[str, Any]) -> str:
    h = state.get("host") or {}
    hw = state.get("hardware") or {}
    net = state.get("network") or {}
    alerts = state.get("alerts") or []
    lines = [
        f"Facility scan: {state.get('scanned_at_iso', 'unknown')}.",
        f"Host {h.get('hostname', '?')} — {h.get('platform', '?')}.",
        f"RAM {hw.get('ram_percent', '?')}% — disk {hw.get('disk_percent', '?')}% free {hw.get('disk_free_gb', '?')} GB.",
        f"Internet {'up' if net.get('internet_ok') else 'down'}.",
        f"Foreground: {((state.get('apps') or {}).get('foreground_window') or 'unknown')}.",
    ]
    if alerts:
        lines.append("Alerts: " + "; ".join(alerts[:3]))
    else:
        lines.append("No critical alerts in the last scan.")
    return " ".join(lines)
