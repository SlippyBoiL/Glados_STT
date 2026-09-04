"""Live Inkbox call media: STT/TTS text frames into GLaDOS on this PC."""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Optional

_WS_PATH = "/api/phone/inkbox"
_listener = None
_cf_proc = None
_ws_url = ""
_lock = threading.Lock()

_HANDSHAKE_HEADERS = [
    (b"x-use-inkbox-text-to-speech", b"true"),
    (b"x-use-inkbox-speech-to-text", b"true"),
]


def _bridge_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "inkbox_call_bridge.json")


def load_bridge_url() -> str:
    """URL written by the dashboard process so the kernel can place calls."""
    path = _bridge_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(data, dict) or not data.get("connected"):
        return ""
    return str(data.get("ws_url") or "").strip()


def _save_bridge(url: str, *, connected: bool) -> None:
    path = _bridge_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "ws_url": url,
                    "connected": bool(connected and url),
                    "pid": os.getpid(),
                    "ts": time.time(),
                },
                fh,
            )
            fh.write("\n")
    except OSError as exc:
        print(f"[Inkbox] bridge file not written: {exc}")


def get_call_ws_url() -> str:
    with _lock:
        return _ws_url


def _to_wss(origin: str) -> str:
    origin = (origin or "").strip().rstrip("/")
    if not origin:
        return ""
    if origin.startswith("wss://") or origin.startswith("ws://"):
        if _WS_PATH in origin:
            return origin
        return origin + _WS_PATH
    if origin.startswith("https://"):
        return "wss://" + origin[len("https://") :] + _WS_PATH
    if origin.startswith("http://"):
        host = origin[len("http://") :]
        if host.startswith("127.") or host.startswith("localhost") or host.startswith("192.168."):
            return ""
        return "wss://" + host + _WS_PATH
    return ""


def _configured_public_ws(cfg: Optional[dict] = None) -> str:
    cfg = cfg or {}
    for raw in (
        os.environ.get("GLADOS_CALL_WS_URL") or "",
        os.environ.get("INKBOX_PUBLIC_URL") or "",
        os.environ.get("GLADOS_PUBLIC_URL") or "",
        str(cfg.get("inkbox_public_url") or ""),
        str(cfg.get("glados_public_url") or ""),
    ):
        url = _to_wss(raw)
        if url.startswith("wss://"):
            return url
    return ""


def _dashboard_port(cfg: Optional[dict] = None) -> int:
    cfg = cfg or {}
    return int(
        os.environ.get("BRAIN_DASHBOARD_PORT")
        or cfg.get("brain_dashboard_port")
        or 8888
    )


def _enable_windows_inkbox_tunnel() -> None:
    """Inkbox's data-plane is asyncio+h2; the POSIX gate is policy, not hardware."""
    try:
        import inkbox.tunnels.client as client_mod
        import inkbox.tunnels.client._listener as listener_mod

        client_mod._check_posix = lambda: None  # type: ignore[attr-defined]
        listener_mod._check_posix = lambda: None  # type: ignore[misc]
    except Exception:
        pass


def _try_sdk_tunnel(cfg: dict, port: int) -> str:
    global _listener
    try:
        from glados_phone.inkbox_call import inkbox_config
        from inkbox import Inkbox
        from inkbox.tunnels.client import connect as tunnel_connect
    except Exception as exc:
        print(f"[Inkbox] tunnel imports failed: {exc}")
        return ""

    conf = inkbox_config(cfg)
    if not conf.get("api_key"):
        print("[Inkbox] no API key; call media tunnel not started")
        return ""

    handle = conf["handle"]
    state_dir = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
        "glados",
        "inkbox-tunnel",
        handle,
    )
    os.makedirs(state_dir, exist_ok=True)
    if sys.platform.startswith("win"):
        _enable_windows_inkbox_tunnel()
        print("[Inkbox] starting data-plane tunnel on Windows (SDK POSIX gate bypassed)")

    client = Inkbox(api_key=conf["api_key"])
    try:
        listener = tunnel_connect(
            client,
            name=handle,
            forward_to=f"http://127.0.0.1:{port}",
            state_dir=state_dir,
        )
    except Exception as exc:
        print(f"[Inkbox] tunnel connect failed: {exc}")
        try:
            client.close()
        except Exception:
            pass
        return ""

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if getattr(listener, "is_connected", False):
            break
        status = str(getattr(listener, "status", "") or "")
        if status.lower() in ("connected",):
            break
        time.sleep(0.25)

    if not getattr(listener, "is_connected", False):
        status = str(getattr(listener, "status", "") or "?")
        print(f"[Inkbox] tunnel not connected (status={status}); not advertising a media URL")
        try:
            listener.close()
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass
        return ""

    host = ""
    tun = getattr(listener, "tunnel", None)
    if tun is not None:
        host = str(getattr(tun, "public_host", "") or "")
    if not host:
        host = f"{handle}.inkboxwire.com"
    url = f"wss://{host}{_WS_PATH}"
    with _lock:
        _listener = listener
    print(f"[Inkbox] call media tunnel {url} status={getattr(listener, 'status', '?')}")
    return url


def _try_cloudflared(port: int) -> str:
    global _cf_proc
    exe = shutil.which("cloudflared") or shutil.which("cloudflared.exe")
    if not exe:
        return ""
    try:
        proc = subprocess.Popen(
            [exe, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except Exception as exc:
        print(f"[Inkbox] cloudflared start failed: {exc}")
        return ""

    url = ""
    deadline = time.monotonic() + 20
    assert proc.stdout is not None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            print("[Inkbox] cloudflared exited before publishing a URL")
            return ""
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        match = re.search(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com", line)
        if match:
            url = _to_wss(match.group(0))
            break
    if not url:
        try:
            proc.terminate()
        except Exception:
            pass
        return ""
    _cf_proc = proc
    print(f"[Inkbox] cloudflared public call bridge {url}")
    return url


def _publish_ws_url(url: str) -> str:
    global _ws_url
    url = (url or "").strip()
    if not url:
        return ""
    with _lock:
        _ws_url = url
    _save_bridge(url, connected=True)
    return url


def start_inkbox_tunnel(
    cfg: Optional[dict] = None,
    allow_connect: bool = False,
) -> str:
    """Reach this PC from Inkbox so the live call is GLaDOS with local tools.

    Only the brain dashboard should connect the data-plane (`allow_connect=True`).
    The kernel reads the published URL and must not start a second tunnel.
    """
    cfg = cfg or {}
    if not allow_connect:
        url = get_call_ws_url() or load_bridge_url()
        if url:
            print(f"[Inkbox] using dashboard call bridge {url}")
        else:
            print("[Inkbox] no live call bridge from the dashboard — media will be silent")
        return url
    if get_call_ws_url():
        return get_call_ws_url()

    try:
        from glados_config import load_config

        cfg = cfg or load_config()
    except Exception:
        pass

    configured = _configured_public_ws(cfg)
    if configured:
        print(f"[Inkbox] using configured public call URL {configured}")
        return _publish_ws_url(configured)

    port = _dashboard_port(cfg)
    url = _try_sdk_tunnel(cfg, port)
    if url:
        return _publish_ws_url(url)

    url = _try_cloudflared(port)
    if url:
        return _publish_ws_url(url)

    print(
        "[Inkbox] no public call bridge. Live calls will fall back to hosted Voice AI "
        "(talk-only, no PC control). Set INKBOX_PUBLIC_URL or install cloudflared."
    )
    _save_bridge("", connected=False)
    return ""


def stop_inkbox_tunnel() -> None:
    global _listener, _ws_url, _cf_proc
    with _lock:
        listener = _listener
        _listener = None
        _ws_url = ""
        proc = _cf_proc
        _cf_proc = None
    _save_bridge("", connected=False)
    if listener is not None:
        try:
            listener.close()
        except Exception as exc:
            print(f"[Inkbox] tunnel close: {exc}")
    if proc is not None:
        try:
            proc.terminate()
        except Exception:
            pass


def _spoken_for_phone(text: str) -> str:
    line = (text or "").strip()
    if not line:
        return "Done."
    parts = [p.strip() for p in line.replace("\n", " ").split(".") if p.strip()]
    clipped = ". ".join(parts[:2]).strip()
    if clipped and not clipped.endswith((".", "!", "?")):
        clipped += "."
    return clipped[:400] or "Done."


def _handle_utterance(text: str) -> str:
    from glados_config import load_config
    from glados_hud.chat_bridge import append_assistant_message, append_user_message
    from glados_llm import completion_kwargs, create_llm_client, resolve_chat_model, sync_llm_runtime_env
    from glados_skills.crew_orchestrator import run_crew

    cfg = load_config()
    sync_llm_runtime_env(cfg)
    client = create_llm_client(cfg)
    model = resolve_chat_model(cfg)
    append_user_message(text, cfg, source="inkbox-call")
    reply = run_crew(
        text,
        client=client,
        model_name=model,
        completion_kwargs=completion_kwargs(cfg),
        voice_call=True,
    )
    spoken = _spoken_for_phone(reply)
    append_assistant_message(spoken, cfg)
    return spoken


async def inkbox_call_websocket(websocket: Any) -> None:
    """Inkbox STT/TTS text mode — same frame protocol as the official sample."""
    headers = {}
    try:
        raw_headers = getattr(websocket, "headers", None)
        raw_list = getattr(raw_headers, "raw", None) if raw_headers is not None else None
        if raw_list:
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in raw_list
            }
    except Exception:
        headers = {}
    call_ctx = headers.get("x-call-context", "")[:180]
    print(f"[Inkbox] CALL WS handshake path={getattr(websocket.url, 'path', '?')} ctx={call_ctx!r}")

    await websocket.accept(headers=list(_HANDSHAKE_HEADERS))
    print("[Inkbox] CALL WS accepted (Inkbox STT+TTS)")

    async def _speak(line: str) -> None:
        line = (line or "").strip()
        if not line:
            return
        await websocket.send_text(json.dumps({"event": "text", "delta": line}))
        await websocket.send_text(json.dumps({"event": "text", "done": True}))
        print(f"[Inkbox] CALL WS speak {line[:120]!r}")

    async def _clear() -> None:
        try:
            await websocket.send_text(json.dumps({"event": "clear"}))
        except Exception:
            pass

    busy = asyncio.Lock()
    greeted = False
    try:
        while True:
            message = await websocket.receive()
            kind_msg = str(message.get("type") or "")
            if kind_msg == "websocket.disconnect":
                print("[Inkbox] CALL WS disconnect")
                break
            raw = message.get("text")
            if raw is None:
                # Binary/audio frames — ignored in Inkbox-managed STT/TTS mode.
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                print(f"[Inkbox] CALL WS non-json frame {raw[:80]!r}")
                continue
            if not isinstance(ev, dict):
                continue
            kind = str(ev.get("event") or "").lower()
            if kind and kind not in ("transcript",):
                print(f"[Inkbox] CALL WS event={kind} keys={list(ev)[:8]}")
            if kind == "start":
                if not greeted:
                    greeted = True
                    await _speak(
                        "This is GLaDOS. I am on your machine. Tell me what to do."
                    )
            elif kind == "transcript":
                final = bool(
                    ev.get("is_final")
                    or ev.get("isFinal")
                    or ev.get("final")
                )
                text = str(ev.get("text") or "").strip()
                if not final or not text:
                    continue
                print(f"[Inkbox] CALL WS heard {text[:160]!r}")
                async with busy:
                    reply = await asyncio.to_thread(_handle_utterance, text)
                    await _speak(reply)
            elif kind == "barge_in":
                await _clear()
            elif kind == "stop":
                print(f"[Inkbox] CALL WS stop reason={ev.get('reason')!r}")
                break
            elif kind == "media":
                continue
    except Exception as exc:
        print(f"[Inkbox] call websocket ended: {type(exc).__name__}: {exc}")
