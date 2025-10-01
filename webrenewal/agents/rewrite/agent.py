"""Public RewriteAgent implementation with supporting helpers."""

from __future__ import annotations

import json
import logging
from typing import Optional

from openai import AsyncOpenAI, OpenAIError

from ..common import Agent
from ...tracing import log_event
from ...models import ContentBundle, ContentExtract, RenewalPlan
from .async_utils import run_async
from .client import ClientConfig, OpenAIClientFactory
from .fallback import FallbackBuilder
from .input_normaliser import InputNormaliser
from .runner import SectionRewriteCoordinator
from .types import RewriteInput


class RewriteAgent(Agent[RewriteInput, ContentBundle]):
    """Produce refreshed copy for the website."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.4,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        max_parallel_requests: int = 4,
    ) -> None:
        super().__init__(name="A11.Rewrite")
        self._model = model
        self._temperature = temperature
        self._client_factory = OpenAIClientFactory(
            ClientConfig(api_key=api_key, base_url=base_url)
        )
        self._max_parallel = max(1, max_parallel_requests)
        self._normaliser = InputNormaliser()
        self._fallback = FallbackBuilder()
        self._coordinator = SectionRewriteCoordinator(
            model=model,
            temperature=temperature,
            max_parallel_requests=self._max_parallel,
            logger=self.logger,
            agent_name=self.name,
        )

    def run(self, data: RewriteInput) -> ContentBundle:  # type: ignore[override]
        domain, content, plan = self._normaliser.normalise(data)
        client = self._get_client()

        log_event(
            self.logger,
            logging.DEBUG,
            "rewrite.run",
            agent=self.name,
            domain=domain,
            sections=len(content.sections),
            goals=len(plan.goals),
        )

        if client is None:
            log_event(
                self.logger,
                logging.WARNING,
                "rewrite.openai.missing_key",
                agent=self.name,
                domain=domain,
            )
            return self._fallback_bundle(domain, content)

        try:
            bundle = self._rewrite_with_llm(client, domain, content, plan)
        except (OpenAIError, ValueError, json.JSONDecodeError) as exc:
            log_event(
                self.logger,
                logging.WARNING,
                "rewrite.llm.failure",
                agent=self.name,
                domain=domain,
                error=repr(exc),
                exc_info=True,
            )
            return self._fallback_bundle(domain, content, error=repr(exc))

        log_event(
            self.logger,
            logging.INFO,
            "rewrite.success",
            agent=self.name,
            domain=domain,
            blocks=len(bundle.blocks),
            fallback=bundle.fallback_used,
        )
        return bundle

    def _get_client(self) -> Optional[AsyncOpenAI]:
        return self._client_factory.get_client()

    def _rewrite_with_llm(
        self, client: AsyncOpenAI, domain: str, content: ContentExtract, plan: RenewalPlan
    ) -> ContentBundle:
        return run_async(
            self._coordinator.rewrite(client, domain, content, plan)
        )

    def _fallback_bundle(
        self, domain: str, content: ContentExtract, error: Optional[str] = None
    ) -> ContentBundle:
        bundle = self._fallback.build(domain, content)
        log_event(
            self.logger,
            logging.INFO,
            "rewrite.fallback",
            agent=self.name,
            domain=domain,
            reason="missing_openai_key" if error is None else "llm_failure",
            error=error,
            blocks=len(bundle.blocks),
        )
        return bundle


__all__ = ["RewriteAgent"]
