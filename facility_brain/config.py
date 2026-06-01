from __future__ import annotations

import os
from typing import Any, Dict, List

try:
    import yaml
except ImportError:
    yaml = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(REPO_ROOT, "configs", "facility_brain.yaml")


def _defaults() -> Dict[str, Any]:
    return {
        "enabled": True,
        "state_path": os.path.join(REPO_ROOT, "data", "facility_brain_state.json"),
        "scan_on_startup": True,
        "scan_blocking_startup": False,
        "deep_scan_enabled": True,
        "file_scan_enabled": True,
        "file_scan_max_files": 25000,
        "file_scan_max_depth": 12,
        "file_scan_user_profile": True,
        "file_scan_entire_home": False,
        "file_scan_include_appdata": False,
        "file_scan_index_path": os.path.join(REPO_ROOT, "data", "facility_file_index.json"),
        "brain_path_batches_per_root": 6,
        "brain_paths_per_batch": 40,
        "scan_interval_sec": 900,
        "web_search_engine": "google",
        "llm_context_max_chars": 1400,
        "routing_mode": "brain_first",
        "min_decision_confidence": 0.55,
        "autonomy": {
            "allow_app_open": True,
            "allow_app_close": True,
            "allow_powershell": True,
            "allow_skill_run": True,
            "allow_network_fixes": True,
            "allow_server_ssh": True,
            "allow_web_search": True,
        },
        "custom_facts": [],
        "app_aliases": {},
        "decision_rules": [],
    }


def load_facility_brain_config(path: str | None = None) -> Dict[str, Any]:
    cfg = _defaults()
    config_path = path or DEFAULT_CONFIG_PATH
    if yaml is not None and os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                for k, v in data.items():
                    if v is not None:
                        cfg[k] = v
        except Exception:
            pass
    p = str(cfg.get("state_path") or "")
    if p and not os.path.isabs(p):
        cfg["state_path"] = os.path.normpath(os.path.join(REPO_ROOT, p))
    return cfg
