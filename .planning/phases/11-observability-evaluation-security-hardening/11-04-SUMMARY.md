---
phase: 11-observability-evaluation-security-hardening
plan: "04"
subsystem: grafana-dashboards-lgtm-doc
tags:
  - grafana
  - provisioning
  - dashboards
  - prometheus
  - lgtm
  - kpi
  - cost
  - observability
dependency_graph:
  requires:
    - "11-00: infra/grafana/provisioning (dashboards.yaml + datasources.yaml)"
    - "11-01: sft_agents.otel (OT Bridge metrics already in metrics.py)"
  provides:
    - infra/grafana/dashboards/agent-kpis.json (OBS-04/07 agent latency + token proxy)
    - infra/grafana/dashboards/factory-kpis.json (OBS-04 OEE/MTTR/MTBF/scrap)
    - infra/grafana/dashboards/cost-dashboard.json (OBS-07 cost + token + latency)
    - docs/observability/lgtm-stack.md (OBS-03 documentation)
    - infra/grafana/tests/test_dashboards_valid.py (T-11-04-02 schema drift mitigation)
  affects:
    - "11-05: .env.example (Pushgateway vars for BudgetSnapshot metrics)"
tech_stack:
  added: []
  patterns:
    - "Grafana dashboard JSON schemaVersion 39 (Grafana v11.x compatible)"
    - "PromQL histogram_quantile(0.50|0.95|0.99) on ingest_latency_seconds_bucket"
    - "events_published_total counter as token consumption proxy (Pushgateway wiring deferred)"
    - "pytest parametrized fixture over glob('*.json') for schema validation"
key_files:
  created:
    - infra/grafana/dashboards/agent-kpis.json
    - infra/grafana/dashboards/factory-kpis.json
    - infra/grafana/dashboards/cost-dashboard.json
    - docs/observability/lgtm-stack.md
    - infra/grafana/tests/test_dashboards_valid.py
  modified: []
decisions:
  - "OT Bridge ingest_latency_seconds_bucket used for p50/p95/p99 — the only histogram metric available in the dev stack; agent-level histograms require Pushgateway wiring (deferred to 11-05)"
  - "BudgetSnapshot metrics (tokens_input/output, cost_usd_simulated) are not yet pushed to Prometheus — dashboards use sft_agent_* metric names as forward declarations with events_published_total fallback proxy"
  - "factory-kpis OEE/MTTR/MTBF/scrap are TimescaleDB-derived (svc_api_gateway/kpi/queries.py) — noted in dashboard descriptions as requiring Pushgateway or HTTP datasource wiring; PromQL panels show OT-bridge event-rate proxy"
  - "schemaVersion 39 chosen (Grafana v11.3.1 native format, confirmed in RESEARCH)"
  - "19 pytest tests cover all three dashboards: JSON validity, title/panels/schemaVersion presence, datasource UID containment (prometheus/tempo), content assertions (p95, OEE, MTTR, MTBF, scrap, cost, tokens)"
  - "obs.yml docker compose config exit 0 — stack config still valid after plan (no obs.yml modifications needed)"
metrics:
  duration: "7 minuti"
  completed_date: "2026-05-25"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
---

# Phase 11 Plan 04: Grafana Provisioning Dashboards + LGTM Doc Summary

**One-liner:** Three Grafana v11 provisioned dashboard JSON (agent KPIs with p50/p95/p99 latency + token proxy, factory KPIs with OEE/MTTR/MTBF/scrap, cost dashboard with simulated cost + token + latency) auto-loaded from `infra/grafana/dashboards/` via dashboards.yaml provider; LGTM stack documented as optional (OBS-03); 19 validation tests green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | agent-kpis.json + factory-kpis.json (OBS-04) | 1a27f46 | infra/grafana/dashboards/agent-kpis.json, infra/grafana/dashboards/factory-kpis.json |
| 2 | cost-dashboard.json + LGTM doc + validation tests (OBS-03/07) | 9a7d6b4 | infra/grafana/dashboards/cost-dashboard.json, docs/observability/lgtm-stack.md, infra/grafana/tests/test_dashboards_valid.py |

## Verification Results

### Automated verification (plan spec)

```
python3 -c "import json; [json.load(open(f)) for f in ['infra/grafana/dashboards/agent-kpis.json','infra/grafana/dashboards/factory-kpis.json']]; ..."
→ dash-agent-factory-ok
  agent-kpis: 11 panels, schemaVersion=39
  factory-kpis: 10 panels, schemaVersion=39

python3 -c "... assert 'cost' in json.dumps(c).lower(); assert os.path.getsize('docs/observability/lgtm-stack.md') > 400 ..."
→ cost-lgtm-ok
  cost-dashboard: 12 panels, size=15195 bytes
  lgtm-stack.md: 6852 bytes

pytest infra/grafana/tests/test_dashboards_valid.py -x -q
→ 19 passed in 0.03s

docker compose -f infra/compose/obs.yml config --quiet
→ Exit code: 0 (obs.yml still valid)
```

### Dashboard content assertions

| Dashboard | Requirement | Present |
|-----------|-------------|---------|
| agent-kpis.json | p50 latency (histogram_quantile 0.50) | Yes |
| agent-kpis.json | p95 latency (histogram_quantile 0.95) | Yes |
| agent-kpis.json | p99 latency (histogram_quantile 0.99) | Yes |
| agent-kpis.json | token count proxy (events_published_total) | Yes |
| factory-kpis.json | OEE gauge + trend | Yes |
| factory-kpis.json | MTTR stat panel | Yes |
| factory-kpis.json | MTBF stat panel | Yes |
| factory-kpis.json | Scrap rate gauge | Yes |
| cost-dashboard.json | Simulated cost (sft_agent_cost_usd_simulated_total) | Yes |
| cost-dashboard.json | Token input/output panels | Yes |
| cost-dashboard.json | Latency p50/p95/p99 | Yes |
| cost-dashboard.json | Budget limit utilization gauge | Yes |

### Datasource references

All three dashboards reference only provisioned datasource UIDs:
- `prometheus` (uid: `prometheus`) — default datasource, Prometheus at http://prometheus:9090
- Row panels and annotation panels use Grafana built-in UIDs (`-- Grafana --`) — allowed

## Deviations from Plan

### Known Stubs / Forward Declarations

**1. BudgetSnapshot Prometheus metrics not yet Pushgateway-wired**

The cost dashboard and agent-kpis token panels reference metric names (`sft_agent_cost_usd_simulated_total`, `sft_agent_tokens_input_total`, `sft_agent_tokens_output_total`, `sft_agent_tokens_total`, `sft_agent_cost_usd_limit`, `sft_agent_tokens_limit`) that do not yet exist in Prometheus.

- **Reason:** BudgetSnapshot (sft_agents/models/budget.py D-60) captures cost_usd_simulated and tokens_* fields but does not push them to Prometheus yet. A Pushgateway wiring step is needed.
- **Fallback:** Dashboards include fallback PromQL using `events_published_total` as a proxy (event rate × constant coefficients) — visible data at dev time without Pushgateway.
- **Resolution:** Deferred to plan 11-05 (.env.example + Phase 11 env vars) or a dedicated Pushgateway wiring plan.
- **Impact:** Agent-level token and cost panels show proxy data or zero until wired. Latency panels (using `ingest_latency_seconds_bucket`) work immediately.

**2. Factory KPIs OEE/MTTR/MTBF require TimescaleDB HTTP wiring**

The factory-kpis dashboard panels for OEE, MTTR, MTBF, and scrap rate require TimescaleDB queries (svc_api_gateway/kpi/queries.py). These are not natively queryable via PromQL without a Pushgateway or Grafana HTTP datasource connector.

- **Reason:** KPI values are computed in FastAPI using asyncpg (Plan 10-02). Prometheus does not scrape TimescaleDB directly.
- **Fallback:** OT Bridge event rate used as OEE/throughput proxy; MTTR/MTBF panels show 0 placeholder with notes.
- **Resolution:** Expose KPIs via Pushgateway from the /v1/kpi endpoint, or add a Grafana HTTP datasource pointing to the API Gateway. Deferred.
- **Impact:** Factory KPI gauges show 0 or proxy values at dev time; the panel titles and descriptions clearly document the wiring requirement.

### Auto-fixed Issues

None — plan executed without Rule 1/2/3 triggers.

## Known Stubs

| Stub | File | Line/Panel | Reason |
|------|------|-----------|--------|
| `sft_agent_cost_usd_simulated_total` (metric absent) | cost-dashboard.json | panels 1, 2 | BudgetSnapshot not yet Pushgateway-wired |
| `sft_agent_tokens_input_total` (metric absent) | cost-dashboard.json | panel 3 | BudgetSnapshot not yet Pushgateway-wired |
| `sft_agent_tokens_output_total` (metric absent) | cost-dashboard.json | panel 4 | BudgetSnapshot not yet Pushgateway-wired |
| `sft_agent_tokens_total` (metric absent) | cost-dashboard.json, agent-kpis.json | panels 5, 7 | BudgetSnapshot not yet Pushgateway-wired |
| OEE gauge: `vector(0)` placeholder | factory-kpis.json | panel 1 | TimescaleDB KPI not in Prometheus |
| MTTR stat: `0` placeholder | factory-kpis.json | panel 4 | TimescaleDB KPI not in Prometheus |
| MTBF stat: `0` placeholder | factory-kpis.json | panel 5 | TimescaleDB KPI not in Prometheus |

These stubs do not prevent the plan's primary goal (provisioned dashboard JSON loaded by Grafana). They are intentional forward declarations for Pushgateway wiring deferred to 11-05.

## Threat Flags

None — no new network endpoints or trust boundaries introduced. All files are static JSON/Markdown. The dashboard validation test mitigates T-11-04-02 (schema drift).

## Self-Check

```
FOUND: infra/grafana/dashboards/agent-kpis.json
FOUND: infra/grafana/dashboards/factory-kpis.json
FOUND: infra/grafana/dashboards/cost-dashboard.json
FOUND: docs/observability/lgtm-stack.md
FOUND: infra/grafana/tests/test_dashboards_valid.py

Task 1 commit: 1a27f46 (FOUND in git log)
Task 2 commit: 9a7d6b4 (FOUND in git log)

package.json UNCHANGED: not touched
.claude/ not staged: verified
obs.yml UNCHANGED: not modified (docker compose config exit 0)
```

## Self-Check: PASSED
