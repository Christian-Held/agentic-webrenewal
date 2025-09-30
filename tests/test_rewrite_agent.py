import sys
import unittest
from types import SimpleNamespace


class _DummyOpenAIError(Exception):
    """Lightweight stand-in for the OpenAI SDK error type."""


class _DummyOpenAI:
    def __init__(self, *args, **kwargs):  # pragma: no cover - simple stub
        pass


if "openai" not in sys.modules:
    sys.modules["openai"] = SimpleNamespace(OpenAI=_DummyOpenAI, OpenAIError=_DummyOpenAIError)

from webrenewal.agents.rewrite import RewriteAgent
from webrenewal.models import (
    ContentBundle,
    ContentExtract,
    ContentSection,
    RenewalAction,
    RenewalPlan,
)


class RewriteAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sections = [
            ContentSection(title="Welcome", text="Hello world", readability_score=65.2),
            ContentSection(title="Services", text="We offer things", readability_score=70.1),
        ]
        self.content = ContentExtract(sections=self.sections, language="en")
        self.plan = RenewalPlan(
            goals=["Improve clarity"],
            actions=[
                RenewalAction(
                    identifier="A1",
                    description="Revise hero copy",
                    impact="high",
                    effort_hours=3.0,
                )
            ],
            estimate_hours=12.0,
        )

    def test_run_with_legacy_tuple_uses_fallback(self) -> None:
        agent = RewriteAgent()
        agent._get_client = lambda: None  # type: ignore[assignment]

        bundle = agent.run((self.content, self.plan))

        self.assertTrue(bundle.fallback_used)
        self.assertEqual(len(bundle.blocks), len(self.sections))
        self.assertIn("Unknown Site", bundle.meta_title or "")

    def test_run_with_domain_tuple_threads_domain(self) -> None:
        agent = RewriteAgent()
        fake_client = object()
        agent._get_client = lambda: fake_client  # type: ignore[assignment]

        captured: dict[str, object] = {}

        def fake_llm(self, client, domain, content, plan):  # type: ignore[no-untyped-def]
            captured["client"] = client
            captured["domain"] = domain
            captured["content"] = content
            captured["plan"] = plan
            return ContentBundle(blocks=[], meta_title=None, meta_description="desc", fallback_used=False)

        agent._rewrite_with_llm = fake_llm.__get__(agent, RewriteAgent)

        bundle = agent.run(("example.com", self.content, self.plan))

        self.assertFalse(bundle.fallback_used)
        self.assertIs(captured.get("client"), fake_client)
        self.assertEqual(captured.get("domain"), "example.com")
        self.assertIs(captured.get("content"), self.content)
        self.assertIs(captured.get("plan"), self.plan)


if __name__ == "__main__":
    unittest.main()
