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
