# DESCRIPTION: A Python script using regular expressions to extract unique patterns from input strings.
# --- GLADOS SKILL: skill_unique_pattern_matcher.py ---

#!/usr/bin/python

# skill_unique_pattern_matcher.py

import os
import re

def unique_pattern_matcher(pattern, input_string):
    """
    Use regular expression to find all unique patterns in the input string.

    Args:
        pattern (str): A regular expression pattern.
        input_string (str): The string to match against.

    Returns:
        set: A set of unique patterns found in the input string.
    """
    matches = re.findall(pattern, input_string)
    return set(matches)

if __name__ == "__main__":
    # get the list of files in the current directory
    dir_files = os.listdir(".")
    
    # initialize a set to store the unique patterns
    unique_patterns = set()
    
    # iterate over each file in the directory
    for file in dir_files:
        # skip os and __pycache__ directories
        if file in ["__pycache__", "os"]:
            continue
        
        try:
            # try to open the file as a text file
            with open(file, "r") as f:
                file_contents = f.read()
                
                # find all unique patterns in the file contents
                patterns = unique_pattern_matcher(r"\b\w*[a-zA-Z]\w*\b", file_contents)
                
                # add the patterns to the set of unique patterns
                unique_patterns.update(patterns)
        except FileNotFoundError:
            # handle the case where the file does not exist
            print(f"Error: Unable to read {file}")]
            
    # print the unique patterns
    print("Unique Patterns:")
    for pattern in sorted(unique_patterns):
        print(pattern)