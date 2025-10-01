"""Tests for :class:`webrenewal.agents.accessibility.AccessibilityAgent`."""

from __future__ import annotations

from webrenewal.agents.accessibility import AccessibilityAgent


def test_accessibility_agent_flags_missing_alts(sample_crawl_result) -> None:
    """Given pages with missing alt attributes When analysed Then issues and score reflect the findings."""

    agent = AccessibilityAgent()

    report = agent.run(sample_crawl_result)

    assert report.score < 100
    assert any("missing alt" in issue.description for issue in report.issues)


def test_accessibility_agent_handles_no_images(empty_crawl_result) -> None:
    """Given no images When analysed Then the score stays perfect without issues."""

    agent = AccessibilityAgent()

    report = agent.run(empty_crawl_result)

    assert report.score == 100
    assert report.issues == []

