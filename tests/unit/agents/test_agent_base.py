"""Tests for :class:`webrenewal.agents.base.Agent`."""

from __future__ import annotations

from dataclasses import dataclass

from webrenewal.agents.base import Agent


@dataclass
class EchoAgent(Agent[int, int]):
    """Minimal agent used to validate the abstract interface."""

    def __init__(self) -> None:
        super().__init__(name="echo")

    def run(self, data: int) -> int:
        return data


def test_agent_base_exposes_name() -> None:
    """Given a custom agent When instantiated Then name and logger properties are accessible."""

    agent = EchoAgent()

    assert agent.name == "echo"
    assert agent.logger.name == "echo"
    assert agent.run(3) == 3

