"""Tests for :class:`webrenewal.agents.rewrite.RewriteAgent`."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

import pytest

from webrenewal.agents.rewrite import RewriteAgent
from webrenewal.llm import LLMResponse
from webrenewal.models import ContentBundle, ContentExtract, ContentSection, RenewalAction, RenewalPlan


class StubLLMClient:
    """Deterministic LLM client returning queued payloads."""

    def __init__(self, payloads: List[Dict[str, Any]]) -> None:
        self._payloads = payloads
        self.calls: List[Dict[str, Any]] = []
        self._index = 0

    async def complete_json(self, messages: Iterable[Dict[str, Any]], *, model: str, temperature: float | None = None) -> LLMResponse:  # noqa: D401 - async stub
        self.calls.append({"messages": list(messages), "model": model, "temperature": temperature})
        payload = self._payloads[self._index]
        self._index += 1
        return LLMResponse(text=json.dumps(payload), data=payload)


class ErrorLLMClient:
    async def complete_json(self, *args, **kwargs) -> LLMResponse:  # noqa: D401 - async stub
        raise ValueError("boom")


@pytest.fixture
def rewrite_agent_payloads() -> List[Dict[str, Any]]:
    """Return payloads for the stub LLM client representing block rewrites."""

    return [
        {
            "meta_title": "Example Site",
            "meta_description": "Description",
            "blocks": [{"title": "Welcome", "body": "New welcome copy."}],
        },
        {
            "meta_title": None,
            "meta_description": None,
            "blocks": [{"title": "Services", "body": "Updated services details."}],
        },
    ]


@pytest.fixture
def legacy_content() -> ContentExtract:
    """Return sample content sections used by the rewrite agent tests."""

    sections = [
        ContentSection(title="Welcome", text="Hello world", readability_score=65.2),
        ContentSection(title="Services", text="We offer things", readability_score=70.1),
    ]
    return ContentExtract(sections=sections, language="en")


@pytest.fixture
def renewal_plan() -> RenewalPlan:
    """Return a plan with a single action for rewrite prompts."""

    return RenewalPlan(
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


def test_rewrite_agent_fallback_without_client(legacy_content: ContentExtract, renewal_plan: RenewalPlan) -> None:
    """Given legacy input tuple When no LLM client is configured Then fallback bundle is produced."""

    agent = RewriteAgent()
    agent._get_client = lambda: None  # type: ignore[assignment]

    bundle = agent.run((legacy_content, renewal_plan))

    assert isinstance(bundle, ContentBundle)
    assert bundle.fallback_used is True
    assert len(bundle.blocks) == len(legacy_content.sections)


def test_rewrite_agent_threads_domain_into_prompts(
    rewrite_agent_payloads: List[Dict[str, Any]],
    legacy_content: ContentExtract,
    renewal_plan: RenewalPlan,
) -> None:
    """Given domain-aware tuples When rewriting Then prompts mention the requested domain."""

    stub = StubLLMClient(rewrite_agent_payloads)
    agent = RewriteAgent(llm_client=stub, model="test-model", max_parallel_requests=2)

    bundle = agent.run(("example.com", legacy_content, renewal_plan))

    assert bundle.fallback_used is False
    assert len(bundle.blocks) == len(legacy_content.sections)
    first_messages = stub.calls[0]["messages"]
    assert any("example.com" in message["content"] for message in first_messages)


def test_rewrite_agent_handles_llm_failures(legacy_content: ContentExtract, renewal_plan: RenewalPlan) -> None:
    """Given LLM exceptions When rewriting Then fallback bundle is returned with safe defaults."""

    agent = RewriteAgent(llm_client=ErrorLLMClient())

    bundle = agent.run(("example.com", legacy_content, renewal_plan))

    assert bundle.fallback_used is True
    assert len(bundle.blocks) == len(legacy_content.sections)


def test_rewrite_agent_normalise_input_validates_tuple(legacy_content: ContentExtract, renewal_plan: RenewalPlan) -> None:
    """Given unexpected tuple sizes When normalising Then ValueError is raised."""

    agent = RewriteAgent()

    with pytest.raises(ValueError):
        agent._normalise_input(("only-one",))  # type: ignore[arg-type]


def test_rewrite_agent_normalise_input_type_checks() -> None:
    """Given incorrect types When normalising Then TypeError is raised."""

    agent = RewriteAgent()

    with pytest.raises(TypeError):
        agent._normalise_input(("domain", object(), object()))  # type: ignore[arg-type]

