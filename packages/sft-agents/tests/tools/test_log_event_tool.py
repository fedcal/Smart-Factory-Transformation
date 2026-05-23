"""Tests for LogEventTool (Plan 06-05 — D-OA-02 #5, observability-only).

Covers:
    - LogEventInput frozen + extra=forbid + event_type Literal whitelist.
    - Sync `_run` raises NotImplementedError (PATTERNS Shared Pattern 7).
    - `_arun` writes one AuditRecord with Decision.LOGGED + no HITL interrupt.
    - Return shape is `{"logged": True, "action_id": <uuid str>}`.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from sft_agents.models.audit import AuditRecord
from sft_agents.models.enums import ActionType, Decision
from sft_agents.tools.audit import LogEventInput, LogEventTool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool(*, audit_writer: Any | None = None) -> LogEventTool:
    audit_writer = audit_writer or MagicMock(write=AsyncMock(return_value=None))
    return LogEventTool(audit_writer=audit_writer)


def _valid_args() -> dict[str, Any]:
    return {
        "event_type": "operator_question",
        "summary": "Operator asked: 'why is shade off on lot DL-LOOM-01-...?'",
        "payload": {"lot_id": "DL-LOOM-01-20260518-ab12"},
    }


def _call_kwargs() -> dict[str, Any]:
    """Per-call context the calling node injects (agent_id / thread_id / cluster)."""
    return {
        "agent_id": "operator-assistant",
        "thread_id": "ops.operator-assistant.session-xyz",
        "cluster": "ops",
    }


# ---------------------------------------------------------------------------
# LogEventInput schema
# ---------------------------------------------------------------------------


def test_args_schema_frozen_extra_forbid() -> None:
    """LogEventInput rejects unknown fields (T-V6-injection mitigation)."""
    with pytest.raises(ValidationError):
        LogEventInput(**_valid_args(), unknown="leak")  # type: ignore[call-arg]


def test_args_schema_is_frozen() -> None:
    """LogEventInput instances are immutable."""
    inp = LogEventInput(**_valid_args())
    with pytest.raises(ValidationError):
        inp.summary = "mutated"  # type: ignore[misc]


def test_input_event_type_literal_accepts_starter_set() -> None:
    """All 4 starter event_type literals are accepted."""
    base = _valid_args()
    for et in (
        "shift_handover_input",
        "operator_question",
        "operator_note",
        "kpi_observation",
    ):
        bad = dict(base)
        bad["event_type"] = et
        # Must not raise.
        LogEventInput(**bad)


def test_input_event_type_literal_rejects_other() -> None:
    """event_type outside whitelist is rejected by Pydantic Literal."""
    bad = dict(_valid_args())
    bad["event_type"] = "rogue_event"
    with pytest.raises(ValidationError):
        LogEventInput(**bad)


def test_input_payload_defaults_to_empty_dict() -> None:
    """payload is optional — defaults to {} (Field(default_factory=dict))."""
    inp = LogEventInput(
        event_type="operator_note",
        summary="some operator note about LOOM-01",
    )
    assert inp.payload == {}


def test_input_summary_constraints() -> None:
    """summary must be 1..2000 chars."""
    base = _valid_args()
    bad_empty = dict(base, summary="")
    with pytest.raises(ValidationError):
        LogEventInput(**bad_empty)
    bad_long = dict(base, summary="x" * 2001)
    with pytest.raises(ValidationError):
        LogEventInput(**bad_long)


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


async def test_arun_writes_audit_logged() -> None:
    """One AuditRecord written with Decision.LOGGED + ActionType.GOVERNOR_ALERT."""
    audit_writer = MagicMock(write=AsyncMock(return_value=None))
    tool = _make_tool(audit_writer=audit_writer)

    out = await tool._arun(**_valid_args(), **_call_kwargs())

    assert audit_writer.write.await_count == 1
    record = audit_writer.write.await_args.args[0]
    assert isinstance(record, AuditRecord)
    assert record.decision == Decision.LOGGED
    # GOVERNOR_ALERT is the placeholder action_type for observability-only rows
    # (later phases may add a dedicated OPERATOR_LOG enum value).
    assert record.action_type == ActionType.GOVERNOR_ALERT.value
    assert record.agent_id == "operator-assistant"
    assert record.thread_id == "ops.operator-assistant.session-xyz"
    assert record.cluster == "ops"
    assert out == {"logged": True, "action_id": str(record.action_id)}
    # action_id is a UUID
    UUID(out["action_id"])


async def test_arun_no_hitl_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    """LogEvent is observability-only — must not call interrupt() nor queue."""
    interrupt_called = {"flag": False}

    def _interrupt(_p: dict[str, Any]) -> dict[str, Any]:
        interrupt_called["flag"] = True
        return {}

    # Patch LangGraph's interrupt at the source — if anything imports + calls
    # it from inside the tool the flag flips.
    monkeypatch.setattr("langgraph.types.interrupt", _interrupt, raising=False)

    tool = _make_tool()
    await tool._arun(**_valid_args(), **_call_kwargs())

    assert interrupt_called["flag"] is False


async def test_arun_embeds_event_type_and_payload_in_audit() -> None:
    """The audit row's evidence_panel carries the event_type + summary + payload."""
    audit_writer = MagicMock(write=AsyncMock(return_value=None))
    tool = _make_tool(audit_writer=audit_writer)
    await tool._arun(**_valid_args(), **_call_kwargs())

    record = audit_writer.write.await_args.args[0]
    # The payload + event_type + summary should be reachable from the audit
    # (we encode them inside evidence_panel.extras or similar — implementation
    # choice; the test only asserts they are *somewhere* in the record.)
    blob = record.model_dump_json()
    assert "operator_question" in blob
    assert "DL-LOOM-01-20260518-ab12" in blob


# ---------------------------------------------------------------------------
# Tool metadata
# ---------------------------------------------------------------------------


def test_tool_name_and_description() -> None:
    """LLM-facing metadata is stable (LangChain BaseTool contract)."""
    tool = _make_tool()
    assert tool.name == "log_event"
    assert "log" in tool.description.lower()
    assert tool.args_schema is LogEventInput
