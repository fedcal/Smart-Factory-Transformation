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

Wave 0 scaffold: test functions fail explicitly with a message naming the
unimplemented contract. NOT module-level pytest.skip (Phase 6/7 Wave 0 decision).
"""

from __future__ import annotations

import pytest


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
    pytest.fail(
        "NOT IMPLEMENTED — contract: normalized_sha256() produces identical hashes "
        "for text that differs only in case or whitespace. "
        "D-KC-01 exact-dup SHA-256 fast path. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.dedup"
    )


def test_exact_dup_different_content_different_hash() -> None:
    """Two documents with different content produce different SHA-256 hashes.

    D-KC-01: normalized_sha256 must distinguish semantically different documents.
    'SOP-001: sostituzione subbio' vs 'SOP-002: pulizia telai' -> different hashes.

    Implementation target: trn_knowledge_curator.dedup.normalized_sha256()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: normalized_sha256() produces different hashes "
        "for documents with different content. "
        "D-KC-01 exact-dup SHA-256 fast path. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.dedup"
    )


def test_exact_dup_checker_flags_known_hash_as_duplicate() -> None:
    """ExactDedupChecker flags document whose hash is already in the known-hash set.

    Given a set of known hashes and a new document whose hash matches one,
    ExactDedupChecker.is_duplicate(text, known_hashes) returns True.

    Implementation target: trn_knowledge_curator.dedup.ExactDedupChecker
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: ExactDedupChecker returns True when document "
        "hash is in the known-hash set. D-KC-01 exact-dup detection. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.dedup"
    )


# ---------------------------------------------------------------------------
# Contract 2: Near-dup via BGE-M3 cosine threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_near_dup_threshold_above_returns_is_duplicate() -> None:
    """Near-dup: cosine score >= threshold (0.92 default) -> document is near-dup.

    Given mock embedder returning a fixed dense vector and mock Qdrant query_points
    returning a result with score=0.95 (above threshold), NearDedupChecker must
    return (is_dup=True, matched_id=<the returned point id>).

    D-KC-01: configurable threshold, default 0.92.

    Implementation target: trn_knowledge_curator.dedup.NearDedupChecker
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: NearDedupChecker returns is_dup=True "
        "when Qdrant query_points returns results with score >= threshold (default 0.92). "
        "D-KC-01 near-dup semantic path with configurable threshold. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.dedup"
    )


@pytest.mark.asyncio
async def test_near_dup_threshold_below_returns_not_duplicate() -> None:
    """Near-dup: cosine score < threshold -> document is new (not a near-dup).

    Given mock Qdrant query_points returning no results above the threshold
    (score_threshold=0.92), NearDedupChecker must return (is_dup=False, matched_id=None).

    D-KC-01: below-threshold documents are accepted as new content.

    Implementation target: trn_knowledge_curator.dedup.NearDedupChecker
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: NearDedupChecker returns is_dup=False "
        "when Qdrant query_points returns no results above threshold (default 0.92). "
        "D-KC-01 near-dup boundary: below-threshold = new document. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.dedup"
    )


@pytest.mark.asyncio
async def test_near_dup_threshold_is_configurable() -> None:
    """NearDedupChecker uses a configurable threshold, not a hardcoded constant.

    Given threshold=0.80, a result with score=0.85 must return is_dup=True.
    Given threshold=0.90, the same score=0.85 must return is_dup=False.

    Pitfall §6 guard: threshold is server-side config (not API body input).

    Implementation target: trn_knowledge_curator.dedup.NearDedupChecker
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: NearDedupChecker.cosine_threshold is configurable. "
        "Same score produces different is_dup result depending on threshold value. "
        "Pitfall §6: document threshold in config, not hardcoded, not in API body. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.dedup"
    )
