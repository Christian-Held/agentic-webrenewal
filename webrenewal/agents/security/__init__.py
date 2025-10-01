"""Implementation of the A7 Security agent."""

from __future__ import annotations

from typing import List

from ..common import Agent
from ...models import CrawlResult, Issue, SecurityReport


class SecurityAgent(Agent[CrawlResult, SecurityReport]):
    """Evaluate basic HTTP security headers."""

    def __init__(self) -> None:
        super().__init__(name="A7.Security")

    _REQUIRED_HEADERS = [
        "content-security-policy",
        "strict-transport-security",
        "x-content-type-options",
        "x-frame-options",
    ]

    def run(self, crawl: CrawlResult) -> SecurityReport:
        issues: List[Issue] = []
        score = 100.0
        for page in crawl.pages:
            headers = {k.lower(): v for k, v in page.headers.items()}
            for required in self._REQUIRED_HEADERS:
                if required not in headers:
                    issues.append(
                        Issue(
                            description=f"Missing {required} header on {page.url}",
                            severity="high",
                            recommendation=f"Configure the {required} response header for improved security.",
                        )
                    )
                    score -= 5
        score = max(score, 0.0)
        return SecurityReport(score=score, issues=issues)


__all__ = ["SecurityAgent"]
