"""Incremental builder for post-edit site rendering."""

from __future__ import annotations

import hashlib
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .models import ChangeSet, SiteBlock, SitePage, SiteState


@dataclass(slots=True)
class BuildResult:
    """Result of an incremental build run."""

    output_dir: Path
    changed_files: List[Path] = field(default_factory=list)
    unchanged_files: List[Path] = field(default_factory=list)
    css_path: Path | None = None


class IncrementalBuilder:
    """Generate a static site from the SiteState while reusing unchanged files."""

    def __init__(self, sandbox_dir: Path) -> None:
        self.sandbox_dir = sandbox_dir

    def build(self, state: SiteState, change_set: ChangeSet) -> BuildResult:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_dir = self.sandbox_dir / f"newsite-{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        previous_dir = state.build.get("latest_dist")
        previous_dir_path = Path(previous_dir) if previous_dir else None

        dirty_pages = self._determine_dirty_pages(change_set, state)
        changed_files: List[Path] = []
        unchanged_files: List[Path] = []

        css_path = self._write_css(state, output_dir, change_set)
        if css_path:
            changed_files.append(css_path)

        for page in state.pages:
            filename = self._page_filename(page)
            target = output_dir / filename
            target.parent.mkdir(parents=True, exist_ok=True)

            should_render = page.path in dirty_pages or page.url in dirty_pages
            previous_file = (
                previous_dir_path / filename if previous_dir_path else None
            )

            if should_render or not previous_file or not previous_file.exists():
                html = self._render_page(state, page)
                content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
                page.content_hash = content_hash
                page.rendered = html
                target.write_text(html, encoding="utf-8")
                changed_files.append(target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(previous_file, target)
                unchanged_files.append(target)

        state.build["latest_dist"] = str(output_dir)
        history = state.build.setdefault("history", [])
        history.append({"dir": str(output_dir), "timestamp": timestamp})

        return BuildResult(
            output_dir=output_dir,
            changed_files=changed_files,
            unchanged_files=unchanged_files,
            css_path=css_path,
        )

    # ------------------------------------------------------------------
    def _determine_dirty_pages(self, change_set: ChangeSet, state: SiteState) -> set[str]:
        dirty: set[str] = set()
        for op in change_set.operations:
            if op.type.startswith("content.") or op.type.startswith("seo."):
                if op.page:
                    dirty.add(op.page)
            if op.type.startswith("head."):
                dirty.update(page.path for page in state.pages)
            if op.type.startswith("nav."):
                dirty.update(page.path for page in state.pages)
        return dirty

    def _page_filename(self, page: SitePage) -> str:
        path = page.path or page.url or "index"
        if path.endswith(".html"):
            filename = path.lstrip("/")
        else:
            slug = path.strip("/") or "index"
            if slug.endswith(".html"):
                filename = slug
            elif slug == "index":
                filename = "index.html"
            else:
                filename = f"{slug}.html"
        return filename

    def _render_page(self, state: SiteState, page: SitePage) -> str:
        nav_html = state.nav.get("html") or self._build_nav_html(state)
        head = state.head
        seo_meta = state.seo.get("meta", {}).get(page.path or page.url, {})
        blocks_html = "\n".join(self._render_block(block) for block in page.blocks)
        head_meta_parts = [
            f'<meta name="description" content="{seo_meta.get("description", "")}" />'
            if seo_meta
            else "",
        ]
        head_links = "\n".join(
            f'<link rel="{link.get("rel", "stylesheet")}" href="{link.get("href", "")}">' for link in head.get("links", [])
        )
        title = head.get("title") or page.title or "Updated Page"
        html = (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            f"  <meta charset=\"utf-8\"/>\n"
            f"  <title>{title}</title>\n"
            f"  {''.join(head_meta_parts)}\n"
            f"  <link rel=\"stylesheet\" href=\"assets/css/main.css\"/>\n"
            f"  {head_links}\n"
            "</head>\n"
            "<body>\n"
            f"  <header>{nav_html}</header>\n"
            f"  <main>\n{blocks_html}\n  </main>\n"
            "  <footer class=\"site-footer\">Generated by Post-Edit Builder</footer>\n"
            "</body>\n"
            "</html>\n"
        )
        return html

    def _render_block(self, block: SiteBlock) -> str:
        text = block.text
        heading = block.meta.get("heading") or block.id.replace("-", " ").title()
        extra = ""
        if block.meta.get("call_to_action"):
            extra = (
                "<p class=\"cta\">"
                f"{block.meta['call_to_action']}"
                "</p>"
            )
        return (
            f"    <section id=\"{block.id}\" class=\"block-{block.type}\">\n"
            f"      <h2>{heading}</h2>\n"
            f"      <p>{text}</p>\n"
            f"      {extra}\n"
            "    </section>"
        )

    def _build_nav_html(self, state: SiteState) -> str:
        items_html = "".join(
            f"<li><a href=\"{item.get('href', '#')}\">{item.get('label', 'Item')}</a></li>"
            for item in state.nav.get("items", [])
        )
        layout = state.nav.get("layout", {})
        classes = ["nav"]
        if layout.get("location"):
            classes.append(f"nav-{layout['location']}")
        return f"<nav class=\"{' '.join(classes)}\"><ul>{items_html}</ul></nav>"

    def _write_css(self, state: SiteState, output_dir: Path, change_set: ChangeSet) -> Path | None:
        if not any(op.type.startswith("css.") for op in change_set.operations):
            # Reuse previous CSS if available
            previous_dir = state.build.get("latest_dist")
            if previous_dir:
                previous_path = Path(previous_dir) / "assets" / "css" / "main.css"
                if previous_path.exists():
                    target = output_dir / "assets" / "css" / "main.css"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(previous_path, target)
                    return target
            return None

        css_content = state.css_bundle.get("raw") or self._generate_css_from_tokens(state)
        target = output_dir / "assets" / "css" / "main.css"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(css_content, encoding="utf-8")
        return target

    def _generate_css_from_tokens(self, state: SiteState) -> str:
        tokens = state.theme.get("tokens", {})
        palette = tokens.get("palette", {})
        shape = tokens.get("shape", {})
        shadow = tokens.get("shadow", {})
        css_lines = [":root {"]
        for key, value in palette.items():
            css_lines.append(f"  --color-{key}: {value};")
        if shape.get("radius"):
            css_lines.append(f"  --radius-base: {shape['radius']};")
        css_lines.append("}")
        css_lines.append("")
        css_lines.append(
            ".btn-primary {"
            "  background: var(--color-primary, #0d6efd);"
            "  color: #fff;"
            "  border-radius: var(--radius-base, 0.5rem);"
            f"  box-shadow: {shadow.get('button', '0 4px 12px rgba(0,0,0,0.1)')};"
            "  padding: 0.75rem 1.5rem;"
            "}"
        )
        css_lines.append("")
        css_lines.append(
            "nav ul { display: flex; gap: 1rem; list-style: none; padding: 0; margin: 0; }"
        )
        return "\n".join(css_lines)


__all__ = ["IncrementalBuilder", "BuildResult"]

