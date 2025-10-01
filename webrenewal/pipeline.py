"""Agentic post-edit pipeline orchestration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from . import configure_logging
from .config import PipelineConfig, load_pipeline_config
from .delta import DeltaPlanner
from .postedit.builder import IncrementalBuilder
from .postedit.models import ChangeSet, SiteBlock, SiteState
from .postedit.preview import PreviewGenerator
from .state import StateStore, default_state_store
from .storage import SANDBOX_DIR
from .tracing import log_event, trace
from .agents import NavigationBuilderAgent, RewriteAgent, SEOAgent, ThemingAgent
from .agents.head import HeadAgent
from .models import RenewalConfig
from .llm import default_model_for


class PostEditPipeline:
    """Coordinate delta planning, agent application and incremental builds."""

    def __init__(
        self,
        config: RenewalConfig,
        *,
        state_store: StateStore | None = None,
        logger: logging.Logger | None = None,
        pipeline_config: PipelineConfig | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("postedit")
        self.pipeline_config = pipeline_config or load_pipeline_config()
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        self.state_store = state_store or default_state_store(SANDBOX_DIR)
        self.builder = IncrementalBuilder(SANDBOX_DIR)
        self.preview = PreviewGenerator(SANDBOX_DIR)
        self.resolved_model = config.llm_model or default_model_for(config.llm_provider)
        self.rewrite_agent = RewriteAgent(model=self.resolved_model, llm_provider=config.llm_provider)
        self.theming_agent = ThemingAgent(
            design_directives=self.pipeline_config.design_directives,
            theme_style=config.theme_style,
            css_framework=config.css_framework,
        )
        self.navigation_builder = NavigationBuilderAgent(css_framework=config.css_framework)
        self.seo_agent = SEOAgent()
        self.head_agent = HeadAgent()

    # ------------------------------------------------------------------
    def execute(self) -> Dict[str, object]:
        self._log_configuration()
        site_state = self.state_store.load_site_state()
        site_state.ensure_defaults()

        if not site_state.pages:
            self._bootstrap_state(site_state)

        planner = DeltaPlanner(
            site_state=site_state,
            apply_scope=self.config.apply_scope,
            user_prompt=self.config.user_prompt,
        )
        change_set = planner.plan()
        change_hash = change_set.hash()

        log_event(
            self.logger,
            logging.INFO,
            "pipeline.change_set",
            targets=change_set.targets,
            operations=len(change_set.operations),
            hash=change_hash,
        )

        if change_set.is_empty() or self.state_store.has_change_set(change_hash):
            log_event(
                self.logger,
                logging.INFO,
                "pipeline.no_changes",
                reason="empty" if change_set.is_empty() else "duplicate",
                hash=change_hash,
            )
            latest_preview = self.state_store.latest_preview()
            preview_info = None
            if latest_preview:
                preview_info = {
                    "id": latest_preview.get("id"),
                    "path": latest_preview.get("index_path"),
                }
            build_info = None
            if site_state.build.get("latest_dist"):
                build_info = {"output_dir": site_state.build.get("latest_dist")}
            return {
                "change_set": change_set.to_dict(),
                "preview": preview_info,
                "build": build_info,
            }

        with trace("postedit.apply", logger=self.logger, operations=len(change_set.operations)):
            results = self._apply_operations(site_state, change_set)

        previous_dir = site_state.build.get("latest_dist")
        with trace("postedit.build", logger=self.logger):
            build_result = self.builder.build(site_state, change_set)

        preview_result = self.preview.generate(
            old_dir=Path(previous_dir) if previous_dir else None,
            new_dir=build_result.output_dir,
        )
        self.state_store.record_preview(
            old_dir=Path(previous_dir) if previous_dir else None,
            new_dir=build_result.output_dir,
            index_path=preview_result.index_path,
        )

        self.state_store.save_site_state(site_state)
        self.state_store.record_edit(
            scope=",".join(change_set.targets),
            prompt=self.config.user_prompt,
            change_set=change_set,
            diff_stats={
                "changed_files": [str(path.relative_to(build_result.output_dir)) for path in build_result.changed_files],
                "unchanged_files": [
                    str(path.relative_to(build_result.output_dir))
                    for path in build_result.unchanged_files
                ],
                "operations": len(change_set.operations),
                "results": results,
            },
        )

        log_event(
            self.logger,
            logging.INFO,
            "pipeline.preview.ready",
            preview_id=preview_result.preview_id,
            index=str(preview_result.index_path),
        )

        return {
            "change_set": change_set.to_dict(),
            "preview": {
                "id": preview_result.preview_id,
                "path": str(preview_result.index_path),
            },
            "build": {
                "output_dir": str(build_result.output_dir),
                "changed_files": [str(path) for path in build_result.changed_files],
            },
        }

    # ------------------------------------------------------------------
    def _apply_operations(self, state: SiteState, change_set: ChangeSet) -> Dict[str, object]:
        results: Dict[str, object] = {}
        content_ops = [op for op in change_set.operations if op.type.startswith("content.")]
        css_ops = [op for op in change_set.operations if op.type.startswith("css.")]
        nav_ops = [op for op in change_set.operations if op.type.startswith("nav.")]
        seo_ops = [op for op in change_set.operations if op.type.startswith("seo.")]
        head_ops = [op for op in change_set.operations if op.type.startswith("head.")]

        if css_ops:
            results["css"] = self.theming_agent.apply_post_edit(
                state,
                css_ops,
                user_prompt=self.config.user_prompt,
                state_store=self.state_store,
                provider=self.config.llm_provider,
                model=self.resolved_model,
            )

        if nav_ops:
            results["nav"] = self.navigation_builder.apply_post_edit(state, nav_ops)

        if content_ops:
            results["content"] = self.rewrite_agent.apply_post_edit(
                state,
                content_ops,
                user_prompt=self.config.user_prompt,
                state_store=self.state_store,
                provider=self.config.llm_provider,
                model=self.resolved_model,
            )

        if seo_ops:
            results["seo"] = self.seo_agent.apply_post_edit(
                state,
                seo_ops,
                user_prompt=self.config.user_prompt,
                state_store=self.state_store,
                provider=self.config.llm_provider,
                model=self.resolved_model,
            )

        if head_ops:
            results["head"] = self.head_agent.apply_post_edit(state, head_ops)

        return results

    def _bootstrap_state(self, state: SiteState) -> None:
        log_event(self.logger, logging.INFO, "pipeline.bootstrap")
        home = state.ensure_page("/", url="/", title="Home")
        if not home.blocks:
            home.blocks.append(
                SiteBlock(id="hero", text="Welcome to the renewed site", meta={"heading": "Welcome"})
            )
        state.nav.setdefault("items", [
            {"label": "Home", "href": "index.html"},
        ])
        state.head.setdefault("title", f"Renewed {self.config.domain}")

    def _log_configuration(self) -> None:
        log_event(
            self.logger,
            logging.INFO,
            "pipeline.config",  # log resolved config once
            config=json.loads(self.config.model_dump_json()),
        )


def run_pipeline(
    config: RenewalConfig,
    *,
    pipeline_config: Optional[PipelineConfig] = None,
    state_store: StateStore | None = None,
) -> Dict[str, object]:
    level = getattr(logging, str(config.log_level).upper(), logging.INFO)
    if isinstance(level, str):
        level = logging.INFO
    configure_logging(level=level)
    pipeline = PostEditPipeline(
        config,
        pipeline_config=pipeline_config,
        state_store=state_store,
    )
    return pipeline.execute()


__all__ = ["PostEditPipeline", "run_pipeline"]

