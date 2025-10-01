"""Tests for :mod:`webrenewal.utils.domain`."""

from __future__ import annotations

import pytest

from webrenewal.utils.domain import domain_to_display_name, normalise_domain


def test_normalise_domain_strips_protocol_and_www() -> None:
    """Given a complex domain When normalise_domain is called Then protocol and www are removed."""

    assert normalise_domain("https://www.Example.com/path") == "example.com"


def test_domain_to_display_name_handles_empty() -> None:
    """Given an empty domain When domain_to_display_name is executed Then the stripped input is returned."""

    assert domain_to_display_name("   ") == ""


def test_domain_to_display_name_converts_segments() -> None:
    """Given a hyphenated domain When converted Then segments are capitalised for readability."""

    assert domain_to_display_name("blog.example-site.com") == "Blog Example Site Com"


def test_normalise_domain_accepts_partial_url() -> None:
    """Given a bare host When normalised Then trailing slashes are removed without error."""

    assert normalise_domain("example.com/") == "example.com"

