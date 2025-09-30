"""Helpers for working with URLs and filesystem paths."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse, unquote


def url_to_relative_path(url: str) -> Path:
    """Convert a page URL to a relative ``Path`` suitable for the sandbox.

    The function keeps the original hierarchy and ensures a concrete filename,
    normalising directories to ``index.html`` and appending a short hash when a
    query string is present to avoid collisions.
    """

    parsed = urlparse(url)
    path = unquote(parsed.path)
    if not path or path.endswith("/"):
        path = f"{path}index.html"
    elif not Path(path).suffix:
        path = f"{path.rstrip('/')}/index.html"

    path = path.lstrip("/") or "index.html"

    if parsed.query:
        digest = hashlib.sha1(parsed.query.encode("utf-8")).hexdigest()[:8]
        stem_path = Path(path)
        suffix = stem_path.suffix or ".html"
        stem = stem_path.stem or "index"
        parent = stem_path.parent
        filename = f"{stem}_{digest}{suffix}"
        path = filename if str(parent) in {"", "."} else str(parent / filename)

    return Path(path)


__all__ = ["url_to_relative_path"]
