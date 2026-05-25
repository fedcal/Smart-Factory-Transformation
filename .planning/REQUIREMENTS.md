# Requirements: Smart Factory Transformation

**Defined:** 2026-05-16
**Core Value:** Ogni decisione critica dell'AI passa per un essere umano informato, ma nessun essere umano è mai solo davanti a un problema operativo.

> Cliente di riferimento: **Mantis Textile Group** (gruppo tessile fittizio).
> Repo: <https://github.com/fedcal/Smart-Factory-Transformation>
> Modello economico: OEPV con Base d'Asta €108.000 (70% tecnico / 30% economico).

---

## v1 Requirements

Requirements del rilascio iniziale. Ogni REQ è atomico, testabile e mappato a una fase di roadmap.

### Platform & Monorepo (PLAT)

- [ ] **PLAT-01**: Monorepo Nx con plugin `@nxlv/python` e supporto Angular first-class
- [ ] **PLAT-02**: Workspace polyglot con `uv` workspaces per pacchetti Python e `pnpm`/Nx per TypeScript/Angular
- [ ] **PLAT-03**: Struttura `apps/`, `packages/`, `services/`, `docs/`, `infra/`, `simulators/` documentata
- [ ] **PLAT-04**: GitHub Actions con `nx affected` per build/test/lint solo sui pacchetti impattati
- [ ] **PLAT-05**: Pipeline CI con license scanner (es. `pip-licenses`, `license-checker`) che blocca dipendenze incompatibili con OSS
- [ ] **PLAT-06**: Pre-commit hooks (ruff, mypy strict, eslint, prettier) eseguiti in CI
- [ ] **PLAT-07**: Docker Compose per dev locale con PostgreSQL+TimescaleDB, Qdrant, NATS JetStream, Ollama, Langfuse
- [ ] **PLAT-08**: Helm chart skeleton (o Kustomize) per deploy prod on-premise
- [ ] **PLAT-09**: Makefile/Just con comandi standard (`make up`, `make test`, `make docs`, `make demo`)
- [ ] **PLAT-10**: Versionamento semantico delle release con Changesets o release-please

### Core Agentico (CORE)

- [ ] **CORE-01**: SDK Python `sft-agents` con interfaccia uniforme `Agent`, `Tool`, `Memory`, `Policy`
- [ ] **CORE-02**: Orchestratore LangGraph con pattern supervisor + cluster subgraphs (4 cluster)
- [ ] **CORE-03**: `recursion_limit` esplicito su ogni `graph.invoke()` (default ≤25, configurabile per agente)
- [ ] **CORE-04**: Checkpointer PostgreSQL per persistenza stato LangGraph (resume cross-session)
- [ ] **CORE-05**: Adapter LLM provider-agnostic con backend Ollama (dev) e vLLM (prod) selezionabile da config
- [ ] **CORE-06**: Default LLM Qwen2.5 14B AWQ (vLLM) con fallback 7B Q4_K_M (Ollama) per dev
- [ ] **CORE-07**: Tool registry con tipizzazione Pydantic e schema JSON esportabili per function calling
- [ ] **CORE-08**: Memory layer: short-term (LangGraph state), long-term (Qdrant + PostgreSQL), episodic (NATS replay)
- [ ] **CORE-09**: Budget/quota tracker per token, costo simulato, durata esecuzione per ogni agente
- [ ] **CORE-10**: Replay deterministico di esecuzioni passate da checkpoint + audit log

### Human-in-the-Loop & Governance (HITL)

- [ ] **HITL-01**: `interrupt()` LangGraph nativo con resume tramite checkpointer
- [ ] **HITL-02**: 4 livelli di escalation: Operator → Supervisor → Manager → Safety Interlock
- [ ] **HITL-03**: Safety Interlock rifiuta a priori qualsiasi azione che scriva setpoint PLC (whitelist tool)
- [ ] **HITL-04**: Approval queue persistente con SLA per livello (es. 2 min Operator, 15 min Supervisor)
- [ ] **HITL-05**: Audit trail immutabile su NATS `AUDIT_STREAM` (retention 90 giorni) + tabella PG append-only
- [ ] **HITL-06**: Ogni decisione AI include evidence panel (input, tool calls, citazioni RAG, confidence)
- [ ] **HITL-07**: Override umano sempre tracciato con motivazione obbligatoria
- [ ] **HITL-08**: Rollback di azione agente tramite event sourcing replay
- [ ] **HITL-09**: Approval rate governor: se >80% azioni auto-approvate consecutivamente, alert al Manager
- [x] **HITL-10**: Rate-limit alarm su UI operatore (max 12 alert/ora per persona)

### IT/OT Integration (IOT)

- [ ] **IOT-01**: Simulatore Python custom della linea tessile (telai, filatoi, orditoi, finissaggio, tintoria)
- [ ] **IOT-02**: Mock OPC-UA server (asyncua) con nodi browsabili e sottoscrizione eventi
- [ ] **IOT-03**: Fault injection nel simulatore: NaN, drift, jitter, burst noise, alarm storm
- [ ] **IOT-04**: Bus eventi NATS JetStream con subject hierarchy `sensor.events.*`, `agent.actions.*`, `audit.*`
- [ ] **IOT-05**: OT Bridge separato (microservizio): legge OPC-UA → pubblica su NATS, nessun path inverso
- [ ] **IOT-06**: TimescaleDB per ingest time-series sensori (hypertable con compression policy)
- [ ] **IOT-07**: Replay loader per dataset NASA C-MAPSS (predictive maintenance) integrato come tool
- [ ] **IOT-08**: Replay loader per dataset UCI Manufacturing integrato come tool
- [ ] **IOT-09**: Ingest schema documentato con esempi (asset registry, tag dictionary, units of measure)
- [ ] **IOT-10**: Test di carico simulato fino a 5K msg/s con assert di latency p99 < 200ms

### Knowledge Layer (KNW)

- [ ] **KNW-01**: Qdrant self-hosted con collections separate per categoria (SOP, manuali, troubleshooting, training)
- [ ] **KNW-02**: Embedding model BGE-M3 (MIT) come default, con adapter per multilingual-e5-large
- [ ] **KNW-03**: A/B evaluation su corpus tessile IT+EN documentato in `docs/`
- [ ] **KNW-04**: Pipeline di document ingestion: PDF/DOCX/HTML/MD → chunking → embedding → upsert
- [ ] **KNW-05**: Provenance obbligatoria: ogni chunk indicizzato ha `source_uri`, `page`, `version`, `lang`
- [ ] **KNW-06**: Access control tag per chunk (es. `public`, `internal`, `restricted`) rispettati a query time
- [x] **KNW-07**: Reindex incrementale via watcher sul filesystem (o webhook Git)
- [ ] **KNW-08**: Entity graph (Neo4j Community o Memgraph OSS) per relazioni asset-procedura-difetto-causa
- [ ] **KNW-09**: Hybrid retrieval (dense BGE-M3 + sparse BM25) con rerank opzionale
- [ ] **KNW-10**: Corpus sintetico bilingue (IT/EN) di SOP tessili seedato nel repo per demo

### Agenti Operations & Production (OPS)

- [ ] **OPS-01**: `OperatorAssistant` — guida runtime, risponde a domande contestuali, suggerisce next-best-action
- [ ] **OPS-02**: `ProductionPlanner` — ottimizza scheduling ordini su linee/macchine con vincoli capacità
- [ ] **OPS-03**: `QualityInspector` — valuta segnali QC, applica tassonomia difetti tessili (broken end, mispick, slub, neppy, selvage fault, shade deviation, unlevel dyeing) e 4-point grading
- [ ] **OPS-04**: `AnomalyDetector` — rileva anomalie real-time su streaming sensori con baseline per-machine
- [x] **OPS-05**: Ogni agente OPS dichiara: tool usati, fonti dati, livello HITL richiesto, KPI impattati
- [x] **OPS-06**: Test end-to-end per ciascun agente OPS su scenario simulato con verità nota

### Agenti Maintenance & Reliability (MNT)

- [ ] **MNT-01**: `PredictiveMaintenance` — stima RUL (Remaining Useful Life) su asset (modello adattato da C-MAPSS a tessile)
- [ ] **MNT-02**: `RCASpecialist` — root cause analysis su downtime con 5-Whys assistito e citazioni dal knowledge base
- [ ] **MNT-03**: `MaintenanceCoach` — guida procedurale step-by-step durante intervento con checkpoint HITL
- [ ] **MNT-04**: `DowntimeAnalyzer` — categorizza fermi, calcola MTTR/MTBF, suggerisce pattern recurring
- [ ] **MNT-05**: Tassonomia eventi di manutenzione documentata e usata coerentemente
- [ ] **MNT-06**: Integrazione con asset registry (PG) e storico interventi (event store)

### Agenti Knowledge & Training (TRN)

- [ ] **TRN-01**: `KnowledgeCurator` — ingest e cura RAG su SOP/manuali, deduplicazione, segnalazione contenuti stale
- [x] **TRN-02**: `TrainingCoach` — adaptive learning su procedure, valuta competenza con quiz contestualizzati
- [x] **TRN-03**: `ShiftHandover` — sintetizza handover di turno aggregando eventi, decisioni, alert aperti
- [x] **TRN-04**: `DocumentationSynthesizer` — genera bozze SOP/runbook da eventi storici, sempre con HITL approval
- [x] **TRN-05**: Tutti gli output TRN includono citazioni con `source_uri` e timestamp

### Agenti Supply Chain & Economics (SCM)

- [x] **SCM-01**: `InventoryManager` — monitora livelli magazzino (filato grezzo, accessori, ricambi), suggerisce riordini
- [x] **SCM-02**: `EnergyOptimizer` — analizza consumi (kWh, vapore, acqua) e suggerisce schedule energy-efficient
- [x] **SCM-03**: `CostAnalyzer` — calcola impatto economico di downtime/scrap, alimenta dashboard OEPV
- [x] **SCM-04**: `DemandForecaster` — proietta domanda da ordini storici + segnali esterni configurabili
- [ ] **SCM-05**: Esempi numerici realistici per Mantis (gamma prodotti, capacità, costi) documentati come sintetici

### Frontend & UX (UI)

- [x] **UI-01**: App Angular 18+ con SSR (Universal) e routing app `operator/`, `technician/`, `manager/`, `admin/`
- [x] **UI-02**: Design system con Tailwind + Angular Material; touch target ≥64px per uso factory floor
- [x] **UI-03**: Approval queue UI con evidence panel inline (input, tool calls, RAG citations, confidence)
- [x] **UI-04**: Dashboard control room con KPI live (OEE, MTTR, MTBF, scrap rate, throughput, downtime)
- [x] **UI-05**: Tema dark/light + alta leggibilità (contrast WCAG AA minimo)
- [x] **UI-06**: Stream eventi via SSE/WebSocket dal backend FastAPI
- [x] **UI-07**: i18n IT+EN su tutti i testi UI con lazy load lingua
- [x] **UI-08**: Persona walkthrough demo (operatore, capo turno, tecnico, CIO) integrato nell'app
- [x] **UI-09**: Mock UI documentate in `docs/` con screenshot generati automaticamente in CI
- [x] **UI-10**: Test E2E Playwright per i flussi HITL approval e operator handover

### Backend Services (SRV)

- [x] **SRV-01**: API Gateway FastAPI con OpenAPI 3.1, autenticazione JWT, RBAC per ruolo
- [x] **SRV-02**: Endpoint REST + SSE per approval queue, evidence, KPI, audit
- [x] **SRV-03**: WebSocket bridge tra Angular UI e NATS subjects autorizzati
- [x] **SRV-04**: Health/readiness probe + OTEL spans su ogni endpoint
- [x] **SRV-05**: Contract test Pydantic ↔ TypeScript per type-safety end-to-end

### Observability & Evaluation (OBS)

- [ ] **OBS-01**: Langfuse self-hosted v3 (Docker Compose dev + Helm prod) come traces backend
- [x] **OBS-02**: OpenTelemetry SDK su tutti gli agenti, OT Bridge, API Gateway con propagazione trace ID
- [x] **OBS-03**: Stack LGTM (Loki + Grafana + Tempo + Mimir/Prometheus) opzionale documentato
- [x] **OBS-04**: Dashboard Grafana preconfezionate per KPI agenti e KPI factory
- [x] **OBS-05**: Suite di eval RAG con DeepEval e RAGAS, gate in CI con threshold configurabili
- [x] **OBS-06**: Eval di agenti: ground truth dataset di 30+ scenari per cluster con scoring documentato
- [x] **OBS-07**: Cost dashboard: token consumati, costo simulato, latency p50/p95/p99 per agente

### Security & Governance (SEC)

- [x] **SEC-01**: Threat model documentato (STRIDE) per IT/OT, RAG ingestion, agent orchestration
- [x] **SEC-02**: Mitigation per OWASP LLM Top 10 (prompt injection, sensitive info leak, supply chain)
- [x] **SEC-03**: RBAC con ruoli `operator`, `supervisor`, `manager`, `technician`, `admin`, `auditor`
- [x] **SEC-04**: Sanitizzazione documenti in ingest (markdown safe, stripping di prompt-injection patterns noti)
- [x] **SEC-05**: Secret management via env + `.env.example` documentato; nessun secret hard-coded
- [x] **SEC-06**: Network policy: OT Bridge non ha route inverso verso OPC-UA (verificato in test)
- [x] **SEC-07**: Audit log di ogni accesso a documenti `restricted`

### Documentation (DOC)

- [ ] **DOC-01**: `docs/` con MkDocs Material e plugin i18n (IT default, EN parallelo)
- [ ] **DOC-02**: Workflow GitHub Actions che fa build docs e deploy su branch `gh-pages`
- [ ] **DOC-03**: GitHub Pages configurato con custom domain opzionale e versionato con `mike`
- [ ] **DOC-04**: Sezione **Target Architecture**: diagrammi C4 (context, container, component), data flow
- [ ] **DOC-05**: Sezione **Domain Analysis**: dominio tessile manifatturiero (processi, ruoli, pain point)
- [ ] **DOC-06**: Sezione **Functional Analysis**: end-to-end workflows Operations / Maintenance / Training
- [ ] **DOC-07**: Sezione **Use Cases** con prioritizzazione (quick win 0-3m, medio termine 3-9m, lungo termine 9-18m)
- [ ] **DOC-08**: Sezione **Mock UI / User Journey** con screenshot e flow diagram per ogni persona
- [ ] **DOC-09**: Sezione **Adoption Roadmap** con fasi, KPI, rischi, mitigazioni
- [ ] **DOC-10**: Sezione **Economic Analysis**: OEPV simulato, TCO 3 anni, value driver, cost breakdown
- [x] **DOC-11**: Sezione **Security & Governance**: threat model, mitigations, AI explainability
- [ ] **DOC-12**: Sezione **Assumption Register**: assunzioni esplicite su data quality, simulazione, limiti
- [ ] **DOC-13**: ADR (Architecture Decision Records) tracciate in `docs/adr/`
- [ ] **DOC-14**: README progetto con quick start, struttura, contributing guide
- [ ] **DOC-15**: Diagrammi Mermaid/D2 versionati come testo (no immagini binarie statiche)
- [ ] **DOC-16**: CONTRIBUTING.md, CODE_OF_CONDUCT.md, LICENSE (Apache 2.0) presenti
- [ ] **DOC-17**: Trasformazione esplicita della traccia originale documentata: cosa è stato cambiato e perché
- [ ] **DOC-18**: Glossario IT+EN dei termini tessili + agentici

### Economics & OEPV (ECO)

- [ ] **ECO-01**: Modello economico simulato con Base d'Asta €108.000 e parametri configurabili
- [x] **ECO-02**: Formula OEPV documentata: scoring tecnico (70) + economico (30) con curva non lineare per ribasso
- [ ] **ECO-03**: Calcolatore TCO 3 anni: licenze, infrastruttura on-prem (GPU, server), ops FTE, energia, change management
- [ ] **ECO-04**: Value driver quantificati: riduzione downtime, scrap, MTTR, training time, knowledge reuse
- [x] **ECO-05**: Ribasso simulator con sensitivity analysis e warning su soglia di anomalia (Codice Appalti)
- [ ] **ECO-06**: Cost component breakdown: tech, IT/OT integration, training, change management
- [ ] **ECO-07**: Risk register con probability/impact e mitigation per ogni rischio economico
- [ ] **ECO-08**: Documento `docs/economic-analysis/` con fogli di calcolo riproducibili (es. Python notebook o CSV+script)

### Deliverable di Competizione (DEL)

- [ ] **DEL-01**: Target Architecture deliverable completo allineato a `docs/architecture/`
- [ ] **DEL-02**: End-to-End Process & Workflow deliverable (production / maintenance / training)
- [ ] **DEL-03**: Prioritized Use Cases deliverable con rationale di prioritizzazione
- [ ] **DEL-04**: Mock UI / User Journey deliverable con clarity/simplicity criteria
- [ ] **DEL-05**: Adoption Roadmap deliverable con KPI, rischi, mitigations
- [ ] **DEL-06**: Economic Evaluation deliverable (OEPV completo, BA, Ri, rationale)
- [ ] **DEL-07**: Assumption Register dichiarato (data quality, simulazione, limiti)
- [ ] **DEL-08**: Zero riferimenti ad Accenture o brand della traccia originale (verifica automatica in CI)

## v2 Requirements

Acknowledged ma rinviati a milestone successivi.

### Advanced AI

- **V2-AI-01**: Fine-tuning LoRA su corpus Mantis sintetico per specializzazione dominio
- **V2-AI-02**: Multi-agent debate per decisioni complesse
- **V2-AI-03**: Computer vision per controllo qualità ottico tessuti (vision-language model)

### Real Integration

- **V2-INT-01**: Connettori reali a SAP, Oracle, MES commerciali (Tulip, Siemens Opcenter)
- **V2-INT-02**: PWA / mobile-ready installabile su tablet ruggedizzati factory floor
- **V2-INT-03**: Edge deployment su Raspberry Pi 5 / Jetson Orin per agenti leggeri

### Extended Coverage

- **V2-EXT-01**: Cluster agenti aggiuntivo Safety & Compliance (HSE, ATEX, GDPR)
- **V2-EXT-02**: Multilingua oltre IT/EN (es. ZH, DE per gruppi internazionali)
- **V2-EXT-03**: Agent marketplace / registry per plugin community

### Advanced Governance

- **V2-GOV-01**: Policy as code (OPA / Cedar) per autorizzazioni agentiche
- **V2-GOV-02**: Compliance pack EU AI Act (risk classification, technical documentation)
- **V2-GOV-03**: Certificazione ISO 27001 / SOC2 readiness checklist

## Out of Scope

Esclusioni esplicite documentate per prevenire scope creep.

| Feature | Reason |
|---------|--------|
| Integrazione con PLC fisici reali | Il PoC simula OPC-UA; integrazioni hardware richiedono deploy on-prem dedicato (responsabilità integrator) |
| Foundation model training from scratch | Usiamo Qwen2.5 open weight; training foundation è fuori budget e fuori scope |
| Marketplace SaaS multi-tenant | Anti-feature esplicita: il prodotto è single-tenant on-premise per design |
| Mobile app native (iOS/Android) | Web SSR responsive è sufficiente per v1; PWA in v2 |
| Computer vision custom per QC ottico | `QualityInspector` lavora su sensori e log in v1; CV è v2 |
| Certificazione SIL / safety hardware | La traccia è dimostrativa; cita standard senza certificarli |
| Riferimenti, branding, terminologia di Accenture | Esclusione esplicita richiesta dall'utente; verifica automatica in CI |
| Riproduzione testuale della traccia `Smart Factory Transformation.md` | Il materiale è rielaborato e ampliato per originalità |
| Cloud LLM API come default | Cloud-API è solo adapter opzionale; default è self-hosted (sostenibilità + data sovereignty) |
| Hosting community di agenti di terze parti | SDK aperto, ma niente registry/marketplace gestito |

## Traceability

Mappatura REQ ↔ fase. Popolata dal roadmapper. Aggiornata dopo `/gsd:plan-phase` e `/gsd:execute-phase`.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLAT-01 | Phase 1 | Pending |
| PLAT-02 | Phase 1 | Pending |
| PLAT-03 | Phase 1 | Pending |
| PLAT-04 | Phase 1 | Pending |
| PLAT-05 | Phase 1 | Pending |
| PLAT-06 | Phase 1 | Pending |
| PLAT-07 | Phase 1 | Pending |
| PLAT-08 | Phase 1 | Pending |
| PLAT-09 | Phase 1 | Pending |
| PLAT-10 | Phase 1 | Pending |
| OBS-01 | Phase 1 | Pending |
| DOC-05 | Phase 2 | Pending |
| DOC-12 | Phase 2 | Pending |
| DOC-18 | Phase 2 | Pending |
| KNW-10 | Phase 2 | Pending |
| IOT-01 | Phase 3 | Pending |
| IOT-02 | Phase 3 | Pending |
| IOT-03 | Phase 3 | Pending |
| IOT-04 | Phase 3 | Pending |
| IOT-05 | Phase 3 | Pending |
| IOT-06 | Phase 3 | Pending |
| IOT-07 | Phase 3 | Pending |
| IOT-08 | Phase 3 | Pending |
| IOT-09 | Phase 3 | Pending |
| IOT-10 | Phase 3 | Pending |
| CORE-01 | Phase 4 | Pending |
| CORE-02 | Phase 4 | Pending |
| CORE-03 | Phase 4 | Pending |
| CORE-04 | Phase 4 | Pending |
| CORE-05 | Phase 4 | Pending |
| CORE-06 | Phase 4 | Pending |
| CORE-07 | Phase 4 | Pending |
| CORE-08 | Phase 4 | Pending |
| CORE-09 | Phase 4 | Pending |
| CORE-10 | Phase 4 | Pending |
| HITL-01 | Phase 4 | Pending |
| HITL-02 | Phase 4 | Pending |
| HITL-03 | Phase 4 | Pending |
| HITL-04 | Phase 4 | Pending |
| HITL-05 | Phase 4 | Pending |
| HITL-06 | Phase 4 | Pending |
| HITL-07 | Phase 4 | Pending |
| HITL-08 | Phase 4 | Pending |
| HITL-09 | Phase 4 | Pending |
| HITL-10 | Phase 4 | Complete |
| KNW-01 | Phase 5 | Pending |
| KNW-02 | Phase 5 | Pending |
| KNW-03 | Phase 5 | Pending |
| KNW-04 | Phase 5 | Pending |
| KNW-05 | Phase 5 | Pending |
| KNW-06 | Phase 5 | Pending |
| KNW-07 | Phase 5 | Complete |
| KNW-08 | Phase 5 | Pending |
| KNW-09 | Phase 5 | Pending |
| TRN-01 | Phase 5 | Pending |
| OPS-01 | Phase 6 | Pending |
| OPS-02 | Phase 6 | Pending |
| OPS-03 | Phase 6 | Pending |
| OPS-04 | Phase 6 | Pending |
| OPS-05 | Phase 6 | Complete |
| OPS-06 | Phase 6 | Complete |
| MNT-01 | Phase 7 | Pending |
| MNT-02 | Phase 7 | Pending |
| MNT-03 | Phase 7 | Pending |
| MNT-04 | Phase 7 | Pending |
| MNT-05 | Phase 7 | Pending |
| MNT-06 | Phase 7 | Pending |
| TRN-02 | Phase 8 | Complete |
| TRN-03 | Phase 8 | Complete |
| TRN-04 | Phase 8 | Complete |
| TRN-05 | Phase 8 | Complete |
| SCM-01 | Phase 9 | Complete |
| SCM-02 | Phase 9 | Complete |
| SCM-03 | Phase 9 | Complete |
| SCM-04 | Phase 9 | Complete |
| SCM-05 | Phase 9 | Pending |
| SRV-01 | Phase 10 | Complete |
| SRV-02 | Phase 10 | Complete |
| SRV-03 | Phase 10 | Complete |
| SRV-04 | Phase 10 | Complete |
| SRV-05 | Phase 10 | Complete |
| UI-01 | Phase 10 | Complete |
| UI-02 | Phase 10 | Complete |
| UI-03 | Phase 10 | Complete |
| UI-04 | Phase 10 | Complete |
| UI-05 | Phase 10 | Complete |
| UI-06 | Phase 10 | Complete |
| UI-07 | Phase 10 | Complete |
| UI-08 | Phase 10 | Complete |
| UI-09 | Phase 10 | Complete |
| UI-10 | Phase 10 | Complete |
| OBS-02 | Phase 11 | Complete |
| OBS-03 | Phase 11 | Complete |
| OBS-04 | Phase 11 | Complete |
| OBS-05 | Phase 11 | Complete |
| OBS-06 | Phase 11 | Complete |
| OBS-07 | Phase 11 | Complete |
| SEC-01 | Phase 11 | Complete |
| SEC-02 | Phase 11 | Complete |
| SEC-03 | Phase 11 | Complete |
| SEC-04 | Phase 11 | Complete |
| SEC-05 | Phase 11 | Complete |
| SEC-06 | Phase 11 | Complete |
| SEC-07 | Phase 11 | Complete |
| DOC-01 | Phase 12 | Pending |
| DOC-02 | Phase 12 | Pending |
| DOC-03 | Phase 12 | Pending |
| DOC-04 | Phase 12 | Pending |
| DOC-06 | Phase 12 | Pending |
| DOC-07 | Phase 12 | Pending |
| DOC-08 | Phase 12 | Pending |
| DOC-09 | Phase 12 | Pending |
| DOC-10 | Phase 12 | Pending |
| DOC-11 | Phase 12 | Complete |
| DOC-13 | Phase 12 | Pending |
| DOC-14 | Phase 12 | Pending |
| DOC-15 | Phase 12 | Pending |
| DOC-16 | Phase 12 | Pending |
| DOC-17 | Phase 12 | Pending |
| ECO-01 | Phase 12 | Pending |
| ECO-02 | Phase 12 | Complete |
| ECO-03 | Phase 12 | Pending |
| ECO-04 | Phase 12 | Pending |
| ECO-05 | Phase 12 | Complete |
| ECO-06 | Phase 12 | Pending |
| ECO-07 | Phase 12 | Pending |
| ECO-08 | Phase 12 | Pending |
| DEL-01 | Phase 12 | Pending |
| DEL-02 | Phase 12 | Pending |
| DEL-03 | Phase 12 | Pending |
| DEL-04 | Phase 12 | Pending |
| DEL-05 | Phase 12 | Pending |
| DEL-06 | Phase 12 | Pending |
| DEL-07 | Phase 12 | Pending |
| DEL-08 | Phase 12 | Pending |

**Coverage:**
- v1 requirements: **135 totali** (PLAT 10, CORE 10, HITL 10, IOT 10, KNW 10, OPS 6, MNT 6, TRN 5, SCM 5, UI 10, SRV 5, OBS 7, SEC 7, DOC 18, ECO 8, DEL 8)
- Mapped to phases: **135/135** (100%)
- Unmapped: **0**

---
*Requirements defined: 2026-05-16*
*Last updated: 2026-05-16 after roadmap creation — traceability table populated*
