from __future__ import annotations

import logging
from typing import Dict

import pytest

from webrenewal.models import (
    A11yReport,
    BuildArtifact,
    ContentBlock,
    ContentBundle,
    ContentExtract,
    ContentSection,
    CrawlResult,
    DiffResult,
    MediaReport,
    MemoryRecord,
    NavModel,
    NavigationItem,
    OfferDoc,
    PageContent,
    PreviewIndex,
    RenewalAction,
    RenewalPlan,
    ScopePlan,
    SEOReport,
    SecurityReport,
    ThemeTokens,
    ToolCatalog,
    ToolInfo,
    RenewalConfig,
    TechFingerprint,
)
from webrenewal.pipeline import WebRenewalPipeline
from webrenewal.storage import SANDBOX_DIR


def _default_stage_outputs(content_extract: ContentExtract) -> Dict[str, object]:
    crawl = CrawlResult(pages=[PageContent(url="https://example.com", status_code=200, headers={}, html="<html></html>")])
    base_theme = ThemeTokens(
        colors={
            "primary": "#0b7285",
            "secondary": "#f1f3f5",
            "accent": "#ffd43b",
            "surface": "#ffffff",
            "surface_alt": "#f8f9fa",
            "text": "#212529",
            "muted": "#495057",
            "border": "#dee2e6",
        },
        typography={
            "body_family": "'Inter', sans-serif",
            "heading_family": "'Inter', sans-serif",
            "base_size": "16px",
            "scale": "1.25",
            "line_height": "1.6",
            "heading_weight": "600",
        },
        spacing={"xs": "0.25rem", "sm": "0.5rem", "md": "1rem", "lg": "1.5rem", "xl": "2.5rem"},
        radius={"sm": "0.25rem", "md": "0.5rem", "lg": "0.75rem", "pill": "999px"},
        breakpoints={"sm": "576px", "md": "768px", "lg": "992px", "xl": "1200px"},
        elevation={
            "flat": "0 1px 2px rgba(15, 23, 42, 0.06)",
            "raised": "0 12px 30px rgba(15, 23, 42, 0.12)",
            "overlay": "0 24px 60px rgba(15, 23, 42, 0.18)",
        },
        slots={},
    )
    blocks = [
        ContentBlock(title=section.title, body=section.text, type="text")
        for section in content_extract.sections
    ]
    return {
        "tool_catalog": ToolCatalog(
            tools=[ToolInfo(name="crawler", category="core", description="", usage_snippet="crawl()")]
        ),
        "scope": ScopePlan(domain="https://example.com", seed_urls=["https://example.com"], sitemap_urls=[]),
        "crawl": crawl,
        "readability": content_extract,
        "tech": TechFingerprint(frameworks=["django"], evidence={}),
        "a11y": A11yReport(score=95.0, issues=[]),
        "seo": SEOReport(score=90.0, issues=[]),
        "security": SecurityReport(score=88.0, issues=[]),
        "media": MediaReport(images=[]),
        "navigation": NavModel(items=[NavigationItem(label="Home", href="index.html")]),
        "plan": RenewalPlan(goals=["Improve"], actions=[RenewalAction(identifier="a", description="desc", impact="high", effort_hours=2.0)], estimate_hours=2.0),
        "rewrite": ContentBundle(blocks=blocks, meta_title="Title", meta_description="Desc", fallback_used=False),
        "theming": base_theme,
        "build": BuildArtifact(output_dir=str(SANDBOX_DIR / "newsite"), files=[]),
        "compare": PreviewIndex(diffs=[DiffResult(page="https://example.com", diff="")], style_deltas=["design"]),
        "offer": OfferDoc(title="Offer", summary="Summary", pricing_eur=600.0),
        "memory": MemoryRecord(key="example", payload={}),
    }


@pytest.mark.parametrize(
    "mode,expected_present,expected_absent",
    [
        ("full", {"rewrite", "theming", "build", "compare"}, set()),
        ("text-only", {"rewrite"}, {"theming", "build", "compare"}),
        ("design-only", {"theming", "build", "compare"}, {"rewrite"}),
        ("seo-only", set(), {"rewrite", "theming", "build", "compare"}),
    ],
)
def test_pipeline_modes_control_agent_execution(
    mode: str,
    expected_present: set[str],
    expected_absent: set[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = logging.getLogger(f"pipeline-{mode}")
    logger.setLevel(logging.CRITICAL)
    content_extract = ContentExtract(
        sections=[ContentSection(title="Intro", text="Body", readability_score=70.0)],
        language="en",
    )
    config = RenewalConfig(
        domain="https://example.com",
        renewal_mode=mode,
        css_framework="custom",
        theme_style="modern, blue",
        llm_provider="openai",
        llm_model=None,
        log_level="CRITICAL",
    )
    pipeline = WebRenewalPipeline(renewal_config=config, logger=logger)
    outputs = _default_stage_outputs(content_extract)
    called: list[str] = []

    def _fake_run_agent(self, agent, payload, *, stage: str):
        called.append(stage)
        return outputs[stage]

    monkeypatch.setattr(WebRenewalPipeline, "_run_agent", _fake_run_agent)

    pipeline.execute()

    assert expected_present.issubset(set(called))
    assert not expected_absent.intersection(set(called))
