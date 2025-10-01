"""Implementation of the A0 Tool Discovery agent."""

from __future__ import annotations

from typing import Iterable

from ..common import Agent
from ..models import ToolCatalog, ToolInfo


class ToolDiscoveryAgent(Agent[None, ToolCatalog]):
    """Return a curated set of MCP tools used across the pipeline."""

    def __init__(self) -> None:
        super().__init__(name="A0.ToolDiscovery")

    def run(self, data: None = None) -> ToolCatalog:  # type: ignore[override]
        self.logger.info("Compiling tool catalog")
        tools: Iterable[ToolInfo] = [
            ToolInfo(
                name="@playwright/mcp",
                category="browsing",
                description="Browser automation with Playwright for rendering and accessibility audits.",
                usage_snippet="await browser.goto(url); await inject_axe();",
            ),
            ToolInfo(
                name="mcp-server-fetch",
                category="http",
                description="Generic HTTP client for crawling and header analysis.",
                usage_snippet="fetch('https://example.com', { method: 'GET' })",
            ),
            ToolInfo(
                name="@modelcontextprotocol/server-filesystem",
                category="filesystem",
                description="Sandboxed file persistence used to store crawl and build artifacts.",
                usage_snippet="write_file('sandbox/plan.json', JSON.stringify(plan))",
            ),
            ToolInfo(
                name="mcp-memory-libsql",
                category="memory",
                description="Structured and vector memory persistence via LibSQL backend.",
                usage_snippet="memory.put('renewal', payload)",
            ),
        ]
        catalog = ToolCatalog(tools=list(tools))
        self.logger.debug("Generated tool catalog with %d entries", len(catalog.tools))
        return catalog


__all__ = ["ToolDiscoveryAgent"]
