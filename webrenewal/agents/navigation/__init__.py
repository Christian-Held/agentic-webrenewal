"""Implementation of the A9 Navigation agent."""

from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from ..common import Agent
from ...models import CrawlResult, NavModel, NavigationItem


class NavigationAgent(Agent[CrawlResult, NavModel]):
    """Reconstruct a simplified navigation model."""

    def __init__(self) -> None:
        super().__init__(name="A9.Navigation")

    def run(self, crawl: CrawlResult) -> NavModel:
        items: List[NavigationItem] = []
        seen = set()
        for page in crawl.pages:
            soup = BeautifulSoup(page.html, "lxml")
            nav_tags = soup.find_all(["nav", "ul"])
            for container in nav_tags:
                for anchor in container.find_all("a", href=True):
                    label = anchor.get_text(strip=True)
                    href = anchor["href"].strip()
                    if label and href and (label, href) not in seen:
                        seen.add((label, href))
                        items.append(NavigationItem(label=label, href=href))
        return NavModel(items=items)


__all__ = ["NavigationAgent"]
