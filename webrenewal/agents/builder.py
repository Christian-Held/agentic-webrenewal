"""Implementation of the A13 Builder agent."""

from __future__ import annotations

from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .base import Agent
from ..models import BuildArtifact, ContentBundle, NavModel, ThemeTokens
from ..storage import SANDBOX_DIR, list_files

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

        template = self._env.get_template("index.html.jinja")
        html = template.render(content=content, theme=theme, navigation=nav)
        output_path = output_dir / "index.html"
        output_path.write_text(html, encoding="utf-8")

        files = list_files(output_dir)
        return BuildArtifact(output_dir=str(output_dir), files=files)


__all__ = ["BuilderAgent"]
