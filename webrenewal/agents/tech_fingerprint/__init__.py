"""Implementation of the A4 Tech Fingerprint agent."""

from __future__ import annotations

import re
from typing import Dict, List

from ..common import Agent
from ...models import CrawlResult, TechFingerprint


class TechFingerprintAgent(Agent[CrawlResult, TechFingerprint]):
    """Detect frameworks and libraries based on simple heuristics."""

    _PATTERNS: Dict[str, List[re.Pattern[str]]] = {
        "Bootstrap": [re.compile(r"bootstrap(\.min)?\.css", re.I)],
        "jQuery": [re.compile(r"jquery(\.min)?\.js", re.I)],
        "Google Tag Manager": [re.compile(r"googletagmanager", re.I)],
        "WordPress": [re.compile(r"wp-content", re.I), re.compile(r"wp-includes", re.I)],
    }

    def __init__(self) -> None:
        super().__init__(name="A4.TechFingerprint")

    def run(self, crawl: CrawlResult) -> TechFingerprint:
        frameworks: List[str] = []
        evidence: Dict[str, List[str]] = {}
        for page in crawl.pages:
            html = page.html
            for name, patterns in self._PATTERNS.items():
                for pattern in patterns:
                    if pattern.search(html):
                        frameworks.append(name)
                        evidence.setdefault(name, []).append(page.url)
                        break
        frameworks = sorted(set(frameworks))
        return TechFingerprint(frameworks=frameworks, evidence=evidence)


__all__ = ["TechFingerprintAgent"]
