from __future__ import annotations

import os
import platform
import socket
import subprocess
from typing import Any, Dict, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_user_profile() -> Dict[str, Any]:
    path = os.path.join(REPO_ROOT, "configs", "user_profile.yaml")
    if not os.path.isfile(path):
        return {}
    try:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _list_dir_names(path: str, limit: int = 40) -> List[str]:
    if not path or not os.path.isdir(path):
        return []
    try:
        names = []
        for name in os.listdir(path):
            if name.startswith("."):
                continue
            names.append(name)
            if len(names) >= limit:
                break
        return sorted(names, key=str.lower)
    except Exception:
        return []


def _installed_programs(limit: int = 120) -> List[str]:
    names: List[str] = []
    if platform.system() != "Windows":
        return names
    try:
        import winreg

        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        seen = set()
        for hive, sub in roots:
            try:
                with winreg.OpenKey(hive, sub) as key:
                    n = winreg.QueryInfoKey(key)[0]
                    for i in range(n):
                        if len(names) >= limit:
                            break
                        try:
                            sk = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, sk) as appkey:
                                disp, _ = winreg.QueryValueEx(appkey, "DisplayName")
                                if disp and disp not in seen:
                                    seen.add(disp)
                                    names.append(str(disp)[:120])
                        except Exception:
                            continue
            except Exception:
                continue
    except Exception:
        pass
    return sorted(names, key=str.lower)[:limit]


def _startup_items(limit: int = 30) -> List[str]:
    items: List[str] = []
    if platform.system() != "Windows":
        return items
    try:
        import winreg

        path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            for i in range(min(winreg.QueryInfoKey(key)[1], limit)):
                try:
                    name, _, _ = winreg.EnumValue(key, i)
                    items.append(str(name))
                except Exception:
                    break
    except Exception:
        pass
    return items


def _all_drives() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        import psutil  # type: ignore

        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                out.append(
                    {
                        "device": part.device,
                        "mount": part.mountpoint,
                        "fstype": part.fstype,
                        "percent": round(float(usage.percent), 1),
                        "free_gb": round(usage.free / (1024**3), 1),
                    }
                )
            except Exception:
                continue
    except Exception:
        pass
    return out


def _local_ips() -> List[str]:
    ips: List[str] = []
    try:
        import psutil  # type: ignore

        for _if, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                if getattr(a, "family", None) == socket.AF_INET:
                    ip = str(a.address)
                    if ip and not ip.startswith("127."):
                        ips.append(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return sorted(set(ips))[:8]


def _gpu_name() -> str:
    if platform.system() != "Windows":
        return ""
    try:
        r = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            capture_output=True,
            text=True,
            timeout=12,
        )
        lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip() and ln.strip().lower() != "name"]
        return lines[0] if lines else ""
    except Exception:
        return ""


def _tools_on_path() -> List[str]:
    tools = ["python", "py", "node", "npm", "git", "ollama", "code", "chrome", "firefox"]
    found = []
    path_env = os.environ.get("PATH") or ""
    for t in tools:
        for folder in path_env.split(os.pathsep):
            candidate = os.path.join(folder, f"{t}.exe" if platform.system() == "Windows" else t)
            if os.path.isfile(candidate):
                found.append(t)
                break
    return found


def run_deep_scan() -> Dict[str, Any]:
    """Rich machine + user profile (local only). Kept separate from lightweight metrics."""
    home = os.path.expanduser("~")
    profile = load_user_profile()
    user_paths = {
        "home": home,
        "desktop": os.path.join(home, "Desktop"),
        "documents": os.path.join(home, "Documents"),
        "downloads": os.path.join(home, "Downloads"),
        "pictures": os.path.join(home, "Pictures"),
    }
    return {
        "user_profile": profile,
        "user_paths": {k: v for k, v in user_paths.items() if v},
        "folder_inventory": {
            "desktop": _list_dir_names(user_paths["desktop"]),
            "documents": _list_dir_names(user_paths["documents"]),
            "downloads": _list_dir_names(user_paths["downloads"]),
        },
        "installed_programs": _installed_programs(),
        "startup_items": _startup_items(),
        "drives": _all_drives(),
        "local_ips": _local_ips(),
        "gpu": _gpu_name(),
        "tools_on_path": _tools_on_path(),
        "env_user": os.environ.get("USERNAME") or os.environ.get("USER") or "",
        "computer_name": platform.node(),
    }
