"""Persistence helpers for the pipeline artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Serializable

SANDBOX_DIR = Path("sandbox")


def write_json(data: Serializable, filename: str) -> Path:
    """Serialize ``data`` to JSON within the sandbox directory."""

    path = SANDBOX_DIR / filename
    data.to_json(path)
    return path


def write_text(content: str, filename: str) -> Path:
    """Write raw ``content`` to a file inside the sandbox directory."""

    path = SANDBOX_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def list_files(directory: Path) -> list[str]:
    """Return a sorted list of relative file paths inside ``directory``."""

    files: list[str] = []
    for item in directory.rglob("*"):
        if item.is_file():
            files.append(str(item.relative_to(directory)))
    return sorted(files)


__all__ = ["write_json", "write_text", "SANDBOX_DIR", "list_files"]
