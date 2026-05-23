"""Enums for sft-agents — Tier, Decision, ActionType, ApprovalStatus (D-55, D-56, D-57).

All enums are `str, Enum` (Pydantic v2 native) so JSON serialization yields plain strings
and DB CHECK constraints match exactly.
"""

from __future__ import annotations

from enum import Enum


class Tier(str, Enum):
    """4-tier escalation chain (D-57).

    Safety Interlock is manual-only (no auto-escalation, no timeout).
    """

    OPERATOR = "operator"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    SAFETY_INTERLOCK = "safety_interlock"


class Decision(str, Enum):
    """Audit decision outcomes (D-56 + Claude's Discretion line 431).

    hitl_* variants REQUIRE motivation + approval_id (HITL-07).
    auto REQUIRES approval_id IS NULL.

    Phase 6 extensions:
        SUPPRESSED — D-AD-03: anomaly-detector / RateLimiter dropped the
            proposed action before tier evaluation. No HITL involvement,
            no PLC actuation; audit row written for observability only.
        LOGGED — D-OA-02: ops-asst observability-only audit row (no
            actuation, no HITL). Used by Operator Assistant when
            surfacing facts to the operator without proposing actions.

    Migration `infra/migrations/timescale/007_extend_audit_decisions.sql`
    syncs the SQL CHECK constraint with the values below. Drift between
    enum.value strings and CHECK values causes runtime PG check violations.
    """

    AUTO = "auto"
    HITL_OPERATOR = "hitl_operator"
    HITL_SUPERVISOR = "hitl_supervisor"
    HITL_MANAGER = "hitl_manager"
    INTERLOCK_REJECT = "interlock_reject"
    ROLLED_BACK = "rolled_back"
    TIMED_OUT = "timed_out"
    GOVERNOR_ALERT = "governor_alert"
    ESCALATED = "escalated"
    # Phase 6 additions — keep in lockstep with migration 007.
    SUPPRESSED = "suppressed"
    LOGGED = "logged"


class ApprovalStatus(str, Enum):
    """hitl.approvals.status lifecycle (D-55)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"


class ActionType(str, Enum):
    """Categorical action labels for ProposedAction + audit.actions (D-58).

    Extensible — cluster-specific subclasses can extend via string values without
    breaking the enum membership check (str-based).

    Phase 6 extensions:
        ESCALATION_REQUEST — D-OA-02 / Pitfall §9: emitted by
            EscalateToSupervisorTool when ops-asst escalates to a higher
            tier rather than proposing a direct actuation.
        QUALITY_VERDICT — D-QI-02: quality-inspector verdict audit row
            (pass/fail decision against a quality threshold).
        SCHEDULE_DRAFT — D-PP-03: production-planner draft schedule
            audit row (proposed schedule pending operator review).
        ANOMALY_ALERT — D-AD-01: anomaly-detector alert audit row
            (anomaly score crossed threshold).

    Migration `infra/migrations/timescale/007_extend_audit_decisions.sql`
    syncs the SQL CHECK constraint with the values below.
    """

    WRITE_PLC_SETPOINT = "WRITE_PLC_SETPOINT"
    ACTUATOR_COMMAND = "ACTUATOR_COMMAND"
    FIRMWARE_DEPLOY = "FIRMWARE_DEPLOY"
    NETWORK_ACL_CHANGE = "NETWORK_ACL_CHANGE"
    GRAPH_RECURSION_REVIEW = "GRAPH_RECURSION_REVIEW"
    GOVERNOR_ALERT = "GOVERNOR_ALERT"
    # Phase 6 additions — keep in lockstep with migration 007.
    ESCALATION_REQUEST = "ESCALATION_REQUEST"
    QUALITY_VERDICT = "QUALITY_VERDICT"
    SCHEDULE_DRAFT = "SCHEDULE_DRAFT"
    ANOMALY_ALERT = "ANOMALY_ALERT"
