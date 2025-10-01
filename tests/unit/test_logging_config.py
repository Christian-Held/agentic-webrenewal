"""Tests for :mod:`webrenewal.logging_config`."""

from __future__ import annotations

import logging
from io import StringIO

from webrenewal.logging_config import configure_logging


def test_configure_logging_sets_handler() -> None:
    """Given a custom stream When configure_logging is called Then logs are formatted and directed there."""

    stream = StringIO()
    handler = logging.StreamHandler(stream)

    configure_logging(level=logging.DEBUG, stream=handler)

    logger = logging.getLogger("demo")
    logger.debug("hello")

    contents = stream.getvalue()
    assert "hello" in contents
    assert "demo" in contents

