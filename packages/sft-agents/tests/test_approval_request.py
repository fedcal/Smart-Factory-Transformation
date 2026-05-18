"""Test suite for sft_agents.models.approval (Plan 04-01 Task 2)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

UTC = timezone.utc


def _make_approval(**overrides):
    from sft_agents.models import ApprovalRequest, Tier

    base = {
        "id": uuid4(),
        "agent_id": "operator-assistant",
        "thread_id": "ops.operator-assistant.7c3a",
        "tier": Tier.OPERATOR,
        "action_type": "WRITE_PLC_SETPOINT",
        "payload_json": {"asset_id": "LOOM-01", "setpoint": 1200},
        "created_at": datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        "sla_deadline": datetime(2026, 5, 18, 12, 2, 0, tzinfo=UTC),
    }
    base.update(overrides)
    return ApprovalRequest(**base)


class TestApprovalRequestDefaults:
    def test_default_status_pending(self) -> None:
        req = _make_approval()
        assert req.status.value == "pending"

    def test_optional_fields_default_none(self) -> None:
        req = _make_approval()
        assert req.decided_at is None
        assert req.decided_by is None
        assert req.decision_json is None
        assert req.escalated_to_id is None


class TestApprovalRequestTzAware:
    def test_naive_created_at_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_approval(created_at=datetime(2026, 5, 18, 12, 0, 0))

    def test_naive_sla_deadline_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_approval(sla_deadline=datetime(2026, 5, 18, 12, 2, 0))


class TestApprovalRequestStatusEnum:
    def test_all_status_values(self) -> None:
        from sft_agents.models import ApprovalStatus

        for s in ("pending", "approved", "rejected", "escalated", "timed_out"):
            req = _make_approval(status=ApprovalStatus(s))
            assert req.status.value == s

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_approval(status="bogus")


class TestApprovalRequestTier:
    def test_all_tiers(self) -> None:
        from sft_agents.models import Tier

        for t in ("operator", "supervisor", "manager", "safety_interlock"):
            req = _make_approval(tier=Tier(t))
            assert req.tier.value == t


class TestApprovalRequestImmutability:
    def test_frozen(self) -> None:
        req = _make_approval()
        with pytest.raises(ValidationError):
            req.agent_id = "hijack"

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            _make_approval(rogue="x")


class TestApprovalDecision:
    def test_valid_approve(self) -> None:
        from sft_agents.models import ApprovalDecision

        d = ApprovalDecision(
            decision="approve",
            motivation="Looks safe",
            decided_by="op1@mantis",
        )
        assert d.decision == "approve"

    def test_empty_motivation_rejected(self) -> None:
        from sft_agents.models import ApprovalDecision

        with pytest.raises(ValidationError):
            ApprovalDecision(decision="approve", motivation="", decided_by="op1")

    def test_invalid_decision_value_rejected(self) -> None:
        from sft_agents.models import ApprovalDecision

        with pytest.raises(ValidationError):
            ApprovalDecision(decision="maybe", motivation="x", decided_by="op1")
