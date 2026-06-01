from __future__ import annotations

from typing import Any, Dict, Optional


def analyze_user_intent(
    client: Any,
    model: str,
    user_input: str,
    pc_context: str,
    completion_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Clarify what the user means before coding. Returns dict with keys:
    summary, approach, search_queries, success_criteria
    """
    kw = dict(completion_kwargs or {})
    prompt = (
        "You are GLaDOS analyzing a test subject's request before learning a skill.\n"
        f'REQUEST: "{user_input}"\n\n'
        f"PC CONTEXT:\n{pc_context[:2500]}\n\n"
        "Respond in this exact format (plain text, no code):\n"
        "SUMMARY: (one sentence what they want)\n"
        "APPROACH: (numbered steps to accomplish on their PC)\n"
        "SEARCH: (comma-separated web search queries to research how)\n"
        "SUCCESS: (how we know the protocol worked)\n"
    )
    out = {
        "summary": user_input,
        "approach": "",
        "search_queries": user_input,
        "success_criteria": "Script runs and prints useful output.",
    }
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kw,
        )
        raw = r.choices[0].message.content or ""
    except Exception as e:
        out["approach"] = f"Analysis failed: {e}"
        return out

    for line in raw.splitlines():
        low = line.strip()
        if low.upper().startswith("SUMMARY:"):
            out["summary"] = low.split(":", 1)[-1].strip()
        elif low.upper().startswith("APPROACH:"):
            out["approach"] = low.split(":", 1)[-1].strip()
        elif low.upper().startswith("SEARCH:"):
            out["search_queries"] = low.split(":", 1)[-1].strip()
        elif low.upper().startswith("SUCCESS:"):
            out["success_criteria"] = low.split(":", 1)[-1].strip()
    return out
