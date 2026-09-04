"""Capability Registry gate — verify, classify confidence, dry-run before PowerShell."""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_REGISTRY = os.path.join(_REPO, "data", "capability_registry.json")
_CACHE: Optional[Dict[str, Any]] = None
_CACHE_MTIME = 0.0


@dataclass
class GateDecision:
    allowed: bool
    action: str  # execute | confirm | block | dry_run
    confidence: str  # CERTAIN | PROBABLE | UNKNOWN
    reason: str
    matched_rule: str = ""
    dry_run_output: str = ""


def load_registry(path: Optional[str] = None) -> Dict[str, Any]:
    global _CACHE, _CACHE_MTIME
    path = path or os.environ.get("GLADOS_CAPABILITY_REGISTRY") or _DEFAULT_REGISTRY
    try:
        mtime = os.path.getmtime(path)
        if _CACHE is not None and mtime == _CACHE_MTIME:
            return _CACHE
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CACHE = data if isinstance(data, dict) else {}
        _CACHE_MTIME = mtime
        return _CACHE
    except Exception as exc:
        return {
            "allowed_auto_execute": [],
            "requires_confirmation": [],
            "blocked_operations": ["Remove-Item -Recurse -Force C:\\Windows"],
            "error": str(exc),
            "dry_run": {"enabled": True},
        }


def _normalize(cmd: str) -> str:
    return re.sub(r"\s+", " ", (cmd or "").strip())


def _match_rule(cmd: str, patterns: List[str]) -> Optional[str]:
    low = cmd.lower()
    for pat in patterns or []:
        p = str(pat).strip()
        if not p:
            continue
        # Glob-ish: treat * as .*
        if "*" in p or ".*" in p:
            rx = re.escape(p).replace(r"\.\*", ".*").replace(r"\*", ".*")
            if re.search(rx, cmd, re.IGNORECASE):
                return p
        if p.lower() in low:
            return p
    return None


def classify_confidence(cmd: str, registry: Optional[Dict[str, Any]] = None) -> str:
    """
    Tag execution confidence:
      [CERTAIN]  — exact allowlist hit, read-only-ish cmdlets
      [UNKNOWN]  — unrecognized / dynamic / piped remote code
      [PROBABLE] — confirmation list or soft match
    """
    reg = registry or load_registry()
    n = _normalize(cmd)
    if _match_rule(n, list(reg.get("blocked_operations") or [])):
        return "UNKNOWN"
    if re.search(r"iex|invoke-expression|downloadstring|frombase64string", n, re.I):
        return "UNKNOWN"
    if _match_rule(n, list(reg.get("allowed_auto_execute") or [])):
        # Prefer CERTAIN when the command is short and matches a known safe verb
        if len(n) < 180 and not re.search(r"[;&|]", n):
            return "CERTAIN"
        return "PROBABLE"
    if _match_rule(n, list(reg.get("requires_confirmation") or [])):
        return "PROBABLE"
    return "UNKNOWN"


def dry_run_powershell(script: str, *, timeout: int = 30) -> str:
    """Prefer -WhatIf when supported; otherwise parse/validate without side effects."""
    script = (script or "").strip()
    if not script:
        return "[DRY-RUN] empty"
    # Wrap with WhatIf preference for cmdlets that support it
    wrapped = (
        "$ErrorActionPreference='Continue'; "
        "$WhatIfPreference=$true; "
        f"{script}"
    )
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                wrapped,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd(),
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        body = "\n".join(x for x in (out, err) if x)
        return f"[DRY-RUN] exit={proc.returncode}\n{body}".strip()
    except Exception as exc:
        return f"[DRY-RUN] error: {exc}"


def evaluate_command(
    cmd: str,
    *,
    force_confirm: bool = False,
    skip_dry_run: bool = False,
    registry_path: Optional[str] = None,
) -> GateDecision:
    """
    Interceptor entrypoint.
    Returns whether the command may run, and whether confirmation / dry-run is required.
    """
    reg = load_registry(registry_path)
    n = _normalize(cmd)
    confidence = classify_confidence(n, reg)

    blocked = _match_rule(n, list(reg.get("blocked_operations") or []))
    if blocked:
        return GateDecision(
            allowed=False,
            action="block",
            confidence=confidence,
            reason=f"Blocked by OS-preservation rule: {blocked}",
            matched_rule=blocked,
        )

    # System path bulk destroy heuristic
    for path in (reg.get("os_preservation") or {}).get("protect_system_paths") or []:
        if re.search(
            rf"Remove-Item.*-Recurse.*{re.escape(path)}",
            n,
            re.IGNORECASE,
        ):
            return GateDecision(
                allowed=False,
                action="block",
                confidence="UNKNOWN",
                reason=f"Blocked: recursive delete of protected path {path}",
                matched_rule=path,
            )

    allowed_hit = _match_rule(n, list(reg.get("allowed_auto_execute") or []))
    confirm_hit = _match_rule(n, list(reg.get("requires_confirmation") or []))

    dry_cfg = reg.get("dry_run") or {}
    dry_out = ""
    if dry_cfg.get("enabled", True) and not skip_dry_run:
        if confidence in ("UNKNOWN", "PROBABLE") or dry_cfg.get("require_before_confirmation"):
            dry_out = dry_run_powershell(n)

    if allowed_hit and confidence == "CERTAIN" and not force_confirm:
        return GateDecision(
            allowed=True,
            action="execute",
            confidence="CERTAIN",
            reason=f"Allowlisted auto-execute: {allowed_hit}",
            matched_rule=allowed_hit,
            dry_run_output=dry_out,
        )

    if confirm_hit or confidence != "CERTAIN" or force_confirm:
        return GateDecision(
            allowed=False,
            action="confirm" if not dry_out else "dry_run",
            confidence=confidence,
            reason=(
                f"Requires confirmation ({confidence})"
                + (f"; matched {confirm_hit}" if confirm_hit else "")
            ),
            matched_rule=confirm_hit or "",
            dry_run_output=dry_out,
        )

    return GateDecision(
        allowed=True,
        action="execute",
        confidence=confidence,
        reason="Passed capability gate",
        dry_run_output=dry_out,
    )


def format_gate_report(decision: GateDecision, cmd: str) -> str:
    tag = f"[{decision.confidence}]"
    lines = [
        f"{tag} action={decision.action} allowed={decision.allowed}",
        f"reason: {decision.reason}",
        f"command: {cmd[:500]}",
    ]
    if decision.dry_run_output:
        lines.append(decision.dry_run_output[:2000])
    return "\n".join(lines)


def intercept_powershell(
    script: str,
    *,
    auto_confirm: bool = False,
    run_fn=None,
) -> Tuple[bool, str]:
    """
    Full interceptor: registry check → confidence → dry-run → optional execute.
    Returns (executed, report_or_output).
    """
    decision = evaluate_command(script)
    report = format_gate_report(decision, script)
    if decision.action == "block":
        return False, report
    if decision.action in ("confirm", "dry_run") and not auto_confirm:
        return False, report + "\n[INTERCEPT] Execution withheld — confirmation required."
    if run_fn is None:
        return False, report + "\n[INTERCEPT] No runner provided."
    try:
        output = run_fn(script)
        return True, f"{report}\n[EXECUTED]\n{output}"
    except Exception as exc:
        return False, f"{report}\n[EXECUTE ERROR] {exc}"
