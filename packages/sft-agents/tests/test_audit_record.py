"""Test suite for sft_agents.models.audit (Plan 04-01 Task 2).

Verifies the AuditRecord Pydantic projection of audit.actions (D-56):
    - frozen + extra=forbid
    - All tz-aware datetime fields
    - motivation required when decision starts with 'hitl_' (HITL-07)
    - approval_id required when decision starts with 'hitl_'
    - approval_id MUST be None when decision == 'auto'
    - decision_actor field flows through correctly
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

UTC = timezone.utc


def _make_evidence_panel():
    from sft_agents.models import EvidencePanel, TokenUsage

    return EvidencePanel(
        input_summary="Test",
        tool_calls=[],
        rag_citations=[],
        confidence=0.9,
        model="qwen2.5-7b@ollama-0.6",
        prompt_hash="a" * 64,
        tokens=TokenUsage(input=10, output=5, total=15),
        duration_ms=50,
    )


def _make_budget_snapshot():
    from sft_agents.models import BudgetSnapshot

    return BudgetSnapshot(
        tokens_input=10,
        tokens_output=5,
        tokens_total=15,
        cost_usd_simulated=0.001,
        duration_ms=50,
        limit_tokens=50_000,
        limit_cost_usd=1.0,
        limit_duration_s=60,
    )


def _make_audit(**overrides):
    from sft_agents.models import AuditRecord, Decision

    base = {
        "id": uuid4(),
        "ts": datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        "action_id": uuid4(),
        "agent_id": "operator-assistant",
        "thread_id": "ops.operator-assistant.7c3a",
        "cluster": "ops",
        "action_type": "WRITE_PLC_SETPOINT",
        "evidence_panel": _make_evidence_panel(),
        "decision": Decision.AUTO,
        "decision_actor": None,
        "motivation": None,
        "budget_snapshot": _make_budget_snapshot(),
        "approval_id": None,
    }
    base.update(overrides)
    return AuditRecord(**base)


class TestAuditRecordValid:
    """Well-formed AuditRecord variants."""

    def test_valid_auto_decision(self) -> None:
        rec = _make_audit()
        assert rec.decision.value == "auto"
        assert rec.approval_id is None

    def test_valid_hitl_decision(self) -> None:
        from sft_agents.models import Decision

        approval_id = uuid4()
        rec = _make_audit(
            decision=Decision.HITL_OPERATOR,
            motivation="Operator approved due to safety margin",
            decision_actor="user@mantis.example",
            approval_id=approval_id,
        )
        assert rec.decision.value == "hitl_operator"
        assert rec.motivation
        assert rec.approval_id == approval_id


class TestAuditRecordHITLMotivation:
    """HITL-07: motivation required for hitl_* decisions."""

    def test_hitl_operator_without_motivation_rejected(self) -> None:
        from sft_agents.models import Decision

        with pytest.raises(ValidationError):
            _make_audit(
                decision=Decision.HITL_OPERATOR,
                motivation=None,
                approval_id=uuid4(),
            )

    def test_hitl_supervisor_empty_motivation_rejected(self) -> None:
        from sft_agents.models import Decision

        with pytest.raises(ValidationError):
            _make_audit(
                decision=Decision.HITL_SUPERVISOR,
                motivation="",
                approval_id=uuid4(),
            )

    def test_hitl_manager_with_motivation_ok(self) -> None:
        from sft_agents.models import Decision

        rec = _make_audit(
            decision=Decision.HITL_MANAGER,
            motivation="Manager override per cost ceiling",
            approval_id=uuid4(),
        )
        assert rec.motivation == "Manager override per cost ceiling"


class TestAuditRecordApprovalIdMatrix:
    """approval_id consistency: hitl_* allows NULL (pending) or UUID (approved); auto implies NULL.

    Plan 07-15 (CR-03 fix): HITL decisions now allow approval_id=None to represent
    a *pending* escalation where the supervisor has been notified but has not yet
    approved. The fabricated-UUID anti-pattern (generating uuid4() as a placeholder
    that breaks hitl.approvals JOIN integrity) is replaced by explicit None + a
    pending-state motivation string.
    """

    def test_hitl_with_null_approval_id_allowed_for_pending_escalation(self) -> None:
        """HITL decision with approval_id=None is valid — represents pending escalation."""
        from sft_agents.models import Decision

        # approval_id=None is now permitted for HITL decisions (pending state)
        record = _make_audit(
            decision=Decision.HITL_OPERATOR,
            motivation="Supervisor approval required for asset LOOM-01",
            approval_id=None,
        )
        assert record.approval_id is None
        assert record.decision.value == "hitl_operator"

    def test_hitl_with_valid_approval_id_allowed_for_finalized_approval(self) -> None:
        """HITL decision with a real approval UUID is valid — represents finalized approval."""
        from sft_agents.models import Decision

        approval_id = uuid4()
        record = _make_audit(
            decision=Decision.HITL_SUPERVISOR,
            motivation="Supervisor approved corrective action for asset LOOM-01",
            approval_id=approval_id,
        )
        assert record.approval_id == approval_id

    def test_auto_with_approval_id_rejected(self) -> None:
        from sft_agents.models import Decision

        with pytest.raises(ValidationError):
            _make_audit(
                decision=Decision.AUTO,
                approval_id=uuid4(),
            )


class TestAuditRecordTzAware:
    """ts must be tz-aware."""

    def test_naive_ts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_audit(ts=datetime(2026, 5, 18, 12, 0, 0))


class TestAuditRecordImmutability:
    """frozen + extra=forbid."""

    def test_frozen(self) -> None:
        rec = _make_audit()
        with pytest.raises(ValidationError):
            rec.agent_id = "hijack"

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            _make_audit(rogue_field="x")
