"""Tests for :class:`webrenewal.agents.scope.ScopeAgent`."""

from __future__ import annotations

import pytest

from webrenewal.agents.scope import ScopeAgent
from webrenewal.http import HttpResponse


def test_scope_agent_builds_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a domain When ScopeAgent runs Then robots and sitemap information is captured."""

    def fake_get(url: str, timeout: int = 20, headers=None):  # noqa: D401 - stub
        return HttpResponse(url=url, status_code=200, headers={}, text="Sitemap: https://example.com/sitemap.xml")

    monkeypatch.setattr("webrenewal.agents.scope.get", fake_get)

    agent = ScopeAgent()
    plan = agent.run("example.com")

    assert plan.domain == "https://example.com"
    assert plan.sitemap_urls == ["https://example.com/sitemap.xml"]
    assert "User-agent" not in (plan.robots_txt or "")


def test_scope_agent_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a network error When ScopeAgent fetches robots Then the plan still contains defaults."""

    import requests

    def fake_get(url: str, timeout: int = 20, headers=None):  # noqa: D401 - stub
        raise requests.RequestException("boom")

    monkeypatch.setattr("webrenewal.agents.scope.get", fake_get)

    agent = ScopeAgent()
    plan = agent.run("https://example.org")

    assert plan.domain == "https://example.org"
    assert plan.sitemap_urls == []
    assert plan.robots_txt is None

