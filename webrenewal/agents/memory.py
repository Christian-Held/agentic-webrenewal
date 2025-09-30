"""Implementation of the A16 Memory agent."""

from __future__ import annotations

from typing import Dict

from .base import Agent
from ..models import MemoryRecord, OfferDoc, PreviewIndex, RenewalPlan


class MemoryAgent(Agent[tuple[RenewalPlan, OfferDoc], MemoryRecord]):
    """Persist a summary payload in memory storage."""

    def __init__(self) -> None:
        super().__init__(name="A16.Memory")
        self._memory: Dict[str, MemoryRecord] = {}

    def run(self, data: tuple[RenewalPlan, OfferDoc]) -> MemoryRecord:
        plan, offer = data
        payload = {
            "goals": ", ".join(plan.goals),
            "hours": str(plan.estimate_hours),
            "offer_price": f"{offer.pricing_eur:.2f}",
        }
        record = MemoryRecord(key="physioheld", payload=payload)
        self._memory[record.key] = record
        return record

    def get(self, key: str) -> MemoryRecord | None:
        return self._memory.get(key)


__all__ = ["MemoryAgent"]
