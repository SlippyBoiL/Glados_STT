from __future__ import annotations

import os
from typing import Any, Dict, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROFILE = os.path.join(REPO_ROOT, "data", "glados_playwright_profile")


def profile_dir_from_cfg(cfg: Dict[str, Any]) -> str:
    raw = str(
        cfg.get("browser_agent_profile_dir")
        or cfg.get("browser_profile_dir")
        or DEFAULT_PROFILE
    ).strip()
    if not os.path.isabs(raw):
        raw = os.path.join(REPO_ROOT, raw)
    return raw


class GladosBrowser:
    """Headed Playwright browser — visible on the user's monitor."""

    def __init__(self, cfg: Dict[str, Any]) -> None:
        self._cfg = cfg
        self._profile = profile_dir_from_cfg(cfg)
        self._headless = bool(cfg.get("browser_agent_headless", False))
        self._slow_mo = int(cfg.get("browser_agent_slow_mo_ms") or 80)
        self._pw: Any = None
        self._context: Any = None
        self.page: Any = None
        self.last_error = ""

    def start(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.last_error = (
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
            return False

        os.makedirs(self._profile, exist_ok=True)
        try:
            self._pw = sync_playwright().start()
            launch_kw: Dict[str, Any] = {
                "user_data_dir": self._profile,
                "headless": self._headless,
                "slow_mo": self._slow_mo,
                "viewport": {"width": 1280, "height": 900},
                "args": ["--start-maximized"],
            }
            channel = str(self._cfg.get("browser_agent_channel") or "chrome").strip()
            if channel:
                launch_kw["channel"] = channel

            try:
                self._context = self._pw.chromium.launch_persistent_context(**launch_kw)
            except Exception:
                launch_kw.pop("channel", None)
                self._context = self._pw.chromium.launch_persistent_context(**launch_kw)

            self.page = self._context.pages[0] if self._context.pages else self._context.new_page()
            self.last_error = ""
            return True
        except Exception as e:
            self.last_error = str(e)
            self.close()
            return False

    def close(self) -> None:
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._context = None
        self._pw = None
        self.page = None

    def __enter__(self) -> "GladosBrowser":
        if not self.start():
            raise RuntimeError(self.last_error or "Browser failed to start")
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
