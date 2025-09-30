"""Utilities for working with domain names and URLs."""

from __future__ import annotations

import re
from urllib.parse import urlparse


def normalise_domain(domain: str) -> str:
    """Return a lowercase host name without protocol or path segments."""

    parsed = urlparse(domain)
    host = parsed.netloc or parsed.path
    host = host.strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host.rstrip("/")


def domain_to_display_name(domain: str) -> str:
    """Generate a human-friendly label derived from ``domain``."""

    host = normalise_domain(domain)
    if not host:
        return domain.strip()

    parts = [segment for segment in re.split(r"[.-]", host) if segment]
    if not parts:
        return host

    return " ".join(segment.capitalize() for segment in parts)


__all__ = ["domain_to_display_name", "normalise_domain"]
