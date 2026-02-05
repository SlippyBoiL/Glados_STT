# DESCRIPTION: Fetches public IP and geolocation data.
# --- GLADOS SKILL: skill_public_ip.py ---

import requests

def get_public_ip():
    try:
        response = requests.get("http://ip-api.com/json/", timeout=5)
        data = response.json()
        return f"Surveillance Data: {data['query']} ({data['city']}, {data['country']}) - ISP: {data['isp']}"
    except Exception as e:
        return f"Network obfuscated. Error: {e}"

if __name__ == "__main__":
    print(get_public_ip())