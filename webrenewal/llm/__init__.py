"""Public interface for the LLM integration layer."""

from __future__ import annotations

import os
from typing import Dict

from .clients import (
    AnthropicClient,
    DeepSeekClient,
    GeminiClient,
    GroqClient,
    LLMClient,
    OllamaClient,
    OpenAIClient,
)
from .models import JSONCompletion, JSONPayload, Message, TextCompletion
from .service import JSONValidationError, LLMService
from .tracer import LLMTracer, get_tracer

__all__ = [
    "AnthropicClient",
    "DeepSeekClient",
    "GeminiClient",
    "GroqClient",
    "JSONCompletion",
    "JSONPayload",
    "JSONValidationError",
    "LLMClient",
    "LLMService",
    "LLMTracer",
    "Message",
    "OllamaClient",
    "OpenAIClient",
    "TextCompletion",
    "create_llm_client",
    "create_llm_service",
    "default_model_for",
    "get_tracer",
    "list_available_providers",
]


_PROVIDER_DEFAULTS: Dict[str, Dict[str, str]] = {
    "openai": {"env_key": "OPENAI_API_KEY", "model": "gpt-4.1-mini"},
    "ollama": {"env_key": "OLLAMA_HOST", "model": "llama3.2"},
    "anthropic": {"env_key": "ANTHROPIC_API_KEY", "model": "claude-3-7-sonnet-latest"},
    "gemini": {"env_key": "GEMINI_API_KEY", "model": "gemini-1.5-pro"},
    "deepseek": {"env_key": "DEEPSEEK_API_KEY", "model": "deepseek-chat"},
    "groq": {"env_key": "GROQ_API_KEY", "model": "llama3-70b-8192"},
}


def create_llm_client(
    provider: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    host: str | None = None,
) -> LLMClient | None:
    provider_normalised = provider.lower()

    if provider_normalised == "openai":
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL")
        if not resolved_key:
            return None
        return OpenAIClient(api_key=resolved_key, base_url=resolved_base_url)

    if provider_normalised == "ollama":
        resolved_host = host or base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        return OllamaClient(host=resolved_host)

    if provider_normalised == "anthropic":
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        resolved_base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        if not resolved_key:
            return None
        return AnthropicClient(api_key=resolved_key, base_url=resolved_base_url)

    if provider_normalised == "gemini":
        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        resolved_base_url = base_url or os.getenv("GEMINI_BASE_URL")
        if not resolved_key:
            return None
        return GeminiClient(api_key=resolved_key, base_url=resolved_base_url)

    if provider_normalised == "deepseek":
        resolved_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        resolved_base_url = base_url or os.getenv("DEEPSEEK_BASE_URL")
        if not resolved_key:
            return None
        return DeepSeekClient(api_key=resolved_key, base_url=resolved_base_url)

    if provider_normalised == "groq":
        resolved_key = api_key or os.getenv("GROQ_API_KEY")
        resolved_base_url = base_url or os.getenv("GROQ_BASE_URL")
        if not resolved_key:
            return None
        return GroqClient(api_key=resolved_key, base_url=resolved_base_url)

    raise ValueError(f"Unsupported LLM provider: {provider}")


def default_model_for(provider: str) -> str:
    provider_normalised = provider.lower()
    defaults = _PROVIDER_DEFAULTS.get(provider_normalised)
    if not defaults:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    env_var = f"{provider_normalised.upper()}_MODEL"
    return os.getenv(env_var, defaults["model"])


def create_llm_service(
    provider: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    host: str | None = None,
    tracer: LLMTracer | None = None,
) -> LLMService | None:
    client = create_llm_client(provider, api_key=api_key, base_url=base_url, host=host)
    if client is None:
        return None
    return LLMService(provider=provider, client=client, tracer=tracer)


def list_available_providers() -> Dict[str, Dict[str, str]]:
    """Return metadata about known providers and defaults."""

    catalog: Dict[str, Dict[str, str]] = {}
    for name, defaults in _PROVIDER_DEFAULTS.items():
        catalog[name] = {
            "default_model": default_model_for(name),
            "credential_env": defaults["env_key"],
        }
    return catalog

