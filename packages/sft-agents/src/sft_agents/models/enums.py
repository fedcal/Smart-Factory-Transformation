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

    Phase 7 extensions (Maintenance & Reliability cluster, D-AE-MNT):
        RUL_ESTIMATE — D-PM-04: predictive-maintenance Remaining
            Useful Life estimate audit row.
        RCA_CHAIN — D-RCA-02: rca-specialist 5-Why root-cause chain
            audit row (one row per investigation).
        COACH_STEP — D-MC-02: maintenance-coach guided procedure-step
            audit row (one row per coached step).
        DOWNTIME_VERDICT — D-DA-01: downtime-analyzer event verdict
            audit row (classification of a downtime event).
        OEE_REPORT — D-DA-03: downtime-analyzer OEE roll-up report
            audit row (periodic Overall Equipment Effectiveness summary).

    Phase 8 extensions (Knowledge & Training cluster, D-X-01):
        HANDOVER_DRAFT — D-SH-01: shift handover draft compiled by ShiftHandover.
        HANDOVER_SIGNOFF — D-SH-03: supervisor sign-off row (2 rows per handover).
        TRAINING_SESSION — D-TC-01: quiz delivery session record.
        TRAINING_SIGNOFF — D-TC-03: supervisor competency sign-off.
        KNOWLEDGE_DEDUP — D-KC-01: dedup verdict (exact or near-dup).
        STALE_FLAG — D-KC-02: staleness flag on a document.
        SOP_DRAFT — D-DS-03: synthesized SOP draft before indexing.

    Migration `infra/migrations/timescale/007_extend_audit_decisions.sql`
    introduced the action_type CHECK with Phase 1-6 values; migration
    `infra/migrations/timescale/009_extend_audit_mnt.sql` extends it with
    the Phase 7 values; migration `infra/migrations/timescale/010_extend_audit_knw.sql`
    extends it with the Phase 8 values; migration
    `infra/migrations/timescale/012_extend_audit_scm.sql` extends it with
    the Phase 9 values below. The SQL CHECK string must stay in lockstep
    with the .value strings here — drift triggers PG CheckViolationError
    at runtime.
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
    # Phase 7 additions — keep in lockstep with migration 009 (D-AE-MNT).
    RUL_ESTIMATE = "RUL_ESTIMATE"          # D-PM-04: predictive-maintenance audit row
    RCA_CHAIN = "RCA_CHAIN"                # D-RCA-02: rca-specialist 5-Why chain audit
    COACH_STEP = "COACH_STEP"              # D-MC-02: maintenance-coach step audit
    DOWNTIME_VERDICT = "DOWNTIME_VERDICT"  # D-DA-01: downtime-analyzer event audit
    OEE_REPORT = "OEE_REPORT"              # D-DA-03: downtime-analyzer OEE report audit
    # Phase 8 additions — keep in lockstep with migration 010 (D-X-01).
    HANDOVER_DRAFT = "HANDOVER_DRAFT"       # D-SH-01: draft compiled by ShiftHandover
    HANDOVER_SIGNOFF = "HANDOVER_SIGNOFF"   # D-SH-03: supervisor sign-off row (2 rows per handover)
    TRAINING_SESSION = "TRAINING_SESSION"   # D-TC-01: quiz delivery session record
    TRAINING_SIGNOFF = "TRAINING_SIGNOFF"   # D-TC-03: supervisor competency sign-off
    KNOWLEDGE_DEDUP = "KNOWLEDGE_DEDUP"     # D-KC-01: dedup verdict (exact or near-dup)
    STALE_FLAG = "STALE_FLAG"               # D-KC-02: staleness flag on a document
    SOP_DRAFT = "SOP_DRAFT"                 # D-DS-03: synthesized SOP draft before indexing
    # Phase 9 additions — keep in lockstep with migration 012 (D-DATA / Supply Chain & Economics).
    REORDER_ALERT = "REORDER_ALERT"                          # SCM-01: InventoryManager reorder alert
    PURCHASE_RECOMMENDATION_DRAFT = "PURCHASE_RECOMMENDATION_DRAFT"  # SCM-01: InventoryManager procurement draft
    PURCHASE_SIGNOFF = "PURCHASE_SIGNOFF"                    # SCM-01: procurement supervisor sign-off
    ENERGY_PROPOSAL = "ENERGY_PROPOSAL"                      # SCM-02: EnergyOptimizer off-peak proposal draft
    ENERGY_SIGNOFF = "ENERGY_SIGNOFF"                        # SCM-02: energy supervisor sign-off
    DEMAND_PLAN_DRAFT = "DEMAND_PLAN_DRAFT"                  # SCM-04: DemandForecaster demand plan draft
    DEMAND_PLAN_SIGNOFF = "DEMAND_PLAN_SIGNOFF"              # SCM-04: ProductionPlanner publish sign-off
    COST_REPORT = "COST_REPORT"                              # SCM-03: CostAnalyzer autonomous ROI/OEPV report row (Decision.AUTO)
