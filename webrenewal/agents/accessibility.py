"""Implementation of the A5 Accessibility agent."""

from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from .base import Agent
from ..models import A11yReport, CrawlResult, Issue


class AccessibilityAgent(Agent[CrawlResult, A11yReport]):
    """Run lightweight static accessibility checks."""

    def __init__(self) -> None:
        super().__init__(name="A5.Accessibility")

    def run(self, crawl: CrawlResult) -> A11yReport:
        issues: List[Issue] = []
        total_images = 0
        missing_alts = 0
        for page in crawl.pages:
            soup = BeautifulSoup(page.html, "lxml")
            images = soup.find_all("img")
            total_images += len(images)
            for image in images:
                if not image.get("alt"):
                    missing_alts += 1
                    issues.append(
                        Issue(
                            description=f"Image missing alt attribute on {page.url}",
                            severity="medium",
                            recommendation="Provide descriptive alt text for the image to improve accessibility.",
                        )
                    )
        score = 100.0
        if total_images:
            score -= (missing_alts / total_images) * 40.0
        score = max(score, 0.0)
        return A11yReport(score=score, issues=issues)


__all__ = ["AccessibilityAgent"]
