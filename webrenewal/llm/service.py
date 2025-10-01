"""High level orchestration for LLM calls with tracing and validation."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, MutableMapping, Sequence, Tuple, Type

try:  # pragma: no cover - optional dependency
    import jsonschema  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised in unit tests without dependency
    jsonschema = None  # type: ignore
from pydantic import BaseModel, ValidationError

from ..tracing import log_event, safe_json
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


def _prompt_preview(messages: Sequence[MessageType]) -> str:
    joined = "\n".join(
        f"{str(message.get('role', 'user'))}: {str(message.get('content', ''))}"
        for message in messages
    )
    return truncate_preview(joined)


def _build_json_instruction(
    schema_dict: Dict[str, Any] | None, schema_model: Type[BaseModel] | None
) -> str:
    if schema_model is not None:
        schema_description = json.dumps(
            schema_model.model_json_schema(), ensure_ascii=False, sort_keys=True
        )
    elif schema_dict is not None:
        schema_description = json.dumps(schema_dict, ensure_ascii=False, sort_keys=True)
    else:
        schema_description = "the requested structure"
    return (
        "Return ONLY valid JSON with no explanations. The payload must strictly conform "
        f"to {schema_description}."
    )


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
                prompt_preview=_prompt_preview(messages),
                raw_preview=truncate_preview(str(safe_json(response.raw))),
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
                prompt_preview=_prompt_preview(messages),
                raw_preview=truncate_preview(str(safe_json(response.raw))) if response else None,
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
        attempts = 0
        entry = self._tracer.start(self._provider, model)
        last_error: Exception | None = None
        instruction_text = retry_instruction or _build_json_instruction(schema_dict, schema_model)
        supports_json_mode = self._client.supports_json_mode
        base_messages = list(messages)
        if not supports_json_mode:
            base_messages = base_messages + [
                {"role": "system", "content": instruction_text},
            ]
        retry_messages = list(base_messages)
        last_prompt_messages: Sequence[MessageType] = list(retry_messages)
        last_response_text: str | None = None
        last_response_raw: Any | None = None
        while attempts < 2:
            attempts += 1
            start = time.perf_counter()
            response: ProviderResponse | None = None
            error: Exception | None = None
            parsed_payload: Any | None = None
            try:
                last_prompt_messages = list(retry_messages)
                response = await self._client.complete(
                    retry_messages,
                    model=model,
                    temperature=temperature,
                    response_format="json_object" if supports_json_mode else None,
                )
                last_response_text = response.text
                last_response_raw = response.raw
                parsed_payload = json.loads(response.text)
                if schema_dict is not None:
                    if jsonschema is not None:
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
                    prompt_preview=_prompt_preview(last_prompt_messages),
                    raw_preview=truncate_preview(str(safe_json(response.raw))),
                    parsed_preview=truncate_preview(
                        str(safe_json(payload_model.model_dump(mode="json")))
                    ),
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
                if response is not None:
                    last_response_text = response.text
                    last_response_raw = response.raw
                log_event(
                    LOGGER,
                    logging.WARNING,
                    "llm.complete.json.retry",
                    provider=self._provider,
                    model=model,
                    attempt=attempts,
                    error=repr(exc),
                    prompt_preview=_prompt_preview(last_prompt_messages),
                    raw_preview=truncate_preview(str(safe_json(response.raw)))
                    if response
                    else None,
                )
                if not isinstance(
                    exc,
                    tuple(
                        filter(
                            None,
                            [
                                json.JSONDecodeError,
                                getattr(jsonschema, "ValidationError", None),
                                ValidationError,
                            ],
                        )
                    ),
                ):
                    raise
                last_error = exc
                if attempts >= 2:
                    break
                retry_messages = list(base_messages)
                retry_prompt = instruction_text
                if last_error:
                    retry_prompt = (
                        f"{instruction_text} Previous error: {last_error}."
                    )
                retry_messages.append({"role": "system", "content": retry_prompt})

        log_event(
            LOGGER,
            logging.ERROR,
            "llm.complete.json.error",
            provider=self._provider,
            model=model,
            error=repr(last_error) if last_error else None,
            prompt_preview=_prompt_preview(last_prompt_messages),
            raw_preview=truncate_preview(str(safe_json(last_response_raw)))
            if last_response_raw is not None
            else None,
            response_preview=truncate_preview(last_response_text or "")
            if last_response_text
            else None,
        )
        raise JSONValidationError(
            f"Failed to parse JSON response from {self._provider}:{model}: {last_error}"
        )


__all__ = ["JSONValidationError", "LLMService"]

