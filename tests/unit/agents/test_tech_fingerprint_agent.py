"""Tests for :class:`webrenewal.agents.tech_fingerprint.TechFingerprintAgent`."""

from __future__ import annotations

from webrenewal.agents.tech_fingerprint import TechFingerprintAgent
from webrenewal.models import CrawlResult, PageContent


def test_tech_fingerprint_identifies_frameworks() -> None:
    """Given known asset signatures When analysed Then frameworks and evidence are recorded."""

    html = "<html><script src='https://cdn.example.com/jquery.min.js'></script></html>"
    crawl = CrawlResult(pages=[PageContent(url="https://example.com", status_code=200, headers={}, html=html)])
    agent = TechFingerprintAgent()

    report = agent.run(crawl)

    assert "jQuery" in report.frameworks
    assert report.evidence["jQuery"] == ["https://example.com"]


def test_tech_fingerprint_handles_no_matches(empty_crawl_result) -> None:
    """Given pages without signatures When analysed Then no frameworks are detected."""

    agent = TechFingerprintAgent()
    report = agent.run(empty_crawl_result)

    assert report.frameworks == []
    assert report.evidence == {}

