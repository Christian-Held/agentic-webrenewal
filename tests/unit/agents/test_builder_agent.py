"""Tests for :class:`webrenewal.agents.builder.BuilderAgent`."""

from __future__ import annotations

from pathlib import Path

import pytest

from webrenewal.agents.builder import BuilderAgent
from webrenewal.models import ContentBlock, ContentBundle, NavModel, NavigationItem, ThemeTokens


@pytest.fixture
def builder_agent() -> BuilderAgent:
    """Return a builder agent configured with the vanilla framework for predictability."""

    return BuilderAgent(css_framework="vanilla")


def test_builder_agent_renders_pages(
    builder_agent: BuilderAgent,
    sample_content_bundle: ContentBundle,
    sample_theme_tokens: ThemeTokens,
    sample_nav_model: NavModel,
    sandbox_dir: Path,
) -> None:
    """Given a content bundle When builder runs Then static files are produced in the sandbox."""

    artifact = builder_agent.run((sample_content_bundle, sample_theme_tokens, sample_nav_model))

    assert (Path(artifact.output_dir) / "index.html").exists()
    assert any(file.endswith(".html") for file in artifact.files)
    assert artifact.navigation_bundle is not None
    assert "nav" in artifact.navigation_bundle.html.lower()


def test_builder_agent_generates_unique_slugs(builder_agent: BuilderAgent, sample_theme_tokens: ThemeTokens, sample_nav_model: NavModel) -> None:
    """Given blocks with identical titles When rendered Then unique filenames are assigned."""

    bundle = ContentBundle(
        blocks=[
            ContentBlock(title="Overview", body="One"),
            ContentBlock(title="Overview", body="Two"),
        ],
        meta_title="Example",
        meta_description="Desc",
        fallback_used=False,
    )

    artifact = builder_agent.run((bundle, sample_theme_tokens, sample_nav_model))

    filenames = [Path(path).name for path in artifact.files if path.endswith(".html")]
    page_files = [name for name in filenames if name != "index.html"]
    assert len(set(page_files)) == len(page_files)
    assert artifact.navigation_bundle is not None


def test_builder_agent_supports_custom_framework() -> None:
    """Given a custom framework When constructing Then metadata reflects the request."""

    agent = BuilderAgent(css_framework="custom-xyz", style_hints="rounded buttons")

    assert agent._framework_meta["is_custom"] is True  # type: ignore[attr-defined]
    assert agent._framework_meta["style_hints"] == "rounded buttons"  # type: ignore[attr-defined]

