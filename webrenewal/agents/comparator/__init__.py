"""Implementation of the A14 Comparator agent."""

from __future__ import annotations

import difflib
import logging
from pathlib import Path
from typing import List, Optional

from ..common import Agent
from ..models import CrawlResult, DiffResult, PreviewIndex
from ..storage import SANDBOX_DIR
from ..tracing import log_event
from ..utils import url_to_relative_path


class ComparatorAgent(Agent[tuple[CrawlResult, str], PreviewIndex]):
    """Generate textual diffs between the original and rebuilt site."""

    def __init__(self) -> None:
        super().__init__(name="A14.Comparator")

    def run(self, data: tuple[CrawlResult, str]) -> PreviewIndex:
        crawl, newsite_dir = data
        newsite_root = SANDBOX_DIR / newsite_dir
        generated_files = sorted(
            (path for path in newsite_root.rglob("*.html") if path.is_file()),
            key=lambda path: str(path.relative_to(newsite_root)),
        )
        unused_files = [path for path in generated_files if path.name != "index.html"]
        used_files: set[Path] = set()
        index_page = newsite_root / "index.html"

        diffs: List[DiffResult] = []
        for page in crawl.pages:
            relative_path = url_to_relative_path(page.url)
            new_page = self._locate_new_page(
                relative_path, newsite_root, unused_files, used_files, index_page
            )
            tofile = (
                str(new_page.relative_to(newsite_root))
                if new_page and new_page.exists()
                else "<missing>"
            )
            new_content = (
                new_page.read_text(encoding="utf-8")
                if new_page and new_page.exists()
                else ""
            )
            diff = difflib.unified_diff(
                page.html.splitlines(),
                new_content.splitlines(),
                fromfile=page.url,
                tofile=tofile,
                lineterm="",
            )
            diffs.append(DiffResult(page=page.url, diff="\n".join(diff)))
        return PreviewIndex(diffs=diffs)

    def _locate_new_page(
        self,
        relative_path: Path,
        newsite_root: Path,
        unused_files: List[Path],
        used_files: set[Path],
        index_page: Path,
    ) -> Optional[Path]:
        """Return the best matching generated page for ``relative_path``."""

        candidates = [newsite_root / relative_path]

        if relative_path.name:
            candidates.append(newsite_root / relative_path.name)

        stem = relative_path.stem
        if relative_path.suffix:
            candidates.append(newsite_root / f"{stem}{relative_path.suffix}")
        else:
            candidates.append(newsite_root / f"{stem}.html")

        for candidate in candidates:
            if candidate.exists() and candidate not in used_files:
                if candidate in unused_files:
                    unused_files.remove(candidate)
                used_files.add(candidate)
                log_event(
                    self.logger,
                    logging.DEBUG,
                    "comparator.match",
                    requested=str(relative_path),
                    selected=str(candidate.relative_to(newsite_root)),
                )
                return candidate

        if unused_files:
            candidate = unused_files.pop(0)
            used_files.add(candidate)
            log_event(
                self.logger,
                logging.INFO,
                "comparator.match.fallback_unused",
                requested=str(relative_path),
                selected=str(candidate.relative_to(newsite_root)),
            )
            return candidate

        if index_page.exists() and index_page not in used_files:
            used_files.add(index_page)
            log_event(
                self.logger,
                logging.WARNING,
                "comparator.match.index",
                requested=str(relative_path),
                selected="index.html",
            )
            return index_page

        log_event(
            self.logger,
            logging.ERROR,
            "comparator.match.missing",
            requested=str(relative_path),
        )
        return None


__all__ = ["ComparatorAgent"]
