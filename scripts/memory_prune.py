#!/usr/bin/env python3
"""
Memory pruning — compress ChromaDB collections and rotate SQLite / JSONL event logs
so long-term memory stays lean (sub-5s response target).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load_cfg() -> Dict[str, Any]:
    from glados_config import load_config

    return load_config()


def prune_telemetry_jsonl(path: str, *, keep_lines: int = 5000) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {"ok": True, "skipped": True, "path": path}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        before = len(lines)
        if before <= keep_lines:
            return {"ok": True, "before": before, "after": before, "path": path}
        kept = lines[-keep_lines:]
        bak = path + f".bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(path, bak)
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(kept)
        return {"ok": True, "before": before, "after": len(kept), "backup": bak, "path": path}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": path}


def prune_sqlite(path: str, *, vacuum: bool = True) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {"ok": True, "skipped": True, "path": path}
    try:
        size_before = os.path.getsize(path)
        conn = sqlite3.connect(path)
        try:
            # Drop very old optional event tables if present
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [r[0] for r in cur.fetchall()]
            deleted = 0
            for table in tables:
                if table.lower() in ("events", "event_log", "telemetry", "logs"):
                    try:
                        # Keep newest ~10k rows when an id/ts column exists
                        cols = [
                            r[1]
                            for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
                        ]
                        order = "rowid"
                        for c in ("ts", "timestamp", "created_at", "id"):
                            if c in cols:
                                order = c
                                break
                        conn.execute(
                            f"DELETE FROM {table} WHERE rowid NOT IN "
                            f"(SELECT rowid FROM {table} ORDER BY {order} DESC LIMIT 10000)"
                        )
                        deleted += conn.total_changes
                    except Exception:
                        pass
            if vacuum:
                conn.execute("VACUUM")
            conn.commit()
        finally:
            conn.close()
        size_after = os.path.getsize(path)
        return {
            "ok": True,
            "path": path,
            "bytes_before": size_before,
            "bytes_after": size_after,
            "deleted_ops": deleted,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": path}


def prune_chroma(persist_dir: str, collection: str, *, max_items: int = 8000) -> Dict[str, Any]:
    if not os.path.isdir(persist_dir):
        return {"ok": True, "skipped": True, "path": persist_dir}
    try:
        import chromadb  # type: ignore
    except ImportError:
        return {"ok": False, "error": "chromadb not installed", "path": persist_dir}

    try:
        client = chromadb.PersistentClient(path=persist_dir)
        try:
            col = client.get_collection(collection)
        except Exception:
            return {"ok": True, "skipped": True, "reason": "collection missing", "path": persist_dir}

        count = col.count()
        if count <= max_items:
            return {"ok": True, "count": count, "pruned": 0, "collection": collection}

        # Fetch ids in batches; delete oldest by metadata ts when available
        batch = col.get(include=["metadatas"], limit=count)
        ids = list(batch.get("ids") or [])
        metas = list(batch.get("metadatas") or [])
        scored: List[tuple] = []
        for i, mid in enumerate(ids):
            meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
            ts = 0.0
            for key in ("ts", "timestamp", "created_at", "time"):
                if key in meta:
                    try:
                        ts = float(meta[key])
                    except Exception:
                        ts = 0.0
                    break
            scored.append((ts, mid))
        scored.sort(key=lambda x: x[0])  # oldest first
        to_delete = [mid for _, mid in scored[: max(0, count - max_items)]]
        # delete in chunks
        for i in range(0, len(to_delete), 200):
            chunk = to_delete[i : i + 200]
            col.delete(ids=chunk)
        return {
            "ok": True,
            "count_before": count,
            "pruned": len(to_delete),
            "count_after": col.count(),
            "collection": collection,
        }
    except BaseException as exc:  # noqa: BLE001 — chromadb Rust PanicException is BaseException
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "path": persist_dir,
            "hint": "Chroma store may be incompatible with this chromadb version; prune skipped.",
        }


def run_prune(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or _load_cfg()
    plugins = cfg.get("plugins_dir") or "plugins"
    home = ROOT
    telemetry = os.path.join(home, plugins, "telemetry.jsonl")
    chroma_dir = str(cfg.get("chroma_persist_dir") or os.path.join(home, "chroma_db"))
    collection = str(cfg.get("chroma_collection") or "glados_memories")
    sqlite_candidates = [
        os.path.join(chroma_dir, "chroma.sqlite3"),
        os.path.join(home, "data", "events.sqlite3"),
        os.path.join(home, "data", "event_log.sqlite3"),
    ]

    report: Dict[str, Any] = {
        "ts": time.time(),
        "telemetry": prune_telemetry_jsonl(telemetry, keep_lines=int(cfg.get("telemetry_keep_lines") or 5000)),
        "sqlite": [],
    }

    # Chroma open can Rust-panic on incompatible on-disk format — isolate each call.
    if bool(cfg.get("memory_prune_chroma", True)):
        report["chroma"] = prune_chroma(
            chroma_dir,
            collection,
            max_items=int(cfg.get("chroma_max_items") or 8000),
        )
        report["shared_brain"] = prune_chroma(
            chroma_dir,
            "glados_shared_brain",
            max_items=int(cfg.get("chroma_max_items") or 8000),
        )
    else:
        report["chroma"] = {"ok": True, "skipped": True, "reason": "memory_prune_chroma=false"}
        report["shared_brain"] = {"ok": True, "skipped": True}

    for path in sqlite_candidates:
        # Never VACUUM chroma.sqlite3 while chromadb may hold it; skip that file.
        if os.path.basename(path).lower() == "chroma.sqlite3":
            report["sqlite"].append(
                {"ok": True, "skipped": True, "path": path, "reason": "managed by chromadb"}
            )
            continue
        report["sqlite"].append(prune_sqlite(path))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="GLaDOS memory prune")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument("--loop-hours", type=float, default=0, help="If >0, prune forever on this interval")
    args = parser.parse_args()
    cfg = _load_cfg()

    def once() -> Dict[str, Any]:
        report = run_prune(cfg)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("[MemoryPrune]", json.dumps(report)[:500], "...")
        return report

    if args.loop_hours and args.loop_hours > 0:
        while True:
            once()
            time.sleep(args.loop_hours * 3600)
    else:
        once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
