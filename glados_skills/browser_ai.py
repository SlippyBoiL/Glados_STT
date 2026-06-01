from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from glados_skills.browser_session import (
    DEFAULT_DEBUG_PORT,
    debug_port_from_cfg,
    ensure_browser_tab,
    list_cdp_targets,
)

SITE_URLS: Dict[str, str] = {
    "gemini": "https://gemini.google.com/app",
    "perplexity": "https://www.perplexity.ai/",
}

SITE_HINTS: Dict[str, str] = {
    "gemini": "gemini.google",
    "perplexity": "perplexity.ai",
}


class CdpSession:
    """One WebSocket — multiple CDP commands (focus, type, submit)."""

    def __init__(self, ws_url: str, timeout: float = 120.0):
        try:
            import websocket  # websocket-client
        except ImportError as e:
            raise RuntimeError(
                "Install websocket-client: py -3.11 -m pip install websocket-client"
            ) from e
        self._timeout = timeout
        self._ws = websocket.create_connection(ws_url, timeout=timeout)
        self._msg_id = 0

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass

    def call(self, method: str, params: Optional[dict] = None) -> dict:
        self._msg_id += 1
        mid = self._msg_id
        self._ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            raw = self._ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("id") != mid:
                continue
            if data.get("error"):
                raise RuntimeError(str(data["error"]))
            return data.get("result") or {}
        raise TimeoutError(f"CDP {method} timed out")

    def evaluate(self, expression: str, *, await_promise: bool = False) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": await_promise,
                "returnByValue": True,
            },
        )
        exc = result.get("exceptionDetails") or {}
        if exc:
            raise RuntimeError(str(exc.get("text") or exc))
        return (result.get("result") or {}).get("value")

    def setup_page(self) -> None:
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("DOM.enable")
        try:
            self.call("Page.bringToFront")
        except Exception:
            pass

    def navigate(self, url: str) -> None:
        self.call("Page.navigate", {"url": url})

    def insert_text(self, text: str) -> None:
        self.call("Input.insertText", {"text": text})

    def press_enter(self) -> None:
        for event_type in ("keyDown", "keyUp"):
            self.call(
                "Input.dispatchKeyEvent",
                {
                    "type": event_type,
                    "key": "Enter",
                    "code": "Enter",
                    "windowsVirtualKeyCode": 13,
                    "nativeVirtualKeyCode": 13,
                },
            )

    def click_at(self, x: float, y: float) -> None:
        for event_type, button in (
            ("mouseMoved", "none"),
            ("mousePressed", "left"),
            ("mouseReleased", "left"),
        ):
            params: Dict[str, Any] = {
                "type": event_type,
                "x": x,
                "y": y,
            }
            if button != "none":
                params["button"] = button
                params["clickCount"] = 1
            self.call("Input.dispatchMouseEvent", params)


FOCUS_INPUT_JS = """
(function() {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  function visible(el) {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return r.width > 12 && r.height > 12;
  }
  function walkShadow(root, fn) {
    const hit = fn(root);
    if (hit) return hit;
    const all = root.querySelectorAll ? root.querySelectorAll('*') : [];
    for (const el of all) {
      if (el.shadowRoot) {
        const inner = walkShadow(el.shadowRoot, fn);
        if (inner) return inner;
      }
    }
    return null;
  }
  function pick() {
    const tries = [
      () => walkShadow(document, (r) => r.querySelector('rich-textarea div[contenteditable="true"]')),
      () => walkShadow(document, (r) => r.querySelector('rich-textarea [contenteditable="true"]')),
      () => walkShadow(document, (r) => r.querySelector('rich-textarea textarea')),
      () => document.querySelector('div.ql-editor[contenteditable="true"]'),
      () => document.querySelector('[contenteditable="true"][aria-label*="Enter" i]'),
      () => document.querySelector('textarea[placeholder*="Ask" i]'),
      () => document.querySelector('textarea#ask-input'),
      () => document.querySelector('textarea'),
      () => document.querySelector('[role="textbox"]'),
      () => document.querySelector('div[contenteditable="true"]'),
    ];
    for (const fn of tries) {
      try {
        const el = fn();
        if (visible(el)) return el;
      } catch (e) {}
    }
    return null;
  }
  return (async function() {
    const input = pick();
    if (!input) return { ok: false, error: 'no input found' };
    input.scrollIntoView({ block: 'center', behavior: 'instant' });
    await sleep(300);
    input.focus();
    input.click();
    await sleep(200);
    if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {
      input.value = '';
      input.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      try {
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(input);
        sel.removeAllRanges();
        sel.addRange(range);
      } catch (e) {}
    }
    await sleep(150);
    return { ok: true, tag: input.tagName, site: location.hostname };
  })();
})()
"""


VERIFY_INPUT_JS = """
(function() {
  function walkShadow(root, fn) {
    const hit = fn(root);
    if (hit) return hit;
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) {
        const inner = walkShadow(el.shadowRoot, fn);
        if (inner) return inner;
      }
    }
    return null;
  }
  const el = walkShadow(document, (r) => r.querySelector('rich-textarea div[contenteditable="true"]'))
    || document.querySelector('div.ql-editor[contenteditable="true"]')
    || document.querySelector('textarea')
    || document.querySelector('[contenteditable="true"]');
  if (!el) return '';
  if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') return (el.value || '').trim();
  return (el.innerText || el.textContent || '').trim();
})()
"""


SUBMIT_JS = """
(function() {
  function visible(el) {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return r.width > 8 && r.height > 8;
  }
  const buttons = [...document.querySelectorAll('button, [role="button"]')];
  const sendBtn = buttons.find((b) => {
    if (!visible(b) || b.disabled) return false;
    const label = ((b.getAttribute('aria-label') || '') + ' ' + (b.innerText || '')).toLowerCase();
    return /send|submit|ask|search|enter/.test(label);
  });
  if (sendBtn) {
    sendBtn.click();
    return { ok: true, method: 'click' };
  }
  return { ok: false, method: 'none' };
})()
"""


EXTRACT_RESPONSE_JS = """
(function() {
  const chunks = [];
  const selectors = [
    '[data-message-author-role="model"]',
    '[data-testid*="answer"]',
    'model-response',
    '.prose',
    'main article',
    '[class*="markdown"]',
  ];
  for (const sel of selectors) {
    for (const el of document.querySelectorAll(sel)) {
      const t = (el.innerText || '').trim();
      if (t.length > 40) chunks.push(t);
    }
  }
  const merged = [...new Set(chunks)].join('\\n\\n');
  if (merged.length > 80) return merged.slice(-12000);
  return (document.body.innerText || '').trim().slice(-8000);
})()
"""


GET_INPUT_RECT_JS = """
(function() {
  function visible(el) {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return r.width > 12 && r.height > 12;
  }
  function walkShadow(root, fn) {
    const hit = fn(root);
    if (hit) return hit;
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) {
        const inner = walkShadow(el.shadowRoot, fn);
        if (inner) return inner;
      }
    }
    return null;
  }
  const tries = [
    () => walkShadow(document, (r) => r.querySelector('rich-textarea div[contenteditable="true"]')),
    () => walkShadow(document, (r) => r.querySelector('rich-textarea textarea')),
    () => document.querySelector('textarea#ask-input'),
    () => document.querySelector('textarea'),
    () => document.querySelector('div[contenteditable="true"]'),
  ];
  let input = null;
  for (const fn of tries) {
    try { input = fn(); if (visible(input)) break; } catch (e) {}
    input = null;
  }
  if (!input) return { ok: false };
  const r = input.getBoundingClientRect();
  return {
    ok: true,
    x: r.left + r.width / 2,
    y: r.top + r.height / 2,
    w: r.width,
    h: r.height,
  };
})()
"""


def _wait_for_page_ready(session: CdpSession, max_wait: float) -> bool:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            ready = session.evaluate("document.readyState")
            if ready == "complete":
                has_input = session.evaluate(
                    "Boolean(document.querySelector('textarea') || "
                    "document.querySelector('[contenteditable]') || "
                    "document.querySelector('rich-textarea'))"
                )
                if has_input:
                    return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


def _type_prompt(
    session: CdpSession,
    prompt: str,
    cfg: Dict[str, Any],
    *,
    site_key: str = "gemini",
    think_fn=None,
) -> tuple[bool, str]:
    type_delay = float(cfg.get("skills_learn_browser_type_delay_sec") or 1.5)
    after_type = float(cfg.get("skills_learn_browser_after_type_sec") or 2.5)
    verify_min = int(cfg.get("skills_learn_browser_verify_min_chars") or 8)
    use_desktop = bool(cfg.get("skills_learn_browser_desktop_admin", True))

    def log(phase: str, msg: str) -> None:
        if think_fn:
            try:
                think_fn(phase, msg)
            except Exception:
                pass

    use_desktop_first = bool(cfg.get("skills_learn_browser_desktop_first", True))
    if use_desktop_first:
        log("browser", "Desktop admin mode — focusing browser and typing with real keyboard.")
        from glados_skills.browser_desktop import desktop_admin_type

        ok, msg = desktop_admin_type(prompt, site_key, cfg)
        if ok:
            return True, msg
        log("browser", f"Desktop typing failed ({msg}); trying CDP…")

    log("browser", "Clicking the chat box via CDP…")

    rect = session.evaluate(GET_INPUT_RECT_JS)
    if isinstance(rect, dict) and rect.get("ok"):
        try:
            session.click_at(float(rect["x"]), float(rect["y"]))
            time.sleep(0.4)
        except Exception:
            pass

    session.evaluate(FOCUS_INPUT_JS, await_promise=True)
    time.sleep(type_delay)
    session.insert_text(prompt[:12000])
    time.sleep(after_type)

    typed = str(session.evaluate(VERIFY_INPUT_JS) or "").strip()
    if len(typed) < min(verify_min, max(8, len(prompt) // 5)):
        log("browser", "CDP typing failed — using real keyboard (admin mode).")
        if use_desktop:
            from glados_skills.browser_desktop import desktop_admin_type

            return desktop_admin_type(prompt, site_key, cfg)
        return False, f"Text did not stick in prompt ({len(typed)} chars visible)."

    before_submit = float(cfg.get("skills_learn_browser_before_submit_sec") or 2.0)
    time.sleep(before_submit)
    log("browser", "Submitting prompt.")

    submit = session.evaluate(SUBMIT_JS)
    if isinstance(submit, dict) and submit.get("ok"):
        return True, "submitted"

    session.press_enter()
    time.sleep(0.5)
    session.press_enter()
    return True, "submitted via Enter"


def _resolve_ws(port: int, hint: str, site_key: str) -> Optional[str]:
    for tab in list_cdp_targets(port):
        url = str(tab.get("url") or "").lower()
        if hint in url and tab.get("webSocketDebuggerUrl"):
            return str(tab["webSocketDebuggerUrl"])
    from glados_skills.browser_session import SESSION_FILE
    import os

    try:
        if os.path.isfile(SESSION_FILE):
            with open(SESSION_FILE, encoding="utf-8") as f:
                data = json.load(f) or {}
            tab_id = (data.get("site_tabs") or {}).get(site_key)
            if tab_id:
                for tab in list_cdp_targets(port):
                    if tab.get("id") == tab_id:
                        ws = tab.get("webSocketDebuggerUrl")
                        return str(ws) if ws else None
    except Exception:
        pass
    return None


def consult_in_browser(
    site: str,
    prompt: str,
    cfg: Dict[str, Any],
    *,
    think_fn=None,
) -> str:
    site_key = (site or "gemini").lower().strip()
    url = SITE_URLS.get(site_key) or SITE_URLS["gemini"]
    hint = SITE_HINTS.get(site_key, site_key)
    port = debug_port_from_cfg(cfg) or DEFAULT_DEBUG_PORT
    browser = str(cfg.get("preferred_browser") or "chrome")
    if browser == "default":
        browser = "chrome"

    load_sec = float(cfg.get("skills_learn_browser_load_sec") or 12.0)
    wait_sec = float(cfg.get("skills_learn_browser_wait_sec") or 180)
    poll_sec = float(cfg.get("skills_learn_browser_poll_sec") or 4.0)
    settle_polls = int(cfg.get("skills_learn_browser_settle_polls") or 4)

    def log(phase: str, msg: str) -> None:
        if think_fn:
            try:
                think_fn(phase, msg)
            except Exception:
                pass

    log("browser", f"Opening {site_key} in the Glados browser (admin control).")

    ok, nav_msg, ws_url = ensure_browser_tab(
        url,
        site_key=site_key,
        url_hint=hint,
        browser=browser,
        profile_dir=cfg.get("browser_profile_dir"),
        debug_port=port,
    )
    if not ok:
        return f"Browser unavailable: {nav_msg}"

    time.sleep(float(cfg.get("skills_learn_browser_after_nav_sec") or 2.0))
    if not ws_url:
        ws_url = _resolve_ws(port, hint, site_key)
    if not ws_url:
        time.sleep(load_sec)
        ws_url = _resolve_ws(port, hint, site_key)
    if not ws_url:
        return (
            f"Could not attach to {site_key} tab. Log in once in the Glados browser profile, then retry."
        )

    session = CdpSession(ws_url, timeout=wait_sec + 30)
    try:
        session.setup_page()
        try:
            session.navigate(url)
        except Exception:
            pass

        if not _wait_for_page_ready(session, load_sec):
            time.sleep(3.0)

        typed_ok, type_msg = _type_prompt(
            session,
            prompt,
            cfg,
            site_key=site_key,
            think_fn=think_fn,
        )
        if not typed_ok:
            return f"Browser {site_key}: could not type prompt — {type_msg}"
        log("browser", type_msg[:100])

        log("browser", f"Waiting for {site_key} to finish answering…")
        deadline = time.time() + wait_sec
        last_text = ""
        stable = 0
        min_response = int(cfg.get("skills_learn_browser_min_response_chars") or 60)

        while time.time() < deadline:
            time.sleep(poll_sec)
            try:
                text = str(session.evaluate(EXTRACT_RESPONSE_JS) or "").strip()
            except Exception:
                continue
            if len(text) < min_response:
                continue
            if text == last_text:
                stable += 1
                if stable >= settle_polls:
                    return text[:8000]
            else:
                stable = 0
                last_text = text

        if last_text:
            return last_text[:8000]
        return (
            f"Browser {site_key}: typed and submitted, but no full reply within {int(wait_sec)}s. "
            "Check the tab — partial notes may still help."
        )
    finally:
        session.close()


def list_browser_sites(cfg: Dict[str, Any]) -> List[str]:
    raw = cfg.get("skills_learn_browser_sites")
    if isinstance(raw, list) and raw:
        return [str(s).lower().strip() for s in raw if str(s).strip()]
    return ["gemini", "perplexity"]
