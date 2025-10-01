import json
import unittest


class _StubLLMClient:
    """Test double that mimics the ``complete_json`` contract."""

    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self._payloads = payloads
        self.calls: list[dict[str, object]] = []
        self._index = 0

    async def complete_json(  # pragma: no cover - behaviour exercised via agent
        self,
        messages,
        *,
        model,
        temperature=None,
    ):
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
            }
        )
        payload = self._payloads[self._index]
        self._index += 1
        return LLMResponse(text=json.dumps(payload), data=payload)


class _ErrorLLMClient:
    async def complete_json(self, *args, **kwargs):  # pragma: no cover - simple stub
        raise ValueError("boom")

from webrenewal.agents.rewrite import RewriteAgent
from webrenewal.llm import LLMResponse
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

        stub = _StubLLMClient(payloads)
        agent = RewriteAgent(llm_client=stub, model="test-model", max_parallel_requests=2)

        bundle = agent.run(("example.com", self.content, self.plan))

        self.assertFalse(bundle.fallback_used)
        self.assertEqual(len(bundle.blocks), len(self.sections))
        self.assertEqual(len(stub.calls), len(self.sections))
        first_messages = stub.calls[0]["messages"]
        self.assertTrue(any("example.com" in msg["content"] for msg in first_messages))

    def test_value_error_from_llm_triggers_fallback(self) -> None:
        agent = RewriteAgent(llm_client=_ErrorLLMClient())

        bundle = agent.run(("example.com", self.content, self.plan))

        self.assertTrue(bundle.fallback_used)
        self.assertEqual(len(bundle.blocks), len(self.sections))


if __name__ == "__main__":
    unittest.main()
