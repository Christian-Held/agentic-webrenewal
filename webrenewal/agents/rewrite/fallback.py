"""Fallback rewrite implementation used when the LLM is unavailable."""

from __future__ import annotations

from typing import List

from ...models import ContentBlock, ContentBundle, ContentExtract
from ...utils import domain_to_display_name


class FallbackBuilder:
    """Create deterministic rewrite bundles for degraded operation."""

    def build(self, domain: str, content: ContentExtract) -> ContentBundle:
        site_label = domain_to_display_name(domain)
        notice = f"[Automated fallback for {site_label}]"

        blocks: List[ContentBlock] = []
        for index, section in enumerate(content.sections, start=1):
            readability = self._format_readability(section.readability_score)
            refreshed = (
                f"{notice} Original readability score: {readability}.\n\n{section.text}"
            )
            blocks.append(
                ContentBlock(
                    title=section.title or f"Section {index}",
                    body=refreshed,
                )
            )

        bundle = ContentBundle(
            blocks=blocks,
            meta_title=f"{site_label} – Updated Website Experience",
            meta_description=(
                f"Fallback content for {site_label}. Review once OpenAI rewriting succeeds."
            ),
            fallback_used=True,
        )
        return bundle

    def _format_readability(self, score: float | None) -> str:
        return "n/a" if score is None else f"{score:.1f}"


__all__ = ["FallbackBuilder"]
