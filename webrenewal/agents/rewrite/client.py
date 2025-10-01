"""OpenAI client lifecycle management for the rewrite agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from openai import AsyncOpenAI


@dataclass(frozen=True)
class ClientConfig:
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class OpenAIClientFactory:
    """Create AsyncOpenAI instances on demand."""

    def __init__(self, config: ClientConfig) -> None:
        self._config = config

    def get_client(self) -> Optional[AsyncOpenAI]:
        api_key = self._config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        kwargs: dict[str, Any] = {"api_key": api_key}
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url

        return AsyncOpenAI(**kwargs)


__all__ = ["ClientConfig", "OpenAIClientFactory"]
