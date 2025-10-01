"""Implementation of the A3 Readability agent."""

from __future__ import annotations

import logging
from typing import List, Optional

from bs4 import BeautifulSoup

try:
    import trafilatura
except ModuleNotFoundError:  # pragma: no cover - fallback when dependency missing
    trafilatura = None  # type: ignore[assignment]

try:
    from textstat import flesch_reading_ease
except ModuleNotFoundError:  # pragma: no cover
    def flesch_reading_ease(text: str) -> float:
        return 0.0

from ..common import Agent
from ...models import ContentExtract, ContentSection, CrawlResult


class ReadabilityAgent(Agent[CrawlResult, ContentExtract]):
    """Extract structured content from crawled pages."""

    def __init__(self) -> None:
        super().__init__(name="A3.Readability")

    def _extract_with_trafilatura(self, html: str) -> Optional[str]:
        if trafilatura is None:
            return None
        try:
            return trafilatura.extract(html)
        except Exception:  # pragma: no cover - library specific exceptions
            return None

    def run(self, crawl: CrawlResult) -> ContentExtract:
        sections: List[ContentSection] = []
        language: Optional[str] = None

        for page in crawl.pages:
            soup = BeautifulSoup(page.html, "lxml")
            if soup.html and soup.html.has_attr("lang"):
                language = soup.html["lang"]

            text_content = self._extract_with_trafilatura(page.html)
            if not text_content:
                text_content = soup.get_text(" ", strip=True)

            readability = flesch_reading_ease(text_content)
            title = soup.title.string.strip() if soup.title and soup.title.string else None
            sections.append(
                ContentSection(
                    title=title,
                    text=text_content,
                    readability_score=readability,
                )
            )
        return ContentExtract(sections=sections, language=language)


__all__ = ["ReadabilityAgent"]
