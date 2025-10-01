"""Unit tests for :mod:`webrenewal.pipeline`."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from webrenewal.models import CrawlResult, PageContent
from webrenewal.pipeline import WebRenewalPipeline


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch, sandbox_dir: Path) -> WebRenewalPipeline:
    """Return a pipeline instance with logging disabled for unit tests."""

    logger = logging.getLogger("pipeline-test")
    logger.setLevel(logging.CRITICAL)
    return WebRenewalPipeline(logger=logger)


def test_summarise_output_handles_model(pipeline: WebRenewalPipeline) -> None:
    """Given a dataclass output When summarised Then metrics are derived from attributes."""

    summary = pipeline._summarise_output(CrawlResult(pages=[PageContent(url="u", status_code=200, headers={}, html="")]))

    assert summary["type"] == "CrawlResult"
    assert summary["pages"] == 1


def test_summarise_output_handles_dict_and_sequence(pipeline: WebRenewalPipeline) -> None:
    """Given plain collections When summarised Then counts and items length are provided."""

    class ItemContainer:
        def __init__(self) -> None:
            self.items = [1, 2]

    summary_items = pipeline._summarise_output(ItemContainer())
    summary_list = pipeline._summarise_output([1, 2, 3])

    assert summary_items["items"] == 2
    assert summary_list["count"] == 3


def test_export_original_site_writes_files(pipeline: WebRenewalPipeline, sandbox_dir: Path) -> None:
    """Given a crawl result When exported Then HTML pages are persisted under sandbox/original."""

    crawl = CrawlResult(
        pages=[
            PageContent(url="https://example.com/", status_code=200, headers={}, html="<html></html>"),
            PageContent(url="https://example.com/about", status_code=200, headers={}, html="<html></html>"),
        ]
    )

    exported = pipeline._export_original_site(crawl)

    expected_paths = {"original/index.html", "original/about/index.html"}
    assert set(exported) == expected_paths
    for relative in expected_paths:
        assert (sandbox_dir / relative).exists()

