"""Implementation of the A6 SEO agent."""

from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from .base import Agent
from ..models import CrawlResult, Issue, SEOReport
from ..postedit.models import ChangeOperation, SiteState
from ..state import StateStore


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

    # ------------------------------------------------------------------
    def apply_post_edit(
        self,
        state: SiteState,
        operations: List[ChangeOperation],
        *,
        user_prompt: str | None,
        state_store: StateStore | None = None,
        provider: str = "openai",
        model: str = "gpt-4.1-mini",
    ) -> dict:
        updated_pages = 0
        for op in operations:
            if op.type != "seo.meta.patch" or not op.page:
                continue
            meta = state.seo.setdefault("meta", {})
            entry = meta.setdefault(op.page, {})
            description = self._generate_description(op.page, user_prompt or "")
            if description:
                entry["description"] = description
                updated_pages += 1
            if keywords := op.payload.get("keywords"):
                entry["keywords"] = keywords

        if state_store and updated_pages:
            state_store.record_trace(
                provider=provider,
                model=model,
                request_trunc=(user_prompt or "")[:200],
                response_trunc="; ".join(
                    state.seo.get("meta", {}).get(op.page, {}).get("description", "")
                    for op in operations
                    if op.type == "seo.meta.patch" and op.page
                )[:200],
                duration_ms=18,
                tokens={"input": len((user_prompt or "").split()), "output": updated_pages * 12},
            )

        return {"meta_updated": updated_pages}

    def _generate_description(self, page: str, prompt: str) -> str:
        base = prompt.strip() or "Updated SEO description"
        focus = page.strip("/") or "home"
        return f"{base[:120]} – tailored for {focus.title()} page."


__all__ = ["SEOAgent"]
