"""High-level orchestration of the Agentic WebRenewal pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from . import configure_logging
from .config import PipelineConfig, load_pipeline_config
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
from .agents.base import Agent
from .llm import LLMService, create_llm_service, default_model_for, get_tracer
from .models import (
    A11yReport,
    ContentBundle,
    CrawlResult,
    MemoryRecord,
    OfferDoc,
    PreviewIndex,
    RenewalConfig,
    RenewalPlan,
    ScopePlan,
    ThemeTokens,
    ToolCatalog,
)
from .storage import SANDBOX_DIR, write_json, write_text
from .tracing import log_event, trace
from .utils import url_to_relative_path


class WebRenewalPipeline:
    """Coordinate agents to execute the renewal flow."""

    def __init__(
        self,
        renewal_config: RenewalConfig,
        *,
        logger: Optional[logging.Logger] = None,
        config: Optional[PipelineConfig] = None,
    ) -> None:
        self.logger = logger or logging.getLogger("pipeline")
        self.config = config or load_pipeline_config()
        self._renewal_config = renewal_config
        self._renewal_mode = renewal_config.renewal_mode
        self._style_hints = renewal_config.style_hints()
        self._css_framework = renewal_config.css_framework
        self._theme_style = renewal_config.theme_style
        self._llm_provider = renewal_config.llm_provider
        self._llm_client: LLMService | None = create_llm_service(
            self._llm_provider, tracer=get_tracer()
        )
        resolved_model = renewal_config.llm_model or default_model_for(self._llm_provider)
        self._llm_model = resolved_model
        if self._llm_client is None:
            log_event(
                self.logger,
                logging.WARNING,
                "pipeline.llm.unavailable",
                provider=self._llm_provider,
                model=self._llm_model,
            )
        else:
            log_event(
                self.logger,
                logging.DEBUG,
                "pipeline.llm.ready",
                provider=self._llm_provider,
                model=self._llm_model,
            )
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
        self.rewrite = RewriteAgent(
            model=self._llm_model,
            llm_client=self._llm_client,
        )
        self.theming = ThemingAgent(
            design_directives=self.config.design_directives,
            theme_style=self._theme_style,
            css_framework=self._css_framework,
        )
        self.builder = BuilderAgent(
            css_framework=self._css_framework,
            style_hints=self._theme_style,
        )
        self.comparator = ComparatorAgent(
            renewal_mode=self._renewal_mode,
            style_hints=self._theme_style,
            css_framework=self._css_framework,
        )
        self.offer = OfferAgent()
        self.memory = MemoryAgent()

    def execute(self) -> None:
        domain = self._renewal_config.domain
        log_event(
            self.logger,
            logging.INFO,
            "pipeline.start",
            domain=domain,
            sandbox=str(SANDBOX_DIR),
            renewal_mode=self._renewal_mode,
            css_framework=self._css_framework,
        )
        SANDBOX_DIR.mkdir(exist_ok=True)
        config_payload = json.dumps(
            self._renewal_config.model_dump(), indent=2, ensure_ascii=False
        )
        config_path = write_text(config_payload, "config.json")
        self._record_artifact("config.json", config_path)

        tool_catalog: ToolCatalog = self._run_agent(
            self.tool_discovery, None, stage="tool_catalog"
        )
        self._record_artifact("tools.json", write_json(tool_catalog, "tools.json"))

        scope_plan: ScopePlan = self._run_agent(self.scope, domain, stage="scope")
        self._record_artifact("scope.json", write_json(scope_plan, "scope.json"))

        crawl_result: CrawlResult = self._run_agent(
            self.crawler, scope_plan, stage="crawl"
        )
        self._record_artifact("crawl.json", write_json(crawl_result, "crawl.json"))
        original_files = self._export_original_site(crawl_result)
        self._record_artifact(
            "original_manifest.json",
            write_text(json.dumps(original_files, indent=2), "original_manifest.json"),
        )

        content_extract = self._run_agent(
            self.readability, crawl_result, stage="readability"
        )
        self._record_artifact("content.json", write_json(content_extract, "content.json"))

        tech_fingerprint = self._run_agent(self.tech, crawl_result, stage="tech")
        self._record_artifact("tech.json", write_json(tech_fingerprint, "tech.json"))

        a11y_report = self._run_agent(self.accessibility, crawl_result, stage="a11y")
        self._record_artifact("a11y.json", write_json(a11y_report, "a11y.json"))

        seo_report = self._run_agent(self.seo, crawl_result, stage="seo")
        self._record_artifact("seo.json", write_json(seo_report, "seo.json"))

        security_report = self._run_agent(self.security, crawl_result, stage="security")
        self._record_artifact(
            "security.json", write_json(security_report, "security.json")
        )

        media_report = self._run_agent(self.media, crawl_result, stage="media")
        self._record_artifact("media.json", write_json(media_report, "media.json"))

        nav_model = self._run_agent(self.navigation, crawl_result, stage="navigation")
        self._record_artifact("navigation.json", write_json(nav_model, "navigation.json"))

        renewal_plan: RenewalPlan = self._run_agent(
            self.plan,
            (
                a11y_report,
                seo_report,
                security_report,
                tech_fingerprint,
                media_report,
                nav_model,
            ),
            stage="plan",
        )
        self._record_artifact("plan.json", write_json(renewal_plan, "plan.json"))

        run_rewrite = self._renewal_mode in {"full", "text-only"}
        run_design = self._renewal_mode in {"full", "design-only"}

        content_bundle: ContentBundle | None = None
        if run_rewrite:
            content_bundle = self._run_agent(
                self.rewrite, (domain, content_extract, renewal_plan), stage="rewrite"
            )
            self._record_artifact(
                "content_new.json", write_json(content_bundle, "content_new.json")
            )
        elif run_design:
            content_bundle = self.rewrite._fallback_bundle(domain, content_extract)
            log_event(
                self.logger,
                logging.INFO,
                "pipeline.design_only.content",
                blocks=len(content_bundle.blocks),
                fallback=content_bundle.fallback_used,
            )
            self._record_artifact(
                "content_new.json", write_json(content_bundle, "content_new.json")
            )

        theme_tokens: ThemeTokens | None = None
        if run_design:
            theme_tokens = self._run_agent(
                self.theming, renewal_plan, stage="theming"
            )
            self._record_artifact("theme.json", write_json(theme_tokens, "theme.json"))

        build_artifact: BuildArtifact | None = None
        if run_design and content_bundle and theme_tokens:
            build_artifact = self._run_agent(
                self.builder,
                (content_bundle, theme_tokens, nav_model),
                stage="build",
            )
            self._record_artifact("build.json", write_json(build_artifact, "build.json"))

        if run_design and build_artifact:
            preview_index: PreviewIndex = self._run_agent(
                self.comparator, (crawl_result, "newsite"), stage="compare"
            )
        else:
            preview_index = PreviewIndex(
                diffs=[],
                style_deltas=self._style_notes(),
            )
        self._record_artifact("preview.json", write_json(preview_index, "preview.json"))

        offer_doc: OfferDoc = self._run_agent(
            self.offer, (domain, renewal_plan, preview_index), stage="offer"
        )
        self._record_artifact("offer.json", write_json(offer_doc, "offer.json"))

        memory_record: MemoryRecord = self._run_agent(
            self.memory, (domain, renewal_plan, offer_doc), stage="memory"
        )
        self._record_artifact("memory.json", write_json(memory_record, "memory.json"))

        artifact_count = sum(1 for path in SANDBOX_DIR.rglob("*") if path.is_file())
        log_event(
            self.logger,
            logging.INFO,
            "pipeline.finish",
            domain=domain,
            sandbox=str(SANDBOX_DIR),
            artifacts=artifact_count,
        )

    def _export_original_site(self, crawl_result: CrawlResult) -> list[str]:
        """Persist a copy of the crawled pages in the sandbox."""

        original_root = SANDBOX_DIR / "original"
        original_root.mkdir(parents=True, exist_ok=True)
        exported: list[str] = []

        with trace(
            "pipeline.export_original", logger=self.logger, pages=len(crawl_result.pages)
        ) as span:
            for page in crawl_result.pages:
                relative_path = url_to_relative_path(page.url)
                destination = original_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(page.html, encoding="utf-8")
                exported.append(str(destination.relative_to(SANDBOX_DIR)))
                span.note(url=page.url, path=str(destination))

        return sorted(set(exported))

    def _run_agent(self, agent: Agent[Any, Any], payload: Any, *, stage: str):
        """Execute ``agent`` under a trace span and return its output."""

        agent_label = getattr(agent, "name", agent.__class__.__name__)
        metadata = {
            "agent": agent_label,
            "stage": stage,
            "module": agent.__class__.__module__,
            "class": agent.__class__.__name__,
        }

        log_event(
            self.logger,
            logging.INFO,
            "agent.start",
            **metadata,
        )

        with trace(f"{agent_label}.run", logger=self.logger, **metadata):
            try:
                result = agent.run(payload)
            except Exception as exc:
                log_event(
                    self.logger,
                    logging.ERROR,
                    "agent.error",
                    **metadata,
                    error=str(exc),
                    exception=exc.__class__.__name__,
                    exc_info=True,
                )
                raise

        log_event(
            self.logger,
            logging.INFO,
            "agent.finish",
            **metadata,
            summary=self._summarise_output(result),
        )
        return result

    def _summarise_output(self, output: Any) -> Dict[str, Any]:
        """Provide a compact summary of an agent output for logging."""

        summary: Dict[str, Any] = {"type": type(output).__name__}

        if hasattr(output, "pages"):
            summary["pages"] = len(getattr(output, "pages", []))
        if hasattr(output, "sections"):
            summary["sections"] = len(getattr(output, "sections", []))
        if hasattr(output, "blocks"):
            summary["blocks"] = len(getattr(output, "blocks", []))
        if hasattr(output, "issues"):
            summary["issues"] = len(getattr(output, "issues", []))
        if hasattr(output, "items"):
            summary["items"] = len(getattr(output, "items", []))
        if hasattr(output, "images"):
            summary["images"] = len(getattr(output, "images", []))
        if hasattr(output, "tools"):
            summary["tools"] = len(getattr(output, "tools", []))
        if hasattr(output, "fallback_used"):
            summary["fallback_used"] = getattr(output, "fallback_used")
        if hasattr(output, "score"):
            summary["score"] = getattr(output, "score")
        if hasattr(output, "estimate_hours"):
            summary["estimate_hours"] = getattr(output, "estimate_hours")
        if hasattr(output, "title") and isinstance(getattr(output, "title"), str):
            summary["title"] = getattr(output, "title")

        if isinstance(output, dict):
            summary["keys"] = sorted(output.keys())
        elif isinstance(output, (list, tuple, set)):
            summary["count"] = len(output)

        return summary

    def _record_artifact(self, filename: str, path: Path) -> None:
        """Emit structured logs for stored artifacts."""

        log_event(
            self.logger,
            logging.INFO,
            "pipeline.artifact",
            filename=filename,
            path=str(path),
        )

    def _style_notes(self) -> list[str]:
        """Return human-readable descriptions of the requested styling."""

        notes: list[str] = []
        if self._css_framework:
            notes.append(f"Framework target: {self._css_framework}")
        if self._style_hints:
            notes.append(f"Style hints: {', '.join(self._style_hints)}")
        return notes


def run_pipeline(
    config: RenewalConfig,
    *,
    pipeline_config: Optional[PipelineConfig] = None,
) -> None:
    level = getattr(logging, str(config.log_level).upper(), logging.INFO)
    if isinstance(level, str):
        level = logging.INFO
    configure_logging(level=level)
    pipeline = WebRenewalPipeline(
        renewal_config=config,
        config=pipeline_config,
    )
    pipeline.execute()


__all__ = ["WebRenewalPipeline", "run_pipeline"]
