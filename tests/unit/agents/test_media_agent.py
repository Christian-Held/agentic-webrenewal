"""Tests for :class:`webrenewal.agents.media.MediaAgent`."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

import pytest

from webrenewal.agents.media import MediaAgent


@pytest.fixture
def media_agent(monkeypatch: pytest.MonkeyPatch) -> MediaAgent:
    """Return a MediaAgent with a patched HEAD request."""

    agent = MediaAgent()

    def fake_head(url: str) -> Optional[SimpleNamespace]:  # noqa: D401 - stub
        return SimpleNamespace(headers={"Content-Length": "1024", "Content-Type": "image/jpeg"})

    monkeypatch.setattr(agent, "_head_request", fake_head)
    return agent


def test_media_agent_collects_images(media_agent: MediaAgent, sample_crawl_result) -> None:
    """Given pages with images When analysed Then metadata is returned for each image."""

    report = media_agent.run(sample_crawl_result)

    assert len(report.images) >= 1
    assert report.images[0].size_bytes == 1024
    assert report.images[0].format == "jpeg"


def test_media_agent_handles_head_failures(monkeypatch: pytest.MonkeyPatch, sample_crawl_result) -> None:
    """Given HEAD failures When analysed Then images are returned with missing metadata."""

    agent = MediaAgent()
    monkeypatch.setattr(agent, "_head_request", lambda url: None)

    report = agent.run(sample_crawl_result)

    assert all(image.size_bytes is None for image in report.images)

