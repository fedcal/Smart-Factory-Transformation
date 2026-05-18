"""SafetyInterlockMiddleware whitelist enforcement (HITL-03, D-58, T-04-Whitelist-Bypass).

Tests use the on-disk ``policies/safety-interlock.yaml`` so they double as
yaml-load smoke tests (yaml.safe_load + glob translation).
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

pytest.importorskip(
    "sft_agents.policies.safety_interlock",
    reason="Plan 04-06 Task 03 implements SafetyInterlockMiddleware",
)

from sft_agents.models.budget import BudgetSnapshot  # noqa: E402
from sft_agents.models.enums import ActionType, Decision  # noqa: E402
from sft_agents.models.evidence import EvidencePanel, TokenUsage  # noqa: E402
from sft_agents.models.proposed_action import ProposedAction  # noqa: E402
from sft_agents.policies.safety_interlock import (  # noqa: E402
    SafetyInterlockMiddleware,
    SafetyInterlockRejection,
)


def _make_evidence() -> EvidencePanel:
    return EvidencePanel(
        input_summary="x",
        tool_calls=[],
        rag_citations=[],
        confidence=0.9,
        model="qwen2.5-14b-awq@vllm-0.8",
        prompt_hash="a" * 64,
        tokens=TokenUsage(input=10, output=5, total=15),
        duration_ms=42,
    )


def _make_budget() -> BudgetSnapshot:
    return BudgetSnapshot(
        tokens_input=10,
        tokens_output=5,
        tokens_total=15,
        cost_usd_simulated=0.01,
        duration_ms=42,
        limit_tokens=50000,
        limit_cost_usd=1.0,
        limit_duration_s=60,
    )


def _audit_writer_mock() -> AsyncMock:
    audit = AsyncMock()
    audit.write = AsyncMock(return_value=None)
    return audit


async def test_plc_setpoint_blocked() -> None:
    """target_subject=cmd.plc.setpoint.* → SafetyInterlockRejection + audit row."""
    audit = _audit_writer_mock()
    mw = SafetyInterlockMiddleware(audit_writer=audit)

    action = ProposedAction.from_payload(
        thread_id="ops.x.s1",
        action_type=ActionType.WRITE_PLC_SETPOINT,
        args={"value": 1.0},
        target_subject="cmd.plc.setpoint.loom-T-12.speed",
    )

    with pytest.raises(SafetyInterlockRejection) as exc_info:
        await mw.check(
            action,
            agent_id="operator-assistant",
            thread_id="ops.x.s1",
            cluster="ops",
            evidence_panel=_make_evidence(),
            budget_snapshot=_make_budget(),
        )

    assert exc_info.value.action_type == "WRITE_PLC_SETPOINT"
    audit.write.assert_awaited_once()
    record = audit.write.await_args.args[0]
    assert record.decision == Decision.INTERLOCK_REJECT


async def test_firmware_deploy_blocked_by_action_type() -> None:
    """action_type matches forbidden_action_types even with benign subject."""
    audit = _audit_writer_mock()
    mw = SafetyInterlockMiddleware(audit_writer=audit)

    action = ProposedAction.from_payload(
        thread_id="ops.x.s1",
        action_type=ActionType.FIRMWARE_DEPLOY,
        args={"image": "v1.2"},
        target_subject="cmd.firmware.deploy",
    )

    with pytest.raises(SafetyInterlockRejection):
        await mw.check(
            action,
            agent_id="operator-assistant",
            thread_id="ops.x.s1",
            cluster="ops",
            evidence_panel=_make_evidence(),
            budget_snapshot=_make_budget(),
        )
    audit.write.assert_awaited_once()


async def test_actuator_command_subject_blocked() -> None:
    audit = _audit_writer_mock()
    mw = SafetyInterlockMiddleware(audit_writer=audit)

    action = ProposedAction.from_payload(
        thread_id="ops.x.s1",
        action_type=ActionType.ACTUATOR_COMMAND,
        args={"x": 1},
        target_subject="cmd.actuator.gripper.open",
    )
    with pytest.raises(SafetyInterlockRejection):
        await mw.check(
            action,
            agent_id="operator-assistant",
            thread_id="ops.x.s1",
            cluster="ops",
            evidence_panel=_make_evidence(),
            budget_snapshot=_make_budget(),
        )


async def test_benign_action_passes() -> None:
    """Action with non-forbidden subject + action_type → no exception, no audit."""
    audit = _audit_writer_mock()
    mw = SafetyInterlockMiddleware(audit_writer=audit)

    action = ProposedAction.from_payload(
        thread_id="ops.x.s1",
        action_type=ActionType.GRAPH_RECURSION_REVIEW,
        args={"reason": "test"},
        target_subject="sensor.events.x",
    )
    result = await mw.check(
        action,
        agent_id="operator-assistant",
        thread_id="ops.x.s1",
        cluster="ops",
        evidence_panel=_make_evidence(),
        budget_snapshot=_make_budget(),
    )
    assert result is None
    audit.write.assert_not_awaited()


async def test_yaml_loaded_from_default_path() -> None:
    """yaml_path=None uses the package-relative safety-interlock.yaml."""
    mw = SafetyInterlockMiddleware()  # default path
    # Sanity: at least one forbidden subject prefix loaded.
    assert mw._forbidden_prefixes  # type: ignore[attr-defined]
    assert mw._forbidden_action_types  # type: ignore[attr-defined]


async def test_no_audit_writer_does_not_crash(caplog) -> None:
    """Missing audit_writer logs a warning but the rejection still raises."""
    mw = SafetyInterlockMiddleware(audit_writer=None)
    action = ProposedAction.from_payload(
        thread_id="ops.x.s1",
        action_type=ActionType.WRITE_PLC_SETPOINT,
        args={},
        target_subject="cmd.plc.setpoint.x.y",
    )
    with pytest.raises(SafetyInterlockRejection):
        await mw.check(
            action,
            agent_id="operator-assistant",
            thread_id="ops.x.s1",
            cluster="ops",
            evidence_panel=_make_evidence(),
            budget_snapshot=_make_budget(),
        )
