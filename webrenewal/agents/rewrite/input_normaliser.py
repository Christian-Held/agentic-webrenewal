"""Utilities for converting legacy rewrite inputs into the canonical form."""

from __future__ import annotations

from typing import Tuple

from ...models import ContentExtract, RenewalPlan
from .types import RewriteInput


class InputNormaliser:
    """Accept both legacy and domain-aware rewrite payloads."""

    def normalise(self, data: RewriteInput) -> Tuple[str, ContentExtract, RenewalPlan]:
        if len(data) == 3:
            domain, content, plan = data  # type: ignore[misc]
        elif len(data) == 2:
            content, plan = data  # type: ignore[misc]
            domain = None
        else:  # pragma: no cover - defensive
            raise ValueError("RewriteAgent expects a 2- or 3-item tuple")

        if not isinstance(content, ContentExtract) or not isinstance(plan, RenewalPlan):
            raise TypeError("RewriteAgent received unexpected input types")

        resolved_domain = (
            domain
            or getattr(content, "domain", None)
            or getattr(plan, "domain", None)
            or "unknown-site"
        )

        return resolved_domain, content, plan


__all__ = ["InputNormaliser"]
