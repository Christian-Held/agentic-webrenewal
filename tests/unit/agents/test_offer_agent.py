"""Tests for :class:`webrenewal.agents.offer.OfferAgent`."""

from __future__ import annotations

from webrenewal.agents.offer import OfferAgent
from webrenewal.models import DiffResult, PreviewIndex, RenewalPlan


def test_offer_agent_generates_summary(sample_plan, sample_preview_index) -> None:
    """Given a plan and preview When offer agent runs Then summary includes action descriptions."""

    agent = OfferAgent()
    offer = agent.run(("https://example.com", sample_plan, sample_preview_index))

    assert "Example" in offer.title
    assert "Proposed improvements" in offer.summary
    assert offer.pricing_eur >= 600


def test_offer_agent_enforces_minimum_price(sample_plan) -> None:
    """Given a low estimate When offer agent runs Then minimum price floor is respected."""

    low_plan = RenewalPlan(goals=[], actions=[], estimate_hours=2)
    agent = OfferAgent()
    preview = PreviewIndex(diffs=[DiffResult(page="/", diff="")])
    offer = agent.run(("example.com", low_plan, preview))

    assert offer.pricing_eur == 600.0

