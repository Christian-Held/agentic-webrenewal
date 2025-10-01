import json
import sys
import unittest
from types import SimpleNamespace


class _DummyOpenAIError(Exception):
    """Lightweight stand-in for the OpenAI SDK error type."""


class _DummyOpenAI:
    def __init__(self, *args, **kwargs):  # pragma: no cover - simple stub
        pass


class _LegacyResponses:
    def __init__(self, payloads):
        self._payloads = payloads
        self.calls: list[dict[str, object]] = []
        self._successes = 0

    async def create(self, **kwargs):  # pragma: no cover - behaviour tested indirectly
        self.calls.append(kwargs)
        if len(self.calls) == 1 and "response_format" in kwargs:
            raise TypeError("create() got an unexpected keyword argument 'response_format'")

        payload = self._payloads[self._successes]
        self._successes += 1
        return SimpleNamespace(output_text=json.dumps(payload))


class _LegacyClient:
    def __init__(self, payloads):
        self.responses = _LegacyResponses(payloads)


if "openai" not in sys.modules:
    sys.modules["openai"] = SimpleNamespace(
        OpenAI=_DummyOpenAI,
        AsyncOpenAI=_DummyOpenAI,
        OpenAIError=_DummyOpenAIError,
    )

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

    def test_retry_without_response_format_when_unsupported(self) -> None:
        payloads = [
            {
                "meta_title": "Example Site",
                "meta_description": "Description",
                "blocks": [
                    {"title": "Welcome", "body": "New welcome copy."},
                ],
            },
            {
                "meta_title": None,
                "meta_description": None,
                "blocks": [
                    {"title": "Services", "body": "Updated services details."},
                ],
            },
        ]

        agent = RewriteAgent(max_parallel_requests=2)
        legacy_client = _LegacyClient(payloads)
        agent._get_client = lambda: legacy_client  # type: ignore[assignment]

        bundle = agent.run(("example.com", self.content, self.plan))

        self.assertFalse(bundle.fallback_used)
        self.assertEqual(len(legacy_client.responses.calls), 3)
        self.assertIn("response_format", legacy_client.responses.calls[0])
        self.assertNotIn("response_format", legacy_client.responses.calls[1])
        self.assertIn("response_format", legacy_client.responses.calls[2])
        self.assertEqual(bundle.blocks[0].body, "New welcome copy.")


if __name__ == "__main__":
    unittest.main()
