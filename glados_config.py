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
LOCAL_CONFIG_PATH = os.path.join(REPO_ROOT, "configs", "glados.local.yaml")
DOTENV_PATH = os.path.join(REPO_ROOT, ".env")


def _load_dotenv(path: str = DOTENV_PATH) -> None:
    """Load KEY=VALUE lines into os.environ (only if not already set)."""
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


def _deep_set(target: Dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    target[key] = value


def load_config() -> Dict[str, Any]:
    """
    Defaults → configs/glados.yaml → configs/glados.local.yaml → .env → environment variables.
    """
    _load_dotenv()
    cfg: Dict[str, Any] = {
        "llm_provider": "hermes",
        "hermes_base_url": "http://127.0.0.1:18434/v1",
        "hermes_model": "Qwen3.6-35B-A3B-UD-Q4_K_M",
        "hermes_api_key": "",
        "nvidia_base_url": "https://integrate.api.nvidia.com/v1",
        "nvidia_model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
        "nvidia_prefer_hermes": True,
        "hermes_openrouter_model": "nousresearch/hermes-3-llama-3.1-70b",
        "nvidia_api_key": "",
        "nvidia_api_keys": [],
        "local_failover_base_url": "http://192.168.0.102:5000/v1",
        "local_failover_model": "deepseek-moe",
        "openrouter_base_url": "https://openrouter.ai/api/v1",
        "openrouter_api_key": "",
        "openrouter_app_title": "GLaDOS",
        "openrouter_http_referer": "",
        "openclaw_base_url": "http://127.0.0.1:18789/v1",
        "openclaw_model": "openclaw/default",
        "openclaw_config_path": "",
        "openclaw_api_key": "",
        "openclaw_vision_backend": "",
        "openclaw_embedding_backend": "",
        "ollama_base_url": "http://192.168.0.102:5000/v1",
        # Emergency local failover when NVIDIA keys are exhausted
        "ollama_fallback_enabled": True,
        "ollama_fallback_url": "http://192.168.0.102:5000/v1/chat/completions",
        "ollama_fallback_model": "deepseek-moe",
        "model_name": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
        "vision_model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
        "piper_model_path": os.path.join(REPO_ROOT, "glados.onnx"),
        "piper_output_wav": os.path.join(REPO_ROOT, "local_glados_response.wav"),
        "piper_exe_path": "",
        "tts_engine": "piper",
        "alltalk_url": "http://127.0.0.1:7851",
        "alltalk_voice": "frieren.wav",
        "alltalk_language": "en",
        "alltalk_timeout_sec": 60,
        "twilio_to_number": "+16896102968",
        "twilio_from_number": "",
        "twilio_account_sid": "",
        "twilio_auth_token": "",
        "twilio_voice_url": "",
        "twilio_public_ws_url": "",
        "nvidia_endpoint_models": [
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
        ],
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
        # Memory — Honcho (peer profiles + dialectic) primary; Chroma optional leftover
        "memory_enable_honcho": True,
        "honcho_url": "http://127.0.0.1:8000",
        "honcho_api_key": "",
        "honcho_workspace": "glados",
        "honcho_user_peer": "operator",
        "honcho_glados_peer": "glados",
        "honcho_computer_peer": "computer",
        "memory_enable_chroma": False,
        "chroma_persist_dir": os.path.join(REPO_ROOT, "chroma_db"),
        "chroma_collection": "glados_memories",
        "embedding_backend": "none",
        "embedding_model": "nomic-embed-text",
        "memory_consolidation_enabled": True,
        "memory_consolidation_min_fact_len": 10,
        # Inference speed
        "llm_max_tokens": 2048,
        "chat_history_max_messages": 24,
        "screen_capture_max_edge": 960,
        "vision_jpeg_max_edge": 896,
        "vision_jpeg_quality": 78,
        "ollama_keep_alive": "",
        # Input mode: voice | text | hybrid | daemon
        "input_mode": "daemon",
        # Background monitoring
        "monitoring_enabled": False,
        "monitoring_interval_sec": 300,
        "monitoring_devices": ["proxmox"],
        "watchdog_enabled": True,
        "watchdog_poll_sec": 5,
        "watchdog_cpu_spike_percent": 92,
        "watchdog_cpu_spike_sec": 20,
        "watchdog_network_drop_kbps": 0.5,
        "watchdog_docker_containers": [],
        "watchdog_govee_alert_device": "bedroom",
        "watchdog_critical_dial": True,
        "memory_prune_interval_hours": 6,
        "capability_registry_path": os.path.join(REPO_ROOT, "data", "capability_registry.json"),
        "glados_identity_path": os.path.join(REPO_ROOT, "data", "glados_identity.txt"),
        "phone_line_enabled": False,
        "phone_alert_provider": "inkbox",
        "inkbox_identity": "gladosai",
        "inkbox_auto_provision": False,
        "inkbox_public_url": "",
        "telegram_inbox_enabled": True,
        "telegram_allowed_users": "",
        "telegram_home_channel": "",
        "telegram_allow_all_users": False,
        "inkbox_task_inbox_enabled": True,
        "ntfy_server": "https://ntfy.sh",
        "ntfy_topic": "",
        "ntfy_token": "",
        "phone_server_port": 5050,
        # Brain dashboard (FastAPI + web UI)
        "brain_dashboard_enabled": True,
        "brain_dashboard_host": "0.0.0.0",
        "brain_dashboard_port": 8888,
        "brain_dashboard_url": "http://localhost:8888",
        "brain_dashboard_token": "",
        # Chat vs execution: text_only (default), auto (legacy: run code when model outputs it)
        "execution_mode": "text_only",
        "memory_top_k": 2,
        "memory_force_sandwich": False,
        "os_control_enabled": False,
        # Facility Brain (separate scan + decision file — configs/facility_brain.yaml)
        "facility_brain_enabled": True,
        "clear_chat_on_startup": True,
        "facility_brain_config_path": os.path.join(REPO_ROOT, "configs", "facility_brain.yaml"),
        "skills_brain_path": os.path.join(REPO_ROOT, "data", "glados_skills_brain.json"),
        "skills_self_develop": False,
        "swarm_routing_only": True,
        "skills_conversational_learn": True,
        "skills_learn_until_success": True,
        "skills_learn_unlimited_attempts": True,
        "skills_learn_safety_cap": 0,
        "skills_learn_max_attempts": 0,
        "skills_learn_use_web": True,
        "web_search_mode": "duckduckgo_scrape",
        "web_search_engine": "google",
        "preferred_browser": "chrome",
        "skills_learn_use_free_web": True,
        "web_scrape_timeout_sec": 12.0,
        "skills_learn_open_browser": False,
        "skills_learn_reuse_browser": False,
        "skills_learn_pause_sec": 2.0,
        "skills_learn_step_pause_sec": 6.0,
        "skills_learn_use_browser_ai": False,
        "browser_agent_enabled": True,
        "browser_agent_headless": False,
        "browser_agent_max_steps": 20,
        "browser_agent_slow_mo_ms": 80,
        "browser_agent_channel": "chrome",
        "browser_agent_profile_dir": os.path.join(REPO_ROOT, "data", "glados_playwright_profile"),
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

    if yaml is not None and os.path.isfile(LOCAL_CONFIG_PATH):
        try:
            with open(LOCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                local_cfg = yaml.safe_load(f)
            if isinstance(local_cfg, dict):
                cfg.update({k: v for k, v in local_cfg.items() if v is not None})
        except Exception:
            pass

    # Env overrides (same names you already use in places)
    _deep_set(cfg, "llm_provider", os.environ.get("LLM_PROVIDER"))
    _deep_set(cfg, "hermes_base_url", os.environ.get("HERMES_BASE_URL"))
    _deep_set(cfg, "hermes_model", os.environ.get("HERMES_MODEL"))
    _deep_set(cfg, "hermes_api_key", os.environ.get("HERMES_API_KEY"))
    _deep_set(cfg, "nvidia_base_url", os.environ.get("NVIDIA_BASE_URL"))
    _deep_set(cfg, "nvidia_model", os.environ.get("NVIDIA_MODEL"))
    _deep_set(cfg, "nvidia_api_key", os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVIDIA_API_KEY_1"))
    _deep_set(cfg, "local_failover_base_url", os.environ.get("LOCAL_FAILOVER_BASE_URL"))
    _deep_set(cfg, "local_failover_model", os.environ.get("LOCAL_FAILOVER_MODEL"))
    _deep_set(cfg, "openrouter_base_url", os.environ.get("OPENROUTER_BASE_URL"))
    _deep_set(cfg, "openrouter_api_key", os.environ.get("OPENROUTER_API_KEY"))
    _deep_set(cfg, "openclaw_base_url", os.environ.get("OPENCLAW_BASE_URL"))
    _deep_set(cfg, "openclaw_model", os.environ.get("OPENCLAW_MODEL"))
    _deep_set(cfg, "openclaw_api_key", os.environ.get("OPENCLAW_GATEWAY_TOKEN") or os.environ.get("OPENCLAW_API_KEY"))
    _deep_set(cfg, "openclaw_vision_backend", os.environ.get("OPENCLAW_VISION_BACKEND"))
    _deep_set(cfg, "openclaw_embedding_backend", os.environ.get("OPENCLAW_EMBEDDING_BACKEND"))
    _deep_set(cfg, "ollama_base_url", os.environ.get("OLLAMA_BASE_URL"))
    provider_now = str(cfg.get("llm_provider") or "").strip().lower()
    if provider_now in ("hermes", "llamacpp", "llama.cpp", "llama-cpp", "hermes_local"):
        _deep_set(cfg, "model_name", os.environ.get("MODEL_NAME") or os.environ.get("HERMES_MODEL"))
        _deep_set(cfg, "vision_model", os.environ.get("VISION_MODEL") or os.environ.get("HERMES_MODEL"))
    else:
        _deep_set(cfg, "model_name", os.environ.get("MODEL_NAME") or os.environ.get("NVIDIA_MODEL"))
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

    _deep_set(cfg, "memory_enable_honcho", os.environ.get("MEMORY_ENABLE_HONCHO"))
    _deep_set(cfg, "honcho_url", os.environ.get("HONCHO_URL") or os.environ.get("HONCHO_BASE_URL"))
    _deep_set(cfg, "honcho_api_key", os.environ.get("HONCHO_API_KEY"))
    _deep_set(cfg, "honcho_workspace", os.environ.get("HONCHO_WORKSPACE"))
    _deep_set(cfg, "nvidia_prefer_hermes", os.environ.get("NVIDIA_PREFER_HERMES"))
    _deep_set(cfg, "hermes_openrouter_model", os.environ.get("HERMES_OPENROUTER_MODEL"))
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
    _deep_set(cfg, "watchdog_enabled", os.environ.get("GLADOS_WATCHDOG_ENABLED"))
    _deep_set(cfg, "phone_line_enabled", os.environ.get("GLADOS_PHONE_LINE_ENABLED"))
    _deep_set(cfg, "phone_alert_provider", os.environ.get("PHONE_ALERT_PROVIDER"))
    _deep_set(cfg, "inkbox_identity", os.environ.get("INKBOX_IDENTITY"))
    _deep_set(cfg, "inkbox_to_number", os.environ.get("INKBOX_TO_NUMBER"))
    _deep_set(cfg, "inkbox_auto_provision", os.environ.get("INKBOX_AUTO_PROVISION"))
    _deep_set(
        cfg,
        "inkbox_public_url",
        os.environ.get("INKBOX_PUBLIC_URL") or os.environ.get("GLADOS_PUBLIC_URL"),
    )
    _deep_set(cfg, "ntfy_topic", os.environ.get("NTFY_TOPIC"))
    _deep_set(cfg, "ntfy_server", os.environ.get("NTFY_SERVER"))
    _deep_set(cfg, "ntfy_token", os.environ.get("NTFY_TOKEN"))
    _deep_set(cfg, "telegram_bot_token", os.environ.get("TELEGRAM_BOT_TOKEN"))
    _deep_set(cfg, "telegram_allowed_users", os.environ.get("TELEGRAM_ALLOWED_USERS"))
    _deep_set(cfg, "telegram_home_channel", os.environ.get("TELEGRAM_HOME_CHANNEL"))
    _deep_set(cfg, "telegram_allow_all_users", os.environ.get("TELEGRAM_ALLOW_ALL_USERS"))
    _deep_set(cfg, "telegram_inbox_enabled", os.environ.get("TELEGRAM_INBOX_ENABLED"))
    _deep_set(cfg, "inkbox_task_inbox_enabled", os.environ.get("INKBOX_TASK_INBOX_ENABLED"))
    _deep_set(cfg, "phone_server_port", os.environ.get("PHONE_SERVER_PORT"))
    _deep_set(cfg, "capability_registry_path", os.environ.get("GLADOS_CAPABILITY_REGISTRY"))
    _deep_set(cfg, "glados_identity_path", os.environ.get("GLADOS_IDENTITY_PATH"))
    _deep_set(cfg, "brain_dashboard_enabled", os.environ.get("BRAIN_DASHBOARD_ENABLED"))
    _deep_set(cfg, "brain_dashboard_host", os.environ.get("BRAIN_DASHBOARD_HOST"))
    _deep_set(cfg, "brain_dashboard_port", os.environ.get("BRAIN_DASHBOARD_PORT"))
    _deep_set(cfg, "brain_dashboard_url", os.environ.get("BRAIN_DASHBOARD_URL"))
    _deep_set(cfg, "brain_dashboard_token", os.environ.get("BRAIN_DASHBOARD_TOKEN"))
    _deep_set(cfg, "execution_mode", os.environ.get("GLADOS_EXECUTION_MODE"))
    _deep_set(cfg, "memory_top_k", os.environ.get("GLADOS_MEMORY_TOP_K"))
    _deep_set(cfg, "facility_brain_enabled", os.environ.get("GLADOS_FACILITY_BRAIN_ENABLED"))
    _deep_set(cfg, "facility_brain_config_path", os.environ.get("GLADOS_FACILITY_BRAIN_CONFIG"))
    _deep_set(cfg, "skills_brain_path", os.environ.get("GLADOS_SKILLS_BRAIN_PATH"))
    _deep_set(cfg, "skills_self_develop", os.environ.get("GLADOS_SKILLS_SELF_DEVELOP"))
    _deep_set(cfg, "swarm_routing_only", os.environ.get("GLADOS_SWARM_ROUTING_ONLY"))
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
    _deep_set(cfg, "browser_agent_enabled", os.environ.get("GLADOS_BROWSER_AGENT_ENABLED"))
    _deep_set(cfg, "browser_agent_headless", os.environ.get("GLADOS_BROWSER_AGENT_HEADLESS"))
    _deep_set(cfg, "browser_agent_max_steps", os.environ.get("GLADOS_BROWSER_AGENT_MAX_STEPS"))
    _deep_set(cfg, "skills_learn_use_ai_council", os.environ.get("GLADOS_SKILLS_USE_AI_COUNCIL"))
    _deep_set(cfg, "skills_learn_reuse_browser", os.environ.get("GLADOS_SKILLS_REUSE_BROWSER"))
    _deep_set(cfg, "skills_learn_use_web", os.environ.get("GLADOS_SKILLS_LEARN_USE_WEB"))
    _deep_set(cfg, "skills_learn_open_browser", os.environ.get("GLADOS_SKILLS_LEARN_OPEN_BROWSER"))
    _deep_set(cfg, "llm_warmup_on_start", os.environ.get("GLADOS_LLM_WARMUP"))
    _deep_set(cfg, "conversational_skip_memory", os.environ.get("GLADOS_SKIP_MEMORY_ON_CHAT"))
    _deep_set(cfg, "memory_force_sandwich", os.environ.get("GLADOS_MEMORY_FORCE_SANDWICH"))
    _deep_set(cfg, "os_control_enabled", os.environ.get("GLADOS_OS_CONTROL_ENABLED"))
    _deep_set(cfg, "facility_context_in_chat", os.environ.get("GLADOS_FACILITY_CONTEXT"))
    _deep_set(cfg, "tts_engine", os.environ.get("GLADOS_TTS_ENGINE"))
    _deep_set(cfg, "twilio_to_number", os.environ.get("TWILIO_TO_NUMBER"))
    _deep_set(cfg, "twilio_from_number", os.environ.get("TWILIO_FROM_NUMBER"))
    _deep_set(cfg, "twilio_account_sid", os.environ.get("TWILIO_ACCOUNT_SID"))
    _deep_set(cfg, "twilio_auth_token", os.environ.get("TWILIO_AUTH_TOKEN"))
    _deep_set(cfg, "twilio_voice_url", os.environ.get("TWILIO_VOICE_URL"))
    _deep_set(cfg, "twilio_public_ws_url", os.environ.get("TWILIO_PUBLIC_WS_URL"))
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
    if isinstance(cfg.get("watchdog_enabled"), str):
        cfg["watchdog_enabled"] = cfg["watchdog_enabled"].strip().lower() in ("1", "true", "yes", "on")
    if isinstance(cfg.get("phone_line_enabled"), str):
        cfg["phone_line_enabled"] = cfg["phone_line_enabled"].strip().lower() in ("1", "true", "yes", "on")
    if isinstance(cfg.get("watchdog_critical_dial"), str):
        cfg["watchdog_critical_dial"] = cfg["watchdog_critical_dial"].strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    if isinstance(cfg.get("memory_enable_honcho"), str):
        cfg["memory_enable_honcho"] = cfg["memory_enable_honcho"].strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    if isinstance(cfg.get("nvidia_prefer_hermes"), str):
        cfg["nvidia_prefer_hermes"] = cfg["nvidia_prefer_hermes"].strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    if isinstance(cfg.get("memory_enable_chroma"), str):
        cfg["memory_enable_chroma"] = cfg["memory_enable_chroma"].strip().lower() in ("1", "true", "yes", "on")
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
