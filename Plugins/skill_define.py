# DESCRIPTION: Fetches word definitions from free API.
# --- GLADOS SKILL: skill_define.py ---

import requests
import sys

def define_word(word="science"):
    if len(sys.argv) > 1: word = sys.argv[1]
    
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        data = requests.get(url).json()
        if isinstance(data, list):
            meaning = data[0]['meanings'][0]['definitions'][0]['definition']
            return f"Definition of '{word}': {meaning}"
        return f"'{word}' is not in my database. Perhaps you made it up."
    except:
        return "Dictionary error."

if __name__ == "__main__":
    print(define_word())