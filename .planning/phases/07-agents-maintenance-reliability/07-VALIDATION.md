---
phase: 7
slug: agents-maintenance-reliability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-23
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `07-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio + testcontainers (Phase 1+ locked) |
| **Config file** | `pyproject.toml` root + per-project (`packages/*/pyproject.toml`, `apps/*/pyproject.toml`) |
| **Quick run command** | `nx run-many --target=test --projects=sft-ml,mnt-predictive-maintenance,mnt-rca-specialist,mnt-maintenance-coach,mnt-downtime-analyzer -- --no-cov -x` |
| **Full suite command** | `nx affected --target=test -- --cov` |
| **Estimated runtime** | ~40-60 seconds (quick), ~3-5 min (full with testcontainers) |

---

## Sampling Rate

- **After every task commit:** Run `nx affected --target=test -- --no-cov -x` (atomic project tests only, <30s typical)
- **After every plan wave:** Run `nx affected --target=test -- --cov` (full coverage report)
- **Before `/gsd:verify-work`:** Full suite must be green + E2E maintenance scenarios pass: `pytest tests/e2e/maintenance/ -m "e2e and not real-llm" --tb=short`
- **Max feedback latency:** 30s (per-task quick), 300s (per-wave full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-00-* | 00 | 0 | (scaffold) | — | N/A | scaffold | `pytest --collect-only` | ❌ W0 | ⬜ pending |
| 07-PM-01 | PM | 2 | MNT-01 | V12 (joblib integrity) | Reject load if companion JSON metadata mismatches | unit + integration | `pytest apps/agents/maintenance/predictive-maintenance/tests/test_inference.py -x` | ❌ W0 | ⬜ pending |
| 07-PM-02 | PM | 1 | MNT-01 | V5 (input validation) | Pydantic v2 frozen+extra=forbid on RULEstimate | unit | `pytest packages/sft-ml/tests/test_feature_map.py -x` | ❌ W0 | ⬜ pending |
| 07-PM-03 | PM | 1 | MNT-01 | V12 | Joblib model load + predict cross-Python compat smoke | smoke | `pytest packages/sft-ml/tests/test_model_smoke.py -x` | ❌ W0 | ⬜ pending |
| 07-PM-E2E-H | PM | 3 | MNT-01 | V5 | E2E happy: AD alert → NATS → PM inference → audit row RUL_ESTIMATE | e2e | `pytest tests/e2e/maintenance/test_predictive_maintenance_scenarios.py::test_happy -x` | ❌ W0 | ⬜ pending |
| 07-PM-E2E-D | PM | 3 | MNT-01 | — | E2E degraded: health_index < 0.3 → HITL supervisor interrupt | e2e | `pytest tests/e2e/maintenance/test_predictive_maintenance_scenarios.py::test_degraded -x` | ❌ W0 | ⬜ pending |
| 07-PM-E2E-F | PM | 3 | MNT-01 | V5 | E2E failure: malformed sensor input → predictable error + audit | e2e | `pytest tests/e2e/maintenance/test_predictive_maintenance_scenarios.py::test_failure -x` | ❌ W0 | ⬜ pending |
| 07-RCA-01 | RCA | 1 | MNT-02 | V5 | RCAChain Pydantic enforce 5 step + ≥1 citation/step | unit | `pytest apps/agents/maintenance/rca-specialist/tests/test_models.py -x` | ❌ W0 | ⬜ pending |
| 07-RCA-02 | RCA | 2 | MNT-02 | T-V7-llm-hallucination | Validator post-LLM enforce + re-prompt 2x + escalate on fail | unit + integration | `pytest apps/agents/maintenance/rca-specialist/tests/test_validators.py -x` | ❌ W0 | ⬜ pending |
| 07-RCA-E2E | RCA | 3 | MNT-02 | — | E2E happy/degraded/failure (mock LLM scenarios) | e2e | `pytest tests/e2e/maintenance/test_rca_specialist_scenarios.py -x` | ❌ W0 | ⬜ pending |
| 07-MC-01 | MC | 2 | MNT-03 | V3 (session) | LangGraph checkpoint thread resume cross-restart (testcontainers PG) | integration | `pytest apps/agents/maintenance/maintenance-coach/tests/test_checkpoint_resume.py -x` | ❌ W0 | ⬜ pending |
| 07-MC-02 | MC | 2 | MNT-03 | — | MTTR computation: thread.created_at → completed_at correct | unit | `pytest apps/agents/maintenance/maintenance-coach/tests/test_mttr.py -x` | ❌ W0 | ⬜ pending |
| 07-MC-03 | MC | 1 | MNT-03 | T-V7-double-write | `request_help` tool wrappa `escalate_to_supervisor` + audit con marker | unit + integration | `pytest packages/sft-agents/tests/tools/test_request_help.py -x` | ❌ W0 | ⬜ pending |
| 07-MC-E2E | MC | 3 | MNT-03 | — | E2E multi-turn happy/degraded/failure con checkpoint replay | e2e | `pytest tests/e2e/maintenance/test_maintenance_coach_scenarios.py -x` | ❌ W0 | ⬜ pending |
| 07-DA-MIG | DA | 1 | MNT-04 | V5 | Migration 008 applies idempotent + hypertable + CAGG created | integration | `pytest infra/migrations/timescale/tests/test_migration_008.py -x` | ❌ W0 | ⬜ pending |
| 07-DA-01 | DA | 2 | MNT-04 | — | OEE.A computation correct on synthetic downtime window | unit | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_oee.py::test_availability -x` | ❌ W0 | ⬜ pending |
| 07-DA-02 | DA | 2 | MNT-04 | V8 (data) | OEE.Q cross-cluster audit query + fallback path | integration | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_oee.py::test_quality_cross_cluster -x` | ❌ W0 | ⬜ pending |
| 07-DA-03 | DA | 2 | MNT-04 | — | Pareto top-N query correct ordering | unit | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_pareto.py -x` | ❌ W0 | ⬜ pending |
| 07-DA-04 | DA | 2 | MNT-04 | T-V7-nats-ack-after-error | NATS durable consumer `da-consumer` ack-after-INSERT + nak-on-error | integration | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_consumer.py -x` | ❌ W0 | ⬜ pending |
| 07-DA-E2E | DA | 3 | MNT-04 | — | E2E happy/degraded/failure (deterministic SQL aggregation, no LLM mock) | e2e | `pytest tests/e2e/maintenance/test_downtime_analyzer_scenarios.py -x` | ❌ W0 | ⬜ pending |
| 07-TAX-01 | TAX | 1 | MNT-05 | V5 | `failure_modes.yaml` schema extension loads + reason_code unique | unit | `pytest packages/sft-domain/tests/failure_modes/test_maintenance_meta.py -x` | ❌ W0 | ⬜ pending |
| 07-TAX-02 | TAX | 1 | MNT-05 | — | Validator CI: `intervention_steps_sop_id` esiste in corpus Phase 5 | integration | `pytest scripts/validate_failure_modes_test.py -x` | ⚠️ estendere | ⬜ pending |
| 07-TAX-DOC | TAX | 4 | MNT-05 | — | Doc bilingue `event-taxonomy.{it,en}.md` build OK in mkdocs | doc-build | `mkdocs build --strict` | ✓ Phase 5 | ⬜ pending |
| 07-REG-01 | DA | 2 | MNT-06 | V4 (RBAC) | Asset registry integration (sft-assets) + downtime_events FK-like check | integration | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_repository.py::test_asset_validation -x` | ❌ W0 | ⬜ pending |
| 07-REG-02 | PM | 3 | MNT-06 | — | Audit chain `triggered_by_action_id` link AD→PM | integration | `pytest tests/e2e/maintenance/test_predictive_maintenance_scenarios.py::test_audit_chain -x` | ❌ W0 | ⬜ pending |
| 07-AE-01 | AE | 1 | (audit ext) | V5 | Migration 009 ActionType ext idempotent + enum lockstep | integration | `pytest infra/migrations/timescale/tests/test_migration_009.py -x` | ❌ W0 | ⬜ pending |
| 07-AE-02 | AE | 1 | (audit ext) | V5 | Python `ActionType` ↔ SQL CHECK constraint round-trip | unit | `pytest packages/sft-agents/tests/test_audit_constraints.py -x` (estendere) | ⚠️ estendere | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 (test scaffold, mirror pattern Phase 6 06-00) DEVE creare:

- [ ] `packages/sft-ml/tests/__init__.py` + `test_feature_map.py` + `test_model_smoke.py` placeholder
- [ ] `apps/agents/maintenance/predictive-maintenance/tests/{__init__.py,conftest.py,test_inference.py,test_evidence_panel.py}` placeholder
- [ ] `apps/agents/maintenance/rca-specialist/tests/{__init__.py,conftest.py,test_models.py,test_validators.py,test_evidence_panel.py}` placeholder
- [ ] `apps/agents/maintenance/maintenance-coach/tests/{__init__.py,conftest.py,test_checkpoint_resume.py,test_mttr.py,test_evidence_panel.py}` placeholder
- [ ] `apps/agents/maintenance/downtime-analyzer/tests/{__init__.py,conftest.py,test_oee.py,test_pareto.py,test_consumer.py,test_repository.py,test_evidence_panel.py}` placeholder
- [ ] `infra/migrations/timescale/tests/test_migration_008.py` + `test_migration_009.py` placeholder
- [ ] `tests/e2e/maintenance/{__init__.py,conftest.py,test_predictive_maintenance_scenarios.py,test_rca_specialist_scenarios.py,test_maintenance_coach_scenarios.py,test_downtime_analyzer_scenarios.py}` placeholder
- [ ] `tests/fixtures/mnt_scenarios/<agent>/{happy,degraded,failure}.yaml` — 12 scenario stubs (4 agent × 3)
- [ ] `tests/fixtures/llm_responses/{rca-specialist,maintenance-coach}/{happy,degraded,failure}.jsonl` — 6 mock LLM replay stubs
- [ ] `packages/sft-agents/tests/tools/test_request_help.py` placeholder
- [ ] `packages/sft-domain/tests/failure_modes/test_maintenance_meta.py` placeholder
- [ ] Estendere `scripts/validate-failure-modes.py` con nuovo check `reason_code` unicità
- [ ] Estendere `packages/sft-agents/tests/test_audit_constraints.py` con i 5 nuovi ActionType (round-trip)

**Mock LLM strategy per Phase 7:**
- **PredictiveMaintenance**: NO LLM mock needed — deterministic scikit-learn inference. Test fixtures = pre-computed sensor windows + expected RUL output (assertion exact match).
- **DowntimeAnalyzer**: NO LLM mock needed — deterministic SQL aggregation. Test fixtures = pre-seeded `downtime_events` rows + expected `OEEReport`.
- **RCASpecialist**: LLM mock REQUIRED (record/replay JSONL via 06-03 MockReplayChatModel). 3 scenari × happy (valid 5-Why) / degraded (1 retry needed) / failure (2 retry → escalation).
- **MaintenanceCoach**: LLM mock REQUIRED. 3 scenari × happy (5-step intervention completes) / degraded (technician keyword "aiuto" mid-flow) / failure (LLM produce step inesistente).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration 008 push to dev TimescaleDB (CAGG materialization with sample data) | MNT-04 | Live PG required, testcontainers covers schema not population | `make migrate-timescale` then `SELECT * FROM maintenance.oee_hourly LIMIT 5;` |
| Migration 009 push to dev TimescaleDB | (audit ext) | Same as Phase 6 D-AE-MNT pattern | `make migrate-timescale` then verify `audit.actions_action_type_chk` includes 5 new values |
| Real-LLM smoke for RCASpecialist + MaintenanceCoach (Qwen2.5-7B via Ollama) | MNT-02, MNT-03 | Semantic equivalence requires human judgment | `pytest tests/e2e/maintenance/ -m real-llm` + review citations + 5-Why coherence |
| HITL approval queue surfacing for RCA recommendations | MNT-02 | UI consumer ships in Phase 10 | Inspect `audit.actions WHERE decision='hitl_supervisor' AND action_type='RCA_CHAIN'` |
| C-MAPSS model card review — accept domain-shift limitation | MNT-01 | Documentation review by domain expert | Review `packages/sft-ml/MODEL_CARD.md` + Pitfall 3 disclaimer |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies declared
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (28 test files + scaffolds + 12 YAML + 6 JSONL)
- [ ] No watch-mode flags in CI commands
- [ ] Feedback latency < 30s (per-task) / < 300s (per-wave)
- [ ] `nyquist_compliant: true` set in frontmatter (toggled by plan-checker after coverage verification)

**Approval:** pending
</content>
</invoke>