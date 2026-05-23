---
phase: 6
phase_name: Agents — Operations & Production
phase_slug: agents-operations-production
discussed_at: "2026-05-23"
requirements: [OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-06]
depends_on_phases: [3, 4, 5]
---

# Phase 6 Context — Agents — Operations & Production

<domain>
## Phase Boundary

**What this phase delivers:** la business logic dei 4 agenti del cluster `ops` (OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector) sopra il runtime Phase 4 (supervisor + HITL + LLM adapter + audit), il knowledge layer Phase 5 (rag_search + traverse_graph + ACL) e il simulator Phase 3 (NATS sensor.events + TimescaleDB + asset registry).

Concretamente:
- 4 implementazioni `sft_agents.sdk.Agent` in `apps/agents/ops/{operator-assistant,production-planner,quality-inspector,anomaly-detector}/src/` con `__call__(state) -> state` callable invocato come nodo del `clusters/ops` subgraph (D-53 Phase 4).
- **OperatorAssistant**: ReAct LangGraph (`langgraph.prebuilt.create_react_agent`) con full toolbelt (`rag_search`, `traverse_graph`, `query_timescale`, `escalate_to_supervisor`, `log_event`), risposta cross-lingual IT/EN nella lingua della query, citations strutturate obbligatorie con validator post-LLM.
- **ProductionPlanner**: greedy heuristic SPT/EDD deterministica in `packages/sft-domain/scheduling/` + LLM Qwen2.5 per rationale + citations SOP; input da `packages/sft-domain/orders.yaml` + `packages/sft-domain/asset_capacity.yaml` sintetici Mantis Textile Group; output `ScheduleDraft` JSON che passa per supervisor HITL approve → audit log only (no publish NATS Phase 6).
- **QualityInspector**: consumer/handler di QC events generati sia da estensione `sim-textile` (`quality.events.*` NATS) sia da operator-entered API (`POST /v1/quality/events`); applica 4-point grading via LLM reasoning con grading rules in prompt; HITL routing per defect severity (`minor → auto-log` / `major → supervisor` / `critical → manager + safety-interlock`) basato su tabella `hitl_tier` estesa in `failure_modes.yaml` Phase 5; ogni event include obbligatoriamente `dye_lot_id` (validato).
- **AnomalyDetector**: nodo on-demand invocato da scheduler esterno cron-like (`services/agents-scheduler/`) ogni 5 min default + endpoint API opzionale; legge ultimi N minuti TimescaleDB via `query_timescale` tool, applica baseline statico YAML per-asset (`packages/sft-domain/anomaly_baselines.yaml`) con override runtime per `machine_id`, rate-limit per-agent global 12 alert/h.
- Estensione **sim-textile** con: (a) `quality-event-generator` che emette QC events su NATS `quality.events.<asset_id>` con `defect_type` da tassonomia Phase 2 + `dye_lot_id`; (b) `production_state` model con `current_dye_lot_id` per asset (ruota su trigger o periodicamente).
- **Tassonomia difetti tessili applicata**: broken_end, mispick, slub, neppy, selvage_fault, shade_deviation, unlevel_dyeing (Phase 2 corpus). Mapping defect → severity in `packages/sft-domain/failure_modes.yaml` (esteso Phase 5).
- **Test E2E**: 3 scenari per agente (happy / degraded / failure) con LLM mock (record/replay JSON via `LLM_BACKEND=mock` Phase 4 pattern) + scenario YAML deterministici in `tests/fixtures/ops_scenarios/`. Real LLM solo opt-in via `@pytest.mark.real-llm`.

Questa phase **NON** estende parser knowledge layer (Phase 8), **NON** introduce OR-tools o constraint solver (heuristic-only), **NON** ships UI HITL approval card (Phase 10), **NON** publica schedule a NATS subject cross-cluster (deferred Phase 9), **NON** introduce watchdog filesystem per orders.yaml (deferred Phase 10), **NON** introduce auto-tuning baseline rolling-window per AnomalyDetector (deferred Phase 11 quando emerge drift osservato in produzione simulata).
</domain>

<decisions>
## Implementation Decisions

### AnomalyDetector

- **D-AD-01 — Consumo on-demand + window pull TimescaleDB.** AnomalyDetector è un nodo LangGraph standard del subgraph `clusters/ops`. Viene invocato dal supervisor con parametro `window_minutes` (default 15). Al `__call__`, legge ultimi `window_minutes` di sample da TimescaleDB usando `query_timescale` tool (Phase 3), batch-scoring, ritorna `list[Anomaly]`. **Perché:** allineato al pattern degli altri agenti (nodo LangGraph, audit uniforme, HITL nativo), no servizio long-running aggiuntivo, riusa tool esistente. **Rejected:** long-running NATS consumer (vive fuori dal grafo, duplica audit path); hybrid scorer+agent (complessità infra per PoC).

- **D-AD-02 — Baseline statico YAML per-asset + override runtime per `machine_id`.** File `packages/sft-domain/anomaly_baselines.yaml` con threshold/banda per `(asset_family, tag)` — es. loom vibration `p99 < 0.8g`, dyer temperature drift `< 2°C/min`. Override opzionale per `machine_id` specifico. Loader Pydantic `AnomalyBaseline` con validation; agente confronta sample corrente vs banda → anomaly se outside. **Perché:** deterministic, audit-friendly, riproducibile in test E2E con mock LLM, no statistical training Phase 6. Risolve success criterion #3 (no false positive su vibrazioni telaio normali via banda calibrata) senza training data dependency. **Rejected:** statistical baseline da TimescaleDB rolling (richiede continuous aggregate + drift-aware logic non ancora prioritario); hybrid YAML+auto-tuning (stato in-process fragile a restart, deferred Phase 11).

- **D-AD-03 — Rate limit per-agent global 12 alert/h.** Token bucket globale sull'agente AnomalyDetector (no per-machine partition Phase 6). Implementato come `RateLimiter` in `packages/sft-agents/src/sft_agents/runtime/rate_limit.py` (nuovo) con stato persistito in PG `audit.actions` (count query su sliding window) per sopravvivere a restart. Anomaly extra suppress (count += 1, no HITL emit) + ogni ora summary alert con `suppressed_count`. **Perché:** match preciso success criterion #3 (12/h totale). Per-machine + per-anomaly-type sono granularità future (Phase 11 osservabilità). Per-agent semplifica state management e PoC governance. **Rejected:** per-machine sliding (granularità eccessiva ora); per-(machine, anomaly_type) (richiede nuovo PG schema, deferred).

- **D-AD-04 — Trigger: scheduler esterno cron-like ogni 5 min.** Nuovo servizio `services/agents-scheduler/` (Python APScheduler + asyncio loop) container container che invoca `POST /v1/agents/anomaly-detector/scan?window_minutes=15` ogni 5 minuti (configurabile). Dockerfile + compose entry + Helm chart. Audit ogni invocazione (`triggered_by: scheduler`). Endpoint API resta disponibile per invocazione manuale (`triggered_by: operator` o `agent`). **Perché:** deterministic, audit-friendly, separazione concerns (scheduler ≠ agent logic), allineato al PoC con success criterion #3 "real-time" (5 min è accettabile per textile manufacturing latency profile). **Rejected:** solo operator-triggered (success criterion #3 chiede real-time scoring); hybrid con event-driven (deferred Phase 11 quando OBS-* emergono).

### QualityInspector

- **D-QI-01 — Input dual: sim-textile generator + operator API.** Phase 6 estende `sim-textile` con modulo `quality_event_generator.py` che, basato su `fault_profile` + `asset_family` + `current_dye_lot_id`, emette QC events stochastic su NATS subject `quality.events.<asset_id>` (payload include `defect_type` da Phase 2 taxonomy, `severity`, `dye_lot_id`, `asset_id`, `position_meters`, `timestamp`, `source: simulator`). Parallelamente endpoint `POST /v1/quality/events` (FastAPI gateway Phase 4) accetta inspection event payload Pydantic con stesso schema (`source: operator`). QualityInspector ascolta NATS subject (durable consumer JetStream `qi-consumer`) e processa ogni event in maniera uniforme regardless of source. **Perché:** copre demo realistic (simulator continuo) + casi manuali (operator inspection ad-hoc) senza duplicare schema o handler; field `source` permette audit + filtering test. **Rejected:** solo simulator (preclude flow operator inspection); solo API (perde "real-time" routine inspection mood).

- **D-QI-02 — 4-point grading via LLM reasoning + grading rules in prompt.** Prompt system per QualityInspector include le 4-point grading rules ASTM tabulari + esempi + tassonomia Phase 2. LLM Qwen2.5 produce JSON strutturato `{score: int [0..4], rationale_md: str, citations: [RagCitation]}`. Validator Pydantic + range check `[0..4]`. **Perché:** scelta accettata user-confermata per flessibilità su edge case (combinazioni defect_type × severity × dye_lot context) senza tabella esaustiva manuale. Trade-off noto: score non perfettamente deterministico (LLM stability dipendente); mitigato in test via mock LLM (D-X-01) e in produzione via HITL gate severity-based (D-QI-03 routes critical a manager/safety dove un human verifica). **Rejected:** deterministic mapper puro (rigida, copre solo regole tabulate); hybrid deterministic+LLM (deferred — se in produzione emergono inconsistenze score, Phase 11 può aggiungere deterministic floor).

- **D-QI-03 — HITL tier routing per defect severity.** Tabella `hitl_tier` per `(defect_type, severity_band)` aggiunta a `packages/sft-domain/failure_modes.yaml` (esteso da Phase 5 D-65). Mapping:
  - `severity: minor` (es. slub isolato, neppy bassa frequenza) → `auto-log` (audit + quality_events PG, no HITL interrupt)
  - `severity: major` (es. mispick ricorrente, shade_deviation ΔE > soglia) → `supervisor` (HITL tier 2)
  - `severity: critical` (es. broken_end con safety implication, unlevel_dyeing su lotto pregiato) → `manager + safety-interlock` (HITL tier 3 + SafetyInterlockMiddleware Phase 4)

  Severity prodotta dall'LLM reasoning (D-QI-02) e validata via Pydantic `Literal['minor','major','critical']`; default fallback `major` se LLM produce valore fuori range (fail-safe conservative).
  **Perché:** scala HITL al rischio reale (no flood approval queue su slub minor; manager visibility su critical). Failure modes yaml è single source of truth (estensione naturale Phase 5). **Rejected:** sempre supervisor uniform (flood); per 4-point score threshold (score è LLM-prodotto, doppia dipendenza).

- **D-QI-04 — `dye_lot_id` gestito da sim-textile production_state.** Estendere `sim-textile` con `ProductionState` model che mantiene `current_dye_lot_id` per asset (formato `DL-<asset_id>-<YYYYMMDD>-<seq>`) ruotato periodicamente (default ogni 60 min sim-time, configurabile per fault profile). Stato in-process simulator (no PG persistence Phase 6). QC events del simulator iniettano `dye_lot_id` dal `ProductionState`. Endpoint operator API richiede `dye_lot_id` esplicito nel payload (validato regex Pydantic). Audit trail: ogni QC event ha `dye_lot_id` non-null. **Perché:** match success criterion #2 ("include dye lot ID in every quality event") KISS senza nuova migration PG. Phase 9 (CostAnalyzer) può promuovere a tabella PG `production.dye_lots` quando ROI analytics emerge. **Rejected:** nuova migration `007_create_dye_lots.sql` (scope creep Phase 6, payload Pydantic basta); convention-only senza simulator state (operator API resta non-validated cross-event).

### ProductionPlanner

- **D-PP-01 — Greedy heuristic SPT/EDD + LLM rationale (no OR-tools).** Algoritmo deterministico puro Python in `packages/sft-domain/scheduling/`:
  - Modulo `heuristic.py` con funzioni `schedule_spt(orders, capacity) -> ScheduleDraft` (Shortest Processing Time) e `schedule_edd(orders, capacity) -> ScheduleDraft` (Earliest Due Date), selezione strategia via parametro request.
  - Vincoli applicati: capacity per asset_family (`asset_capacity.yaml`), due-date hard cap, setup-time da `failure_modes.yaml` setup_minutes (estensione), no-overlap per asset, dye_lot compatibility constraint (no shade conflict same asset same hour).
  - Output `ScheduleDraft` Pydantic; LLM Qwen2.5 invocato post-scheduling per generare `rationale_md` (spiegazione + citations SOP via `rag_search` Tool su strategie scheduling rilevanti dal corpus Phase 2/5).
  
  **Perché:** scope appropriato per PoC + competition demo (riproducibile, no dipendenza pesante ortools ~30MB, testable unit-test deterministico). Phase 9 (Supply Chain) può promuovere a CP-SAT quando InventoryManager/DemandForecaster emergono con vincoli più complessi. **Rejected:** OR-tools CP-SAT (deps pesanti, overkill Phase 6 con orders sintetici limitati); LLM-only JSON-mode (non-deterministic, replan loop overhead, audit complesso).

- **D-PP-02 — Input da YAML seed in `packages/sft-domain/`.** Nuovi file:
  - `packages/sft-domain/orders.yaml` — ~20 ordini sintetici Mantis Textile Group (fabric SKU groups, quantità m², due-date, priority); loader Pydantic `OrderSpec`.
  - `packages/sft-domain/asset_capacity.yaml` — capacity sheet derivata da `packages/sft-assets` 30 asset Phase 3 (asset_id → max_meters_per_hour, max_concurrent_dye_lots, downtime_windows opzionali); loader Pydantic `AssetCapacity`.
  
  Caricati al startup dell'agente (cached). Validator CI verifica referenze (`asset_id` orders.yaml ⊂ asset_capacity.yaml ⊂ packages/sft-assets registry).
  **Perché:** riproducibile, audit-friendly, demo-ready per competition (file in repo). KISS senza migration PG. Phase 9 CostAnalyzer può consumare gli stessi YAML per ROI sensitivity. **Rejected:** PG `production.orders` (overkill PoC, no UI Phase 6); hybrid YAML+PG schedule_history (deferred — audit basta su `audit.actions` Phase 4).

- **D-PP-03 — Output `ScheduleDraft` JSON → supervisor HITL approve → audit log only.** Pydantic schema:
  ```python
  class ScheduleDraftItem(BaseModel):
      model_config = {"frozen": True, "extra": "forbid"}
      order_id: str
      asset_id: str
      start_at: datetime
      end_at: datetime
      dye_lot_id: str | None
      sequence: int

  class ScheduleDraft(BaseModel):
      model_config = {"frozen": True, "extra": "forbid"}
      schedule_id: str  # UUID4
      strategy: Literal['spt','edd']
      horizon_start: datetime
      horizon_end: datetime
      items: list[ScheduleDraftItem]
      rationale_md: str
      citations: list[RagCitation]
      created_at: datetime
  ```
  Draft serializzato in `audit.actions` payload + interrupt() HITL Phase 4. Supervisor approve via UI → audit log entry `decision: approved` + draft diventa "active draft" (read-only, no further mutation). No publish NATS Phase 6 (deferred D-PP-deferred-1 a Phase 9 cross-cluster).
  **Perché:** match preciso success criterion #4. Audit-only output coerente con PoC (no PLC real release). **Rejected:** auto-publish NATS (scope creep cross-cluster Phase 9); pre-approval Q&A via OperatorAssistant (cross-agent dipendenza intra-Phase 6, può emergere in Phase 10 UI quando EvidencePanel guida la conversation).

- **D-PP-04 — Trigger on-demand via API/UI.** Endpoint `POST /v1/agents/production-planner/plan` con body `{horizon_days: int, strategy: 'spt'|'edd'}`. Invocato manualmente da operator/supervisor (UI Phase 10) o test E2E. No cron, no event-trigger Phase 6. **Perché:** allineato al flow PoC dove demo è user-driven (competition demo flow + Phase 10 walkthrough). Cron giornaliero o event-driven sono ottimizzazioni Phase 9/11. **Rejected:** scheduler daily 06:00 (overhead infra non giustificato Phase 6); event-driven su orders change (watcher complessità deferred Phase 10).

### OperatorAssistant

- **D-OA-01 — LangGraph prebuilt `create_react_agent` (ReAct loop, max_iterations=5).** Uso `langgraph.prebuilt.create_react_agent(model, tools)` con `LLM_BACKEND` factory Phase 4 (default Qwen2.5-7B Ollama). `recursion_limit=5` enforced via Phase 4 `safe_invoke` (eccedenza → HITL escalation D-53). Audit automatico per ogni `tool_call` via Langfuse callback Phase 4. Stato del subgraph include `messages`, `tool_results`, `iteration_count`, `evidence_citations`. **Perché:** best practice LangGraph 2025, audit nativo, code minimo. Rispecchia il pattern multi-tool consigliato dalla docs LangChain v0.3+. **Rejected:** custom plan-then-execute (pi� codice, meno flessibile su query non previste); custom ReAct state machine (replica funzionalit� con maintenance overhead).

- **D-OA-02 — Full toolbelt: `rag_search` + `traverse_graph` + `query_timescale` + `escalate_to_supervisor` + `log_event`.** 5 tool esposti:
  1. `rag_search` (Phase 5) — query knowledge base, ACL-aware via `user_roles` injected dal supervisor state.
  2. `traverse_graph` (Phase 5) — naviga Machine→Part→FailureMode→SOP per contestualizzare query su asset specifico.
  3. `query_timescale` (Phase 3) — legge sensor history per dare risposta data-driven (es. "che temperatura ha avuto il telaio L01 ieri?").
  4. `escalate_to_supervisor` (NEW Phase 6, in `packages/sft-agents/src/sft_agents/tools/hitl.py`) — il LLM può forzare HITL interrupt quando user chiede azione che richiede approval umano. Wrappa `interrupt()` Phase 4 con payload `{reason, suggested_action, evidence}`.
  5. `log_event` (NEW Phase 6, in `packages/sft-agents/src/sft_agents/tools/audit.py`) — scrive evento informativo in `audit.actions` con `decision: logged` (no HITL); usato per tracking shift-handover-ready dati.

  Audit policy: ogni tool_call registrato in Langfuse span + `audit.actions` se action-bearing (escalate, log_event). RAG citations propagate nello state per validator finale (D-OA-04).
  **Perché:** scelta user-confermata per esporre OperatorAssistant come "primo punto di contatto" che può sia rispondere (rag/graph/timescale) sia agire entro confini sicuri (escalate + log). Tool dedicati semplificano audit e test isolation. **Rejected:** solo rag+graph (preclude data-driven sensor Q); solo rag+graph+timescale (preclude flow azione/escalation).

- **D-OA-03 — Lingua di risposta = lingua della query, retrieval cross-lingual default.** Detect lingua query con `langdetect` (lib stabile, deterministic con `langdetect.DetectorFactory.seed=42` per riproducibilità). Risposta LLM nella lingua detected. `rag_search` invocato sempre con `lang=None` (cross-lingual via BGE-M3 D-64 Phase 5). Citations preserve source lang (es. SOP IT cited in risposta EN). Prompt system include esempio bilingue per garantire LLM segue language coherence. **Perché:** match success criterion #1 ("Italian-language query"), supporta demo bilingue PROJECT.md, sfrutta investimento Phase 5 cross-lingual retrieval. **Rejected:** sempre IT default (rompe success criterion #5 multi-scenario testing in EN); parametro `output_lang` API esplicito (può emergere Phase 10 UI ma non required ora).

- **D-OA-04 — `escalate_to_supervisor` auto-trigger HITL + citation validator post-LLM.**
  - Tool `escalate_to_supervisor`: quando LLM lo invoca, il nodo wrappa `interrupt()` Phase 4 con payload strutturato + auto-routing a supervisor HITL tier. Audit dual-write Phase 4.
  - Citations: response output sempre include `citations: list[RagCitation]` strutturate per EvidencePanel Phase 10. Inline references `[1]`, `[2]` nel `response_md`.
  - **Validator post-LLM** (in `apps/agents/ops/operator-assistant/src/.../validators.py`): se il graph ha invocato `rag_search` (tool_results contiene `rag_search` con risultati) ma `response_md` non contiene `[N]` reference né `citations` è non-vuoto → raise `MissingCitationError` → nodo replan con prompt augmentation (max 1 retry) → se ancora missing → response esce con warning logged + flag `citations_missing: true` in audit.
  
  **Perché:** match esplicito success criterion #1 ("cites the source chunk inline"). Validator enforce non opzionale per evitare drift LLM. Auto-HITL su escalate match valore-core PROJECT.md ("ogni decisione critica passa per umano informato"). **Rejected:** manual escalate approval (perde immediatezza); citation soft (success criterion specifically requires inline cite).

### Cross-cutting

- **D-X-01 — Test E2E: mock LLM record/replay + scenario YAML deterministici.** Tests in `tests/e2e/ops/test_<agent>_scenarios.py` (4 file, uno per agente). Ogni file copre 3 scenari (`happy`, `degraded`, `failure`) come parametrize fixture caricato da `tests/fixtures/ops_scenarios/<agent>/<scenario>.yaml`. LLM Backend `mock` (`LLM_BACKEND=mock` env, factory Phase 4) legge response da `tests/fixtures/llm_responses/<agent>/<scenario>.jsonl`. Knowledge layer (Qdrant + Neo4j) provided via testcontainers fixture (esistente Phase 5 `tests/conftest.py`). NATS testcontainer per consumer test (Phase 3). PG testcontainer per `audit.actions` (Phase 4).
  - Marker `@pytest.mark.e2e` + `@pytest.mark.integration`.
  - Opt-in real LLM: `@pytest.mark.real-llm` salta in CI default, run manuale `pytest -m real-llm` con Ollama in services GitHub Actions.
  
  **Perché:** CI veloce (< 3 min E2E ops), deterministico, riproducibile su PR. Match success criterion #5 (3 scenari × 4 agenti = 12 test). Real LLM disponibile per smoke validation pre-release. **Rejected:** real Qwen2.5 in CI default (lentezza + flakiness, non sostenibile per PR loop); hybrid mock+real-N (1 golden real-llm per agente è opzione legittima ma può essere aggiunta in Phase 11 senza rifare l'impalcatura — accettato come potenziale follow-up).

### Claude's Discretion

- **Naming convention agent slug per file** (`ops-operator-assistant` vs `operator_assistant`): segue convenzione esistente `apps/agents/ops/operator-assistant/` (kebab dir, snake_case Python package `ops_operator_assistant`).
- **Pydantic model file organization**: ogni agent ha `src/<pkg>/models.py` per types specifici; types cross-agent (es. `Anomaly`, `QualityEvent`, `ScheduleDraft`) in `packages/sft-domain/src/sft_domain/ops/`.
- **Logging structlog field naming**: convention Phase 1-5 (`agent.<slug>`, `event.<type>`, `decision.<action>`, snake_case fields).
- **Test naming pattern**: `test_<concern>.py` (unit) vs `test_<scenario>_e2e.py` (E2E) — match Phase 3/4/5 esistenti.
- **OPS cluster subgraph routing logic** (chi del cluster ops viene invocato quando il supervisor entra in `clusters/ops`): Claude implementa via field `target_agent` nello state subgraph (HybridRouter Phase 4 lo popola da supervisor LLM routing decision); fallback su `operator-assistant` quando ambiguo. Documentato in plan.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner) MUST read these before planning or implementing.**

### Project-level
- `.planning/ROADMAP.md` §"Phase 6: Agents — Operations & Production" — goal + 5 success criteria + 6 requirements (OPS-01..06)
- `.planning/REQUIREMENTS.md` §"Agenti Operations & Production (OPS)" — OPS-01..06 dettaglio testuale
- `.planning/PROJECT.md` — core value "ogni decisione critica AI passa per umano informato"; Mantis Textile Group context; ecosistema tecnico (Qwen2.5 + LangGraph + Qdrant + Neo4j)

### Research artifacts
- `.planning/research/STACK.md` — stack LOCKED (LangGraph + Qwen2.5 via Ollama/vLLM + ortools deliberately NOT in core stack); il greedy heuristic D-PP-01 evita di reintrodurre dep non-locked
- `.planning/research/ARCHITECTURE.md` — cluster subgraph topology (D-53), HITL interrupt cycle, EvidencePanel data contract
- `.planning/research/PITFALLS.md` — pitfall su agent state mutation, asyncio cancellation, LLM hallucination su numerical reasoning (rilevante D-QI-02 LLM grading + D-PP-01 LLM rationale non scheduling)
- `.planning/research/FEATURES.md` — features list OPS agents + HITL tiering

### Prior phase contexts (carry-forward decisions)
- `.planning/phases/01-foundation-monorepo/01-CONTEXT.md` — D-02 packages layout (kebab-dir / snake-pkg); D-09 docker-compose pattern; Helm chart skeleton
- `.planning/phases/02-domain-modeling-synthetic-corpus/02-CONTEXT.md` — defect taxonomy (broken_end, mispick, slub, neppy, selvage_fault, shade_deviation, unlevel_dyeing) → D-QI-02/03; D-25 SOP `status: reviewed` gate; glossary bilingue
- `.planning/phases/03-it-ot-simulation-layer/03-CONTEXT.md` — sim-textile architecture + fault profiles YAML pattern (estesi in D-QI-01 + D-QI-04); NATS subjects `sensor.events.*`; TimescaleDB hypertables + `query_timescale` tool; `packages/sft-assets` 30 asset registry
- `.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md` — D-53 cluster `ops` subgraph esiste con 4 placeholder children (Phase 6 riempie); HITL interrupt/resume cycle + 4-tier escalation (operator/supervisor/manager/safety); LLM_BACKEND factory; AuditWriter dual-write; SafetyInterlockMiddleware; BudgetTracker; recursion_limit→HITL via safe_invoke; D-59 `RagCitation` schema
- `.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md` — D-66 separato `rag_search` + `traverse_graph` Tool; D-72 ACL `acl_level` + `ROLE_TO_ACL` mapping; D-64 cross-lingual via BGE-M3 (no query translation) → D-OA-03; `failure_modes.yaml` schema (esteso Phase 6 con `hitl_tier` + `setup_minutes`)

### Code artifacts to extend
- `apps/agents/ops/{operator-assistant,production-planner,quality-inspector,anomaly-detector}/` — 4 scaffold packages esistenti (`pyproject.toml` + empty `src/__init__.py`); Phase 6 popola business logic
- `packages/sft-agents/src/sft_agents/clusters/ops/__init__.py` — `CHILD_AGENT_SLUGS` constant; Phase 6 wires real callables
- `packages/sft-agents/src/sft_agents/runtime/clusters.py` — `build_cluster_subgraph` placeholder (Phase 4); Phase 6 può estendere con routing logic ops-specific (D-X "Claude's Discretion" OPS cluster routing)
- `packages/sft-agents/src/sft_agents/sdk/agent.py` — Agent ABC base
- `packages/sft-agents/src/sft_agents/runtime/supervisor.py` — `build_supervisor_graph` + HybridRouter (Phase 4); Phase 6 verifica routing a `clusters/ops`
- `packages/sft-agents/src/sft_agents/tools/` (NEW Phase 6 additions): `hitl.py` (escalate_to_supervisor tool), `audit.py` (log_event tool)
- `packages/sft-domain/` — Phase 6 aggiunge: `orders.yaml`, `asset_capacity.yaml`, `anomaly_baselines.yaml`, `scheduling/heuristic.py`, `ops/` models package; ESTENDE `failure_modes.yaml` con `hitl_tier` + `setup_minutes` + `severity` mapping
- `packages/sft-knowledge/src/sft_knowledge/tools/{rag.py,graph.py}` — `RagSearchTool` + `TraverseGraphTool` (Phase 5); Phase 6 USA, non duplica
- `packages/sft-tools/src/sft_tools/query_timescale.py` — `QueryTimescaleTool` (Phase 3); Phase 6 USA per AnomalyDetector + OperatorAssistant
- `simulators/sim-textile/` — Phase 6 estende: nuovo `quality_event_generator.py` + `production_state.py`; aggiunge subject NATS `quality.events.*` al publisher
- `services/agents-scheduler/` (NEW Phase 6) — cron-like scheduler container (APScheduler) per AnomalyDetector trigger 5min
- `apps/api-gateway/` (Phase 4) — Phase 6 aggiunge endpoint: `POST /v1/quality/events`, `POST /v1/agents/anomaly-detector/scan`, `POST /v1/agents/production-planner/plan`, `POST /v1/agents/operator-assistant/chat`
- `infra/compose/core.yml` — Phase 6 aggiunge service `agents-scheduler`; estende sim-textile env per `quality_event_generator` enable
- `tests/conftest.py` — fixture pattern Phase 3/4/5; Phase 6 estende con `mock_llm_backend` fixture (record/replay JSON) + `ops_scenario` parametrize loader

### External references (consultative only)
- LangGraph docs §"prebuilt agents" → `create_react_agent` API contract (Phase 6 D-OA-01)
- 4-point system ASTM (referenza dominio, NO code-citation; usata in prompt LLM D-QI-02)

No external SPEC.md or ADR exists for Phase 6 — this CONTEXT.md is source of truth.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`packages/sft-knowledge/src/sft_knowledge/tools/{rag,graph}.py`** (Phase 5): `RagSearchTool` + `TraverseGraphTool` LangChain BaseTool — Phase 6 li registra direttamente nei ReAct agents (OperatorAssistant). ACL filter via `user_roles` injected dal supervisor state Phase 4.
- **`packages/sft-tools/src/sft_tools/query_timescale.py`** (Phase 3): `QueryTimescaleTool` Phase 3 — Phase 6 lo riusa per AnomalyDetector (batch sample window) + OperatorAssistant (sensor history Q&A). Schema input/output gi� Pydantic-validated.
- **`packages/sft-agents/src/sft_agents/runtime/supervisor.py`** (Phase 4): `build_supervisor_graph` con HybridRouter — Phase 6 verifica che `clusters/ops` subgraph riceva routing correttamente; non modifica supervisor logic.
- **`packages/sft-agents/src/sft_agents/hitl/`** (Phase 4): `interrupt()` + `approval_queue` + `EscalationSupervisor` + `SafetyInterlockMiddleware` — Phase 6 USA via `escalate_to_supervisor` tool e HITL tier mapping (D-QI-03).
- **`packages/sft-agents/src/sft_agents/models/`** (Phase 4): `RagCitation`, `EvidencePanel`, `AuditAction`, `HitlDecision` — Phase 6 popola; aggiunge `Anomaly`, `QualityEvent`, `ScheduleDraft`, `ScheduleDraftItem` types in `packages/sft-domain/src/sft_domain/ops/models.py`.
- **`packages/sft-agents/src/sft_agents/llm/`** (Phase 4): `LLM_BACKEND` factory + Langfuse callback + BudgetTracker — Phase 6 ottiene LLM via factory, callback Langfuse traccia automaticamente span `agent.<slug>.invoke`.
- **`packages/sft-assets/`** (Phase 3): 30 asset seed con Asset/Tag models — Phase 6 carica per validator `asset_capacity.yaml` + AnomalyDetector baseline lookup.
- **`packages/sft-domain/`** (Phase 2/5): glossary IT/EN, defect taxonomy, `failure_modes.yaml` — Phase 6 estende failure_modes (hitl_tier, setup_minutes, severity); aggiunge orders/capacity/baselines yaml + scheduling module.

### Established Patterns (consistency requirements)
- **Pydantic v2 frozen + `extra=forbid`** mandatory for ALL new models (Phase 1+2+3+4+5 standard).
- **`yaml.safe_load` only** (mai yaml.load).
- **asyncpg `$1..$N` placeholders ONLY** for SQL (Phase 3 T-V5-sql threat).
- **`datetime.now(UTC)`** mandatory (Phase 3 Pitfall 7).
- **structlog JSON logging** con context binding (`agent.<slug>`, `decision`, `tool_call`, ...).
- **Test markers**: `@pytest.mark.integration` (testcontainers), `@pytest.mark.e2e` (full scenario), `@pytest.mark.real-llm` (opt-in real Qwen2.5), `@pytest.mark.gpu` (BGE-M3 only — Phase 6 NON usa GPU, embedding pre-fetchato via Phase 5 indexer).
- **Naming**: Conventional Commits `feat(06-NN-slug):` per atomic commit; agent slug kebab-case dir, snake_case Python package; YAML keys snake_case; frontmatter fields kebab-case.
- **LLM mock backend**: `LLM_BACKEND=mock` factory legge response da `tests/fixtures/llm_responses/` (Phase 4 pattern); Phase 6 ships fixtures aggiuntive per ops agents.

### Integration Points
- **Supervisor subgraph routing**: HybridRouter Phase 4 routa al cluster `ops` → ops subgraph deve decidere quale dei 4 agenti invocare. Phase 6 implementa via `target_agent` field nello state (popolato da supervisor LLM o da request context) con fallback `operator-assistant`.
- **HITL approval queue**: Phase 6 agents publica HITL interrupts via Phase 4 `interrupt()`; supervisor UI Phase 10 consumer� (Phase 6 NON ship UI).
- **Audit dual-write**: ogni decision agent (anomaly detected, schedule draft, QI verdict, OA escalation) scritta in PG `audit.actions` + NATS `AUDIT_STREAM` (Phase 4 D-AuditWriter).
- **NATS subjects**: Phase 6 introduce nuovi subjects:
  - `quality.events.<asset_id>` (publisher: sim-textile + api-gateway operator endpoint; consumer: QualityInspector durable `qi-consumer`)
  - `alerts.anomalies.<asset_id>` (publisher: AnomalyDetector via Phase 4 audit + opzionale broadcast)
  - Subjects esistenti riusati: `sensor.events.*` (Phase 3), `AUDIT_STREAM` (Phase 4)
- **TimescaleDB schema extensions**: Phase 6 NON aggiunge migration (dye_lot e schedule_draft restano in audit.actions JSON payload + in-process sim-textile state). Phase 9 promuover� se ROI emerge.
- **Knowledge layer integration**: tutti i 4 agenti dipendono da Qdrant + Neo4j up (Phase 5 D-65). Compose stack Phase 5 gi� avvia entrambi; Phase 6 verifica startup ordering (`depends_on`).

</code_context>

<specifics>
## Specific Ideas

- **OperatorAssistant come "primo punto di contatto"**: full toolbelt scelto deliberatamente per supportare flow conversazionali estesi (knowledge Q&A + sensor data check + escalation azione). Allineato a value PROJECT.md "nessun essere umano � mai solo davanti a un problema operativo".
- **Tassonomia tessile Phase 2 come single source of truth**: defect_type, severity, asset_family, dye_lot vivono in `packages/sft-domain` (no duplicazione cross-package). Phase 6 estende `failure_modes.yaml` invece di creare nuovi file overlap.
- **PoC senza release reale**: ScheduleDraft "approvato" rimane audit log + read-only state; nessun publish PLC/ERP. Demo competition focalizzata su flow HITL + provenance.
- **Mock LLM-first per CI**: deliberato per garantire CI determinism. Real LLM esiste come escape hatch (`@pytest.mark.real-llm`) per pre-release smoke. Allineato a strategia Phase 4 (LLM_BACKEND factory).
- **Severity drive HITL routing** invece di score numerico: scelta esplicita user per non vincolare HITL a LLM stability sul numerical reasoning.

</specifics>

<deferred>
## Deferred Ideas

- **AnomalyDetector auto-tuning baseline** (statistical rolling-window per machine drift detection) → **Phase 11** (Observability) quando drift osservato in produzione simulata emerge come bisogno; Phase 6 YAML baseline + override copre PoC.
- **AnomalyDetector per-machine + per-anomaly-type rate limiting** → **Phase 11** quando OBS-* defining; Phase 6 per-agent global � KISS.
- **ProductionPlanner OR-tools CP-SAT solver** → **Phase 9** (Supply Chain & Economics) quando InventoryManager/DemandForecaster richiedono vincoli complessi (capacity multi-stage, JIT inventory, cost optimization); Phase 6 greedy heuristic copre PoC.
- **ProductionPlanner auto-publish a NATS `production.schedule.approved`** per consumer cross-cluster → **Phase 9** (downstream agents come EnergyOptimizer, CostAnalyzer consumeranno).
- **ProductionPlanner cron daily 06:00** trigger → **Phase 11** se monitoring evidenzia bisogno proattivo; Phase 6 on-demand basta per demo.
- **ProductionPlanner event-driven replan** su orders.yaml change → **Phase 10** (UI + filesystem watcher quando UI upload entra; analogo a Phase 5 D-68).
- **QualityInspector hybrid deterministic+LLM grading** (deterministic floor su score) → **Phase 11** se LLM-only D-QI-02 mostra inconsistenze score in produzione.
- **QualityInspector PG `production.dye_lots` schema** (migration dedicata + recipe tracking) → **Phase 9** (CostAnalyzer ROI per lotto) quando analytics emerge come bisogno.
- **QualityInspector publish `quality.alerts.*` cross-cluster** (per Phase 7 RCASpecialist consumer) → **Phase 7**.
- **OperatorAssistant `output_lang` parameter API esplicito** → **Phase 10** UI quando user preferences emergono dalla shell.
- **Real-LLM golden path E2E per agente** (1 test reale Qwen2.5 ops, `@pytest.mark.real-llm` opt-in) → **Phase 11** insieme a OBS-2 LLM tracing + RAG eval CI gates.
- **Long-running NATS consumer per AnomalyDetector** (scoring hot path low-latency) → **Phase 11** quando observability esige sub-second latency anomaly detection.
- **OperatorAssistant proactive engagement** (es. l'agente apre conversation su alert AnomalyDetector senza richiesta operatore) → **Phase 10** UI quando push notifications + websocket infrastructure emergono.

### Reviewed Todos (not folded)
None — no pending todos cross-referenced this phase.

</deferred>

---

*Phase: 6-Agents — Operations & Production*
*Context gathered: 2026-05-23*
