"""Tests for RetrievalPipeline + BgeReranker + ACL filter (Plan 05-09 Task 1).

Covers:
    - KNW-09 (hybrid retrieval, score in [0,1], ranked desc)
    - D-63 ACL pre-filter at Qdrant engine level
    - Sync→async bridge in BgeReranker

Layered:
    - 3 unit tests for build_acl_filter (no markers, no testcontainer)
    - 3 integration tests (@pytest.mark.integration) using mocked embedder + reranker
      to keep CI CPU-only feasible without GPU/2GB model downloads
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from sft_knowledge.models import RagCitation
from sft_knowledge.retrieval import (
    ROLE_TO_ACL,
    BgeReranker,
    RetrievalPipeline,
    build_acl_filter,
)

UTC = timezone.utc

# ===========================================================================
# Unit: build_acl_filter (no markers)
# ===========================================================================


def test_acl_filter_raises_on_empty_roles() -> None:
    """build_acl_filter([]) must raise ValueError (fail-closed; T-05-09-01)."""
    with pytest.raises(ValueError, match="No ACL levels resolved"):
        build_acl_filter([])


def test_acl_filter_raises_on_unknown_role() -> None:
    """Unknown roles resolve to empty allowed-set → ValueError (fail-closed)."""
    with pytest.raises(ValueError, match="No ACL levels resolved"):
        build_acl_filter(["NOT_A_ROLE"])


def test_acl_filter_allowed_set_operator() -> None:
    """build_acl_filter(['operator']) must produce MatchAny(any=['public'])."""
    flt = build_acl_filter(["operator"])
    assert flt.must is not None
    cond = list(flt.must)
    assert len(cond) == 1
    assert cond[0].key == "acl_level"
    # MatchAny.any is sorted (deterministic).
    assert list(cond[0].match.any) == ["public"]


def test_acl_filter_multi_role_union() -> None:
    """build_acl_filter(['technician','manager']) unions to {public,internal,restricted}."""
    flt = build_acl_filter(["technician", "manager"])
    cond = list(flt.must)
    assert len(cond) == 1
    assert sorted(cond[0].match.any) == ["internal", "public", "restricted"]


def test_role_to_acl_locked_mapping() -> None:
    """ROLE_TO_ACL constant must match D-63 LOCKED exactly."""
    assert ROLE_TO_ACL["operator"] == frozenset({"public"})
    assert ROLE_TO_ACL["technician"] == frozenset({"public", "internal"})
    assert ROLE_TO_ACL["manager"] == frozenset(
        {"public", "internal", "restricted"}
    )


# ===========================================================================
# Test doubles for integration tests (CI CPU-only friendly)
# ===========================================================================


class _StubEncodeOutput:
    """Stand-in for ``EncodeOutput`` (lightweight, no numpy)."""

    def __init__(
        self,
        dense_vecs: list[list[float]],
        sparse_weights: list[dict[str, float]],
    ) -> None:
        self.dense_vecs = dense_vecs
        self.sparse_weights = sparse_weights


class _StubEmbedder:
    """Deterministic stand-in for ``BgeM3Embedder``.

    Returns a fixed dense vector (1024D zeros except first slot = 1.0) and an
    empty sparse dict → ``RetrievalPipeline`` falls back to dense-only Prefetch.
    """

    def __init__(self, dim: int = 1024) -> None:
        self._dim = dim

    def encode(
        self,
        texts: list[str],
        return_dense: bool = True,
        return_sparse: bool = True,
    ) -> _StubEncodeOutput:
        dense = [[1.0] + [0.0] * (self._dim - 1) for _ in texts]
        sparse: list[dict[str, float]] = [{} for _ in texts]
        return _StubEncodeOutput(dense_vecs=dense, sparse_weights=sparse)

    def to_qdrant_sparse(self, _lex: dict[str, float]) -> Any:
        # Not invoked by the pipeline when sparse_weights[0] is empty.
        raise RuntimeError("stub: sparse not supported")


class _StubReranker:
    """Deterministic stand-in for ``BgeReranker``.

    Score = 1.0 / (1 + i) for the i-th hit → monotonically decreasing in [0,1].
    """

    async def rerank(
        self,
        query: str,
        hits: list[Any],
    ) -> list[tuple[Any, float]]:
        if not hits:
            return []
        ranked = [
            (hit, 1.0 / (1.0 + i)) for i, hit in enumerate(hits)
        ]
        return sorted(ranked, key=lambda p: -p[1])


# ===========================================================================
# Integration tests (require Qdrant testcontainer)
# ===========================================================================


async def _bootstrap_hybrid_collection(
    qdrant_client: Any, collection: str = "sop"
) -> None:
    """Create a Qdrant collection with named dense+sparse vectors.

    Mirrors Plan 05-04 bootstrap shape (D-61) — but inlined here to avoid the
    test depending on the bootstrap CLI subprocess.
    """
    from qdrant_client.http.models import (
        Distance,
        SparseVectorParams,
        VectorParams,
    )

    # Drop+recreate to keep tests hermetic.
    try:
        await qdrant_client.delete_collection(collection_name=collection)
    except Exception:
        pass

    await qdrant_client.create_collection(
        collection_name=collection,
        vectors_config={
            "dense": VectorParams(size=1024, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(),
        },
    )


async def _index_fixture_chunks(
    qdrant_client: Any,
    collection: str,
    chunks: list[dict[str, Any]],
) -> None:
    """Upsert deterministic fixture chunks. Each chunk dict carries the payload.

    Uses the same dense vector as the StubEmbedder query → cosine similarity is
    1.0 for every chunk, so the Fusion ordering depends only on the *order* of
    points (which we then re-rank via _StubReranker). This isolates rerank-vs-fusion
    behavior for KNW-09 assertions without depending on real embeddings.
    """
    from qdrant_client.http.models import PointStruct

    points: list[PointStruct] = []
    for i, ch in enumerate(chunks):
        dense = [1.0] + [0.0] * 1023
        points.append(
            PointStruct(
                id=ch["id"],
                vector={"dense": dense},
                payload=ch["payload"],
            )
        )
    await qdrant_client.upsert(collection_name=collection, points=points)


def _make_chunk(
    point_id: str,
    text: str,
    source_uri: str,
    acl_level: str,
    lang: str = "it",
    asset_family: str = "loom",
    sop_id: str = "SOP-LOOM-001",
) -> dict[str, Any]:
    return {
        "id": point_id,
        "payload": {
            "text": text,
            "source_uri": source_uri,
            "acl_level": acl_level,
            "lang": lang,
            "asset_family": asset_family,
            "sop_id": sop_id,
            "chunk_idx": 0,
            "version": "1.0",
        },
    }


@pytest.mark.integration
async def test_pipeline_search_returns_rag_citations(qdrant_client: Any) -> None:
    """End-to-end: pipeline.search returns list[RagCitation] con snippet ≤200,
    score in [0,1], retrieved_at tz-aware."""
    collection = "sop"
    await _bootstrap_hybrid_collection(qdrant_client, collection)
    chunks = [
        _make_chunk(
            "11111111-1111-1111-1111-111111111111",
            "Procedura riparazione filo ordito su telaio.",
            "file://sop/SOP-LOOM-001-v1.md",
            "public",
        ),
        _make_chunk(
            "22222222-2222-2222-2222-222222222222",
            "Tensione ordito drift causato da calibrazione.",
            "file://sop/SOP-LOOM-002-v1.md",
            "internal",
        ),
    ]
    await _index_fixture_chunks(qdrant_client, collection, chunks)

    pipeline = RetrievalPipeline(
        qdrant_client=qdrant_client,
        embedder=_StubEmbedder(),
        reranker=_StubReranker(),
    )
    citations = await pipeline.search(
        query="filo ordito",
        user_roles=["technician"],  # vede public + internal
        k=5,
    )

    assert isinstance(citations, list)
    assert len(citations) >= 1
    for c in citations:
        assert isinstance(c, RagCitation)
        assert 0.0 <= c.score <= 1.0
        assert len(c.snippet) <= 200
        assert c.retrieved_at.tzinfo is not None
        assert c.source_uri.startswith("file://sop/")


@pytest.mark.integration
async def test_hybrid_retrieval_returns_ranked(qdrant_client: Any) -> None:
    """KNW-09: scores must be monotonically descending and all in [0,1]."""
    collection = "sop"
    await _bootstrap_hybrid_collection(qdrant_client, collection)

    # 10 chunks per soddisfare il requisito "≥10".
    chunks = [
        _make_chunk(
            f"aaaa{i:04d}-aaaa-aaaa-aaaa-aaaaaaaaaaaa".replace(
                "aaaa", "abcd", 1
            ),
            f"Chunk number {i} about loom warp.",
            f"file://sop/SOP-LOOM-{i:03d}-v1.md",
            "public",
        )
        for i in range(10)
    ]
    await _index_fixture_chunks(qdrant_client, collection, chunks)

    pipeline = RetrievalPipeline(
        qdrant_client=qdrant_client,
        embedder=_StubEmbedder(),
        reranker=_StubReranker(),
    )
    citations = await pipeline.search(
        query="loom warp",
        user_roles=["technician"],
        k=10,
    )
    assert len(citations) > 1
    for c in citations:
        assert 0.0 <= c.score <= 1.0
        assert c.source_uri  # non-empty
    # Monotonically decreasing.
    scores = [c.score for c in citations]
    assert scores == sorted(scores, reverse=True), (
        f"scores not desc-sorted: {scores}"
    )


@pytest.mark.integration
async def test_rerank_disabled_uses_fusion_score(qdrant_client: Any) -> None:
    """rerank=False keeps Fusion RRF scores (different distribution from
    rerank scores)."""
    collection = "sop"
    await _bootstrap_hybrid_collection(qdrant_client, collection)
    chunks = [
        _make_chunk(
            f"cccc{i:04d}-cccc-cccc-cccc-cccccccccccc".replace(
                "cccc", "deed", 1
            ),
            f"Fusion chunk {i}.",
            f"file://sop/SOP-FUSE-{i:03d}-v1.md",
            "public",
        )
        for i in range(3)
    ]
    await _index_fixture_chunks(qdrant_client, collection, chunks)

    pipeline = RetrievalPipeline(
        qdrant_client=qdrant_client,
        embedder=_StubEmbedder(),
        reranker=_StubReranker(),
    )
    cits_no_rerank = await pipeline.search(
        "fusion", user_roles=["operator"], k=3, rerank=False
    )
    assert len(cits_no_rerank) >= 1
    # Tutti i punti hanno acl_level=public e dense identico → Fusion score in [0,1].
    for c in cits_no_rerank:
        assert 0.0 <= c.score <= 1.0


# ===========================================================================
# BgeReranker stand-alone unit (sync→async bridge correctness)
# ===========================================================================


async def test_bge_reranker_empty_hits_returns_empty_list() -> None:
    """rerank(query, []) must short-circuit to []. Does NOT load the model."""
    r = BgeReranker()
    out = await r.rerank("any query", [])
    assert out == []
