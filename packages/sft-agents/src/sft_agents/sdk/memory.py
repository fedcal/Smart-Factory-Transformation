"""Memory ABC interface (CORE-01, D-59).

Phase 4 ships:
    - ShortTermMemory  — LangGraph checkpointer wrapper (Plan 04-05)
    - EpisodicReplay   — NATS audit log replay (Plan 04-06)
    - StubLongTermMemory — returns [] for any query (Plan 04-06; Phase 5 replaces with Qdrant)

All three implement this ABC so agents code against a single interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sft_agents.models.memory_record import MemoryRecord


class Memory(ABC):
    """Abstract memory store — query for past records + persist new ones.

    Phase 4 implementations (short-term + episodic + stub long-term) all satisfy this
    contract. Phase 5 swaps `StubLongTermMemory` for `QdrantLongTermMemory` without
    touching agents.
    """

    @abstractmethod
    async def query(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        """Retrieve up to `k` records relevant to `query`, optionally filtered."""

    @abstractmethod
    async def store(self, record: MemoryRecord) -> str:
        """Persist a record and return its identifier (URI or row id)."""
