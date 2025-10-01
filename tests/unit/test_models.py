"""Tests for dataclasses in :mod:`webrenewal.models`."""

from __future__ import annotations

from pathlib import Path

from webrenewal.models import ContentBlock, ContentBundle, ThemeTokens


def test_serializable_to_dict_handles_nested(tmp_path: Path) -> None:
    """Given nested dataclasses When to_dict is called Then nested dictionaries are produced."""

    bundle = ContentBundle(
        blocks=[ContentBlock(title="Title", body="Body")],
        meta_title="Meta",
        meta_description="Desc",
        fallback_used=True,
    )

    as_dict = bundle.to_dict()
    bundle.to_json(tmp_path / "bundle.json")

    assert as_dict["blocks"][0]["title"] == "Title"
    assert (tmp_path / "bundle.json").exists()


def test_theme_tokens_css_variables_flattens(sample_theme_tokens: ThemeTokens) -> None:
    """Given theme tokens When css_variables is invoked Then keys are flattened into CSS custom properties."""

    css = sample_theme_tokens.css_variables()

    assert css["--color-primary"] == "#0b7285"
    assert css["--font-body-family"].startswith("'")
    assert "--shadow-flat" in css

