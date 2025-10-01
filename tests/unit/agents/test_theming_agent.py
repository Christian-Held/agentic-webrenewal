"""Tests for :class:`webrenewal.agents.theming.ThemingAgent`."""

from __future__ import annotations

from webrenewal.agents.theming import ThemingAgent
from webrenewal.models import RenewalPlan


def test_theming_agent_applies_directives(sample_plan: RenewalPlan) -> None:
    """Given design directives When theming runs Then palettes are adjusted accordingly."""

    agent = ThemingAgent(design_directives="Blau tech warm")
    tokens = agent.run(sample_plan)

    assert tokens.colors["primary"] == "#1d4ed8"
    assert tokens.typography["body_family"].startswith("'IBM")
    assert tokens.slots["nav"]["background"] == tokens.colors["primary"]


def test_theming_agent_handles_dark_mode(sample_plan: RenewalPlan) -> None:
    """Given dark directives When theming runs Then slots compute contrasting text."""

    agent = ThemingAgent(design_directives="dark")
    tokens = agent.run(sample_plan)

    assert tokens.colors["surface"] == "#0f172a"
    assert tokens.slots["nav"]["text"] == "#ffffff"

