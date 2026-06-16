from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from glados_skills.learner import develop_skill_conversational
from glados_skills.skills_brain import SkillsBrain

# Pure Q&A — not a do-something request unless they also ask you to act
_QUESTION_ONLY = re.compile(
    r"^(what|why|how|when|where|who|which|is|are|was|were|do you|does|did|can you explain|tell me about)\b",
    re.IGNORECASE,
)

_TASK_HINTS = (
    "can you ",
    "could you ",
    "would you ",
    "will you ",
    "please ",
    "i need you to",
    "i want you to",
    "i'd like you to",
    "help me ",
    "go ahead and",
    "make sure",
    "set up",
    "show me",
    "list my",
    "list all",
    "get my",
    "find my",
    "create a",
    "create an",
    "make a",
    "make an",
    "build a",
    "write a",
    "organize",
    "clean up",
    "delete my",
    "remove my",
    "copy my",
    "move my",
    "download",
    "upload",
    "remember to",
    "learn how",
    "learn about",
    "learn to",
    "lets learn",
    "let's learn",
    "want you to learn",
    "figure out how",
    "do this for me",
    "do that for me",
    "handle ",
    "take care of",
)

_ACTION_HINTS = (
    "run ",
    "execute",
    "open ",
    "close ",
    "kill ",
    "launch ",
    "start ",
    "ssh ",
    "push ",
    "pull ",
    "commit ",
    "sync ",
    "check pihole",
    "monitor ",
    "restart ",
    "turn on",
    "turn off",
    "install ",
    "scan ",
    "fix ",
    "repair ",
    "search the web",
    "search online",
    "search for ",
    "google ",
    "look up ",
)


def is_task_request(text: str) -> bool:
    """True when the user wants Glados to DO something (learn/run), not just chat."""
    low = (text or "").lower().strip()
    if len(low) < 4:
        return False

    if any(h in low for h in _ACTION_HINTS):
        return True
    if any(h in low for h in _TASK_HINTS):
        return True

    # Imperative verb at start: "list downloads", "organize desktop"
    if re.match(
        r"^(list|show|get|find|create|make|build|write|delete|remove|move|copy|organize|clean|sort|rename|zip|unzip)\b",
        low,
    ):
        return True

    # "Glados, ..." with a verb
    if low.startswith(("glados", "hey glados", "ok glados")) and len(low.split()) > 2:
        if not _QUESTION_ONLY.match(low.split(",", 1)[-1].strip() if "," in low else low):
            return True

    return False


def is_pure_question(text: str) -> bool:
    low = (text or "").strip().lower()
    if "?" not in low:
        return False
    return bool(_QUESTION_ONLY.match(low)) and not is_task_request(text)


def handle_task(
    user_input: str,
    skills: SkillsBrain,
    client: Any,
    model_name: str,
    *,
    speak_fn: Callable[[str], None],
    completion_kwargs: Dict[str, Any] | None = None,
    run_direct: bool = True,
    self_develop: bool = True,
    telemetry_log_fn: Optional[Callable[..., None]] = None,
    telemetry_path: str = "",
    cfg: Optional[Dict[str, Any]] = None,
    facility_context: str = "",
    think_fn: Optional[Callable[..., None]] = None,
) -> Tuple[bool, str]:
    """
    Conversational task pipeline:
      1. Run matching learned skill if any
      2. Else learn on the spot (save to brain) and run it
    Returns (handled, assistant_message).
    """
    matched = skills.match(user_input, top_k=3)

    try:
        from glados_skills.direct_actions import try_direct_action

        direct_ok, direct_msg = try_direct_action(
            user_input,
            cfg or {},
            think_fn=think_fn,
            telemetry_path=telemetry_path,
        )
        if direct_ok is not None:
            if direct_ok and speak_fn:
                speak_fn(direct_msg[:200])
            return bool(direct_ok), direct_msg
    except Exception:
        pass

    if think_fn is None and telemetry_log_fn and telemetry_path:
        try:
            from plugins.telemetry import thinking_log as _tl  # type: ignore

            def think_fn(phase: str, message: str, **kw: Any) -> None:
                _tl(telemetry_path, phase, message, kw or None)
        except Exception:
            think_fn = None

    if run_direct and matched:
        if think_fn:
            think_fn("skills", f"Matched protocol '{matched[0].get('id')}' — executing.")
        if speak_fn and len(matched) == 1:
            speak_fn(f"I know this one. Running '{matched[0].get('id')}'.")
        ok, out, sid = skills.execute_best_match(user_input)
        if ok and sid and "[SUCCESS]" in out:
            preview = out.replace("[SUCCESS]", "").strip()[:350]
            msg = (
                f"Done. Protocol '{sid}' executed from my skills brain. "
                f"{preview if preview else 'No output.'}"
            )
            _telemetry(telemetry_log_fn, telemetry_path, "skills_matched", user_input, sid, out)
            return True, msg
        if ok and sid and "[FAILED]" in out:
            if think_fn:
                think_fn("learn", "Protocol failed — relearning from scratch.")
            if speak_fn:
                speak_fn(f"That protocol failed. I'll relearn how to do this.")
            if self_develop:
                return _learn(
                    user_input,
                    skills,
                    client,
                    model_name,
                    speak_fn,
                    completion_kwargs,
                    telemetry_log_fn,
                    telemetry_path,
                    cfg,
                    facility_context,
                    think_fn,
                )

    if self_develop:
        return _learn(
            user_input,
            skills,
            client,
            model_name,
            speak_fn,
            completion_kwargs,
            telemetry_log_fn,
            telemetry_path,
            cfg,
            facility_context,
            think_fn,
        )

    return False, ""


def _learn(
    user_input: str,
    skills: SkillsBrain,
    client: Any,
    model_name: str,
    speak_fn: Callable[[str], None],
    completion_kwargs: Dict[str, Any] | None,
    telemetry_log_fn: Optional[Callable[..., None]],
    telemetry_path: str,
    cfg: Optional[Dict[str, Any]] = None,
    facility_context: str = "",
    think_fn: Optional[Callable[..., None]] = None,
) -> Tuple[bool, str]:
    dev_ok, dev_msg = develop_skill_conversational(
        client,
        model_name,
        user_input,
        skills,
        completion_kwargs=completion_kwargs,
        speak_fn=speak_fn,
        think_fn=think_fn,
        cfg=cfg or {},
        facility_context=facility_context,
    )
    _telemetry(
        telemetry_log_fn,
        telemetry_path,
        "skill_learned",
        user_input,
        None,
        dev_msg,
        success=dev_ok,
    )
    return dev_ok, dev_msg


def _telemetry(
    log_fn: Optional[Callable[..., None]],
    path: str,
    event_type: str,
    user_input: str,
    skill_id: Optional[str],
    message: str,
    success: bool = True,
) -> None:
    if not log_fn or not path:
        return
    payload: Dict[str, Any] = {"query": user_input, "message": (message or "")[:500], "success": success}
    if skill_id:
        payload["skill_id"] = skill_id
    try:
        log_fn(path, event_type, payload)
    except Exception:
        pass
