from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import httpx
import pytest

from webrenewal.llm import (
    JSONValidationError,
    LLMService,
    create_llm_client,
    create_llm_service,
    default_model_for,
    get_tracer,
    list_available_providers,
)
from webrenewal.llm.clients import LLMClient, ProviderResponse


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class StubLLMClient(LLMClient):
    """Deterministic client returning queued responses."""

    def __init__(self, responses: Sequence[ProviderResponse]) -> None:
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    async def _complete(
        self,
        messages: Sequence[Dict[str, Any]],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
        self.calls.append(
            {
                "messages": list(messages),
                "model": model,
                "temperature": temperature,
                "response_format": response_format,
            }
        )
        if not self._responses:
            raise RuntimeError("No more responses configured")
        return self._responses.pop(0)


@dataclass
class BlockingClient(LLMClient):
    """Client raising a timeout error."""

    exception: Exception

    async def _complete(
        self,
        messages: Sequence[Dict[str, Any]],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
        raise self.exception


@pytest.mark.anyio
async def test_complete_json_validates_schema() -> None:
    """Given a valid JSON response When schema is provided Then payload is validated."""

    stub = StubLLMClient([ProviderResponse(text='{"answer": 42}')])
    service = LLMService(provider="stub", client=stub, tracer=get_tracer())

    completion = await service.complete_json(
        [{"role": "user", "content": "Give me JSON"}],
        model="stub-model",
        schema={"type": "object", "properties": {"answer": {"type": "number"}}, "required": ["answer"]},
    )

    assert completion.data == {"answer": 42}
    assert stub.calls[0]["response_format"] == "json_object"


@pytest.mark.anyio
async def test_complete_json_retries_on_invalid_payload() -> None:
    """Given malformed JSON When completing Then the service retries with stricter instructions."""

    stub = StubLLMClient(
        [
            ProviderResponse(text="not-json"),
            ProviderResponse(text='{"answer": 7}'),
        ]
    )
    service = LLMService(provider="stub", client=stub, tracer=get_tracer())

    completion = await service.complete_json(
        [{"role": "user", "content": "Return json"}],
        model="stub-model",
        schema={"type": "object"},
    )

    assert completion.data == {"answer": 7}
    assert len(stub.calls) == 2


@pytest.mark.anyio
async def test_complete_json_raises_after_retries() -> None:
    """Given repeated invalid responses When completing Then JSONValidationError is raised."""

    stub = StubLLMClient([ProviderResponse(text="oops"), ProviderResponse(text="still bad")])
    service = LLMService(provider="stub", client=stub, tracer=get_tracer())

    with pytest.raises(JSONValidationError):
        await service.complete_json(
            [{"role": "user", "content": "Return json"}],
            model="stub-model",
            schema={"type": "object"},
        )


@pytest.mark.anyio
async def test_complete_text_propagates_empty_response() -> None:
    """Given empty response text When completing Then a ValueError bubbles up."""

    stub = StubLLMClient([ProviderResponse(text="")])
    service = LLMService(provider="stub", client=stub, tracer=get_tracer())

    with pytest.raises(ValueError):
        await service.complete_text(
            [{"role": "user", "content": "say"}],
            model="stub-model",
        )


@pytest.mark.anyio
async def test_complete_json_propagates_timeout() -> None:
    """Given a timeout error When completing JSON Then the exception is propagated."""

    timeout = httpx.ReadTimeout("timed out")
    client = BlockingClient(exception=timeout)
    service = LLMService(provider="stub", client=client, tracer=get_tracer())

    with pytest.raises(httpx.ReadTimeout):
        await service.complete_json(
            [{"role": "user", "content": "Return json"}],
            model="stub-model",
            schema={"type": "object"},
        )


def test_list_available_providers_contains_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure catalog exposes provider defaults and respects environment overrides."""

    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    catalog = list_available_providers()

    assert catalog["openai"]["default_model"] == "gpt-test"
    assert "credential_env" in catalog["openai"]


def test_create_llm_client_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """When credentials are missing for API providers Then None is returned."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert create_llm_client("openai") is None


def test_create_llm_service_wraps_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ollama does not require credentials so the service is created."""

    service = create_llm_service("ollama", host="http://fake")
    assert isinstance(service, LLMService)


def test_default_model_for_prefers_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment model overrides default values."""

    monkeypatch.setenv("OLLAMA_MODEL", "custom-ollama")
    assert default_model_for("ollama") == "custom-ollama"
