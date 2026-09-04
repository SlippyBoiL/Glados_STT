from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from typing import Any, Callable, Optional, Tuple

from glados_paths import REPO_ROOT, resolve_plugins_dir


def _think(think_fn: Optional[Callable[..., None]], phase: str, msg: str) -> None:
    if think_fn:
        try:
            think_fn(phase, msg)
        except Exception:
            pass


def _git_root(cfg: dict) -> str:
    root = str(cfg.get("glados_repo_root") or REPO_ROOT)
    return os.path.abspath(root)


def _is_git_push_request(text: str) -> bool:
    low = (text or "").lower()
    if "github" not in low and "git" not in low:
        return False
    return any(
        p in low
        for p in (
            "push",
            "upload",
            "publish",
            "commit and push",
            "push the project",
            "push to github",
            "push to git",
        )
    )


def _run_git_push(cwd: str, think_fn: Optional[Callable[..., None]] = None) -> Tuple[bool, str]:
    _think(think_fn, "admin", f"Running git push in {cwd}")
    if not os.path.isdir(os.path.join(cwd, ".git")):
        return False, f"Not a git repository: {cwd}"

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if status.returncode != 0:
        return False, (status.stderr or status.stdout or "git status failed")[:500]

    dirty = bool((status.stdout or "").strip())
    if dirty:
        _think(think_fn, "admin", "Staging and committing changes before push.")
        subprocess.run(["git", "add", "-A"], cwd=cwd, capture_output=True, text=True, timeout=120)
        commit = subprocess.run(
            ["git", "commit", "-m", "Glados: automated commit before push"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if commit.returncode != 0 and "nothing to commit" not in (commit.stdout or commit.stderr or "").lower():
            return False, (commit.stderr or commit.stdout or "git commit failed")[:500]

    push = subprocess.run(
        ["git", "push"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=180,
    )
    out = ((push.stdout or "") + "\n" + (push.stderr or "")).strip()
    if push.returncode == 0:
        preview = out[-400:] if out else "Push completed."
        return True, f"Git push succeeded. {preview}"

    if "set-upstream" in out.lower() or "upstream" in out.lower():
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        br = (branch.stdout or "main").strip() or "main"
        push2 = subprocess.run(
            ["git", "push", "-u", "origin", br],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=180,
        )
        out2 = ((push2.stdout or "") + "\n" + (push2.stderr or "")).strip()
        if push2.returncode == 0:
            return True, f"Git push succeeded (set upstream {br}). {out2[-400:]}"

    return False, f"Git push failed: {out[:500]}"


def _is_organize_request(text: str) -> bool:
    low = (text or "").lower()
    if not re.search(r"\b(organize|sort|tidy|clean up)\b", low):
        return False
    if any(p in low for p in ("learn how", "learn to", "teach yourself", "figure out how")):
        return False
    return True


def _organize_target_from_text(text: str) -> Optional[str]:
    """Return explicit path, folder alias, or None for Downloads default."""
    m = re.search(r"[a-zA-Z]:\\(?:[^\"'\s?]+)", text or "")
    if m:
        return m.group(0).rstrip(".,;")
    low = (text or "").lower()
    for key in ("downloads", "download", "desktop", "documents", "pictures", "videos", "music"):
        if key in low:
            return "downloads" if key in ("downloads", "download") else key
    return None


def _load_organize_skill(cfg: dict):
    plugins = resolve_plugins_dir(cfg)
    path = os.path.join(plugins, "skill_organize_files.py")
    if not os.path.isfile(path):
        path = os.path.join(plugins, "skill_organize_files.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("skill_organize_files", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["skill_organize_files"] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_organize(
    user_input: str,
    cfg: dict,
    *,
    think_fn: Optional[Callable[..., None]] = None,
    hud_log_fn: Optional[Callable[[str], None]] = None,
    telemetry_path: str = "",
) -> Tuple[bool, str]:
    mod = _load_organize_skill(cfg)
    if mod is None:
        return False, "Organize skill not found (Plugins/skill_organize_files.py)."

    target = _organize_target_from_text(user_input)
    if target and target not in ("downloads", "download") and target in (
        "desktop",
        "documents",
        "pictures",
        "videos",
        "music",
    ):
        target = os.path.join(os.path.expanduser("~"), target.title())

    _think(think_fn, "organize", f"Organizing files in {target or 'Downloads'}…")

    try:
        from action_display import make_action_publisher
    except ImportError:
        try:
            plugins = resolve_plugins_dir(cfg)
            if plugins not in sys.path:
                sys.path.insert(0, plugins)
            from action_display import make_action_publisher
        except ImportError:
            make_action_publisher = None  # type: ignore

    publish = None
    if make_action_publisher:
        publish = make_action_publisher(
            cfg,
            think_fn=think_fn,
            hud_log_fn=hud_log_fn,
            telemetry_path=telemetry_path,
        )

    run_fn = getattr(mod, "run_organize", None) or getattr(mod, "organize_directory_alphabetically", None)
    if not run_fn:
        return False, "Organize skill has no run function."

    msg = run_fn(target, on_progress=publish)
    ok = not str(msg).lower().startswith("error")
    return ok, msg


def _is_phone_call_request(text: str) -> bool:
    low = (text or "").lower()
    if not any(w in low for w in ("call", "dial", "phone", "ring")):
        return False
    return any(
        p in low
        for p in (
            "call me",
            "call my",
            "dial me",
            "dial my",
            "ring me",
            "ring my",
            "call my cell",
            "call my phone",
            "call my mobile",
            "phone me",
            "give me a call",
            "place a call",
            "make a call",
            "call the operator",
        )
    )


def _run_phone_call(
    cfg: dict,
    *,
    think_fn: Optional[Callable[..., None]] = None,
    user_input: str = "",
) -> Tuple[bool, str]:
    """Wake / ring the operator via Inkbox, ntfy, or Twilio."""
    provider = str(
        cfg.get("phone_alert_provider")
        or os.environ.get("PHONE_ALERT_PROVIDER")
        or "inkbox"
    ).strip().lower()

    spoken = (
        "This is GLaDOS. You asked me to call. "
        "Check your phone — I am placing the call now."
    )

    def _try_ntfy() -> Tuple[bool, str]:
        _think(think_fn, "phone", "Sending free ntfy urgent alert…")
        call_url = ""
        try:
            from brain_server.call_routes import call_page_url

            call_url = call_page_url(cfg, reason="operator")
        except Exception:
            call_url = ""
        try:
            from glados_phone.ntfy_alert import push_ntfy_alert
        except Exception as exc:
            return False, f"ntfy module unavailable: {exc}"
        result = push_ntfy_alert(
            cfg,
            title="GLaDOS - incoming call",
            message=spoken + f"\n\nRequest: {(user_input or '')[:160]}",
            priority="urgent",
            click_url=call_url,
            action_label="Answer GLaDOS",
        )
        if result.get("ok"):
            link = result.get("click_url") or call_url
            extra = f" Tap the notification (or open {link}) to talk." if link else ""
            return (
                True,
                f"Ringing you via free ntfy.{extra} ({result.get('detail')})",
            )
        return False, str(result.get("detail") or "ntfy failed")

    def _try_twilio() -> Tuple[bool, str]:
        _think(think_fn, "phone", "Placing outbound Twilio PSTN call…")
        try:
            from glados_phone.emergency import dial_operator
        except Exception as exc:
            return False, f"Phone module unavailable: {exc}"
        result = dial_operator(cfg, message=spoken, wait_for_answer=False)
        to = result.get("to") or cfg.get("twilio_to_number") or "your cell"
        if result.get("ok"):
            return (
                True,
                f"Dialing {to} now via Twilio ({result.get('detail')}). "
                "Answer the phone — I will speak briefly when connected.",
            )
        return False, str(result.get("detail") or "Twilio dial failed")

    def _try_inkbox() -> Tuple[bool, str]:
        _think(think_fn, "phone", "Placing outbound call through GLaDOS on this PC…")
        try:
            from glados_phone.inkbox_call import place_operator_call
        except Exception as exc:
            return False, f"Inkbox module unavailable: {exc}"
        result = place_operator_call(
            cfg,
            user_input=user_input,
            opening_message=spoken,
            purpose="Operator asked GLaDOS to call their cell to verify the Inkbox line.",
        )
        if result.get("ok"):
            extra = result.get("detail") or "queued"
            if result.get("pc_control"):
                return (
                    True,
                    "Dialing your cell. I will be on this machine with local control. "
                    f"Answer when it rings. ({extra})",
                )
            if result.get("task_dispatch"):
                return (
                    True,
                    "Dialing your cell. Inkbox Voice AI will talk on the call. "
                    "When you want this PC to do something, tell it to text GLaDOS — "
                    "I will run that as a prompt here and reply on Telegram. "
                    f"({extra})",
                )
            return (
                True,
                "Dialing. On the call, tell Voice AI to text GLaDOS the computer task. "
                f"({extra})",
            )
        return False, str(result.get("detail") or "Inkbox place-call failed")

    if provider in ("inkbox", "hermes", "hermes-plugin", "voice-ai"):
        return _try_inkbox()

    if provider in ("ntfy", "free", "googlevoice", "google_voice", "google-voice", "gv"):
        return _try_ntfy()

    if provider in ("twilio", "pstn", "dial"):
        return _try_twilio()

    # auto: Inkbox then ntfy then Twilio
    if provider in ("auto", ""):
        ib_ok, ib_msg = _try_inkbox()
        if ib_ok:
            return True, ib_msg
        nt_ok, nt_msg = _try_ntfy()
        if nt_ok:
            return True, nt_msg
        tw_ok, tw_msg = _try_twilio()
        if tw_ok:
            return True, tw_msg
        return (
            False,
            "No phone path ready.\n"
            f"- Inkbox: {ib_msg}\n"
            f"- ntfy: {nt_msg}\n"
            f"- Twilio: {tw_msg}\n"
            "Inkbox setup: hermes inkbox setup (provision a number).",
        )

    return False, (
        f"Unknown phone_alert_provider={provider!r} "
        "(use inkbox, ntfy, or twilio)"
    )



def try_direct_action(
    user_input: str,
    cfg: Optional[dict] = None,
    *,
    think_fn: Optional[Callable[..., None]] = None,
    hud_log_fn: Optional[Callable[[str], None]] = None,
    telemetry_path: str = "",
) -> Tuple[Optional[bool], str]:
    """
    Facility-admin actions without browser/LLM loops.
    Returns (True, msg), (False, err), or (None, "") if not handled.
    """
    cfg = cfg or {}
    text = (user_input or "").strip()
    if not text:
        return None, ""

    if _is_phone_call_request(text):
        return _run_phone_call(cfg, think_fn=think_fn, user_input=text)

    if _is_git_push_request(text):
        _think(think_fn, "admin", "GitHub push requested — executing git directly on this PC.")
        return _run_git_push(_git_root(cfg), think_fn=think_fn)

    if _is_organize_request(text):
        _think(think_fn, "organize", "File organize requested — running alphabetical sort.")
        return _run_organize(
            text,
            cfg,
            think_fn=think_fn,
            hud_log_fn=hud_log_fn,
            telemetry_path=telemetry_path,
        )

    return None, ""
