"""Hybrid deduplication for KnowledgeCurator (D-KC-01).

Provides:
  - normalized_sha256: standalone helper for exact-dup SHA-256 hashing.
  - ExactDedupChecker: SHA-256 exact-duplicate checker (fast path).
  - NearDedupChecker: BGE-M3 cosine near-duplicate checker (slow path).
  - DedupResult: immutable result dataclass.

Security (T-08-11, T-08-12):
  - Threshold is a server-side config parameter (not in API request body).
  - Qdrant query uses with_payload=False (no chunk content leaked in dedup path).

Pattern references: 08-PATTERNS.md dedup.py section (lines 834-906).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger("trn_knowledge_curator.dedup")


# ---------------------------------------------------------------------------
# Result type (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DedupResult:
    """Result of a deduplication check (D-KC-01).

    Attributes:
        is_duplicate: True when an exact or near-duplicate is detected.
        dup_type: "exact" | "near" | None.
        source_uri: Matched document URI from Qdrant or hash table; None if new.
        score: Cosine similarity score for near-dup; 1.0 for exact; None if new.
    """

    is_duplicate: bool
    dup_type: str | None = None
    source_uri: str | None = None
    score: float | None = None


# ---------------------------------------------------------------------------
# Standalone helper (also imported by tests directly)
# ---------------------------------------------------------------------------


def normalized_sha256(text: str) -> str:
    """Normalize text and return its SHA-256 hex digest.

    Normalization: lowercase + collapse all whitespace runs to a single space.
    Two documents identical after normalization produce the same digest.

    Args:
        text: Raw document text.

    Returns:
        64-character hexadecimal SHA-256 digest of the normalized text.
    """
    normalized = _normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_text(text: str) -> str:
    """Lowercase and collapse whitespace (pure function, no side effects)."""
    return re.sub(r"\s+", " ", text.lower()).strip()


# ---------------------------------------------------------------------------
# ExactDedupChecker — SHA-256 fast path (D-KC-01)
# ---------------------------------------------------------------------------


class ExactDedupChecker:
    """SHA-256 exact-duplicate checker (D-KC-01 fast path).

    Compares the SHA-256 hash of normalized document text against a known-hash set.
    No embedding call is made — this is a pure hash comparison.

    SQL lookup constant is exposed as ClassVar for meta-test inspection.
    The actual lookup is against an in-memory set supplied by the caller; the SQL
    is available for database-backed implementations.
    """

    #: ClassVar SQL for DB-backed hash lookup (parameterized — $N only).
    _NORMALIZE_SQL: ClassVar[str] = (
        "SELECT source_uri FROM documents WHERE sha256_hash = $1 LIMIT 1"
    )

    @staticmethod
    def normalize(text: str) -> str:
        """Return normalized form of text (lowercase + collapsed whitespace).

        Args:
            text: Raw document text.

        Returns:
            Normalized string (lowercase, single spaces).
        """
        return _normalize_text(text)

    @staticmethod
    def sha256(normalized: str) -> str:
        """Return SHA-256 hex digest of an already-normalized string.

        Args:
            normalized: Text that has already been processed by normalize().

        Returns:
            64-character hexadecimal SHA-256 digest.
        """
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def is_duplicate(self, text: str, known_hashes: set[str]) -> bool:
        """Check if document text matches any hash in the known-hash set.

        Args:
            text: Raw document text.
            known_hashes: Set of SHA-256 hex digests already in the corpus.

        Returns:
            True when the normalized hash of text is found in known_hashes.
        """
        normalized = self.normalize(text)
        digest = self.sha256(normalized)
        return digest in known_hashes

    def check(self, text: str, known_hashes: set[str]) -> DedupResult:
        """Full dedup check returning a DedupResult.

        Args:
            text: Raw document text.
            known_hashes: Set of SHA-256 hex digests already in the corpus.

        Returns:
            DedupResult with is_duplicate=True and dup_type="exact" when a match is found.
        """
        if self.is_duplicate(text, known_hashes):
            logger.info("exact_dup_detected", hash=self.sha256(self.normalize(text)))
            return DedupResult(is_duplicate=True, dup_type="exact", source_uri=None, score=1.0)
        return DedupResult(is_duplicate=False)


# ---------------------------------------------------------------------------
# NearDedupChecker — BGE-M3 cosine slow path (D-KC-01)
# ---------------------------------------------------------------------------


class NearDedupChecker:
    """BGE-M3 cosine near-duplicate checker (D-KC-01 slow path).

    Uses direct Qdrant query_points with score_threshold — NOT RetrievalPipeline.
    Embedding is dense-only (BGE-M3 1024D). Qdrant result with_payload=False
    prevents chunk content leak in the dedup path (T-08-12).

    Threshold is a server-side config parameter (T-08-11 mitigation): it is
    injected at construction time and never read from the request body.

    Defaults: cosine_threshold=0.92 (Pitfall §6 — recommended semantic boundary).

    Pattern reference: 08-PATTERNS.md NearDedupChecker section (lines 869-905).
    """

    #: Default cosine similarity threshold (Pitfall §6).
    _DEFAULT_COSINE_THRESHOLD: float = 0.92

    def __init__(
        self,
        *,
        qdrant_client: Any,
        embedder: Any,
        cosine_threshold: float = _DEFAULT_COSINE_THRESHOLD,
        collection_name: str = "sop",
    ) -> None:
        """Initialise the checker with injected collaborators.

        Args:
            qdrant_client: AsyncQdrantClient instance.
            embedder: BgeM3Embedder — exposes encode(texts, return_dense, return_sparse).
            cosine_threshold: Minimum cosine score to consider a near-dup (server-side config).
            collection_name: Qdrant collection to query.
        """
        if qdrant_client is None:
            raise ValueError("qdrant_client must not be None")
        if embedder is None:
            raise ValueError("embedder must not be None")
        self._client = qdrant_client
        self._embedder = embedder
        self._threshold = cosine_threshold
        self._collection = collection_name

    async def check(self, normalized_text: str) -> DedupResult:
        """Check for a near-duplicate via BGE-M3 embedding + Qdrant cosine query.

        Args:
            normalized_text: Document text already passed through ExactDedupChecker.normalize().

        Returns:
            DedupResult with is_duplicate=True and dup_type="near" when a match above
            the threshold is found; is_duplicate=False otherwise.

        Security:
            with_payload=False — no chunk content returned in dedup path (T-08-12).
        """
        # Encode dense-only (1024D BGE-M3 vector).
        output = self._embedder.encode(
            [normalized_text], return_dense=True, return_sparse=False
        )
        dense_vec = output.dense_vecs[0]

        # Direct Qdrant query — NOT RetrievalPipeline (RF-1).
        result = await self._client.query_points(
            collection_name=self._collection,
            query=dense_vec.tolist(),
            using="dense",
            limit=5,
            with_payload=False,  # T-08-12: no content leaked
            score_threshold=self._threshold,
        )

        is_near_dup = len(result.points) > 0
        if is_near_dup:
            top = result.points[0]
            matched_id = str(top.id)
            score = float(top.score)
            logger.info(
                "near_dup_detected",
                matched_id=matched_id,
                score=score,
                threshold=self._threshold,
            )
            return DedupResult(
                is_duplicate=True,
                dup_type="near",
                source_uri=matched_id,
                score=score,
            )

        return DedupResult(is_duplicate=False)


__all__ = [
    "DedupResult",
    "ExactDedupChecker",
    "NearDedupChecker",
    "normalized_sha256",
]
