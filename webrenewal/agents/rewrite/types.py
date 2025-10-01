"""Shared typing helpers for the rewrite agent package."""

from __future__ import annotations

from typing import Tuple, Union

from ...models import ContentExtract, RenewalPlan

RewriteInput = Union[
    Tuple[ContentExtract, RenewalPlan],
    Tuple[str, ContentExtract, RenewalPlan],
]

__all__ = ["RewriteInput"]
