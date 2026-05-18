---
phase: 04-core-agentic-runtime-hitl
plan: 06
type: execute
wave: 3
depends_on: ["04-01", "04-02", "04-04", "04-05"]
files_modified:
  - packages/sft-agents/src/sft_agents/hitl/__init__.py
  - packages/sft-agents/src/sft_agents/hitl/interrupt.py
  - packages/sft-agents/src/sft_agents/hitl/approval_queue.py
  - packages/sft-agents/src/sft_agents/hitl/redactor.py
  - packages/sft-agents/src/sft_agents/audit/writer.py
  - packages/sft-agents/src/sft_agents/audit/pg_writer.py
  - packages/sft-agents/src/sft_agents/audit/outbox.py
  - packages/sft-agents/src/sft_agents/policies/safety_interlock.py
  - packages/sft-agents/src/sft_agents/policies/safety-interlock.yaml
  - packages/sft-agents/src/sft_agents/policies/escalation-sla.yaml
  - packages/sft-agents/src/sft_agents/policies/budgets.yaml
  - packages/sft-agents/src/sft_agents/runtime/budget.py
  - packages/sft-agents/src/sft_agents/runtime/escalation.py
  - packages/sft-agents/src/sft_agents/runtime/governor.py
  - packages/sft-agents/src/sft_agents/memory/__init__.py
  - packages/sft-agents/src/sft_agents/memory/episodic.py
  - packages/sft-agents/src/sft_agents/memory/long_term_stub.py
  - packages/sft-agents/tests/test_hitl_cycle.py
  - packages/sft-agents/tests/test_safety_interlock.py
  - packages/sft-agents/tests/test_escalation.py
  - packages/sft-agents/tests/test_governor.py
  - packages/sft-agents/tests/test_budget.py
  - packages/sft-agents/tests/test_audit_writer.py
  - packages/sft-agents/tests/test_rate_limit_audit_query.py
  - packages/sft-agents/tests/test_long_term_stub.py
autonomous: true
requirements: [HITL-01, HITL-02, HITL-03, HITL-04, HITL-05, HITL-06, HITL-07, HITL-08, HITL-09, HITL-10, CORE-08, CORE-09]
threat_refs: [T-04-Bypass-HITL, T-04-LLM-Inject, T-04-Audit-Tamper, T-04-Outbox-Drop, T-04-Budget-Exhaust, T-04-Whitelist-Bypass, T-04-Checkpoint-PII, T-04-Resume-Replay]

must_haves:
  truths:
    - "Calling `human_approval_node(state)` emits an ApprovalRequest row in PG hitl.approvals, publishes NATS `hitl.approvals.new.<tier>`, then `interrupt()` returns; resuming via `Command(resume=ApprovalDecision)` updates the PG row + writes an AuditRecord with motivation required for hitl_* decisions (HITL-01, HITL-04, HITL-06, HITL-07)"
    - "Audit dual-write: PG INSERT into audit.actions is sync blocking (agent ABORTS if PG fails); NATS publish is fire-and-forget with audit.outbox fallback retry (D-56 + T-04-Outbox-Drop)"
    - "SafetyInterlockMiddleware runs PRE every ToolNode; if action.target_subject matches safety-interlock.yaml forbidden_subjects OR action.action_type ∈ forbidden_action_types → audit `decision=interlock_reject` + raise SafetyInterlockRejection (HITL-03, T-04-Whitelist-Bypass)"
    - "EscalationSupervisor background asyncio task scans hitl.approvals WHERE status='pending' AND sla_deadline < NOW() every 30s; per row creates next-tier approval + marks original status='escalated' + emits audit `decision=escalated`; Manager tier alert only, no further escalation; Safety Interlock never times out (D-57)"
    - "Governor background asyncio task scans audit.actions WHERE ts > NOW() - INTERVAL '1 hour' every 60s; if auto_rate > 0.80 AND count(*) >= 20 → audit `decision=governor_alert` + NATS hitl.governor.alert + Manager-tier ApprovalRequest (HITL-09, D-58)"
    - "BudgetTracker middleware UPSERTs budget.executions on every step; soft threshold 80% tokens → operator ApprovalRequest; hard threshold cost/duration > limit → supervisor ApprovalRequest (CORE-09, D-60)"
    - "GDPRRedactor pre-checkpoint pass strips PII fields from EvidencePanel.input_summary (A-013..A-018) before checkpoint write — mitigates T-04-Checkpoint-PII"
    - "EpisodicReplay.replay_thread(thread_id, since) returns list[AuditRecord] via query_timescale Phase 3 tool (D-59 episodic memory; CORE-08)"
    - "StubLongTermMemory exists and query() returns [] for any input (Phase 4 → Phase 5 contract anchor for CORE-08; D-59 long-term stub)"
  artifacts:
    - path: packages/sft-agents/src/sft_agents/hitl/interrupt.py
      provides: "human_approval_node + ApprovalQueueWriter (PG INSERT) + NATS notify (publish_approval_new) + interrupt() + resume path"
      contains: "def human_approval_node"
    - path: packages/sft-agents/src/sft_agents/audit/writer.py
      provides: "AuditWriter orchestrator: PG sync FIRST + NATS async + outbox retry"
      contains: "class AuditWriter"
    - path: packages/sft-agents/src/sft_agents/policies/safety_interlock.py
      provides: "SafetyInterlockMiddleware + SafetyInterlockRejection exception"
      contains: "class SafetyInterlockMiddleware"
    - path: packages/sft-agents/src/sft_agents/runtime/escalation.py
      provides: "EscalationSupervisor background asyncio task (D-57 timers 2/15/60min)"
      contains: "class EscalationSupervisor"
    - path: packages/sft-agents/src/sft_agents/runtime/governor.py
      provides: "Governor background asyncio task (D-58 1h sliding window, 80% threshold, 20 sample minimum)"
      contains: "class Governor"
    - path: packages/sft-agents/src/sft_agents/runtime/budget.py
      provides: "BudgetTracker middleware node + PG UPSERT on budget.executions"
      contains: "class BudgetTracker"
    - path: packages/sft-agents/src/sft_agents/memory/episodic.py
      provides: "EpisodicReplay class using query_timescale on audit.actions"
      contains: "class EpisodicReplay"
    - path: packages/sft-agents/src/sft_agents/memory/long_term_stub.py
      provides: "StubLongTermMemory placeholder (D-59) — Phase 5 supplies QdrantLongTermMemory"
      contains: "class StubLongTermMemory"
  key_links:
    - from: packages/sft-agents/src/sft_agents/hitl/interrupt.py
      to: langgraph.types.interrupt
      via: "interrupt() call site after persisting ApprovalRequest"
      pattern: "interrupt\\("
    - from: packages/sft-agents/src/sft_agents/audit/writer.py
      to: packages/sft-agents/src/sft_agents/audit/pg_writer.py + nats_publisher.py + outbox.py
      via: "AuditWriter.write() → pg_writer.insert() (sync) → nats_publisher.publish_audit() (async) → on fail, outbox.enqueue()"
      pattern: "AuditWriter|publish_audit|outbox"
    - from: packages/sft-agents/src/sft_agents/runtime/escalation.py
      to: packages/sft-agents/src/sft_agents/policies/escalation-sla.yaml
      via: "yaml.safe_load on init"
      pattern: "escalation-sla.yaml"
    - from: packages/sft-agents/src/sft_agents/memory/long_term_stub.py
      to: packages/sft-agents/src/sft_agents/sdk/memory.py
      via: "class StubLongTermMemory(Memory)"
      pattern: "class StubLongTermMemory\\(Memory\\)"
---

<objective>
Wave 3 Plan B: ship the HITL middleware + audit dual-write + safety interlock + escalation/governor/budget background tasks + GDPR redactor + episodic memory + long-term memory stub. This plan delivers the heart of Phase 4 — the full interrupt-to-resume HITL cycle with immutable audit, 4-tier escalation, safety blocking, approval-rate governance, budget enforcement, and the long-term memory contract anchor for Phase 5.

Purpose: deliver HITL-01..10 (interrupt+resume, 4-tier escalation, Safety Interlock whitelist, approval queue persistence, audit immutability, evidence panel, motivation-required, rollback substrate, governor 80% threshold, rate-limit alarm primitive), CORE-08 final (episodic memory via NATS+TimescaleDB replay + StubLongTermMemory per D-59), CORE-09 final (budget tracker enforcement).

Output: 14 production Python modules + 3 YAML policy files + 8 unskipped tests covering full HITL cycle (interrupt → PG persist → NATS notify → resume → audit dual-write), safety interlock whitelist enforcement, escalation chain (2/15/60min timers), governor sliding-window alert, budget UPSERT + ApprovalRequest emit, audit dual-write with outbox retry, episodic replay, and the long-term memory stub contract.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md
@.planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md
@.planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md
@.planning/phases/04-core-agentic-runtime-hitl/04-VALIDATION.md
@services/ot-bridge/src/svc_ot_bridge/timescale_writer.py
@services/ot-bridge/src/svc_ot_bridge/nats_publisher.py
@services/ot-bridge/src/svc_ot_bridge/main.py
@packages/sft-domain/src/sft_domain/glossary/_loader.py
@packages/sft-tools/src/sft_tools/timescale/query.py

<interfaces>
human_approval_node contract (HITL-01, HITL-04, HITL-06, HITL-07):
```
async def human_approval_node(
    state: AgentState,
    *,
    proposed_action: ProposedAction,
    evidence_panel: EvidencePanel,
    pg_pool, nats_publisher,
) -> AgentState:
    """
    1. Compute sla_deadline from escalation-sla.yaml (per tier)
    2. INSERT row into hitl.approvals (status='pending') via asyncpg pool
    3. Build ApprovalRequest from row → publish NATS hitl.approvals.new.<tier> via AuditNatsPublisher
    4. Call interrupt({"approval_id": id, "tier": tier, "payload": ...}) — LangGraph persists checkpoint + pauses
    5. On resume: receive ApprovalDecision (decision, motivation, decided_by) via Command(resume=)
    6. UPDATE hitl.approvals row (status, decided_at, decided_by, decision_json) via asyncpg
    7. Publish NATS hitl.approvals.resolved.<tier>
    8. Build AuditRecord (decision in {hitl_operator, hitl_supervisor, hitl_manager} → motivation required, approval_id set) → AuditWriter.write(record)
    9. Return updated state (pending_approval_id cleared, evidence attached)
    """
```

AuditWriter contract (D-56, T-04-Outbox-Drop):
- `class AuditWriter`: __init__ stores pg_pool + nats_publisher + outbox_writer
- `async def write(self, record: AuditRecord) -> None`:
  1. PG INSERT into audit.actions (sync; if fails → log error + re-raise → agent ABORTS, no fake audit)
  2. Try publish NATS via nats_publisher.publish_audit(record)
  3. On NATS failure: log warning + INSERT into audit.outbox (subject, payload_json, next_attempt_at=NOW())
- `OutboxRetry` background task: every 30s SELECT FROM audit.outbox WHERE next_attempt_at < NOW() AND attempts < 10 LIMIT 50 → re-publish via nats_publisher; on success UPDATE published_at; on failure UPDATE attempts++ + next_attempt_at = NOW() + EXP_BACKOFF(attempts)

SafetyInterlockMiddleware (HITL-03, D-58, T-04-Whitelist-Bypass):
- `class SafetyInterlockMiddleware`: __init__ loads safety-interlock.yaml via yaml.safe_load
- `async def check(self, action: ProposedAction) -> None`:
  - Match action.target_subject against forbidden_subjects glob list (`cmd.plc.setpoint.>` etc.)
  - Match action.action_type against forbidden_action_types
  - If match → audit `decision=interlock_reject` + raise SafetyInterlockRejection
  - Else → return None (pass-through)
- LangGraph wire: this is a Policy class invoked PRE every ToolNode (via Agent.policy.pre_tool_check from Plan 04-01 ABC)

EscalationSupervisor (D-57):
- `class EscalationSupervisor`: __init__ stores pg_pool, nats_publisher, audit_writer, scan_interval_s=30
- Loads `escalation-sla.yaml`: operator→supervisor (2min), supervisor→manager (15min), manager→null (60min alert only), safety_interlock→null (no timeout)
- `async def run(self)`: while not self._shutdown: scan PG `SELECT id, tier, agent_id, thread_id FROM hitl.approvals WHERE status='pending' AND sla_deadline < NOW() AND tier <> 'safety_interlock' LIMIT 100`; for each row: determine next_tier from yaml; if next_tier is None (manager) → audit `decision=timed_out` + NATS hitl.governor.alert (Manager-tier-only); else INSERT new row at next_tier + UPDATE original status='escalated' escalated_to_id=new_id + audit `decision=escalated`
- Pattern: replicate `services/ot-bridge/src/svc_ot_bridge/main.py:114-168` worker loop with `asyncio.wait_for` + shutdown_event

Governor (HITL-09, D-58):
- `class Governor`: __init__ stores pg_pool, nats_publisher, audit_writer, scan_interval_s=60, threshold=0.80, min_sample_size=20, window_hours=1
- `async def run(self)`: while not self._shutdown: SELECT count(*) FILTER (WHERE decision='auto') AS auto_count, count(*) AS total FROM audit.actions WHERE ts > NOW() - INTERVAL '1 hour' AND decision NOT IN ('escalated','governor_alert'); if total >= 20 AND (auto_count / total) > 0.80: emit audit `decision=governor_alert` + NATS hitl.governor.alert payload {auto_rate, sample_size, window_start, window_end, top_agents (separate query GROUP BY agent_id ORDER BY count DESC LIMIT 5)} + create Manager-tier ApprovalRequest action_type=GOVERNOR_ALERT
- Use parameterized SQL ($1..$N), statement_cache_size=0 (Phase 3 idiom)

BudgetTracker middleware (CORE-09, D-60):
- `class BudgetTracker`: __init__ stores pg_pool, audit_writer, limits_yaml_path
- Loads `budgets.yaml` per cluster + agent_id override
- `async def track(self, state: AgentState, step_input_tokens: int, step_output_tokens: int, step_cost_usd: float, step_duration_ms: int) -> AgentState`:
  - UPSERT budget.executions: INSERT (thread_id, agent_id, tokens_total=$3, cost_usd=$4, duration_ms=$5, step_count=1) ON CONFLICT (thread_id, agent_id) DO UPDATE SET tokens_total=budget.executions.tokens_total + EXCLUDED.tokens_total, cost_usd=budget.executions.cost_usd + EXCLUDED.cost_usd, duration_ms=budget.executions.duration_ms + EXCLUDED.duration_ms, step_count=budget.executions.step_count + 1, last_step_at=NOW()
  - SELECT current row totals; compare against limits:
    - tokens_total > 0.80 * limit_tokens → emit Operator-tier ApprovalRequest (soft)
    - cost_usd > limit_cost_usd → emit Supervisor-tier ApprovalRequest (hard, blocking)
    - duration_ms > limit_duration_s * 1000 → emit Operator-tier ApprovalRequest (soft)
  - Update state.budget with current BudgetSnapshot
- Wire: middleware decorator on every LLM call (via BudgetingChatModel.ainvoke wrapping from Plan 04-03) + ToolNode invocation (decorator pattern)

GDPRRedactor (T-04-Checkpoint-PII):
- `class GDPRRedactor`: pure function `redact(state: AgentState) -> AgentState`
- Regex sources: module-level compiled `re.Pattern` constants in `gdpr/redactor.py` (phone/email/codice_fiscale). NO external YAML file — the regexes are stable, project-owned, and version-controlled in source for tamper-evidence (T-04-Checkpoint-PII defense-in-depth: an attacker editing a YAML on disk could disable redaction; constants force a code+PR change).
- Strips matching patterns from EvidencePanel.input_summary (replace with [REDACTED-PHONE] etc.) before checkpoint write
- Wire: middleware called inside graph state reducer or right before checkpointer.aput()

EpisodicReplay (CORE-08, D-59):
- `class EpisodicReplay(MemoryStore)` subclass of Plan 04-01 ABC
- `async def replay_thread(self, thread_id: str, since: datetime | None = None) -> list[AuditRecord]`: use query_timescale Tool (Phase 3) wrapping `SELECT * FROM audit.actions WHERE thread_id=$1 AND ts >= $2 ORDER BY ts ASC`; deserialize each row to AuditRecord Pydantic model
- `async def query(self, query: str, k: int = 5, filters: dict | None = None) -> list[MemoryRecord]`: implements abstract method — converts AuditRecord rows to MemoryRecord (content=evidence_panel.input_summary, kind='episodic'); k limits result count
- `async def store(self, record: MemoryRecord) -> str`: NOT directly callable — episodic memory is read-only projection of audit log; raises NotImplementedError("EpisodicReplay is read-only; episodes are created via AuditWriter")

StubLongTermMemory (CORE-08 long-term stub, D-59 CONTEXT.md lines 285-298):
- `class StubLongTermMemory(Memory)` subclass of Plan 04-01 `sft_agents.sdk.memory.Memory` ABC
- `async def query(self, query: str, k: int = 5, filters: dict | None = None) -> list[MemoryRecord]`: returns `[]` for ANY input (no Qdrant client; placeholder for Phase 5)
- `async def store(self, record: MemoryRecord) -> str`: raises `NotImplementedError("Phase 5 supplies QdrantLongTermMemory (D-59); long-term storage is not available in Phase 4")`
- Optional Pydantic v2 config dataclass `class StubLongTermMemoryConfig(BaseModel)` with `model_config = {"frozen": True, "extra": "forbid"}` — empty body Phase 4, fields added by Phase 5 (collection_name, qdrant_url, embedding_model). Phase 4 ships the class with no fields so Phase 5 can extend without breaking imports.
- Contract anchor: Phase 5 (KNW cluster) replaces this module with `QdrantLongTermMemory` having identical method signatures (BGE-M3 embedding + Qdrant search). Phase 4 freezes the import path `from sft_agents.memory.long_term_stub import StubLongTermMemory` AND the broader `from sft_agents.memory import LongTermMemory` (re-exported alias) so downstream agents (Plan 04-07 api-gateway, Phase 6-9 cluster agents) can depend on the symbol today.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <id>04-06-01</id>
  <name>Task 1: Audit dual-write (pg_writer + writer orchestrator + outbox retry) + audit_writer test</name>
  <files>packages/sft-agents/src/sft_agents/audit/__init__.py, packages/sft-agents/src/sft_agents/audit/pg_writer.py, packages/sft-agents/src/sft_agents/audit/writer.py, packages/sft-agents/src/sft_agents/audit/outbox.py, packages/sft-agents/tests/test_audit_writer.py</files>
  <read_first>
    services/ot-bridge/src/svc_ot_bridge/timescale_writer.py (ENTIRE file — pool + _INSERT_SQL + executemany + _flush_loop pattern; especially lines 30-34, 82-91, 108-144, 146-158)
    services/ot-bridge/src/svc_ot_bridge/nats_publisher.py (publish_audit method lines 120-132)
    services/ot-bridge/src/svc_ot_bridge/main.py (publisher+writer orchestration lines 158-159)
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-56 audit dual-write ordering invariant)
    .planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md (§3.7 — 1:1 dual-write replica; §4.1 audit dual-write idiom; §4.2 background asyncio loop)
    packages/sft-agents/src/sft_agents/audit/nats_publisher.py (Plan 04-04 — AuditNatsPublisher consumer)
  </read_first>
  <behavior>
    - `AuditPgWriter(pool).insert(record: AuditRecord)` executes INSERT into audit.actions with $1..$N placeholders; on success returns the row id; on failure logs error + raises
    - `AuditWriter(pg_writer, nats_publisher, outbox_writer).write(record)`:
      - First: pg_writer.insert(record) — sync; on exception re-raises (agent ABORTS — D-56 invariant)
      - Then: try nats_publisher.publish_audit(record); on success log debug; on exception log warning + outbox_writer.enqueue(subject, payload_bytes)
    - `OutboxWriter(pool).enqueue(subject, payload)`: INSERT into audit.outbox (subject, payload_json) DEFAULT next_attempt_at=NOW()
    - `OutboxRetry(pool, nats_publisher, interval_s=30, max_attempts=10).run()`: background loop SELECT outbox rows next_attempt_at < NOW() AND attempts < 10 LIMIT 50; per row publish via nats_publisher.publish_raw(subject, payload); on success UPDATE outbox.published_at; on failure UPDATE attempts=attempts+1, next_attempt_at=NOW() + exp_backoff(attempts) where backoff = min(2^attempts, 3600) seconds; structlog throughout
    - Integration test: with testcontainers PG + NATS, force a NATS unavailability (drain publisher mid-test), call AuditWriter.write → assert PG row inserted + outbox row created; restore NATS, call OutboxRetry.run_once → assert outbox row marked published_at and NATS stream contains the message
  </behavior>
  <action>
    `audit/pg_writer.py`: `class AuditPgWriter`: `__init__(self, pool: asyncpg.Pool)`; module-level constant `_INSERT_SQL = """INSERT INTO audit.actions (id, ts, action_id, agent_id, thread_id, cluster, action_type, evidence_panel, decision, decision_actor, motivation, budget_snapshot, approval_id) VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9,$10,$11,$12::jsonb,$13)"""`. `async def insert(self, record: AuditRecord) -> UUID`: convert record to tuple binding; use `await conn.execute(_INSERT_SQL, ...)` inside pool.acquire context; serialize evidence_panel and budget_snapshot via `record.evidence_panel.model_dump_json()` (asyncpg accepts str for jsonb). structlog log on success at debug, error on fail. Re-raise on failure.
    `audit/outbox.py`: `class OutboxWriter`: `async def enqueue(self, subject: str, payload: bytes) -> UUID`: INSERT into audit.outbox (subject, payload_json) — note payload is bytes, decode to str for JSONB storage (assert UTF-8 valid via .decode("utf-8") which raises if not). `class OutboxRetry`: `async def run_once(self) -> int`: SELECT FROM audit.outbox WHERE published_at IS NULL AND attempts < 10 AND (next_attempt_at < NOW() OR next_attempt_at IS NULL) ORDER BY created_at LIMIT 50; for each row try `self._nats_publisher.publish_raw(row.subject, row.payload_json.encode("utf-8"))`; on success UPDATE published_at=NOW(); on exception UPDATE attempts=attempts+1, last_attempt_at=NOW(), last_error=str(exc), next_attempt_at=NOW() + INTERVAL('{backoff}s'); return count_processed. `async def run(self)`: loop calling run_once every self._interval_s; CancelledError-safe per PATTERNS §4.2.
    `audit/writer.py`: `class AuditWriter`: `__init__(self, pg_writer: AuditPgWriter, nats_publisher: AuditNatsPublisher, outbox_writer: OutboxWriter)`. `async def write(self, record: AuditRecord) -> None`: `await self._pg.insert(record)` (sync first, re-raises); try `await self._nats.publish_audit(record)`; except Exception as exc: log warning(`audit_nats_publish_failed`, error=str(exc)); subject = subject_for_audit(cluster=record.cluster, agent_id=record.agent_id); payload = record.model_dump_json().encode("utf-8"); `await self._outbox.enqueue(subject, payload)`.
    Add `nats_publisher.publish_raw(subject, payload_bytes)` method to AuditNatsPublisher (Plan 04-04) — extend if not present in that plan's spec; this plan adds it explicitly. Refactor that method into the existing nats_publisher.py file.
    Update `audit/__init__.py` to re-export AuditWriter, AuditPgWriter, OutboxWriter, OutboxRetry, AuditNatsPublisher, subject_for_audit, etc.
    `tests/test_audit_writer.py` (NEW, integration): `@pytest.mark.integration`. Fixtures use testcontainers PG + NATS. Test 1 (happy path): create AuditRecord; call AuditWriter.write; assert audit.actions row exists; assert NATS message published. Test 2 (NATS failure): mock nats_publisher.publish_audit to raise ConnectionError; call write; assert PG row exists; assert audit.outbox row exists with attempts=0; assert no exception raised to caller. Test 3 (PG failure): mock pg_writer.insert to raise asyncpg.PostgresError; call write; assert exception re-raises; assert no audit.outbox row created (no fake audit). Test 4 (outbox retry success): seed outbox row; OutboxRetry.run_once() with healthy NATS; assert published_at set, attempts unchanged. Test 5 (outbox retry failure backoff): seed outbox row; OutboxRetry.run_once() with broken NATS; assert attempts=1, next_attempt_at increases by ~2s.

    Conventional commits per file: (1) `feat(04-06-hitl-middleware-01): audit pg_writer asyncpg pattern (replicates ot-bridge timescale_writer)`, (2) `feat(04-06-hitl-middleware-01): audit outbox + retry background task`, (3) `feat(04-06-hitl-middleware-01): audit writer orchestrator with dual-write D-56 invariant`, (4) `test(04-06-hitl-middleware-01): audit writer happy path + NATS failure + PG failure + outbox retry`.
  </action>
  <pattern_ref>services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:30-34 (constant _INSERT_SQL) ; :82-91 (pool with statement_cache_size=0, command_timeout) ; :108-144 (_flush_locked executemany pattern, adapt to single-row) ; :146-158 (_flush_loop async background — replica for OutboxRetry.run) ; services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:120-132 (publish_audit shape)</pattern_ref>
  <threat_ref>T-04-Audit-Tamper (REVOKE enforced at DB level Plan 04-02; AuditWriter respects invariant — PG fail = abort, no NATS-only audit) ; T-04-Outbox-Drop (outbox retry with exp backoff)</threat_ref>
  <done>
    **AuditPgWriter (sync PG write — D-56 first half):**
    - `python -c "from sft_agents.audit import AuditPgWriter; print('ok')"` exits 0
    - `grep -nE 'INSERT INTO audit\.actions' packages/sft-agents/src/sft_agents/audit/pg_writer.py` returns 1 match (constant SQL, not f-string)
    - Test `test_audit_writer.py::test_pg_happy_path` (Test 1) passes: `audit.actions` row exists after `AuditWriter.write`

    **AuditWriter orchestrator (D-56 dual-write invariant):**
    - `python -c "from sft_agents.audit import AuditWriter; print('ok')"` exits 0
    - Test `test_audit_writer.py::test_pg_failure_no_outbox_fallback` (Test 3) passes: when `pg_writer.insert` raises, `AuditWriter.write` re-raises AND no `audit.outbox` row is created (no fake audit)
    - Test `test_audit_writer.py::test_nats_failure_falls_to_outbox` (Test 2) passes: when NATS publish raises, PG row exists AND outbox row exists with attempts=0

    **OutboxWriter + OutboxRetry (T-04-Outbox-Drop):**
    - `python -c "from sft_agents.audit import OutboxWriter, OutboxRetry; print('ok')"` exits 0
    - Test `test_audit_writer.py::test_outbox_retry_success` (Test 4) passes: seeded outbox row gets `published_at` set after `OutboxRetry.run_once()` with healthy NATS
    - Test `test_audit_writer.py::test_outbox_retry_backoff` (Test 5) passes: failing NATS bumps `attempts` to 1 AND `next_attempt_at` increases by ~2s (exp backoff)

    **SQL safety (cross-component):**
    - `grep -nE 'f["\\\'](?=.*INSERT|.*UPDATE|.*SELECT).*\$\{' packages/sft-agents/src/sft_agents/audit/*.py` returns no matches (no f-string SQL — T-V5-sql rule)
    - `grep -nE 'statement_cache_size=0' packages/sft-agents/src/sft_agents/audit/*.py` returns at least 1 match (or in pool init context — verify via lifecycle code path)
  </done>
  <verify>
    <automated>nx test sft-agents --testNamePattern=test_audit_writer</automated>
  </verify>
  <commit_scope>feat(04-06-hitl-middleware)</commit_scope>
</task>

<task type="auto" tdd="true">
  <id>04-06-02</id>
  <name>Task 2: HITL interrupt/resume node + ApprovalQueueWriter + GDPRRedactor + EpisodicReplay + StubLongTermMemory</name>
  <files>packages/sft-agents/src/sft_agents/hitl/__init__.py, packages/sft-agents/src/sft_agents/hitl/interrupt.py, packages/sft-agents/src/sft_agents/hitl/approval_queue.py, packages/sft-agents/src/sft_agents/hitl/redactor.py, packages/sft-agents/src/sft_agents/memory/__init__.py, packages/sft-agents/src/sft_agents/memory/episodic.py, packages/sft-agents/src/sft_agents/memory/long_term_stub.py, packages/sft-agents/tests/test_hitl_cycle.py, packages/sft-agents/tests/test_rate_limit_audit_query.py, packages/sft-agents/tests/test_long_term_stub.py</files>
  <read_first>
    .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md (§9 interrupt/Command round-trip; §10 escalation pattern; Pitfall §6 interrupt node re-runs from start)
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-55 approval queue schema; D-56 audit dual-write; D-58 governor; D-59 episodic memory + long-term stub lines 271-305; A-013..A-018 GDPR PII boundaries)
    packages/sft-agents/src/sft_agents/audit/writer.py (Task 1 — AuditWriter consumer)
    packages/sft-agents/src/sft_agents/audit/subjects.py (Plan 04-04 — subject_for_approval_new + subject_for_approval_resolved)
    packages/sft-agents/src/sft_agents/runtime/state.py (Plan 04-05 — AgentState)
    packages/sft-agents/src/sft_agents/sdk/memory.py (Plan 04-01 — Memory ABC; StubLongTermMemory MUST subclass this)
    packages/sft-tools/src/sft_tools/timescale/query.py (Phase 3 — query_timescale tool, consumed by EpisodicReplay)
    services/ot-bridge/src/svc_ot_bridge/timescale_writer.py (asyncpg $N parameterized INSERT/UPDATE pattern)
  </read_first>
  <behavior>
    - `ApprovalQueueWriter(pool).insert(approval: ApprovalRequest) -> UUID`: INSERT into hitl.approvals with $1..$N; return inserted id
    - `ApprovalQueueWriter(pool).update_decision(id, decision, decided_by, motivation, decided_at) -> None`: UPDATE row WHERE id=$1 AND status='pending' SET status='approved|rejected', decided_at, decided_by, decision_json={"decision":..., "motivation":...}; RETURN rowcount=1 (raise NotFoundError if 0 — protects against T-04-Resume-Replay)
    - `ApprovalQueueWriter(pool).insert_escalation(original_id, new_tier) -> UUID`: in transaction — INSERT new row at new_tier (copy payload from original) RETURNING id + UPDATE original SET status='escalated', escalated_to_id=new_id
    - `human_approval_node(state, *, proposed_action, evidence_panel, pg_pool, nats_publisher, audit_writer, sla_yaml_path) -> dict (state delta)`:
      1. Determine tier from proposed_action.requires_tier
      2. Load sla_minutes from escalation-sla.yaml; sla_deadline = NOW() + sla_minutes (None for safety_interlock)
      3. Build ApprovalRequest; queue_writer.insert(approval) → approval_id
      4. nats_publisher.publish_approval_new(approval)
      5. Call `value = interrupt({"approval_id": str(approval_id), "tier": tier.value, "payload": proposed_action.model_dump(), "evidence_panel": evidence_panel.model_dump()})` — LangGraph persists checkpoint + pauses
      6. After resume: `decision = ApprovalDecision.model_validate(value)` (the resume value must be ApprovalDecision-shaped)
      7. queue_writer.update_decision(approval_id, decision.decision, decision.decided_by, decision.motivation, NOW())
      8. nats_publisher.publish_approval_resolved(approval.model_copy(update={"status": "approved" if decision.decision=="approve" else ...}))
      9. Build AuditRecord (decision=Decision.HITL_OPERATOR/etc based on tier, motivation=decision.motivation, approval_id=approval_id); audit_writer.write(record)
      10. Return state delta: `{"pending_approval_id": None, "evidence": evidence_panel, "proposed_actions": state.proposed_actions - this one}`
    - Pitfall §6 reminder: human_approval_node will re-execute from the top on resume; the INSERT step must be idempotent (use ON CONFLICT DO NOTHING on a deterministic id based on hash(thread_id+action_id) OR rely on idempotent approval_id derived from ProposedAction.id which is sha256-derived per Plan 04-01)
    - `GDPRRedactor.redact(state)` is a pure function applying regex replacements to state.evidence.input_summary (phone, email, codice_fiscale IT regex `^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$`); returns new state with input_truncated unchanged
    - `EpisodicReplay(pool, query_tool).replay_thread(thread_id, since=None) -> list[AuditRecord]`: SELECT FROM audit.actions WHERE thread_id=$1 AND ($2::timestamptz IS NULL OR ts >= $2) ORDER BY ts ASC; deserialize each row to AuditRecord
    - `EpisodicReplay.query(query, k=5, filters=None) -> list[MemoryRecord]`: filter by thread_id if filters contains it, else recent activity per agent_id; map AuditRecord → MemoryRecord
    - `StubLongTermMemory()` (no constructor args) instantiable WITHOUT raising; `await StubLongTermMemory().query("anything", k=5, filters=None)` returns `[]` for ANY input (typed `list[MemoryRecord]`); `await StubLongTermMemory().store(record)` raises `NotImplementedError` with message containing `"Phase 5"` and `"QdrantLongTermMemory"`
    - `from sft_agents.memory.long_term_stub import StubLongTermMemory` resolves; `from sft_agents.memory import StubLongTermMemory` (re-exported) also resolves
  </behavior>
  <action>
    `hitl/approval_queue.py`: `class ApprovalQueueWriter` with constant `_INSERT_SQL` and `_UPDATE_DECISION_SQL` and `_INSERT_ESCALATION_SQL` (transactional) — all parameterized with $N; methods as described. Use `asyncpg` pool acquire context. For idempotency on re-runs after interrupt, the insert uses `INSERT INTO hitl.approvals (id, agent_id, thread_id, tier, action_type, payload_json, status, created_at, sla_deadline) VALUES ($1, ...) ON CONFLICT (id) DO NOTHING RETURNING id` — id is derived from sha256-based ProposedAction.id (Plan 04-01) so re-execution after interrupt produces same id, ON CONFLICT prevents duplicate insert. Add `class ApprovalNotFoundError(LookupError)` raised when update_decision affects 0 rows (T-04-Resume-Replay defense — resume with stale id fails).
    `hitl/interrupt.py`: imports `interrupt` from langgraph.types; `from .approval_queue import ApprovalQueueWriter`; `from sft_agents.audit.subjects import subject_for_approval_new, subject_for_approval_resolved`; `from sft_agents.audit.writer import AuditWriter`. Implements `human_approval_node` as a regular async function that takes state + dependencies; in production this gets wrapped by `functools.partial` to bind pg_pool/nats_publisher/audit_writer/sla_yaml_path at graph-build time. Tier-to-Decision mapping helper: `def tier_to_decision(tier: Tier, approved: bool) -> Decision`: operator+approve → HITL_OPERATOR (audit terminology), supervisor → HITL_SUPERVISOR, manager → HITL_MANAGER, etc. Build AuditRecord using EvidencePanel from input + budget_snapshot from state.budget. Include `idempotency_key` = sha256(thread_id + approval_id) embedded in payload_json for downstream replay deduplication.
    `hitl/redactor.py`: `class GDPRRedactor` with module-level compiled regex constants: `_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,15}\d")`, `_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")`, `_CF_RE = re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b")`. Regexes are Python constants — NOT loaded from any YAML file (defense-in-depth per `<interfaces>` note: tamper-evidence via code+PR review). `def redact_str(s: str) -> str`: applies all 3 substitutions with tokens `[REDACTED-PHONE]`, `[REDACTED-EMAIL]`, `[REDACTED-CF]`. `def redact_evidence(panel: EvidencePanel) -> EvidencePanel`: returns new EvidencePanel via model_copy(update={"input_summary": redact_str(panel.input_summary)}). Optional helper `redact_state(state: AgentState) -> AgentState` for pre-checkpoint wiring.
    `hitl/__init__.py` re-exports `human_approval_node, ApprovalQueueWriter, ApprovalNotFoundError, GDPRRedactor, redact_str, redact_evidence`.
    `memory/episodic.py`: `class EpisodicReplay(MemoryStore)` (where MemoryStore is the Plan 04-01 ABC). Constructor: `__init__(self, *, pool: asyncpg.Pool)` (we connect directly via asyncpg rather than wrap Phase 3 query_timescale, because EpisodicReplay needs the AuditRecord shape — Phase 3 QueryTimescaleTool returns generic tuples). SQL constant `_REPLAY_SQL = """SELECT id, ts, action_id, agent_id, thread_id, cluster, action_type, evidence_panel::text, decision, decision_actor, motivation, budget_snapshot::text, approval_id FROM audit.actions WHERE thread_id=$1 AND ($2::timestamptz IS NULL OR ts >= $2) ORDER BY ts ASC LIMIT 1000"""`. `async def replay_thread(self, thread_id: str, since: datetime | None = None) -> list[AuditRecord]`: execute SQL; per row parse evidence_panel JSON via `EvidencePanel.model_validate_json(row["evidence_panel"])` (preserves the tz-aware validator) and budget_snapshot analogously; build AuditRecord. `async def query(self, query: str, k: int = 5, filters: dict | None = None) -> list[MemoryRecord]`: if filters has thread_id, call replay_thread and limit to k; else SELECT recent rows by agent_id (filters["agent_id"]) or empty. `async def store(self, record: MemoryRecord) -> str`: raise NotImplementedError("EpisodicReplay is read-only; use AuditWriter").
    `memory/long_term_stub.py`: `from __future__ import annotations` + imports `from sft_agents.sdk.memory import Memory` (the Plan 04-01 ABC) + `MemoryRecord` from sft_agents.models. Optional Pydantic v2 frozen config dataclass `class StubLongTermMemoryConfig(BaseModel): model_config = ConfigDict(frozen=True, extra="forbid")` — empty body for Phase 4 (Phase 5 adds collection_name, qdrant_url, embedding_model). `class StubLongTermMemory(Memory)`: `def __init__(self, config: StubLongTermMemoryConfig | None = None) -> None`: store config (default StubLongTermMemoryConfig()); structlog.info("stub_long_term_memory_instantiated", note="D-59 placeholder; Phase 5 supplies QdrantLongTermMemory"). `async def query(self, query: str, k: int = 5, filters: dict | None = None) -> list[MemoryRecord]`: return `[]` (no Qdrant client — D-59 contract anchor). `async def store(self, record: MemoryRecord) -> str`: raise NotImplementedError("Phase 5 supplies QdrantLongTermMemory (D-59); long-term storage is not available in Phase 4"). Docstring at module top: cite CONTEXT.md D-59 lines 285-298 and RESEARCH.md memory layout. NO Qdrant or BGE-M3 dependencies imported (the entire module is stdlib + Pydantic + structlog only — Phase 5 introduces the qdrant-client dep).
    `memory/__init__.py` updated to re-export `EpisodicReplay, StubLongTermMemory, StubLongTermMemoryConfig`. Also alias `LongTermMemory = StubLongTermMemory` so downstream callers can write `from sft_agents.memory import LongTermMemory` and Phase 5 can swap the alias to point at QdrantLongTermMemory without breaking imports.
    `tests/test_hitl_cycle.py` (UPGRADE from W0 stub): integration test (testcontainers PG + NATS). Test 1 (happy path operator): build a tiny graph with one node that calls human_approval_node(...) inside; invoke graph with config recursion_limit=10; assert it pauses (state contains pending_approval_id); inspect PG → assert hitl.approvals row with status='pending' exists; inspect NATS → assert hitl.approvals.new.operator subject received; resume via `Command(resume=ApprovalDecision(decision="approve", motivation="ok", decided_by="user-1"))`; assert PG row updated to status='approved'; assert NATS hitl.approvals.resolved.operator received; assert audit.actions row exists with decision='hitl_operator' AND motivation NOT NULL AND approval_id matches. Test 2 (motivation missing for hitl_*): build with resume=ApprovalDecision(decision="approve", motivation="", decided_by="x"); assert validation error (Plan 04-01 model_validator) before INSERT into audit.actions. Test 3 (idempotent replay): invoke graph twice with same initial state + thread_id; assert only 1 row in hitl.approvals (ON CONFLICT DO NOTHING + sha256-deterministic id). Test 4 (T-04-Resume-Replay defense): try update_decision with non-existing approval_id; assert raises ApprovalNotFoundError.
    `tests/test_rate_limit_audit_query.py` (UPGRADE from W0 stub): integration test asserting EpisodicReplay.replay_thread limited to 1000 rows + uses parameterized SQL ($1 thread_id, $2 since). Seed 5 audit rows for thread_id="t-rate-1" then 5 for "t-rate-2"; replay_thread("t-rate-1") returns 5 rows; replay_thread("t-rate-1", since=middle_ts) returns rows with ts >= middle_ts only.
    `tests/test_long_term_stub.py` (NEW — UPGRADE from any prior W0 placeholder or new file): unit-test (no testcontainers needed — pure in-memory). Test 1: `StubLongTermMemory()` instantiates without raising. Test 2: `await StubLongTermMemory().query("anything", k=5)` returns `[]`. Test 3: `await StubLongTermMemory().query("foo", k=100, filters={"agent_id":"x"})` still returns `[]` (no filter forwarding logic — pure stub). Test 4: `await StubLongTermMemory().store(MemoryRecord(...))` raises `NotImplementedError` with message containing both `"Phase 5"` and `"QdrantLongTermMemory"`. Test 5: `isinstance(StubLongTermMemory(), Memory)` is True (subclass contract upheld). Test 6: `from sft_agents.memory import LongTermMemory; assert LongTermMemory is StubLongTermMemory` (alias contract). Test 7 (config frozen): `cfg = StubLongTermMemoryConfig(); cfg.foo = "x"` raises ValidationError (frozen=True+extra=forbid; even empty config rejects mutation/extras).

    Conventional commits per file: (1) `feat(04-06-hitl-middleware-02): approval queue writer with idempotent insert (T-04-Resume-Replay defense)`, (2) `feat(04-06-hitl-middleware-02): gdpr redactor for evidence panel input_summary (T-04-Checkpoint-PII)`, (3) `feat(04-06-hitl-middleware-02): human_approval_node interrupt/resume cycle (HITL-01,04,06,07)`, (4) `feat(04-06-hitl-middleware-02): episodic memory replay from audit.actions (CORE-08, D-59)`, (5) `feat(04-06-long-term-stub-02): add StubLongTermMemory placeholder for Phase 5 contract (D-59, CORE-08)`, (6) `test(04-06-hitl-middleware-02): hitl cycle integration tests (testcontainers PG + NATS)`, (7) `test(04-06-long-term-stub-02): StubLongTermMemory query=[] + store=NotImplementedError contract`.
  </action>
  <pattern_ref>services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:30-34 + :103-144 (parameterized INSERT/UPDATE pattern) ; packages/sft-agents/src/sft_agents/sdk/memory.py (Plan 04-01 — Memory ABC; StubLongTermMemory subclasses this) ; PATTERNS §3.6 (HITL sub-area + EscalationSupervisor worker analogy at main.py:114-168 — borrowed for next task)</pattern_ref>
  <threat_ref>T-04-LLM-Inject (EvidencePanel attached at every interrupt enforces auditability) ; T-04-Resume-Replay (ApprovalNotFoundError raised on missing/stale id; idempotent insert via sha256-deterministic id) ; T-04-Checkpoint-PII (GDPRRedactor strips PHI/PII before checkpoint write)</threat_ref>
  <done>
    **ApprovalQueueWriter (HITL-04, T-04-Resume-Replay):**
    - `python -c "from sft_agents.hitl import ApprovalQueueWriter, ApprovalNotFoundError; print('ok')"` exits 0
    - `grep -nF 'ON CONFLICT (id) DO NOTHING' packages/sft-agents/src/sft_agents/hitl/approval_queue.py` returns 1 match (idempotent insert)
    - Test `test_hitl_cycle.py::test_idempotent_replay` (Test 3) passes: invoking graph twice with same thread_id produces only 1 hitl.approvals row
    - Test `test_hitl_cycle.py::test_approval_not_found_on_stale_id` (Test 4) passes: update_decision with non-existent id raises `ApprovalNotFoundError`

    **human_approval_node (HITL-01, HITL-06, HITL-07):**
    - `python -c "from sft_agents.hitl import human_approval_node; print('ok')"` exits 0
    - `grep -nF 'interrupt(' packages/sft-agents/src/sft_agents/hitl/interrupt.py` returns at least 1 match
    - Test `test_hitl_cycle.py::test_happy_path_operator` (Test 1) passes: full interrupt → PG persist → NATS notify → resume → audit dual-write cycle with motivation populated
    - Test `test_hitl_cycle.py::test_motivation_required_for_hitl` (Test 2) passes: empty motivation on hitl_* decision raises ValidationError before audit INSERT

    **GDPRRedactor (T-04-Checkpoint-PII):**
    - `python -c "from sft_agents.hitl import GDPRRedactor, redact_str, redact_evidence; print('ok')"` exits 0
    - `grep -nE 'yaml\.(safe_)?load|redactor\.yaml' packages/sft-agents/src/sft_agents/hitl/redactor.py` returns 0 matches (NO YAML — regexes are Python constants per W4 resolution)
    - `grep -cE '^_(PHONE|EMAIL|CF)_RE = re\.compile' packages/sft-agents/src/sft_agents/hitl/redactor.py` returns 3 (three module-level compiled regex constants)
    - `python -c "from sft_agents.hitl import redact_str; assert '[REDACTED-PHONE]' in redact_str('call +39 333 1234567'); assert '[REDACTED-EMAIL]' in redact_str('email a@b.it'); assert '[REDACTED-CF]' in redact_str('RSSMRA80A01H501Z'); print('ok')"` exits 0

    **EpisodicReplay (CORE-08, D-59):**
    - `python -c "from sft_agents.memory import EpisodicReplay; print('ok')"` exits 0
    - `grep -nE 'LIMIT 1000' packages/sft-agents/src/sft_agents/memory/episodic.py` returns 1 match (bounded query)
    - Test `test_rate_limit_audit_query.py::test_replay_thread_filters` passes: 5 seeded rows per thread_id, `replay_thread` returns 5 rows, `since=middle_ts` returns only `ts >= since`

    **StubLongTermMemory (CORE-08 long-term stub, D-59 — B1 RESOLUTION):**
    - File exists: `test -f packages/sft-agents/src/sft_agents/memory/long_term_stub.py`
    - `grep -nF 'class StubLongTermMemory(Memory):' packages/sft-agents/src/sft_agents/memory/long_term_stub.py` returns 1 match
    - `python -c "from sft_agents.memory.long_term_stub import StubLongTermMemory; import asyncio; r=asyncio.run(StubLongTermMemory().query('foo')); assert r==[], r"` exits 0
    - `python -c "from sft_agents.memory.long_term_stub import StubLongTermMemory; import asyncio; asyncio.run(StubLongTermMemory().store(None))"` exits non-zero with NotImplementedError containing both `"Phase 5"` and `"QdrantLongTermMemory"`
    - `python -c "from sft_agents.memory import LongTermMemory, StubLongTermMemory; assert LongTermMemory is StubLongTermMemory"` exits 0 (alias for Phase 5 swap)
    - `python -c "from sft_agents.sdk.memory import Memory; from sft_agents.memory.long_term_stub import StubLongTermMemory; assert issubclass(StubLongTermMemory, Memory)"` exits 0 (ABC contract)
    - `grep -nE 'qdrant|bge[-_]m3|sentence[-_]transformers' packages/sft-agents/src/sft_agents/memory/long_term_stub.py` returns 0 matches (NO Phase 5 deps imported)
    - Test `test_long_term_stub.py` all 7 tests pass: `nx test sft-agents --testNamePattern=test_long_term_stub` exits 0

    **SQL safety (cross-component):**
    - `grep -nE 'yaml\.load\b' packages/sft-agents/src/sft_agents/hitl/*.py packages/sft-agents/src/sft_agents/memory/*.py | grep -v safe_load` returns 0 matches
    - `grep -nE 'f["\\\'].*INSERT|f["\\\'].*UPDATE|f["\\\'].*SELECT' packages/sft-agents/src/sft_agents/hitl/*.py packages/sft-agents/src/sft_agents/memory/episodic.py` returns 0 matches
  </done>
  <verify>
    <automated>nx test sft-agents --testNamePattern='test_hitl_cycle|test_rate_limit_audit_query|test_long_term_stub'</automated>
  </verify>
  <commit_scope>feat(04-06-hitl-middleware) + feat(04-06-long-term-stub-NN): add StubLongTermMemory placeholder for Phase 5 contract</commit_scope>
</task>

<task type="auto" tdd="true">
  <id>04-06-03</id>
  <name>Task 3: SafetyInterlockMiddleware + safety-interlock.yaml + EscalationSupervisor + escalation-sla.yaml</name>
  <files>packages/sft-agents/src/sft_agents/policies/safety_interlock.py, packages/sft-agents/src/sft_agents/policies/safety-interlock.yaml, packages/sft-agents/src/sft_agents/policies/escalation-sla.yaml, packages/sft-agents/src/sft_agents/policies/budgets.yaml, packages/sft-agents/src/sft_agents/runtime/escalation.py, packages/sft-agents/tests/test_safety_interlock.py, packages/sft-agents/tests/test_escalation.py</files>
  <read_first>
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-57 escalation SLA full block lines 209-232; D-58 Safety Interlock whitelist lines 234-269)
    .planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md (§3.6 HITL sub-areas; §4.2 background asyncio loop; §4.3 yaml policy loader)
    services/ot-bridge/src/svc_ot_bridge/main.py:114-168 (worker pattern with shutdown_event — CRITICAL pattern for EscalationSupervisor.run)
    packages/sft-domain/src/sft_domain/glossary/_loader.py:21-80 (yaml.safe_load + Pydantic validation + lru_cache)
    packages/sft-agents/src/sft_agents/audit/writer.py (Task 1 — AuditWriter consumer)
    packages/sft-agents/src/sft_agents/hitl/approval_queue.py (Task 2 — ApprovalQueueWriter.insert_escalation)
  </read_first>
  <behavior>
    - `safety-interlock.yaml` contains keys forbidden_subjects (glob list) + forbidden_action_types (enum list) per D-58 exactly
    - `escalation-sla.yaml` contains 4 tier blocks (operator/supervisor/manager/safety_interlock) with sla_minutes + next_tier per D-57 exactly
    - `SafetyInterlockMiddleware(yaml_path=None).check(action: ProposedAction)`: matches action.target_subject via NATS-glob (treat `cmd.plc.setpoint.>` as `cmd.plc.setpoint.*` glob); matches action.action_type via membership; on match: build interlock-reject AuditRecord via audit_writer + raise SafetyInterlockRejection
    - SafetyInterlockMiddleware MUST NOT be bypassable — no UI override; the design is code-only override (requires PR + audit trail per D-58)
    - `EscalationSupervisor.run()` scans pending approvals every 30s; for tier != safety_interlock and sla_deadline < NOW(): if next_tier is None → audit decision=timed_out + NATS hitl.governor.alert; else queue_writer.insert_escalation(original_id, next_tier) + audit decision=escalated
    - Safety Interlock approvals never time out (sla_deadline IS NULL or skipped by query filter `tier <> 'safety_interlock'`)
    - On manager timeout (next_tier=null), the alert payload includes `{thread_id, action_type, approval_id, timed_out_at, sla_deadline}` so Phase 10 UI dashboard can render
  </behavior>
  <action>
    `policies/safety-interlock.yaml`: exact content per D-58 lines 240-251:
    ```yaml
    forbidden_subjects:
      - "cmd.plc.setpoint.>"
      - "cmd.actuator.>"
      - "cmd.firmware.deploy"
      - "cmd.network.acl.>"
    forbidden_action_types:
      - WRITE_PLC_SETPOINT
      - ACTUATOR_COMMAND
      - FIRMWARE_DEPLOY
      - NETWORK_ACL_CHANGE
    ```
    `policies/escalation-sla.yaml`: exact content per D-57 lines 220-225:
    ```yaml
    operator:           {sla_minutes: 2,  next_tier: supervisor}
    supervisor:         {sla_minutes: 15, next_tier: manager}
    manager:            {sla_minutes: 60, next_tier: null}
    safety_interlock:   {sla_minutes: null, next_tier: null}
    ```
    `policies/budgets.yaml`: exact content per D-60 lines 343-349:
    ```yaml
    ops:                {tokens: 50000, cost_usd: 1.00, duration_s: 60}
    maintenance:        {tokens: 100000, cost_usd: 2.00, duration_s: 300}
    knowledge-curation: {tokens: 200000, cost_usd: 5.00, duration_s: 600}
    knowledge-training: {tokens: 100000, cost_usd: 2.00, duration_s: 300}
    supply:             {tokens: 100000, cost_usd: 2.00, duration_s: 300}
    agents:
      # per-agent overrides (empty Phase 4; Phase 6-9 populates)
    ```
    `policies/safety_interlock.py`: imports yaml, re, fnmatch; `class SafetyInterlockRejection(Exception)` with `action_id, action_type, reason` attributes. `class SafetyInterlockMiddleware`: `__init__(self, *, yaml_path: Path | None = None, audit_writer: AuditWriter | None = None)`: load yaml via yaml.safe_load; precompile subject globs (translate NATS `.>` to fnmatch `.*` or use prefix-match `subject.startswith(prefix)`); store action_types as frozenset. `async def check(self, action: ProposedAction, *, agent_id: str, thread_id: str, cluster: str, evidence_panel: EvidencePanel, budget_snapshot: BudgetSnapshot) -> None`: scan; on match build AuditRecord(decision=Decision.INTERLOCK_REJECT, motivation=None, approval_id=None, action_id=action.id, agent_id=agent_id, thread_id=thread_id, cluster=cluster, action_type=action.action_type, evidence_panel=evidence_panel, budget_snapshot=budget_snapshot); await audit_writer.write(record); raise SafetyInterlockRejection(action_id=action.id, action_type=action.action_type, reason=match_reason).
    `runtime/escalation.py`: `class EscalationSupervisor`: __init__ stores pg_pool, audit_writer, nats_publisher (for governor.alert on manager timeout), queue_writer, sla_yaml_path; scan_interval_s=30 (configurable). Load yaml; build internal map `tier → (sla_minutes, next_tier)`. `_SCAN_SQL = "SELECT id, agent_id, thread_id, tier, action_type, payload_json FROM hitl.approvals WHERE status='pending' AND sla_deadline < NOW() AND tier <> 'safety_interlock' LIMIT 100"`. `async def _scan_once(self) -> int`: SELECT pending+expired rows; for each row: determine next_tier from yaml; if next_tier is None (manager): audit decision=timed_out + nats publish_governor_alert payload with {tier:manager, action_id, thread_id, sla_breach_at:NOW()}; queue_writer marks status='timed_out' (UPDATE). Else: queue_writer.insert_escalation(original_id, next_tier) — this is a single transaction that inserts the new row + updates the old; emit audit decision=escalated. Return rows_processed count. `async def run(self)`: shutdown_event = asyncio.Event(); while not self._shutdown.is_set(): try await asyncio.wait_for(self._shutdown.wait(), timeout=self._scan_interval_s) — break loop on shutdown; on TimeoutError → continue → call _scan_once + log; on CancelledError → re-raise. `async def stop(self)`: self._shutdown.set().
    `tests/test_safety_interlock.py` (UPGRADE from W0 stub): unit tests (mock audit_writer). Test 1: action with target_subject="cmd.plc.setpoint.loom-T-12.speed" → raises SafetyInterlockRejection AND audit_writer.write called once with decision=INTERLOCK_REJECT. Test 2: action_type=ActionType.FIRMWARE_DEPLOY → raises. Test 3: action with benign subject "sensor.events.x" and action_type=arbitrary → no exception, no audit call. Test 4: yaml file path traversal attempt — passing yaml_path containing `..` to constructor — middleware accepts (path is internal) but assert yaml.safe_load used (not yaml.load). Test 5: assert middleware loads from default package-relative path when yaml_path=None.
    `tests/test_escalation.py` (UPGRADE from W0 stub): integration test (testcontainers PG + NATS). Test 1: seed hitl.approvals row at tier=operator with sla_deadline=NOW()-INTERVAL'5 minutes'; run EscalationSupervisor._scan_once(); assert original row status='escalated', escalated_to_id set; assert new row exists at tier=supervisor with status='pending'; assert audit.actions row decision='escalated'. Test 2: chain escalation operator→supervisor→manager (3 scan cycles or seeded scenarios). Test 3: manager-tier expired → no new row, status='timed_out', NATS hitl.governor.alert received with thread_id+sla_breach_at. Test 4 (safety_interlock no-timeout): seed safety_interlock approval with sla_deadline=NULL (or far past); _scan_once does NOT escalate (filter excludes safety_interlock); assert original row status remains 'pending'.

    Conventional commits: (1) `feat(04-06-hitl-middleware-03): safety interlock yaml + middleware + interlock_reject audit (HITL-03, D-58)`, (2) `feat(04-06-hitl-middleware-03): escalation-sla.yaml + budgets.yaml policy files (D-57, D-60)`, (3) `feat(04-06-hitl-middleware-03): escalation supervisor background task (HITL-02, D-57)`, (4) `test(04-06-hitl-middleware-03): safety interlock whitelist + escalation chain (testcontainers PG + NATS)`.
  </action>
  <pattern_ref>services/ot-bridge/src/svc_ot_bridge/main.py:114-168 (worker loop with asyncio.wait_for + shutdown_event — replicate 1:1 for EscalationSupervisor.run) ; packages/sft-domain/src/sft_domain/glossary/_loader.py:21-80 (yaml.safe_load + pathlib pattern) ; PATTERNS §3.6 + §4.2 + §4.3</pattern_ref>
  <threat_ref>T-04-Whitelist-Bypass (SafetyInterlockMiddleware enforces YAML whitelist via fnmatch/startswith; no UI override; code-only changes require audit trail) ; T-04-Bypass-HITL (escalation timer guarantees no action stays pending forever — even Manager timeout still emits governor.alert)</threat_ref>
  <done>
    **YAML policy files (D-57, D-58, D-60 verbatim):**
    - `python -c "import yaml; d=yaml.safe_load(open('packages/sft-agents/src/sft_agents/policies/safety-interlock.yaml')); assert 'cmd.plc.setpoint.>' in d['forbidden_subjects']; assert 'WRITE_PLC_SETPOINT' in d['forbidden_action_types']; print('ok')"` exits 0
    - `python -c "import yaml; d=yaml.safe_load(open('packages/sft-agents/src/sft_agents/policies/escalation-sla.yaml')); assert d['operator']['sla_minutes']==2; assert d['safety_interlock']['sla_minutes'] is None; print('ok')"` exits 0
    - `python -c "import yaml; d=yaml.safe_load(open('packages/sft-agents/src/sft_agents/policies/budgets.yaml')); assert d['ops']['tokens']==50000; print('ok')"` exits 0

    **SafetyInterlockMiddleware (HITL-03, T-04-Whitelist-Bypass):**
    - `python -c "from sft_agents.policies.safety_interlock import SafetyInterlockMiddleware, SafetyInterlockRejection; print('ok')"` exits 0
    - Test `test_safety_interlock.py::test_plc_setpoint_blocked` passes: forbidden subject → SafetyInterlockRejection raised + audit_writer.write called with decision=INTERLOCK_REJECT
    - Test `test_safety_interlock.py::test_firmware_deploy_blocked` passes: forbidden action_type → SafetyInterlockRejection
    - Test `test_safety_interlock.py::test_benign_action_passes` passes: non-forbidden → no exception, no audit
    - `grep -nE 'yaml\.load\b' packages/sft-agents/src/sft_agents/policies/safety_interlock.py | grep -v safe_load` returns 0 matches

    **EscalationSupervisor (HITL-02, D-57):**
    - `python -c "from sft_agents.runtime.escalation import EscalationSupervisor; print('ok')"` exits 0
    - Test `test_escalation.py::test_operator_to_supervisor` passes: expired operator row → escalated_to_id set, new supervisor row, audit decision='escalated'
    - Test `test_escalation.py::test_manager_timeout` passes: expired manager-tier → no new row, status='timed_out', NATS hitl.governor.alert received
    - Test `test_escalation.py::test_safety_interlock_no_timeout` passes: safety_interlock row NOT escalated even when sla_deadline expired

    **SQL safety:**
    - `grep -nE 'yaml\.load\b' packages/sft-agents/src/sft_agents/policies/*.py packages/sft-agents/src/sft_agents/runtime/escalation.py | grep -v safe_load` returns 0 matches
  </done>
  <verify>
    <automated>nx test sft-agents --testNamePattern='test_safety_interlock|test_escalation'</automated>
  </verify>
  <commit_scope>feat(04-06-hitl-middleware)</commit_scope>
</task>

<task type="auto" tdd="true">
  <id>04-06-04</id>
  <name>Task 4: Governor + BudgetTracker middleware + tests</name>
  <files>packages/sft-agents/src/sft_agents/runtime/governor.py, packages/sft-agents/src/sft_agents/runtime/budget.py, packages/sft-agents/tests/test_governor.py, packages/sft-agents/tests/test_budget.py</files>
  <read_first>
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-58 governor lines 253-269; D-60 budget tracker lines 307-359)
    .planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md (§3.8 governor; §3.9 budget UPSERT)
    packages/sft-tools/src/sft_tools/timescale/query.py:35-43 (SQL constant pattern)
    services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:30-34 + :146-158 (constant SQL + background loop)
    packages/sft-agents/src/sft_agents/policies/budgets.yaml (Task 3 created)
  </read_first>
  <behavior>
    - `Governor.run()` loop scans audit.actions every 60s; query is parameterized constant SQL; if total >= 20 AND auto_rate > 0.80 → audit governor_alert + NATS publish_governor_alert + create Manager-tier ApprovalRequest
    - First run with empty audit table: no alert (total < 20)
    - Anti-thrash: after a governor_alert is emitted, do NOT re-emit if the most-recent audit.actions row already has decision='governor_alert' AND ts > NOW() - INTERVAL '5 minutes' (cooldown)
    - Governor alert payload includes `top_agents` (top 5 agent_ids by count in window) via second SELECT
    - `BudgetTracker.track(state, step_input_tokens, step_output_tokens, step_cost_usd, step_duration_ms)` UPSERTs budget.executions; returns new BudgetSnapshot reflecting current totals
    - Soft threshold: tokens_total / limit_tokens > 0.80 → emit Operator-tier ApprovalRequest (one-shot per crossing — track via state flag `budget_soft_alerted: bool`)
    - Hard threshold: cost_usd > limit_cost_usd → emit Supervisor-tier ApprovalRequest with action_type=BUDGET_EXHAUSTED (Plan 04-01 ActionType extensible)
    - Limit resolution: budget.yaml lookup precedence — `agents[<agent_id>]` override → `<cluster>` default → hard-coded module-level safe default
  </behavior>
  <action>
    `runtime/governor.py`: imports asyncpg, structlog, asyncio; constants: `_GOVERNOR_SCAN_SQL = "SELECT count(*) FILTER (WHERE decision='auto') AS auto_count, count(*) AS total FROM audit.actions WHERE ts > NOW() - INTERVAL '1 hour' AND decision NOT IN ('escalated','governor_alert','timed_out')"`, `_TOP_AGENTS_SQL = "SELECT agent_id, count(*) AS cnt FROM audit.actions WHERE ts > NOW() - INTERVAL '1 hour' AND decision='auto' GROUP BY agent_id ORDER BY cnt DESC LIMIT 5"`, `_COOLDOWN_SQL = "SELECT 1 FROM audit.actions WHERE decision='governor_alert' AND ts > NOW() - INTERVAL '5 minutes' LIMIT 1"`. `class Governor`: __init__ stores pool, audit_writer, nats_publisher, queue_writer, scan_interval_s=60, threshold=0.80, min_sample=20. `async def _scan_once(self) -> bool`: check cooldown first (if exists, return False — no alert); else fetchrow scan SQL; if total < min_sample: return False; if auto_count/total > threshold: fetch top_agents; build AuditRecord(decision=GOVERNOR_ALERT, action_type='GOVERNOR_ALERT', agent_id='governor', thread_id='__system__', cluster='ops' (system marker — could be 'system' but Plan 04-01 enum currently doesn't include 'system' — use 'ops' as the canonical home or extend enum here; align with CONTEXT.md D-58 which doesn't specify cluster for governor — Claude's Discretion: cluster='ops' as default home), evidence_panel=<minimal with input_summary='governor alert auto_rate={rate}'>, budget_snapshot=<empty>, motivation=None, approval_id=None); await audit_writer.write(record); nats_publisher.publish_governor_alert(payload={auto_rate, sample_size:total, window_start, window_end, top_agents}); create Manager-tier ApprovalRequest with payload=alert payload via queue_writer.insert. Return True. `async def run(self)`: same loop pattern as EscalationSupervisor with shutdown_event.
    `runtime/budget.py`: imports asyncpg, yaml; `class BudgetLimits` Pydantic frozen: tokens, cost_usd, duration_s. `class BudgetTracker`: __init__ stores pool, queue_writer, budgets_yaml_path (default package-relative). Load yaml on init via yaml.safe_load → store cluster_defaults dict + agent_overrides dict (under top-level `agents:` key). Module constants `_UPSERT_SQL = """INSERT INTO budget.executions (thread_id, agent_id, tokens_total, cost_usd, duration_ms, step_count, last_step_at) VALUES ($1, $2, $3, $4, $5, 1, NOW()) ON CONFLICT (thread_id, agent_id) DO UPDATE SET tokens_total = budget.executions.tokens_total + EXCLUDED.tokens_total, cost_usd = budget.executions.cost_usd + EXCLUDED.cost_usd, duration_ms = budget.executions.duration_ms + EXCLUDED.duration_ms, step_count = budget.executions.step_count + 1, last_step_at = NOW() RETURNING tokens_total, cost_usd, duration_ms, step_count, started_at"""`. `def resolve_limits(self, *, cluster: str, agent_id: str) -> BudgetLimits`: agent_overrides.get(agent_id) or cluster_defaults.get(cluster) or safe_defaults. `async def track(self, *, thread_id: str, agent_id: str, cluster: str, tier_for_overrun: Tier, step_input_tokens: int, step_output_tokens: int, step_cost_usd: float, step_duration_ms: int) -> BudgetSnapshot`: execute UPSERT with step delta; fetchrow returns new totals; build BudgetSnapshot(tokens_input=step_input_tokens (cumulative not tracked at this level — only deltas + totals), tokens_output, tokens_total=totals.tokens_total, cost_usd_simulated=totals.cost_usd, duration_ms=totals.duration_ms, step_count, limit_tokens=limits.tokens, limit_cost_usd=limits.cost_usd, limit_duration_s=limits.duration_s); evaluate thresholds; if soft tokens crossing → emit Operator-tier ApprovalRequest; if hard cost → emit Supervisor-tier ApprovalRequest with action_type='BUDGET_EXHAUSTED'; if hard duration → emit Operator-tier ApprovalRequest. Return snapshot. Wire suggestion (planner note): BudgetTracker is typically called from within BudgetingChatModel.ainvoke (Plan 04-03) — that wrapper currently captures token deltas; this plan extends it to call BudgetTracker.track after each LLM call.
    `tests/test_governor.py` (UPGRADE from W0 stub): integration test (testcontainers PG + NATS). Test 1: seed 25 audit.actions rows decision='auto' in last hour; _scan_once returns True; assert audit row decision='governor_alert' written; assert NATS hitl.governor.alert subject received with auto_rate≈1.0, sample_size=25, top_agents non-empty; assert Manager-tier hitl.approvals row created with action_type='GOVERNOR_ALERT'. Test 2: seed 25 audit rows decision='auto' + 15 decision='hitl_operator' (auto_rate = 25/40 = 0.625) → _scan_once returns False (below 0.80). Test 3: seed only 10 rows decision='auto' → returns False (below min_sample 20). Test 4 (cooldown): after a successful alert in Test 1, immediately call _scan_once again → returns False (cooldown). Test 5: top_agents query result is list of {agent_id, cnt} length ≤ 5.
    `tests/test_budget.py` (UPGRADE from W0 stub): integration test. Test 1: BudgetTracker.track increments thread_id+agent_id row idempotently — call 3 times with (100,100,0.01,500) deltas → final row tokens_total=600, step_count=3. Test 2: tokens_total cumulatively crosses 80% of limit (ops default 50000 tokens → 40000 trigger) → assert Operator-tier ApprovalRequest emitted. Test 3: cost_usd > limit_cost_usd → Supervisor-tier ApprovalRequest with action_type='BUDGET_EXHAUSTED'. Test 4: resolve_limits prefers agent_id override when set in budgets.yaml — temporarily seed override via fixture-level YAML rewrite. Test 5: budget.yaml uses yaml.safe_load (grep test or import-time check that BudgetTracker.__init__ doesn't fail on yaml content).

    Conventional commits: (1) `feat(04-06-hitl-middleware-04): governor sliding-window 80% threshold with cooldown (HITL-09, D-58)`, (2) `feat(04-06-hitl-middleware-04): budget tracker upsert + soft/hard thresholds (CORE-09, D-60)`, (3) `test(04-06-hitl-middleware-04): governor + budget integration tests`.
  </action>
  <pattern_ref>PATTERNS §3.8 (governor SQL constant) ; §3.9 (UPSERT pattern adapted from ot-bridge timescale_writer) ; §4.2 background loop replicated for governor.run</pattern_ref>
  <threat_ref>T-04-Budget-Exhaust (BudgetTracker enforces token+cost+duration limits; soft+hard thresholds emit ApprovalRequest before runaway spend) ; T-04-LLM-Inject (Governor cooldown anti-thrash prevents adversarial input causing alert spam)</threat_ref>
  <done>
    **Governor (HITL-09, D-58):**
    - `python -c "from sft_agents.runtime.governor import Governor; print('ok')"` exits 0
    - `grep -nF 'INTERVAL ' packages/sft-agents/src/sft_agents/runtime/governor.py` returns at least 2 matches (1-hour window + 5-minute cooldown)
    - Test `test_governor.py::test_governor_alert_fires` passes: 25 auto rows → audit governor_alert + NATS published + Manager-tier ApprovalRequest created
    - Test `test_governor.py::test_below_threshold_no_alert` passes: auto_rate=0.625 → returns False
    - Test `test_governor.py::test_below_min_sample` passes: 10 rows → returns False
    - Test `test_governor.py::test_cooldown_prevents_thrash` passes: second scan within 5min → returns False
    - Test `test_governor.py::test_top_agents_length_capped` passes: result length ≤ 5

    **BudgetTracker (CORE-09, D-60):**
    - `python -c "from sft_agents.runtime.budget import BudgetTracker, BudgetLimits; print('ok')"` exits 0
    - `grep -nF 'ON CONFLICT (thread_id, agent_id) DO UPDATE' packages/sft-agents/src/sft_agents/runtime/budget.py` returns 1 match (UPSERT)
    - Test `test_budget.py::test_upsert_idempotent_accumulates` passes: 3 calls → tokens_total=600, step_count=3
    - Test `test_budget.py::test_soft_token_threshold` passes: crossing 80% of cluster limit → Operator-tier ApprovalRequest emitted
    - Test `test_budget.py::test_hard_cost_threshold` passes: cost > limit → Supervisor-tier ApprovalRequest with action_type='BUDGET_EXHAUSTED'
    - Test `test_budget.py::test_resolve_limits_agent_override` passes: agent_overrides take precedence over cluster_defaults
    - Test `test_budget.py::test_yaml_safe_load_used` passes: BudgetTracker.__init__ uses yaml.safe_load

    **SQL safety:**
    - `grep -nE 'f["\\\'].*INSERT|f["\\\'].*UPDATE|f["\\\'].*SELECT' packages/sft-agents/src/sft_agents/runtime/governor.py packages/sft-agents/src/sft_agents/runtime/budget.py` returns 0 matches
  </done>
  <verify>
    <automated>nx test sft-agents --testNamePattern='test_governor|test_budget'</automated>
  </verify>
  <commit_scope>feat(04-06-hitl-middleware)</commit_scope>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent → audit.actions (PG) | Sync write path; revoke at DB-level (Plan 04-02); AuditWriter respects D-56 invariant |
| Agent → NATS audit | Async write path; outbox retry on failure (T-04-Outbox-Drop) |
| Agent → ProposedAction → ToolNode | Safety Interlock middleware intercepts (T-04-Whitelist-Bypass) |
| LLM-generated proposed action target_subject | Untrusted string; whitelist match prevents PLC command injection |
| Resume payload (`Command(resume=value)`) | Untrusted from api-gateway; ApprovalNotFoundError on stale/forged id (T-04-Resume-Replay) |
| EvidencePanel.input_summary → PG checkpoint | GDPRRedactor strips PII before checkpoint write (T-04-Checkpoint-PII) |
| Agent → StubLongTermMemory.query | No external network; returns []; defense against accidental Phase 5 dependency leak |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-Bypass-HITL | Elevation | human_approval_node + SafetyInterlockMiddleware | mitigate | interrupt() persists checkpoint before pause; resume validates ApprovalDecision; Safety Interlock blocks pre-tool with whitelist YAML |
| T-04-Whitelist-Bypass | Elevation | SafetyInterlockMiddleware + safety-interlock.yaml | mitigate | YAML whitelist enforced via fnmatch/startswith on target_subject AND action_type; SafetyInterlockRejection raises terminate-agent; no UI override |
| T-04-LLM-Inject | Tampering | EvidencePanel attachment + GDPRRedactor | mitigate | Every decision audited with EvidencePanel (HITL-06); GDPRRedactor strips PII; Pydantic-validated ApprovalDecision rejects malformed resume payloads |
| T-04-Audit-Tamper | Tampering/Repudiation | AuditWriter dual-write | mitigate | DB-level REVOKE (Plan 04-02) + AuditWriter respects PG-first invariant (no NATS-only fake audit) |
| T-04-Outbox-Drop | Repudiation | OutboxWriter + OutboxRetry | mitigate | audit.outbox enqueued on NATS failure; retry loop with exp backoff; max 10 attempts (then dead-letter — Phase 11 alerting) |
| T-04-Budget-Exhaust | DoS | BudgetTracker | mitigate | UPSERT every step + soft 80%/hard 100% thresholds emit ApprovalRequest; Governor catches systemic auto-approve drift |
| T-04-Checkpoint-PII | Info Disclosure | GDPRRedactor | mitigate | Phone/email/codice_fiscale regex redaction in EvidencePanel.input_summary before checkpoint write; A-013..A-018 boundary; regex constants live in Python source (not YAML) so disabling redaction requires PR+review |
| T-04-Resume-Replay | Tampering | ApprovalQueueWriter.update_decision | mitigate | Idempotent insert via sha256-deterministic id (ON CONFLICT DO NOTHING); ApprovalNotFoundError when update affects 0 rows (stale/forged id rejected) |
</threat_model>

<verification>
- Full HITL cycle (interrupt → PG persist → NATS notify → resume → audit dual-write) integration-tested
- Safety Interlock whitelist enforcement integration-tested (`cmd.plc.setpoint.>` + 4 forbidden_action_types)
- Escalation chain operator→supervisor→manager→timeout integration-tested with D-57 timer config
- Governor 80% threshold + 20 sample minimum + 5-min cooldown integration-tested
- BudgetTracker UPSERT + soft 80% (operator) + hard 100% cost (supervisor) integration-tested
- AuditWriter dual-write D-56 invariant: PG fail = abort, NATS fail = outbox enqueue, outbox retry succeeds
- EpisodicReplay reads from audit.actions ordered by ts (D-59 CORE-08)
- StubLongTermMemory.query() returns [] for any input; store() raises NotImplementedError with Phase 5 message (D-59 long-term stub contract)
- GDPRRedactor strips phone/email/codice_fiscale from EvidencePanel.input_summary; regexes in Python constants (not YAML)
- 8 unskipped tests green: test_audit_writer, test_hitl_cycle, test_rate_limit_audit_query, test_long_term_stub, test_safety_interlock, test_escalation, test_governor, test_budget
</verification>

<success_criteria>
- HITL-01: interrupt()/resume cycle operational with PG checkpoint persistence
- HITL-02: 4-tier escalation enforced via EscalationSupervisor + D-57 timers
- HITL-03: Safety Interlock blocks PLC setpoint writes + 4 forbidden action types via whitelist YAML
- HITL-04: Approval queue persistent in hitl.approvals with SLA per tier
- HITL-05: Audit immutable via PG REVOKE (Plan 04-02) + NATS AUDIT_STREAM 90d (Plan 04-04); AuditWriter respects dual-write invariant
- HITL-06: EvidencePanel attached at every interrupt (human_approval_node)
- HITL-07: motivation required for hitl_* decisions (Pydantic model_validator Plan 04-01 + DB CHECK Plan 04-02 + ApprovalDecision validation here)
- HITL-08: rollback substrate via EpisodicReplay (read audit log) + replay tool (Plan 04-08)
- HITL-09: Governor sliding-window 80% threshold with 20-sample minimum + cooldown
- HITL-10: rate-limit alarm data primitive (audit.actions queryable for "12 alerts/h per agent") — UI deferred Phase 10
- CORE-08: episodic memory via NATS+TimescaleDB replay (EpisodicReplay) + long-term stub (StubLongTermMemory) shipping the Phase 5 contract anchor per D-59
- CORE-09: budget tracker with PG UPSERT + soft/hard thresholds
- Success criterion #1 met: full HITL cycle end-to-end with audit dual-write
- Success criterion #5 met: 80% approval-rate governor fires Manager alert
- D-59 contract: `from sft_agents.memory.long_term_stub import StubLongTermMemory` resolves; Phase 5 replaces module body with `QdrantLongTermMemory` having identical signatures (no API break)
</success_criteria>

<output>
Create `.planning/phases/04-core-agentic-runtime-hitl/04-06-SUMMARY.md`. Include: module count (14 production + 3 YAML), test count (8 unskipped), StubLongTermMemory contract row (D-59 line reference), downstream consumer (Plan 04-07 wires human_approval_node into supervisor graph via Plan 04-05 build_supervisor_graph; Plan 04-08 replay tool consumes EpisodicReplay; Phase 5 KNW cluster replaces long_term_stub.py with QdrantLongTermMemory).
</output>
