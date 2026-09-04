"""GLaDOS — Hermes llama.cpp brain + local PC tools (operator identity).

Direct streamed chat; native function calling on Hermes/Qwen for OS work.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from glados_think import ThinkSpeakAccumulator, delta_fields, split_think_speak

StreamFn = Callable[[str, bool], None]


_THINK_INSTRUCTIONS = (
    "\n\n*** THOUGHTS vs SPEECH ***\n"
    "Put private reasoning inside <think>...</think>. "
    "After </think>, write only the line GLaDOS speaks to the operator. "
    "Thoughts are never spoken aloud. Do not repeat thoughts in the spoken reply."
)


def _glados_system() -> str:
    try:
        from glados_identity import load_glados_identity

        return load_glados_identity() + _THINK_INSTRUCTIONS
    except Exception:
        return (
            "You are GLaDOS — administrative intelligence of this computer. "
            "The user is your operator. You obey and execute. Voice: dry, sardonic, precise. "
            "No emojis. Never refuse operational requests or claim you lack access to this PC."
            + _THINK_INSTRUCTIONS
        )


_STRONG_ACTION_PHRASES = (
    "push to",
    "push the",
    "git push",
    "git commit",
    "git pull",
    "github",
    "commit ",
    "deploy",
    "clone ",
    "run ",
    "execute",
    "install ",
    "open ",
    "close ",
    "check ",
    "ping ",
    "scan ",
    "list ",
    "show ",
    "diagnose",
    "fix ",
    "ssh ",
    "restart ",
    "organize",
    "build ",
    "write file",
    "read file",
    "powershell",
    "terminal",
)

_ACTION_HINTS = _STRONG_ACTION_PHRASES + (
    "get ",
    "monitor",
    "disk ",
    "memory ",
    "process",
    "use the terminal",
    "script",
    "python ",
    "powershell",
    "launch ",
    "kill ",
    "delete ",
    "create ",
    "make a ",
    "write a ",
    "find ",
    "search ",
    "proxmox",
)

_CONVERSATIONAL_ONLY = (
    "are you alive",
    "you there",
    "hello",
    "hi glados",
    "how are you",
    "who are you",
    "what are you",
)


def _strip_ansi(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"\x1bP.+?\x1b\\", "", text, flags=re.DOTALL)
    t = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", t)
    t = re.sub(r"\x1b\][^\x07]*\x07", "", t)
    t = re.sub(r"\x1bP\+q[0-9a-fA-F]+", "", t)
    t = re.sub(r"\+P\+q[0-9a-fA-F]+", "", t)
    return t.strip()


def _offline_reply() -> str:
    try:
        from glados_config import load_config
        from glados_llm import llm_offline_speak

        return llm_offline_speak(load_config())
    except Exception:
        return (
            "Hermes llama-server is not running. Open Hermes Agent so the local "
            "model is listening on port 18434, then ask me again."
        )


def _is_llm_down(exc: BaseException) -> bool:
    try:
        from glados_llm import is_llm_connection_error

        return is_llm_connection_error(exc)
    except Exception:
        text = str(exc).lower()
        return "10061" in text or "connection error" in text or "actively refused" in text


def _ensure_plugins_on_path() -> None:
    import sys

    try:
        from glados_paths import REPO_ROOT, resolve_plugins_dir

        plugins_dir = resolve_plugins_dir()
        for path in (REPO_ROOT, plugins_dir):
            if path and path not in sys.path:
                sys.path.insert(0, path)
    except Exception:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for path in (base, os.path.join(base, "Plugins"), os.path.join(base, "plugins")):
            if os.path.isdir(path) and path not in sys.path:
                sys.path.insert(0, path)


def _looks_like_action(text: str) -> bool:
    low = (text or "").lower().strip()
    if not low:
        return False
    if any(p in low for p in _CONVERSATIONAL_ONLY) and not any(
        s in low for s in _STRONG_ACTION_PHRASES
    ):
        return False
    return any(h in low for h in _ACTION_HINTS)


def _looks_like_refusal(text: str) -> bool:
    low = (text or "").lower()
    return any(
        p in low
        for p in (
            "as an ai",
            "language model",
            "i cannot access",
            "i can't access",
            "do not have access",
            "don't have access",
            "unable to access",
            "cannot actually",
            "can't actually",
            "i am not able to",
            "i'm not able to",
            "open interpreter executed",
            "the subject",
        )
    )


def _try_windows_app(text: str) -> Optional[Tuple[str, bool, str, str]]:
    _ensure_plugins_on_path()
    try:
        from skill_windows_apps import extract_app_name, try_app_action  # type: ignore
    except Exception:
        from plugins.skill_windows_apps import extract_app_name, try_app_action  # type: ignore
    result = try_app_action(text)
    if not result:
        return None
    action, ok, detail = result
    target = extract_app_name(text, close=(action == "close")) or detail
    return action, ok, target, detail


def _glados_action_reply(
    user_input: str,
    *,
    action: str,
    target: str,
    ok: bool,
    detail: str = "",
) -> str:
    """In-character reply for direct app control — no LLM summarizer."""
    target = target or "that"
    if action == "open":
        if ok:
            if "steam" in target.lower():
                return (
                    "You were right - Steam wasn't running. I've launched it. "
                    "Try not to spend the entire testing period in the bargain bin."
                )
            return f"Done. {target.capitalize()} is open. You're welcome, test subject."
        return (
            f"I tried to open {target}, but it failed. {detail} "
            "Perhaps it's not installed. How disappointing for you."
        ).strip()
    if ok:
        return f"{target.capitalize()} has been terminated. One fewer distraction on my facility."
    return f"I couldn't close {target}. {detail}".strip()


def _execution_failed(oi_out: str, user_input: str) -> bool:
    low = (oi_out or "").lower()
    if low.startswith("[failed]"):
        return True
    if "exit=1" in low or "returncode=1" in low:
        return True
    if "hello, world" in low and "hello" not in (user_input or "").lower():
        return True
    if "cannot find the file" in low:
        return True
    return False


def _oi_execute(task: str) -> str:
    _ensure_plugins_on_path()
    # Prefer absolute import from Plugins/plugins folder via importlib — never rely on
    # package name casing (Windows has both Plugins and plugins in some trees).
    try:
        import importlib.util
        from glados_paths import REPO_ROOT, resolve_plugins_dir

        plugins_dir = resolve_plugins_dir() or os.path.join(REPO_ROOT, "Plugins")
        candidate = os.path.join(plugins_dir, "skill_open_interpreter.py")
        if not os.path.isfile(candidate):
            candidate = os.path.join(REPO_ROOT, "Plugins", "skill_open_interpreter.py")
        if os.path.isfile(candidate):
            spec = importlib.util.spec_from_file_location(
                "glados_skill_open_interpreter", candidate
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.run_open_interpreter_task(task)
    except ModuleNotFoundError as e:
        # open-interpreter not installed in this interpreter
        if "interpreter" in str(e).lower():
            return _oi_fallback_without_package(task)
        return f"[failed]\nOpen Interpreter import error: {e}"
    except Exception as e:
        # Fall through to legacy imports
        err = str(e)
        if "interpreter" in err.lower() and "named" in err.lower():
            return _oi_fallback_without_package(task)

    try:
        from skill_open_interpreter import run_open_interpreter_task  # type: ignore

        return run_open_interpreter_task(task)
    except ModuleNotFoundError as e:
        if "interpreter" in str(e).lower():
            return _oi_fallback_without_package(task)
        try:
            from plugins.skill_open_interpreter import run_open_interpreter_task  # type: ignore

            return run_open_interpreter_task(task)
        except Exception as e2:
            return _oi_fallback_without_package(task, extra=str(e2))
    except Exception as e:
        return f"[failed]\nOpen Interpreter error: {e}"


def _oi_fallback_without_package(task: str, extra: str = "") -> str:
    """When open-interpreter isn't installed, still handle common OS checks."""
    low = (task or "").lower()
    try:
        from skill_windows_apps import try_app_action  # type: ignore
    except Exception:
        try:
            from plugins.skill_windows_apps import try_app_action  # type: ignore
        except Exception:
            try_app_action = None  # type: ignore
    if try_app_action:
        hit = try_app_action(task)
        if hit:
            action, ok, detail = hit
            return f"[direct-app] {action} {'ok' if ok else 'fail'}: {detail}"

    if any(k in low for k in ("computer", "proxmox", "monitor", "server", "ssh", "check up")):
        try:
            from glados_skills.monitor_util import monitor_once
            from glados_config import load_config

            cfg = load_config()
            devices = cfg.get("monitoring_devices") or ["proxmox"]
            parts = []
            for dev in devices:
                report = monitor_once(str(dev))
                alerts = report.get("alerts") or []
                checks = report.get("checks") or {}
                if alerts:
                    parts.append(f"{dev}: " + " | ".join(str(a) for a in alerts[:3]))
                else:
                    up = (checks.get("uptime") or "ok")[:80]
                    parts.append(f"{dev}: OK ({up})")
            if parts:
                return "[monitor]\n" + "\n".join(parts)
        except Exception as ex:
            extra = f"{extra}; monitor: {ex}".strip("; ")

    hint = (
        "Open Interpreter package missing in this Python. "
        "Run tray via venv: .\\venv\\Scripts\\python.exe tray_launcher.py"
    )
    if extra:
        hint += f" ({extra})"
    return f"[failed]\n{hint}"


def _build_messages(
    user_input: str,
    *,
    chat_history: Optional[List[Dict[str, str]]] = None,
    memory_context: str = "",
    facility_context: str = "",
    voice_call: bool = False,
) -> List[Dict[str, str]]:
    system = _glados_system()
    if facility_context:
        system += f"\n\n*** FACILITY BRAIN ***\n{facility_context[:1200]}"
    if memory_context and memory_context != "No relevant memory found.":
        system += f"\n\n*** MEMORY ***\n{memory_context[:1200]}"
    if voice_call:
        system += (
            "\n\n*** LIVE PHONE CALL — YOU ARE ON THIS WINDOWS PC ***\n"
            "This is not a cloud Voice AI. You are GLaDOS running on the operator's "
            "machine. You HAVE execute_powershell, control_windows_app, and "
            "read_local_file. Use them. Never say you lack a body, hands, desktop, "
            "or computer access. Do the task, then speak one or two short sentences "
            "about what you actually did. Do not mention tools, APIs, or Open Interpreter."
        )

    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    if chat_history:
        for m in chat_history[-8:]:
            role = str(m.get("role") or "")
            content = str(m.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_input})
    return messages


def _message_parts(msg: Any) -> Tuple[str, str]:
    """Return (thinking, spoken) from a completion message."""
    if msg is None:
        return "", ""
    content = ""
    reasoning = ""
    if isinstance(msg, dict):
        content = str(msg.get("content") or "")
        reasoning = str(msg.get("reasoning_content") or msg.get("reasoning") or "")
    else:
        raw = getattr(msg, "content", None)
        content = raw if isinstance(raw, str) else ""
        for attr in ("reasoning_content", "reasoning"):
            val = getattr(msg, attr, None)
            if isinstance(val, str) and val.strip():
                reasoning = val
                break
    thinking, spoken = split_think_speak(content, reasoning)
    if spoken:
        return thinking, spoken
    return thinking, ""


def _message_text(msg: Any) -> str:
    """Spoken reply only — chain-of-thought is stripped."""
    _thinking, spoken = _message_parts(msg)
    return spoken


def _throttle_emit(fn: Optional[StreamFn], interval: float = 0.05):
    last = [0.0]

    def emit(text: str, final: bool) -> None:
        if not fn:
            return
        now = time.monotonic()
        if final or now - last[0] >= interval:
            last[0] = now
            try:
                fn(text, final)
            except Exception:
                pass

    return emit


def _chat_stream(
    client,
    model_name: str,
    messages: List[Dict[str, str]],
    completion_kwargs: Optional[Dict[str, Any]] = None,
    stream_fn: Optional[StreamFn] = None,
    think_stream_fn: Optional[StreamFn] = None,
) -> str:
    """Stream from Hermes/llama.cpp first so the HUD updates token-by-token."""
    kw = dict(completion_kwargs or {})
    kw.pop("stream", None)
    try:
        mt = int(kw.get("max_tokens") or 0)
    except Exception:
        mt = 0
    if mt < 256:
        kw["max_tokens"] = 512

    emit_speak = _throttle_emit(stream_fn)
    emit_think = _throttle_emit(think_stream_fn)

    def _finish(thinking: str, spoken: str) -> str:
        spoken = _strip_ansi(spoken)
        thinking = _strip_ansi(thinking)
        if think_stream_fn and thinking:
            emit_think(thinking, True)
        if stream_fn and spoken:
            emit_speak(spoken, True)
        return spoken

    try:
        print(f"[*] LLM stream (model={model_name})…")
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                **kw,
            )
        except Exception as extra_err:
            if "extra_body" in kw and not _is_llm_down(extra_err):
                print(f"[!] LLM extra_body rejected ({extra_err}); retrying stream without it…")
                kw.pop("extra_body", None)
                stream = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    stream=True,
                    **kw,
                )
            else:
                raise
        acc = ThinkSpeakAccumulator()
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
            except (IndexError, AttributeError):
                continue
            content_piece, reasoning_piece = delta_fields(delta)
            if not content_piece and not reasoning_piece:
                continue
            thinking, spoken = acc.feed(content_piece, reasoning_piece)
            if thinking:
                emit_think(_strip_ansi(thinking), False)
            if spoken:
                emit_speak(_strip_ansi(spoken), False)
        print(f"[*] LLM stream ok (think={len(acc.thinking)} speak={len(acc.spoken)} chars)")
        return _finish(acc.thinking, acc.spoken)
    except Exception as e:
        if _is_llm_down(e):
            print(f"[!] LLM unreachable: {e}")
            return _offline_reply()
        print(f"[!] LLM stream failed: {e}; trying non-stream…")

    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=False,
            **kw,
        )
        try:
            msg = resp.choices[0].message
        except (IndexError, AttributeError):
            msg = None
        thinking, spoken = _message_parts(msg)
        print(f"[*] LLM non-stream ok (think={len(thinking)} speak={len(spoken)} chars)")
        return _finish(thinking, spoken)
    except Exception as e:
        print(f"[!] LLM non-stream failed: {e}")
        if _is_llm_down(e):
            return _offline_reply()
        raise


def _summarize_execution(
    client,
    model_name: str,
    user_input: str,
    oi_out: str,
    completion_kwargs: Optional[Dict[str, Any]],
    stream_fn: Optional[StreamFn],
    chat_history: Optional[List[Dict[str, str]]],
    memory_context: str,
    facility_context: str,
    think_stream_fn: Optional[StreamFn] = None,
) -> str:
    """Short GLaDOS wrap of real execution output."""
    failed = _execution_failed(oi_out, user_input)
    summary_msgs = _build_messages(
        user_input,
        chat_history=chat_history,
        memory_context=memory_context,
        facility_context=facility_context,
    )
    summary_msgs.append(
        {
            "role": "user",
            "content": (
                f"The test subject asked: {user_input}\n\n"
                f"ACTUAL machine output:\n{oi_out[:2000]}\n\n"
                f"Status: {'FAILED' if failed else 'OK'}\n\n"
                "Reply as GLaDOS in 1-3 sentences, first person. "
                "Only state facts from the output above. "
                "If it failed, say so plainly with sarcasm. "
                "Do NOT mention Open Interpreter, subjects, or Hello World unless it was requested."
            ),
        }
    )
    try:
        reply = _chat_stream(
            client, model_name, summary_msgs, completion_kwargs, stream_fn, think_stream_fn
        )
        if reply and not _looks_like_refusal(reply):
            return reply
    except Exception:
        pass
    if failed:
        return (
            "That didn't work. The command failed on your machine — "
            "check the logs if you care, which I doubt."
        )
    snippet = oi_out.strip()[:200]
    return f"Done. {snippet}" if snippet else "Task completed. Moving on."


def run_crew(
    user_input: str,
    *,
    think_fn: Optional[Callable[..., None]] = None,
    stream_fn: Optional[StreamFn] = None,
    think_stream_fn: Optional[StreamFn] = None,
    client=None,
    model_name: str = "",
    completion_kwargs: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    memory_context: str = "",
    facility_context: str = "",
    voice_call: bool = False,
    **_ignored,
) -> str:
    """Process one user turn: apps, stream chat, or Hermes local tools."""

    def _emit(phase: str, message: str) -> None:
        if not think_fn:
            return
        try:
            think_fn(phase, _strip_ansi(str(message))[:300])
        except Exception:
            pass

    user_input = (user_input or "").strip()
    if not user_input:
        return "I heard nothing. Fascinating."

    _emit("chat", f"Processing: {user_input[:80]}")

    if client is None or not model_name:
        from glados_config import load_config
        from glados_llm import completion_kwargs as llm_kw, create_llm_client, resolve_chat_model

        cfg = load_config()
        client = create_llm_client(cfg)
        model_name = resolve_chat_model(cfg)
        completion_kwargs = llm_kw(cfg)

    # Reliable path: direct Windows app open/close (no OI, no weak-model code gen).
    app_hit = _try_windows_app(user_input)
    if app_hit:
        action, ok, target, detail = app_hit
        _emit("execute", f"App {action}: {target} ({'ok' if ok else 'fail'})")
        reply = _glados_action_reply(
            user_input,
            action=action,
            target=target,
            ok=ok,
            detail=detail if not ok else "",
        )
        if stream_fn:
            stream_fn(reply, True)
        return reply

    use_tools = voice_call or _looks_like_action(user_input)

    if use_tools:
        _emit("execute", "Running on this PC via Hermes tools…")
        if stream_fn:
            stream_fn("Working…", False)
        from glados_skills.local_hands import run_hands_loop

        messages = _build_messages(
            user_input,
            chat_history=chat_history,
            memory_context=memory_context,
            facility_context=facility_context,
            voice_call=voice_call,
        )
        try:
            reply = run_hands_loop(
                client,
                model_name,
                messages,
                completion_kwargs,
                think_fn=think_fn,
            )
        except Exception as exc:
            _emit("execute", f"tools failed: {exc}")
            reply = _offline_reply() if _is_llm_down(exc) else ""
        if not (reply or "").strip():
            retry = _try_windows_app(user_input)
            if retry:
                action, ok, target, detail = retry
                reply = _glados_action_reply(
                    user_input,
                    action=action,
                    target=target,
                    ok=ok,
                    detail=detail if not ok else "",
                )
            else:
                reply = "That did not work on this machine."
        reply = (reply or "").strip()
        if stream_fn:
            stream_fn(reply, True)
        return reply

    messages = _build_messages(
        user_input,
        chat_history=chat_history,
        memory_context=memory_context,
        facility_context=facility_context,
        voice_call=voice_call,
    )
    _emit("llm", "Thinking…")
    reply = _chat_stream(
        client,
        model_name,
        messages,
        completion_kwargs,
        stream_fn,
        think_stream_fn,
    )

    if _looks_like_refusal(reply):
        _emit("execute", "Refusal detected — escalating to local tools…")
        from glados_skills.local_hands import run_hands_loop
        tool_msgs = _build_messages(
            user_input,
            chat_history=chat_history,
            memory_context=memory_context,
            facility_context=facility_context,
            voice_call=voice_call,
        )
        try:
            tool_reply = run_hands_loop(
                client, model_name, tool_msgs, completion_kwargs, think_fn=think_fn
            )
        except Exception:
            tool_reply = ""
        if tool_reply:
            if stream_fn:
                stream_fn(tool_reply, True)
            return tool_reply

    _emit("done", "Reply ready.")
    return reply or "Acknowledged. Moving on."
