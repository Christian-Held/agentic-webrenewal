"""Delta planning utilities for the post-edit flow."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence

from .postedit.models import ChangeOperation, ChangeSet, SiteState, merge_operations


_ALL_TARGETS = ["css", "seo", "images", "logo", "content", "nav", "head"]


def _extract_colors(prompt: str) -> List[str]:
    names = [
        "blue",
        "navy",
        "teal",
        "green",
        "purple",
        "orange",
        "red",
        "yellow",
        "white",
        "black",
    ]
    prompt_lower = prompt.lower()
    return [name for name in names if name in prompt_lower]


def _detect(keyword: str, prompt: str) -> bool:
    return keyword.lower() in prompt.lower()


def _nav_location_from_prompt(prompt: str, fallback: str) -> str:
    mapping = {
        "top right": "top-right",
        "top-right": "top-right",
        "top left": "top-left",
        "top-left": "top-left",
        "top center": "top-center",
        "center": "top-center",
        "side left": "side-left",
        "left": "side-left",
        "side right": "side-right",
        "right": "side-right",
        "footer": "footer",
    }
    prompt_lower = prompt.lower()
    for key, value in mapping.items():
        if key in prompt_lower:
            return value
    return fallback


def _dropdown_mode_from_prompt(prompt: str, fallback: str) -> str:
    prompt_lower = prompt.lower()
    if "hover" in prompt_lower:
        return "hover"
    if "click" in prompt_lower:
        return "click"
    if "none" in prompt_lower:
        return "none"
    return fallback


def _dropdown_state_from_prompt(prompt: str, fallback: str) -> str:
    prompt_lower = prompt.lower()
    if "open" in prompt_lower and "closed" not in prompt_lower:
        return "open"
    if "closed" in prompt_lower:
        return "closed"
    return fallback


@dataclass(slots=True)
class DeltaPlanner:
    """Translate user intent into concrete change operations."""

    site_state: SiteState
    apply_scope: Sequence[str]
    user_prompt: str | None = None

    def plan(self) -> ChangeSet:
        targets = self._resolve_targets(self.apply_scope)
        operations: List[ChangeOperation] = []

        if "css" in targets:
            operations.extend(self._plan_css())
        if "nav" in targets:
            operations.extend(self._plan_nav())
        if "content" in targets:
            operations.extend(self._plan_content())
        if "seo" in targets:
            operations.extend(self._plan_seo())
        if "head" in targets:
            operations.extend(self._plan_head())

        # Images/logo scopes may be implemented later – keep placeholders for logging
        if "images" in targets:
            operations.append(
                ChangeOperation(
                    type="images.placeholder",
                    payload={"note": "image operations are not implemented in this build"},
                )
            )
        if "logo" in targets:
            operations.append(
                ChangeOperation(
                    type="logo.placeholder",
                    payload={"note": "logo operations are not implemented in this build"},
                )
            )

        operations = merge_operations(operations)
        return ChangeSet(targets=list(targets), operations=operations)

    # ------------------------------------------------------------------
    def _resolve_targets(self, scope: Sequence[str]) -> List[str]:
        if not scope:
            return list(_ALL_TARGETS)
        scope_lower = [entry.strip().lower() for entry in scope if entry]
        if "all" in scope_lower:
            return list(_ALL_TARGETS)
        resolved = [target for target in _ALL_TARGETS if target in scope_lower]
        return resolved or list(_ALL_TARGETS)

    def _plan_css(self) -> List[ChangeOperation]:
        prompt = self.user_prompt or ""
        colors = _extract_colors(prompt)
        palette = self.site_state.theme.get("tokens", {}).get("palette", {}).copy()
        if colors:
            primary = colors[0]
            palette.update(
                {
                    "primary": primary,
                    "accent": colors[1] if len(colors) > 1 else primary,
                    "background": "white" if "white" in colors else palette.get("background", "white"),
                }
            )

        shape_tokens = self.site_state.theme.get("tokens", {}).get("shape", {}).copy()
        if _detect("rounded", prompt):
            shape_tokens["radius"] = "1.25rem"
        if _detect("pill", prompt):
            shape_tokens["radius"] = "999px"

        shadow_tokens = self.site_state.theme.get("tokens", {}).get("shadow", {}).copy()
        if _detect("shadow", prompt):
            shadow_tokens["button"] = "0 12px 32px rgba(12, 35, 64, 0.18)"

        tokens_payload = {
            "palette": palette,
            "shape": shape_tokens,
            "shadow": shadow_tokens,
        }

        operations = [
            ChangeOperation(
                type="css.tokens.update",
                payload={"path": "theme.tokens", "tokens": tokens_payload},
            ),
            ChangeOperation(
                type="css.bundle.rewrite",
                payload={
                    "strategy": "llm",
                    "styleHints": self.user_prompt or "",
                    "framework": self.site_state.css_bundle.get("framework", "bootstrap"),
                },
            ),
        ]
        return operations

    def _plan_nav(self) -> List[ChangeOperation]:
        prompt = self.user_prompt or ""
        current_layout = self.site_state.nav.get("layout", {})
        location = _nav_location_from_prompt(prompt, current_layout.get("location", "top-left"))
        dropdown = _dropdown_mode_from_prompt(prompt, current_layout.get("dropdown", "hover"))
        default_state = _dropdown_state_from_prompt(
            prompt, current_layout.get("default", "closed")
        )
        payload = {
            "location": location,
            "dropdown": dropdown,
            "default": default_state,
        }
        return [ChangeOperation(type="nav.layout.update", payload=payload)]

    def _plan_content(self) -> List[ChangeOperation]:
        prompt = self.user_prompt or ""
        operations: List[ChangeOperation] = []
        for page in self.site_state.pages:
            for block in page.blocks:
                operations.append(
                    ChangeOperation(
                        type="content.rewrite",
                        page=page.path or page.url,
                        block_id=block.id,
                        payload={
                            "length": "longer" if _detect("long", prompt) else "default",
                            "call_to_action": _detect("call-to-action", prompt)
                            or _detect("cta", prompt),
                            "prompt": prompt,
                        },
                    )
                )
        return operations

    def _plan_seo(self) -> List[ChangeOperation]:
        prompt = self.user_prompt or ""
        operations: List[ChangeOperation] = []
        for page in self.site_state.pages:
            operations.append(
                ChangeOperation(
                    type="seo.meta.patch",
                    page=page.path or page.url,
                    payload={
                        "description_hint": prompt,
                        "keywords": self._extract_keywords(prompt),
                    },
                )
            )
        return operations

    def _plan_head(self) -> List[ChangeOperation]:
        prompt = self.user_prompt or ""
        payload = {
            "title_policy": "brand_first" if _detect("brand first", prompt) else "site_first",
            "favicon": self._find_favicon_hint(prompt),
        }
        return [ChangeOperation(type="head.patch", payload=payload)]

    def _extract_keywords(self, prompt: str) -> List[str]:
        words = [word.strip(".,!?") for word in prompt.split()]
        keywords = [word.lower() for word in words if len(word) > 4]
        # Deduplicate while preserving order
        seen: set[str] = set()
        ordered: List[str] = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                ordered.append(keyword)
        return ordered

    def _find_favicon_hint(self, prompt: str) -> str | None:
        match = re.search(r"favicon\s*:\s*(\S+)", prompt, re.IGNORECASE)
        if match:
            return match.group(1)
        return None


__all__ = ["DeltaPlanner"]

