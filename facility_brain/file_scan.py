from __future__ import annotations

import json
import os
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INDEX_PATH = os.path.join(REPO_ROOT, "data", "facility_file_index.json")

# Directory names skipped anywhere in the path (case-insensitive on Windows)
DEFAULT_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".next",
        "dist",
        "build",
        "Cache",
        "Caches",
        "INetCache",
        "Temp",
        "tmp",
        "Windows",
        "WinSxS",
        "System Volume Information",
        "$Recycle.Bin",
        "Program Files",
        "Program Files (x86)",
        "ProgramData",
        "AppData",  # skip whole AppData unless user enables
    }
)

# Sensitive — never index by default
DEFAULT_SKIP_FILE_PREFIXES = (".env", ".pem", ".key", "id_rsa", "credentials", "secrets")

DEFAULT_ROOT_LABELS = {
    "desktop": "Desktop",
    "documents": "Documents",
    "downloads": "Downloads",
    "pictures": "Pictures",
    "videos": "Videos",
    "music": "Music",
    "onedrive": "OneDrive",
}


def _normalize_path(p: str) -> str:
    return os.path.normpath(os.path.expanduser(p))


def _should_skip_dir(dirname: str, full_path: str, cfg: Dict[str, Any]) -> bool:
    skip = DEFAULT_SKIP_DIR_NAMES
    extra = cfg.get("file_scan_skip_dir_names") or []
    if isinstance(extra, list):
        skip = skip | {str(x).lower() for x in extra}
    if cfg.get("file_scan_include_appdata"):
        skip = {x for x in skip if x.lower() != "appdata"}

    name = dirname.lower()
    if name in skip:
        return True

    low_path = full_path.lower()
    for blocked in cfg.get("file_scan_blocked_path_contains") or []:
        if str(blocked).lower() in low_path:
            return True
    return False


def _should_skip_file(filename: str, cfg: Dict[str, Any]) -> bool:
    low = filename.lower()
    max_mb = float(cfg.get("file_scan_max_file_mb") or 200)
    for prefix in DEFAULT_SKIP_FILE_PREFIXES:
        if low.startswith(prefix) or low == prefix:
            return True
    skip_ext = cfg.get("file_scan_skip_extensions") or [
        ".exe",
        ".dll",
        ".msi",
        ".sys",
        ".bin",
        ".iso",
        ".vmdk",
        ".pak",
    ]
    for ext in skip_ext:
        if low.endswith(str(ext).lower()):
            return True
    return False


def resolve_scan_roots(cfg: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return list of (label, absolute_path) to walk."""
    home = _normalize_path(os.path.expanduser("~"))
    roots: List[Tuple[str, str]] = []

    custom = cfg.get("file_scan_extra_roots") or []
    if isinstance(custom, list):
        for item in custom:
            if isinstance(item, str) and item.strip():
                p = _normalize_path(item.strip())
                label = os.path.basename(p) or "extra"
                roots.append((label, p))
            elif isinstance(item, dict) and item.get("path"):
                p = _normalize_path(str(item["path"]))
                label = str(item.get("label") or os.path.basename(p) or "extra")
                roots.append((label, p))

    if cfg.get("file_scan_user_profile", True):
        for label, folder in DEFAULT_ROOT_LABELS.items():
            path = os.path.join(home, folder)
            if os.path.isdir(path):
                roots.append((label, path))

        # OneDrive folder if present (may overlap Documents)
        od = os.path.join(home, "OneDrive")
        if os.path.isdir(od) and not any(r[1] == od for r in roots):
            roots.append(("onedrive", od))

    if cfg.get("file_scan_entire_home", False):
        if not any(r[1] == home for r in roots):
            roots.insert(0, ("home", home))

    # Deduplicate by path
    seen: Set[str] = set()
    out: List[Tuple[str, str]] = []
    for label, path in roots:
        if path not in seen and os.path.isdir(path):
            seen.add(path)
            out.append((label, path))
    return out


def run_file_scan(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Walk configured user folders and build a searchable file index.
    Full list → data/facility_file_index.json; summary → facility brain state.
    """
    if not cfg.get("file_scan_enabled", True):
        return {"enabled": False}

    max_files = max(1000, int(cfg.get("file_scan_max_files") or 25000))
    max_depth = max(1, int(cfg.get("file_scan_max_depth") or 12))
    index_path = str(cfg.get("file_scan_index_path") or DEFAULT_INDEX_PATH)
    if not os.path.isabs(index_path):
        index_path = os.path.join(REPO_ROOT, index_path)

    roots = resolve_scan_roots(cfg)
    if not roots:
        return {"enabled": True, "error": "No scan roots found.", "file_count": 0}

    home = _normalize_path(os.path.expanduser("~"))
    started = time.time()
    files: List[Dict[str, Any]] = []
    ext_counter: Counter = Counter()
    root_counter: Counter = Counter()
    errors = 0

    print(f"[*] File scan: indexing up to {max_files} files across {len(roots)} roots...")

    for root_label, root_path in roots:
        if len(files) >= max_files:
            break
        root_base = root_path
        for dirpath, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=False):
            if len(files) >= max_files:
                dirnames.clear()
                break

            rel_dir = os.path.relpath(dirpath, root_base)
            depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
            if depth > max_depth:
                dirnames.clear()
                continue

            # Prune excluded directories in-place for os.walk
            kept: List[str] = []
            for d in dirnames:
                full = os.path.join(dirpath, d)
                if _should_skip_dir(d, full, cfg):
                    continue
                kept.append(d)
            dirnames[:] = kept

            for fn in filenames:
                if len(files) >= max_files:
                    break
                if _should_skip_file(fn, cfg):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    errors += 1
                    continue

                size_mb = st.st_size / (1024 * 1024)
                if size_mb > float(cfg.get("file_scan_max_file_mb") or 200):
                    continue

                rel_from_home = os.path.relpath(full, home)
                if rel_from_home.startswith(".."):
                    rel_from_home = os.path.join(root_label, os.path.relpath(full, root_base))

                ext = os.path.splitext(fn)[1].lower() or "(no ext)"
                entry = {
                    "p": rel_from_home.replace("\\", "/"),
                    "r": root_label,
                    "n": fn,
                    "e": ext,
                    "s": st.st_size,
                    "m": int(st.st_mtime),
                }
                files.append(entry)
                ext_counter[ext] += 1
                root_counter[root_label] += 1

    elapsed = round(time.time() - started, 1)
    files.sort(key=lambda x: x.get("m") or 0, reverse=True)
    recent = [
        {"path": f["p"], "root": f["r"], "name": f["n"], "modified": f["m"]}
        for f in files[:25]
    ]
    large = sorted(files, key=lambda x: x.get("s") or 0, reverse=True)[:15]
    large_out = [
        {
            "path": f["p"],
            "size_mb": round((f.get("s") or 0) / (1024 * 1024), 2),
        }
        for f in large
    ]

    index_payload = {
        "version": 1,
        "scanned_at": time.time(),
        "scanned_at_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "home": home,
        "file_count": len(files),
        "truncated": len(files) >= max_files,
        "max_files": max_files,
        "roots": [{"label": l, "path": p} for l, p in roots],
        "files": files,
    }
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_payload, f, ensure_ascii=False)

    top_ext = ext_counter.most_common(15)
    print(
        f"[*] File scan done: {len(files)} files in {elapsed}s"
        + (" (limit reached)" if len(files) >= max_files else "")
    )

    return {
        "enabled": True,
        "file_count": len(files),
        "truncated": len(files) >= max_files,
        "scan_seconds": elapsed,
        "errors": errors,
        "index_path": index_path,
        "roots_scanned": [{"label": l, "path": p, "files": root_counter.get(l, 0)} for l, p in roots],
        "extensions_top": [{"ext": e, "count": c} for e, c in top_ext],
        "recent_files": recent,
        "large_files": large_out,
        "home": home,
    }


def search_file_index(
    query: str,
    index_path: str | None = None,
    top_k: int = 12,
) -> List[str]:
    """Substring search over indexed paths for memory injection."""
    path = index_path or DEFAULT_INDEX_PATH
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        return []

    files = data.get("files") or []
    q = (query or "").lower().strip()
    if not q:
        return []

    tokens = [t for t in q.replace("\\", "/").split() if len(t) > 2]
    scored: List[Tuple[float, str]] = []

    for item in files:
        if not isinstance(item, dict):
            continue
        p = str(item.get("p") or "")
        n = str(item.get("n") or "")
        hay = f"{p} {n}".lower()
        score = 0.0
        if q in hay:
            score += 5.0
        for t in tokens:
            if t in hay:
                score += 2.0
        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:top_k]]
