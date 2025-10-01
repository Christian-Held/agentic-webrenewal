"""Integration tests for running the WebRenewal pipeline end-to-end."""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from webrenewal.agents.accessibility import AccessibilityAgent
from webrenewal.agents.media import MediaAgent
from webrenewal.agents.navigation import NavigationAgent
from webrenewal.agents.plan import PlanProposalAgent
from webrenewal.agents.readability import ReadabilityAgent
from webrenewal.agents.security import SecurityAgent
from webrenewal.agents.seo import SEOAgent
from webrenewal.agents.tech_fingerprint import TechFingerprintAgent
from webrenewal.agents.tool_discovery import ToolDiscoveryAgent
from webrenewal.models import ContentBundle, ContentBlock
from webrenewal.pipeline import WebRenewalPipeline
from webrenewal.models import RenewalConfig


class StaticAgent:
    """Small helper that always returns a precomputed payload."""

    def __init__(self, name: str, output: Any) -> None:
        self.name = name
        self._output = output

    def run(self, data: Any) -> Any:  # noqa: D401 - simple proxy
        return self._output


@pytest.fixture
def prepared_outputs(sample_crawl_result, sample_scope_plan, sample_content_bundle, sample_theme_tokens):
    """Prepare deterministic agent outputs used across the integration test."""

    tool_catalog = ToolDiscoveryAgent().run(None)
    readability = ReadabilityAgent().run(sample_crawl_result)
    tech = TechFingerprintAgent().run(sample_crawl_result)
    accessibility = AccessibilityAgent().run(sample_crawl_result)
    seo = SEOAgent().run(sample_crawl_result)
    security = SecurityAgent().run(sample_crawl_result)

    media_agent = MediaAgent()
    media_agent._head_request = lambda url: SimpleNamespace(headers={"Content-Length": "512", "Content-Type": "image/png"})  # type: ignore[assignment]
    media_report = media_agent.run(sample_crawl_result)

    navigation = NavigationAgent().run(sample_crawl_result)
    plan = PlanProposalAgent().run((accessibility, seo, security, tech, media_report, navigation))

    bundle = sample_content_bundle
    theme = sample_theme_tokens

    return {
        "tool_catalog": tool_catalog,
        "scope_plan": sample_scope_plan,
        "crawl_result": sample_crawl_result,
        "readability": readability,
        "tech": tech,
        "accessibility": accessibility,
        "seo": seo,
        "security": security,
        "media": media_report,
        "navigation": navigation,
        "plan": plan,
        "bundle": bundle,
        "theme": theme,
    }


def test_pipeline_creates_expected_artifacts(
    prepared_outputs,
    sandbox_dir,
) -> None:
    """Given prepared agent outputs When executing the pipeline Then all artefacts are produced deterministically."""

    logger = logging.getLogger("pipeline-integration")
    logger.setLevel(logging.CRITICAL)
    config = RenewalConfig(
        domain="https://example.com",
        renewal_mode="full",
        css_framework="vanilla",
        theme_style="",
        llm_provider="openai",
        llm_model=None,
        log_level="CRITICAL",
    )
    pipeline = WebRenewalPipeline(renewal_config=config, logger=logger)

    pipeline.tool_discovery = StaticAgent("A0.ToolDiscovery", prepared_outputs["tool_catalog"])
    pipeline.scope = StaticAgent("A1.Scope", prepared_outputs["scope_plan"])
    pipeline.crawler = StaticAgent("A2.Crawler", prepared_outputs["crawl_result"])
    pipeline.readability = StaticAgent("A3.Readability", prepared_outputs["readability"])
    pipeline.tech = StaticAgent("A4.Tech", prepared_outputs["tech"])
    pipeline.accessibility = StaticAgent("A5.Accessibility", prepared_outputs["accessibility"])
    pipeline.seo = StaticAgent("A6.SEO", prepared_outputs["seo"])
    pipeline.security = StaticAgent("A7.Security", prepared_outputs["security"])
    pipeline.media = StaticAgent("A8.Media", prepared_outputs["media"])
    pipeline.navigation = StaticAgent("A9.Navigation", prepared_outputs["navigation"])
    pipeline.plan = StaticAgent("A10.Plan", prepared_outputs["plan"])
    pipeline.rewrite = StaticAgent("A11.Rewrite", prepared_outputs["bundle"])
    pipeline.theming = StaticAgent("A12.Theming", prepared_outputs["theme"])
    # keep builder/comparator/offer/memory agents to exercise real behaviour

    pipeline.execute()

    artifacts = {path.name for path in sandbox_dir.iterdir() if path.is_file()}
    expected_files = {
        "tools.json",
        "scope.json",
        "crawl.json",
        "content.json",
        "tech.json",
        "a11y.json",
        "seo.json",
        "security.json",
        "media.json",
        "navigation.json",
        "plan.json",
        "content_new.json",
        "theme.json",
        "build.json",
        "preview.json",
        "offer.json",
        "memory.json",
        "original_manifest.json",
    }
    assert expected_files.issubset(artifacts)

    newsite_dir = sandbox_dir / "newsite"
    assert newsite_dir.exists()
    assert any(path.name.endswith(".html") for path in newsite_dir.glob("**/*.html"))

    with open(sandbox_dir / "offer.json", "r", encoding="utf-8") as handle:
        offer_payload = json.load(handle)
    assert "Proposed improvements" in offer_payload["summary"]

    with open(sandbox_dir / "preview.json", "r", encoding="utf-8") as handle:
        preview_payload = json.load(handle)
    assert isinstance(preview_payload["diffs"], list)

