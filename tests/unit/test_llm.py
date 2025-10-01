"""Tests for :mod:`webrenewal.llm`."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List

import pytest

from webrenewal.llm import (
    BaseLLMClient,
    LLMError,
    LLMResponse,
    OllamaClient,
    _normalise_messages,
    create_llm_client,
    default_model_for,
)


class DummyClient(BaseLLMClient):
    """Simple client returning canned responses for unit tests."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.calls: List[Dict[str, Any]] = []

    async def _complete(
        self,
        messages: Iterable[Dict[str, Any]],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "messages": list(messages),
                "model": model,
                "temperature": temperature,
                "response_format": response_format,
            }
        )
        return LLMResponse(text=self._response)


def test_base_client_complete_json_parses_payload() -> None:
    """Given a JSON string When complete_json is used Then the parsed data is attached to the response."""

    client = DummyClient('{"answer": 42}')

    response = asyncio.run(client.complete_json([{"role": "user", "content": "Hi"}], model="demo"))

    assert response.data == {"answer": 42}
    assert client.calls[0]["response_format"] == "json_object"


def test_complete_text_preserves_arguments() -> None:
    """Given messages When complete_text is invoked Then the underlying implementation receives them unchanged."""

    client = DummyClient("Hello")
    asyncio.run(client.complete_text([{"role": "system", "content": "Hi"}], model="demo", temperature=0.3))

    call = client.calls[0]
    assert call["model"] == "demo"
    assert call["temperature"] == 0.3
    assert call["response_format"] is None


def test_ollama_client_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a successful response When OllamaClient completes Then the message content is concatenated."""

    async def fake_post(self, path: str, json: Dict[str, Any]):  # noqa: D401 - stub
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "message": {
                    "content": [
                        {"type": "text", "text": "Hello"},
                        {"type": "text", "text": " World"},
                    ]
                }
            },
        )

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs) -> None:  # noqa: D401 - stub
            pass

        async def __aenter__(self) -> "DummyAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401 - stub
            return None

        post = fake_post

    monkeypatch.setattr("httpx.AsyncClient", DummyAsyncClient)

    client = OllamaClient(host="http://localhost:11434")
    response = asyncio.run(client.complete_text([{"role": "user", "content": "Hello"}], model="llama"))

    assert response.text.strip() == "Hello World"


def test_normalise_messages_handles_varied_content() -> None:
    """Given mixed message payloads When normalised Then role and stringified content are returned."""

    messages = _normalise_messages(
        [
            {"role": "system", "content": {"json": True}},
            {"content": "plain"},
        ]
    )

    assert messages[0]["content"].startswith("{")
    assert messages[1]["role"] == "user"


def test_create_llm_client_returns_none_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given missing environment variables When requesting OpenAI Then no client is created."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert create_llm_client("openai") is None


def test_create_llm_client_supports_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given the ollama provider When creating a client Then an OllamaClient instance is returned."""

    client = create_llm_client("ollama", host="http://fake")

    assert isinstance(client, OllamaClient)


def test_default_model_for_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given provider overrides When default_model_for is called Then environment values win."""

    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    assert default_model_for("openai") == "gpt-test"
    assert default_model_for("ollama").startswith("llama")


def test_ollama_client_raises_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given an empty response When OllamaClient completes Then an LLMError is raised."""

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "DummyAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, path: str, json: Dict[str, Any]):  # noqa: D401 - stub
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"message": {"content": []}})

    monkeypatch.setattr("httpx.AsyncClient", DummyAsyncClient)

    client = OllamaClient(host="http://localhost:11434")
    with pytest.raises(LLMError):
        asyncio.run(client.complete_text([{"role": "user", "content": ""}], model="llama"))

