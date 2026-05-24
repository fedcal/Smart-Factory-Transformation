-- Migration 010: extend audit.actions.action_type CHECK constraint for Phase 8 (D-X-01).
-- File: infra/migrations/timescale/010_extend_audit_knw.sql
-- Phase 8 — Plan 08-00a
-- Idempotent: safe to re-run.
--
-- Phase 8 ActionType labels (HANDOVER_DRAFT, HANDOVER_SIGNOFF, TRAINING_SESSION,
-- TRAINING_SIGNOFF, KNOWLEDGE_DEDUP, STALE_FLAG, SOP_DRAFT).
-- Decision enum NOT extended (existing values sufficient per D-X-01).
-- Sync packages/sft-agents/src/sft_agents/models/enums.py ActionType in lockstep.
--
-- Source: 08-PATTERNS.md Section "010_extend_audit_knw.sql" — exact mirror of 009 DROP+ADD CHECK pattern.
--
-- Schema before this migration (post-009):
--   audit_actions_action_type_chk CHECK (action_type IN (
--     'WRITE_PLC_SETPOINT','ACTUATOR_COMMAND','FIRMWARE_DEPLOY',
--     'NETWORK_ACL_CHANGE','GRAPH_RECURSION_REVIEW','GOVERNOR_ALERT',
--     'ESCALATION_REQUEST','QUALITY_VERDICT','SCHEDULE_DRAFT','ANOMALY_ALERT',
--     'RUL_ESTIMATE','RCA_CHAIN','COACH_STEP','DOWNTIME_VERDICT','OEE_REPORT'))
--
-- Strategy:
--   Idempotent DROP IF EXISTS + ADD on the named constraint
--   `audit_actions_action_type_chk` introduced by migration 007. Decision
--   CHECK constraint is NOT touched (D-X-01 explicit). Round-trip
--   integration test in infra/migrations/timescale/tests/test_migration_010.py
--   verifies (a) all 7 new values insert successfully, (b) legacy Phase 1-7
--   values still insert (no regression), (c) Decision CHECK definition is
--   bytewise unchanged from post-009 state, (d) double-apply is a no-op.

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
      -- Phase 8 extensions (D-X-01) — keep in lockstep with sft_agents.models.enums.ActionType:
      'HANDOVER_DRAFT',       -- D-SH-01: draft compiled by ShiftHandover
      'HANDOVER_SIGNOFF',     -- D-SH-03: supervisor sign-off row (2 rows per handover)
      'TRAINING_SESSION',     -- D-TC-01: quiz delivery session record
      'TRAINING_SIGNOFF',     -- D-TC-03: supervisor competency sign-off
      'KNOWLEDGE_DEDUP',      -- D-KC-01: dedup verdict (exact or near-dup)
      'STALE_FLAG',           -- D-KC-02: staleness flag on a document
      'SOP_DRAFT'             -- D-DS-03: synthesized SOP draft before indexing
    )
  );
