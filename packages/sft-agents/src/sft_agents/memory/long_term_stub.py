"""StubLongTermMemory — D-59 long-term memory contract anchor (Plan 04-06 Task 02).

This module is the **import path** that Phase 5 will replace with the real
``QdrantLongTermMemory`` (BGE-M3 embeddings + Qdrant collection search). Shipping
the stub in Phase 4 freezes the import path so downstream consumers (Plan 04-07
api-gateway, Phase 6-9 cluster agents) can depend on the symbol today without
breaking when Phase 5 swaps the implementation.

D-59 stub contract (CONTEXT.md lines 285-298):
    - ``query(...)`` returns ``[]`` for ANY input (no Qdrant client, no I/O).
    - ``store(...)`` raises ``NotImplementedError`` with a Phase-5 marker message.

Defense-in-depth:
    No Qdrant / BGE-M3 / sentence-transformers imports — stdlib + Pydantic + structlog
    ONLY. Phase 5 adds the qdrant-client dependency at the same time it replaces
    this module body.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict

from sft_agents.models.memory_record import MemoryRecord
from sft_agents.sdk.memory import Memory

logger = structlog.get_logger(__name__)


class StubLongTermMemoryConfig(BaseModel):
    """Frozen empty config for the Phase 4 stub.

    Phase 5 will extend this with ``collection_name``, ``qdrant_url``, and
    ``embedding_model`` fields. The empty body ships now so downstream callers
    can do ``StubLongTermMemoryConfig()`` without imports breaking when the
    real implementation lands.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class StubLongTermMemory(Memory):
    """Phase 4 placeholder satisfying the :class:`Memory` ABC (D-59).

    ``query()`` returns ``[]`` unconditionally; ``store()`` raises with a
    descriptive Phase-5 message so callers who accidentally try to persist
    fail fast.
    """

    def __init__(self, config: StubLongTermMemoryConfig | None = None) -> None:
        """Bind optional config; default to empty ``StubLongTermMemoryConfig()``."""
        self._config = config or StubLongTermMemoryConfig()
        logger.info(
            "stub_long_term_memory_instantiated",
            note="D-59 placeholder; Phase 5 supplies QdrantLongTermMemory",
        )

    async def query(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        """Return an empty list — no Qdrant available in Phase 4."""
        return []

    async def store(self, record: MemoryRecord) -> str:
        """Raise — long-term storage is a Phase 5 capability."""
        raise NotImplementedError(
            "Phase 5 supplies QdrantLongTermMemory (D-59); long-term storage "
            "is not available in Phase 4"
        )
