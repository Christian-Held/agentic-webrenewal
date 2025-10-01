"""Provider specific client implementations for LLM interactions."""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Sequence

import httpx

from .models import Message, TokenUsage


MessagePayload = MutableMapping[str, Any]


def _normalise_messages(messages: Iterable[MessagePayload]) -> List[Dict[str, Any]]:
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


@dataclass
class ProviderResponse:
    """Normalised response from a provider."""

    text: str
    raw: Any | None = None
    usage: TokenUsage | None = None


class LLMClient(abc.ABC):
    """Interface for provider specific clients."""

    @property
    def supports_json_mode(self) -> bool:
        """Return whether the client can request native JSON mode."""

        return False

    async def complete(
        self,
        messages: Sequence[MessagePayload],
        *,
        model: str,
        temperature: float | None = None,
        response_format: str | None = None,
    ) -> ProviderResponse:
        return await self._complete(
            messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
        )

    @abc.abstractmethod
    async def _complete(
        self,
        messages: Sequence[MessagePayload],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """Adapter around the official OpenAI SDK."""

    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        from openai import AsyncOpenAI

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)

    async def _complete(
        self,
        messages: Sequence[MessagePayload],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
        request: Dict[str, Any] = {"model": model, "input": _normalise_messages(messages)}
        if temperature is not None:
            request["temperature"] = temperature
        if response_format == "json_object":
            request["response_format"] = {"type": "json_object"}

        response = await self._client.responses.create(**request)
        text = getattr(response, "output_text", None)
        if not text:
            parts: List[str] = []
            for item in getattr(response, "output", []) or []:
                for content_item in getattr(item, "content", []) or []:
                    text_value = getattr(content_item, "text", None)
                    if isinstance(text_value, str) and text_value.strip():
                        parts.append(text_value)
                    json_value = getattr(content_item, "json", None)
                    if isinstance(json_value, dict):
                        parts.append(json.dumps(json_value))
            text = "".join(parts)

        if not text:
            raise ValueError("OpenAI returned an empty response")

        usage = None
        usage_obj = getattr(response, "usage", None)
        if usage_obj is not None:
            usage = TokenUsage(
                prompt_tokens=getattr(usage_obj, "prompt_tokens", None),
                completion_tokens=getattr(usage_obj, "completion_tokens", None),
                total_tokens=getattr(usage_obj, "total_tokens", None),
            )

        return ProviderResponse(text=text, raw=response, usage=usage)


class AnthropicClient(LLMClient):
    """Adapter around Anthropic's SDK."""

    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        from anthropic import AsyncAnthropic

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncAnthropic(**client_kwargs)

    async def _complete(
        self,
        messages: Sequence[MessagePayload],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
        normalised = _normalise_messages(messages)
        system_messages = [m["content"] for m in normalised if m["role"] == "system"]
        user_messages = [m for m in normalised if m["role"] != "system"]

        request: Dict[str, Any] = {"model": model, "messages": user_messages}
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
        text = "".join(parts)
        if not text:
            raise ValueError("Anthropic returned an empty response")

        usage = None
        usage_obj = getattr(response, "usage", None)
        if usage_obj is not None:
            usage = TokenUsage(
                prompt_tokens=getattr(usage_obj, "input_tokens", None),
                completion_tokens=getattr(usage_obj, "output_tokens", None),
                total_tokens=getattr(usage_obj, "total_tokens", None),
            )

        return ProviderResponse(text=text, raw=response, usage=usage)


class OllamaClient(LLMClient):
    """HTTP adapter for Ollama."""

    def __init__(self, *, host: str, timeout: float = 60.0) -> None:
        self._host = host.rstrip("/")
        self._timeout = timeout

    async def _complete(
        self,
        messages: Sequence[MessagePayload],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
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

        async with httpx.AsyncClient(base_url=self._host, timeout=self._timeout) as http:
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
            raise ValueError("Ollama returned an empty response")

        eval_count = data.get("eval_count") if isinstance(data, dict) else None
        usage = None
        if isinstance(eval_count, int):
            usage = TokenUsage(completion_tokens=eval_count)

        return ProviderResponse(text=text, raw=data, usage=usage)


class GeminiClient(LLMClient):
    """HTTP client for Google Gemini."""

    def __init__(self, *, api_key: str, base_url: str | None = None, timeout: float = 60.0) -> None:
        self._api_key = api_key
        self._base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self._timeout = timeout

    async def _complete(
        self,
        messages: Sequence[MessagePayload],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
        contents = [
            {"role": message.get("role", "user"), "parts": [{"text": str(message.get("content", ""))}]}
            for message in messages
        ]

        body: Dict[str, Any] = {"contents": contents}
        if temperature is not None:
            body.setdefault("generationConfig", {})["temperature"] = temperature
        if response_format == "json_object":
            body.setdefault("generationConfig", {})["responseMimeType"] = "application/json"

        url = f"{self._base_url}/models/{model}:generateContent"
        params = {"key": self._api_key}

        async with httpx.AsyncClient(timeout=self._timeout) as http:
            response = await http.post(url, params=params, json=body)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") if isinstance(data, dict) else None
        if not candidates:
            raise ValueError("Gemini returned an empty response")
        first = candidates[0] or {}
        content = first.get("content", {})
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
        if not text:
            raise ValueError("Gemini returned an empty response")

        usage = None
        usage_data = data.get("usageMetadata") if isinstance(data, dict) else None
        if isinstance(usage_data, dict):
            usage = TokenUsage(
                prompt_tokens=usage_data.get("promptTokenCount"),
                completion_tokens=usage_data.get("candidatesTokenCount"),
                total_tokens=usage_data.get("totalTokenCount"),
            )

        return ProviderResponse(text=text, raw=data, usage=usage)


class OpenAICompatibleClient(LLMClient):
    """Generic HTTP client for OpenAI compatible chat APIs."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 60.0,
        headers: Optional[Dict[str, str]] = None,
        supports_json_mode: bool = True,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._headers = headers or {}
        self._supports_json_mode = supports_json_mode

    @property
    def supports_json_mode(self) -> bool:
        return self._supports_json_mode

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        headers.update(self._headers)
        return headers

    async def _complete(
        self,
        messages: Sequence[MessagePayload],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": _normalise_messages(messages),
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self._timeout) as http:
            response = await http.post(
                f"{self._base_url}/chat/completions",
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            raise ValueError("Provider returned an empty response")
        message = choices[0].get("message", {})
        text = message.get("content")
        if not text and isinstance(message.get("tool_calls"), list):
            text = json.dumps(message["tool_calls"])  # fallback when JSON mode returns tool calls
        if not text:
            raise ValueError("Provider returned an empty response")

        usage = None
        usage_data = data.get("usage") if isinstance(data, dict) else None
        if isinstance(usage_data, dict):
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens"),
                completion_tokens=usage_data.get("completion_tokens"),
                total_tokens=usage_data.get("total_tokens"),
            )

        return ProviderResponse(text=text, raw=data, usage=usage)


class DeepSeekClient(OpenAICompatibleClient):
    """HTTP client for DeepSeek."""

    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        super().__init__(
            base_url=base_url or "https://api.deepseek.com/v1",
            api_key=api_key,
            supports_json_mode=False,
        )


class GroqClient(OpenAICompatibleClient):
    """HTTP client for Groq."""

    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        super().__init__(
            base_url=base_url or "https://api.groq.com/openai/v1",
            api_key=api_key,
            supports_json_mode=False,
        )


__all__ = [
    "AnthropicClient",
    "DeepSeekClient",
    "GeminiClient",
    "GroqClient",
    "LLMClient",
    "Message",
    "OllamaClient",
    "OpenAIClient",
    "OpenAICompatibleClient",
    "ProviderResponse",
    "TokenUsage",
]

