"""Emergency outbound dialing + local Z906 alarm failover."""
from __future__ import annotations

import html
import os
import threading
import time
from typing import Any, Callable, Dict, Optional


def _twilio_creds(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    cfg = cfg or {}
    return {
        "sid": str(os.environ.get("TWILIO_ACCOUNT_SID") or cfg.get("twilio_account_sid") or "").strip(),
        "token": str(os.environ.get("TWILIO_AUTH_TOKEN") or cfg.get("twilio_auth_token") or "").strip(),
        "from_num": str(os.environ.get("TWILIO_FROM_NUMBER") or cfg.get("twilio_from_number") or "").strip(),
        "to_num": str(os.environ.get("TWILIO_TO_NUMBER") or cfg.get("twilio_to_number") or "").strip(),
        "voice_url": str(os.environ.get("TWILIO_VOICE_URL") or cfg.get("twilio_voice_url") or "").strip(),
        "public": str(
            os.environ.get("TWILIO_PUBLIC_WS_URL") or cfg.get("twilio_public_ws_url") or ""
        ).strip(),
    }


def dial_operator(
    cfg: Optional[Dict[str, Any]] = None,
    *,
    message: str = "",
    wait_for_answer: bool = True,
) -> Dict[str, Any]:
    """
    Place a real outbound PSTN call to TWILIO_TO_NUMBER via Twilio.

    Prefers inline TwiML (no public webhook required). Falls back to voice_url /
    derived TWILIO_PUBLIC_WS_URL host when provided.
    """
    cfg = cfg or {}
    creds = _twilio_creds(cfg)
    sid, token, from_num, to_num = (
        creds["sid"],
        creds["token"],
        creds["from_num"],
        creds["to_num"],
    )
    voice_url = creds["voice_url"]
    if not voice_url and creds["public"]:
        voice_url = creds["public"].replace("wss://", "https://").replace("/media", "/voice")

    missing = [
        name
        for name, val in (
            ("TWILIO_ACCOUNT_SID", sid),
            ("TWILIO_AUTH_TOKEN", token),
            ("TWILIO_FROM_NUMBER", from_num),
            ("TWILIO_TO_NUMBER", to_num),
        )
        if not val
    ]
    if missing:
        return {
            "ok": False,
            "detail": (
                "Twilio not configured — set in .env: "
                + ", ".join(missing)
                + ". TO number alone is not enough; you need a Twilio Account SID, Auth Token, "
                "and a Twilio phone number (FROM) that can place calls."
            ),
            "answered": False,
            "to": to_num or None,
        }

    say = (message or "").strip() or (
        "This is GLaDOS. Your operator requested this call from the facility. "
        "I am online and awaiting directives."
    )
    # Keep TwiML short — Twilio Say has practical length limits.
    say = say[:450]
    twiml = (
        "<Response>"
        f"<Say voice='alice'>{html.escape(say)}</Say>"
        "<Pause length='1'/>"
        "<Say voice='alice'>End of transmission.</Say>"
        "</Response>"
    )

    try:
        from twilio.rest import Client  # type: ignore

        client = Client(sid, token)
        create_kwargs: Dict[str, Any] = {
            "to": to_num,
            "from_": from_num,
            "timeout": 30,
        }
        # Inline TwiML works without a public tunnel — preferred for "call me".
        if voice_url:
            create_kwargs["url"] = voice_url
        else:
            create_kwargs["twiml"] = twiml

        call = client.calls.create(**create_kwargs)
        status = str(getattr(call, "status", "") or "queued")
        answered = False
        if wait_for_answer:
            for _ in range(15):
                time.sleep(2)
                fresh = client.calls(call.sid).fetch()
                status = str(fresh.status or "")
                if status in ("in-progress", "answered"):
                    answered = True
                    break
                if status in ("busy", "failed", "no-answer", "canceled", "completed"):
                    break
        return {
            "ok": True,
            "detail": f"call sid={call.sid} status={status} to={to_num}",
            "answered": answered,
            "sid": call.sid,
            "status": status,
            "to": to_num,
            "message": say,
        }
    except Exception as exc:
        return {"ok": False, "detail": str(exc), "answered": False, "to": to_num}


def blast_z906_alarm(
    cfg: Optional[Dict[str, Any]] = None,
    *,
    duration_sec: float = 8.0,
    frequency_hz: float = 880.0,
) -> str:
    """
    Localized failover alarm — loud tone through default output (target: Logitech Z906).
    Uses sounddevice if available; falls back to winsound on Windows.
    """
    cfg = cfg or {}
    try:
        import numpy as np
        import sounddevice as sd

        sr = 44100
        t = np.linspace(0, duration_sec, int(sr * duration_sec), False)
        # Alternating dual-tone siren
        tone = 0.55 * np.sin(2 * np.pi * frequency_hz * t)
        tone += 0.35 * np.sin(2 * np.pi * (frequency_hz * 1.5) * t)
        # Amplitude gate for piercing pulses
        gate = (np.sin(2 * np.pi * 3.0 * t) > 0).astype(np.float32)
        audio = (tone * (0.4 + 0.6 * gate)).astype(np.float32)
        device = os.environ.get("ALERT_SPEAKER_DEVICE") or cfg.get("alert_speaker_device")
        kwargs: Dict[str, Any] = {"samplerate": sr, "blocking": True}
        # Prefer Wave Link / Z906 substring match when possible
        match = str(device or cfg.get("audio_output_match") or "Z906")
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                name = str(d.get("name") or "")
                if match.lower() in name.lower() and int(d.get("max_output_channels") or 0) > 0:
                    kwargs["device"] = i
                    break
        except Exception:
            pass
        sd.play(audio, **kwargs)
        return f"Z906 alarm blasted ({duration_sec}s) via sounddevice"
    except Exception:
        try:
            import winsound

            end = time.time() + duration_sec
            while time.time() < end:
                winsound.Beep(int(frequency_hz), 400)
                winsound.Beep(int(frequency_hz * 1.5), 400)
            return f"Z906 alarm blasted ({duration_sec}s) via winsound"
        except Exception as exc:
            return f"Alarm failed: {exc}"


def handle_critical_failure(
    cfg: Dict[str, Any],
    *,
    message: str,
    govee_fn: Optional[Callable] = None,
    govee_device: str = "bedroom",
) -> Dict[str, Any]:
    """Alert operator: ntfy first, optional Twilio, then Z906."""
    result: Dict[str, Any] = {"message": message}

    if govee_fn:
        try:
            result["govee"] = govee_fn(govee_device, "red")
            govee_fn(govee_device, "brightness", 100)
        except Exception as exc:
            result["govee"] = str(exc)

    call_url = ""
    try:
        from brain_server.call_routes import call_page_url

        call_url = call_page_url(cfg, reason="emergency")
    except Exception:
        call_url = ""
    try:
        from glados_phone.ntfy_alert import push_ntfy_alert

        result["ntfy"] = push_ntfy_alert(
            cfg,
            title="GLaDOS CRITICAL",
            message=message or "Facility critical failure",
            priority="urgent",
            click_url=call_url,
            action_label="Open emergency line",
        )
        result["call_url"] = call_url or None
    except Exception as exc:
        result["ntfy"] = {"ok": False, "detail": str(exc)}

    dial = dial_operator(cfg, message=message, wait_for_answer=True)
    result["dial"] = dial
    ntfy_ok = bool((result.get("ntfy") or {}).get("ok"))
    if not dial.get("answered") and not ntfy_ok:
        result["alarm"] = blast_z906_alarm(cfg)
    return result
