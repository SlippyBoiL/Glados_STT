from __future__ import annotations

import os
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple


class ComputerBrainStore:
    """
    Searchable facts from the facility PC scan (`data/computer_brain_memory.json`).
    Synced after each scan — this IS Glados's computer knowledge brain.
    """

    def __init__(self, memory_path: str) -> None:
        self._path = memory_path
        self._facts: List[Dict[str, Any]] = []
        self._meta: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        self._facts = []
        self._meta = {}
        if not os.path.isfile(self._path):
            return
        try:
            import json

            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if not isinstance(data, dict):
                return
            self._meta = {
                "synced_at_iso": data.get("synced_at_iso"),
                "fact_count": data.get("fact_count"),
                "hostname": data.get("hostname"),
            }
            raw = data.get("facts") or []
            for item in raw:
                if isinstance(item, dict) and item.get("text"):
                    self._facts.append(item)
        except Exception:
            self._facts = []

    def reload(self) -> None:
        self._load()

    @property
    def fact_count(self) -> int:
        return len(self._facts)

    @property
    def meta(self) -> Dict[str, Any]:
        return dict(self._meta)

    def all_facts(self) -> List[Dict[str, Any]]:
        return list(self._facts)

    def baseline(self) -> List[Tuple[float, str]]:
        out: List[Tuple[float, str]] = []
        for fact in self._facts:
            if fact.get("baseline"):
                out.append((10.0, str(fact.get("text"))))
        return out

    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[float, str]]:
        q = (query or "").lower().strip()
        if not q or not self._facts:
            return []

        scored: List[Tuple[float, str]] = []
        for fact in self._facts:
            if fact.get("baseline"):
                continue
            text = str(fact.get("text") or "")
            keywords = fact.get("keywords") or []
            score = 0.0
            for kw in keywords:
                kw_s = str(kw).lower().strip()
                if not kw_s:
                    continue
                if kw_s in q:
                    score += 3.0
                if len(kw_s) > 4 and kw_s in text.lower():
                    score += 0.5
            score += SequenceMatcher(None, q, text.lower()).ratio() * 1.2
            if score > 0.8:
                scored.append((score, text))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[: max(1, int(top_k))]
