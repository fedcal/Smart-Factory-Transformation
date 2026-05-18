---
phase: 04-core-agentic-runtime-hitl
plan: 08
type: execute
wave: 4
depends_on: ["04-01", "04-02", "04-05", "04-06"]
files_modified:
  - packages/sft-agents/src/sft_agents/replay/__init__.py
  - packages/sft-agents/src/sft_agents/replay/from_checkpoint.py
  - packages/sft-agents/tests/test_replay.py
  - .planning/ROADMAP.md
  - docs/docs/architecture/agentic-runtime.md
  - docs/docs/architecture/hitl-cycle.md
  - docs/mkdocs.yml
autonomous: false
requirements: [CORE-10, HITL-08]
threat_refs: [T-04-Audit-Tamper, T-04-LLM-Inject]

must_haves:
  truths:
    - "`replay_thread(thread_id, action_id=None) -> ReplayResult` re-executes the agent from PG checkpoint + audit log; tool calls are deterministic (mocked from audit log); LLM calls use the recorded prompt with seed (best-effort determinism per Pitfall §5)"
    - "Re-running replay on the same checkpoint+action_id produces a ReplayResult with identical state shape AND identical AuditRecord.id values (replay does NOT write new audit rows by default — flag `write_audit=False`)"
    - "ROADMAP.md Phase 4 section says `5 cluster subgraph skeletons` instead of `four cluster subgraph skeletons` (D-53 override committed)"
    - "docs/docs/architecture/agentic-runtime.md describes the 5 cluster structure, supervisor + hybrid routing, HITL cycle, escalation, governor, budget, audit dual-write; rendered via mkdocs without broken links"
    - "docs/docs/architecture/hitl-cycle.md describes the interrupt→resume contract with a Mermaid sequence diagram"
  artifacts:
    - path: packages/sft-agents/src/sft_agents/replay/from_checkpoint.py
      provides: "replay_thread function + ReplayResult Pydantic frozen model"
      contains: "def replay_thread"
    - path: docs/docs/architecture/agentic-runtime.md
      provides: "Phase 4 architecture page"
      min_lines: 100
    - path: docs/docs/architecture/hitl-cycle.md
      provides: "HITL interrupt→resume sequence diagram + decision matrix"
      min_lines: 60
    - path: .planning/ROADMAP.md
      provides: "Phase 4 description aligned to D-53 (5 clusters)"
      contains: "5 cluster"
  key_links:
    - from: packages/sft-agents/src/sft_agents/replay/from_checkpoint.py
      to: packages/sft-agents/src/sft_agents/memory/episodic.py + packages/sft-agents/src/sft_agents/runtime/checkpointer.py
      via: "EpisodicReplay reads audit; checkpointer reads state snapshot"
      pattern: "EpisodicReplay|get_postgres_checkpointer"
    - from: docs/mkdocs.yml
      to: docs/docs/architecture/agentic-runtime.md + hitl-cycle.md
      via: "nav entries under Architecture section"
      pattern: "agentic-runtime|hitl-cycle"
---

<objective>
Wave 4 Plan B: deliver the final 3 deliverables that close Phase 4:
1. Replay tool (CORE-10, HITL-08) — `replay_thread(thread_id, action_id)` reconstructs an agent execution from PG checkpoint + audit log; tool calls deterministic from audit; LLM calls best-effort with seed.
2. [BLOCKING] ROADMAP.md edit (D-53 align: 4 → 5 clusters).
3. Phase 4 architecture docs (mkdocs) covering agentic-runtime + hitl-cycle pages.

Purpose: replay tool enables HITL-08 rollback substrate (event-sourcing replay) + CORE-10 deterministic replay; ROADMAP edit closes D-53 traceability; docs land Phase 4 in the MkDocs site established Phase 1.

Output: 2 Python modules + 1 unskipped replay test + 2 mkdocs pages + ROADMAP.md edit (BLOCKING manual task) + mkdocs.yml nav update.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md
@.planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md
@.planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md
@packages/sft-tools/src/sft_tools/replay/models.py
@packages/sft-tools/src/sft_tools/replay/cmapss.py
@packages/sft-agents/src/sft_agents/memory/episodic.py
@packages/sft-agents/src/sft_agents/runtime/checkpointer.py
@docs/mkdocs.yml

<interfaces>
ReplayResult Pydantic frozen:
- thread_id: str
- replayed_steps: list[ReplayedAgentStep]
- divergence_at_step: int | None  # first step where replay state differs from recorded
- recorded_audit_ids: list[UUID]
- replayed_audit_ids: list[UUID] | None  # null when write_audit=False (default)
- ts_replay_start: datetime
- ts_replay_end: datetime

ReplayedAgentStep Pydantic frozen:
- step_index: int
- recorded_action: AuditRecord
- replayed_state_delta: dict
- divergence_reason: str | None
- llm_prompt_hash_match: bool
- tool_calls_match: bool

replay_thread function signature:
```
async def replay_thread(
    thread_id: str,
    *,
    pool: asyncpg.Pool,
    checkpointer,
    fake_llm: BaseChatModel | None = None,
    action_id: UUID | None = None,
    write_audit: bool = False,
) -> ReplayResult:
    """
    Re-executes the agent loop for `thread_id` from the start of the recorded audit log.
    
    - Loads audit rows via EpisodicReplay (Plan 04-06)
    - Loads checkpoint snapshot via checkpointer (Plan 04-05)
    - For each recorded step: re-invokes the agent with the same input,
      but with tool calls FROZEN to recorded outputs (deterministic per CORE-10 Phase 4 scope)
    - LLM calls: if fake_llm given, use it; else attempt to recreate model with seed
      matching EvidencePanel.model (best-effort — Pitfall §5)
    - Returns step-by-step divergence report
    - write_audit=False (default): replay is a dry-run; no new audit.actions rows
    - write_audit=True: writes new audit rows with cluster=<original> + action_type prefixed 'REPLAY:'
      AND adds `replay_of_action_id` field in evidence_panel.input_summary (T-04-Audit-Tamper consideration:
      replay rows have non-`auto` decisions to distinguish from original audit)
    
    If action_id given: replay STOPS after reaching that recorded action_id (useful for "rollback before X")
    """
```

LLM determinism for replay (Pitfall §5):
- Phase 4 BEST-EFFORT: temperature=0 + seed (if backend supports it) on FakeListChatModel or real Ollama
- Tool calls: ALWAYS deterministic — replayed_state_delta uses recorded `evidence_panel.tool_calls[]` directly, bypassing real tool execution
- Frozen tool outputs (full determinism) → Phase 11 (CONTEXT.md scope_boundaries)

mkdocs pages target structure:
docs/docs/architecture/agentic-runtime.md (≥100 lines):
- ## Overview (Phase 4 charter, what it ships, what it doesn't — link CONTEXT.md scope boundaries)
- ## Cluster Structure (D-53 — 5 clusters with 16 agents; table)
- ## Supervisor Routing (D-54 hybrid rules + LLM fallback; routing.yaml link)
- ## PostgreSQL Checkpointer (CORE-04 — thread_id convention)
- ## LLM Adapter (CORE-05 — LLM_BACKEND env var; link llm-serving.md)
- ## Tool Registry (CORE-07 — OpenAI function-calling export)
- ## Memory Layers (CORE-08 — short-term + episodic + long-term stub)
- ## Budget Tracker (CORE-09 — soft/hard thresholds)
- ## Replay (CORE-10 — best-effort determinism)
- ## Cross-references (links to hitl-cycle.md, llm-serving.md, ingest-schema.md)

docs/docs/architecture/hitl-cycle.md (≥60 lines):
- ## Overview (HITL-01..10 — link to REQUIREMENTS.md)
- ## Sequence Diagram (Mermaid sequenceDiagram: agent → graph → interrupt → PG → NATS → operator → REST → resume → audit)
- ## Approval Queue (D-55 — hitl.approvals shape; tier+SLA matrix)
- ## Escalation Chain (D-57 — 2/15/60min table + Safety Interlock no-timeout)
- ## Safety Interlock (D-58 — forbidden_subjects + forbidden_action_types; whitelist YAML)
- ## Audit Dual-Write (D-56 — PG-first invariant; outbox retry)
- ## Governor (D-58 — 80% threshold + cooldown)
- ## Decision Matrix (table: input → tier → SLA → next_tier → audit decision value)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <id>04-08-01</id>
  <name>Task 1: Replay tool (replay_thread + ReplayResult) + integration test</name>
  <files>packages/sft-agents/src/sft_agents/replay/__init__.py, packages/sft-agents/src/sft_agents/replay/from_checkpoint.py, packages/sft-agents/tests/test_replay.py</files>
  <read_first>
    packages/sft-tools/src/sft_tools/replay/models.py (ReplayRecord pattern — analog for ReplayResult shape)
    packages/sft-tools/src/sft_tools/replay/cmapss.py (full replay tool implementation — pattern reference)
    packages/sft-agents/src/sft_agents/memory/episodic.py (Plan 04-06 — EpisodicReplay.replay_thread consumer)
    packages/sft-agents/src/sft_agents/runtime/checkpointer.py (Plan 04-05 — get_postgres_checkpointer)
    .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md (§8 replay best-effort Phase 4; Pitfall §5 LLM determinism caveat)
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-46 ReplayRecord re-used + CORE-10 + HITL-08 + scope_boundaries replay Phase 11 frozen outputs)
  </read_first>
  <behavior>
    - `replay_thread("ops.operator-assistant.<uuid>", pool=pool, checkpointer=saver, fake_llm=FakeListChatModel(responses=[...]))` returns ReplayResult with replayed_steps matching recorded audit row count
    - Tool calls are deterministic: replayed evidence_panel.tool_calls equals recorded evidence_panel.tool_calls (no real tool execution)
    - LLM calls: with fake_llm provided, replayed prompt_hash equals recorded prompt_hash for steps that re-use exact input; divergence_at_step set on first mismatch
    - write_audit=False (default): no new audit.actions rows; replayed_audit_ids is None
    - write_audit=True: writes new audit rows with cluster + agent_id of original AND action_type='REPLAY:<original_action_type>'; replayed_audit_ids returned
    - action_id parameter: replay stops AFTER reaching recorded action with that id (HITL-08 rollback substrate)
    - Empty audit log → returns ReplayResult with empty replayed_steps, divergence_at_step=None
    - Replay records `ts_replay_start` and `ts_replay_end` (tz-aware UTC)
  </behavior>
  <action>
    `replay/__init__.py` re-exports `replay_thread, ReplayResult, ReplayedAgentStep`.
    `replay/from_checkpoint.py`:
    - Import EpisodicReplay (Plan 04-06), AuditRecord (Plan 04-01), AuditWriter (Plan 04-06), structlog, asyncpg.
    - Pydantic frozen models `ReplayedAgentStep` and `ReplayResult` (with tz-aware validators on datetimes).
    - `async def replay_thread(thread_id, *, pool, checkpointer, fake_llm=None, action_id=None, write_audit=False, audit_writer=None) -> ReplayResult`:
      1. ts_replay_start = datetime.now(timezone.utc)
      2. episodic = EpisodicReplay(pool=pool); records = await episodic.replay_thread(thread_id)
      3. If action_id is given, truncate records at the first matching record (inclusive).
      4. For each record in records: build a ReplayedAgentStep:
         - step_index from enumeration
         - recorded_action = record (full AuditRecord)
         - tool_calls_match: True (by definition — deterministic; populated from recorded evidence_panel.tool_calls)
         - llm_prompt_hash_match: if fake_llm is None → True (skip LLM call); else compute hash of "would-be" prompt from recorded input_summary + tool_calls, compare to recorded prompt_hash; mismatch → set divergence_reason
         - replayed_state_delta: dict approximating what re-execution would produce — use recorded evidence_panel projection: `{"messages_appended":[], "tool_calls":[...], "model": recorded.evidence_panel.model}`
         - divergence_reason: None unless prompt_hash mismatches
      5. divergence_at_step = first step with divergence_reason not None (or None if all match)
      6. If write_audit AND audit_writer is not None: per step, build a new AuditRecord with cluster=record.cluster, agent_id=record.agent_id, thread_id=record.thread_id, action_type=f"REPLAY:{record.action_type}", decision=Decision.AUTO (replay is system-initiated, not human; mark via action_type prefix to satisfy T-04-Audit-Tamper distinction), evidence_panel=record.evidence_panel.model_copy(update={"input_summary": f"[REPLAY of {record.action_id}] " + record.evidence_panel.input_summary[:400]}), approval_id=None, motivation=None; await audit_writer.write(new_record); collect new_ids.
      7. ts_replay_end = datetime.now(timezone.utc).
      8. Return ReplayResult.
    - Add `async def _hash_prompt(input_summary: str, tool_calls: list) -> str`: sha256 hex of canonical-json(input_summary + tool_calls). Used for prompt_hash comparison.
    - structlog logs every step + final summary (records_count, divergence_at_step, write_audit).

    `tests/test_replay.py` (UPGRADE from W0 stub): integration test (testcontainers PG + NATS). Test 1: seed 5 audit.actions rows for thread_id="ops.operator-assistant.<replay-test-1>" with known evidence_panels; call replay_thread without fake_llm; assert ReplayResult.replayed_steps length == 5; assert divergence_at_step is None; assert replayed_audit_ids is None. Test 2: with fake_llm=FakeListChatModel(responses=[same hash content]); assert all steps have llm_prompt_hash_match=True. Test 3: with fake_llm=FakeListChatModel returning different response; assert divergence_at_step == 0 (first step mismatches). Test 4: action_id=<3rd record id>; assert replayed_steps length == 3 (truncated). Test 5: write_audit=True; assert 5 new audit.actions rows exist with action_type starting with "REPLAY:"; assert replayed_audit_ids has 5 UUIDs. Test 6: empty audit log → ReplayResult with empty steps.

    Conventional commits: (1) `feat(04-08-replay-roadmap-docs-01): replay tool from checkpoint + audit log (CORE-10, HITL-08)`, (2) `test(04-08-replay-roadmap-docs-01): replay determinism + divergence detection + write_audit modes`.
  </action>
  <pattern_ref>packages/sft-tools/src/sft_tools/replay/cmapss.py (full file — replay tool structure analog) ; packages/sft-tools/src/sft_tools/replay/models.py:25-63 (ReplayRecord Pydantic shape — analog for ReplayResult/ReplayedAgentStep)</pattern_ref>
  <threat_ref>T-04-Audit-Tamper (replay-written audit rows distinguish from original via action_type prefix 'REPLAY:' + input_summary prefix '[REPLAY of ...]'; no fake originals) ; T-04-LLM-Inject (prompt_hash comparison detects if a replay would diverge — surfaces tampering)</threat_ref>
  <acceptance_criteria>
    - `python -c "from sft_agents.replay import replay_thread, ReplayResult, ReplayedAgentStep; print('ok')"` exits 0
    - `grep -nE 'sha256' packages/sft-agents/src/sft_agents/replay/from_checkpoint.py` returns at least 1 match (prompt hash)
    - `grep -nF 'REPLAY:' packages/sft-agents/src/sft_agents/replay/from_checkpoint.py` returns at least 1 match (replay-written audit action_type prefix)
    - `nx test sft-agents --testNamePattern=test_replay` exits 0 (6 test cases pass)
  </acceptance_criteria>
  <verify>
    <automated>nx test sft-agents --testNamePattern=test_replay</automated>
  </verify>
  <done>replay_thread reconstructs agent steps from audit log; divergence detection via prompt_hash; write_audit mode distinguishes replay rows; 6 test cases green.</done>
  <commit_scope>feat(04-08-replay-roadmap-docs)</commit_scope>
</task>

<task type="auto" tdd="true">
  <id>04-08-02</id>
  <name>Task 2: Phase 4 architecture docs (agentic-runtime + hitl-cycle) + mkdocs.yml nav</name>
  <files>docs/docs/architecture/agentic-runtime.md, docs/docs/architecture/hitl-cycle.md, docs/mkdocs.yml</files>
  <read_first>
    docs/mkdocs.yml (current nav structure — find architecture section)
    docs/docs/architecture/ (existing pages from Phase 3 — replicate structure: front-matter, headings, language)
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (decisions D-53..D-60 verbatim source of truth)
    .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md (§Summary + §Architectural Responsibility Map)
    .planning/phases/03-it-ot-simulation-layer/03-CONTEXT.md (cross-references to ingest-schema.md, opcua-schema.md — link these as sibling pages)
  </read_first>
  <behavior>
    - `docs/docs/architecture/agentic-runtime.md` exists with the 10-section structure above; rendered by mkdocs without warnings
    - `docs/docs/architecture/hitl-cycle.md` exists with sequence diagram (Mermaid) + decision matrix; rendered by mkdocs without warnings
    - `docs/mkdocs.yml` nav includes both new pages under Architecture section
    - `mkdocs build --strict` (or equivalent) succeeds (no broken internal links)
    - Italian/English bilingual content per Phase 1 i18n setup (front-matter `lang: it` for primary; EN translations can come Phase 12 — but the Phase 4 docs MUST be technical-English-by-default to align with PATTERNS.md cross-cutting "tech docs primarily English; user-facing IT first")
  </behavior>
  <action>
    Create `docs/docs/architecture/agentic-runtime.md`:
    - Front-matter `--- title: "Core Agentic Runtime" tags: [phase-4, architecture, langgraph, hitl] ---`
    - Sections per interfaces block above (10 sections, ≥100 lines total).
    - For ## Cluster Structure: table with 5 rows (cluster | agent_count | slugs | typical SLA) referencing D-53.
    - For ## Supervisor Routing: brief explanation + link to `packages/sft-agents/src/sft_agents/policies/routing.yaml` (relative link).
    - For ## Memory Layers: explain Plan 04-06 EpisodicReplay + Plan 04-01 StubLongTermMemory + that Phase 5 will replace stub with QdrantLongTermMemory.
    - For ## Replay: mention `replay_thread(thread_id, action_id, write_audit=False)` + best-effort determinism caveat (Pitfall §5).
    - Cross-references at bottom: `- [HITL Cycle](./hitl-cycle.md)` `- [LLM Serving](./llm-serving.md)` `- [Ingest Schema](./ingest-schema.md)` (Phase 3 link).
    Create `docs/docs/architecture/hitl-cycle.md`:
    - Front-matter `--- title: "HITL Cycle" tags: [phase-4, architecture, hitl, governance] ---`
    - ## Overview with REQUIREMENTS.md HITL-01..10 link
    - ## Sequence Diagram (Mermaid):
      ```
      sequenceDiagram
        participant Agent
        participant SupervisorGraph
        participant PG as PostgreSQL
        participant NATS
        participant Operator
        participant API as api-gateway

        Agent->>SupervisorGraph: ProposedAction(requires_tier=operator)
        SupervisorGraph->>SafetyInterlock: check(action)
        alt forbidden
          SafetyInterlock->>PG: audit decision=interlock_reject
          SafetyInterlock-->>Agent: SafetyInterlockRejection
        else allowed
          SupervisorGraph->>PG: INSERT hitl.approvals (status=pending)
          SupervisorGraph->>NATS: publish hitl.approvals.new.operator
          SupervisorGraph->>SupervisorGraph: interrupt() → checkpoint persisted
          NATS-->>Operator: notification
          Operator->>API: POST /v1/approvals/{id}/decide
          API->>PG: UPDATE hitl.approvals SET status=approved
          API->>SupervisorGraph: Command(resume=ApprovalDecision)
          SupervisorGraph->>PG: INSERT audit.actions (decision=hitl_operator)
          SupervisorGraph->>NATS: publish audit.actions.<cluster>.<agent>
        end
      ```
    - ## Approval Queue Schema (link to migration 002)
    - ## Escalation Chain (D-57 table: operator 2min → supervisor 15min → manager 60min → alert)
    - ## Safety Interlock (D-58 forbidden_subjects + forbidden_action_types table)
    - ## Audit Dual-Write (D-56 invariant: PG sync first; NATS async; outbox retry)
    - ## Governor (D-58 80% threshold + 20 sample min + 5-min cooldown)
    - ## Decision Matrix (table: tier | SLA | next_tier | audit_decision_value)
    Update `docs/mkdocs.yml`:
    - Find `nav:` section; under Architecture add:
      ```yaml
      - Architecture:
          - Overview: architecture/index.md
          - Ingest Schema: architecture/ingest-schema.md
          - OPC-UA Schema: architecture/opcua-schema.md
          - LLM Serving: architecture/llm-serving.md   # Plan 04-03
          - Agentic Runtime: architecture/agentic-runtime.md   # NEW Plan 04-08
          - HITL Cycle: architecture/hitl-cycle.md             # NEW Plan 04-08
      ```
    - (Exact YAML structure depends on existing mkdocs.yml — read first, then append minimally without breaking existing entries.)
    Verify mkdocs builds: `mkdocs build --strict` should exit 0 (no broken links). If link to ingest-schema.md or opcua-schema.md is broken (those are Phase 3 — must exist), adjust path or omit that specific cross-ref.

    Conventional commits: (1) `docs(04-08-replay-roadmap-docs-02): add phase 4 agentic-runtime architecture page`, (2) `docs(04-08-replay-roadmap-docs-02): add phase 4 hitl-cycle architecture page with mermaid sequence diagram`, (3) `docs(04-08-replay-roadmap-docs-02): wire new pages into mkdocs nav`.
  </action>
  <pattern_ref>docs/docs/architecture/ingest-schema.md and opcua-schema.md (Phase 3 03-07 deliverables — use as structure analog: front-matter + heading hierarchy + cross-ref pattern)</pattern_ref>
  <threat_ref>—</threat_ref>
  <acceptance_criteria>
    - `test -f docs/docs/architecture/agentic-runtime.md && wc -l docs/docs/architecture/agentic-runtime.md | awk '{exit ($1 < 100)}'` exits 0 (≥100 lines)
    - `test -f docs/docs/architecture/hitl-cycle.md && wc -l docs/docs/architecture/hitl-cycle.md | awk '{exit ($1 < 60)}'` exits 0 (≥60 lines)
    - `grep -nF 'sequenceDiagram' docs/docs/architecture/hitl-cycle.md` returns 1 match (Mermaid block)
    - `grep -nF 'agentic-runtime.md' docs/mkdocs.yml` and `grep -nF 'hitl-cycle.md' docs/mkdocs.yml` both return at least 1 match
    - `cd docs && mkdocs build --strict 2>&1 | tail -10` shows no WARNING and no ERROR (or run from repo root with `--config-file docs/mkdocs.yml`)
    - `grep -nE '\bAccenture\b' docs/docs/architecture/agentic-runtime.md docs/docs/architecture/hitl-cycle.md` returns 0 matches (Phase 12 DEL-08 anti-pattern check applied early)
  </acceptance_criteria>
  <verify>
    <automated>cd docs && mkdocs build --strict 2>&1 | tail -10</automated>
  </verify>
  <done>2 architecture pages shipped with proper front-matter + Mermaid diagram; mkdocs nav updated; mkdocs build --strict succeeds.</done>
  <commit_scope>docs(04-08-replay-roadmap-docs)</commit_scope>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <id>04-08-03</id>
  <name>Task 3: [BLOCKING] ROADMAP.md edit — align Phase 4 to D-53 (4 → 5 clusters)</name>
  <what-built>Phase 4 SDK now ships 5 cluster subgraphs (D-53). The ROADMAP.md Phase 4 description still says "four cluster subgraph skeletons" (line 83 of ROADMAP.md). This is BLOCKING because traceability validators (Phase 12 DEL deliverables) cross-check ROADMAP against CONTEXT decisions; the mismatch would fail the audit.</what-built>
  <how-to-verify>
    1. Open `.planning/ROADMAP.md` and locate the Phase 4 section (search for `### Phase 4: Core Agentic Runtime & HITL`).
    2. Update the **Goal** line:
       - FROM: `The LangGraph supervisor graph with four cluster subgraph skeletons, ...`
       - TO:   `The LangGraph supervisor graph with five cluster subgraph skeletons (Operations, Maintenance, Knowledge-Curation, Knowledge-Training, Supply per D-53), ...`
       (Preserve the rest of the Goal sentence exactly.)
    3. If success criterion #1 references "four cluster" or "4 cluster", update consistently. (Read the full Phase 4 section before editing — there may be 1-3 references.)
    4. Update the Phase 4 **Plans** count placeholder: change `**Plans**: TBD` to `**Plans**: 8 plans` and below it list all 8 PLAN.md filenames with their primary objective (mirror the Phase 3 pattern in ROADMAP.md):
       ```
       Plans: 8 plans
         - [ ] 04-01-sdk-foundation-PLAN.md — Pydantic models + ABCs + Wave 0 stubs (CORE-01, CORE-02, HITL-06, HITL-07)
         - [ ] 04-02-pg-migrations-PLAN.md — 002+003+004+005 SQL migrations + REVOKE + outbox + langgraph-init [BLOCKING migration push] (CORE-04, CORE-08, CORE-09, HITL-05)
         - [ ] 04-03-llm-adapter-PLAN.md — LLM_BACKEND factory + BudgetingChatModel + Langfuse callback + tool registry + vLLM Hermes docs (CORE-05, CORE-06, CORE-07)
         - [ ] 04-04-nats-audit-stream-PLAN.md — AUDIT_STREAM bootstrap + AuditNatsPublisher + injection-safe subject derivation (CORE-08, HITL-05)
         - [ ] 04-05-supervisor-clusters-checkpointer-PLAN.md — Supervisor StateGraph + 5 cluster subgraphs + HybridRouter + AsyncPostgresSaver + recursion_limit-to-HITL safe_invoke (CORE-02, CORE-03, CORE-04, CORE-07)
         - [ ] 04-06-hitl-middleware-PLAN.md — interrupt/resume node + AuditWriter dual-write + outbox retry + SafetyInterlockMiddleware + EscalationSupervisor + Governor + BudgetTracker + GDPRRedactor + EpisodicReplay (HITL-01..10, CORE-08, CORE-09)
         - [ ] 04-07-api-gateway-e2e-PLAN.md — FastAPI scaffold + lifespan + /v1/approvals + /v1/threads/{id}/resume + Idempotency-Key + E2E HITL cycle survives docker compose restart (HITL-01, HITL-04, CORE-04)
         - [ ] 04-08-replay-roadmap-docs-PLAN.md — replay_thread tool + mkdocs architecture pages + ROADMAP edit [BLOCKING] (CORE-10, HITL-08)
       ```
    5. Save the file.
    6. Verify with: `grep -nE 'four cluster|4 cluster' .planning/ROADMAP.md | grep -v 'four cluster.*→ five cluster\|historical'` returns 0 matches. (Allow explicit "deprecated: four cluster → five cluster per D-53" notes only.)
    7. Verify the Plans count consistency: `grep -nE 'Phase 4.*0/TBD' .planning/ROADMAP.md` returns 0 matches (the progress table row also needs the count updated from `0/TBD` to `0/8`).
    8. Commit: `git add .planning/ROADMAP.md && git commit -m "docs(04-08-replay-roadmap-docs-03): align ROADMAP phase 4 to D-53 (4→5 clusters) and finalize plan list"`
  </how-to-verify>
  <pattern_ref>—</pattern_ref>
  <threat_ref>—</threat_ref>
  <resume-signal>Type "approved" after the edit is committed and the two grep verifications return 0 hits, OR paste the offending lines if the edit is non-trivial. Why blocking: traceability gate — leaving the inconsistency violates the Phase 4 closure invariant (D-53 must show in ROADMAP).</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| audit.actions (read) → replay reconstruction | Read-only path; replay does NOT mutate originals; write_audit creates new rows distinguished by action_type prefix |
| replay-written audit row → audit.actions | Distinguished from originals via action_type 'REPLAY:' prefix; auditor can filter |
| ROADMAP.md edit | Manual; human-authored; commit-traced |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-Audit-Tamper | Tampering | replay_thread(write_audit=True) | mitigate | Replay rows distinguish from originals via action_type='REPLAY:<orig>' + input_summary '[REPLAY of <id>] ...' prefix; auditor SQL filter trivial; T-04-Audit-Tamper Plan 04-02 REVOKE still applies (replay also goes through agent_role grants) |
| T-04-LLM-Inject | Tampering | replay prompt_hash comparison | mitigate | Replay surfaces prompt_hash divergence — if an attacker tampered with audit log between original and replay, divergence_at_step flags it (forensics aid) |
| T-04-Audit-Tamper (replay forge) | Tampering | replay_thread(write_audit=True) | accept | Replay can theoretically forge "fake history" if attacker controls invocation — but only via authenticated agent_role + audit row clearly tagged 'REPLAY:'; Phase 11 adds signed audit rows |
</threat_model>

<verification>
- replay_thread test green (6 cases: happy path, divergence detection, action_id truncation, write_audit mode, empty log)
- 2 mkdocs pages render via `mkdocs build --strict` with no warnings
- ROADMAP.md Phase 4 references 5 clusters (D-53 aligned) + Plans count = 8 + Plans list complete
- Phase 4 anti-pattern check: no "Accenture" string in new docs (early DEL-08 hygiene)
</verification>

<success_criteria>
- CORE-10: replay deterministic best-effort (tool calls frozen from audit; LLM with seed + prompt_hash compare)
- HITL-08: replay tool provides rollback substrate via event-sourcing replay
- D-53 traceability closed: ROADMAP aligned with CONTEXT decisions
- Phase 4 architecture documented in mkdocs (agentic-runtime + hitl-cycle pages)
- 8/8 Phase 4 plans listed in ROADMAP.md
</success_criteria>

<output>
Create `.planning/phases/04-core-agentic-runtime-hitl/04-08-SUMMARY.md`. Include: replay_thread API, divergence detection mechanism, mkdocs pages added, ROADMAP edit confirmation (4→5 clusters + 8 plans listed), Phase 4 final state (all 20 requirement IDs satisfied across the 8 plans).

Also create `.planning/phases/04-core-agentic-runtime-hitl/PHASE-SUMMARY.md` (phase-level): mapping of all 20 requirement IDs to plans, success criteria evidence (which test/artifact proves each), deferrals to Phase 5-12, known limitations (replay best-effort; auth deferred; Langfuse self-hosted server deferred).
</output>
