# DESCRIPTION: Skills are being exported to a JSON file.
# --- GLADOS SKILL: skill_json_export.py ---

#!/usr/bin/env python3
import os
import json

def skill_export_json(**kwargs):
    """
    Export environment variables to a JSON file.

    Parameters:
        **kwargs (dict): Any number of keyword arguments to be exported.

    Returns:
        None
    """

    # Check if environment variables are provided
    if not kwargs:
        print("No variables to export.")
        return

    # Get current date and time
    now = datetime.datetime.now()

    # Create a unique filename
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_ exported_vars.json"

    # Open a file in write mode
    with open(filename, "w") as f:
        # Loop through the keyword arguments
        for key, value in kwargs.items():
            # Write the key-value pair to the file
            f.write(f"{key} = {value}\n")

    # Print a success message
    print(f"Variables exported to {filename}")

if __name__ == "__main__":
    skill_export_json(a=1, b=4, c='test')