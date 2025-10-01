"""Tests for :class:`webrenewal.agents.tool_discovery.ToolDiscoveryAgent`."""

from __future__ import annotations

from webrenewal.agents.tool_discovery import ToolDiscoveryAgent


def test_tool_discovery_returns_catalog(tool_catalog) -> None:
    """Given no input When ToolDiscoveryAgent runs Then a populated tool catalog is returned."""

    agent = ToolDiscoveryAgent()

    catalog = agent.run()

    assert len(catalog.tools) >= 1
    assert all(tool.name for tool in catalog.tools)

