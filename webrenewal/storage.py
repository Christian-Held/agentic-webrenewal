"""Persistence helpers for the pipeline artifacts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .models import Serializable
from .tracing import log_event

SANDBOX_DIR = Path("sandbox")

_LOGGER = logging.getLogger("storage")


def write_json(data: Serializable, filename: str) -> Path:
    """Serialize ``data`` to JSON within the sandbox directory."""

    path = SANDBOX_DIR / filename
    log_event(
        _LOGGER,
        logging.DEBUG,
        "storage.write_json.start",
        filename=filename,
        path=str(path),
        data_type=type(data).__name__,
    )
    data.to_json(path)
    log_event(
        _LOGGER,
        logging.INFO,
        "storage.write_json.finish",
        filename=filename,
        path=str(path),
    )
    return path


def write_text(content: str, filename: str) -> Path:
    """Write raw ``content`` to a file inside the sandbox directory."""

    path = SANDBOX_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    log_event(
        _LOGGER,
        logging.DEBUG,
        "storage.write_text.start",
        filename=filename,
        path=str(path),
        bytes=len(content.encode("utf-8")),
    )
    path.write_text(content, encoding="utf-8")
    log_event(
        _LOGGER,
        logging.INFO,
        "storage.write_text.finish",
        filename=filename,
        path=str(path),
    )
    return path


def list_files(directory: Path) -> list[str]:
    """Return a sorted list of relative file paths inside ``directory``."""

    files: list[str] = []
    for item in directory.rglob("*"):
        if item.is_file():
            files.append(str(item.relative_to(directory)))
    return sorted(files)


__all__ = ["write_json", "write_text", "SANDBOX_DIR", "list_files"]
