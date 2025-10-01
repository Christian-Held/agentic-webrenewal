"""Tests for :class:`webrenewal.agents.navigation.NavigationAgent`."""

from __future__ import annotations

from webrenewal.agents.navigation import NavigationAgent
from webrenewal.models import CrawlResult, PageContent


def test_navigation_agent_extracts_nested_lists() -> None:
    """Given navigation lists When processed Then nested children are preserved."""

    html = """
    <html>
        <body>
            <nav>
                <ul>
                    <li><a href='/'>Home</a></li>
                    <li><a href='/services'>Services</a>
                        <ul>
                            <li><a href='/services/design'>Design</a></li>
                        </ul>
                    </li>
                </ul>
            </nav>
        </body>
    </html>
    """
    crawl = CrawlResult(pages=[PageContent(url="https://example.com", status_code=200, headers={}, html=html)])
    agent = NavigationAgent()

    nav = agent.run(crawl)

    services = next(item for item in nav.items if item.label == "Services")
    assert services.children[0].label == "Design"


def test_navigation_agent_fallbacks_when_missing_nav(empty_crawl_result) -> None:
    """Given no explicit nav When processed Then anchors are flattened into a fallback menu."""

    agent = NavigationAgent()
    nav = agent.run(empty_crawl_result)

    assert nav.items == []

