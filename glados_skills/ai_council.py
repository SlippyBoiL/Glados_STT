from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


@dataclass
class Advisor:
    name: str
    client: Any = None
    model: str = ""
    browser_site: str = field(default="")


def build_advisors(cfg: Dict[str, Any], primary_client: Any, primary_model: str) -> List[Advisor]:
    """Primary LLM (OpenClaw/Ollama) for codegen; browser Gemini/Perplexity for research (no API keys)."""
    advisors: List[Advisor] = []

    if primary_client and primary_model:
        from glados_llm import is_openclaw

        name = "openclaw" if is_openclaw(cfg) else "ollama"
        advisors.append(Advisor(name, primary_client, primary_model))

    use_browser = bool(cfg.get("skills_learn_use_browser_ai", True))
    use_api = bool(cfg.get("skills_learn_use_ai_council", False))

    if use_browser:
        from glados_skills.browser_ai import list_browser_sites

        for site in list_browser_sites(cfg):
            advisors.append(Advisor(name=site, browser_site=site))

    if not use_api:
        return advisors

    gemini_key = (
        os.environ.get("GEMINI_API_KEY", "").strip()
        or str(cfg.get("gemini_api_key") or "").strip()
    )
    gemini_model = str(cfg.get("gemini_model") or "gemini-2.0-flash")
    gemini_base = str(
        cfg.get("gemini_base_url")
        or "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    if gemini_key and OpenAI is not None:
        try:
            advisors.append(
                Advisor(
                    "gemini-api",
                    OpenAI(api_key=gemini_key, base_url=gemini_base),
                    gemini_model,
                )
            )
        except Exception:
            pass

    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    openai_model = str(cfg.get("openai_advisor_model") or "gpt-4o-mini")
    if bool(cfg.get("skills_learn_use_openai_advisor", False)) and openai_key and OpenAI is not None:
        try:
            advisors.append(Advisor("openai", OpenAI(api_key=openai_key), openai_model))
        except Exception:
            pass

    for entry in cfg.get("skills_learn_extra_advisors") or []:
        if not isinstance(entry, dict) or not entry.get("enabled", True):
            continue
        name = str(entry.get("name") or "advisor")
        base = str(entry.get("base_url") or "").strip()
        model = str(entry.get("model") or "").strip()
        key_env = str(entry.get("api_key_env") or "ADVISOR_API_KEY")
        api_key = os.environ.get(key_env, "").strip() or str(entry.get("api_key") or "")
        if base and model and api_key and OpenAI is not None:
            try:
                advisors.append(Advisor(name, OpenAI(api_key=api_key, base_url=base), model))
            except Exception:
                pass

    return advisors


def _advisor_prompt(
    user_input: str,
    intent_text: str,
    context: str,
    prior_error: str,
) -> str:
    prompt = (
        "You are helping GLaDOS learn a Python protocol for a Windows PC.\n"
        f"USER TASK: {user_input}\n\n"
        f"INTERPRETED INTENT:\n{intent_text}\n\n"
        f"PC / RESEARCH CONTEXT:\n{context[:3000]}\n\n"
    )
    if prior_error:
        prompt += f"LAST FAILURE:\n{prior_error[:1500]}\n\n"
    prompt += (
        "Explain clearly: (1) what the user wants, (2) step-by-step approach, "
        "(3) Python/stdlib technique, (4) pitfalls to avoid. "
        "Plain text only, under 500 words."
    )
    return prompt


def council_consult(
    advisor: Advisor,
    user_input: str,
    intent_text: str,
    context: str,
    prior_error: str,
    completion_kwargs: Optional[Dict[str, Any]] = None,
    cfg: Optional[Dict[str, Any]] = None,
    think_fn: Optional[Any] = None,
) -> str:
    """Ask an advisor — browser (Gemini/Perplexity) or optional API model."""
    prompt = _advisor_prompt(user_input, intent_text, context, prior_error)

    if advisor.browser_site:
        try:
            from glados_skills.browser_ai import consult_in_browser

            return consult_in_browser(
                advisor.browser_site,
                prompt,
                cfg or {},
                think_fn=think_fn,
            )
        except Exception as e:
            return f"Browser advisor {advisor.name} unavailable: {e}"

    if not advisor.client or not advisor.model:
        return f"Advisor {advisor.name} not configured."

    kw = dict(completion_kwargs or {})
    try:
        r = advisor.client.chat.completions.create(
            model=advisor.model,
            messages=[{"role": "user", "content": prompt}],
            **kw,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        return f"Advisor {advisor.name} unavailable: {e}"
