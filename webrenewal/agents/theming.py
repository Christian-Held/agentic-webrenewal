"""Implementation of the A12 Theming agent."""

from __future__ import annotations

from .base import Agent
from ..models import RenewalPlan, ThemeTokens


class ThemingAgent(Agent[RenewalPlan, ThemeTokens]):
    """Generate design tokens for the rebuilt site."""

    def __init__(self) -> None:
        super().__init__(name="A12.Theming")

    def run(self, plan: RenewalPlan) -> ThemeTokens:
        brand = {"primary": "#0b7285", "secondary": "#f8f9fa", "accent": "#ffd43b"}
        typography = {"font_family": "'Inter', sans-serif", "base_size": "16px", "scale": "1.25"}
        layout = {"framework": "bootstrap-5", "container_width": "960px", "border_radius": "0.5rem"}
        return ThemeTokens(brand=brand, typography=typography, layout=layout)


__all__ = ["ThemingAgent"]
