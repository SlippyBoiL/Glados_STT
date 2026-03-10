# DESCRIPTION: Prints CPU, memory, disk usage and top CPU processes.
# --- GLADOS SKILL: skill_cpu_stats.py ---

import datetime

try:
    import psutil
except ImportError:
    psutil = None


def main():
    if not psutil:
        print("Install psutil: pip install psutil")
        return
    print(f"Boot time: {datetime.datetime.fromtimestamp(psutil.boot_time())}")
    print(f"CPU: {psutil.cpu_percent(interval=1)}%")
    print(f"Memory: {psutil.virtual_memory().percent}%")
    try:
        path = "C:\\" if __import__("sys").platform == "win32" else "/"
        print(f"Disk: {psutil.disk_usage(path).percent}%")
    except Exception:
        print("Disk: (unavailable)")
    print("Top CPU (sample):")
    for p in sorted(
        psutil.process_iter(["name", "cpu_percent"]),
        key=lambda x: x.info.get("cpu_percent") or 0,
        reverse=True,
    )[:8]:
        info = p.info
        print(f"  {info.get('name', '?')}: {info.get('cpu_percent') or 0}%")


if __name__ == "__main__":
    main()
