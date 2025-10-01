"""Implementation of the A11 Rewrite agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from itertools import zip_longest
from typing import Any, List, Optional, Tuple, Union

from openai import AsyncOpenAI, OpenAIError

from .base import Agent
from ..models import ContentBlock, ContentBundle, ContentExtract, RenewalPlan
from ..tracing import log_event, trace
from ..utils import domain_to_display_name

RewriteInput = Union[
    Tuple[ContentExtract, RenewalPlan],
    Tuple[str, ContentExtract, RenewalPlan],
]


class RewriteAgent(Agent[RewriteInput, ContentBundle]):
    """Produce refreshed copy for the website."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.4,
        *,
        max_parallel_requests: int = 4,
    ) -> None:
        super().__init__(name="A11.Rewrite")
        self._model = model
        self._temperature = temperature
        self._client: Optional[AsyncOpenAI] = None
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
                "rewrite.openai.missing_key",
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
                reason="missing_openai_key",
                blocks=len(bundle.blocks),
            )
            return bundle

        try:
            bundle = self._rewrite_with_llm(client, domain, content, plan)
        except (OpenAIError, ValueError, json.JSONDecodeError) as exc:
            log_event(
                self.logger,
                logging.WARNING,
                "rewrite.llm.failure",
                agent=self.name,
                domain=domain,
                error=repr(exc),
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
                error=repr(exc),
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

    def _get_client(self) -> Optional[AsyncOpenAI]:
        """Initialise the OpenAI client if credentials are configured."""

        if self._client is not None:
            return self._client

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        self._client = AsyncOpenAI(api_key=api_key)
        return self._client

    def _rewrite_with_llm(
        self, client: AsyncOpenAI, domain: str, content: ContentExtract, plan: RenewalPlan
    ) -> ContentBundle:
        """Leverage the OpenAI Responses API to refresh the site copy."""

        return self._run_async(
            self._rewrite_with_llm_async(client, domain, content, plan)
        )

    async def _rewrite_with_llm_async(
        self, client: AsyncOpenAI, domain: str, content: ContentExtract, plan: RenewalPlan
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
                    self.logger.debug("Skipping empty section/block at index %s", index)
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
                    )
                )
                continue

            if not isinstance(block_data, dict):
                raise ValueError("Block data is not an object")

            title = block_data.get("title")
            body = block_data.get("body")
            if not isinstance(body, str) or not body.strip():
                raise ValueError("Invalid block body returned by LLM")

            if section is None:
                fallback_title = title or f"Additional Section {index}"
            else:
                fallback_title = title or section.title or f"Section {index}"

            blocks.append(
                ContentBlock(
                    title=fallback_title,
                    body=body.strip(),
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
        client: AsyncOpenAI,
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
            "Provide exactly one entry in 'blocks' with 'title' and 'body'. "
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
                try:
                    response = await client.responses.create(
                        **request_kwargs,
                        response_format={"type": "json_object"},
                    )
                    span.note(mode="json_object")
                except TypeError as exc:
                    if "response_format" not in str(exc):
                        span.note(error=repr(exc))
                        raise

                    log_event(
                        self.logger,
                        logging.DEBUG,
                        "rewrite.llm.legacy_client",
                        agent=self.name,
                        domain=domain,
                        error=repr(exc),
                        section=index + 1,
                    )
                    response = await client.responses.create(**request_kwargs)
                    span.note(mode="fallback_request")

        raw_output = self._extract_response_text(response)
        if not raw_output:
            raise ValueError("No textual output returned by LLM")

        cleaned_output = self._strip_json_fences(raw_output)
        if not cleaned_output:
            raise ValueError("Empty JSON payload returned by LLM")
        try:
            data = json.loads(cleaned_output)
        except json.JSONDecodeError:
            log_event(
                self.logger,
                logging.DEBUG,
                "rewrite.llm.parse_failure",
                agent=self.name,
                domain=domain,
                section=index + 1,
                sample=raw_output[:500],
            )
            raise

        return data

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

    def _extract_response_text(self, response: Any) -> str:
        """Normalise the various OpenAI client payload shapes into a JSON string."""

        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        parts: List[str] = []
        for item in getattr(response, "output", []) or []:
            for content_item in getattr(item, "content", []) or []:
                text_value = self._coerce_content_text(content_item)
                if text_value:
                    parts.append(text_value)
        if parts:
            return "".join(parts)

        structured = self._safe_model_dump(response)
        if structured:
            candidate = self._locate_rewrite_payload(structured)
            if candidate:
                return candidate

        return ""

    def _coerce_content_text(self, content_item: Any) -> Optional[str]:
        content_type = getattr(content_item, "type", None)

        if content_type in {"output_json", "json"}:
            json_payload = getattr(content_item, "json", None)
            if isinstance(json_payload, dict):
                return json.dumps(json_payload)
            if hasattr(json_payload, "model_dump"):
                try:
                    dumped = json_payload.model_dump()
                except Exception:  # pragma: no cover - defensive
                    dumped = None
                if isinstance(dumped, dict):
                    return json.dumps(dumped)

        if content_type in {"output_text", "text", None}:
            text_obj = getattr(content_item, "text", None)
            normalised = self._normalise_text_value(text_obj)
            if normalised:
                return normalised

        return None

    def _normalise_text_value(self, text_obj: Any) -> Optional[str]:
        if text_obj is None:
            return None
        if isinstance(text_obj, str):
            return text_obj
        if hasattr(text_obj, "value"):
            value = getattr(text_obj, "value")
            if isinstance(value, str):
                return value
        if isinstance(text_obj, dict):
            value = text_obj.get("value") or text_obj.get("text")
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                segments = [segment.get("text") for segment in value if isinstance(segment, dict)]
                return "".join(filter(None, segments)) if segments else None
        if isinstance(text_obj, list):
            pieces: List[str] = []
            for item in text_obj:
                if isinstance(item, str):
                    pieces.append(item)
                elif isinstance(item, dict):
                    piece = item.get("text") or item.get("value")
                    if isinstance(piece, str):
                        pieces.append(piece)
            return "".join(pieces) if pieces else None
        if hasattr(text_obj, "model_dump"):
            try:
                dumped = text_obj.model_dump()
            except Exception:  # pragma: no cover - defensive
                dumped = None
            if dumped is not None:
                return self._normalise_text_value(dumped)
        return None

    def _safe_model_dump(self, response: Any) -> Optional[Any]:
        for attr in ("model_dump", "to_dict", "dict"):
            method = getattr(response, attr, None)
            if callable(method):
                try:
                    data = method()
                except Exception:  # pragma: no cover - defensive
                    continue
                if data:
                    return data
        return None

    def _locate_rewrite_payload(self, data: Any, depth: int = 0) -> Optional[str]:
        if depth > 6:
            return None
        if isinstance(data, str):
            stripped = data.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                return stripped
            return None
        if isinstance(data, dict):
            if self._looks_like_rewrite_payload(data):
                return json.dumps(data)
            for value in data.values():
                candidate = self._locate_rewrite_payload(value, depth + 1)
                if candidate:
                    return candidate
        if isinstance(data, list):
            for item in data:
                candidate = self._locate_rewrite_payload(item, depth + 1)
                if candidate:
                    return candidate
        return None

    def _looks_like_rewrite_payload(self, data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        if "blocks" not in data:
            return False
        if not isinstance(data["blocks"], list):
            return False
        return any(key in data for key in ("meta_title", "meta_description"))

    def _strip_json_fences(self, payload: str) -> str:
        stripped = payload.strip()
        if stripped.startswith("```"):
            fence_match = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
            if fence_match:
                stripped = fence_match.group(1).strip()
        if stripped and not stripped.startswith("{"):
            brace_match = re.search(r"\{.*\}", stripped, re.DOTALL)
            if brace_match:
                stripped = brace_match.group(0).strip()
        return stripped

    def _extract_response_text(self, response: Any) -> str:
        """Normalise the various OpenAI client payload shapes into a JSON string."""

        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        parts: List[str] = []
        for item in getattr(response, "output", []) or []:
            for content_item in getattr(item, "content", []) or []:
                text_value = self._coerce_content_text(content_item)
                if text_value:
                    parts.append(text_value)
        if parts:
            return "".join(parts)

        structured = self._safe_model_dump(response)
        if structured:
            candidate = self._locate_rewrite_payload(structured)
            if candidate:
                return candidate

        return ""

    def _coerce_content_text(self, content_item: Any) -> Optional[str]:
        content_type = getattr(content_item, "type", None)

        if content_type in {"output_json", "json"}:
            json_payload = getattr(content_item, "json", None)
            if isinstance(json_payload, dict):
                return json.dumps(json_payload)
            if hasattr(json_payload, "model_dump"):
                try:
                    dumped = json_payload.model_dump()
                except Exception:  # pragma: no cover - defensive
                    dumped = None
                if isinstance(dumped, dict):
                    return json.dumps(dumped)

        if content_type in {"output_text", "text", None}:
            text_obj = getattr(content_item, "text", None)
            normalised = self._normalise_text_value(text_obj)
            if normalised:
                return normalised

        return None

    def _normalise_text_value(self, text_obj: Any) -> Optional[str]:
        if text_obj is None:
            return None
        if isinstance(text_obj, str):
            return text_obj
        if hasattr(text_obj, "value"):
            value = getattr(text_obj, "value")
            if isinstance(value, str):
                return value
        if isinstance(text_obj, dict):
            value = text_obj.get("value") or text_obj.get("text")
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                segments = [segment.get("text") for segment in value if isinstance(segment, dict)]
                return "".join(filter(None, segments)) if segments else None
        if isinstance(text_obj, list):
            pieces: List[str] = []
            for item in text_obj:
                if isinstance(item, str):
                    pieces.append(item)
                elif isinstance(item, dict):
                    piece = item.get("text") or item.get("value")
                    if isinstance(piece, str):
                        pieces.append(piece)
            return "".join(pieces) if pieces else None
        if hasattr(text_obj, "model_dump"):
            try:
                dumped = text_obj.model_dump()
            except Exception:  # pragma: no cover - defensive
                dumped = None
            if dumped is not None:
                return self._normalise_text_value(dumped)
        return None

    def _safe_model_dump(self, response: Any) -> Optional[Any]:
        for attr in ("model_dump", "to_dict", "dict"):
            method = getattr(response, attr, None)
            if callable(method):
                try:
                    data = method()
                except Exception:  # pragma: no cover - defensive
                    continue
                if data:
                    return data
        return None

    def _locate_rewrite_payload(self, data: Any, depth: int = 0) -> Optional[str]:
        if depth > 6:
            return None
        if isinstance(data, str):
            stripped = data.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                return stripped
            return None
        if isinstance(data, dict):
            if self._looks_like_rewrite_payload(data):
                return json.dumps(data)
            for value in data.values():
                candidate = self._locate_rewrite_payload(value, depth + 1)
                if candidate:
                    return candidate
        if isinstance(data, list):
            for item in data:
                candidate = self._locate_rewrite_payload(item, depth + 1)
                if candidate:
                    return candidate
        return None

    def _looks_like_rewrite_payload(self, data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        if "blocks" not in data:
            return False
        if not isinstance(data["blocks"], list):
            return False
        return any(key in data for key in ("meta_title", "meta_description"))

    def _strip_json_fences(self, payload: str) -> str:
        stripped = payload.strip()
        if stripped.startswith("```"):
            fence_match = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
            if fence_match:
                stripped = fence_match.group(1).strip()
        if stripped and not stripped.startswith("{"):
            brace_match = re.search(r"\{.*\}", stripped, re.DOTALL)
            if brace_match:
                stripped = brace_match.group(0).strip()
        return stripped


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
                )
            )

        meta_title = f"{site_label} – Updated Website Experience"
        meta_description = (
            f"Fallback content for {site_label}. Review and replace once OpenAI rewriting succeeds."
        )
        return ContentBundle(
            blocks=blocks,
            meta_title=meta_title,
            meta_description=meta_description,
            fallback_used=True,
        )


__all__ = ["RewriteAgent"]
