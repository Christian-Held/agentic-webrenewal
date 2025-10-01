"""Implementation of the A8 Media agent."""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..common import Agent
from ...models import CrawlResult, MediaInfo, MediaReport


class MediaAgent(Agent[CrawlResult, MediaReport]):
    """Analyse media elements from crawled pages."""

    def __init__(self) -> None:
        super().__init__(name="A8.Media")

    def _head_request(self, url: str) -> Optional[requests.Response]:
        try:
            return requests.head(url, timeout=15, allow_redirects=True)
        except requests.RequestException:
            return None

    def run(self, crawl: CrawlResult) -> MediaReport:
        images: List[MediaInfo] = []
        for page in crawl.pages:
            soup = BeautifulSoup(page.html, "lxml")
            for img in soup.find_all("img", src=True):
                src = img["src"].strip()
                absolute = urljoin(page.url, src)
                head = self._head_request(absolute)
                size = int(head.headers.get("Content-Length", "0")) if head else None
                content_type = head.headers.get("Content-Type") if head else None
                fmt = content_type.split("/")[-1] if content_type else None
                images.append(
                    MediaInfo(
                        url=absolute,
                        alt_text=img.get("alt"),
                        size_bytes=size,
                        format=fmt,
                    )
                )
        return MediaReport(images=images)


__all__ = ["MediaAgent"]
