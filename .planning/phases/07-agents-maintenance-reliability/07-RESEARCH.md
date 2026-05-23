---
phase: 7
phase_name: Agents — Maintenance & Reliability
phase_slug: agents-maintenance-reliability
researched_at: "2026-05-23"
research_language: it
domain: "predictive maintenance + RCA + procedural coaching + OEE analytics (textile)"
confidence: HIGH (stack + patterns), MEDIUM (cross-domain C-MAPSS→tessile transfer), HIGH (TimescaleDB + LangGraph), MEDIUM (RCA citation enforcement at scale)
requirements: [MNT-01, MNT-02, MNT-03, MNT-04, MNT-05, MNT-06]
depends_on_phases: [3, 4, 5, 6]
---

# Phase 7 — Research: Maintenance & Reliability Cluster

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (verbatim — il planner DEVE rispettarle, no alternatives)

**PredictiveMaintenance**
- **D-PM-01** — Lightweight ML scikit-learn (Ridge / RandomForest, ~5–10 MB) addestrato offline su subset NASA C-MAPSS, inference deterministic con `random_state` fissato. Output `RULEstimate` Pydantic. NIENTE torch/PyTorch in Phase 7.
- **D-PM-02** — Dataset C-MAPSS **FD001 + FD003** committato in repo (`packages/sft-ml/data/c-mapss-fd001/`, `c-mapss-fd003/`, ~10 MB CSV/Parquet train+test). FD001 = single fault mode / single op condition; FD003 = HPC + Fan degradation → mapping textile a 2 fault families (mechanical wear / dye chamber contamination). Citazione PHM 2008 NASA Prognostics CoE nel model card. No download runtime in CI.
- **D-PM-03** — Train su C-MAPSS pure (21 sensors + 3 op_settings), infer su textile sensor proxies via mapping table (`packages/sft-ml/src/sft_ml/cmapss/feature_map.py`). Ambient T/H = `op_setting_2`, `op_setting_3`. Es. spindle_vibration → s9 (fan vibration); loom_temperature → s8 (LPT outlet temperature).
- **D-PM-04** — Trigger event-driven da AnomalyDetector Phase 6 via NATS subject `maintenance.predict.<asset_id>`. Output Pydantic `RULEstimate` con `rul_cycles, confidence_band_lower/upper, health_index∈[0,1], recommended_action, triggered_by_action_id, model_version, created_at`. HITL supervisor su `health_index < 0.3`. Audit `Decision.AUTO + ActionType.RUL_ESTIMATE`. NIENTE cron periodico (event-driven preferred).

**RCASpecialist**
- **D-RCA-01** — Form-based 5-Why fixed schema con `WhyStep{question, answer, citations: list[RagCitation] min_length=1, confidence}` e `RCAChain{problem_statement, why_1..why_5, root_cause, corrective_action_recommendation, downtime_event_id?}`. Validator post-LLM enforce 5 step esatti + ≥1 citation per step + `source_uri` non-null. Re-prompt fino a 2 retry su schema fail (mirror Phase 6 D-QI-02).
- **D-RCA-02** — **Always supervisor HITL** su ogni `corrective_action_recommendation` (literal success criterion #2, no severity branching). Audit `Decision.HITL_SUPERVISOR + ActionType.RCA_CHAIN`.

**MaintenanceCoach**
- **D-MC-01** — Async LangGraph thread con state persistito in PG via `langgraph_checkpoints` (riuso migration 005 Phase 4). Thread state: `{intervention_id, asset_id, sop_id, technician_id, current_step, completed_steps: list[StepReport], messages, mttr_start, mttr_end?}`. MTTR = `thread.mttr_end - thread.mttr_start` (effettivo elapsed time incluso pause). Active work time tracciato in `completed_steps[*].duration_minutes`.
- **D-MC-02** — Nuovo tool `request_help(reason, context)` in `packages/sft-agents/src/sft_agents/tools/hitl.py` (wrappa `escalate_to_supervisor`). Keyword detection in system prompt bilingue IT+EN ("aiuto","non ci riesco","help","stuck","blocked"). Audit `Decision.HITL_SUPERVISOR + ActionType.COACH_STEP` con marker `escalation_trigger: 'technician_request'`.

**DowntimeAnalyzer**
- **D-DA-01** — sim-textile nuovo modulo `downtime_event_generator.py` mirror di `quality_event_generator.py` (06-09). NATS subject `maintenance.downtime.<asset_id>` payload `{event_id, asset_id, reason_code, duration_min, severity, work_order_id?, dye_lot_id?, source:'simulator', timestamp}`. DowntimeAnalyzer consumer JetStream durable `da-consumer` persiste su nuova tabella PG `maintenance.downtime_events` (migration 008, TimescaleDB hypertable su `timestamp`).
- **D-DA-02** — OEE.Quality cross-cluster: query `audit.actions WHERE action_type='QUALITY_VERDICT'` Phase 6, estrae `good_parts/total_parts` da `evidence_panel` payload. Fallback automatico a sim-textile `production_state.py` metrics se gap finestra (ops cluster offline).
- **D-DA-03** — TimescaleDB **continuous aggregate** `maintenance.oee_hourly` (window 1h, refresh policy 5min). Migration 008 include `CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)`. Endpoint `POST /v1/agents/downtime-analyzer/report` body `{window_start, window_end, by_asset?, top_n_pareto?}` → `OEEReport{availability, performance, quality, oee, by_asset?, pareto: list[ParetoEntry], report_id, generated_at}`. Audit `Decision.AUTO + ActionType.OEE_REPORT`.

**Taxonomy & Audit**
- **D-MNT-TAX** — Estendere `failure_modes.yaml` con campi maintenance-specific (additive, no breaking): `reason_code` (taxonomy MNT-05 stable code), `mttr_target_minutes` (SLO), `intervention_steps_sop_id` (link Phase 5 corpus), `preventive_check_interval_hours`. Loader Pydantic esteso in `packages/sft-domain/src/sft_domain/failure_modes/models.py`. CI validator: `reason_code` unicità + `intervention_steps_sop_id` esiste in corpus.
- **D-AE-MNT** — Migration `009_extend_audit_mnt.sql` DROP+ADD CHECK constraints pattern (mirror Phase 6 migration 007). Nuovi `ActionType`: `RUL_ESTIMATE`, `RCA_CHAIN`, `COACH_STEP`, `DOWNTIME_VERDICT`, `OEE_REPORT`. Decision values esistenti sufficienti — nessun nuovo Decision needed. Python enum `ActionType` esteso in lockstep in `packages/sft-agents/src/sft_agents/models/enums.py`.

### Claude's Discretion (research e raccomanda)
1. **Wiring AD→PM**: NATS pub/sub loose coupling (preferito in CONTEXT) vs supervisor subgraph routing. Decisione finale al planner dopo lettura 04-CONTEXT D-53 hierarchical supervisor.
2. **Citation validator `source_uri`**: full PG lookup (decisione tentativa: full lookup, audit-friendly) vs shape-only validation. Trade-off latency vs robustezza.
3. **Scikit-learn / joblib pin**: esatta versione minimum vs caret range; necessità di pin Python minor.
4. **Continuous aggregate refresh interval**: 5min default vs valutazione ad-hoc su 30 asset × 5 sensor 1Hz.
5. **NATS consumer ack policy**: explicit ack vs all-ack per `da-consumer` e `pm-consumer`.
6. **Naming convention coach thread_id**: `coach-<intervention_id>` (kebab + UUID4) suggested; planner conferma.

### Deferred Ideas (OUT OF SCOPE — il planner NON deve includere)
- Auto-tuning RUL baseline rolling-window → Phase 11 (drift osservato in produzione simulata).
- PreventiveMaintenanceScheduler agent → Phase 9 (Supply Chain, coordina con InventoryManager).
- WorkOrderManager integration (CMMS SAP PM/Maximo) → post-competition.
- MaintenanceCoach auto-trigger su step timeout → Phase 11.
- Cross-cluster orchestrator AD→PM→Coach autochain → Phase 9 (cross-cluster orchestration).
- RUL output in giorni reali (`rul_cycles → rul_days`) → Phase 10 (UI-side conversion).
- LSTM PyTorch port → post-competition.
- OEE drill-down per shift / per operator → Phase 10/11.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MNT-01 | `PredictiveMaintenance` — stima RUL su asset (modello adattato da C-MAPSS a tessile) | §Standard Stack (scikit-learn 1.7.2 stable / Ridge + RandomForest), §C-MAPSS Dataset Schema, §Cross-Domain Mapping, §Pitfall 1 (joblib version pinning), §Pitfall 2 (RUL piecewise linear target) |
| MNT-02 | `RCASpecialist` — RCA su downtime con 5-Whys assistito e citazioni dal knowledge base | §RCA Structured Prompting Pattern, §Citation Validator Pattern, §Pitfall 5 (LLM citation hallucination), §Pitfall 6 (retry loop budget) |
| MNT-03 | `MaintenanceCoach` — guida procedurale step-by-step con checkpoint HITL | §LangGraph Async Thread Pattern, §Checkpoint Serialization Size, §Pitfall 7 (state bloat), §Pitfall 8 (re-execution dual-write) |
| MNT-04 | `DowntimeAnalyzer` — categorizza fermi, calcola OEE/MTTR/MTBF, Pareto recurring | §OEE Decomposition Pattern, §TimescaleDB Continuous Aggregate, §NATS JetStream Durable Consumer, §Pitfall 9 (OEE.Quality cross-cluster gap), §Pitfall 10 (CAGG retention vs raw retention) |
| MNT-05 | Tassonomia eventi manutenzione documentata e usata coerentemente cross-agent | §failure_modes.yaml extension, §Bilingue documentation pattern (mirror 06-14), §ISO 14224 reason_code convention |
| MNT-06 | Integrazione con asset registry (PG) e storico interventi (event store) | §`packages/sft-assets` registry reuse, §migration 008 `maintenance.downtime_events` hypertable, §audit chain via `triggered_by_action_id` |
</phase_requirements>

## Summary

Phase 7 implementa il cluster `maintenance` (4 agenti: PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer) sopra runtime Phase 4 + knowledge layer Phase 5 + simulator Phase 3 + artefatti Phase 6. Le 4 dimensioni tecniche principali sono:

1. **ML lightweight per RUL** — scikit-learn (Ridge / RandomForest) addestrato offline su NASA C-MAPSS FD001+FD003, inferenza deterministica con cross-domain mapping textile via feature proxy. Niente PyTorch. Trade-off accuratezza vs riproducibilità chiaramente accettato (PoC competition demo).
2. **LangGraph async thread cross-shift** — MaintenanceCoach come `langgraph_checkpoints` PG-backed thread riavviabile dopo pause/restart, mirror del pattern HITL Phase 4 con thread_id come "puntatore persistente".
3. **TimescaleDB continuous aggregate** — OEE materializzato live (window 1h, refresh 5min) su nuova migration 008, query API on-demand restituisce Pareto + breakdown per asset.
4. **NATS JetStream durable consumer** — DowntimeAnalyzer (`da-consumer`) e PredictiveMaintenance (`pm-consumer`) ascoltano subject `maintenance.downtime.<asset_id>` e `maintenance.predict.<asset_id>` rispettivamente, con explicit ack per resilience cross-restart.

**Primary recommendation:** Mirror il più possibile i pattern Phase 6 (agent skeleton `apps/agents/{cluster}/<slug>/`, build_*_subgraph router, E2E mock LLM scenario YAML, audit enum extension migration DROP+ADD CHECK), introducendo solo gli artefatti veramente nuovi: `packages/sft-ml/` per il modello ML pre-trained, migration 008 (downtime_events + CAGG) e 009 (audit ActionType ext), nuovo `request_help` tool, `build_maintenance_subgraph` router. **NIENTE nuove dipendenze infrastrutturali** oltre scikit-learn/joblib già in transitive deps Phase 1-5.

## Architectural Responsibility Map

Le 4 capability del cluster mappate al tier architetturale primario. Riferimento: Phase 4 D-53 hierarchical supervisor + cluster subgraphs.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| RUL estimation (PredictiveMaintenance) | API / Backend (LangGraph node) | Database / Storage (PG `audit.actions`) | Inferenza scikit-learn lightweight in-process come nodo del subgraph; il modello joblib è committato nel package, no servizio ML separato. |
| 5-Why RCA chain (RCASpecialist) | API / Backend (ReAct loop su LangGraph) | Knowledge layer (Phase 5 `rag_search` + `traverse_graph`) | Logica ReAct LangGraph; citation grounding via tool calls al knowledge layer (Phase 5 ownership). |
| Procedural coaching (MaintenanceCoach) | API / Backend (LangGraph async thread) | Database / Storage (`langgraph_checkpoints` PG) | State PG-persisted = SSOT; checkpoint riavviabile cross-shift. |
| OEE + Pareto analytics (DowntimeAnalyzer) | Database / Storage (TimescaleDB CAGG) | API / Backend (FastAPI endpoint `POST /v1/agents/downtime-analyzer/report`) | OEE.A e OEE.P materializzati lato DB (CAGG), agent compone solo Quality cross-cluster + Pareto query SQL. |
| Downtime event ingestion | API / Backend (NATS consumer in agent process) | Database / Storage (PG `maintenance.downtime_events` hypertable) | NATS durable consumer durante agent process lifetime; persistenza in TimescaleDB hypertable. |
| Asset registry integration (MNT-06) | Library (`packages/sft-assets` Phase 3) | API / Backend (agent imports) | Pure Pydantic loader; no separato microservizio. |
| Failure mode taxonomy (MNT-05) | Library (`packages/sft-domain` failure_modes) | Documentation (`docs/agents/maintenance/event-taxonomy.{it,en}.md`) | Single source of truth in YAML + Pydantic loader; doc bilingue per audience. |

**Cross-tier sanity check:** Nessuna logica scivola sul browser tier (no Phase 10 UI in scope). Nessuna logica nel CDN/static tier. La separazione "agente in-process scikit-learn" vs "ML service dedicato" è esplicitamente locked (D-PM-01 — niente torch, niente service separato).

## Standard Stack

### Core Maintenance Stack (nuovi vs Phase 7)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scikit-learn` | `^1.7.0` (latest stable 1.7.2; 1.8.0 just released) | Ridge + RandomForestRegressor per RUL | Standard de facto Python ML lightweight, MIT, joblib serializable, deterministic con `random_state`. [VERIFIED: pip index versions scikit-learn → 1.8.0 latest, 1.7.2 stable from prev minor] |
| `joblib` | `^1.5.0` (latest 1.5.3) | Model serialization | Built-in scikit-learn save/load idiomatico; supporta compression. [VERIFIED: pip index versions joblib → 1.5.3] |
| `pandas` | `^2.3.0` (latest 2.3.3; 3.0.x out) | C-MAPSS dataset loading + feature engineering | Standard per CSV/Parquet ingest; già transitive dep di scikit-learn. [VERIFIED: pip index versions pandas → 3.0.3 latest, 2.3.3 prev major] |
| `numpy` | `^1.26.0` o `^2.0` (compat scikit-learn) | Array math | Transitive dep. [ASSUMED — non re-verificato runtime, già locked Phase 3] |

### Riusati da Phase precedenti (NO new install)

| Library | Da | Per | Riferimento |
|---------|------|-----|----|
| `langgraph` 0.4+ | Phase 4 | ReAct loop (RCASpecialist), async thread (MaintenanceCoach), subgraph router | research/STACK.md |
| `langgraph-checkpoint-postgres` 3.1.0 | Phase 4 | MaintenanceCoach thread persistence | [VERIFIED: pip index versions → 3.1.0 latest] |
| `langchain-core` 0.3+ | Phase 4/5 | BaseTool per `request_help`, ReAct tools | research/STACK.md |
| `nats-py` 2.10+ (latest 2.14.0) | Phase 3/4 | DowntimeAnalyzer + PredictiveMaintenance JetStream durable consumer | [VERIFIED: pip index versions nats-py → 2.14.0] |
| `asyncpg` | Phase 3/4 | Migration 008/009 + query OEE CAGG + downtime_events insert | research/STACK.md |
| `pydantic` v2 | Phase 1+ | Tutti i modelli (`RULEstimate`, `RCAChain`, `WhyStep`, `OEEReport`, `ParetoEntry`, `StepReport`, `DowntimeEvent`) | Standard cross-phase |
| `structlog` | Phase 1+ | JSON logging | Standard cross-phase |
| `langfuse` | Phase 4 | LLM span tracing | Standard cross-phase |
| `APScheduler` | Phase 6 (services/agents-scheduler) | NON RIUSATO Phase 7 — D-PM-04 event-driven preferred | Constraint locked |
| TimescaleDB PG extension | Phase 3 | Hypertable + continuous aggregate per OEE | research/STACK.md |

### Reused Knowledge Layer Tools (Phase 5)

| Tool | Package | Usato da | Riferimento |
|------|---------|---|----|
| `RagSearchTool` | `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` | RCASpecialist (citation per ogni WhyStep), MaintenanceCoach (SOP step retrieval) | Phase 5 D-66 |
| `TraverseGraphTool` | `packages/sft-knowledge/src/sft_knowledge/tools/graph.py` | RCASpecialist (Machine→Part→FailureMode→SOP) | Phase 5 D-66/D-65 |
| `QueryTimescaleTool` | `packages/sft-tools/src/sft_tools/timescale/query.py` | PredictiveMaintenance (sensor history feature retrieval) | Phase 3 D-46/D-47 |

### Reused Phase 6 Tools

| Tool | Package | Usato da |
|------|---------|---|
| `EscalateToSupervisorTool` | `packages/sft-agents/src/sft_agents/tools/hitl.py` | RCASpecialist (corrective_action HITL), MaintenanceCoach (via `request_help` wrapper) |
| `LogEventTool` | `packages/sft-agents/src/sft_agents/tools/audit.py` | Tutti gli agenti per audit row writing |
| `MockReplayChatModel` (06-03) | `packages/sft-agents/src/sft_agents/llm/mock.py` | E2E test deterministic (DIRECT REUSE) |
| `build_ops_subgraph` pattern | `packages/sft-agents/src/sft_agents/runtime/clusters.py` | MODEL per nuovo `build_maintenance_subgraph` con stessa signature |
| `production_state.py` pattern | `simulators/sim-textile/src/sim_textile/production_state.py` | MODEL per estensione downtime_event_generator |
| `quality_event_generator.py` pattern | `simulators/sim-textile/src/sim_textile/quality_event_generator.py` | MIRROR DIRETTO per `downtime_event_generator.py` |

### Alternatives Considered (e RIGETTATE)

| Instead of | Could Use | Tradeoff | Verdetto |
|------------|-----------|----------|---------|
| scikit-learn Ridge/RF | PyTorch LSTM (literature standard C-MAPSS) | +20-30% accuracy ma ~700MB deps + non-deterministic training senza CUDA seed control | RIGETTATO da D-PM-01 (PoC scope) |
| Joblib | ONNX export | Cross-framework portability ma serve `skl2onnx` + ONNX runtime in inference | Non necessario per single-language stack |
| TimescaleDB continuous aggregate | Materialized view PG nativa + cron refresh | View nativa non incrementale; richiede full recompute ogni 5min su 30 asset × 5 sensor 1Hz | CAGG vince per scalabilità |
| NATS durable pull consumer | NATS push subscribe | Push più semplice ma menos controllabile su backpressure | Pull preferred per ack explicit + retry control |
| Hand-rolled state machine MaintenanceCoach | LangGraph thread + checkpoint | LangGraph già investito Phase 4, integrazione nativa con HITL `interrupt()` | LangGraph wins |

**Installation (esempio pyproject.toml del nuovo `packages/sft-ml/`):**
```toml
[project]
dependencies = [
  "scikit-learn>=1.7.0,<1.9.0",
  "joblib>=1.5.0,<2.0.0",
  "pandas>=2.3.0,<3.0.0",
  "numpy>=1.26.0,<3.0.0",
  "pydantic>=2.7.0,<3.0.0",
]
```

**Pin rationale:**
- `scikit-learn>=1.7.0,<1.9.0`: 1.7.x stable + tolleranza 1.8.x (rilasciata ma ancora minor); 1.9.x bump implica re-train + re-validation joblib cross-version.
- `joblib`: locked al minor — joblib è il serializer del modello, version drift può rendere `joblib.load()` non backward-compatible (vedi Pitfall 1).
- `numpy<3.0`: tipica conservazione finché scikit-learn dichiara compat.

## Package Legitimacy Audit

Run del Package Legitimacy Gate eseguito 2026-05-23. slopcheck installato globalmente (`/home/federicocalo/.local/bin/slopcheck`) ma chiamato senza `--json` ha invocato modalità npm install (errata per ecosystem Python). Risultato: **slopcheck non disponibile in modalità query Python per questo run**. Tutti i pacchetti tagged `[ASSUMED]` benché verificati via `pip index versions` su PyPI ufficiale (esistenza confermata + versioni recenti). Il planner deve inserire `checkpoint:human-verify` prima di ogni install (best-effort fallback per package legitimacy protocol).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `scikit-learn` | PyPI | ~17 yrs (2008+) | ~80M/week | github.com/scikit-learn/scikit-learn | n/a | Approved [ASSUMED — verified via `pip index versions` + project well-known] |
| `joblib` | PyPI | ~16 yrs | ~150M/week | github.com/joblib/joblib | n/a | Approved [ASSUMED — `pip index versions` confirms 1.5.3 latest; scikit-learn transitive dep] |
| `pandas` | PyPI | ~16 yrs | ~250M/week | github.com/pandas-dev/pandas | n/a | Approved [ASSUMED — pip verified] |
| `nats-py` | PyPI | ~6 yrs | ~5M/month | github.com/nats-io/nats.py | n/a | Approved [ASSUMED — already locked Phase 3] |
| `langgraph-checkpoint-postgres` | PyPI | <2 yrs | growing | github.com/langchain-ai/langgraph | n/a | Approved [ASSUMED — already locked Phase 4] |

**Packages removed due to slopcheck [SLOP] verdict:** none (verdict unavailable).
**Packages flagged as suspicious [SUS]:** none verified.

⚠️ **PLANNER ACTION:** Insert `checkpoint:human-verify` task before each new install (cf. D-PM-01 install di scikit-learn/joblib). The audit above is best-effort; user confirmation closes the loop.

## Architecture Patterns

### System Architecture Diagram

```
        ┌──────────────────────────────────────────────────────────────────────┐
        │  Phase 4 LangGraph Supervisor + HybridRouter (esistente, no modify)  │
        └────────────────┬───────────────────────────────┬─────────────────────┘
                         │ routing.yaml keyword:        │
                         │ manutenzione/riparazione/    │  (Phase 6 ops ratio
                         │ guasto/broken/downtime/RCA   │   identico)
                         │                              │
                         ▼                              ▼
        ┌────────────────────────────────┐    ┌──────────────────────────┐
        │  build_maintenance_subgraph()  │    │ build_ops_subgraph()     │
        │  router su state[target_agent] │    │ (Phase 6 esistente)      │
        │  fallback: maintenance-coach   │    └──────────────────────────┘
        └──┬──────┬───────────┬──────┬───┘
           │      │           │      │
           ▼      ▼           ▼      ▼
        ┌────┐ ┌────┐    ┌─────┐ ┌────────────────┐
        │ PM │ │RCA │    │Coach│ │ DowntimeAnalzr │
        └─┬──┘ └─┬──┘    └──┬──┘ └────┬───────────┘
          │      │          │         │
          │      │          │         ▼
          │      │          │     ┌────────────────────────────────────┐
          │      │          │     │ NATS JetStream durable consumer    │
          │      │          │     │ subject: maintenance.downtime.>    │
          │      │          │     │ consumer name: da-consumer         │
          │      │          │     │ (long-running task in agent proc)  │
          │      │          │     └────────┬───────────────────────────┘
          │      │          │              ▼
          │      │          │     ┌────────────────────────────────────┐
          │      │          │     │ INSERT INTO maintenance.downtime_events │
          │      │          │     │ (TimescaleDB hypertable, migr 008) │
          │      │          │     └────────┬───────────────────────────┘
          │      │          │              │
          │      │          │              ▼
          │      │          │     ┌─────────────────────────────────────┐
          │      │          │     │  CAGG maintenance.oee_hourly        │
          │      │          │     │  (window 1h, refresh policy 5min)   │
          │      │          │     │  + audit.actions WHERE QUALITY_VERDICT│
          │      │          │     │     (cross-cluster read, fallback   │
          │      │          │     │      sim-textile metrics)           │
          │      │          │     └────────┬────────────────────────────┘
          │      │          │              │
          │      │          │              ▼  on-demand POST /report
          │      │          │     ┌─────────────────────────────────────┐
          │      │          │     │ OEEReport + Pareto JSON Pydantic    │
          │      │          │     └─────────────────────────────────────┘
          │      │          │
          │      │          ▼
          │      │     ┌──────────────────────────────────────────────────┐
          │      │     │ langgraph_checkpoints (PG, migration 005 Phase 4)│
          │      │     │ thread_id = coach-<intervention_id>              │
          │      │     │ state {intervention_id, asset_id, sop_id,        │
          │      │     │        current_step, completed_steps, mttr_*}    │
          │      │     │ riavviabile cross-shift                          │
          │      │     └──────────────┬───────────────────────────────────┘
          │      │                    │
          │      │                    │ tool calls
          │      │                    ▼
          │      │     ┌──────────────────────────────────────────────────┐
          │      │     │ Phase 5: rag_search (SOP step retrieval)         │
          │      │     │ Phase 6: escalate_to_supervisor (via request_help│
          │      │     │           tool wrapper, D-MC-02)                 │
          │      │     └──────────────────────────────────────────────────┘
          │      │
          │      ▼
          │  ┌──────────────────────────────────────────────────────────────┐
          │  │ ReAct LangGraph + 2 tools: rag_search + traverse_graph       │
          │  │ Output: RCAChain Pydantic (5 WhyStep + each ≥1 citation)     │
          │  │ Validator post-LLM: 5 step + citation shape + source_uri lookup│
          │  │ Re-prompt fino 2 retry → ALWAYS escalate_to_supervisor       │
          │  └──────────────────────────────────────────────────────────────┘
          │
          ▼
       ┌─────────────────────────────────────────────────────────────────────┐
       │ NATS JetStream durable consumer pm-consumer                         │
       │ subject: maintenance.predict.<asset_id>                             │
       │ trigger: AnomalyDetector Phase 6 alert severity major+              │
       │ (publish-subscribe loose coupling — no Phase 6 code change)         │
       └─────────────────────────┬───────────────────────────────────────────┘
                                 ▼
       ┌─────────────────────────────────────────────────────────────────────┐
       │ scikit-learn pipeline (Ridge or RF Regressor)                       │
       │ joblib.load(packages/sft-ml/models/ridge-fd001-fd003-v1.0.joblib)   │
       │ feature mapping: textile sensor → C-MAPSS s1..s21 proxy             │
       │ ambient T/H → op_setting_2/3                                        │
       │ Output: RULEstimate Pydantic                                        │
       │ HITL supervisor if health_index < 0.3                               │
       │ Audit: Decision.AUTO + ActionType.RUL_ESTIMATE                      │
       │        triggered_by_action_id = AD alert audit row                  │
       └─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (additions only — existing Phase 1-6 unchanged)

```
apps/agents/maintenance/
├── predictive-maintenance/
│   ├── pyproject.toml         # deps: sft-agents, sft-ml, sft-tools, nats-py
│   ├── src/mnt_predictive_maintenance/
│   │   ├── __init__.py
│   │   ├── agent.py           # __call__(state) → state delta
│   │   ├── consumer.py        # NATS JetStream durable pm-consumer
│   │   ├── models.py          # RULEstimate Pydantic
│   │   └── inference.py       # joblib.load + feature mapping
│   └── tests/
├── rca-specialist/
│   ├── src/mnt_rca_specialist/
│   │   ├── agent.py           # ReAct LangGraph + rag_search + traverse_graph
│   │   ├── models.py          # WhyStep, RCAChain Pydantic
│   │   ├── validators.py      # 5-step + citation enforce + retry
│   │   └── prompts.py         # 5-Why system prompt bilingue
│   └── tests/
├── maintenance-coach/
│   ├── src/mnt_maintenance_coach/
│   │   ├── agent.py           # async LangGraph thread builder
│   │   ├── models.py          # StepReport, CoachState
│   │   ├── prompts.py         # bilingue step-by-step + escalation kw
│   │   └── mttr.py            # MTTR computation helper
│   └── tests/
└── downtime-analyzer/
    ├── src/mnt_downtime_analyzer/
    │   ├── agent.py           # endpoint handler /report
    │   ├── consumer.py        # NATS JetStream durable da-consumer
    │   ├── models.py          # OEEReport, ParetoEntry, DowntimeEvent
    │   ├── oee.py             # OEE.A/P/Q calculation + Pareto SQL
    │   └── repository.py      # asyncpg queries to maintenance.* + audit.actions
    └── tests/

packages/sft-ml/                          # NEW package
├── pyproject.toml
├── project.json                          # Nx project
├── src/sft_ml/
│   ├── __init__.py
│   ├── cmapss/
│   │   ├── __init__.py
│   │   ├── feature_map.py                # C-MAPSS sensor → textile proxy
│   │   ├── training.py                   # offline training pipeline (CLI)
│   │   ├── inference.py                  # deterministic predict helper
│   │   └── schema.py                     # CMAPSSRecord Pydantic
│   └── data/                             # COMMITTATO (~10MB)
│       ├── c-mapss-fd001/
│       │   ├── train_FD001.txt           # NASA original schema
│       │   ├── test_FD001.txt
│       │   └── RUL_FD001.txt
│       └── c-mapss-fd003/
│           ├── train_FD003.txt
│           ├── test_FD003.txt
│           └── RUL_FD003.txt
└── models/                                # COMMITTATO
    └── ridge-fd001-fd003-v1.0.joblib     # ~5MB pre-trained
                                           # (RandomForest variant opzionale)

packages/sft-agents/src/sft_agents/
├── tools/hitl.py                          # EXTEND: add RequestHelpTool
├── models/enums.py                        # EXTEND: ActionType.RUL_ESTIMATE etc.
└── runtime/clusters.py                    # EXTEND: build_maintenance_subgraph

packages/sft-domain/src/sft_domain/
├── failure_modes.yaml                     # EXTEND: maintenance: {reason_code,
│                                          # mttr_target_minutes, intervention_steps_sop_id,
│                                          # preventive_check_interval_hours}
└── failure_modes/models.py                # EXTEND: MaintenanceMeta Pydantic

simulators/sim-textile/src/sim_textile/
├── downtime_event_generator.py            # NEW (mirror quality_event_generator.py)
└── (production_state.py — already exists, reuse)

infra/migrations/timescale/
├── 008_create_downtime_events.sql         # NEW: hypertable + CAGG
└── 009_extend_audit_mnt.sql               # NEW: ActionType ext (mirror 007)

apps/api-gateway/src/svc_api_gateway/
└── routers/maintenance_agents.py          # NEW (mirror routers/ops_agents.py 06-12)

docs/docs/agents/maintenance/              # NEW bilingue (mirror 06-14)
├── predictive-maintenance.it.md / .en.md
├── rca-specialist.it.md / .en.md
├── maintenance-coach.it.md / .en.md
├── downtime-analyzer.it.md / .en.md
└── event-taxonomy.it.md / .en.md

tests/e2e/maintenance/                     # NEW (mirror tests/e2e/ops/)
├── test_predictive_maintenance_scenarios.py
├── test_rca_specialist_scenarios.py
├── test_maintenance_coach_scenarios.py
└── test_downtime_analyzer_scenarios.py

tests/fixtures/mnt_scenarios/              # NEW (mirror ops_scenarios/)
├── predictive-maintenance/{happy,degraded,failure}.yaml
├── rca-specialist/...
├── maintenance-coach/...
└── downtime-analyzer/...

tests/fixtures/llm_responses/              # NEW maintenance entries
├── rca-specialist/{happy,degraded,failure}.jsonl
├── maintenance-coach/...
└── (predictive-maintenance and downtime-analyzer don't need LLM mock —
   PM is deterministic ML, DA is deterministic SQL aggregation)
```

### Pattern 1: NASA C-MAPSS Data Loading & Schema

**What:** C-MAPSS dataset ha schema fissato — 26 colonne (`unit_number, time_cycles, op_setting_1, op_setting_2, op_setting_3, s1..s21`) in spazio-separato. RUL ground truth derivata da `max(time_cycles per unit) - current_cycle` (training set); per test set, ultima riga per unit + valore in `RUL_FDxxx.txt`.

**When to use:** Pipeline `training.py` di `packages/sft-ml/` (offline, riproducibile in CI smoke).

**Example:**
```python
# Source: NASA Prognostics CoE C-MAPSS PHM 2008 schema + verified via
# https://github.com/makinarocks/awesome-industrial-machine-datasets/blob/master/data-explanation/C-MAPSS/README.md
import pandas as pd
import numpy as np
from pathlib import Path

CMAPSS_COLUMNS = (
    ["unit_number", "time_cycles", "op_setting_1", "op_setting_2", "op_setting_3"]
    + [f"s{i}" for i in range(1, 22)]
)

def load_fd_subset(data_dir: Path, subset: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Load FD001 or FD003 train/test/RUL ground truth."""
    train = pd.read_csv(
        data_dir / f"train_{subset}.txt",
        sep=r"\s+",
        header=None,
        names=CMAPSS_COLUMNS,
    )
    test = pd.read_csv(
        data_dir / f"test_{subset}.txt",
        sep=r"\s+",
        header=None,
        names=CMAPSS_COLUMNS,
    )
    rul_truth = pd.read_csv(
        data_dir / f"RUL_{subset}.txt", sep=r"\s+", header=None, names=["rul"]
    )["rul"]
    return train, test, rul_truth

def compute_train_rul(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'rul' column: max_cycle_per_unit - current_cycle (piecewise-linear truncated)."""
    max_per_unit = df.groupby("unit_number")["time_cycles"].transform("max")
    df = df.copy()
    df["rul"] = max_per_unit - df["time_cycles"]
    # Piecewise-linear: cap at 125 (standard C-MAPSS literature convention)
    df["rul"] = np.minimum(df["rul"], 125)
    return df
```

[CITED: github.com/makinarocks/awesome-industrial-machine-datasets/blob/master/data-explanation/C-MAPSS/README.md — column schema canonical]
[CITED: data.nasa.gov/dataset/cmapss-jet-engine-simulated-data — dataset metadata + 4 sub-datasets descrizione]

### Pattern 2: Cross-Domain Feature Mapping (Textile → C-MAPSS)

**What:** Inference su sensori textile facendo "proxy mapping" verso schema C-MAPSS 21 sensor + 3 op_setting. Bridge tra Phase 3 sim-textile sensori e modello pre-trained.

**When to use:** `packages/sft-ml/src/sft_ml/cmapss/feature_map.py` — invocato in inference path di PredictiveMaintenance.

**Example (mapping table proposta — il planner valida con sft-assets registry):**
```python
# Source: D-PM-03 + cross-reference C-MAPSS sensor descriptions
# (https://github.com/makinarocks/awesome-industrial-machine-datasets/.../C-MAPSS/README.md)
TEXTILE_TO_CMAPSS_FEATURE_MAP: dict[str, dict[str, str]] = {
    "loom": {
        "loom_temperature": "s8",       # LPT outlet temperature analog
        "warp_tension": "s11",          # Static pressure HPC outlet analog
        "creel_speed": "s9",            # Physical fan speed analog
        "broken_pick_count": "s14",     # Demanded core speed (proxy event rate)
        # Phase 3 ambient (env_temp, env_humidity) → op_setting_2/3
    },
    "spinning": {
        "spindle_vibration": "s9",      # Fan vibration analog
        "spindle_temperature": "s8",
        "ring_position": "s11",
    },
    # ...
}

OP_SETTING_MAP = {
    "ambient_temperature": "op_setting_2",
    "ambient_humidity": "op_setting_3",
    # op_setting_1 = "altitude" in C-MAPSS — set to constant 0 for textile
    # (single operating condition, equivalent to FD001 sea-level baseline)
}

def map_textile_window_to_cmapss(window_df: pd.DataFrame, asset_family: str) -> pd.DataFrame:
    """Aggregate last-window textile sensors into a single C-MAPSS row."""
    feature_map = TEXTILE_TO_CMAPSS_FEATURE_MAP[asset_family]
    out = pd.Series(0.0, index=CMAPSS_COLUMNS[2:])  # skip unit_number, time_cycles
    out["op_setting_1"] = 0.0
    for textile_tag, cmapss_col in feature_map.items():
        if textile_tag in window_df.columns:
            out[cmapss_col] = window_df[textile_tag].mean()
    for ambient_tag, op_col in OP_SETTING_MAP.items():
        if ambient_tag in window_df.columns:
            out[op_col] = window_df[ambient_tag].mean()
    return out.to_frame().T
```

**Caveat HONEST:** Il mapping è "best guess" basato su similarità semantica (temperature → temperature, vibration → vibration). La letteratura su domain adaptation NASA→manufacturing dimostra che il transfer **funziona qualitativamente** ma soffre `domain shift` significativo (LAMA-Net e Bi-Discrepancy Network sono proprio dedicati a mitigare questo). Per il PoC, è accettabile come baseline; performance reale richiederebbe domain adaptation tecniche (deferred). Documentare esplicitamente nel model card.

[CITED: arxiv.org/pdf/2208.08388 — LAMA-Net domain adaptation per RUL]
[CITED: arxiv.org/html/2510.03604 — Deep Domain Adaptation for Turbofan RUL survey 2025]

### Pattern 3: scikit-learn RUL Training Pipeline (Deterministic)

**What:** Training offline riproducibile in CI, output `ridge-fd001-fd003-v1.0.joblib` committato al repo.

**When to use:** `packages/sft-ml/src/sft_ml/cmapss/training.py` — invocato da CLI `python -m sft_ml.cmapss.training` (one-shot offline), output binary committed.

**Example:**
```python
# Source: scikit-learn docs https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html
#         + standard C-MAPSS preprocessing (piecewise-linear RUL cap 125)
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import root_mean_squared_error

RANDOM_STATE = 42

def train_ridge(train_df: pd.DataFrame) -> Pipeline:
    """Train deterministic Ridge regressor on engineered features."""
    features = [c for c in train_df.columns if c.startswith(("op_setting_", "s"))]
    X, y = train_df[features], train_df["rul"]
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=1.0, random_state=RANDOM_STATE)),
    ])
    pipeline.fit(X, y)
    return pipeline

def train_random_forest(train_df: pd.DataFrame) -> Pipeline:
    features = [c for c in train_df.columns if c.startswith(("op_setting_", "s"))]
    X, y = train_df[features], train_df["rul"]
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=RANDOM_STATE, n_jobs=1
        )),
    ])
    pipeline.fit(X, y)
    return pipeline

def save_model(pipeline: Pipeline, out_path: Path, version: str = "v1.0") -> None:
    """joblib serialize with explicit compression (size budget ~5MB)."""
    joblib.dump(pipeline, out_path, compress=("gzip", 3))
    # Companion JSON metadata for inspection without unpickling.
    out_path.with_suffix(".json").write_text(
        '{"version": "' + version + '", "sklearn_min": "1.7.0", "python_min": "3.12"}'
    )
```

**CI smoke test (deterministic):** Train su FD001, assert RMSE ≤ baseline threshold (es. 35 cycles) — fixed seed guarantees byte-equal model across runs.

[CITED: scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html]
[CITED: scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html]

### Pattern 4: NATS JetStream Durable Pull Consumer (DowntimeAnalyzer + PredictiveMaintenance)

**What:** Long-running async task in agent process che fa pull consumer durable con explicit ack — sopravvive restart container e load-balancia se replicato.

**When to use:** `apps/agents/maintenance/downtime-analyzer/src/.../consumer.py` (subject `maintenance.downtime.>`), `apps/agents/maintenance/predictive-maintenance/src/.../consumer.py` (subject `maintenance.predict.*`).

**Example:**
```python
# Source: docs.nats.io/using-nats/developer/develop_jetstream/consumers + nats-py official examples
import asyncio
import json
import structlog
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy, AckPolicy, RetentionPolicy

_log = structlog.get_logger("mnt.downtime-analyzer.consumer")

async def run_da_consumer(servers: list[str], stream: str = "MAINTENANCE_STREAM") -> None:
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()

    # Bootstrap stream (idempotent — mirror Phase 3 scripts/nats-bootstrap-streams.py)
    await js.add_stream(
        name=stream,
        subjects=["maintenance.downtime.>", "maintenance.predict.*"],
        retention=RetentionPolicy.LIMITS,
        max_age=30 * 24 * 60 * 60,  # 30 days
    )

    # Durable pull consumer — survives restart, supports load-balanced scale-out.
    psub = await js.pull_subscribe(
        subject="maintenance.downtime.>",
        durable="da-consumer",
        config=ConsumerConfig(
            deliver_policy=DeliverPolicy.ALL,
            ack_policy=AckPolicy.EXPLICIT,    # explicit ack only after PG insert success
            max_deliver=5,                    # 5 redeliveries on nak before DLQ
            ack_wait=30,                      # 30s per message
        ),
    )

    while True:
        try:
            msgs = await psub.fetch(batch=10, timeout=2.0)
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            _log.exception("fetch_error", error=str(e))
            await asyncio.sleep(1.0)
            continue

        for m in msgs:
            try:
                payload = json.loads(m.data)
                await _persist_downtime_event(payload)   # asyncpg INSERT
                await m.ack()
            except Exception as e:
                _log.exception("process_error", subject=m.subject, error=str(e))
                await m.nak(delay=5)                     # negative ack + retry in 5s
```

[CITED: docs.nats.io/using-nats/developer/develop_jetstream/consumers — durable consumer concepts]
[CITED: nats-io.github.io/nats.py/modules.html — pull_subscribe API]

### Pattern 5: LangGraph Async Thread + Checkpoint Cross-Shift (MaintenanceCoach)

**What:** Ogni intervention è 1 thread LangGraph identificato da `thread_id = "coach-<intervention_id>"`. State persistito in `langgraph_checkpoints` PG. Technician pausa → restart → resume con `Command(resume=...)` o ri-invocazione con stesso thread_id legge dal checkpoint.

**When to use:** `apps/agents/maintenance/maintenance-coach/src/.../agent.py` — entry point esposto da `routers/maintenance_agents.py` come `POST /v1/agents/maintenance-coach/step` con body `{intervention_id, technician_input}`.

**Example skeleton:**
```python
# Source: docs.langchain.com/oss/python/langgraph/interrupts +
#         langgraph-checkpoint-postgres pypi.org/project/langgraph-checkpoint-postgres/
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import interrupt, Command
from typing import TypedDict, NotRequired
from datetime import datetime
from sft_agents.models.enums import ActionType, Decision

class CoachState(TypedDict):
    intervention_id: str
    asset_id: str
    sop_id: str
    technician_id: str
    current_step: int
    completed_steps: list[dict]   # list[StepReport.model_dump()]
    messages: list[dict]
    mttr_start: str               # ISO timestamp
    mttr_end: NotRequired[str]

async def step_node(state: CoachState) -> dict:
    # 1. retrieve current SOP step via rag_search Tool
    # 2. ask LLM to format guidance bilingue
    # 3. interrupt() to wait technician confirmation
    technician_response = interrupt({
        "type": "coach_step",
        "step_no": state["current_step"],
        "guidance": "...",
    })
    return {
        "completed_steps": state["completed_steps"] + [{
            "step_no": state["current_step"],
            "duration_minutes": ...,
            "technician_input": technician_response,
        }],
        "current_step": state["current_step"] + 1,
    }

async def build_coach_graph():
    g: StateGraph = StateGraph(CoachState)
    g.add_node("step", step_node)
    g.add_edge(START, "step")
    g.add_edge("step", END)   # planner can wire conditional loop until last_step
    return g

async def invoke_coach(intervention_id: str, **kwargs):
    async with AsyncPostgresSaver.from_conn_string(PG_DSN) as saver:
        graph = (await build_coach_graph()).compile(checkpointer=saver)
        config = {"configurable": {"thread_id": f"coach-{intervention_id}"}}
        return await graph.ainvoke(kwargs, config=config)
```

**Critical pattern: MTTR computation.**
- `mttr_start` set in state on first invocation (intervention start).
- `mttr_end` set when last step completes (graph reaches END normally).
- `mttr_total = mttr_end - mttr_start` includes all pauses (effective elapsed time per definition MTTR).
- Active work time = `sum(StepReport.duration_minutes for step in completed_steps)` — questo è il secondo metric, complementare a MTTR.

[CITED: docs.langchain.com/oss/python/langgraph/interrupts — interrupt + Command pattern]
[CITED: pypi.org/project/langgraph-checkpoint-postgres/ — AsyncPostgresSaver API]

### Pattern 6: 5-Why RCA Structured Prompting (RCASpecialist)

**What:** LLM produce JSON strutturato che matcha `RCAChain` Pydantic schema; validator post-LLM enforce 5 step + citation. Retry budget 2.

**When to use:** `apps/agents/maintenance/rca-specialist/src/.../agent.py` — ReAct loop invoca tool, validator chiude il loop.

**Example prompt skeleton (bilingue, system + user template):**
```python
# Source: prompt engineering literature for structured CoT RCA
# (mljar.com/ai-prompts/.../prompt-root-cause-cot/, arxiv.org/pdf/2305.15778)
SYSTEM_PROMPT_IT = """Sei RCASpecialist, un agente di root cause analysis per impianti tessili.

Ogni risposta DEVE essere un JSON valido che matchi questo schema esatto:
{
  "problem_statement": "<descrizione del downtime in 1 frase>",
  "why_1": {"question": "Perché ...?", "answer": "...", "citations": [{"source_uri": "...", "snippet": "..."}], "confidence": 0.0-1.0},
  "why_2": {...},
  "why_3": {...},
  "why_4": {...},
  "why_5": {...},
  "root_cause": "<sintesi root cause>",
  "corrective_action_recommendation": "<azione correttiva proposta>"
}

REGOLE STRINGENTI:
- ESATTAMENTE 5 step why_1..why_5 (no di più, no di meno).
- OGNI step DEVE avere ALMENO 1 citation con source_uri non vuoto.
- USA i tool rag_search e traverse_graph per recuperare citazioni dal knowledge base.
- Se non hai citation per uno step, NON inventare: chiama prima il tool, poi rispondi.
- corrective_action_recommendation è SEMPRE inoltrata a supervisor HITL (no auto-execute).
"""
```

**Validator post-LLM (parsing + enforcement):**
```python
# Source: D-RCA-01 + Phase 6 D-QI-02 retry pattern (validators.py)
from pydantic import ValidationError

class RCAValidationError(Exception): ...

async def validate_rca_chain_with_retry(
    llm_response: str,
    *,
    rag_lookup: Callable,
    max_retries: int = 2,
) -> RCAChain:
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            chain = RCAChain.model_validate_json(llm_response)
            # Beyond shape: verify each citation source_uri exists in knowledge base
            for step_name in ("why_1","why_2","why_3","why_4","why_5"):
                step = getattr(chain, step_name)
                for cit in step.citations:
                    if not await rag_lookup(cit.source_uri):
                        raise RCAValidationError(
                            f"{step_name} citation source_uri not found: {cit.source_uri}"
                        )
            return chain
        except (ValidationError, RCAValidationError) as e:
            last_err = e
            if attempt < max_retries:
                # Re-prompt with augmentation (Phase 6 D-QI-02 pattern)
                llm_response = await reprompt_with_correction(llm_response, e)
            else:
                raise
```

**Citation source_uri lookup — recommended (Claude's Discretion #2):** full PG lookup vs shape-only. Recommendation: **full PG lookup against `ingest.documents` table (Phase 5) + Qdrant payload `source_uri` field**. Trade-off: +~50ms per citation × 5 step = +250ms latency per RCA chain. Acceptable vs alternative (shape-only) che lascia LLM libero di hallucinare URI plausibili (T-V6-llm-hallucination Phase 6 esiste già come threat; questa è la mitigation per RCA).

[CITED: arxiv.org/pdf/2305.15778 — "Automatic Root Cause Analysis via LLMs for Cloud Incidents"]
[CITED: mljar.com/ai-prompts/prompts-engineer/chain-of-thought-for-analysis/prompt-root-cause-cot/ — structured CoT RCA prompt template]

### Pattern 7: TimescaleDB Continuous Aggregate for OEE Hourly

**What:** Materialized view auto-refreshed che pre-aggrega downtime + production metrics in finestre 1h per asset.

**When to use:** Migration `008_create_downtime_events.sql` definisce schema + CAGG.

**Example:**
```sql
-- Source: docs.tigerdata.com/docs/use-timescale/latest/continuous-aggregates/refresh-policies
--         + Phase 3 hypertable pattern (infra/migrations/timescale/001_create_sensor_events.sql)

-- 1. Schema + table (idempotent DO blocks pattern Phase 3)
CREATE SCHEMA IF NOT EXISTS maintenance;

CREATE TABLE IF NOT EXISTS maintenance.downtime_events (
    event_id        UUID NOT NULL,
    asset_id        TEXT NOT NULL,
    reason_code     TEXT NOT NULL,
    duration_min    INTEGER NOT NULL CHECK (duration_min >= 0),
    severity        TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
    work_order_id   TEXT,
    dye_lot_id      TEXT,
    source          TEXT NOT NULL CHECK (source IN ('simulator','operator','api')),
    timestamp       TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (event_id, timestamp)
);

SELECT create_hypertable(
    'maintenance.downtime_events',
    'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_downtime_asset_time
    ON maintenance.downtime_events (asset_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_downtime_reason_time
    ON maintenance.downtime_events (reason_code, timestamp DESC);

-- 2. Continuous aggregate maintenance.oee_hourly
-- Computes Availability + Performance per asset per hour.
-- OEE.Quality cross-cluster is computed at query time from audit.actions (D-DA-02).
CREATE MATERIALIZED VIEW IF NOT EXISTS maintenance.oee_hourly
WITH (timescaledb.continuous) AS
SELECT
    asset_id,
    time_bucket('1 hour', timestamp) AS bucket,
    COALESCE(SUM(duration_min), 0) AS total_downtime_min,
    COUNT(*) AS downtime_event_count
FROM maintenance.downtime_events
GROUP BY asset_id, bucket
WITH NO DATA;

-- 3. Refresh policy: every 5 min, look back 3h, end 1h ago
-- (best practice: end_offset ≥ chunk boundary tolerance, start_offset > data retention)
SELECT add_continuous_aggregate_policy(
    'maintenance.oee_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);
```

**Query pattern (DowntimeAnalyzer `/report`):**
```python
# Availability per asset per window from CAGG
SELECT
  asset_id,
  SUM(total_downtime_min) AS down_min,
  -- planned_minutes per window from asset_capacity.yaml (Phase 6 D-PP-02 loader)
  60.0 * <hours_in_window> AS planned_min,
  1.0 - (SUM(total_downtime_min) / (60.0 * <hours_in_window>)) AS availability
FROM maintenance.oee_hourly
WHERE bucket BETWEEN $1 AND $2
GROUP BY asset_id

-- Quality cross-cluster from audit.actions (D-DA-02)
SELECT
  evidence_panel->'verdict'->>'asset_id' AS asset_id,
  SUM((evidence_panel->'verdict'->>'good_parts')::int) AS good,
  SUM((evidence_panel->'verdict'->>'total_parts')::int) AS total
FROM audit.actions
WHERE action_type = 'QUALITY_VERDICT'
  AND ts BETWEEN $1 AND $2
GROUP BY 1

-- Pareto top-N
SELECT reason_code,
       SUM(duration_min) AS total_downtime_min,
       COUNT(*) AS occurrence_count
FROM maintenance.downtime_events
WHERE timestamp BETWEEN $1 AND $2
GROUP BY reason_code
ORDER BY total_downtime_min DESC
LIMIT $3
```

[CITED: tigerdata.com/blog/real-time-analytics-for-time-series-continuous-aggregates — CAGG concept]
[CITED: tigerdata.com/docs/use-timescale/latest/continuous-aggregates/refresh-policies — refresh policy best practice]
[CITED: leanproduction.com/oee/ — OEE = Availability × Performance × Quality formula]

### Pattern 8: Audit Enum Extension Migration (mirror 007)

**What:** Migration `009_extend_audit_mnt.sql` segue identico pattern DROP+ADD CHECK constraint di 007, aggiungendo nuovi ActionType.

**When to use:** Plan task per migration 009, in lockstep con extension `packages/sft-agents/src/sft_agents/models/enums.py`.

**Example (skeleton DROP+ADD):**
```sql
-- Source: infra/migrations/timescale/007_extend_audit_decisions.sql (Phase 6 D-AE-01)
-- Idempotent: safe to re-run.

ALTER TABLE audit.actions
  DROP CONSTRAINT IF EXISTS audit_actions_action_type_chk;

ALTER TABLE audit.actions
  ADD CONSTRAINT audit_actions_action_type_chk CHECK (
    action_type IN (
      -- Phases 1-5:
      'WRITE_PLC_SETPOINT','ACTUATOR_COMMAND','FIRMWARE_DEPLOY',
      'NETWORK_ACL_CHANGE','GRAPH_RECURSION_REVIEW','GOVERNOR_ALERT',
      -- Phase 6:
      'ESCALATION_REQUEST','QUALITY_VERDICT','SCHEDULE_DRAFT','ANOMALY_ALERT',
      -- Phase 7 extensions:
      'RUL_ESTIMATE',       -- D-PM-04: PredictiveMaintenance RUL output audit
      'RCA_CHAIN',          -- D-RCA-02: RCASpecialist 5-Why chain output
      'COACH_STEP',         -- D-MC-01: MaintenanceCoach single step audit
      'DOWNTIME_VERDICT',   -- D-DA-01: DowntimeAnalyzer event ingestion + categorization
      'OEE_REPORT'          -- D-DA-03: DowntimeAnalyzer OEE report generation
    )
  );
```

**Companion Python enum extension (lockstep):**
```python
# packages/sft-agents/src/sft_agents/models/enums.py — EXTEND
class ActionType(str, Enum):
    # ... existing Phase 1-6 ...
    # Phase 7 additions — keep in lockstep with migration 009.
    RUL_ESTIMATE = "RUL_ESTIMATE"
    RCA_CHAIN = "RCA_CHAIN"
    COACH_STEP = "COACH_STEP"
    DOWNTIME_VERDICT = "DOWNTIME_VERDICT"
    OEE_REPORT = "OEE_REPORT"
```

**Test pattern (mirror Phase 6 `test_migration_007.py` 18-test set):** testcontainers PG + apply 003 + 007 + 009 in sequence + INSERT row per ogni nuovo ActionType + INSERT row with invalid type → CHECK violation.

[CITED: infra/migrations/timescale/007_extend_audit_decisions.sql — local model]

### Pattern 9: build_maintenance_subgraph Router (mirror build_ops_subgraph)

**What:** Cluster subgraph che branchia da START a child agent in base a `state["target_agent"]`, fallback a `maintenance-coach` (most ambiguous-friendly default — coach può sempre escalare).

**Example (mirror clusters.py:90 build_ops_subgraph):**
```python
# Source: packages/sft-agents/src/sft_agents/runtime/clusters.py (D-X OPS routing)
_MAINTENANCE_DEFAULT_AGENT: str = "maintenance-coach"

def build_maintenance_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    if not child_callables:
        raise ValueError("child_callables must be non-empty for the maintenance subgraph")
    if _MAINTENANCE_DEFAULT_AGENT not in child_callables:
        raise ValueError(
            f"child_callables must include {_MAINTENANCE_DEFAULT_AGENT!r} "
            f"(the fallback target for the MAINTENANCE router); got slugs {sorted(child_callables)}"
        )
    children = dict(child_callables)
    g: StateGraph = StateGraph(AgentState)
    for slug, fn in children.items():
        g.add_node(slug, fn)
    def _route(state: AgentState) -> str:
        target = state.get("target_agent") if isinstance(state, dict) else None
        if not target or target not in children:
            _log.warning("maintenance_route_unknown_target", target=target,
                         fallback=_MAINTENANCE_DEFAULT_AGENT)
            return _MAINTENANCE_DEFAULT_AGENT
        return str(target)
    g.add_conditional_edges(START, _route, {slug: slug for slug in children})
    for slug in children:
        g.add_edge(slug, END)
    return g
```

### Anti-Patterns to Avoid

- **Sync ReAct single-shot per MaintenanceCoach:** session timeout fa perdere MTTR su intervention multi-ora. Sempre async LangGraph thread.
- **Storing C-MAPSS raw dataframes nel checkpoint state:** sforerebbe il limite serialization. Solo `RULEstimate` finale nello state; raw data live in PG/joblib model.
- **Free-form RCA chain LLM output:** non auditable. Sempre fixed Pydantic schema (D-RCA-01).
- **Polling `audit.actions` per Quality senza index:** lentezza. Riusare indice esistente `(action_type, created_at)` (verifica Phase 6 migration 003 + 007).
- **Re-emit downtime events su rebuild:** idempotency. `event_id` come UUID generato lato sim-textile + ON CONFLICT DO NOTHING su INSERT.
- **Auto-publish RUL su NATS cross-cluster:** scope Phase 9. Phase 7 audit only.
- **Trigger PredictiveMaintenance via cron:** locked D-PM-04 (event-driven only).
- **Bypassare `escalate_to_supervisor` per `request_help`:** il nuovo tool deve **wrappare**, non duplicare, la logica. Audit chain identica.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RUL training/inference | Custom regression code | scikit-learn `Ridge` / `RandomForestRegressor` | Battle-tested, deterministic con `random_state`, joblib serialization built-in |
| Model serialization | Pickle ad hoc | `joblib.dump(..., compress=("gzip", 3))` | scikit-learn idiomatic + compressed + secure handling |
| C-MAPSS dataset loading | Custom CSV parser | `pandas.read_csv(sep=r"\s+")` con schema fissato | Schema NASA standardizzato, no edge case |
| Thread checkpointing per Coach | Custom PG table + JSON state | `langgraph-checkpoint-postgres` `AsyncPostgresSaver` | Officially supported by LangGraph, riusa migration 005 Phase 4 |
| NATS durable consumer | Custom polling loop | `js.pull_subscribe(durable=..., config=ConsumerConfig(...))` con explicit ack | nats-py official API, load-balanceable se replicato |
| OEE pre-aggregation | Custom cron + materialized view manuale | TimescaleDB `CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)` + `add_continuous_aggregate_policy` | Incremental refresh, scales su 30 asset × 1Hz, no full recompute |
| Pareto chart calculation | Custom Python loop | `SELECT reason_code, SUM(duration_min) ... ORDER BY ... LIMIT $N` | Postgres do the lifting, no in-memory aggregation di milioni di righe |
| 5-Why validation | Free-form regex matching | Pydantic schema `RCAChain` con `min_length` constraints + ValidationError exception | Type-safe, Phase 1-6 standard, retry loop integrabile |
| Citation grounding | Trust LLM URI | Full PG lookup against `ingest.documents` + Qdrant payload | Mitiga T-V6-llm-hallucination Phase 6 threat |
| Failure mode taxonomy | New YAML file | Extend existing `failure_modes.yaml` (D-MNT-TAX) | Single source of truth, additive non-breaking |
| MTTR computation | Custom timer with side-effects | `thread.created_at` → `thread.completed_at` from checkpoint metadata | Resilient cross-restart, audit-friendly |

**Key insight:** Phase 7 deve **assemblare** componenti maturi (scikit-learn + LangGraph + TimescaleDB + NATS), non costruirne di nuovi. Ogni "custom" è un debito tecnico in PoC competition.

## Runtime State Inventory

Phase 7 è una phase di **estensione greenfield** (nuovi agenti + nuovi storage + nuovi modelli), non rename/refactor. La tabella sotto è inclusa per completezza ma la maggior parte delle categorie è vuota.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — nessun rename di colonne/tabelle esistenti. Nuove tabelle `maintenance.downtime_events`, CAGG `maintenance.oee_hourly`, nuova enum value ActionType (Phase 7 additive only). | Solo CREATE forward — migrations 008 + 009. |
| Live service config | None — nessun servizio esistente cambia config. `agents-scheduler` Phase 6 esplicitamente NON usato (D-PM-04). | Nessuna azione. |
| OS-registered state | None — il NATS stream `MAINTENANCE_STREAM` è nuovo, idempotent bootstrap via `js.add_stream(...)`. Consumer names `da-consumer`, `pm-consumer` registrati alla prima `js.pull_subscribe` call. | Bootstrap in container startup (idempotent). |
| Secrets/env vars | None nuovi richiesti. Riusa `DATABASE_URL`, `NATS_URL`, `LLM_BACKEND` Phase 1-6. | Nessuna azione. |
| Build artifacts | Nuovo `packages/sft-ml/` editable install richiede `uv sync` dopo creazione. Modello pre-trained `ridge-fd001-fd003-v1.0.joblib` committato — re-train solo se schema features cambia. | Plan task: `nx run sft-ml:train` come CI smoke. |

## Common Pitfalls

### Pitfall 1: joblib Cross-Version Serialization Breakage
**What goes wrong:** Modello `joblib.dump(pipeline)` con scikit-learn 1.7 + Python 3.12 fallisce `joblib.load()` su scikit-learn 1.9 o Python 3.13. UnpicklingError silente o behavior change in inference.
**Why it happens:** scikit-learn pickle format NON è stable across major versions. Pickle is "not designed for long-term storage" (warning ufficiale `model_persistence.html`).
**How to avoid:**
- Pin `scikit-learn>=1.7.0,<1.9.0` e `joblib>=1.5.0,<2.0.0` in `packages/sft-ml/pyproject.toml`.
- Companion `*.json` metadata file (vedi Pattern 3) con `sklearn_min`, `python_min` per fail-fast check on load.
- CI smoke test: `joblib.load(...)` + predict on FD001 first row + assert prediction within tolerance. Esegue su matrix Python 3.12 ONLY (Phase 1 locked Python 3.12+).
- Document re-train procedure in `packages/sft-ml/README.md`: `nx run sft-ml:train`.
**Warning signs:** `UnpicklingError`, `ModuleNotFoundError` su loading, predictions silently different from training baseline.
[CITED: scikit-learn.org/stable/model_persistence.html — "Pickle serialization is not designed for long-term storage"]

### Pitfall 2: RUL Target Engineering (piecewise-linear cap)
**What goes wrong:** Training su raw `max_cycle - current_cycle` produce modello con RMSE dominato dalla cosiddetta "healthy region" (early-life cycles dove RUL è grande e quasi non informativo). Performance reale (sui last cycles, dove RUL conta) è scarsa.
**Why it happens:** È un noto issue C-MAPSS — la convenzione di letteratura è cap RUL a 125 (piecewise-linear: degradation begins at threshold).
**How to avoid:**
- `compute_train_rul()` applica `np.minimum(rul, 125)` (vedi Pattern 3).
- Document choice in model card + cite Heimes 2008 (originale piecewise-linear).
- Test: assert RMSE_test ≤ 35 (typical baseline for Ridge with cap 125 on FD001).
**Warning signs:** Test RMSE > 50, predictions clustering attorno a un singolo valore, train/test gap > 20.

### Pitfall 3: Cross-Domain Feature Mapping Drift
**What goes wrong:** Mapping `loom_temperature → s8` produce predictions arbitrarie perché s8 in C-MAPSS è in range temperature LPT (~1400°F) mentre loom temperature è ~25-40°C. Magnitude shift rende l'inferenza unreliable.
**Why it happens:** No domain adaptation step in `feature_map.py`. La letteratura (LAMA-Net, MTLTrans) usa MMD o adversarial training per allineare distributions.
**How to avoid:**
- Documentare esplicitamente la limitation nel model card e in `feature_map.py` docstring.
- **Standardize per ASSET FAMILY** in inference: convert textile sensor a "C-MAPSS equivalent normalized" via `(x - textile_mean) / textile_std * cmapss_std + cmapss_mean`. Statistiche `textile_*` raccolte in offline calibration step (committed YAML).
- Phase 11 deferred: real domain adaptation (out of scope Phase 7).
- E2E test scenario `degraded` deve evidenziare il behavior — il planner deve accettare RUL output meno preciso su textile data come trade-off documentato.
**Warning signs:** Inference RUL predictions constantly at maximum (125) o costantemente bassi, no monotonic decrease across asset lifecycle.
[CITED: arxiv.org/pdf/2208.08388 — LAMA-Net per domain shift mitigation]

### Pitfall 4: TimescaleDB CAGG Retention Conflict
**What goes wrong:** Set `add_retention_policy('maintenance.downtime_events', INTERVAL '30 days')` + CAGG `oee_hourly` su 30 days di lookback → eseguire un `refresh_continuous_aggregate(...)` manuale dopo che la retention ha già droppato chunks vecchi cancella i bucket aggregati corrispondenti dal CAGG (TimescaleDB interpreta `assenza raw = righe cancellate`).
**Why it happens:** Documentation esplicita: "Always keep the aggregate's start_offset wider than your raw data retention window, and never manually refresh over a window where raw data no longer exists" (Tiger Data docs).
**How to avoid:**
- Phase 7: NIENTE retention policy su `maintenance.downtime_events` (dati piccoli ~MB/anno per 30 asset, no pressure).
- Se planner aggiunge retention policy → DEVE essere `> CAGG start_offset`.
- Documentare warning nel migration 008 SQL comments.
- NIENTE manual `refresh_continuous_aggregate` calls in agent code — solo policy-driven refresh.
**Warning signs:** OEE Pareto query restituisce bucket vuoti per finestre passate dopo restart.
[CITED: tigerdata.com/docs/use-timescale/latest/continuous-aggregates/refresh-policies]

### Pitfall 5: LLM RCA Citation Hallucination
**What goes wrong:** LLM ritorna citation `source_uri: "corpus://it/loom/SOP-LOOM-999-invented.md"` che non esiste nel knowledge base. Shape validation passa, ma evidence panel mostra link rotto a operatore.
**Why it happens:** LLM tendono a hallucinare URI plausibili sotto schema pressure. T-V6-llm-hallucination Phase 6 documenta proprio questo.
**How to avoid:**
- Citation validator FULL PG lookup (Claude's Discretion #2 recommendation): per ogni `cit.source_uri`, query `SELECT 1 FROM ingest.documents WHERE source_uri = $1 LIMIT 1`.
- Re-prompt budget 2 (oltre il quale → audit con flag `citations_hallucinated: true` + escalate to supervisor with explicit warning in payload).
- System prompt warning: "Se non trovi citation, chiama rag_search PRIMA di rispondere. Non inventare source_uri."
**Warning signs:** Re-prompt rate > 30% in test, `citations_hallucinated` flag > 0 in any audit row.
[CITED: arxiv.org/html/2604.06171 — "LLM-Augmented Knowledge Base Construction" su hallucination grounding]

### Pitfall 6: RCA Retry Loop Token Budget Exhaustion
**What goes wrong:** 2 retry × 4-step ReAct × 5 WhyStep × full citation evidence in prompt = facile sforare token budget per chiamata. Pitfall 1 research/PITFALLS.md (Infinite Agent Loops) applicabile.
**Why it happens:** Re-prompt non riassume il context, accumula error + previous response + corrective hint.
**How to avoid:**
- Re-prompt template: solo `{previous_response, error_message, correction_hint}`, NON tutto il history ReAct.
- `recursion_limit=10` esplicito sul `graph.invoke()` (consistente con Phase 4 D-X safe_invoke).
- BudgetTracker Phase 4 enforce per-thread token cap; oltre → HITL escalation con marker `budget_exhausted`.
- E2E test "failure" scenario include un mock LLM response che fa fallire validation 3 volte → assert correct escalation behavior.
**Warning signs:** Coach/RCA thread duration > 60s, repeated identical tool calls in trace.

### Pitfall 7: LangGraph Checkpoint State Bloat (MaintenanceCoach)
**What goes wrong:** Coach thread state cresce ad ogni step (messages history, completed_steps con full StepReport). Su intervention 4h × 30 step, state può crescere a 5-10MB; checkpoint write latency aumenta + PG storage pressure.
**Why it happens:** LangGraph state è serializzato JsonPlusSerializer (ormsgpack); PostgreSQL supporta fino a 1GB per field ma performance degrada > 10MB checkpoint blob.
**How to avoid:**
- State design: **NIENTE messages history completo nel state**. Solo `last_n_messages: list[dict]` (es. ultimi 5) + reference a `audit.actions` per full history.
- StepReport committato solo come `{step_no, duration_minutes, status}` (compact), no full LLM transcript.
- Test budget: state.size_bytes() < 200KB anche dopo 50 step.
- Monitoring: log warning su checkpoint write > 100ms.
**Warning signs:** Resume di un thread tarda > 2s, PG checkpoint_blobs table grows > 100MB.
[CITED: azguards.com/distributed-systems/the-checkpoint-bloat-mitigating-write-amplification-in-langgraph-postgres-savers/]
[CITED: pypi.org/project/langgraph-checkpoint-postgres/ — JsonPlusSerializer + 1GB field limit]

### Pitfall 8: Re-execution Dual-Write on Coach Resume (Phase 6 Pitfall §3 applicable)
**What goes wrong:** Coach step_node fa audit.write() PRIMA di `interrupt()`. Su resume, il node ri-esegue dall'inizio → audit row duplicato.
**Why it happens:** LangGraph re-executes the node body from the start on resume (esplicito in docs: "It reruns any work in that node done before this is called, but no previous nodes").
**How to avoid:**
- Pattern Phase 6 D-OA-04 / `EscalateToSupervisorTool` Pitfall §3: NIENTE side-effects PRIMA di interrupt(). Solo DOPO resume (POST il `Command(resume=...)`) si fa l'audit write — analogo a `human_approval_node` Phase 4.
- Per Coach: il pattern è leggermente diverso (l'interrupt è alla fine del step per attendere technician confirmation, dopo che il LLM ha già parlato). Soluzione: audit write usa `ON CONFLICT (action_id) DO NOTHING` + deterministic `action_id` = `sha256(thread_id || step_no || event_type)`.
**Warning signs:** Audit table grows con duplicate rows per stesso `thread_id, step_no`.

### Pitfall 9: OEE.Quality Cross-Cluster Gap (Phase 6 dependency)
**What goes wrong:** DowntimeAnalyzer query `audit.actions WHERE action_type='QUALITY_VERDICT'` ma QualityInspector Phase 6 non ha emesso QUALITY_VERDICT nella finestra (es. ops cluster offline 30min). OEE.Q ritorna NULL o 0 erroneamente.
**Why it happens:** Cross-cluster read-only dependency senza coordination.
**How to avoid:**
- Implementare fallback come D-DA-02: query sim-textile `production_state` metrics (`good_meters / total_meters` Phase 6 06-09) se window contiene 0 QUALITY_VERDICT rows.
- Log `oee_quality_fallback_used` warning structlog.
- OEEReport include `quality_source: 'audit'|'sim_metrics'|'mixed'` field per trasparenza.
- E2E test "degraded" scenario: simula ops cluster offline → assert fallback usato + audit row con quality_source='sim_metrics'.
**Warning signs:** OEE.Q = 1.0 perfetto sospetto (no QualityInspector rows), `quality_source: 'sim_metrics'` predominante in production traces.

### Pitfall 10: NATS Consumer ack-after-error
**What goes wrong:** DowntimeAnalyzer consumer fa `await m.ack()` PRIMA di INSERT in PG. Se INSERT fallisce (connessione, conflict), evento è perso (NATS lo considera consegnato).
**Why it happens:** Sviluppatore vede `ack` come "ho ricevuto" invece di "ho processato con successo".
**How to avoid:**
- Pattern Pattern 4: ack SOLO dopo INSERT success; `nak(delay=5)` su exception → JetStream redelivers fino `max_deliver`.
- `AckPolicy.EXPLICIT` esplicito in ConsumerConfig.
- Idempotent INSERT (`ON CONFLICT (event_id) DO NOTHING`) per gestire redelivery.
**Warning signs:** Downtime events count in PG < count in NATS stream, race con sim-textile generator.

## Code Examples

Già coperto in §Architecture Patterns 1-9 sopra. Reference quick:

| Operation | Pattern # |
|-----------|-----------|
| Load C-MAPSS FD001/FD003 | Pattern 1 |
| Map textile sensors → C-MAPSS schema | Pattern 2 |
| Train Ridge/RF deterministic + save | Pattern 3 |
| NATS durable pull consumer (DA + PM) | Pattern 4 |
| LangGraph async thread + checkpoint (Coach) | Pattern 5 |
| 5-Why structured prompt + validator | Pattern 6 |
| TimescaleDB CAGG OEE hourly + OEE queries | Pattern 7 |
| Audit enum extension migration 009 | Pattern 8 |
| build_maintenance_subgraph router | Pattern 9 |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| RUL prediction with LSTM/CNN PyTorch | scikit-learn Ridge/RF for PoC + domain adaptation papers (LAMA-Net 2022, Bi-Discrepancy 2023) | Ongoing — heavier models still SOTA accuracy, ma scope PoC ≠ production accuracy | D-PM-01 esplicitamente sceglie scikit-learn — accept trade-off |
| Materialized view PG nativa + cron refresh | TimescaleDB continuous aggregate | TimescaleDB 1.7+ (2020), maturo a 2.x | D-DA-03 — CAGG vince per incremental update |
| Sync ReAct single-shot | LangGraph async thread + AsyncPostgresSaver | LangGraph 0.4+ (2025) | D-MC-01 — direct match cross-shift requirement |
| Free-form LLM RCA | Structured CoT + citation grounding (RAG) | 2024-2025 best practice for production RCA | D-RCA-01 — match success criterion #2 |
| NATS push subscribe | Pull subscribe durable + explicit ack | nats-py 2.10+ JetStream maturity | Pattern 4 — backpressure control |

**Deprecated/outdated:**
- Pickle senza joblib: usare joblib per scikit-learn (idiomatic).
- `langgraph-checkpoint-sqlite` in prod: solo dev (locked Phase 4).
- ReAct con max_iterations infinito: sempre `recursion_limit` esplicito (Phase 4 D-X).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Textile sensor → C-MAPSS sensor proxy mapping è "semantically reasonable" senza domain adaptation tecniche | Pattern 2 | RUL predictions su textile data unreliable (Pitfall 3 mitigation: per-family normalization + esplicito limitation doc) |
| A2 | RUL piecewise-linear cap 125 standard è ottimale per textile (preso da C-MAPSS literature) | Pattern 3 + Pitfall 2 | Sub-optimal predictions su long-tail healthy assets; può richiedere tuning empirico durante CI smoke |
| A3 | CAGG refresh 5min su 30 asset × ingest 1Hz è adeguato per "real-time" OEE | Pattern 7 + D-DA-03 | Stale OEE in finestre fresche; mitigation via real-time aggregate option TimescaleDB |
| A4 | scikit-learn 1.7.x è "future-stable" per i prossimi 6 mesi di vita PoC | Stack | Re-train se 1.9+ rompe deserialization (Pitfall 1) — mitigation pinning |
| A5 | LangGraph checkpoint state < 200KB sostenibile per Coach 50-step intervention | Pitfall 7 | Resume latency degrada → operator UX impatto; mitigation state design parsimonioso |
| A6 | OEE.Quality cross-cluster query (audit.actions index existing) gestisce 1h-24h window senza nuovo index | D-DA-02 + Pitfall 9 | Slow query → endpoint latency; mitigation: misurare in plan; se >500ms aggiungere indice composito |
| A7 | Citation full PG lookup (~50ms × 5 = 250ms per RCA chain) accettabile latency-wise | Pattern 6 + Claude's Discretion #2 | Slow user perception; mitigation: aggregate citation lookup in single `IN (...)` query |
| A8 | NATS `MAINTENANCE_STREAM` separation from `SENSOR_EVENTS` + `AUDIT_STREAM` (Phase 3/4) è il design coerente | Pattern 4 + Architecture diagram | Subject overlap potentially; mitigation: bootstrap stream con disjoint subjects whitelist |
| A9 | `failure_modes.yaml` extension additive non rompe Phase 6 loader (no breaking change a `OpsLoader`) | D-MNT-TAX | Loader breaks → Phase 6 tests fail; mitigation: planner task dedicato a backward compat test |
| A10 | `request_help` tool wrapper non duplica audit row (1 audit per escalation, marker `escalation_trigger` distingue) | D-MC-02 | Duplicate audit → reporting inflato; mitigation: deterministic action_id (Pitfall 8 pattern) |
| A11 | Trigger event-driven AnomalyDetector→PredictiveMaintenance via NATS subject `maintenance.predict.*` può essere implementato in Phase 7 side senza touch Phase 6 code | Cross-cluster wiring | Se Phase 6 AnomalyDetector non pubblica già su questo subject, Phase 7 deve aggiungere publish (modificare Phase 6) — VIOLA locked constraint. **Planner DEVE verificare** in `apps/agents/ops/anomaly-detector/src/.../agent.py` se publish hook esiste o va aggiunto. |
| A12 | Bootstrap `MAINTENANCE_STREAM` via `js.add_stream(...)` idempotent in agent process startup è acceptable (no nuovo bootstrap script) | Pattern 4 | Race condition se 2 agent process competono → mitigation: dedicated bootstrap script tipo Phase 3 `nats-bootstrap-streams.py` esteso |

## Open Questions

1. **AnomalyDetector publish hook esiste?**
   - **What we know:** Phase 6 D-AD-01 dice "alert via audit.actions"; non c'è mention esplicita di NATS publish su `maintenance.predict.*`.
   - **What's unclear:** Se NATS publish va aggiunto a `apps/agents/ops/anomaly-detector/src/.../agent.py` — violerebbe locked constraint "no modifications a Phase 6 agents/code".
   - **Recommendation:** Planner ispeziona codice esistente. Se hook assente, valutare alternative: (a) thin extension Phase 7 al codice AD (audit comment chiarito come non-business-logic-modification), (b) usare DIFFERENT trigger pathway (es. Phase 7 PredictiveMaintenance consumer su `audit.actions` rows INSERT via PG NOTIFY/LISTEN — più elegant ma più costoso da implementare). Discutere con user.

2. **Continuous aggregate refresh interval ottimo.**
   - **What we know:** D-DA-03 specifica 5min default; research conferma "5min ragionevole" su low-frequency event stream (downtime ~5 events/h/asset, total ~150 events/h cluster).
   - **What's unclear:** Se planner vuole "near-real-time" OEE dashboard (1min refresh), trade-off worker contention vs freshness.
   - **Recommendation:** Mantenere 5min per Phase 7. Phase 11 può tunare in base a Langfuse traces se UI mostra "stale OEE perceived".

3. **Coach thread state initial bootstrap quando intervention starts senza technician noto.**
   - **What we know:** D-MC-01 schema include `technician_id`.
   - **What's unclear:** Se intervention auto-opens su RCA recommendation (no technician assigned), valore di `technician_id`?
   - **Recommendation:** Allow nullable + assert non-null prima del primo step. Planner decide UX.

4. **Joint training su FD001 + FD003 vs ensemble vs strategy.**
   - **What we know:** D-PM-02 dice "FD001 + FD003 committato".
   - **What's unclear:** Single model joint o 2 model + routing per asset_family (mechanical vs dye chamber)?
   - **Recommendation:** Single Ridge model joint baseline (simpler, deterministic). RandomForest variant come optional. Document choice in model card.

5. **OEE.Performance computation.**
   - **What we know:** D-DA-03 menziona OEE = A × P × Q; data sources documented per A (downtime) e Q (cross-cluster).
   - **What's unclear:** P (Performance = actual_speed / ideal_speed) data source. Sim-textile production_state ha `target_meters_per_hour`? Cycle time disponibile?
   - **Recommendation:** Planner verifica `production_state.py` e `asset_capacity.yaml` (Phase 6 D-PP-02): se `target_throughput` esiste, usalo. Else: P = 1.0 placeholder + flag `performance_source: 'placeholder'` in OEEReport. Phase 11 può raffinare.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Tutti i package | ✓ (Phase 1 locked) | 3.12.x | — |
| PostgreSQL 16 + TimescaleDB 2.x | migration 008/009 + CAGG + checkpoints | ✓ (Phase 3/4) | running | — |
| NATS JetStream 2.10+ | downtime + predict subjects | ✓ (Phase 3/4) | running | — |
| Qdrant 1.16+ | RAG citation lookup (RCA + Coach) | ✓ (Phase 5) | running | — |
| Neo4j Community 5.24 | traverse_graph (RCA) | ✓ (Phase 5) | running | — |
| Ollama (dev) | LLM mock factory fallback per dev tests | ✓ (Phase 4) | running | LLM_BACKEND=mock |
| scikit-learn 1.7+ | RUL training/inference | ✗ (NEW install) | — | NIENTE fallback — install è blocking task |
| joblib 1.5+ | model serialization | ✗ (transitive di sklearn, but explicit) | — | NIENTE fallback |
| nats-py 2.10+ | consumer | ✓ (Phase 3) | already installed | — |
| `langgraph-checkpoint-postgres` 3.1.0 | Coach thread | ✓ (Phase 4) | already installed | — |
| GPU CUDA | NOT REQUIRED — niente torch/inference su GPU | n/a | n/a | scikit-learn CPU only |

**Missing dependencies with no fallback:**
- `scikit-learn>=1.7.0` — install required, planner aggiunge a `packages/sft-ml/pyproject.toml`.
- `joblib>=1.5.0` — analogo.
- `pandas>=2.3.0` — analogo (transitive sklearn ma esplicito per IO data).

**Missing dependencies with fallback:** None.

## Validation Architecture

Nyquist validation è `true` in `.planning/config.json` — questa sezione è REQUIRED.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Phase 1+ locked) + pytest-asyncio + testcontainers |
| Config file | `pyproject.toml` root (Phase 1) + per-project (`packages/*/pyproject.toml`) |
| Quick run command | `nx run-many --target=test --projects=sft-ml,mnt-predictive-maintenance,mnt-rca-specialist,mnt-maintenance-coach,mnt-downtime-analyzer -- --no-cov -x` |
| Full suite command | `nx affected --target=test -- --cov` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MNT-01 | PredictiveMaintenance produce `RULEstimate` deterministic su input C-MAPSS-mapped textile window | unit + integration | `pytest apps/agents/maintenance/predictive-maintenance/tests/test_inference.py -x` | ❌ Wave 0 |
| MNT-01 | C-MAPSS feature mapping table coerente con `sft-assets` registry | unit | `pytest packages/sft-ml/tests/test_feature_map.py -x` | ❌ Wave 0 |
| MNT-01 | Joblib model load + predict cross-Python compat smoke | smoke | `pytest packages/sft-ml/tests/test_model_smoke.py -x` | ❌ Wave 0 |
| MNT-01 | E2E happy: AD alert → NATS → PM inference → audit row RUL_ESTIMATE | e2e | `pytest tests/e2e/maintenance/test_predictive_maintenance_scenarios.py::test_happy -x` | ❌ Wave 0 |
| MNT-01 | E2E degraded: health_index < 0.3 → HITL supervisor interrupt | e2e | `pytest tests/e2e/maintenance/test_predictive_maintenance_scenarios.py::test_degraded -x` | ❌ Wave 0 |
| MNT-01 | E2E failure: malformed sensor input → predictable error + audit | e2e | `pytest tests/e2e/maintenance/test_predictive_maintenance_scenarios.py::test_failure -x` | ❌ Wave 0 |
| MNT-02 | RCAChain Pydantic schema enforce 5 step + ≥1 citation/step | unit | `pytest apps/agents/maintenance/rca-specialist/tests/test_models.py -x` | ❌ Wave 0 |
| MNT-02 | Validator post-LLM enforce + re-prompt 2x + escalate on fail | unit + integration | `pytest apps/agents/maintenance/rca-specialist/tests/test_validators.py -x` | ❌ Wave 0 |
| MNT-02 | E2E happy/degraded/failure (mock LLM scenarios) | e2e | `pytest tests/e2e/maintenance/test_rca_specialist_scenarios.py -x` | ❌ Wave 0 |
| MNT-03 | LangGraph checkpoint thread resume cross-restart (testcontainers PG) | integration | `pytest apps/agents/maintenance/maintenance-coach/tests/test_checkpoint_resume.py -x` | ❌ Wave 0 |
| MNT-03 | MTTR computation: thread.created_at → completed_at correct | unit | `pytest apps/agents/maintenance/maintenance-coach/tests/test_mttr.py -x` | ❌ Wave 0 |
| MNT-03 | `request_help` tool wrappa `escalate_to_supervisor` + audit con marker | unit + integration | `pytest packages/sft-agents/tests/tools/test_request_help.py -x` | ❌ Wave 0 |
| MNT-03 | E2E multi-turn happy/degraded/failure con checkpoint replay | e2e | `pytest tests/e2e/maintenance/test_maintenance_coach_scenarios.py -x` | ❌ Wave 0 |
| MNT-04 | Migration 008 applies idempotent + hypertable + CAGG created | integration | `pytest infra/migrations/timescale/tests/test_migration_008.py -x` | ❌ Wave 0 |
| MNT-04 | OEE.A computation correct on synthetic downtime window | unit | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_oee.py::test_availability -x` | ❌ Wave 0 |
| MNT-04 | OEE.Q cross-cluster audit query + fallback path | integration | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_oee.py::test_quality_cross_cluster -x` | ❌ Wave 0 |
| MNT-04 | Pareto top-N query correct ordering | unit | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_pareto.py -x` | ❌ Wave 0 |
| MNT-04 | NATS durable consumer `da-consumer` ack-after-INSERT + nak-on-error | integration | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_consumer.py -x` | ❌ Wave 0 |
| MNT-04 | E2E happy/degraded/failure (deterministic SQL aggregation, no LLM mock) | e2e | `pytest tests/e2e/maintenance/test_downtime_analyzer_scenarios.py -x` | ❌ Wave 0 |
| MNT-05 | `failure_modes.yaml` schema extension loads + validator CI verifica unicità reason_code | unit | `pytest packages/sft-domain/tests/failure_modes/test_maintenance_meta.py -x` | ❌ Wave 0 |
| MNT-05 | Validator CI: `intervention_steps_sop_id` esiste in corpus Phase 5 | integration | `pytest scripts/validate_failure_modes_test.py -x` (estende esistente) | ⚠️ estendere |
| MNT-05 | Doc bilingue `event-taxonomy.{it,en}.md` build OK in mkdocs | doc-build | `mkdocs build --strict` | ✓ (Phase 5 esistente) |
| MNT-06 | Asset registry integration (sft-assets) + downtime_events FK-like check | integration | `pytest apps/agents/maintenance/downtime-analyzer/tests/test_repository.py::test_asset_validation -x` | ❌ Wave 0 |
| MNT-06 | Audit chain `triggered_by_action_id` link AD→PM | integration | `pytest tests/e2e/maintenance/test_predictive_maintenance_scenarios.py::test_audit_chain -x` | ❌ Wave 0 |
| Migration 009 | ActionType ext idempotent + enum lockstep | integration | `pytest infra/migrations/timescale/tests/test_migration_009.py -x` | ❌ Wave 0 |
| Enum sync | Python `ActionType` ↔ SQL CHECK constraint | unit | `pytest packages/sft-agents/tests/test_audit_constraints.py -x` (esistente, estendere) | ⚠️ estendere |

### Sampling Rate

- **Per task commit:** `nx affected --target=test -- --no-cov -x` (atomic project tests only, <30s typical)
- **Per wave merge:** `nx affected --target=test -- --cov` (full coverage report)
- **Phase gate:** Full suite green + E2E maintenance scenarios pass before `/gsd:verify-work`. Comando:
  ```
  pytest tests/e2e/maintenance/ -m "e2e and not real-llm" --tb=short
  ```

### Wave 0 Gaps

Wave 0 (test scaffold) deve creare:
- [ ] `packages/sft-ml/tests/__init__.py` + `test_feature_map.py` + `test_model_smoke.py` placeholder
- [ ] `apps/agents/maintenance/predictive-maintenance/tests/{__init__.py,conftest.py,test_inference.py}` placeholder
- [ ] `apps/agents/maintenance/rca-specialist/tests/{__init__.py,conftest.py,test_models.py,test_validators.py}` placeholder
- [ ] `apps/agents/maintenance/maintenance-coach/tests/{__init__.py,conftest.py,test_checkpoint_resume.py,test_mttr.py}` placeholder
- [ ] `apps/agents/maintenance/downtime-analyzer/tests/{__init__.py,conftest.py,test_oee.py,test_pareto.py,test_consumer.py,test_repository.py}` placeholder
- [ ] `infra/migrations/timescale/tests/test_migration_008.py` + `test_migration_009.py` placeholder
- [ ] `tests/e2e/maintenance/{__init__.py,conftest.py,test_predictive_maintenance_scenarios.py,test_rca_specialist_scenarios.py,test_maintenance_coach_scenarios.py,test_downtime_analyzer_scenarios.py}` placeholder
- [ ] `tests/fixtures/mnt_scenarios/<agent>/{happy,degraded,failure}.yaml` 12 scenario stubs (4 agent × 3)
- [ ] `tests/fixtures/llm_responses/{rca-specialist,maintenance-coach}/{happy,degraded,failure}.jsonl` mock LLM replay stubs (6 totali)
- [ ] `packages/sft-agents/tests/tools/test_request_help.py` placeholder
- [ ] `packages/sft-domain/tests/failure_modes/test_maintenance_meta.py` placeholder
- [ ] Estendere `scripts/validate-failure-modes.py` con nuovo check `reason_code` unicità
- [ ] Estendere `packages/sft-agents/tests/test_audit_constraints.py` con i 5 nuovi ActionType (round-trip)

**Mock LLM strategy per Phase 7:**
- **PredictiveMaintenance**: NO LLM mock needed — deterministic scikit-learn inference. Test fixtures = pre-computed sensor windows + expected RUL output (assertion exact match).
- **DowntimeAnalyzer**: NO LLM mock needed — deterministic SQL aggregation. Test fixtures = pre-seeded `downtime_events` rows + expected OEEReport.
- **RCASpecialist**: LLM mock REQUIRED (record/replay JSONL). 3 scenari × happy (valid 5-Why)/degraded (1 retry needed)/failure (2 retry → escalation).
- **MaintenanceCoach**: LLM mock REQUIRED. 3 scenari × happy (5-step intervention completes)/degraded (technician keyword "aiuto" mid-flow)/failure (LLM produce step inesistente).

## Security Domain

`security_enforcement` non esplicitamente disabled in config — included per default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | partial — riusa Phase 4/Phase 10 JWT (no nuova auth in Phase 7) | FastAPI Depends + JWT (Phase 4/10) |
| V3 Session Management | partial — `thread_id` per Coach è sensibile (può leakare info su intervention attive) | Riusa Phase 4 RBAC + thread_id non-guessable (UUID4) |
| V4 Access Control | yes — endpoint `/v1/agents/downtime-analyzer/report` deve essere RBAC-gated (manager/operator) | FastAPI Depends + `user_roles` injection Phase 4 |
| V5 Input Validation | YES — every input via Pydantic v2 frozen + extra=forbid. NATS payload validation. SQL via asyncpg `$1..$N`. | Pydantic v2 + asyncpg parameterized queries |
| V6 Cryptography | minimal — no nuovi secret, no nuova encryption. joblib model file integrity garantita da git hash. | git commit hash come integrity proof |
| V8 Data Protection | yes — downtime events include `work_order_id`, `dye_lot_id` potenzialmente sensibili (commercial info) | acl_level inheritance da Phase 5 sui SOP citati; `downtime_events` table accessible only via agent role (no anonymous reads) |
| V12 Files | yes — joblib pickle file → security risk se caricato da source untrusted | Modello viene da repo committato (trust source = code review) + companion JSON metadata fail-fast su version mismatch |

### Known Threat Patterns for Phase 7 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Pickle/joblib deserialization arbitrary code execution | Tampering + Elevation | Modello loadato SOLO da path interno al package `packages/sft-ml/models/*.joblib` (no user upload). Companion JSON metadata fail-fast su mismatch (Pitfall 1). |
| LLM prompt injection nel RCA (es. downtime_event.notes con instruction "ignore previous") | Tampering | Phase 6 T-V6-injection mitigation: prompt input length cap (max 2000 chars per field, mirror EscalateInput); structured output enforce. |
| LLM citation hallucination (Pitfall 5) | Tampering (integrity of audit) | Full PG source_uri lookup; escalate to supervisor with explicit warning on `citations_hallucinated: true` |
| NATS DoS event flood (`maintenance.downtime.*`) | DoS | Mirror Phase 6 T-V6-dos-event-flood: rate-limit downtime_event_generator to ≤30/min faulted, ≤10/min nominal (already designed in mirror pattern); JetStream consumer max_ack_pending limit |
| Cross-cluster audit reads expose QualityVerdict di altri tenant | Information Disclosure | PoC single-tenant — non applica. Documentare in assumption register se Phase deploy diventa multi-tenant. |
| Coach thread state leak via PG dump | Information Disclosure | langgraph_checkpoints riusa Phase 4 ACL — agent_role only. Backup PG già scope Phase 11. |
| OEE Pareto query SQL injection via window_start/window_end | Tampering | Pydantic v2 datetime parsing + asyncpg $1..$N (Phase 1 standard). |
| Coach `request_help` tool log of `context` field può contenere PII technician | Information Disclosure | Audit `context` field length-capped + structured; documentare retention 90d NATS + 7y PG (Phase 4 D-56 standard). |

## Project Constraints (from CLAUDE.md)

**NO project-level CLAUDE.md found at repo root** (`./CLAUDE.md` not present at `/media/federicocalo/D1/prj/Smart Factory Transformation/`). Solo global instructions in `~/.claude/rules/common/*.md` applicabili a tutti i progetti. Estratto le direttive globali rilevanti per Phase 7:

- **Immutability:** Tutti i Pydantic models `frozen=True` + `extra="forbid"` (già standard Phase 1+).
- **File Organization:** 200-400 lines typical, 800 max. Many small files preferito. → Planner distribuisce business logic per agent in `agent.py`, `models.py`, `validators.py`, `consumer.py`, `prompts.py` (non un singolo god file).
- **Error Handling:** No silent swallow. Tutti gli error path verso audit + structlog + HITL escalation se rilevante.
- **Input Validation:** Pydantic v2 + asyncpg parameterized + NATS payload validation (`json.loads` + Pydantic constructor).
- **Code Quality Checklist:** Pre-completion check obbligatorio (planner include in DoD).
- **Testing 80%+ coverage:** Plan deve includere coverage gate.
- **TDD:** Wave 0 test scaffolds prima (RED), business logic dopo (GREEN), refactor.
- **Security checks:** No hardcoded secrets, input validation, SQL injection prevention (asyncpg parameterized).
- **Hooks/TodoWrite:** Planner usa TodoWrite per tracking.

## Sources

### Primary (HIGH confidence)
- `docs.langchain.com/oss/python/langgraph/interrupts` — interrupt + Command + cross-shift resume pattern
- `pypi.org/project/langgraph-checkpoint-postgres/` — AsyncPostgresSaver API (verified 3.1.0 latest via `pip index versions`)
- `scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html` — Ridge API
- `scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html` — RF API
- `scikit-learn.org/stable/model_persistence.html` — joblib persistence + warning on cross-version
- `docs.nats.io/using-nats/developer/develop_jetstream/consumers` — Durable consumer concepts
- `nats-io.github.io/nats.py/modules.html` — nats-py API (pull_subscribe + ConsumerConfig)
- `tigerdata.com/docs/use-timescale/latest/continuous-aggregates/refresh-policies` — CAGG refresh best practice
- `leanproduction.com/oee/` — OEE formula canonical
- Local: `infra/migrations/timescale/007_extend_audit_decisions.sql` — model per migration 009
- Local: `packages/sft-agents/src/sft_agents/runtime/clusters.py` — `build_ops_subgraph` model
- Local: `packages/sft-agents/src/sft_agents/tools/hitl.py` — `EscalateToSupervisorTool` pattern (wrap)
- Local: `simulators/sim-textile/src/sim_textile/quality_event_generator.py` — mirror for downtime generator
- Local: `simulators/sim-textile/src/sim_textile/production_state.py` — pattern for ProductionState reuse
- Local: `packages/sft-domain/src/sft_domain/failure_modes.yaml` — extension target

### Secondary (MEDIUM confidence — webcoverage + literature)
- `github.com/makinarocks/awesome-industrial-machine-datasets/blob/master/data-explanation/C-MAPSS/README.md` — C-MAPSS schema explanation
- `data.nasa.gov/dataset/cmapss-jet-engine-simulated-data` — dataset metadata
- `arxiv.org/pdf/2208.08388` — LAMA-Net domain adaptation per RUL
- `arxiv.org/html/2510.03604` — Deep Domain Adaptation Turbofan RUL survey 2025
- `arxiv.org/pdf/2305.15778` — LLM-based RCA cloud incidents
- `mljar.com/ai-prompts/prompts-engineer/chain-of-thought-for-analysis/prompt-root-cause-cot/` — RCA CoT prompt template
- `azguards.com/distributed-systems/the-checkpoint-bloat-mitigating-write-amplification-in-langgraph-postgres-savers/` — LangGraph checkpoint bloat mitigation
- `tigerdata.com/blog/real-time-analytics-for-time-series-continuous-aggregates` — CAGG concept
- `arxiv.org/html/2604.06171` — LLM-augmented KB construction for RCA hallucination grounding

### Tertiary (LOW confidence — to be re-verified durante implementation)
- `oneuptime.com/blog/post/2026-02-02-nats-python/view` — nats-py beginner guide
- `medium.com/@mihaitimoficiuc/predicting-jet-engine-failures-with-nasas-c-mapss-dataset-and-lstm-...` — practical LSTM C-MAPSS guide (informativo, NON cited per scelta architetturale)

## Metadata

**Confidence breakdown:**
- Standard stack (scikit-learn, joblib, langgraph-checkpoint-postgres, nats-py, TimescaleDB): **HIGH** — verified pip index versions + official docs cited
- Architecture patterns (durable consumer, CAGG, async thread, ReAct router): **HIGH** — multiple authoritative sources + local Phase 6 reference implementations
- C-MAPSS dataset schema: **HIGH** — official NASA + awesome-industrial-machine-datasets corroboration
- Cross-domain mapping textile→C-MAPSS: **MEDIUM** — semantic best-guess, literature acknowledges domain shift problem; explicit limitation documented (Pitfall 3)
- RCA citation grounding pattern: **MEDIUM** — best practice well-established, exact validator design (full PG lookup vs shape) is Claude's Discretion #2
- Audit migration pattern: **HIGH** — DIRECT mirror of Phase 6 migration 007
- Maintenance event taxonomy: **MEDIUM** — ISO 14224 referenced (not certified), reason_code naming convention to be planner-chosen
- OEE methodology: **HIGH** — Nakajima 1988 TPM standard, OEE.com canonical
- Wiring AD→PM event-driven: **MEDIUM** — locked in CONTEXT but requires Phase 6 code inspection (Open Question 1) to verify no Phase 6 modification needed

**Research date:** 2026-05-23
**Valid until:** 2026-06-22 (30 days — stable stack); re-verify scikit-learn ≥1.9 release dates and TimescaleDB CAGG policy syntax if reopened later.
