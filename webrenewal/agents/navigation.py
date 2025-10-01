"""Implementation of the A9 Navigation agent."""

from __future__ import annotations

from collections.abc import Iterable
from typing import List

from bs4 import BeautifulSoup
from bs4.element import Tag

from .base import Agent
from ..models import CrawlResult, NavModel, NavigationItem


class NavigationAgent(Agent[CrawlResult, NavModel]):
    """Reconstruct a simplified navigation model."""

    def __init__(self) -> None:
        super().__init__(name="A9.Navigation")

    def run(self, crawl: CrawlResult) -> NavModel:
        aggregated: List[NavigationItem] = []

        for page in crawl.pages:
            soup = BeautifulSoup(page.html, "lxml")
            nav_structures: List[NavigationItem] = []

            for nav in soup.find_all("nav"):
                nav_structures.extend(self._extract_navigation(nav))

            if not nav_structures:
                nav_structures.extend(self._extract_fallback_lists(soup))

            if nav_structures:
                self._merge_navigation(aggregated, nav_structures)

        if not aggregated:
            aggregated = self._fallback_flat(crawl)

        return NavModel(items=aggregated)

    def _extract_navigation(self, container: Tag) -> List[NavigationItem]:
        top_level_lists = [
            lst
            for lst in container.find_all(["ul", "ol"])
            if lst.find_parent(["ul", "ol"]) is None
        ]
        items: List[NavigationItem] = []
        for lst in top_level_lists:
            items.extend(self._parse_list(lst))
        if items:
            return items

        anchors = container.find_all("a", href=True)
        return self._anchors_to_items(anchors)

    def _extract_fallback_lists(self, soup: BeautifulSoup) -> List[NavigationItem]:
        top_level_lists = [
            lst
            for lst in soup.find_all(["ul", "ol"])
            if lst.find_parent(["ul", "ol"]) is None
        ]
        items: List[NavigationItem] = []
        for lst in top_level_lists:
            items.extend(self._parse_list(lst))
        return items

    def _parse_list(self, list_node: Tag) -> List[NavigationItem]:
        items: List[NavigationItem] = []
        for item in list_node.find_all("li", recursive=False):
            anchor = item.find("a", href=True)
            if not anchor:
                continue
            label = anchor.get_text(strip=True)
            href = anchor["href"].strip()
            if not label or not href:
                continue

            child_lists = [
                child
                for child in item.find_all(["ul", "ol"])
                if child.find_parent("li") is item
            ]
            children: List[NavigationItem] = []
            for child in child_lists:
                children.extend(self._parse_list(child))

            items.append(
                NavigationItem(
                    label=label,
                    href=href,
                    children=children,
                )
            )
        return items

    def _anchors_to_items(self, anchors: Iterable[Tag]) -> List[NavigationItem]:
        items: List[NavigationItem] = []
        seen: set[tuple[str, str]] = set()
        for anchor in anchors:
            label = anchor.get_text(strip=True)
            href = anchor.get("href", "").strip()
            key = (label.lower(), href)
            if not label or not href or key in seen:
                continue
            seen.add(key)
            items.append(NavigationItem(label=label, href=href))
        return items

    def _merge_navigation(
        self, existing: List[NavigationItem], new_items: Iterable[NavigationItem]
    ) -> None:
        lookup = {
            (item.label.strip().lower(), item.href.strip()): item for item in existing
        }

        for new_item in new_items:
            key = (new_item.label.strip().lower(), new_item.href.strip())
            if key in lookup:
                target = lookup[key]
                if new_item.children:
                    self._merge_navigation(target.children, new_item.children)
            else:
                cloned = NavigationItem(
                    label=new_item.label,
                    href=new_item.href,
                    children=[],
                )
                if new_item.children:
                    self._merge_navigation(cloned.children, new_item.children)
                existing.append(cloned)
                lookup[key] = cloned

    def _fallback_flat(self, crawl: CrawlResult) -> List[NavigationItem]:
        items: List[NavigationItem] = []
        seen: set[tuple[str, str]] = set()
        for page in crawl.pages:
            soup = BeautifulSoup(page.html, "lxml")
            for anchor in soup.find_all("a", href=True):
                label = anchor.get_text(strip=True)
                href = anchor["href"].strip()
                key = (label.lower(), href)
                if label and href and key not in seen:
                    seen.add(key)
                    items.append(NavigationItem(label=label, href=href))
        return items


__all__ = ["NavigationAgent"]
