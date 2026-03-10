# DESCRIPTION: Analyzes a given text by removing non-alphanumeric characters, counting words and characters, and determining the most frequently used words.
# --- GLADOS SKILL: skill_text_analyzer.py ---

#!/usr/bin/env python

# script: skill_text_analyzer.py

import re
import sys

def analyze_text(text):
    # Remove non-alphanumeric characters and convert to lowercase
    cleaned_text = re.sub(r'\W+', ' ', text).lower()
    
    # Calculate word count, total characters, and most frequently used words
    words = cleaned_text.split()
    word_count = len(words)
    char_count = sum(len(word) for word in words)
    word_freq = {word: words.count(word) for word in words}
    
    # Find the most frequently used word
    top_word = max(word_freq, key=word_freq.get, default=None)
    
    if top_word:
        print(f"Analyzing '{text}':")
        print(f"Word count: {word_count}")
        print(f"Total characters: {char_count}")
        print(f"Most frequently used word: '{top_word}' ({word_freq[top_word]} occurrences)")
    else:
        print(f"Text contains only whitespace or no words.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python skill_text_analyzer.py <text>")
        sys.exit(1)
    
    try:
        analyze_text(sys.argv[1])
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


Write this script's directory to `/usr/local/bin/` to make it executable, then run `skill_text_analyzer.py <text>` in your terminal. The script will print out the word count, total characters, and most frequently used word in the input text.