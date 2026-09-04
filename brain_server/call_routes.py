"""Free remote voice/text call line — phone opens /call after ntfy ring."""
from __future__ import annotations

import os
import re
import socket
import subprocess
import tempfile
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from glados_config import load_config

router = APIRouter(tags=["call"])

_WHISPER = None
_WHISPER_FAILED = False


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def call_page_url(cfg: Optional[Dict[str, Any]] = None, *, reason: str = "operator") -> str:
    """Public/LAN URL the phone should open for a live GLaDOS session."""
    cfg = cfg or load_config()
    explicit = str(
        os.environ.get("GLADOS_CALL_URL")
        or cfg.get("call_page_url")
        or ""
    ).strip()
    if explicit:
        base = explicit.rstrip("/")
    else:
        dash = str(cfg.get("brain_dashboard_url") or "").strip().rstrip("/")
        if dash and "localhost" not in dash and "127.0.0.1" not in dash:
            base = dash
        else:
            port = int(cfg.get("brain_dashboard_port") or 8888)
            base = f"http://{_lan_ip()}:{port}"
    q = f"?reason={reason}&t={int(time.time())}"
    if base.endswith("/call"):
        return base + q
    return f"{base}/call{q}"


def _ensure_whisper(cfg: Dict[str, Any]):
    global _WHISPER, _WHISPER_FAILED
    if _WHISPER_FAILED:
        return None
    if _WHISPER is not None:
        return _WHISPER
    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = str(cfg.get("whisper_model") or "tiny.en")
        compute = str(cfg.get("whisper_compute_type") or "int8")
        _WHISPER = WhisperModel(model, device="cpu", compute_type=compute)
        return _WHISPER
    except Exception:
        _WHISPER_FAILED = True
        return None


def _transcribe_wav(path: str, cfg: Dict[str, Any]) -> str:
    model = _ensure_whisper(cfg)
    if model is None:
        return ""
    try:
        segments, _info = model.transcribe(path, language=str(cfg.get("whisper_language") or "en"))
        parts = [seg.text.strip() for seg in segments if getattr(seg, "text", None)]
        return " ".join(parts).strip()
    except Exception:
        return ""


def _piper_wav_bytes(text: str, cfg: Dict[str, Any]) -> Optional[bytes]:
    text = re.sub(r"[*`#_\[\]{}]", "", (text or "")).strip()
    text = text.encode("ascii", "ignore").decode("ascii").strip()
    if not text:
        return None
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe = str(cfg.get("piper_exe_path") or "").strip()
    if not exe or not os.path.isfile(exe):
        cand = os.path.join(repo, "venv", "Scripts", "piper.exe")
        exe = cand if os.path.isfile(cand) else "piper"
    model = str(cfg.get("piper_model_path") or os.path.join(repo, "glados.onnx"))
    if not os.path.isfile(model):
        return None
    fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        proc = subprocess.run(
            [exe, "--model", model, "--output_file", out_path],
            input=text[:500],
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
        )
        if proc.returncode != 0 or not os.path.isfile(out_path):
            return None
        with open(out_path, "rb") as f:
            return f.read()
    except Exception:
        return None
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


def _send_and_wait(text: str, *, timeout_sec: float = 90.0) -> Dict[str, Any]:
    from glados_hud.chat_bridge import enqueue_user_message, read_history

    cfg = load_config()
    msg_id = enqueue_user_message(text, cfg)
    if not msg_id:
        raise HTTPException(status_code=503, detail="Kernel inbox busy — is GLaDOS running?")

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        time.sleep(1.0)
        hist = read_history(limit=40, cfg=cfg)
        # Find our user message, then the next assistant reply after it
        seen_user = False
        for m in hist:
            if not seen_user:
                if str(m.get("id") or "") == msg_id or (
                    m.get("role") == "user" and str(m.get("text") or "").strip() == text.strip()
                ):
                    seen_user = True
                continue
            if m.get("role") == "assistant":
                reply = str(m.get("text") or "").strip()
                if reply:
                    return {
                        "ok": True,
                        "id": msg_id,
                        "user_text": text,
                        "reply": reply,
                        "call_url": call_page_url(cfg),
                    }
    return {
        "ok": False,
        "id": msg_id,
        "user_text": text,
        "reply": "No reply yet — GLaDOS may still be thinking. Stay on this page.",
        "call_url": call_page_url(cfg),
    }


class CallTurnBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@router.get("/api/call/info")
def call_info() -> Dict[str, Any]:
    cfg = load_config()
    return {
        "ok": True,
        "call_url": call_page_url(cfg),
        "lan_ip": _lan_ip(),
        "hint": "Phone and PC must be on the same Wi-Fi unless you set GLADOS_CALL_URL to a public tunnel.",
    }


@router.post("/api/call/turn")
def call_turn(body: CallTurnBody) -> Dict[str, Any]:
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty")
    return _send_and_wait(text)


@router.post("/api/call/audio")
async def call_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    cfg = load_config()
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty audio")
    suffix = ".webm"
    filename = (file.filename or "").lower()
    if filename.endswith(".wav"):
        suffix = ".wav"
    elif filename.endswith(".ogg"):
        suffix = ".ogg"
    elif filename.endswith(".mp4") or filename.endswith(".m4a"):
        suffix = ".mp4"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(raw)
        # Convert to wav via ffmpeg if needed (optional)
        wav_path = path
        if suffix != ".wav":
            wav_path = path + ".wav"
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", path, "-ar", "16000", "-ac", "1", wav_path],
                    capture_output=True,
                    timeout=30,
                )
            except Exception:
                wav_path = path
        text = _transcribe_wav(wav_path if os.path.isfile(wav_path) else path, cfg)
        if not text:
            raise HTTPException(
                status_code=400,
                detail="Could not transcribe audio (install faster-whisper; optional ffmpeg for webm).",
            )
        return _send_and_wait(text)
    finally:
        for p in (path, path + ".wav"):
            try:
                if os.path.isfile(p):
                    os.unlink(p)
            except OSError:
                pass


@router.get("/api/call/tts")
def call_tts(text: str = "") -> Response:
    cfg = load_config()
    wav = _piper_wav_bytes(text, cfg)
    if not wav:
        raise HTTPException(status_code=503, detail="Piper TTS unavailable")
    return Response(content=wav, media_type="audio/wav")


_CALL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<title>GLaDOS Call</title>
<style>
  :root { color-scheme: dark; --cyan:#00F0FF; --bg:#00050b; }
  * { box-sizing: border-box; }
  body {
    margin:0; min-height:100dvh; background:radial-gradient(1200px 600px at 50% -10%, #002633, var(--bg));
    color:#b8f4ff; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    display:flex; flex-direction:column; padding:16px; gap:12px;
  }
  h1 { font-size:14px; letter-spacing:.28em; text-transform:uppercase; color:var(--cyan); margin:0; }
  .sub { font-size:11px; opacity:.55; }
  #log {
    flex:1; overflow:auto; border:1px solid rgba(0,240,255,.2); padding:12px; border-radius:4px;
    background:rgba(0,10,20,.55); min-height:40vh;
  }
  .bubble { margin:8px 0; padding:10px 12px; border:1px solid rgba(0,240,255,.22); border-radius:4px; white-space:pre-wrap; }
  .u { margin-left:18%; border-color:rgba(16,185,129,.35); background:rgba(6,40,24,.45); }
  .a { margin-right:18%; background:rgba(0,24,32,.7); }
  .row { display:flex; gap:8px; }
  input, button {
    font:inherit; border-radius:4px; border:1px solid rgba(0,240,255,.35);
    background:#001018; color:var(--cyan); padding:14px 12px;
  }
  input { flex:1; outline:none; }
  button { cursor:pointer; text-transform:uppercase; letter-spacing:.12em; font-size:11px; }
  button:disabled { opacity:.4; }
  #mic { flex:0 0 auto; min-width:110px; background:rgba(0,240,255,.12); }
  #mic.rec { background:rgba(220,38,38,.35); border-color:#f87171; color:#fecaca; }
  #status { font-size:11px; opacity:.65; min-height:1.2em; }
</style>
</head>
<body>
  <div>
    <h1>GLaDOS Live Line</h1>
    <div class="sub">Free voice/text channel — same Wi‑Fi as the facility PC</div>
  </div>
  <div id="log"></div>
  <div id="status">Connecting…</div>
  <div class="row">
    <input id="text" placeholder="Type a command…" autocomplete="off"/>
    <button id="send" type="button">Send</button>
  </div>
  <div class="row">
    <button id="mic" type="button">Hold mic</button>
    <button id="end" type="button">End</button>
  </div>
<script>
const logEl = document.getElementById('log');
const statusEl = document.getElementById('status');
const textEl = document.getElementById('text');
const sendBtn = document.getElementById('send');
const micBtn = document.getElementById('mic');
let busy = false;
let mediaRecorder = null;
let chunks = [];

function addBubble(role, text) {
  const d = document.createElement('div');
  d.className = 'bubble ' + (role === 'user' ? 'u' : 'a');
  d.textContent = (role === 'user' ? 'YOU: ' : 'GLaDOS: ') + text;
  logEl.appendChild(d);
  logEl.scrollTop = logEl.scrollHeight;
}

async function playTts(text) {
  try {
    const url = '/api/call/tts?text=' + encodeURIComponent(text.slice(0, 450));
    const audio = new Audio(url);
    await audio.play();
  } catch (e) { /* ignore autoplay blocks after user gesture */ }
}

async function turn(text) {
  if (!text || busy) return;
  busy = true;
  sendBtn.disabled = true;
  statusEl.textContent = 'GLaDOS is thinking…';
  addBubble('user', text);
  try {
    const res = await fetch('/api/call/turn', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    const data = await res.json();
    const reply = (data.reply || data.detail || 'No reply').toString();
    addBubble('assistant', reply);
    statusEl.textContent = data.ok ? 'Listening.' : 'Waiting…';
    await playTts(reply);
  } catch (e) {
    statusEl.textContent = 'Line error: ' + e;
  } finally {
    busy = false;
    sendBtn.disabled = false;
  }
}

sendBtn.onclick = () => {
  const t = textEl.value.trim();
  textEl.value = '';
  turn(t);
};
textEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); sendBtn.click(); }
});
document.getElementById('end').onclick = () => {
  statusEl.textContent = 'Call ended.';
  addBubble('assistant', 'Line closed. You may close this tab.');
};

async function startMic() {
  if (busy) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
      if (blob.size < 800) { statusEl.textContent = 'Too short — hold longer.'; return; }
      busy = true; statusEl.textContent = 'Transcribing…';
      const fd = new FormData();
      fd.append('file', blob, 'utterance.webm');
      try {
        const res = await fetch('/api/call/audio', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'audio failed');
        addBubble('user', data.user_text || '(voice)');
        addBubble('assistant', data.reply || '');
        statusEl.textContent = 'Listening.';
        await playTts(data.reply || '');
      } catch (e) {
        statusEl.textContent = String(e.message || e);
        addBubble('assistant', 'Voice path failed — type instead. ' + (e.message || e));
      } finally { busy = false; }
    };
    mediaRecorder.start();
    micBtn.classList.add('rec');
    micBtn.textContent = 'Release';
    statusEl.textContent = 'Recording…';
  } catch (e) {
    statusEl.textContent = 'Mic blocked — use text.';
  }
}
function stopMic() {
  if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
  micBtn.classList.remove('rec');
  micBtn.textContent = 'Hold mic';
}
micBtn.addEventListener('pointerdown', (e) => { e.preventDefault(); startMic(); });
micBtn.addEventListener('pointerup', (e) => { e.preventDefault(); stopMic(); });
micBtn.addEventListener('pointerleave', () => stopMic());

(async function boot() {
  const params = new URLSearchParams(location.search);
  const reason = params.get('reason') || 'operator';
  statusEl.textContent = 'Line open.';
  const greeting = reason === 'emergency'
    ? 'Emergency line open. Report the facility status or give me a directive.'
    : 'Live line open. Speak or type a command.';
  addBubble('assistant', greeting);
  try { await playTts(greeting); } catch (_) {}
})();
</script>
</body>
</html>
"""


@router.get("/call", response_class=HTMLResponse)
def call_page() -> HTMLResponse:
    return HTMLResponse(_CALL_HTML)


@router.websocket("/api/phone/inkbox")
@router.websocket("/phone/media/ws")
async def inkbox_phone_media(websocket: WebSocket) -> None:
    from glados_phone.inkbox_media import inkbox_call_websocket

    await inkbox_call_websocket(websocket)
