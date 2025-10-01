"""Tests for :mod:`webrenewal.utils.paths`."""

from __future__ import annotations

from webrenewal.utils.paths import url_to_relative_path


def test_url_to_relative_path_handles_directories() -> None:
    """Given a trailing slash URL When converted Then index.html is appended."""

    assert str(url_to_relative_path("https://example.com/about/")) == "about/index.html"


def test_url_to_relative_path_hashes_query_strings() -> None:
    """Given a URL with query parameters When converted Then the hash suffix ensures uniqueness."""

    path = url_to_relative_path("https://example.com/page?ref=source")

    assert path.suffix == ".html"
    assert "_" in path.stem


def test_url_to_relative_path_handles_extensions() -> None:
    """Given a URL pointing to a file When converted Then the filename is preserved."""

    assert str(url_to_relative_path("https://example.com/assets/logo.png")) == "assets/logo.png"

