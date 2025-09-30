"""Implementation of the A15 Offer agent."""

from __future__ import annotations

from .base import Agent
from ..models import OfferDoc, PreviewIndex, RenewalPlan
from ..utils import domain_to_display_name


class OfferAgent(Agent[tuple[str, RenewalPlan, PreviewIndex], OfferDoc]):
    """Create a commercial offer summarising the proposal."""

    def __init__(self) -> None:
        super().__init__(name="A15.Offer")

    def run(self, data: tuple[str, RenewalPlan, PreviewIndex]) -> OfferDoc:
        domain, plan, preview = data
        site_label = domain_to_display_name(domain)

        summary_lines = [f"Proposed improvements for {site_label}:"]
        for action in plan.actions:
            summary_lines.append(f"- {action.description} ({action.impact} impact, {action.effort_hours}h)")
        summary_lines.append("")
        summary_lines.append(
            f"Diff preview generated for {len(preview.diffs)} page(s); review under sandbox/newsite/."
        )
        summary = "\n".join(summary_lines)
        pricing = max(plan.estimate_hours * 120.0, 600.0)
        return OfferDoc(
            title=f"{site_label} Renewal Offer",
            summary=summary,
            pricing_eur=pricing,
        )


__all__ = ["OfferAgent"]
