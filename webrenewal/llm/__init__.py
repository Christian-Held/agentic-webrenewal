"""Unified client abstractions for interacting with multiple LLM providers."""

from __future__ import annotations

import abc
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, MutableMapping, Optional

import httpx


class LLMError(RuntimeError):
    """Raised when an LLM provider returns an unexpected payload."""


@dataclass
class LLMResponse:
    """Normalised response returned by an LLM provider."""

    text: str
    data: Any | None = None
    raw: Any | None = None


Message = MutableMapping[str, Any]


def _normalise_messages(messages: Iterable[Message]) -> List[Dict[str, Any]]:
    """Coerce arbitrary message payloads into ``{"role", "content"}`` mappings."""

    normalised: List[Dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = message.get("content", "")
        if isinstance(content, (dict, list)):
            serialised = json.dumps(content, ensure_ascii=False)
        else:
            serialised = str(content)
        normalised.append({"role": role, "content": serialised})
    return normalised


class BaseLLMClient(abc.ABC):
    """Abstract base class for all concrete LLM provider implementations."""

    async def complete_text(
        self,
        messages: Iterable[Message],
        *,
        model: str,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Return the textual response for the given prompt ``messages``."""

        return await self._complete(
            messages, model=model, temperature=temperature, response_format=None
        )

    async def complete_json(
        self,
        messages: Iterable[Message],
        *,
        model: str,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Return the parsed JSON response for ``messages`` when supported."""

        response = await self._complete(
            messages,
            model=model,
            temperature=temperature,
            response_format="json_object",
        )
        try:
            parsed = json.loads(response.text)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise LLMError("LLM did not return valid JSON payload") from exc
        return LLMResponse(text=response.text, data=parsed, raw=response.raw)

    @abc.abstractmethod
    async def _complete(
        self,
        messages: Iterable[Message],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> LLMResponse:
        """Provider specific implementation returning a normalised response."""


class OpenAIClient(BaseLLMClient):
    """Adapter around the official OpenAI SDK."""

    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        from openai import AsyncOpenAI  # import lazily to keep optional dependency local

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)

    async def _complete(
        self,
        messages: Iterable[Message],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> LLMResponse:
        request: Dict[str, Any] = {
            "model": model,
            "input": _normalise_messages(messages),
        }
        if temperature is not None:
            request["temperature"] = temperature
        if response_format == "json_object":
            request["response_format"] = {"type": "json_object"}

        try:
            response = await self._client.responses.create(**request)
        except TypeError as exc:  # pragma: no cover - compatibility with older SDKs
            if response_format and "response_format" in str(exc):
                request.pop("response_format", None)
                response = await self._client.responses.create(**request)
            else:
                raise

        text = self._extract_text(response)
        if not text:
            raise LLMError("OpenAI returned an empty response")
        return LLMResponse(text=text, raw=response)

    def _extract_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        parts: List[str] = []
        for item in getattr(response, "output", []) or []:
            for content_item in getattr(item, "content", []) or []:
                text_value = getattr(content_item, "text", None)
                if isinstance(text_value, str) and text_value.strip():
                    parts.append(text_value)
                    continue
                json_value = getattr(content_item, "json", None)
                if isinstance(json_value, dict):
                    parts.append(json.dumps(json_value))
        if parts:
            return "".join(parts)
        return ""


class OllamaClient(BaseLLMClient):
    """HTTP based adapter for interacting with a local Ollama server."""

    def __init__(self, *, host: str, timeout: float = 60.0) -> None:
        self._host = host.rstrip("/")
        self._timeout = timeout

    async def _complete(
        self,
        messages: Iterable[Message],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> LLMResponse:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": _normalise_messages(messages),
            "stream": False,
        }
        options: Dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if response_format == "json_object":
            options["format"] = "json"
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(
            base_url=self._host, timeout=self._timeout
        ) as http:
            response = await http.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        message = data.get("message", {}) if isinstance(data, dict) else {}
        content = message.get("content", "")
        if isinstance(content, list):
            text = "".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            )
        else:
            text = str(content)
        if not text:
            raise LLMError("Ollama returned an empty response")
        return LLMResponse(text=text, raw=data)


class AnthropicClient(BaseLLMClient):
    """Adapter around the Anthropic SDK."""

    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        from anthropic import AsyncAnthropic  # local import to keep dependency optional

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncAnthropic(**client_kwargs)

    async def _complete(
        self,
        messages: Iterable[Message],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> LLMResponse:
        normalised = _normalise_messages(messages)
        system_messages = [m["content"] for m in normalised if m["role"] == "system"]
        user_messages = [m for m in normalised if m["role"] != "system"]

        request: Dict[str, Any] = {
            "model": model,
            "messages": user_messages,
        }
        if system_messages:
            request["system"] = "\n\n".join(system_messages)
        if temperature is not None:
            request["temperature"] = temperature
        if response_format == "json_object":
            request["response_format"] = {"type": "json_object"}

        response = await self._client.messages.create(**request)

        parts: List[str] = []
        for item in getattr(response, "content", []) or []:
            text_value = getattr(item, "text", None)
            if isinstance(text_value, str) and text_value.strip():
                parts.append(text_value)
        if not parts:
            raise LLMError("Anthropic returned an empty response")
        return LLMResponse(text="".join(parts), raw=response)


def create_llm_client(
    provider: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    host: str | None = None,
) -> BaseLLMClient | None:
    """Instantiate a client for the requested provider if credentials are present."""

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

    raise ValueError(f"Unsupported LLM provider: {provider}")


def default_model_for(provider: str) -> str:
    """Return the default model name for the given provider."""

    provider_normalised = provider.lower()
    if provider_normalised == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if provider_normalised == "ollama":
        return os.getenv("OLLAMA_MODEL", "llama3.1")
    if provider_normalised == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
    raise ValueError(f"Unsupported LLM provider: {provider}")


__all__ = [
    "AnthropicClient",
    "BaseLLMClient",
    "LLMError",
    "LLMResponse",
    "OllamaClient",
    "OpenAIClient",
    "create_llm_client",
    "default_model_for",
]

