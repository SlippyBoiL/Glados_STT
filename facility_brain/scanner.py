from __future__ import annotations

import os
import platform
import socket
import subprocess
import time
from typing import Any, Dict, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ping_host(host: str = "1.1.1.1", count: int = 1) -> bool:
    try:
        r = subprocess.run(
            ["ping", "-n", str(count), host] if platform.system() == "Windows" else ["ping", "-c", str(count), host],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return r.returncode == 0
    except Exception:
        return False


def _top_processes(limit: int = 15) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        import psutil  # type: ignore

        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                procs.append(
                    {
                        "pid": info.get("pid"),
                        "name": info.get("name"),
                        "cpu_percent": info.get("cpu_percent") or 0,
                        "memory_percent": round(float(info.get("memory_percent") or 0), 2),
                    }
                )
            except Exception:
                continue
        procs.sort(key=lambda x: float(x.get("memory_percent") or 0), reverse=True)
        out = procs[:limit]
    except Exception:
        pass
    return out


def _registry_app_hints(limit: int = 40) -> List[str]:
    names: List[str] = []
    if platform.system() != "Windows":
        return names
    try:
        import winreg

        path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            for i in range(min(winreg.QueryInfoKey(key)[0], limit)):
                try:
                    sub = winreg.EnumKey(key, i)
                    if sub and not sub.startswith("."):
                        names.append(sub.replace(".exe", "").lower())
                except Exception:
                    break
    except Exception:
        pass
    return sorted(set(names))[:limit]


def _foreground_window() -> str:
    try:
        import pygetwindow as gw  # type: ignore

        w = gw.getActiveWindow()
        if w and w.title:
            return str(w.title)
    except Exception:
        pass
    return ""


def _load_skills(plugins_dir: str) -> List[Dict[str, str]]:
    """Skills from the unified brain file (not plugins/skill_*.py)."""
    _ = plugins_dir
    try:
        from glados_skills.skills_brain import SkillsBrain

        return SkillsBrain().list_for_scan()
    except Exception:
        return []


def _load_devices_yaml() -> List[Dict[str, Any]]:
    path = os.path.join(REPO_ROOT, "configs", "devices.yaml")
    try:
        import yaml

        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            devices = data.get("devices") or {}
            return [{"name": k, **(v if isinstance(v, dict) else {})} for k, v in devices.items()]
    except Exception:
        pass
    return []


def run_full_scan(
    plugins_dir: str = "plugins",
    custom_facts: List[Dict[str, Any]] | None = None,
    deep_scan_enabled: bool = True,
    facility_cfg: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Full machine scan → dict persisted as the facility brain."""
    now = time.time()
    host = {
        "hostname": platform.node(),
        "platform": platform.system(),
        "release": platform.release(),
        "user": os.environ.get("USERNAME") or os.environ.get("USER") or "",
    }
    hardware: Dict[str, Any] = {"cpu_count": os.cpu_count() or 0}
    network: Dict[str, Any] = {"internet_ok": _ping_host(), "dns_ok": _ping_host("8.8.8.8")}
    alerts: List[str] = []

    try:
        import psutil  # type: ignore

        mem = psutil.virtual_memory()
        hardware["ram_percent"] = float(mem.percent)
        hardware["ram_total_gb"] = round(mem.total / (1024**3), 2)
        disk = psutil.disk_usage("C:\\") if platform.system() == "Windows" else psutil.disk_usage("/")
        hardware["disk_percent"] = float(disk.percent)
        hardware["disk_free_gb"] = round(disk.free / (1024**3), 2)
        if hardware["disk_percent"] > 90:
            alerts.append(f"Disk critical: {hardware['disk_percent']:.0f}% used on system drive.")
        if hardware["ram_percent"] > 92:
            alerts.append(f"RAM critical: {hardware['ram_percent']:.0f}% in use.")
        net = psutil.net_if_addrs()
        network["interfaces"] = list(net.keys())[:12]
    except Exception as e:
        hardware["error"] = str(e)

    state: Dict[str, Any] = {
        "version": 1,
        "scanned_at": now,
        "scanned_at_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "host": host,
        "hardware": hardware,
        "network": network,
        "apps": {
            "registry_hints": _registry_app_hints(),
            "foreground_window": _foreground_window(),
        },
        "processes_top": _top_processes(),
        "skills": _load_skills(plugins_dir),
        "servers": _load_devices_yaml(),
        "alerts": alerts,
        "custom": {"facts": custom_facts or []},
    }
    if deep_scan_enabled:
        try:
            from facility_brain.deep_scan import run_deep_scan

            state["deep"] = run_deep_scan()
            profile = state["deep"].get("user_profile") or {}
            if profile.get("facts"):
                merged = list(custom_facts or [])
                for f in profile.get("facts") or []:
                    merged.append({"id": "profile", "text": str(f)})
                state["custom"]["facts"] = merged
        except Exception as e:
            state["deep"] = {"error": str(e)}

    cfg = facility_cfg or {}
    if cfg.get("file_scan_enabled", True):
        try:
            from facility_brain.file_scan import run_file_scan

            state["file_scan"] = run_file_scan(cfg)
        except Exception as e:
            state["file_scan"] = {"enabled": True, "error": str(e), "file_count": 0}

    return state
