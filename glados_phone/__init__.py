"""GLaDOS Phone Line — Twilio bidirectional Media Streams + emergency dial."""
from __future__ import annotations

import audioop
import base64
import io
import json
import os
import threading
import wave
from typing import Any, Callable, Dict, Optional

try:
    from flask import Flask, Response, request
except ImportError:  # pragma: no cover
    Flask = None  # type: ignore
    Response = None  # type: ignore
    request = None  # type: ignore

try:
    from flask_sock import Sock
except ImportError:  # pragma: no cover
    Sock = None  # type: ignore


def _mulaw_decode(payload_b64: str) -> bytes:
    raw = base64.b64decode(payload_b64)
    return audioop.ulaw2lin(raw, 2)


def _mulaw_encode(pcm16: bytes) -> str:
    ulaw = audioop.lin2ulaw(pcm16, 2)
    return base64.b64encode(ulaw).decode("ascii")


def _resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    if src_rate == dst_rate:
        return pcm
    try:
        converted, _ = audioop.ratecv(pcm, 2, 1, src_rate, dst_rate, None)
        return converted
    except Exception:
        return pcm


class AudioPipelineBridge:
    """Whisper STT (inbound) ↔ Piper TTS (outbound) for Twilio μ-law streams."""

    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.piper_model = str(
            cfg.get("piper_model_path") or os.path.join(repo, "glados.onnx")
        )
        self.piper_wav = str(
            cfg.get("piper_output_wav") or os.path.join(repo, "phone_glados_reply.wav")
        )
        self.piper_exe = str(cfg.get("piper_exe_path") or "").strip() or "piper"
        self._whisper = None
        self._buf = bytearray()

    def _ensure_whisper(self):
        if self._whisper is not None:
            return self._whisper
        try:
            from faster_whisper import WhisperModel  # type: ignore

            model = str(self.cfg.get("whisper_model") or "tiny.en")
            compute = str(self.cfg.get("whisper_compute_type") or "int8")
            self._whisper = WhisperModel(model, device="cpu", compute_type=compute)
        except Exception as exc:
            print(f"[Phone] Whisper unavailable: {exc}")
            self._whisper = False
        return self._whisper

    def ingest_mulaw(self, payload_b64: str) -> Optional[str]:
        """Accumulate inbound Twilio media; return transcript when buffer is full."""
        pcm = _mulaw_decode(payload_b64)
        self._buf.extend(pcm)
        if len(self._buf) > 16000 * 2:  # ~2s at 8kHz
            return self.flush_stt()
        return None

    def flush_stt(self) -> Optional[str]:
        if not self._buf:
            return None
        pcm = bytes(self._buf)
        self._buf.clear()
        model = self._ensure_whisper()
        if not model:
            return None
        pcm16 = _resample_pcm16(pcm, 8000, 16000)
        try:
            import numpy as np

            audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = model.transcribe(audio, language="en")
            text = " ".join(s.text.strip() for s in segments).strip()
            return text or None
        except Exception as exc:
            print(f"[Phone] STT error: {exc}")
            return None

    def synthesize_mulaw_chunks(self, text: str, *, chunk_ms: int = 20) -> list[str]:
        """Piper TTS → PCM → μ-law base64 frames for Twilio playback."""
        import shutil
        import subprocess

        text = (text or "").strip()
        if not text:
            return []
        clean = text.replace("*", "").encode("ascii", "ignore").decode("ascii").strip()
        if not clean:
            return []

        exe = (
            self.piper_exe
            if os.path.isfile(self.piper_exe)
            else shutil.which(self.piper_exe) or shutil.which("piper")
        )
        if not exe or not os.path.isfile(self.piper_model):
            print("[Phone] Piper unavailable for outbound TTS")
            return []

        try:
            os.makedirs(os.path.dirname(self.piper_wav) or ".", exist_ok=True)
            proc = subprocess.Popen(
                [exe, "--model", self.piper_model, "--output_file", self.piper_wav],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            _out, err = proc.communicate(input=clean, timeout=90)
            if proc.returncode != 0 or not os.path.isfile(self.piper_wav):
                print(f"[Phone] Piper failed: {(err or '')[:300]}")
                return []
            with open(self.piper_wav, "rb") as f:
                wav_bytes = f.read()
        except Exception as exc:
            print(f"[Phone] Piper TTS failed: {exc}")
            return []

        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                rate = wf.getframerate()
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                frames = wf.readframes(wf.getnframes())
            if sampwidth != 2:
                frames = audioop.lin2lin(frames, sampwidth, 2)
            if channels > 1:
                frames = audioop.tomono(frames, 2, 0.5, 0.5)
            frames = _resample_pcm16(frames, rate, 8000)
        except Exception as exc:
            print(f"[Phone] WAV decode failed: {exc}")
            return []

        frame_bytes = int(8000 * (chunk_ms / 1000.0) * 2)
        chunks: list[str] = []
        for i in range(0, len(frames), frame_bytes):
            piece = frames[i : i + frame_bytes]
            if len(piece) < frame_bytes:
                piece = piece + b"\x00" * (frame_bytes - len(piece))
            chunks.append(_mulaw_encode(piece))
        return chunks


def create_phone_app(
    cfg: Dict[str, Any],
    *,
    on_utterance: Optional[Callable[[str], str]] = None,
) -> Any:
    """
    Flask app with:
      GET/POST /voice  → TwiML <Connect><Stream>
      WS     /media    → bidirectional media stream
    """
    if Flask is None or Sock is None:
        raise RuntimeError("Install flask and flask-sock for the phone line.")

    app = Flask("glados_phone")
    sock = Sock(app)
    bridge = AudioPipelineBridge(cfg)
    public_ws = (
        os.environ.get("TWILIO_PUBLIC_WS_URL")
        or cfg.get("twilio_public_ws_url")
        or "wss://localhost:5050/media"
    )

    @app.route("/voice", methods=["GET", "POST"])
    def voice():
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{public_ws}">
      <Parameter name="facility" value="aperture" />
    </Stream>
  </Connect>
</Response>"""
        return Response(twiml, mimetype="application/xml")

    @sock.route("/media")
    def media(ws):
        stream_sid = None
        print("[Phone] Media stream connected")
        try:
            while True:
                raw = ws.receive()
                if raw is None:
                    break
                data = json.loads(raw)
                event = data.get("event")
                if event == "start":
                    stream_sid = (data.get("start") or {}).get("streamSid")
                    print(f"[Phone] stream start sid={stream_sid}")
                elif event == "media":
                    payload = (data.get("media") or {}).get("payload")
                    if not payload:
                        continue
                    transcript = bridge.ingest_mulaw(payload)
                    if transcript and on_utterance:
                        reply = on_utterance(transcript) or "Acknowledged."
                        for chunk in bridge.synthesize_mulaw_chunks(reply):
                            if not stream_sid:
                                break
                            ws.send(
                                json.dumps(
                                    {
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {"payload": chunk},
                                    }
                                )
                            )
                elif event == "stop":
                    print("[Phone] stream stop")
                    break
        except Exception as exc:
            print(f"[Phone] media error: {exc}")

    return app


def start_phone_server_background(cfg: Dict[str, Any], **kwargs: Any) -> Optional[threading.Thread]:
    if not bool(cfg.get("phone_line_enabled")):
        return None

    def _run() -> None:
        try:
            app = create_phone_app(cfg, **kwargs)
            host = os.environ.get("PHONE_SERVER_HOST") or "0.0.0.0"
            port = int(os.environ.get("PHONE_SERVER_PORT") or cfg.get("phone_server_port") or 5050)
            print(f"[*] Phone line listening on {host}:{port}")
            app.run(host=host, port=port, threaded=True, use_reloader=False)
        except Exception as exc:
            print(f"[!] Phone line failed: {exc}")

    t = threading.Thread(target=_run, daemon=True, name="glados-phone")
    t.start()
    return t
