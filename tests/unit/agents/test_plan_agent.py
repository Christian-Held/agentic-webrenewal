"""Tests for :class:`webrenewal.agents.plan.PlanProposalAgent`."""

from __future__ import annotations

from webrenewal.agents.plan import PlanProposalAgent
from webrenewal.models import (
    A11yReport,
    MediaReport,
    NavModel,
    SEOReport,
    SecurityReport,
    TechFingerprint,
)


def test_plan_agent_creates_actions(sample_crawl_result) -> None:
    """Given failing scores When aggregated Then actions include improvements."""

    agent = PlanProposalAgent()
    plan = agent.run(
        (
            A11yReport(score=80, issues=[]),
            SEOReport(score=70, issues=[]),
            SecurityReport(score=60, issues=[]),
            TechFingerprint(frameworks=["Bootstrap"], evidence={"Bootstrap": ["https://example.com"]}),
            MediaReport(images=[]),
            NavModel(items=[]),
        )
    )

    identifiers = {action.identifier for action in plan.actions}
    assert {"improve_alt_text", "optimize_meta", "add_security_headers", "modernize_stack"}.issubset(identifiers)
    assert plan.estimate_hours == sum(action.effort_hours for action in plan.actions)


def test_plan_agent_falls_back_to_content_refresh() -> None:
    """Given perfect scores When aggregated Then a content refresh action is suggested."""

    agent = PlanProposalAgent()
    plan = agent.run(
        (
            A11yReport(score=100, issues=[]),
            SEOReport(score=100, issues=[]),
            SecurityReport(score=100, issues=[]),
            TechFingerprint(frameworks=[], evidence={}),
            MediaReport(images=[]),
            NavModel(items=[]),
        )
    )

    assert plan.actions[0].identifier == "content_refresh"

