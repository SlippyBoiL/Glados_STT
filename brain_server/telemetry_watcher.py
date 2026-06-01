from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any, Dict, List, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class TelemetryBroadcaster:
    """Tails telemetry.jsonl and pushes new events to WebSocket clients."""

    def __init__(self, telemetry_path: str) -> None:
        self.telemetry_path = telemetry_path
        self._clients: Set[Any] = set()
        self._lock = threading.Lock()
        self._file_pos = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._observer: Observer | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._init_file_pos()

    def _init_file_pos(self) -> None:
        if os.path.isfile(self.telemetry_path):
            self._file_pos = os.path.getsize(self.telemetry_path)

    def register(self, ws: Any) -> None:
        with self._lock:
            self._clients.add(ws)

    def unregister(self, ws: Any) -> None:
        with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, event: Dict[str, Any]) -> None:
        dead = []
        with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        if dead:
            with self._lock:
                for ws in dead:
                    self._clients.discard(ws)

    def _read_new_lines(self) -> List[Dict[str, Any]]:
        if not os.path.isfile(self.telemetry_path):
            return []
        events: List[Dict[str, Any]] = []
        try:
            size = os.path.getsize(self.telemetry_path)
            if size < self._file_pos:
                self._file_pos = 0
            with open(self.telemetry_path, "r", encoding="utf-8") as f:
                f.seek(self._file_pos)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                self._file_pos = f.tell()
        except Exception:
            pass
        return events

    def _on_file_change(self) -> None:
        events = self._read_new_lines()
        if not events or self._loop is None:
            return
        for ev in events:
            asyncio.run_coroutine_threadsafe(self.broadcast(ev), self._loop)

    def start_watcher(self) -> None:
        directory = os.path.dirname(self.telemetry_path) or "."
        os.makedirs(directory, exist_ok=True)

        handler = _TelemetryHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, directory, recursive=False)
        self._observer.daemon = True
        self._observer.start()


class _TelemetryHandler(FileSystemEventHandler):
    def __init__(self, broadcaster: TelemetryBroadcaster) -> None:
        self._broadcaster = broadcaster

    def on_modified(self, event: Any) -> None:
        if event.is_directory:
            return
        if os.path.basename(event.src_path) == os.path.basename(self._broadcaster.telemetry_path):
            self._broadcaster._on_file_change()

    def on_created(self, event: Any) -> None:
        self.on_modified(event)
