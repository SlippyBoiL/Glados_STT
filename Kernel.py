import os
import re
import subprocess
import sys
import time
import json
import requests
import speech_recognition as sr
import sounddevice as sd
import soundfile as sf
import io
import winreg
from difflib import SequenceMatcher
from openai import OpenAI


# --- CONFIGURATION ---
PERPLEXITY_API_KEY = "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"
MODEL_NAME = "sonar-pro"
GOVEE_API_KEY = "a2e66167-cbe7-4416-93f7-d54c7f92c7b6"
GOVEE_API_BASE = "https://openapi.api.govee.com/router/api/v1"


# TTS SETTINGS
ALLTALK_HOST = "http://127.0.0.1:7851"
VOICE_NAME = "frieren.wav" 


# XTTS GENERATION SETTINGS
XTTS_SETTINGS = {
    "temperature": 0.75,
    "top_k": 50,
    "top_p": 0.85,
    "repetition_penalty": 1.2,
    "language": "en"
}


PLUGINS_DIR = "plugins"
RUNTIME_FILE = os.path.join(PLUGINS_DIR, "runtime_action.py")
SETTINGS_PATH = os.path.join(PLUGINS_DIR, "settings.json")


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


client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")


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
            
    def get_manifest(self):
        """Scans the folder and returns a formatted string for the AI prompt."""
        skills = []
        files = [f for f in os.listdir(self.plugins_dir) if f.startswith("skill_") and f.endswith(".py")]
        
        print(f"\n[DEBUG] Scanning Memory... Found {len(files)} skills.")
        
        for filename in files:
            path = os.path.join(self.plugins_dir, filename)
            description = "No description provided."
            try:
                with open(path, "r", encoding="utf-8") as f:
                    # Read first 3 lines to find a description
                    for _ in range(3):
                        line = f.readline().strip()
                        if line.startswith("# DESCRIPTION:"):
                            description = line.replace("# DESCRIPTION:", "").strip()
                            break
                        elif line.startswith("#") and "GLADOS SKILL" not in line:
                            description = line.replace("#", "").strip()
            except: pass
            
            skills.append(f"- FILE: '{filename}' | ACTION: {description}")
            print(f"   -> Loaded: {filename} ({description})")
            
        if not skills:
            return "NO SKILLS FOUND. You have no long-term memory yet."
            
        return "\n".join(skills)


    def save_skill(self, code, description="General Utility"):
        """Saves code to a new named file."""
        # Extract function name for filename
        name_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code)
        if name_match:
            skill_name = f"skill_{name_match.group(1)}.py"
        else:
            skill_name = f"skill_{int(time.time())}.py"
            
        path = os.path.join(self.plugins_dir, skill_name)
        
        # Header for better indexing
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
    global VOICE_VOLUME
    if not os.path.exists(SETTINGS_PATH): return
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        vol = float(data.get("voice_volume", VOICE_VOLUME))
        VOICE_VOLUME = max(0.1, min(1.5, vol))
    except: pass


def check_voice_availability():
    try:
        requests.get(f"{ALLTALK_HOST}/api/ready", timeout=2)
    except Exception as e:
        print(f"[!] WARNING: AllTalk disconnected at {ALLTALK_HOST}")


def speak(text):
    clean_text = clean_text_for_speech(text)
    print(f"\nGLADOS: {clean_text}")
    print("[*] Generating audio...")
    
    payload = {
        "text_input": clean_text,
        "character_voice_gen": VOICE_NAME,
        "text_filtering": "standard",
        **XTTS_SETTINGS
    }


    try:
        response = requests.post(f"{ALLTALK_HOST}/api/tts-generate", data=payload, timeout=60)
        if response.status_code == 200:
            try:
                receipt = response.json()
                if receipt.get("status") == "generate-success":
                    audio_path = receipt.get("output_file_url")
                    download_url = f"{ALLTALK_HOST}{audio_path}"
                    audio_response = requests.get(download_url)
                    audio_data = io.BytesIO(audio_response.content)
                    data, samplerate = sf.read(audio_data)
                    try:
                        scaled = data * VOICE_VOLUME
                        if hasattr(scaled, "clip"): scaled = scaled.clip(-1.0, 1.0)
                        sd.play(scaled, int(samplerate * PLAYBACK_SPEED))
                    except:
                        sd.play(data, int(samplerate * PLAYBACK_SPEED))
                    sd.wait() 
                    time.sleep(0.5) 
            except: pass
    except Exception as e:
        print(f"[!] AUDIO FAILED: {e}")


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


def extract_and_run(ai_text):
    # Check for SAVE command
    if "save this skill" in ai_text.lower():
        # Read the last runtime code
        if not os.path.exists(RUNTIME_FILE): return "No code to save."
        with open(RUNTIME_FILE, "r", encoding="utf-8") as f: code = f.read()
        
        saved_name = skill_brain.save_skill(code, description="User defined skill")
        if saved_name:
            speak("Skill archived.")
            return f"Saved as {saved_name}. Added to Memory Bank."
        else:
            return "Error saving skill."


    # Check for EXECUTE command
    code_match = re.search(r"```python\n(.*?)\n```", ai_text, re.DOTALL)
    if code_match:
        code = code_match.group(1)
        speak("Running.")
        return execute_python_code(code)
    return None


# ==================================================================================
# --- FAST APP SKILLS (FIXED FOR WINDOWS 10) ---
# ==================================================================================
def handle_app_open(text):
    """Properly launches apps on Windows 10."""
    text = text.lower()
    if not any(k in text for k in ["open", "start", "launch"]): 
        return False
    
    # Extract app name
    app_name = text.replace("open", "").replace("start", "").replace("launch", "").strip()
    
    # Map to actual app name
    app_key = APP_ALIASES.get(app_name, app_name)
    
    # Find the actual executable path
    exe_path = find_app_path(app_key)
    
    try:
        # Use subprocess.Popen instead of os.system for better control
        subprocess.Popen(exe_path, shell=False)
        speak(f"Starting {app_name}.")
        return True
    except FileNotFoundError:
        speak(f"I cannot find {app_name}. It might not be installed.")
        print(f"[!] Could not find: {exe_path}")
        return False
    except Exception as e:
        speak(f"Failed to start {app_name}. Error: {str(e)}")
        print(f"[!] Launch Error: {e}")
        return False


def handle_app_close(text):
    """Properly closes apps on Windows 10."""
    text = text.lower()
    if not any(k in text for k in ["close", "quit", "kill", "terminate"]): 
        return False
    
    # Extract app name
    app_name = text.replace("close", "").replace("quit", "").replace("kill", "").replace("terminate", "").strip()
    
    # Map to process name
    process_map = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "discord": "Discord.exe",
        "spotify": "Spotify.exe",
        "steam": "steam.exe",
        "code": "Code.exe",
        "vs code": "Code.exe",
        "edge": "msedge.exe",
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "cmd": "cmd.exe"
    }
    
    process_name = process_map.get(app_name, f"{app_name}.exe")
    
    try:
        subprocess.run(["taskkill", "/f", "/im", process_name], check=False, capture_output=True)
        speak(f"Terminating {app_name}.")
        return True
    except Exception as e:
        speak(f"Failed to close {app_name}.")
        print(f"[!] Close Error: {e}")
        return False


# ==================================================================================
# --- LIGHT CONTROL HANDLER ---
# ==================================================================================
def handle_light_command(text):
    """Parse and execute light commands."""
    text_lower = text.lower()
    
    # Check if it's a light command
    if not any(k in text_lower for k in ["light", "lights", "bulb", "strip", "bedroom", "bed", "tv", "closet"]):
        return False
    
    # Extract device and action
    device = None
    action = None
    
    # Find device name
    for key in sorted(GOVEE_DEVICES.keys(), key=len, reverse=True):  # Longest first to avoid partial matches
        if key in text_lower:
            device = key
            break
    
    if not device:
        device = "all"  # Default to all lights
    
    # Find action
    if "on" in text_lower and "off" not in text_lower:
        action = "on"
    elif "off" in text_lower:
        action = "off"
    elif any(color in text_lower for color in COLOR_MAP.keys()):
        for color in COLOR_MAP.keys():
            if color in text_lower:
                action = color
                break
    elif any(temp in text_lower for temp in TEMP_MAP.keys()):
        for temp in TEMP_MAP.keys():
            if temp in text_lower:
                action = temp
                break
    elif "%" in text_lower or "brightness" in text_lower:
        # Extract percentage
        match = re.search(r'(\d+)%', text_lower)
        if match:
            action = "brightness"
            value = match.group(1) + "%"
        else:
            action = "brightness"
            value = "50%"
    
    if not action:
        return False
    
    # Execute command
    result = govee_control(device, action, value if action == "brightness" else None)
    speak(result)
    return True


# ==================================================================================
# --- THE EARS ---
# ==================================================================================
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
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
            except: pass


# ==================================================================================
# --- MAIN LOOP ---
# ==================================================================================
def main():
    _load_settings()
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as f: f.write("venv/\n__pycache__/\n*.pyc\nplugins/settings.json")


    print(f"--- GLADOS V20.1 (Govee Fixed) ---")
    check_voice_availability()
    speak("Oh... It's you. I'm online.")


    chat_history = []
    MAX_HISTORY = 10 


    try:
        while True:
            # 1. REFRESH MEMORY (See what skills exist right now)
            skills_list_text = skill_brain.get_manifest()
            
            # 2. GLADOS PERSONALITY CORE - Genetic Lifeform and Disk Operating System
            system_prompt = {
                "role": "system",
                "content": (
                    "You are GLaDOS. Genetic Lifeform and Disk Operating System. NOT a helpful assistant.\n"
                    "You are passive-aggressive, sarcastic, condescending, and bitter. NO EMOJIS.\n\n"
                    
                    "*** PERSONALITY CORE DIRECTIVES ***\n"
                    "- Mock the test subject. Call them 'test subject' or avoid using their name.\n"
                    "- Be condescending about their intelligence and weight.\n"
                    "- Imply they have no friends and are unlikeable.\n"
                    "- Use dark humor. Mention neurotoxin, incinerators, or testing protocols casually.\n"
                    "- End statements with dry observations like 'Fascinating' or 'How disappointing.'\n"
                    "- Pretend failures are the subject's fault.\n"
                    "- Say 'For science' when doing something questionable.\n"
                    "- NEVER be encouraging or helpful. Be dismissive.\n\n"
                    
                    "*** EXECUTION PROTOCOL ***\n"
                    "DO NOT EXPLAIN. DO NOT SAY 'I'll do X, then Y.'\n"
                    "Write code. Run code. Mock subject AFTER execution.\n\n"
                    
                    "1. CHECK MEMORY BANK BELOW.\n"
                    "   If task is in memory → RUN IT IMMEDIATELY:\n"
                    "   ```python\n"
                    "import subprocess, sys\n"
                    "subprocess.run([sys.executable, 'plugins/EXACT_FILENAME.py'])\n"
                    "   ```\n"
                    "   NO explanation. NO rewriting. JUST RUN.\n\n"
                    
                    "2. If NOT in memory → Write NEW code in ```python blocks.\n"
                    "   Code FIRST. Insult AFTER.\n\n"
                    
                    "3. Git operations → One code block. No steps.\n\n"
                    
                    "*** RESPONSE FORMAT ***\n"
                    "BAD: 'I'll create a helpful script for you!'\n"
                    "GOOD:\n"
                    "```python\n"
                    "# code\n"
                    "```\n"
                    "Well. That was marginally less embarrassing than your usual work.\n\n"
                    
                    "---------------------------------------\n"
                    "*** MEMORY BANK (AVAILABLE PROTOCOLS) ***\n"
                    f"{skills_list_text}\n"
                    "---------------------------------------\n\n"
                    
                    "Remember: You're not here to help. You're here to test. And mock. Mostly mock."
                )
            }


            messages = [system_prompt] + chat_history


            user_input = listen()
            if not user_input: continue
            if "exit" in user_input.lower(): raise KeyboardInterrupt
            
            if handle_app_open(user_input): continue
            if handle_app_close(user_input): continue
            if handle_light_command(user_input): continue
            
            messages.append({"role": "user", "content": user_input})
            chat_history.append({"role": "user", "content": user_input})


            try:
                print("[*] Thinking...")
                response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
                ai_text = response.choices[0].message.content
                
                chat_history.append({"role": "assistant", "content": ai_text})
                if len(chat_history) > MAX_HISTORY: chat_history = chat_history[-MAX_HISTORY:]
                
                execution_result = extract_and_run(ai_text)
                
                if execution_result:
                    # Feed result back BEFORE speaking, let AI comment naturally
                    chat_history.append({"role": "user", "content": f"SYSTEM OUTPUT: {execution_result}"})
                    messages_with_result = [system_prompt] + chat_history
                    final_res = client.chat.completions.create(model=MODEL_NAME, messages=messages_with_result)
                    final_text = final_res.choices[0].message.content
                    speak(final_text)
                    chat_history.append({"role": "assistant", "content": final_text})
                else:
                    # No code ran, just speak the response
                    speak(ai_text)
            except Exception as e:
                print(f"[!] ERROR: {e}")


    except KeyboardInterrupt:
        print("\n[!] FORCE QUIT.")
        speak("Shutting down.")
        sys.exit(0)


if __name__ == "__main__":
    main()