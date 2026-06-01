from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_brain_path(cfg: Dict[str, Any] | None = None) -> str:
    if cfg:
        p = str(cfg.get("skills_brain_path") or "").strip()
        if p:
            return p if os.path.isabs(p) else os.path.join(REPO_ROOT, p)
    return os.path.join(REPO_ROOT, "data", "glados_skills_brain.json")


class SkillsBrain:
    """
    All learned skills live in ONE file: data/glados_skills_brain.json.
    Glados develops skills over time — no scattered plugins/skill_*.py files.
    """

    def __init__(self, cfg: Dict[str, Any] | None = None, runtime_file: str | None = None) -> None:
        self._cfg = cfg or {}
        self.path = default_brain_path(self._cfg)
        self.runtime_file = runtime_file or os.path.join(REPO_ROOT, "runtime.py")
        self._data: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        if not os.path.isfile(self.path):
            self._data = {"version": 2, "skills": [], "learning_log": []}
            self.save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = json.load(f) or {}
        except Exception:
            self._data = {"version": 2, "skills": [], "learning_log": []}
        if "skills" not in self._data:
            self._data["skills"] = []

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._data["version"] = 2
        self._data["updated_at_iso"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    @property
    def skills(self) -> List[Dict[str, Any]]:
        return list(self._data.get("skills") or [])

    def _slug(self, text: str) -> str:
        s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
        return (s[:48] or f"skill_{int(time.time())}").strip("_")

    def _unique_id(self, base: str) -> str:
        existing = {str(s.get("id")) for s in self.skills}
        if base not in existing:
            return base
        for i in range(2, 999):
            cand = f"{base}_{i}"
            if cand not in existing:
                return cand
        return f"{base}_{int(time.time())}"

    def match(self, user_query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        q = (user_query or "").lower().strip()
        if not q:
            return []

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for sk in self.skills:
            if str(sk.get("status") or "active") == "disabled":
                continue
            score = 0.0
            sid = str(sk.get("id") or "").lower()
            name = str(sk.get("name") or "").lower()
            if sid and sid in q:
                score += 6.0
            if name and name in q:
                score += 4.0
            for trig in sk.get("triggers") or []:
                t = str(trig).lower().strip()
                if t and t in q:
                    score += 5.0
                elif t and len(t) > 4 and any(t in tok for tok in q.split()):
                    score += 2.0
            desc = str(sk.get("description") or "").lower()
            score += SequenceMatcher(None, q, desc).ratio() * 1.5
            if score > 1.0:
                scored.append((score, sk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [sk for _, sk in scored[:top_k]]

    def get_manifest(self, user_query: str = "") -> str:
        matches = self.match(user_query, top_k=5)
        if not matches:
            return (
                "No matching protocols in the skills brain yet. "
                "Glados can develop a new skill for this request (self-development mode). "
                "Reply conversationally OR output one ```python``` block if inventing code."
            )
        lines = []
        for sk in matches:
            sid = sk.get("id", "?")
            desc = sk.get("description", "No description")
            runs = sk.get("successes", 0)
            lines.append(f"- ID: '{sid}' | ACTION: {desc} | SUCCESS_RUNS: {runs}")
        lines.append(
            "\nTo run a learned protocol, reference its ID in a ```python``` block "
            f"or say run skill <id>. All skills are stored in: {os.path.basename(self.path)}"
        )
        return "\n".join(lines)

    def get_matched_skills(self, user_query: str = "") -> List[Dict[str, Any]]:
        return [
            {
                "id": s.get("id"),
                "description": s.get("description"),
                "file": self.path,
            }
            for s in self.match(user_query, top_k=5)
        ]

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        sid = (skill_id or "").strip().lower()
        for sk in self.skills:
            if str(sk.get("id") or "").lower() == sid:
                return sk
        return None

    def learn(
        self,
        code: str,
        description: str,
        triggers: List[str] | None = None,
        *,
        user_request: str = "",
        status: str = "active",
    ) -> str:
        code = (code or "").strip()
        if not code:
            raise ValueError("empty code")
        ast.parse(code)

        base_id = self._slug(description or user_request or "learned_skill")
        skill_id = self._unique_id(base_id)
        trig = list(triggers or [])
        if user_request and user_request.lower() not in [t.lower() for t in trig]:
            trig.insert(0, user_request.lower()[:120])

        entry = {
            "id": skill_id,
            "name": description[:80] if description else skill_id,
            "description": description or "Learned protocol",
            "triggers": trig[:12],
            "code": code,
            "created_at_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "last_run_iso": None,
            "runs": 0,
            "successes": 0,
            "failures": 0,
            "status": status,
        }
        self._data.setdefault("skills", []).append(entry)
        self._log_learning(f"learned skill '{skill_id}'", user_request)
        self.save()
        return skill_id

    def _log_learning(self, message: str, user_request: str = "") -> None:
        log = self._data.setdefault("learning_log", [])
        log.append(
            {
                "ts": time.time(),
                "ts_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "message": message,
                "user_request": (user_request or "")[:300],
            }
        )
        if len(log) > 200:
            self._data["learning_log"] = log[-200:]

    def update_code(self, skill_id: str, code: str) -> bool:
        sk = self.get_skill(skill_id)
        if not sk:
            return False
        ast.parse(code)
        sk["code"] = code.strip()
        sk["status"] = "active"
        self.save()
        return True

    def execute(self, skill_id: str, extra_env: Dict[str, str] | None = None) -> str:
        sk = self.get_skill(skill_id)
        if not sk:
            return f"No skill with id '{skill_id}' in the brain."

        code = str(sk.get("code") or "")
        if not code.strip():
            return f"Skill '{skill_id}' has no code."

        if "kernel.py" in code.lower() and ("write" in code or "delete" in code):
            return "ERROR: ACCESS DENIED. Cannot modify kernel.py."

        os.makedirs(os.path.dirname(self.runtime_file) or ".", exist_ok=True)
        with open(self.runtime_file, "w", encoding="utf-8") as f:
            f.write(code)

        sk["runs"] = int(sk.get("runs") or 0) + 1
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)

        try:
            result = subprocess.run(
                [sys.executable, self.runtime_file],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=REPO_ROOT,
                env=env,
            )
            out = (result.stdout or "") + (result.stderr or "")
            sk["last_run_iso"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            if result.returncode == 0:
                sk["successes"] = int(sk.get("successes") or 0) + 1
                self.save()
                return (out.strip() or "Protocol completed with no output.") + "\n\n[SUCCESS]"
            sk["failures"] = int(sk.get("failures") or 0) + 1
            self.save()
            return (out.strip() or "Unknown error.") + "\n\n[FAILED]"
        except Exception as e:
            sk["failures"] = int(sk.get("failures") or 0) + 1
            self.save()
            return f"Execution Error: {e}"

    def execute_best_match(self, user_input: str) -> Tuple[bool, str, Optional[str]]:
        matches = self.match(user_input, top_k=1)
        if not matches:
            return False, "", None
        sid = str(matches[0].get("id"))
        return True, self.execute(sid), sid

    def skill_id_from_llm_text(self, ai_text: str) -> Optional[str]:
        if not ai_text:
            return None
        m = re.search(r"ID:\s*'([^']+)'", ai_text, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"run\s+skill\s+([a-z0-9_]+)", ai_text, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    def list_for_scan(self) -> List[Dict[str, str]]:
        return [
            {"id": str(s.get("id")), "stem": str(s.get("id")), "description": str(s.get("description") or "")}
            for s in self.skills
            if str(s.get("status") or "active") == "active"
        ]
