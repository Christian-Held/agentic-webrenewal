"""Tests for :class:`webrenewal.agents.crawler.CrawlerAgent`."""

from __future__ import annotations

from collections import deque
from typing import Dict

import pytest

from webrenewal.agents.crawler import CrawlerAgent
from webrenewal.http import HttpResponse
from webrenewal.models import ScopePlan


class FakeResponse(HttpResponse):
    def __init__(self, url: str, status_code: int, html: str, headers: Dict[str, str] | None = None) -> None:
        super().__init__(url=url, status_code=status_code, headers=headers or {}, text=html)


@pytest.fixture
def fake_get(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the HTTP client to return deterministic HTML documents."""

    pages = {
        "https://example.com": FakeResponse(
            "https://example.com",
            200,
            "<html><a href='/about'>About</a><a href='https://external.com'>External</a></html>",
        ),
        "https://example.com/about": FakeResponse(
            "https://example.com/about",
            200,
            "<html><a href='/team'>Team</a></html>",
        ),
        "https://example.com/team": FakeResponse(
            "https://example.com/team",
            404,
            "<html></html>",
        ),
    }

    def fake_get(url: str, headers=None):  # noqa: D401 - stub
        return pages[url.rstrip("/")]

    monkeypatch.setattr("webrenewal.agents.crawler.get", fake_get)


def test_crawler_agent_traverses_domain(fake_get) -> None:
    """Given a scope plan When CrawlerAgent runs Then only in-domain links are visited."""

    plan = ScopePlan(domain="https://example.com", seed_urls=["https://example.com"], sitemap_urls=[])
    agent = CrawlerAgent()

    result = agent.run(plan)

    urls = [page.url for page in result.pages]
    assert "https://example.com" in urls
    assert "https://example.com/about" in urls
    assert "https://example.com/team" in urls
    assert all("external" not in url for url in urls)


def test_crawler_agent_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given request errors When crawling Then failures are skipped and processing continues."""

    call_count = {"value": 0}

    import requests

    def failing_get(url: str, headers=None):  # noqa: D401 - stub
        call_count["value"] += 1
        raise requests.RequestException("boom")

    monkeypatch.setattr("webrenewal.agents.crawler.get", failing_get)
    plan = ScopePlan(domain="https://example.com", seed_urls=["https://example.com"], sitemap_urls=[])
    agent = CrawlerAgent()

    result = agent.run(plan)

    assert result.pages == []
    assert call_count["value"] == 1

