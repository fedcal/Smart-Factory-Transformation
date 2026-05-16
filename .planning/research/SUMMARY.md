# Project Research Summary

**Project:** Smart Factory Transformation
**Domain:** Opensource agentic platform — textile manufacturing, HITL governance, IT/OT simulation, OEPV economic context
**Researched:** 2026-05-16
**Confidence:** HIGH (core architecture and stack); MEDIUM (LLM serving tradeoffs, OEPV formula details, simulator fidelity)

---

## Executive Summary

Smart Factory Transformation is an opensource, self-hostable agentic platform for textile manufacturing, built around Human-in-the-Loop governance as the primary, non-negotiable architectural constraint. It is not a MES replacement or an analytics dashboard: it is an AI coordination layer that places 16 scoped agents between raw operational data and human decision-makers, ensuring every irreversible action is approved, explained, and audited before execution. All four research threads converged independently on the same structural conclusion: HITL is not a feature to add; it is the load-bearing wall of the entire design. Any component, agent, or pattern that bypasses or weakens HITL must be treated as an anti-feature.

The recommended approach, supported by both the architecture and stack research, is a hierarchical LangGraph supervisor with four cluster subgraphs (Operations, Maintenance, Knowledge, Supply Chain), served by Qwen2.5 self-hosted via Ollama (development) or vLLM (production), with Qdrant for hybrid dense+sparse RAG, TimescaleDB for sensor time-series, NATS JetStream as the IT/OT event bus, and Langfuse for LLM observability. The monorepo is Nx with the `@nxlv/python` plugin for polyglot Python+Angular support. Build order is strictly dependency-driven: foundation infrastructure and the IT/OT simulation layer must exist before agents can be exercised on real data flows, and the HITL policy layer must exist before any agent is exposed to production-affecting decisions. The six-phase macro-structure — Foundation, HITL Core, IT/OT Simulation, Knowledge Layer, Agent Clusters + Frontend, Observability + Docs + Economics — reflects the hard dependency graph, not an arbitrary sequencing preference.

The two project-critical risks that all four research threads identified independently are: (a) the simulator fidelity gap — agents tuned on clean synthetic data will fail when exposed to real-world noise, and this gap must be addressed by injecting adversarial patterns (NaN, out-of-order timestamps, sensor drift, burst duplicates) into the simulator from the first sprint; and (b) the OEPV economic model accuracy — the procurement scoring model must include GPU amortization, electricity at real industrial tariffs, and partial FTE operations cost, or the ribasso calculation will be either too aggressive (triggering anomaly verification under Codice Appalti) or non-credible to evaluators.

---

## Key Findings

### Recommended Stack

The stack is effectively locked at the project level with strong research validation on every choice. The only meaningful open questions are within the LLM serving tier (Ollama vs. vLLM in CI environments) and the graph database tier (Neo4j Community vs. Memgraph OSS). All other technology decisions are confirmed by official documentation and multiple corroborating sources.

The LLM tier deserves special attention because it determines hardware requirements, concurrent throughput, and developer experience simultaneously. The research prescribes a strict split: Ollama with Qwen2.5-7B Q4_K_M for developer machines and CI smoke tests (low VRAM requirement, simple setup), and vLLM with Qwen2.5-14B AWQ for production or multi-user concurrent scenarios (793 tok/s vs. Ollama's 41 tok/s). The 14B AWQ model at approximately 10 GB VRAM is the sweet spot for PoC quality versus hardware accessibility. Going below Q4_K_M quantization (Q2, Q3) crosses a nonlinear quality cliff where function calling and structured JSON output reliability degrades unacceptably for industrial agent workflows.

**Core technologies:**
- **Nx 20.x + @nxlv/python 21.x**: Monorepo orchestrator with first-class Python+Angular polyglot support; `nx affected` for CI-selective builds is essential in a 16-agent monorepo
- **LangGraph 0.4+**: Agentic orchestration with native `interrupt()` / `Command(resume=)` HITL, inspectable state machine, pluggable PostgreSQL checkpointer (v3.1.0)
- **Qwen2.5 7B/14B (Ollama dev / vLLM prod)**: Apache 2.0, excellent multilingual IT/EN function calling, self-hostable; 14B AWQ on a single 16-24 GB GPU is the reference target
- **Qdrant 1.16+**: Self-hosted vector store with BM42 hybrid search (dense + sparse); MIT license; on-prem first
- **BGE-M3**: Primary embedding model; MIT license; triple output (dense + sparse + multi-vector); 8192-token context; multilingual-e5-large-instruct as A/B test candidate for Italian-language retrieval
- **PostgreSQL 16 + TimescaleDB 2.x**: Unified relational + time-series store; LangGraph checkpointer target; TimescaleDB hypertables for sensor data (SQL JOIN compatibility with operational data is decisive over InfluxDB)
- **NATS JetStream 2.10+**: IT/OT event bus; 820K msg/s; native MQTT bridge for OPC-UA; single binary; durable streams for audit replay
- **asyncua (opcua-asyncio) 1.0+**: OPC-UA client/server for IT/OT simulation; async-native Python; `python-opcua` (synchronous, deprecated) must not be used
- **FastAPI 0.115+**: Agent API gateway and service layer; async-first; OpenAPI auto-generated
- **Angular 18+ with SSR**: Frontend locked by project owner; `@nx/angular:setup-ssr` generator; esbuild integrated; touch-friendly for factory-floor use
- **Langfuse v3 (self-hosted)**: LLM observability; MIT license; OTEL-native; PostgreSQL + ClickHouse backend; LangSmith is ruled out (closed-source, SaaS, data leaves factory)
- **DeepEval 1.x (CI gate) + RAGAS 0.2+ (production monitoring)**: Dual-framework RAG evaluation; DeepEval blocks PRs on hallucination rate > 5%; RAGAS as weekly CronJob sampling Langfuse traces
- **MkDocs Material 9.5+ with i18n plugin**: Bilingual IT/EN documentation; GitHub Pages deploy via `mkdocs gh-deploy`

### Expected Features

All four research threads confirm that HITL governance is not one feature among many — it is the prerequisite that every other feature depends on. The dependency graph in the features research makes this concrete: the HITL Policy Layer is required by all 16 agents, the audit trail, and the OEPV compliance argument. No agent should ship before the HITL skeleton exists.

**Must have — table stakes (evaluators and operators will check for these immediately):**
- HITL approval gate (Tier 0-4 escalation model) on every non-trivial agent action — absence disqualifies the platform from industrial trust
- Immutable audit trail: agent proposal, reviewer identity, decision, timestamp, rationale
- Agent action explainability: every recommendation carries a structured `rationale` field; no opaque outputs
- Override and rollback of any agent decision, logged to audit trail
- OEE, MTBF, MTTR dashboard with authoritative formulas (world-class targets: OEE >= 85%, Availability >= 90%, Quality >= 99.5%)
- Real-time sensor/event ingestion pipeline (mock OPC-UA -> NATS -> agent subscriptions)
- Structured downtime event log (prerequisite for MTBF, MTTR, RCA, predictive maintenance)
- RAG over seeded SOPs and technical manuals (hybrid dense+sparse, multilingual IT/EN)
- Per-user RBAC (operator / supervisor / technician / manager) — without RBAC the HITL tier model breaks
- Shift handover auto-report (reduces 15-30 minute verbal handover to under 3 minutes)
- Self-hostable deployment (Docker Compose + optional Kubernetes); no mandatory external API calls
- Bilingual documentation IT/EN (MkDocs Material i18n)

**Should have — differentiators vs. Siemens Opcenter, Rockwell FactoryTalk, Tulip:**
- 16 reference agents as working code with concrete tool bindings (not dashboard widgets or chat interfaces)
- Textile-specific defect taxonomy embedded in QualityInspector (4-point grading, dye lot tracking, shade deviation alerting with CIELab delta)
- RUL (Remaining Useful Life) estimation on textile machinery using NASA C-MAPSS methodology adapted to spindle/loom failure modes
- Multi-cluster agent orchestration with inspectable LangGraph state machine (fully visible vs. commercial black boxes)
- OEPV ribasso simulator (unique to this platform; no commercial MES ships procurement scoring tools)
- Python SDK for custom agent development (uniform interface: tools, memory, policy hooks, HITL hooks)
- Bi-directional context between agent clusters (Maintenance findings feed QualityInspector; Quality alerts feed PredictiveMaintenance)
- Knowledge reuse rate KPI (queries resolved from KB vs. escalated; no commercial platform tracks this)
- Energy per unit KPI with ISO 50001 framing (wet processing = 60% of textile energy; kWh/kg against EnPI baseline)
- OEPV TCO 3-year model with GPU amortization, electricity, and ops FTE allocation

**Defer to v2+:**
- DemandForecaster with fashion seasonality signals (requires historical demand data not available in PoC)
- DocumentationSynthesizer with multilingual output (requires real document corpus)
- CostAnalyzer full ROI/TCO/OEPV (partial v1; full model in v2)
- LoRA fine-tuning of Qwen2.5 on textile vocabulary (requires evaluation dataset; use RAG instead in v1)
- Computer vision optical defect detection (requires specialized hardware and image corpus; explicitly out of scope)
- MaintenanceCoach LOTO procedure retrieval (safety-critical content needs expert vetting before deployment)
- Angular PWA for offline factory-floor tablet support

### Architecture Approach

The architecture follows a Hierarchical Supervisor + Cluster Subgraph pattern in LangGraph, placed squarely on the IT side of the ISA-95 Purdue model (Levels 3-5), with a strict one-way OT Ingestion Bridge as the sole interface to the simulated OT zone (Levels 0-2). The OT Bridge is a data-diode: it publishes sensor events to NATS but cannot receive write-back commands from agents. This boundary is enforced at the network level (Docker network ACLs, NATS subject ACL restricting agent subscriptions) and documented with explicit OPC-UA security mode enforcement (SignAndEncrypt even in simulation). Four data planes are kept separate: real-time sensor (OT-derived, TimescaleDB), relational/transactional (PostgreSQL), document/knowledge (Qdrant + Neo4j, batch-ingested), and event/audit (NATS AUDIT_STREAM with 90-day retention, append-only).

**Major components:**
1. **OT Simulator + OT Bridge** — Python asyncua server emitting textile sensor streams (loom, spinner, warper, dyeing, stenter); bridge normalizes and publishes to NATS; agents never touch OPC-UA directly
2. **LangGraph Supervisor Graph** — top-level routing graph; the sole HITL interrupt owner; delegates to four cluster subgraphs; holds cross-cluster state; checkpointed to PostgreSQL for pause-resume durability across shift boundaries
3. **Four Cluster Subgraphs** — Operations, Maintenance, Knowledge, Supply Chain; each owns a typed state schema and a defined tool set; independently testable; communicate via NATS (never direct HTTP)
4. **HITL Approval Flow** — LangGraph `interrupt()` to PostgreSQL checkpoint to NATS `hitl.approval.pending.*` to API Gateway SSE to Angular UI to human decision to `hitl.approval.decision.*` to `Command(resume=)` to audit record; full sequence is durable across server restarts
5. **API Gateway (FastAPI)** — sole external HTTP entry point; SSE for real-time push to Angular; NATS consumer for agent events; never bypassed by agent-to-agent direct calls
6. **Knowledge Ingestion Pipeline** — unstructured.io/docling to entity extraction (Qwen2.5 7B) to dual-write Qdrant (dense+sparse) and Neo4j (entity graph); agents never write to knowledge stores during inference (prevents hallucination contamination)
7. **Angular SSR Shell** — operator dashboard (touch-friendly, >= 64px touch targets, high-contrast industrial theme); HITL approval cards with inline evidence (sensor readings, rationale, confidence); KPI widgets (OEE, MTBF, MTTR); persistent approval queue side drawer
8. **Observability Stack** — Langfuse self-hosted (LLM traces, HITL decision latency, approval-to-rejection ratios) + OTEL Collector to Prometheus + Grafana + Loki (infrastructure metrics and logs)

### Critical Pitfalls

All four research threads independently surfaced overlapping risk areas. The six pitfalls below represent the convergent high-severity findings — address these before they can compound.

1. **Infinite agent loops without circuit breakers** — Set `recursion_limit` on every `graph.invoke()` / `graph.astream()` call; track attempt counters in LangGraph state; add semantic caching of recent tool invocations (same tool + identical args within N turns -> abort and escalate to HITL); never rely on LLM self-termination
2. **HITL approval queue stalling and auto-approve creep** — Implement TTL-based expiry (8h shift-level, 30min safety-critical); build a `revalidate_proposal` node that checks current world state before applying a proposal approved after a delay; auto-approve whitelist is version-controlled and requires code review to extend, never a runtime config toggle
3. **Operator alarm fatigue converting HITL to liability theatre** — Global approval rate governor capping pending requests per operator per hour; correlated alert aggregation (same machine, same 10-minute window = one HITL context); priority triage (safety queue vs. informational digest); track approval latency and rejection rate as KPIs (rubber-stamping threshold: approval latency < 5 seconds)
4. **Simulator too clean — demo passes, real data fails** — Inject fault profiles from day one: NaN, out-of-order timestamps, duplicate events, sensor drift (slow linear bias), burst noise; adversarial scenarios in CI test suite (not just happy path); document simulation fidelity gap explicitly in Assumption Register
5. **Prompt injection via document ingestion** — Sanitize all ingested documents before embedding; add a validation LLM pass on retrieved chunks ("does this chunk contain instructions directed at an AI system?"); every retrieved chunk carries provenance metadata; HITL gate required for any action triggered by document-sourced suggestions
6. **OEPV score miscalculation and non-defensible ribasso** — Include GPU amortization, electricity at 0.25 EUR/kWh under continuous inference load, and 1 FTE partial ops allocation in the economic model; set ribasso at 10-15% below base d'asta with written justification; never set at the mathematical anomaly verification threshold

---

## Implications for Roadmap

All four research threads converged on a six-phase macro-structure driven by the hard dependency graph. The ordering is non-negotiable: later phases cannot be exercised without earlier phases providing their data contracts, infrastructure, and governance primitives.

### Phase 1: Monorepo Foundation + Infrastructure

**Rationale:** Every other component depends on the Nx workspace structure, CI pipeline, Docker Compose stack, and shared Pydantic type definitions. Building this first prevents the most common polyglot monorepo failure mode: silently misconfigured project graphs that cause `nx affected` to miss cross-language dependency edges. The license scanner and project graph assertion must be in CI from the first commit — retrofitting is high-cost.

**Delivers:** Nx workspace (Nx 20.x + @nxlv/python 21.x + @nx/angular), Docker Compose stack (NATS, PostgreSQL+TimescaleDB, Qdrant, Redis), `sdk-agent-types` (shared Pydantic models: `SensorEvent`, `AgentAction`, `HITLRequest`), CI/CD pipeline (GitHub Actions, `nrwl/nx-set-shas`, affected commands, `pip-licenses` + `license-checker` gates), MkDocs Material skeleton (IT/EN structure, GitHub Pages deploy)

**Addresses:** Monorepo structure requirement; bilingual documentation baseline; Docker Compose self-hosted deployment constraint

**Avoids:** Pitfall 16 (Nx polyglot graph misconfiguration); Pitfall 20 (OSS license conflicts); Pitfall 12 (OPC-UA boundary violations — enforce network topology from Docker Compose day one)

**Research flag:** Well-documented patterns — standard Nx + GitHub Actions CI. No additional research phase needed.

---

### Phase 2: HITL Core + Agentic Skeleton

**Rationale:** The HITL policy layer is architecturally non-negotiable and must be built before any agent is exposed to production-affecting decisions. All four research files named HITL as the load-bearing constraint. Building the supervisor graph skeleton (routing only, no real agents) and the full HITL approval loop (interrupt to checkpoint to NATS to API to SSE to Angular to resume to audit) means every subsequent agent inherits governance by default rather than retrofitting it.

**Delivers:** LangGraph supervisor graph skeleton (routing, HITL interrupt nodes, PostgreSQL checkpointer v3.1.0), HITL approval loop (full sequence from interrupt to audit record), `sdk-agent-python` (AgentBase, ToolBase, HITLHook interface, recursion_limit enforcement), API Gateway (FastAPI + NATS consumer + SSE endpoint), LLM server (Ollama + Qwen2.5-7B first run, provider-agnostic adapter), RBAC policy layer (four roles minimum), audit trail (append-only, agent-write-only)

**Addresses:** HITL approval gate (table stakes #1); audit trail; explainability; override/rollback; RBAC

**Avoids:** Pitfall 1 (infinite loops — recursion_limit enforced in SDK); Pitfall 2 (HITL stalling — TTL expiry and revalidation node designed here); Pitfall 6 (VRAM exhaustion — hardware requirements and adapter pattern locked here)

**Research flag:** LangGraph HITL patterns are well-documented. The recursion_limit enforcement and TTL expiry node design may need one planning-phase research pass focused on LangGraph advanced patterns if the team is new to LangGraph checkpointing.

---

### Phase 3: IT/OT Simulation Layer

**Rationale:** Agents cannot be meaningfully exercised without realistic sensor data flows. The simulator must be built with adversarial fault injection from the start (not added later), because the pitfalls research makes clear that retrofitting realistic noise profiles after agents have been tuned on clean data is a project-killing rework cycle. The OT Bridge (asyncua -> NATS) must enforce the data-diode boundary at the network layer, not just in code, because the architecture research shows this boundary is the primary security control.

**Delivers:** Textile factory simulator (Python asyncua server: loom, spinner, warper, dyeing, stenter sensors with configurable fault injection profiles — NaN, drift, jitter, burst), OT Ingestion Bridge (asyncua client to NATS publisher, schema validation, rate limiter, data-diode ACL), NASA C-MAPSS + UCI dataset replay scripts, adversarial test suite (5 fault profiles in CI), ambient humidity and temperature signals in all sensor streams

**Addresses:** Sensor ingestion pipeline (table stakes); downtime event log (prerequisite for all monitoring agents)

**Avoids:** Pitfall 4 (simulator too clean); Pitfall 9 (humidity/seasonal blindness — humidity signals from day one); Pitfall 11 (machine-noise vs. anomaly — per-machine calibration config required in simulator design); Pitfall 12 (Purdue model boundary violation — network segmentation enforced here)

**Research flag:** Custom textile simulator design has no off-the-shelf template. This phase benefits from a planning-phase research pass on industrial loom and spinning machine sensor signatures to ensure the simulated profiles are defensible to domain-expert evaluators.

---

### Phase 4: Knowledge Layer (RAG + Graph)

**Rationale:** Knowledge agents (OperatorAssistant, MaintenanceCoach, TrainingCoach) are useless with an empty vector store. The ingestion pipeline must be built — including multilingual retrieval validation, access control tags on every chunk, and the document sanitization step — before any knowledge-dependent agent is integrated. The pitfalls research explicitly warns that multilingual retrieval (Italian query to English document) degrades measurably without evaluation, and that prompt injection via ingested PDFs is an OWASP LLM01:2025 class vulnerability.

**Delivers:** Document ingestion pipeline (unstructured.io/docling to entity extraction to dual-write Qdrant + Neo4j), BGE-M3 embedding with BM42 hybrid search, cross-lingual retrieval evaluation (Italian + English query test set), document access control tags (role-based payload filter on every vector search), document sanitization step (validation LLM pass on retrieved chunks), seeded knowledge base (loom troubleshooting SOPs, dye procedures, maintenance manuals — synthetic but representative), Neo4j schema (machine to part to failure-mode to SOP), textile defect taxonomy document in knowledge base

**Addresses:** RAG over SOPs (table stakes); KnowledgeCurator baseline; cross-language retrieval quality

**Avoids:** Pitfall 5 (prompt injection — sanitization pipeline built here); Pitfall 7 (stale RAG index — event-driven incremental indexing designed here); Pitfall 13 (multilingual RAG confusion — evaluation before agent integration); Pitfall 17 (citation hallucination — inline source display and citation verification step); Pitfall 19 (sensitive document leakage — access control tags on all chunks)

**Research flag:** BGE-M3 vs. multilingual-e5-large-instruct final choice requires A/B evaluation on actual Italian textile documents. Plan for a short evaluation sprint (2-3 days) at the start of this phase before committing to the embedding model. The Neo4j Community license cap (4 GB heap) may become binding for a production knowledge graph; verify whether Memgraph OSS is preferable before schema design is finalized.

---

### Phase 5: Agent Clusters + Frontend

**Rationale:** With the HITL skeleton, IT/OT simulation, and knowledge layer in place, the 16 agents can be built in dependency order within each cluster. Operations agents come first (OperatorAssistant is the simplest RAG agent and provides the first end-to-end HITL demo); Maintenance agents require TimescaleDB sensor history; Knowledge agents require the full ingestion pipeline; Supply Chain agents require relational data and are last because CostAnalyzer depends on outputs from all three peer clusters. The Angular frontend is built in parallel with agent clusters once the API Gateway contract is stable.

**Delivers — Operations cluster first:** AnomalyDetector (multivariate anomaly scoring with textile-specific sensor profiles, per-machine calibration, dye lot context), OperatorAssistant (procedure lookup, alert acknowledgment, shift status summary), QualityInspector (4-point grading, shade deviation alerting, NCR draft), ProductionPlanner (schedule generation, replan on disruption, work order draft)

**Delivers — Maintenance cluster:** PredictiveMaintenance (RUL estimation, NASA C-MAPSS adapted to spindle/loom), RCASpecialist (5-Why chains, fishbone, fault-symptom pattern matching), MaintenanceCoach (procedure retrieval, MTTR logging), DowntimeAnalyzer (Pareto, OEE decomposition, downtime cost)

**Delivers — Knowledge cluster:** KnowledgeCurator (ingestion approval, duplicate detection, reuse rate KPI), TrainingCoach (skill gap detection, competency assessment, training completion rate), ShiftHandover (auto-compile from event log, dual-supervisor HITL sign-off, target < 3 minutes)

**Delivers — Supply Chain cluster:** InventoryManager (reorder alerts, purchase recommendations, dye lot inventory), EnergyOptimizer (energy per unit KPI, ISO 50001 EnPI baseline, wet process focus), CostAnalyzer (downtime cost, scrap cost, ROI aggregation, OEPV ribasso simulator), DemandForecaster (demand signal to ProductionPlanner — v1 stub; full model v2)

**Delivers — Angular frontend:** Control room dashboard (agent state, KPI widgets, alert queue), HITL approval UI (64px touch targets, inline evidence panel, SSE listener, persistent side drawer), OEE/MTBF/MTTR widgets, operator and technician user journeys, bilingual UI (Italian primary, English toggle), high-contrast factory-floor theme

**Addresses:** All 16 reference agents; OEE/MTBF/MTTR dashboard; shift handover; HITL approval UI; OEPV ribasso simulator

**Avoids:** Pitfall 3 (alarm fatigue — global rate governor, correlated alert aggregation built into agent cluster integration); Pitfall 8 (textile defect taxonomy mismatch — taxonomy document required in knowledge base before QualityInspector integration); Pitfall 10 (dye lot variability — dye lot ID mandatory in every quality inspection event); Pitfall 15 (demo-driven development — adversarial tests required for every agent at three scenarios: happy path, degraded input, failure/escalation)

**Research flag:** Individual agent designs within each cluster will benefit from planning-phase research during Phase 5 planning. PredictiveMaintenance RUL adaptation from C-MAPSS to textile machinery, and AnomalyDetector per-machine calibration design, are the highest-uncertainty areas. Each cluster is a reasonable candidate for `--research-phase` during roadmap plan-phase invocation.

---

### Phase 6: Observability + Documentation + Economics

**Rationale:** Observability infrastructure can be built in parallel with Phases 4-5 but is formalized and completed here. The documentation deliverable (bilingual MkDocs, architecture docs, use case prioritization, threat model) and the economic model (OEPV, TCO, ROI dashboard) are competition deliverables that require all agents to exist before they can be accurately described and costed. This phase also includes the Assumption Register, which must explicitly document the simulation fidelity gap and all scoping decisions.

**Delivers:** Langfuse self-hosted deployment (PostgreSQL + ClickHouse + Redis + MinIO), OTEL instrumentation across all agents and FastAPI, Prometheus + Grafana dashboards (CPU, GPU, VRAM, NATS lag, Qdrant latency), Loki log aggregation, DeepEval CI gate (hallucination rate <= 5%, answer relevance >= 0.75), RAGAS weekly CronJob (faithfulness + context precision on 5% Langfuse trace sample), bilingual MkDocs documentation (Target Architecture, End-to-End Workflows, Use Cases, Mock UI/User Journey, Adoption Roadmap), OEPV economic model with full TCO (GPU amortization, electricity at 0.25 EUR/kWh, 1 FTE partial ops), ribasso sensitivity analysis, threat model, Assumption Register, final Helm chart for Kubernetes production deployment

**Addresses:** Langfuse observability; bilingual documentation; OEPV model; threat model; Assumption Register

**Avoids:** Pitfall 14 (OEPV miscalculation — electricity and ops salary explicitly in model); Pitfall 15 (demo-driven development — architecture docs describe implemented system, not aspirational one)

**Research flag:** The OEPV formula simulation (linear / bilinear / non-linear scoring under the Codice Appalti framework) requires someone familiar with Italian public procurement law to validate. This is the most under-researched area across all four research files and warrants a dedicated planning-phase research pass, particularly on the ribasso anomalo threshold and the 70/30 criterion weighting sub-criteria mapping.

---

### Phase Ordering Rationale

The six-phase ordering reflects four hard dependency constraints that all four research files independently identified:

1. **HITL before agents** — The features research states explicitly: "HITL Policy Layer must exist before any agent ships; agents without governance are anti-features." Building HITL in Phase 2 (not Phase 5) makes governance the default, not a retrofit.

2. **Simulator before agent data flows** — Agents exercised on flat JSON mocks never encounter missing values, jitter, or burst duplicates. The simulator must provide adversarial data from the start. Phase 3 before Phase 5 enforces this.

3. **Knowledge layer before knowledge-dependent agents** — The features research dependency graph makes this explicit: "RAG store must be seeded before knowledge agents are useful; empty vector store = useless coaching." Building the ingestion pipeline and evaluating multilingual retrieval before integrating OperatorAssistant or MaintenanceCoach prevents the most common RAG anti-pattern.

4. **CostAnalyzer last among agents** — The features research states: "CostAnalyzer depends on all three peer clusters; it is the last agent to become useful; build it in the final phase."

The critical path for a minimum viable HITL demonstration is: Phase 1 (monorepo + Docker Compose) to Phase 2 (HITL skeleton + API Gateway) to Phase 3 (simulator + OT bridge) to Phase 5 start (AnomalyDetector + OperatorAssistant). This path produces one complete, auditable HITL loop end-to-end and is the minimum credible demo for competition evaluators.

### Research Flags

Phases likely needing deeper research during plan-phase:
- **Phase 3 (IT/OT Simulation):** Textile-specific sensor signatures (loom resonance profiles, spindle vibration patterns, dyeing bath dynamics) are not covered by generic industrial datasets. Planning research should source textile machinery specifications or academic references for realistic simulator calibration.
- **Phase 5 — Maintenance cluster (PredictiveMaintenance):** Adapting NASA C-MAPSS RUL methodology to textile machinery failure modes (spindle bearing degradation, traveller wear, heddle fatigue) requires domain-specific validation that the research files flagged but did not resolve.
- **Phase 5 — Operations cluster (AnomalyDetector):** Per-machine calibration design (baseline calibration phase, machine-type-specific threshold configuration) needs detailed design before implementation.
- **Phase 6 (OEPV Economics):** Italian public procurement formula mechanics (ribasso anomalo thresholds, Codice Appalti 2023 sub-criteria weighting interpretation, TAR Sicily 1181/2025 implications) are the most under-researched area and need a dedicated research pass with a procurement-law-informed reviewer.

Phases with well-documented patterns where standard implementation applies:
- **Phase 1 (Foundation):** Nx + @nxlv/python + GitHub Actions CI is well-documented. Official docs and plugin documentation are sufficient.
- **Phase 2 (HITL Core):** LangGraph HITL patterns (`interrupt()`, `AsyncPostgresSaver`, `Command(resume=)`) are thoroughly documented in official LangGraph docs. Standard patterns apply.
- **Phase 4 (Knowledge Layer):** Qdrant hybrid search setup, BGE-M3 FastEmbed integration, and unstructured.io document parsing follow well-documented library patterns. The A/B evaluation between BGE-M3 and multilingual-e5 is the only non-standard element.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every technology choice validated against official documentation and multiple corroborating sources. The Ollama vs. vLLM CI concern and BGE-M3 vs. multilingual-e5 final choice are the only open questions. |
| Features | HIGH | Textile manufacturing domain well-documented in academic and industry sources. HITL governance patterns verified against LangGraph docs and industrial AI guidance. KPI formulas are authoritative. |
| Architecture | HIGH | LangGraph, Nx, Qdrant, NATS all from official docs. ISA-95 Purdue model placement for agentic systems is inferred from edge-computing patterns (MEDIUM for that specific sub-topic). |
| Pitfalls | HIGH | Multiple corroborating sources across all major categories. Operator alarm fatigue threshold, Therac-25 HITL habituation, OPC-UA 92% misconfiguration, OEPV TAR Sicily 1181/2025 all from verifiable primary sources. |

**Overall confidence:** HIGH for architecture, stack, features, and risk identification. MEDIUM for OEPV formula specifics and textile simulator signal profiles (both require domain-expert validation).

### Gaps to Address

The following open questions should be resolved before or during the planning phase for the affected phase. They do not block roadmap creation but must be tracked.

- **vLLM vs. Ollama in CI:** Stack research recommends Ollama for CI smoke tests (low resource requirement); pitfalls research flags that Ollama hangs under sustained concurrent load on Linux. Recommended resolution: use Ollama for single-shot smoke tests in CI (no concurrency), and use vLLM only if integration tests require concurrent inference. Decision should be made explicit in the Phase 2 plan.
- **Neo4j Community vs. Memgraph OSS:** Architecture research flags Neo4j Community's 4 GB heap limit as potentially binding for a production knowledge graph. Memgraph OSS has no such cap. Evaluate heap requirements against expected entity counts before schema design in Phase 4.
- **BGE-M3 vs. multilingual-e5-large-instruct final choice:** Run the A/B evaluation on actual Italian textile documents at the start of Phase 4 and record results in the Phase 4 plan.
- **Hardware spec for reference deployment:** State as a concrete requirement (minimum: NVIDIA GPU with 16 GB VRAM, recommended: 24 GB) in the Phase 2 deliverable and in ARCHITECTURE.md. Pitfalls research requires this to be explicit before agents are built.
- **Real Mantis SOPs vs. synthetic corpus:** The Assumption Register (Phase 6 deliverable) must explicitly state: all SOPs are synthetic, all sensor data is simulated, and all KPI baselines are modeled. Evaluators who probe this boundary need a prepared answer.
- **Competition deadline:** The OEPV evaluation is the primary external forcing function. The deadline is not documented in any research file and must be confirmed with the project owner before roadmap phase durations are set.

---

## Sources

### Primary (HIGH confidence)
- LangGraph official docs: HITL patterns, `interrupt()`, `AsyncPostgresSaver`, `Command(resume=)`, checkpointing backends
- LangGraph checkpoint-postgres PyPI 3.1.0: version confirmed, setup requirements
- Qdrant official docs: BM42 (v1.10+), ACORN (v1.14+), FastEmbed integration, 1.16 release notes
- @nxlv/python npm: uv workspace support confirmed
- Nx Angular setup-ssr generator docs: SSR generator, esbuild integration
- ANSI/ISA-95.00.01-2025 update (industrialcyber.co): containerized workloads, cloud-hybrid placement
- Langfuse vs. LangSmith comparison (langfuse.com): MIT license, self-hosting, OTEL integration
- Langfuse v3 Docker Compose (github.com/langfuse/langfuse): PostgreSQL + ClickHouse + Redis + MinIO dependencies
- asyncua GitHub (FreeOpcUa/opcua-asyncio): async-native, 35K downloads/week, LGPL license
- Qwen2.5 speed benchmark (qwen.readthedocs.io): throughput 7B/14B/32B confirmed
- OPC-UA 92% misconfiguration finding (eprint.iacr.org/2025/148.pdf): formal security analysis
- Operator alarm fatigue threshold 12 alarms/hour (brainboxai.com): industrial management reference
- Therac-25 HITL habituation failure (aijourn.com): well-documented historical case
- Yarn breakage seasonal/environmental correlation (IEEE Xplore 9395528): peer-reviewed
- OEPV ribasso anomalo and TAR Sicily 1181/2025 (biblus.acca.it): Italian public procurement
- Apache 2.0 / GPL compatibility (apache.org): official source
- MMTEB benchmark 2025 (arxiv.org/abs/2502.13595): multilingual embedding benchmarks, peer-reviewed
- Ollama production limitations 4 parallel requests, Linux hang (spheron.network): confirmed from multiple sources

### Secondary (MEDIUM confidence)
- vLLM vs. Ollama production benchmark 2026 (codersera.com): 793 tok/s vs. 41 tok/s — benchmarks are environment-specific; directionally correct
- NATS JetStream vs. Redis Streams 2026 (javacodegeeks.com): throughput comparison, IoT suitability
- TimescaleDB review 2026 (modern-datatools.com): JOIN capability, sensor data use cases
- BGE-M3 vs. Jina comparison (VIPS): embedding model comparison
- Best embedding models for multilingual RAG (knightli.com): multilingual-e5 recommendation
- Qwen2.5 32B VRAM requirements (apxml.com): estimate, not official
- LLM quantization Q4_K_M vs. AWQ vs. FP16 (sitepoint.com): quality cliff below Q4_K_M confirmed
- Demo-vs-production gap in agentic AI (dev.to): HIGH directional confidence, MEDIUM source authority
- Multilingual RAG Italian/English evaluation (MDPI 2504-2289/9/5/141): peer-reviewed, MEDIUM on direct applicability to BGE-M3

### Tertiary (LOW confidence — validate during planning)
- OEPV sub-criteria weighting mechanics (vincenzogliottone.it): Italian procurement formula simulation — needs legal-domain validation
- Textile machinery vibration resonance profiles: no primary source found; must be sourced from machinery manufacturers or academic references during Phase 3 planning research
- ISA-95 Purdue model placement for agentic AI systems: placement is logical extrapolation from edge-computing patterns; no agentic AI-specific guidance in the standard

---

*Research completed: 2026-05-16*
*Ready for roadmap: yes*
