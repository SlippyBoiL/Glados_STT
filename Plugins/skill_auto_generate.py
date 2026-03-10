import os
import re
import time
import ast
from openai import OpenAI

# Bring in the compiler so the factory can update the brain
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import brain_compiler
except ImportError:
    print("[!] Could not import brain_compiler. Make sure it is in the main Glados folder.")

# --- SETUP ---
client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
MODEL_NAME = "llama3.2"
PLUGINS_DIR = "plugins"

def auto_manufacture_skill():
    print("[*] Factory Assembly Line Started...")
    
    # 1. BRAINSTORMING PHASE
    idea_prompt = "You are an autonomous AI factory. Invent a short, highly useful Python script that a voice assistant could use. Just give me a 1 sentence description of what it does. Do not write the code yet."
    try:
        idea_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": idea_prompt}],
            temperature=0.8
        )
        description = idea_response.choices[0].message.content.strip()
        print(f"[*] Drafting new skill...\n    -> {description}")
    except Exception as e:
        print(f"[!] Brainstorming failed: {e}")
        return

    # 2. DRAFTING AND SELF-HEALING PHASE
    code_prompt = f"Write a complete, working Python script for this task: '{description}'. The code must be inside a ```python ``` markdown block. Do not include any explanations outside the block."
    
    max_retries = 3
    valid_code = False
    final_code = ""

    for attempt in range(max_retries):
        print(f"[*] Writing code (Attempt {attempt + 1}/{max_retries})...")
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": code_prompt}],
                temperature=0.3
            )
            
            draft_text = response.choices[0].message.content
            
            # Extract just the python code from the markdown block
            code_match = re.search(r"```python\n(.*?)\n```", draft_text, re.DOTALL)
            if code_match:
                final_code = code_match.group(1)
            else:
                final_code = draft_text.replace("```", "")
                
            # --- THE QUALITY ASSURANCE CHECK ---
            ast.parse(final_code) # This tests if the code is actually valid Python
            valid_code = True
            print("[+] Syntax check passed. Code is structurally sound.")
            break # It works! Break out of the retry loop.
            
        except SyntaxError as e:
            print(f"[!] Syntax Error detected by AST: {e}")
            print("[*] Forcing Llama 3.2 to rewrite the defective code...")
            # Append the error to the prompt and make it try again
            code_prompt += f"\n\nCRITICAL ERROR: Your last attempt failed with a Syntax Error: {e}. Please fix the exact line causing the syntax error and return the full corrected code."
        except Exception as e:
             print(f"[!] Generation error: {e}")
             return
    
    if not valid_code:
        print("[!] Factory failed to produce working code after 3 attempts. Scrapping project.")
        return
        
    # 3. ASSEMBLY PHASE (Saving the file)
    name_match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", final_code)
    if name_match:
        filename = f"skill_{name_match.group(1)}.py"
    else:
        filename = f"skill_{int(time.time())}.py"

    filepath = os.path.join(PLUGINS_DIR, filename)
    header = f"# DESCRIPTION: {description}\n# --- AUTONOMOUSLY GENERATED SKILL ---\n\n"
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + final_code)
        print(f"[+] Successfully manufactured: {filename}")
    except Exception as e:
        print(f"[!] Failed to save file: {e}")
        return
    
    # 4. NEUROPLASTICITY PHASE (Updating her brain)
    print("[*] Alerting Omni-Brain to new skill...")
    try:
        brain_compiler.update_brain_json()
    except Exception as e:
        print(f"[!] Failed to trigger brain compiler: {e}")

if __name__ == "__main__":
    if not os.path.exists(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR)
        
    print("=== GLaDOS AUTONOMOUS SKILL FACTORY ===")
    print("Press Ctrl+C to stop the assembly line.\n")
    
    try:
        while True:
            auto_manufacture_skill()
            print("\n[*] Factory cooling down for 10 seconds before next build...\n")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n[!] Factory shut down.")