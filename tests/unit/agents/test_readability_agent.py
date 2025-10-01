"""Tests for :class:`webrenewal.agents.readability.ReadabilityAgent`."""

from __future__ import annotations

import pytest

from webrenewal.agents.readability import ReadabilityAgent
from webrenewal.models import CrawlResult, PageContent


def test_readability_agent_extracts_sections(sample_crawl_result) -> None:
    """Given crawl pages When readability runs Then sections with scores are returned."""

    agent = ReadabilityAgent()
    extract = agent.run(sample_crawl_result)

    assert len(extract.sections) == len(sample_crawl_result.pages)
    assert extract.language == "en"


def test_readability_agent_handles_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given no trafilatura output When readability runs Then soup fallback is used."""

    agent = ReadabilityAgent()
    monkeypatch.setattr(agent, "_extract_with_trafilatura", lambda html: None)
    html = "<html lang='en'><head><title>Title</title></head><body><p>Hello</p></body></html>"
    crawl = CrawlResult(pages=[PageContent(url="https://example.com", status_code=200, headers={}, html=html)])

    extract = agent.run(crawl)

    assert extract.sections[0].text.strip().startswith("Title")

