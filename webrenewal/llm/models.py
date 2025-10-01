"""Pydantic data models used by the LLM integration layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


MAX_PREVIEW_CHARS = 800


def truncate_preview(value: str, *, limit: int = MAX_PREVIEW_CHARS) -> str:
    """Return a preview of ``value`` limited to ``limit`` characters."""

    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


class Message(BaseModel):
    """A single message sent to an LLM provider."""

    role: str
    content: str


class TokenUsage(BaseModel):
    """Token usage accounting for a single LLM response."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class CompletionMetadata(BaseModel):
    """Metadata describing a completion call."""

    provider: str
    model: str
    duration_ms: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    usage: TokenUsage | None = None


class BaseCompletion(BaseModel):
    """Common fields for completion payloads."""

    id: str
    metadata: CompletionMetadata
    text: str
    raw: Any | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)


class JSONPayload(RootModel[Dict[str, Any] | List[Any]]):
    """Wrapper ensuring JSON payloads are structured data."""

    root: Dict[str, Any] | List[Any]

    @model_validator(mode="after")
    def _ensure_serialisable(self) -> "JSONPayload":
        if isinstance(self.root, (dict, list)):
            return self
        raise TypeError("JSON payload must be a dict or list")


class JSONCompletion(BaseCompletion):
    """Completion that returned a structured JSON payload."""

    payload: BaseModel | JSONPayload

    @property
    def data(self) -> Dict[str, Any] | List[Any]:
        """Return the payload as serialisable data."""

        if isinstance(self.payload, JSONPayload):
            return self.payload.root
        return self.payload.model_dump(mode="json")


class TextCompletion(BaseCompletion):
    """Simple text completion."""


class TracePrompt(BaseModel):
    """Representation of the prompt used for a single attempt."""

    messages: Sequence[Message]
    preview: str


class TraceAttempt(BaseModel):
    """Single attempt when invoking an LLM."""

    attempt: int
    prompt: TracePrompt
    response_preview: str | None = None
    parsed_preview: str | None = None
    duration_ms: float | None = None
    usage: TokenUsage | None = None
    error: str | None = None


class LLMTraceEntry(BaseModel):
    """Full trace of an LLM interaction (possibly with retries)."""

    id: str
    provider: str
    model: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attempts: List[TraceAttempt] = Field(default_factory=list)
    error: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def add_attempt(self, attempt: TraceAttempt) -> None:
        """Append an attempt to the trace entry."""

        self.attempts.append(attempt)
        if attempt.error:
            self.error = attempt.error
        else:
            self.error = None

    @property
    def last_attempt(self) -> TraceAttempt | None:
        """Return the most recent attempt."""

        if not self.attempts:
            return None
        return self.attempts[-1]

    @property
    def prompt_preview(self) -> str:
        """Return the preview of the first attempt prompt."""

        attempt = self.last_attempt if self.attempts else None
        if attempt is None:
            return ""
        return attempt.prompt.preview


def serialise_messages(messages: Iterable[Message]) -> str:
    """Return a text representation of messages for logging."""

    parts: List[str] = []
    for message in messages:
        parts.append(f"{message.role}: {message.content}")
    return "\n".join(parts)

