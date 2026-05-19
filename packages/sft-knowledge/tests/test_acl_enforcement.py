"""Tests for RagSearchTool + TraverseGraphTool + ACL enforcement (Plan 05-09 Task 2).

Covers:
    - KNW-06 SC#2 (operator cannot see restricted) — integration
    - D-66 args_schema frozen+forbid — unit
    - T-05-09-02 Cypher injection mitigation (source-scan) — unit
    - PATTERNS Shared Pattern 7 async-only — unit
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sft_knowledge.retrieval import RetrievalPipeline
from sft_knowledge.tools import (
    RagSearchInput,
    RagSearchTool,
    TraverseGraphInput,
    TraverseGraphTool,
)

# ===========================================================================
# Unit: input schema frozen+forbid (D-66)
# ===========================================================================


def test_rag_input_rejects_unknown_args() -> None:
    """RagSearchInput must reject extra fields (extra='forbid')."""
    with pytest.raises(ValidationError):
        RagSearchInput(
            query="x",
            user_roles=["operator"],
            unknown_param="leak",  # type: ignore[call-arg]
        )


def test_rag_input_is_frozen() -> None:
    """RagSearchInput instances must be immutable (frozen=True)."""
    inp = RagSearchInput(query="x", user_roles=["operator"])
    with pytest.raises(ValidationError):
        inp.query = "mutated"  # type: ignore[misc]


def test_rag_input_k_range_validated() -> None:
    """k must be in [1, 20]."""
    with pytest.raises(ValidationError):
        RagSearchInput(query="x", user_roles=["operator"], k=0)
    with pytest.raises(ValidationError):
        RagSearchInput(query="x", user_roles=["operator"], k=21)


def test_rag_tool_async_only() -> None:
    """RagSearchTool._run must raise NotImplementedError (PATTERNS Pattern 7)."""
    tool = RagSearchTool(pipeline=object())
    with pytest.raises(NotImplementedError, match="async-only"):
        tool._run()


def test_traverse_input_rejects_invalid_label() -> None:
    """TraverseGraphInput rejects seed_label outside whitelist."""
    with pytest.raises(ValidationError):
        TraverseGraphInput(
            seed_label="DROP TABLE",  # type: ignore[arg-type]
            seed_id="x",
            relation_path=["HAS_PART"],
        )


def test_traverse_input_rejects_invalid_relation() -> None:
    """TraverseGraphInput rejects relation outside whitelist."""
    with pytest.raises(ValidationError):
        TraverseGraphInput(
            seed_label="Machine",
            seed_id="x",
            relation_path=["DROP_TABLE"],  # type: ignore[list-item]
        )


def test_traverse_input_rejects_extra() -> None:
    """TraverseGraphInput rejects extra fields."""
    with pytest.raises(ValidationError):
        TraverseGraphInput(
            seed_label="Machine",
            seed_id="x",
            relation_path=["HAS_PART"],
            unknown=1,  # type: ignore[call-arg]
        )


def test_traverse_input_max_depth_range() -> None:
    """max_depth must be in [1, 5]."""
    with pytest.raises(ValidationError):
        TraverseGraphInput(
            seed_label="Machine",
            seed_id="x",
            relation_path=["HAS_PART"],
            max_depth=0,
        )
    with pytest.raises(ValidationError):
        TraverseGraphInput(
            seed_label="Machine",
            seed_id="x",
            relation_path=["HAS_PART"],
            max_depth=6,
        )


def test_traverse_tool_async_only() -> None:
    """TraverseGraphTool._run must raise NotImplementedError."""
    tool = TraverseGraphTool(driver=object())
    with pytest.raises(NotImplementedError, match="async-only"):
        tool._run()


# ===========================================================================
# Source-scan: T-05-09-02 Cypher injection mitigation
# ===========================================================================


def _graph_source() -> str:
    """Read the source of ``tools/graph.py`` as text."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "sft_knowledge"
        / "tools"
        / "graph.py"
    )
    return src_path.read_text(encoding="utf-8")


def test_traverse_tool_uses_param_for_seed_id() -> None:
    """seed_id MUST be passed as $param to Cypher, never f-string interpolated.

    Acceptance gate (Plan 05-09 Task 2): the literal ``$seed_id`` must appear
    in the cypher; and a f-string interpolation pattern ``f".*{seed_id}.*"``
    on the seed_id variable must NOT appear.
    """
    src = _graph_source()
    assert "$seed_id" in src, "Cypher must reference $seed_id as a parameter"
    # f"...{seed_id}..." would be the injection vulnerability.
    # Match a Python f-string fragment that interpolates the bare name `seed_id`
    # (the Cypher constant {{id: $seed_id}} uses doubled braces; this matches
    # only literal `{seed_id}` in an f-string slot, which is the unsafe form).
    pattern = re.compile(r"""f["'][^"']*\{seed_id\}""")
    matches = pattern.findall(src)
    assert matches == [], (
        f"seed_id must never be f-string interpolated; found: {matches!r}"
    )


def test_traverse_tool_passes_seed_id_kwarg() -> None:
    """The session.run call must pass seed_id as a kwarg (parametrized query)."""
    src = _graph_source()
    assert "seed_id=seed_id" in src, (
        "session.run must receive `seed_id=seed_id` as parametrized arg"
    )


# ===========================================================================
# Integration: KNW-06 SC#2 (ACL non-leak)
# ===========================================================================


async def _bootstrap_acl_collection(qdrant_client: Any) -> None:
    from qdrant_client.http.models import (
        Distance,
        SparseVectorParams,
        VectorParams,
    )

    try:
        await qdrant_client.delete_collection(collection_name="sop")
    except Exception:
        pass
    await qdrant_client.create_collection(
        collection_name="sop",
        vectors_config={
            "dense": VectorParams(size=1024, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(),
        },
    )


async def _index_acl_fixtures(qdrant_client: Any) -> None:
    """Index 3 SOPs with public / internal / restricted acl_level."""
    from qdrant_client.http.models import PointStruct

    dense = [1.0] + [0.0] * 1023
    points = [
        PointStruct(
            id="00000000-0000-0000-0000-000000000001",
            vector={"dense": dense},
            payload={
                "text": "Public SOP — calibrazione standard.",
                "source_uri": "file://sop/PUBLIC.md",
                "acl_level": "public",
                "lang": "it",
                "asset_family": "loom",
                "sop_id": "SOP-PUBLIC",
                "chunk_idx": 0,
                "version": "1.0",
            },
        ),
        PointStruct(
            id="00000000-0000-0000-0000-000000000002",
            vector={"dense": dense},
            payload={
                "text": "Internal SOP — procedura riservata team.",
                "source_uri": "file://sop/INTERNAL.md",
                "acl_level": "internal",
                "lang": "it",
                "asset_family": "loom",
                "sop_id": "SOP-INTERNAL",
                "chunk_idx": 0,
                "version": "1.0",
            },
        ),
        PointStruct(
            id="00000000-0000-0000-0000-000000000003",
            vector={"dense": dense},
            payload={
                "text": "Restricted SOP — confidential procedure.",
                "source_uri": "file://sop/RESTRICTED.md",
                "acl_level": "restricted",
                "lang": "it",
                "asset_family": "loom",
                "sop_id": "SOP-RESTRICTED",
                "chunk_idx": 0,
                "version": "1.0",
            },
        ),
    ]
    await qdrant_client.upsert(collection_name="sop", points=points)


# Reuse stubs from test_retrieval_pipeline (kept lightweight here).
class _StubEmbedder:
    def encode(
        self,
        texts: list[str],
        return_dense: bool = True,
        return_sparse: bool = True,
    ) -> Any:
        class _O:
            dense_vecs = [[1.0] + [0.0] * 1023 for _ in texts]
            sparse_weights = [{} for _ in texts]

        return _O()

    def to_qdrant_sparse(self, _l: dict[str, float]) -> Any:
        raise RuntimeError("stub: no sparse")


class _StubReranker:
    async def rerank(
        self, query: str, hits: list[Any]
    ) -> list[tuple[Any, float]]:
        return sorted(
            [(h, 1.0 / (1.0 + i)) for i, h in enumerate(hits)],
            key=lambda p: -p[1],
        )


@pytest.mark.integration
async def test_operator_cannot_see_restricted(qdrant_client: Any) -> None:
    """KNW-06 SC#2: operator role retrieves zero restricted chunks."""
    await _bootstrap_acl_collection(qdrant_client)
    await _index_acl_fixtures(qdrant_client)

    pipeline = RetrievalPipeline(
        qdrant_client=qdrant_client,
        embedder=_StubEmbedder(),
        reranker=_StubReranker(),
    )
    tool = RagSearchTool(pipeline=pipeline)
    citations = await tool.ainvoke(
        {"query": "test", "user_roles": ["operator"], "k": 10}
    )
    # Operator può vedere solo `public`.
    assert len(citations) >= 1
    for c in citations:
        assert "RESTRICTED" not in c.source_uri, (
            f"ACL leak: {c.source_uri} should be filtered for operator"
        )
        assert "INTERNAL" not in c.source_uri, (
            f"ACL leak: {c.source_uri} should be filtered for operator"
        )


@pytest.mark.integration
async def test_technician_can_see_internal(qdrant_client: Any) -> None:
    """Technician sees public + internal but NOT restricted."""
    await _bootstrap_acl_collection(qdrant_client)
    await _index_acl_fixtures(qdrant_client)

    pipeline = RetrievalPipeline(
        qdrant_client=qdrant_client,
        embedder=_StubEmbedder(),
        reranker=_StubReranker(),
    )
    citations = await pipeline.search(
        query="test", user_roles=["technician"], k=10
    )
    uris = {c.source_uri for c in citations}
    assert any("INTERNAL" in u for u in uris), (
        f"technician must see internal; got: {uris}"
    )
    assert not any("RESTRICTED" in u for u in uris), (
        f"technician must not see restricted; got: {uris}"
    )


@pytest.mark.integration
async def test_manager_can_see_restricted(qdrant_client: Any) -> None:
    """Manager sees all 3 ACL levels."""
    await _bootstrap_acl_collection(qdrant_client)
    await _index_acl_fixtures(qdrant_client)

    pipeline = RetrievalPipeline(
        qdrant_client=qdrant_client,
        embedder=_StubEmbedder(),
        reranker=_StubReranker(),
    )
    citations = await pipeline.search(
        query="test", user_roles=["manager"], k=10
    )
    uris = {c.source_uri for c in citations}
    assert any("RESTRICTED" in u for u in uris), (
        f"manager must see restricted; got: {uris}"
    )
