# Phase 6: Agents — Operations & Production - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 6-agents-operations-production
**Areas discussed:** AnomalyDetector — consumo & calibrazione, QualityInspector — input QC events, ProductionPlanner — scheduling, OperatorAssistant — ReAct & tool orchestrazione, Test E2E cross-cutting

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| AnomalyDetector — consumo & calibrazione | Real-time NATS vs polling vs on-demand; baseline per-machine YAML/TSDB/hybrid; rate-limit; trigger | ✓ |
| QualityInspector — input QC events | Simulator vs operator API vs entrambi; payload + dye_lot_id; 4-point grading; HITL tier | ✓ |
| ProductionPlanner — scheduling | LLM-only vs OR-tools vs greedy heuristic; input source; output flow; trigger | ✓ |
| OperatorAssistant — ReAct & tool orchestrazione | create_react_agent vs custom; toolset; lingua cross-lingual; citation policy | ✓ |

---

## AnomalyDetector — consumo & calibrazione

### Sub-area 1: pattern di consumo

| Option | Description | Selected |
|--------|-------------|----------|
| Long-running NATS consumer (servizio dedicato) | Container long-running subscribe sensor.events.* | |
| On-demand dal supervisor (pull window TimescaleDB) | Nodo LangGraph invocato, batch-read TSDB via query_timescale | ✓ |
| Hybrid: NATS consumer scoring + LangGraph HITL | Servizio leggero scorer + agent LangGraph per HITL | |

**User's choice:** On-demand dal supervisor (pull window TimescaleDB)
**Notes:** Allineato pattern altri agenti, riusa query_timescale Phase 3, no nuova infra long-running.

### Sub-area 2: baseline per-machine

| Option | Description | Selected |
|--------|-------------|----------|
| Statistical baseline da TimescaleDB historical query | Continuous aggregate, μ/σ rolling 24h, z-score >3 | |
| YAML config statico per-asset + override runtime | failure_modes-like YAML con threshold per asset_family + per-machine override | ✓ |
| Hybrid: YAML banda base + auto-tuning rolling window in-memory | YAML floor + rolling adattivo clampato | |

**User's choice:** YAML config statico per-asset + override runtime
**Notes:** Deterministic, riproducibile in test E2E, no statistical training Phase 6.

### Sub-area 3: rate limit (12 alert/h)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-machine sliding window | Token bucket per machine_id | |
| Per-agent global (12/h totale AnomalyDetector) | Counter globale agente | ✓ |
| Per (machine_id, anomaly_type) sliding window | Chiave composta, granularità fine | |

**User's choice:** Per-agent global (12/h totale AnomalyDetector)
**Notes:** Match success criterion #3 letterale. Granularità raffinata deferred Phase 11.

### Sub-area 4: trigger di invocazione

| Option | Description | Selected |
|--------|-------------|----------|
| Scheduler esterno (cron-like) ogni N minuti | APScheduler container ogni 5 min | ✓ |
| Operator-triggered via UI/API | Solo invocato manualmente | |
| Hybrid: scheduler + on-demand operator | Cron + API operator | |

**User's choice:** Scheduler esterno (cron-like) ogni N minuti
**Notes:** Endpoint API resta disponibile per trigger manuale (incluso in CONTEXT D-AD-04); user ha confermato scheduler primario.

---

## QualityInspector — input QC events

### Sub-area 1: sorgente inspection event

| Option | Description | Selected |
|--------|-------------|----------|
| Estensione sim-textile genera QC events su NATS | Sim-textile pubblica quality.events.* | |
| Operator-entered via API (PoC manuale) | Solo POST /v1/quality/events | |
| Entrambi: sim-textile genera + API operator | Doppia source, stesso schema, field `source` per audit | ✓ |

**User's choice:** Entrambi
**Notes:** Demo realistic + flow operator inspection; QualityInspector handler uniforme.

### Sub-area 2: 4-point grading

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic mapper Python (no LLM) | Funzione pura ASTM tabulare | |
| LLM reasoning con domain prompt + grading rules in context | Qwen2.5 produce score + reasoning | ✓ |
| Hybrid: deterministic score + LLM justification | Score deterministic, rationale LLM | |

**User's choice:** LLM reasoning con domain prompt + grading rules in context
**Notes:** Flessibilità su edge case; trade-off LLM stability mitigato via mock test + HITL gate severity-based.

### Sub-area 3: HITL tier routing

| Option | Description | Selected |
|--------|-------------|----------|
| Per defect severity: minor→auto-log, major→supervisor, critical→manager+safety | Severity-based tiering | ✓ |
| Sempre supervisor HITL (uniform) | No tiering | |
| Per 4-point score threshold | Score-based | |

**User's choice:** Per defect severity
**Notes:** Scala HITL al rischio reale; failure_modes.yaml esteso con hitl_tier (estensione Phase 5).

### Sub-area 4: dye_lot_id tracking

| Option | Description | Selected |
|--------|-------------|----------|
| Sim-textile gestisce stato dye_lot per asset (model state) | ProductionState model in simulator | ✓ |
| Tabella PG `quality.dye_lots` come source of truth | Migration 007 + FK | |
| Pydantic-only synthetic id da operator + simulator (no DB persistence) | Solo payload validation | |

**User's choice:** Sim-textile gestisce stato dye_lot per asset
**Notes:** KISS senza migration; operator API richiede dye_lot esplicito validato.

---

## ProductionPlanner — scheduling

### Sub-area 1: algoritmo

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid: OR-tools CP-SAT solver + LLM rationale | Constraint solver + LLM explanation | |
| LLM-only con vincoli in prompt + JSON-mode output | Qwen2.5 produce schedule JSON | |
| Deterministic greedy heuristic + LLM rationale (no OR-tools) | SPT/EDD heuristic + LLM rationale | ✓ |

**User's choice:** Deterministic greedy heuristic + LLM rationale
**Notes:** Scope appropriato PoC; ortools deferred Phase 9 quando InventoryManager emerge.

### Sub-area 2: input data

| Option | Description | Selected |
|--------|-------------|----------|
| YAML seed file in repo (orders + asset capacity sintetici) | orders.yaml + asset_capacity.yaml | ✓ |
| PG tabella production.orders + production.capacity | Migration dedicata | |
| Hybrid: orders.yaml seed + PG production.schedule_history per output | Input YAML, output PG | |

**User's choice:** YAML seed file in repo
**Notes:** Riproducibile, demo-ready; schedule history coperto da audit.actions Phase 4.

### Sub-area 3: output & HITL flow

| Option | Description | Selected |
|--------|-------------|----------|
| Schedule draft JSON → supervisor HITL approve → audit log only | Draft Pydantic + HITL + audit | ✓ |
| Schedule draft + auto-publish a NATS subject production.schedule.approved | Cross-cluster publish | |
| Schedule draft con OperatorAssistant per Q&A pre-approval | Cross-agent Q&A | |

**User's choice:** Schedule draft JSON → supervisor HITL approve → audit log only
**Notes:** Match preciso success criterion #4; NATS cross-cluster publish deferred Phase 9.

### Sub-area 4: trigger

| Option | Description | Selected |
|--------|-------------|----------|
| On-demand operator/supervisor via API/UI | POST /v1/agents/production-planner/plan | ✓ |
| Scheduler giornaliero (cron) + on-demand | Cron daily 06:00 | |
| Triggered by event (nuovo ordine inserito) | Hot-reload YAML watcher | |

**User's choice:** On-demand operator/supervisor via API/UI
**Notes:** Allineato flow PoC user-driven; cron/event-driven deferred.

---

## OperatorAssistant — ReAct & tool orchestrazione

### Sub-area 1: pattern orchestrazione

| Option | Description | Selected |
|--------|-------------|----------|
| LangGraph prebuilt create_react_agent (ReAct loop standard) | Best practice 2025 | ✓ |
| Nodo custom con planning step esplicito (plan-then-execute) | Audit granular | |
| Custom ReAct con state machine in supervisor (full control) | Massimo control | |

**User's choice:** LangGraph prebuilt create_react_agent
**Notes:** Audit nativo, code minimo, max_iterations=5 via safe_invoke Phase 4.

### Sub-area 2: tool set + max iter

| Option | Description | Selected |
|--------|-------------|----------|
| rag_search + traverse_graph + query_timescale (max 5 iter) | 3 tool knowledge+sensor | |
| Solo rag_search + traverse_graph (knowledge-first, max 4 iter) | Knowledge-only | |
| Full toolbelt: + escalate_to_supervisor + log_event | 5 tool incl. action-bearing | ✓ |

**User's choice:** Full toolbelt
**Notes:** Primo punto di contatto operatore; escalate_to_supervisor + log_event sono nuovi Phase 6.

### Sub-area 3: lingua di risposta

| Option | Description | Selected |
|--------|-------------|----------|
| Risponde nella lingua della query, retrieval cross-lingual default | langdetect + LLM lang coherence | ✓ |
| Sempre IT default (PoC Italian-first), retrieval cross-lingual | IT default | |
| Parametro esplicito output_lang nell'API + auto-detect fallback | API param | |

**User's choice:** Risponde nella lingua della query, retrieval cross-lingual default
**Notes:** Match success criterion #1; cross-lingual sfrutta Phase 5 D-64.

### Sub-area 4: HITL gating & citation policy

| Option | Description | Selected |
|--------|-------------|----------|
| escalate=auto-trigger HITL; citations sempre inline + structured | Auto HITL + validator post-LLM | ✓ |
| escalate=manual approval supervisor, citations inline only | Manual approval | |
| escalate=auto-trigger HITL; citations soft (best-effort, no validator) | Soft citation | |

**User's choice:** escalate=auto-trigger HITL; citations sempre inline + structured
**Notes:** Validator post-LLM con max 1 retry; flag citations_missing in audit se ancora missing.

---

## Cross-cutting: Test E2E

| Option | Description | Selected |
|--------|-------------|----------|
| Mock LLM (record/replay JSON) + scenario YAML deterministici | LLM_BACKEND=mock + fixtures | ✓ |
| Real Qwen2.5-7B via Ollama in CI services + scenari YAML | Ollama in GitHub Actions services | |
| Hybrid: mock per unit + real LLM per N scenari critici (smoke) | Mock + golden real-llm | |

**User's choice:** Mock LLM (record/replay JSON) + scenario YAML deterministici
**Notes:** CI veloce e deterministic; real LLM opt-in via @pytest.mark.real-llm; hybrid golden-path deferred Phase 11.

---

## Claude's Discretion

Aree dove Claude decide allineandosi a convenzioni esistenti (no input user specifico richiesto):

- Naming convention agent slug (kebab-dir + snake_case Python package) → segue Phase 1-5
- Pydantic model file organization per cross-agent types in `packages/sft-domain/src/sft_domain/ops/`
- structlog field naming convention
- Test file naming pattern
- OPS cluster subgraph routing logic (chi viene invocato dentro `clusters/ops` quando supervisor entra nel cluster): implementato via `target_agent` field nello state subgraph, popolato dal supervisor HybridRouter Phase 4, fallback `operator-assistant`.

## Deferred Ideas

Vedi sezione `<deferred>` di CONTEXT.md per la lista completa. Highlights:
- AnomalyDetector auto-tuning baseline → Phase 11
- ProductionPlanner OR-tools CP-SAT → Phase 9
- ProductionPlanner NATS cross-cluster publish → Phase 9
- QualityInspector hybrid grading → Phase 11
- QualityInspector PG dye_lots schema → Phase 9
- OperatorAssistant output_lang parameter API → Phase 10
- Real-LLM golden path E2E per agente → Phase 11
- Long-running NATS consumer AnomalyDetector → Phase 11
- OperatorAssistant proactive engagement → Phase 10
