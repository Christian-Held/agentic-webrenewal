"""Tests for :class:`webrenewal.agents.seo.SEOAgent`."""

from __future__ import annotations

from webrenewal.agents.seo import SEOAgent
from webrenewal.models import CrawlResult, PageContent


def test_seo_agent_detects_missing_meta() -> None:
    """Given missing title and description When analysed Then issues are raised and score reduced."""

    crawl = CrawlResult(
        pages=[PageContent(url="https://example.com", status_code=200, headers={}, html="<html></html>")]
    )
    agent = SEOAgent()

    report = agent.run(crawl)

    assert report.score < 100
    assert len(report.issues) == 2


def test_seo_agent_accepts_complete_metadata() -> None:
    """Given complete metadata When analysed Then the score remains perfect."""

    html = "<html><head><title>Title</title><meta name='description' content='Desc'></head></html>"
    crawl = CrawlResult(
        pages=[PageContent(url="https://example.com", status_code=200, headers={}, html=html)]
    )
    agent = SEOAgent()

    report = agent.run(crawl)

    assert report.score == 100

