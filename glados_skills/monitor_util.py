# DESCRIPTION: SSH into a device and run a health checklist (uptime, load, disk, services, updates).
# --- GLADOS SKILL: skill_monitor.py ---

from __future__ import annotations

import json
import os
import time

from glados_skills.ssh_util import resolve_target, run_ssh


def _load_monitoring_config():
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(repo, "configs", "monitoring.yaml")
    try:
        import yaml
    except Exception:
        yaml = None
    if not (yaml and os.path.isfile(path)):
        return {"defaults": {}, "devices": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {"defaults": {}, "devices": {}}
        data.setdefault("defaults", {})
        data.setdefault("devices", {})
        return data
    except Exception:
        return {"defaults": {}, "devices": {}}


def _merge(a: dict, b: dict) -> dict:
    out = dict(a or {})
    for k, v in (b or {}).items():
        out[k] = v
    return out


def _sh(cmd: str, target: str) -> str:
    return run_ssh(cmd, target=target)


def _linux_health(target: str, profile: dict) -> dict:
    res: dict = {"os": "linux", "checks": {}, "alerts": []}

    res["checks"]["uptime"] = _sh("uptime -p || uptime", target)
    res["checks"]["kernel"] = _sh("uname -a", target)

    # CPU/load
    load = _sh("cat /proc/loadavg 2>/dev/null | awk '{print $1\" \"$2\" \"$3}'", target)
    cpu_count = _sh("nproc 2>/dev/null || getconf _NPROCESSORS_ONLN", target)
    res["checks"]["loadavg"] = load
    res["checks"]["cpu_count"] = cpu_count

    try:
        l1 = float((load or "").strip().split()[0])
        ncpu = int((cpu_count or "1").strip().split()[0])
        warn = float(profile.get("warn_load_per_cpu", 1.5))
        if ncpu > 0 and (l1 / ncpu) > warn:
            res["alerts"].append(f"High load: 1m load {l1} on {ncpu} CPUs (>{warn} per CPU)")
    except Exception:
        pass

    # Memory
    res["checks"]["mem"] = _sh("free -h 2>/dev/null || vm_stat 2>/dev/null || true", target)

    # Disk
    res["checks"]["disk"] = _sh("df -h --output=source,fstype,size,used,avail,pcent,target -x tmpfs -x devtmpfs 2>/dev/null || df -h", target)
    warn_disk = int(profile.get("warn_disk_percent", 90))
    pcent_lines = _sh("df -P | awk 'NR>1 {print $5\" \"$6}'", target)
    try:
        for line in (pcent_lines or "").splitlines():
            pct, mount = line.split(maxsplit=1)
            pct_i = int(pct.strip().replace("%", ""))
            if pct_i >= warn_disk:
                res["alerts"].append(f"Disk nearly full: {mount} at {pct_i}% (>= {warn_disk}%)")
    except Exception:
        pass

    # Services (systemd)
    services = profile.get("services") or []
    if services:
        svc_status = {}
        for svc in services:
            svc = str(svc).strip()
            if not svc:
                continue
            svc_status[svc] = _sh(f"systemctl is-active {svc} 2>/dev/null || echo unknown", target).strip()
            if svc_status[svc] not in ("active", "unknown"):
                res["alerts"].append(f"Service not active: {svc} = {svc_status[svc]}")
        res["checks"]["services"] = svc_status

    # Docker containers
    containers = profile.get("docker_containers") or []
    if containers:
        docker_ok = _sh("command -v docker >/dev/null 2>&1 && echo yes || echo no", target).strip()
        if docker_ok == "yes":
            running = _sh("docker ps --format '{{.Names}}' 2>/dev/null", target)
            running_set = set([x.strip() for x in (running or "").splitlines() if x.strip()])
            # Consider a container "present" if any running name contains the requested token.
            missing = []
            for c in containers:
                token = str(c).strip()
                if not token:
                    continue
                if not any(token.lower() in r.lower() for r in running_set):
                    missing.append(token)
            res["checks"]["docker_running"] = sorted(list(running_set))
            if missing:
                res["alerts"].append(f"Docker containers not running: {', '.join(missing)}")
        else:
            res["alerts"].append("Docker not installed but docker_containers configured.")

    # Updates (best-effort)
    updates = _sh(
        "if command -v apt-get >/dev/null 2>&1; then "
        "  sudo -n true 2>/dev/null; "
        "  apt-get -s upgrade 2>/dev/null | awk '/^Inst /{c++} END{print c+0}'; "
        "elif command -v dnf >/dev/null 2>&1; then "
        "  dnf -q check-update 2>/dev/null | wc -l; "
        "elif command -v yum >/dev/null 2>&1; then "
        "  yum -q check-update 2>/dev/null | wc -l; "
        "else echo unknown; fi",
        target,
    ).strip()
    res["checks"]["updates_pending"] = updates

    # Custom commands (best-effort)
    cmds = profile.get("commands") or []
    if cmds:
        out = {}
        for item in cmds:
            if isinstance(item, str):
                name = item
                cmd = item
            elif isinstance(item, dict):
                name = str(item.get("name") or item.get("cmd") or "").strip()
                cmd = str(item.get("cmd") or "").strip()
            else:
                continue
            if not (name and cmd):
                continue
            out[name] = _sh(cmd, target)
        if out:
            res["checks"]["custom"] = out

            # Simple heuristics for known checks
            if "pihole_status" in out and "active" not in (out["pihole_status"] or "").lower():
                res["alerts"].append("Pi-hole status is not active.")
            if "twingate_systemd" in out and "no running" in (out["twingate_systemd"] or "").lower():
                # only alert if docker check also indicates no running container
                if "twingate_docker" in out and "no running" in (out["twingate_docker"] or "").lower():
                    res["alerts"].append("Twingate connector not detected (systemd/docker).")
            if "pve_version" in out and "missing" in (out["pve_version"] or "").lower():
                res["alerts"].append("Proxmox pveversion unavailable.")
            if "pve_web" in out:
                code = (out["pve_web"] or "").strip()
                if code and code not in ("200", "301", "302", "401", "403"):
                    res["alerts"].append(f"Proxmox web UI on :8080 returned {code}.")

    return res


def monitor_once(device: str) -> dict:
    cfg = _load_monitoring_config()
    defaults = cfg.get("defaults") or {}
    per_dev = (cfg.get("devices") or {}).get(device) or {}
    profile = _merge(defaults, per_dev)

    # Detect OS (and catch SSH failures early)
    os_probe = _sh("uname -s 2>/dev/null || echo unknown", device).strip()
    if os_probe.lower().startswith("ssh failed:"):
        return {
            "device": resolve_target(device),
            "os": "unknown",
            "checks": {"ssh": os_probe},
            "alerts": [os_probe],
            "ts": int(time.time()),
        }
    os_name = os_probe.lower()
    if "linux" in os_name:
        result = _linux_health(device, profile)
    else:
        result = {"os": os_name or "unknown", "checks": {"uname": os_name}, "alerts": ["Unsupported OS for monitoring profile."]}

    result["device"] = resolve_target(device)
    result["ts"] = int(time.time())
    return result


def monitor_loop(device: str, interval_sec: int = 30):
    while True:
        report = monitor_once(device)
        print(json.dumps(report, indent=2))
        time.sleep(max(5, int(interval_sec)))


if __name__ == "__main__":
    # Usage:
    #   python plugins/skill_monitor.py <device>
    #   python plugins/skill_monitor.py <device> --loop 30
    import sys

    args = sys.argv[1:]
    if not args:
        print("Usage: python plugins/skill_monitor.py <device> [--loop SECONDS]")
        raise SystemExit(2)

    dev = args[0]
    if "--loop" in args:
        i = args.index("--loop")
        sec = int(args[i + 1]) if i + 1 < len(args) else 30
        monitor_loop(dev, interval_sec=sec)
    else:
        print(json.dumps(monitor_once(dev), indent=2))

