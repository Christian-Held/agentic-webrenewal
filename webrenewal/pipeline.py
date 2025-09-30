"""High-level orchestration of the Agentic WebRenewal pipeline."""

from __future__ import annotations

import json
import logging
from typing import Optional

from . import configure_logging
from .agents import (
    AccessibilityAgent,
    BuilderAgent,
    ComparatorAgent,
    CrawlerAgent,
    MemoryAgent,
    MediaAgent,
    NavigationAgent,
    OfferAgent,
    PlanProposalAgent,
    ReadabilityAgent,
    RewriteAgent,
    ScopeAgent,
    SecurityAgent,
    SEOAgent,
    TechFingerprintAgent,
    ThemingAgent,
    ToolDiscoveryAgent,
)
from .models import (
    A11yReport,
    ContentBundle,
    CrawlResult,
    MemoryRecord,
    OfferDoc,
    PreviewIndex,
    RenewalPlan,
    ScopePlan,
    ThemeTokens,
    ToolCatalog,
)
from .storage import SANDBOX_DIR, write_json, write_text
from .utils import url_to_relative_path


class WebRenewalPipeline:
    """Coordinate agents to execute the renewal flow."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger("pipeline")
        self.tool_discovery = ToolDiscoveryAgent()
        self.scope = ScopeAgent()
        self.crawler = CrawlerAgent()
        self.readability = ReadabilityAgent()
        self.tech = TechFingerprintAgent()
        self.accessibility = AccessibilityAgent()
        self.seo = SEOAgent()
        self.security = SecurityAgent()
        self.media = MediaAgent()
        self.navigation = NavigationAgent()
        self.plan = PlanProposalAgent()
        self.rewrite = RewriteAgent()
        self.theming = ThemingAgent()
        self.builder = BuilderAgent()
        self.comparator = ComparatorAgent()
        self.offer = OfferAgent()
        self.memory = MemoryAgent()

    def execute(self, domain: str) -> None:
        self.logger.info("Starting WebRenewal pipeline for %s", domain)
        SANDBOX_DIR.mkdir(exist_ok=True)

        tool_catalog: ToolCatalog = self.tool_discovery.run(None)
        write_json(tool_catalog, "tools.json")

        scope_plan: ScopePlan = self.scope.run(domain)
        write_json(scope_plan, "scope.json")

        crawl_result: CrawlResult = self.crawler.run(scope_plan)
        write_json(crawl_result, "crawl.json")
        original_files = self._export_original_site(crawl_result)
        write_text(json.dumps(original_files, indent=2), "original_manifest.json")

        content_extract = self.readability.run(crawl_result)
        write_json(content_extract, "content.json")

        tech_fingerprint = self.tech.run(crawl_result)
        write_json(tech_fingerprint, "tech.json")

        a11y_report = self.accessibility.run(crawl_result)
        write_json(a11y_report, "a11y.json")

        seo_report = self.seo.run(crawl_result)
        write_json(seo_report, "seo.json")

        security_report = self.security.run(crawl_result)
        write_json(security_report, "security.json")

        media_report = self.media.run(crawl_result)
        write_json(media_report, "media.json")

        nav_model = self.navigation.run(crawl_result)
        write_json(nav_model, "navigation.json")

        renewal_plan: RenewalPlan = self.plan.run((a11y_report, seo_report, security_report, tech_fingerprint, media_report, nav_model))
        write_json(renewal_plan, "plan.json")

        content_bundle: ContentBundle = self.rewrite.run((domain, content_extract, renewal_plan))
        write_json(content_bundle, "content_new.json")

        theme_tokens: ThemeTokens = self.theming.run(renewal_plan)
        write_json(theme_tokens, "theme.json")

        build_artifact = self.builder.run((content_bundle, theme_tokens, nav_model))
        write_json(build_artifact, "build.json")

        preview_index: PreviewIndex = self.comparator.run((crawl_result, "newsite"))
        write_json(preview_index, "preview.json")

        offer_doc: OfferDoc = self.offer.run((domain, renewal_plan, preview_index))
        write_json(offer_doc, "offer.json")

        memory_record: MemoryRecord = self.memory.run((domain, renewal_plan, offer_doc))
        write_json(memory_record, "memory.json")

        self.logger.info("Pipeline execution finished. Outputs stored in %s", SANDBOX_DIR)

    def _export_original_site(self, crawl_result: CrawlResult) -> list[str]:
        """Persist a copy of the crawled pages in the sandbox."""

        original_root = SANDBOX_DIR / "original"
        original_root.mkdir(parents=True, exist_ok=True)
        exported: list[str] = []

        for page in crawl_result.pages:
            relative_path = url_to_relative_path(page.url)
            destination = original_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(page.html, encoding="utf-8")
            exported.append(str(destination.relative_to(SANDBOX_DIR)))

        return sorted(set(exported))


def run_pipeline(domain: str, log_level: int = logging.INFO) -> None:
    configure_logging(level=log_level)
    pipeline = WebRenewalPipeline()
    pipeline.execute(domain)


__all__ = ["WebRenewalPipeline", "run_pipeline"]
