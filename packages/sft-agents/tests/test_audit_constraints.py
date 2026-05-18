"""Test HITL-07 motivation-required matrix end-to-end (Plan 04-01 Task 2).

Cross-cutting integration test for the Decision × motivation × approval_id
validator. Distinct from test_audit_record.py (which tests model construction);
this file enumerates the full decision matrix and ensures the validator fires
in every relevant combination.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

UTC = timezone.utc


def _evidence():
    from sft_agents.models import EvidencePanel, TokenUsage

    return EvidencePanel(
        input_summary="Test",
        tool_calls=[],
        rag_citations=[],
        confidence=0.9,
        model="qwen2.5-7b@ollama",
        prompt_hash="a" * 64,
        tokens=TokenUsage(input=10, output=5, total=15),
        duration_ms=50,
    )


def _budget():
    from sft_agents.models import BudgetSnapshot

    return BudgetSnapshot(
        limit_tokens=50_000,
        limit_cost_usd=1.0,
        limit_duration_s=60,
    )


def _audit(decision, motivation=None, approval_id=None):
    from sft_agents.models import AuditRecord

    return AuditRecord(
        id=uuid4(),
        ts=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        action_id=uuid4(),
        agent_id="op-asst",
        thread_id="t1",
        cluster="ops",
        action_type="WRITE_PLC_SETPOINT",
        evidence_panel=_evidence(),
        decision=decision,
        decision_actor=None,
        motivation=motivation,
        budget_snapshot=_budget(),
        approval_id=approval_id,
    )


HITL_DECISIONS = ["hitl_operator", "hitl_supervisor", "hitl_manager"]


class TestHITL07MotivationMatrix:
    """HITL-07: every hitl_* decision requires non-empty motivation."""

    @pytest.mark.parametrize("dec_value", HITL_DECISIONS)
    def test_motivation_required(self, dec_value: str) -> None:
        from sft_agents.models import Decision

        with pytest.raises(ValidationError):
            _audit(Decision(dec_value), motivation=None, approval_id=uuid4())

    @pytest.mark.parametrize("dec_value", HITL_DECISIONS)
    def test_motivation_empty_rejected(self, dec_value: str) -> None:
        from sft_agents.models import Decision

        with pytest.raises(ValidationError):
            _audit(Decision(dec_value), motivation="", approval_id=uuid4())

    @pytest.mark.parametrize("dec_value", HITL_DECISIONS)
    def test_approval_id_required(self, dec_value: str) -> None:
        from sft_agents.models import Decision

        with pytest.raises(ValidationError):
            _audit(Decision(dec_value), motivation="ok", approval_id=None)

    @pytest.mark.parametrize("dec_value", HITL_DECISIONS)
    def test_valid_combo(self, dec_value: str) -> None:
        from sft_agents.models import Decision

        rec = _audit(Decision(dec_value), motivation="ok", approval_id=uuid4())
        assert rec.motivation == "ok"


class TestAutoDecisionConstraint:
    def test_auto_with_approval_id_rejected(self) -> None:
        from sft_agents.models import Decision

        with pytest.raises(ValidationError):
            _audit(Decision.AUTO, motivation=None, approval_id=uuid4())

    def test_auto_clean_ok(self) -> None:
        from sft_agents.models import Decision

        rec = _audit(Decision.AUTO, motivation=None, approval_id=None)
        assert rec.approval_id is None
