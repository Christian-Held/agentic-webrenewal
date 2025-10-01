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

    def __init__(
        self,
        *,
        accessibility_target: float = 95.0,
        seo_target: float = 90.0,
        security_target: float = 90.0,
    ) -> None:
        super().__init__(name="A10.Plan")
        self._accessibility_target = accessibility_target
        self._seo_target = seo_target
        self._security_target = security_target

    def run(
        self,
        data: tuple[A11yReport, SEOReport, SecurityReport, TechFingerprint, MediaReport, NavModel],
    ) -> RenewalPlan:
        a11y, seo, security, tech, media, nav = data
        actions: List[RenewalAction] = []

        if a11y.score < self._accessibility_target:
            actions.append(
                RenewalAction(
                    identifier="improve_alt_text",
                    description="Add descriptive alternative text to all meaningful images.",
                    impact="high",
                    effort_hours=2.0,
                )
            )
        if seo.score < self._seo_target:
            actions.append(
                RenewalAction(
                    identifier="optimize_meta",
                    description="Create unique titles and meta descriptions for core pages.",
                    impact="high",
                    effort_hours=3.0,
                )
            )
        if security.score < self._security_target:
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

        goals = [
            f"Accessibility >= {self._format_goal(self._accessibility_target)}",
            f"SEO >= {self._format_goal(self._seo_target)}",
            f"Security >= {self._format_goal(self._security_target)}",
        ]
        estimate = sum(action.effort_hours for action in actions)
        return RenewalPlan(goals=goals, actions=actions, estimate_hours=estimate)

    @staticmethod
    def _format_goal(value: float) -> str:
        if float(value).is_integer():
            return str(int(value))
        return (f"{value:.2f}").rstrip("0").rstrip(".")


__all__ = ["PlanProposalAgent"]
