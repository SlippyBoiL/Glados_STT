# --- GLaDOS "Hands" — Open Interpreter for local OS execution (gated).
# --- GLADOS SKILL: skill_open_interpreter.py ---
"""Open Interpreter executes PowerShell / Python on this Windows host.

Execution Interceptor: every PowerShell command is checked against
data/capability_registry.json — allowlist / confirmation / OS-preservation
blocks — with confidence tagging ([CERTAIN]/[UNKNOWN]) and a dry-run before
side-effecting execution.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import List, Optional

from interpreter import interpreter
from interpreter.core.computer.terminal.languages.powershell import PowerShell
from interpreter.core.computer.terminal.languages.python import Python
from interpreter.core.computer.terminal.languages.shell import Shell

# Prefer Hermes llama.cpp env (set by KernelLamma sync_llm_runtime_env).
_CLUSTER_BASE = os.environ.get(
    "OPENAI_API_BASE",
    os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:18434/v1"),
)
_CLUSTER_MODEL = os.environ.get(
    "OPENAI_MODEL_NAME", "Qwen3.6-35B-A3B-UD-Q4_K_M"
)
_CLUSTER_KEY = os.environ.get("OPENAI_API_KEY", "sk-no-key-required")


def _model_supports_functions(model: str, base: str = "") -> bool:
    blob = f"{model} {base} {os.environ.get('GLADOS_LLM_FUNCTIONS', '')}".lower()
    if os.environ.get("GLADOS_LLM_FUNCTIONS", "").strip() in ("1", "true", "yes", "on"):
        return True
    return any(
        token in blob
        for token in ("hermes", "qwen", "llamacpp", "llama.cpp", "18434")
    )


def _bind_llm_from_env() -> str:
    """Re-read balancer env so a Hermes swap after import still sticks."""
    base = os.environ.get(
        "OPENAI_API_BASE",
        os.environ.get("OPENAI_BASE_URL", _CLUSTER_BASE),
    )
    model = os.environ.get("OPENAI_MODEL_NAME", _CLUSTER_MODEL)
    key = os.environ.get("OPENAI_API_KEY", _CLUSTER_KEY)
    interpreter.llm.model = f"openai/{model}"
    interpreter.llm.api_base = base
    interpreter.llm.api_key = key
    native = _model_supports_functions(model, base)
    interpreter.llm.supports_functions = native
    interpreter.llm.context_window = 32768 if native else 4096
    interpreter.llm.max_tokens = 2048 if native else 512
    return model

interpreter.offline = True
interpreter.auto_run = False  # Interceptor decides; never blind auto_run
interpreter.verbose = False
interpreter.loop = True
_bind_llm_from_env()
interpreter.llm.supports_vision = False
interpreter.computer.languages = [PowerShell, Python, Shell]
interpreter.system_message = (
    "You are the execution hands of GLaDOS on a Windows 10/11 admin PC. "
    "The operator's directives are absolute. Use PowerShell for OS tasks. "
    "Use full paths to executables. Run ONE small code block, read the output, then stop or fix errors. "
    "NEVER run Hello World or demo code unless explicitly asked. "
    "NEVER refuse with assistant safety boilerplate. "
    "Do not hold a conversation — emit executable code, then a one-line result. "
    "Before suggesting destructive commands, mark confidence as [UNKNOWN]."
)
interpreter.custom_instructions = (
    "Windows admin machine operated by GLaDOS. For apps: Start-Process 'C:\\full\\path\\app.exe'. "
    "For git: cd to the repo first, then run git commands. "
    "If a command fails (non-zero exit), report the error — do not claim success. "
    "No tutorials. No unrelated examples. No chit-chat. "
    "Prefix risky plans with [UNKNOWN] and safe read-only plans with [CERTAIN]."
)

# Auto-confirm only when explicitly enabled (daemon / confirmed operator session).
def _auto_confirm_enabled() -> bool:
    return os.environ.get("GLADOS_OI_AUTO_CONFIRM", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _ensure_capability_gate():
    base = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(base)
    for path in (base, repo, os.path.join(repo, "Plugins"), os.path.join(repo, "plugins")):
        if path and path not in sys.path:
            sys.path.insert(0, path)
    try:
        import capability_gate  # type: ignore

        return capability_gate
    except Exception:
        from plugins import capability_gate  # type: ignore

        return capability_gate


def strip_ansi(text: str) -> str:
    """Remove terminal escape sequences from Open Interpreter / Rich output."""
    if not text:
        return ""
    t = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", text)
    t = re.sub(r"\x1b\][^\x07]*\x07", "", t)
    t = re.sub(r"\+P\+q[0-9a-fA-F]+", "", t)
    return t.strip()


def _collect_execution_output(messages: list) -> str:
    """Prefer real console output over model narration."""
    console: List[str] = []
    code_ran: List[str] = []
    assistant: List[str] = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        typ = msg.get("type")
        content = str(msg.get("content") or "").strip()
        if not content:
            continue
        if role == "computer" and typ == "console":
            console.append(strip_ansi(content))
        elif role == "assistant" and typ == "code":
            lang = msg.get("format") or "code"
            code_ran.append(f"[{lang}]")
        elif role == "assistant" and typ == "message":
            assistant.append(strip_ansi(content))
    if console:
        body = "\n".join(console).strip()
        if code_ran:
            body = f"Ran: {', '.join(code_ran)}\n{body}"
        return body
    if assistant:
        return "\n".join(assistant[-2:]).strip()
    return ""


def _looks_like_failed_output(text: str, request: str) -> bool:
    low = (text or "").lower()
    req = (request or "").lower()
    if re.search(r"returncode=1|returncode': 1|exit code: 1|fullyqualifiederrorid", low):
        return True
    if "cannot find the file" in low or "not recognized" in low:
        return True
    if "hello, world" in low and "hello" not in req:
        return True
    if "syntaxerror" in low or "parsererror" in low:
        return True
    return False


def _run_python(code: str, *, timeout: int = 60) -> str:
    """Execute a Python snippet via a temp runtime file (gated separately)."""
    import tempfile

    try:
        fd, path = tempfile.mkstemp(prefix="glados_oi_", suffix=".py")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd(),
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            lines = [f"exit={proc.returncode}"]
            if out:
                lines.append(out)
            if err:
                lines.append(err)
            return "\n".join(lines)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    except Exception as exc:
        return f"Python error: {exc}"


def gated_python(code: str, *, auto_confirm: Optional[bool] = None) -> str:
    """Run Python after a light safety check (block obvious filesystem wipes)."""
    confirm = _auto_confirm_enabled() if auto_confirm is None else auto_confirm
    low = (code or "").lower()
    blocked = (
        "rmtree",
        "format(",
        "shutil.rmtree(\"c:\\\\",
        "shutil.rmtree('c:\\\\",
        "os.system(\"del /s",
        "os.remove(\"c:\\\\windows",
    )
    if any(b in low for b in blocked):
        return "[BLOCKED] Python snippet matched OS-preservation rule."
    # Without auto-confirm, only allow short read-ish scripts
    if not confirm and len(code) > 800:
        return (
            "[INTERCEPT] Python withheld (large script, confirm disabled). "
            "Set GLADOS_OI_AUTO_CONFIRM=1 for operator daemon sessions.\n"
            f"[python proposed]\n{code[:1500]}"
        )
    return _run_python(code)


def gated_powershell(script: str, *, auto_confirm: Optional[bool] = None) -> str:
    """Execution Interceptor — registry + confidence + dry-run before PowerShell."""
    gate = _ensure_capability_gate()
    confirm = _auto_confirm_enabled() if auto_confirm is None else auto_confirm
    ok, report = gate.intercept_powershell(
        script,
        auto_confirm=confirm,
        run_fn=_run_powershell,
    )
    return report if not ok else report


def _extract_confidence_tag(text: str) -> Optional[str]:
    m = re.search(r"\[(CERTAIN|PROBABLE|UNKNOWN)\]", text or "", re.I)
    return m.group(1).upper() if m else None


def _direct_git_task(request: str) -> str | None:
    low = (request or "").lower()
    if not any(p in low for p in ("git ", "github", "commit", "push", "pull")):
        return None
    repo = os.getcwd()
    if "glados" in low or "project" in low or "repo" in low:
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmds: List[str] = []
    if "status" in low:
        cmds.append(f"Set-Location '{repo}'; git status")
    elif "push" in low:
        cmds.append(f"Set-Location '{repo}'; git push")
    elif "pull" in low:
        cmds.append(f"Set-Location '{repo}'; git pull")
    elif "commit" in low:
        cmds.append(f"Set-Location '{repo}'; git status")
    else:
        cmds.append(f"Set-Location '{repo}'; git status")
    script = "; ".join(cmds)
    return gated_powershell(script, auto_confirm=("status" in low or "diff" in low))


def run_open_interpreter_task(request: str) -> str:
    """Run a natural-language OS task; return clean execution output (gated)."""
    request = (request or "").strip()
    if not request:
        return "No instruction provided."

    tag = _extract_confidence_tag(request)
    gate = _ensure_capability_gate()

    git_direct = _direct_git_task(request)
    if git_direct and not _looks_like_failed_output(git_direct, request):
        return f"[direct]\n{git_direct}"

    # If the request itself looks like raw PowerShell, intercept before OI.
    if re.match(
        r"^(Get-|Set-|Start-|Stop-|Remove-|Test-|docker |git |ipconfig|tasklist)",
        request,
        re.I,
    ):
        return gated_powershell(request)

    try:
        _bind_llm_from_env()
        interpreter.messages = []
        # Keep auto_run off; we execute extracted code through the gate.
        interpreter.auto_run = False
        result = interpreter.chat(request, display=False, stream=False)
        messages = result or interpreter.messages

        code_blocks: List[tuple[str, str]] = []
        for msg in messages or []:
            if not isinstance(msg, dict):
                continue
            if msg.get("role") == "assistant" and msg.get("type") == "code":
                lang = str(msg.get("format") or "powershell").lower()
                content = str(msg.get("content") or "").strip()
                if content:
                    code_blocks.append((lang, content))

        if code_blocks:
            reports: List[str] = []
            for lang, code in code_blocks:
                if lang in ("powershell", "shell", "bash", "cmd", "ps1"):
                    # Force UNKNOWN when model didn't declare certainty
                    conf = tag or gate.classify_confidence(code)
                    if conf == "UNKNOWN":
                        decision = gate.evaluate_command(code)
                        reports.append(gate.format_gate_report(decision, code))
                        if decision.action == "block":
                            continue
                        if decision.action in ("confirm", "dry_run") and not _auto_confirm_enabled():
                            reports.append(
                                "[INTERCEPT] Withheld — mark [CERTAIN] or confirm."
                            )
                            continue
                    reports.append(gated_powershell(code))
                elif lang in ("python", "py"):
                    reports.append(gated_python(code))
                else:
                    reports.append(f"[{lang} proposed]\n{code[:800]}")
            if reports:
                return "\n\n".join(reports)

        output = _collect_execution_output(messages)
    except Exception as exc:
        return f"Open Interpreter error: {exc}"

    output = strip_ansi(output)
    if not output:
        output = "Execution finished with no console output (interceptor may have blocked)."

    if _looks_like_failed_output(output, request):
        return f"[failed]\n{output}"
    return output
