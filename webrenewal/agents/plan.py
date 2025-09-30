"""Implementation of the A10 Plan/Proposal agent."""

from __future__ import annotations

from typing import List

from .base import Agent
from ..models import (
    A11yReport,
    MediaReport,
    NavModel,
    RenewalAction,
    RenewalPlan,
    SEOReport,
    SecurityReport,
    TechFingerprint,
)


class PlanProposalAgent(
    Agent[tuple[A11yReport, SEOReport, SecurityReport, TechFingerprint, MediaReport, NavModel], RenewalPlan]
):
    """Aggregate findings into a renewal plan."""

    def __init__(self) -> None:
        super().__init__(name="A10.Plan")

    def run(
        self,
        data: tuple[A11yReport, SEOReport, SecurityReport, TechFingerprint, MediaReport, NavModel],
    ) -> RenewalPlan:
        a11y, seo, security, tech, media, nav = data
        actions: List[RenewalAction] = []

        if a11y.score < 95:
            actions.append(
                RenewalAction(
                    identifier="improve_alt_text",
                    description="Add descriptive alternative text to all meaningful images.",
                    impact="high",
                    effort_hours=2.0,
                )
            )
        if seo.score < 90:
            actions.append(
                RenewalAction(
                    identifier="optimize_meta",
                    description="Create unique titles and meta descriptions for core pages.",
                    impact="high",
                    effort_hours=3.0,
                )
            )
        if security.score < 90:
            actions.append(
                RenewalAction(
                    identifier="add_security_headers",
                    description="Harden HTTP responses with standard security headers.",
                    impact="medium",
                    effort_hours=1.5,
                )
            )
        if tech.frameworks:
            actions.append(
                RenewalAction(
                    identifier="modernize_stack",
                    description="Review and update legacy front-end dependencies.",
                    impact="medium",
                    effort_hours=4.0,
                )
            )
        if not actions:
            actions.append(
                RenewalAction(
                    identifier="content_refresh",
                    description="Refresh on-page copy to highlight differentiators and services.",
                    impact="medium",
                    effort_hours=3.0,
                )
            )

        goals = ["Accessibility >= 95", "SEO >= 90", "Security >= 90"]
        estimate = sum(action.effort_hours for action in actions)
        return RenewalPlan(goals=goals, actions=actions, estimate_hours=estimate)


__all__ = ["PlanProposalAgent"]
