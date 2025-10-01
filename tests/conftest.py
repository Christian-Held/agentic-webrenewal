"""Shared pytest fixtures for the Agentic WebRenewal test-suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from webrenewal.models import (
    A11yReport,
    BuildArtifact,
    ContentBlock,
    ContentBundle,
    ContentExtract,
    ContentSection,
    CrawlResult,
    MemoryRecord,
    NavModel,
    NavigationItem,
    OfferDoc,
    PageContent,
    PreviewIndex,
    RenewalAction,
    RenewalPlan,
    ScopePlan,
    ThemeTokens,
    ToolCatalog,
    ToolInfo,
)
from webrenewal.storage import SANDBOX_DIR


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the root directory containing reusable fixture files."""

    return Path(__file__).parent / "fixtures"


@pytest.fixture
def html_loader(fixtures_dir: Path) -> Callable[[str], str]:
    """Return a callable that loads HTML fixture files by name."""

    def _load(name: str) -> str:
        path = fixtures_dir / "html" / name
        return path.read_text(encoding="utf-8")

    return _load


@pytest.fixture
def json_fixture(fixtures_dir: Path) -> Callable[[str], dict]:
    """Return a callable that loads JSON fixture payloads by name."""

    def _load(name: str) -> dict:
        path = fixtures_dir / "json" / name
        return json.loads(path.read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def sample_scope_plan() -> ScopePlan:
    """Return a scope plan for https://example.com used across tests."""

    return ScopePlan(
        domain="https://example.com",
        seed_urls=["https://example.com"],
        sitemap_urls=["https://example.com/sitemap.xml"],
        robots_txt="User-agent: *\nAllow: /",
    )


@pytest.fixture
def sample_crawl_result(html_loader: Callable[[str], str]) -> CrawlResult:
    """Return a crawl result containing the sample HTML pages."""

    pages = [
        PageContent(
            url="https://example.com/",
            status_code=200,
            headers={
                "Content-Type": "text/html",
                "Content-Security-Policy": "default-src 'self'",
                "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "SAMEORIGIN",
            },
            html=html_loader("home.html"),
        ),
        PageContent(
            url="https://example.com/about",
            status_code=200,
            headers={
                "Content-Type": "text/html",
                "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
                "X-Content-Type-Options": "nosniff",
            },
            html=html_loader("about.html"),
        ),
    ]
    return CrawlResult(pages=pages)


@pytest.fixture
def empty_crawl_result() -> CrawlResult:
    """Return a crawl result without any pages for edge-case scenarios."""

    return CrawlResult(pages=[])


@pytest.fixture
def sample_content_extract() -> ContentExtract:
    """Return an extracted content bundle derived from the fixture pages."""

    sections = [
        ContentSection(title="Welcome to Example Corp", text="Hello world", readability_score=72.3),
        ContentSection(title="Our Story", text="History of the company", readability_score=65.0),
    ]
    return ContentExtract(sections=sections, language="en")


@pytest.fixture
def sample_plan() -> RenewalPlan:
    """Return a renewal plan with multiple actions."""

    actions = [
        RenewalAction(
            identifier="improve_alt_text",
            description="Add descriptive alternative text",
            impact="high",
            effort_hours=2.0,
        ),
        RenewalAction(
            identifier="optimize_meta",
            description="Improve metadata",
            impact="medium",
            effort_hours=1.5,
        ),
    ]
    return RenewalPlan(goals=["Accessibility >= 95"], actions=actions, estimate_hours=sum(a.effort_hours for a in actions))


@pytest.fixture
def sample_theme_tokens() -> ThemeTokens:
    """Return default theme tokens for builder/theming tests."""

    return ThemeTokens(
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


@pytest.fixture
def sample_nav_model() -> NavModel:
    """Return a navigation model with two entries."""

    return NavModel(
        items=[
            NavigationItem(label="Home", href="index.html"),
            NavigationItem(label="Contact", href="contact.html"),
        ]
    )


@pytest.fixture
def sample_content_bundle(sample_content_extract: ContentExtract) -> ContentBundle:
    """Return a content bundle derived from the sample extract."""

    blocks = [
        ContentBlock(title=section.title, body=section.text, type="text")
        for section in sample_content_extract.sections
    ]
    return ContentBundle(
        blocks=blocks,
        meta_title="Example Corp",
        meta_description="Example Corp renewed",
        fallback_used=False,
    )


@pytest.fixture
def sample_preview_index() -> PreviewIndex:
    """Return a preview index with one diff entry."""

    return PreviewIndex(diffs=[], style_deltas=[])


@pytest.fixture
def sample_offer_doc() -> OfferDoc:
    """Return a basic offer document for memory tests."""

    return OfferDoc(title="Offer", summary="Summary", pricing_eur=1200.0)


@pytest.fixture
def tool_catalog() -> ToolCatalog:
    """Return a sample tool catalog."""

    return ToolCatalog(
        tools=[
            ToolInfo(
                name="tool-one",
                category="http",
                description="Test tool",
                usage_snippet="tool_one()",
            )
        ]
    )


@pytest.fixture
def sandbox_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the sandbox directory to a temporary path for each test."""

    monkeypatch.setattr("webrenewal.storage.SANDBOX_DIR", tmp_path)
    monkeypatch.setattr("webrenewal.pipeline.SANDBOX_DIR", tmp_path)
    monkeypatch.setattr("webrenewal.agents.builder.SANDBOX_DIR", tmp_path)
    monkeypatch.setattr("webrenewal.agents.comparator.SANDBOX_DIR", tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def ensure_sandbox_dir(sandbox_dir: Path) -> None:
    """Ensure that the sandbox directory exists for tests using storage helpers."""

    sandbox_dir.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def memory_record(sample_plan: RenewalPlan, sample_offer_doc: OfferDoc) -> MemoryRecord:
    """Return a memory record stored for example.com."""

    payload = {
        "goals": ", ".join(sample_plan.goals),
        "hours": str(sample_plan.estimate_hours),
        "offer_price": f"{sample_offer_doc.pricing_eur:.2f}",
    }
    return MemoryRecord(key="example.com", payload=payload)


@pytest.fixture
def artifact_collector(tmp_path: Path) -> Iterable[Path]:
    """Return a helper for gathering files written during integration tests."""

    (tmp_path / "build").mkdir(exist_ok=True)
    return tmp_path.glob("**/*")

