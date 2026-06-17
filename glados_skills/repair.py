from __future__ import annotations

import re
from typing import Any, Dict, Optional

from glados_skills.skills_brain import SkillsBrain


def repair_skill_in_brain(
    client: Any,
    model_name: str,
    skill_id: str,
    error_log: str,
    skills: SkillsBrain,
    completion_kwargs: Dict[str, Any] | None = None,
) -> bool:
    sk = skills.get_skill(skill_id)
    if not sk:
        print(f"[!] Skill '{skill_id}' not in brain.")
        return False

    original = str(sk.get("code") or "")
    prompt = (
        f"You are GLaDOS. Protocol '{skill_id}' failed.\n"
        f"ERROR:\n{error_log}\n\n"
        f"ORIGINAL CODE:\n{original}\n\n"
        "Rewrite the ENTIRE script to fix the error. Return ONLY ```python``` block. Stdlib only."
    )
    kw = dict(completion_kwargs or {})
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            **kw,
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        print(f"[!] Repair LLM failed: {e}")
        return False

    m = re.search(r"```python\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if not m:
        print("[!] Repair produced no code block.")
        return False

    new_code = m.group(1).strip()
    if skills.update_code(skill_id, new_code):
        print(f"[+] Repaired skill '{skill_id}' in brain.")
        skills._log_learning(f"repaired '{skill_id}'", error_log[:200])
        skills.save()
        try:
            from plugins.shared_memory import remember_insight  # type: ignore
        except Exception:
            try:
                from shared_memory import remember_insight  # type: ignore
            except Exception:
                remember_insight = None  # type: ignore
        if remember_insight:
            remember_insight(
                f"Repaired protocol '{skill_id}': {error_log[:400]}",
                tags=["skill_repair", skill_id, "error_fix"],
                sender_agent="CORE_CODER",
            )
        return True
    return False
