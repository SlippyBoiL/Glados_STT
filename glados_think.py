"""Split model chain-of-thought from the spoken GLaDOS reply.

Handles Qwen/llama.cpp ``<think>`` tags and OpenAI-style ``reasoning_content``.
Thoughts are for the HUD only — never TTS.
"""
from __future__ import annotations

import re
from typing import Any, Tuple

_THINK_BLOCK = re.compile(r"<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)
_UNCLOSED_THINK = re.compile(r"<think>(.*)\Z", re.IGNORECASE | re.DOTALL)
_INCOMPLETE_TAG = re.compile(r"</?t(?:h(?:i(?:n(?:k(?:\s*)?)?)?)?)?\Z", re.IGNORECASE)
_THINK_TAG_ANY = re.compile(r"</?think>", re.IGNORECASE)


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def delta_fields(delta: Any) -> Tuple[str, str]:
    """Return (content, reasoning) from a streaming chat delta."""
    if delta is None:
        return "", ""
    if isinstance(delta, dict):
        content = _as_text(delta.get("content"))
        reasoning = _as_text(
            delta.get("reasoning_content") or delta.get("reasoning")
        )
        return content, reasoning
    content = _as_text(getattr(delta, "content", None))
    reasoning = _as_text(
        getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
    )
    extra = getattr(delta, "model_extra", None)
    if isinstance(extra, dict) and not reasoning:
        reasoning = _as_text(extra.get("reasoning_content") or extra.get("reasoning"))
    return content, reasoning


def split_think_speak(content: str, reasoning: str = "") -> Tuple[str, str]:
    """Return (thinking, spoken) from accumulated content + optional reasoning field."""
    content = _as_text(content)
    reasoning = _as_text(reasoning).strip()
    think_parts = []
    if reasoning:
        think_parts.append(reasoning)

    closed = _THINK_BLOCK.findall(content)
    think_parts.extend(p.strip() for p in closed if p and p.strip())
    remainder = _THINK_BLOCK.sub("", content)
    unclosed = _UNCLOSED_THINK.search(remainder)
    if unclosed:
        think_parts.append(unclosed.group(1).strip())
        remainder = remainder[: unclosed.start()]
    remainder = _INCOMPLETE_TAG.sub("", remainder)
    remainder = _THINK_TAG_ANY.sub("", remainder).strip()
    thinking = "\n".join(p for p in think_parts if p).strip()
    return thinking, remainder


def strip_think_tags(text: str) -> str:
    """Drop think blocks so TTS never reads them."""
    _, spoken = split_think_speak(text or "")
    return spoken


class ThinkSpeakAccumulator:
    """Incremental splitter for streamed tokens."""

    def __init__(self) -> None:
        self._content = ""
        self._reasoning = ""
        self.thinking = ""
        self.spoken = ""

    def feed(self, content_piece: str = "", reasoning_piece: str = "") -> Tuple[str, str]:
        if content_piece:
            self._content += content_piece
        if reasoning_piece:
            self._reasoning += reasoning_piece
        self.thinking, self.spoken = split_think_speak(self._content, self._reasoning)
        return self.thinking, self.spoken
