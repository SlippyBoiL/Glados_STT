#!/usr/bin/env python3
"""
Restart KernelLamma.py when you save project source files (debounced).

Does NOT watch visual_buffer.png / .wav / runtime_action.py — those change often and would
restart the bot in a loop.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
KERNEL = REPO_ROOT / "KernelLamma.py"
DEBOUNCE_SEC = 1.5

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("[!] Missing package `watchdog`. With your venv activated, run:")
    print("    python -m pip install watchdog")
    print("    python run_watch.py")
    print("[!] On Windows, `py run_watch.py` may use another Python than `(venv)` — use `python` inside the venv.")
    raise SystemExit(1)


def _interesting(path: str) -> bool:
    path = path.replace("\\", "/")
    low = path.lower()
    name = os.path.basename(path)

    if name in ("visual_buffer.png", "runtime_action.py"):
        return False
    if name.endswith(".wav"):
        return False
    if "__pycache__" in low:
        return False
    if ".git" in Path(path).parts:
        return False
    if "/venv/" in low or low.endswith("/venv"):
        return False
    if "/.cursor/" in low:
        return False

    ext = Path(path).suffix.lower()
    if ext in (".py", ".yaml", ".yml", ".toml", ".json", ".md", ".txt"):
        return True
    if name == ".gitignore":
        return True
    return False


_kernel_proc: subprocess.Popen | None = None
_timer: threading.Timer | None = None
_timer_lock = threading.Lock()


def _start_kernel() -> None:
    global _kernel_proc
    if _kernel_proc is not None and _kernel_proc.poll() is None:
        print("[*] Stopping kernel...")
        _kernel_proc.terminate()
        try:
            _kernel_proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            _kernel_proc.kill()
    print("[*] Starting KernelLamma.py ...\n")
    _kernel_proc = subprocess.Popen(
        [sys.executable, str(KERNEL)],
        cwd=str(REPO_ROOT),
    )


def _schedule_restart() -> None:
    global _timer

    def fire() -> None:
        global _timer
        with _timer_lock:
            _timer = None
        print("\n[*] Source saved — restarting kernel.\n")
        try:
            _start_kernel()
        except Exception as e:
            print(f"[!] Restart failed: {e}")

    with _timer_lock:
        if _timer is not None:
            _timer.cancel()
        _timer = threading.Timer(DEBOUNCE_SEC, fire)
        _timer.daemon = True
        _timer.start()


class _Handler(FileSystemEventHandler):
    def on_modified(self, event):  # type: ignore[override]
        if event.is_directory:
            return
        if _interesting(event.src_path):
            _schedule_restart()

    def on_created(self, event):  # type: ignore[override]
        if event.is_directory:
            return
        if _interesting(event.src_path):
            _schedule_restart()


def main() -> None:
    if not KERNEL.is_file():
        print(f"[!] Missing {KERNEL}")
        raise SystemExit(1)

    print("[*] Watch mode: saving .py / .yaml / etc. restarts the kernel after {:.1f}s idle.".format(DEBOUNCE_SEC))
    print("[*] Ignored: visual_buffer.png, *.wav, runtime_action.py, venv, .git\n")

    _start_kernel()

    handler = _Handler()
    observer = Observer()
    observer.schedule(handler, str(REPO_ROOT), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(0.5)
            if _kernel_proc is not None and _kernel_proc.poll() is not None:
                code = _kernel_proc.returncode
                print(f"\n[!] Kernel exited ({code}). Fix errors and save a file to restart, or Ctrl+C.\n")
                _kernel_proc = None
    except KeyboardInterrupt:
        print("\n[*] Shutting down watch...")
        observer.stop()
        observer.join()
        if _kernel_proc is not None and _kernel_proc.poll() is None:
            _kernel_proc.terminate()
            _kernel_proc.wait(timeout=5)


if __name__ == "__main__":
    main()
