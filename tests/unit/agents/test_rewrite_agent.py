from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

import pytest

from webrenewal.agents.rewrite import RewriteAgent
from webrenewal.llm import LLMService, get_tracer
from webrenewal.llm.clients import LLMClient, ProviderResponse
from webrenewal.models import (
    ContentBundle,
    ContentExtract,
    ContentSection,
    RenewalAction,
    RenewalPlan,
)


class StubLLMProvider(LLMClient):
    """Return queued JSON payloads for rewrite tests."""

    def __init__(self, payloads: Sequence[Dict[str, Any]]) -> None:
        self._payloads = list(payloads)
        self.calls: List[Dict[str, Any]] = []

    async def _complete(
        self,
        messages: Sequence[Dict[str, Any]],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
        self.calls.append(
            {
                "messages": list(messages),
                "model": model,
                "temperature": temperature,
                "response_format": response_format,
            }
        )
        payload = self._payloads.pop(0)
        return ProviderResponse(text=json.dumps(payload))


@dataclass
class ErrorProvider(LLMClient):
    """Client raising an exception for every call."""

    exception: Exception

    async def _complete(
        self,
        messages: Sequence[Dict[str, Any]],
        *,
        model: str,
        temperature: float | None,
        response_format: str | None,
    ) -> ProviderResponse:
        raise self.exception


@pytest.fixture
def rewrite_agent_payloads() -> List[Dict[str, Any]]:
    return [
        {
            "meta_title": "Example Site",
            "meta_description": "Description",
            "blocks": [{"title": "Welcome", "body": "New welcome copy.", "type": "text"}],
        },
        {
            "meta_title": None,
            "meta_description": None,
            "blocks": [
                {
                    "title": "Services",
                    "body": "Updated services details.",
                    "type": "text",
                }
            ],
        },
    ]


@pytest.fixture
def legacy_content() -> ContentExtract:
    sections = [
        ContentSection(title="Welcome", text="Hello world", readability_score=65.2),
        ContentSection(title="Services", text="We offer things", readability_score=70.1),
    ]
    return ContentExtract(sections=sections, language="en")


@pytest.fixture
def renewal_plan() -> RenewalPlan:
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


def build_service(payloads: Sequence[Dict[str, Any]]) -> Tuple[LLMService, StubLLMProvider]:
    provider = StubLLMProvider(payloads)
    service = LLMService(provider="stub", client=provider, tracer=get_tracer())
    return service, provider


def test_rewrite_agent_fallback_without_client(
    legacy_content: ContentExtract, renewal_plan: RenewalPlan
) -> None:
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
    service, provider = build_service(rewrite_agent_payloads)
    agent = RewriteAgent(llm_client=service, model="test-model", max_parallel_requests=2)

    bundle = agent.run(("example.com", legacy_content, renewal_plan))

    assert bundle.fallback_used is False
    assert len(bundle.blocks) == len(legacy_content.sections)
    first_call = provider.calls[0]
    assert any("example.com" in message["content"] for message in first_call["messages"])


def test_rewrite_agent_handles_llm_failures(
    legacy_content: ContentExtract, renewal_plan: RenewalPlan
) -> None:
    service = LLMService(provider="stub", client=ErrorProvider(exception=ValueError("boom")), tracer=get_tracer())
    agent = RewriteAgent(llm_client=service)

    bundle = agent.run(("example.com", legacy_content, renewal_plan))

    assert bundle.fallback_used is True
    assert len(bundle.blocks) == len(legacy_content.sections)


def test_rewrite_agent_normalise_input_validates_tuple(
    legacy_content: ContentExtract, renewal_plan: RenewalPlan
) -> None:
    agent = RewriteAgent()

    with pytest.raises(ValueError):
        agent._normalise_input(("only-one",))  # type: ignore[arg-type]


def test_rewrite_agent_normalise_input_type_checks() -> None:
    agent = RewriteAgent()

    with pytest.raises(TypeError):
        agent._normalise_input(("domain", object(), object()))  # type: ignore[arg-type]
