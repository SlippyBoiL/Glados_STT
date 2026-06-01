from __future__ import annotations

import os
from typing import Any, Dict, List

from facility_brain.knowledge_sync import _chunk_list, _fact, _keywords_from_names


def file_scan_to_facts(file_scan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert file scan summary into brain memory facts."""
    if not file_scan or not file_scan.get("enabled"):
        return []

    facts: List[Dict[str, Any]] = []
    count = int(file_scan.get("file_count") or 0)
    truncated = bool(file_scan.get("truncated"))
    roots = file_scan.get("roots_scanned") or []
    root_summary = ", ".join(f"{r.get('label')}: {r.get('files', 0)}" for r in roots)

    facts.append(
        _fact(
            "file_index_summary",
            f"Full user file index: {count} files indexed across {len(roots)} areas "
            f"({root_summary})."
            + (" Scan hit file limit — not every file on disk." if truncated else ""),
            ["files", "file", "folder", "documents", "desktop", "downloads", "index", "scan"],
            baseline=True,
            category="files",
        )
    )

    for ext_row in (file_scan.get("extensions_top") or [])[:8]:
        ext = ext_row.get("ext")
        c = ext_row.get("count")
        if ext:
            facts.append(
                _fact(
                    f"files_ext_{str(ext).replace('.', 'dot')}",
                    f"Operator has {c} indexed files with extension {ext}.",
                    ["files", str(ext).lstrip("."), "extension", "type"],
                    category="files",
                )
            )

    recent = file_scan.get("recent_files") or []
    if recent:
        names = [f"{r.get('path')} ({r.get('name')})" for r in recent[:12]]
        facts.append(
            _fact(
                "files_recent",
                "Recently modified files (from index): " + "; ".join(names) + ".",
                _keywords_from_names([r.get("name", "") for r in recent], ["recent", "modified", "files"]),
                category="files",
            )
        )

    large = file_scan.get("large_files") or []
    if large:
        names = [f"{x.get('path')} ({x.get('size_mb')} MB)" for x in large[:8]]
        facts.append(
            _fact(
                "files_large",
                "Largest indexed files: " + "; ".join(names) + ".",
                ["large", "big", "files", "storage"],
                category="files",
            )
        )

    # Load path batches from index for keyword search (by root)
    index_path = file_scan.get("index_path") or ""
    if index_path and os.path.isfile(index_path):
        try:
            import json

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            by_root: Dict[str, List[str]] = {}
            for item in data.get("files") or []:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("r") or "other")
                rel = str(item.get("p") or "")
                if rel:
                    by_root.setdefault(label, []).append(rel)

            max_batches = int(file_scan.get("brain_path_batches_per_root") or 6)
            paths_per_batch = int(file_scan.get("brain_paths_per_batch") or 40)
            for label, paths in by_root.items():
                for i, chunk in enumerate(_chunk_list(paths, paths_per_batch)):
                    if i >= max_batches:
                        break
                    preview = "; ".join(chunk[:paths_per_batch])
                    facts.append(
                        _fact(
                            f"files_{label}_{i}",
                            f"Indexed files under {label} (batch {i + 1}): {preview}.",
                            _keywords_from_names(
                                [os.path.basename(p) for p in chunk[:25]],
                                [label, "files", "path", "folder"],
                            ),
                            category="files",
                        )
                    )
        except Exception:
            pass

    return facts
