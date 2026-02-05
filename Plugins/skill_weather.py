# DESCRIPTION: Fetches simple text-based weather.
# --- GLADOS SKILL: skill_weather.py ---

import requests

def get_weather():
    try:
        # format 3 is a one-line output
        response = requests.get("https://wttr.in/?format=3", timeout=5)
        return f"Atmospheric Report: {response.text.strip()}"
    except:
        return "Unable to access meteorological sensors."

if __name__ == "__main__":
    print(get_weather())