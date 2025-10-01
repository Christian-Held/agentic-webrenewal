"""High level orchestration for LLM calls with tracing and validation."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, MutableMapping, Sequence, Tuple, Type

import jsonschema
from pydantic import BaseModel, ValidationError

from ..tracing import log_event
from .clients import LLMClient, ProviderResponse
from .models import (
    CompletionMetadata,
    JSONCompletion,
    JSONPayload,
    Message,
    TextCompletion,
    truncate_preview,
)
from .tracer import LLMTracer, get_tracer

LOGGER = logging.getLogger("llm")


MessageType = MutableMapping[str, Any]


def _ensure_messages(prompt: Sequence[MessageType] | str) -> List[MessageType]:
    if isinstance(prompt, str):
        return [{"role": "user", "content": prompt}]
    return [dict(message) for message in prompt]


def _to_model_messages(messages: Sequence[MessageType]) -> List[Message]:
    result: List[Message] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = message.get("content", "")
        result.append(Message(role=role, content=str(content)))
    return result


def _load_schema(schema: str | Dict[str, Any] | Type[BaseModel] | None) -> Tuple[
    Dict[str, Any] | None,
    Type[BaseModel] | None,
]:
    if schema is None:
        return None, None
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return None, schema
    if isinstance(schema, dict):
        return schema, None
    if isinstance(schema, str):
        try:
            parsed = json.loads(schema)
        except json.JSONDecodeError as exc:  # pragma: no cover - invalid schema provided by user
            raise ValueError("Schema must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Schema JSON must be an object")
        return parsed, None
    raise TypeError("Unsupported schema type")


class JSONValidationError(RuntimeError):
    """Raised when JSON parsing or validation fails."""


class LLMService:
    """Wrap a provider client with tracing, retries and validation."""

    def __init__(
        self,
        *,
        provider: str,
        client: LLMClient,
        tracer: LLMTracer | None = None,
    ) -> None:
        self._provider = provider
        self._client = client
        self._tracer = tracer or get_tracer()

    @property
    def provider(self) -> str:
        return self._provider

    async def complete_text(
        self,
        prompt: Sequence[MessageType] | str,
        *,
        model: str,
        temperature: float | None = None,
    ) -> TextCompletion:
        messages = _ensure_messages(prompt)
        entry = self._tracer.start(self._provider, model)
        start = time.perf_counter()
        response: ProviderResponse | None = None
        error: Exception | None = None
        try:
            response = await self._client.complete(
                messages,
                model=model,
                temperature=temperature,
                response_format=None,
            )
            if not response.text or not response.text.strip():
                raise ValueError("LLM returned an empty response")
            duration_ms = (time.perf_counter() - start) * 1000
            usage = response.usage
            self._tracer.record_attempt(
                entry,
                attempt=1,
                messages=_to_model_messages(messages),
                response_text=response.text,
                parsed=None,
                duration_ms=duration_ms,
                usage=usage,
                error=None,
            )
            completion = TextCompletion(
                id=entry.id,
                text=response.text,
                raw=response.raw,
                metadata=CompletionMetadata(
                    provider=self._provider,
                    model=model,
                    duration_ms=round(duration_ms, 2),
                    usage=usage,
                ),
            )
            self._tracer.record_last_response(self._provider, model, entry.id)
            log_event(
                LOGGER,
                logging.INFO,
                "llm.complete.text",
                provider=self._provider,
                model=model,
                duration_ms=round(duration_ms, 2),
                usage=response.usage.model_dump() if response.usage else None,
                preview=truncate_preview(response.text),
            )
            return completion
        except Exception as exc:  # pragma: no cover - error path validated via tests elsewhere
            error = exc
            duration_ms = (time.perf_counter() - start) * 1000
            self._tracer.record_attempt(
                entry,
                attempt=1,
                messages=_to_model_messages(messages),
                response_text=response.text if response else None,
                parsed=None,
                duration_ms=duration_ms,
                usage=response.usage if response else None,
                error=exc,
            )
            log_event(
                LOGGER,
                logging.ERROR,
                "llm.complete.text.error",
                provider=self._provider,
                model=model,
                error=repr(exc),
            )
            raise

    async def complete_json(
        self,
        prompt: Sequence[MessageType] | str,
        *,
        model: str,
        schema: str | Dict[str, Any] | Type[BaseModel] | None = None,
        temperature: float | None = None,
        retry_instruction: str | None = None,
    ) -> JSONCompletion:
        messages = _ensure_messages(prompt)
        schema_dict, schema_model = _load_schema(schema)
        retry_messages = list(messages)
        attempts = 0
        entry = self._tracer.start(self._provider, model)
        last_error: Exception | None = None
        while attempts < 2:
            attempts += 1
            start = time.perf_counter()
            response: ProviderResponse | None = None
            error: Exception | None = None
            parsed_payload: Any | None = None
            try:
                response = await self._client.complete(
                    retry_messages,
                    model=model,
                    temperature=temperature,
                    response_format="json_object",
                )
                parsed_payload = json.loads(response.text)
                if schema_dict is not None:
                    jsonschema.validate(instance=parsed_payload, schema=schema_dict)
                    payload_model: BaseModel = JSONPayload(root=parsed_payload)
                elif schema_model is not None:
                    payload_model = schema_model.model_validate(parsed_payload)
                else:
                    payload_model = JSONPayload(root=parsed_payload)

                duration_ms = (time.perf_counter() - start) * 1000
                usage = response.usage
                self._tracer.record_attempt(
                    entry,
                    attempt=attempts,
                    messages=_to_model_messages(retry_messages),
                    response_text=response.text,
                    parsed=payload_model.model_dump(mode="json"),
                    duration_ms=duration_ms,
                    usage=usage,
                    error=None,
                )
                completion = JSONCompletion(
                    id=entry.id,
                    text=response.text,
                    payload=payload_model,
                    raw=response.raw,
                    metadata=CompletionMetadata(
                        provider=self._provider,
                        model=model,
                        duration_ms=round(duration_ms, 2),
                        usage=usage,
                    ),
                )
                self._tracer.record_last_response(self._provider, model, entry.id)
                log_event(
                    LOGGER,
                    logging.INFO,
                    "llm.complete.json",
                    provider=self._provider,
                    model=model,
                    duration_ms=round(duration_ms, 2),
                    usage=usage.model_dump() if usage else None,
                    preview=truncate_preview(response.text),
                )
                return completion
            except Exception as exc:
                error = exc
                duration_ms = (time.perf_counter() - start) * 1000
                self._tracer.record_attempt(
                    entry,
                    attempt=attempts,
                    messages=_to_model_messages(retry_messages),
                    response_text=response.text if response else None,
                    parsed=parsed_payload,
                    duration_ms=duration_ms,
                    usage=response.usage if response else None,
                    error=exc,
                )
                log_event(
                    LOGGER,
                    logging.WARNING,
                    "llm.complete.json.retry",
                    provider=self._provider,
                    model=model,
                    attempt=attempts,
                    error=repr(exc),
                )
                if not isinstance(
                    exc, (json.JSONDecodeError, jsonschema.ValidationError, ValidationError)
                ):
                    raise
                last_error = exc
                if attempts >= 2:
                    break
                retry_messages = list(messages) + [
                    {
                        "role": "system",
                        "content": retry_instruction
                        or "Return valid JSON only, matching the provided schema exactly.",
                    }
                ]

        raise JSONValidationError(
            f"Failed to parse JSON response from {self._provider}:{model}: {last_error}"
        )


__all__ = ["JSONValidationError", "LLMService"]

