"""
Central config for Glados (OpenJarvis-style: local-first, single YAML + env overrides).
"""
from __future__ import annotations

import os
from typing import Any, Dict

try:
    import yaml
except ImportError:
    yaml = None

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(REPO_ROOT, "configs", "glados.yaml")


def _deep_set(target: Dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    target[key] = value


def load_config() -> Dict[str, Any]:
    """
    Defaults → configs/glados.yaml → environment variables (highest priority).
    """
    cfg: Dict[str, Any] = {
        "ollama_base_url": "http://127.0.0.1:11434/v1",
        "model_name": "llama3.2-vision",
        "vision_model": "llama3.2-vision",
        "piper_model_path": os.path.join(REPO_ROOT, "glados.onnx"),
        "piper_output_wav": os.path.join(REPO_ROOT, "local_glados_response.wav"),
        "audio_output_match": "Wave Link",
        "audio_input_match": "Wave Link",
        "plugins_dir": "plugins",
        # Inference speed (Ollama does GPU work on the *server* at ollama_base_url, not this PC)
        "llm_max_tokens": 512,
        "chat_history_max_messages": 24,
        "screen_capture_max_edge": 960,
        "vision_jpeg_max_edge": 896,
        "vision_jpeg_quality": 78,
        "ollama_keep_alive": "",
        # Input mode: "voice" (wake word), "text" (type), "hybrid" (type or press Enter for voice)
        "input_mode": "voice",
    }

    if yaml is not None and os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                file_cfg = yaml.safe_load(f)
            if isinstance(file_cfg, dict):
                cfg.update({k: v for k, v in file_cfg.items() if v is not None})
        except Exception:
            pass

    # Env overrides (same names you already use in places)
    _deep_set(cfg, "ollama_base_url", os.environ.get("OLLAMA_BASE_URL"))
    _deep_set(cfg, "model_name", os.environ.get("MODEL_NAME"))
    _deep_set(cfg, "vision_model", os.environ.get("VISION_MODEL"))
    _deep_set(cfg, "piper_model_path", os.environ.get("PIPER_MODEL_PATH"))
    _deep_set(cfg, "piper_output_wav", os.environ.get("PIPER_OUTPUT_WAV"))
    _deep_set(cfg, "audio_output_match", os.environ.get("AUDIO_OUTPUT_MATCH"))
    _deep_set(cfg, "audio_input_match", os.environ.get("AUDIO_INPUT_MATCH"))
    _deep_set(cfg, "llm_max_tokens", os.environ.get("GLADOS_LLM_MAX_TOKENS"))
    _deep_set(cfg, "chat_history_max_messages", os.environ.get("GLADOS_CHAT_HISTORY_MAX"))
    _deep_set(cfg, "screen_capture_max_edge", os.environ.get("GLADOS_SCREEN_MAX_EDGE"))
    _deep_set(cfg, "vision_jpeg_max_edge", os.environ.get("GLADOS_VISION_JPEG_MAX_EDGE"))
    _deep_set(cfg, "vision_jpeg_quality", os.environ.get("GLADOS_VISION_JPEG_QUALITY"))
    _deep_set(cfg, "ollama_keep_alive", os.environ.get("OLLAMA_KEEP_ALIVE"))
    _deep_set(cfg, "input_mode", os.environ.get("GLADOS_INPUT_MODE"))

    for key in ("llm_max_tokens", "chat_history_max_messages", "screen_capture_max_edge", "vision_jpeg_max_edge", "vision_jpeg_quality"):
        if cfg.get(key) is not None:
            try:
                cfg[key] = int(cfg[key])
            except (TypeError, ValueError):
                pass

    # Resolve relative paths from repo root
    for key in ("piper_model_path", "piper_output_wav"):
        p = cfg.get(key)
        if isinstance(p, str) and p and not os.path.isabs(p):
            cfg[key] = os.path.normpath(os.path.join(REPO_ROOT, p))

    return cfg
