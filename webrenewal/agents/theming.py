"""Implementation of the A12 Theming agent."""

from __future__ import annotations

from typing import Dict

from .base import Agent
from ..models import RenewalPlan, ThemeTokens


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def _is_dark(color: str) -> bool:
    r, g, b = _hex_to_rgb(color)
    # Perceived luminance formula
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance < 0.6


class ThemingAgent(Agent[RenewalPlan, ThemeTokens]):
    """Generate design tokens for the rebuilt site."""

    def __init__(
        self,
        *,
        design_directives: str | None = None,
        theme_style: str | None = None,
        css_framework: str = "vanilla",
    ) -> None:
        super().__init__(name="A12.Theming")
        self._design_directives = design_directives or ""
        self._theme_style = theme_style or ""
        self._css_framework = css_framework or ""

    def run(self, plan: RenewalPlan) -> ThemeTokens:
        directives_parts = [self._design_directives, self._theme_style, self._css_framework]
        directives = " ".join(part.strip().lower() for part in directives_parts if part)
        tokens = self._base_tokens()

        self._apply_framework_rules(tokens, directives)
        self._apply_palette_rules(tokens["colors"], directives)
        self._apply_typography_rules(tokens["typography"], directives)
        self._apply_spacing_rules(tokens["spacing"], directives)
        self._apply_mood_rules(tokens["colors"], directives)
        self._apply_shape_rules(tokens["radius"], directives)
        self._apply_elevation_rules(tokens["elevation"], directives)

        tokens["slots"] = self._build_slots(tokens["colors"])

        return ThemeTokens(**tokens)

    def _apply_framework_rules(self, tokens: Dict[str, Dict[str, str]], directives: str) -> None:
        if "tailwind" in directives:
            tokens["spacing"].update({"md": "1.25rem", "lg": "2rem", "xl": "3.5rem"})
            tokens["typography"].update(
                {
                    "body_family": "'Inter', 'Helvetica Neue', sans-serif",
                    "heading_family": "'Poppins', 'Inter', sans-serif",
                    "heading_weight": "600",
                }
            )
        if "bootstrap" in directives:
            tokens["typography"].update(
                {
                    "body_family": "'Helvetica Neue', Arial, sans-serif",
                    "heading_family": "'Poppins', 'Helvetica Neue', Arial, sans-serif",
                    "heading_weight": "600",
                }
            )

    def _base_tokens(self) -> Dict[str, Dict[str, str]]:
        colors = {
            "primary": "#0b7285",
            "secondary": "#f1f3f5",
            "accent": "#ffd43b",
            "surface": "#ffffff",
            "surface_alt": "#f8f9fa",
            "text": "#212529",
            "muted": "#495057",
            "border": "#dee2e6",
        }
        typography = {
            "body_family": "'Inter', sans-serif",
            "heading_family": "'Inter', sans-serif",
            "base_size": "16px",
            "scale": "1.25",
            "line_height": "1.6",
            "heading_weight": "600",
        }
        spacing = {"xs": "0.25rem", "sm": "0.5rem", "md": "1rem", "lg": "1.5rem", "xl": "2.5rem"}
        radius = {"sm": "0.25rem", "md": "0.5rem", "lg": "0.75rem", "pill": "999px"}
        breakpoints = {"sm": "576px", "md": "768px", "lg": "992px", "xl": "1200px"}
        elevation = {
            "flat": "0 1px 2px rgba(15, 23, 42, 0.06)",
            "raised": "0 12px 30px rgba(15, 23, 42, 0.12)",
            "overlay": "0 24px 60px rgba(15, 23, 42, 0.18)",
        }

        return {
            "colors": colors,
            "typography": typography,
            "spacing": spacing,
            "radius": radius,
            "breakpoints": breakpoints,
            "elevation": elevation,
            "slots": {},
        }

    def _apply_palette_rules(self, colors: Dict[str, str], directives: str) -> None:
        if "blau" in directives or "blue" in directives:
            colors.update(
                {
                    "primary": "#1d4ed8",
                    "accent": "#38bdf8",
                    "secondary": "#e2e8f0",
                }
            )
        if any(token in directives for token in ("weiß", "weiss", "white")):
            colors["surface"] = "#ffffff"
            colors["surface_alt"] = "#f8fafc"
            colors["border"] = "#e2e8f0"
        if "grün" in directives or "green" in directives:
            colors.update(
                {
                    "primary": "#047857",
                    "accent": "#34d399",
                    "secondary": "#ecfdf5",
                }
            )
        if "violett" in directives or "purple" in directives:
            colors.update(
                {
                    "primary": "#6d28d9",
                    "accent": "#c084fc",
                    "secondary": "#f3e8ff",
                }
            )
        if "dunkel" in directives or "dark" in directives:
            colors.update(
                {
                    "surface": "#0f172a",
                    "surface_alt": "#1e293b",
                    "text": "#e2e8f0",
                    "muted": "#94a3b8",
                    "border": "#1f2937",
                }
            )

    def _apply_typography_rules(self, typography: Dict[str, str], directives: str) -> None:
        if "serif" in directives:
            typography.update(
                {
                    "body_family": "'Merriweather', serif",
                    "heading_family": "'Playfair Display', serif",
                    "heading_weight": "500",
                }
            )
        if "tech" in directives or "modern" in directives:
            typography.update(
                {
                    "body_family": "'IBM Plex Sans', 'Inter', sans-serif",
                    "heading_family": "'IBM Plex Sans', 'Inter', sans-serif",
                    "heading_weight": "600",
                    "scale": "1.2",
                }
            )

    def _apply_spacing_rules(self, spacing: Dict[str, str], directives: str) -> None:
        if any(token in directives for token in ("luftig", "airy", "spacious")):
            spacing.update({"md": "1.5rem", "lg": "2rem", "xl": "3rem"})
        if any(token in directives for token in ("kompakt", "compact")):
            spacing.update({"md": "0.75rem", "lg": "1rem", "xl": "1.5rem"})

    def _apply_mood_rules(self, colors: Dict[str, str], directives: str) -> None:
        if any(token in directives for token in ("sachlich", "business", "clean")):
            colors["accent"] = "#228be6" if "accent" in colors else "#228be6"
        if any(token in directives for token in ("warm", "freundlich", "friendly")):
            colors.update({"accent": "#f59f00", "secondary": "#fff4e6"})

    def _apply_shape_rules(self, radius: Dict[str, str], directives: str) -> None:
        if any(token in directives for token in ("rounded", "soft", "pill")):
            radius.update({"sm": "0.5rem", "md": "1rem", "lg": "1.5rem", "pill": "999px"})
        if any(token in directives for token in ("square", "sharp", "minimal")):
            radius.update({"sm": "0.125rem", "md": "0.25rem", "lg": "0.375rem", "pill": "2rem"})

    def _apply_elevation_rules(self, elevation: Dict[str, str], directives: str) -> None:
        if any(token in directives for token in ("shadow", "elevated", "depth")):
            elevation.update(
                {
                    "flat": "0 4px 10px rgba(15, 23, 42, 0.12)",
                    "raised": "0 18px 40px rgba(15, 23, 42, 0.18)",
                    "overlay": "0 32px 70px rgba(15, 23, 42, 0.28)",
                }
            )
        if any(token in directives for token in ("flat", "minimal", "clean")):
            elevation.update(
                {
                    "flat": "0 1px 2px rgba(15, 23, 42, 0.06)",
                    "raised": "0 6px 12px rgba(15, 23, 42, 0.12)",
                    "overlay": "0 12px 24px rgba(15, 23, 42, 0.16)",
                }
            )

    def _build_slots(self, colors: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        nav_text = "#ffffff" if _is_dark(colors["primary"]) else colors.get("text", "#212529")
        footer_text = "#ffffff" if _is_dark(colors["primary"]) else colors.get("text", "#212529")
        hero_text = colors.get("text", "#212529")
        if _is_dark(colors.get("secondary", colors["surface"])):
            hero_text = "#ffffff"

        return {
            "nav": {
                "background": colors["primary"],
                "text": nav_text,
                "hover": colors.get("accent", nav_text),
            },
            "hero": {
                "background": colors.get("secondary", colors["surface"]),
                "text": hero_text,
                "accent": colors.get("accent", colors["primary"]),
            },
            "footer": {
                "background": colors["primary"],
                "text": footer_text,
                "muted": colors.get("muted", footer_text),
            },
        }


__all__ = ["ThemingAgent"]
