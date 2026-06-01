from __future__ import annotations

import os
from typing import Any, Dict, Optional

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def resolve_plugins_dir(cfg: Optional[Dict[str, Any]] = None) -> str:
    """
    Canonical plugins folder (Windows may use Plugins/ on disk while config says plugins).
    Prefer the directory that already has telemetry.jsonl.
    """
    cfg = cfg or {}
    rel = str(cfg.get("plugins_dir") or "plugins").strip()
    candidates: list[str] = []
    if os.path.isabs(rel):
        candidates.append(rel)
    else:
        candidates.append(os.path.join(REPO_ROOT, rel))
        candidates.append(os.path.join(REPO_ROOT, "Plugins"))
        candidates.append(os.path.join(REPO_ROOT, "plugins"))

    seen: set[str] = set()
    unique: list[str] = []
    for p in candidates:
        norm = os.path.normcase(os.path.abspath(p))
        if norm not in seen:
            seen.add(norm)
            unique.append(p)

    for p in unique:
        if os.path.isfile(os.path.join(p, "telemetry.jsonl")):
            return p
    for p in unique:
        if os.path.isdir(p):
            return p
    return unique[0] if unique else os.path.join(REPO_ROOT, "plugins")
