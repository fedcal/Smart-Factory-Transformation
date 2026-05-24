# Roadmap: Smart Factory Transformation

## Overview

The platform is built in 12 horizontal layers, each completing one coherent technical capability before the next begins. The dependency chain is non-negotiable: infrastructure before agents, HITL governance before any agent touches production decisions, IT/OT simulation before sensor-dependent agents, knowledge layer before knowledge-dependent agents, then four domain agent clusters, followed by backend API plus frontend, observability and security hardening, and finally documentation with economic deliverables. Every v1 requirement maps to exactly one phase.

## Phases

- [x] **Phase 1: Foundation & Monorepo** - Nx polyglot workspace, Docker Compose dev stack, GitHub Actions CI, license scanner, shared infra services (completed 2026-05-16)
- [x] **Phase 2: Domain Modeling & Synthetic Corpus** - Textile domain analysis, defect taxonomy, asset registry schema, synthetic SOP corpus IT+EN (completed 2026-05-18)
- [x] **Phase 3: IT/OT Simulation Layer** - Python textile simulator with OPC-UA, fault injection, OT Bridge data-diode, TimescaleDB ingest, dataset replay (completed 2026-05-18)
- [x] **Phase 4: Core Agentic Runtime & HITL** - LangGraph supervisor + cluster subgraphs skeleton, PG checkpointer, LLM adapter, full HITL interrupt loop, audit trail (completed 2026-05-18)
- [ ] **Phase 5: Knowledge Layer (RAG + Graph)** - Qdrant collections, BGE-M3 embeddings, document ingest pipeline, provenance, ACL, entity graph, hybrid retrieval (functional 2026-05-19; 3 gap-closure plans in progress 2026-05-19)
- [x] **Phase 6: Agents — Operations & Production** - OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector with cluster tests (completed 2026-05-23)
- [x] **Phase 7: Agents — Maintenance & Reliability** - PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer with tests (completed 2026-05-23)
- [x] **Phase 8: Agents — Knowledge & Training** - KnowledgeCurator, TrainingCoach, ShiftHandover, DocumentationSynthesizer with tests (completed 2026-05-24)
- [ ] **Phase 9: Agents — Supply Chain & Economics** - InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster with tests
- [x] **Phase 10: Backend API & Frontend** - FastAPI gateway, SSE/WebSocket, RBAC, Angular Universal app, HITL UI, control room dashboard, i18n IT/EN, E2E tests (completed 2026-05-24)
- [ ] **Phase 11: Observability, Evaluation & Security Hardening** - OTEL across services, Langfuse traces, LGTM dashboards, RAG/agent evals in CI, STRIDE threat model, OWASP LLM mitigations
- [ ] **Phase 12: Documentation, Economic Model & Competition Deliverables** - MkDocs Material i18n, all doc sections, OEPV simulator, TCO, ribasso analysis, deliverable bundle, brand-scrub CI check

## Phase Details

### Phase 1: Foundation & Monorepo
**Goal**: The Nx polyglot workspace is fully operational with Docker Compose dev stack, CI/CD pipeline, license scanning, and all shared infrastructure services running locally.
**Depends on**: Nothing (first phase)
**Requirements**: PLAT-01, PLAT-02, PLAT-03, PLAT-04, PLAT-05, PLAT-06, PLAT-07, PLAT-08, PLAT-09, PLAT-10, OBS-01
**Success Criteria** (what must be TRUE):
  1. `make up` starts all dev services (PostgreSQL+TimescaleDB, Qdrant, NATS JetStream, Ollama, Langfuse) in a single Docker Compose command with no manual configuration
  2. `nx affected --target=test` runs only the changed packages and correctly resolves Python-to-TypeScript dependency edges in the Nx project graph
  3. A PR with a GPL-licensed transitive dependency is blocked automatically by the CI license scanner before merging
  4. Pre-commit hooks (ruff, mypy strict, eslint, prettier) execute on every commit and fail fast on violations
  5. A Helm chart skeleton deploys the core services to a local Kubernetes cluster without error
**Plans**: 8 plans
  - [ ] 01-PLAN-01-nx-workspace.md — Nx polyglot workspace skeleton (PLAT-01, PLAT-02, PLAT-03)
  - [ ] 01-PLAN-02-compose.md — Docker Compose dev stack (PLAT-05 partial via Makefile, PLAT-07, PLAT-09, OBS-01)
  - [ ] 01-PLAN-03-license-scanner.md — Syft + Trivy SBOM license scanner (PLAT-05)
  - [ ] 01-PLAN-04-pre-commit.md — Pre-commit hooks + Conventional Commits + gitleaks (PLAT-06)
  - [ ] 01-PLAN-05-ci.md — GitHub Actions CI with nx affected + Nx/uv cache (PLAT-04, PLAT-08 implicit, OBS-01 dev-only)
  - [ ] 01-PLAN-06-helm.md — Helm umbrella + per-service charts + k3d smoke test + SealedSecrets (PLAT-08)
  - [ ] 01-PLAN-07-mkdocs.md — MkDocs Material i18n scaffold + gh-pages deploy (PLAT-10 docs side)
  - [ ] 01-PLAN-08-changesets.md — Changesets versioning + release.yml (PLAT-10 release side)

### Phase 2: Domain Modeling & Synthetic Corpus
**Goal**: The textile manufacturing domain is fully modeled in structured documents and a synthetic bilingue SOP corpus is seeded in the repository, providing the knowledge foundation for all downstream agents and documentation.
**Depends on**: Phase 1
**Requirements**: DOC-05, DOC-12, DOC-18, KNW-10
**Success Criteria** (what must be TRUE):
  1. A textile domain analysis document exists in `docs/` covering processes (weaving, spinning, warping, dyeing, finishing), roles (operator, technician, quality manager, shift supervisor), and pain points with explicit references to Mantis Textile Group
  2. An assumption register enumerates all data quality assumptions, simulation boundaries, and scope limitations — with each assumption tagged by affected agent or component
  3. A bilingual (IT+EN) glossary of textile and agentic terms is complete and linked from the docs index
  4. At least 20 synthetic SOP documents (10 IT + 10 EN) covering loom troubleshooting, dyeing procedures, spinning maintenance, and quality grading are committed to `simulators/synthetic-corpus/` and pass a format validation check in CI
**Plans**: 7 plans
  - [x] 02-01-PLAN.md — Schemas + Pydantic glossary loader + bootstrap glossary (~70 terms) + pytest scaffold (DOC-18 foundation)
  - [x] 02-02-PLAN.md — Domain analysis IT (5 process + 4 role + index) + pytest structural tests (DOC-05 IT side)
  - [x] 02-03-PLAN.md — Assumption register schema + 30 seed entries + validator + components-check + generator (DOC-12 part 1)
  - [x] 02-04-PLAN.md — synthetic-corpus Nx project + 5 example IT SOPs + 3 corpus validators (KNW-10 foundation)
  - [x] 02-05-PLAN.md — Remaining 15 IT SOPs + all 20 EN SOPs + 10 EN domain pages + glossary expansion to ≥150 (KNW-10 + DOC-05 EN + DOC-18 esaustivo)
  - [x] 02-06-PLAN.md — Assumption register expansion to 50 + glossary schema/coverage scripts + 6 Nx targets + CI wiring (DOC-12 close + DOC-18 gates live)
  - [x] 02-07-PLAN.md — mkdocs nav + tags plugin + SOP indexes + regenerate derived content + D-25 user review checkpoint + mkdocs strict build + Phase 2 sign-off (all 4 requirements close) (completed 2026-05-18)

### Phase 3: IT/OT Simulation Layer
**Goal**: A Python textile factory simulator emits realistic adversarial sensor streams via asyncua OPC-UA, a data-diode OT Bridge publishes events to NATS JetStream, TimescaleDB ingests time-series data, and NASA C-MAPSS plus UCI dataset replay scripts are available as tools.
**Depends on**: Phase 1
**Requirements**: IOT-01, IOT-02, IOT-03, IOT-04, IOT-05, IOT-06, IOT-07, IOT-08, IOT-09, IOT-10
**Success Criteria** (what must be TRUE):
  1. The simulator emits sensor events for loom, spinner, warper, dyehouse, and stenter assets including ambient temperature and humidity; fault injection produces NaN, drift, jitter, burst noise, and alarm storms configurable per asset
  2. The OT Bridge publishes to NATS `sensor.events.*` subjects and is demonstrably incapable of receiving write commands from agents (Docker network ACL verified in an automated test)
  3. TimescaleDB hypertables ingest sensor events at sustained throughput with latency p99 below 200ms under a 5,000 msg/s load test
  4. NASA C-MAPSS and UCI Manufacturing dataset replay scripts execute without error and surface data to agents via standard tool interface
  5. The ingest schema (asset registry, tag dictionary, units of measure) is documented with working examples
**UI hint**: no
**Plans**: 7 plans
  - [x] 03-01-PLAN.md — packages/sft-assets (Pydantic models + loader + JSON Schema + 30 asset seed + validator + Makefile) (IOT-09)
  - [x] 03-02-PLAN.md — packages/sft-tools (replay_cmapss + replay_uci + query_timescale LangChain Tools + SHA256 download script) (IOT-07, IOT-08)
  - [x] 03-03-PLAN.md — sim-textile (asyncua server multi-namespace + 5 YAML fault profiles + pure-function fault state machine + Prometheus metrics + Dockerfile) (IOT-01, IOT-02, IOT-03)
  - [x] 03-04-PLAN.md — ot-bridge (SensorEvent + normalizer + NATS publisher D-52 + asyncpg writer + data-diode Layer 3 + Dockerfile + nats-bootstrap script) (IOT-04, IOT-05)
  - [x] 03-05-PLAN.md — TimescaleDB migration (hypertable + compression(7d) + retention(90d) + idempotent runner + [BLOCKING] schema-push) (IOT-06)
  - [x] 03-06-PLAN.md — docker-compose dual-network (sft-ot/sft-core) + 3-layer data-diode test + OPC-UA browseable + NATS subjects + E2E + smoke load 1k×10s + CI wiring (IOT-02, IOT-04, IOT-05, IOT-10 smoke)
  - [x] 03-07-PLAN.md — full load test 5k×60s (PR-label gated) + MkDocs IT/OT docs IT+EN (ingest-schema + opcua-schema) (IOT-09, IOT-10 full)

### Phase 4: Core Agentic Runtime & HITL
**Goal**: The LangGraph supervisor graph with five cluster subgraph skeletons (Operations, Maintenance, Knowledge-Curation, Knowledge-Training, Supply per D-53), PostgreSQL checkpointer, provider-agnostic LLM adapter, full HITL interrupt-to-resume loop, 4-tier escalation model, and immutable audit trail are operational end-to-end.
**Depends on**: Phase 1, Phase 3
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06, CORE-07, CORE-08, CORE-09, CORE-10, HITL-01, HITL-02, HITL-03, HITL-04, HITL-05, HITL-06, HITL-07, HITL-08, HITL-09, HITL-10
**Success Criteria** (what must be TRUE):
  1. A full HITL cycle completes end-to-end: agent proposes action → LangGraph `interrupt()` fires → state persists to PostgreSQL → NATS publishes approval request → human decision resumes the graph → audit record is written to the immutable append-only PG table and NATS AUDIT_STREAM
  2. The SDK `recursion_limit` is enforced on every `graph.invoke()` call; a graph exceeding the limit escalates to HITL rather than crashing
  3. The LLM adapter switches between Ollama (Qwen2.5-7B Q4_K_M) and vLLM (Qwen2.5-14B AWQ) by changing one environment variable with no code changes in agents
  4. A paused HITL approval thread survives a full service restart and resumes correctly from the PostgreSQL checkpoint
  5. The approval rate governor fires an alert to the Manager role when more than 80% of consecutive actions are auto-approved
**Plans**: 8 plans
  - [x] 04-01-sdk-foundation-PLAN.md — Pydantic models + ABC interfaces + Wave 0 stub set (CORE-01, CORE-02, HITL-06, HITL-07)
  - [x] 04-02-pg-migrations-PLAN.md — 4 idempotent SQL migrations (002 hitl.approvals, 003 audit.actions+outbox+REVOKE, 004 budget.executions, 005 langgraph schema) + scripts/langgraph-init.py + [BLOCKING] migration push (CORE-04, CORE-08, CORE-09, HITL-05)
  - [x] 04-03-llm-adapter-PLAN.md — LLM_BACKEND={ollama,vllm} factory + BudgetingChatModel + Langfuse v3 callback + tool registry + vLLM Hermes serving docs (CORE-05, CORE-06, CORE-07)
  - [x] 04-04-nats-audit-stream-PLAN.md — AUDIT_STREAM bootstrap (90d) + AuditNatsPublisher + injection-safe subject derivation (CORE-08, HITL-05)
  - [x] 04-05-supervisor-clusters-checkpointer-PLAN.md — supervisor StateGraph + 5 cluster subgraphs + 16 placeholder children + HybridRouter + AsyncPostgresSaver wiring + safe_invoke recursion_limit→HITL (CORE-02, CORE-03, CORE-04, CORE-07)
  - [x] 04-06-hitl-middleware-PLAN.md — interrupt/resume node + AuditWriter dual-write + outbox retry + SafetyInterlockMiddleware + EscalationSupervisor + Governor + BudgetTracker + GDPRRedactor + EpisodicReplay (HITL-01..10, CORE-08, CORE-09)
  - [x] 04-07-api-gateway-e2e-PLAN.md — FastAPI scaffold + lifespan + /v1/approvals + /v1/threads/{id}/resume + Idempotency-Key + E2E HITL cycle surviving docker compose restart (HITL-01, HITL-04, CORE-04)
  - [x] 04-08-replay-roadmap-docs-PLAN.md — replay_thread tool + mkdocs agentic-runtime + hitl-cycle pages + [BLOCKING] ROADMAP edit (CORE-10, HITL-08)

### Phase 5: Knowledge Layer (RAG + Graph)
**Goal**: Qdrant collections with BGE-M3 hybrid retrieval, a document ingest pipeline with provenance and access control, incremental re-indexing, and a Neo4j/Memgraph entity graph are operational and validated for bilingual Italian-English retrieval quality.
**Depends on**: Phase 1, Phase 2, Phase 4
**Requirements**: KNW-01, KNW-02, KNW-03, KNW-04, KNW-05, KNW-06, KNW-07, KNW-08, KNW-09, TRN-01
**Success Criteria** (what must be TRUE):
  1. An Italian-language query for a procedure described only in an English SOP returns the correct document chunk with a relevance score above the configured threshold, verified in an automated cross-lingual eval suite
  2. Every indexed chunk carries `source_uri`, `page`, `version`, `lang`, and access level tag; a query from an `operator`-role user cannot retrieve `restricted`-tagged chunks
  3. A document update triggers incremental re-indexing of only the changed chunks within the configured staleness threshold; full reindex is not triggered
  4. The entity graph contains machine → part → failure-mode → SOP relationships for all asset classes in the simulator; a traversal query returns a valid SOP for a given failure mode
  5. The BGE-M3 vs multilingual-e5-large A/B evaluation results are documented in `docs/` with a justified model selection decision

**KNW-04 scope note:** Phase 5 ships MarkdownParser only. The DocumentParser ABC enables PDF/DOCX/HTML parsers in Phase 8 KnowledgeCurator (scoping deviation from literal KNW-04; documented in CONTEXT.md D-67).

**Plans**: 13 plans (10 original + 3 gap closure)
  - [x] 05-01-sft-knowledge-sdk-PLAN.md — sft-knowledge SDK scaffold + Pydantic models + MarkdownParser (KNW-04, KNW-05)
  - [x] 05-02-acl-migration-PLAN.md — acl_level migration script + 41 SOP frontmatter update + validator extension (KNW-06)
  - [x] 05-03-failure-modes-yaml-PLAN.md — failure_modes.yaml + loader + 30+ entries + CI validator (KNW-08)
  - [x] 05-04-qdrant-bootstrap-PLAN.md — 4-collection bootstrap script + integration test (KNW-01)
  - [x] 05-05-neo4j-compose-bootstrap-PLAN.md — Neo4j 5.24 compose + bootstrap + Helm + APOC (KNW-08 infra)
  - [x] 05-06-pg-migration-ingest-state-PLAN.md — migration 006 + state.py + knowledge-ingest scaffold (KNW-07, TRN-01)
  - [x] 05-07-embedding-chunking-PLAN.md — BgeM3Embedder + SemanticChunker (KNW-02)
  - [x] 05-08-indexer-graph-builder-PLAN.md — QdrantIndexer + Neo4jGraphBuilder (KNW-05, KNW-08)
  - [x] 05-09-retrieval-pipeline-tools-memory-PLAN.md — RetrievalPipeline + RagSearchTool + TraverseGraphTool + QdrantLongTermMemory (KNW-06, KNW-09)
  - [x] 05-10-ingest-service-cli-ci-eval-docs-PLAN.md — Typer CLI + pipeline + reindex.yml + A/B eval + MkDocs (KNW-03, KNW-04, KNW-07, TRN-01)
  - [x] 05-11-PLAN.md — gap-closure: TraverseGraphTool._arun defense-in-depth Pydantic re-validation (KNW-09 / CR-01 BLOCKER)
  - [x] 05-12-PLAN.md — gap-closure: shared sft_knowledge.path_utils.derive_source_uri helper for parser+orchestrator (KNW-07 / CR-02 BLOCKER)
  - [x] 05-13-PLAN.md — gap-closure: --skip-eval→--stub rename + Preliminary stub metrics admonition on MkDocs IT/EN eval pages (KNW-03 / IN-05)

### Phase 6: Agents — Operations & Production
**Goal**: All four Operations cluster agents (OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector) are implemented with full HITL integration, textile-specific domain knowledge, and passing end-to-end tests on simulated scenarios.
**Depends on**: Phase 3, Phase 4, Phase 5
**Requirements**: OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-06
**Success Criteria** (what must be TRUE):
  1. OperatorAssistant retrieves the correct loom troubleshooting procedure from the RAG store in response to a natural-language Italian-language query and cites the source chunk inline
  2. QualityInspector applies the textile defect taxonomy (broken end, mispick, slub, neppy, selvage fault, shade deviation, unlevel dyeing) and 4-point grading to a simulated inspection event, routes to the correct HITL tier, and includes dye lot ID in every quality event
  3. AnomalyDetector scores a real-time sensor anomaly with per-machine calibration, does not fire false positives on normal high-frequency loom vibration, and enforces the 12-alert/hour rate limit
  4. ProductionPlanner generates a schedule draft and routes it to supervisor-level HITL before release
  5. Each agent's end-to-end test covers three scenarios: happy path, degraded sensor input, and failure/escalation path
**Plans**: 15 plans
  - [x] 06-00-PLAN.md — Wave 0 test scaffolds + 12 scenario YAML/JSONL stubs + conftest extensions (OPS-05, OPS-06)
  - [x] 06-01-PLAN.md — Migration 007 extend audit.actions decision+action_type CHECK; sync Decision/ActionType enums (OPS-04, OPS-05)
  - [x] 06-02-PLAN.md — RateLimiter PG-backed sliding window 12/h (OPS-04)
  - [x] 06-03-PLAN.md — MockReplayChatModel + LLM_BACKEND=mock factory branch (OPS-05, OPS-06)
  - [x] 06-04-PLAN.md — sft-domain ops models + scheduling heuristic SPT/EDD + orders/capacity/baselines YAML + failure_modes.yaml hitl_tier extension (OPS-01..04)
  - [x] 06-05-PLAN.md — EscalateToSupervisorTool + LogEventTool + build_ops_subgraph router (OPS-01, OPS-05)
  - [x] 06-06-PLAN.md — AnomalyDetector agent + baseline + rate-limit + audit (OPS-04)
  - [x] 06-07-PLAN.md — QualityInspector agent + NATS qi-consumer + LLM 4-point grader + HITL tier routing + QUALITY_STREAM bootstrap (OPS-03, OPS-05)
  - [x] 06-08-PLAN.md — ProductionPlanner agent + LLM rationale + supervisor HITL (OPS-02)
  - [x] 06-09-PLAN.md — sim-textile QualityEvent generator + ProductionState dye_lot rotation (OPS-03)
  - [x] 06-10-PLAN.md — OperatorAssistant agent: create_react_agent + 5-tool toolbelt + langdetect + citation validator (OPS-01, OPS-05)
  - [x] 06-11-PLAN.md — agents-scheduler APScheduler 5-min cron container + Docker + Helm (OPS-04)
  - [x] 06-12-PLAN.md — api-gateway endpoints: /v1/quality/events + /v1/agents/{slug}/{action} (OPS-01..04)
  - [x] 06-13-PLAN.md — 12 E2E scenarios (4 agents × happy/degraded/failure) with testcontainers + mock LLM (OPS-06)
  - [x] 06-14-PLAN.md — Agent docs IT+EN (8 pages) + evidence_panel unit tests + mkdocs nav (OPS-05)

### Phase 7: Agents — Maintenance & Reliability
**Goal**: All four Maintenance cluster agents (PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer) are implemented with C-MAPSS-adapted RUL estimation, 5-Why RCA, humidity-aware modeling, and integration with the asset registry and event store.
**Depends on**: Phase 3, Phase 4, Phase 5
**Requirements**: MNT-01, MNT-02, MNT-03, MNT-04, MNT-05, MNT-06
**Success Criteria** (what must be TRUE):
  1. PredictiveMaintenance estimates Remaining Useful Life for spindle, loom, and warper assets using degradation curves adapted from NASA C-MAPSS methodology; the model feature set includes ambient temperature and humidity sensors
  2. RCASpecialist generates a 5-Why chain for a simulated downtime event, cites knowledge base sources with provenance, and routes the corrective action recommendation to supervisor-level HITL
  3. MaintenanceCoach retrieves the correct step-by-step procedure from the RAG store for the current repair, tracks MTTR contribution, and escalates when the technician requests it
  4. DowntimeAnalyzer calculates OEE decomposition (Availability, Performance, Quality) and produces a Pareto of downtime causes from the event store
  5. A textile maintenance event taxonomy is documented and used consistently across all four agents
**Plans**: 17 plans (13 original + 4 gap closure)
  - [x] 07-00 through 07-12 — original maintenance cluster build (4 agents + taxonomy + gateway + E2E) (MNT-01..06)
  - [x] 07-13-PLAN.md — gap-closure: MaintenanceCoach saver lifecycle (CR-01) + single audit row on resume (WR-02) (MNT-03 / SC-3)
  - [x] 07-14-PLAN.md — gap-closure: RCASpecialist direct-interrupt audit ordering (CR-02) + populated tool_calls_log (WR-05) (MNT-02 / SC-2)
  - [x] 07-15-PLAN.md — gap-closure: PredictiveMaintenance null approval_id (CR-03) + safe missing-asset_id ValueError (CR-04) (MNT-01 / SC-1)
  - [x] 07-16-PLAN.md — gap-closure: DowntimeAnalyzer gateway datetime (WR-03) + Pareto grand_total (WR-04) + bounded by_asset (CR-05) (MNT-04 / SC-4)

### Phase 8: Agents — Knowledge & Training
**Goal**: All four Knowledge cluster agents (KnowledgeCurator, TrainingCoach, ShiftHandover, DocumentationSynthesizer) are implemented with citation provenance, adaptive training delivery, automated shift handover compilation, and bilingual document synthesis under HITL approval.
**Depends on**: Phase 4, Phase 5
**Requirements**: TRN-02, TRN-03, TRN-04, TRN-05
**Success Criteria** (what must be TRUE):
  1. ShiftHandover auto-compiles a structured handover report from the shift's event log (open alerts, completed work orders, equipment status, quality events) in under 3 minutes of elapsed time, with dual-supervisor HITL sign-off
  2. TrainingCoach delivers a contextual coaching session to an operator persona, assesses competency via quiz, and routes the competency sign-off to supervisor HITL before recording
  3. KnowledgeCurator detects a duplicate document during ingest, flags a stale document beyond its staleness threshold, and tracks the knowledge reuse rate KPI
  4. DocumentationSynthesizer generates a bilingual SOP draft from historical maintenance events and routes it to HITL approval before indexing; every output includes `source_uri` and timestamp
  5. All TRN agent outputs include citations with `source_uri` and timestamp; no opaque outputs are accepted by the test suite
**Plans**: 10 plans
  - [x] 08-00a-PLAN.md — Wave 1: migration 010 + ActionType enum lockstep + migration test (D-X-01)
  - [x] 08-00b-PLAN.md — Wave 1: all agent test scaffolds — Nyquist tests before impl (TRN-02/03/04/05)
  - [x] 08-01-PLAN.md — build_knowledge_subgraph + curator fallback (D-X-04)
  - [x] 08-02-PLAN.md — ShiftHandover data layer: models + cross-cluster aggregator (D-SH-02, TRN-03/05)
  - [x] 08-04-PLAN.md — ShiftHandover dual-supervisor HITL agent + NATS shift.boundary consumer (D-SH-01/03, SC-1)
  - [x] 08-05-PLAN.md — TrainingCoach deterministic quiz + dynamic difficulty + supervisor sign-off (D-TC-01/02/03, SC-2)
  - [x] 08-06-PLAN.md — KnowledgeCurator autonomous hybrid dedup + staleness + reuse-rate KPI (D-KC-01/02/03/04, SC-3)
  - [x] 08-07-PLAN.md — DocumentationSynthesizer bilingual SOP + citation re-anchoring + pre-index HITL (D-DS-01/02/03, SC-4)
  - [x] 08-08-PLAN.md — knowledge_agents.py gateway router + lifespan DI wiring (D-X-04)
  - [x] 08-09-PLAN.md — four-agent E2E + TRN-05 opaque-output rejection + bilingual docs (SC-5)

### Phase 9: Agents — Supply Chain & Economics
**Goal**: All four Supply Chain cluster agents (InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster) are implemented with realistic Mantis Textile Group example data, OEPV ribasso simulation, ISO 50001 energy tracking, and HITL-gated purchase recommendations.
**Depends on**: Phase 4, Phase 5, Phase 6, Phase 7
**Requirements**: SCM-01, SCM-02, SCM-03, SCM-04, SCM-05
**Success Criteria** (what must be TRUE):
  1. InventoryManager fires a reorder alert when a SKU falls below its reorder point, generates a purchase recommendation draft, and routes it to procurement supervisor HITL before any order action
  2. EnergyOptimizer calculates energy per unit (kWh/kg) for dyeing and finishing processes against an ISO 50001 EnPI baseline and recommends off-peak scheduling via HITL-gated proposal
  3. CostAnalyzer aggregates downtime cost, scrap cost, and energy cost into an ROI dashboard and produces a OEPV ribasso simulation with sensitivity analysis
  4. DemandForecaster produces a demand plan for at least two fabric SKU groups, publishes it to ProductionPlanner via HITL-gated approval, and tracks forecast accuracy KPI
  5. Realistic numerical examples for Mantis Textile Group (product lines, capacity, unit costs) are documented explicitly as synthetic in `docs/`
**Plans**: 11 plans (8 waves)
  - [x] 09-00a-PLAN.md — Migration 011 (scm.* schema) + migration 012 (audit ActionType enum/CHECK lockstep, 8 Phase 9 action types) + migration tests (SCM-01, SCM-02, SCM-04, SCM-05)
  - [x] 09-00b-PLAN.md — Nyquist agent test-contract scaffolds for all 4 supply agents (tests before implementation) (SCM-01, SCM-02, SCM-03, SCM-04)
  - [x] 09-01-PLAN.md — build_supply_subgraph (fallback cost-analyzer) + Mantis synthetic seed dataset + seed smoke test (SCM-01, SCM-02, SCM-04, SCM-05)
  - [x] 09-02-PLAN.md — InventoryManager: reorder-point logic + repository + HITL agent (interrupt-then-audit, stable id) (SCM-01)
  - [x] 09-03-PLAN.md — EnergyOptimizer: ISO 50001 EnPI + repository + off-peak HITL agent (SCM-02)
  - [x] 09-04-PLAN.md — CostAnalyzer: parametric OEPV ribasso simulator + cost aggregator + autonomous agent (Decision.AUTO) (SCM-03, ECO-02, ECO-05)
  - [x] 09-05-PLAN.md — DemandForecaster: Holt-Winters + rolling MAPE + HITL agent publishing to ProductionPlanner via state (SCM-04)
  - [x] 09-06-PLAN.md — API gateway supply_agents.py router + DI wiring (build_supply_subgraph) with Phase 8 boundary fixes (SCM-01..04, SEC-02)
  - [x] 09-07-PLAN.md — Four-agent supply cluster E2E against the Mantis seed (per-agent audit-row counts, OEPV, cross-cluster plan) (SCM-01..05)
  - [x] 09-08-PLAN.md — Bilingual IT+EN supply-cluster docs + Mantis synthetic-dataset page + mkdocs nav (SCM-05)


### Phase 10: Backend API & Frontend
**Goal**: The FastAPI gateway with JWT/RBAC, SSE/WebSocket streaming, and the Angular 18+ SSR application with HITL approval UI, evidence panel, control room dashboard, bilingual i18n, touch-friendly design, and Playwright E2E tests are production-ready.
**Depends on**: Phase 4, Phase 6, Phase 7, Phase 8, Phase 9
**Requirements**: SRV-01, SRV-02, SRV-03, SRV-04, SRV-05, UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10
**Success Criteria** (what must be TRUE):
  1. An operator persona can log in, see the control room dashboard with live OEE, MTTR, MTBF, scrap rate KPIs streamed via SSE, and approve or reject a pending HITL action with the inline evidence panel visible — all with touch targets at minimum 64px
  2. The Angular app renders correctly via SSR on first load and hydrates to a full SPA; Italian is the default language and English toggles without page reload
  3. A Playwright E2E test covering the full HITL approval flow (alert fires → approval card appears → operator reviews evidence → approves → audit record created) passes in CI
  4. The FastAPI OpenAPI spec exports correctly, Pydantic models and TypeScript types are contract-tested, and all endpoints have health/readiness probes with OTEL spans
  5. The persona walkthrough demo (operator, shift supervisor, technician, CIO) is navigable in-app with no broken routes or missing data
**UI hint**: yes
**Plans**: 13 plans (11 waves, sequential on main tree — worktrees disabled)
  - [x] 10-00a-PLAN.md — Wave 0 dependency install (PyJWT/sse-starlette/OTEL backend; @angular/material+cdk+localize, @jsverse/transloco, ng2-charts@8, chart.js, tailwind v4, playwright) + Tailwind/Material 64px baseline (SRV-01/02/04, UI-02/04/05/07/10)
  - [x] 10-00b-PLAN.md — Wave 0 Nyquist test scaffolds (pytest auth/RBAC/SSE/KPI; Jest Jwt/SSE/ApprovalCard) (SRV-01/02/05, UI-03/04/07, HITL-07/10)
  - [x] 10-01-PLAN.md — Backend JWT issuance + RBAC dependency + auth router (SRV-01, HITL-02)
  - [x] 10-02-PLAN.md — Backend real KPI aggregations over TimescaleDB + GET /v1/kpi (SRV-02, UI-04)
  - [x] 10-03-PLAN.md — Backend SSE streams + query-param JWT + HITL-10 rate limit + OTEL middleware + migration 013 seed (SRV-02/04, UI-06, HITL-10)
  - [x] 10-04-PLAN.md — Frontend foundation: design tokens + dark/light Material themes + responsive AppShell + persona routes (UI-01/02/05)
  - [x] 10-05-PLAN.md — Frontend core services: JwtService/interceptor/RbacGuard + Signal SseService + ThemeService + transloco LocaleService (UI-05/06/07, SRV-01)
  - [x] 10-06-PLAN.md — Frontend HITL UI: login + dev persona chips + toggles + ApprovalCard + EvidencePanel (UI-02/03/05/07, HITL-01/06/07)
  - [x] 10-07-PLAN.md — Frontend dashboard primitives: KpiTile + AlertFeed (rate-limit banner) + virtual-scroll ApprovalQueueFeed (UI-02/04/06, HITL-04/10)
  - [x] 10-08-PLAN.md — Frontend features: operator area + manager control room (6 KPI grid + ng2-charts) + route wiring (UI-01/04/06, HITL-01/04)
  - [x] 10-09-PLAN.md — Frontend features: technician + admin (audit log + governor) + persona walkthrough demo (UI-01/08, HITL-04/09)
  - [x] 10-10-PLAN.md — Playwright E2E: separate Nx project apps/factory-ui-e2e + full HITL approval flow (UI-10, HITL-01/06/07)
  - [x] 10-11-PLAN.md — Pydantic↔TS contract test (openapi-typescript) + bilingual mock-UI screenshots (SRV-05, UI-09)

### Phase 11: Observability, Evaluation & Security Hardening
**Goal**: OpenTelemetry instrumentation spans all services, Langfuse traces every LLM call, Grafana dashboards expose agent and factory KPIs, DeepEval gates PRs on hallucination rate, and STRIDE threat model mitigations are implemented including OWASP LLM Top 10 defenses.
**Depends on**: Phase 4, Phase 5, Phase 10
**Requirements**: OBS-02, OBS-03, OBS-04, OBS-05, OBS-06, OBS-07, SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, SEC-07
**Success Criteria** (what must be TRUE):
  1. A single trace ID propagates from the Angular UI through the FastAPI gateway, through the NATS agent command, to the LangGraph node execution, and appears as a single correlated trace in Langfuse with LLM token counts, latency, and HITL decision metadata
  2. A PR introducing a RAG change that degrades hallucination rate above 5% or answer relevance below 0.75 is automatically blocked by the DeepEval CI gate before merge
  3. A crafted PDF containing prompt-injection instructions is sanitized during document ingestion and does not influence any subsequent agent action, verified by a security test in CI
  4. The STRIDE threat model document identifies at least one threat per category (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) for IT/OT boundary, RAG ingestion, and agent orchestration; each threat has a documented mitigation mapped to code
  5. The OT Bridge data-diode boundary is verified by an automated network policy test that attempts to send a write command from the agent layer into the OPC-UA simulator and confirms it is blocked
**Plans**: 6 plans (3 waves)
  - [x] 11-00-PLAN.md — Wave 1: infra/deps/scaffolds (obs.yml Grafana/Prometheus/Tempo, OTEL package, migration 014, eval scaffolds, Langfuse/RAGAS verify)
  - [x] 11-01-PLAN.md — Wave 2: OTEL trace propagation end-to-end gateway→NATS→agent (OBS-02)
  - [x] 11-02-PLAN.md — Wave 2: DeepEval+RAGAS deterministic CI gate (OBS-05/06)
  - [x] 11-03-PLAN.md — Wave 2: security hardening — auditor RBAC, sanitizer, OT AST guard, restricted audit (SEC-03/04/06/07)
  - [x] 11-04-PLAN.md — Wave 3: Grafana dashboards JSON + LGTM doc (OBS-03/04/07)
  - [ ] 11-05-PLAN.md — Wave 3: STRIDE doc + OWASP LLM + secrets/.env.example + AR-01..07 closure (SEC-01/02/05)

### Phase 12: Documentation, Economic Model & Competition Deliverables
**Goal**: The complete bilingual MkDocs Material documentation site is deployed to GitHub Pages covering all required sections, the OEPV economic model with TCO and ribasso simulator is complete and defensible, all competition deliverables are bundled, and a CI check confirms zero references to Accenture or the original brand.
**Depends on**: Phase 2, Phase 10, Phase 11
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-06, DOC-07, DOC-08, DOC-09, DOC-10, DOC-11, DOC-13, DOC-14, DOC-15, DOC-16, DOC-17, ECO-01, ECO-02, ECO-03, ECO-04, ECO-05, ECO-06, ECO-07, ECO-08, DEL-01, DEL-02, DEL-03, DEL-04, DEL-05, DEL-06, DEL-07, DEL-08
**Success Criteria** (what must be TRUE):
  1. `mkdocs build` produces a complete bilingual (IT default, EN parallel) site with no broken links; GitHub Actions deploys it to `gh-pages` branch and the site is publicly accessible via GitHub Pages
  2. The OEPV economic model document contains: Base d'Asta €108,000, GPU amortization over 3 years, electricity at 0.25 EUR/kWh under continuous inference, 1 FTE partial ops allocation, ribasso set at 10-15% below base d'asta with written justification, and a non-linear scoring sensitivity analysis table
  3. All six competition deliverables (Target Architecture, End-to-End Workflows, Use Cases, Mock UI/User Journey, Adoption Roadmap, Economic Evaluation) are present as complete sections in `docs/` with no aspirational content that is not implemented in code
  4. A CI grep scan finds zero occurrences of "Accenture" or the original brand name across all files in the repository, including generated docs
  5. All diagrams in `docs/` are Mermaid or D2 source files committed as text; no binary diagram images are present in the repository
**UI hint**: yes
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Monorepo | 8/8 | Complete   | 2026-05-16 |
| 2. Domain Modeling & Synthetic Corpus | 10/7 | Complete   | 2026-05-18 |
| 3. IT/OT Simulation Layer | 7/7 | Complete   | 2026-05-18 |
| 4. Core Agentic Runtime & HITL | 8/8 | Complete   | 2026-05-18 |
| 5. Knowledge Layer (RAG + Graph) | 10/10 | Complete   | 2026-05-19 |
| 6. Agents — Operations & Production | 15/15 | Complete   | 2026-05-23 |
| 7. Agents — Maintenance & Reliability | 17/17 | Complete   | 2026-05-23 |
| 8. Agents — Knowledge & Training | 10/10 | Complete   | 2026-05-24 |
| 9. Agents — Supply Chain & Economics | 8/10 | In Progress|  |
| 10. Backend API & Frontend | 13/13 | Complete    | 2026-05-24 |
| 11. Observability, Evaluation & Security Hardening | 5/6 | In Progress|  |
| 12. Documentation, Economic Model & Competition Deliverables | 0/TBD | Not started | - |
