"""Test SEC-07: accesso a chunk restricted scrive RESTRICTED_DOC_ACCESS audit row.

Tests:
    2. Una query di retrieval che restituisce ≥1 chunk con acl_level=='restricted'
       scrive una audit row con ActionType.RESTRICTED_DOC_ACCESS.
    3. Una query senza chunk restricted NON scrive la audit row (no false positive).

Plan 11-03, Task 3 (SEC-07).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc


def _make_hit(acl_level: str, source_uri: str = "sop://test/doc") -> Any:
    """Costruisce un fake ScoredPoint Qdrant con il payload necessario."""
    hit = MagicMock()
    hit.id = "test-chunk-id"
    hit.score = 0.85
    hit.payload = {
        "text": f"Contenuto del chunk acl_level={acl_level}",
        "source_uri": source_uri,
        "acl_level": acl_level,
    }
    return hit


def _make_pipeline(audit_writer: Any) -> Any:
    """Costruisce un RetrievalPipeline con mock collaboratori + audit_writer."""
    from sft_knowledge.retrieval.pipeline import RetrievalPipeline

    mock_client = AsyncMock()
    mock_embedder = MagicMock()
    mock_reranker = AsyncMock()

    # Embed output mock
    mock_encode_output = MagicMock()
    mock_encode_output.dense_vecs = [[0.1] * 1024]
    mock_encode_output.sparse_weights = [None]
    mock_embedder.encode = MagicMock(return_value=mock_encode_output)

    # Reranker ritorna lista (hit, score)
    async def _rerank(query, hits):
        return [(h, float(h.score)) for h in hits]

    mock_reranker.rerank = _rerank

    pipeline = RetrievalPipeline(
        qdrant_client=mock_client,
        embedder=mock_embedder,
        reranker=mock_reranker,
        audit_writer=audit_writer,
    )
    return pipeline, mock_client


# ---------------------------------------------------------------------------
# Test 2: chunk restricted → audit row RESTRICTED_DOC_ACCESS
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_restricted_chunk_writes_audit_row():
    """Accesso a chunk acl_level='restricted' scrive RESTRICTED_DOC_ACCESS (SEC-07)."""
    from sft_agents.models.enums import ActionType

    audit_writer = AsyncMock()
    audit_writer.write = AsyncMock(return_value=None)

    pipeline, mock_client = _make_pipeline(audit_writer)

    # Qdrant ritorna un chunk restricted
    restricted_hit = _make_hit("restricted", "sop://secure/proc-001")
    mock_result = MagicMock()
    mock_result.points = [restricted_hit]
    mock_client.query_points = AsyncMock(return_value=mock_result)

    citations = await pipeline.search(
        "procedura riservata",
        user_roles=["manager"],
        k=5,
        principal={"sub": "manager@mantis.it"},
    )

    assert len(citations) >= 1, "Doveva restituire almeno una citation"

    # Verifica che audit_writer.write sia stato chiamato
    assert audit_writer.write.called, (
        "RESTRICTED_DOC_ACCESS audit row NON scritta (SEC-07)"
    )

    # Verifica che l'action_type nell'audit record sia RESTRICTED_DOC_ACCESS
    write_call_args = audit_writer.write.call_args
    audit_record = write_call_args[0][0]  # primo argomento posizionale
    assert audit_record.action_type == ActionType.RESTRICTED_DOC_ACCESS.value, (
        f"action_type errato: {audit_record.action_type!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: nessun chunk restricted → NO audit row (no false positive)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_non_restricted_chunk_does_not_write_audit_row():
    """Accesso a chunk NON restricted NON scrive audit row (no false positive, SEC-07)."""
    audit_writer = AsyncMock()
    audit_writer.write = AsyncMock(return_value=None)

    pipeline, mock_client = _make_pipeline(audit_writer)

    # Qdrant ritorna chunk public e internal — nessun restricted
    hit_public = _make_hit("public", "sop://public/doc-001")
    hit_internal = _make_hit("internal", "sop://internal/doc-002")
    mock_result = MagicMock()
    mock_result.points = [hit_public, hit_internal]
    mock_client.query_points = AsyncMock(return_value=mock_result)

    citations = await pipeline.search(
        "procedura standard",
        user_roles=["technician"],
        k=5,
        principal={"sub": "tech@mantis.it"},
    )

    # audit_writer.write NON deve essere chiamato per chunk non-restricted
    assert not audit_writer.write.called, (
        "Audit row scritta per chunk NON restricted — falso positivo (SEC-07)"
    )


# ---------------------------------------------------------------------------
# Test bonus: nessun hit → no audit row
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_no_hits_does_not_write_audit_row():
    """Nessun hit da Qdrant → nessuna audit row scritta."""
    audit_writer = AsyncMock()
    audit_writer.write = AsyncMock(return_value=None)

    pipeline, mock_client = _make_pipeline(audit_writer)

    mock_result = MagicMock()
    mock_result.points = []
    mock_client.query_points = AsyncMock(return_value=mock_result)

    citations = await pipeline.search(
        "query senza risultati",
        user_roles=["operator"],
        k=5,
        principal={"sub": "op@mantis.it"},
    )

    assert citations == []
    assert not audit_writer.write.called, "Audit row scritta per 0 hits"
