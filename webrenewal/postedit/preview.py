"""Preview and diff utilities for post-edit runs."""

from __future__ import annotations

import difflib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(slots=True)
class PreviewResult:
    preview_id: str
    index_path: Path
    old_dir: Path | None
    new_dir: Path


class PreviewGenerator:
    """Create HTML previews comparing old and new dist directories."""

    def __init__(self, sandbox_dir: Path) -> None:
        self.preview_root = sandbox_dir / "preview"
        self.preview_root.mkdir(parents=True, exist_ok=True)

    def generate(self, *, old_dir: Path | None, new_dir: Path) -> PreviewResult:
        preview_id = uuid.uuid4().hex
        target_dir = self.preview_root / preview_id
        target_dir.mkdir(parents=True, exist_ok=True)
        index_path = target_dir / "index.html"

        if old_dir and old_dir.exists():
            diff_html = self._diff_directories(old_dir, new_dir)
        else:
            diff_html = self._render_new_only(new_dir)

        index_path.write_text(diff_html, encoding="utf-8")
        return PreviewResult(preview_id=preview_id, index_path=index_path, old_dir=old_dir, new_dir=new_dir)

    def _diff_directories(self, old_dir: Path, new_dir: Path) -> str:
        old_files = self._list_files(old_dir)
        new_files = self._list_files(new_dir)
        all_files = sorted(set(old_files) | set(new_files))

        sections: List[str] = [
            "<h1>Preview Diff</h1>",
            "<p>Comparing the previous build with the new build.</p>",
        ]

        diff = difflib.HtmlDiff(wrapcolumn=80)
        for relative in all_files:
            old_path = old_dir / relative
            new_path = new_dir / relative
            if old_path.exists():
                old_lines = old_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            else:
                old_lines = []
            if new_path.exists():
                new_lines = new_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            else:
                new_lines = []
            if old_lines == new_lines:
                continue
            sections.append(f"<h2>{relative}</h2>")
            sections.append(
                diff.make_table(
                    old_lines,
                    new_lines,
                    fromdesc="previous",
                    todesc="new",
                    context=True,
                    numlines=3,
                )
            )

        if len(sections) == 2:
            sections.append("<p>No differences detected – builds are identical.</p>")

        return self._wrap_html("\n".join(sections))

    def _render_new_only(self, new_dir: Path) -> str:
        sections = [
            "<h1>New Build</h1>",
            "<p>No previous build found. Listing files in the generated directory.</p>",
            "<ul>",
        ]
        for relative in self._list_files(new_dir):
            sections.append(f"  <li>{relative}</li>")
        sections.append("</ul>")
        return self._wrap_html("\n".join(sections))

    def _list_files(self, directory: Path) -> List[str]:
        files: List[str] = []
        for path in directory.rglob("*"):
            if path.is_file():
                files.append(str(path.relative_to(directory)))
        return sorted(files)

    def _wrap_html(self, body: str) -> str:
        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head><meta charset=\"utf-8\"/><title>Preview</title>"
            "<style>body{font-family:Inter,sans-serif;margin:2rem;}table{border-collapse:collapse;}"
            "td,th{border:1px solid #ccc;padding:0.25rem 0.5rem;}"
            "tr:nth-child(even){background:#f6f6f6;}</style></head>\n"
            "<body>\n"
            f"{body}\n"
            "</body>\n"
            "</html>\n"
        )


__all__ = ["PreviewGenerator", "PreviewResult"]

