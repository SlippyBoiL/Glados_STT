"""
GLaDOS Event-Driven Daemon — replaces the blocking while True text-input loop.

Monitors CPU spikes, network drops, and Docker container crashes. On anomaly:
  - wake CrewAI / Maintenance agents
  - flash Govee lights red
  - optionally trigger emergency Twilio dial + local Z906 alarm
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore


AnomalyHandler = Callable[["Anomaly"], Awaitable[None] | None]
UserInputHandler = Callable[[str, str], Awaitable[None] | None]


@dataclass
class Anomaly:
    kind: str
    severity: str  # warn | critical
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


class SystemWatchdog:
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        self.poll_sec = float(cfg.get("watchdog_poll_sec") or 5)
        self.cpu_pct = float(cfg.get("watchdog_cpu_spike_percent") or 92)
        self.cpu_hold_sec = float(cfg.get("watchdog_cpu_spike_sec") or 20)
        self.net_drop_kbps = float(cfg.get("watchdog_network_drop_kbps") or 0.5)
        self.docker_watch = list(cfg.get("watchdog_docker_containers") or [])
        self._cpu_high_since: Optional[float] = None
        self._last_net = None
        self._last_net_ts: Optional[float] = None
        self._known_containers: set[str] = set()
        self._bootstrap_docker = True

    def sample(self) -> List[Anomaly]:
        anomalies: List[Anomaly] = []
        if psutil is None:
            return anomalies

        # CPU spike
        try:
            cpu = float(psutil.cpu_percent(interval=0.15))
            now = time.time()
            if cpu >= self.cpu_pct:
                if self._cpu_high_since is None:
                    self._cpu_high_since = now
                elif now - self._cpu_high_since >= self.cpu_hold_sec:
                    anomalies.append(
                        Anomaly(
                            "cpu_spike",
                            "warn",
                            f"CPU sustained at {cpu:.0f}% for {self.cpu_hold_sec:.0f}s",
                            {"cpu_percent": cpu},
                        )
                    )
                    self._cpu_high_since = now  # reset hold window
            else:
                self._cpu_high_since = None
        except Exception:
            pass

        # Network drop (near-zero throughput after previously healthy traffic)
        try:
            io = psutil.net_io_counters()
            now = time.time()
            if self._last_net is not None and self._last_net_ts is not None:
                dt = max(0.001, now - self._last_net_ts)
                sent_kbps = (io.bytes_sent - self._last_net.bytes_sent) / 1024.0 / dt
                recv_kbps = (io.bytes_recv - self._last_net.bytes_recv) / 1024.0 / dt
                total = sent_kbps + recv_kbps
                # Only flag drop if we previously saw meaningful traffic
                prev_total = getattr(self, "_prev_total_kbps", 10.0)
                if prev_total > 5.0 and total < self.net_drop_kbps:
                    anomalies.append(
                        Anomaly(
                            "network_drop",
                            "warn",
                            f"Network throughput collapsed to {total:.2f} kbps",
                            {"sent_kbps": sent_kbps, "recv_kbps": recv_kbps},
                        )
                    )
                self._prev_total_kbps = total
            self._last_net = io
            self._last_net_ts = now
        except Exception:
            pass

        # Docker container crashes
        try:
            running = self._docker_running_names()
            if self._bootstrap_docker:
                self._known_containers = set(running)
                self._bootstrap_docker = False
            else:
                watched = set(self.docker_watch) if self.docker_watch else set(self._known_containers)
                missing = [c for c in watched if c and c not in running]
                for name in missing:
                    anomalies.append(
                        Anomaly(
                            "docker_crash",
                            "critical",
                            f"Docker container '{name}' is not running",
                            {"container": name, "running": running},
                        )
                    )
                # Track newly seen containers
                self._known_containers |= set(running)
        except Exception:
            pass

        return anomalies

    def _docker_running_names(self) -> List[str]:
        try:
            proc = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if proc.returncode != 0:
                return []
            return [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
        except Exception:
            return []


class EventDaemon:
    """Async event loop: HUD inbox + optional terminal + system watchdog."""

    def __init__(
        self,
        cfg: Dict[str, Any],
        *,
        on_user_input: UserInputHandler,
        on_anomaly: Optional[AnomalyHandler] = None,
        pop_hud_message: Optional[Callable[[], tuple]] = None,
        pop_terminal: Optional[Callable[[], Optional[str]]] = None,
        telemetry_log: Optional[Callable[..., None]] = None,
        telemetry_path: str = "",
    ) -> None:
        self.cfg = cfg
        self.on_user_input = on_user_input
        self.on_anomaly = on_anomaly
        self.pop_hud_message = pop_hud_message
        self.pop_terminal = pop_terminal
        self.telemetry_log = telemetry_log
        self.telemetry_path = telemetry_path
        self.watchdog = SystemWatchdog(cfg)
        self._stop = asyncio.Event()
        self._busy = asyncio.Lock()
        self._last_anomaly_key: Dict[str, float] = {}
        self._cooldown_sec = 90.0

    def request_stop(self) -> None:
        self._stop.set()

    async def run_forever(self) -> None:
        print("[*] Event daemon online — awaiting HUD / voice / anomalies (no blocking text loop).")
        poll = float(self.cfg.get("watchdog_poll_sec") or 5)
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:
                print("[!] Event daemon tick error:")
                print(traceback.format_exc())
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=max(0.25, poll))
            except asyncio.TimeoutError:
                pass

    async def _tick(self) -> None:
        # 1) HUD inbox
        if self.pop_hud_message:
            try:
                msg, msg_id = self.pop_hud_message()
            except Exception:
                msg, msg_id = None, None
            if msg:
                await self._handle_user(str(msg), "hud")

        # 2) Non-blocking terminal/voice queue
        if self.pop_terminal:
            try:
                t = self.pop_terminal()
            except Exception:
                t = None
            if t:
                await self._handle_user(str(t), "terminal")

        # 3) System anomalies
        if bool(self.cfg.get("watchdog_enabled", True)):
            for anomaly in self.watchdog.sample():
                await self._emit_anomaly(anomaly)

    async def _handle_user(self, text: str, source: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        async with self._busy:
            if asyncio.iscoroutinefunction(self.on_user_input):
                await self.on_user_input(text, source)
            else:
                # Sync kernel turn off the event loop (keeps HUD inbox responsive)
                await asyncio.to_thread(self.on_user_input, text, source)

    async def _emit_anomaly(self, anomaly: Anomaly) -> None:
        key = f"{anomaly.kind}:{anomaly.message}"
        now = time.time()
        last = self._last_anomaly_key.get(key, 0)
        if now - last < self._cooldown_sec:
            return
        self._last_anomaly_key[key] = now
        print(f"[Watchdog] {anomaly.severity.upper()} {anomaly.kind}: {anomaly.message}")
        if self.telemetry_log and self.telemetry_path:
            try:
                self.telemetry_log(
                    self.telemetry_path,
                    "watchdog_anomaly",
                    {
                        "kind": anomaly.kind,
                        "severity": anomaly.severity,
                        "message": anomaly.message,
                        "detail": anomaly.detail,
                    },
                )
            except Exception:
                pass
        if self.on_anomaly:
            result = self.on_anomaly(anomaly)
            if asyncio.iscoroutine(result):
                await result


def run_daemon_sync(**kwargs: Any) -> None:
    """Blocking entry used by KernelLamma.main when input_mode=daemon."""
    daemon = EventDaemon(**kwargs)

    async def _main() -> None:
        await daemon.run_forever()

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        daemon.request_stop()
