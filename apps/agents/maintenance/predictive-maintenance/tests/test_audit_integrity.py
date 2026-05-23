"""Regression tests for PredictiveMaintenance audit-integrity defects (Plan 07-15).

CR-03: HITL_SUPERVISOR audit rows must carry ``approval_id=None`` (pending escalation).
       Previously, ``_write_audit`` fabricated a random uuid4() labeled as a
       "placeholder UUID ... during testing" that ran in production. Downstream
       JOINs on ``audit.actions.approval_id`` → ``hitl.approvals`` found no match,
       making forensic audit tools falsely conclude escalations were approved.

CR-04: ``state["asset_id"]`` raised a bare ``KeyError`` that propagated to the API
       gateway, leaking the internal field name in 500 response bodies. Must raise
       a structured ``ValueError`` with a controlled human-readable message instead.

These tests are authored RED (fail against current code) and must turn GREEN after the
fixes in Task 2 land (agent.py + AuditRecord validator update).
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
from datetime import UTC, datetime


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _loom_asset(asset_id: str = "LOOM-01"):
    """Build a minimal loom Asset for use in agent construction."""
    from sft_assets.models import Asset, AssetFamily, SemanticType, Tag

    return Asset(
        asset_id=asset_id,
        asset_family=AssetFamily.LOOM,
        line_id="weaving-line-1",
        opcua_namespace=f"urn:mantis:loom:{asset_id}",
        tags=(
            Tag(
                tag_id="warp_tension",
                unit="N",
                sample_rate_hz=10.0,
                semantic_type=SemanticType.TENSION,
            ),
        ),
        status="active",
    )


def _sensor_window_df(asset_id: str = "LOOM-01", rows: int = 60) -> pd.DataFrame:
    """Build a synthetic sensor window matching QueryTimescaleTool output shape."""
    now = datetime.now(UTC)
    records = [
        {
            "asset_id": asset_id,
            "sensor_id": "warp_tension",
            "timestamp": now,
            "value": 0.5,
            "unit": "N",
        }
        for _ in range(rows)
    ]
    return pd.DataFrame(records)


def _low_health_model():
    """Return a mock sklearn Pipeline that predicts 0 RUL (health_index=0.0 < 0.3)."""
    from sklearn.pipeline import Pipeline

    mock_model = MagicMock(spec=Pipeline)
    mock_model.predict.return_value = [0.0]  # rul_cycles=0 → health_index=0.0
    return mock_model


# ---------------------------------------------------------------------------
# CR-03 regression: HITL audit row must carry null approval_id (not fabricated UUID)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hitl_audit_row_has_null_approval_id(
    mock_audit_writer: AsyncMock,
    mock_query_tool: AsyncMock,
) -> None:
    """CR-03 regression: HITL_SUPERVISOR audit row must have approval_id=None.

    The real approval_id is assigned only after a human supervisor approves in the
    HITL system; the initial escalation row represents a *pending* approval, not an
    approved one. Fabricating a random uuid4() breaks JOIN integrity with hitl.approvals.

    Against current code: approval_id is a fabricated uuid4() → assertion fails.
    After fix: approval_id is None (AuditRecord validator updated to allow pending state).
    """
    from mnt_predictive_maintenance.agent import PredictiveMaintenance
    from sft_agents.models.enums import Decision

    asset = _loom_asset("LOOM-01")
    mock_query_tool._arun.return_value = _sensor_window_df("LOOM-01", rows=60)

    mock_escalate = AsyncMock()
    mock_escalate._arun = AsyncMock(return_value=None)

    # Capture the written AuditRecord
    written_records: list = []

    async def capture_write(record) -> None:
        written_records.append(record)

    mock_audit_writer.write.side_effect = capture_write

    agent = PredictiveMaintenance(
        pool=MagicMock(),
        audit_writer=mock_audit_writer,
        asset_registry=[asset],
        model=_low_health_model(),  # forces health_index=0.0 < 0.3 → HITL path
        query_tool=mock_query_tool,
        escalate_tool=mock_escalate,
    )

    await agent({"asset_id": "LOOM-01", "triggered_by_action_id": "ad-action-uuid-1"})

    assert len(written_records) == 1, "Expected exactly one audit row written"
    record = written_records[0]

    # The decision must be HITL_SUPERVISOR (low health_index < 0.3)
    assert record.decision is Decision.HITL_SUPERVISOR, (
        f"Expected HITL_SUPERVISOR decision, got {record.decision!r}"
    )

    # CR-03: approval_id MUST be None for pending escalation — not a fabricated UUID
    assert record.approval_id is None, (
        f"CR-03: approval_id must be None for pending HITL escalation, "
        f"got {record.approval_id!r} (fabricated UUID breaks JOIN with hitl.approvals)"
    )

    # Motivation must describe the PENDING state (not "Supervisor approved ...")
    assert record.motivation is not None, "motivation must be set for HITL_SUPERVISOR"
    motivation_lower = record.motivation.lower()
    assert "approv" not in motivation_lower.replace("approval required", ""), (
        "motivation must NOT say 'approved' — escalation is still pending. "
        f"Got: {record.motivation!r}"
    )


# ---------------------------------------------------------------------------
# CR-04 regression: missing asset_id must raise ValueError, not KeyError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_asset_id_raises_valueerror_not_keyerror(
    mock_audit_writer: AsyncMock,
    mock_query_tool: AsyncMock,
) -> None:
    """CR-04 regression: missing asset_id must raise ValueError with controlled message.

    ``state["asset_id"]`` raises a bare ``KeyError('asset_id')`` that propagates
    to the API gateway as a 500 with ``str(KeyError("asset_id")) == "'asset_id'"``
    in the response body — leaking the internal field name.

    After fix: ``state.get("asset_id")`` + explicit ``ValueError`` guard raises
    ``ValueError("PredictiveMaintenance requires 'asset_id' in state")`` (a controlled
    message that cannot be mistaken for a key-leak).

    Against current code: bare ``KeyError`` is raised → ``pytest.raises(ValueError)`` fails.
    After fix: ``ValueError`` raised with a non-leaky message → test passes.
    """
    from mnt_predictive_maintenance.agent import PredictiveMaintenance

    asset = _loom_asset("LOOM-01")
    mock_query_tool._arun.return_value = _sensor_window_df("LOOM-01", rows=60)

    agent = PredictiveMaintenance(
        pool=MagicMock(),
        audit_writer=mock_audit_writer,
        asset_registry=[asset],
        query_tool=mock_query_tool,
        escalate_tool=AsyncMock(),
    )

    # State dict explicitly omits 'asset_id'
    state_without_asset_id = {"triggered_by_action_id": "ad-action-uuid-1"}

    with pytest.raises(ValueError) as exc_info:
        await agent(state_without_asset_id)

    exc_str = str(exc_info.value)

    # The error message must NOT be the bare repr that KeyError produces
    # str(KeyError("asset_id")) == "'asset_id'"
    assert exc_str != "'asset_id'", (
        "CR-04: error is a bare KeyError repr — leaks internal field name. "
        "Must be an explicit ValueError with a controlled message."
    )

    # The controlled message should mention the requirement
    assert "asset_id" in exc_str.lower(), (
        f"ValueError message should mention 'asset_id', got: {exc_str!r}"
    )
    assert "requires" in exc_str.lower() or "missing" in exc_str.lower(), (
        f"ValueError message should describe the requirement, got: {exc_str!r}"
    )
