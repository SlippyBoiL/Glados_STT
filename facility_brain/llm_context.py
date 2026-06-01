from __future__ import annotations

from typing import Any, Dict


def compact_context_for_llm(state: Dict[str, Any], max_chars: int = 1400) -> str:
    """Short facility snapshot for the chat model (no full file lists)."""
    if not state:
        return ""

    h = state.get("host") or {}
    hw = state.get("hardware") or {}
    net = state.get("network") or {}
    apps = state.get("apps") or {}
    deep = state.get("deep") or {}
    profile = deep.get("user_profile") or {}
    custom = state.get("custom") or {}

    lines = [
        f"PC: {h.get('hostname', '?')} ({h.get('platform', '?')}), user {h.get('user', deep.get('env_user', '?'))}.",
        f"Resources: RAM {hw.get('ram_percent', '?')}%, system disk {hw.get('disk_percent', '?')}%.",
        f"Network: internet {'up' if net.get('internet_ok') else 'down'}.",
        f"Foreground window: {apps.get('foreground_window') or 'unknown'}.",
    ]

    name = str(profile.get("display_name") or "").strip()
    about = str(profile.get("about") or "").strip()
    if name:
        lines.append(f"Operator name: {name}.")
    if about:
        lines.append(f"About operator: {about[:300]}")

    facts = profile.get("facts") or []
    if isinstance(facts, list):
        for f in facts[:6]:
            if f:
                lines.append(f"Operator fact: {f}")

    for f in (custom.get("facts") or [])[:4]:
        if isinstance(f, dict) and f.get("text"):
            lines.append(str(f["text"])[:200])
        elif isinstance(f, str):
            lines.append(f[:200])

    inv = deep.get("folder_inventory") or {}
    for label in ("desktop", "downloads"):
        items = inv.get(label) or []
        if items:
            preview = ", ".join(str(x) for x in items[:8])
            lines.append(f"Recent {label} items (names only): {preview}.")

    progs = deep.get("installed_programs") or []
    if progs:
        lines.append(f"Installed software sample ({len(progs)} total): " + ", ".join(progs[:12]) + ".")

    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text
