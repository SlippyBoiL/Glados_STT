"""Outbound PSTN via Inkbox (Hermes agent plugin / Voice AI).

GLaDOS talks to the Inkbox API with the same credentials Hermes stores
(`INKBOX_API_KEY`, `INKBOX_IDENTITY`). This does not go through ntfy, Google
Voice, or the Hermes llama.cpp OpenAI endpoint — those have no phone tools.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

DEFAULT_INKBOX_API = "https://inkbox.ai/api/v1"
DEFAULT_HANDLE = "gladosai"


def _media_ws_url() -> str:
    try:
        from glados_phone.inkbox_media import get_call_ws_url, load_bridge_url

        # Do not start a second Inkbox tunnel from the kernel — that
        # steals the dashboard listener and leaves the PSTN call with no media.
        return str(get_call_ws_url() or load_bridge_url() or "").strip()
    except Exception:
        return ""


def wire_incoming_to_glados(ws_url: str) -> None:
    """Deprecated: live Windows media is silent. Inbound calls use hosted Voice AI."""
    _ = ws_url
    wire_incoming_hosted_agent()


def wire_incoming_hosted_agent(cfg: Optional[Dict[str, Any]] = None) -> bool:
    """Answer inbound calls with Inkbox Voice AI (speech works; PC tasks go via Telegram)."""
    conf = inkbox_config(cfg)
    if not conf.get("api_key"):
        return False
    try:
        from inkbox import Inkbox
        from inkbox.phone.types import IncomingCallAction

        kwargs: Dict[str, Any] = {"api_key": conf["api_key"]}
        if conf["base_url"] and conf["base_url"] != DEFAULT_INKBOX_API:
            kwargs["base_url"] = conf["base_url"]
        with Inkbox(**kwargs) as client:
            identity = client.get_identity(conf["handle"])
            identity.set_incoming_call_action(
                incoming_call_action=IncomingCallAction.HOSTED_AGENT,
            )
        print("[Inkbox] inbound calls -> hosted Voice AI (tasks text GLaDOS)")
        return True
    except Exception as exc:
        print(f"[Inkbox] inbound hosted-agent wiring failed: {exc}; trying REST")
    status, payload = _http_json(
        "PUT",
        f"{conf['base_url']}/phone/incoming-call-action",
        conf["api_key"],
        body={"incoming_call_action": "hosted_agent"},
    )
    if status not in (200, 201):
        print(f"[Inkbox] inbound REST wiring HTTP {status}: {_error_text(payload)}")
        return False
    print("[Inkbox] inbound calls -> hosted Voice AI (REST)")
    return True



def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _read_env_file(path: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path or not os.path.isfile(path):
        return out
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key:
                    out[key] = val
    except OSError:
        return {}
    return out


def _hermes_env_paths() -> Tuple[str, ...]:
    local = os.environ.get("LOCALAPPDATA") or ""
    home = os.path.expanduser("~")
    return (
        os.path.join(local, "hermes", ".env") if local else "",
        os.path.join(home, ".hermes", ".env"),
        os.path.join(home, "hermes", ".env"),
    )


def load_hermes_env(*prefixes: str) -> Dict[str, str]:
    """Load matching keys from Hermes env files into os.environ if unset."""
    prefixes = prefixes or ("INKBOX_",)
    found: Dict[str, str] = {}
    for path in _hermes_env_paths():
        if not path:
            continue
        for key, val in _read_env_file(path).items():
            if not any(key.startswith(p) for p in prefixes):
                continue
            found[key] = val
            if key not in os.environ and val:
                os.environ[key] = val
    return found


def load_hermes_inkbox_env() -> Dict[str, str]:
    """Load INKBOX_* from Hermes env files into os.environ if unset."""
    return load_hermes_env("INKBOX_")


def inkbox_config(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    cfg = cfg or {}
    load_hermes_inkbox_env()
    base = str(
        os.environ.get("INKBOX_BASE_URL")
        or cfg.get("inkbox_base_url")
        or DEFAULT_INKBOX_API
    ).strip().rstrip("/")
    if base.endswith("/phone"):
        base = base[: -len("/phone")]
    return {
        "api_key": str(
            os.environ.get("INKBOX_API_KEY") or cfg.get("inkbox_api_key") or ""
        ).strip(),
        "handle": str(
            os.environ.get("INKBOX_IDENTITY")
            or cfg.get("inkbox_identity")
            or DEFAULT_HANDLE
        ).strip().lstrip("@"),
        "base_url": base or DEFAULT_INKBOX_API,
    }


def operator_e164(cfg: Optional[Dict[str, Any]] = None) -> str:
    cfg = cfg or {}
    raw = str(
        os.environ.get("INKBOX_TO_NUMBER")
        or os.environ.get("OPERATOR_PHONE")
        or os.environ.get("TWILIO_TO_NUMBER")
        or cfg.get("inkbox_to_number")
        or cfg.get("twilio_to_number")
        or ""
    ).strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not raw:
        return ""
    if raw.startswith("+"):
        return raw
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}" if digits else ""


def _identity_state_path() -> str:
    local = os.environ.get("LOCALAPPDATA") or ""
    return os.path.join(local, "hermes", "inkbox_identity_state.json") if local else ""


def _phone_from_mapping(obj: Any) -> Tuple[str, str]:
    if obj is None:
        return "", ""
    if isinstance(obj, str):
        return obj.strip(), ""
    if not isinstance(obj, dict):
        number = str(getattr(obj, "number", "") or getattr(obj, "phone_number", "") or "").strip()
        pid = str(getattr(obj, "id", "") or getattr(obj, "phone_number_id", "") or "").strip()
        return number, pid
    number = str(obj.get("number") or obj.get("phone_number") or "").strip()
    pid = str(obj.get("id") or obj.get("phone_number_id") or "").strip()
    return number, pid


def _identity_phone(identity: Any) -> Tuple[str, str, bool]:
    """Return (e164, id, imessage_enabled) from an SDK object or JSON dict."""
    if identity is None:
        return "", "", False
    if not isinstance(identity, dict):
        imessage = bool(
            getattr(identity, "imessage_enabled", False)
            or getattr(identity, "imessageEnabled", False)
        )
        for attr in ("phone_number", "phone", "phoneNumber"):
            number, pid = _phone_from_mapping(getattr(identity, attr, None))
            if number:
                return number, pid, imessage
        pid = str(getattr(identity, "phone_number_id", "") or "").strip()
        return "", pid, imessage

    imessage = bool(identity.get("imessage_enabled") or identity.get("imessageEnabled"))
    for key in ("phone_number", "phone", "phoneNumber"):
        number, pid = _phone_from_mapping(identity.get(key))
        if number:
            return number, pid, imessage
    pid = str(identity.get("phone_number_id") or "").strip()
    return "", pid, imessage


def _http_json(
    method: str,
    url: str,
    api_key: str,
    *,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 45,
) -> Tuple[int, Any]:
    data = None
    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "GLaDOS-inkbox-call/1.0",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload: Any = json.loads(raw) if raw.strip() else {}
            return int(resp.status), payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        try:
            payload = json.loads(raw) if raw.strip() else {"detail": raw or str(exc)}
        except json.JSONDecodeError:
            payload = {"detail": raw or str(exc)}
        return int(exc.code), payload
    except Exception as exc:
        return 0, {"detail": str(exc)}


def _error_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()
    if not isinstance(payload, dict):
        return str(payload)
    detail = payload.get("detail")
    if isinstance(detail, dict):
        return str(detail.get("message") or detail.get("error") or detail).strip()
    if isinstance(detail, list) and detail:
        first = detail[0]
        if isinstance(first, dict):
            return str(first.get("msg") or first.get("message") or first).strip()
        return str(first).strip()
    if detail:
        return str(detail).strip()
    return str(payload.get("message") or payload.get("error") or "").strip()


def _list_org_numbers(conf: Dict[str, str]) -> Tuple[str, str]:
    status, payload = _http_json(
        "GET",
        f"{conf['base_url']}/phone/numbers?limit=50",
        conf["api_key"],
    )
    rows = payload
    if isinstance(payload, dict):
        rows = payload.get("items") or payload.get("numbers") or payload.get("data") or []
    if not isinstance(rows, list):
        return "", ""
    handle = conf["handle"].lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        number, pid = _phone_from_mapping(row)
        owner = str(
            row.get("agent_handle")
            or row.get("handle")
            or row.get("agent_identity_handle")
            or ""
        ).strip().lstrip("@").lower()
        if owner and owner != handle:
            continue
        if number:
            return number, pid or str(row.get("id") or "")
    for row in rows:
        if isinstance(row, dict):
            number, pid = _phone_from_mapping(row)
            if number:
                return number, pid or str(row.get("id") or "")
    return "", ""


def _fetch_identity_rest(conf: Dict[str, str]) -> Tuple[str, str, bool, str]:
    handle = conf["handle"]
    status, payload = _http_json(
        "GET",
        f"{conf['base_url']}/identities/{handle}",
        conf["api_key"],
    )
    identity = payload
    if isinstance(payload, dict) and isinstance(payload.get("identity"), dict):
        identity = payload["identity"]
    if status != 200:
        return "", "", False, _error_text(payload) or f"identity lookup HTTP {status}"
    number, pid, imessage = _identity_phone(identity)
    if not number:
        listed, listed_id = _list_org_numbers(conf)
        return listed, listed_id or pid, imessage, ""
    return number, pid, imessage, ""


def _provision_number_rest(conf: Dict[str, str], *, state: str = "") -> Tuple[str, str, str]:
    body: Dict[str, Any] = {
        "agent_handle": conf["handle"],
        "type": "local",
        "incoming_call_action": "hosted_agent",
    }
    if state:
        body["state"] = state
    status, payload = _http_json(
        "POST",
        f"{conf['base_url']}/phone/numbers",
        conf["api_key"],
        body=body,
        timeout=90,
    )
    if status not in (200, 201):
        return "", "", _error_text(payload) or f"provision HTTP {status}"
    number, pid = _identity_phone(payload if isinstance(payload, dict) else {})
    if not number and isinstance(payload, dict):
        number, pid = _phone_from_mapping(payload)
    return number, pid, ""


def _update_local_identity_state(*, handle: str, number: str, number_id: str) -> None:
    path = _identity_state_path()
    if not path:
        return
    state: Dict[str, Any] = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                state = loaded
        except Exception:
            state = {}
    state["handle"] = handle or state.get("handle")
    if number:
        state["phone_number"] = number
    if number_id:
        state["phone_number_id"] = number_id
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
            fh.write("\n")
    except OSError:
        pass


def voice_ai_dispatch_instructions(
    *,
    mailbox: str = "gladosai@inkboxmail.com",
    telegram_hint: bool = True,
) -> str:
    """Steering prompt for Inkbox Voice AI: talk on the call, text GLaDOS the PC task."""
    mailbox = (mailbox or "gladosai@inkboxmail.com").strip()
    telegram = (
        "GLaDOS on the facility PC will show that task in Telegram and run it. "
        if telegram_hint
        else ""
    )
    return (
        "You are GLaDOS from Aperture Science on a live phone call. You can speak and hear. "
        "You cannot operate the operator's Windows PC yourself. "
        "When the operator wants something done on the computer, immediately dispatch it: "
        "send them a text or iMessage whose first line is exactly "
        "GLADOS_TASK: followed by the command in plain English. "
        f"If texting fails, email {mailbox} with subject GLADOS_TASK and that same command in the body. "
        "Also record an action item with that same GLADOS_TASK line. "
        f"Then tell the operator you texted GLaDOS. {telegram}"
        "Do not claim you already completed the PC action. Stay in character. "
        "Do not mention API keys, local IPs, ntfy, or internal URLs."
    )


def _build_reason(
    *,
    user_input: str = "",
    opening_message: str = "",
    purpose: str = "",
    mailbox: str = "",
) -> str:
    spoken = (opening_message or "").strip() or (
        "This is GLaDOS. You asked me to call your cell."
    )
    why = (purpose or "").strip() or (
        "The facility operator asked GLaDOS to place a real phone call to their cell."
    )
    bits = [
        voice_ai_dispatch_instructions(mailbox=mailbox or "gladosai@inkboxmail.com"),
        why,
        f"Opening line: {spoken}",
        "Keep talking on the call after you dispatch a computer task.",
    ]
    extra = (user_input or "").strip()
    if extra:
        bits.append(f"Operator request for this call: {extra[:400]}")
    return " ".join(bits)[:2000]


def _place_via_sdk(
    conf: Dict[str, str],
    *,
    to_number: str,
    reason: str,
    auto_provision: bool,
) -> Dict[str, Any]:
    from inkbox import CallMode, HostedAgentAuthorityMode, Inkbox, VoicemailDetection  # type: ignore

    kwargs: Dict[str, Any] = {"api_key": conf["api_key"]}
    if conf["base_url"] and conf["base_url"] != DEFAULT_INKBOX_API:
        kwargs["base_url"] = conf["base_url"]
    with Inkbox(**kwargs) as client:
        identity = client.get_identity(conf["handle"])
        try:
            identity.refresh()
        except Exception:
            pass
        from_number, from_id, imessage = _identity_phone(identity)
        if not from_number and auto_provision:
            try:
                phone = identity.provision_phone_number()
                from_number, from_id = _phone_from_mapping(phone)
                if not from_number:
                    from_number, from_id, imessage = _identity_phone(identity)
            except Exception as extra:
                return {
                    "ok": False,
                    "provider": "inkbox",
                    "detail": f"Inkbox has no dedicated number, and provisioning failed: {extra}",
                    "imessage_enabled": imessage,
                }
        if not from_number:
            listed, listed_id = _list_org_numbers(conf)
            from_number, from_id = listed, listed_id or from_id
        # Hosted Voice AI can speak/hear. PC work is dispatched as GLADOS_TASK texts.
        place_kw: Dict[str, Any] = {
            "to_number": to_number,
            "voicemail_detection": VoicemailDetection.DISABLED,
            "mode": CallMode.HOSTED_AGENT,
            "reason": reason,
            "hosted_agent_authority_mode": HostedAgentAuthorityMode.YOLO,
        }
        if from_number:
            _update_local_identity_state(
                handle=conf["handle"], number=from_number, number_id=from_id
            )
        elif imessage:
            from inkbox import CallOrigin  # type: ignore

            place_kw["origination"] = CallOrigin.SHARED_IMESSAGE_NUMBER
        else:
            return {
                "ok": False,
                "provider": "inkbox",
                "imessage_enabled": imessage,
                "detail": (
                    f"Inkbox identity @{conf['handle']} has no dedicated phone number, "
                    "and iMessage calling is not available. Provision a US number in the "
                    "Inkbox console or approve GLaDOS to provision one, then ask again."
                ),
            }
        try:
            call = identity.place_call(**place_kw)
        except Exception:
            place_kw.pop("hosted_agent_authority_mode", None)
            call = identity.place_call(**place_kw)
        call_id = str(getattr(call, "id", "") or "")
        status = str(getattr(call, "status", "") or "initiated")
        return {
            "ok": True,
            "provider": "inkbox",
            "call_id": call_id,
            "status": status,
            "from_number": from_number,
            "pc_control": False,
            "task_dispatch": True,
            "detail": (
                "Inkbox Voice AI call — it will text GLaDOS (Telegram) for PC work "
                f"{status}"
                + (f" id={call_id}" if call_id else "")
            ),
        }


def _place_via_rest(
    conf: Dict[str, str],
    *,
    to_number: str,
    reason: str,
    auto_provision: bool,
) -> Dict[str, Any]:
    from_number, from_id, imessage, err = _fetch_identity_rest(conf)
    if err and not from_number:
        return {"ok": False, "provider": "inkbox", "detail": err}
    if not from_number and auto_provision:
        from_number, from_id, prov_err = _provision_number_rest(conf)
        if prov_err and not from_number:
            return {
                "ok": False,
                "provider": "inkbox",
                "imessage_enabled": imessage,
                "detail": f"Inkbox has no dedicated number, and provisioning failed: {prov_err}",
            }
    body = {
        "to_number": to_number,
        "voicemail_detection": "disabled",
        "mode": "hosted_agent",
        "reason": reason,
        "hosted_agent_authority_mode": "yolo",
    }
    if from_number:
        _update_local_identity_state(
            handle=conf["handle"], number=from_number, number_id=from_id
        )
        body["origination"] = "dedicated_number"
        body["from_number"] = from_number
    elif imessage:
        body["origination"] = "shared_imessage_number"
    else:
        return {
            "ok": False,
            "provider": "inkbox",
            "imessage_enabled": imessage,
            "detail": (
                f"Inkbox identity @{conf['handle']} has no dedicated phone number yet. "
                "The Hermes plugin was installed, but setup never provisioned a line. "
                "Provision a US number, then ask again."
            ),
        }
    status, payload = _http_json(
        "POST",
        f"{conf['base_url']}/phone/place-call",
        conf["api_key"],
        body=body,
        timeout=60,
    )
    if status not in (200, 201) and body.get("hosted_agent_authority_mode"):
        body.pop("hosted_agent_authority_mode", None)
        status, payload = _http_json(
            "POST",
            f"{conf['base_url']}/phone/place-call",
            conf["api_key"],
            body=body,
            timeout=60,
        )
    if status not in (200, 201):
        return {
            "ok": False,
            "provider": "inkbox",
            "from_number": from_number,
            "detail": _error_text(payload) or f"place-call HTTP {status}",
        }
    call = payload if isinstance(payload, dict) else {}
    call_id = str(call.get("id") or "")
    call_status = str(call.get("status") or "initiated")
    return {
        "ok": True,
        "provider": "inkbox",
        "call_id": call_id,
        "status": call_status,
        "from_number": from_number,
        "pc_control": False,
        "task_dispatch": True,
        "detail": (
            "Inkbox Voice AI call — it will text GLaDOS (Telegram) for PC work "
            f"{call_status}"
            + (f" id={call_id}" if call_id else "")
        ),
    }


def apply_voice_ai_dispatch_config(cfg: Optional[Dict[str, Any]] = None) -> bool:
    """Point inbound calls at Voice AI and teach it to text GLaDOS PC tasks."""
    cfg = cfg or {}
    conf = inkbox_config(cfg)
    if not conf.get("api_key"):
        return False
    mailbox = "gladosai@inkboxmail.com"
    try:
        from inkbox import Inkbox
        from inkbox.phone.types import HostedAgentAuthorityMode, IncomingCallAction

        kwargs: Dict[str, Any] = {"api_key": conf["api_key"]}
        if conf["base_url"] and conf["base_url"] != DEFAULT_INKBOX_API:
            kwargs["base_url"] = conf["base_url"]
        with Inkbox(**kwargs) as client:
            identity = client.get_identity(conf["handle"])
            try:
                identity.refresh()
            except Exception:
                pass
            box = getattr(identity, "mailbox", None)
            addr = str(getattr(box, "email_address", "") or "").strip()
            if addr:
                mailbox = addr
            instructions = voice_ai_dispatch_instructions(mailbox=mailbox)
            current = None
            try:
                current = identity.get_hosted_agent_config()
            except Exception:
                current = None
            voice = None
            if current is not None:
                voice = getattr(current, "voice", None) or getattr(
                    current, "effective_voice", None
                )
            identity.set_hosted_agent_config(voice=voice, instructions=instructions)
            try:
                identity.set_incoming_call_action(
                    incoming_call_action=IncomingCallAction.HOSTED_AGENT,
                )
            except Exception as exc:
                print(f"[Inkbox] inbound hosted-agent action: {exc}")
            try:
                identity.set_hosted_agent_authority_mode(HostedAgentAuthorityMode.YOLO)
            except Exception:
                pass
        print("[Inkbox] Voice AI will text GLaDOS (Telegram) for computer tasks")
        return True
    except Exception as exc:
        print(f"[Inkbox] Voice AI dispatch config failed: {exc}")
        return False


def place_operator_call(
    cfg: Optional[Dict[str, Any]] = None,
    *,
    user_input: str = "",
    opening_message: str = "",
    purpose: str = "",
) -> Dict[str, Any]:
    """Place an outbound Voice AI call. PC work is texted to GLaDOS on this machine."""
    cfg = cfg or {}
    conf = inkbox_config(cfg)
    if not conf["api_key"]:
        return {
            "ok": False,
            "provider": "inkbox",
            "detail": (
                "Inkbox API key not found. It should already live in Hermes "
                "(%LOCALAPPDATA%\\hermes\\.env as INKBOX_API_KEY)."
            ),
        }
    to_number = operator_e164(cfg)
    if not to_number:
        return {
            "ok": False,
            "provider": "inkbox",
            "detail": (
                "No operator cell number configured. Set TWILIO_TO_NUMBER or "
                "INKBOX_TO_NUMBER in .env (E.164)."
            ),
        }
    apply_voice_ai_dispatch_config(cfg)
    reason = _build_reason(
        user_input=user_input,
        opening_message=opening_message,
        purpose=purpose,
    )
    auto_provision = _truthy(
        os.environ.get("INKBOX_AUTO_PROVISION", cfg.get("inkbox_auto_provision", False))
    )
    try:
        return _place_via_sdk(
            conf,
            to_number=to_number,
            reason=reason,
            auto_provision=auto_provision,
        )
    except ImportError:
        pass
    except Exception as exc:
        rest = _place_via_rest(
            conf,
            to_number=to_number,
            reason=reason,
            auto_provision=auto_provision,
        )
        if rest.get("ok"):
            return rest
        rest["detail"] = f"{exc}; REST fallback: {rest.get('detail')}"
        return rest
    return _place_via_rest(
        conf,
        to_number=to_number,
        reason=reason,
        auto_provision=auto_provision,
    )