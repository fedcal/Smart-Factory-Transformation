---
phase: 6
slug: agents-operations-production
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-23
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio + testcontainers |
| **Config file** | `pyproject.toml` (per-package) + `tests/conftest.py` (root + ops e2e) |
| **Quick run command** | `nx run-many --target=test --projects=ops-operator-assistant,ops-production-planner,ops-quality-inspector,ops-anomaly-detector,sft-agents,sft-domain --skip-nx-cache` |
| **Full suite command** | `nx affected --target=test -m "integration or e2e"` |
| **Estimated runtime** | ~180s quick (unit only); ~480s full (testcontainers Qdrant+Neo4j+TSDB+NATS+PG) |

Markers:
- `unit` (default — no testcontainers)
- `integration` (testcontainers required)
- `e2e` (full ops scenario with mock LLM)
- `real-llm` (opt-in real Qwen2.5 via Ollama — CI skip)

---

## Sampling Rate

- **After every task commit:** Run quick command (unit tests of affected packages) — ~60-90s budget
- **After every plan wave:** Run full suite of affected projects with `-m "integration or e2e"` markers
- **Before `/gsd:verify-work`:** Full suite green + 12 E2E ops scenarios pass (3 scenarios × 4 agents)
- **Max feedback latency:** 90 seconds for unit; 480s for full integration+e2e

---

## Per-Task Verification Map

> Filled in by planner with per-task entries. Wave 0 shell shown below; planner expands with concrete task IDs after Wave 0 stub generation.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-00-01 | 00-w0-stubs | 0 | OPS-01..06 | — | N/A — test scaffold | unit | `pytest tests/e2e/ops/ -m "not real-llm" --collect-only` | ❌ W0 | ⬜ pending |
| 06-01-XX | 01-mock-llm-backend | 1 | OPS-05 | — | Mock LLM never calls external network | unit | `pytest packages/sft-agents/tests/llm/test_mock_backend.py` | ❌ W0 | ⬜ pending |
| 06-02-XX | 02-rate-limiter | 1 | OPS-04 (12 alert/h) | T-V6-throttle | Rate limiter persists across restart | integration | `pytest packages/sft-agents/tests/runtime/test_rate_limiter.py -m integration` | ❌ W0 | ⬜ pending |
| 06-03-XX | 03-ops-cluster-routing | 1 | OPS-05 | — | Subgraph routes to correct child agent | unit | `pytest packages/sft-agents/tests/runtime/test_clusters_ops.py` | ❌ W0 | ⬜ pending |
| 06-04-XX | 04-ops-domain-models | 1 | OPS-01..04 | — | Pydantic frozen + extra=forbid | unit | `pytest packages/sft-domain/tests/test_ops_models.py` | ❌ W0 | ⬜ pending |
| 06-05-XX | 05-anomaly-detector | 2 | OPS-04 | T-V6-baseline | YAML baseline override applied | integration | `pytest apps/agents/ops/anomaly-detector/tests/ -m integration` | ❌ W0 | ⬜ pending |
| 06-06-XX | 06-quality-inspector | 2 | OPS-03, OPS-05 | T-V6-injection | dye_lot_id required, NATS subject safe | integration | `pytest apps/agents/ops/quality-inspector/tests/ -m integration` | ❌ W0 | ⬜ pending |
| 06-07-XX | 07-production-planner | 2 | OPS-02 | — | Schedule no-overlap invariant | unit+integration | `pytest apps/agents/ops/production-planner/tests/` | ❌ W0 | ⬜ pending |
| 06-08-XX | 08-operator-assistant | 2 | OPS-01, OPS-05 | T-V6-citation | Citation validator blocks ungrounded response | integration | `pytest apps/agents/ops/operator-assistant/tests/ -m integration` | ❌ W0 | ⬜ pending |
| 06-09-XX | 09-sim-textile-extension | 1 | OPS-03 | — | quality_event_generator NATS subject + dye_lot state | integration | `pytest simulators/sim-textile/tests/test_quality_generator.py -m integration` | ❌ W0 | ⬜ pending |
| 06-10-XX | 10-agents-scheduler | 2 | OPS-04 | — | Scheduler single-replica + misfire grace | integration | `pytest services/agents-scheduler/tests/ -m integration` | ❌ W0 | ⬜ pending |
| 06-11-XX | 11-api-gateway-ops-endpoints | 3 | OPS-01,02,03,04 | T-V6-injection | Endpoints validate Pydantic + propagate user_roles | integration | `pytest apps/api-gateway/tests/test_ops_endpoints.py -m integration` | ❌ W0 | ⬜ pending |
| 06-12-XX | 12-e2e-scenarios | 3 | OPS-06 (success criterion #5) | — | 12 scenarios (3×4 agents) pass | e2e | `pytest tests/e2e/ops/ -m "e2e and not real-llm"` | ❌ W0 | ⬜ pending |
| 06-13-XX | 13-docs-mkdocs | 3 | OPS-05 | — | MkDocs builds with new ops pages | unit | `mkdocs build --strict --config-file docs/mkdocs.yml` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Note:** planner refines task IDs (`06-NN-XX`) during Wave 0 task generation. Plan IDs may be reorganized into different wave compositions; the rows above describe expected coverage breadth.

---

## Wave 0 Requirements

Wave 0 stubs (test scaffolds + shared fixtures + mock LLM infra) MUST exist before Wave 1 implementation begins:

- [ ] `packages/sft-agents/tests/llm/test_mock_backend.py` — stub tests for MockReplayChatModel
- [ ] `packages/sft-agents/src/sft_agents/llm/mock.py` — `MockReplayChatModel(BaseChatModel)` skeleton + JSONL loader
- [ ] `packages/sft-agents/tests/runtime/test_rate_limiter.py` — stub for global 12/h rate limiter
- [ ] `packages/sft-agents/tests/runtime/test_clusters_ops.py` — stub for ops cluster routing
- [ ] `packages/sft-domain/tests/test_ops_models.py` — stub for `Anomaly`, `QualityEvent`, `ScheduleDraft` Pydantic models
- [ ] `apps/agents/ops/anomaly-detector/tests/test_anomaly_detector.py` — stub OPS-04 happy/degraded/failure
- [ ] `apps/agents/ops/quality-inspector/tests/test_quality_inspector.py` — stub OPS-03 happy/degraded/failure
- [ ] `apps/agents/ops/production-planner/tests/test_production_planner.py` — stub OPS-02 happy/degraded/failure
- [ ] `apps/agents/ops/operator-assistant/tests/test_operator_assistant.py` — stub OPS-01 happy/degraded/failure
- [ ] `simulators/sim-textile/tests/test_quality_generator.py` — stub for quality_event_generator
- [ ] `services/agents-scheduler/tests/test_scheduler.py` — stub for cron 5min
- [ ] `apps/api-gateway/tests/test_ops_endpoints.py` — stub OPS endpoints
- [ ] `tests/e2e/ops/conftest.py` — shared fixtures (mock_llm_backend, ops_scenario loader, all 4 testcontainers wiring)
- [ ] `tests/fixtures/ops_scenarios/{operator-assistant,production-planner,quality-inspector,anomaly-detector}/{happy,degraded,failure}.yaml` — 12 scenario YAML
- [ ] `tests/fixtures/llm_responses/{operator-assistant,production-planner,quality-inspector,anomaly-detector}/{happy,degraded,failure}.jsonl` — record/replay fixtures
- [ ] `packages/sft-domain/anomaly_baselines.yaml` — YAML schema + loader stub
- [ ] `packages/sft-domain/orders.yaml` + `packages/sft-domain/asset_capacity.yaml` — seed data stubs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-LLM smoke (Qwen2.5-7B via Ollama) on golden path per agente | OPS-06 (acceptance follow-up) | Real LLM is non-deterministic; semantic equivalence judgment | `pytest tests/e2e/ops/ -m real-llm` (requires Ollama running + model pulled) — review citations + reasoning quality manually |
| EvidencePanel citation render preview | OPS-01 | EvidencePanel UI is Phase 10; Phase 6 only validates structured data contract | Inspect `tests/fixtures/ops_scenarios/operator-assistant/happy.yaml` expected output: `citations: [{source_uri, snippet, score, retrieved_at}]` must match RagCitation schema |
| HITL approval queue surfacing | OPS-02, OPS-03 | Phase 6 stops at audit + interrupt(); UI consumer is Phase 10 | Verify via `psql -c "SELECT decision, payload->>'agent' FROM audit.actions WHERE phase=6 ORDER BY created_at DESC LIMIT 10"` that interrupt entries reach PG |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s for unit / 480s for integration+e2e
- [ ] `nyquist_compliant: true` set in frontmatter after planner refinement

**Approval:** pending
