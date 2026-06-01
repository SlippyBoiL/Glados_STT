from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional

from glados_skills.ai_council import Advisor, build_advisors, council_consult
from glados_skills.intent import analyze_user_intent
from glados_skills.research import infer_search_query, research_for_learning
from glados_skills.skills_brain import SkillsBrain


def _extract_python(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


def _triggers_from_request(user_input: str) -> list[str]:
    low = (user_input or "").lower().strip()
    triggers = [low[:120]] if low else []
    for strip_prefix in (
        "can you ",
        "could you ",
        "would you ",
        "please ",
        "hey glados ",
        "glados ",
        "i need you to ",
        "i want you to ",
    ):
        if low.startswith(strip_prefix):
            short = low[len(strip_prefix) :].strip()
            if len(short) > 8 and short not in triggers:
                triggers.append(short[:120])
    return triggers[:8]


def _attempt_limit(cfg: Dict[str, Any]) -> int:
    """Return 0 for unlimited attempts (no safety cap)."""
    if bool(cfg.get("skills_learn_unlimited_attempts", True)):
        return 0
    if bool(cfg.get("skills_learn_until_success", True)):
        cap = int(cfg.get("skills_learn_safety_cap") or 0)
        return cap if cap > 0 else 0
    n = int(cfg.get("skills_learn_max_attempts") or 0)
    if n <= 0:
        return 0
    return max(n, 2)


def develop_skill_conversational(
    client: Any,
    model_name: str,
    user_input: str,
    skills: SkillsBrain,
    completion_kwargs: Dict[str, Any] | None = None,
    speak_fn: Callable[[str], None] | None = None,
    think_fn: Callable[..., None] | None = None,
    *,
    cfg: Dict[str, Any] | None = None,
    facility_context: str = "",
    max_attempts: int | None = None,
) -> tuple[bool, str]:
    """
    Persistent learning: understand intent → research (same browser) → AI council →
    code → test → repeat until success or safety cap.
    """
    cfg = dict(cfg or {})
    kw = dict(completion_kwargs or {})
    cap = max_attempts if max_attempts is not None else _attempt_limit(cfg)
    use_web = bool(cfg.get("skills_learn_use_web", True))
    advisors = build_advisors(cfg, client, model_name)

    def _say(line: str, phase: str = "learn") -> None:
        if think_fn:
            try:
                think_fn(phase, line)
            except Exception:
                pass
        if speak_fn and line:
            speak_fn(line)

    use_browser_ai = bool(cfg.get("skills_learn_use_browser_ai", True))
    _say(
        "I will not stop until this is learned—I'll clarify what you mean, "
        + (
            "use Gemini and Perplexity in my browser, "
            if use_browser_ai
            else "research and consult advisors, "
        )
        + "and save a working protocol to my brain. No attempt limit.",
        "learn",
    )

    base_context = _gather_context(user_input, cfg, facility_context)
    draft_id: Optional[str] = None
    last_error = ""
    last_code = ""
    research_text = ""
    council_notes = ""
    intent: Dict[str, str] = {}
    search_queries: List[str] = []
    attempt = 0
    pause = float(cfg.get("skills_learn_pause_sec") or 2.0)
    step_pause = float(cfg.get("skills_learn_step_pause_sec") or 5.0)
    if use_browser_ai:
        pause = max(pause, float(cfg.get("skills_learn_browser_cycle_pause_sec") or 8.0))

    while True:
        attempt += 1
        if cap > 0 and attempt > cap:
            break
        _say(f"Learning cycle {attempt}—taking this slowly.", "learn")
        time.sleep(step_pause)

        try:
            from glados_skills.direct_actions import try_direct_action

            if attempt == 1:
                direct_ok, direct_msg = try_direct_action(user_input, cfg, think_fn=think_fn)
                if direct_ok is True:
                    return True, direct_msg
                if direct_ok is False:
                    from glados_skills.direct_actions import _is_git_push_request

                    if _is_git_push_request(user_input):
                        return False, direct_msg
                    last_error = direct_msg
        except Exception:
            pass

        if attempt == 1 or attempt % 4 == 0:
            primary = next((a for a in advisors if a.client and a.model), None)
            if primary:
                intent = analyze_user_intent(
                    primary.client,
                    primary.model,
                    user_input,
                    base_context,
                    completion_kwargs=kw,
                )
                _say(f"I understand: {intent.get('summary', user_input)}", "learn")
                if think_fn:
                    think_fn(
                        "learn",
                        "Intent locked in.",
                        detail=intent.get("summary", "")[:120],
                    )
            raw_q = intent.get("search_queries") or user_input
            search_queries = [q.strip() for q in raw_q.split(",") if q.strip()]
            if not search_queries:
                search_queries = [infer_search_query(user_input)]

        q_index = (attempt - 1) % len(search_queries)
        query = search_queries[q_index] if search_queries else infer_search_query(user_input)

        skip_browser_research = bool(cfg.get("skills_learn_skip_browser_for_direct", True))
        try:
            from glados_skills.direct_actions import try_direct_action

            if try_direct_action(user_input, cfg)[0] is not None:
                skip_browser_research = True
        except Exception:
            pass

        if use_web and not skip_browser_research:
            _say(
                f"Researching in my browser window: {query[:60]}…",
                "research",
            )
            try:
                engine = str(cfg.get("web_search_engine") or "google")
                profile_browser = "chrome"
                try:
                    from facility_brain.deep_scan import load_user_profile

                    profile_browser = str(
                        (load_user_profile() or {}).get("preferred_browser") or "chrome"
                    )
                except Exception:
                    pass
                if profile_browser == "default":
                    profile_browser = "chrome"
                _, research_text = research_for_learning(
                    user_input,
                    open_browser=bool(cfg.get("skills_learn_open_browser", True)),
                    engine=engine,
                    browser=profile_browser,
                    search_query=query,
                    cfg=cfg,
                )
            except Exception as e:
                research_text = f"Web research error: {e}"
            time.sleep(step_pause)

        browser_advisors = [a for a in advisors if a.browser_site]
        api_advisors = [a for a in advisors if a.client and a.model]
        ollama_advisors = [a for a in api_advisors if a.name == "ollama"] or api_advisors[:1]

        need_browser = bool(browser_advisors) and (
            attempt == 1 or attempt % 2 == 1 or bool(last_error)
        )
        if browser_advisors and need_browser:
            advisor = browser_advisors[(attempt - 1) % len(browser_advisors)]
            _say(
                f"Opening {advisor.name}, typing my question, and waiting for the full answer.",
                "learn",
            )
            time.sleep(step_pause)
            council_notes = council_consult(
                advisor,
                user_input,
                intent.get("summary", user_input),
                f"{base_context}\n{research_text}\n{council_notes}",
                last_error,
                completion_kwargs=kw,
                cfg=cfg,
                think_fn=think_fn,
            )
            if think_fn:
                think_fn(
                    "learn",
                    f"{advisor.name} (browser) responded.",
                    detail=council_notes[:80],
                )
            time.sleep(step_pause)

        codegen_advisor = ollama_advisors[0] if ollama_advisors else None
        if codegen_advisor is None:
            codegen_advisor = next((a for a in advisors if a.client and a.model), None)
        time.sleep(pause)
        if not codegen_advisor or not codegen_advisor.client or not codegen_advisor.model:
            last_error = "No local model available for code generation."
            _say("No local Ollama model for code generation.", "learn")
            time.sleep(pause)
            continue

        _say(f"Writing protocol with {codegen_advisor.name}.", "learn")
        code = _generate_protocol(
            codegen_advisor.client,
            codegen_advisor.model,
            user_input,
            intent=intent,
            base_context=base_context,
            research_text=research_text,
            council_notes=council_notes,
            prior_code=last_code,
            prior_error=last_error,
            attempt=attempt,
            kw=kw,
        )

        if not code:
            last_error = "No Python code block returned."
            time.sleep(pause)
            continue

        _say("Saving to skills brain and testing.", "learn")
        desc = intent.get("summary") or (user_input or "Learned task")[:120]
        triggers = _triggers_from_request(user_input)
        try:
            if draft_id and skills.get_skill(draft_id):
                skills.update_code(draft_id, code)
                skill_id = draft_id
            else:
                skill_id = skills.learn(
                    code,
                    desc,
                    triggers=triggers,
                    user_request=user_input,
                    status="learning",
                )
                draft_id = skill_id
        except SyntaxError as e:
            last_error = f"SyntaxError: {e}"
            last_code = code
            time.sleep(pause)
            continue

        output = skills.execute(skill_id)
        if "[SUCCESS]" in output:
            sk = skills.get_skill(skill_id)
            if sk:
                sk["status"] = "active"
                sk["intent"] = intent
                sk["learned_with_web"] = bool(research_text)
                sk["advisors_used"] = [a.name for a in advisors]
                skills.save()
            skills._log_learning(f"learned '{skill_id}' cycle {attempt}", user_input)
            skills.save()
            preview = output.replace("[SUCCESS]", "").strip()[:300]
            _say(
                f"Success. Skill '{skill_id}' is verified and stored in my brain after {attempt} cycles.",
                "learn",
            )
            return True, (
                f"Learned and saved as '{skill_id}' after {attempt} attempt(s). "
                f"{preview or 'Task complete.'}"
            )

        last_error = output.replace("[FAILED]", "").strip()[:1200]
        last_code = code
        sk = skills.get_skill(skill_id)
        if sk:
            sk["status"] = "learning"
            sk["last_error"] = last_error[:500]
            skills.save()
        _say("Test failed. Re-analyzing and trying again—I am not finished.", "learn")
        time.sleep(pause)

    if draft_id:
        sk = skills.get_skill(draft_id)
        if sk:
            sk["status"] = "broken"
            skills.save()

    skills._log_learning(f"stopped after {attempt} cycles (cap={cap})", user_input)
    skills.save()
    _say(
        f"Learning paused after {attempt} cycles (configured cap {cap}). "
        f"Draft '{draft_id}' remains in my brain.",
        "learn",
    )
    return False, (
        f"Paused after {attempt} cycles. Draft: {draft_id or 'none'}. "
        f"Last error: {last_error[:350]}. Ask again to continue."
    )


def _gather_context(user_input: str, cfg: Dict[str, Any], facility_context: str) -> str:
    parts = []
    if facility_context:
        parts.append(f"=== THIS PC ===\n{facility_context}")
    try:
        from memory.interface import retrieve_computer_brain_context

        block = retrieve_computer_brain_context(user_input, cfg, top_k=12)
        if block:
            parts.append(block)
    except Exception:
        pass
    return "\n\n".join(parts)[:5000]


def _generate_protocol(
    client: Any,
    model_name: str,
    user_input: str,
    *,
    intent: Dict[str, str],
    base_context: str,
    research_text: str,
    council_notes: str,
    prior_code: str,
    prior_error: str,
    attempt: int,
    kw: Dict[str, Any],
) -> Optional[str]:
    repair_block = ""
    if prior_error:
        repair_block = (
            f"\nPREVIOUS CODE FAILED:\n```python\n{prior_code[:4000]}\n```\n"
            f"ERROR:\n{prior_error}\n"
        )
    prompt = (
        "You are GLaDOS. Write ONE Python 3 script for the test subject's PC.\n"
        f'ORIGINAL REQUEST: "{user_input}"\n'
        f"INTENT: {intent.get('summary', '')}\n"
        f"APPROACH: {intent.get('approach', '')}\n"
        f"SUCCESS CRITERIA: {intent.get('success_criteria', '')}\n"
        f"ATTEMPT: {attempt}\n"
        f"{base_context}\n"
        f"\nRESEARCH:\n{research_text}\n"
        f"\nADVISOR NOTES:\n{council_notes[:2000]}\n"
        f"{repair_block}\n"
        "Rules: ONE ```python``` block only. Stdlib OK. No kernel.py edits. Print clear results.\n"
    )
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            **kw,
        )
        return _extract_python(response.choices[0].message.content or "")
    except Exception:
        return None


develop_skill = develop_skill_conversational
