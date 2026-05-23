# Phase 7 Discussion Log — Agents — Maintenance & Reliability

**Discussed at:** 2026-05-23
**Mode:** discuss (default, single-question turns)
**Areas selected:** RUL model approach, Downtime source + OEE Quality wiring, 5-Why RCA structure, MaintenanceCoach session model
**Areas pre-decided (no discussion):** Maintenance event taxonomy (MNT-05) → extension of existing `failure_modes.yaml`

---

## Area 1 — RUL model approach (PredictiveMaintenance)

### Q1.1 — ML approach
**Options presented:**
1. Heuristic degradation curve per asset_family (Recommended)
2. Lightweight ML model (Ridge / RandomForest) addestrato su NASA C-MAPSS subset
3. Hybrid LLM+analytical (Qwen2.5 + heuristic floor)
4. LSTM port su NASA C-MAPSS direttamente

**User selection:** Lightweight ML model (Ridge/RandomForest) on NASA C-MAPSS subset

**Rationale captured (D-PM-01):** scelta data-driven con citazione esplicita del dataset NASA come richiesto dal success criterion #1, deps leggere (~5-10MB), training pipeline riproducibile in CI, evita LSTM/torch overhead.

### Q1.2 — C-MAPSS dataset subset
**Options presented:**
1. Solo FD001 in repo (Recommended)
2. FD001 + FD003 (multi fault mode)
3. Download lazy on first train

**User selection:** FD001 + FD003 (multi fault mode)

**Rationale captured (D-PM-02):** copertura più realistica con 2 fault families (mechanical wear / dye chamber contamination); ~10MB committato in `packages/sft-ml/data/`; deterministic CI offline.

### Q1.3 — Feature mapping C-MAPSS → textile
**Options presented:**
1. Train su C-MAPSS pure, infer su feature aggregate proxy (Recommended)
2. Retrain con feature textile da zero
3. Hybrid pretrain + fine-tune

**User selection:** Train su C-MAPSS pure, infer su textile sensor proxies (Recommended)

**Rationale captured (D-PM-03):** preserva transfer-learning value dal NASA dataset; ambient T/H entrano come `op_setting_2/3` per soddisfare success criterion #1 ("feature set includes ambient T/H"); mapping documentato in `packages/sft-ml/src/sft_ml/cmapss/feature_map.py`.

### Q1.4 — Trigger pattern + output format
**Options presented:**
1. Cron periodico via agents-scheduler (riuso 06-11) + RUL in cycles (Recommended)
2. API on-demand + RUL in giorni reali
3. Event-driven su anomaly threshold da AnomalyDetector + RUL in cycles

**User selection:** Event-driven su anomaly threshold da AnomalyDetector + RUL in cycles

**Rationale captured (D-PM-04):** cross-cluster wiring esplicito Phase 6 → Phase 7 (AnomalyDetector emette su `maintenance.predict.<asset_id>`), audit chain trasparente con `triggered_by_action_id`, no scheduler overhead quando AnomalyDetector è già il trigger naturale. **Cross-cluster impact:** richiede coordinamento documentato in PLAN.md (no modifiche a Phase 6, solo nuovo NATS publish da AD side).

---

## Area 2 — Downtime source + OEE Quality wiring (DowntimeAnalyzer)

### Q2.1 — Downtime event source
**Options presented:**
1. Sim-textile downtime_event_generator (mirror 06-09) + PG event store (Recommended)
2. Solo PG seed sintetico (YAML → migration script)
3. Solo sim-textile continuous stream (in-memory)

**User selection:** Sim-textile downtime_event_generator + PG event store (Recommended)

**Rationale captured (D-DA-01):** hybrid live (sim stream) + historical (PG) coerente con Phase 6 D-QI-01 dual-source pattern; nuova migration 008 con TimescaleDB hypertable; Pareto multi-shift via SQL.

### Q2.2 — OEE.Quality source
**Options presented:**
1. Cross-cluster: legge audit.actions del QualityInspector + sim metrics fallback (Recommended)
2. Solo audit (strict cross-cluster, no fallback)
3. Solo sim metrics (cluster isolation)

**User selection:** Cross-cluster: audit.actions QUALITY_VERDICT + sim metrics fallback (Recommended)

**Rationale captured (D-DA-02):** OEE.Q riflette le verdict reali degli agent (single source of truth audit-driven); fallback evita brittle behavior; audit chain trasparente.

### Q2.3 — OEE output format
**Options presented:**
1. OEEReport Pydantic + ParetoEntry list (Recommended)
2. Markdown report + structured KPI dict
3. TimescaleDB continuous aggregate + on-demand query

**User selection:** TimescaleDB continuous aggregate + on-demand query

**Rationale captured (D-DA-03):** scala a multi-shift/multi-day senza ricomputo; refresh policy 5min (open question per researcher); endpoint `POST /v1/agents/downtime-analyzer/report` con output Pydantic `OEEReport` + `list[ParetoEntry]`; nuova migration 008 include `CREATE MATERIALIZED VIEW maintenance.oee_hourly`.

---

## Area 3 — 5-Why RCA structure (RCASpecialist)

### Q3.1 — Schema rigidity
**Options presented:**
1. Form-based: 5 campi fissi con citation obbligatoria per step (Recommended)
2. Free-chain LLM con validation minima
3. Hybrid LLM-generated + validator re-prompt loop

**User selection:** Form-based 5 fixed fields with mandatory citation per step (Recommended)

**Rationale captured (D-RCA-01):** deterministic + audit-friendly; EvidencePanel render facile; validation forte previene LLM hallucination su citation (mitigation T-V6-llm-hallucination da Phase 6); pattern Pydantic `WhyStep { question, answer, citations[min_length=1], confidence }`.

### Q3.2 — HITL routing
**Options presented:**
1. Always supervisor (literal success criterion) (Recommended)
2. Severity-based mirror Phase 6 D-QI-03
3. Hybrid: supervisor floor + escalate to manager on high

**User selection:** Always supervisor (literal success criterion)

**Rationale captured (D-RCA-02):** match preciso del wording success criterion #2 ("routes corrective action to supervisor-level HITL"); no ambiguità su escalation policy; semplice da spiegare.

---

## Area 4 — MaintenanceCoach session model

### Q4.1 — Session pattern
**Options presented:**
1. Async LangGraph thread checkpoint resumable cross-shift (Recommended)
2. Sync ReAct single-shot
3. Stateless step-by-step (call API separata per step)

**User selection:** Async LangGraph thread checkpoint resumable cross-shift (Recommended)

**Rationale captured (D-MC-01):** realistic per intervention multi-ora/multi-giorno; riuso `langgraph_checkpoints` migration 005 Phase 4; MTTR = `thread.mttr_end - thread.mttr_start`; sopravvive a restart container; technician può pausare a step N e tornare ore dopo (anche post shift handover).

### Q4.2 — Escalation trigger
**Options presented:**
1. Esplicito via tool `request_help` invocato dal LLM su technician keyword (Recommended)
2. Esplicito + auto-trigger su step timeout
3. Solo esplicito con marker testuale 'CONTACT_SUPERVISOR'

**User selection:** Esplicito via tool `request_help` invocato dal LLM su technician keyword (Recommended)

**Rationale captured (D-MC-02):** match success criterion #3 ("escalates when technician requests it"); nuovo tool in `packages/sft-agents/src/sft_agents/tools/hitl.py` (estende toolbox 06); wrappa `escalate_to_supervisor` esistente; prompt include esempi bilingue IT/EN di keyword detection.

---

## Pre-decided (no discussion)

### Maintenance event taxonomy (MNT-05)

**Decision (D-MNT-TAX):** estendere `failure_modes.yaml` esistente con campi maintenance-specific (`reason_code`, `mttr_target_minutes`, `intervention_steps_sop_id`, `preventive_check_interval_hours`). No nuovo file separato.

**Rationale:** naturale dopo Phase 5 D-65 (failure_modes registry creation) e Phase 6 D-QI-03 (hitl_tier extension); additive non rompe consumer Phase 6; single source of truth domain; documentazione bilingue in `docs/docs/agents/maintenance/event-taxonomy.{it,en}.md` mirror pattern 06-14.

### Audit enum extension

**Decision (D-AE-MNT):** migration `009_extend_audit_mnt.sql` mirror del pattern Phase 6 D-AE-01 (07-extend_audit_decisions.sql). Nuovi `ActionType`: `RUL_ESTIMATE`, `RCA_CHAIN`, `COACH_STEP`, `DOWNTIME_VERDICT`, `OEE_REPORT`. No nuovi `Decision` values needed.

**Rationale:** pattern provato in Phase 6 (testcontainers 18/18); python enum lockstep; gating prerequisite per scrittura audit dei 4 nuovi agent.

---

## Deferred Ideas (capture for backlog)

- Auto-tuning RUL baseline rolling-window (Phase 11)
- PreventiveMaintenanceScheduler agent (Phase 9, coordinato con InventoryManager)
- WorkOrderManager integration con CMMS reale (post-competition)
- Coach auto-trigger su step timeout (Phase 11 con metrics reali Langfuse)
- Cross-cluster orchestrator AD→PM→Coach autochain (Phase 9)
- RUL output in giorni reali via mapping `cycle_to_day` per asset_family (Phase 10 UI)
- Real LSTM port C-MAPSS in dedicated ML service (post-competition)
- OEE drill-down per shift / per operator (Phase 10/11)

---

## Open Questions for Researcher

1. Best practice NASA C-MAPSS feature mapping cross-domain (transfer learning robustness).
2. TimescaleDB continuous aggregate refresh policy ottimale (5min default vs ad-hoc).
3. LangGraph checkpoint serialization size limit per Coach thread.
4. NATS subject vs supervisor routing — quale pattern più allineato a Phase 4 D-53.
5. Validator citation `source_uri` — full PG lookup vs shape-only validation.
6. Scikit-learn model versioning + joblib compat cross Python minor.
</content>
</invoke>