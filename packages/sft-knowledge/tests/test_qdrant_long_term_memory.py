"""Tests for QdrantLongTermMemory + D-59 stub swap (Plan 05-09 Task 4).

Covers:
    - Memory ABC contract (query + store)
    - Default role fallback (operator = most restrictive)
    - store() raises NotImplementedError (T-05-09-03)
    - sft_agents.memory.LongTermMemory swap preserves alias name
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from sft_agents.models.memory_record import MemoryRecord
from sft_knowledge.memory import (
    QdrantLongTermMemory,
    QdrantLongTermMemoryConfig,
)
from sft_knowledge.models import RagCitation

UTC = timezone.utc


# ===========================================================================
# Stub pipeline + injection helper
# ===========================================================================


class _StubPipeline:
    """Deterministic stand-in che bypassa Qdrant/BGE-M3.

    Permette di esercitare ``QdrantLongTermMemory.query`` senza testcontainer.
    """

    def __init__(self, citations: list[RagCitation]) -> None:
        self._citations = citations
        self.last_call: dict[str, Any] | None = None

    async def search(
        self,
        query: str,
        user_roles: list[str],
        category: str = "sop",
        k: int = 5,
        lang: str | None = None,
        sop_ids: list[str] | None = None,
        asset_family: str | None = None,
        rerank: bool = True,
    ) -> list[RagCitation]:
        self.last_call = {
            "query": query,
            "user_roles": list(user_roles),
            "category": category,
            "k": k,
            "lang": lang,
            "sop_ids": sop_ids,
            "asset_family": asset_family,
        }
        return self._citations[:k]


def _inject_stub_pipeline(
    memory: QdrantLongTermMemory, pipeline: _StubPipeline
) -> None:
    """Bypass ``_get_pipeline`` by setting the private attribute."""
    memory._pipeline = pipeline  # noqa: SLF001 — test-only access


# ===========================================================================
# Unit tests
# ===========================================================================


def test_config_is_frozen_and_forbids_extra() -> None:
    """QdrantLongTermMemoryConfig is frozen + extra='forbid'."""
    cfg = QdrantLongTermMemoryConfig()
    with pytest.raises(Exception):
        cfg.qdrant_url = "mutated"  # type: ignore[misc]
    with pytest.raises(Exception):
        QdrantLongTermMemoryConfig(unknown="x")  # type: ignore[call-arg]


def test_config_defaults_match_d70_spec() -> None:
    """Default config values match D-70."""
    cfg = QdrantLongTermMemoryConfig()
    assert cfg.qdrant_url == "http://localhost:6333"
    assert cfg.collection_name == "sop"
    assert cfg.embedding_device == "cpu"


def test_memory_is_memory_abc_subclass() -> None:
    """QdrantLongTermMemory implements the Memory ABC."""
    from sft_agents.sdk.memory import Memory

    assert issubclass(QdrantLongTermMemory, Memory)


async def test_query_returns_memory_records_from_pipeline() -> None:
    """query() should call RetrievalPipeline.search and map to MemoryRecord."""
    citations = [
        RagCitation(
            source_uri="file://sop/test.md",
            snippet="public chunk",
            score=0.9,
            retrieved_at=datetime.now(UTC),
        ),
        RagCitation(
            source_uri="file://sop/test2.md",
            snippet="another chunk",
            score=0.7,
            retrieved_at=datetime.now(UTC),
        ),
    ]
    pipeline = _StubPipeline(citations)
    memory = QdrantLongTermMemory()
    _inject_stub_pipeline(memory, pipeline)

    records = await memory.query(
        "what about warp?", k=2, filters={"user_roles": ["technician"]}
    )
    assert len(records) == 2
    for r in records:
        assert isinstance(r, MemoryRecord)
        assert r.ts.tzinfo is not None
    # Score preserved.
    assert records[0].score == pytest.approx(0.9)
    assert records[1].score == pytest.approx(0.7)
    # Pipeline was called with the user_roles override.
    assert pipeline.last_call is not None
    assert pipeline.last_call["user_roles"] == ["technician"]


async def test_default_role_is_operator() -> None:
    """When filters lacks user_roles, default to ['operator'] (fail-safe)."""
    pipeline = _StubPipeline([])
    memory = QdrantLongTermMemory()
    _inject_stub_pipeline(memory, pipeline)

    await memory.query("x")  # no filters
    assert pipeline.last_call is not None
    assert pipeline.last_call["user_roles"] == ["operator"]


async def test_store_raises_not_implemented() -> None:
    """store() must raise NotImplementedError (T-05-09-03 mitigation)."""
    memory = QdrantLongTermMemory()
    record = MemoryRecord(
        source_uri="file://x.md",
        content="content",
        score=0.5,
        ts=datetime.now(UTC),
    )
    with pytest.raises(NotImplementedError, match="ARCHITECTURE.md"):
        await memory.store(record)


def test_sft_agents_memory_swap_preserves_alias() -> None:
    """sft_agents.memory.LongTermMemory is now QdrantLongTermMemory.

    The swap is graceful: if sft-knowledge is unavailable, the alias falls back
    to StubLongTermMemory. In this test env sft-knowledge IS installed so the
    alias must resolve to QdrantLongTermMemory.
    """
    from sft_agents.memory import LongTermMemory

    assert LongTermMemory.__name__ in {
        "QdrantLongTermMemory",
        "StubLongTermMemory",
    }
    # In this CI we expect the real swap to happen.
    assert LongTermMemory.__name__ == "QdrantLongTermMemory", (
        "Expected QdrantLongTermMemory; got "
        f"{LongTermMemory.__name__}. sft-knowledge import failed?"
    )
