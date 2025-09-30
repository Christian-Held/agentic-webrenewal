"""Implementation of the A1 Scope agent."""

from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

from .base import Agent
from ..http import get
from ..models import ScopePlan


class ScopeAgent(Agent[str, ScopePlan]):
    """Derive the crawling scope from a provided domain or URL."""

    def __init__(self) -> None:
        super().__init__(name="A1.Scope")

    def _fetch_robots(self, base_url: str) -> Optional[str]:
        robots_url = urljoin(base_url, "/robots.txt")
        try:
            response = get(robots_url)
        except requests.RequestException as exc:  # type: ignore[attr-defined]
            self.logger.warning("Failed to fetch robots.txt: %s", exc)
            return None
        if response.status_code >= 400:
            self.logger.info("Robots.txt not available at %s", robots_url)
            return None
        return response.text

    def _extract_sitemaps(self, robots_text: str) -> List[str]:
        pattern = re.compile(r"(?i)^sitemap:\s*(?P<url>\S+)", re.MULTILINE)
        return [match.group("url").strip() for match in pattern.finditer(robots_text)]

    def run(self, domain: str) -> ScopePlan:
        parsed = urlparse(domain)
        if not parsed.scheme:
            base_url = f"https://{domain}".rstrip("/")
        else:
            base_url = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        self.logger.info("Deriving scope for %s", base_url)

        robots_text = self._fetch_robots(base_url)
        sitemap_urls: List[str] = []
        if robots_text:
            sitemap_urls = self._extract_sitemaps(robots_text)

        seed_urls = [base_url]
        plan = ScopePlan(domain=base_url, seed_urls=seed_urls, sitemap_urls=sitemap_urls, robots_txt=robots_text)
        self.logger.debug("Scope plan derived with %d sitemap URLs", len(plan.sitemap_urls))
        return plan


__all__ = ["ScopeAgent"]
