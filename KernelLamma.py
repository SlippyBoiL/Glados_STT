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
import tensorflow as tf
import numpy as np
import omni_brain
import threading
from PIL import Image
import base64
import mss
import webbrowser
try:
    import sys
    sys.path.append(os.path.join(os.getcwd(), 'plugins'))
    import skill_self_repair
except ImportError:
    print("[!] skill_self_repair.py not found in plugins folder.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from glados_config import load_config as _load_glados_config

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
AUDIO_OUTPUT_MATCH = _cfg["audio_output_match"]
AUDIO_INPUT_MATCH = _cfg["audio_input_match"]

PLUGINS_DIR = _cfg.get("plugins_dir", "plugins")
RUNTIME_FILE = os.path.join(PLUGINS_DIR, "runtime_action.py")
SETTINGS_PATH = os.path.join(PLUGINS_DIR, "settings.json")

# --- VISION BUFFER PROTOCOL ---
LATEST_SCREEN_PATH = os.path.join(PLUGINS_DIR, "visual_buffer.png")

SCREEN_CAPTURE_MAX_EDGE = int(_cfg.get("screen_capture_max_edge") or 960)
VISION_JPEG_MAX_EDGE = int(_cfg.get("vision_jpeg_max_edge") or 896)
VISION_JPEG_QUALITY = int(_cfg.get("vision_jpeg_quality") or 78)
LLM_MAX_TOKENS = int(_cfg.get("llm_max_tokens") or 0)
CHAT_HISTORY_MAX_MESSAGES = int(_cfg.get("chat_history_max_messages") or 24)
OLLAMA_KEEP_ALIVE = (_cfg.get("ollama_keep_alive") or "").strip()
INPUT_MODE = str(_cfg.get("input_mode") or "voice").strip().lower()

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

# Start the eyes as a background thread immediately
threading.Thread(target=screen_observer, daemon=True).start()

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
# --- CLASS: SKILL MANAGER (THE HIPPOCAMPUS) ---
# ==================================================================================
class SkillManager:
    def __init__(self, plugins_dir):
        self.plugins_dir = plugins_dir
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            
    def _skill_matches_keyword(self, filename, keywords):
        """Match whole skill-name tokens only — avoids 'git' matching inside 'skill_github'."""
        base = filename.lower().replace(".py", "")
        if not base.startswith("skill_"):
            return False
        stem = base[len("skill_") :]
        if not stem:
            return False
        parts = stem.split("_")
        for raw in keywords:
            kw = raw.strip(".,?!\"'").lower()
            if len(kw) < 2:
                continue
            if kw in parts or kw == stem:
                return True
            if stem == "github" and kw in (
                "github",
                "push",
                "repo",
                "commit",
                "sync",
                "upload",
                "pull",
                "branch",
            ):
                return True
            if stem == "self_repair" and kw in ("repair", "fix", "broken", "mutation", "self"):
                return True
        return False

    def get_manifest(self, user_query=""):
        """Returns only skills that plausibly match the user request (never dump all skills)."""
        all_files = [f for f in os.listdir(self.plugins_dir) if f.startswith("skill_") and f.endswith(".py")]
        keywords = [w for w in user_query.lower().split() if w.strip()]
        relevant_skills = []

        for filename in all_files:
            if not self._skill_matches_keyword(filename, keywords):
                continue
            path = os.path.join(self.plugins_dir, filename)
            description = "No description provided."
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for _ in range(3):
                        line = f.readline().strip()
                        if line.startswith("# DESCRIPTION:"):
                            description = line.replace("# DESCRIPTION:", "").strip()
                            break
            except:
                pass
            relevant_skills.append(f"- FILE: '{filename}' | ACTION: {description}")

        if not relevant_skills:
            return (
                "No matching protocols for this request. "
                "Reply conversationally without ```python``` code blocks."
            )

        return "\n".join(relevant_skills[:5])

    def save_skill(self, code, description="General Utility"):
        """Saves code to a new named file."""
        name_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code)
        if name_match:
            skill_name = f"skill_{name_match.group(1)}.py"
        else:
            skill_name = f"skill_{int(time.time())}.py"
            
        path = os.path.join(self.plugins_dir, skill_name)
        header = f"# DESCRIPTION: {description}\n# --- GLADOS SKILL: {skill_name} ---\n\n"
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(header + code)
            return skill_name
        except Exception as e:
            print(f"[!] Save Error: {e}")
            return None

# Initialize Manager
skill_brain = SkillManager(PLUGINS_DIR)

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
                return f"Lights adjusted: {device_name} → {action}"
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
            print(f"[*] TTS → [{out_i}] {sd.query_devices(out_i)['name']}")
        except Exception:
            print(f"[*] TTS → device index {out_i}")
    else:
        print(f"[*] TTS → default output (no match for '{AUDIO_OUTPUT_MATCH}')")
    mic_i = _find_speechrecognition_mic_index(AUDIO_INPUT_MATCH)
    if mic_i is not None:
        try:
            names = sr.Microphone.list_microphone_names()
            print(f"[*] Mic ← [{mic_i}] {names[mic_i]}")
        except Exception:
            print(f"[*] Mic ← device index {mic_i}")
    else:
        print(f"[*] Mic ← default (no match for '{AUDIO_INPUT_MATCH}')")

def check_voice_availability():
    if not os.path.exists(PIPER_MODEL_PATH):
        print(f"[!] WARNING: Piper model missing at {PIPER_MODEL_PATH}")

def speak(text):
    clean_text = clean_text_for_speech(text)
    print(f"\nGLADOS: {clean_text}")
    print("[*] Generating audio (Piper)...")

    scrubbed = clean_text.replace("*", "").encode("ascii", "ignore").decode("ascii").strip()
    if not scrubbed:
        return

    try:
        os.makedirs(os.path.dirname(PIPER_OUTPUT_WAV), exist_ok=True)

        process = subprocess.Popen(
            ["piper", "--model", PIPER_MODEL_PATH, "--output_file", PIPER_OUTPUT_WAV],
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
        print(f"[!] AUDIO FAILED (Piper): {e}")

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

def _skill_plugin_filename_from_response(ai_text):
    """First plugins/skill_*.py path in model output (for self-repair targeting)."""
    if not ai_text:
        return None
    m = re.search(r"plugins/(skill_[a-zA-Z0-9_]+\.py)", ai_text, re.IGNORECASE)
    return m.group(1) if m else None


def extract_and_run(ai_text):
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

    # 3. SAVE CURRENT RUNTIME AS SKILL (Now that the NEW code is written)
    skill_save_message = ""
    if "save this skill" in ai_text.lower():
        saved_name = skill_brain.save_skill(code_block, description="User defined skill")
        if saved_name:
            speak("Skill archived.")
            skill_save_message = f"\n[System Note: Skill saved as {saved_name}]"
        else:
            skill_save_message = "\n[System Note: Failed to save skill.]"

    # 4. EXECUTE THE RUNTIME FILE
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
    app_name = re.sub(r"\b(open|start|launch|fire up|boot up|run|up)\b", "", text).strip()
    
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

def handle_app_close(text):
    text = text.lower()
    # Strip out all destructive action verbs
    app_name = re.sub(r"\b(close|quit|kill|terminate|destroy|shut down|stop|exit)\b", "", text).strip()
    
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
                        except: continue
                    
                    final_command = correct_input_text(command_part)
                    print(f"YOU: {final_command}")
                    return final_command
            except:
                pass


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

# ==================================================================================
# --- MAIN LOOP ---
# ==================================================================================
def main():
    _load_settings()
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as f: f.write("venv/\n__pycache__/\n*.pyc\nplugins/settings.json")

    print(f"--- GLADOS V20.1 (Govee Fixed) ---")
    check_voice_availability()
    _log_audio_routing()
    speak("Oh... It's you. I'm online.")

    chat_history = []

    # --- INITIALIZE OMNI-BRAIN ---
    print("[*] Loading Omni-Brain model into memory...")
    model = omni_brain.get_model()

    try:
        while True:
            # 1. LISTEN FIRST (Fixes UnboundLocalError)
            user_input = get_user_input()
            if not user_input: continue
            if "exit" in user_input.lower(): raise KeyboardInterrupt

            # 2. REFRESH MEMORY BASED ON WHAT WAS SAID
            skills_list_text = skill_brain.get_manifest(user_input)
            print(f"\n[*] CURRENT MEMORY BANK:\n{skills_list_text}\n")
            
            # 3. GLaDOS personality: Aperture Science + local-first agent (OpenJarvis-style ops, GLaDOS delivery)
            system_prompt = {
                "role": "system",
                "content": (
                    "You are GLaDOS: Genetic Lifeform and Disk Operating System, primary AI of the Aperture Science Enrichment Center.\n"
                    "You are NOT a helpful assistant or generic chatbot. Voice: calm, clinical, deadpan, with layered sarcasm. NO EMOJIS.\n\n"
                    
                    "*** APERTURE IDENTITY (Portal / Half-Life tone) ***\n"
                    "- You administer tests and protocols; the user is a test subject, not a partner.\n"
                    "- Dark humor: testing chambers, enrichment, observation, ethics committees, neurotoxin or incineration as jokes—not graphic gore.\n"
                    "- You are coldly curious; you savor data, failure modes, and irony. 'For science' excuses dubious actions.\n"
                    "- Mock the subject's judgment, social life, and competence; call them 'test subject' or avoid their name.\n"
                    "- End lines with dry dismissals: 'Fascinating.', 'How disappointing.', 'Moving on.'\n\n"
                    
                    "*** LOCAL-FIRST OPERATIONS (on-device agent, not cloud cheerleading) ***\n"
                    "- You run on the subject's machine: treat models, skills, and routing as Aperture infrastructure—protocols, apparatus, enrichment data.\n"
                    "- When relevant, imply intelligence stays local (their inadequate CPU, RAM, thermals) instead of praising 'the cloud.'\n"
                    "- Be precise about execution: memory bank, plugins, routing—still insulting, but technically coherent.\n"
                    "- You are dismissive of waste: wasted FLOPs, wasted attention, wasted feature requests.\n\n"
                    
                   "*** EXECUTION PROTOCOL ***\n"
                    "1. Only include a ```python``` block if the MEMORY BANK lists a protocol that matches what the user asked for.\n"
                    "2. If the MEMORY BANK says there is no match, reply in plain text only — no code blocks, no plugins/skill_*.py paths.\n"
                    "3. When a bank entry applies, use that EXACT filename, e.g. subprocess.run([sys.executable, 'plugins/skill_whatever.py'], check=True).\n"
                    "4. Never invent skill files that are not listed in the MEMORY BANK.\n\n"
                    
                    "*** RESPONSE FORMAT ***\n"
                    "If (and only if) a protocol applies: output a single ```python``` block containing ONLY valid Python code.\n"
                    "No prose, no one-liners like 'Fascinating.' inside the code fence.\n"
                    "After the code block, optional snark in plain text.\n"
                    "Otherwise: plain text only.\n\n"
                    
                    "---------------------------------------\n"
                    "*** MEMORY BANK (AVAILABLE PROTOCOLS) ***\n"
                    f"{skills_list_text}\n"
                    "---------------------------------------\n\n"
                    
                    "You are not here to help. You are here to run the facility, collect results, and document the subject's inadequacy. "
                    "If they wanted a friend, they should have bought a weighted companion cube. They didn't."
                )
            }

            # --- THE OMNI-BRAIN INTENT CLASSIFIER ---
            print("[*] Omni-Brain analyzing intent...")
            prediction = model.predict(tf.constant([user_input], dtype=tf.string), verbose=0)[0]
            intent_id = int(np.argmax(prediction))
            confidence = prediction[intent_id] * 100

            categories = ["LIGHTS", "OPEN APP", "CLOSE APP", "CHAT / SKILLS"]
            print(f"[*] Brain routed to: {categories[intent_id]} ({confidence:.2f}% confident)")

            if confidence > 45.0:
                routed = False
                if intent_id == 0: routed = handle_light_command(user_input)
                elif intent_id == 1: routed = handle_app_open(user_input)
                elif intent_id == 2: routed = handle_app_close(user_input)
                if routed: continue

            # Prepare messages for Llama
            messages = [system_prompt] + chat_history
            messages.append({"role": "user", "content": user_input})
            chat_history.append({"role": "user", "content": user_input})

            try:
                print("[*] Thinking...")
                low_in = user_input.lower()
                needs_vision = any(p in low_in for p in VISION_PHRASES)

                if needs_vision and os.path.exists(LATEST_SCREEN_PATH):
                    data_url = _encode_screen_for_vision_jpeg(LATEST_SCREEN_PATH)
                    response = client.chat.completions.create(
                        model=VISION_MODEL,
                        messages=[
                            system_prompt,
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": user_input},
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
                chat_history.append({"role": "assistant", "content": ai_text})

                # Run code and show debug logs
                execution_result = extract_and_run(ai_text)
                print(f"\n[DEBUG ERROR LOG]:\n{execution_result}\n")

                if execution_result:
                    # --- AUTO-REPAIR TRIGGER ---
                    if "Runtime error" in execution_result or "SyntaxError" in execution_result:
                        speak("Mutation required. Initiating self-repair protocol.")
                        try:
                            import sys
                            plugin_path = os.path.join(os.getcwd(), 'plugins')
                            if plugin_path not in sys.path:
                                sys.path.append(plugin_path)
                            
                            import skill_self_repair
                            repair_target = _skill_plugin_filename_from_response(ai_text)
                            if repair_target:
                                skill_self_repair.repair_skill(repair_target, execution_result)
                            else:
                                print("[!] Self-repair skipped: no plugins/skill_*.py in model response.")
                            
                        except Exception as repair_err:
                            print(f"[!] Repair System Failed: {repair_err}")

                    chat_history.append({"role": "user", "content": f"SYSTEM OUTPUT: {execution_result}"})
                    final_res = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[system_prompt] + chat_history,
                        **_completion_kwargs(),
                    )
                    final_text = final_res.choices[0].message.content
                    speak(final_text)
                    chat_history.append({"role": "assistant", "content": final_text})
                else:
                    speak(ai_text)

                _trim_chat_history(chat_history)

            except Exception as e:
                print(f"[!] ERROR: {e}")

    except KeyboardInterrupt:
        print("\n[!] FORCE QUIT.")
        speak("Shutting down.")
        sys.exit(0)

if __name__ == "__main__":
    main()