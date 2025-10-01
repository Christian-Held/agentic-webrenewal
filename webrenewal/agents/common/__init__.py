"""Base classes shared by all agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Agent(ABC, Generic[InputT, OutputT]):
    """Abstract agent defining the contract for every pipeline step."""

    def __init__(self, name: str, logger: Optional[logging.Logger] = None) -> None:
        self._name = name
        self._logger = logger or logging.getLogger(name)

    @property
    def name(self) -> str:
        """Return the human readable name for the agent."""

        return self._name

    @property
    def logger(self) -> logging.Logger:
        """Return the logger associated with the agent."""

        return self._logger

    @abstractmethod
    def run(self, data: InputT) -> OutputT:
        """Execute the agent with ``data`` and return its output."""

        raise NotImplementedError


__all__ = ["Agent"]
