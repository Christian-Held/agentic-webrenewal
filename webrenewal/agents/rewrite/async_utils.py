"""Utilities for safely executing async rewrite workflows."""

from __future__ import annotations

import asyncio
from typing import Any


def run_async(coro: Any) -> Any:
    try:
        return asyncio.run(coro)
    except RuntimeError as exc:  # pragma: no cover - defensive branch
        if "asyncio.run()" not in str(exc):
            raise
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
            loop.close()


__all__ = ["run_async"]
