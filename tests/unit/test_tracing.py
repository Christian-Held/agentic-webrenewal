"""Tests for :mod:`webrenewal.tracing`."""

from __future__ import annotations

import logging

import pytest

from webrenewal.tracing import log_event, safe_json, trace


def test_safe_json_serialises_dataclass(memory_record) -> None:
    """Given a dataclass When safe_json is used Then nested types become serialisable dictionaries."""

    payload = safe_json(memory_record)

    assert payload["key"] == "example.com"
    assert payload["payload"]["goals"].startswith("Accessibility")


def test_log_event_emits_json(caplog: pytest.LogCaptureFixture) -> None:
    """Given structured fields When log_event is called Then a JSON encoded message is logged."""

    logger = logging.getLogger("test")
    with caplog.at_level(logging.INFO):
        log_event(logger, logging.INFO, "test.event", answer=42)

    assert caplog.records
    assert "\"event\": \"test.event\"" in caplog.text


def test_trace_context_records_duration(caplog: pytest.LogCaptureFixture) -> None:
    """Given a trace context When exiting Then start and end events are logged with duration."""

    logger = logging.getLogger("trace-test")
    with caplog.at_level(logging.INFO):
        with trace("unit", logger=logger):
            pass

    messages = [record.getMessage() for record in caplog.records]
    assert any("trace.start" in message for message in messages)
    assert any("trace.end" in message for message in messages)

