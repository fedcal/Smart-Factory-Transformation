# Covers KNW-09 (hybrid retrieval) per 05-VALIDATION.md
"""Wave 0 stub — implemented in Plan 05-09 (retrieval + tools + memory)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-09")


def test_hybrid_retrieval_returns_ranked() -> None:
    """KNW-09: RetrievalPipeline.search() returns dense+sparse fused results re-ranked by bge-reranker."""
    pass
