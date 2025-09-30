"""HTTP helper utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

import requests

from .tracing import log_event


@dataclass(slots=True)
class HttpResponse:
    url: str
    status_code: int
    headers: Dict[str, str]
    text: str


def get(url: str, timeout: int = 20, headers: Dict[str, str] | None = None) -> HttpResponse:
    """Perform a HTTP GET request and return an :class:`HttpResponse`."""

    logger = logging.getLogger("http")
    log_event(
        logger,
        logging.DEBUG,
        "http.request",
        method="GET",
        url=url,
        timeout=timeout,
    )
    response = requests.get(url, timeout=timeout, headers=headers)
    elapsed_ms = (
        round(response.elapsed.total_seconds() * 1000, 2)
        if getattr(response, "elapsed", None)
        else None
    )
    log_event(
        logger,
        logging.INFO,
        "http.response",
        method="GET",
        url=str(response.url),
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
    )
    return HttpResponse(
        url=str(response.url),
        status_code=response.status_code,
        headers=dict(response.headers),
        text=response.text,
    )


__all__ = ["get", "HttpResponse"]
