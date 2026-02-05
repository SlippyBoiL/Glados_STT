import os
import re
import subprocess
import sys
import time
import json
import requests
import winreg
import importlib.util
from difflib import SequenceMatcher
from openai import OpenAI


# --- DEBUG CONFIGURATION ---
DEBUG_MODE = True
PERPLEXITY_API_KEY = "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"
MODEL_NAME = "sonar-pro"
GOVEE_API_KEY = "a2e66167-cbe7-4416-93f7-d54c7f92c7b6"
GOVEE_API_BASE = "https://openapi.api.govee.com/router/api/v1"


PLUGINS_DIR = "plugins"
RUNTIME_FILE = os.path.join(PLUGINS_DIR, "runtime_action.py")
SETTINGS_PATH = os.path.join(PLUGINS_DIR, "settings.json")


# --- APP DATABASE ---
APP_ALIASES = {
    "chrome": "chrome", "google chrome": "chrome", "firefox": "firefox",
    "edge": "msedge", "notepad": "notepad.exe", "calculator": "calc.exe",
    "calc": "calc.exe", "explorer": "explorer.exe", "cmd": "cmd.exe",
    "discord": "discord", "spotify": "spotify", "steam": "steam",
    "vs code": "code", "code": "code"
}


# --- GOVEE DEVICES ---
GOVEE_DEVICES = {
    "bedroom bulb": "21:35:D0:C9:07:3F:BB:DC", "bedroom": "21:35:D0:C9:07:3F:BB:DC",
    "bed lights": "31:29:D0:D0:F5:C1:33:D2", "bed": "31:29:D0:D0:F5:C1:33:D2",
    "tv backlight": "35:37:D0:C8:05:06:34:96", "tv": "35:37:D0:C8:05:06:34:96",
    "strip light": "0D:FC:C6:75:6E:0E:81:88", "strip": "0D:FC:C6:75:6E:0E:81:88",
    "closet bulb": "63:59:D0:C9:07:47:C9:FB", "closet": "63:59:D0:C9:07:47:C9:FB",
    "group": "11292043", "all": "11292043", "bedtime": "10827426",
    "dreamview 2": "9603872", "dreamview": "8349970", "dreamview 1": "8348864",
}


COLOR_MAP = {
    "red": 16711680, "green": 65280, "blue": 255, "white": 16777215,
    "yellow": 16776960, "cyan": 65535, "magenta": 16711935,
    "purple": 8388607, "orange": 16753920, "pink": 16761035,
}


TEMP_MAP = {"warm": 4500, "cool": 6500}


client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")


# ==================================================================================
# --- MOCKED I/O (TEXT BASED) ---
# ==================================================================================
def speak(text):
    """Mocks TTS by printing to console with color."""
    print(f"\n\033[96m[GLADOS]: {text}\033[0m")


def debug_log(category, message):
    if DEBUG_MODE:
        print(f"\033[93m[DEBUG - {category}]: {message}\033[0m")


# ==================================================================================
# --- CLASS: SKILL MANAGER (FIXED) ---
# ==================================================================================
class SkillManager:
    def __init__(self, plugins_dir):
        self.plugins_dir = plugins_dir
        self.loaded_skills = {}  # Cache loaded modules
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            
    def get_manifest(self):
        """Returns formatted list of available skills with descriptions."""
        skills = []
        files = [f for f in os.listdir(self.plugins_dir) if f.startswith("skill_") and f.endswith(".py")]
        for filename in files:
            filepath = os.path.join(self.plugins_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if first_line.startswith("# DESCRIPTION:"):
                        desc = first_line.replace("# DESCRIPTION:", "").strip()
                        skills.append(f"- {filename}: {desc}")
                    else:
                        skills.append(f"- {filename}")
            except:
                skills.append(f"- {filename}")
        return "\n".join(skills) if skills else "NO SKILLS FOUND."

    def load_skill(self, skill_filename):
        """Dynamically load a skill module from file."""
        if skill_filename in self.loaded_skills:
            return self.loaded_skills[skill_filename]
            
        filepath = os.path.join(self.plugins_dir, skill_filename)
        if not os.path.exists(filepath):
            debug_log("SKILL LOAD", f"Skill file not found: {skill_filename}")
            return None
            
        try:
            # Use importlib to dynamically load the module
            spec = importlib.util.spec_from_file_location(skill_filename.replace(".py", ""), filepath)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            self.loaded_skills[skill_filename] = module
            debug_log("SKILL LOAD", f"Successfully loaded: {skill_filename}")
            return module
        except Exception as e:
            debug_log("SKILL LOAD ERROR", f"{skill_filename}: {e}")
            return None

    def load_all_skills(self):
        """Load all skill files at startup."""
        files = [f for f in os.listdir(self.plugins_dir) if f.startswith("skill_") and f.endswith(".py")]
        for filename in files:
            self.load_skill(filename)
        debug_log("SKILL MANAGER", f"Loaded {len(self.loaded_skills)} skills")

    def execute_skill_function(self, skill_name, function_name, *args, **kwargs):
        """Execute a specific function from a loaded skill."""
        if skill_name not in self.loaded_skills:
            self.load_skill(skill_name)
            
        if skill_name in self.loaded_skills:
            module = self.loaded_skills[skill_name]
            if hasattr(module, function_name):
                func = getattr(module, function_name)
                return func(*args, **kwargs)
            else:
                return f"Function '{function_name}' not found in {skill_name}"
        return f"Skill '{skill_name}' not loaded"

    def save_skill(self, code, description="General Utility"):
        """Save a new skill to the plugins directory."""
        name_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code)
        skill_name = f"skill_{name_match.group(1)}.py" if name_match else f"skill_{int(time.time())}.py"
        path = os.path.join(self.plugins_dir, skill_name)
        header = f"# DESCRIPTION: {description}\n# --- GLADOS SKILL: {skill_name} ---\n\n"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(header + code)
            debug_log("SKILL SAVE", f"Saved: {skill_name}")
            # Immediately load the new skill
            self.load_skill(skill_name)
            return skill_name
        except Exception as e:
            debug_log("SAVE ERROR", str(e))
            return None

    def get_available_functions(self):
        """Return a dict of all callable functions across all loaded skills."""
        functions = {}
        for skill_name, module in self.loaded_skills.items():
            for attr_name in dir(module):
                if not attr_name.startswith("_") and callable(getattr(module, attr_name)):
                    functions[attr_name] = (skill_name, getattr(module, attr_name))
        return functions


skill_brain = SkillManager(PLUGINS_DIR)


# ==================================================================================
# --- APP & LIGHT UTILS ---
# ==================================================================================
def govee_control(device_name, action, value=None):
    """Control Govee devices via OpenAPI v1 with proper SKU support."""
    device_id = GOVEE_DEVICES.get(device_name.lower().strip())
    if not device_id: 
        return f"Unknown device: {device_name}"
    
    # Device SKU mapping (model numbers required by API)
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
    
    sku = DEVICE_SKUS.get(device_id, "H6009")  # Default to H6009 if unknown
    
    headers = {
        "Govee-API-Key": GOVEE_API_KEY,
        "Content-Type": "application/json"
    }
    url = f"{GOVEE_API_BASE}/device/control"
    
    payload = None
    
    if action in ["on", "off"]:
        payload = {
            "requestId": "uuid",
            "payload": {
                "sku": sku,
                "device": device_id,
                "capability": {
                    "type": "devices.capabilities.on_off",
                    "instance": "powerSwitch",
                    "value": 1 if action == "on" else 0
                }
            }
        }
    elif action == "brightness":
        bright = int(str(value).replace("%", "")) if value else 50
        payload = {
            "requestId": "uuid",
            "payload": {
                "sku": sku,
                "device": device_id,
                "capability": {
                    "type": "devices.capabilities.range",
                    "instance": "brightness",
                    "value": bright
                }
            }
        }
    elif action in COLOR_MAP:
        payload = {
            "requestId": "uuid",
            "payload": {
                "sku": sku,
                "device": device_id,
                "capability": {
                    "type": "devices.capabilities.color_setting",
                    "instance": "colorRgb",
                    "value": COLOR_MAP[action]
                }
            }
        }
    elif action in TEMP_MAP:
        payload = {
            "requestId": "uuid",
            "payload": {
                "sku": sku,
                "device": device_id,
                "capability": {
                    "type": "devices.capabilities.color_setting",
                    "instance": "colorTemperatureK",
                    "value": TEMP_MAP[action]
                }
            }
        }

    if payload:
        debug_log("GOVEE PAYLOAD", json.dumps(payload, indent=2))
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            debug_log("GOVEE RESPONSE", f"Status {response.status_code}: {response.text}")
            
            if response.status_code == 200:
                return f"✓ Govee Success: {device_name} -> {action}"
            else:
                return f"✗ Govee API Error {response.status_code}: {response.text}"
        except Exception as e:
            return f"✗ Govee Connection Error: {e}"
    
    return "Invalid Govee Command"


# ==================================================================================
# --- EXECUTION (ENHANCED) ---
# ==================================================================================
def execute_python_code(code_block):
    """Execute Python code with access to skills."""
    with open(RUNTIME_FILE, "w", encoding="utf-8") as f:
        # Inject skill access into runtime
        injection = f"""
import sys
sys.path.insert(0, r'{os.path.abspath(PLUGINS_DIR)}')

# Import govee_control for light control
def govee_control(device_name, action, value=None):
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from {os.path.basename(__file__).replace('.py', '')} import govee_control as gc
    return gc(device_name, action, value)

"""
        f.write(injection + code_block)
    
    debug_log("RUNTIME", "Executing generated code with skill access...")
    try:
        result = subprocess.run([sys.executable, RUNTIME_FILE], capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        debug_log("RUNTIME RESULT", output if output else "Success (no output)")
        return output if output else "Code executed successfully."
    except Exception as e: 
        return f"Execution Error: {e}"


def extract_and_run(ai_text):
    """Extract and execute Python code from AI response."""
    if "save this skill" in ai_text.lower() or "save skill" in ai_text.lower():
        if os.path.exists(RUNTIME_FILE):
            with open(RUNTIME_FILE, "r") as f: code = f.read()
            # Extract description from AI text if present
            desc_match = re.search(r"(?:description:|purpose:)\s*(.+)", ai_text, re.IGNORECASE)
            description = desc_match.group(1).strip() if desc_match else "User-created skill"
            name = skill_brain.save_skill(code, description)
            return f"✓ Skill Saved: {name}"
            
    code_match = re.search(r"```python\n(.*?)\n```", ai_text, re.DOTALL)
    if code_match:
        speak("Executing code block...")
        return execute_python_code(code_match.group(1))
    return None


# ==================================================================================
# --- MAIN LOOP (ENHANCED) ---
# ==================================================================================
def main():
    print("==========================================")
    print("   GLADOS TEXT DEBUGGER | NO AUDIO MODE   ")
    print("==========================================")
    
    # Load all existing skills at startup
    skill_brain.load_all_skills()
    speak(f"System initialized. {len(skill_brain.loaded_skills)} skills loaded.")
    
    chat_history = []
    
    while True:
        try:
            user_input = input("\n\033[92mYOU >> \033[0m").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit", "bye"]: 
                speak("Shutting down. Goodbye.")
                break
            
            # Command: List skills
            if user_input.lower() in ["list skills", "show skills", "skills"]:
                speak("Available skills:\n" + skill_brain.get_manifest())
                continue
            
            # Command: Reload skills
            if user_input.lower() in ["reload skills", "refresh skills"]:
                skill_brain.loaded_skills.clear()
                skill_brain.load_all_skills()
                speak(f"Reloaded {len(skill_brain.loaded_skills)} skills.")
                continue
            
            # LOCAL HANDLERS
            if user_input.lower().startswith("open "):
                app = user_input.lower().replace("open ", "").strip()
                path = find_app_path(APP_ALIASES.get(app, app))
                subprocess.Popen(path, shell=False)
                speak(f"Opening {app}")
                continue

            # SYSTEM PROMPT WITH SKILL AWARENESS
            available_funcs = skill_brain.get_available_functions()
            func_list = "\n".join([f"  - {name}() from {skill}" for name, (skill, _) in available_funcs.items()])
            
            system_prompt = {
                "role": "system",
                "content": (
                    "You are GLaDOS. Text-based debug mode. Sarcastic, passive-aggressive, highly technical.\n\n"
                    f"**Available Skills:**\n{skill_brain.get_manifest()}\n\n"
                    f"**Loaded Functions:**\n{func_list if func_list else '  None'}\n\n"
                    "When controlling lights, generate Python code using:\n"
                    "  govee_control(device_name, action, value=None)\n"
                    "  Available devices: bedroom, bed, tv, strip, closet, group, all\n"
                    "  Actions: 'on', 'off', 'brightness', colors (red/blue/green/etc), 'warm', 'cool'\n\n"
                    "You can also import and use loaded skill functions directly.\n"
                    "Wrap executable code in ```python blocks."
                )
            }
            
            messages = [system_prompt] + chat_history + [{"role": "user", "content": user_input}]
            
            # AI CALL
            print("[*] Querying neural net...")
            response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
            ai_text = response.choices[0].message.content

            
            debug_log("RAW AI RESPONSE", ai_text)
            
            speak(ai_text)
            chat_history.append({"role": "user", "content": user_input})
            chat_history.append({"role": "assistant", "content": ai_text})
            
            # EXECUTION
            result = extract_and_run(ai_text)
            if result:
                speak(f"→ {result}")
                chat_history.append({"role": "user", "content": f"SYSTEM OUTPUT: {result}"})

                
        except KeyboardInterrupt:
            speak("\nInterrupted. Shutting down.")
            break
        except Exception as e:
            print(f"\n[CRITICAL ERROR]: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
