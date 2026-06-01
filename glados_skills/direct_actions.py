from __future__ import annotations

import os
import subprocess
from typing import Any, Callable, Optional, Tuple

from glados_paths import REPO_ROOT


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


def try_direct_action(
    user_input: str,
    cfg: Optional[dict] = None,
    *,
    think_fn: Optional[Callable[..., None]] = None,
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

    return None, ""
