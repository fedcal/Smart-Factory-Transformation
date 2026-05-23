-- Migration 009: extend audit.actions.action_type CHECK constraint for Phase 7 (D-AE-MNT).
-- File: infra/migrations/timescale/009_extend_audit_mnt.sql
-- Phase 7 — Plan 07-01
-- Idempotent: safe to re-run.
--
-- Phase 7 ActionType labels (RUL_ESTIMATE, RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT, OEE_REPORT).
-- Decision enum NOT extended (existing values sufficient per D-AE-MNT).
-- Sync packages/sft-agents/src/sft_agents/models/enums.py ActionType in lockstep.
--
-- Source: 07-PATTERNS.md Section 10 (lines 432-462) — exact mirror of 007 DROP+ADD CHECK pattern.
--
-- Schema before this migration (post-007):
--   audit_actions_action_type_chk CHECK (action_type IN (
--     'WRITE_PLC_SETPOINT','ACTUATOR_COMMAND','FIRMWARE_DEPLOY',
--     'NETWORK_ACL_CHANGE','GRAPH_RECURSION_REVIEW','GOVERNOR_ALERT',
--     'ESCALATION_REQUEST','QUALITY_VERDICT','SCHEDULE_DRAFT','ANOMALY_ALERT'))
--
-- Strategy:
--   Idempotent DROP IF EXISTS + ADD on the named constraint
--   `audit_actions_action_type_chk` introduced by migration 007. Decision
--   CHECK constraint is NOT touched (D-AE-MNT explicit). Round-trip
--   integration test in infra/migrations/timescale/tests/test_migration_009.py
--   verifies (a) all 5 new values insert successfully, (b) legacy Phase 1-6
--   values still insert (no regression), (c) Decision CHECK definition is
--   bytewise unchanged from post-007 state, (d) double-apply is a no-op.

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
      -- Phase 7 extensions (D-AE-MNT — Maintenance & Reliability cluster):
      'RUL_ESTIMATE',         -- D-PM-04: predictive-maintenance RUL audit row
      'RCA_CHAIN',            -- D-RCA-02: rca-specialist 5-Why chain audit
      'COACH_STEP',           -- D-MC-02: maintenance-coach step audit
      'DOWNTIME_VERDICT',     -- D-DA-01: downtime-analyzer event verdict audit
      'OEE_REPORT'            -- D-DA-03: downtime-analyzer OEE report audit
    )
  );
