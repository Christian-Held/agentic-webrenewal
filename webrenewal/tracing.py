"""Tracing and structured logging helpers for the pipeline."""

from __future__ import annotations

import json
import logging
import math
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional

__all__ = ["TraceSpan", "trace", "log_event", "safe_json"]


def safe_json(value: Any) -> Any:
    """Return ``value`` converted into a JSON-serialisable structure."""

    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return repr(value)
        return value

    if isinstance(value, (list, tuple, set)):
        return [safe_json(item) for item in value]

    if isinstance(value, dict):
        return {str(key): safe_json(val) for key, val in value.items()}

    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        try:
            return value.to_dict()
        except Exception:  # pragma: no cover - defensive serialisation
            return repr(value)

    if hasattr(value, "__dict__"):
        return {key: safe_json(val) for key, val in vars(value).items() if not key.startswith("_")}

    return repr(value)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    exc_info: bool | BaseException | tuple[Any, Any, Any] | None = None,
    **fields: Any,
) -> None:
    """Emit a structured log line encoded as JSON."""

    payload: Dict[str, Any] = {"event": event}
    if fields:
        payload.update({key: safe_json(value) for key, value in fields.items() if value is not None})

    message = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    logger.log(level, message, exc_info=exc_info)


@dataclass
class TraceSpan:
    """Represents an active trace span."""

    name: str
    logger: logging.Logger
    fields: Dict[str, Any]
    start_time: float

    def note(self, **fields: Any) -> None:
        """Emit an in-span structured debug note."""

        base = {"trace": self.name}
        base.update(self.fields)
        base.update(fields)
        log_event(self.logger, logging.DEBUG, "trace.note", **base)


@contextmanager
def trace(name: str, *, logger: Optional[logging.Logger] = None, **fields: Any):
    """Context manager that logs start/end events with duration and exceptions."""

    logger = logger or logging.getLogger("trace")
    start_time = time.perf_counter()
    base_fields = {"trace": name}
    base_fields.update(fields)
    log_event(logger, logging.INFO, "trace.start", **base_fields)
    span = TraceSpan(name=name, logger=logger, fields=dict(fields), start_time=start_time)
    try:
        yield span
    except Exception as exc:  # pragma: no cover - exercised via runtime failures
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        error_fields = dict(base_fields)
        error_fields["duration_ms"] = duration_ms
        error_fields["error"] = repr(exc)
        log_event(logger, logging.ERROR, "trace.error", exc_info=True, **error_fields)
        raise
    else:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        end_fields = dict(base_fields)
        end_fields["duration_ms"] = duration_ms
        log_event(logger, logging.INFO, "trace.end", **end_fields)
