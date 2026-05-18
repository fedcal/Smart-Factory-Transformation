---
phase: 04-core-agentic-runtime-hitl
plan: 06
subsystem: hitl-middleware
tags: [hitl, audit-dual-write, safety-interlock, escalation, governor, budget, gdpr-redactor, episodic-memory, long-term-stub, wave-3]
requires:
  - "04-01 (sft-agents SDK foundation — AuditRecord/ApprovalRequest/ProposedAction/BudgetSnapshot/EvidencePanel + Tier/Decision/ActionType enums; Memory ABC)"
  - "04-02 (PG migrations — audit.actions hypertable, hitl.approvals, audit.outbox, budget.executions, REVOKE UPDATE/DELETE on audit.actions)"
  - "04-04 (AuditNatsPublisher — publish_audit/publish_approval_*/publish_governor_alert; extended here with publish_raw for OutboxRetry)"
  - "04-05 (AgentState TypedDict, build_supervisor_graph — consumed by human_approval_node wiring in Plan 04-07)"
provides:
  - "AuditPgWriter — sync INSERT into audit.actions ($1..$13 parameterized, D-56 first half)"
  - "AuditWriter — dual-write orchestrator enforcing D-56 (PG first, then NATS, on failure outbox enqueue)"
  - "OutboxWriter + OutboxRetry — T-04-Outbox-Drop fallback with exponential backoff (2s..3600s cap)"
  - "AuditNatsPublisher.publish_raw — re-publish path used by OutboxRetry (extends Plan 04-04)"
  - "ApprovalQueueWriter — ON CONFLICT DO NOTHING idempotent insert + update_decision raises ApprovalNotFoundError (T-04-Resume-Replay)"
  - "human_approval_node — full interrupt()/Command(resume=) cycle (HITL-01,04,06,07) with audit dual-write step"
  - "GDPRRedactor — module-level regex constants strip phone/email/codice fiscale from EvidencePanel.input_summary (T-04-Checkpoint-PII)"
  - "EpisodicReplay — read-only Memory projection of audit.actions (CORE-08, D-59) with LIMIT 1000 and $1/$2 parameterized SQL"
  - "StubLongTermMemory + StubLongTermMemoryConfig + LongTermMemory alias — D-59 contract anchor (Phase 5 swaps in QdrantLongTermMemory)"
  - "SafetyInterlockMiddleware + SafetyInterlockRejection — HITL-03 whitelist enforcement with interlock_reject audit (T-04-Whitelist-Bypass)"
  - "EscalationSupervisor — D-57 background task; operator(2m)→supervisor(15m)→manager(60m)→timed_out + governor.alert; safety_interlock filtered out"
  - "Governor — D-58 sliding-window scan (1h window, min_sample=20, threshold=0.80) with 5-min cooldown; emits audit governor_alert + NATS + Manager-tier approval"
  - "BudgetTracker — D-60 ON CONFLICT (thread_id, agent_id) DO UPDATE UPSERT with soft/hard threshold approval emission"
  - "safety-interlock.yaml + escalation-sla.yaml + budgets.yaml — D-57/D-58/D-60 policy files"
affects:
  - "Unblocks Plan 04-07: api-gateway wires human_approval_node into build_supervisor_graph; safe_invoke catches GraphInterrupt + returns approval_id for UI poll"
  - "Unblocks Plan 04-08: replay tool consumes EpisodicReplay.replay_thread to reconstruct timelines from audit.actions"
  - "Phase 5 (KNW cluster): swaps memory/long_term_stub.py body with QdrantLongTermMemory (D-59 — same method signatures, same import path)"
tech_stack:
  added:
    - "audit.outbox SQL constants (T-V5-sql parameterized + module-level INSERT/SELECT/UPDATE)"
    - "fnmatch-style NATS subject prefix matching (.> → startswith) for SafetyInterlockMiddleware"
    - "Pydantic ApprovalDecision Literal['approve','reject','escalate'] for resume payload validation"
  patterns:
    - "ot-bridge background-loop pattern replicated for OutboxRetry/EscalationSupervisor/Governor (asyncio.wait_for + shutdown_event + CancelledError re-raise)"
    - "D-56 dual-write invariant: PG first (sync re-raise), NATS async (outbox on failure)"
    - "sha256-deterministic approval id derived from (thread_id, action_id) — idempotent re-execution after interrupt() (Pitfall §6)"
    - "ON CONFLICT (id) DO NOTHING with RETURNING — idempotent INSERT pattern"
    - "Module-level compiled regex constants for GDPR redaction (defense-in-depth vs YAML tampering)"
key_files:
  created:
    - packages/sft-agents/src/sft_agents/audit/pg_writer.py
    - packages/sft-agents/src/sft_agents/audit/writer.py
    - packages/sft-agents/src/sft_agents/audit/outbox.py
    - packages/sft-agents/src/sft_agents/hitl/__init__.py
    - packages/sft-agents/src/sft_agents/hitl/interrupt.py
    - packages/sft-agents/src/sft_agents/hitl/approval_queue.py
    - packages/sft-agents/src/sft_agents/hitl/redactor.py
    - packages/sft-agents/src/sft_agents/memory/__init__.py
    - packages/sft-agents/src/sft_agents/memory/episodic.py
    - packages/sft-agents/src/sft_agents/memory/long_term_stub.py
    - packages/sft-agents/src/sft_agents/policies/safety_interlock.py
    - packages/sft-agents/src/sft_agents/policies/safety-interlock.yaml
    - packages/sft-agents/src/sft_agents/policies/escalation-sla.yaml
    - packages/sft-agents/src/sft_agents/policies/budgets.yaml
    - packages/sft-agents/src/sft_agents/runtime/escalation.py
    - packages/sft-agents/src/sft_agents/runtime/governor.py
    - packages/sft-agents/src/sft_agents/runtime/budget.py
    - packages/sft-agents/tests/test_audit_writer.py
    - packages/sft-agents/tests/test_long_term_stub.py
  modified:
    - packages/sft-agents/src/sft_agents/audit/__init__.py
    - packages/sft-agents/src/sft_agents/audit/nats_publisher.py
    - packages/sft-agents/tests/test_hitl_cycle.py
    - packages/sft-agents/tests/test_safety_interlock.py
    - packages/sft-agents/tests/test_escalation.py
    - packages/sft-agents/tests/test_governor.py
    - packages/sft-agents/tests/test_budget.py
    - packages/sft-agents/tests/test_rate_limit_audit_query.py
decisions:
  - "Defense-in-depth GDPR redactor: regex constants in Python source (NOT YAML) so disabling redaction requires PR+code-review tamper-evidence (resolves W4 open question)"
  - "EpisodicReplay queries audit.actions directly via asyncpg rather than wrapping Phase 3 query_timescale tool — the tool returns generic tuples while EpisodicReplay needs AuditRecord-shaped hydration"
  - "Audit outbox bump SQL inlines exponential-backoff seconds as a server-side INTERVAL literal (PostgreSQL disallows parameter binding inside INTERVAL); the integer is clamped to [0, 3600] before string interpolation (defense-in-depth, never user input)"
  - "Governor uses cluster='ops' as the system marker on its audit row (Plan 04-01 enum does not include 'system'; the cluster field is required NOT NULL)"
  - "Integration tests gated behind @pytest.mark.integration; unit tests with mock_pool/mock_nats_js fixtures cover all branches without requiring docker; full e2e PG/NATS round-trip lives in tests/integration/ owned by Plan 04-07 api-gateway"
metrics:
  duration_minutes: 32
  task_count: 4
  files_created: 19
  files_modified: 8
  tests_added: 69
  total_test_runs: 4
  final_suite: "292 passed, 2 skipped (1.82s)"
completed: 2026-05-18T18:00:00Z
---

# Phase 04 Plan 06: HITL Middleware Summary

One-liner: shipped the full HITL interrupt-to-resume cycle with D-56 audit dual-write (PG-first + NATS-async + outbox retry), Safety Interlock whitelist enforcement, 4-tier escalation supervisor with D-57 SLA timers, 80% approval-rate Governor with cooldown, BudgetTracker UPSERT with soft/hard thresholds, GDPR redactor for EvidencePanel.input_summary, EpisodicReplay over audit.actions, and the StubLongTermMemory Phase-5 contract anchor — 19 production modules + 3 YAML policy files + 69 unit tests, full suite green at 292 pass / 2 skip.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Audit dual-write (pg_writer + writer + outbox retry) | c880f8b | `packages/sft-agents/src/sft_agents/audit/{pg_writer,writer,outbox,nats_publisher,__init__}.py` + `tests/test_audit_writer.py` |
| 2 | HITL interrupt/resume + GDPR redactor + EpisodicReplay + StubLongTermMemory | eea69c9 | `packages/sft-agents/src/sft_agents/hitl/{interrupt,approval_queue,redactor,__init__}.py` + `memory/{episodic,long_term_stub,__init__}.py` + `policies/escalation-sla.yaml` + tests |
| 3 | SafetyInterlock + EscalationSupervisor + policy YAMLs | 183d936 | `policies/{safety_interlock.py,safety-interlock.yaml,budgets.yaml}` + `runtime/escalation.py` + tests |
| 4 | Governor + BudgetTracker | 6fdf45b | `runtime/{governor,budget}.py` + tests |

## Verification

- 69 unit tests (test_audit_writer 14, test_hitl_cycle 12, test_rate_limit_audit_query 7, test_long_term_stub 7, test_safety_interlock 6, test_escalation 6, test_governor 7, test_budget 10)
- Full sft-agents suite: 292 passed, 2 skipped, 2 deselected (1.82s)
- Lint: 31 ruff warnings carried over from pre-Plan-04-06 baseline; ZERO new warnings introduced by this plan
- All SQL parameterized + module-level constants (T-V5-sql confirmed)
- No `yaml.load` (unsafe) anywhere; only `yaml.safe_load`
- StubLongTermMemory contract row (D-59 CONTEXT.md lines 285-298): `query()→[]`, `store()→NotImplementedError("Phase 5 supplies QdrantLongTermMemory")`, `LongTermMemory is StubLongTermMemory` alias confirmed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] AuditPgWriter `_INSERT_SQL` placeholder count widened from $11 to $13**
- **Found during:** Task 1 — schema migration `003_create_audit_actions.sql` includes `id` and `ts` columns NOT in the plan's 11-arg shape; the hypertable PK is `(ts, id)` so both must be passed explicitly (no DB default that the writer relies on).
- **Fix:** Use `$1..$13` for all audit-row fields (id, ts, action_id, agent_id, thread_id, cluster, action_type, evidence_panel, decision, decision_actor, motivation, budget_snapshot, approval_id).
- **Files:** `packages/sft-agents/src/sft_agents/audit/pg_writer.py`
- **Commit:** c880f8b

**2. [Rule 3 - Blocking] OutboxRetry exponential-backoff SQL inlines INTERVAL literal**
- **Found during:** Task 1 — PostgreSQL disallows parameter binding inside an INTERVAL literal (`INTERVAL '$1s'` is a syntax error). The backoff seconds must be embedded in the SQL string.
- **Fix:** Wrap the SQL build in `_build_bump_sql(seconds: int) -> str` that asserts `0 ≤ seconds ≤ 3600` (clamped from `_backoff_seconds`) BEFORE string formatting — the integer is never user input.
- **Files:** `packages/sft-agents/src/sft_agents/audit/outbox.py`
- **Commit:** c880f8b

**3. [Rule 2 - Critical] AuditWriter swallows outbox enqueue failure (D-56 invariant)**
- **Found during:** Task 1 — if both NATS publish AND outbox enqueue fail, re-raising would corrupt the D-56 contract (PG row exists, agent already wrote the audit). The audit is durable in PG (source of truth).
- **Fix:** Log `audit_outbox_enqueue_failed` at error level (Phase 11 alerting will catch via structlog sink) but do NOT re-raise.
- **Files:** `packages/sft-agents/src/sft_agents/audit/writer.py`
- **Commit:** c880f8b

**4. [Rule 3 - Blocking] Test backoff assertion adjusted to match real cap**
- **Found during:** Task 1 TDD GREEN — the plan asserted `_backoff_seconds(10) == 3600` but `min(2**11, 3600) == 2048`. The cap engages at attempts=11 (`min(2**12, 3600) == 3600`).
- **Fix:** Test now asserts `_backoff_seconds(11) == 3600` and `_backoff_seconds(100) == 3600`.
- **Files:** `packages/sft-agents/tests/test_audit_writer.py`
- **Commit:** c880f8b

**5. [Rule 3 - Blocking] `escalation-sla.yaml` shipped in Task 2 (not Task 3)**
- **Found during:** Task 2 — `human_approval_node` loads escalation-sla.yaml to compute `sla_deadline`. The plan's commit ordering assigned the YAML to Task 3, but Task 2 imports it.
- **Fix:** Ship `escalation-sla.yaml` in the Task 2 commit; Task 3 still authors `safety-interlock.yaml` + `budgets.yaml`.
- **Files:** `packages/sft-agents/src/sft_agents/policies/escalation-sla.yaml`
- **Commit:** eea69c9

### Authentication Gates

None — all tests are pure unit-level with mocked asyncpg pools + mocked AuditNatsPublisher.

## Threat Mitigations Implemented

| Threat | Mitigation | Files |
|--------|------------|-------|
| T-04-Audit-Tamper | DB REVOKE (Plan 04-02) + AuditWriter PG-first invariant — re-raises on PG failure, NEVER NATS-only audit | `audit/writer.py`, `audit/pg_writer.py` |
| T-04-Outbox-Drop | OutboxWriter.enqueue on NATS failure; OutboxRetry exp backoff (2s..3600s); max 10 attempts then dead-letter | `audit/outbox.py`, `audit/writer.py` |
| T-04-Bypass-HITL | interrupt() persists checkpoint before pause; resume validates ApprovalDecision via Pydantic | `hitl/interrupt.py` |
| T-04-Whitelist-Bypass | SafetyInterlockMiddleware enforces YAML whitelist via prefix-match + frozenset; interlock_reject audit before raise; no UI override | `policies/safety_interlock.py`, `policies/safety-interlock.yaml` |
| T-04-LLM-Inject | ApprovalDecision Pydantic min_length=1 motivation; EvidencePanel attached at every interrupt; Governor cooldown anti-thrash | `hitl/interrupt.py`, `runtime/governor.py` |
| T-04-Checkpoint-PII | GDPRRedactor module-level regex constants (not YAML) strip phone/email/CF before checkpoint write; PR+review required to disable | `hitl/redactor.py` |
| T-04-Resume-Replay | ApprovalQueueWriter.update_decision raises ApprovalNotFoundError on 0-row UPDATE; INSERT uses ON CONFLICT (id) DO NOTHING with sha256-deterministic id | `hitl/approval_queue.py`, `hitl/interrupt.py` |
| T-04-Budget-Exhaust | BudgetTracker UPSERT every step; soft 80% tokens/duration → Operator approval; hard cost > limit → Supervisor approval | `runtime/budget.py` |

## Known Stubs

| File | Lines | Reason |
|------|-------|--------|
| `packages/sft-agents/src/sft_agents/memory/long_term_stub.py` | 1-90 | INTENTIONAL — D-59 contract anchor. Phase 5 (KNW cluster) replaces this module with `QdrantLongTermMemory` having identical method signatures (BGE-M3 + Qdrant). `query()` returns `[]`, `store()` raises NotImplementedError with Phase-5 marker. |

## Deferred Issues

- 31 pre-existing ruff lint warnings (UP012/UP017/UP041/UP037 — datetime.UTC alias, encode() argument, TimeoutError builtin, quote-annotated forward refs). Carried from pre-Plan-04-06 baseline. Cleanup deferred to a dedicated `chore(04): ruff --fix` commit so this plan's diff stays focused on functionality.
- Real testcontainers PG + NATS round-trip for AuditWriter and EscalationSupervisor: deferred to `tests/integration/` (Plan 04-07 api-gateway owns the full e2e suite per CONTEXT.md Wave 4 plan).

## Self-Check: PASSED

- All 19 created files present: VERIFIED (`ls packages/sft-agents/src/sft_agents/{hitl,memory,policies,audit,runtime}/`)
- All 4 task commits in git log: VERIFIED (c880f8b, eea69c9, 183d936, 6fdf45b)
- Full sft-agents non-integration test suite: 292 passed, 2 skipped, 2 deselected (1.82s)
- StubLongTermMemory contract: `from sft_agents.memory import LongTermMemory, StubLongTermMemory; assert LongTermMemory is StubLongTermMemory` exits 0
