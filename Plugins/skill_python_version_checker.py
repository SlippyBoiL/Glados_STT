# DESCRIPTION: This script checks the version of the Python interpreter used in the system.
# --- GLADOS SKILL: skill_python_version_checker.py ---

#!/usr/bin/python3

skill_version_checker.py

"""
A simple Python script that checks the version of your Python installation and
compares it to the version used by popular packages.
"""

import importlib.util
import json
import platform
import sys

def check_python_version():
    """
    Checks and prints the version of the Python interpreter used.
    """
    print("Your Python Version:")
    print(sys.version)
    print("Platform:", platform.system(), platform.release())
    print("Python Implementation:", platform.python_implementation())

def check_library_version(library_name):
    """
    Checks and prints the versions of the given library used by your Python installation.
    """
    try:
        spec = importlib.util.find_spec(library_name)
        if spec:
            module = importlib.util.spec_from_fgen(spec.spec, spec.module)
            spec.loader.exec_module(module)
            return spec.origin_info.version
    except Exception as e:
        print(f"Failed to load or check {library_name}.")
        return None
    return None

def main():
    """
    Main function of the script.
    """
    print("Python Version Checker")
    print("-----------------------")
    check_python_version()
    print("\nLibrary Versions")
    print("----------------")
    libraries = ['requests', 'numpy', 'pandas', 'matplotlib', 'scikit-learn']
    for lib in libraries:
        version = check_library_version(lib)
        if version:
            print(f"{lib}: {version}")

if __name__ == "__main__":
    main()