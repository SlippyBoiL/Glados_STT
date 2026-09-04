from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from brain_server.data import telemetry_path
from glados_config import load_config
from glados_hud.chat_bridge import enqueue_user_message, read_history

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _telemetry_log(cfg, event_type: str, payload: dict) -> None:
    try:
        from plugins.telemetry import telemetry_log
    except ImportError:
        try:
            from telemetry import telemetry_log  # type: ignore
        except ImportError:
            return
    telemetry_log(telemetry_path(cfg), event_type, payload)


class ChatSendBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@router.post("/send")
def chat_send(body: ChatSendBody) -> Dict[str, Any]:
    return _dispatch_user_prompt(body.text, source="hud")


@router.post("/prompt")
def user_text_prompt(body: ChatSendBody) -> Dict[str, Any]:
    """Manual override bar — typed command to Swarm Manager (no STT)."""
    return _dispatch_user_prompt(body.text, source="hud_manual")


def _dispatch_user_prompt(text: str, *, source: str) -> Dict[str, Any]:
    cfg = load_config()
    text = (text or "").strip()
    msg_id = enqueue_user_message(text, cfg)
    if not msg_id:
        raise HTTPException(
            status_code=503,
            detail="Kernel inbox busy — GLaDOS may still be starting. Retry in a few seconds.",
        )
    _telemetry_log(
        cfg,
        "user_text_prompt",
        {
            "text": text,
            "source": source,
            "agent_id": "MANAGER",
            "id": msg_id,
        },
    )
    _telemetry_log(
        cfg,
        "swarm_telemetry",
        {
            "agent_id": "MANAGER",
            "status": "idle",
            "message": text,
            "current_subtask": "Standing by",
            "source": source,
        },
    )
    _telemetry_log(
        cfg,
        "hud_chat",
        {"role": "user", "text": text, "source": source, "id": msg_id, "pending": True},
    )
    return {"ok": True, "id": msg_id}


@router.get("/history")
def chat_history(limit: int = 150) -> Dict[str, Any]:
    cfg = load_config()
    from glados_paths import resolve_plugins_dir
    from glados_hud.chat_bridge import history_path, read_session

    session = read_session(cfg)
    messages = read_history(limit=limit, cfg=cfg)
    session_ts = float(session.get("session_started_at") or 0)
    if session_ts > 0:
        messages = [m for m in messages if float(m.get("ts") or 0) >= session_ts - 0.001]
    return {
        "messages": messages,
        "count": len(messages),
        "session": session,
        "session_started_at": session_ts or None,
        "history_path": history_path(cfg),
        "plugins_dir": resolve_plugins_dir(cfg),
    }
