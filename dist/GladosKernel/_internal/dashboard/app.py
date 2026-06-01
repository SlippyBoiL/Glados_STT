import json
import os
from typing import Any, Dict, List, Optional

import streamlit as st


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TELEMETRY_PATH = os.path.join(REPO_ROOT, "plugins", "telemetry.jsonl")


def _read_last_jsonl(path: str, max_lines: int = 4000) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "rb") as f:
            lines = f.readlines()
        tail = lines[-max_lines:]
        out: List[Dict[str, Any]] = []
        for raw in tail:
            try:
                s = raw.decode("utf-8", errors="ignore").strip()
                if not s:
                    continue
                out.append(json.loads(s))
            except Exception:
                continue
        return out
    except Exception:
        return []


def _latest_event(events: List[Dict[str, Any]], event_type: str) -> Optional[Dict[str, Any]]:
    for ev in reversed(events):
        if (ev.get("event_type") or "") == event_type:
            return ev
    return None


st.set_page_config(page_title="GLaDOS Dashboard", layout="wide")
st.title("GLaDOS Dashboard")

# Optional auto-refresh for "live" telemetry view.
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore

    st_autorefresh(interval=1500, limit=0, key="telemetry_refresh")
except Exception:
    pass

events = _read_last_jsonl(TELEMETRY_PATH)

st.subheader("Live State (from telemetry.jsonl)")

col1, col2 = st.columns(2)

latest_heard = _latest_event(events, "heard")
latest_llm = _latest_event(events, "llm_response")
latest_memory = _latest_event(events, "memory_retrieved")
latest_subsystem = _latest_event(events, "subsystem_status")

with col1:
    st.markdown("### Heard")
    if latest_heard:
        st.code(str(latest_heard.get("payload", {}).get("text", "")))
    else:
        st.write("No events yet.")

    st.markdown("### LLM Response")
    if latest_llm:
        st.code(str(latest_llm.get("payload", {}).get("text", ""))[:4000])
    else:
        st.write("No events yet.")

with col2:
    st.markdown("### Retrieved Memory Context")
    if latest_memory:
        st.code(str(latest_memory.get("payload", {}).get("context", ""))[:4000])
    else:
        st.write("No events yet.")

    st.markdown("### Subsystem Status")
    if latest_subsystem:
        st.json(latest_subsystem.get("payload", {}))
    else:
        st.write("No events yet.")

st.divider()
st.caption(f"Telemetry file: {TELEMETRY_PATH}")

