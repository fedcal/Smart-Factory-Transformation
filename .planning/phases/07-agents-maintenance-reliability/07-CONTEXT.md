---
phase: 7
phase_name: Agents — Maintenance & Reliability
phase_slug: agents-maintenance-reliability
discussed_at: "2026-05-23"
requirements: [MNT-01, MNT-02, MNT-03, MNT-04, MNT-05, MNT-06]
depends_on_phases: [3, 4, 5, 6]
---

# Phase 7 Context — Agents — Maintenance & Reliability

<domain>
## Phase Boundary

**What this phase delivers:** la business logic dei 4 agenti del cluster `maintenance` (PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer) sopra il runtime Phase 4 (supervisor + HITL + LLM adapter + audit), knowledge layer Phase 5 (rag_search + traverse_graph), simulator Phase 3 (NATS sensor.events + TimescaleDB) e gli artefatti Phase 6 (cluster subgraph pattern, audit enum extension pattern, scheduler service, mock LLM backend, sim-textile extension pattern di 06-09).

Concretamente:
- 4 implementazioni agent in `apps/agents/maintenance/{predictive-maintenance,rca-specialist,maintenance-coach,downtime-analyzer}/src/` con `__call__(state) -> state` callable invocato come nodo del `clusters/maintenance` subgraph (nuovo `build_maintenance_subgraph` analogo a `build_ops_subgraph` di Phase 6 D-X OPS routing).
- **PredictiveMaintenance**: modello ML lightweight (Ridge / RandomForest scikit-learn) addestrato offline su subset NASA C-MAPSS FD001+FD003, inference deterministic; trigger event-driven da AnomalyDetector Phase 6 quando severity major+; output `RULEstimate` Pydantic con `rul_cycles`, `confidence_band_lower/upper`, `health_index [0..1]`, `recommended_action: str | None`; HITL supervisor su `health_index < 0.3`.
- **RCASpecialist**: ReAct LangGraph + tool `rag_search` + tool `traverse_graph`; produce `RCAChain` Pydantic con form-based 5-Why fixed schema (5 step esatti, ognuno con citation obbligatoria dal knowledge base); validator post-LLM enforce 5+citation; `corrective_action_recommendation` sempre passa per HITL tier `supervisor` (success criterion #2 letterale).
- **MaintenanceCoach**: async LangGraph thread con checkpoint persistito in PG (riuso `langgraph_checkpoints` migration 005 Phase 4); ogni intervention = 1 thread riavviabile cross-shift (technician pausa al step N, riprende a step N+1 ore dopo); MTTR computato da `thread.created_at` → `thread.completed_at`; tool nuovo `request_help(reason, context)` per escalation esplicita su technician keyword (wrappa `escalate_to_supervisor` di Phase 6 D-OA-04).
- **DowntimeAnalyzer**: consumer NATS JetStream durable `da-consumer` su `maintenance.downtime.>` + storage in PG `maintenance.downtime_events` (nuova migration 008); calcola OEE decomposition (Availability × Performance × Quality) materializzata come TimescaleDB continuous aggregate `maintenance.oee_hourly`; on-demand query API restituisce `OEEReport` + `list[ParetoEntry]`; OEE.Quality cross-cluster da `audit.actions WHERE action_type='QUALITY_VERDICT'` (Phase 6) con fallback sim-textile production metrics.
- **Estensione sim-textile**: nuovo modulo `downtime_event_generator.py` (mirror del `quality_event_generator.py` di 06-09) che emette stochastic downtime events su NATS subject `maintenance.downtime.<asset_id>` con payload `{reason_code, duration_min, severity, work_order_id?, dye_lot_id?, timestamp}` da taxonomy MNT-05 derivata da `failure_modes.yaml`.
- **Estensione failure_modes.yaml** (D-MNT-TAX, pre-decisa): aggiunta di campi maintenance-specific (`reason_code`, `mttr_target_minutes`, `intervention_steps_sop_id`) — naturale dopo Phase 5 D-65 (registry) e Phase 6 D-QI-03 (hitl_tier). No nuovo file separato.
- **Audit enum extension** (mirror Phase 6 D-AE-01): migration `009_extend_audit_mnt.sql` (DROP+ADD CHECK constraints) per nuovi `ActionType.RUL_ESTIMATE`, `ActionType.RCA_CHAIN`, `ActionType.COACH_STEP`, `ActionType.DOWNTIME_VERDICT`, `ActionType.OEE_REPORT`. Pattern testcontainers Phase 6 D-AE-02.
- **Tassonomia eventi manutenzione** (MNT-05): estensione `failure_modes.yaml` esistente + documentazione in `docs/agents/maintenance/event-taxonomy.it.md` + `.en.md` (mirror pattern 06-14). Bilingue, validator CI verifica `reason_code` orfani.
- **Test E2E**: 3 scenari per agente (happy / degraded / failure) con LLM mock (`LLM_BACKEND=mock` Phase 6 D-X-01 / 06-03 MockReplayChatModel) + scenario YAML deterministici in `tests/fixtures/mnt_scenarios/` mirror del pattern di Phase 6 06-13. Per PredictiveMaintenance: scenari deterministic via fissaggio `random_state` dei modelli scikit-learn. Per MaintenanceCoach: scenari multi-turn con checkpoint replay.

Questa phase **NON** introduce torch/PyTorch (LSTM port scartato), **NON** introduce auto-tuning della baseline RUL (deferred Phase 11 quando osservato drift in produzione simulata), **NON** ship UI delle approval card (Phase 10), **NON** publica RUL/OEE su subject cross-cluster automatico oltre l'event-driven trigger AnomalyDetector→PredictiveMaintenance (deferred Phase 9 cross-cluster orchestration), **NON** introduce real-time work-order management system (work_order_id rimane riferimento opaco a sistema esterno per il PoC), **NON** introduce maintenance scheduling algorithms (PreventiveMaintenance scheduling è fuori scope, deferred Phase 9).

## Cross-Cluster Wiring (importante per researcher e planner)

Phase 7 introduce **2 dipendenze cross-cluster esplicite verso Phase 6**:

1. **AnomalyDetector → PredictiveMaintenance** (event-driven trigger). Quando AnomalyDetector di Phase 6 emette un alert con severity `major` o `critical`, automaticamente trigga PredictiveMaintenance scoring sull'asset. Wiring options da valutare in research:
   - (a) Direct NATS subject `maintenance.predict.<asset_id>` su cui PredictiveMaintenance ha consumer + AnomalyDetector emette su detection (publish-subscribe loose coupling, preferito).
   - (b) Supervisor subgraph routing esplicito (cluster `ops` invoca `target_agent='predictive-maintenance'`).
   - Audit chain: AnomalyDetector audit row `Decision.ANOMALY_ALERT` → trigger audit row `Decision.AUTO + ActionType.RUL_ESTIMATE` con `triggered_by_action_id` link.

2. **DowntimeAnalyzer ← QualityInspector audit reads** (cross-cluster query). OEE.Quality calcolata leggendo righe `audit.actions WHERE action_type='QUALITY_VERDICT'` emesse da QualityInspector Phase 6. Fallback su sim-textile production metrics se gap finestra. Nessun cambiamento all'audit schema (read-only cross-cluster).

Entrambi i wiring richiedono **coordinamento con Phase 6 esistente, no modifiche a Phase 6 agents** (solo aggiunte da Phase 7 side). Da documentare in PLAN.md come "Cross-cluster integration".
</domain>

<decisions>
## Implementation Decisions

### PredictiveMaintenance

- **D-PM-01 — Lightweight ML (Ridge / RandomForest) su NASA C-MAPSS subset.** Modello scikit-learn (target ~5–10MB total package) addestrato offline su subset NASA C-MAPSS, inference deterministic con `random_state` fissato. Output `RULEstimate` Pydantic. **Perché:** match preciso success criterion #1 ("C-MAPSS adapted to textile") con citazione del dataset NASA, deps leggere (scikit-learn già in transitive deps), training pipeline riproducibile in CI. **Rejected:** Pure heuristic (non cita C-MAPSS), Hybrid LLM (audit complesso + meno deterministic), LSTM PyTorch port (~700MB torch overkill PoC).

- **D-PM-02 — Dataset C-MAPSS FD001 + FD003 committato in repo.** Subset CSV/Parquet in `packages/sft-ml/data/c-mapss-fd001/` e `packages/sft-ml/data/c-mapss-fd003/` (~10MB train+test). FD001 = single fault mode + single op condition (baseline); FD003 = multi fault mode (HPC degradation) → mapping textile a 2 fault families (mechanical wear / dye chamber contamination). Citazione PHM 2008 NASA Prognostics CoE nel model card. **Perché:** riproducibile, no download runtime, deterministic CI offline; copertura di 2 fault families più realistica del solo FD001. **Rejected:** Solo FD001 (single fault non riflette textile reality), Download lazy (rete richiesta in CI, mirror NASA può cambiare URL).

- **D-PM-03 — Feature mapping: train su C-MAPSS pure, infer su textile sensor proxies.** Modello addestrato sui 21 sensor C-MAPSS originali + 3 op_settings. A inference time, sensor textile vengono mappati a "sensor proxy" equivalenti (es. spindle vibration → fan vibration C-MAPSS sensor s9; loom temperature → LPT outlet temperature C-MAPSS sensor s8). Ambient temperature + humidity di Phase 3 simulator entrano come **operating condition** addizionali (`op_setting_2`, `op_setting_3`). Mapping documentato in `packages/sft-ml/src/sft_ml/cmapss/feature_map.py` con riferimento PHM 2008 schema + textile sensor mapping table. **Perché:** soddisfa success criterion #1 ("feature set includes ambient T/H") senza ri-training cross-domain ambiguo. **Rejected:** Retrain con feature textile da zero (perde transfer-learning value dal dataset NASA), Hybrid pretrain + fine-tune (pipeline 2-step troppo complesso PoC).

- **D-PM-04 — Trigger event-driven da AnomalyDetector + RUL in cycles equivalenti.** Pattern: AnomalyDetector Phase 6 emette alert su `audit.actions` con `decision='auto'` e `severity` payload; PredictiveMaintenance consumer NATS subject `maintenance.predict.<asset_id>` (publish-subscribe loose coupling preferito vs supervisor routing esplicito — da confermare in research). Output Pydantic:
  ```python
  class RULEstimate(BaseModel):
      model_config = {"frozen": True, "extra": "forbid"}
      estimate_id: str  # UUID4
      asset_id: str
      rul_cycles: int  # cicli equivalenti C-MAPSS
      confidence_band_lower: int
      confidence_band_upper: int
      health_index: float  # [0..1]
      recommended_action: str | None  # HITL message se health_index < 0.3
      triggered_by_action_id: str | None  # link audit chain AD → PM
      model_version: str  # es. "ridge-fd001-fd003-v1.0"
      created_at: datetime
  ```
  HITL supervisor su `health_index < 0.3`. Audit `Decision.AUTO + ActionType.RUL_ESTIMATE`. **Perché:** allinea event-driven con investimento Phase 6 AnomalyDetector, audit chain trasparente, recursion_limit gestito dal supervisor. **Rejected:** Cron periodico via agents-scheduler (overhead infra non giustificato quando AnomalyDetector è già il trigger naturale), API on-demand only (perde proactive alerting).

### RCASpecialist

- **D-RCA-01 — Form-based 5-Why fixed schema, citation obbligatoria per step.** Pydantic schema:
  ```python
  class WhyStep(BaseModel):
      model_config = {"frozen": True, "extra": "forbid"}
      question: str
      answer: str
      citations: list[RagCitation]  # min_length=1
      confidence: float  # [0..1]

  class RCAChain(BaseModel):
      model_config = {"frozen": True, "extra": "forbid"}
      chain_id: str  # UUID4
      problem_statement: str
      why_1: WhyStep
      why_2: WhyStep
      why_3: WhyStep
      why_4: WhyStep
      why_5: WhyStep
      root_cause: str
      corrective_action_recommendation: str
      downtime_event_id: str | None  # link a downtime_events
      created_at: datetime
  ```
  LLM riempie ogni WhyStep, validator post-LLM enforce: 5 step esatti + `len(citations) >= 1` per step + `source_uri` non-null in ogni citation. Re-prompt fino a 2 retry se schema fails (mirror Phase 6 D-QI-02 pattern). **Perché:** match success criterion #2 letterale ("5-Why chain"), deterministic + audit-friendly, EvidencePanel Phase 10 render facile, validation forte previene LLM hallucination su citation (mitigation T-V6-llm-hallucination Phase 6). **Rejected:** Free-chain (meno deterministic, audit difficile), Hybrid LLM+validator retry-loop (latency variabile).

- **D-RCA-02 — Always supervisor HITL (literal success criterion #2).** Ogni `corrective_action_recommendation` passa per HITL tier `supervisor` via `escalate_to_supervisor` tool (Phase 6 D-OA-04 / D-X HITL tools). Audit `Decision.HITL_SUPERVISOR + ActionType.RCA_CHAIN`. **Perché:** match preciso del success criterion #2 ("routes corrective action to supervisor-level HITL"); coerenza con la safety posture del PoC; no ambiguità su escalation policy. **Rejected:** Severity-based mirror Phase 6 (success criterion dice letteralmente 'supervisor', re-interpretazione richiederebbe re-allineamento con domain expert), Hybrid floor+escalate (chain troppo lunga).

### MaintenanceCoach

- **D-MC-01 — Async LangGraph thread con checkpoint cross-shift.** Ogni intervention = 1 LangGraph thread con state persistito in PG via `langgraph_checkpoints` (riuso migration 005 Phase 4). Schema thread state: `{intervention_id, asset_id, sop_id, technician_id, current_step, completed_steps: list[StepReport], messages, mttr_start: datetime, mttr_end: datetime | None}`. Technician può pausare a step N e tornare (anche dopo shift handover), il coach legge dal checkpoint e riprende dal punto preciso. MTTR calcolato come `thread.mttr_end - thread.mttr_start` (effettivo elapsed time incluso pause; "active work time" tracciato separatamente da `completed_steps[*].duration_minutes`). **Perché:** match realistic intervention flow (interventi tessili durano ore-giorni con multiple pause), audit completo via LangGraph checkpoint history, sopravvive a restart container, riusa investimento Phase 4. **Rejected:** Sync ReAct single-shot (session times out su intervention multi-ora, MTTR perso), Stateless step-by-step (perde context conversazionale, prompt deve replay history a ogni call).

- **D-MC-02 — Tool dedicato `request_help(reason, context)` per escalation esplicita.** Nuovo tool in `packages/sft-agents/src/sft_agents/tools/hitl.py` (estende toolbox Phase 6 D-OA-04). Il LLM lo invoca quando rileva keyword tecnico ("aiuto", "non ci riesco", "help", "stuck", "blocked") o richiesta esplicita dal technician. Il tool wrappa internamente `escalate_to_supervisor` con payload `{intervention_id, current_step, reason, technician_context}`. Audit `Decision.HITL_SUPERVISOR + ActionType.COACH_STEP` con marker `escalation_trigger: 'technician_request'`. Prompt system del Coach include esempi bilingue (IT + EN) di keyword detection. **Perché:** esplicito + auditable (match success criterion #3 "escalates when technician requests it"), riusa pattern Phase 6 senza duplicare logica, tool dedicato semplifica test isolation. **Rejected:** Auto-trigger su step timeout (timeout estimate vario, falsi positivi su technician junior — può emergere Phase 11 se metrics lo giustificano), Marker testuale 'CONTACT_SUPERVISOR' nel response (parsing fragile).

### DowntimeAnalyzer

- **D-DA-01 — Sim-textile downtime_event_generator + PG event store.** Estensione sim-textile con `downtime_event_generator.py` (mirror del `quality_event_generator.py` di 06-09): emette stochastic downtime events su NATS subject `maintenance.downtime.<asset_id>` con payload Pydantic `{event_id, asset_id, reason_code, duration_min, severity, work_order_id?, dye_lot_id?, source: 'simulator', timestamp}`. DowntimeAnalyzer ha consumer JetStream durable `da-consumer` + persiste ogni event in nuova tabella PG `maintenance.downtime_events` (nuova migration `008_create_downtime_events.sql` con TimescaleDB hypertable on `timestamp`). Hybrid live (sim stream) + historical (PG queryable). **Perché:** coerente con Phase 6 D-QI-01 dual-source pattern, demo continuous monitoring realistic, Pareto multi-shift via SQL su PG, success criterion #4 ("calculates OEE + Pareto") soddisfatto con dati reali del simulatore. **Rejected:** Solo PG seed sintetico (no live stream debole per demo), Solo in-memory aggregation (rebuild su restart, no Pareto multi-shift).

- **D-DA-02 — OEE.Quality cross-cluster: audit.actions QUALITY_VERDICT + sim metrics fallback.** Query SQL su `audit.actions WHERE action_type='QUALITY_VERDICT' AND created_at BETWEEN window_start AND window_end`, estrae da `evidence_panel` payload `good_parts / total_parts` per finestra; aggrega per `asset_id`. Se gap dati (es. ops cluster offline / QualityInspector non gira da X minuti), fallback automatico a sim-textile production metrics (`good_meters / total_meters` da `production_state.py` di Phase 6 06-09). Cross-cluster cohesion + resilience. **Perché:** OEE.Q riflette le verdict reali degli agent (single source of truth audit-driven), fallback evita brittle behavior, audit chain trasparente per ogni window. **Rejected:** Solo audit strict (brittle quando ops cluster offline), Solo sim metrics (2 sorgenti di verità divergenti).

- **D-DA-03 — TimescaleDB continuous aggregate `maintenance.oee_hourly` + on-demand query API.** Materializza OEE in TimescaleDB continuous aggregate `maintenance.oee_hourly` (window 1h, refresh policy 5min) aggiornato live; nuova migration `008_create_downtime_events.sql` include `CREATE MATERIALIZED VIEW maintenance.oee_hourly WITH (timescaledb.continuous) AS ...`. DowntimeAnalyzer espone endpoint `POST /v1/agents/downtime-analyzer/report` con body `{window_start, window_end, by_asset?: bool, top_n_pareto?: int}`. Output:
  ```python
  class OEEReport(BaseModel):
      model_config = {"frozen": True, "extra": "forbid"}
      window_start: datetime
      window_end: datetime
      availability: float  # [0..1]
      performance: float  # [0..1]
      quality: float  # [0..1]
      oee: float  # product of the 3
      by_asset: dict[str, OEEMetrics] | None
      pareto: list[ParetoEntry]
      report_id: str
      generated_at: datetime

  class ParetoEntry(BaseModel):
      model_config = {"frozen": True, "extra": "forbid"}
      reason_code: str
      total_downtime_min: int
      occurrence_count: int
      cumulative_percent: float
  ```
  EvidencePanel UI Phase 10 render diretto. JSON serializzabile. Audit `Decision.AUTO + ActionType.OEE_REPORT`. **Perché:** scala a multi-shift / multi-day window senza ricomputo costoso a ogni query (PoC ha già 30 asset × 5 sensor 1Hz = 150 sample/s); riusa pattern hypertable Phase 3. **Rejected:** Pydantic + Pareto on-demand from raw events (ricomputo costoso > 1 shift), Markdown report only (parsing client-side).

### Maintenance Event Taxonomy (MNT-05) — pre-decisa

- **D-MNT-TAX — Estendere failure_modes.yaml esistente con maintenance fields.** Schema esteso (additive, no breaking change):
  ```yaml
  - id: broken_end
    # ... existing fields (name_it, name_en, asset_families, parts, severity, hitl_tier, setup_minutes, severity_band) ...
    # NEW Phase 7 fields:
    maintenance:
      reason_code: WEAVING-BE-001  # taxonomy MNT-05 stable code
      mttr_target_minutes: 30      # SLO per benchmarking
      intervention_steps_sop_id: SOP-LOOM-001  # link a SOP corpus Phase 2/5
      preventive_check_interval_hours: 168  # opzionale, per future MaintenanceScheduler Phase 9
  ```
  Loader Pydantic esteso (`packages/sft-domain/src/sft_domain/failure_modes/models.py`). Validator CI esistente esteso per verificare `reason_code` unicità + `intervention_steps_sop_id` esiste in corpus Phase 5. Documentazione MNT-05 in `docs/agents/maintenance/event-taxonomy.it.md` + `.en.md` (mirror pattern 06-14). **Perché:** evita proliferazione di YAML separati (single source of truth domain), naturale dopo Phase 5 D-65 + Phase 6 D-QI-03 (registry già esiste), additive non rompe consumer Phase 6. **Rejected:** Nuovo file `maintenance_taxonomy.yaml` (duplica concept con failure_modes), Two-layer (over-engineering PoC).

## Audit Enum Extension (mirror Phase 6 D-AE-01)

- **D-AE-MNT — Migration `009_extend_audit_mnt.sql`.** Pattern DROP+ADD CHECK constraint per estendere `audit.actions.action_type`:
  - Nuovi `ActionType`: `RUL_ESTIMATE`, `RCA_CHAIN`, `COACH_STEP`, `DOWNTIME_VERDICT`, `OEE_REPORT`
  - Decision values esistenti (`AUTO`, `HITL_SUPERVISOR`, `HITL_MANAGER`, `SUPPRESSED`, etc.) sufficienti — nessun nuovo Decision needed
  - Testcontainers test mirror Phase 6 `test_migration_007.py` (18 test pattern)
  - Python enum `ActionType` esteso in lockstep in `packages/sft-agents/src/sft_agents/models/enums.py`

## Cross-Cluster Wiring Implementation Notes

- **AnomalyDetector → PredictiveMaintenance trigger:** raccomandazione (da confermare in research) di usare NATS publish-subscribe loose coupling: AnomalyDetector emette su `maintenance.predict.<asset_id>` quando alert severity >= major; PredictiveMaintenance ha consumer durable `pm-consumer`. Audit chain: AD audit row `Decision.AUTO + ActionType.ANOMALY_ALERT` → PM audit row con `triggered_by_action_id` link. Pro: zero modifiche a Phase 6 AnomalyDetector code (solo nuovo NATS subject publish da aggiungere).

- **DowntimeAnalyzer ← QualityInspector reads:** read-only su `audit.actions`, no schema change. Performance: indice esistente su `(action_type, created_at)` sufficiente per window query 1h-24h. Documentare in PLAN.md come "non-blocking dependency".
</decisions>

<canonical_refs>
## Canonical References (MANDATORY reading per researcher e planner)

**Project-level:**
- `.planning/PROJECT.md` — core value + key decisions registry
- `.planning/REQUIREMENTS.md` — MNT-01..06 specs (lines 92-96)
- `.planning/ROADMAP.md` — Phase 7 entry (line 157), success criteria (lines 161-167)

**Prior phase contexts (CRITICAL — cross-cluster wiring depends on these):**
- `.planning/phases/03-it-ot-simulation-layer/03-CONTEXT.md` — sim-textile architecture, NATS subjects, TimescaleDB hypertable pattern, query_timescale tool
- `.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md` — LangGraph subgraph pattern, HITL tier system, langgraph_checkpoints PG persistence (migration 005), safety middleware
- `.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md` — rag_search + traverse_graph tools, ACL via user_roles, failure_modes.yaml registry D-65
- `.planning/phases/06-agents-operations-production/06-CONTEXT.md` — cluster subgraph pattern (D-X OPS routing), HITL tools (D-OA-04 escalate_to_supervisor, log_event), audit enum extension pattern (D-AE-01 migration 007 model), mock LLM backend (D-X-01), sim-textile extension pattern (D-QI-04 production_state, 06-09 quality_event_generator), scheduler service (06-11 agents-scheduler), failure_modes.yaml hitl_tier extension (D-QI-03)
- `.planning/phases/06-agents-operations-production/06-VERIFICATION.md` — Phase 6 verification status (3 outstanding items: psql migration push, real-LLM smoke, HITL UI)

**Codebase references (researcher must inspect):**
- `packages/sft-domain/src/sft_domain/failure_modes.yaml` — extension target per D-MNT-TAX
- `packages/sft-domain/src/sft_domain/failure_modes/models.py` — Pydantic loader to extend
- `packages/sft-agents/src/sft_agents/runtime/clusters.py` — `build_ops_subgraph` pattern to mirror with `build_maintenance_subgraph`
- `packages/sft-agents/src/sft_agents/tools/hitl.py` — `escalate_to_supervisor` to extend con `request_help`
- `packages/sft-agents/src/sft_agents/tools/audit.py` — `log_event` pattern
- `packages/sft-agents/src/sft_agents/models/enums.py` — `ActionType` / `Decision` to extend in lockstep with migration 009
- `infra/migrations/timescale/005_create_langgraph_checkpoints.sql` — checkpoint table for MaintenanceCoach reuse
- `infra/migrations/timescale/007_extend_audit_decisions.sql` — model for new migration 009 (DROP+ADD CHECK pattern)
- `simulators/sim-textile/src/sim_textile/quality_event_generator.py` — mirror pattern for `downtime_event_generator.py`
- `simulators/sim-textile/src/sim_textile/production_state.py` — Phase 6 state pattern
- `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py` — agent skeleton pattern to mirror; also emits the alerts that trigger PredictiveMaintenance
- `services/agents-scheduler/` — Phase 6 scheduler (Phase 7 does NOT reuse — event-driven trigger preferred over cron)
- `apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py` — pattern per nuovo `routers/maintenance_agents.py`

**External references (per researcher):**
- NASA Prognostics CoE C-MAPSS dataset (PHM 2008 Data Challenge): Saxena, A. et al. (2008) "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation"
- Documentation: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ (FD001 + FD003)
- ISO 14224 (Reliability data collection in process industries) — riferimento per taxonomy MNT-05 (NOT a hard requirement but useful reference for reason_code naming convention)
- OEE methodology — standard textile manufacturing reference (Nakajima 1988 TPM); not to be re-invented
</canonical_refs>

<code_context>
## Reusable Assets from Prior Phases

**From Phase 3 (sim + IT/OT):**
- `query_timescale` tool — direct reuse per PredictiveMaintenance feature retrieval, DowntimeAnalyzer historical query
- TimescaleDB hypertable pattern — model per migration 008 `maintenance.downtime_events`
- NATS subject naming convention (`<cluster>.<event_type>.<asset_id>`) — model per `maintenance.downtime.<asset_id>` e `maintenance.predict.<asset_id>`

**From Phase 4 (runtime + HITL):**
- `langgraph_checkpoints` migration 005 + PG persistence — DIRECT REUSE per MaintenanceCoach thread state (D-MC-01)
- Supervisor subgraph + HITL tier system — host del nuovo `build_maintenance_subgraph`
- SafetyInterlockMiddleware — disponibile se RCASpecialist `corrective_action_recommendation` ha safety implication

**From Phase 5 (knowledge):**
- `rag_search` + `traverse_graph` tools — RCASpecialist consumer principale (citation per ogni WhyStep)
- `failure_modes.yaml` registry + Pydantic loader — extension target D-MNT-TAX
- BGE-M3 cross-lingual retrieval — utile per MaintenanceCoach prompt IT/EN

**From Phase 6 (ops):**
- `build_ops_subgraph` (clusters/ops) — mirror pattern per `build_maintenance_subgraph`
- `escalate_to_supervisor` + `log_event` tools — RCASpecialist + Coach + DowntimeAnalyzer riusano direct
- `LogEventTool` audit writer — pattern per audit row writing
- `MockReplayChatModel` (06-03) — DIRECT REUSE per test E2E deterministic (mirror 06-13)
- `production_state.py` + `quality_event_generator.py` (06-09) — mirror pattern per `downtime_event_generator.py`
- `RateLimiter` (06-02) — disponibile per DowntimeAnalyzer report rate-limiting se needed (TBD in plan)
- `audit_actions` migration 007 DROP+ADD CHECK pattern — model per migration 009
- `agents-scheduler` (06-11) — NON riusato in Phase 7 (event-driven trigger preferred)
- `apps/agents/ops/<agent>/` directory layout — DIRECT mirror per `apps/agents/maintenance/<agent>/`
- `routers/ops_agents.py` (06-12) — pattern per nuovo `routers/maintenance_agents.py`
- `tests/e2e/ops/` scenario pattern (06-13) — mirror per `tests/e2e/maintenance/`
- `docs/docs/agents/operations/` bilingue pattern (06-14) — mirror per `docs/docs/agents/maintenance/`

## New Assets to Build

- **Package nuovo** `packages/sft-ml/` — host del modello scikit-learn RUL (separazione concerns ML pipeline vs agent business logic)
  - `src/sft_ml/cmapss/feature_map.py` — mapping C-MAPSS sensor → textile sensor proxy
  - `src/sft_ml/cmapss/training.py` — training pipeline Ridge/RandomForest (offline, riproducibile)
  - `src/sft_ml/cmapss/inference.py` — inference helper deterministic
  - `data/c-mapss-fd001/` + `data/c-mapss-fd003/` — committato CSV/Parquet
  - `models/ridge-fd001-fd003-v1.0.joblib` — modello pre-trained committato
- **App nuovi** `apps/agents/maintenance/{predictive-maintenance,rca-specialist,maintenance-coach,downtime-analyzer}/`
- **Runtime** `packages/sft-agents/src/sft_agents/runtime/clusters.py` — aggiunge `build_maintenance_subgraph`
- **Tool nuovo** `packages/sft-agents/src/sft_agents/tools/hitl.py` — aggiunge `request_help`
- **Migration** `infra/migrations/timescale/008_create_downtime_events.sql` (table + continuous aggregate)
- **Migration** `infra/migrations/timescale/009_extend_audit_mnt.sql` (ActionType extension)
- **Sim extension** `simulators/sim-textile/src/sim_textile/downtime_event_generator.py`
- **Router** `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py`
- **Docs** `docs/docs/agents/maintenance/` (8 bilingue file + event-taxonomy)
</code_context>

<deferred>
## Deferred Ideas (capture for future phases)

- **Auto-tuning RUL baseline rolling-window** — quando emerge drift osservato in produzione simulata. Deferred Phase 11 (mirror del rationale di Phase 6 D-AD-02).
- **PreventiveMaintenanceScheduler agent** — pianificazione preventive (non solo predittiva): suggerisce intervention windows basate su `preventive_check_interval_hours` di `failure_modes.yaml`. Deferred Phase 9 (Supply Chain cluster — coordina con InventoryManager per spare parts).
- **WorkOrderManager integration** — work_order_id rimane riferimento opaco PoC; integrazione con CMMS reale (SAP PM, IBM Maximo) deferred a deployment industriale post-competition.
- **MaintenanceCoach auto-trigger su step timeout** — falsi positivi alti su technician junior; valutare in Phase 11 con metrics reali da Langfuse.
- **Cross-cluster orchestrator: AnomalyDetector → PredictiveMaintenance → MaintenanceCoach autochain** — chain completo (alert → RUL → coaching procedure suggestion) auto-triggerato; per ora ogni agent gira indipendente. Deferred Phase 9 (cross-cluster orchestration).
- **RUL output in giorni reali** — conversione `rul_cycles → rul_days` via mapping `cycle_to_day` per asset_family. Phase 7 produce solo cycles; conversione UI-side può emergere in Phase 10.
- **Real LSTM port C-MAPSS** — se serve maggiore accuracy in produzione industriale, considerare port PyTorch in dedicated ML service. Deferred post-competition.
- **OEE drill-down per shift / per operator** — Phase 7 produce OEE per asset; drill-down per shift/operator può emergere in Phase 10 (UI) o Phase 11 (analytics).
</deferred>

<constraints>
## Locked Constraints

- **No torch / PyTorch** in Phase 7. ML scope limitato a scikit-learn (Ridge / RandomForest).
- **No nuovo file taxonomy YAML** — failure_modes.yaml è il single source of truth, esteso additively.
- **No cron schedule for PredictiveMaintenance** — event-driven da AnomalyDetector è la modalità primaria.
- **HITL routing RCASpecialist = always supervisor** — literal interpretation di success criterion #2; nessuna severity branching.
- **No modifications a Phase 6 agents/code** — cross-cluster wiring (AD→PM, DA←QI audit) si aggiunge da Phase 7 side; Phase 6 emette già su NATS / scrive già audit.
- **All E2E test DETERMINISTIC** — mock LLM backend + `random_state` fissato per scikit-learn + LangGraph checkpoint replay riproducibile.

## Open Questions (per researcher)

1. **Best practice NASA C-MAPSS feature mapping cross-domain.** Esiste letteratura su domain adaptation NASA→manufacturing? Quanto è robusto il transfer? (Se troppo poco, fallback documentato a synthetic-only training.)
2. **TimescaleDB continuous aggregate refresh policy.** Su 30 asset × 5 sensor 1Hz, qual è il refresh interval ottimo per `oee_hourly`? 5min default ragionevole o ricalcolare ad-hoc?
3. **LangGraph checkpoint serialization size.** Quanto grande può diventare lo state di un Coach thread su intervention di 4h con 30 step? Limit PG payload?
4. **NATS subject `maintenance.predict.<asset_id>` vs supervisor routing.** Quale dei due pattern è più allineato all'architettura Phase 4 (D-53 hierarchical supervisor)? Decisione finale al planner dopo lettura 04-CONTEXT.md + research.
5. **Validator citation per WhyStep** — la `source_uri` deve esistere fisicamente in PG `documents` table o basta validation di shape? (Decisione: full PG lookup, audit-friendly.)
6. **Scikit-learn model versioning** — joblib serialization compat across Python minor versions? Pin di `joblib==X.Y` necessario in pyproject?
</constraints>
</content>
</invoke>