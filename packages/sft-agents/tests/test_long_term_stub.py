"""StubLongTermMemory contract tests (D-59 long-term stub, Plan 04-06 Task 02).

Phase 4 ships ``StubLongTermMemory`` as a no-Qdrant placeholder so downstream
callers can import the Phase 5 path today. The contract is:

    1. instantiable without args
    2. query(...) returns [] for ANY input
    3. store(...) raises NotImplementedError with a Phase-5 marker
    4. isinstance(StubLongTermMemory(), Memory) is True
    5. LongTermMemory is StubLongTermMemory (alias)
    6. config dataclass is frozen + extra=forbid

These tests do NOT need docker/testcontainers — pure stdlib.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

# Skip if Phase 4 contract not yet shipped.
pytest.importorskip(
    "sft_agents.memory.long_term_stub",
    reason="Plan 04-06 Task 02 implements StubLongTermMemory",
)

from sft_agents.memory import LongTermMemory  # noqa: E402
from sft_agents.memory.long_term_stub import (  # noqa: E402
    StubLongTermMemory,
    StubLongTermMemoryConfig,
)
from sft_agents.models.memory_record import MemoryRecord  # noqa: E402
from sft_agents.sdk.memory import Memory  # noqa: E402


async def test_stub_instantiable_without_args() -> None:
    stub = StubLongTermMemory()
    assert isinstance(stub, StubLongTermMemory)


async def test_stub_query_returns_empty_list() -> None:
    stub = StubLongTermMemory()
    result = await stub.query("anything", k=5)
    assert result == []
    assert isinstance(result, list)


async def test_stub_query_ignores_filters_and_k() -> None:
    stub = StubLongTermMemory()
    result = await stub.query("foo", k=100, filters={"agent_id": "x"})
    assert result == []


async def test_stub_store_raises_phase5_marker() -> None:
    stub = StubLongTermMemory()
    record = MemoryRecord(
        source_uri="mem://x",
        content="hello",
        score=0.5,
        ts=datetime(2026, 5, 18, tzinfo=UTC),
    )
    with pytest.raises(NotImplementedError) as exc_info:
        await stub.store(record)
    msg = str(exc_info.value)
    assert "Phase 5" in msg
    assert "QdrantLongTermMemory" in msg


def test_stub_subclasses_memory_abc() -> None:
    assert issubclass(StubLongTermMemory, Memory)
    assert isinstance(StubLongTermMemory(), Memory)


def test_long_term_memory_alias_points_to_stub() -> None:
    assert LongTermMemory is StubLongTermMemory


def test_stub_config_frozen_extra_forbid() -> None:
    cfg = StubLongTermMemoryConfig()
    # frozen: cannot mutate
    with pytest.raises(ValidationError):
        cfg.foo = "x"  # type: ignore[attr-defined]
    # extra=forbid: cannot construct with extra fields
    with pytest.raises(ValidationError):
        StubLongTermMemoryConfig(unknown_field=1)  # type: ignore[call-arg]
