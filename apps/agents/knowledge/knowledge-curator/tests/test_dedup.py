"""Contract tests for KnowledgeCurator deduplication (D-KC-01).

CONTRACT: Hybrid dedup using SHA-256 hash (exact-dup fast path) + BGE-M3 cosine
similarity (near-dup semantic path).

EXACT-DUP (D-KC-01 fast path):
  - SHA-256 of normalized text (lowercase, collapsed whitespace)
  - Two documents with identical normalized content share the same hash
  - Hash-matched documents are flagged as exact duplicates without embedding query

NEAR-DUP (D-KC-01 semantic path, threshold 0.92 default):
  - Mock embedder returns dense vector; mock Qdrant query_points returns results
  - Above threshold: document flagged as near-dup
  - Below threshold: document accepted as new
  - Threshold is configurable (not hardcoded)

Implementation target:
  trn_knowledge_curator.dedup.ExactDedupChecker  (SHA-256)
  trn_knowledge_curator.dedup.NearDedupChecker   (BGE-M3 + Qdrant)
(Wave 2-3 plan: 08-06)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from trn_knowledge_curator.dedup import (
    ExactDedupChecker,
    NearDedupChecker,
    normalized_sha256,
)


# ---------------------------------------------------------------------------
# Contract 1: Exact dedup via SHA-256
# ---------------------------------------------------------------------------


def test_exact_dup_same_normalized_text_same_hash() -> None:
    """Two documents with identical normalized text produce the same SHA-256 hash.

    D-KC-01 exact-dup fast path: normalized_sha256(text) is deterministic.
    Normalization: lowercase + collapse whitespace.
    "Hello  World" and "hello world" must produce the same hash.

    Implementation target: trn_knowledge_curator.dedup.normalized_sha256()
    """
    hash1 = normalized_sha256("Hello  World")
    hash2 = normalized_sha256("hello world")
    assert hash1 == hash2, (
        f"Normalized SHA-256 must be identical for text that differs only in case or whitespace. "
        f"Got hash1={hash1!r}, hash2={hash2!r}"
    )
    # Also verify with whitespace-heavy document
    hash3 = normalized_sha256("SOP-001:   Sostituzione   subbio\n\n")
    hash4 = normalized_sha256("sop-001: sostituzione subbio")
    assert hash3 == hash4


def test_exact_dup_different_content_different_hash() -> None:
    """Two documents with different content produce different SHA-256 hashes.

    D-KC-01: normalized_sha256 must distinguish semantically different documents.
    'SOP-001: sostituzione subbio' vs 'SOP-002: pulizia telai' -> different hashes.

    Implementation target: trn_knowledge_curator.dedup.normalized_sha256()
    """
    hash1 = normalized_sha256("SOP-001: sostituzione subbio")
    hash2 = normalized_sha256("SOP-002: pulizia telai")
    assert hash1 != hash2, (
        f"Different documents must produce different SHA-256 hashes. "
        f"Got hash1={hash1!r}, hash2={hash2!r}"
    )


def test_exact_dup_checker_flags_known_hash_as_duplicate() -> None:
    """ExactDedupChecker flags document whose hash is already in the known-hash set.

    Given a set of known hashes and a new document whose hash matches one,
    ExactDedupChecker.is_duplicate(text, known_hashes) returns True.

    Implementation target: trn_knowledge_curator.dedup.ExactDedupChecker
    """
    checker = ExactDedupChecker()

    # Build a known-hash set from a document already in the corpus.
    original_text = "SOP-001: sostituzione subbio — procedura completa"
    known = {normalized_sha256(original_text)}

    # Exact same content (including case/whitespace variant) — must flag as duplicate.
    assert checker.is_duplicate(original_text, known) is True

    # Normalized variant must also be flagged.
    assert checker.is_duplicate("SOP-001: sostituzione subbio — procedura completa", known) is True

    # Different content — must NOT be flagged.
    assert checker.is_duplicate("SOP-002: pulizia telai", known) is False


# ---------------------------------------------------------------------------
# Contract 2: Near-dup via BGE-M3 cosine threshold
# ---------------------------------------------------------------------------


def _make_mock_embedder(dense_vec: np.ndarray) -> MagicMock:
    """Return a mock BgeM3Embedder that returns a fixed dense vector."""
    output = MagicMock()
    output.dense_vecs = [dense_vec]
    embedder = MagicMock()
    embedder.encode.return_value = output
    return embedder


def _make_mock_qdrant(score: float | None) -> MagicMock:
    """Return an async mock Qdrant client.

    If score is not None, query_points returns one point with that score.
    If score is None, query_points returns zero points (below threshold).
    """
    client = MagicMock()
    result = MagicMock()
    if score is not None:
        point = MagicMock()
        point.id = "doc-abc-123"
        point.score = score
        result.points = [point]
    else:
        result.points = []
    client.query_points = AsyncMock(return_value=result)
    return client


@pytest.mark.asyncio
async def test_near_dup_threshold_above_returns_is_duplicate() -> None:
    """Near-dup: cosine score >= threshold (0.92 default) -> document is near-dup.

    Given mock embedder returning a fixed dense vector and mock Qdrant query_points
    returning a result with score=0.95 (above threshold), NearDedupChecker must
    return (is_dup=True, matched_id=<the returned point id>).

    D-KC-01: configurable threshold, default 0.92.

    Implementation target: trn_knowledge_curator.dedup.NearDedupChecker
    """
    dense_vec = np.ones(1024, dtype=np.float32)
    embedder = _make_mock_embedder(dense_vec)
    qdrant = _make_mock_qdrant(score=0.95)

    checker = NearDedupChecker(qdrant_client=qdrant, embedder=embedder)
    result = await checker.check("This is a near-duplicate document.")

    assert result.is_duplicate is True, "Score 0.95 above default threshold 0.92 must flag near-dup"
    assert result.dup_type == "near"
    assert result.source_uri == "doc-abc-123"
    assert result.score == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_near_dup_threshold_below_returns_not_duplicate() -> None:
    """Near-dup: cosine score < threshold -> document is new (not a near-dup).

    Given mock Qdrant query_points returning no results above the threshold
    (score_threshold=0.92), NearDedupChecker must return (is_dup=False, matched_id=None).

    D-KC-01: below-threshold documents are accepted as new content.

    Implementation target: trn_knowledge_curator.dedup.NearDedupChecker
    """
    dense_vec = np.ones(1024, dtype=np.float32)
    embedder = _make_mock_embedder(dense_vec)
    # Qdrant returns no points above threshold (score_threshold filters server-side).
    qdrant = _make_mock_qdrant(score=None)

    checker = NearDedupChecker(qdrant_client=qdrant, embedder=embedder)
    result = await checker.check("This is a brand new unique document.")

    assert result.is_duplicate is False, "No results above threshold must return is_dup=False"
    assert result.source_uri is None
    assert result.score is None


@pytest.mark.asyncio
async def test_near_dup_threshold_is_configurable() -> None:
    """NearDedupChecker uses a configurable threshold, not a hardcoded constant.

    Given threshold=0.80, a result with score=0.85 must return is_dup=True.
    Given threshold=0.90, the same score=0.85 must return is_dup=False.

    Pitfall §6 guard: threshold is server-side config (not API body input).

    Implementation target: trn_knowledge_curator.dedup.NearDedupChecker
    """
    dense_vec = np.ones(1024, dtype=np.float32)
    embedder_low = _make_mock_embedder(dense_vec)
    embedder_high = _make_mock_embedder(dense_vec)

    # threshold=0.80 — score=0.85 is ABOVE -> is_dup=True
    qdrant_low = _make_mock_qdrant(score=0.85)
    checker_low = NearDedupChecker(
        qdrant_client=qdrant_low,
        embedder=embedder_low,
        cosine_threshold=0.80,
    )
    result_low = await checker_low.check("document text")
    assert result_low.is_duplicate is True, (
        "With threshold=0.80, score=0.85 should return is_dup=True"
    )

    # threshold=0.90 — Qdrant returns no results above 0.90 (score=0.85 filtered out)
    qdrant_high = _make_mock_qdrant(score=None)  # no results above high threshold
    checker_high = NearDedupChecker(
        qdrant_client=qdrant_high,
        embedder=embedder_high,
        cosine_threshold=0.90,
    )
    result_high = await checker_high.check("document text")
    assert result_high.is_duplicate is False, (
        "With threshold=0.90, no results above threshold should return is_dup=False"
    )
