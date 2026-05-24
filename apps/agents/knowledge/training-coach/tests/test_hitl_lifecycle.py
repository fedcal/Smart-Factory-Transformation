"""Contract tests for TrainingCoach HITL competency sign-off lifecycle (TRN-02 / D-TC-03).

CONTRACT (W4/CR-02 compliant):
  ON PASS (score >= threshold):
    - Single interrupt() call for supervisor sign-off
    - Exactly 1 TRAINING_SIGNOFF audit row, written AFTER interrupt() returns (CR-02)
    - Exactly 1 TRAINING_SESSION audit row TOTAL for the passing session
    - TRAINING_SESSION write occurs AFTER interrupt() returns so it is NOT
      replayed/double-written on resume (CR-02 prevention)
    - TRAINING_SESSION row is NOT written before interrupt() (not replayed on resume)
    - approval_id=None on the TRAINING_SIGNOFF row (CR-03 fix)

  ON FAIL (score < threshold):
    - No interrupt() call
    - No TRAINING_SIGNOFF row
    - Exactly 1 TRAINING_SESSION row total (session still recorded)
    - No HITL escalation

KEY CONTRACT (W4/CR-02): The TRAINING_SESSION write occurs AFTER interrupt() returns
so it is NOT replayed/double-written on resume. Total audit rows for a passing
session == 2 (1 TRAINING_SIGNOFF + 1 TRAINING_SESSION). A failing session == 1
(1 TRAINING_SESSION only).

Implementation target: trn_training_coach.agent.TrainingCoach
(Wave 2-3 plan: 08-05)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.errors import GraphInterrupt

from sft_agents.models.enums import ActionType
from trn_training_coach.agent import TrainingCoach
from trn_training_coach.quiz import MCQQuestion, MCQSession


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------


def _make_passing_question(correct_index: int = 0) -> MCQQuestion:
    """Build a simple MCQQuestion for test use."""
    return MCQQuestion(
        question_text="Test question?",
        options=["Risposta A (corretta)", "Risposta B", "Risposta C", "Risposta D"],
        correct_answer_index=correct_index,
        source_uri="sop://test/section-1",
        difficulty="medium",
    )


def _make_coach(*, pass_threshold: float = 0.80) -> tuple[TrainingCoach, MagicMock]:
    """Build a TrainingCoach with all collaborators mocked.

    Returns (coach, audit_writer_mock).
    """
    audit_writer = MagicMock()
    audit_writer.write = AsyncMock()

    coach = TrainingCoach(
        pool=MagicMock(),
        audit_writer=audit_writer,
        llm=None,       # LLM not needed for pre-scored tests
        retrieval_pipeline=None,  # no retrieval needed for pre-scored tests
        escalate_tool=MagicMock(),
        pass_threshold=pass_threshold,
    )
    return coach, audit_writer


def _make_passing_state(session_id: str = "sess-pass") -> dict[str, Any]:
    """State dict for a passing session (score 1.0 — all answers correct)."""
    return {
        "persona_role": "tessitore",
        "user_roles": ["tessitore"],
        "session_id": session_id,
        # answers will be matched with generated fallback questions (correct_index=0)
        "answers": [0, 0, 0, 0, 0],
    }


def _make_failing_state(session_id: str = "sess-fail") -> dict[str, Any]:
    """State dict for a failing session (score 0.0 — no answers correct)."""
    return {
        "persona_role": "tessitore",
        "user_roles": ["tessitore"],
        "session_id": session_id,
        # answers deliberately wrong (correct_index=0, answers=1)
        "answers": [1, 1, 1, 1, 1],
    }


# ---------------------------------------------------------------------------
# Contract 1: Passing session — exactly 1 TRAINING_SIGNOFF + 1 TRAINING_SESSION
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_passing_session_produces_exactly_one_training_signoff_row() -> None:
    """On pass: audit_writer.write called with TRAINING_SIGNOFF exactly once.

    Given a passing quiz session (score >= 0.80), after interrupt() returns
    (resume path), audit_writer.write must be called with
    action_type=TRAINING_SIGNOFF exactly once.

    CR-02: write fires only after interrupt() returns (on resume), not on first run.

    Implementation target: trn_training_coach.agent.TrainingCoach.__call__()
    """
    coach, audit_writer = _make_coach(pass_threshold=0.80)
    state = _make_passing_state()

    # Patch interrupt() to return directly (simulates resume — interrupt already returned)
    with patch("trn_training_coach.agent.interrupt", return_value={"approved": True}):
        await coach(state=state)

    # Count TRAINING_SIGNOFF writes
    signoff_calls = [
        call_args
        for call_args in audit_writer.write.call_args_list
        if call_args.kwargs.get("action_type") == ActionType.TRAINING_SIGNOFF
    ]
    assert len(signoff_calls) == 1, (
        f"Expected exactly 1 TRAINING_SIGNOFF write, got {len(signoff_calls)}. "
        f"All write calls: {audit_writer.write.call_args_list}"
    )


@pytest.mark.asyncio
async def test_passing_session_produces_exactly_one_training_session_row_total() -> None:
    """On pass: exactly 1 TRAINING_SESSION row total — never double-written (W4/CR-02).

    TRAINING_SESSION write occurs after interrupt() returns so it is NOT replayed
    on resume. Total audit rows = 2 (TRAINING_SIGNOFF + TRAINING_SESSION).
    TRAINING_SESSION must NOT be written before interrupt() (which would cause
    double-write on resume — the CR-02 anti-pattern).

    Implementation target: trn_training_coach.agent.TrainingCoach.__call__()
    """
    coach, audit_writer = _make_coach(pass_threshold=0.80)
    state = _make_passing_state()

    with patch("trn_training_coach.agent.interrupt", return_value={"approved": True}):
        await coach(state=state)

    # Count TRAINING_SESSION writes
    session_calls = [
        call_args
        for call_args in audit_writer.write.call_args_list
        if call_args.kwargs.get("action_type") == ActionType.TRAINING_SESSION
    ]
    assert len(session_calls) == 1, (
        f"Expected exactly 1 TRAINING_SESSION write, got {len(session_calls)}. "
        f"W4/CR-02: TRAINING_SESSION must be written AFTER interrupt() returns "
        f"(not before, which would cause double-write on LangGraph replay). "
        f"All write calls: {audit_writer.write.call_args_list}"
    )

    # Total writes = 2 (TRAINING_SIGNOFF + TRAINING_SESSION)
    total_writes = audit_writer.write.call_count
    assert total_writes == 2, (
        f"Expected 2 total audit writes for a passing session "
        f"(1 TRAINING_SESSION + 1 TRAINING_SIGNOFF), got {total_writes}. "
        f"All write calls: {audit_writer.write.call_args_list}"
    )


@pytest.mark.asyncio
async def test_no_audit_write_before_interrupt_on_first_run_passing_session() -> None:
    """On first execution of passing session (before interrupt): 0 audit rows written.

    CR-02: audit write must not fire before interrupt() returns on first execution.
    Given a passing session, on first run (GraphInterrupt raised), write count == 0.

    Implementation target: trn_training_coach.agent.TrainingCoach.__call__()
    """
    coach, audit_writer = _make_coach(pass_threshold=0.80)
    state = _make_passing_state()

    # Simulate first execution: interrupt() raises GraphInterrupt (LangGraph first-run)
    def _interrupt_first_run(value: Any) -> Any:
        raise GraphInterrupt(value)

    with patch("trn_training_coach.agent.interrupt", side_effect=_interrupt_first_run):
        with pytest.raises(GraphInterrupt):
            await coach(state=state)

    # On first run, NO writes should have fired
    assert audit_writer.write.call_count == 0, (
        f"CR-02 FAIL: audit_writer.write was called "
        f"{audit_writer.write.call_count} time(s) before interrupt() returned. "
        f"All writes must happen AFTER interrupt() returns (on resume). "
        f"Write calls: {audit_writer.write.call_args_list}"
    )


@pytest.mark.asyncio
async def test_training_signoff_has_approval_id_none() -> None:
    """TRAINING_SIGNOFF audit row uses approval_id=None (CR-03 fix).

    CR-03 pattern (Phase 7): approval_id must be None for pending HITL rows.
    The TRAINING_SIGNOFF row must never fabricate a UUID at write time.

    Implementation target: trn_training_coach.agent.TrainingCoach.__call__()
    """
    coach, audit_writer = _make_coach(pass_threshold=0.80)
    state = _make_passing_state()

    with patch("trn_training_coach.agent.interrupt", return_value={"approved": True}):
        await coach(state=state)

    # Find the TRAINING_SIGNOFF write call
    signoff_calls = [
        call_args
        for call_args in audit_writer.write.call_args_list
        if call_args.kwargs.get("action_type") == ActionType.TRAINING_SIGNOFF
    ]
    assert len(signoff_calls) == 1, "Expected 1 TRAINING_SIGNOFF call"

    approval_id = signoff_calls[0].kwargs.get("approval_id")
    assert approval_id is None, (
        f"CR-03 FAIL: TRAINING_SIGNOFF row has approval_id={approval_id!r}. "
        f"approval_id must be None for pending HITL rows — never fabricate a UUID "
        f"at write time (CR-03 fix)."
    )


# ---------------------------------------------------------------------------
# Contract 2: Failing session — no interrupt, no TRAINING_SIGNOFF
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failing_session_no_interrupt_no_training_signoff() -> None:
    """On fail (score < threshold): no interrupt(), no TRAINING_SIGNOFF row.

    Given a failing quiz session (score < 0.80), TrainingCoach must NOT call
    interrupt() and must NOT write a TRAINING_SIGNOFF row.
    interrupt mock call_count == 0; write calls with TRAINING_SIGNOFF == 0.

    D-TC-03: interrupt/HITL only on pass, not on fail.

    Implementation target: trn_training_coach.agent.TrainingCoach.__call__()
    """
    coach, audit_writer = _make_coach(pass_threshold=0.80)
    state = _make_failing_state()

    interrupt_mock = MagicMock(side_effect=lambda v: (_ for _ in ()).throw(
        AssertionError("interrupt() must NOT be called on fail path")
    ))

    with patch("trn_training_coach.agent.interrupt", interrupt_mock):
        await coach(state=state)

    # No interrupt should have been called
    assert interrupt_mock.call_count == 0, (
        f"D-TC-03 FAIL: interrupt() was called {interrupt_mock.call_count} time(s) "
        f"on a failing session. HITL escalation is only for passing sessions."
    )

    # No TRAINING_SIGNOFF should have been written
    signoff_calls = [
        call_args
        for call_args in audit_writer.write.call_args_list
        if call_args.kwargs.get("action_type") == ActionType.TRAINING_SIGNOFF
    ]
    assert len(signoff_calls) == 0, (
        f"D-TC-03 FAIL: TRAINING_SIGNOFF was written {len(signoff_calls)} time(s) "
        f"on a failing session. No TRAINING_SIGNOFF row must be created on fail."
    )


@pytest.mark.asyncio
async def test_failing_session_produces_exactly_one_training_session_row() -> None:
    """On fail: exactly 1 TRAINING_SESSION row (session still recorded even on fail).

    Given a failing session, audit_writer.write must be called exactly once with
    action_type=TRAINING_SESSION (the session record). No TRAINING_SIGNOFF.
    Total write calls == 1.

    Implementation target: trn_training_coach.agent.TrainingCoach.__call__()
    """
    coach, audit_writer = _make_coach(pass_threshold=0.80)
    state = _make_failing_state()

    with patch("trn_training_coach.agent.interrupt", MagicMock()):
        await coach(state=state)

    # Exactly 1 TRAINING_SESSION write
    session_calls = [
        call_args
        for call_args in audit_writer.write.call_args_list
        if call_args.kwargs.get("action_type") == ActionType.TRAINING_SESSION
    ]
    assert len(session_calls) == 1, (
        f"Expected exactly 1 TRAINING_SESSION write on fail, got {len(session_calls)}. "
        f"All write calls: {audit_writer.write.call_args_list}"
    )

    # Total writes == 1 (TRAINING_SESSION only, no TRAINING_SIGNOFF)
    total_writes = audit_writer.write.call_count
    assert total_writes == 1, (
        f"Expected 1 total audit write for a failing session "
        f"(1 TRAINING_SESSION only), got {total_writes}. "
        f"All write calls: {audit_writer.write.call_args_list}"
    )
