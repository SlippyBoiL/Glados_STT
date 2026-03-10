# DESCRIPTION: Prints system disk, memory, and CPU usage.
# --- GLADOS SKILL: skill_system_info.py ---

import os
import sys

try:
    import psutil
except ImportError:
    psutil = None


def get_disk_usage():
    if sys.platform == "win32":
        path = os.environ.get("SystemDrive", "C:") + "\\"
    else:
        path = "/"
    try:
        u = psutil.disk_usage(path) if psutil else None
        if u:
            return f"Disk: {u.percent}% used ({u.free // (1024**3)} GB free)"
    except Exception:
        pass
    return "Disk: (unavailable)"


def get_memory_usage():
    if psutil:
        return f"Memory: {psutil.virtual_memory().percent}% used"
    return "Memory: (install psutil)"


def get_cpu_usage():
    if psutil:
        return f"CPU: {psutil.cpu_percent(interval=0.5)}%"
    return "CPU: (install psutil)"


def main():
    print(get_disk_usage())
    print(get_memory_usage())
    print(get_cpu_usage())


if __name__ == "__main__":
    main()
