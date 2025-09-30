"""Implementation of the A13 Builder agent."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .base import Agent
from ..models import BuildArtifact, ContentBlock, ContentBundle, NavModel, NavigationItem, ThemeTokens
from ..storage import SANDBOX_DIR, list_files


def _slugify(block: ContentBlock, index: int) -> str:
    """Generate a filesystem-friendly slug for a content block."""

    import re

    title = block.title or f"section-{index}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    return slug or f"section-{index}"


def _merge_navigation(nav: NavModel, blocks: Iterable[tuple[ContentBlock, str]]) -> List[NavigationItem]:
    """Return the navigation augmented with newly generated pages."""

    existing = list(nav.items)
    seen = {(item.label.strip().lower(), item.href) for item in existing}

    for block, filename in blocks:
        label = block.title or filename
        href = filename
        key = (label.strip().lower(), href)
        if key not in seen:
            seen.add(key)
            existing.append(NavigationItem(label=label, href=href))

    return existing

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


class BuilderAgent(Agent[tuple[ContentBundle, ThemeTokens, NavModel], BuildArtifact]):
    """Assemble a static site using Jinja2 templates."""

    def __init__(self) -> None:
        super().__init__(name="A13.Builder")
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def run(self, data: tuple[ContentBundle, ThemeTokens, NavModel]) -> BuildArtifact:
        content, theme, nav = data
        output_dir = SANDBOX_DIR / "newsite"
        output_dir.mkdir(parents=True, exist_ok=True)

        page_entries: list[tuple[ContentBlock, str]] = []
        for index, block in enumerate(content.blocks, start=1):
            slug = _slugify(block, index)
            filename = f"{slug}.html"
            page_entries.append((block, filename))

        augmented_navigation = _merge_navigation(nav, page_entries)
        generated_pages = [
            {"title": block.title or filename, "href": filename}
            for block, filename in page_entries
        ]

        index_template = self._env.get_template("index.html.jinja")
        index_html = index_template.render(
            content=content,
            theme=theme,
            navigation=augmented_navigation,
            generated_pages=generated_pages,
        )
        (output_dir / "index.html").write_text(index_html, encoding="utf-8")

        page_template = self._env.get_template("page.html.jinja")
        for block, filename in page_entries:
            page_html = page_template.render(
                block=block,
                theme=theme,
                navigation=augmented_navigation,
                home_href="index.html",
                meta_title=(block.title or content.meta_title or "Renewed Page"),
                fallback_used=content.fallback_used,
            )
            (output_dir / filename).write_text(page_html, encoding="utf-8")

        files = list_files(output_dir)
        return BuildArtifact(output_dir=str(output_dir), files=files)


__all__ = ["BuilderAgent"]
