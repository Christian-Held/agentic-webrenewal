"""Core orchestration logic for issuing rewrite requests."""

from __future__ import annotations

import asyncio
import json
import logging
from itertools import zip_longest
from typing import Any, Dict, List, Optional, Sequence

from openai import AsyncOpenAI

from ...models import ContentBlock, ContentBundle, ContentExtract, RenewalPlan
from ...tracing import log_event, trace
from ...utils import domain_to_display_name
from .parsing import extract_response_text, parse_json_payload
from .prompts import (
    build_action_summaries,
    build_guidelines,
    build_request,
    build_section_payload,
    build_user_instruction,
)


class SectionRewriteCoordinator:
    """Manage prompt dispatching and aggregation for section rewrites."""

    def __init__(
        self,
        *,
        model: str,
        temperature: float,
        max_parallel_requests: int,
        logger: logging.Logger,
        agent_name: str,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._max_parallel = max(1, max_parallel_requests)
        self._logger = logger
        self._agent_name = agent_name

    async def rewrite(
        self,
        client: AsyncOpenAI,
        domain: str,
        content: ContentExtract,
        plan: RenewalPlan,
    ) -> ContentBundle:
        if not content.sections:
            raise ValueError("No sections available for rewrite")

        site_label = domain_to_display_name(domain)
        action_summaries = build_action_summaries(plan.actions)
        guidelines = build_guidelines(domain, plan)

        semaphore = asyncio.Semaphore(self._max_parallel)
        tasks = [
            self._rewrite_single(
                client,
                domain,
                content,
                plan,
                guidelines,
                action_summaries,
                index,
                semaphore,
            )
            for index in range(len(content.sections))
        ]

        with trace(
            "rewrite.parallel",
            logger=self._logger,
            agent=self._agent_name,
            domain=domain,
            sections=len(tasks),
            parallel=self._max_parallel,
        ):
            responses = await asyncio.gather(*tasks)

        return self._aggregate(domain, site_label, content, responses)

    async def _rewrite_single(
        self,
        client: AsyncOpenAI,
        domain: str,
        content: ContentExtract,
        plan: RenewalPlan,
        guidelines: str,
        action_summaries: List[dict[str, Any]],
        section_index: int,
        semaphore: asyncio.Semaphore,
    ) -> dict[str, Any]:
        payload = build_section_payload(domain, content, section_index, plan, action_summaries)
        instruction = build_user_instruction(
            payload,
            section_index,
            len(content.sections),
            include_meta=section_index == 0,
        )
        request = build_request(self._model, self._temperature, guidelines, instruction)

        async with semaphore:
            with trace(
                "rewrite.llm_request",
                logger=self._logger,
                agent=self._agent_name,
                domain=domain,
                model=self._model,
                temperature=self._temperature,
                section=section_index + 1,
                sections=len(content.sections),
            ) as span:
                response, mode = await self._dispatch_request(client, request)
                span.note(mode=mode)

        raw_output = extract_response_text(response)
        if not raw_output:
            raise ValueError("No textual output returned by LLM")

        try:
            parsed = parse_json_payload(raw_output)
        except json.JSONDecodeError as exc:
            log_event(
                self._logger,
                logging.DEBUG,
                "rewrite.llm.parse_failure",
                agent=self._agent_name,
                domain=domain,
                section=section_index + 1,
                sample=raw_output[:500],
                error=repr(exc),
            )
            raise

        return parsed

    async def _dispatch_request(
        self, client: AsyncOpenAI, request: Dict[str, Any]
    ) -> tuple[Any, str]:
        try:
            response = await client.responses.create(
                **request,
                response_format={"type": "json_object"},
            )
            return response, "json_object"
        except TypeError as exc:
            if "response_format" not in str(exc):
                raise
            log_event(
                self._logger,
                logging.DEBUG,
                "rewrite.llm.legacy_client",
                agent=self._agent_name,
                error=repr(exc),
            )
            response = await client.responses.create(**request)
            return response, "fallback_request"

    def _aggregate(
        self,
        domain: str,
        site_label: str,
        content: ContentExtract,
        responses: Sequence[dict[str, Any]],
    ) -> ContentBundle:
        blocks_payload: List[dict[str, Any]] = []
        meta_title: Optional[str] = None
        meta_description: Optional[str] = None

        for index, data in enumerate(responses, start=1):
            block_list = data.get("blocks") if isinstance(data, dict) else None
            if not isinstance(block_list, list):
                raise ValueError("Missing blocks in LLM response")

            blocks_payload.extend(block_list)
            meta_title = meta_title or self._extract_meta(data, "meta_title")
            meta_description = meta_description or self._extract_meta(
                data, "meta_description"
            )

            self._log_section_stats(domain, index, len(block_list))

        expected_sections = len(content.sections)
        if len(blocks_payload) != expected_sections:
            log_event(
                self._logger,
                logging.WARNING,
                "rewrite.blocks.mismatch.aggregate",
                agent=self._agent_name,
                domain=domain,
                received=len(blocks_payload),
                expected=expected_sections,
            )

        blocks = self._build_content_blocks(content.sections, blocks_payload, domain)

        if not meta_title:
            meta_title = content.sections[0].title if content.sections else None
        if not meta_description:
            meta_description = (
                f"Refreshed content for {site_label}, generated via Agentic WebRenewal after analysing {domain}."
            )

        return ContentBundle(
            blocks=blocks,
            meta_title=meta_title.strip() if isinstance(meta_title, str) else None,
            meta_description=meta_description.strip(),
            fallback_used=False,
        )

    def _extract_meta(self, data: dict[str, Any], key: str) -> Optional[str]:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _log_section_stats(self, domain: str, section: int, received: int) -> None:
        log_event(
            self._logger,
            logging.DEBUG,
            "rewrite.llm.response",
            agent=self._agent_name,
            domain=domain,
            section=section,
            received=received,
            expected=1,
        )
        if received != 1:
            log_event(
                self._logger,
                logging.WARNING,
                "rewrite.blocks.mismatch",
                agent=self._agent_name,
                domain=domain,
                section=section,
                received=received,
                expected=1,
            )

    def _build_content_blocks(
        self,
        sections: Sequence[Any],
        payloads: Sequence[dict[str, Any]],
        domain: str,
    ) -> List[ContentBlock]:
        blocks: List[ContentBlock] = []
        for index, (section, payload) in enumerate(zip_longest(sections, payloads), start=1):
            if payload is None:
                if section is None:
                    continue
                log_event(
                    self._logger,
                    logging.DEBUG,
                    "rewrite.blocks.fill_missing",
                    agent=self._agent_name,
                    domain=domain,
                    index=index,
                    title=getattr(section, "title", None),
                )
                body = getattr(section, "text", "")
                blocks.append(
                    ContentBlock(
                        title=getattr(section, "title", None) or f"Section {index}",
                        body=body,
                    )
                )
                continue

            if not isinstance(payload, dict):
                raise ValueError("Block data is not an object")

            body = payload.get("body")
            if not isinstance(body, str) or not body.strip():
                raise ValueError("Invalid block body returned by LLM")

            title = payload.get("title")
            if section is None:
                fallback_title = title or f"Additional Section {index}"
            else:
                fallback_title = title or getattr(section, "title", None) or f"Section {index}"

            blocks.append(
                ContentBlock(
                    title=fallback_title,
                    body=body.strip(),
                )
            )

        return blocks


__all__ = ["SectionRewriteCoordinator"]
