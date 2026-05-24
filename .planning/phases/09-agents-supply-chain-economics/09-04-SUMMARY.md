---
phase: 09-agents-supply-chain-economics
plan: "04"
subsystem: supply-chain-economics
tags: [cost-analyzer, oepv, autonomous, decision-auto, ecm-03, eco-02, eco-05, read-only]
dependency_graph:
  requires: [09-00a, 09-00b, 09-01]
  provides: [scm_cost_analyzer.oepv, scm_cost_analyzer.agent.CostAnalyzer, COST_REPORT-audit]
  affects: [supply-subgraph-fallback, oepv-simulator, roi-dashboard]
tech_stack:
  added: []
  patterns:
    - "parametric-oepv-simulator: math.exp non-linear ribasso curve, all coefficients in OepvConfig"
    - "autonomous-agent: Decision.AUTO, no interrupt(), single COST_REPORT audit row"
    - "read-only-aggregator: HistoricalCostAggregator, ClassVar SQL, asyncpg $N params"
key_files:
  created:
    - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/oepv.py
    - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/models.py
    - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/cost_aggregator.py
    - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/metadata.py
    - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/agent.py
  modified:
    - apps/agents/supply/cost-analyzer/tests/test_oepv.py
    - apps/agents/supply/cost-analyzer/tests/test_cost_analyzer_agent.py
decisions:
  - "CostAnalyzer è pienamente autonomo (Decision.AUTO) — nessun HITL in nessuna condizione"
  - "anomaly_threshold_pct è un WARNING configurabile, non la regola definitiva del Codice Appalti (demandata F12)"
  - "HistoricalCostAggregator usa fetchrow (non fetch) per le 3 query di aggregazione — pattern asyncpg idiomatico"
metrics:
  duration: "25min"
  completed_date: "2026-05-24"
  tasks: 2
  files: 7
---

# Phase 09 Plan 04: CostAnalyzer — OEPV Parametric Simulator + Autonomous Agent Summary

**One-liner:** Simulatore OEPV parametrico (70/30 + curva exponenziale ribasso + sensitivity) con agente autonomo Decision.AUTO che legge audit.actions e scrive un'unica riga COST_REPORT senza mai chiamare interrupt().

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | OEPV simulator + models + cost aggregator (ECO-02/ECO-05) | f82b404 | oepv.py, models.py, cost_aggregator.py, metadata.py, test_oepv.py |
| 2 | CostAnalyzer autonomous agent (Decision.AUTO, no HITL) | 9feed70 | agent.py, test_cost_analyzer_agent.py |

## What Was Built

### Task 1: OEPV Parametric Simulator + Supporting Modules

**`oepv.py`** — simulatore parametrico puro (no LLM, no asyncpg, synchronous):
- `OepvConfig`: tutti i coefficienti configurabili (`base_d_asta_eur=108000`, `weight_technical=0.70`, `weight_economic=0.30`, `pe_max=30`, `lambda_curve=3.0`, `ribasso_ref_pct=20.0`, `anomaly_threshold_pct=20.0`)
- `compute_oepv(ribasso_pct, pt, config)`: formula `total = weight_technical*pt + weight_economic*pe_max*(1-exp(-lambda*Ri/Ri_ref))`; sensitivity dict per ±1/5/10%; ValueError su input out-of-range
- `build_sensitivity_table`: tabella estesa su un range di ribassi
- Docstring esplicita: `anomaly_threshold_pct` è WARNING CONFIGURABILE, non regola F12

**`models.py`** — modelli Pydantic frozen + extra=forbid:
- `CostBreakdown`: aggregato costi (downtime_cost_eur, scrap_cost_eur, energy_cost_eur, total_eur, roi_savings_pct)
- `OepvReport`: wrapper OepvResult + tabella sensitivity; `from_oepv_result()` factory

**`cost_aggregator.py`** — HistoricalCostAggregator (read-only):
- ClassVar SQL constants parametrizzate ($1..$N, no f-string nell'SQL)
- 3 query separate per DOWNTIME_VERDICT / QUALITY_VERDICT / ANOMALY_ALERT da audit.actions
- Costi stimati: duration_min/60 * cost_per_hour; quantity_scrapped_kg * cost_per_kg; anomaly_kwh * cost_per_kwh

**`metadata.py`** — AGENT_ID="cost-analyzer", CLUSTER="supply", HITL_TIER_DEFAULT=None

**Test OEPV:** 14/14 green — formula 70/30, curva non-lineare Pe, monotonia Pe, offer_eur, anomaly warning, sensitivity keys/values, ValueError guards.

### Task 2: CostAnalyzer Autonomous Agent

**`agent.py`** — CostAnalyzer LangGraph node (Decision.AUTO, no HITL):
- `__call__(state)`: legge input con `state.get()` + default sicuri (no KeyError — CR-03)
- Aggrega costi via `HistoricalCostAggregator`; calcola OEPV; scrive audit; ritorna `{cost_breakdown, oepv_report}`
- **ZERO chiamate a `interrupt()`** — autonomo per design (SCM-03)
- `_write_cost_audit()`: AuditRecord passato POSIZIONALMENTE (CR-02), `decision=Decision.AUTO`, `action_type=ActionType.COST_REPORT.value`, `approval_id=None`

**Test Agent:** 6/6 green — no interrupt, Decision.AUTO, COST_REPORT, read-only, AuditRecord posizionale.

## Verification Results

```
pytest apps/agents/supply/cost-analyzer/tests/ -x -q
20 passed in 0.49s
```

- test_oepv.py: 14/14 (formula, curve, sensitivity, ValueError)
- test_cost_analyzer_agent.py: 6/6 (interrupt, decision, action_type, read-only, aggregation, positional)

## Deviations from Plan

**Nessuna** — piano eseguito esattamente come scritto.

La formula OEPV e il pattern autonomo corrispondono verbatim a 09-RESEARCH.md Pattern 8 e al pattern KnowledgeCurator (08-06). Nessun bug auto-fix, nessuna deviazione architetturale.

## Known Stubs

Nessuno. L'aggregatore legge da audit.actions (che può essere vuoto in ambiente di test — restituisce CostBreakdown con tutti zero, comportamento corretto e documentato).

## Threat Flags

Nessuna nuova superficie di sicurezza non prevista dal threat model del piano.

| T-09-15 | Tampering su input OEPV | **Mitigato** — compute_oepv lancia ValueError su ribasso/pt out-of-range |
| T-09-16 | Repudiation audit | **Mitigato** — singola riga deterministica Decision.AUTO, no replay double-write |
| T-09-17 | Misinterpretazione anomaly threshold come regola legale | **Documentato** — warning configurabile, docstring esplicita, non regola F12 |

## Self-Check: PASSED

Tutti i file creati verificati sul filesystem. Tutti i commit verificati nel log git.

| Check | Risultato |
|-------|-----------|
| oepv.py | FOUND |
| models.py | FOUND |
| cost_aggregator.py | FOUND |
| metadata.py | FOUND |
| agent.py | FOUND |
| commit f82b404 (Task 1) | FOUND |
| commit 9feed70 (Task 2) | FOUND |
