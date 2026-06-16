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
        "llm_provider": "openclaw",
        "openclaw_base_url": "http://127.0.0.1:18789/v1",
        "openclaw_model": "openclaw/default",
        "openclaw_config_path": "",
        "openclaw_api_key": "",
        "openclaw_vision_backend": "",
        "openclaw_embedding_backend": "",
        "ollama_base_url": "http://127.0.0.1:11434/v1",
        "model_name": "openclaw/default",
        "vision_model": "openclaw/default",
        "piper_model_path": os.path.join(REPO_ROOT, "glados.onnx"),
        "piper_output_wav": os.path.join(REPO_ROOT, "local_glados_response.wav"),
        "piper_exe_path": "",
        "audio_output_match": "Wave Link",
        "audio_input_match": "Wave Link",
        "plugins_dir": "plugins",
        # Wake word + local STT (Phase 1)
        "wake_word_engine": "porcupine",
        "porcupine_keywords": ["hey glados"],
        "stt_engine": "faster_whisper",
        "whisper_model": "base.en",
        "whisper_compute_type": "int8",
        "whisper_language": "en",
        "wake_cooldown_sec": 1.5,
        "mic_sample_rate": 16000,
        "mic_channels": 1,
        "pre_roll_ms": 500,
        "utterance_max_sec": 10,
        # Memory (Phase 0: static JSON facts + optional ChromaDB)
        "memory_enable_chroma": False,
        "chroma_persist_dir": os.path.join(REPO_ROOT, "chroma_db"),
        "chroma_collection": "glados_memories",
        "embedding_backend": "openclaw",
        "embedding_model": "openclaw/default",
        "memory_consolidation_enabled": True,
        "memory_consolidation_min_fact_len": 10,
        # Inference speed (Ollama does GPU work on the *server* at ollama_base_url, not this PC)
        "llm_max_tokens": 512,
        "chat_history_max_messages": 24,
        "screen_capture_max_edge": 960,
        "vision_jpeg_max_edge": 896,
        "vision_jpeg_quality": 78,
        "ollama_keep_alive": "",
        # Input mode: "voice" (wake word), "text" (type), "hybrid" (type or press Enter for voice)
        "input_mode": "voice",
        # Background monitoring
        "monitoring_enabled": False,
        "monitoring_interval_sec": 300,
        "monitoring_devices": ["pihole", "twingate"],
        # Brain dashboard (FastAPI + web UI)
        "brain_dashboard_enabled": True,
        "brain_dashboard_host": "0.0.0.0",
        "brain_dashboard_port": 8080,
        "brain_dashboard_url": "http://localhost:8080",
        "brain_dashboard_token": "",
        # Chat vs execution: text_only (default), auto (legacy: run code when model outputs it)
        "execution_mode": "text_only",
        # TensorFlow intent router (often misroutes chat); off by default for speed/clarity
        "omni_brain_enabled": False,
        "omni_brain_confidence_threshold": 72,
        "memory_top_k": 2,
        "memory_force_sandwich": False,
        "os_control_enabled": False,
        # Facility Brain (separate scan + decision file — configs/facility_brain.yaml)
        "facility_brain_enabled": True,
        "facility_brain_config_path": os.path.join(REPO_ROOT, "configs", "facility_brain.yaml"),
        "skills_brain_path": os.path.join(REPO_ROOT, "data", "glados_skills_brain.json"),
        "skills_self_develop": True,
        "skills_conversational_learn": True,
        "skills_learn_until_success": True,
        "skills_learn_unlimited_attempts": True,
        "skills_learn_safety_cap": 0,
        "skills_learn_max_attempts": 0,
        "skills_learn_use_web": True,
        "web_search_mode": "duckduckgo_scrape",
        "skills_learn_use_free_web": True,
        "web_scrape_timeout_sec": 12.0,
        "skills_learn_open_browser": False,
        "skills_learn_reuse_browser": False,
        "skills_learn_pause_sec": 2.0,
        "skills_learn_step_pause_sec": 6.0,
        "skills_learn_use_browser_ai": False,
        "idle_epiphany_enabled": True,
        "idle_epiphany_minutes": 5.0,
        "idle_epiphany_poll_sec": 30.0,
        "skills_learn_skip_search_tabs": True,
        "skills_learn_browser_sites": ["gemini", "perplexity"],
        "skills_learn_browser_wait_sec": 180,
        "skills_learn_browser_poll_sec": 4.0,
        "skills_learn_browser_load_sec": 14.0,
        "skills_learn_browser_after_nav_sec": 3.0,
        "skills_learn_browser_type_delay_sec": 1.5,
        "skills_learn_browser_after_type_sec": 2.5,
        "skills_learn_browser_before_submit_sec": 2.0,
        "skills_learn_browser_cycle_pause_sec": 10.0,
        "skills_learn_browser_settle_polls": 4,
        "skills_learn_browser_desktop_admin": True,
        "skills_learn_browser_desktop_first": True,
        "skills_learn_skip_browser_for_direct": True,
        "glados_repo_root": REPO_ROOT,
        "skills_learn_use_ai_council": False,
        "gemini_model": "gemini-2.0-flash",
        "gemini_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "skills_learn_use_openai_advisor": False,
        "openai_advisor_model": "gpt-4o-mini",
        "skills_auto_learn_on_success": False,
        "skills_run_direct": True,
        "llm_warmup_on_start": True,
        "conversational_skip_memory": True,
        "facility_context_in_chat": True,
        "tts_async": True,
        "tts_enabled": True,
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
    _deep_set(cfg, "llm_provider", os.environ.get("LLM_PROVIDER"))
    _deep_set(cfg, "openclaw_base_url", os.environ.get("OPENCLAW_BASE_URL"))
    _deep_set(cfg, "openclaw_model", os.environ.get("OPENCLAW_MODEL"))
    _deep_set(cfg, "openclaw_api_key", os.environ.get("OPENCLAW_GATEWAY_TOKEN") or os.environ.get("OPENCLAW_API_KEY"))
    _deep_set(cfg, "openclaw_vision_backend", os.environ.get("OPENCLAW_VISION_BACKEND"))
    _deep_set(cfg, "openclaw_embedding_backend", os.environ.get("OPENCLAW_EMBEDDING_BACKEND"))
    _deep_set(cfg, "ollama_base_url", os.environ.get("OLLAMA_BASE_URL"))
    _deep_set(cfg, "model_name", os.environ.get("MODEL_NAME"))
    _deep_set(cfg, "vision_model", os.environ.get("VISION_MODEL"))
    _deep_set(cfg, "piper_model_path", os.environ.get("PIPER_MODEL_PATH"))
    _deep_set(cfg, "piper_output_wav", os.environ.get("PIPER_OUTPUT_WAV"))
    _deep_set(cfg, "piper_exe_path", os.environ.get("PIPER_EXE_PATH"))
    _deep_set(cfg, "audio_output_match", os.environ.get("AUDIO_OUTPUT_MATCH"))
    _deep_set(cfg, "audio_input_match", os.environ.get("AUDIO_INPUT_MATCH"))
    _deep_set(cfg, "wake_word_engine", os.environ.get("WAKE_WORD_ENGINE"))
    _deep_set(cfg, "porcupine_keywords", os.environ.get("PORCUPINE_KEYWORDS"))
    _deep_set(cfg, "stt_engine", os.environ.get("STT_ENGINE"))
    _deep_set(cfg, "whisper_model", os.environ.get("WHISPER_MODEL"))
    _deep_set(cfg, "whisper_compute_type", os.environ.get("WHISPER_COMPUTE_TYPE"))
    _deep_set(cfg, "whisper_language", os.environ.get("WHISPER_LANGUAGE"))
    _deep_set(cfg, "wake_cooldown_sec", os.environ.get("WAKE_COOLDOWN_SEC"))
    _deep_set(cfg, "mic_sample_rate", os.environ.get("MIC_SAMPLE_RATE"))
    _deep_set(cfg, "mic_channels", os.environ.get("MIC_CHANNELS"))
    _deep_set(cfg, "pre_roll_ms", os.environ.get("PRE_ROLL_MS"))
    _deep_set(cfg, "utterance_max_sec", os.environ.get("UTTERANCE_MAX_SEC"))

    _deep_set(cfg, "memory_enable_chroma", os.environ.get("MEMORY_ENABLE_CHROMA"))
    _deep_set(cfg, "chroma_persist_dir", os.environ.get("CHROMA_PERSIST_DIR"))
    _deep_set(cfg, "chroma_collection", os.environ.get("CHROMA_COLLECTION"))
    _deep_set(cfg, "embedding_backend", os.environ.get("EMBEDDING_BACKEND"))
    _deep_set(cfg, "embedding_model", os.environ.get("EMBEDDING_MODEL"))
    _deep_set(cfg, "llm_max_tokens", os.environ.get("GLADOS_LLM_MAX_TOKENS"))
    _deep_set(cfg, "chat_history_max_messages", os.environ.get("GLADOS_CHAT_HISTORY_MAX"))
    _deep_set(cfg, "screen_capture_max_edge", os.environ.get("GLADOS_SCREEN_MAX_EDGE"))
    _deep_set(cfg, "vision_jpeg_max_edge", os.environ.get("GLADOS_VISION_JPEG_MAX_EDGE"))
    _deep_set(cfg, "vision_jpeg_quality", os.environ.get("GLADOS_VISION_JPEG_QUALITY"))
    _deep_set(cfg, "ollama_keep_alive", os.environ.get("OLLAMA_KEEP_ALIVE"))
    _deep_set(cfg, "input_mode", os.environ.get("GLADOS_INPUT_MODE"))
    _deep_set(cfg, "monitoring_enabled", os.environ.get("GLADOS_MONITORING_ENABLED"))
    _deep_set(cfg, "monitoring_interval_sec", os.environ.get("GLADOS_MONITORING_INTERVAL_SEC"))
    _deep_set(cfg, "monitoring_devices", os.environ.get("GLADOS_MONITORING_DEVICES"))
    _deep_set(cfg, "brain_dashboard_enabled", os.environ.get("BRAIN_DASHBOARD_ENABLED"))
    _deep_set(cfg, "brain_dashboard_host", os.environ.get("BRAIN_DASHBOARD_HOST"))
    _deep_set(cfg, "brain_dashboard_port", os.environ.get("BRAIN_DASHBOARD_PORT"))
    _deep_set(cfg, "brain_dashboard_url", os.environ.get("BRAIN_DASHBOARD_URL"))
    _deep_set(cfg, "brain_dashboard_token", os.environ.get("BRAIN_DASHBOARD_TOKEN"))
    _deep_set(cfg, "execution_mode", os.environ.get("GLADOS_EXECUTION_MODE"))
    _deep_set(cfg, "omni_brain_enabled", os.environ.get("GLADOS_OMNI_BRAIN_ENABLED"))
    _deep_set(cfg, "omni_brain_confidence_threshold", os.environ.get("GLADOS_OMNI_BRAIN_THRESHOLD"))
    _deep_set(cfg, "memory_top_k", os.environ.get("GLADOS_MEMORY_TOP_K"))
    _deep_set(cfg, "facility_brain_enabled", os.environ.get("GLADOS_FACILITY_BRAIN_ENABLED"))
    _deep_set(cfg, "facility_brain_config_path", os.environ.get("GLADOS_FACILITY_BRAIN_CONFIG"))
    _deep_set(cfg, "skills_brain_path", os.environ.get("GLADOS_SKILLS_BRAIN_PATH"))
    _deep_set(cfg, "skills_self_develop", os.environ.get("GLADOS_SKILLS_SELF_DEVELOP"))
    _deep_set(cfg, "skills_auto_learn_on_success", os.environ.get("GLADOS_SKILLS_AUTO_LEARN"))
    _deep_set(cfg, "skills_run_direct", os.environ.get("GLADOS_SKILLS_RUN_DIRECT"))
    _deep_set(cfg, "skills_conversational_learn", os.environ.get("GLADOS_SKILLS_CONVERSATIONAL_LEARN"))
    _deep_set(cfg, "skills_learn_until_success", os.environ.get("GLADOS_SKILLS_LEARN_UNTIL_SUCCESS"))
    _deep_set(cfg, "skills_learn_safety_cap", os.environ.get("GLADOS_SKILLS_LEARN_SAFETY_CAP"))
    _deep_set(cfg, "skills_learn_max_attempts", os.environ.get("GLADOS_SKILLS_LEARN_MAX_ATTEMPTS"))
    _deep_set(cfg, "gemini_api_key", os.environ.get("GEMINI_API_KEY"))
    _deep_set(cfg, "gemini_model", os.environ.get("GEMINI_MODEL"))
    _deep_set(cfg, "gemini_base_url", os.environ.get("GEMINI_BASE_URL"))
    _deep_set(cfg, "skills_learn_unlimited_attempts", os.environ.get("GLADOS_SKILLS_UNLIMITED"))
    _deep_set(cfg, "skills_learn_use_browser_ai", os.environ.get("GLADOS_SKILLS_BROWSER_AI"))
    _deep_set(cfg, "skills_learn_use_ai_council", os.environ.get("GLADOS_SKILLS_USE_AI_COUNCIL"))
    _deep_set(cfg, "skills_learn_reuse_browser", os.environ.get("GLADOS_SKILLS_REUSE_BROWSER"))
    _deep_set(cfg, "skills_learn_use_web", os.environ.get("GLADOS_SKILLS_LEARN_USE_WEB"))
    _deep_set(cfg, "skills_learn_open_browser", os.environ.get("GLADOS_SKILLS_LEARN_OPEN_BROWSER"))
    _deep_set(cfg, "llm_warmup_on_start", os.environ.get("GLADOS_LLM_WARMUP"))
    _deep_set(cfg, "conversational_skip_memory", os.environ.get("GLADOS_SKIP_MEMORY_ON_CHAT"))
    _deep_set(cfg, "memory_force_sandwich", os.environ.get("GLADOS_MEMORY_FORCE_SANDWICH"))
    _deep_set(cfg, "os_control_enabled", os.environ.get("GLADOS_OS_CONTROL_ENABLED"))
    _deep_set(cfg, "facility_context_in_chat", os.environ.get("GLADOS_FACILITY_CONTEXT"))
    _deep_set(cfg, "tts_async", os.environ.get("GLADOS_TTS_ASYNC"))
    _deep_set(cfg, "tts_enabled", os.environ.get("GLADOS_TTS_ENABLED"))

    for key in (
        "llm_max_tokens",
        "chat_history_max_messages",
        "screen_capture_max_edge",
        "vision_jpeg_max_edge",
        "vision_jpeg_quality",
        "mic_sample_rate",
        "mic_channels",
        "pre_roll_ms",
        "utterance_max_sec",
        "brain_dashboard_port",
        "memory_top_k",
        "memory_consolidation_min_fact_len",
        "omni_brain_confidence_threshold",
    ):
        if cfg.get(key) is not None:
            try:
                cfg[key] = int(cfg[key])
            except (TypeError, ValueError):
                pass

    if isinstance(cfg.get("brain_dashboard_enabled"), str):
        cfg["brain_dashboard_enabled"] = cfg["brain_dashboard_enabled"].strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    if cfg.get("wake_cooldown_sec") is not None:
        try:
            cfg["wake_cooldown_sec"] = float(cfg["wake_cooldown_sec"])
        except (TypeError, ValueError):
            cfg["wake_cooldown_sec"] = 1.5

    if isinstance(cfg.get("monitoring_enabled"), str):
        cfg["monitoring_enabled"] = cfg["monitoring_enabled"].strip().lower() in ("1", "true", "yes", "on")
    if isinstance(cfg.get("memory_enable_chroma"), str):
        cfg["memory_enable_chroma"] = cfg["memory_enable_chroma"].strip().lower() in ("1", "true", "yes", "on")
    if isinstance(cfg.get("omni_brain_enabled"), str):
        cfg["omni_brain_enabled"] = cfg["omni_brain_enabled"].strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    if isinstance(cfg.get("facility_brain_enabled"), str):
        cfg["facility_brain_enabled"] = cfg["facility_brain_enabled"].strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    for flag in (
        "llm_warmup_on_start",
        "conversational_skip_memory",
        "memory_consolidation_enabled",
        "memory_force_sandwich",
        "os_control_enabled",
        "facility_context_in_chat",
        "tts_async",
        "tts_enabled",
        "skills_self_develop",
        "skills_conversational_learn",
        "skills_learn_until_success",
        "skills_learn_unlimited_attempts",
        "skills_learn_use_web",
        "skills_learn_open_browser",
        "skills_learn_reuse_browser",
        "skills_learn_use_browser_ai",
        "skills_learn_skip_search_tabs",
        "skills_learn_browser_desktop_admin",
        "skills_learn_browser_desktop_first",
        "skills_learn_skip_browser_for_direct",
        "skills_learn_use_ai_council",
        "skills_learn_use_openai_advisor",
        "skills_auto_learn_on_success",
        "skills_run_direct",
    ):
        if isinstance(cfg.get(flag), str):
            cfg[flag] = cfg[flag].strip().lower() in ("1", "true", "yes", "on")
    for key in ("skills_learn_max_attempts", "skills_learn_safety_cap"):
        if cfg.get(key) is not None:
            try:
                cfg[key] = int(cfg[key])
            except (TypeError, ValueError):
                pass
    if cfg.get("skills_learn_max_attempts") is None:
        cfg["skills_learn_max_attempts"] = 0
    if cfg.get("skills_learn_safety_cap") is None:
        cfg["skills_learn_safety_cap"] = 0
    try:
        if cfg.get("omni_brain_confidence_threshold") is not None:
            cfg["omni_brain_confidence_threshold"] = float(cfg["omni_brain_confidence_threshold"])
    except (TypeError, ValueError):
        cfg["omni_brain_confidence_threshold"] = 72.0
    try:
        if cfg.get("monitoring_interval_sec") is not None:
            cfg["monitoring_interval_sec"] = int(cfg["monitoring_interval_sec"])
    except (TypeError, ValueError):
        cfg["monitoring_interval_sec"] = 300
    if isinstance(cfg.get("monitoring_devices"), str):
        # comma-separated
        cfg["monitoring_devices"] = [x.strip() for x in cfg["monitoring_devices"].split(",") if x.strip()]

    # Resolve relative paths from repo root
    for key in ("piper_model_path", "piper_output_wav", "chroma_persist_dir", "piper_exe_path"):
        p = cfg.get(key)
        if isinstance(p, str) and p and not os.path.isabs(p):
            cfg[key] = os.path.normpath(os.path.join(REPO_ROOT, p))

    return cfg
