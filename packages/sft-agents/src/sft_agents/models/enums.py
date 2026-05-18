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
    """

    WRITE_PLC_SETPOINT = "WRITE_PLC_SETPOINT"
    ACTUATOR_COMMAND = "ACTUATOR_COMMAND"
    FIRMWARE_DEPLOY = "FIRMWARE_DEPLOY"
    NETWORK_ACL_CHANGE = "NETWORK_ACL_CHANGE"
    GRAPH_RECURSION_REVIEW = "GRAPH_RECURSION_REVIEW"
    GOVERNOR_ALERT = "GOVERNOR_ALERT"
