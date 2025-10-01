"""Tests for :class:`webrenewal.agents.security.SecurityAgent`."""

from __future__ import annotations

from webrenewal.agents.security import SecurityAgent
from webrenewal.models import CrawlResult, PageContent


def test_security_agent_requires_headers() -> None:
    """Given missing headers When analysed Then issues list contains missing entries and score drops."""

    page = PageContent(
        url="https://example.com",
        status_code=200,
        headers={"Content-Type": "text/html"},
        html="<html></html>",
    )
    crawl = CrawlResult(pages=[page])
    agent = SecurityAgent()
    report = agent.run(crawl)

    assert report.score < 100
    assert any("content-security-policy" in issue.description.lower() for issue in report.issues)


def test_security_agent_perfect_headers() -> None:
    """Given complete headers When analysed Then no issues are reported."""

    page = PageContent(
        url="https://example.com",
        status_code=200,
        headers={
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
        },
        html="<html></html>",
    )
    crawl = CrawlResult(pages=[page])

    agent = SecurityAgent()
    report = agent.run(crawl)

    assert report.score == 100
    assert report.issues == []

