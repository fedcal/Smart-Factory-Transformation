---
phase: 09-agents-supply-chain-economics
plan: 00b
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/agents/supply/inventory-manager/tests/__init__.py
  - apps/agents/supply/inventory-manager/tests/conftest.py
  - apps/agents/supply/inventory-manager/tests/test_reorder.py
  - apps/agents/supply/inventory-manager/tests/test_inventory_hitl.py
  - apps/agents/supply/energy-optimizer/tests/__init__.py
  - apps/agents/supply/energy-optimizer/tests/conftest.py
  - apps/agents/supply/energy-optimizer/tests/test_enpi.py
  - apps/agents/supply/energy-optimizer/tests/test_energy_hitl.py
  - apps/agents/supply/cost-analyzer/tests/__init__.py
  - apps/agents/supply/cost-analyzer/tests/conftest.py
  - apps/agents/supply/cost-analyzer/tests/test_oepv.py
  - apps/agents/supply/cost-analyzer/tests/test_cost_analyzer_agent.py
  - apps/agents/supply/demand-forecaster/tests/__init__.py
  - apps/agents/supply/demand-forecaster/tests/conftest.py
  - apps/agents/supply/demand-forecaster/tests/test_holt_winters.py
  - apps/agents/supply/demand-forecaster/tests/test_mape.py
  - apps/agents/supply/demand-forecaster/tests/test_demand_hitl.py
autonomous: true
requirements: [SCM-01, SCM-02, SCM-03, SCM-04]
must_haves:
  truths:
    - "Every Phase 9 supply agent test file exists with bodies that name the contract under test (no module-level skip)"
    - "Each test file plus 4 conftests and 4 tests/__init__.py collect without import errors in the test files themselves"
    - "Each HITL lifecycle scaffold asserts interrupt-then-audit ordering: no audit row before resume, exactly 1 DRAFT row and (where applicable) exactly 1 SIGNOFF row after resume, with a STABLE id reused across the replayed node (CR-04)"
  artifacts:
    - path: "apps/agents/supply/inventory-manager/tests/test_inventory_hitl.py"
      provides: "Reorder HITL interrupt-then-audit + stable-id contract (CR-02/CR-04)"
      contains: "PURCHASE_RECOMMENDATION_DRAFT"
    - path: "apps/agents/supply/cost-analyzer/tests/test_cost_analyzer_agent.py"
      provides: "Autonomous Decision.AUTO contract (no interrupt, no SIGNOFF)"
      contains: "Decision.AUTO"
    - path: "apps/agents/supply/demand-forecaster/tests/test_demand_hitl.py"
      provides: "Demand plan HITL + plan-in-state-for-ProductionPlanner contract"
      contains: "DEMAND_PLAN_SIGNOFF"
  key_links:
    - from: "apps/agents/supply/*/tests/test_*.py"
      to: "apps/agents/supply/*/src/scm_*/ (Wave 2-5 modules)"
      via: "import path named in each placeholder body"
      pattern: "scm_"
---

<objective>
Wave 1 foundation B for Phase 9: scaffold every supply agent test file so downstream waves implement against a known contract (Nyquist rule — tests exist before implementation). Mirror the 08-00b pattern exactly.

Purpose: Defines the acceptance surface for the agent waves (09-02..09-05). Each test file names the behavioral contract it will enforce, including the Phase 8 anti-bug guardrails (interrupt-then-audit, stable ids, AuditRecord positional, KPI clamps).
Output: 4× tests/__init__.py, 4× tests/conftest.py, and 9 agent test files with contract-naming bodies.

Split note: 09-00 is split into 09-00a (schema + audit-enum migrations + their tests) and 09-00b (this plan — agent test scaffolds). Both are independent Wave 1 plans with disjoint files — 09-00b touches only `apps/agents/supply/*/tests/`.

Execution note: worktrees DISABLED — sequential executors on main tree.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/09-agents-supply-chain-economics/09-CONTEXT.md
@.planning/phases/09-agents-supply-chain-economics/09-RESEARCH.md
@.planning/phases/08-agents-knowledge-training/08-REVIEW.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Supply agent test scaffolds (Nyquist — tests before impl)</name>
  <files>apps/agents/supply/inventory-manager/tests, apps/agents/supply/energy-optimizer/tests, apps/agents/supply/cost-analyzer/tests, apps/agents/supply/demand-forecaster/tests</files>
  <read_first>
    - apps/agents/knowledge/shift-handover/tests/conftest.py and test_dual_signoff.py (HITL interrupt-then-audit test analog; AsyncMock pool + audit_writer fixtures)
    - apps/agents/knowledge/knowledge-curator/tests/test_dedup.py and test_reuse_rate.py (pure-function + asyncpg mock + KPI clamp analog)
    - apps/agents/maintenance/downtime-analyzer/tests/test_oee.py (pure-function deterministic numeric test analog)
    - 09-RESEARCH.md "Validation Architecture" Phase Requirements → Test Map (exact file list + behaviors) and the Wave 0 Gaps checklist
    - 09-RESEARCH.md Patterns 2/3/4 (interrupt-then-audit, stable id from thread_id, AuditWriter positional) and 08-REVIEW.md CR-02/CR-04/CR-05
  </read_first>
  <action>
    For each of the 4 supply agents create tests/__init__.py and tests/conftest.py (mirror shift-handover conftest: AsyncMock pool and audit_writer fixtures; a patched `interrupt` that on first call raises GraphInterrupt-like and on resume returns a payload — NOT a MagicMock, which masks failures per WR-01). Then create the test files from the RESEARCH Test Map. Use explicit test functions that assert the named contract, or a `def test_placeholder` body that FAILS with a clear message naming the unimplemented contract (NEVER module-level pytest.skip). Files and their named contracts:
    - inventory-manager/tests/test_reorder.py — check_reorder pure function: is_below_threshold True when current_qty < reorder_point, deficit_qty = max(0, reorder_point - current_qty), estimated_cost_eur = reorder_qty * unit_cost_eur; exact Decimal arithmetic, no LLM (SCM-01).
    - inventory-manager/tests/test_inventory_hitl.py — interrupt-then-audit: on first run interrupt is raised BEFORE any audit write (assert 0 audit writes pre-resume); on resume exactly 1 PURCHASE_RECOMMENDATION_DRAFT row then exactly 1 PURCHASE_SIGNOFF row after sign-off; recommendation_id is STABLE across replay (derived from thread_id, NOT uuid4 — CR-04); audit written via a single positional AuditRecord (CR-02); approval_id is None on the pending row (CR-03); REORDER_ALERT emitted (SCM-01).
    - energy-optimizer/tests/test_enpi.py — compute_enpi pure function: enpi_actual = sum(kwh)/sum(kg) over slots with kg>0, deviation_pct vs baseline, is_above_baseline boolean, off_peak_kwh_pct; raises ValueError when no kg>0 slot; exact numbers (SCM-02).
    - energy-optimizer/tests/test_energy_hitl.py — interrupt-then-audit for ENERGY_PROPOSAL then ENERGY_SIGNOFF; stable proposal_id from thread_id; no audit before resume; positional AuditRecord; approval_id None pending (SCM-02).
    - cost-analyzer/tests/test_oepv.py — compute_oepv pure function: total_score = 0.70*pt + 0.30*pe; pe from the parametric non-linear ribasso curve pe_max*(1-exp(-lambda*Ri/Ri_ref)); offer_eur = BA*(1-Ri/100); is_anomaly_warning when Ri >= anomaly_threshold_pct (configurable warning, NOT definitive — F12 boundary); sensitivity dict for ±1/5/10%; ValueError on out-of-range ribasso/pt; coefficients all come from OepvConfig (no hardcoded values) (SCM-03, ECO-02, ECO-05).
    - cost-analyzer/tests/test_cost_analyzer_agent.py — AUTONOMOUS: __call__ does NOT call interrupt; writes audit with Decision.AUTO; read-only (no scm.* writes); aggregates downtime+scrap+energy cost from audit.actions; positional AuditRecord (SCM-03).
    - demand-forecaster/tests/test_holt_winters.py — forecast_holt_winters deterministic output for a fixed series + fixed alpha/beta/gamma (assert exact rounded values); test_seasonal_naive: series shorter than min_periods falls back to seasonal_naive method tag; non-negative forecasts (SCM-04).
    - demand-forecaster/tests/test_mape.py — compute_mape over matched pairs, skips actuals<=0, per-point contribution clamped to 1.0 (100%), returns 0.0 on empty; and MAPE clamped to <=100 before model construction (CR-05) (SCM-04).
    - demand-forecaster/tests/test_demand_hitl.py — interrupt-then-audit for DEMAND_PLAN_DRAFT then DEMAND_PLAN_SIGNOFF; stable plan_id from thread_id; after resume the demand plan for >=2 SKU groups is present in the returned state delta (state["demand_plan"]) so the gateway can route it to ProductionPlanner (Open Question 2 resolution — cross-cluster via state, no direct invocation); approval_id None pending; positional AuditRecord (SCM-04).
    Each placeholder references the agent module path it will import once Waves 2-5 land (e.g. scm_inventory_manager.reorder, scm_cost_analyzer.oepv).
  </action>
  <verify>
    <automated>cd "/run/media/federicocalo/D/prj/Smart Factory Transformation" && python -m pytest apps/agents/supply -q --co 2>&1 | tail -2; python -c "from pathlib import Path; base=Path('apps/agents/supply'); files=['inventory-manager/tests/test_reorder.py','inventory-manager/tests/test_inventory_hitl.py','energy-optimizer/tests/test_enpi.py','energy-optimizer/tests/test_energy_hitl.py','cost-analyzer/tests/test_oepv.py','cost-analyzer/tests/test_cost_analyzer_agent.py','demand-forecaster/tests/test_holt_winters.py','demand-forecaster/tests/test_mape.py','demand-forecaster/tests/test_demand_hitl.py']; missing=[f for f in files if not (base/f).exists()]; assert not missing, missing; conftests=[f for f in ['inventory-manager','energy-optimizer','cost-analyzer','demand-forecaster'] if not (base/f/'tests'/'conftest.py').exists()]; assert not conftests, conftests; print('all 9 test files + 4 conftests present')"</automated>
  </verify>
  <acceptance_criteria>
    - All 9 named test files plus 4 conftest.py and 4 tests/__init__.py exist.
    - No file uses a module-level pytest.skip; no conftest assigns MagicMock to `interrupt` (WR-01).
    - test_inventory_hitl.py / test_energy_hitl.py / test_demand_hitl.py each name the interrupt-then-audit ordering AND the stable-id-from-thread_id contract (grep finds thread_id).
    - test_cost_analyzer_agent.py names Decision.AUTO and asserts no interrupt is called.
    - `pytest apps/agents/supply --co` collects without import errors in the test files themselves.
  </acceptance_criteria>
  <done>Every Phase 9 supply agent behavior from the RESEARCH Test Map has a corresponding test file with a contract-naming body, encoding the Phase 8 anti-bug guardrails.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test scaffold to agent impl | placeholder contracts gate Wave 2-5 implementation; no runtime trust boundary crossed |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-04 | Tampering | test scaffold completeness | mitigate | Verify step asserts all 9 files present; no module-level skip masks an unimplemented contract |
| T-09-05 | Tampering | HITL replay correctness | mitigate | HITL scaffolds assert stable-id + interrupt-then-audit + single-write (encodes CR-02/CR-04) |
| T-09-SC | Tampering | npm/pip/cargo installs | accept | No package installs in Phase 9 |
</threat_model>

<verification>
- `python -m pytest apps/agents/supply --co` collects without test-file import errors.
- All 9 test files + 4 conftests + 4 tests/__init__.py present.
- HITL scaffolds assert stable-id-from-thread_id and interrupt-then-audit ordering.
</verification>

<success_criteria>
All 9 supply agent test files + conftests scaffolded with contract-naming bodies; downstream waves have a fixed acceptance surface that encodes the Phase 8 critical-bug guardrails.
</success_criteria>

<output>
Create `.planning/phases/09-agents-supply-chain-economics/09-00b-SUMMARY.md` when done.
</output>
