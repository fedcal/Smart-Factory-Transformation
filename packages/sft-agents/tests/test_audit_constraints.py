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
    def test_approval_id_null_allowed_for_pending_escalation(self, dec_value: str) -> None:
        """Plan 07-15 CR-03 fix: HITL decisions with approval_id=None represent pending
        escalations where the supervisor has been notified but has not yet approved.
        The AuditRecord validator no longer rejects HITL+None — fabricating a random
        UUID placeholder was the CR-03 defect being corrected here."""
        from sft_agents.models import Decision

        # approval_id=None is valid for HITL decisions (pending escalation state)
        rec = _audit(Decision(dec_value), motivation="Supervisor approval required for pending escalation", approval_id=None)
        assert rec.approval_id is None
        assert rec.motivation is not None

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


# ---------------------------------------------------------------------------
# Phase 6 enum extensions (Plan 06-01 Task 2)
#
# The 6 new enum values (Decision.SUPPRESSED, Decision.LOGGED + 4 new
# ActionType members) MUST stay in lockstep with the SQL CHECK constraints
# in infra/migrations/timescale/007_extend_audit_decisions.sql. The migration
# round-trip integration test lives at
# infra/migrations/timescale/tests/test_migration_007.py — those tests verify
# the DB side. These tests verify the Python side:
#   - enum members exist and import cleanly
#   - .value strings match the SQL CHECK enum strings exactly
#   - construction of AuditRecord with the new values does not raise
#     (i.e., model-level validators do not reject the Phase 6 additions)
# ---------------------------------------------------------------------------


_PHASE6_DECISION_VALUES: list[tuple[str, str]] = [
    # (enum member name, .value string that must match SQL CHECK)
    ("SUPPRESSED", "suppressed"),
    ("LOGGED", "logged"),
]


_PHASE6_ACTION_TYPE_VALUES: list[tuple[str, str]] = [
    ("ESCALATION_REQUEST", "ESCALATION_REQUEST"),
    ("QUALITY_VERDICT", "QUALITY_VERDICT"),
    ("SCHEDULE_DRAFT", "SCHEDULE_DRAFT"),
    ("ANOMALY_ALERT", "ANOMALY_ALERT"),
]


# ---------------------------------------------------------------------------
# Phase 7 enum extensions (Plan 07-01 Task 2)
#
# The 5 new ActionType members (RUL_ESTIMATE, RCA_CHAIN, COACH_STEP,
# DOWNTIME_VERDICT, OEE_REPORT) MUST stay in lockstep with the SQL CHECK
# constraint in infra/migrations/timescale/009_extend_audit_mnt.sql (D-AE-MNT).
# The migration round-trip integration test lives at
# infra/migrations/timescale/tests/test_migration_009.py — those tests verify
# the DB side. The tests below verify the Python side:
#   - enum members exist and import cleanly
#   - .value strings match the SQL CHECK enum strings exactly
#   - Decision enum is NOT extended (D-AE-MNT explicit: existing values suffice)
# ---------------------------------------------------------------------------


_PHASE7_ACTION_TYPE_VALUES: list[tuple[str, str]] = [
    ("RUL_ESTIMATE", "RUL_ESTIMATE"),
    ("RCA_CHAIN", "RCA_CHAIN"),
    ("COACH_STEP", "COACH_STEP"),
    ("DOWNTIME_VERDICT", "DOWNTIME_VERDICT"),
    ("OEE_REPORT", "OEE_REPORT"),
]


class TestPhase7ActionTypeEnum:
    """Five Phase 7 ActionType additions (RUL_ESTIMATE, RCA_CHAIN, COACH_STEP,
    DOWNTIME_VERDICT, OEE_REPORT) per 07-PATTERNS.md Section 3 lines 148-174
    and D-AE-MNT."""

    @pytest.mark.parametrize(("member_name", "value"), _PHASE7_ACTION_TYPE_VALUES)
    def test_member_present_with_expected_value(
        self, member_name: str, value: str
    ) -> None:
        from sft_agents.models import ActionType

        assert hasattr(ActionType, member_name), (
            f"ActionType.{member_name} missing — Phase 7 enum extension required"
        )
        member = ActionType[member_name]
        assert member.value == value, (
            f"ActionType.{member_name}.value must equal {value!r} to match"
            f" migration 009 CHECK constraint; got {member.value!r}"
        )

    @pytest.mark.parametrize(("_member_name", "value"), _PHASE7_ACTION_TYPE_VALUES)
    def test_string_lookup_round_trip(
        self, _member_name: str, value: str
    ) -> None:
        from sft_agents.models import ActionType

        # SQL CHECK constraint stores the .value; Python reads it back via ActionType(str)
        looked_up = ActionType(value)
        assert looked_up.value == value


class TestPhase7DecisionEnumUnchanged:
    """D-AE-MNT: Decision enum MUST NOT be extended in Phase 7.

    Asserts the exact Decision member set after Phase 6 (Plan 06-01) is the
    same after Phase 7 enum changes — no additions, no removals, no renames.
    Catches accidental Decision extensions that would drift from migration 009
    (which leaves the decision CHECK constraint untouched)."""

    _EXPECTED_DECISION_MEMBERS: set[str] = {
        # Phase 1-5 baseline
        "AUTO",
        "HITL_OPERATOR",
        "HITL_SUPERVISOR",
        "HITL_MANAGER",
        "INTERLOCK_REJECT",
        "ROLLED_BACK",
        "TIMED_OUT",
        "GOVERNOR_ALERT",
        "ESCALATED",
        # Phase 6 (migration 007)
        "SUPPRESSED",
        "LOGGED",
    }

    def test_decision_members_exactly_match_phase6_set(self) -> None:
        from sft_agents.models import Decision

        actual = set(Decision.__members__)
        assert actual == self._EXPECTED_DECISION_MEMBERS, (
            "Decision enum drifted from Phase 6 set — D-AE-MNT forbids"
            f" Phase 7 Decision extensions.\n"
            f" Added members:   {actual - self._EXPECTED_DECISION_MEMBERS}\n"
            f" Removed members: {self._EXPECTED_DECISION_MEMBERS - actual}"
        )


class TestPhase6DecisionEnum:
    """D-AD-03 (suppressed) + D-OA-02 (logged) Decision additions."""

    @pytest.mark.parametrize(("member_name", "value"), _PHASE6_DECISION_VALUES)
    def test_member_present_with_expected_value(
        self, member_name: str, value: str
    ) -> None:
        from sft_agents.models import Decision

        assert hasattr(Decision, member_name), (
            f"Decision.{member_name} missing — Phase 6 enum extension required"
        )
        member = Decision[member_name]
        assert member.value == value, (
            f"Decision.{member_name}.value must equal {value!r} to match"
            f" migration 007 CHECK constraint; got {member.value!r}"
        )

    @pytest.mark.parametrize(("_member_name", "value"), _PHASE6_DECISION_VALUES)
    def test_string_lookup_round_trip(
        self, _member_name: str, value: str
    ) -> None:
        from sft_agents.models import Decision

        # SQL CHECK constraint stores the .value; Python reads it back via Decision(str)
        looked_up = Decision(value)
        assert looked_up.value == value

    def test_audit_record_admits_suppressed(self) -> None:
        """Decision.SUPPRESSED constructs cleanly (no motivation/approval_id required)."""
        from sft_agents.models import Decision

        rec = _audit(Decision.SUPPRESSED, motivation=None, approval_id=None)
        assert rec.decision == Decision.SUPPRESSED

    def test_audit_record_admits_logged(self) -> None:
        """Decision.LOGGED constructs cleanly (D-OA-02 observability-only)."""
        from sft_agents.models import Decision

        rec = _audit(Decision.LOGGED, motivation=None, approval_id=None)
        assert rec.decision == Decision.LOGGED


class TestPhase6ActionTypeEnum:
    """Four Phase 6 ActionType additions (ESCALATION_REQUEST, QUALITY_VERDICT,
    SCHEDULE_DRAFT, ANOMALY_ALERT) per 06-PATTERNS.md lines 280-303."""

    @pytest.mark.parametrize(("member_name", "value"), _PHASE6_ACTION_TYPE_VALUES)
    def test_member_present_with_expected_value(
        self, member_name: str, value: str
    ) -> None:
        from sft_agents.models import ActionType

        assert hasattr(ActionType, member_name), (
            f"ActionType.{member_name} missing — Phase 6 enum extension required"
        )
        member = ActionType[member_name]
        assert member.value == value, (
            f"ActionType.{member_name}.value must equal {value!r} to match"
            f" migration 007 CHECK constraint; got {member.value!r}"
        )

    @pytest.mark.parametrize(("_member_name", "value"), _PHASE6_ACTION_TYPE_VALUES)
    def test_string_lookup_round_trip(
        self, _member_name: str, value: str
    ) -> None:
        from sft_agents.models import ActionType

        looked_up = ActionType(value)
        assert looked_up.value == value


class TestPreExistingEnumsUnchanged:
    """Backward-compatibility: every pre-Phase-6 Decision + ActionType member
    still exists with its original string value. Catches accidental renames."""

    _LEGACY_DECISIONS = [
        ("AUTO", "auto"),
        ("HITL_OPERATOR", "hitl_operator"),
        ("HITL_SUPERVISOR", "hitl_supervisor"),
        ("HITL_MANAGER", "hitl_manager"),
        ("INTERLOCK_REJECT", "interlock_reject"),
        ("ROLLED_BACK", "rolled_back"),
        ("TIMED_OUT", "timed_out"),
        ("GOVERNOR_ALERT", "governor_alert"),
        ("ESCALATED", "escalated"),
    ]

    _LEGACY_ACTION_TYPES = [
        ("WRITE_PLC_SETPOINT", "WRITE_PLC_SETPOINT"),
        ("ACTUATOR_COMMAND", "ACTUATOR_COMMAND"),
        ("FIRMWARE_DEPLOY", "FIRMWARE_DEPLOY"),
        ("NETWORK_ACL_CHANGE", "NETWORK_ACL_CHANGE"),
        ("GRAPH_RECURSION_REVIEW", "GRAPH_RECURSION_REVIEW"),
        ("GOVERNOR_ALERT", "GOVERNOR_ALERT"),
    ]

    @pytest.mark.parametrize(("member", "value"), _LEGACY_DECISIONS)
    def test_decision_unchanged(self, member: str, value: str) -> None:
        from sft_agents.models import Decision

        assert Decision[member].value == value

    @pytest.mark.parametrize(("member", "value"), _LEGACY_ACTION_TYPES)
    def test_action_type_unchanged(self, member: str, value: str) -> None:
        from sft_agents.models import ActionType

        assert ActionType[member].value == value
