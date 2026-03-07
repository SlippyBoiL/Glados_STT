# DESCRIPTION: Generates a unique, timestamped filename.
# --- GLADOS SKILL: skill_generate.py ---

import uuid
import datetime


def generate_unique_filename() -> str:
    """Return a unique, timestamped filename string."""
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"glados_{ts}_{uuid.uuid4().hex}.txt"


def main() -> None:
    name = generate_unique_filename()
    print(f"Generated unique filename: {name}")


if __name__ == "__main__":
    main()