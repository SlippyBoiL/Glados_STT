from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _plugins_dir(cfg: Dict[str, Any]) -> str:
    from glados_paths import resolve_plugins_dir

    return resolve_plugins_dir(cfg)


def telemetry_path(cfg: Dict[str, Any]) -> str:
    return os.path.join(_plugins_dir(cfg), "telemetry.jsonl")


def read_telemetry_tail(path: str, limit: int = 200) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "rb") as f:
            lines = f.readlines()
        out: List[Dict[str, Any]] = []
        for raw in lines[-max(1, limit) :]:
            try:
                s = raw.decode("utf-8", errors="ignore").strip()
                if s:
                    out.append(json.loads(s))
            except Exception:
                continue
        return out
    except Exception:
        return []


def latest_event(events: List[Dict[str, Any]], event_type: str) -> Optional[Dict[str, Any]]:
    for ev in reversed(events):
        if (ev.get("event_type") or "") == event_type:
            return ev
    return None


def load_brain_intents() -> Dict[str, List[str]]:
    path = os.path.join(REPO_ROOT, "brain_data.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(v, list)}
    except Exception:
        return {}


def computer_brain_memory_path() -> str:
    return os.path.join(REPO_ROOT, "data", "computer_brain_memory.json")


def load_computer_brain_memories() -> Dict[str, Any]:
    path = computer_brain_memory_path()
    if not os.path.isfile(path):
        return {"facts": [], "fact_count": 0, "synced_at_iso": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        facts = data.get("facts") if isinstance(data, dict) else []
        return {
            "facts": facts if isinstance(facts, list) else [],
            "fact_count": data.get("fact_count") or len(facts or []),
            "synced_at_iso": data.get("synced_at_iso"),
            "hostname": data.get("hostname"),
        }
    except Exception:
        return {"facts": [], "fact_count": 0, "synced_at_iso": None}


def load_static_memories() -> List[Dict[str, Any]]:
    path = os.path.join(REPO_ROOT, "configs", "static_memory.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        facts = data.get("facts") if isinstance(data, dict) else []
        return facts if isinstance(facts, list) else []
    except Exception:
        return []


def load_chroma_memories(cfg: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
    if not cfg.get("memory_enable_chroma"):
        return []
    try:
        import chromadb  # type: ignore
    except ImportError:
        return []
    persist = str(cfg.get("chroma_persist_dir") or os.path.join(REPO_ROOT, "chroma_db"))
    collection_name = str(cfg.get("chroma_collection") or "glados_memories")
    if not os.path.isdir(persist):
        return []
    try:
        client = chromadb.PersistentClient(path=persist)
        collection = client.get_collection(collection_name)
        result = collection.get(limit=limit, include=["documents", "metadatas"])
        docs = result.get("documents") or []
        metas = result.get("metadatas") or []
        ids = result.get("ids") or []
        out: List[Dict[str, Any]] = []
        for i, doc_id in enumerate(ids):
            out.append(
                {
                    "id": doc_id,
                    "text": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                }
            )
        return out
    except Exception:
        return []


def _skill_category(filename: str) -> str:
    stem = filename.lower().replace(".py", "").replace("skill_", "")
    if stem in ("ssh", "monitor", "github"):
        return "server"
    if stem in ("discord_message", "telegram_message", "whatsapp_message"):
        return "messaging"
    if stem in ("self_repair",):
        return "meta"
    return "general"


def load_skills(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Load from unified skills brain JSON (not plugins/skill_*.py)."""
    _ = cfg
    path = os.path.join(REPO_ROOT, "data", "glados_skills_brain.json")
    if str(cfg.get("skills_brain_path") or "").strip():
        p = str(cfg["skills_brain_path"])
        path = p if os.path.isabs(p) else os.path.join(REPO_ROOT, p)
    skills: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return skills
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        for sk in data.get("skills") or []:
            if not isinstance(sk, dict):
                continue
            sid = str(sk.get("id") or "unknown")
            skills.append(
                {
                    "file": sid,
                    "id": sid,
                    "description": str(sk.get("description") or "Learned protocol"),
                    "category": "learned",
                    "status": sk.get("status"),
                    "successes": sk.get("successes", 0),
                    "runs": sk.get("runs", 0),
                }
            )
    except Exception:
        pass
    return skills


def parse_skills_from_manifest(manifest: str) -> List[Dict[str, str]]:
    skills: List[Dict[str, str]] = []
    for line in manifest.splitlines():
        m = re.search(r"FILE:\s*'([^']+)'\s*\|\s*ACTION:\s*(.+)", line)
        if m:
            skills.append({"file": m.group(1), "description": m.group(2).strip()})
    return skills


def build_graph(cfg: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids: set = set()

    def add_node(nid: str, label: str, group: str, meta: Optional[Dict[str, Any]] = None) -> None:
        if nid in node_ids:
            return
        node_ids.add(nid)
        nodes.append({"id": nid, "label": label, "group": group, "meta": meta or {}})

    for fact in load_static_memories():
        fid = f"mem:{fact.get('id', 'unknown')}"
        add_node(fid, str(fact.get("id", "fact")), "memory", {"text": fact.get("text", "")})

    computer = load_computer_brain_memories()
    for fact in (computer.get("facts") or [])[:80]:
        if not isinstance(fact, dict):
            continue
        fid = f"computer:{fact.get('id', 'unknown')}"
        add_node(
            fid,
            str(fact.get("id", "pc"))[:32],
            "computer",
            {"text": (fact.get("text") or "")[:120], "category": fact.get("category")},
        )

    for skill in load_skills(cfg):
        sid = f"skill:{skill['file']}"
        add_node(sid, skill["file"], "skill", {"description": skill["description"]})

    for category, phrases in load_brain_intents().items():
        cid = f"intent:{category}"
        add_node(cid, category, "intent", {"count": len(phrases)})

    last_query: Optional[str] = None
    retrieved: List[str] = []
    matched_skills: List[str] = []

    for ev in events:
        et = ev.get("event_type") or ""
        payload = ev.get("payload") or {}
        if et == "heard":
            last_query = str(payload.get("text") or "")
        elif et == "memory_retrieved":
            ctx = str(payload.get("context") or "")
            for fact in load_static_memories():
                if fact.get("text", "")[:40] in ctx:
                    retrieved.append(f"mem:{fact.get('id')}")
        elif et == "skills_matched":
            for s in payload.get("skills") or []:
                if isinstance(s, dict) and s.get("file"):
                    matched_skills.append(f"skill:{s['file']}")

    if last_query:
        qid = "query:current"
        add_node(qid, "Current query", "query", {"text": last_query})
        for mid in retrieved:
            if mid in node_ids:
                edges.append({"source": qid, "target": mid, "type": "retrieved"})
        for sid in matched_skills:
            if sid in node_ids:
                edges.append({"source": qid, "target": sid, "type": "matched"})

    return {"nodes": nodes, "edges": edges}


def build_state(cfg: Dict[str, Any]) -> Dict[str, Any]:
    events = read_telemetry_tail(telemetry_path(cfg), limit=500)
    heard = latest_event(events, "heard")
    llm = latest_event(events, "llm_response")
    memory = latest_event(events, "memory_retrieved")
    subsystem = latest_event(events, "subsystem_status")
    intent = latest_event(events, "intent_classified")
    skills = latest_event(events, "skills_matched")
    executed = latest_event(events, "code_executed")
    monitor = latest_event(events, "monitor_alert")

    flags_path = os.path.join(_plugins_dir(cfg), "subsystem_flags.json")
    flags: Dict[str, Any] = {}
    if os.path.isfile(flags_path):
        try:
            with open(flags_path, "r", encoding="utf-8") as f:
                flags = json.load(f) or {}
        except Exception:
            pass

    computer = load_computer_brain_memories()
    facility_scan = latest_event(events, "facility_scan")
    file_index_meta: Dict[str, Any] = {"file_count": 0}
    fi_path = os.path.join(REPO_ROOT, "data", "facility_file_index.json")
    if os.path.isfile(fi_path):
        try:
            with open(fi_path, "r", encoding="utf-8") as f:
                fi = json.load(f) or {}
            file_index_meta = {
                "file_count": fi.get("file_count", 0),
                "synced_at_iso": fi.get("scanned_at_iso"),
                "truncated": fi.get("truncated"),
            }
        except Exception:
            pass

    return {
        "computer_brain": {
            "fact_count": computer.get("fact_count", 0),
            "synced_at_iso": computer.get("synced_at_iso"),
            "hostname": computer.get("hostname"),
            "last_scan_event": facility_scan.get("payload") if facility_scan else None,
            "file_index": file_index_meta,
        },
        "last_heard": heard.get("payload") if heard else None,
        "last_llm_response": llm.get("payload") if llm else None,
        "last_memory": memory.get("payload") if memory else None,
        "subsystem_status": subsystem.get("payload") if subsystem else None,
        "last_intent": intent.get("payload") if intent else None,
        "last_skills_matched": skills.get("payload") if skills else None,
        "last_code_executed": executed.get("payload") if executed else None,
        "last_monitor_alert": monitor.get("payload") if monitor else None,
        "subsystem_flags": flags,
        "event_count": len(events),
    }
