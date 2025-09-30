"""Implementation of the A11 Rewrite agent."""

from __future__ import annotations

from typing import List

from .base import Agent
from ..models import ContentBlock, ContentBundle, ContentExtract, RenewalPlan


class RewriteAgent(Agent[tuple[ContentExtract, RenewalPlan], ContentBundle]):
    """Produce refreshed copy for the website.

    The PoC implementation performs deterministic transformations to keep the
    pipeline self-contained without external LLM calls.
    """

    def __init__(self) -> None:
        super().__init__(name="A11.Rewrite")

    def run(self, data: tuple[ContentExtract, RenewalPlan]) -> ContentBundle:
        content, plan = data
        blocks: List[ContentBlock] = []
        for index, section in enumerate(content.sections, start=1):
            intro = (
                "This content was refreshed to emphasise the clinic's benefits and clarity. "
                "Original readability score: "
            )
            if section.readability_score is not None:
                readability_score = f"{section.readability_score:.1f}"
            else:
                readability_score = "n/a"
            refreshed = f"{intro}{readability_score}.\n\n{section.text}"
            blocks.append(
                ContentBlock(
                    title=section.title or f"Section {index}",
                    body=refreshed,
                )
            )
        meta_title = "PhysioHeld – Personalised Physiotherapy in Switzerland"
        meta_description = (
            "Discover PhysioHeld's tailored physiotherapy treatments, modern rehabilitation techniques and expert therapists."  # noqa: E501
        )
        return ContentBundle(blocks=blocks, meta_title=meta_title, meta_description=meta_description)


__all__ = ["RewriteAgent"]
