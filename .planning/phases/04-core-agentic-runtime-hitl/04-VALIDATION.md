---
phase: 4
slug: core-agentic-runtime-hitl
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-18
nyquist_signed_off_at: 2026-05-18
---

> **Nyquist sign-off rationale:** Plan 04-01 Task 3 creates all 12 Wave 0 stub files
> enumerated below (with `pytest.mark.skip(reason="W0 — implemented in Wave N")` until
> the corresponding implementation wave lands). `conftest.py` fixtures (`mock_pool`,
> `mock_nats_js`, `mock_llm`, `mock_checkpointer`, `frozen_dt`) are created in Plan 04-01
> Task 1. Every task in plans 04-01..04-08 has an `<automated>` verify command (or is a
> manual checkpoint), no 3-consecutive-task gap exists, and feedback latency targets are
> met (≤ 30s quick / ≤ 6 min full). Validation contract is materialized; flags flipped
> from `false` after plan-checker iteration 1.

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (asyncio, postgres, NATS via testcontainers) |
| **Config file** | `pyproject.toml` per package (`packages/sft-agents/pyproject.toml`, `apps/api-gateway/pyproject.toml`) + root `pytest.ini` |
| **Quick run command** | `nx affected -t test --base=HEAD~1` (≤ 30s on affected packages) |
| **Full suite command** | `nx run-many -t test --projects=sft-agents,api-gateway` (single full Phase 4 pass) |
| **Estimated runtime** | quick ~30s · full ~6 min (incl. testcontainers PG + NATS bootstrap) |

---

## Sampling Rate

- **After every task commit:** Run `nx affected -t test --base=HEAD~1` (target package only — Nyquist signal at task granularity)
- **After every plan wave:** Run `nx run-many -t test --projects=sft-agents,api-gateway` (cross-package integration)
- **Before `/gsd:verify-work`:** Full suite must be green AND `docker compose -f infra/compose/core.yml up -d && python tests/e2e/test_hitl_cycle.py` (end-to-end success criterion #1)
- **Max feedback latency:** 30s (quick) · 6 min (full)

---

## Per-Task Verification Map

> Filled by the planner during PLAN.md generation. Each task line links a `<requirement>` ID and a `<threat>` ref (from PLAN.md `<threat_model>`) to a concrete pytest test command. Wave 0 stubs must exist before any implementation task in subsequent waves runs.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-W0 | 01 | 0 | (test scaffold) | — | Wave 0 stubs in place | scaffold | `test -d packages/sft-agents/tests` | ❌ W0 | ⬜ pending |
| 04-01-01 | 01 | 1 | CORE-01, CORE-02 | T-04-01 | `Agent`/`Tool`/`Memory`/`Policy` ABCs reject unknown subclasses; Pydantic v2 `frozen=True` + `extra="forbid"` | unit | `nx test sft-agents --testNamePattern=sdk_interfaces` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | CORE-04 | T-04-04 | Migrations idempotent (re-apply no-op); audit.actions REVOKE UPDATE/DELETE enforced | integration | `nx test sft-agents --testNamePattern=migrations_idempotent` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | CORE-05, CORE-06 | T-04-05 | `LLM_BACKEND=ollama\|vllm` switch; no agent code references provider directly | unit | `nx test sft-agents --testNamePattern=llm_adapter_switch` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 2 | CORE-08 | T-04-08 | NATS `AUDIT_STREAM` declared (retention 90d); outbox table retries on NATS failure | integration | `nx test sft-agents --testNamePattern=audit_stream_bootstrap` | ❌ W0 | ⬜ pending |
| 04-05-01 | 05 | 3 | CORE-03, CORE-07 | T-04-03 | Supervisor `StateGraph` compiles; recursion_limit escalates to HITL (not crash) | unit + integration | `nx test sft-agents --testNamePattern=supervisor_recursion` | ❌ W0 | ⬜ pending |
| 04-05-02 | 05 | 3 | CORE-02, CORE-07 | T-04-02 | 5 cluster subgraphs (Ops/Maintenance/Knowledge-Curation/Knowledge-Training/Supply) wired with hybrid routing (rules + LLM fallback) | unit | `nx test sft-agents --testNamePattern=cluster_subgraphs` | ❌ W0 | ⬜ pending |
| 04-06-01 | 06 | 3 | HITL-01, HITL-02, HITL-06 | T-04-H1 | Full `interrupt()` → PG checkpoint → NATS notify → `Command(resume=)` cycle survives service restart; EvidencePanel attached at every interrupt | integration | `nx test sft-agents --testNamePattern=hitl_interrupt_resume` | ❌ W0 | ⬜ pending |
| 04-06-02 | 06 | 3 | HITL-03, HITL-04, HITL-05 | T-04-H3 | 4-tier escalation (Operator→Supervisor→Manager→Safety Interlock) with auto-escalation 2min/15min/1h; Safety Interlock manual-only + whitelist YAML | unit + integration | `nx test sft-agents --testNamePattern=escalation_chain` | ❌ W0 | ⬜ pending |
| 04-06-03 | 06 | 3 | HITL-07, HITL-08 | T-04-H7 | Approval rate governor: sliding-window detection > 80% auto-approve → Manager NATS alert | unit | `nx test sft-agents --testNamePattern=governor_threshold` | ❌ W0 | ⬜ pending |
| 04-06-04 | 06 | 3 | HITL-09, HITL-10, CORE-09 | T-04-B1 | Budget/quota middleware: per-thread + per-agent atomic increment; hard-stop on exhaustion | integration | `nx test sft-agents --testNamePattern=budget_middleware` | ❌ W0 | ⬜ pending |
| 04-06-LT | 06 | 3 | CORE-08 (long-term stub, D-59) | — | `StubLongTermMemory(Memory)` shipped at `packages/sft-agents/src/sft_agents/memory/long_term_stub.py`; `query()` returns `[]` for any input; `store()` raises `NotImplementedError` with Phase 5 message; Phase 4 → Phase 5 import-path contract frozen | unit | `nx test sft-agents --testNamePattern=test_long_term_stub` | ❌ W0 | ⬜ pending |
| 04-07-01 | 07 | 4 | (E2E) | T-04-E1 | api-gateway FastAPI scaffold up; `/v1/threads/{id}/resume` accepts `Command(resume=)` payload | integration | `nx test api-gateway --testNamePattern=resume_endpoint` | ❌ W0 | ⬜ pending |
| 04-07-02 | 07 | 4 | success_criterion #1 #4 | T-04-E1 | E2E HITL cycle survives full `docker compose restart` (cross-restart resume) | e2e | `pytest tests/e2e/test_hitl_cycle.py::test_restart_resume` | ❌ W0 | ⬜ pending |
| 04-08-01 | 08 | 4 | CORE-10 | T-04-10 | Replay tool deterministic re-execution from checkpoint + audit log (mocked tool-call replay) | integration | `nx test sft-agents --testNamePattern=replay_determinism` | ❌ W0 | ⬜ pending |
| 04-08-02 | 08 | 4 | (ROADMAP edit) | — | ROADMAP.md updated 4→5 clusters per D-53 (blocking) | manual | `grep -q "5 cluster" .planning/ROADMAP.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Note:** Final task IDs, wave assignments, and exact test commands are confirmed by the planner in PLAN.md generation. The table above is the validation contract the planner MUST satisfy — every task in PLAN.md needs a corresponding row here (or be marked manual below).

---

## Wave 0 Requirements

- [ ] `packages/sft-agents/tests/conftest.py` — pytest fixtures: `pg_dsn` (testcontainers), `nats_url` (testcontainers), `checkpointer` (AsyncPostgresSaver), `compiled_graph` (LangGraph supervisor with mocks), `llm_mock` (deterministic seed=42 fake LLM)
- [ ] `packages/sft-agents/tests/test_sdk_interfaces.py` — stubs for CORE-01, CORE-02 (Agent/Tool/Memory/Policy ABCs)
- [ ] `packages/sft-agents/tests/test_migrations.py` — stubs for CORE-04 (idempotency + append-only enforcement)
- [ ] `packages/sft-agents/tests/test_llm_adapter.py` — stubs for CORE-05, CORE-06 (LLM_BACKEND env-var switch)
- [ ] `packages/sft-agents/tests/test_supervisor.py` — stubs for CORE-02, CORE-03, CORE-07 (StateGraph + hybrid routing + recursion_limit)
- [ ] `packages/sft-agents/tests/test_hitl_cycle.py` — stubs for HITL-01, HITL-02, HITL-06 (interrupt/resume + EvidencePanel)
- [ ] `packages/sft-agents/tests/test_escalation.py` — stubs for HITL-03..05 (4-tier + timers + Safety Interlock whitelist)
- [ ] `packages/sft-agents/tests/test_governor.py` — stubs for HITL-07, HITL-08 (sliding window)
- [ ] `packages/sft-agents/tests/test_budget.py` — stubs for HITL-09, HITL-10, CORE-09 (middleware quota)
- [ ] `packages/sft-agents/tests/test_replay.py` — stubs for CORE-10 (deterministic replay)
- [ ] `apps/api-gateway/tests/test_resume_endpoint.py` — stubs for E2E resume endpoint
- [ ] `tests/e2e/test_hitl_cycle.py` — stubs for success criteria #1 + #4 (E2E with `docker compose restart`)
- [ ] `testcontainers-python` added to root `pyproject.toml` (per OQ8 — Plan 04-07 fixes Phase 3 port-5432 issue as bonus)

> Per RESEARCH §Validation Architecture: every Wave 0 stub uses `pytest.mark.skip(reason="W0 — implemented in Wave N")` until its implementation wave lands. Stubs MUST import the symbol they will test (forces the symbol to be declared in source ahead of body fill — type-driven scaffolding).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ROADMAP.md edit (4→5 clusters per D-53) is human-readable and consistent with goal text | success_criterion #1 (clusters) | Doc-edit consistency check is judgment, not testable | Review `.planning/ROADMAP.md` Phase 4 section — confirm "5 cluster subgraphs (Ops, Maintenance, Knowledge-Curation, Knowledge-Training, Supply)" replaces "4 cluster" everywhere; success criteria still parse |
| HITL-10 alarm dashboard data primitive (12 alarms/h test signal) | HITL-10 | UI/dashboard rendering deferred to Phase 10 — Phase 4 only ships the data primitive | Confirm `audit.actions` rows have shape consumable by Phase 10 grafana panels (sample query in CONTEXT.md §D-58) |
| Manager-alert NATS message human-readable | HITL-08 | Operator UX of the alert is judgment | `nats sub "alerts.manager.>"` and trigger governor; alert payload includes thread_id + ratio + window |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (quick) · 6 min (full)
- [ ] `nyquist_compliant: true` set in frontmatter (set by planner after PLAN.md generation)

**Approval:** pending
