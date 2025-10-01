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
from ..tracing import log_event


class ScopeAgent(Agent[str, ScopePlan]):
    """Derive the crawling scope from a provided domain or URL."""

    def __init__(self) -> None:
        super().__init__(name="A1.Scope")

    def _fetch_robots(self, base_url: str) -> Optional[str]:
        robots_url = urljoin(base_url, "/robots.txt")
        try:
            response = get(robots_url)
        except requests.RequestException as exc:  # type: ignore[attr-defined]
            log_event(
                self.logger,
                logging.WARNING,
                "scope.robots.error",
                agent=self.name,
                url=robots_url,
                error=str(exc),
                exception=exc.__class__.__name__,
                exc_info=True,
            )
            return None
        if response.status_code >= 400:
            log_event(
                self.logger,
                logging.INFO,
                "scope.robots.missing",
                agent=self.name,
                url=robots_url,
                status=response.status_code,
            )
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
        log_event(
            self.logger,
            logging.INFO,
            "scope.start",
            agent=self.name,
            domain=domain,
            base_url=base_url,
        )

        robots_text = self._fetch_robots(base_url)
        sitemap_urls: List[str] = []
        if robots_text:
            sitemap_urls = self._extract_sitemaps(robots_text)

        seed_urls = [base_url]
        plan = ScopePlan(
            domain=base_url,
            seed_urls=seed_urls,
            sitemap_urls=sitemap_urls,
            robots_txt=robots_text,
        )
        log_event(
            self.logger,
            logging.DEBUG,
            "scope.finish",
            agent=self.name,
            domain=base_url,
            seeds=len(seed_urls),
            sitemaps=len(plan.sitemap_urls),
            robots=robots_text is not None,
        )
        return plan


__all__ = ["ScopeAgent"]
