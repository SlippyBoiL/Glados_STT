from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
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
    cfg = load_config()
    text = body.text.strip()
    msg_id = enqueue_user_message(text, cfg)
    if not msg_id:
        return {"ok": False, "error": "empty message"}
    _telemetry_log(
        cfg,
        "hud_chat",
        {"role": "user", "text": text, "source": "hud", "id": msg_id, "pending": True},
    )
    return {"ok": True, "id": msg_id}


@router.get("/history")
def chat_history(limit: int = 150) -> Dict[str, Any]:
    cfg = load_config()
    from glados_paths import resolve_plugins_dir

    messages = read_history(limit=limit, cfg=cfg)
    return {
        "messages": messages,
        "count": len(messages),
        "history_path": __import__("glados_hud.chat_bridge", fromlist=["history_path"]).history_path(cfg),
        "plugins_dir": resolve_plugins_dir(cfg),
    }
