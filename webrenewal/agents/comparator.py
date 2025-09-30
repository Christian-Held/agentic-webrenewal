"""Implementation of the A14 Comparator agent."""

from __future__ import annotations

import difflib
from typing import List

from .base import Agent
from ..models import CrawlResult, DiffResult, PreviewIndex
from ..storage import SANDBOX_DIR
from ..utils import url_to_relative_path


class ComparatorAgent(Agent[tuple[CrawlResult, str], PreviewIndex]):
    """Generate textual diffs between the original and rebuilt site."""

    def __init__(self) -> None:
        super().__init__(name="A14.Comparator")

    def run(self, data: tuple[CrawlResult, str]) -> PreviewIndex:
        crawl, newsite_dir = data
        diffs: List[DiffResult] = []
        for page in crawl.pages:
            relative_path = url_to_relative_path(page.url)
            new_page = SANDBOX_DIR / newsite_dir / relative_path
            if not new_page.exists():
                new_page = SANDBOX_DIR / newsite_dir / "index.html"
            new_content = new_page.read_text(encoding="utf-8") if new_page.exists() else ""
            diff = difflib.unified_diff(
                page.html.splitlines(),
                new_content.splitlines(),
                fromfile=page.url,
                tofile=str(new_page),
                lineterm="",
            )
            diffs.append(DiffResult(page=page.url, diff="\n".join(diff)))
        return PreviewIndex(diffs=diffs)


__all__ = ["ComparatorAgent"]
