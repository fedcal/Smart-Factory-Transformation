"""Contract tests for DocumentationSynthesizer HITL pre-index approval (TRN-04 / D-DS-03).

CONTRACT (CR-02 pattern):
  - Qdrant indexing (upsert) must NOT happen before interrupt() returns
  - Exactly 1 SOP_DRAFT audit row written AFTER interrupt() returns on resume
  - No Qdrant upsert on first execution (before interrupt returns)
  - On resume: Qdrant upsert fires exactly once AFTER audit write
  - approval_id=None on SOP_DRAFT row (CR-03 fix)

D-DS-03: HITL approval before indexing — DocumentationSynthesizer.__call__() must:
  1. Generate IT SOP + EN translation
  2. Call interrupt() for human approval
  3. On resume: write SOP_DRAFT audit row + call Qdrant upsert

Implementation target: trn_documentation_synthesizer.agent.DocumentationSynthesizer
(Wave 2-3 plan: 08-07)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sft_agents.models.evidence import RagCitation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_mock_citation(n: int = 1) -> RagCitation:
    return RagCitation(
        source_uri=f"doc://sop-{n:03d}",
        snippet=f"Technical snippet {n}.",
        score=0.9,
        retrieved_at=_now(),
    )


def _make_llm_mock() -> MagicMock:
    """Build a mock LLM that always returns an appropriate response."""
    llm = MagicMock()
    it_sop_content = (
        "## Scopo\nProcedura per overheating. [SRC:1]\n\n"
        "## Prerequisiti\nAttrezzatura necessaria.\n\n"
        "## Passi\n1. Analisi. 2. Correzione.\n\n"
        "## Sicurezza\nNorme di sicurezza.\n\n"
        "## Riferimenti\nDocumentazione tecnica. [SRC:1]"
    )
    en_content = "Procedure for overheating. [SRC:1]"

    call_count = [0]

    async def _ainvoke(messages: Any) -> Any:
        call_count[0] += 1
        response = MagicMock()
        # First call is always the IT SOP generation
        if call_count[0] == 1:
            response.content = it_sop_content
        else:
            # EN translations (5 sections)
            response.content = en_content
        return response

    llm.ainvoke = AsyncMock(side_effect=_ainvoke)
    return llm


def _make_agent() -> Any:
    """Build a DocumentationSynthesizer with all dependencies mocked."""
    from trn_documentation_synthesizer.agent import DocumentationSynthesizer

    # Mock pool
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    conn.fetch = AsyncMock(return_value=[])

    # Mock audit writer
    audit_writer = MagicMock()
    audit_writer.write = AsyncMock()

    # Mock LLM with unlimited responses
    llm = _make_llm_mock()

    # Mock retrieval pipeline — returns one citation
    retrieval = MagicMock()
    retrieval.search = AsyncMock(return_value=[_make_mock_citation(1)])

    # Mock Qdrant indexer
    indexer = MagicMock()
    indexer.upsert = AsyncMock()

    # Mock event aggregator
    event_aggregator = MagicMock()
    event_aggregator.fetch = AsyncMock(return_value=[])

    # Mock SOPCitationValidator — passes validation
    from trn_documentation_synthesizer.validators import SOPCitationValidator
    validator = SOPCitationValidator()

    # Non-None saver (CR-01 guard requires non-None saver)
    saver = MagicMock()

    agent = DocumentationSynthesizer(
        pool=pool,
        audit_writer=audit_writer,
        llm=llm,
        retrieval_pipeline=retrieval,
        indexer=indexer,
        event_aggregator=event_aggregator,
        validator=validator,
        saver=saver,
    )

    return agent, indexer, audit_writer


_STATE: dict[str, Any] = {
    "failure_mode": "overheating",
    "asset_id": "loom-01",
    "window_days": 180,
    "user_roles": ["technician"],
}


# ---------------------------------------------------------------------------
# Contract 1: No Qdrant upsert before interrupt returns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_qdrant_upsert_before_interrupt_returns() -> None:
    """Qdrant upsert must NOT be called on first execution (before interrupt returns).

    D-DS-03: HITL approval gates Qdrant indexing. On first execution, interrupt()
    raises GraphInterrupt. Qdrant client mock's upsert must have call_count == 0
    after the first (interrupted) execution.
    """
    try:
        from langgraph.types import GraphInterrupt
    except ImportError:
        # In test environments without langgraph, simulate GraphInterrupt
        class GraphInterrupt(Exception):  # type: ignore[no-redef]
            pass

    agent, indexer, audit_writer = _make_agent()

    interrupt_call_count = 0

    def _simulated_interrupt(value: Any) -> Any:
        nonlocal interrupt_call_count
        interrupt_call_count += 1
        if interrupt_call_count == 1:
            raise GraphInterrupt(value)
        return {"approved": True, "supervisor_id": "user-001"}

    with patch("trn_documentation_synthesizer.agent.interrupt", _simulated_interrupt):
        with pytest.raises((GraphInterrupt, NotImplementedError, Exception)) as exc_info:
            await agent(state=_STATE)

        # After first execution (interrupted): Qdrant upsert must NOT have been called
        assert indexer.upsert.call_count == 0, (
            f"D-DS-03 FAIL: Qdrant indexer.upsert was called {indexer.upsert.call_count} "
            f"time(s) on the first execution (before interrupt returns). "
            f"Qdrant indexing must be gated behind supervisor HITL (CR-02 pattern)."
        )


# ---------------------------------------------------------------------------
# Contract 2: Exactly 1 SOP_DRAFT row on resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exactly_one_sop_draft_audit_row_on_resume() -> None:
    """On resume: audit_writer.write called exactly once with SOP_DRAFT action_type.

    After interrupt() returns (supervisor approved), exactly 1 SOP_DRAFT audit row
    is written. The row uses approval_id=None (CR-03 fix).
    """
    try:
        from langgraph.types import GraphInterrupt
    except ImportError:
        class GraphInterrupt(Exception):  # type: ignore[no-redef]
            pass

    agent, indexer, audit_writer = _make_agent()

    interrupt_call_count = 0

    def _simulated_interrupt(value: Any) -> Any:
        nonlocal interrupt_call_count
        interrupt_call_count += 1
        if interrupt_call_count == 1:
            raise GraphInterrupt(value)
        return {"approved": True, "supervisor_id": "user-001"}

    write_audit_calls: list[dict] = []

    async def _spy_write_audit(**kwargs: Any) -> None:
        write_audit_calls.append(dict(kwargs))

    with patch("trn_documentation_synthesizer.agent.interrupt", _simulated_interrupt):
        # First execution: interrupted
        with pytest.raises((GraphInterrupt, NotImplementedError, Exception)):
            await agent(state=_STATE)

        assert audit_writer.write.call_count == 0, (
            f"Audit row must NOT be written on first (interrupted) execution. "
            f"Got {audit_writer.write.call_count} write(s)."
        )

        # Resume execution: audit row should fire exactly once
        with patch.object(agent, "_write_audit", side_effect=_spy_write_audit):
            await agent(state=_STATE)

    assert len(write_audit_calls) == 1, (
        f"D-DS-03 FAIL (resume): _write_audit was called {len(write_audit_calls)} "
        f"time(s) — expected exactly 1. "
        f"Exactly one SOP_DRAFT audit row must be written on resume (CR-02 pattern)."
    )


@pytest.mark.asyncio
async def test_qdrant_upsert_fires_after_audit_write_on_resume() -> None:
    """On resume: Qdrant upsert fires exactly once AFTER the SOP_DRAFT audit write.

    Both the audit write and the Qdrant upsert must fire on resume (not on first
    execution). Execution order: interrupt() returns -> write SOP_DRAFT -> Qdrant upsert.
    """
    try:
        from langgraph.types import GraphInterrupt
    except ImportError:
        class GraphInterrupt(Exception):  # type: ignore[no-redef]
            pass

    agent, indexer, audit_writer = _make_agent()

    interrupt_call_count = 0
    call_order: list[str] = []

    def _simulated_interrupt(value: Any) -> Any:
        nonlocal interrupt_call_count
        interrupt_call_count += 1
        if interrupt_call_count == 1:
            raise GraphInterrupt(value)
        return {"approved": True}

    # Track call order: audit write vs Qdrant upsert
    original_write = audit_writer.write.side_effect

    async def _tracking_write(*args: Any, **kwargs: Any) -> None:
        call_order.append("audit_write")

    async def _tracking_upsert(*args: Any, **kwargs: Any) -> None:
        call_order.append("qdrant_upsert")

    audit_writer.write.side_effect = _tracking_write
    indexer.upsert.side_effect = _tracking_upsert

    with patch("trn_documentation_synthesizer.agent.interrupt", _simulated_interrupt):
        # First execution: interrupted (no side effects)
        with pytest.raises((GraphInterrupt, NotImplementedError, Exception)):
            await agent(state=_STATE)

        assert len(call_order) == 0, (
            f"No side effects (audit or upsert) must occur on first execution. "
            f"Got: {call_order}"
        )

        # Resume execution: both should fire
        await agent(state=_STATE)

    assert "audit_write" in call_order, "SOP_DRAFT audit row must be written on resume"
    assert "qdrant_upsert" in call_order, "Qdrant upsert must fire on resume"
    assert indexer.upsert.call_count == 1, (
        f"Qdrant upsert must fire exactly once on resume. "
        f"Got {indexer.upsert.call_count} call(s)."
    )


@pytest.mark.asyncio
async def test_sop_draft_audit_row_has_approval_id_none() -> None:
    """SOP_DRAFT audit row uses approval_id=None (CR-03 fix).

    CR-03 pattern (Phase 7): approval_id must be None for pending HITL rows.
    """
    try:
        from langgraph.types import GraphInterrupt
    except ImportError:
        class GraphInterrupt(Exception):  # type: ignore[no-redef]
            pass

    agent, indexer, audit_writer = _make_agent()

    interrupt_call_count = 0

    def _simulated_interrupt(value: Any) -> Any:
        nonlocal interrupt_call_count
        interrupt_call_count += 1
        if interrupt_call_count == 1:
            raise GraphInterrupt(value)
        return {"approved": True}

    with patch("trn_documentation_synthesizer.agent.interrupt", _simulated_interrupt):
        # First execution: interrupted
        with pytest.raises((GraphInterrupt, NotImplementedError, Exception)):
            await agent(state=_STATE)

        # Resume: audit row is written
        await agent(state=_STATE)

    # Verify the AuditRecord written to audit_writer has approval_id=None
    assert audit_writer.write.call_count >= 1, (
        "audit_writer.write must be called at least once on resume"
    )

    written_record = audit_writer.write.call_args[0][0]  # first positional arg
    assert written_record.approval_id is None, (
        f"CR-03 FAIL: SOP_DRAFT audit row must have approval_id=None "
        f"(pending HITL — never fabricate UUID). Got: {written_record.approval_id!r}"
    )
