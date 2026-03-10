# DESCRIPTION: Logs a message with a timestamp.
# --- GLADOS SKILL: skill_logging.py ---

import datetime


def log(message, fmt="%Y-%m-%d %H:%M:%S"):
    ts = datetime.datetime.now().strftime(fmt)
    print(f"[{ts}] {message}")


def main():
    log("Skill log started")
    log("Sample entry")


if __name__ == "__main__":
    main()
