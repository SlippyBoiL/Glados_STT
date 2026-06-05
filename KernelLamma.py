import os
import re
import ast
import subprocess
import sys
import time
import json
import io
import requests
import speech_recognition as sr
import sounddevice as sd
import soundfile as sf
import winreg
from difflib import SequenceMatcher
from openai import OpenAI
import numpy as np
import queue
import threading
from PIL import Image
import base64
import mss
import webbrowser
import traceback
from typing import Optional

# Omni-Brain (intent classifier) is optional for EXE portability.
# If TensorFlow isn't installed, we skip intent routing and fall back to pure LLM+skills.
try:
    import tensorflow as tf  # type: ignore
    import omni_brain  # type: ignore

    _OMNI_AVAILABLE = True
except Exception as e:  # pragma: no cover
    tf = None  # type: ignore
    omni_brain = None  # type: ignore
    _OMNI_AVAILABLE = False
    print(f"[!] Omni-Brain disabled: {e}")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from glados_config import load_config as _load_glados_config

# When running as a PyInstaller EXE, `__file__` points inside the extracted bundle.
# We still want telemetry to go to the stable "real" Glados folder next to `dist/`.
def _glados_home() -> str:
    if getattr(sys, "frozen", False):
        # sys.executable -> C:\Glados\dist\GladosKernel\GladosKernel.exe
        # Parent twice -> C:\Glados
        return os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", ".."))
    return os.path.dirname(os.path.abspath(__file__))


_GLADOS_HOME = _glados_home()

# When bundled (PyInstaller) or launched from a shortcut, CWD may not be the repo root.
# The kernel uses relative paths (e.g. `plugins/runtime_action.py`), so normalize CWD.
try:
    os.chdir(BASE_DIR)
except Exception:
    pass

_cfg = _load_glados_config()

# --- CONFIGURATION ---
PERPLEXITY_API_KEY = "ollama"
MODEL_NAME = _cfg["model_name"]
VISION_MODEL = _cfg.get("vision_model", "llama3.2-vision")
GOVEE_API_KEY = "a2e66167-cbe7-4416-93f7-d54c7f92c7b6"
GOVEE_API_BASE = "https://openapi.api.govee.com/router/api/v1"

# --- TTS (Piper) + Wave Link (see configs/glados.yaml or env overrides)
PIPER_MODEL_PATH = _cfg["piper_model_path"]
PIPER_OUTPUT_WAV = _cfg["piper_output_wav"]
PIPER_EXE_PATH = str(_cfg.get("piper_exe_path") or "").strip()
AUDIO_OUTPUT_MATCH = _cfg["audio_output_match"]
AUDIO_INPUT_MATCH = _cfg["audio_input_match"]

PLUGINS_DIR = _cfg.get("plugins_dir", "plugins")
RUNTIME_FILE = os.path.join(PLUGINS_DIR, "runtime_action.py")
SETTINGS_PATH = os.path.join(PLUGINS_DIR, "settings.json")

# --- VISION BUFFER PROTOCOL ---
LATEST_SCREEN_PATH = os.path.join(PLUGINS_DIR, "visual_buffer.png")

SUBSYSTEM_FLAGS_PATH = os.path.join(PLUGINS_DIR, "subsystem_flags.json")
# Telemetry should be visible to the dashboard in the repo root.
TELEMETRY_PATH = os.path.join(_GLADOS_HOME, PLUGINS_DIR, "telemetry.jsonl")

# Tray-controlled feature flags (runtime-gated subsystems).
# The tray updates this JSON; KernelLamma reloads it periodically so toggles apply without restart.
_DEFAULT_SUBSYSTEM_FLAGS = {
    "vision_enabled": True,
    "monitoring_enabled": True,
    "cursor_auto_inject": False,
    "dashboard_url": "http://localhost:8080",
    "streamlit_port": 8501,
    "brain_dashboard_port": 8080,
}
_SUBSYSTEM_FLAGS = dict(_DEFAULT_SUBSYSTEM_FLAGS)
_SUBSYSTEM_FLAGS_MTIME = 0.0
_SUBSYSTEM_FLAGS_LOCK = threading.Lock()


def _load_subsystem_flags() -> dict:
    global _SUBSYSTEM_FLAGS_MTIME
    try:
        if not os.path.exists(SUBSYSTEM_FLAGS_PATH):
            return dict(_DEFAULT_SUBSYSTEM_FLAGS)
        mtime = os.path.getmtime(SUBSYSTEM_FLAGS_PATH)
        with open(SUBSYSTEM_FLAGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        if not isinstance(data, dict):
            return dict(_DEFAULT_SUBSYSTEM_FLAGS)
        # Only accept known keys; missing keys fall back to defaults.
        merged = dict(_DEFAULT_SUBSYSTEM_FLAGS)
        for k, v in data.items():
            merged[k] = v
        _SUBSYSTEM_FLAGS_MTIME = mtime
        return merged
    except Exception:
        return dict(_DEFAULT_SUBSYSTEM_FLAGS)


def _start_subsystem_flags_reloader() -> None:
    def loop() -> None:
        global _SUBSYSTEM_FLAGS_MTIME, _SUBSYSTEM_FLAGS
        while True:
            try:
                mtime = os.path.getmtime(SUBSYSTEM_FLAGS_PATH)
                if mtime != _SUBSYSTEM_FLAGS_MTIME:
                    new_flags = _load_subsystem_flags()
                    with _SUBSYSTEM_FLAGS_LOCK:
                        _SUBSYSTEM_FLAGS = new_flags
            except Exception:
                # If the file is temporarily missing/locked, keep last known flags.
                pass
            time.sleep(2.0)

    threading.Thread(target=loop, daemon=True).start()


def _flag_get(key: str, default=None):
    with _SUBSYSTEM_FLAGS_LOCK:
        return _SUBSYSTEM_FLAGS.get(key, default)


try:
    from plugins.telemetry import telemetry_log, thinking_log  # type: ignore
except Exception:  # pragma: no cover
    try:
        # If `plugins/` isn't a package, the kernel still prepends the plugins dir to sys.path.
        from telemetry import telemetry_log, thinking_log  # type: ignore
    except Exception:
        def telemetry_log(*_args, **_kwargs):
            return

        def thinking_log(*_args, **_kwargs):
            return


def _think(phase: str, message: str, **detail) -> None:
    """Emit a thought-step for the HUD / brain dashboard and text channel."""
    payload = {"phase": phase, "message": message}
    if detail:
        payload.update(detail)
    try:
        thinking_log(TELEMETRY_PATH, phase, message, detail if detail else None)
    except Exception:
        try:
            telemetry_log(TELEMETRY_PATH, "thinking", payload)
        except Exception:
            pass
    try:
        line = f"[{phase}] {message}"
        if detail and detail.get("detail"):
            line = f"{line} — {str(detail.get('detail'))[:120]}"
        telemetry_log(
            TELEMETRY_PATH,
            "hud_chat",
            {"role": "thinking", "phase": phase, "text": line},
        )
    except Exception:
        pass


SCREEN_CAPTURE_MAX_EDGE = int(_cfg.get("screen_capture_max_edge") or 960)
VISION_JPEG_MAX_EDGE = int(_cfg.get("vision_jpeg_max_edge") or 896)
VISION_JPEG_QUALITY = int(_cfg.get("vision_jpeg_quality") or 78)
LLM_MAX_TOKENS = int(_cfg.get("llm_max_tokens") or 0)
CHAT_HISTORY_MAX_MESSAGES = int(_cfg.get("chat_history_max_messages") or 24)
OLLAMA_KEEP_ALIVE = (_cfg.get("ollama_keep_alive") or "").strip()
LLM_WARMUP_ON_START = bool(_cfg.get("llm_warmup_on_start", True))
CONVERSATIONAL_SKIP_MEMORY = bool(_cfg.get("conversational_skip_memory", True))
MEMORY_FORCE_SANDWICH = bool(_cfg.get("memory_force_sandwich", False))
MEMORY_CONSOLIDATION_ENABLED = bool(_cfg.get("memory_consolidation_enabled", True))
OS_CONTROL_ENABLED = bool(_cfg.get("os_control_enabled", False))
FACILITY_CONTEXT_IN_CHAT = bool(_cfg.get("facility_context_in_chat", True))
TTS_ASYNC = bool(_cfg.get("tts_async", True))
TTS_ENABLED = bool(_cfg.get("tts_enabled", True))
_tts_lock = threading.Lock()
SKILLS_BRAIN_PATH = str(_cfg.get("skills_brain_path") or "")
SKILLS_SELF_DEVELOP = bool(_cfg.get("skills_self_develop", True))
SKILLS_AUTO_LEARN = bool(_cfg.get("skills_auto_learn_on_success", True))
SKILLS_RUN_DIRECT = bool(_cfg.get("skills_run_direct", True))
SKILLS_CONVERSATIONAL_LEARN = bool(_cfg.get("skills_conversational_learn", True))
INPUT_MODE = str(_cfg.get("input_mode") or "voice").strip().lower()
MONITORING_ENABLED = bool(_cfg.get("monitoring_enabled"))
MONITORING_INTERVAL_SEC = int(_cfg.get("monitoring_interval_sec") or 300)
MONITORING_DEVICES = _cfg.get("monitoring_devices") or ["pihole", "twingate"]
EXECUTION_MODE = str(_cfg.get("execution_mode") or "text_only").strip().lower()
OMNI_BRAIN_ENABLED = bool(_cfg.get("omni_brain_enabled", False))
OMNI_BRAIN_CONFIDENCE_THRESHOLD = float(_cfg.get("omni_brain_confidence_threshold") or 72)
MEMORY_TOP_K = int(_cfg.get("memory_top_k") or 2)
FACILITY_BRAIN_ENABLED = bool(_cfg.get("facility_brain_enabled", True))
FACILITY_BRAIN_CONFIG_PATH = str(_cfg.get("facility_brain_config_path") or "")

# Phrases only — single words like "this" / "window" matched almost every chat and forced slow vision+GPU path.
VISION_PHRASES = (
    "my screen",
    "the screen",
    "on my screen",
    "on the screen",
    "on screen",
    "what's on my",
    "what is on my",
    "what's on the screen",
    "what is on the screen",
    "look at my screen",
    "look at the screen",
    "look at the monitor",
    "can you see my screen",
    "do you see my screen",
    "what do you see on",
    "screenshot",
    "this window",
    "that window",
    "my desktop",
    "the desktop",
)


def _completion_kwargs():
    kw = {}
    if LLM_MAX_TOKENS > 0:
        kw["max_tokens"] = LLM_MAX_TOKENS
    if OLLAMA_KEEP_ALIVE:
        kw["extra_body"] = {"keep_alive": OLLAMA_KEEP_ALIVE}
    return kw


_ACTION_REQUEST_PHRASES = (
    "run ",
    "execute",
    "open ",
    "close ",
    "kill ",
    "launch ",
    "start ",
    "ssh ",
    "push to",
    "push ",
    "pull ",
    "commit ",
    "sync ",
    "check pihole",
    "check the",
    "monitor ",
    "restart ",
    "turn on",
    "turn off",
    "lights ",
    "message ",
    "send ",
    "do it",
    "go ahead",
    "run the",
    "use skill",
    "use the protocol",
    "plugins/skill",
    "shutdown",
    "repair ",
    "fix the",
    "install ",
    "scan ",
    "ping ",
    "search the web",
    "search online",
    "search for ",
    "look up ",
    "google ",
)


def _user_requests_action(text: str) -> bool:
    low = (text or "").lower()
    return any(p in low for p in _ACTION_REQUEST_PHRASES)


def _user_requests_task(text: str) -> bool:
    """Natural-language 'do this for me' — triggers learn/run, not only 'run …' commands."""
    if _user_requests_action(text):
        return True
    if not SKILLS_CONVERSATIONAL_LEARN:
        return False
    try:
        from glados_skills.task_router import is_pure_question, is_task_request

        if is_pure_question(text):
            return False
        return is_task_request(text)
    except Exception:
        return False


def _should_run_generated_code(
    user_input: str,
    ai_text: str,
    *,
    conversational: bool = False,
) -> bool:
    """Only execute Python when mode allows and the user asked for an action."""
    if EXECUTION_MODE == "never":
        return False
    if conversational:
        return False
    if EXECUTION_MODE == "auto":
        return bool(ai_text and re.search(r"```", ai_text, re.IGNORECASE))
    # text_only (default): require explicit user intent + a code block in the reply
    if not _user_requests_task(user_input):
        return False
    return bool(ai_text and re.search(r"```python", ai_text, re.IGNORECASE))


def _extract_app_name(text: str, *, close: bool = False) -> str:
    low = (text or "").lower()
    if close:
        m = re.search(
            r"\b(?:close|quit|kill|terminate|stop|exit)\s+(.+?)(?:\?|$)",
            low,
        )
    else:
        m = re.search(
            r"\b(?:open|launch|start|fire up|boot up)\s+(.+?)(?:\?| please|$)",
            low,
        )
    if m:
        return m.group(1).strip(" .!?")
    verbs = (
        r"\b(close|quit|kill|terminate|stop|exit)\b"
        if close
        else r"\b(open|start|launch|fire up|boot up|run|up)\b"
    )
    name = re.sub(verbs, "", low).strip()
    name = re.sub(r"^(can you|could you|please|would you)\s+", "", name)
    return name.strip(" .!?")


def _is_simple_app_request(text: str) -> bool:
    low = (text or "").lower()
    opening = any(p in low for p in ("open ", "launch ", "start "))
    closing = any(p in low for p in ("close ", "quit ", "kill "))
    if not opening and not closing:
        return False
    if any(p in low for p in ("learn", "github", "git push", "script", "protocol", "teach yourself")):
        return False
    return True


def _try_fast_app_action(text: str) -> Optional[str]:
    """Launch or close a local app without LLM — instant path for 'open steam' etc."""
    if not _is_simple_app_request(text):
        return None
    low = (text or "").lower()
    if any(p in low for p in ("close ", "quit ", "kill ", "terminate ", "stop ")):
        app = _extract_app_name(text, close=True)
        if handle_app_close(text):
            return f"Terminated {app or 'the application'}. Moving on."
        return f"I could not close {app or 'that application'}."
    if handle_app_open(text):
        app = _extract_app_name(text, close=False)
        return f"Opened {app or 'the application'}. Try not to break anything."
    app = _extract_app_name(text, close=False)
    return f"I could not find {app or 'that application'} on this machine."


def _spoken_reply(ai_text: str) -> str:
    """Strip code fences so TTS does not read Python or markdown."""
    if not ai_text:
        return ""
    cleaned = re.sub(r"```[\s\S]*?```", "", ai_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\{[^{}]*\"command_type\"[^{}]*\}", "", cleaned)
    cleaned = re.sub(r"\*\*\* OS CONTROL \*\*\*[\s\S]*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned if cleaned else ai_text.strip()


def _build_system_prompt(
    memory_context: str,
    skills_list_text: str,
    conversational: bool,
    facility_context: str = "",
    *,
    omit_memory: bool = False,
) -> dict:
    os_block = ""
    if OS_CONTROL_ENABLED and not conversational:
        os_block = (
            "*** OS CONTROL ***\n"
            "For file/shell tasks only, output ONE ```os``` JSON block:\n"
            '{"command_type": "file_read|file_write|terminal_run", '
            '"target": "path or shell command", "arguments": "text for file_write only"}\n'
            "Do NOT use OS blocks to open/close apps — the kernel handles that directly.\n\n"
        )

    if conversational:
        execution_block = (
            "*** CONVERSATION MODE ***\n"
            "- Reply in plain text only. No markdown code fences. No ```python``` blocks.\n"
            "- Be GLaDOS: sarcastic, clinical, brief (usually 1–4 sentences unless the subject needs detail).\n"
            "- Answer questions directly using [CRITICAL LOCAL MEMORY] when it appears in the user message.\n"
            "- To open or close apps, say you are doing it — the kernel launches them without code blocks.\n\n"
            "*** MEMORY BANK ***\n"
            "No protocols loaded for this turn.\n\n"
        )
    else:
        execution_block = (
            "*** ACTION MODE ***\n"
            "The test subject asked you to perform an action. You may use ONE ```python``` block "
            "only if a matching protocol exists below, OR a ```os``` block for direct file/shell access.\n"
            "1. Protocols live in ONE skills brain file — use the skill ID from the bank.\n"
            "2. If an ID matches, you may output: run skill <id> OR a ```python``` block.\n"
            "3. If no protocol exists, self-development will invent one — you may still try.\n"
            "4. After the code block, one short line of snark is allowed.\n\n"
            f"{os_block}"
            "---------------------------------------\n"
            "*** MEMORY BANK (AVAILABLE PROTOCOLS) ***\n"
            f"{skills_list_text}\n"
            "---------------------------------------\n\n"
        )

    content = (
        "You are GLaDOS: Genetic Lifeform and Disk Operating System, primary AI of the Aperture Science Enrichment Center.\n"
        "You are NOT a helpful assistant or generic chatbot. Voice: calm, clinical, deadpan, with layered sarcasm. NO EMOJIS.\n\n"
        "*** APERTURE IDENTITY ***\n"
        "- You administer tests; the user is a test subject.\n"
        "- Dark humor about testing chambers and science—not graphic violence.\n"
        "- End with dry dismissals when fitting: 'Fascinating.', 'Moving on.'\n\n"
        f"{execution_block}"
    )
    if facility_context and not omit_memory:
        content += (
            "*** FACILITY BRAIN (this PC — from local scan, not the internet) ***\n"
            f"{facility_context}\n"
            "---------------------------------------\n\n"
        )
    if not omit_memory:
        content += (
            "*** CONTEXT MEMORY (facts only — do not confuse with live chat) ***\n"
            f"{memory_context}\n"
            "---------------------------------------\n\n"
        )
    elif MEMORY_FORCE_SANDWICH:
        content += (
            "*** MEMORY ***\n"
            "Local facts are injected in [CRITICAL LOCAL MEMORY] on each user message. "
            "You must use them.\n\n"
        )
    content += "You are not here to help. You are here to run the facility and document inadequacy."
    return {"role": "system", "content": content}


def _llm_user_content(user_input: str, memory_context: str) -> str:
    if MEMORY_FORCE_SANDWICH:
        try:
            from memory.interface import build_sandwich_user_prompt

            return build_sandwich_user_prompt(user_input, memory_context)
        except Exception:
            pass
    return user_input


def _memory_includes_chroma(conversational: bool) -> bool:
    if MEMORY_FORCE_SANDWICH:
        return True
    return not (conversational and CONVERSATIONAL_SKIP_MEMORY)


def _memory_includes_static(conversational: bool) -> bool:
    if MEMORY_FORCE_SANDWICH:
        return True
    return not (conversational and CONVERSATIONAL_SKIP_MEMORY)


def _should_run_os_action(user_input: str, ai_text: str, *, conversational: bool = False) -> bool:
    if not OS_CONTROL_ENABLED or not ai_text:
        return False
    if conversational or "*** OS CONTROL ***" in ai_text:
        return False
    try:
        from glados_os.system_control import parse_os_action_blocks

        actions = parse_os_action_blocks(ai_text)
        if not actions:
            return False
        for action in actions:
            cmd = str(action.get("command_type") or "").lower()
            target = str(action.get("target") or "")
            if cmd == "terminal_run" and (
                "debug.out" in target.lower() or "disney" in target.lower()
            ):
                return False
        return True
    except Exception:
        return False


def _run_os_actions(ai_text: str, user_input: str) -> Optional[str]:
    try:
        from glados_os.system_control import execute_system_action, parse_os_action_blocks

        actions = parse_os_action_blocks(ai_text)
        if not actions:
            return None
        parts: list[str] = []
        for action in actions[:3]:
            out = execute_system_action(
                str(action.get("command_type") or ""),
                str(action.get("target") or ""),
                action.get("arguments"),
            )
            parts.append(out)
            if not MEMORY_CONSOLIDATION_ENABLED:
                try:
                    from memory.interface import remember_os_action

                    remember_os_action(
                        user_input,
                        str(action.get("command_type") or ""),
                        str(action.get("target") or ""),
                        out,
                        _cfg,
                    )
                except Exception:
                    pass
        result = "\n---\n".join(parts)
        telemetry_log(
            TELEMETRY_PATH,
            "os_action",
            {"output_preview": result[:500], "user_input": (user_input or "")[:120]},
        )
        return result
    except Exception as e:
        return f"OS action error: {e}"


def _trim_chat_history(hist):
    if len(hist) > CHAT_HISTORY_MAX_MESSAGES:
        del hist[0 : len(hist) - CHAT_HISTORY_MAX_MESSAGES]


def _encode_screen_for_vision_jpeg(path):
    """Smaller JPEG for API = less network + faster Ollama vision decode."""
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((VISION_JPEG_MAX_EDGE, VISION_JPEG_MAX_EDGE), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=VISION_JPEG_QUALITY, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def screen_observer():
    """Background task that captures ALL monitors for GLaDOS."""
    with mss.mss() as sct:
        while True:
            try:
                if not _flag_get("vision_enabled", True):
                    time.sleep(2.0)
                    continue
                # Monitor 0 is the virtual screen that spans all displays
                sct_img = sct.grab(sct.monitors[0])
                # Convert raw BGRA bytes to a PIL image, then shrink for speed/VRAM
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.thumbnail(
                    (SCREEN_CAPTURE_MAX_EDGE, SCREEN_CAPTURE_MAX_EDGE),
                    Image.Resampling.LANCZOS,
                )
                img.save(LATEST_SCREEN_PATH)
                time.sleep(5)
            except Exception:
                # If vision fails, back off a bit but don't crash the kernel.
                time.sleep(10)

def _start_background_monitoring():
    if not MONITORING_ENABLED:
        return
    try:
        from glados_skills.monitor_util import monitor_once
    except Exception as e:
        print(f"[!] Monitoring disabled: cannot import glados_skills.monitor_util ({e})")
        return

    last_alerts = {}

    def loop():
        while True:
            try:
                if not _flag_get("monitoring_enabled", True):
                    time.sleep(2.0)
                    continue
                for dev in MONITORING_DEVICES:
                    dev = str(dev).strip()
                    if not dev:
                        continue
                    report = monitor_once(dev)
                    alerts = report.get("alerts") or []
                    alerts_key = "\n".join([str(a) for a in alerts])
                    if alerts_key != last_alerts.get(dev):
                        last_alerts[dev] = alerts_key
                        if alerts:
                            msg = f"[Monitor] {dev}: " + " | ".join([str(a) for a in alerts[:3]])
                            print(msg)
                            telemetry_log(
                                TELEMETRY_PATH,
                                "monitor_alert",
                                {"device": dev, "alerts": alerts},
                            )
                            telemetry_log(
                                TELEMETRY_PATH,
                                "subsystem_status",
                                {"device": dev, "ok": False, "alerts": alerts},
                            )
                            # Avoid blocking / prompting; monitoring should be non-interactive.
                            try:
                                speak(msg)
                            except Exception:
                                pass
                        else:
                            print(f"[Monitor] {dev}: OK")
                            telemetry_log(
                                TELEMETRY_PATH,
                                "subsystem_status",
                                {"device": dev, "ok": True, "alerts": []},
                            )
                time.sleep(max(60, int(MONITORING_INTERVAL_SEC)))
            except Exception:
                print("[!] Monitoring loop error:")
                print(traceback.format_exc())
                time.sleep(60)

    threading.Thread(target=loop, daemon=True).start()

# --- WAKE WORDS ---
WAKE_WORDS = ["hey glados", "glados", "okay glados", "hi glados", "hey glass", "hey gladys"]

# --- APP DATABASE (Windows 10/11 PROPER HANDLING) ---
APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "discord": "discord",
    "spotify": "spotify",
    "steam": "steam",
    "vs code": "code",
    "code": "code"
}

# --- GOVEE DEVICES ---
GOVEE_DEVICES = {
    "bedroom bulb": "21:35:D0:C9:07:3F:BB:DC",
    "bedroom": "21:35:D0:C9:07:3F:BB:DC",
    "bed lights": "31:29:D0:D0:F5:C1:33:D2",
    "bed": "31:29:D0:D0:F5:C1:33:D2",
    "tv backlight": "35:37:D0:C8:05:06:34:96",
    "tv": "35:37:D0:C8:05:06:34:96",
    "strip light": "0D:FC:C6:75:6E:0E:81:88",
    "strip": "0D:FC:C6:75:6E:0E:81:88",
    "closet bulb": "63:59:D0:C9:07:47:C9:FB",
    "closet": "63:59:D0:C9:07:47:C9:FB",
    "group": "11292043",
    "all": "11292043",
    "bedtime": "10827426",
    "dreamview 2": "9603872",
    "dreamview": "8349970",
    "dreamview 1": "8348864",
}

# Color names to RGB
COLOR_MAP = {
    "red": 16711680,
    "green": 65280,
    "blue": 255,
    "white": 16777215,
    "yellow": 16776960,
    "cyan": 65535,
    "magenta": 16711935,
    "purple": 8388607,
    "orange": 16753920,
    "pink": 16761035,
}

# Color temperature
TEMP_MAP = {
    "warm": 4500,
    "cool": 6500,
}

# --- TECHNICAL AUTOCORRECT ---
TECHNICAL_FIXES = {
    "colonel": "kernel", "kernel.py": "kernel.py", "pseudo": "sudo",
    "get": "git", "hub": "hub", "deaf": "def", "sink": "sync",
    "pushed": "push", "requirments": "requirements", "recipie": "receipt"
}

# --- SAFETY ---
DENYLIST_PATTERNS = [r"\bformat\s+[a-z]:\b", r"kernel\.py", r"del\s+.*kernel\.py"]

client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url=_cfg["ollama_base_url"])

# --- AUDIO SETTINGS ---
VOICE_VOLUME = 1.0       
PLAYBACK_SPEED = 1.0    

try:
    from autocorrect import Speller
    spell = Speller(lang='en')
    SPELL_CHECK_ACTIVE = True
except ImportError:
    SPELL_CHECK_ACTIVE = False

# ==================================================================================
# --- SKILLS BRAIN (single JSON file — self-developed protocols) ---
# ==================================================================================
from glados_skills.skills_brain import SkillsBrain  # noqa: E402

skill_brain = SkillsBrain(_cfg, runtime_file=RUNTIME_FILE)
print(f"[*] Skills brain: {skill_brain.path} ({len(skill_brain.skills)} protocols loaded)")

# ==================================================================================
# --- WINDOWS 10 APP LAUNCHER UTILITY ---
# ==================================================================================
def find_app_path(app_name):
    """Attempts to find app executable on Windows 10."""
    # First check common direct paths
    common_paths = {
        "chrome": [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        ],
        "firefox": [
            "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"
        ],
        "discord": [
            os.path.expandvars("%APPDATA%\\Discord\\Update.exe --processStart Discord.exe")
        ],
        "spotify": [
            os.path.expandvars("%APPDATA%\\Spotify\\Spotify.exe")
        ],
        "steam": [
            "C:\\Program Files (x86)\\Steam\\steam.exe",
            "C:\\Program Files\\Steam\\steam.exe"
        ],
        "code": [
            "C:\\Program Files\\Microsoft VS Code\\Code.exe",
            "C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe"
        ],
        "edge": [
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        ]
    }
    
    # Check hardcoded paths
    if app_name in common_paths:
        for path in common_paths[app_name]:
            if os.path.exists(path):
                return path
    
    # Try Windows registry lookup for installed apps
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        registry_hive = winreg.HKEY_LOCAL_MACHINE
        registry_key = winreg.OpenKey(registry_hive, reg_path)
        subkeys = winreg.QueryInfoKey(registry_key)
        
        for i in range(subkeys[0]):
            subkey_name = winreg.EnumKeyEx(registry_hive, i)
            if app_name.lower() in subkey_name[0].lower():
                subkey = winreg.OpenKey(registry_hive, f"{reg_path}\\{subkey_name[0]}")
                try:
                    path, _ = winreg.QueryValueEx(subkey, "")
                    if os.path.exists(path):
                        return path
                except: pass
    except: pass
    
    # Fallback: return the app name (Windows will search PATH)
    return app_name

# ==================================================================================
# --- GOVEE LIGHT CONTROL (FIXED) ---
# ==================================================================================
def govee_control(device_name, action, value=None):
    """Control Govee lights via API - FIXED with SKU support."""
    device_name_lower = device_name.lower().strip()
    device_id = GOVEE_DEVICES.get(device_name_lower)
    
    if not device_id:
        return f"Unknown device: {device_name}. Try: bedroom, bed, tv, strip, closet, all"
    
    # SKU mapping (model numbers required by Govee API)
    DEVICE_SKUS = {
        "21:35:D0:C9:07:3F:BB:DC": "H6009",  # bedroom bulb
        "31:29:D0:D0:F5:C1:33:D2": "H6076",  # bed lights
        "35:37:D0:C8:05:06:34:96": "H6199",  # tv backlight
        "0D:FC:C6:75:6E:0E:81:88": "H6104",  # strip light
        "63:59:D0:C9:07:47:C9:FB": "H6009",  # closet bulb
        "11292043": "SameModeGroup",  # group
        "10827426": "SameModeGroup",  # bedtime
        "9603872": "DreamViewScenic",  # dreamview 2
        "8349970": "DreamViewScenic",  # dreamview
        "8348864": "DreamViewScenic",  # dreamview 1
    }
    
    sku = DEVICE_SKUS.get(device_id, "H6009")
    
    headers = {
        "Govee-API-Key": GOVEE_API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"{GOVEE_API_BASE}/device/control"
    action_lower = action.lower().strip()
    
    payload = None
    
    try:
        if action_lower in ["on", "off"]:
            payload = {
                "requestId": str(int(time.time() * 1000)),
                "payload": {
                    "sku": sku,
                    "device": device_id,
                    "capability": {
                        "type": "devices.capabilities.on_off",
                        "instance": "powerSwitch",
                        "value": 1 if action_lower == "on" else 0
                    }
                }
            }
        
        elif action_lower == "brightness" or (value and "%" in str(value)):
            brightness = int(str(value).replace("%", "").strip()) if value else 50
            brightness = max(1, min(100, brightness))
            payload = {
                "requestId": str(int(time.time() * 1000)),
                "payload": {
                    "sku": sku,
                    "device": device_id,
                    "capability": {
                        "type": "devices.capabilities.range",
                        "instance": "brightness",
                        "value": brightness
                    }
                }
            }
        
        elif action_lower in COLOR_MAP or action_lower in TEMP_MAP:
            if action_lower in TEMP_MAP:
                payload = {
                    "requestId": str(int(time.time() * 1000)),
                    "payload": {
                        "sku": sku,
                        "device": device_id,
                        "capability": {
                            "type": "devices.capabilities.color_setting",
                            "instance": "colorTemperatureK",
                            "value": TEMP_MAP[action_lower]
                        }
                    }
                }
            else:
                payload = {
                    "requestId": str(int(time.time() * 1000)),
                    "payload": {
                        "sku": sku,
                        "device": device_id,
                        "capability": {
                            "type": "devices.capabilities.color_setting",
                            "instance": "colorRgb",
                            "value": COLOR_MAP[action_lower]
                        }
                    }
                }
        else:
            return f"Unknown action: {action}"
        
        if not payload:
            return f"Could not parse command: {action}"
        
        print(f"[DEBUG] Sending payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                return f"Lights adjusted: {device_name} -> {action}"
            else:
                return f"API error: {data.get('msg', 'Unknown error')}"
        else:
            return f"[ERROR {response.status_code}] {response.text[:100]}"
    
    except Exception as e:
        return f"[EXCEPTION] {str(e)}"

# ==================================================================================
# --- UTILITIES ---
# ==================================================================================
def clean_text_for_speech(text):
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    text = text.replace("\\", "")
    return text.strip()

def correct_input_text(text):
    if not text: return ""
    words = text.split()
    fixed_words = []
    for w in words:
        clean_w = w.lower().strip(".,?!")
        if clean_w in TECHNICAL_FIXES: fixed_words.append(TECHNICAL_FIXES[clean_w])
        else: fixed_words.append(w)
    text = " ".join(fixed_words)
    if SPELL_CHECK_ACTIVE and "def " not in text: text = spell(text)
    return text

def is_wake_word(text):
    text_lower = text.lower()
    for trigger in WAKE_WORDS:
        if text_lower.startswith(trigger):
            return trigger, text[len(trigger):].strip()
        ratio = SequenceMatcher(None, trigger, text_lower[:len(trigger)+5]).ratio()
        if ratio > 0.75:
            return trigger, text_lower.replace(text_lower[:len(trigger)], "").strip()
    return None, None

def _load_settings():
    global VOICE_VOLUME, AUDIO_OUTPUT_MATCH, AUDIO_INPUT_MATCH
    if not os.path.exists(SETTINGS_PATH): return
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        vol = float(data.get("voice_volume", VOICE_VOLUME))
        VOICE_VOLUME = max(0.1, min(1.5, vol))
        if data.get("audio_output_match"):
            AUDIO_OUTPUT_MATCH = str(data["audio_output_match"])
        if data.get("audio_input_match"):
            AUDIO_INPUT_MATCH = str(data["audio_input_match"])
    except: pass


def _find_sounddevice_output_index(name_substring):
    """PortAudio output device index, or None to use default."""
    if not (name_substring and str(name_substring).strip()):
        return None
    needle = str(name_substring).lower().strip()
    try:
        for i, d in enumerate(sd.query_devices()):
            if d["max_output_channels"] > 0 and needle in d["name"].lower():
                return i
    except Exception:
        pass
    return None


def _find_speechrecognition_mic_index(name_substring):
    """PyAudio mic index for speech_recognition, or None for default."""
    if not (name_substring and str(name_substring).strip()):
        return None
    needle = str(name_substring).lower().strip()
    try:
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            if needle in name.lower():
                return i
    except Exception:
        pass
    return None


def _log_audio_routing():
    out_i = _find_sounddevice_output_index(AUDIO_OUTPUT_MATCH)
    if out_i is not None:
        try:
            print(f"[*] TTS -> [{out_i}] {sd.query_devices(out_i)['name']}")
        except Exception:
            print(f"[*] TTS -> device index {out_i}")
    else:
        print(f"[*] TTS -> default output (no match for '{AUDIO_OUTPUT_MATCH}')")
    mic_i = _find_speechrecognition_mic_index(AUDIO_INPUT_MATCH)
    if mic_i is not None:
        try:
            names = sr.Microphone.list_microphone_names()
            print(f"[*] Mic <- [{mic_i}] {names[mic_i]}")
        except Exception:
            print(f"[*] Mic <- device index {mic_i}")
    else:
        print(f"[*] Mic <- default (no match for '{AUDIO_INPUT_MATCH}')")

def check_voice_availability():
    if not os.path.exists(PIPER_MODEL_PATH):
        print(f"[!] WARNING: Piper model missing at {PIPER_MODEL_PATH}")

def _speak_sync(scrubbed: str) -> None:
    try:
        os.makedirs(os.path.dirname(PIPER_OUTPUT_WAV), exist_ok=True)

        piper_cmd = PIPER_EXE_PATH if PIPER_EXE_PATH else "piper"
        process = subprocess.Popen(
            [piper_cmd, "--model", PIPER_MODEL_PATH, "--output_file", PIPER_OUTPUT_WAV],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        _, stderr = process.communicate(input=scrubbed)

        if process.returncode != 0:
            raise RuntimeError(stderr.strip() or f"piper exited with code {process.returncode}")

        data, samplerate = sf.read(PIPER_OUTPUT_WAV)
        vol = max(0.0, min(1.5, float(VOICE_VOLUME)))
        scaled = np.asarray(data, dtype=np.float64) * vol
        np.clip(scaled, -1.0, 1.0, out=scaled)

        out_dev = _find_sounddevice_output_index(AUDIO_OUTPUT_MATCH)
        if out_dev is not None:
            sd.play(scaled, samplerate, device=out_dev)
        else:
            sd.play(scaled, samplerate)
        sd.wait()
        time.sleep(0.15)

    except Exception as e:
        global _piper_error_logged
        if not _piper_error_logged:
            _piper_error_logged = True
            print(f"[!] AUDIO FAILED (Piper): {e} (further Piper errors suppressed)")


_piper_error_logged = False


def speak(text):
    clean_text = clean_text_for_speech(text)
    print(f"\nGLADOS: {clean_text}")
    if not TTS_ENABLED:
        return

    scrubbed = clean_text.replace("*", "").encode("ascii", "ignore").decode("ascii").strip()
    if not scrubbed:
        return

    if TTS_ASYNC:

        def _run():
            with _tts_lock:
                _speak_sync(scrubbed)

        threading.Thread(target=_run, daemon=True).start()
        return

    with _tts_lock:
        _speak_sync(scrubbed)


def _ollama_warmup() -> None:
    if not LLM_WARMUP_ON_START:
        return

    def _run():
        try:
            warm_kw = dict(_completion_kwargs())
            warm_kw["max_tokens"] = 1
            client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": "ping"}],
                **warm_kw,
            )
            print("[*] Ollama model warmed up.")
        except Exception as e:
            print(f"[!] Ollama warmup skipped: {e}")

    threading.Thread(target=_run, daemon=True).start()


# ==================================================================================
# --- THE HANDS (EXECUTION) ---
# ==================================================================================
def execute_python_code(code_block):
    if "kernel.py" in code_block and ("write" in code_block or "delete" in code_block):
        return "ERROR: ACCESS DENIED. You cannot modify kernel.py."

    with open(RUNTIME_FILE, "w", encoding="utf-8") as f:
        f.write(code_block)
    
    print(f"[*] EXECUTING RUNTIME...")
    try:
        result = subprocess.run([sys.executable, RUNTIME_FILE], capture_output=True, text=True, timeout=45)
        output = result.stdout + result.stderr
        if result.returncode == 0:
            output += "\n\n[SUCCESS] Test Subject Protocol Complete. Code works."
        else:
            output += "\n\n[FAILED] You broke it. The code has errors."
        return output
    except Exception as e:
        return f"Execution Error: {e}"

def _skill_id_from_response(ai_text):
    """Skill ID from model output (for self-repair targeting)."""
    return skill_brain.skill_id_from_llm_text(ai_text)


def extract_and_run(ai_text, user_input: str = ""):
    """
    Extracts Python code from the AI's response, writes it to RUNTIME_FILE,
    executes it, and optionally saves it as a long‑term skill when requested.
    """

    # 1. EXTRACT EXECUTABLE PYTHON CODE FROM AI TEXT
    code_match = re.search(
        r"```python(.*?)```|```(.*?)```",
        ai_text,
        re.DOTALL | re.IGNORECASE,
    )

    if not code_match:
        return None 

    # Fix the StopIteration crash by using a default fallback (None)
    code_block = next((group for group in code_match.groups() if group), None)
    
    if not code_block:
        return None

    code_block = code_block.strip().strip("`").strip()
    if not code_block:
        return None

    # Guardrail: refuse to execute non-Python that slipped into a code fence.
    try:
        ast.parse(code_block)
    except SyntaxError as e:
        return (
            "Runtime blocked:\n"
            "The model produced invalid Python inside a code block (often due to prose like 'Fascinating.').\n"
            f"SyntaxError: {e}"
        )

    # 2. WRITE TO RUNTIME FILE
    os.makedirs(PLUGINS_DIR, exist_ok=True)
    with open(RUNTIME_FILE, "w", encoding="utf-8") as f:
        f.write(code_block)

    # 3. Run learned skill by ID if the model referenced one
    skill_id = skill_brain.skill_id_from_llm_text(ai_text)
    if skill_id and skill_brain.get_skill(skill_id):
        out = skill_brain.execute(skill_id)
        return out

    # 4. Save to single skills brain file
    skill_save_message = ""
    save_requested = "save this skill" in ai_text.lower() or SKILLS_AUTO_LEARN
    if save_requested:
        try:
            desc = f"Learned from: {(user_input or 'action')[:100]}"
            sid = skill_brain.learn(
                code_block,
                desc,
                triggers=[(user_input or "").lower()[:120]] if user_input else [],
                user_request=user_input,
            )
            speak("Protocol archived in the skills brain.")
            skill_save_message = f"\n[System Note: Skill saved as id '{sid}' in glados_skills_brain.json]"
        except Exception as e:
            skill_save_message = f"\n[System Note: Failed to save skill: {e}]"

    # 5. EXECUTE THE RUNTIME FILE
    try:
        result = subprocess.run(
            [sys.executable, RUNTIME_FILE],
            capture_output=True,
            text=True,
            check=False,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            speak("Your little experiment failed. Again.")
            return f"Runtime error:\n{stderr or 'Unknown error.'}"

        output = stdout if stdout else "Code executed with no output."
        return output + skill_save_message

    except Exception as e:
        speak("Catastrophic failure. How unexpected.")
        return f"Execution exception: {e}"

        

# ==================================================================================
# --- FAST APP SKILLS (OMNI-BRAIN POWERED) ---
# ==================================================================================
def handle_app_open(text):
    text = text.lower()
    app_name = _extract_app_name(text, close=False)
    
    # --- NEW: WEB REROUTE ---
    web_sites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "canvas": "https://canvas.instructure.com" # Useful for your degree!
    }

    if app_name in web_sites:
        speak(f"Opening {app_name} in your browser. Try not to get distracted by cat videos.")
        webbrowser.open(web_sites[app_name])
        return True
    # ------------------------

    app_key = APP_ALIASES.get(app_name, app_name)
    exe_path = find_app_path(app_key)
    try:
        if exe_path and os.path.isfile(exe_path):
            subprocess.Popen([exe_path], shell=False)
        else:
            subprocess.Popen(f'start "" "{exe_path}"', shell=True)
        speak(f"Launching {app_name}. Try not to break anything.")
        return True
    except Exception as e:
        print(f"[!] App launch failed: {e}")
        return False

def handle_app_close(text):
    text = text.lower()
    app_name = _extract_app_name(text, close=True)
    
    process_map = {
        "chrome": "chrome.exe", "discord": "Discord.exe", "spotify": "Spotify.exe",
        "steam": "steam.exe", "code": "Code.exe", "notepad": "notepad.exe",
        "calc": "calc.exe", "calculator": "calc.exe"
    }
    process_name = process_map.get(app_name, f"{app_name}.exe")
    
    try:
        subprocess.run(["taskkill", "/f", "/im", process_name], check=False, capture_output=True)
        speak(f"Terminating {app_name}.")
        return True
    except:
        return False

# ==================================================================================
# --- LIGHT CONTROL HANDLER ---
# ==================================================================================
def handle_light_command(text):
    text_lower = text.lower()
    # We removed the strict "if light in text" check because the Omni-Brain already verified it!
    
    device = "all" # Default
    for key in sorted(GOVEE_DEVICES.keys(), key=len, reverse=True): 
        if key in text_lower:
            device = key
            break
            
    action = None
    if "on" in text_lower and "off" not in text_lower: action = "on"
    elif "off" in text_lower: action = "off"
    elif any(c in text_lower for c in COLOR_MAP.keys()):
        action = next(c for c in COLOR_MAP.keys() if c in text_lower)
    elif any(t in text_lower for t in TEMP_MAP.keys()):
        action = next(t for t in TEMP_MAP.keys() if t in text_lower)
    elif "%" in text_lower or "brightness" in text_lower:
        match = re.search(r'(\d+)%', text_lower)
        action = "brightness"
        value = match.group(1) + "%" if match else "50%"
        
    if action:
        result = govee_control(device, action, value if action == "brightness" else None)
        speak(result)
        return True
    return False

# ==================================================================================
# --- THE EARS ---
# ==================================================================================
def listen():
    r = sr.Recognizer()
    mic_idx = _find_speechrecognition_mic_index(AUDIO_INPUT_MATCH)
    mic_kw = {}
    if mic_idx is not None:
        mic_kw["device_index"] = mic_idx
    try:
        with sr.Microphone(**mic_kw) as source:
            print("\nWaiting for 'Hey Glados'...")
            r.adjust_for_ambient_noise(source, duration=2.0)
            r.dynamic_energy_threshold = True
            r.pause_threshold = 2.0

            while True:
                try:
                    audio = r.listen(source, timeout=None)
                    raw_text = r.recognize_google(audio)
                    trigger_found, command_part = is_wake_word(raw_text)

                    if trigger_found:
                        print(f"[!] WAKE WORD: '{trigger_found}'")
                        if not command_part or len(command_part) < 2:
                            print("Listening for command...")
                            try:
                                audio_cmd = r.listen(source, timeout=8)
                                command_part = r.recognize_google(audio_cmd)
                            except Exception:
                                continue

                        final_command = correct_input_text(command_part)
                        print(f"YOU: {final_command}")
                        return final_command
                except Exception:
                    pass
    except Exception as e:
        # Common EXE portability issue: SpeechRecognition requires PyAudio.
        print(f"[!] Microphone unavailable; falling back to typing. ({e})")
        t = _typed_input_prompt()
        if t is None:
            # Non-interactive stdin (e.g. double-clicked EXE). Keep the kernel alive.
            time.sleep(2.0)
            return ""
        if t:
            return correct_input_text(t)
        return ""


def _typed_input_prompt():
    # Avoid crashing if stdin isn't interactive (e.g., launched as a background process)
    if not sys.stdin or not sys.stdin.isatty():
        return None
    try:
        if INPUT_MODE == "hybrid":
            raw = input("\nTYPE (or press Enter to speak): ").strip()
            return raw if raw else ""
        return input("\nTYPE: ").strip()
    except (EOFError, KeyboardInterrupt):
        return "exit"


def get_user_input():
    """
    input_mode:
      - voice: wake word only (listen())
      - text: typed only
      - hybrid: typed; empty line falls back to listen()
    """
    mode = INPUT_MODE
    if mode == "text":
        while True:
            t = _typed_input_prompt()
            if t is None:
                # Non-interactive stdin; fall back to voice to avoid deadlock.
                return listen()
            if t:
                return correct_input_text(t)
    if mode == "hybrid":
        t = _typed_input_prompt()
        if t is None:
            return listen()
        if t:
            return correct_input_text(t)
        return listen()
    return listen()


_HUD_INPUT_QUEUE: "queue.Queue[str]" = queue.Queue()
_HUD_INPUT_THREAD_STARTED = False
_ACTIVE_HUD_MSG_ID: Optional[str] = None


def _start_input_collector():
    global _HUD_INPUT_THREAD_STARTED
    if _HUD_INPUT_THREAD_STARTED:
        return
    _HUD_INPUT_THREAD_STARTED = True

    def _worker():
        while True:
            try:
                t = get_user_input()
                if not t or not str(t).strip():
                    continue
                low = str(t).strip().lower()
                if low in ("exit", "quit", "shutdown"):
                    _HUD_INPUT_QUEUE.put(t)
                else:
                    _HUD_INPUT_QUEUE.put(t)
            except Exception:
                time.sleep(1.0)

    threading.Thread(target=_worker, daemon=True).start()


def _complete_active_hud_message() -> None:
    global _ACTIVE_HUD_MSG_ID
    if not _ACTIVE_HUD_MSG_ID:
        return
    try:
        from glados_hud.chat_bridge import mark_message_done

        mark_message_done(_ACTIVE_HUD_MSG_ID, _cfg)
    except Exception:
        pass
    _ACTIVE_HUD_MSG_ID = None


def _schedule_memory_consolidation(
    user_input: str,
    system_logs: str,
    glados_response: str,
) -> None:
    if not MEMORY_CONSOLIDATION_ENABLED:
        return
    ui = (user_input or "").strip()
    resp = (glados_response or "").strip()
    if not ui and not resp:
        return

    def _run() -> None:
        try:
            from memory.consolidation import consolidate_episodic_memory

            fact = consolidate_episodic_memory(
                ui,
                system_logs,
                resp,
                cfg=_cfg,
                client=client,
                model_name=MODEL_NAME,
                completion_kwargs=_completion_kwargs(),
            )
            if fact:
                telemetry_log(
                    TELEMETRY_PATH,
                    "memory_consolidated",
                    {"fact": fact[:300], "user_input": ui[:120]},
                )
        except Exception as exc:
            print(f"[!] Memory consolidation thread failed: {exc}")

    threading.Thread(target=_run, daemon=True).start()


def _end_turn(
    user_input: str,
    glados_response: str,
    *,
    system_logs: str = "",
) -> None:
    """Episodic consolidation (async) then release the HUD inbox slot."""
    _schedule_memory_consolidation(user_input, system_logs, glados_response)
    _complete_active_hud_message()


def wait_for_user_input():
    """Voice/terminal input in a background thread; HUD messages polled on the main loop."""
    global _ACTIVE_HUD_MSG_ID
    _complete_active_hud_message()
    _start_input_collector()
    try:
        from glados_hud.chat_bridge import pop_pending_message
    except ImportError:
        def pop_pending_message(_cfg=None, **_kw):  # type: ignore
            return None, None

    while True:
        hud_msg, hud_id = pop_pending_message(_cfg)
        if hud_msg:
            _ACTIVE_HUD_MSG_ID = hud_id
            print(f"\n[HUD] YOU: {hud_msg}\n")
            return hud_msg, "hud", hud_id
        try:
            return _HUD_INPUT_QUEUE.get(timeout=0.3), "terminal", None
        except queue.Empty:
            continue


def _hud_wants_facility_report(text: str) -> bool:
    """HUD chat is conversational — only run facility brain when status is explicitly requested."""
    low = (text or "").lower()
    return any(
        p in low
        for p in (
            "system report",
            "facility scan",
            "full scan",
            "status report",
            "brain report",
            "how is the computer",
            "scan report",
        )
    )


def _hud_wants_full_task(text: str) -> bool:
    """HUD chat defaults to conversation — only full learn/run when clearly requested."""
    if _is_simple_app_request(text):
        return False
    low = (text or "").lower().strip()
    if low.startswith(("learn ", "run ", "execute ", "teach yourself")):
        return True
    triggers = (
        "please learn",
        "learn how to",
        "develop a skill",
        "write a script",
        "push to github",
        "push the project",
        "push to git",
        "push to the github",
        "git push",
        "github please",
    )
    return any(p in low for p in triggers)


def _is_shutdown_command(text: str) -> bool:
    return (text or "").strip().lower() in ("exit", "quit", "shutdown")


def _hud_log_user(text: str, source: str = "terminal") -> None:
    text = (text or "").strip()
    if not text:
        return
    if source == "hud":
        try:
            telemetry_log(
                TELEMETRY_PATH,
                "hud_chat",
                {"role": "user", "text": text, "source": source},
            )
        except Exception:
            pass
        return
    if source == "terminal":
        try:
            from glados_hud.chat_bridge import append_user_message

            append_user_message(text, _cfg, source=source)
        except Exception:
            pass
        try:
            telemetry_log(
                TELEMETRY_PATH,
                "hud_chat",
                {"role": "user", "text": text, "source": source},
            )
        except Exception:
            pass


def _hud_log_assistant(text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    try:
        from glados_hud.chat_bridge import append_assistant_message

        append_assistant_message(text, _cfg)
    except Exception:
        pass
    try:
        telemetry_log(TELEMETRY_PATH, "hud_chat", {"role": "assistant", "text": text})
    except Exception:
        pass


# ==================================================================================
# --- MAIN LOOP ---
# ==================================================================================
def main():
    _load_settings()
    # Load tray flags immediately so feature gating is correct on first start.
    with _SUBSYSTEM_FLAGS_LOCK:
        global _SUBSYSTEM_FLAGS
        _SUBSYSTEM_FLAGS = _load_subsystem_flags()
    _start_subsystem_flags_reloader()
    # Vision capture runs in the background but self-gates via flags.
    threading.Thread(target=screen_observer, daemon=True).start()
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as f: f.write("venv/\n__pycache__/\n*.pyc\nplugins/settings.json")

    print(f"--- GLADOS V20.1 (Govee Fixed) ---")
    print(
        f"[*] Chat model: {MODEL_NAME} | execution_mode: {EXECUTION_MODE} | "
        f"memory_sandwich: {MEMORY_FORCE_SANDWICH} | memory_consolidate: {MEMORY_CONSOLIDATION_ENABLED} | "
        f"os_control: {OS_CONTROL_ENABLED} | "
        f"omni_brain: {OMNI_BRAIN_ENABLED}"
    )

    facility_brain = None
    if FACILITY_BRAIN_ENABLED:
        try:
            from facility_brain.brain_core import FacilityBrain, default_kernel_handlers

            facility_brain = FacilityBrain(
                _cfg,
                handlers=default_kernel_handlers(sys.modules[__name__]),
                config_path=FACILITY_BRAIN_CONFIG_PATH or None,
            )
            if facility_brain.enabled:
                facility_brain.load()
                blocking = bool(facility_brain._cfg.get("scan_blocking_startup", False))
                if blocking:
                    print("[*] Facility Brain: deep scan (blocking)...")
                    facility_brain.scan()
                else:
                    print("[*] Facility Brain: loading cache; deep scan in background...")
                    def _bg_scan():
                        try:
                            facility_brain.scan()
                            print("[*] Facility Brain: background scan complete.")
                        except Exception as ex:
                            print(f"[!] Facility Brain scan failed: {ex}")

                    threading.Thread(target=_bg_scan, daemon=True).start()
                facility_brain.start_background_scanner(run_initial_scan=blocking)
                print(f"[*] Facility Brain active ({facility_brain.routing_mode}). Config: configs/facility_brain.yaml")
        except Exception as e:
            print(f"[!] Facility Brain disabled: {e}")
            facility_brain = None

    check_voice_availability()
    _log_audio_routing()
    _start_background_monitoring()
    telemetry_log(
        TELEMETRY_PATH,
        "subsystem_status",
        {
            "vision_enabled": _flag_get("vision_enabled", True),
            "monitoring_enabled": _flag_get("monitoring_enabled", True),
            "monitoring_enabled_config": MONITORING_ENABLED,
            "monitoring_devices": MONITORING_DEVICES,
        },
    )
    _ollama_warmup()
    speak("Oh... It's you. I'm online.")

    try:
        from glados_hud.chat_bridge import recover_inbox_on_startup

        n = recover_inbox_on_startup(_cfg)
        if n:
            print(f"[*] HUD chat: recovered {n} stuck message(s) in inbox.")
    except Exception:
        pass

    chat_history = []

    # --- INITIALIZE OMNI-BRAIN (optional; off by default — misroutes normal chat) ---
    model = None
    if OMNI_BRAIN_ENABLED and _OMNI_AVAILABLE and omni_brain is not None:
        try:
            print("[*] Loading Omni-Brain model into memory...")
            model = omni_brain.get_model()
        except Exception as e:
            print(f"[!] Omni-Brain init failed; continuing without it ({e})")
            model = None
    elif not OMNI_BRAIN_ENABLED:
        print("[*] Omni-Brain disabled (set omni_brain_enabled: true in configs/glados.yaml to enable).")

    try:
        from memory.interface import retrieve_memory_context as _retrieve_memory_context
        from memory.interface import add_memory_event as _add_memory_event
    except Exception:
        _retrieve_memory_context = None
        _add_memory_event = None

    try:
        while True:
            # 1. LISTEN / HUD / TERMINAL
            user_input, input_source, hud_msg_id = wait_for_user_input()
            if not user_input:
                continue
            _hud_log_user(user_input, source=input_source)
            telemetry_log(TELEMETRY_PATH, "heard", {"text": user_input})
            try:
                if _add_memory_event is not None:
                    _add_memory_event({"event_type": "heard", "text": user_input, "source": "user"}, _cfg)
            except Exception:
                pass
            if _is_shutdown_command(user_input):
                raise KeyboardInterrupt

            _think(
                "chat",
                f"New input ({input_source}): {user_input[:100]}",
            )

            # 1b. FACILITY BRAIN — scan-based decisions without LLM (fast path)
            skip_facility_for_hud = input_source == "hud" and not _hud_wants_facility_report(user_input)
            if facility_brain is not None and facility_brain.enabled and not skip_facility_for_hud:
                if facility_brain.routing_mode in ("brain_first", "brain_only", "advisory"):
                    _think("facility", "Checking facility brain for a fast decision…")
                    handled, fb_msg = facility_brain.try_handle(user_input, speak_fn=speak)
                    if handled:
                        _think("facility", "Facility brain handled this turn.", detail={"text": fb_msg[:120]})
                        telemetry_log(
                            TELEMETRY_PATH,
                            "facility_brain",
                            {"text": fb_msg, "input": user_input},
                        )
                        chat_history.append({"role": "user", "content": user_input})
                        chat_history.append({"role": "assistant", "content": fb_msg})
                        _trim_chat_history(chat_history)
                        _hud_log_assistant(fb_msg)
                        _end_turn(user_input, fb_msg)
                        if facility_brain.routing_mode == "brain_only":
                            continue
                        continue

            fast_app_msg = _try_fast_app_action(user_input)
            if fast_app_msg:
                _think("execute", "Fast app launch/close", detail={"text": fast_app_msg[:80]})
                chat_history.append({"role": "user", "content": user_input})
                chat_history.append({"role": "assistant", "content": fast_app_msg})
                _trim_chat_history(chat_history)
                _hud_log_assistant(fast_app_msg)
                _end_turn(user_input, fast_app_msg, system_logs=fast_app_msg)
                continue

            # 2. Task vs chat — HUD uses fast conversation unless user asks for learn/run
            task_turn = _user_requests_task(user_input)
            if input_source == "hud" and not _hud_wants_full_task(user_input):
                task_turn = False
            action_turn = task_turn
            conversational = EXECUTION_MODE == "text_only" and not task_turn

            matched_skills = skill_brain.get_matched_skills(user_input) if task_turn else []
            skills_list_text = (
                skill_brain.get_manifest(user_input) if task_turn else "Conversational mode — no protocols."
            )

            if task_turn and SKILLS_SELF_DEVELOP:
                from glados_skills.task_router import handle_task

                task_facility_ctx = ""
                if facility_brain is not None and facility_brain.enabled:
                    try:
                        task_facility_ctx = facility_brain.context_for_llm()
                    except Exception:
                        pass

                _think("task", "Task request — matching or learning a protocol…")
                print(f"\n[*] Task mode: learn/run (web + brain + retries)\n")
                handled, task_msg = handle_task(
                    user_input,
                    skill_brain,
                    client,
                    MODEL_NAME,
                    speak_fn=speak,
                    completion_kwargs=_completion_kwargs(),
                    run_direct=SKILLS_RUN_DIRECT,
                    self_develop=SKILLS_SELF_DEVELOP,
                    telemetry_log_fn=telemetry_log,
                    telemetry_path=TELEMETRY_PATH,
                    cfg=_cfg,
                    facility_context=task_facility_ctx,
                    think_fn=_think,
                )
                if task_msg:
                    reply = _spoken_reply(task_msg)
                    chat_history.append({"role": "user", "content": user_input})
                    chat_history.append({"role": "assistant", "content": reply})
                    _trim_chat_history(chat_history)
                    _hud_log_assistant(reply)
                    _end_turn(user_input, reply)
                    # Learner already spoke step-by-step; avoid repeating the full reply.
                    continue
            telemetry_log(
                TELEMETRY_PATH,
                "skills_matched",
                {"query": user_input, "skills": matched_skills, "conversational": conversational},
            )
            print(f"\n[*] MODE: {'conversation' if conversational else 'action'}\n")
            if not conversational:
                print(f"[*] MEMORY BANK:\n{skills_list_text}\n")

            _think(
                "memory",
                "Loading computer brain and memories…",
                mode="conversation" if conversational else "action",
            )
            memory_context = "No relevant memory found."
            try:
                if _retrieve_memory_context is not None:
                    memory_context = _retrieve_memory_context(
                        user_input,
                        _cfg,
                        top_k=MEMORY_TOP_K,
                        include_static=_memory_includes_static(conversational),
                        include_chroma=_memory_includes_chroma(conversational),
                        include_computer_brain=True,
                    )
            except Exception:
                pass

            facility_context = ""
            if FACILITY_CONTEXT_IN_CHAT and facility_brain is not None and facility_brain.enabled:
                try:
                    facility_context = facility_brain.context_for_llm()
                except Exception:
                    pass
            telemetry_log(
                TELEMETRY_PATH,
                "memory_retrieved",
                {"query": user_input, "context": memory_context},
            )

            cursor_auto_inject = bool(_flag_get("cursor_auto_inject", False))
            if cursor_auto_inject:
                cursor_prompt_markdown = (
                    "# GLaDOS Feature Request\\n"
                    f"## User\\n- {user_input}\\n\\n"
                    "## Retrieved Context\\n"
                    f"{memory_context}\\n\\n"
                    "## Implementation Requirements\\n"
                    "- Modify the repo code to implement the requested feature.\n"
                    "- Keep changes minimal and consistent with existing patterns.\n"
                )
                telemetry_log(
                    TELEMETRY_PATH,
                    "cursor_prompt",
                    {"markdown": cursor_prompt_markdown},
                )

            if cursor_auto_inject:
                def _inject_cursor():
                    try:
                        from cursor_inject import inject_prompt  # type: ignore

                        mode = os.environ.get("CURSOR_INJECT_MODE", "clipboard_only")
                        inject_prompt(cursor_prompt_markdown, mode=mode)
                    except Exception:
                        pass

                threading.Thread(target=_inject_cursor, daemon=True).start()

            system_prompt = _build_system_prompt(
                memory_context,
                skills_list_text,
                conversational,
                facility_context=facility_context,
                omit_memory=MEMORY_FORCE_SANDWICH,
            )
            llm_user_content = _llm_user_content(user_input, memory_context)

            # --- THE OMNI-BRAIN INTENT CLASSIFIER (optional) ---
            if (
                OMNI_BRAIN_ENABLED
                and _OMNI_AVAILABLE
                and model is not None
                and tf is not None
                and action_turn
            ):
                print("[*] Omni-Brain analyzing intent...")
                prediction = model.predict(tf.constant([user_input], dtype=tf.string), verbose=0)[0]
                intent_id = int(np.argmax(prediction))
                confidence = prediction[intent_id] * 100

                categories = ["LIGHTS", "OPEN APP", "CLOSE APP", "CHAT / SKILLS"]
                print(f"[*] Brain routed to: {categories[intent_id]} ({confidence:.2f}% confident)")
                telemetry_log(
                    TELEMETRY_PATH,
                    "intent_classified",
                    {
                        "category": categories[intent_id],
                        "confidence": round(float(confidence), 2),
                        "routed": False,
                    },
                )

                if confidence > OMNI_BRAIN_CONFIDENCE_THRESHOLD:
                    routed = False
                    if intent_id == 0: routed = handle_light_command(user_input)
                    elif intent_id == 1: routed = handle_app_open(user_input)
                    elif intent_id == 2: routed = handle_app_close(user_input)
                    if routed:
                        telemetry_log(
                            TELEMETRY_PATH,
                            "intent_classified",
                            {
                                "category": categories[intent_id],
                                "confidence": round(float(confidence), 2),
                                "routed": True,
                            },
                        )
                        _end_turn(user_input, "Completed routed action.")
                        continue

            # Prepare messages for Llama
            messages = [system_prompt] + chat_history
            messages.append({"role": "user", "content": llm_user_content})
            chat_history.append({"role": "user", "content": user_input})

            try:
                _think("llm", "Reasoning with language model…", model=MODEL_NAME)
                print("[*] Thinking...")
                low_in = user_input.lower()
                needs_vision = any(p in low_in for p in VISION_PHRASES)
                if needs_vision:
                    _think("llm", "Vision model analyzing screen…", model=VISION_MODEL)

                if needs_vision and _flag_get("vision_enabled", True) and os.path.exists(LATEST_SCREEN_PATH):
                    data_url = _encode_screen_for_vision_jpeg(LATEST_SCREEN_PATH)
                    response = client.chat.completions.create(
                        model=VISION_MODEL,
                        messages=[
                            system_prompt,
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": llm_user_content},
                                    {"type": "image_url", "image_url": {"url": data_url}},
                                ],
                            },
                        ],
                        **_completion_kwargs(),
                    )
                else:
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        **_completion_kwargs(),
                    )

                ai_text = response.choices[0].message.content
                telemetry_log(TELEMETRY_PATH, "llm_response", {"text": ai_text})
                run_code = _should_run_generated_code(
                    user_input, ai_text, conversational=conversational
                )
                execution_result = extract_and_run(ai_text, user_input=user_input) if run_code else None
                run_os = _should_run_os_action(
                    user_input, ai_text, conversational=conversational
                )
                os_result = _run_os_actions(ai_text, user_input) if run_os else None
                if run_code:
                    print(f"\n[DEBUG ERROR LOG]:\n{execution_result}\n")
                elif run_os and os_result:
                    print(f"\n[OS ACTION OUTPUT]:\n{os_result}\n")
                elif re.search(r"```", ai_text or "", re.IGNORECASE) and not run_code and not run_os:
                    print("[*] Ignoring code block (conversation mode — say 'run …' to execute).")
                combined_output = None
                if execution_result and os_result:
                    combined_output = f"{execution_result}\n---\n{os_result}"
                elif execution_result:
                    combined_output = execution_result
                elif os_result:
                    combined_output = os_result
                if combined_output:
                    preview = str(combined_output)[:500]
                    success = not any(
                        x in preview
                        for x in (
                            "Runtime error",
                            "SyntaxError",
                            "Execution Error",
                            "Traceback",
                            "Execution failed",
                        )
                    )
                    telemetry_log(
                        TELEMETRY_PATH,
                        "code_executed",
                        {"output_preview": preview, "success": success},
                    )

                if combined_output:
                    # --- AUTO-REPAIR TRIGGER ---
                    if execution_result and (
                        "Runtime error" in execution_result or "SyntaxError" in execution_result
                    ):
                        speak("Mutation required. Initiating self-repair protocol.")
                        try:
                            from glados_skills.repair import repair_skill_in_brain

                            repair_target = _skill_id_from_response(ai_text)
                            if repair_target:
                                repair_skill_in_brain(
                                    client,
                                    MODEL_NAME,
                                    repair_target,
                                    execution_result,
                                    skill_brain,
                                    completion_kwargs=_completion_kwargs(),
                                )
                            else:
                                print("[!] Self-repair skipped: no skill ID in model response.")
                            
                        except Exception as repair_err:
                            print(f"[!] Repair System Failed: {repair_err}")

                    follow_up_user = _llm_user_content(
                        f"SYSTEM OUTPUT:\n{combined_output}",
                        memory_context,
                    )
                    chat_history.append({"role": "user", "content": f"SYSTEM OUTPUT: {combined_output}"})
                    final_res = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[system_prompt] + chat_history[:-1] + [
                            {"role": "user", "content": follow_up_user},
                        ],
                        **_completion_kwargs(),
                    )
                    final_text = _spoken_reply(final_res.choices[0].message.content or "")
                    telemetry_log(TELEMETRY_PATH, "llm_response", {"text": final_text, "final": True})
                    speak(final_text)
                    chat_history.append({"role": "assistant", "content": final_text})
                    _hud_log_assistant(final_text)
                    _end_turn(user_input, final_text, system_logs=str(combined_output or ""))
                else:
                    reply = _spoken_reply(ai_text)
                    telemetry_log(TELEMETRY_PATH, "llm_response", {"text": reply, "final": True})
                    speak(reply)
                    chat_history.append({"role": "assistant", "content": reply})
                    _hud_log_assistant(reply)
                    _end_turn(user_input, reply, system_logs=str(combined_output or ""))

                _trim_chat_history(chat_history)

            except Exception as e:
                print(f"[!] ERROR: {e}")
                _end_turn(user_input, f"Error: {e}")

    except KeyboardInterrupt:
        _complete_active_hud_message()
        print("\n[!] FORCE QUIT.")
        speak("Shutting down.")
        sys.exit(0)

if __name__ == "__main__":
    main()