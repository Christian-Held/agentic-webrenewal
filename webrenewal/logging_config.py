"""Logging utilities for the Agentic WebRenewal project."""

from __future__ import annotations

import logging
import sys
from typing import Optional


_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


def configure_logging(level: int = logging.INFO, stream: Optional[logging.StreamHandler] = None) -> None:
    """Configure the global logging settings for the application.

    Parameters
    ----------
    level:
        The logging level to apply across the root logger.
    stream:
        Optional stream handler. When omitted a handler pointing to ``sys.stdout``
        is used.
    """

    root_logger = logging.getLogger()
    if stream is None:
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
    else:
        handler = stream

    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    # Clear previous handlers to avoid duplicated log lines when configure_logging
    # gets called multiple times during testing.
    for existing in list(root_logger.handlers):
        root_logger.removeHandler(existing)

    root_logger.setLevel(level)
    root_logger.addHandler(handler)


__all__ = ["configure_logging"]
