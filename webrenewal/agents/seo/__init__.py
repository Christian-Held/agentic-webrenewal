"""Implementation of the A6 SEO agent."""

from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from ..common import Agent
from ...models import CrawlResult, Issue, SEOReport


class SEOAgent(Agent[CrawlResult, SEOReport]):
    """Perform simple SEO quality checks."""

    def __init__(self) -> None:
        super().__init__(name="A6.SEO")

    def run(self, crawl: CrawlResult) -> SEOReport:
        issues: List[Issue] = []
        score = 100.0
        for page in crawl.pages:
            soup = BeautifulSoup(page.html, "lxml")
            title_tag = soup.find("title")
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if not title_tag or not title_tag.text.strip():
                issues.append(
                    Issue(
                        description=f"Missing title tag on {page.url}",
                        severity="high",
                        recommendation="Add a concise, keyword-rich title tag.",
                    )
                )
                score -= 10
            if not meta_desc or not meta_desc.get("content"):
                issues.append(
                    Issue(
                        description=f"Missing meta description on {page.url}",
                        severity="medium",
                        recommendation="Provide a compelling meta description between 120-160 characters.",
                    )
                )
                score -= 10
        score = max(score, 0.0)
        return SEOReport(score=score, issues=issues)


__all__ = ["SEOAgent"]
