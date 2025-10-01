"""Tests for :mod:`webrenewal.storage`."""

from __future__ import annotations

from pathlib import Path

from webrenewal.models import ToolCatalog, ToolInfo
from webrenewal.storage import list_files, write_json, write_text


def test_write_json_persists_serializable(sandbox_dir: Path) -> None:
    """Given a serialisable dataclass When write_json is called Then the file is created under the sandbox."""

    catalog = ToolCatalog(tools=[ToolInfo(name="tool", category="cat", description="desc", usage_snippet="use")])

    path = write_json(catalog, "tools.json")

    assert path.exists()
    assert path.read_text(encoding="utf-8").strip().startswith("{")


def test_write_text_stores_plain_content(sandbox_dir: Path) -> None:
    """Given raw text When write_text is executed Then the bytes are flushed to disk."""

    path = write_text("hello", "notes/info.txt")

    assert path.exists()
    assert path.read_text(encoding="utf-8") == "hello"


def test_list_files_returns_sorted_entries(sandbox_dir: Path) -> None:
    """Given nested files When list_files is called Then sorted relative paths are returned."""

    (sandbox_dir / "a.txt").write_text("a", encoding="utf-8")
    nested = sandbox_dir / "nested"
    nested.mkdir()
    (nested / "b.txt").write_text("b", encoding="utf-8")

    files = list_files(sandbox_dir)

    assert files == ["a.txt", "nested/b.txt"]

