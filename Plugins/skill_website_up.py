# DESCRIPTION: Checks if a website is reachable.
# --- GLADOS SKILL: skill_is_it_up.py ---

import requests
import sys

def check_site(url="google.com"):
    if len(sys.argv) > 1: url = sys.argv[1]
    if not url.startswith("http"): url = "https://" + url
    
    try:
        code = requests.get(url, timeout=3).status_code
        if code == 200:
            return f"{url} is operational."
        return f"{url} returned status {code}."
    except:
        return f"{url} is unreachable."

if __name__ == "__main__":
    print(check_site())