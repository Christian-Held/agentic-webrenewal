"""Implementation of the A15 Offer agent."""

from __future__ import annotations

from .base import Agent
from ..models import OfferDoc, PreviewIndex, RenewalPlan


class OfferAgent(Agent[tuple[RenewalPlan, PreviewIndex], OfferDoc]):
    """Create a commercial offer summarising the proposal."""

    def __init__(self) -> None:
        super().__init__(name="A15.Offer")

    def run(self, data: tuple[RenewalPlan, PreviewIndex]) -> OfferDoc:
        plan, preview = data
        summary_lines = ["Proposed improvements:"]
        for action in plan.actions:
            summary_lines.append(f"- {action.description} ({action.impact} impact, {action.effort_hours}h)")
        summary_lines.append("")
        summary_lines.append("Diff preview generated for core landing page.")
        summary = "\n".join(summary_lines)
        pricing = max(plan.estimate_hours * 120.0, 600.0)
        return OfferDoc(
            title="PhysioHeld Renewal Offer",
            summary=summary,
            pricing_eur=pricing,
        )


__all__ = ["OfferAgent"]
