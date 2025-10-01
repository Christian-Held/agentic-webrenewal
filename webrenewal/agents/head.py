"""Head agent for applying document-level patches."""

from __future__ import annotations

from typing import List

from .base import Agent
from ..postedit.models import ChangeOperation, SiteState


class HeadAgent(Agent[tuple[SiteState, List[ChangeOperation]], SiteState]):
    """Apply head-level updates from change operations."""

    def __init__(self) -> None:
        super().__init__(name="AHead.Patch")

    def run(self, data: tuple[SiteState, List[ChangeOperation]]) -> SiteState:  # type: ignore[override]
        state, operations = data
        for op in operations:
            if op.type != "head.patch":
                continue
            payload = op.payload or {}
            policy = payload.get("title_policy", "site_first")
            title = state.head.get("title", "")
            brand = state.head.get("brand", title)
            if policy == "brand_first" and brand:
                state.head["title"] = f"{brand} | {title}" if title else brand
            elif title:
                state.head["title"] = title
            if payload.get("favicon"):
                self._set_favicon(state, payload["favicon"])
        return state

    # ------------------------------------------------------------------
    def _set_favicon(self, state: SiteState, href: str) -> None:
        links = list(state.head.get("links", []))
        filtered = [link for link in links if link.get("rel") != "icon"]
        filtered.append({"rel": "icon", "href": href})
        state.head["links"] = filtered


__all__ = ["HeadAgent"]

