import json
import os
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple


class StaticMemoryStore:
    """
    Simple keyword + fuzzy retrieval over `configs/static_memory.json`.

    Expected schema:
      { "facts": [ { "id": "...", "keywords": [...], "text": "..." }, ... ] }
    """

    def __init__(self, facts_path: str) -> None:
        self._facts_path = facts_path
        self._facts: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            if not os.path.exists(self._facts_path):
                self._facts = []
                return
            with open(self._facts_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            facts = data.get("facts") or []
            if not isinstance(facts, list):
                self._facts = []
                return
            # Normalize
            norm: List[Dict[str, Any]] = []
            for item in facts:
                if not isinstance(item, dict):
                    continue
                if not item.get("text"):
                    continue
                norm.append(
                    {
                        "id": str(item.get("id") or ""),
                        "keywords": item.get("keywords") or [],
                        "text": str(item.get("text")),
                    }
                )
            self._facts = norm
        except Exception:
            self._facts = []

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[float, str]]:
        q = (query or "").lower().strip()
        if not q or not self._facts:
            return []

        scored: List[Tuple[float, str]] = []
        for fact in self._facts:
            text = str(fact.get("text") or "")
            keywords = fact.get("keywords") or []

            score = 0.0
            for kw in keywords:
                kw_s = str(kw).lower().strip()
                if not kw_s:
                    continue
                if kw_s in q:
                    score += 3.0
                if kw_s in text.lower():
                    score += 1.0

            # Light fuzzy help so synonyms still have a chance.
            score += SequenceMatcher(None, q, text.lower()).ratio() * 1.5

            if score > 0.75:
                scored.append((score, text))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[: max(1, int(top_k))]

