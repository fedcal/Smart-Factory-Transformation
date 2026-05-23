"""Tests for EscalateToSupervisorTool (Plan 06-05 — D-OA-02 #4, Pitfall §3, §9).

Covers:
    - EscalateInput frozen + extra=forbid + min/max length constraints.
    - Sync `_run` raises NotImplementedError (PATTERNS Shared Pattern 7 async-only).
    - `_arun` constructs ProposedAction with ActionType.ESCALATION_REQUEST.
    - `_arun` invokes SafetyInterlockMiddleware.check (Pitfall §9 — uniform safety
      gate even for HITL escalations).
    - `_arun` calls `langgraph.types.interrupt` with structured payload + returns
      the resume decision dict to the LLM as ToolMessage content.
    - SafetyInterlockRejection is re-raised (no silent swallow).
    - No audit row is written before interrupt() (Pitfall §3 — audit happens
      after resume in calling node, not inside the tool itself).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from sft_agents.models.enums import ActionType, Tier
from sft_agents.policies.safety_interlock import SafetyInterlockRejection
from sft_agents.tools.hitl import EscalateInput, EscalateToSupervisorTool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool(
    *,
    safety: Any | None = None,
    audit_writer: Any | None = None,
    queue_writer: Any | None = None,
    nats: Any | None = None,
) -> EscalateToSupervisorTool:
    """Build the tool with permissive default mocks."""
    safety = safety or MagicMock(check=AsyncMock(return_value=None))
    audit_writer = audit_writer or MagicMock(write=AsyncMock(return_value=None))
    queue_writer = queue_writer or MagicMock(insert=AsyncMock(return_value=None))
    nats = nats or MagicMock()
    return EscalateToSupervisorTool(
        audit_writer=audit_writer,
        queue_writer=queue_writer,
        nats=nats,
        safety_middleware=safety,
    )


def _valid_args() -> dict[str, str]:
    return {
        "reason": "User asked to halt the production line — outside agent authority.",
        "suggested_action": "Stop line LOOM-01 then await supervisor authorization.",
        "evidence_summary": "Operator typed stop; SOP requires supervisor sign-off.",
    }


# ---------------------------------------------------------------------------
# EscalateInput schema
# ---------------------------------------------------------------------------


def test_args_schema_frozen_extra_forbid() -> None:
    """EscalateInput rejects extra fields (T-V6-injection mitigation)."""
    with pytest.raises(ValidationError):
        EscalateInput(**_valid_args(), unknown="leak")  # type: ignore[call-arg]


def test_args_schema_is_frozen() -> None:
    """EscalateInput instances are immutable."""
    inp = EscalateInput(**_valid_args())
    with pytest.raises(ValidationError):
        inp.reason = "mutated"  # type: ignore[misc]


def test_args_schema_field_constraints_min_length() -> None:
    """reason/suggested_action/evidence_summary all reject < 10 chars."""
    base = _valid_args()
    for field in ("reason", "suggested_action", "evidence_summary"):
        bad = dict(base)
        bad[field] = "short"
        with pytest.raises(ValidationError):
            EscalateInput(**bad)


def test_args_schema_field_constraints_max_length() -> None:
    """reason/suggested_action/evidence_summary all reject > 2000 chars."""
    base = _valid_args()
    for field in ("reason", "suggested_action", "evidence_summary"):
        bad = dict(base)
        bad[field] = "x" * 2001
        with pytest.raises(ValidationError):
            EscalateInput(**bad)


# ---------------------------------------------------------------------------
# _run sync disabled
# ---------------------------------------------------------------------------


def test_sync_run_raises() -> None:
    """Sync `_run` must raise NotImplementedError with 'async-only' hint."""
    tool = _make_tool()
    with pytest.raises(NotImplementedError, match="async-only"):
        tool._run(**_valid_args())


# ---------------------------------------------------------------------------
# _arun behaviour
# ---------------------------------------------------------------------------


async def test_arun_calls_safety_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Safety middleware is invoked once with ActionType.ESCALATION_REQUEST."""
    safety = MagicMock(check=AsyncMock(return_value=None))
    tool = _make_tool(safety=safety)

    # Stub interrupt() so the call does not actually pause anything.
    monkeypatch.setattr(
        "sft_agents.tools.hitl.interrupt",
        lambda payload: {"decision": "approved"},
    )

    await tool._arun(**_valid_args())

    assert safety.check.await_count == 1
    call_args = safety.check.await_args
    action = call_args.args[0] if call_args.args else call_args.kwargs["action"]
    assert action.action_type == ActionType.ESCALATION_REQUEST


async def test_arun_invokes_interrupt_with_structured_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """interrupt() receives {tool, tier, payload} dict (Pitfall §9 audit shape)."""
    captured: dict[str, Any] = {}

    def _capturing_interrupt(payload: dict[str, Any]) -> dict[str, Any]:
        captured.update(payload)
        return {"decision": "approved", "approver": "supervisor-01"}

    monkeypatch.setattr("sft_agents.tools.hitl.interrupt", _capturing_interrupt)

    tool = _make_tool()
    await tool._arun(**_valid_args())

    assert captured["tool"] == "escalate_to_supervisor"
    assert captured["tier"] == Tier.SUPERVISOR.value
    assert "payload" in captured
    payload = captured["payload"]
    # payload is action.model_dump(mode="json") — must contain ESCALATION_REQUEST
    assert payload["action_type"] == ActionType.ESCALATION_REQUEST.value
    # And the three input fields are echoed under args.
    args = payload["args"]
    assert set(args.keys()) == {"reason", "suggested_action", "evidence_summary"}


async def test_arun_returns_decision_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dict returned by interrupt() is propagated verbatim to the LLM."""
    expected = {"decision": "approved", "approver": "supervisor-01"}
    monkeypatch.setattr("sft_agents.tools.hitl.interrupt", lambda _p: expected)

    tool = _make_tool()
    out = await tool._arun(**_valid_args())

    assert out == expected


async def test_safety_rejection_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """If SafetyInterlock rejects the escalation, the exception is re-raised."""

    async def _reject(*args: Any, **kwargs: Any) -> None:
        raise SafetyInterlockRejection(
            action_id="x", action_type="ESCALATION_REQUEST", reason="forbidden"
        )

    safety = MagicMock(check=_reject)
    tool = _make_tool(safety=safety)

    # If interrupt is ever called we want to know — record it.
    interrupt_called = {"flag": False}

    def _interrupt(_p: dict[str, Any]) -> dict[str, Any]:
        interrupt_called["flag"] = True
        return {}

    monkeypatch.setattr("sft_agents.tools.hitl.interrupt", _interrupt)

    with pytest.raises(SafetyInterlockRejection):
        await tool._arun(**_valid_args())

    assert interrupt_called["flag"] is False


async def test_no_audit_write_before_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pitfall §3 — the tool must not write audit before interrupt().

    The HITL approval node owns the audit dual-write after resume; the tool's
    job is purely to construct the ProposedAction, run the safety check and
    hand off to interrupt(). Writing audit twice on resume would corrupt the
    forensic trail.
    """
    audit_writer = MagicMock(write=AsyncMock(return_value=None))
    queue_writer = MagicMock(insert=AsyncMock(return_value=None))

    # Stub interrupt() to raise immediately so we observe the world right at
    # the interrupt() boundary (no resume in this test).
    def _interrupt(_p: dict[str, Any]) -> dict[str, Any]:
        # At this point: audit/queue MUST NOT have been called yet.
        assert audit_writer.write.await_count == 0
        assert queue_writer.insert.await_count == 0
        return {"decision": "approved"}

    monkeypatch.setattr("sft_agents.tools.hitl.interrupt", _interrupt)

    tool = _make_tool(audit_writer=audit_writer, queue_writer=queue_writer)
    await tool._arun(**_valid_args())

    # Post-call sanity: still zero.
    assert audit_writer.write.await_count == 0
    assert queue_writer.insert.await_count == 0


# ---------------------------------------------------------------------------
# Tool metadata
# ---------------------------------------------------------------------------


def test_tool_name_and_description() -> None:
    """LLM-facing metadata is stable (LangChain BaseTool contract)."""
    tool = _make_tool()
    assert tool.name == "escalate_to_supervisor"
    assert "supervisor" in tool.description.lower()
    assert tool.args_schema is EscalateInput
