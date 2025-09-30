"""Implementation of the A11 Rewrite agent."""

from __future__ import annotations

import json
import os
from typing import List, Optional

from openai import OpenAI, OpenAIError

from .base import Agent
from ..models import ContentBlock, ContentBundle, ContentExtract, RenewalPlan
from ..utils import domain_to_display_name


class RewriteAgent(Agent[tuple[str, ContentExtract, RenewalPlan], ContentBundle]):
    """Produce refreshed copy for the website."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.4) -> None:
        super().__init__(name="A11.Rewrite")
        self._model = model
        self._temperature = temperature
        self._client: Optional[OpenAI] = None

    def run(self, data: tuple[str, ContentExtract, RenewalPlan]) -> ContentBundle:
        domain, content, plan = data
        client = self._get_client()

        if client is None:
            self.logger.warning("OpenAI API key missing; falling back to deterministic rewrite")
            return self._fallback_bundle(domain, content)

        try:
            return self._rewrite_with_llm(client, domain, content, plan)
        except (OpenAIError, ValueError, json.JSONDecodeError) as exc:
            self.logger.warning("LLM rewrite failed (%s); using fallback", exc)
            return self._fallback_bundle(domain, content)

    def _get_client(self) -> Optional[OpenAI]:
        """Initialise the OpenAI client if credentials are configured."""

        if self._client is not None:
            return self._client

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        self._client = OpenAI(api_key=api_key)
        return self._client

    def _rewrite_with_llm(
        self, client: OpenAI, domain: str, content: ContentExtract, plan: RenewalPlan
    ) -> ContentBundle:
        """Leverage the OpenAI Responses API to refresh the site copy."""

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
        payload = {
            "domain": domain,
            "site_name": site_label,
            "language": content.language or "auto",
            "goals": plan.goals,
            "actions": action_summaries,
            "sections": [
                {
                    "title": section.title,
                    "text": section.text,
                    "readability_score": section.readability_score,
                }
                for section in content.sections
            ],
        }

        guidelines = (
            f"You are an expert marketing copywriter refreshing the website for {site_label} ({domain}). "
            "Blend the renewal goals and action plan into persuasive, accessible copy while keeping the original language. "
            "Highlight user benefits, improve clarity, and retain any medical or legal disclaimers."
        )
        user_instruction = (
            "Return JSON with keys 'meta_title', 'meta_description' and 'blocks'. "
            "Each entry in 'blocks' must contain 'title' and 'body' fields. "
            f"Align the tone with the goals: {goals_text}. "
            "Preserve the number of sections provided and keep HTML safe (no Markdown). "
            "Here is the source data: "
            + json.dumps(payload, ensure_ascii=False)
        )
        response = client.responses.create(
            model=self._model,
            temperature=self._temperature,
            response_format={"type": "json_object"},
            input=[
                {
                    "role": "system",
                    "content": guidelines,
                },
                {
                    "role": "user",
                    "content": user_instruction,
                },
            ],
        )

        raw_output = getattr(response, "output_text", None)
        if not raw_output:
            parts: List[str] = []
            for item in getattr(response, "output", []):
                for content_item in getattr(item, "content", []):
                    if getattr(content_item, "type", "") == "output_text":
                        parts.append(getattr(content_item, "text", ""))
            raw_output = "".join(parts)

        if not raw_output:
            raise ValueError("No textual output returned by LLM")

        data = json.loads(raw_output)

        block_payload = data.get("blocks")
        if not isinstance(block_payload, list):
            raise ValueError("Missing blocks in LLM response")
        if len(block_payload) != len(content.sections):
            raise ValueError("LLM returned an unexpected number of blocks")


    def run(self, data: tuple[ContentExtract, RenewalPlan]) -> ContentBundle:
        content, plan = data
        client = self._get_client()

        if client is None:
            self.logger.warning("OpenAI API key missing; falling back to deterministic rewrite")
            return self._fallback_bundle(content)

        try:
            return self._rewrite_with_llm(client, content, plan)
        except (OpenAIError, ValueError, json.JSONDecodeError) as exc:
            self.logger.warning("LLM rewrite failed (%s); using fallback", exc)
            return self._fallback_bundle(content)

    def _get_client(self) -> Optional[OpenAI]:
        """Initialise the OpenAI client if credentials are configured."""

        if self._client is not None:
            return self._client

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        self._client = OpenAI(api_key=api_key)
        return self._client

    def _rewrite_with_llm(
        self, client: OpenAI, content: ContentExtract, plan: RenewalPlan
    ) -> ContentBundle:
        """Leverage the OpenAI Responses API to refresh the site copy."""

        payload = {
            "language": content.language or "auto",
            "goals": plan.goals,
            "actions": [
                {"id": action.identifier, "description": action.description, "impact": action.impact}
                for action in plan.actions
            ],
            "sections": [
                {
                    "title": section.title,
                    "text": section.text,
                    "readability_score": section.readability_score,
                }
                for section in content.sections
            ],
        }

        response = client.responses.create(
            model=self._model,
            temperature=self._temperature,
            response_format={"type": "json_object"},
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert marketing copywriter for physiotherapy clinics. "
                        "Rewrite the provided website sections to improve clarity, persuasion and accessibility. "
                        "Maintain the same language as the input and produce concise HTML-ready paragraphs without Markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Return JSON with keys 'meta_title', 'meta_description' and 'blocks'. "
                        "Each entry in 'blocks' must contain 'title' and 'body' fields. "
                        "Keep the number of blocks equal to the provided sections and preserve critical medical disclaimers. "
                        "Here is the source data: "
                        + json.dumps(payload, ensure_ascii=False)
                    ),
                },
            ],
        )

        raw_output = getattr(response, "output_text", None)
        if not raw_output:
            parts: List[str] = []
            for item in getattr(response, "output", []):
                for content_item in getattr(item, "content", []):
                    if getattr(content_item, "type", "") == "output_text":
                        parts.append(getattr(content_item, "text", ""))
            raw_output = "".join(parts)

        if not raw_output:
            raise ValueError("No textual output returned by LLM")

        data = json.loads(raw_output)

        block_payload = data.get("blocks")
        if not isinstance(block_payload, list):
            raise ValueError("Missing blocks in LLM response")
        if len(block_payload) != len(content.sections):
            raise ValueError("LLM returned an unexpected number of blocks")

        blocks: List[ContentBlock] = []
        for index, (section, block_data) in enumerate(zip(content.sections, block_payload), start=1):
            if not isinstance(block_data, dict):
                raise ValueError("Block data is not an object")
            title = block_data.get("title")
            body = block_data.get("body")
            if not isinstance(body, str) or not body.strip():
                raise ValueError("Invalid block body returned by LLM")
            blocks.append(
                ContentBlock(
                    title=title or section.title or f"Section {index}",
                    body=body.strip(),
                )
            )

        meta_title = data.get("meta_title")
        if not isinstance(meta_title, str) or not meta_title.strip():
            meta_title = content.sections[0].title if content.sections else None

        meta_description = data.get("meta_description")
        if not isinstance(meta_description, str) or not meta_description.strip():
            meta_description = (
                f"Refreshed content for {site_label}, generated via Agentic WebRenewal after analysing {domain}."
            )

        return ContentBundle(
            blocks=blocks,
            meta_title=meta_title.strip() if meta_title else None,
            meta_description=meta_description.strip(),
            fallback_used=False,
        )


    def _fallback_bundle(self, content: ContentExtract) -> ContentBundle:
        """Provide a deterministic rewrite when the LLM is unavailable."""

        blocks: List[ContentBlock] = []
        for index, section in enumerate(content.sections, start=1):
            intro = (
                f"{fallback_notice} Original readability score: "
            )
            readability_score = (
                f"{section.readability_score:.1f}" if section.readability_score is not None else "n/a"
            )
            refreshed = f"{intro}{readability_score}.\n\n{section.text}"
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
