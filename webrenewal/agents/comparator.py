"""Implementation of the A14 Comparator agent."""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup
from .base import Agent
from ..models import CrawlResult, DiffResult, PreviewIndex
from ..storage import SANDBOX_DIR
from ..tracing import log_event
from ..utils import url_to_relative_path


@dataclass(slots=True)
class _GeneratedPage:
    path: Path
    slug: str
    title: Optional[str]


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
        generated_index = [
            _GeneratedPage(
                path=path,
                slug=self._slug_for_path(path.relative_to(newsite_root)),
                title=self._extract_title(path),
            )
            for path in generated_files
        ]
        index_page = newsite_root / "index.html"
        used_files: set[Path] = set()

        diffs: List[DiffResult] = []
        for page in crawl.pages:
            relative_path = url_to_relative_path(page.url)
            new_page = self._locate_new_page(
                relative_path,
                newsite_root,
                generated_index,
                used_files,
                index_page,
                page.html,
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
        generated_index: List[_GeneratedPage],
        used_files: set[Path],
        index_page: Path,
        original_html: str,
    ) -> Optional[Path]:
        """Return the best matching generated page for ``relative_path``."""

        direct_candidates = [newsite_root / relative_path]

        if relative_path.name:
            direct_candidates.append(newsite_root / relative_path.name)

        stem = relative_path.stem or relative_path.name
        if stem:
            if relative_path.suffix:
                direct_candidates.append(newsite_root / f"{stem}{relative_path.suffix}")
            direct_candidates.append(newsite_root / f"{stem}.html")

        index_lookup = {page.path: page for page in generated_index}

        for candidate in direct_candidates:
            page_meta = index_lookup.get(candidate)
            if page_meta and candidate not in used_files:
                used_files.add(candidate)
                log_event(
                    self.logger,
                    logging.DEBUG,
                    "comparator.match.direct",
                    requested=str(relative_path),
                    selected=str(candidate.relative_to(newsite_root)),
                )
                return candidate

        target_slug = self._slug_for_path(relative_path)
        original_title = self._extract_source_title(original_html)

        available_candidates = [
            page
            for page in generated_index
            if page.path not in used_files and page.path.exists()
        ]

        best_match: Optional[_GeneratedPage] = None
        best_score = 0.0

        for candidate in available_candidates:
            score = self._score_candidate(target_slug, original_title, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_match and best_score >= 0.45:
            used_files.add(best_match.path)
            log_event(
                self.logger,
                logging.INFO,
                "comparator.match.similarity",
                requested=str(relative_path),
                selected=str(best_match.path.relative_to(newsite_root)),
                score=f"{best_score:.3f}",
            )
            return best_match.path

        fallback = next(
            (page for page in available_candidates if page.path != index_page),
            None,
        )
        if fallback:
            used_files.add(fallback.path)
            log_event(
                self.logger,
                logging.WARNING,
                "comparator.match.fallback_unused",
                requested=str(relative_path),
                selected=str(fallback.path.relative_to(newsite_root)),
            )
            return fallback.path

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

    def _score_candidate(
        self,
        target_slug: str,
        original_title: Optional[str],
        candidate: _GeneratedPage,
    ) -> float:
        slug_score = difflib.SequenceMatcher(None, target_slug, candidate.slug).ratio()
        title_score = 0.0
        if original_title and candidate.title:
            title_score = difflib.SequenceMatcher(
                None, original_title.lower(), candidate.title.lower()
            ).ratio()
        return (slug_score * 0.6) + (title_score * 0.4)

    def _slug_for_path(self, path: Path) -> str:
        parts = [
            part for part in path.parts if part and part not in {"index", "index.html"}
        ]
        if not parts:
            parts = [path.stem or "index"]
        cleaned = [part.rsplit(".", 1)[0].lower() for part in parts]
        return "-".join(cleaned)

    def _extract_title(self, path: Path) -> Optional[str]:
        try:
            html = path.read_text(encoding="utf-8")
        except OSError:
            return None
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            return title_tag.get_text(strip=True)
        heading = soup.find(["h1", "h2"])
        if heading and heading.get_text(strip=True):
            return heading.get_text(strip=True)
        return None

    def _extract_source_title(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            return title_tag.get_text(strip=True)
        heading = soup.find(["h1", "h2"])
        if heading and heading.get_text(strip=True):
            return heading.get_text(strip=True)
        return None


__all__ = ["ComparatorAgent"]
