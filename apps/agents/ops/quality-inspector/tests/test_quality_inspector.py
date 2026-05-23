"""Tests for the QualityInspector agent — severity -> HITL routing (D-QI-03).

Severity mapping (defaults, overridable by failure_modes.yaml hitl_tier):
    minor    -> auto-log (no HITL, write Decision.AUTO audit row).
    major    -> human_approval_node tier=Tier.SUPERVISOR.
    critical -> SafetyInterlockMiddleware.check + human_approval_node
                tier=Tier.MANAGER.

The dye_lot_id MUST be propagated into the ProposedAction.args / audit row.
The grader is monkey-patched so tests do not depend on the LLM.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sft_agents.models.enums import ActionType, Tier
from sft_domain.ops.quality import QualityEvent, QualityVerdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    defect_type: str = "slub",
    defect_length_inches: float = 1.5,
    full_width: bool = False,
    dye_lot_id: str = "DL-LOOM-01-20260523-a3",
) -> QualityEvent:
    return QualityEvent(
        event_id=uuid4(),
        asset_id="LOOM-01",
        dye_lot_id=dye_lot_id,
        defect_type=defect_type,  # type: ignore[arg-type]
        defect_length_inches=defect_length_inches,
        full_width=full_width,
        position_meters=12.5,
        timestamp=datetime.now(timezone.utc),
        source="simulator",
    )


def _make_verdict(severity: str, score: int = 2) -> QualityVerdict:
    return QualityVerdict(
        score=score,
        severity=severity,  # type: ignore[arg-type]
        rationale_md=f"Test verdict {severity}.",
        citations=[],
    )


def _make_inspector(monkeypatch: pytest.MonkeyPatch, verdict: QualityVerdict) -> Any:
    """Build a QualityInspector with all collaborators mocked + grader stubbed."""
    from ops_quality_inspector import agent as agent_mod

    rag_pipeline = MagicMock()
    rag_pipeline.search = AsyncMock(return_value=[])
    audit_writer = MagicMock()
    audit_writer.write = AsyncMock(return_value=None)
    queue_writer = MagicMock()
    nats_publisher = MagicMock()
    safety = MagicMock()
    safety.check = AsyncMock(return_value=None)
    pool = MagicMock()

    inspector = agent_mod.QualityInspector(
        rag_pipeline=rag_pipeline,
        audit_writer=audit_writer,
        queue_writer=queue_writer,
        nats_publisher=nats_publisher,
        safety_middleware=safety,
        pool=pool,
        agent_id="quality-inspector",
        cluster="ops",
    )

    async def _stub_grader(event, *, rag_pipeline, model=None, user_roles=None):
        return verdict

    monkeypatch.setattr(agent_mod, "grade_quality_event", _stub_grader)

    return inspector, audit_writer, safety


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_minor_severity_auto_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """minor -> AuditWriter.write called once with Decision.AUTO; no interrupt."""
    from sft_agents.models.enums import Decision

    insp, audit, safety = _make_inspector(monkeypatch, _make_verdict("minor", 1))

    # Patch human_approval_node so we can assert it was NOT called.
    from ops_quality_inspector import agent as agent_mod

    approval_mock = AsyncMock(return_value={})
    monkeypatch.setattr(agent_mod, "human_approval_node", approval_mock)

    response = await insp.handle_event(_make_event(defect_type="slub"))

    assert response.hitl_routed_to == "auto-log"
    audit.write.assert_awaited_once()
    record = audit.write.await_args.args[0]
    assert record.decision == Decision.AUTO
    assert record.approval_id is None
    assert record.action_type == ActionType.QUALITY_VERDICT.value
    safety.check.assert_not_called()
    approval_mock.assert_not_called()


@pytest.mark.asyncio
async def test_major_severity_routes_supervisor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """major -> human_approval_node(tier=Tier.SUPERVISOR); no safety check."""
    insp, _audit, safety = _make_inspector(monkeypatch, _make_verdict("major", 3))

    from ops_quality_inspector import agent as agent_mod

    approval_mock = AsyncMock(return_value={})
    monkeypatch.setattr(agent_mod, "human_approval_node", approval_mock)

    response = await insp.handle_event(_make_event(defect_type="shade_deviation"))

    assert response.hitl_routed_to == "supervisor"
    approval_mock.assert_awaited_once()
    call_kwargs = approval_mock.await_args.kwargs
    assert call_kwargs["tier"] == Tier.SUPERVISOR
    safety.check.assert_not_called()


@pytest.mark.asyncio
async def test_critical_severity_routes_manager_with_safety(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """critical -> SafetyInterlockMiddleware.check + human_approval_node MANAGER."""
    insp, _audit, safety = _make_inspector(
        monkeypatch, _make_verdict("critical", 4)
    )

    from ops_quality_inspector import agent as agent_mod

    approval_mock = AsyncMock(return_value={})
    monkeypatch.setattr(agent_mod, "human_approval_node", approval_mock)

    response = await insp.handle_event(
        _make_event(defect_type="broken_end", full_width=True)
    )

    assert response.hitl_routed_to == "manager+safety"
    safety.check.assert_awaited_once()
    approval_mock.assert_awaited_once()
    assert approval_mock.await_args.kwargs["tier"] == Tier.MANAGER


@pytest.mark.asyncio
async def test_severity_fallback_treated_as_major(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Grader returns fallback verdict (severity=major) -> supervisor tier."""
    insp, _audit, _safety = _make_inspector(
        monkeypatch, _make_verdict("major", 4)
    )

    from ops_quality_inspector import agent as agent_mod

    approval_mock = AsyncMock(return_value={})
    monkeypatch.setattr(agent_mod, "human_approval_node", approval_mock)

    response = await insp.handle_event(_make_event(defect_type="slub"))

    assert response.hitl_routed_to == "supervisor"
    assert approval_mock.await_args.kwargs["tier"] == Tier.SUPERVISOR


@pytest.mark.asyncio
async def test_dye_lot_id_propagated_to_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dye_lot_id in event -> appears in audit-row payload (minor branch)."""
    insp, audit, _safety = _make_inspector(
        monkeypatch, _make_verdict("minor", 1)
    )

    from ops_quality_inspector import agent as agent_mod

    approval_mock = AsyncMock(return_value={})
    monkeypatch.setattr(agent_mod, "human_approval_node", approval_mock)

    event = _make_event(
        defect_type="slub", dye_lot_id="DL-LOOM-01-20260523-a3"
    )
    await insp.handle_event(event)

    record = audit.write.await_args.args[0]
    # dye_lot_id is stashed in the synthetic tool_call args - flatten and search.
    tool_calls = record.evidence_panel.tool_calls
    flat_args = [tc.args for tc in tool_calls]
    flat_text = str(flat_args)
    assert "DL-LOOM-01-20260523-a3" in flat_text


@pytest.mark.asyncio
async def test_hitl_tier_from_failure_modes_yaml_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """failure_modes.yaml hitl_tier='manager+safety' for defect overrides default."""
    insp, _audit, safety = _make_inspector(
        monkeypatch, _make_verdict("major", 3)
    )

    from ops_quality_inspector import agent as agent_mod

    approval_mock = AsyncMock(return_value={})
    monkeypatch.setattr(agent_mod, "human_approval_node", approval_mock)

    # 'unlevel_dyeing' has hitl_tier='manager+safety' in failure_modes.yaml.
    # Even though grader returns severity=major (default supervisor), the
    # YAML override pushes to MANAGER+safety.
    response = await insp.handle_event(_make_event(defect_type="unlevel_dyeing"))

    assert response.hitl_routed_to == "manager+safety"
    safety.check.assert_awaited_once()
    assert approval_mock.await_args.kwargs["tier"] == Tier.MANAGER
