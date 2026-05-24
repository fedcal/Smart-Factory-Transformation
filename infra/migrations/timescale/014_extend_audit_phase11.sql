-- Migration 014: extend audit.actions.action_type CHECK constraint for Phase 11 (Observability & Security).
-- File: infra/migrations/timescale/014_extend_audit_phase11.sql
-- Phase 11 — Plan 11-00
-- Idempotent: safe to re-run (DROP IF EXISTS + ADD).
--
-- Phase 11 ActionType label added: RESTRICTED_DOC_ACCESS.
-- Keep in lockstep with packages/sft-agents/src/sft_agents/models/enums.py::ActionType.
-- (ActionType.RESTRICTED_DOC_ACCESS is added to enums.py in Plan 11-03, which depends on this migration.)
--
-- Source: 012_extend_audit_scm.sql — exact mirror of DROP+ADD CHECK pattern.
--
-- Schema before this migration (post-012):
--   audit_actions_action_type_chk CHECK (action_type IN (
--     'WRITE_PLC_SETPOINT','ACTUATOR_COMMAND','FIRMWARE_DEPLOY',
--     'NETWORK_ACL_CHANGE','GRAPH_RECURSION_REVIEW','GOVERNOR_ALERT',
--     'ESCALATION_REQUEST','QUALITY_VERDICT','SCHEDULE_DRAFT','ANOMALY_ALERT',
--     'RUL_ESTIMATE','RCA_CHAIN','COACH_STEP','DOWNTIME_VERDICT','OEE_REPORT',
--     'HANDOVER_DRAFT','HANDOVER_SIGNOFF','TRAINING_SESSION','TRAINING_SIGNOFF',
--     'KNOWLEDGE_DEDUP','STALE_FLAG','SOP_DRAFT',
--     'REORDER_ALERT','PURCHASE_RECOMMENDATION_DRAFT','PURCHASE_SIGNOFF',
--     'ENERGY_PROPOSAL','ENERGY_SIGNOFF','DEMAND_PLAN_DRAFT','DEMAND_PLAN_SIGNOFF',
--     'COST_REPORT'))
--
-- Strategy:
--   Idempotent DROP IF EXISTS + ADD on the named constraint
--   `audit_actions_action_type_chk` introduced by migration 007. Decision
--   CHECK constraint is NOT touched (D-X-01 explicit). Round-trip
--   integration test in infra/migrations/timescale/tests/test_migration_014.py
--   verifies (a) RESTRICTED_DOC_ACCESS inserts successfully, (b) legacy Phase 1-9
--   values still insert (no regression), (c) double-apply is a no-op.

ALTER TABLE audit.actions
  DROP CONSTRAINT IF EXISTS audit_actions_action_type_chk;

ALTER TABLE audit.actions
  ADD CONSTRAINT audit_actions_action_type_chk CHECK (
    action_type IN (
      -- Phases 1-5 baseline (matches sft_agents.models.enums.ActionType, pre-Phase 6):
      'WRITE_PLC_SETPOINT',
      'ACTUATOR_COMMAND',
      'FIRMWARE_DEPLOY',
      'NETWORK_ACL_CHANGE',
      'GRAPH_RECURSION_REVIEW',
      'GOVERNOR_ALERT',
      -- Phase 6 extensions (migration 007):
      'ESCALATION_REQUEST',   -- D-OA-02 / Pitfall §9: EscalateToSupervisorTool audit
      'QUALITY_VERDICT',      -- D-QI-02: quality-inspector verdict audit row
      'SCHEDULE_DRAFT',       -- D-PP-03: production-planner draft audit row
      'ANOMALY_ALERT',        -- D-AD-01: anomaly-detector alert audit row
      -- Phase 7 extensions (migration 009, D-AE-MNT — Maintenance & Reliability cluster):
      'RUL_ESTIMATE',         -- D-PM-04: predictive-maintenance RUL audit row
      'RCA_CHAIN',            -- D-RCA-02: rca-specialist 5-Why chain audit
      'COACH_STEP',           -- D-MC-02: maintenance-coach step audit
      'DOWNTIME_VERDICT',     -- D-DA-01: downtime-analyzer event verdict audit
      'OEE_REPORT',           -- D-DA-03: downtime-analyzer OEE report audit
      -- Phase 8 extensions (migration 010, D-X-01) — Knowledge & Training cluster:
      'HANDOVER_DRAFT',       -- D-SH-01: draft compiled by ShiftHandover
      'HANDOVER_SIGNOFF',     -- D-SH-03: supervisor sign-off row (2 rows per handover)
      'TRAINING_SESSION',     -- D-TC-01: quiz delivery session record
      'TRAINING_SIGNOFF',     -- D-TC-03: supervisor competency sign-off
      'KNOWLEDGE_DEDUP',      -- D-KC-01: dedup verdict (exact or near-dup)
      'STALE_FLAG',           -- D-KC-02: staleness flag on a document
      'SOP_DRAFT',            -- D-DS-03: synthesized SOP draft before indexing
      -- Phase 9 extensions (migration 012, D-DATA) — Supply Chain & Economics cluster:
      'REORDER_ALERT',                  -- SCM-01: InventoryManager reorder alert
      'PURCHASE_RECOMMENDATION_DRAFT',  -- SCM-01: InventoryManager procurement draft
      'PURCHASE_SIGNOFF',               -- SCM-01: procurement supervisor sign-off
      'ENERGY_PROPOSAL',                -- SCM-02: EnergyOptimizer off-peak proposal draft
      'ENERGY_SIGNOFF',                 -- SCM-02: energy supervisor sign-off
      'DEMAND_PLAN_DRAFT',              -- SCM-04: DemandForecaster demand plan draft
      'DEMAND_PLAN_SIGNOFF',            -- SCM-04: ProductionPlanner publish sign-off
      'COST_REPORT',                    -- SCM-03: CostAnalyzer autonomous ROI/OEPV report row
      -- Phase 11 extension (SEC-07): query a chunk with acl_level=restricted.
      -- Lockstep with packages/sft-agents/src/sft_agents/models/enums.py::ActionType.RESTRICTED_DOC_ACCESS
      -- (enum value added in Plan 11-03 which depends on this migration 014).
      'RESTRICTED_DOC_ACCESS'  -- SEC-07: query a chunk acl_level=restricted
    )
  );
