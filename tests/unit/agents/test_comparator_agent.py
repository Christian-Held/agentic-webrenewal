"""Tests for :class:`webrenewal.agents.comparator.ComparatorAgent`."""

from __future__ import annotations

from pathlib import Path

from webrenewal.agents.comparator import ComparatorAgent
from webrenewal.models import CrawlResult, PageContent


def test_comparator_agent_matches_by_relative_path(sample_crawl_result, sandbox_dir: Path, html_loader) -> None:
    """Given matching filenames When comparator runs Then diffs compare against the generated page."""

    newsite = sandbox_dir / "newsite"
    newsite.mkdir()
    (newsite / "index.html").write_text("<html><body>new</body></html>", encoding="utf-8")
    about_dir = newsite / "about"
    about_dir.mkdir()
    (about_dir / "index.html").write_text(html_loader("about.html"), encoding="utf-8")

    agent = ComparatorAgent()
    index = agent.run((sample_crawl_result, "newsite"))

    assert len(index.diffs) == len(sample_crawl_result.pages)
    assert {diff.page for diff in index.diffs} == {page.url for page in sample_crawl_result.pages}


def test_comparator_agent_handles_missing_files(sandbox_dir: Path) -> None:
    """Given missing generated pages When comparator runs Then a placeholder diff is produced."""

    crawl = CrawlResult(pages=[PageContent(url="https://example.com", status_code=200, headers={}, html="old")])
    (sandbox_dir / "newsite").mkdir()
    agent = ComparatorAgent()

    index = agent.run((crawl, "newsite"))

    assert index.diffs[0].diff
    assert index.diffs[0].page == "https://example.com"

