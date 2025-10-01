"""Tests for :class:`webrenewal.agents.memory.MemoryAgent`."""

from __future__ import annotations

from webrenewal.agents.memory import MemoryAgent


def test_memory_agent_persists_records(sample_plan, sample_offer_doc) -> None:
    """Given plan and offer When memory agent runs Then record is stored and retrievable."""

    agent = MemoryAgent()
    record = agent.run(("https://example.com", sample_plan, sample_offer_doc))

    assert record.key == "example.com"
    assert agent.get("example.com") == record


def test_memory_agent_normalises_empty_domain(sample_plan, sample_offer_doc) -> None:
    """Given whitespace domain When stored Then key falls back to stripped input."""

    agent = MemoryAgent()
    record = agent.run(("   ", sample_plan, sample_offer_doc))

    assert record.key == ""

