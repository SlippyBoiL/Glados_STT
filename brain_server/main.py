from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from glados_config import load_config  # noqa: E402

from brain_server.data import (  # noqa: E402
    build_graph,
    build_state,
    load_brain_intents,
    load_chroma_memories,
    load_computer_brain_memories,
    load_skills,
    load_static_memories,
    read_telemetry_tail,
    telemetry_path,
)
from brain_server.chat_routes import router as chat_router  # noqa: E402
from brain_server.system_metrics import get_system_metrics  # noqa: E402
from brain_server.telemetry_watcher import TelemetryBroadcaster  # noqa: E402

STATIC_DIR = os.path.join(REPO_ROOT, "brain_web", "out")
_broadcaster: Optional[TelemetryBroadcaster] = None


def _get_cfg() -> Dict[str, Any]:
    return load_config()


def _auth_token(cfg: Dict[str, Any]) -> str:
    env = os.environ.get("BRAIN_DASHBOARD_TOKEN", "").strip()
    if env:
        return env
    return str(cfg.get("brain_dashboard_token") or "").strip()


def _verify_token(
    cfg: Dict[str, Any] = Depends(_get_cfg),
    authorization: Optional[str] = Header(None),
) -> None:
    token = _auth_token(cfg)
    if not token:
        return
    if not authorization or authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _broadcaster
    cfg = load_config()
    path = telemetry_path(cfg)
    _broadcaster = TelemetryBroadcaster(path)
    _broadcaster.set_loop(asyncio.get_running_loop())
    _broadcaster.start_watcher()

    async def _metrics_loop() -> None:
        """Broadcast host metrics as system_metrics telemetry events."""
        try:
            from plugins.telemetry import system_metrics_log  # type: ignore
        except Exception:
            try:
                from telemetry import system_metrics_log  # type: ignore
            except Exception:
                return

        while True:
            try:
                metrics = get_system_metrics()
                system_metrics_log(path, metrics)
            except Exception:
                pass
            await asyncio.sleep(3.0)

    metrics_task = asyncio.create_task(_metrics_loop())
    yield
    metrics_task.cancel()


app = FastAPI(title="Glados Brain Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, dependencies=[Depends(_verify_token)])


@app.get("/api/health")
def health(_: None = Depends(_verify_token)) -> Dict[str, str]:
    return {"status": "ok", "service": "glados-brain"}


@app.get("/api/telemetry/recent")
def telemetry_recent(
    limit: int = Query(200, ge=1, le=2000),
    cfg: Dict[str, Any] = Depends(_get_cfg),
    _: None = Depends(_verify_token),
) -> Dict[str, Any]:
    events = read_telemetry_tail(telemetry_path(cfg), limit=limit)
    return {"events": events, "count": len(events)}


@app.get("/api/brain/intents")
def brain_intents(_: None = Depends(_verify_token)) -> Dict[str, Any]:
    intents = load_brain_intents()
    clusters = [
        {"category": cat, "phrases": phrases, "count": len(phrases)}
        for cat, phrases in intents.items()
    ]
    return {"clusters": clusters}


@app.get("/api/brain/memories")
def brain_memories(
    cfg: Dict[str, Any] = Depends(_get_cfg),
    _: None = Depends(_verify_token),
) -> Dict[str, Any]:
    static = load_static_memories()
    chroma = load_chroma_memories(cfg)
    computer = load_computer_brain_memories()
    return {
        "static": static,
        "chroma": chroma,
        "chroma_enabled": bool(cfg.get("memory_enable_chroma")),
        "computer": computer.get("facts") or [],
        "computer_meta": {
            "fact_count": computer.get("fact_count", 0),
            "synced_at_iso": computer.get("synced_at_iso"),
            "hostname": computer.get("hostname"),
        },
    }


@app.get("/api/brain/computer")
def brain_computer(_: None = Depends(_verify_token)) -> Dict[str, Any]:
    return load_computer_brain_memories()


@app.get("/api/brain/skills")
def brain_skills(
    cfg: Dict[str, Any] = Depends(_get_cfg),
    _: None = Depends(_verify_token),
) -> Dict[str, Any]:
    skills = load_skills(cfg)
    return {"skills": skills, "count": len(skills)}


@app.get("/api/brain/state")
def brain_state(
    cfg: Dict[str, Any] = Depends(_get_cfg),
    _: None = Depends(_verify_token),
) -> Dict[str, Any]:
    return build_state(cfg)


@app.get("/api/system/metrics")
def system_metrics(_: None = Depends(_verify_token)) -> Dict[str, Any]:
    return get_system_metrics()


@app.get("/api/brain/graph")
def brain_graph(
    cfg: Dict[str, Any] = Depends(_get_cfg),
    _: None = Depends(_verify_token),
) -> Dict[str, Any]:
    events = read_telemetry_tail(telemetry_path(cfg), limit=500)
    return build_graph(cfg, events)


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    cfg = load_config()
    token = _auth_token(cfg)
    if token:
        auth = websocket.headers.get("authorization") or websocket.query_params.get("token")
        expected = f"Bearer {token}" if auth and auth.startswith("Bearer") else token
        if auth not in (expected, token, f"Bearer {token}"):
            await websocket.close(code=4401)
            return

    await websocket.accept()
    if _broadcaster is None:
        await websocket.close()
        return

    _broadcaster.register(websocket)
    try:
        events = read_telemetry_tail(telemetry_path(cfg), limit=200)
        for ev in events:
            await websocket.send_json(ev)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _broadcaster.unregister(websocket)


# Static frontend (after `npm run build` in brain_web/)
if os.path.isdir(STATIC_DIR):

    @app.get("/")
    async def index():
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404)

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:

    @app.get("/")
    def index_placeholder() -> Dict[str, str]:
        return {
            "message": "Glados Brain API is running. Build the UI: cd brain_web && npm install && npm run build",
            "docs": "/docs",
        }


def run_server() -> None:
    import uvicorn

    cfg = load_config()
    host = str(cfg.get("brain_dashboard_host") or "0.0.0.0")
    port = int(cfg.get("brain_dashboard_port") or 8080)
    uvicorn.run("brain_server.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_server()
