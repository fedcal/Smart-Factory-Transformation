-- Migration 007: extend audit.actions CHECK constraints (decision + action_type) for Phase 6
-- File: infra/migrations/timescale/007_extend_audit_decisions.sql
-- Phase 6 — Plan 06-01
-- Idempotent: safe to re-run.
--
-- Source: Phase 6 D-AD-03 (Decision.SUPPRESSED for rate-limited proposals) +
--         D-OA-02 (Decision.LOGGED for ops-asst observability writes) +
--         Phase 6 ActionType labels (ESCALATION_REQUEST, QUALITY_VERDICT,
--         SCHEDULE_DRAFT, ANOMALY_ALERT) — see 06-PATTERNS.md lines 280-303.
--
-- Decision enum sync in packages/sft-agents/src/sft_agents/models/enums.py
-- (Plan 06-01 Task 2). Out-of-sync values WILL fail at runtime — round-trip
-- test in packages/sft-agents/tests/test_audit_constraints.py guards this.
--
-- Schema before this migration (003_create_audit_actions.sql lines 32-44):
--   decision TEXT NOT NULL CHECK (decision IN ('auto','hitl_operator',
--     'hitl_supervisor','hitl_manager','interlock_reject','rolled_back',
--     'timed_out','governor_alert','escalated'))
--   action_type TEXT NOT NULL                  -- no CHECK constraint
--
-- Strategy:
--   The decision CHECK in 003 is column-inline and PostgreSQL auto-names it
--   (typically `actions_decision_check`). We do not rely on a hardcoded name —
--   we query pg_constraint dynamically to find the constraint that mentions
--   the `decision` column and is NOT the named audit_actions_hitl_motivation_chk.
--   This is idempotent because the lookup returns 0 rows on the second apply
--   (after the unnamed CHECK has been replaced by our named one).

DO $$
DECLARE
  v_old_decision_check TEXT;
BEGIN
  -- Locate any pre-existing CHECK constraint on audit.actions that references
  -- the `decision` column but is NOT the dual-side hitl motivation guard.
  -- A column-level CHECK that names only the `decision` column appears in
  -- pg_constraint with conkey = ARRAY[<decision attnum>].
  SELECT c.conname
  INTO v_old_decision_check
  FROM pg_constraint c
  JOIN pg_attribute a
    ON a.attrelid = c.conrelid
   AND a.attnum   = ANY(c.conkey)
  WHERE c.conrelid = 'audit.actions'::regclass
    AND c.contype  = 'c'
    AND a.attname  = 'decision'
    AND c.conname <> 'audit_actions_hitl_motivation_chk'
    AND c.conname <> 'audit_actions_decision_chk'   -- our target named constraint
    AND array_length(c.conkey, 1) = 1               -- single-column CHECK only
  LIMIT 1;

  IF v_old_decision_check IS NOT NULL THEN
    EXECUTE format(
      'ALTER TABLE audit.actions DROP CONSTRAINT IF EXISTS %I',
      v_old_decision_check
    );
  END IF;
END $$;

-- Drop our target named constraint if it already exists (idempotency: second-apply
-- path re-creates an identical constraint, semantically a no-op).
ALTER TABLE audit.actions
  DROP CONSTRAINT IF EXISTS audit_actions_decision_chk;

ALTER TABLE audit.actions
  ADD CONSTRAINT audit_actions_decision_chk CHECK (
    decision IN (
      'auto',
      'hitl_operator',
      'hitl_supervisor',
      'hitl_manager',
      'interlock_reject',
      'rolled_back',
      'timed_out',
      'governor_alert',
      'escalated',
      -- Phase 6 extensions:
      'suppressed',           -- D-AD-03: rate-limited proposal dropped before tier
      'logged'                -- D-OA-02: ops-asst observability-only audit row
    )
  );

-- ---------------------------------------------------------------------------
-- action_type CHECK constraint (NEW in Phase 6 — 003 left action_type unconstrained)
-- ---------------------------------------------------------------------------
-- Add a named CHECK on action_type listing all Phase 1-5 + Phase 6 labels.
-- Idempotent via DROP IF EXISTS + ADD.

ALTER TABLE audit.actions
  DROP CONSTRAINT IF EXISTS audit_actions_action_type_chk;

ALTER TABLE audit.actions
  ADD CONSTRAINT audit_actions_action_type_chk CHECK (
    action_type IN (
      -- Phases 1-5 (matches sft_agents.models.enums.ActionType, pre-Phase 6):
      'WRITE_PLC_SETPOINT',
      'ACTUATOR_COMMAND',
      'FIRMWARE_DEPLOY',
      'NETWORK_ACL_CHANGE',
      'GRAPH_RECURSION_REVIEW',
      'GOVERNOR_ALERT',
      -- Phase 6 extensions:
      'ESCALATION_REQUEST',   -- D-OA-02 / Pitfall §9: EscalateToSupervisorTool audit
      'QUALITY_VERDICT',      -- D-QI-02: quality-inspector verdict audit row
      'SCHEDULE_DRAFT',       -- D-PP-03: production-planner draft audit row
      'ANOMALY_ALERT'         -- D-AD-01: anomaly-detector alert audit row
    )
  );
