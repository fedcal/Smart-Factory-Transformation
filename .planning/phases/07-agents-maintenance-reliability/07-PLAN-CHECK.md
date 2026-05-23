---
phase: 7
phase_name: Agents — Maintenance & Reliability
checked_at: "2026-05-23"
checker: gsd-plan-checker
plan_count: 13
verdict: NEEDS_REVISION
revision_loop: 1
---

# Phase 7 Plan-Check Report

## Verdict

**NEEDS_REVISION** — 2 BLOCKERS + 6 WARNINGS.

I 13 PLAN.md coprono in modo solido tutti i 6 requirements (MNT-01..06) e i 5 success criteria del ROADMAP. Il DAG è valido. Il rispetto delle decisioni di CONTEXT.md è puntuale (D-PM-01..04, D-RCA-01/02, D-MC-01/02, D-DA-01..03, D-MNT-TAX, D-AE-MNT tutte ancorate verbatim a task specifici). Open Q1 risolta esplicitamente in 07-06 con pattern + rationale. Tuttavia ci sono **2 blockers gated dall'infrastruttura del processo gsd** e diverse aree di rischio operativo che vanno chiuse prima dell'execute.

---

## Coverage Matrix

### Requirements MNT-01..06 vs Plans

| Req | Phase Goal Coverage | Plans (FE field) | Plans (task content) | Status |
|-----|---------------------|------------------|----------------------|--------|
| MNT-01 | PM RUL via C-MAPSS adattato + ambient T/H | 07-00, 07-03, 07-06, 07-10, 07-12 | 07-03 (sft-ml + dataset + joblib), 07-06 (agent + consumer + AD hook), 07-10 (HTTP), 07-12 (E2E happy/degraded/failure) | COVERED |
| MNT-02 | RCA 5-Why + citazioni + always-supervisor | 07-00, 07-04, 07-07, 07-10, 07-12 | 07-04 (build_maintenance_subgraph), 07-07 (RCAChain + validator + always-supervisor), 07-12 (3 scenarios) | COVERED |
| MNT-03 | Coach step-by-step + checkpoint + MTTR + request_help | 07-00, 07-04, 07-08, 07-10, 07-12 | 07-04 (RequestHelpTool), 07-08 (CoachThreadState + mttr + AsyncPostgresSaver), 07-12 (multi-turn) | COVERED |
| MNT-04 | DA OEE A×P×Q + Pareto + downtime store | 07-00, 07-01, 07-05, 07-09, 07-10, 07-12 | 07-05 (migration 008 + generator), 07-09 (oee + pareto + repository + consumer), 07-12 (audit + simfallback) | COVERED |
| MNT-05 | Maintenance event taxonomy bilingual + cross-agent | 07-00, 07-02, 07-05, 07-07, 07-11 | 07-02 (failure_modes.yaml extension + validator), 07-05 (generator consuma reason_code), 07-07 (downtime_event_id), 07-11 (docs bilingue) | COVERED |
| MNT-06 | Asset registry + event store integration + audit chain | 07-00, 07-06, 07-09, 07-12 | 07-09 (validate_asset_exists), 07-06 (triggered_by_action_id chain), 07-12 (SQL JOIN E2E asserzione) | COVERED |

### Success Criteria (ROADMAP lines 161-167) vs Plans

| # | Success Criterion | Locked in | Verifying Plan |
|---|-------------------|-----------|----------------|
| 1 | PM stima RUL (loom/spindle/warper) C-MAPSS adapted con ambient T/H | D-PM-01..03 | 07-03 (feature_map ambient → op_setting_2/3), 07-06 (agent), 07-12 PM scenarios |
| 2 | RCA 5-Why + citations + supervisor HITL | D-RCA-01/02 | 07-07 (validator + always-supervisor) + 07-12 RCA scenarios |
| 3 | Coach SOP retrieve + MTTR + escalates when technician requests | D-MC-01/02 | 07-08 (mttr.py + request_help) + 07-12 coach degraded scenario |
| 4 | DA OEE (A×P×Q) + Pareto | D-DA-01..03 | 07-05 + 07-09 (oee.py + pareto.py) + 07-12 DA happy |
| 5 | Maintenance event taxonomy documented + used cross-agent | D-MNT-TAX | 07-02 (data) + 07-11 (docs) + 07-05/07/09 (cross-agent consumption) |

---

## Dimension Results

### Dimension 1: Requirement Coverage — **PASS**

Ogni MNT-01..06 mappato a ≥1 task in ≥1 PLAN. Nessuna requirement orfana. Il roadmap success criterion #5 (event-taxonomy used consistently cross-agent) è enforced anche da test in 07-11 Task 2 (test_evidence_panel.py docs↔code lockstep).

### Dimension 2: Task Completeness — **PASS**

Tutti i task ispezionati hanno: `<files>`, `<action>`, `<verify>` (con `<automated>`), `<done>`. Le `<read_first>` sections sono ricche e referenziano canonical analogs Phase 4/5/6. I 4 task di tipo `checkpoint:human-action`/`checkpoint:human-verify` (07-01 Task 3, 07-03 Task 1, 07-05 Task 2) hanno `<what-built>`, `<how-to-verify>`, `<resume-signal>` come da template.

### Dimension 3: Dependency Correctness — **PASS**

DAG validato:
```
Wave 0: 07-00 (depends_on: [])
Wave 1: 07-01, 07-02, 07-03 (depends_on: ["07-00"])
Wave 2: 07-04 (depends_on: ["07-00","07-01"]), 07-05 (depends_on: ["07-00","07-02"])
Wave 3: 07-06 (deps: ["07-00","07-01","07-03","07-04"]), 07-07 (deps: ["07-00","07-01","07-02","07-04"]),
        07-08 (deps: ["07-00","07-01","07-04"]), 07-09 (deps: ["07-00","07-01","07-04","07-05"])
Wave 4: 07-10 (deps: ["07-06","07-07","07-08","07-09"]), 07-11 (deps: ["07-06","07-07","07-08","07-09"])
Wave 5: 07-12 (deps: ["07-00","07-03","07-06","07-07","07-08","07-09","07-10"])
```

- No cicli. No forward references. Wave number = max(deps.wave)+1 in tutti i casi.
- 07-09 ↔ 07-06 condividono `MAINTENANCE_STREAM` JetStream: race-condition annotato + mitigato via `add_stream(if_not_exists)` in entrambe le consumer routines.

### Dimension 4: Key Links Planned — **PASS**

Tutti i `key_links` sono coperti da task action. Verificato a campione:
- `mnt-predictive-maintenance/agent.py → joblib`: 07-06 Task 2 implementa `load_pretrained_model` con `joblib.load`. ✓
- `mnt-rca-specialist/validators.py → PG documents`: 07-07 Task 2 implementa SQL ClassVar parameterized. ✓
- `mnt-maintenance-coach/agent.py → langgraph_checkpoints`: 07-08 Task 3 implementa `AsyncPostgresSaver`. ✓
- `downtime-analyzer → audit.actions QUALITY_VERDICT`: 07-09 Task 2 implementa `QualityVerdictReader`. ✓
- `AnomalyDetector → maintenance.predict.<asset_id>`: 07-06 Task 3 estende AD agent (Open Q1 Option a). ✓
- `docs/agents/maintenance/*.md → metadata.py`: 07-11 Task 1+2 garantisce lockstep via test_evidence_panel. ✓

### Dimension 5: Scope Sanity — **PASS (con warning su 07-09 e 07-12)**

| Plan | Tasks | Files | Note |
|------|-------|-------|------|
| 07-00 | 3 | ~50 stub | scaffold, OK |
| 07-01 | 3 (incluso checkpoint) | 4 | OK |
| 07-02 | 3 | 4 | OK |
| 07-03 | 4 (incluso checkpoint) | 19 (data files + model) | Borderline, ma data files sono blob non-codice |
| 07-04 | 2 | 4 | OK |
| 07-05 | 4 (incluso checkpoint) | 5 | OK |
| 07-06 | 4 | 12 (+1 modify AD) | OK |
| 07-07 | 3 | 10 | OK |
| 07-08 | 3 | 11 | OK |
| 07-09 | **4** | **13** | WARNING: scopo ampio (4 sotto-moduli + 4 test). Tracciabile ma denso. |
| 07-10 | 2 | 4 | OK |
| 07-11 | 2 | 14 | Documenti bilingue + 4 test |
| 07-12 | 4 | 22 (12 YAML + 6 JSONL + 4 test + 1 conftest) | WARNING: pacchetto E2E grande ma atomico, mirror diretto di 06-13 |

07-09 (4 task × ~13 file su DA solo) e 07-12 (4 task × 22 file E2E) sono i due plan al limite alto. Entrambi sono mirror diretto di Phase 6 (06-07/06-09 + 06-13) che hanno passato l'esecuzione: scope accettabile ma fragile rispetto al context budget durante l'execute.

### Dimension 6: Verification Derivation — **PASS**

`must_haves.truths` sono user-observable in tutti i 13 plan. Esempi virtuosi:
- 07-08: "MTTR (1800) >> active_work (120) when there are pauses" — testa il comportamento, non l'implementazione.
- 07-09: "OEEReport.quality from audit source (structlog `oee_quality_source_audit`)" — observable + testabile.
- 07-06: "AD audit row's `action_id` == PM audit row's `triggered_by_action_id` verifiable via SQL JOIN" — gold standard.

`artifacts` e `key_links` sono ben tipizzati e fanno reference a path concreti.

### Dimension 7: Context Compliance — **PASS**

Tutte le decisioni LOCKED di CONTEXT.md hanno almeno un task implementante:

| Decision | Plan/Task | Verifica |
|----------|-----------|----------|
| D-PM-01 (Ridge/RF scikit-learn) | 07-03 Task 3 | OK — sklearn>=1.7, no torch |
| D-PM-02 (C-MAPSS FD001+FD003 committato) | 07-03 Task 3 | OK — 6 file in `packages/sft-ml/data/` |
| D-PM-03 (textile feature mapping) | 07-03 Task 3 + 07-RESEARCH Pattern 2 | OK — `TEXTILE_TO_CMAPSS_FEATURE_MAP` + `OP_SETTING_MAP` |
| D-PM-04 (event-driven AD trigger + RULEstimate + HITL on health<0.3) | 07-06 Task 1-3 | OK — schema verbatim + Pitfall §3 + audit chain |
| D-RCA-01 (form-based 5-Why + citation per step) | 07-07 Task 2 (models.py) | OK — schema verbatim |
| D-RCA-02 (ALWAYS supervisor) | 07-07 Task 3 (`_resolve_tier` → SUPERVISOR sempre) | OK — `<deviation_rules>` Rule 1 esplicito |
| D-MC-01 (async LangGraph thread + langgraph_checkpoints reuse + MTTR) | 07-08 Task 2-3 | OK — AsyncPostgresSaver |
| D-MC-02 (request_help wraps escalate_to_supervisor + audit marker) | 07-04 + 07-08 | OK |
| D-DA-01 (sim generator + PG event store) | 07-05 Task 3-4 + 07-09 Task 1-2 | OK |
| D-DA-02 (OEE.Q cross-cluster audit + sim fallback) | 07-09 Task 2-3 | OK — entrambi i path + structlog observability |
| D-DA-03 (CAGG + on-demand REST + Pydantic shapes) | 07-05 + 07-09 + 07-10 | OK |
| D-MNT-TAX (extend failure_modes.yaml additive) | 07-02 Task 2 | OK — `maintenance` sub-key opzionale |
| D-AE-MNT (migration 009 + 5 nuovi ActionType + Decision unchanged) | 07-01 Task 1-2 | OK — 6-test matrix + sanity check on Decision |

**Cross-cluster wiring**: 07-06 Open Q1 risolta come Option (a) thin AD extension. Compliant con CONTEXT.md L36-38 ("no modifications to Phase 6 agents/code") interpretato come "no business logic modifications"; aggiunta di kwarg opzionale `nats_client=None` esplicitamente dichiarata additive + Phase 6 contract-preserving. Decisione documentata + razionale verbose in 07-06 `<open_q1_resolution>`. **Accettabile** — è la lettura più ragionevole del vincolo e protetta dal default-None che preserva tutti i test esistenti.

**Deferred Ideas**: nessun plan introduce auto-tuning RUL, PreventiveMaintenanceScheduler, WorkOrderManager CMMS integration, auto-trigger su step timeout, cross-cluster orchestrator AD→PM→Coach autochain, RUL in giorni reali, LSTM PyTorch port, OEE drill-down per shift/operator. ✓

### Dimension 7b: Scope Reduction Detection — **PASS**

Scan delle 13 PLAN.md per linguaggio di scope reduction (`v1`, `static`, `hardcoded`, `placeholder`, `not wired`, `future enhancement`, ecc.):

| Trovato | Plan | Disposizione |
|---------|------|--------------|
| "placeholder" | 07-02 (validator SOP fallback warn-only) | ACCETTABILE — fallback documentato + flag `--strict-sop` per future enforcement; non scope reduction perché il check c'è e diventa hard fail su demand |
| "PoC simplification" | 07-09 (compute_availability planned=window default 100%) | ACCETTABILE — documentato + Phase 11 follow-up esplicito |
| "Future enhancement" | varie sui SHA256 model manifest, drill-down shift/operator, scheduler restart | ACCETTABILE — sono fuori scope del PoC e referenziano deferred list di CONTEXT |
| "best-guess semantic mapping" | 07-03 MODEL_CARD (feature_map non domain-adapted) | ACCETTABILE — è esplicito nel D-PM-03 ("train su C-MAPSS pure, infer su textile sensor proxies") |

NESSUN caso di scope reduction insidioso (es. "implementa D-XX v1") che mascheri sotto-delivery di una decisione locked.

### Dimension 7c: Architectural Tier Compliance — **N/A**

RESEARCH.md non contiene una sezione `## Architectural Responsibility Map`. SKIPPED.

### Dimension 8: Nyquist Compliance

**8e (VALIDATION.md existence)**: PASS — `07-VALIDATION.md` presente.

**8a (Automated verify presence)**: PASS — ogni `<task type="auto">` ha `<verify><automated>`. I 4 checkpoint task non lo richiedono per definizione.

**8b (Feedback latency)**: PASS — i comandi `<automated>` sono o pytest-mirati (sub-30s tipico) o `mkdocs build --strict`. Nessun `--watchAll`. I `-m integration` su testcontainers potrebbero superare 30s ma sotto i 300s per-wave budget di VALIDATION.

**8c (Sampling continuity)**: PASS — ogni wave ha ≥2/3 task con automated verify nella sliding window. Wave 3 (07-06/07/08/09): tutti i 4 plan hanno verify per ogni task. Wave 4 (07-10/07-11): entrambi i plan hanno verify per ogni task.

**8d (Wave 0 completeness)**: PASS — 07-00 crea ~50 file stub coprendo tutti i path referenziati come `MISSING` in 07-VALIDATION.md per-task verification map.

**Tabella sintetica**:

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| 07-00.1-3 | 00 | 0 | pytest collect-only + yaml.safe_load + json.loads | ✓ |
| 07-01.1-2 | 01 | 1 | pytest integration + python -c import smoke | ✓ |
| 07-02.1-3 | 02 | 1 | pytest + python validator | ✓ |
| 07-03.2-4 | 03 | 1 | pytest + MODEL_CARD grep | ✓ |
| 07-04.1-2 | 04 | 2 | pytest sft-agents tests | ✓ |
| 07-05.1,3,4 | 05 | 2 | pytest integration + sim generator | ✓ |
| 07-06.1-4 | 06 | 3 | pytest + AD signature inspect | ✓ |
| 07-07.1-3 | 07 | 3 | pytest models/validators | ✓ |
| 07-08.1-3 | 08 | 3 | pytest mttr + testcontainers checkpoint | ✓ |
| 07-09.1-4 | 09 | 3 | pytest repository/consumer/oee/pareto | ✓ |
| 07-10.1-2 | 10 | 4 | pytest api-gateway + route inventory | ✓ |
| 07-11.1-2 | 11 | 4 | mkdocs --strict + pytest evidence_panel | ✓ |
| 07-12.1-4 | 12 | 5 | yaml/jsonl validation + pytest e2e | ✓ |

Overall: **PASS**. (Nota: 07-VALIDATION.md ha `nyquist_compliant: false` nel frontmatter — andrebbe toggled a true post-verifica.)

### Dimension 9: Cross-Plan Data Contracts — **PASS (con 1 WARNING)**

Verificato che le pipeline condivise siano consistenti:
- DowntimeEvent (07-05 sim) → DA consumer (07-09): contratto Pydantic frozen+extra=forbid identico, severity CHECK constraint doppia validazione (Pydantic + PG).
- AnomalyDetector audit_row.action_id → PM PredictRequest.triggered_by_action_id (07-06): payload JSON encoding consistente, SQL JOIN E2E in 07-12.
- failure_modes.yaml.maintenance.reason_code (07-02) → sim generator reason_code (07-05) → DA Pareto query (07-09) → docs event-taxonomy (07-11): contratto stringa stable, regex `^[A-Z][A-Z0-9-]+$` enforced in tutti i punti di intake.
- QualityInspector EvidencePanel JSONB (Phase 6 06-07) → DA QualityVerdictReader SQL (07-09): **WARNING** — il path JSONB `evidence_panel->'tool_calls'->0->'result'->>'good_parts'` è dichiarato "verify at implementation time" in 07-09 Task 2 read_first. È un contratto cross-fase fragile — se Phase 6 ha messo `good_parts` sotto `args` invece di `result`, l'E2E happy 07-12 DA fallirà al run. Mitigation prevista (test inserts mock QUALITY_VERDICT row, asserts extraction works) è corretta ma rinvia il discovery a Wave 3 — possibile rework loop.

### Dimension 10: CLAUDE.md Compliance — **SKIPPED** (no CLAUDE.md found at repo root).

### Dimension 11: Research Resolution — **BLOCKER**

`07-RESEARCH.md` ha la sezione `## Open Questions` senza il suffisso `(RESOLVED)` né marker `RESOLVED` inline per ognuna delle 5 questions elencate (lines 1143-1168). Il gsd-plan-checker pre-execute richiede questo handshake esplicito. Le questions:

1. AnomalyDetector publish hook esiste? → di fatto risolta in 07-06 `<open_q1_resolution>` come Option (a), ma RESEARCH.md non aggiornato.
2. Continuous aggregate refresh 5min? → confermato da D-DA-03 + 07-05.
3. Coach thread_id senza technician noto → 07-08 Open Q6 risolve naming (`coach-<intervention_id>`), ma la sub-question "nullable technician_id" non è esplicitamente trattata; CoachStartRequest in 07-08 ha `technician_id: str` non-nullable.
4. Single vs joint vs ensemble FD001+FD003 → 07-03 sceglie single joint Ridge baseline + RandomForest opzionale (in `train_random_forest` shipped).
5. OEE.P data source da production_state → 07-09 implementa `compute_performance` con fallback 1.0 + WARN.

Sono **tutte di fatto risolte** nei plan, ma serve aggiornare RESEARCH.md per chiudere il gate. Vedi BLOCKER #1 sotto.

### Dimension 12: Pattern Compliance — **PASS**

07-PATTERNS.md presente, 870+ righe, ben organizzato. Verificato a campione:
- 07-04 task 2 cita verbatim Section 1 lines 68-91 + Section 2 lines 100-138.
- 07-05 task 1 cita Section 9 lines 393-422 SQL skeleton.
- 07-06 task 2-3 cita Section 4 lines 178-238.
- 07-09 cita Section 7 + Section 9 OEE query pattern.
- Shared Pattern A/B/C/E/F/G/H referenziati in tutti i plan tecnici.

Ogni file di codice ha un analog Phase 6 referenziato in `<read_first>` (es. anomaly-detector → predictive-maintenance, quality-inspector → downtime-analyzer, operator-assistant → rca-specialist, ops_agents.py → maintenance_agents.py, 06-09 quality_event_generator → 07-05 downtime_event_generator, 06-13 → 07-12).

---

## Blockers

### BLOCKER #1 — RESEARCH.md `## Open Questions` non marcata RESOLVED

- **Dimension**: research_resolution (#11)
- **File**: `.planning/phases/07-agents-maintenance-reliability/07-RESEARCH.md` line 1143
- **Description**: La sezione `## Open Questions` lista 5 domande senza il suffisso `(RESOLVED)` nell'heading né marker `RESOLVED` inline per ciascuna. Le decisioni sono state prese (Open Q1 in 07-06, Open Q5 in 07-07, Open Q6 in 07-08, Q2/Q4/Q5 in 07-03/05/09) ma il gate pre-execute richiede la chiusura esplicita in RESEARCH.md.
- **Fix**: Marcare la sezione come `## Open Questions (RESOLVED)` e aggiungere per ogni question una linea `RESOLVED: <decisione + plan_id>`. Esempio per Q1:
  > 1. **AnomalyDetector publish hook esiste?** — RESOLVED in 07-06 plan as Option (a): thin extension to AD with optional `nats_client=None` kwarg; preserves Phase 6 contract; documented in 07-06 `<open_q1_resolution>`.
- **Severity rationale**: Senza questa chiusura il plan-checker non può passare la dimensione 11 e il workflow `/gsd:execute-phase` rifiuterà l'entry. Fix mechanico (~5 min) ma blocking.

### BLOCKER #2 — Coach `technician_id` non-nullable contro Open Q3

- **Dimension**: context_compliance + research_resolution
- **File**: `.planning/phases/07-agents-maintenance-reliability/07-08-PLAN.md` (interfaces `CoachStartRequest`, line ~131) + `07-RESEARCH.md` Open Q3 (line 1155-1158)
- **Description**: RESEARCH.md Open Q3 suggerisce "allow nullable `technician_id` + assert non-null prima del primo step" se l'intervention auto-apre da una RCA recommendation senza technician assegnato. 07-08 invece dichiara `technician_id: str` non-nullable in `CoachThreadState` e `CoachStartRequest`. Questo blocca lo scenario "auto-open da RCA" che diventa esplicito nei deferred ideas (Phase 9 cross-cluster orchestrator) ma è già rilevante per il flusso 07-07 RCA → suggested_action → manuale start dell'intervento.
- **Fix**: Una delle due:
  - (A) Mantenere `technician_id: str` non-nullable + documentare esplicitamente in 07-08 SUMMARY che l'auto-open da RCA è fuori scope Phase 7 (technician sempre assegnato via UI Phase 10 OR via api-gateway client che deve sempre passarlo) + chiudere Open Q3 con `RESOLVED: non-nullable, supervisor assegna technician prima del start`.
  - (B) Rendere `technician_id: str | None = None` + aggiungere validator che richiede non-null prima del primo step transition (model_validator con sentinel).
- **Severity rationale**: Decisione di product/UX architectural che cambia signature pubblica del Coach + impatta E2E happy scenario in 07-12 (che oggi assume `technician_id: "TECH-007"` hardcoded). Va chiusa prima dell'execute per evitare rework cross-plan.

---

## Warnings (raccomandate prima dell'execute)

### WARNING #1 — Phase 6 QUALITY_VERDICT JSONB path non verificato pre-execute

- **Dimension**: cross_plan_data_contracts (#9)
- **File**: `07-09-PLAN.md` Task 2 (QualityVerdictReader `_SQL_QUALITY`)
- **Description**: Il path `evidence_panel->'tool_calls'->0->'result'->>'good_parts'` è marcato "verify at implementation time" ma non c'è un task Wave 1-2 che lo accerti. Se Phase 6 ha messo `good_parts` sotto `args` o sotto `output` o ha campi diversi (`good_count` vs `good_parts`), 07-09 Task 2 rework + 07-12 DA happy rework.
- **Fix**: Aggiungere in 07-09 Task 1 una sub-task pre-implementation che apra `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py` e legga la EvidencePanel construction; documentare il path verificato come `<context>` annotation nel plan stesso (non solo `read_first`).

### WARNING #2 — 07-09 scope size borderline (4 task × 13 file)

- **Dimension**: scope_sanity (#5)
- **Description**: Sopra il target di 2-3 task. Mirror diretto di Phase 6 06-07+06-09 (entrambi passati) lo giustifica, ma la complessità DA (consumer + repository + cross-cluster reader + OEE + Pareto + agent + metadata) in un solo plan può forzare context degradation. 4 test module + integration testcontainers.
- **Fix raccomandato**: Non split obbligatorio, ma considerare: spostare `metadata.py` (Task 4 partial) in un commit separato; oppure split in 07-09a (models + repository + consumer) + 07-09b (oee + agent). Se executor sente pressione contesto, può fare il split runtime documentando la deviazione in SUMMARY.

### WARNING #3 — 07-12 scope size borderline (4 task × 22 file)

- **Dimension**: scope_sanity (#5)
- **Description**: Plan E2E con 12 YAML + 6 JSONL + 4 test module + conftest. Mirror 06-13. Total LOC stimato ~2500-3500.
- **Fix raccomandato**: Considerare split logico: Task 1+2 (fixtures only) potrebbero essere un commit/plan separato 07-12a, mentre Task 3+4 (conftest + test modules) sono 07-12b. La dipendenza è puramente sequenziale. Non blocker perché ogni task ha `<verify>` automated indipendente, ma se l'executor incontra context pressure il refactor è già pre-pianificato.

### WARNING #4 — 07-08 Task 3 `AsyncPostgresSaver` constructor signature non confermata

- **Dimension**: cross_plan_data_contracts + task_completeness (#9 + #2)
- **File**: `07-08-PLAN.md` Task 3 behavior bullet
- **Description**: Il plan dice "Default `saver = AsyncPostgresSaver(pool=pool)` ... fallback to `AsyncPostgresSaver.from_conn_string(PG_DSN)` async-with pattern if direct pool injection isn't supported". Questo è un rischio TBD: se il direct pool injection non è supportato in `langgraph-checkpoint-postgres==3.1.0`, l'agent's saver lifecycle diventa per-call (async context manager) cambiando l'invocation pattern.
- **Fix raccomandato**: Aggiungere un task pre-implementation (es. 07-08 Task 1 read_first sub-step) per ispezionare `import langgraph.checkpoint.postgres.aio; help(AsyncPostgresSaver.__init__)` e committare il path scelto prima di Task 3.

### WARNING #5 — 07-10 maintenance-coach `/step` direct-DI bypass cambia routing model

- **Dimension**: context_compliance (#7) + architectural consistency
- **File**: `07-10-PLAN.md` Task 2 action ("Decision: invoke the supervisor for /start ... for /step + /resume use direct DI access to the MaintenanceCoach instance")
- **Description**: Il plan accetta che 2 dei 6 endpoint bypassino il supervisor graph e chiamino direttamente `MaintenanceCoach.step()`/`.resume_after_help()`. Questo crea un'asimmetria di routing nella superficie HTTP: ops e PM/RCA/DA passano dal supervisor, Coach.step/resume no. Documentato in `<deviation_rules>` Rule 4 + commit message, ma è una decisione architetturalmente significativa che merita di essere chiusa in CONTEXT.md (o almeno in 07-PATTERNS.md) e non solo nel SUMMARY post-fact.
- **Fix raccomandato**: Verificare a research time (prima di execute) se il supervisor graph supporta `Command(resume=...)` come state input. Se sì, eliminare il bypass. Se no, documentare la decisione esplicitamente in CONTEXT.md o in PATTERNS.md Section 1 (build_maintenance_subgraph) come pattern di eccezione per agent stateful + langgraph_checkpoints.

### WARNING #6 — 07-11 Task 1 mkdocs i18n plugin convention non verificata

- **Dimension**: task_completeness (#2)
- **File**: `07-11-PLAN.md` Task 1 action ("EN versions resolved via the i18n plugin convention already in use Phase 2/5/6 — verify exact plugin config")
- **Description**: 07-11 assume che `docs/mkdocs.yml` già usi un i18n plugin compatibile con la convenzione `docs/docs/en/...`. Se invece usa nav separato per language o file `.en.md` co-located, lo schema dei `files_modified` di 07-11 (10 file con `docs/docs/agents/` per IT e `docs/docs/en/agents/` per EN) potrebbe essere wrong → mkdocs --strict fallisce.
- **Fix raccomandato**: Aggiungere una pre-task verification step in 07-11 Task 1 (apri `docs/mkdocs.yml` e identifica plugin + path convention) prima di authoring delle 10 pagine.

---

## Per-Plan Notes

| Plan | Status | Notes |
|------|--------|-------|
| 07-00 | ✓ | Wave 0 scaffold robusto, mirror 06-00 |
| 07-01 | ✓ | Migration 009 pattern proven, autonomous:false giusto per dev DB push |
| 07-02 | ✓ | failure_modes.yaml extension additive, validator extended con `--strict-sop` flag |
| 07-03 | ✓ | sft-ml nuovo package + dataset NASA committato + MODEL_CARD; autonomous:false per package legitimacy gate (T-V7-SC) |
| 07-04 | ✓ | Minimal infrastructure plan (2 task), build_maintenance_subgraph + RequestHelpTool |
| 07-05 | ✓ | Migration 008 hypertable + CAGG + simulator generator; autonomous:false per dev DB push |
| 07-06 | ✓ + 1 warn | Open Q1 risolta esplicitamente; PM agent + AD thin extension. Warning su severity literal mapping (`high` vs `major`) da risolvere a impl time |
| 07-07 | ✓ | RCA always-supervisor + Open Q5 full PG lookup; warn-only fallback su pool=None |
| 07-08 | ⚠️ | Vedi BLOCKER #2 (technician_id nullability) + WARNING #4 (AsyncPostgresSaver constructor) |
| 07-09 | ⚠️ | Vedi WARNING #1 (JSONB path) + WARNING #2 (scope size) |
| 07-10 | ⚠️ | Vedi WARNING #5 (Coach direct-DI bypass) |
| 07-11 | ⚠️ | Vedi WARNING #6 (mkdocs i18n convention) |
| 07-12 | ⚠️ | Vedi WARNING #3 (scope size); E2E completo, mock LLM + 6 JSONL ben strutturati |

---

## Recommendation

**Loop iteration #1**: returning to planner with:

1. **MANDATORY (BLOCKER #1)**: Update `07-RESEARCH.md` line 1143:
   - Change heading to `## Open Questions (RESOLVED)`.
   - Append `RESOLVED: ...` to each of the 5 questions with reference to the resolving plan.

2. **MANDATORY (BLOCKER #2)**: Make explicit decision on Coach `technician_id` nullability:
   - Update `07-08-PLAN.md` `<context>` interfaces section + Pydantic schema.
   - Update `07-RESEARCH.md` Open Q3 con RESOLVED.
   - Update `07-12-PLAN.md` coach scenario YAMLs se cambia signature.

3. **RECOMMENDED (Warnings 1, 4, 5, 6)**: Aggiungere pre-implementation verification micro-tasks per:
   - QUALITY_VERDICT JSONB path (07-09 Task 1).
   - AsyncPostgresSaver constructor signature (07-08 Task 1).
   - Supervisor multi-cluster + Command(resume) support (07-10 Task 1).
   - mkdocs.yml i18n plugin convention (07-11 Task 1).
   Le verifications evitano rework Wave 3-4.

4. **OPTIONAL (Warnings 2, 3)**: Considerare split di 07-09 e 07-12 se executor anticipa pressure contesto.

Dopo i fix dei 2 blockers, il plan-set può procedere all'execute. I 6 warnings sono raccomandati ma non blocking.

---

## Structured Issues (YAML)

```yaml
issues:
  - dimension: research_resolution
    severity: blocker
    description: "07-RESEARCH.md ## Open Questions non marcata RESOLVED; 5 questions senza RESOLVED markers inline"
    file: ".planning/phases/07-agents-maintenance-reliability/07-RESEARCH.md"
    line: 1143
    fix_hint: "Cambiare heading in '## Open Questions (RESOLVED)' e aggiungere 'RESOLVED: <decision + plan_id>' per ognuna delle 5 questions"

  - dimension: context_compliance
    severity: blocker
    description: "07-08 dichiara CoachThreadState.technician_id: str (non-nullable) ma RESEARCH.md Open Q3 lascia la nullability aperta; conflitto pre-execute"
    plan: "07-08"
    fix_hint: "Decidere: (A) confermare non-nullable + chiudere Open Q3 con RESOLVED + documentare in 07-08 SUMMARY; oppure (B) rendere Optional + aggiungere model_validator pre-step transition. Aggiornare CoachStartRequest signature consistentemente in 07-10 e 07-12 scenarios."

  - dimension: cross_plan_data_contracts
    severity: warning
    description: "QUALITY_VERDICT JSONB path da Phase 6 non verificato pre-execute; potenziale rework Wave 3 + Wave 5"
    plan: "07-09"
    task: 2
    fix_hint: "Aggiungere sub-task lettura `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py` per accertare path JSONB esatto + documentare in plan <context> annotation"

  - dimension: scope_sanity
    severity: warning
    description: "07-09 ha 4 task + 13 file; borderline target 2-3 task/plan"
    plan: "07-09"
    metrics: {tasks: 4, files: 13}
    fix_hint: "Considerare split 07-09a (models+repository+consumer) + 07-09b (oee+agent+metadata) se executor anticipa context pressure"

  - dimension: scope_sanity
    severity: warning
    description: "07-12 ha 4 task + 22 file (E2E completo). Mirror 06-13 ma denso."
    plan: "07-12"
    metrics: {tasks: 4, files: 22}
    fix_hint: "Considerare split 07-12a (fixtures: 12 YAML + 6 JSONL) + 07-12b (conftest + 4 test modules)"

  - dimension: task_completeness
    severity: warning
    description: "07-08 Task 3 lascia AsyncPostgresSaver constructor signature TBD (pool=pool vs from_conn_string async-with)"
    plan: "07-08"
    task: 3
    fix_hint: "Aggiungere micro-task pre-implementation per ispezionare langgraph.checkpoint.postgres.aio AsyncPostgresSaver __init__ signature + committare il path scelto prima di Task 3"

  - dimension: context_compliance
    severity: warning
    description: "07-10 introduce asimmetria routing: Coach.step + Coach.resume bypassano supervisor graph via direct DI; decisione architetturale non chiusa in CONTEXT/PATTERNS"
    plan: "07-10"
    task: 2
    fix_hint: "Verificare a impl time se supervisor supporta Command(resume=...) come state input. Se sì, eliminare bypass. Se no, documentare in PATTERNS.md Section 1 come pattern di eccezione per agent stateful"

  - dimension: task_completeness
    severity: warning
    description: "07-11 assume mkdocs i18n plugin convention non verificata; potenziale path mismatch su 10 docs files"
    plan: "07-11"
    task: 1
    fix_hint: "Pre-task verification step: aprire docs/mkdocs.yml + identificare plugin + path convention (docs/docs/en/... vs file.en.md co-located) prima di authoring 10 pagine"
```

