"""Implementation of the A2 Crawler agent."""

from __future__ import annotations

import logging
from collections import deque
from typing import Deque, Dict, List, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .base import Agent
from ..http import get
from ..models import CrawlResult, PageContent, ScopePlan


class CrawlerAgent(Agent[ScopePlan, CrawlResult]):
    """Fetch pages within the provided scope."""

    def __init__(self, max_pages: int = 10) -> None:
        super().__init__(name="A2.Crawler")
        self._max_pages = max(1, max_pages)

    def _is_same_domain(self, base: str, url: str) -> bool:
        return urlparse(base).netloc == urlparse(url).netloc

    def run(self, plan: ScopePlan) -> CrawlResult:
        visited: Set[str] = set()
        queue: Deque[str] = deque(plan.seed_urls)
        pages: List[PageContent] = []

        self.logger.info("Starting crawl with up to %d pages", self._max_pages)
        while queue and len(pages) < self._max_pages:
            current_url = queue.popleft()
            if current_url in visited:
                continue
            visited.add(current_url)
            try:
                response = get(current_url, headers={"User-Agent": "AgenticWebRenewal/0.1"})
            except requests.RequestException as exc:  # type: ignore[attr-defined]
                self.logger.error(
                    "Failed to fetch %s: %s", current_url, exc, exc_info=True
                )
                continue
            pages.append(
                PageContent(
                    url=response.url,
                    status_code=response.status_code,
                    headers=response.headers,
                    html=response.text,
                )
            )
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "lxml")
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"].strip()
                absolute = urljoin(current_url, href)
                if self._is_same_domain(plan.domain, absolute) and absolute not in visited:
                    queue.append(absolute)
        self.logger.info("Crawled %d pages", len(pages))
        return CrawlResult(pages=pages)


__all__ = ["CrawlerAgent"]
