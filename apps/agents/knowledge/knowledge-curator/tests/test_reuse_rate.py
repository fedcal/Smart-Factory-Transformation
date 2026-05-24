"""Contract tests for KnowledgeCurator reuse-rate KPI (D-KC-03).

CONTRACT: Reuse-rate KPI = distinct_documents_cited / total_indexed_documents
over a rolling window, computed from source_uri citations in audit.actions.

Computed from asyncpg query against audit.actions:
  - distinct_cited: COUNT(DISTINCT evidence_panel->>'source_uri') in the rolling window
  - total_indexed: COUNT from the document index (Qdrant or ingest_state table)

Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
(Wave 2-3 plan: 08-06)

Wave 0 scaffold: test functions fail explicitly with a message naming the
unimplemented contract. NOT module-level pytest.skip (Phase 6/7 Wave 0 decision).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Contract 1: Basic reuse-rate computation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reuse_rate_distinct_cited_over_total_indexed() -> None:
    """compute_reuse_rate returns distinct_cited / total_indexed from mock asyncpg.

    D-KC-03: reuse_rate = distinct_documents_cited / total_indexed_documents.

    Given mock pool.fetchrow returning (distinct_cited=3, total_indexed=10),
    compute_reuse_rate() must return 0.3 (3/10).

    Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: compute_reuse_rate() = distinct_cited / total_indexed. "
        "Given mock asyncpg (distinct=3, total=10) -> 0.3. "
        "D-KC-03 reuse-rate KPI from source_uri citations in audit.actions. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.reuse_rate"
    )


@pytest.mark.asyncio
async def test_reuse_rate_zero_indexed_returns_zero() -> None:
    """compute_reuse_rate returns 0.0 when total_indexed == 0 (no divide-by-zero).

    D-KC-03: guard against division by zero when no documents are indexed yet.

    Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: compute_reuse_rate() returns 0.0 (not ZeroDivisionError) "
        "when total_indexed == 0. Division-by-zero guard required. "
        "D-KC-03 reuse-rate KPI. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.reuse_rate"
    )


@pytest.mark.asyncio
async def test_reuse_rate_queries_source_uri_from_evidence_panel_jsonb() -> None:
    """compute_reuse_rate queries distinct source_uri from evidence_panel JSONB.

    D-KC-03: citations come from evidence_panel JSONB in audit.actions.
    Verify the mock pool.fetchrow/fetch was called with a query containing
    evidence_panel and source_uri (not a separate table).

    Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: compute_reuse_rate() queries distinct source_uri "
        "from audit.actions.evidence_panel JSONB (not a separate citations table). "
        "Verify pool.fetch/fetchrow was called with evidence_panel + source_uri. "
        "D-KC-03 reuse-rate from existing audit backbone. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.reuse_rate"
    )


@pytest.mark.asyncio
async def test_reuse_rate_uses_rolling_window_not_all_time() -> None:
    """compute_reuse_rate is computed over a configurable rolling window, not all-time.

    D-KC-03: rolling window parameter (e.g. days=30). Verify the asyncpg query
    includes a timestamp filter (ts BETWEEN window_start AND window_end).

    Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: compute_reuse_rate(window_days=30) computes "
        "KPI over a rolling window only (not all-time). asyncpg query must include "
        "timestamp filter on audit.actions.ts. "
        "D-KC-03 rolling window reuse-rate. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.reuse_rate"
    )
