"""Implementation of the A11 Rewrite agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from itertools import zip_longest
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator

from ..llm import (
    JSONCompletion,
    JSONValidationError,
    LLMService,
    create_llm_service,
    default_model_for,
)
from ..postedit.models import ChangeOperation, SiteBlock, SiteState
from ..state import StateStore

from .base import Agent
from ..models import ContentBlock, ContentBundle, ContentExtract, RenewalPlan
from ..tracing import log_event, trace
from ..utils import domain_to_display_name

RewriteInput = Union[
    Tuple[ContentExtract, RenewalPlan],
    Tuple[str, ContentExtract, RenewalPlan],
]


_SECTION_TYPES = {"hero", "faq", "contact", "text"}


class RewriteBlockModel(BaseModel):
    """Structured representation of a rewritten block."""

    title: str
    body: str
    type: str
    data: Dict[str, Any] | None = None

    @field_validator("title", "body", "type")
    @classmethod
    def _ensure_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Block fields must be non-empty strings")
        return value.strip()


class RewriteResponseModel(BaseModel):
    """JSON schema returned by the rewrite LLM."""

    meta_title: str | None = None
    meta_description: str | None = None
    blocks: List[RewriteBlockModel] = Field(default_factory=list)

    @field_validator("blocks")
    @classmethod
    def _ensure_blocks(
        cls, value: List[RewriteBlockModel]
    ) -> List[RewriteBlockModel]:
        if not value:
            raise ValueError("Blocks must not be empty")
        return value


class RewriteAgent(Agent[RewriteInput, ContentBundle]):
    """Produce refreshed copy for the website."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.4,
        *,
        max_parallel_requests: int = 4,
        llm_client: Optional[LLMService] = None,
        llm_provider: Optional[str] = None,
    ) -> None:
        super().__init__(name="A11.Rewrite")
        self._llm_provider = (
            llm_provider
            or os.getenv("LLM_PROVIDER")
            or "openai"
        )
        resolved_model = model or default_model_for(self._llm_provider)
        self._model = resolved_model
        self._temperature = temperature
        self._llm_client: Optional[LLMService] = llm_client
        self._max_parallel = max(1, max_parallel_requests)

    def run(self, data: RewriteInput) -> ContentBundle:  # type: ignore[override]
        domain, content, plan = self._normalise_input(data)
        client = self._get_client()

        log_event(
            self.logger,
            logging.DEBUG,
            "rewrite.run",
            agent=self.name,
            domain=domain,
            sections=len(content.sections),
            goals=len(plan.goals),
        )
        if client is None:
            log_event(
                self.logger,
                logging.WARNING,
                "rewrite.llm.unavailable",
                agent=self.name,
                domain=domain,
            )
            bundle = self._fallback_bundle(domain, content)
            log_event(
                self.logger,
                logging.INFO,
                "rewrite.fallback",
                agent=self.name,
                domain=domain,
                reason="missing_llm_client",
                blocks=len(bundle.blocks),
            )
            return bundle

        try:
            bundle = self._rewrite_with_llm(client, domain, content, plan)
        except Exception as exc:
            log_event(
                self.logger,
                logging.WARNING,
                "rewrite.llm.failure",
                agent=self.name,
                domain=domain,
                error=str(exc),
                exception=exc.__class__.__name__,
                exc_info=True,
            )
            bundle = self._fallback_bundle(domain, content)
            log_event(
                self.logger,
                logging.INFO,
                "rewrite.fallback",
                agent=self.name,
                domain=domain,
                reason="llm_failure",
                error=str(exc),
                exception=exc.__class__.__name__,
                blocks=len(bundle.blocks),
            )
            return bundle

        log_event(
            self.logger,
            logging.INFO,
            "rewrite.success",
            agent=self.name,
            domain=domain,
            blocks=len(bundle.blocks),
            fallback=bundle.fallback_used,
        )
        return bundle

    # ------------------------------------------------------------------
    def apply_post_edit(
        self,
        state: SiteState,
        operations: list[ChangeOperation],
        *,
        user_prompt: str | None,
        state_store: StateStore | None = None,
        provider: str = "openai",
        model: str = "gpt-4.1-mini",
    ) -> dict:
        """Apply ``content.rewrite`` operations to the site state."""

        changed_blocks = 0
        generated_samples: list[str] = []
        prompt_preview = (user_prompt or "").strip()[:200]
        for op in operations:
            if op.type != "content.rewrite" or not op.page or not op.block_id:
                continue
            page = state.find_page(op.page)
            if not page:
                continue
            block = next((b for b in page.blocks if b.id == op.block_id), None)
            if block is None:
                continue
            original = block.text
            rewritten = self._synthesise_text(original, user_prompt or "", op.payload)
            block.text = rewritten
            if op.payload.get("call_to_action"):
                block.meta["call_to_action"] = self._build_cta(block, user_prompt)
            changed_blocks += 1
            generated_samples.append(rewritten[:120])

        if state_store and changed_blocks:
            response_preview = " | ".join(sample for sample in generated_samples[:3])
            state_store.record_trace(
                provider=provider,
                model=model,
                request_trunc=prompt_preview,
                response_trunc=response_preview,
                duration_ms=12 * max(1, changed_blocks),
                tokens={"input": len(prompt_preview.split()), "output": len(response_preview.split())},
            )

        return {"changed_blocks": changed_blocks}

    def _synthesise_text(self, original: str, prompt: str, payload: dict) -> str:
        length_policy = payload.get("length", "default")
        base = original.strip()
        if not base:
            base = "Updated content block"
        extension = ""
        if length_policy == "longer":
            extension = f" {prompt.strip()[:80]}" if prompt else " Expanded with additional context."
        elif length_policy == "default" and prompt:
            extension = f" ({prompt.strip()[:40]})"
        result = f"{base}{extension}".strip()
        return result

    def _build_cta(self, block: ContentBlock | SiteBlock, prompt: str | None) -> str:  # type: ignore[name-defined]
        base = prompt or "Get in touch"
        return f"{base.strip().capitalize()} today."

    def _normalise_input(
        self, data: RewriteInput
    ) -> Tuple[str, ContentExtract, RenewalPlan]:
        """Accept legacy ``(content, plan)`` tuples alongside new domain-aware data."""

        if len(data) == 3:
            domain, content, plan = data  # type: ignore[misc]
        elif len(data) == 2:
            content, plan = data  # type: ignore[misc]
            domain = None
        else:
            raise ValueError("RewriteAgent expects a 2- or 3-item tuple")

        if not isinstance(content, ContentExtract) or not isinstance(plan, RenewalPlan):
            raise TypeError("RewriteAgent received unexpected input types")

        resolved_domain = domain or getattr(content, "domain", None) or getattr(plan, "domain", None)
        if not resolved_domain:
            resolved_domain = "unknown-site"

        return resolved_domain, content, plan

    def _get_client(self) -> Optional[LLMService]:
        """Initialise the configured LLM client if credentials are present."""

        if self._llm_client is None:
            self._llm_client = create_llm_service(self._llm_provider)
        return self._llm_client

    def _rewrite_with_llm(
        self, client: LLMService, domain: str, content: ContentExtract, plan: RenewalPlan
    ) -> ContentBundle:
        """Leverage the configured LLM provider to refresh the site copy."""

        return self._run_async(
            self._rewrite_with_llm_async(client, domain, content, plan)
        )

    async def _rewrite_with_llm_async(
        self,
        client: LLMService,
        domain: str,
        content: ContentExtract,
        plan: RenewalPlan,
    ) -> ContentBundle:
        """Perform concurrent rewrite requests for each section."""

        site_label = domain_to_display_name(domain)
        goals_text = ", ".join(plan.goals) if plan.goals else "general improvements"
        action_summaries = [
            {
                "id": action.identifier,
                "description": action.description,
                "impact": action.impact,
                "effort_hours": action.effort_hours,
            }
            for action in plan.actions
        ]
        total_sections = len(content.sections)
        if total_sections == 0:
            raise ValueError("No sections available for rewrite")

        semaphore = asyncio.Semaphore(self._max_parallel)

        tasks = [
            self._rewrite_section(
                client,
                domain,
                site_label,
                action_summaries,
                content,
                plan,
                goals_text,
                index,
                section,
                total_sections,
                semaphore,
            )
            for index, section in enumerate(content.sections)
        ]

        with trace(
            "rewrite.parallel",
            logger=self.logger,
            agent=self.name,
            domain=domain,
            sections=total_sections,
            parallel=self._max_parallel,
        ):
            responses = await asyncio.gather(*tasks)

        aggregated_blocks: List[dict[str, Any]] = []
        meta_title: Optional[str] = None
        meta_description: Optional[str] = None

        for index, data in enumerate(responses, start=1):
            if not isinstance(data, dict):
                raise ValueError("Unexpected payload type from LLM")

            block_payload = data.get("blocks")
            if not isinstance(block_payload, list):
                raise ValueError("Missing blocks in LLM response")
            aggregated_blocks.extend(block_payload)

            if meta_title is None:
                candidate_title = data.get("meta_title")
                if isinstance(candidate_title, str) and candidate_title.strip():
                    meta_title = candidate_title.strip()

            if meta_description is None:
                candidate_desc = data.get("meta_description")
                if isinstance(candidate_desc, str) and candidate_desc.strip():
                    meta_description = candidate_desc.strip()

            log_event(
                self.logger,
                logging.DEBUG,
                "rewrite.llm.response",
                agent=self.name,
                domain=domain,
                section=index,
                keys=sorted(data.keys()),
                received=len(block_payload),
                expected=1,
            )
            if len(block_payload) != 1:
                log_event(
                    self.logger,
                    logging.WARNING,
                    "rewrite.blocks.mismatch",
                    agent=self.name,
                    domain=domain,
                    section=index,
                    received=len(block_payload),
                    expected=1,
                )

        expected_sections = len(content.sections)
        received_blocks = len(aggregated_blocks)
        if received_blocks != expected_sections:
            log_event(
                self.logger,
                logging.WARNING,
                "rewrite.blocks.mismatch.aggregate",
                agent=self.name,
                domain=domain,
                received=received_blocks,
                expected=expected_sections,
            )

        blocks: List[ContentBlock] = []
        for index, (section, block_data) in enumerate(
            zip_longest(content.sections, aggregated_blocks),
            start=1,
        ):
            if block_data is None:
                if section is None:
                    log_event(
                        self.logger,
                        logging.DEBUG,
                        "rewrite.blocks.skip",
                        agent=self.name,
                        domain=domain,
                        index=index,
                    )
                    continue
                log_event(
                    self.logger,
                    logging.DEBUG,
                    "rewrite.blocks.fill_missing",
                    agent=self.name,
                    domain=domain,
                    index=index,
                    title=section.title if section else None,
                )
                fallback_body = section.text or ""
                blocks.append(
                    ContentBlock(
                        title=section.title or f"Section {index}",
                        body=fallback_body,
                        type="text",
                    )
                )
                continue

            if not isinstance(block_data, dict):
                raise ValueError("Block data is not an object")

            title = block_data.get("title")
            body = block_data.get("body")
            if not isinstance(body, str) or not body.strip():
                raise ValueError("Invalid block body returned by LLM")

            raw_type = block_data.get("type")
            block_type = self._normalise_block_type(raw_type)
            data_payload = block_data.get("data")
            if isinstance(data_payload, dict):
                block_data_payload: Dict[str, Any] = data_payload
            else:
                block_data_payload = {}

            if section is None:
                fallback_title = title or f"Additional Section {index}"
            else:
                fallback_title = title or section.title or f"Section {index}"

            blocks.append(
                ContentBlock(
                    title=fallback_title,
                    body=body.strip(),
                    type=block_type,
                    data=block_data_payload,
                )
            )

        if meta_title is None or not meta_title.strip():
            meta_title = content.sections[0].title if content.sections else None

        if meta_description is None or not meta_description.strip():
            meta_description = (
                f"Refreshed content for {site_label}, generated via Agentic WebRenewal after analysing {domain}."
            )

        return ContentBundle(
            blocks=blocks,
            meta_title=meta_title.strip() if meta_title else None,
            meta_description=meta_description.strip(),
            fallback_used=False,
        )

    async def _rewrite_section(
        self,
        client: LLMService,
        domain: str,
        site_label: str,
        action_summaries: List[dict[str, Any]],
        content: ContentExtract,
        plan: RenewalPlan,
        goals_text: str,
        index: int,
        section: Any,
        total_sections: int,
        semaphore: asyncio.Semaphore,
    ) -> dict[str, Any]:
        section_payload = {
            "domain": domain,
            "site_name": site_label,
            "language": content.language or "auto",
            "goals": plan.goals,
            "actions": action_summaries,
            "section": {
                "title": section.title,
                "text": section.text,
                "readability_score": section.readability_score,
                "index": index + 1,
                "total": total_sections,
            },
        }

        include_meta = index == 0
        guidelines = (
            f"You are an expert marketing copywriter refreshing the website for {site_label} ({domain}). "
            "Blend the renewal goals and action plan into persuasive, accessible copy while keeping the original language. "
            "Highlight user benefits, improve clarity, and retain any medical or legal disclaimers."
        )
        meta_clause = (
            "Include 'meta_title' and 'meta_description' fields only if this is the first section. "
            if include_meta
            else "Set 'meta_title' and 'meta_description' to null for this section. "
        )
        user_instruction = (
            "Return JSON with keys 'meta_title', 'meta_description' and 'blocks'. "
            "Provide exactly one entry in 'blocks' with 'title', 'body', and 'type'. "
            "Allowed block types are hero, faq, contact, or text (use 'text' when unsure). "
            "For hero, faq, or contact sections, include a 'data' object capturing structured details. "
            f"Align the tone with the goals: {', '.join(plan.goals) if plan.goals else goals_text}. "
            "Keep HTML safe (no Markdown). "
            f"This is section {index + 1} of {total_sections}. "
            + meta_clause
            + "Here is the source data: "
            + json.dumps(section_payload, ensure_ascii=False)
        )
        request_kwargs = {
            "model": self._model,
            "temperature": self._temperature,
            "input": [
                {
                    "role": "system",
                    "content": guidelines,
                },
                {
                    "role": "user",
                    "content": user_instruction,
                },
            ],
        }

        async with semaphore:
            with trace(
                "rewrite.llm_request",
                logger=self.logger,
                agent=self.name,
                domain=domain,
                model=self._model,
                temperature=self._temperature,
                section=index + 1,
                sections=total_sections,
            ) as span:
                response = await client.complete_json(
                    request_kwargs["input"],
                    model=request_kwargs["model"],
                    temperature=request_kwargs.get("temperature"),
                    schema=RewriteResponseModel,
                )
                span.note(mode="json_object")

        payload = response.payload
        if not isinstance(payload, RewriteResponseModel):
            raise ValueError("Unexpected payload type from LLM")

        return payload.model_dump(mode="json")

    def _run_async(self, coro: Any) -> Any:
        """Execute ``coro`` ensuring compatibility with running event loops."""

        try:
            return asyncio.run(coro)
        except RuntimeError as exc:  # pragma: no cover - defensive branch
            if "asyncio.run()" not in str(exc):
                raise
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(coro)
            finally:
                asyncio.set_event_loop(None)
                loop.close()

    def _fallback_bundle(self, domain: str, content: ContentExtract) -> ContentBundle:
        """Provide a deterministic rewrite when the LLM is unavailable."""

        site_label = domain_to_display_name(domain)
        fallback_notice = f"[Automated fallback for {site_label}]"

        blocks: List[ContentBlock] = []
        for index, section in enumerate(content.sections, start=1):
            score = section.readability_score
            if score is None:
                readability = "n/a"
            else:
                readability = f"{score:.1f}"
            refreshed = (
                f"{fallback_notice} Original readability score: {readability}.\n\n{section.text}"
            )
            blocks.append(
                ContentBlock(
                    title=section.title or f"Section {index}",
                    body=refreshed,
                    type="text",
                )
            )

        meta_title = f"{site_label} – Updated Website Experience"
        meta_description = (
            f"Fallback content for {site_label}. Review and replace once automated rewriting succeeds."
        )
        return ContentBundle(
            blocks=blocks,
            meta_title=meta_title,
            meta_description=meta_description,
            fallback_used=True,
        )

    def _normalise_block_type(self, raw_type: Any) -> str:
        if isinstance(raw_type, str):
            candidate = raw_type.strip().lower()
            if candidate in _SECTION_TYPES:
                return candidate
        return "text"


__all__ = ["RewriteAgent"]
