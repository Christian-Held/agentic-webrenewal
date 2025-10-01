"""Agent implementations for the Agentic WebRenewal pipeline.

Each agent now lives in its own subpackage to keep responsibilities and dependencies
encapsulated. The convenience exports below preserve the public API that the pipeline
and tests rely on while enabling per-agent extensions.
"""

from .accessibility import AccessibilityAgent
from .builder import BuilderAgent
from .common import Agent
from .comparator import ComparatorAgent
from .crawler import CrawlerAgent
from .media import MediaAgent
from .memory import MemoryAgent
from .navigation import NavigationAgent
from .offer import OfferAgent
from .plan import PlanProposalAgent
from .readability import ReadabilityAgent
from .rewrite import RewriteAgent
from .scope import ScopeAgent
from .security import SecurityAgent
from .seo import SEOAgent
from .tech_fingerprint import TechFingerprintAgent
from .theming import ThemingAgent
from .tool_discovery import ToolDiscoveryAgent

__all__ = [
    "AccessibilityAgent",
    "Agent",
    "BuilderAgent",
    "ComparatorAgent",
    "CrawlerAgent",
    "MediaAgent",
    "MemoryAgent",
    "NavigationAgent",
    "OfferAgent",
    "PlanProposalAgent",
    "ReadabilityAgent",
    "RewriteAgent",
    "ScopeAgent",
    "SecurityAgent",
    "SEOAgent",
    "TechFingerprintAgent",
    "ThemingAgent",
    "ToolDiscoveryAgent",
]
