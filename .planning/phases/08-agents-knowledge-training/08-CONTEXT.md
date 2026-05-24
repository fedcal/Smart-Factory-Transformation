# Phase 8: Agents — Knowledge & Training - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the four Knowledge cluster agents — **ShiftHandover**, **TrainingCoach**, **KnowledgeCurator**, **DocumentationSynthesizer** — with citation provenance (`source_uri` + timestamp on every output), adaptive training delivery, automated shift-handover compilation, and bilingual document synthesis under HITL approval. Requirements: TRN-02, TRN-03, TRN-04, TRN-05 (TRN-01 RAG-ingest foundation was delivered in Phase 5).

Agent packages already scaffolded under `apps/agents/knowledge/{knowledge-curator,training-coach,shift-handover,documentation-synthesizer}` (prefix `trn_*`, only `__init__.py` present). This phase implements their business logic, mirroring the Phase 6/7 cluster pattern.

Out of scope: Supply Chain & Economics agents (InventoryManager/EnergyOptimizer/CostAnalyzer/DemandForecaster, SCM-* = Phase 9); frontend/UI (Phase 10).
</domain>

<decisions>
## Implementation Decisions

### ShiftHandover
- **D-SH-01:** Trigger = scheduled shift boundary (configurable, e.g. 06:00/14:00/22:00) auto-compilation **plus** manual on-demand start by a supervisor. A "shift" is defined by configurable boundary times.
- **D-SH-02:** Data sources = `audit.actions` cross-cluster (ops/maintenance) within the shift window **plus** direct queries to source tables (alerts, work_orders, downtime_events) for extra detail. Hybrid: audit chain as backbone, direct tables for completeness.
- **D-SH-03:** Sign-off = **dual-supervisor sequential**: outgoing-shift supervisor approves, then incoming-shift supervisor confirms takeover. Two distinct HITL audit rows. Must complete within <3 min elapsed.

### TrainingCoach
- **D-TC-01:** Quiz format = **deterministic multiple-choice** (closed questions with known answer keys). Questions may be RAG-curated from SOPs, but scoring is exact and testable without an LLM-judge.
- **D-TC-02:** Adaptivity = **per role/persona content selection + dynamic difficulty** (difficulty rises/falls based on prior answers within the session).
- **D-TC-03:** Pass threshold = **configurable, default 0.80**. On pass, competency sign-off is routed to **supervisor HITL before recording** (criterion #2).

### KnowledgeCurator
- **D-KC-01:** Duplicate detection = **hybrid hash + embedding**: SHA-256 of normalized text for fast exact-dup, then BGE-M3 cosine similarity (Phase 5 embedder) against the index with a configurable threshold for near-duplicates.
- **D-KC-02:** Staleness = **per-document-type configurable thresholds** (e.g. SOP 365d, runbook 180d, note 90d). A doc past its type threshold is flagged stale.
- **D-KC-03:** Reuse-rate KPI = **distinct documents cited / total indexed documents** over a rolling window, computed from the `source_uri` citations already emitted by TRN/MNT agents.
- **D-KC-04:** KnowledgeCurator is **autonomous** (no HITL) — dedup and staleness are read/flag operations with no irreversible action.

### DocumentationSynthesizer
- **D-DS-01:** Bilingual output = **generate primary language (IT) then translate to EN** in a second pass. **Constraint for research/planning:** the translation pass MUST re-anchor `source_uri` + timestamp citations so they do not drift from the IT source (the simultaneous-generation alternative was declined; mitigation is required).
- **D-DS-02:** Source-event selection = **by failure mode + asset within a configurable time window** (aggregates historical RCA/downtime/coach audit events from Phases 6–7).
- **D-DS-03:** Output = **fixed sectioned SOP template** (Scopo, Prerequisiti, Passi, Sicurezza, Riferimenti) with every claim anchored to inline `source_uri` + timestamp. HITL approval before indexing.

### Cross-cutting
- **D-X-01:** New audit `ActionType` values added via a new TimescaleDB migration (mirror 07-01 CHECK-constraint + Python enum lockstep). Use a **granular set (6+)** separating sub-actions — e.g. HANDOVER_DRAFT + HANDOVER_SIGNOFF, KNOWLEDGE_DEDUP + STALE_FLAG, TRAINING_SIGNOFF, SOP_DRAFT. Exact final list finalized in planning.
- **D-X-02:** HITL policy = **gate the state-changing outputs only**: ShiftHandover (dual-supervisor, D-SH-03), TrainingCoach competency sign-off (D-TC-03), DocumentationSynthesizer pre-index approval (D-DS-03). KnowledgeCurator autonomous (D-KC-04). Follow the Phase 7 corrected `interrupt()`-then-audit ordering (CR-02 fix).
- **D-X-03:** Operator personas/roles for TrainingCoach come from the **existing Mantis synthetic registry** (e.g. tessitore, tintore, manutentore) — no new persona source.
- **D-X-04:** Gateway exposure = **dedicated `knowledge_agents.py` router** with per-agent endpoints (e.g. `/v1/agents/shift-handover/compile`, `/training-coach/session`, `/knowledge-curator/ingest`, `/documentation-synthesizer/draft`), wired via a new `build_knowledge_subgraph`, with a configured cluster default agent. Mirror 06-12 / 07-10.

### Claude's Discretion
- Exact enum value names and count for D-X-01 (granular set, finalized in planning).
- Internal retrieval/grounding mechanics via `sft-knowledge` pipeline.
- Architecture/package layout details (follow Phase 6/7 agent pattern).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — TRN-02..TRN-05 definitions (and TRN-01 Phase 5 context)
- `.planning/ROADMAP.md` §"Phase 8" — goal + 5 success criteria

### Prior-phase patterns to mirror
- `.planning/phases/07-agents-maintenance-reliability/07-VERIFICATION.md` — Phase 7 runtime-defect patterns to avoid (CR-01 saver lifecycle, CR-02 interrupt/audit ordering, CR-03 fabricated approval_id, WR-03 asyncpg datetime)
- `.planning/phases/07-agents-maintenance-reliability/07-01-PLAN.md` — audit `ActionType` extension migration pattern (mirror for D-X-01)
- `.planning/phases/07-agents-maintenance-reliability/07-04-PLAN.md` — `build_maintenance_subgraph` + cluster runtime (mirror for `build_knowledge_subgraph`, D-X-04)
- `.planning/phases/07-agents-maintenance-reliability/07-10-PLAN.md` — maintenance gateway router pattern (mirror for `knowledge_agents.py`, D-X-04)
- `.planning/phases/07-agents-maintenance-reliability/07-11-PLAN.md` — bilingual docs pattern (relevant to D-DS-01)
- `.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md` — RAG/embedding decisions (BGE-M3, retrieval pipeline) consumed by D-KC-01 and DocumentationSynthesizer

### Code surfaces
- `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py` + `embedding/bge_m3.py` — RAG retrieval + embedder reused by KnowledgeCurator dedup (D-KC-01) and DocumentationSynthesizer
- `packages/sft-agents/src/sft_agents/models/enums.py` — `ActionType` enum to extend (D-X-01)
- `packages/sft-agents/src/sft_agents/runtime/clusters.py` — `build_cluster_subgraph` / `build_maintenance_subgraph` to mirror (D-X-04)
- `packages/sft-agents/src/sft_agents/tools/hitl.py` — supervisor escalate/`request_help` HITL surface (D-X-02)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sft-knowledge` retrieval pipeline + BGE-M3 embedder (Phase 5): powers KnowledgeCurator near-duplicate detection (D-KC-01) and DocumentationSynthesizer source grounding.
- `sft-agents` HITL tools (`tools/hitl.py`), `ActionType` enum, `build_*_subgraph` runtime: directly reused/extended for D-X-01/02/04.
- RCA citation validator pattern (Phase 7 `validators.py`): full PG `source_uri` lookup — reuse for TRN-05 citation provenance enforcement.
- Phase 6/7 agent package skeleton (`apps/agents/<cluster>/<agent>/`): the 4 `apps/agents/knowledge/*` dirs are already scaffolded with `pyproject.toml`/`project.json`/`README.md`/`src/trn_*/__init__.py`.

### Established Patterns
- Cluster agent = LangGraph node + NATS consumer (where event-driven) + metadata/evidence panel + audit write. Mirror ops/maintenance.
- Audit `ActionType` extension = TimescaleDB migration (CHECK constraint) + Python enum in lockstep (07-01).
- HITL = `interrupt()` directly in the node, audit write AFTER resume return (Phase 7 CR-02 corrected ordering — MUST follow).
- Bilingual docs IT+EN (07-11) — but note D-DS-01 chose translate-pass, requiring citation re-anchoring.

### Integration Points
- ShiftHandover reads cross-cluster `audit.actions` + alerts/work_orders/downtime_events tables (D-SH-02).
- DocumentationSynthesizer reads historical RCA/downtime/coach audit events (Phases 6–7) by failure mode + asset (D-DS-02).
- All 4 agents exposed via new gateway `knowledge_agents.py` router + `build_knowledge_subgraph` (D-X-04).
- TrainingCoach reads operator personas from the existing Mantis synthetic registry (D-X-03).
</code_context>

<specifics>
## Specific Ideas

- ShiftHandover dual sign-off must literally model the outgoing→incoming handover sequence, not parallel approvals.
- TrainingCoach quiz scoring must be deterministic/testable (no LLM-judge in the scoring path) so E2E can assert pass/fail exactly.
- DocumentationSynthesizer SOP template is fixed-section to make TRN-05 citation enforcement mechanically verifiable.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Supply-chain agents and UI surfaced implicitly as boundaries but belong to Phases 9 and 10 respectively.)
</deferred>

---

*Phase: 8-agents-knowledge-training*
*Context gathered: 2026-05-24*
