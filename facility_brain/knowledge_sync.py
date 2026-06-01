from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_PATH = os.path.join(REPO_ROOT, "data", "computer_brain_memory.json")


def _fact(
    fid: str,
    text: str,
    keywords: List[str],
    *,
    baseline: bool = False,
    category: str = "computer",
) -> Dict[str, Any]:
    return {
        "id": fid,
        "text": text,
        "keywords": sorted(set(k.lower().strip() for k in keywords if k)),
        "baseline": baseline,
        "category": category,
    }


def _chunk_list(items: List[str], size: int) -> List[List[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _keywords_from_names(names: List[str], extra: List[str]) -> List[str]:
    kws = list(extra)
    for name in names:
        low = str(name).lower()
        kws.append(low)
        for token in re.split(r"[\s._-]+", low):
            if len(token) > 2:
                kws.append(token)
    return kws[:60]


def state_to_facts(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn a facility scan into searchable brain facts."""
    facts: List[Dict[str, Any]] = []
    h = state.get("host") or {}
    hw = state.get("hardware") or {}
    net = state.get("network") or {}
    apps = state.get("apps") or {}
    deep = state.get("deep") or {}
    profile = deep.get("user_profile") or {}
    custom = state.get("custom") or {}

    hostname = str(h.get("hostname") or "unknown")
    user = str(h.get("user") or deep.get("env_user") or "unknown")
    platform_name = str(h.get("platform") or "?")

    facts.append(
        _fact(
            "pc_identity",
            f"This PC is {hostname} ({platform_name} {h.get('release', '')}). "
            f"Primary Windows user account: {user}.",
            ["computer", "pc", "hostname", hostname.lower(), user.lower(), "machine", "windows"],
            baseline=True,
            category="host",
        )
    )

    facts.append(
        _fact(
            "pc_resources",
            f"System resources: {hw.get('cpu_count', '?')} CPUs, "
            f"{hw.get('ram_total_gb', '?')} GB RAM ({hw.get('ram_percent', '?')}% in use), "
            f"system drive {hw.get('disk_percent', '?')}% full "
            f"({hw.get('disk_free_gb', '?')} GB free).",
            ["ram", "memory", "disk", "storage", "cpu", "resources", "performance"],
            baseline=True,
            category="hardware",
        )
    )

    inet = "online" if net.get("internet_ok") else "offline"
    facts.append(
        _fact(
            "pc_network",
            f"Network: internet is {inet}. DNS reachability: "
            f"{'ok' if net.get('dns_ok') else 'failed'}. "
            f"Interfaces: {', '.join((net.get('interfaces') or [])[:8])}.",
            ["internet", "network", "wifi", "dns", "online", "offline"],
            baseline=True,
            category="network",
        )
    )

    ips = deep.get("local_ips") or []
    if ips:
        facts.append(
            _fact(
                "pc_local_ips",
                f"Local IP addresses on this machine: {', '.join(ips)}.",
                ["ip", "lan", "address", "network"] + [ip.split(".")[0] for ip in ips[:4]],
                category="network",
            )
        )

    gpu = str(deep.get("gpu") or "").strip()
    if gpu:
        facts.append(
            _fact(
                "pc_gpu",
                f"Graphics adapter: {gpu}.",
                ["gpu", "graphics", "video", "nvidia", "amd", "display"],
                category="hardware",
            )
        )

    tools = deep.get("tools_on_path") or []
    if tools:
        facts.append(
            _fact(
                "pc_dev_tools",
                f"Developer tools detected on PATH: {', '.join(tools)}.",
                ["path", "tools", "dev"] + [t.lower() for t in tools],
                category="software",
            )
        )

    fg = str(apps.get("foreground_window") or "").strip()
    if fg:
        facts.append(
            _fact(
                "pc_foreground",
                f"Last scan foreground window: {fg}.",
                ["window", "foreground", "active", "app"] + _keywords_from_names([fg], []),
                category="apps",
            )
        )

    name = str(profile.get("display_name") or "").strip()
    about = str(profile.get("about") or "").strip()
    if name:
        facts.append(
            _fact(
                "operator_name",
                f"The operator's name is {name}.",
                ["name", "operator", "user", name.lower(), "who am i", "my name"],
                baseline=True,
                category="profile",
            )
        )
    if about:
        facts.append(
            _fact(
                "operator_about",
                f"About the operator: {about}",
                ["about", "operator", "user", "me"] + _keywords_from_names(about.split()[:12], []),
                baseline=True,
                category="profile",
            )
        )

    for i, pf in enumerate(profile.get("facts") or []):
        if not pf:
            continue
        facts.append(
            _fact(
                f"profile_fact_{i}",
                str(pf),
                _keywords_from_names(str(pf).split()[:8], ["operator", "profile", "fact"]),
                category="profile",
            )
        )

    for i, item in enumerate(custom.get("facts") or []):
        text = item.get("text") if isinstance(item, dict) else str(item)
        if not text:
            continue
        kws = item.get("keywords") if isinstance(item, dict) else []
        facts.append(
            _fact(
                f"custom_fact_{i}",
                str(text),
                [str(k) for k in (kws or [])] + _keywords_from_names(str(text).split()[:6], ["custom"]),
                category="custom",
            )
        )

    file_scan = state.get("file_scan") or {}
    if file_scan.get("enabled"):
        try:
            from facility_brain.file_scan_facts import file_scan_to_facts

            facts.extend(file_scan_to_facts(file_scan))
        except Exception:
            pass
    else:
        inv = deep.get("folder_inventory") or {}
        for label in ("desktop", "documents", "downloads", "pictures"):
            items = inv.get(label) or []
            if items:
                preview = ", ".join(str(x) for x in items[:35])
                facts.append(
                    _fact(
                        f"folder_{label}",
                        f"Files/folders on {label} (names only): {preview}.",
                        [label, "files", "folders", "directory"] + _keywords_from_names(items[:20], []),
                        category="files",
                    )
                )

    drives = deep.get("drives") or []
    for i, d in enumerate(drives):
        facts.append(
            _fact(
                f"drive_{i}",
                f"Drive {d.get('mount', '?')} ({d.get('device', '?')}): "
                f"{d.get('percent', '?')}% used, {d.get('free_gb', '?')} GB free.",
                ["drive", "disk", str(d.get("mount", "")).lower()],
                category="hardware",
            )
        )

    programs = deep.get("installed_programs") or []
    for i, chunk in enumerate(_chunk_list(programs, 25)):
        preview = "; ".join(chunk)
        facts.append(
            _fact(
                f"installed_programs_{i}",
                f"Installed software (batch {i + 1}): {preview}.",
                _keywords_from_names(chunk, ["installed", "program", "software", "app"]),
                category="software",
            )
        )

    hints = apps.get("registry_hints") or []
    if hints:
        facts.append(
            _fact(
                "app_launch_hints",
                f"Known launchable apps on this PC (registry): {', '.join(hints[:50])}.",
                _keywords_from_names(hints[:40], ["open", "launch", "app", "program"]),
                category="apps",
            )
        )

    startup = deep.get("startup_items") or []
    if startup:
        facts.append(
            _fact(
                "startup_items",
                f"Programs that run at Windows login: {', '.join(startup)}.",
                _keywords_from_names(startup, ["startup", "boot", "login"]),
                category="system",
            )
        )

    for sk in state.get("skills") or []:
        sid = str(sk.get("id") or sk.get("stem") or "")
        desc = str(sk.get("description") or "")
        if sid:
            facts.append(
                _fact(
                    f"skill_{sid}",
                    f"Learned Glados protocol '{sid}': {desc or 'no description'}.",
                    [sid, sid.replace("_", " "), "skill", "protocol", "run skill"],
                    category="skill",
                )
            )

    for srv in state.get("servers") or []:
        sname = str(srv.get("name") or "")
        if not sname:
            continue
        host_s = str(srv.get("host") or srv.get("ip") or "")
        facts.append(
            _fact(
                f"server_{sname}",
                f"Monitored server '{sname}'"
                + (f" at {host_s}" if host_s else "")
                + ".",
                [sname, "server", "ssh", "monitor", host_s],
                category="server",
            )
        )

    procs = state.get("processes_top") or []
    if procs:
        top = ", ".join(f"{p.get('name')} ({p.get('memory_percent', 0)}% RAM)" for p in procs[:8])
        facts.append(
            _fact(
                "top_processes",
                f"Top memory processes at last scan: {top}.",
                ["process", "task", "memory", "cpu"] + _keywords_from_names([p.get("name", "") for p in procs[:8]], []),
                category="system",
            )
        )

    for i, alert in enumerate(state.get("alerts") or []):
        facts.append(
            _fact(
                f"alert_{i}",
                f"System alert: {alert}",
                ["alert", "problem", "warning", "issue"],
                category="alert",
            )
        )

    scanned = state.get("scanned_at_iso") or "unknown"
    facts.append(
        _fact(
            "scan_meta",
            f"Computer brain last synced from facility scan at {scanned}.",
            ["scan", "brain", "facility", "rescan", "update"],
            baseline=True,
            category="meta",
        )
    )

    return facts


def sync_state_to_brain_memory(
    state: Dict[str, Any],
    out_path: str | None = None,
) -> int:
    """Write all computer knowledge into Glados brain memory file."""
    path = out_path or DEFAULT_OUT_PATH
    facts = state_to_facts(state)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "version": 1,
        "synced_at": state.get("scanned_at"),
        "synced_at_iso": state.get("scanned_at_iso"),
        "hostname": (state.get("host") or {}).get("hostname"),
        "fact_count": len(facts),
        "facts": facts,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return len(facts)


def load_brain_memory(path: str | None = None) -> Dict[str, Any]:
    p = path or DEFAULT_OUT_PATH
    if not os.path.isfile(p):
        return {"facts": []}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return data if isinstance(data, dict) else {"facts": []}
    except Exception:
        return {"facts": []}
