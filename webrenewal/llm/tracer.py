"""Tracing utilities dedicated to LLM interactions."""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, List, MutableMapping, Sequence

from pydantic import BaseModel

from ..tracing import log_event, safe_json
from .models import (
    LLMTraceEntry,
    Message,
    TokenUsage,
    TraceAttempt,
    TracePrompt,
    truncate_preview,
)

LOGGER = logging.getLogger("llm")


class LLMTraceStore(BaseModel):
    """Simple in-memory store for trace entries."""

    entries: MutableMapping[str, LLMTraceEntry]
    order: List[str]
    last_responses: MutableMapping[tuple[str, str], str]


class LLMTracer:
    """Collect trace information for LLM calls."""

    def __init__(self, *, max_entries: int = 200) -> None:
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._store = LLMTraceStore(entries={}, order=[], last_responses={})

    def start(self, provider: str, model: str) -> LLMTraceEntry:
        """Create a new trace entry and return it."""

        with self._lock:
            entry_id = uuid.uuid4().hex
            entry = LLMTraceEntry(id=entry_id, provider=provider, model=model)
            self._store.entries[entry_id] = entry
            self._store.order.append(entry_id)
            if len(self._store.order) > self._max_entries:
                oldest = self._store.order.pop(0)
                self._store.entries.pop(oldest, None)
            log_event(
                LOGGER,
                logging.INFO,
                "llm.trace.start",
                id=entry_id,
                provider=provider,
                model=model,
            )
            return entry

    def record_attempt(
        self,
        entry: LLMTraceEntry,
        *,
        attempt: int,
        messages: Sequence[Message],
        response_text: str | None,
        parsed: Any | None,
        duration_ms: float,
        usage: TokenUsage | None,
        error: Exception | None,
    ) -> None:
        """Append attempt details to an entry."""

        prompt_preview = truncate_preview("\n".join(f"{m.role}: {m.content}" for m in messages))
        parsed_preview = None
        if parsed is not None:
            parsed_preview = truncate_preview(str(safe_json(parsed)))

        attempt_entry = TraceAttempt(
            attempt=attempt,
            prompt=TracePrompt(messages=list(messages), preview=prompt_preview),
            response_preview=truncate_preview(response_text or "") if response_text else None,
            parsed_preview=parsed_preview,
            duration_ms=round(duration_ms, 2),
            usage=usage,
            error=repr(error) if error else None,
        )

        with self._lock:
            entry.add_attempt(attempt_entry)
            log_event(
                LOGGER,
                logging.INFO,
                "llm.trace.attempt",
                id=entry.id,
                attempt=attempt,
                provider=entry.provider,
                model=entry.model,
                duration_ms=round(duration_ms, 2),
                error=repr(error) if error else None,
                usage=safe_json(usage.model_dump() if usage else None),
                prompt_preview=prompt_preview,
                response_preview=attempt_entry.response_preview,
                parsed_preview=parsed_preview,
            )

    def record_last_response(self, provider: str, model: str, trace_id: str) -> None:
        """Remember the last response id for the provider/model tuple."""

        with self._lock:
            self._store.last_responses[(provider, model)] = trace_id

    def get_last_trace(self, provider: str, model: str) -> LLMTraceEntry | None:
        """Return the last trace entry for a provider/model tuple."""

        with self._lock:
            trace_id = self._store.last_responses.get((provider, model))
            if not trace_id:
                return None
            return self._store.entries.get(trace_id)

    def get_trace(self, trace_id: str) -> LLMTraceEntry | None:
        """Return a specific trace entry by id."""

        with self._lock:
            return self._store.entries.get(trace_id)

    def list_traces(self) -> List[LLMTraceEntry]:
        """Return traces in chronological order."""

        with self._lock:
            return [self._store.entries[trace_id] for trace_id in self._store.order]


_GLOBAL_TRACER: LLMTracer | None = None
_TRACER_LOCK = threading.Lock()


def get_tracer() -> LLMTracer:
    """Return the process wide tracer instance."""

    global _GLOBAL_TRACER
    with _TRACER_LOCK:
        if _GLOBAL_TRACER is None:
            _GLOBAL_TRACER = LLMTracer()
        return _GLOBAL_TRACER

