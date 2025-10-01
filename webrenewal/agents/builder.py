"""Implementation of the A13 Builder agent."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Set

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .base import Agent
from ..models import BuildArtifact, ContentBlock, ContentBundle, NavModel, NavigationItem, ThemeTokens
from ..storage import SANDBOX_DIR, list_files


def _slugify(block: ContentBlock, index: int, existing: Set[str]) -> str:
    """Generate a filesystem-friendly slug for a content block."""

    import re

    base_title = block.title or f"section-{index}"
    base_slug = re.sub(r"[^a-zA-Z0-9]+", "-", base_title.lower()).strip("-")
    if not base_slug:
        base_slug = f"section-{index}"

    candidate = base_slug
    suffix = 2
    while candidate in existing:
        candidate = f"{base_slug}-{suffix}"
        suffix += 1

    return candidate


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


_FRAMEWORK_PRESETS: Mapping[str, Dict[str, object]] = {
    "vanilla": {
        "name": "vanilla",
        "css_links": [],
        "body_class": "vanilla-scope",
        "description": "Built-in modern layout with custom CSS variables.",
    },
    "bootstrap": {
        "name": "bootstrap",
        "css_links": [
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
        ],
        "body_class": "bootstrap-scope",
        "description": "Bootstrap 5 utility classes available via CDN.",
    },
    "tailwind": {
        "name": "tailwind",
        "css_links": [
            "https://cdn.jsdelivr.net/npm/tailwindcss@3.4.4/dist/tailwind.min.css",
        ],
        "body_class": "tailwind-scope",
        "description": "Tailwind utility classes for rapid prototyping.",
    },
}


def _build_css_variables(theme: ThemeTokens) -> Dict[str, str]:
    """Flatten the theme tokens into CSS custom properties."""

    return theme.css_variables()


class BuilderAgent(Agent[tuple[ContentBundle, ThemeTokens, NavModel], BuildArtifact]):
    """Assemble a static site using Jinja2 templates."""

    def __init__(self, css_framework: str = "vanilla") -> None:
        super().__init__(name="A13.Builder")
        if css_framework not in _FRAMEWORK_PRESETS:
            raise ValueError(
                "Unsupported CSS framework '%s'. Choose from %s"
                % (css_framework, ", ".join(sorted(_FRAMEWORK_PRESETS)))
            )
        self._framework = css_framework
        self._framework_meta = _FRAMEWORK_PRESETS[css_framework]
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._env.globals["FRAMEWORK_PRESETS"] = _FRAMEWORK_PRESETS

    def run(self, data: tuple[ContentBundle, ThemeTokens, NavModel]) -> BuildArtifact:
        content, theme, nav = data
        output_dir = SANDBOX_DIR / "newsite"
        output_dir.mkdir(parents=True, exist_ok=True)

        page_entries: list[tuple[ContentBlock, str]] = []
        used_slugs: Set[str] = set()
        for index, block in enumerate(content.blocks, start=1):
            slug = _slugify(block, index, used_slugs)
            used_slugs.add(slug)
            filename = f"{slug}.html"
            page_entries.append((block, filename))

        augmented_navigation = _merge_navigation(nav, page_entries)
        generated_pages = [
            {"title": block.title or filename, "href": filename}
            for block, filename in page_entries
        ]

        css_variables = _build_css_variables(theme)

        index_template = self._env.get_template("index.html.jinja")
        index_html = index_template.render(
            content=content,
            theme=theme,
            navigation=augmented_navigation,
            generated_pages=generated_pages,
            css_variables=css_variables,
            framework=self._framework_meta,
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
                css_variables=css_variables,
                framework=self._framework_meta,
            )
            (output_dir / filename).write_text(page_html, encoding="utf-8")

        files = list_files(output_dir)
        return BuildArtifact(output_dir=str(output_dir), files=files)


__all__ = ["BuilderAgent"]
