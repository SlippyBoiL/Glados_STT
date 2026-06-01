"""
GLaDOS system tray launcher.

Starts the kernel and brain dashboard API. Open the brain UI from the tray menu.

LAN access:
  1. Set brain_dashboard_url in configs/glados.yaml to your PC LAN IP,
     e.g. http://192.168.1.50:8080
  2. Windows Firewall (Private network only):
     netsh advfirewall firewall add rule name="Glados Brain Dashboard" dir=in action=allow protocol=TCP localport=8080 profile=private
  3. On phone/tablet (same WiFi): open brain_dashboard_url
"""

import json
import os
import socket
import subprocess
import sys
import threading
import webbrowser
from typing import Any, Dict, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KERNEL_PATH = os.path.join(BASE_DIR, "KernelLamma.py")
BRAIN_SERVER_MODULE = "brain_server.main"
FLAGS_PATH = os.path.join(BASE_DIR, "plugins", "subsystem_flags.json")

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from glados_config import load_config  # noqa: E402


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _dashboard_url() -> str:
    cfg = load_config()
    url = str(cfg.get("brain_dashboard_url") or "").strip()
    if url and "localhost" not in url and "127.0.0.1" not in url:
        return url
    port = int(cfg.get("brain_dashboard_port") or 8080)
    flags = _read_flags()
    flag_url = str(flags.get("dashboard_url") or "").strip()
    if flag_url and "localhost" not in flag_url:
        return flag_url
    return f"http://{_lan_ip()}:{port}"


DEFAULT_FLAGS: Dict[str, Any] = {
    "vision_enabled": True,
    "monitoring_enabled": True,
    "cursor_auto_inject": False,
    "dashboard_url": "http://localhost:8080",
    "streamlit_port": 8501,
    "brain_dashboard_port": 8080,
}


def _read_flags() -> Dict[str, Any]:
    try:
        if not os.path.exists(FLAGS_PATH):
            return dict(DEFAULT_FLAGS)
        with open(FLAGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        if not isinstance(data, dict):
            return dict(DEFAULT_FLAGS)
        merged = dict(DEFAULT_FLAGS)
        for k, v in data.items():
            merged[k] = v
        return merged
    except Exception:
        return dict(DEFAULT_FLAGS)


def _write_flags(flags: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(FLAGS_PATH), exist_ok=True)
    with open(FLAGS_PATH, "w", encoding="utf-8") as f:
        json.dump(flags, f, indent=2)


class ProcessController:
    def __init__(self, cmd: list, name: str) -> None:
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._cmd = cmd
        self._name = name

    def start(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return
            self._proc = subprocess.Popen(self._cmd, cwd=BASE_DIR)

    def restart(self) -> None:
        with self._lock:
            self.stop_unlocked()
            self._proc = subprocess.Popen(self._cmd, cwd=BASE_DIR)

    def stop_unlocked(self) -> None:
        if not self._proc or self._proc.poll() is not None:
            return
        try:
            self._proc.terminate()
        except Exception:
            pass
        try:
            self._proc.wait(timeout=5)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass

    def stop(self) -> None:
        with self._lock:
            self.stop_unlocked()


class KernelController(ProcessController):
    def __init__(self) -> None:
        super().__init__([sys.executable, KERNEL_PATH], "kernel")


class BrainServerController(ProcessController):
    def __init__(self) -> None:
        super().__init__(
            [sys.executable, "-m", BRAIN_SERVER_MODULE],
            "brain_server",
        )


def run_tray() -> None:
    try:
        import pystray  # type: ignore
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        print(
            "[tray] pystray (and pillow) not installed. "
            "Install `pystray` to enable the system tray controller."
        )
        return

    cfg = load_config()
    kernel = KernelController()
    brain = BrainServerController()

    kernel.start()
    if cfg.get("brain_dashboard_enabled", True):
        brain.start()

    icon_ref = {"icon": None}

    def toggle_flag(flag_key: str) -> None:
        flags = _read_flags()
        flags[flag_key] = not bool(flags.get(flag_key, True))
        _write_flags(flags)
        print(f"[tray] {flag_key} -> {flags[flag_key]}")

    def restart_kernel(_: Any = None) -> None:
        kernel.restart()

    def restart_brain(_: Any = None) -> None:
        brain.restart()

    def open_dashboard(_: Any = None) -> None:
        url = _dashboard_url().rstrip("/") + "/hud/"
        print(f"[tray] Opening command center: {url}")
        webbrowser.open(url)

    icon_img = Image.new("RGB", (64, 64), (30, 30, 30))
    d = ImageDraw.Draw(icon_img)
    d.ellipse((8, 8, 56, 56), fill=(200, 200, 200))
    d.text((20, 22), "G", fill=(10, 10, 10))

    menu = pystray.Menu(
        pystray.MenuItem("Restart Kernel", restart_kernel),
        pystray.MenuItem("Restart Brain Dashboard", restart_brain),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Toggle Vision",
            lambda _: toggle_flag("vision_enabled"),
        ),
        pystray.MenuItem(
            "Toggle Monitoring",
            lambda _: toggle_flag("monitoring_enabled"),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Toggle Cursor Auto-inject",
            lambda _: toggle_flag("cursor_auto_inject"),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Brain Dashboard", open_dashboard),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Quit",
            lambda _: (
                kernel.stop(),
                brain.stop(),
                icon_ref["icon"].stop() if icon_ref["icon"] is not None else None,
            ),
        ),
    )

    icon = pystray.Icon("Glados", icon_img, "GLaDOS", menu=menu)
    icon_ref["icon"] = icon
    icon.run()


def main() -> None:
    run_tray()


if __name__ == "__main__":
    main()
