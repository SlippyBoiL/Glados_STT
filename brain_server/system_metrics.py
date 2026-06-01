from __future__ import annotations

import platform
import time
from typing import Any, Dict, Optional

_last_net: Optional[Dict[str, int]] = None
_last_net_ts: float = 0.0


def get_system_metrics() -> Dict[str, Any]:
    """Host CPU/RAM/disk/network snapshot for the command-center HUD."""
    out: Dict[str, Any] = {
        "ts": time.time(),
        "hostname": platform.node(),
        "platform": platform.system(),
        "cpu_percent": 0.0,
        "ram_percent": 0.0,
        "ram_used_gb": 0.0,
        "ram_total_gb": 0.0,
        "disk_percent": 0.0,
        "disk_used_gb": 0.0,
        "disk_total_gb": 0.0,
        "network_sent_kbps": 0.0,
        "network_recv_kbps": 0.0,
    }

    try:
        import psutil  # type: ignore
    except ImportError:
        out["error"] = "psutil not installed"
        return out

    global _last_net, _last_net_ts

    try:
        out["cpu_percent"] = float(psutil.cpu_percent(interval=0.1))
    except Exception:
        pass

    try:
        mem = psutil.virtual_memory()
        out["ram_percent"] = float(mem.percent)
        out["ram_used_gb"] = round(mem.used / (1024**3), 2)
        out["ram_total_gb"] = round(mem.total / (1024**3), 2)
    except Exception:
        pass

    try:
        disk = psutil.disk_usage("/") if platform.system() != "Windows" else psutil.disk_usage("C:\\")
        out["disk_percent"] = float(disk.percent)
        out["disk_used_gb"] = round(disk.used / (1024**3), 2)
        out["disk_total_gb"] = round(disk.total / (1024**3), 2)
    except Exception:
        pass

    try:
        net = psutil.net_io_counters()
        now = time.time()
        if _last_net and _last_net_ts and net:
            dt = max(now - _last_net_ts, 0.001)
            out["network_sent_kbps"] = round(
                (net.bytes_sent - _last_net["sent"]) / 1024 / dt, 1
            )
            out["network_recv_kbps"] = round(
                (net.bytes_recv - _last_net["recv"]) / 1024 / dt, 1
            )
        if net:
            _last_net = {"sent": net.bytes_sent, "recv": net.bytes_recv}
            _last_net_ts = now
    except Exception:
        pass

    return out
