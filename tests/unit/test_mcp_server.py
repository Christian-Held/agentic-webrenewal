import json
from types import SimpleNamespace

import pytest

pytest.importorskip("mcp")

from webrenewal.llm import mcp_server


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class StubTraceEntry:
    def __init__(self, *, entry_id: str, provider: str = "stub", model: str = "model") -> None:
        self.id = entry_id
        self.provider = provider
        self.model = model

    def model_dump(self, *, mode: str = "json"):
        return {"id": self.id, "provider": self.provider, "model": self.model}


class StubTracer:
    def __init__(self) -> None:
        self.trace_lookup: dict[str, StubTraceEntry] = {}
        self.last_lookup: dict[tuple[str, str], StubTraceEntry] = {}
        self.requested_trace_id: str | None = None
        self.requested_last: tuple[str, str] | None = None

    def list_traces(self):
        return []

    def get_trace(self, trace_id: str):
        self.requested_trace_id = trace_id
        return self.trace_lookup.get(trace_id)

    def get_last_trace(self, provider: str, model: str):
        self.requested_last = (provider, model)
        return self.last_lookup.get((provider, model))


@pytest.mark.anyio
async def test_read_resource_trace_uses_clean_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = StubTracer()
    tracer.trace_lookup["abc"] = StubTraceEntry(entry_id="abc")
    monkeypatch.setattr(mcp_server, "get_tracer", lambda: tracer)

    request = SimpleNamespace(params=SimpleNamespace(uri="llm://trace/abc"))
    result = await mcp_server.read_resource(request)

    assert tracer.requested_trace_id == "abc"
    payload = json.loads(result.root.contents[0].text)
    assert payload["id"] == "abc"


@pytest.mark.anyio
async def test_read_resource_last_parses_provider_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = StubTracer()
    tracer.last_lookup[("openai", "gpt-4o")] = StubTraceEntry(
        entry_id="xyz", provider="openai", model="gpt-4o"
    )
    monkeypatch.setattr(mcp_server, "get_tracer", lambda: tracer)

    request = SimpleNamespace(params=SimpleNamespace(uri="llm://last/openai/gpt-4o"))
    result = await mcp_server.read_resource(request)

    assert tracer.requested_last == ("openai", "gpt-4o")
    payload = json.loads(result.root.contents[0].text)
    assert payload["id"] == "xyz"


@pytest.mark.anyio
async def test_read_resource_trace_missing_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = StubTracer()
    monkeypatch.setattr(mcp_server, "get_tracer", lambda: tracer)
    captured: dict[str, str] = {}

    def fake_error(message: str):
        captured["message"] = message
        return message

    monkeypatch.setattr(mcp_server.server, "_make_error_result", fake_error)

    request = SimpleNamespace(params=SimpleNamespace(uri="llm://trace/"))
    result = await mcp_server.read_resource(request)

    assert result == "Trace id missing"
    assert captured["message"] == "Trace id missing"


@pytest.mark.anyio
async def test_read_resource_last_invalid_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = StubTracer()
    monkeypatch.setattr(mcp_server, "get_tracer", lambda: tracer)
    captured: dict[str, str] = {}

    def fake_error(message: str):
        captured["message"] = message
        return message

    monkeypatch.setattr(mcp_server.server, "_make_error_result", fake_error)

    request = SimpleNamespace(params=SimpleNamespace(uri="llm://last/openai"))
    result = await mcp_server.read_resource(request)

    assert result == "Invalid last trace URI"
    assert captured["message"] == "Invalid last trace URI"
