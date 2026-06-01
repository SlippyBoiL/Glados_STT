from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, Optional

_LOCK = threading.Lock()


def load_state(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        with _LOCK:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def save_state(path: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with _LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)


def merge_custom_from_config(state: Dict[str, Any], custom_facts: list) -> Dict[str, Any]:
    state = dict(state)
    custom = dict(state.get("custom") or {})
    custom["facts"] = custom_facts or custom.get("facts") or []
    state["custom"] = custom
    return state
