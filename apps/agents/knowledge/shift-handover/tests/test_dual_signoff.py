"""Contract tests for ShiftHandover dual-supervisor sequential interrupt (TRN-03 / D-SH-03).

CONTRACT: Two sequential interrupt() calls in ShiftHandover.__call__():
  1. After first interrupt (outgoing supervisor resume):
     - First HANDOVER_SIGNOFF audit row written
     - Second audit row NOT yet written
  2. After second interrupt (incoming supervisor resume):
     - Second HANDOVER_SIGNOFF audit row written
  3. Total: exactly 2 HANDOVER_SIGNOFF audit rows in correct order

Pattern mirrors: apps/agents/maintenance/rca-specialist/tests/test_interrupt_audit_lifecycle.py
Phase 7 CR-02 fix: audit write AFTER interrupt() returns, not before.
Phase 7 CR-03 fix: approval_id=None for pending HITL rows.

Implementation target: trn_shift_handover.agent.ShiftHandover
(Wave 2-3 plan: 08-04)

Test strategy: the dual-supervisor pattern in LangGraph replays __call__ from
the top on each resume (no checkpoint in unit tests). To isolate each interrupt
boundary we patch interrupt() with a side-effect function that raises on the
first call and returns on subsequent calls. We test one boundary at a time within
a single agent.__call__ invocation using call-ordering.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.errors import GraphInterrupt

from trn_shift_handover.agent import ShiftHandover
from trn_shift_handover.models import HandoverReport, ShiftWindow

# ---------------------------------------------------------------------------
# Shared test constants
# ---------------------------------------------------------------------------

UTC = timezone.utc

_SHIFT_START = datetime(2026, 5, 24, 6, 0, 0, tzinfo=UTC)
_SHIFT_END = datetime(2026, 5, 24, 14, 0, 0, tzinfo=UTC)

_VALID_WINDOW = ShiftWindow(
    shift_start=_SHIFT_START,
    shift_end=_SHIFT_END,
    boundary_label="06:00-14:00",
)

_HANDOVER_REPORT = HandoverReport(
    shift_start=_SHIFT_START,
    shift_end=_SHIFT_END,
    boundary_label="06:00-14:00",
    open_alerts=2,
    completed_work_orders=1,
    downtime_events=0,
    quality_events=3,
    narrative_summary="Turno regolare.",
)

_STATE: dict[str, Any] = {
    "shift_window": _VALID_WINDOW,
    "thread_id": "knowledge.shift-handover.test-001",
}


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def _make_aggregator_mock() -> MagicMock:
    """Return a mock ShiftAggregator that returns _HANDOVER_REPORT on compile()."""
    aggregator = MagicMock()
    aggregator.compile = AsyncMock(return_value=_HANDOVER_REPORT)
    return aggregator


def _make_llm_mock() -> MagicMock:
    """Return a mock LLM that returns a short narrative summary."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="Turno regolare senza criticità."))
    llm.model_name = "qwen2.5-7b"
    return llm


def _make_shift_handover() -> tuple[ShiftHandover, MagicMock]:
    """Build a ShiftHandover with all collaborators mocked.

    Returns (agent, audit_writer_mock).
    """
    pool = MagicMock()
    audit_writer = MagicMock()
    audit_writer.write = AsyncMock()
    llm = _make_llm_mock()
    aggregator = _make_aggregator_mock()
    saver = MagicMock()  # CR-01: saver injected (non-None)

    agent = ShiftHandover(
        pool=pool,
        audit_writer=audit_writer,
        llm=llm,
        aggregator=aggregator,
        saver=saver,
    )
    return agent, audit_writer


# ---------------------------------------------------------------------------
# Contract 1: First HANDOVER_SIGNOFF written between the two interrupts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_handover_signoff_written_after_first_resume() -> None:
    """After first interrupt returns (outgoing supervisor): exactly 1 HANDOVER_SIGNOFF row.

    Simulates one interrupt boundary in a single __call__:
    - interrupt #1 (outgoing): RETURNS immediately (simulating first resume).
    - interrupt #2 (incoming): RAISES GraphInterrupt (simulating second execution abort).
    - Result: exactly 1 HANDOVER_SIGNOFF row written before the second interrupt aborts.

    Also verifies the first-execution (interrupt #1 raises) produces zero audit writes.

    CR-02 pattern: audit write AFTER interrupt() returns (not before).

    Implementation target: trn_shift_handover.agent.ShiftHandover.__call__()
    """
    from sft_agents.models.enums import ActionType

    # ---- Phase A: first execution — interrupt #1 raises, no audit writes ----
    agent, audit_writer = _make_shift_handover()

    def _first_raises(value: Any) -> Any:
        raise GraphInterrupt(value)

    with patch("trn_shift_handover.agent.interrupt", _first_raises):
        with pytest.raises(GraphInterrupt):
            await agent(state=_STATE)

    assert audit_writer.write.call_count == 0, (
        f"CR-02 FAIL (first execution): audit_writer.write called "
        f"{audit_writer.write.call_count} time(s) — expected 0."
    )

    # ---- Phase B: fresh agent — interrupt #1 returns, interrupt #2 raises ----
    # Simulates the first-resume execution in a single __call__: outgoing approved,
    # row #1 written, incoming interrupt fires and aborts the node.
    agent2, audit_writer2 = _make_shift_handover()

    call_count = 0

    def _first_return_second_raise(value: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # interrupt #1 (outgoing) returns — simulate first resume
            return {"approved": True, "supervisor_id": "sup-outgoing"}
        # interrupt #2 (incoming) raises — simulate second interruption
        raise GraphInterrupt(value)

    with patch("trn_shift_handover.agent.interrupt", _first_return_second_raise):
        with pytest.raises(GraphInterrupt):
            await agent2(state=_STATE)

    assert audit_writer2.write.call_count == 1, (
        f"CR-02 FAIL (first resume): expected exactly 1 HANDOVER_SIGNOFF audit row, "
        f"got {audit_writer2.write.call_count}."
    )

    # Verify the row's action_type
    written_record = audit_writer2.write.call_args_list[0][0][0]
    assert written_record.action_type == ActionType.HANDOVER_SIGNOFF.value, (
        f"Expected action_type=HANDOVER_SIGNOFF, got {written_record.action_type!r}"
    )

    # Verify motivation references outgoing
    motivation = written_record.motivation or ""
    assert "outgoing" in motivation.lower(), (
        f"First HANDOVER_SIGNOFF motivation must reference 'outgoing', got: {motivation!r}"
    )


@pytest.mark.asyncio
async def test_second_handover_signoff_written_after_second_resume() -> None:
    """After second interrupt returns (incoming supervisor): exactly 2 HANDOVER_SIGNOFF rows total.

    Simulates both interrupts returning in a single __call__:
    - interrupt #1 (outgoing): RETURNS → row #1 written.
    - interrupt #2 (incoming): RETURNS → row #2 written.
    - Total: exactly 2 HANDOVER_SIGNOFF rows.
    - First row motivation references 'outgoing'.
    - Second row motivation references 'incoming'.

    Implementation target: trn_shift_handover.agent.ShiftHandover.__call__()
    """
    from sft_agents.models.enums import ActionType

    agent, audit_writer = _make_shift_handover()

    call_count = 0

    def _both_return(value: Any) -> Any:
        nonlocal call_count
        call_count += 1
        return {"approved": True, "supervisor_id": f"sup-{call_count}"}

    with patch("trn_shift_handover.agent.interrupt", _both_return):
        result = await agent(state=_STATE)

    # 3 total writes: 2 HANDOVER_SIGNOFF + 1 HANDOVER_DRAFT
    all_records = [call[0][0] for call in audit_writer.write.call_args_list]
    signoff_records = [
        r for r in all_records
        if r.action_type == ActionType.HANDOVER_SIGNOFF.value
    ]

    assert len(signoff_records) == 2, (
        f"Expected exactly 2 HANDOVER_SIGNOFF rows, got {len(signoff_records)}. "
        f"All action_types: {[r.action_type for r in all_records]}"
    )

    # First row motivation references outgoing
    first_motivation = signoff_records[0].motivation or ""
    assert "outgoing" in first_motivation.lower(), (
        f"First HANDOVER_SIGNOFF motivation must reference 'outgoing', "
        f"got: {first_motivation!r}"
    )

    # Second row motivation references incoming
    second_motivation = signoff_records[1].motivation or ""
    assert "incoming" in second_motivation.lower(), (
        f"Second HANDOVER_SIGNOFF motivation must reference 'incoming', "
        f"got: {second_motivation!r}"
    )

    # Result must signal signed_off
    assert result.get("shift_status") == "signed_off", (
        f"Expected shift_status='signed_off', got {result.get('shift_status')!r}"
    )


@pytest.mark.asyncio
async def test_no_audit_rows_on_first_execution_before_interrupt() -> None:
    """On first execution (before any resume): audit_writer.write.call_count == 0.

    When ShiftHandover.__call__ is invoked for the first time, it compiles the
    report and calls interrupt() for the outgoing supervisor. Before interrupt()
    returns (i.e. on first execution), NO audit rows must be written.

    CR-02 contract: audit write is strictly AFTER interrupt() returns on resume.

    Implementation target: trn_shift_handover.agent.ShiftHandover.__call__()
    """
    agent, audit_writer = _make_shift_handover()

    def _first_interrupt_raises(value: Any) -> Any:
        raise GraphInterrupt(value)

    with patch("trn_shift_handover.agent.interrupt", _first_interrupt_raises):
        with pytest.raises(GraphInterrupt):
            await agent(state=_STATE)

    assert audit_writer.write.call_count == 0, (
        f"CR-02 FAIL: on first execution, audit_writer.write was called "
        f"{audit_writer.write.call_count} time(s) — expected 0. "
        f"No HANDOVER_SIGNOFF must be written before interrupt() returns."
    )


@pytest.mark.asyncio
async def test_approval_id_is_none_for_pending_hitl_rows() -> None:
    """Both HANDOVER_SIGNOFF rows use approval_id=None (CR-03 fix).

    CR-03 pattern (Phase 7): approval_id must be None for pending HITL rows;
    never fabricate a UUID at write time.

    Simulates both interrupts returning in a single __call__ to get all rows.

    Implementation target: trn_shift_handover.agent.ShiftHandover.__call__()
    """
    agent, audit_writer = _make_shift_handover()

    call_count = 0

    def _both_return(value: Any) -> Any:
        nonlocal call_count
        call_count += 1
        return {"approved": True, "supervisor_id": f"sup-{call_count}"}

    with patch("trn_shift_handover.agent.interrupt", _both_return):
        await agent(state=_STATE)

    # All writes (SIGNOFF + DRAFT) must have approval_id=None
    assert audit_writer.write.call_count >= 2, (
        f"Expected at least 2 audit writes, got {audit_writer.write.call_count}."
    )

    records = [call[0][0] for call in audit_writer.write.call_args_list]

    for idx, record in enumerate(records):
        assert record.approval_id is None, (
            f"CR-03 FAIL: row {idx + 1} (action_type={record.action_type!r}) "
            f"approval_id={record.approval_id!r}, "
            f"expected None. Never fabricate UUID for pending HITL rows."
        )
