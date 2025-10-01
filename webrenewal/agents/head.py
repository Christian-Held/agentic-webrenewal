"""Head agent for applying document-level patches."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import Agent
from ..postedit.models import ChangeOperation, SiteState


class HeadAgent(Agent[tuple[SiteState, List[ChangeOperation]], SiteState]):
    """Apply head-level updates from change operations."""

    def __init__(self) -> None:
        super().__init__(name="AHead.Patch")

    def run(self, data: tuple[SiteState, List[ChangeOperation]]) -> SiteState:  # type: ignore[override]
        state, operations = data
        self.apply_post_edit(state, operations)
        return state

    def apply_post_edit(self, state: SiteState, operations: List[ChangeOperation]) -> Dict[str, Any]:
        """Apply ``head.patch`` operations and return a JSON-serialisable summary."""

        patched = 0
        title_updates = 0
        favicon_updates = 0
        meta_updates = 0
        link_appends = 0

        for op in operations:
            if op.type != "head.patch":
                continue

            payload = op.payload or {}
            changed = False

            if "title_policy" in payload:
                if self._apply_title_policy(state, payload["title_policy"]):
                    title_updates += 1
                    changed = True

            if payload.get("favicon"):
                if self._set_favicon(state, payload["favicon"]):
                    favicon_updates += 1
                    changed = True

            meta_payload = payload.get("meta")
            if isinstance(meta_payload, dict):
                applied = self._merge_nested_dict(state.head.setdefault("meta", {}), meta_payload)
                if applied:
                    meta_updates += applied
                    changed = True

            links_payload = payload.get("links")
            appended = self._append_links(state, links_payload)
            if appended:
                link_appends += appended
                changed = True

            if changed:
                patched += 1

        return {
            "patched": patched,
            "title_updates": title_updates,
            "favicon_updates": favicon_updates,
            "meta_updates": meta_updates,
            "links_appended": link_appends,
        }

    # ------------------------------------------------------------------
    def _apply_title_policy(self, state: SiteState, policy: str) -> bool:
        policy = str(policy or "site_first").strip().lower()
        title = state.head.get("title", "")
        brand = state.head.get("brand", title)
        original = state.head.get("title")

        if policy == "brand_first" and brand:
            new_title = f"{brand} | {title}" if title else brand
        else:
            new_title = title or brand or original

        if new_title and new_title != original:
            state.head["title"] = new_title
            return True
        return False

    def _set_favicon(self, state: SiteState, href: str) -> bool:
        links = list(state.head.get("links", []))
        filtered = [link for link in links if link.get("rel") != "icon"]
        candidate = {"rel": "icon", "href": href}
        filtered.append(candidate)
        if filtered != links:
            state.head["links"] = filtered
            return True
        return False

    def _merge_nested_dict(self, target: Dict[str, Any], updates: Dict[str, Any]) -> int:
        updated = 0
        for key, value in updates.items():
            if isinstance(value, dict):
                nested = target.setdefault(key, {})
                updated += self._merge_nested_dict(nested, value)
            else:
                if target.get(key) != value:
                    target[key] = value
                    updated += 1
        return updated

    def _append_links(self, state: SiteState, links: Any) -> int:
        if not isinstance(links, list):
            return 0
        current = list(state.head.get("links", []))
        appended = 0
        for link in links:
            if isinstance(link, dict):
                current.append({k: v for k, v in link.items()})
                appended += 1
        if appended:
            state.head["links"] = current
        return appended


__all__ = ["HeadAgent"]

