"""Tests for ``RequestHelpTool`` — MaintenanceCoach wrapper around
``EscalateToSupervisorTool`` (Plan 07-04, D-MC-02, 07-PATTERNS Section 2).

Covers:
    - ``RequestHelpInput`` frozen + extra=forbid + field constraints
      (T-V7-injection-prompt-stuffing, T-V7-intervention-id-overflow).
    - Sync ``_run`` raises NotImplementedError (Shared Pattern B — async-only).
    - ``_arun`` delegates exactly once to the underlying
      ``EscalateToSupervisorTool._arun`` with composed
      ``evidence_summary`` / ``suggested_action`` (D-MC-02 wrapping pattern).
    - Class docstring documents the audit marker ``escalation_trigger`` and
      the D-MC-02 reference (Pitfall §3 inheritance — no audit before
      interrupt; calling node owns the audit dual-write).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from sft_agents.tools.hitl import (
    EscalateToSupervisorTool,
    RequestHelpInput,
    RequestHelpTool,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_args() -> dict[str, Any]:
    return {
        "reason": "Technician stuck on torque calibration — needs supervisor sign-off.",
        "context": "Step 3 of 7 — torque wrench reads 42 Nm, SOP requires 38 Nm ± 1.",
        "intervention_id": "intv-2026-05-001",
        "current_step": 3,
    }


def _make_mock_escalate() -> AsyncMock:
    """Return an AsyncMock standing in for EscalateToSupervisorTool._arun."""
    return AsyncMock(return_value={"decision": "approved", "approver": "supervisor-01"})


def _make_tool(*, escalate_mock: AsyncMock | None = None) -> RequestHelpTool:
    """Build RequestHelpTool with a fully mocked underlying EscalateToSupervisorTool."""
    escalate_mock = escalate_mock or _make_mock_escalate()
    safety = MagicMock(check=AsyncMock(return_value=None))
    audit_writer = MagicMock(write=AsyncMock(return_value=None))
    queue_writer = MagicMock(insert=AsyncMock(return_value=None))
    nats = MagicMock()
    escalate = EscalateToSupervisorTool(
        audit_writer=audit_writer,
        queue_writer=queue_writer,
        nats=nats,
        safety_middleware=safety,
    )
    # Replace the `_arun` method on the instance with our mock so we can
    # capture call args without exercising langgraph.interrupt().
    escalate._arun = escalate_mock  # type: ignore[method-assign]
    tool = RequestHelpTool(escalate=escalate)
    return tool


# ---------------------------------------------------------------------------
# RequestHelpInput schema
# ---------------------------------------------------------------------------


def test_input_schema_frozen() -> None:
    """RequestHelpInput instances are immutable."""
    inp = RequestHelpInput(**_valid_args())
    with pytest.raises(ValidationError):
        inp.reason = "mutated"  # type: ignore[misc]


def test_input_schema_extra_forbid() -> None:
    """RequestHelpInput rejects extra fields (T-V7-injection mitigation)."""
    with pytest.raises(ValidationError):
        RequestHelpInput(**_valid_args(), unknown_field="leak")  # type: ignore[call-arg]


def test_input_schema_reason_min_length() -> None:
    """reason < 10 chars rejected."""
    bad = dict(_valid_args())
    bad["reason"] = "short"
    with pytest.raises(ValidationError):
        RequestHelpInput(**bad)


def test_input_schema_reason_max_length() -> None:
    """reason > 2000 chars rejected."""
    bad = dict(_valid_args())
    bad["reason"] = "x" * 2001
    with pytest.raises(ValidationError):
        RequestHelpInput(**bad)


def test_input_schema_context_min_length() -> None:
    """context < 10 chars rejected."""
    bad = dict(_valid_args())
    bad["context"] = "tiny"
    with pytest.raises(ValidationError):
        RequestHelpInput(**bad)


def test_input_schema_context_max_length() -> None:
    """context > 2000 chars rejected."""
    bad = dict(_valid_args())
    bad["context"] = "y" * 2001
    with pytest.raises(ValidationError):
        RequestHelpInput(**bad)


def test_input_schema_intervention_id_max_length() -> None:
    """intervention_id > 64 chars rejected (T-V7-intervention-id-overflow)."""
    bad = dict(_valid_args())
    bad["intervention_id"] = "x" * 65
    with pytest.raises(ValidationError):
        RequestHelpInput(**bad)


def test_input_schema_intervention_id_min_length() -> None:
    """intervention_id empty rejected."""
    bad = dict(_valid_args())
    bad["intervention_id"] = ""
    with pytest.raises(ValidationError):
        RequestHelpInput(**bad)


def test_input_schema_current_step_below_zero() -> None:
    """current_step < 0 rejected."""
    bad = dict(_valid_args())
    bad["current_step"] = -1
    with pytest.raises(ValidationError):
        RequestHelpInput(**bad)


def test_input_schema_current_step_above_max() -> None:
    """current_step > 100 rejected."""
    bad = dict(_valid_args())
    bad["current_step"] = 101
    with pytest.raises(ValidationError):
        RequestHelpInput(**bad)


# ---------------------------------------------------------------------------
# Tool metadata
# ---------------------------------------------------------------------------


def test_tool_name_and_args_schema() -> None:
    """LLM-facing metadata is stable (LangChain BaseTool contract)."""
    tool = _make_tool()
    assert tool.name == "request_help"
    assert tool.args_schema is RequestHelpInput


def test_tool_docstring_documents_audit_marker_and_d_mc_02() -> None:
    """Pitfall §3 + D-MC-02 audit marker documented in code (07-PATTERNS Section 2)."""
    doc = RequestHelpTool.__doc__ or ""
    assert "escalation_trigger" in doc
    assert "D-MC-02" in doc


# ---------------------------------------------------------------------------
# _run sync disabled (Shared Pattern B)
# ---------------------------------------------------------------------------


def test_sync_run_raises_not_implemented() -> None:
    """Sync `_run` must raise NotImplementedError with 'async-only' hint."""
    tool = _make_tool()
    with pytest.raises(NotImplementedError, match="async-only"):
        tool._run(**_valid_args())


# ---------------------------------------------------------------------------
# _arun delegation contract (D-MC-02 wrapping pattern)
# ---------------------------------------------------------------------------


async def test_arun_delegates_to_escalate_exactly_once() -> None:
    """The wrapping tool calls EscalateToSupervisorTool._arun exactly once."""
    escalate_mock = _make_mock_escalate()
    tool = _make_tool(escalate_mock=escalate_mock)

    await tool._arun(**_valid_args())

    assert escalate_mock.await_count == 1


async def test_arun_returns_escalate_decision() -> None:
    """The underlying escalate decision is propagated verbatim to the LLM."""
    expected = {"decision": "rejected", "approver": "supervisor-42"}
    escalate_mock = AsyncMock(return_value=expected)
    tool = _make_tool(escalate_mock=escalate_mock)

    out = await tool._arun(**_valid_args())

    assert out == expected


async def test_arun_composes_evidence_summary_with_intervention_metadata() -> None:
    """evidence_summary is formatted as 'intervention=<id> step=<n> context=<...>'."""
    escalate_mock = _make_mock_escalate()
    tool = _make_tool(escalate_mock=escalate_mock)
    args = _valid_args()

    await tool._arun(**args)

    call = escalate_mock.await_args
    assert call is not None
    forwarded = call.kwargs
    evidence = forwarded["evidence_summary"]
    assert evidence.startswith(
        f"intervention={args['intervention_id']} step={args['current_step']} context="
    )
    # Original context must appear in the evidence (within 1000 char cap).
    assert args["context"] in evidence


async def test_arun_composes_suggested_action_with_intervention_metadata() -> None:
    """suggested_action describes the review step (D-MC-02 wrapping pattern)."""
    escalate_mock = _make_mock_escalate()
    tool = _make_tool(escalate_mock=escalate_mock)
    args = _valid_args()

    await tool._arun(**args)

    call = escalate_mock.await_args
    forwarded = call.kwargs
    suggested = forwarded["suggested_action"]
    assert suggested.startswith(
        f"Supervisor: review step {args['current_step']} of intervention {args['intervention_id']}"
    )


async def test_arun_passes_reason_through_unchanged() -> None:
    """The technician's reason is forwarded verbatim to the escalation tool."""
    escalate_mock = _make_mock_escalate()
    tool = _make_tool(escalate_mock=escalate_mock)
    args = _valid_args()

    await tool._arun(**args)

    call = escalate_mock.await_args
    assert call.kwargs["reason"] == args["reason"]


async def test_arun_truncates_long_context_to_1000_chars_in_evidence() -> None:
    """Very long context is truncated to 1000 chars in the evidence_summary
    (defense-in-depth on top of Field max_length=2000)."""
    escalate_mock = _make_mock_escalate()
    tool = _make_tool(escalate_mock=escalate_mock)
    args = dict(_valid_args())
    args["context"] = "Z" * 1500  # within field cap but above 1000 char clip

    await tool._arun(**args)

    call = escalate_mock.await_args
    evidence = call.kwargs["evidence_summary"]
    # The truncated context section must be exactly 1000 'Z' chars.
    z_run = "Z" * 1000
    assert z_run in evidence
    # And the next 100 chars (still all Z) MUST NOT appear (proves truncation).
    z_run_overlong = "Z" * 1100
    assert z_run_overlong not in evidence
