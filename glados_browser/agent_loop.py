from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from glados_browser.actions import execute_action, initial_navigation_url
from glados_browser.dom_snapshot import capture_page_state
from glados_browser.playwright_session import GladosBrowser
from glados_browser.routing import should_use_browser_agent

PLANNER_SYSTEM = """You are GLaDOS controlling a VISIBLE web browser on the user's PC.
You must operate in a loop: read the page state → choose ONE action → repeat until done.

Output ONLY a single JSON object (no markdown, no prose):
{
  "action": "navigate|click|type|press|scroll|wait|finish",
  "url": "for navigate only",
  "element": "visible link/button/field label for click or type",
  "text": "text to type, OR final answer when action is finish",
  "key": "Enter|Tab|Escape for press",
  "seconds": 2,
  "reason": "brief why"
}

Rules:
- Use "finish" when you can answer the user's goal; put the spoken answer in "text".
- Prefer clicking visible link/button text from the element list.
- For search: type query, press Enter, read results, click best link, read page, finish.
- If a click fails, try scroll or a different element.
- Keep reasons clinical and brief (GLaDOS tone)."""


@dataclass
class AgentResult:
    handled: bool
    message: str
    steps: int = 0


def _parse_action_json(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _plan_action(
    client: Any,
    model: str,
    user_goal: str,
    page_state: str,
    step_log: List[str],
    completion_kwargs: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    history = "\n".join(f"- {s}" for s in step_log[-12:]) or "(none)"
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {
            "role": "user",
            "content": (
                f"USER GOAL:\n{user_goal}\n\n"
                f"PAGE STATE:\n{page_state}\n\n"
                f"PRIOR STEPS:\n{history}\n\n"
                "Next action JSON:"
            ),
        },
    ]
    try:
        r = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            **completion_kwargs,
        )
        raw = (r.choices[0].message.content or "").strip()
        return _parse_action_json(raw)
    except Exception:
        return None


def _summarize_for_user(
    client: Any,
    model: str,
    user_goal: str,
    step_log: List[str],
    page_state: str,
    completion_kwargs: Dict[str, Any],
) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are GLaDOS. Summarize what you found on the web for the test subject. "
                "Plain text, 2–6 sentences, clinical sarcasm. No JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Goal: {user_goal}\n\nSteps:\n"
                + "\n".join(step_log[-15:])
                + f"\n\nFinal page:\n{page_state[:3000]}"
            ),
        },
    ]
    try:
        r = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.6,
            **completion_kwargs,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return ""


def run_browser_agent_turn(
    user_input: str,
    client: Any,
    model: str,
    cfg: Dict[str, Any],
    *,
    think_fn: Optional[Callable[..., None]] = None,
    completion_kwargs: Optional[Dict[str, Any]] = None,
    telemetry_log_fn: Optional[Callable[..., None]] = None,
    telemetry_path: str = "",
    hud_log_fn: Optional[Callable[[str], None]] = None,
) -> AgentResult:
    """
    Core browser cognition loop — visible Playwright window, agentic navigate/click/type.
    Returns handled=False only when Playwright cannot start (caller may fall back).
    """
    kw = dict(completion_kwargs or {})
    max_steps = int(cfg.get("browser_agent_max_steps") or 20)
    step_log: List[str] = []
    final_answer = ""

    def _emit(phase: str, msg: str, **extra: Any) -> None:
        if think_fn:
            try:
                think_fn(phase, msg, **extra)
            except Exception:
                pass
        if hud_log_fn and phase != "browser":
            pass
        short = msg[:200]
        if hud_log_fn:
            try:
                hud_log_fn(f"🌐 {short}")
            except Exception:
                pass
        if telemetry_log_fn and telemetry_path:
            try:
                telemetry_log_fn(
                    telemetry_path,
                    "browser_step",
                    {"phase": phase, "message": msg, **extra},
                )
            except Exception:
                pass

    browser = GladosBrowser(cfg)
    if not browser.start():
        return AgentResult(False, browser.last_error or "Playwright browser failed to start.")

    try:
        page = browser.page
        start_url = initial_navigation_url(user_input)
        _emit("browser", f"Opening visible browser → {start_url[:70]}")
        page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
        step_log.append(f"navigate → {start_url}")

        for step in range(max_steps):
            snapshot = capture_page_state(page)
            action = _plan_action(
                client, model, user_input, snapshot, step_log, kw
            )
            if not action:
                step_log.append("planner returned no JSON — waiting")
                execute_action(page, {"action": "wait", "seconds": 2})
                continue

            reason = str(action.get("reason") or "").strip()
            act = str(action.get("action") or "").lower()
            _emit("browser", f"Step {step + 1}: {act}" + (f" — {reason}" if reason else ""))

            if act == "finish":
                final_answer = str(action.get("text") or action.get("answer") or "").strip()
                step_log.append(f"finish: {final_answer[:120]}")
                break

            ok, msg = execute_action(page, action)
            step_log.append(f"{act}: {msg}")
            _emit("browser", msg, success=ok)

            if not ok:
                step_log.append(f"error: {msg}")

            try:
                page.wait_for_load_state("domcontentloaded", timeout=12000)
            except Exception:
                pass

        if not final_answer:
            snapshot = capture_page_state(page)
            final_answer = _summarize_for_user(
                client, model, user_input, step_log, snapshot, kw
            )

        if not final_answer:
            final_answer = (
                "I navigated the web, but the page refused to yield anything useful. "
                "Typical."
            )

        _emit("browser", "Closing browser.", done=True)
        return AgentResult(True, final_answer, steps=len(step_log))

    except Exception as e:
        return AgentResult(True, f"Browser agent failed mid-task: {e}", steps=len(step_log))
    finally:
        browser.close()


__all__ = ["run_browser_agent_turn", "should_use_browser_agent", "AgentResult"]
