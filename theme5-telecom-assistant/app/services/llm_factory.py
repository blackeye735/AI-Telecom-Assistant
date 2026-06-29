"""llm_factory.py — creates and caches LLM instances.

Supported providers (set LLM_PROVIDER in .env):
  openai          — OpenAI API  (OPENAI_API_KEY required)
  anthropic       — Anthropic API  (ANTHROPIC_API_KEY required)
  openrouter      — OpenRouter unified LLM API  (OPENROUTER_API_KEY required)
                    Access 200+ models via one API; recommended for production
  github          — GitHub Models via OpenAI-compatible endpoint
                    (GITHUB_TOKEN required; works through most corporate proxies)
  ollama          — Local Ollama server  (no API key; OLLAMA_MODEL optional)

For corporate networks with TLS inspection, set SSL_VERIFY=false in .env.
"""

import warnings
from functools import lru_cache

import httpx

from app.services.config import (
    LLM_MAX_TOKENS,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    SSL_VERIFY,
)
from app.utils.logger import setup_logger

log = setup_logger("llm_factory")

# GitHub Models endpoint — OpenAI-compatible, uses a GitHub PAT
_GITHUB_MODELS_BASE = "https://models.inference.ai.azure.com"

# OpenRouter endpoint — unified API for 200+ models
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _http_client(verify: bool = SSL_VERIFY) -> httpx.Client:
    """Return an httpx.Client with the correct SSL policy."""
    if not verify:
        warnings.warn(
            "SSL_VERIFY=false — TLS verification disabled (corporate proxy mode).",
            stacklevel=3,
        )
    return httpx.Client(verify=verify)


@lru_cache(maxsize=1)
def get_llm():
    """Return a cached LangChain chat LLM based on LLM_PROVIDER env var."""
    import os
    provider = LLM_PROVIDER.lower()
    log.info(f"LLM provider: {provider} | ssl_verify={SSL_VERIFY}")

    # ── OpenRouter (unified API for 200+ models, production-ready) ──────────────
    if provider == "openrouter":
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.startswith("your-"):
            raise ValueError(
                "OPENROUTER_API_KEY is missing or still a placeholder. "
                "Get a free key at https://openrouter.ai/keys and add it to .env"
            )
        from langchain_openai import ChatOpenAI
        log.info(f"LLM → OpenRouter / {OPENROUTER_MODEL}")
        return ChatOpenAI(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url=_OPENROUTER_BASE,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            http_client=_http_client(),
            default_headers={
                "HTTP-Referer": "https://telecom-assistant.local",
                "X-Title": "Telecom Knowledge Assistant",
            }
        )

    # ── GitHub Models (OpenAI-compatible, recommended for corporate networks) ──
    if provider == "github":
        github_token = os.getenv("GITHUB_TOKEN", "")
        if not github_token:
            raise ValueError(
                "GITHUB_TOKEN is not set. "
                "Create a token at https://github.com/settings/tokens "
                "(no scopes needed) and add it to .env as GITHUB_TOKEN=ghp_..."
            )
        github_model = os.getenv("GITHUB_MODEL", "gpt-4o-mini")
        from langchain_openai import ChatOpenAI
        log.info(f"LLM → GitHub Models / {github_model}")
        return ChatOpenAI(
            model=github_model,
            api_key=github_token,
            base_url=_GITHUB_MODELS_BASE,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            http_client=_http_client(),
        )

    # ── Ollama (fully local, no API key, no network needed) ───────────────────
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        log.info(f"LLM → Ollama / {ollama_model} @ {ollama_url}")
        return ChatOllama(
            model=ollama_model,
            base_url=ollama_url,
            temperature=LLM_TEMPERATURE,
        )

    # ── OpenAI ───────────────────────────────────────────────────────────
    if provider == "openai":
        if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("your-") or "abcdef" in OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is missing or still a placeholder. "
                "Set a real key in .env, or switch to LLM_PROVIDER=github / ollama."
            )
        from langchain_openai import ChatOpenAI
        log.info(f"LLM → OpenAI / {OPENAI_MODEL}")
        return ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            http_client=_http_client(),
        )

    # ── Anthropic ────────────────────────────────────────────────────────
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.startswith("your-"):
        raise ValueError(
            "ANTHROPIC_API_KEY is missing or still a placeholder. "
            "Set a real key in .env, or switch to LLM_PROVIDER=github / ollama."
        )
    from langchain_anthropic import ChatAnthropic
    log.info(f"LLM → Anthropic / {ANTHROPIC_MODEL}")
    return ChatAnthropic(
        model=ANTHROPIC_MODEL,
        api_key=ANTHROPIC_API_KEY,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        http_client=_http_client(),
    )
