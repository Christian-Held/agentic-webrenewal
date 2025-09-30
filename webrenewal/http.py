"""HTTP helper utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

import requests


@dataclass(slots=True)
class HttpResponse:
    url: str
    status_code: int
    headers: Dict[str, str]
    text: str


def get(url: str, timeout: int = 20, headers: Dict[str, str] | None = None) -> HttpResponse:
    """Perform a HTTP GET request and return an :class:`HttpResponse`."""

    logger = logging.getLogger("http")
    logger.debug("Fetching URL %s", url)
    response = requests.get(url, timeout=timeout, headers=headers)
    logger.info("Fetched %s with status %s", url, response.status_code)
    return HttpResponse(
        url=str(response.url),
        status_code=response.status_code,
        headers=dict(response.headers),
        text=response.text,
    )


__all__ = ["get", "HttpResponse"]
