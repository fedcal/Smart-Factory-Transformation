# Phase 8: Agents — Knowledge & Training - Research

**Researched:** 2026-05-24
**Domain:** LangGraph agent implementation, RAG citation enforcement, bilingual SOP synthesis, HITL dual-supervisor, deterministic quiz scoring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ShiftHandover**
- D-SH-01: Trigger = scheduled shift boundary (configurable, e.g. 06:00/14:00/22:00) auto-compilation **plus** manual on-demand start by a supervisor.
- D-SH-02: Data sources = `audit.actions` cross-cluster (ops/maintenance) within the shift window **plus** direct queries to source tables (alerts, work_orders, downtime_events). Hybrid backbone.
- D-SH-03: Sign-off = **dual-supervisor sequential**: outgoing-shift supervisor approves, then incoming-shift supervisor confirms. Two distinct HITL audit rows. Must complete in <3 min.

**TrainingCoach**
- D-TC-01: Quiz = deterministic multiple-choice (closed questions, known answer keys). Questions may be RAG-curated from SOPs, but scoring is exact and testable without LLM-judge.
- D-TC-02: Adaptivity = per role/persona content selection + dynamic difficulty (rises/falls on prior answers within session).
- D-TC-03: Pass threshold = configurable default 0.80. On pass, competency sign-off routes to supervisor HITL before recording.

**KnowledgeCurator**
- D-KC-01: Dedup = hybrid hash + embedding: SHA-256 of normalized text for fast exact-dup, then BGE-M3 cosine similarity (configurable threshold) for near-duplicates.
- D-KC-02: Staleness = per-document-type configurable thresholds (SOP 365d, runbook 180d, note 90d).
- D-KC-03: Reuse-rate KPI = distinct documents cited / total indexed documents over rolling window, computed from source_uri citations.
- D-KC-04: KnowledgeCurator is **autonomous** (no HITL) — dedup and staleness are read/flag operations with no irreversible action.

**DocumentationSynthesizer**
- D-DS-01: Bilingual output = generate IT first, then translate to EN in a second pass. **Citation re-anchoring is mandatory** — source_uri + timestamp must not drift from IT source.
- D-DS-02: Source events by failure mode + asset within configurable time window (historical RCA/downtime/coach audit events from Phases 6-7).
- D-DS-03: Output = fixed-section SOP template (Scopo, Prerequisiti, Passi, Sicurezza, Riferimenti) with every claim anchored to inline source_uri + timestamp. HITL approval before indexing.

**Cross-cutting**
- D-X-01: New audit ActionType values via new TimescaleDB migration (mirror 07-01 CHECK-constraint + Python enum lockstep). Granular set (6+), separating sub-actions. Final list is Claude's discretion.
- D-X-02: HITL policy = gate state-changing outputs only (ShiftHandover dual-supervisor, TrainingCoach competency sign-off, DocumentationSynthesizer pre-index). KnowledgeCurator autonomous. Follow Phase 7 corrected interrupt()-then-audit ordering (CR-02 fix).
- D-X-03: Operator personas/roles from existing Mantis synthetic registry (tessitore, tintore, manutentore) — no new persona source.
- D-X-04: Gateway = dedicated `knowledge_agents.py` router with per-agent endpoints, wired via new `build_knowledge_subgraph`, configured cluster default agent. Mirror 07-10.

### Claude's Discretion
- Exact enum value names and count for D-X-01 (granular set, finalized in planning).
- Internal retrieval/grounding mechanics via `sft-knowledge` pipeline.
- Architecture/package layout details (follow Phase 6/7 agent pattern).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. Supply-chain agents (Phase 9) and UI (Phase 10) are explicit boundaries.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRN-02 | `TrainingCoach` — adaptive learning su procedure, valuta competenza con quiz contestualizzati | Persona roles from sft-assets registry (loom/spin/warp/dye families); BGE-M3 RAG search for SOP-grounded quiz generation; deterministic scoring model |
| TRN-03 | `ShiftHandover` — sintetizza handover di turno aggregando eventi, decisioni, alert aperti | audit.actions cross-cluster query pattern; downtime_events hypertable; dual-supervisor interrupt() sequence |
| TRN-04 | `DocumentationSynthesizer` — genera bozze SOP/runbook da eventi storici con HITL approval | DocumentationSynthesizer RCA/downtime event queries; IT→EN translation pass with citation re-anchoring; SOP template structure |
| TRN-05 | Tutti gli output TRN includono citazioni con source_uri e timestamp | RagCitation model from Phase 5; citation validator pattern from Phase 7 RCASpecialist; fixed-section template enforcement |
</phase_requirements>

---

## Summary

Phase 8 implements the four Knowledge cluster agents (KnowledgeCurator, TrainingCoach, ShiftHandover, DocumentationSynthesizer) following the established Phase 6/7 cluster pattern. All code surfaces (runtime, HITL tools, ActionType enum, audit models, RetrievalPipeline, BgeM3Embedder, gateway router) are already present and well-tested. The phase is essentially a matter of wiring existing infrastructure into new agent business logic, not building new primitives.

The most critical planning concerns are: (1) the dual-supervisor sequential HITL pattern for ShiftHandover, which has no prior precedent in the codebase and must use the CR-02-corrected interrupt()-then-audit ordering twice in sequence; (2) citation re-anchoring in DocumentationSynthesizer's IT→EN translation pass to prevent source_uri drift; (3) the alerts and work_orders tables that ShiftHandover needs — these do not yet exist in the migration history and will require new migrations; (4) TrainingCoach quiz determinism must be enforced at the data model level to keep scoring LLM-judge-free; and (5) the knowledge cluster's `build_knowledge_subgraph` must set a safe fallback default agent.

**Primary recommendation:** Mirror 07-01 → 07-04 → agent wave → 07-10 → 07-11 wave plan structure exactly. Start with migration 010 (ActionType extension), then build_knowledge_subgraph, then the four agents in parallel waves, then the gateway router, then docs/evidence_panel tests.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ShiftHandover compilation (cross-cluster query) | API / Backend (agent) | Database / Storage | Aggregates audit.actions + source tables in PG; no frontend involvement |
| ShiftHandover dual-supervisor HITL | API / Backend (LangGraph) | — | Two sequential interrupt() calls within one agent node; both write to audit.actions |
| TrainingCoach quiz delivery + scoring | API / Backend (agent) | — | Deterministic scoring must be server-side (not browser-side); no LLM-judge in scoring path |
| TrainingCoach competency sign-off HITL | API / Backend (LangGraph) | — | Same interrupt()+audit pattern; supervisor tier |
| KnowledgeCurator dedup (SHA-256 + BGE-M3) | API / Backend (agent) | Database / Storage | Hash computed in Python; cosine similarity queried against Qdrant |
| KnowledgeCurator staleness | Database / Storage | API / Backend | Computed from ingest_state PG table + per-type config thresholds |
| KnowledgeCurator reuse-rate KPI | Database / Storage | API / Backend | SQL aggregate over audit.actions.evidence_panel source_uri citations |
| DocumentationSynthesizer IT generation | API / Backend (LLM) | — | LLM-driven, grounded by Phase 5 retrieval pipeline |
| DocumentationSynthesizer EN translation pass | API / Backend (LLM) | — | Second-pass LLM call; citation re-anchoring is a post-translation normalization step |
| DocumentationSynthesizer HITL pre-index | API / Backend (LangGraph) | — | interrupt() before Qdrant indexing write |
| Gateway routing (knowledge_agents.py) | API / Backend (FastAPI) | — | Router + build_knowledge_subgraph wiring; mirrors 07-10 |
| Citation provenance enforcement (TRN-05) | API / Backend (validator) | — | Mirrors RCAChainValidator pattern from Phase 7 |

---

## Standard Stack

### Core (all verified from codebase — [VERIFIED: codebase])

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| LangGraph | 0.4+ | Agent graph + interrupt() | Project-locked; cluster subgraph pattern established |
| FastAPI | current project | Gateway router | Project-locked; maintenance_agents.py is direct mirror |
| asyncpg | current project | PG queries for ShiftHandover | Project-locked; used in DowntimeAnalyzer pattern |
| sft_agents (project SDK) | in-repo | ActionType enum, AuditRecord, EvidencePanel, HITL tools | All existing — just extend |
| sft_knowledge (project SDK) | in-repo | RetrievalPipeline, BgeM3Embedder | Phase 5 deliverable; exact API documented below |
| structlog | current project | Structured logging | Project-locked pattern |
| pydantic v2 | current project | Request/response models, frozen+extra=forbid | Project-locked; all models follow this convention |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib (stdlib) | stdlib | SHA-256 for exact dedup | KnowledgeCurator D-KC-01 fast path |
| APScheduler or asyncio.sleep loop | project choice | Shift boundary scheduler | ShiftHandover D-SH-01 scheduled trigger |
| langchain_core | current project | BaseTool, BaseLLM | All agent tool definitions use this |

### No New Packages Required

This phase does not introduce external packages. All required functionality is in-repo or stdlib.

---

## Package Legitimacy Audit

No external packages are added in this phase. All dependencies are already installed project dependencies.

| Package | Registry | Status |
|---------|----------|--------|
| (none new) | — | — |

---

## Architecture Patterns

### System Architecture Diagram

```
HTTP Client
    │
    ▼
knowledge_agents.py (FastAPI router)
    │ POST /v1/agents/shift-handover/compile
    │ POST /v1/agents/training-coach/session
    │ POST /v1/agents/knowledge-curator/ingest
    │ POST /v1/agents/documentation-synthesizer/draft
    │
    ▼
supervisor_graph.ainvoke(state={target_agent: <slug>}, ...)
    │
    ▼
build_knowledge_subgraph(child_callables)
    │ routes on state["target_agent"]
    │
    ├── KnowledgeCurator.__call__(state) ──── autonomous
    │       │
    │       ├── BgeM3Embedder.encode() ──── Qdrant cosine
    │       └── audit.actions INSERT (ActionType.KNOWLEDGE_DEDUP / STALE_FLAG)
    │
    ├── ShiftHandover.__call__(state) ─────── HITL (dual-supervisor)
    │       │
    │       ├── asyncpg SELECT audit.actions [window]
    │       ├── asyncpg SELECT maintenance.downtime_events [window]
    │       ├── asyncpg SELECT ops.alerts [window]        (migration 010 table)
    │       ├── asyncpg SELECT ops.work_orders [window]   (migration 010 table)
    │       ├── interrupt() ─── outgoing supervisor
    │       │       └── resume ─── audit row 1 (HANDOVER_SIGNOFF)
    │       ├── interrupt() ─── incoming supervisor
    │       │       └── resume ─── audit row 2 (HANDOVER_SIGNOFF)
    │       └── audit.actions INSERT HANDOVER_DRAFT
    │
    ├── TrainingCoach.__call__(state) ──────── HITL (competency sign-off)
    │       │
    │       ├── RetrievalPipeline.search() ─── Qdrant "training" collection
    │       ├── quiz delivery (deterministic MCQ model)
    │       ├── score computation (no LLM-judge)
    │       ├── interrupt() ─── supervisor sign-off (if pass)
    │       │       └── resume ─── audit row (TRAINING_SIGNOFF)
    │       └── audit.actions INSERT TRAINING_SESSION
    │
    └── DocumentationSynthesizer.__call__(state) ── HITL (pre-index)
            │
            ├── asyncpg SELECT audit.actions WHERE action_type IN (RCA_CHAIN, ...)
            │       filtered by failure_mode + asset + time window
            ├── RetrievalPipeline.search() ─── grounding citations
            ├── LLM call ─── generate IT SOP (fixed template)
            ├── LLM call ─── translate EN + re-anchor citations
            ├── interrupt() ─── HITL approval before indexing
            │       └── resume ─── QdrantIndexer.upsert() + audit row (SOP_DRAFT)
            └── audit.actions INSERT SOP_DRAFT
```

### Recommended Project Structure

```
apps/agents/knowledge/
├── shift-handover/
│   └── src/trn_shift_handover/
│       ├── __init__.py
│       ├── agent.py          # ShiftHandover LangGraph node
│       ├── aggregator.py     # Cross-cluster query logic
│       ├── models.py         # HandoverReport, ShiftWindow Pydantic models
│       ├── metadata.py       # AGENT_ID, TOOL_INVENTORY, DATA_SOURCES, build_trn05_evidence_panel
│       └── prompts.py        # Report template + prompt
├── training-coach/
│   └── src/trn_training_coach/
│       ├── agent.py          # TrainingCoach LangGraph node
│       ├── quiz.py           # QuizBank, QuizQuestion, MCQSession (deterministic)
│       ├── difficulty.py     # DifficultyAdaptor (D-TC-02 dynamic difficulty)
│       ├── models.py         # TrainingSession, CompetencyResult
│       ├── metadata.py
│       └── prompts.py
├── knowledge-curator/
│   └── src/trn_knowledge_curator/
│       ├── agent.py          # KnowledgeCurator LangGraph node (autonomous)
│       ├── dedup.py          # ExactDedupChecker (SHA-256), NearDedupChecker (BGE-M3)
│       ├── staleness.py      # StalenessChecker (per-type thresholds)
│       ├── reuse_rate.py     # KPI computation
│       ├── models.py         # IngestRequest, CurationReport
│       └── metadata.py
└── documentation-synthesizer/
    └── src/trn_documentation_synthesizer/
        ├── agent.py          # DocumentationSynthesizer LangGraph node
        ├── event_aggregator.py  # Historical RCA/downtime query (D-DS-02)
        ├── sop_builder.py    # Fixed-section template builder
        ├── translator.py     # IT→EN translation + citation re-anchoring
        ├── validators.py     # Citation validator (mirror Phase 7 RCAChainValidator)
        ├── models.py         # SOPDraft, BilingualSOP
        └── metadata.py
```

---

## Research Finding 1: Exact Reusable Surfaces in sft-knowledge

### RetrievalPipeline (packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py) [VERIFIED: codebase]

```python
class RetrievalPipeline:
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        embedder: BgeM3Embedder,
        reranker: BgeReranker | None = None,
    ) -> None: ...

    async def search(
        self,
        query: str,
        user_roles: list[str],
        category: str = "sop",      # collection name: sop/manuals/troubleshooting/training
        k: int = 5,
        lang: str | None = None,
        sop_ids: list[str] | None = None,
        asset_family: str | None = None,
        rerank: bool = True,
    ) -> list[RagCitation]: ...
```

Returns `list[RagCitation]` where `RagCitation` has `source_uri`, `snippet`, `score`, `retrieved_at`. The `source_uri` is already populated from the Qdrant payload. The `retrieved_at` is a UTC-tz-aware datetime.

**For KnowledgeCurator near-dedup:** Call `embedder.encode([normalized_text], return_dense=True, return_sparse=True)` to get `EncodeOutput.dense_vecs[0]` (shape 1024D). Then do a direct Qdrant `query_points` with the dense vector against the relevant collection (not via RetrievalPipeline — direct client call to get raw cosine scores, not just top-k citations).

**For DocumentationSynthesizer grounding:** Call `pipeline.search(query, user_roles=["technician"], category="sop", k=5, asset_family=failure_mode_asset_family)`. Citations come back with `source_uri` already populated.

### BgeM3Embedder (packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py) [VERIFIED: codebase]

```python
class BgeM3Embedder:
    def encode(
        self,
        texts: list[str],
        return_dense: bool = True,
        return_sparse: bool = True,
    ) -> EncodeOutput: ...
    # EncodeOutput.dense_vecs: list[np.ndarray]  — 1024D each
    # EncodeOutput.sparse_weights: list[dict[str, float]]

    def to_qdrant_sparse(
        self, lexical_weights: dict[str, float]
    ) -> SparseVector: ...
    # Raises RuntimeError if backend is fastembed (no tokenizer)
```

Singleton lazy loader: first `encode()` call loads ~2GB BGE-M3 model. Subsequent calls are fast. In test environments set `BGE_M3_DEVICE=cpu`.

**KnowledgeCurator cosine dedup flow:**

```python
# Phase 8 KnowledgeCurator — exact-dup then near-dup
import hashlib

def normalized_sha256(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()

# If hash not in ingest.documents → new doc; compute embedding for near-dup check
output = embedder.encode([normalized_text], return_dense=True, return_sparse=False)
dense_vec = output.dense_vecs[0]  # np.ndarray 1024D

# Direct Qdrant search for cosine similarity
result = await qdrant_client.query_points(
    collection_name=category,
    query=dense_vec.tolist(),
    using="dense",
    limit=5,
    with_payload=False,
    score_threshold=cosine_threshold,  # configurable, e.g. 0.92
)
is_near_dup = len(result.points) > 0
```

---

## Research Finding 2: Corrected LangGraph HITL Pattern (CR-02 Fix)

[VERIFIED: codebase — 07-VERIFICATION.md + rca-specialist/agent.py + maintenance-coach/agent.py]

The canonical corrected pattern for any agent with HITL in Phase 8:

```python
# CORRECT (CR-02 fixed) — interrupt() called directly, _write_audit AFTER return
async def __call__(self, state: AgentState) -> dict[str, Any]:
    # ... build output ...

    # Step 1: interrupt() directly in __call__ — NOT via a tool
    decision = interrupt({
        "tool": "escalate_to_supervisor",
        "tier": Tier.SUPERVISOR.value,
        "payload": proposed_action.model_dump(mode="json"),
    })
    # On resume: execution continues here with decision from supervisor

    # Step 2: write audit AFTER interrupt() returns
    await self._audit_writer.write(AuditRecord(
        action_type=ActionType.HANDOVER_SIGNOFF,
        decision=Decision.HITL_SUPERVISOR,
        approval_id=None,   # pending — CR-03 fix: never fabricate UUID
        motivation=f"Supervisor decision: {decision}",
        ...
    ))

    return {...}
```

**WRONG pattern (re-introduces CR-02):**
```python
# DO NOT DO THIS — _write_audit fires before interrupt, causing double-write on replay
await self._audit_writer.write(...)
decision = interrupt(...)
```

**WRONG pattern (re-introduces CR-01):**
```python
# DO NOT DO THIS — saver opened inside agent, use-after-close on resume
async with AsyncPostgresSaver.from_conn_string(...) as saver:
    graph = StateGraph(...).compile(checkpointer=saver)
    result = await graph.ainvoke(...)
```
The saver MUST be injected via lifespan DI, not opened inside the agent.

### Dual-Supervisor Sequential Pattern for ShiftHandover

No exact codebase precedent exists — this is new for Phase 8. The pattern is:

```python
async def __call__(self, state: AgentState) -> dict[str, Any]:
    report = await self._compile_report(state)

    # First interrupt — outgoing supervisor
    decision_outgoing = interrupt({
        "tier": "supervisor",
        "handover_step": "outgoing_approval",
        "payload": report.model_dump(mode="json"),
    })

    # Write audit for first sign-off AFTER first resume
    await self._audit_writer.write(AuditRecord(
        action_type=ActionType.HANDOVER_SIGNOFF,
        decision=Decision.HITL_SUPERVISOR,
        approval_id=None,
        motivation=f"Outgoing supervisor: {decision_outgoing}",
        ...
    ))

    # Second interrupt — incoming supervisor (sequential, not parallel)
    decision_incoming = interrupt({
        "tier": "supervisor",
        "handover_step": "incoming_confirmation",
        "payload": report.model_dump(mode="json"),
    })

    # Write audit for second sign-off
    await self._audit_writer.write(AuditRecord(
        action_type=ActionType.HANDOVER_SIGNOFF,
        decision=Decision.HITL_SUPERVISOR,
        approval_id=None,
        motivation=f"Incoming supervisor: {decision_incoming}",
        ...
    ))

    return {"handover_report": report, "shift_status": "signed_off"}
```

**Critical pitfall:** Two consecutive `interrupt()` calls in one `__call__` means the LangGraph thread is suspended twice. The second supervisor approval resumes from the second interrupt, not from the top. The first audit row must be written between the two interrupts (after first resume, before second interrupt). The `<3 min` constraint means: total wall-clock from first API call to second supervisor resume. The report compilation (query phase) must complete in <1 min to leave headroom for two human approvals.

---

## Research Finding 3: ActionType Enum Extension (D-X-01)

[VERIFIED: codebase — enums.py + migration 009]

Current ActionType in `packages/sft-agents/src/sft_agents/models/enums.py` (Phase 1-7):

```python
# Phase 1-5 baseline
WRITE_PLC_SETPOINT, ACTUATOR_COMMAND, FIRMWARE_DEPLOY,
NETWORK_ACL_CHANGE, GRAPH_RECURSION_REVIEW, GOVERNOR_ALERT

# Phase 6
ESCALATION_REQUEST, QUALITY_VERDICT, SCHEDULE_DRAFT, ANOMALY_ALERT

# Phase 7
RUL_ESTIMATE, RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT, OEE_REPORT
```

**Proposed Phase 8 extension (Claude's discretion — D-X-01 granular set):**

```python
# Phase 8 additions — keep in lockstep with migration 010.
HANDOVER_DRAFT = "HANDOVER_DRAFT"           # D-SH-01: draft compiled by ShiftHandover
HANDOVER_SIGNOFF = "HANDOVER_SIGNOFF"       # D-SH-03: supervisor sign-off row (2 rows per handover)
TRAINING_SESSION = "TRAINING_SESSION"       # D-TC-01: quiz delivery session record
TRAINING_SIGNOFF = "TRAINING_SIGNOFF"       # D-TC-03: supervisor competency sign-off
KNOWLEDGE_DEDUP = "KNOWLEDGE_DEDUP"         # D-KC-01: dedup verdict (exact or near-dup)
STALE_FLAG = "STALE_FLAG"                   # D-KC-02: staleness flag on a document
SOP_DRAFT = "SOP_DRAFT"                     # D-DS-03: synthesized SOP draft before indexing
```

That is 7 new values. Migration 010 must follow the exact DROP+ADD CHECK pattern from migrations 007 and 009.

**Migration file:** `infra/migrations/timescale/010_extend_audit_knw.sql`

The audit.actions HITL_MOTIVATION CHECK constraint in migration 003 (`approval_id IS NOT NULL`) was relaxed in Plan 07-15 (CR-03 fix). Current AuditRecord validator at `packages/sft-agents/src/sft_agents/models/audit.py` allows `approval_id=None` for HITL decisions (pending escalation). This is correct — use `approval_id=None` for all pending HITL rows in Phase 8 agents.

---

## Research Finding 4: ShiftHandover Data Sources

[VERIFIED: codebase — migration 008, migration 003, migration 007]

### What exists today

| Table | Schema | Key Columns | Phase Introduced |
|-------|--------|-------------|------------------|
| `audit.actions` | TimescaleDB hypertable | `ts`, `agent_id`, `cluster`, `action_type`, `thread_id`, `evidence_panel` (JSONB), `decision` | Phase 4 (migration 003) |
| `maintenance.downtime_events` | TimescaleDB hypertable | `event_id`, `asset_id`, `reason_code`, `duration_min`, `severity`, `work_order_id`, `timestamp` | Phase 7 (migration 008) |

### What does NOT yet exist

The `ops.alerts` and `ops.work_orders` tables referenced in D-SH-02 do **not** exist in the migration history (migrations 001-009). D-SH-02 says "direct queries to source tables (alerts, work_orders, downtime_events)". This means:

1. **Phase 8 migration 010 must create `ops.alerts` and `ops.work_orders` tables** (or confirm they are scaffolded elsewhere). Check if they exist in sensor_events or elsewhere.
2. Alternatively, ShiftHandover may query alerts from `audit.actions WHERE action_type='ANOMALY_ALERT'` and work orders from `maintenance.downtime_events.work_order_id` if those tables are not yet created.

**Planning decision required:** Either add alert/work_order table creation to migration 010, or document that ShiftHandover derives alert + work_order data from audit.actions JSONB evidence_panel (evidence_based fallback). The planner must decide and document this choice.

### Cross-cluster audit query for ShiftHandover

```sql
-- Shift window query (all clusters, all agents, any action_type)
SELECT
    ts,
    agent_id,
    cluster,
    action_type,
    thread_id,
    evidence_panel,
    decision
FROM audit.actions
WHERE ts BETWEEN $1 AND $2
ORDER BY ts ASC
-- $1 = shift_start TIMESTAMPTZ, $2 = shift_end TIMESTAMPTZ
-- asyncpg: pass datetime objects directly (WR-03 fix from Phase 7 — NO .isoformat())
```

**ShiftHandover report in <3 min:** The query above on a 8-hour audit window is against a TimescaleDB hypertable with `idx_audit_thread_id_ts` index. Should be fast. The constraint risk is the LLM summarization step — cap the LLM call with a timeout or use a deterministic template with LLM only for the narrative summary block.

---

## Research Finding 5: Operator Persona Source (D-X-03)

[VERIFIED: codebase — sft-assets/registry.yaml, synthetic-corpus, failure_modes.yaml]

The "Mantis synthetic registry" for personas/roles does not have a dedicated `personas.yaml` or person-level registry. What exists is:

1. **Asset families from sft-assets/registry.yaml:** `loom` (12 assets), `spinning` (8 assets), `warping` (4 assets), `dyeing` (4 assets), `finishing` (2 assets). These imply operator roles: tessitore (loom), filatore (spinning), tintore (dyeing), orditore (warping), tecnico-finissaggio (finishing).

2. **SOP audience field in synthetic-corpus frontmatter:** The 41 SOP documents have frontmatter fields including `role` and `audience` (e.g., `role: manutentore`, `audience: operator`). These are the persona labels TrainingCoach must use for content selection.

3. **ROLE_TO_ACL mapping in RetrievalPipeline:** `operator`, `technician`, `supervisor`, `manager`, `engineer`, `safety` — these are the access-control roles, not the job-role personas.

**For TrainingCoach planning:** The persona registry is the SOP frontmatter `role` field (e.g., tessitore, tintore, manutentore, operatore). Content selection filters Qdrant by role (e.g., `asset_family=loom` for tessitore). Dynamic difficulty is a session-state variable (e.g., difficulty: easy/medium/hard) that shifts based on quiz answer history within the session.

**There is no pre-existing `personas.yaml` file** — the planner must decide whether to create one or derive personas from SOP frontmatter at runtime.

---

## Research Finding 6: build_knowledge_subgraph Pattern

[VERIFIED: codebase — clusters.py, 07-04-PLAN.md]

`build_maintenance_subgraph` (Plan 07-04, now in clusters.py) is the direct template. The pattern:

```python
_KNW_DEFAULT_AGENT: str = "knowledge-curator"
# Rationale: KnowledgeCurator is autonomous (D-KC-04) with no irreversible side effects.
# Unknown-target routing to an autonomous agent is the safest fallback.

def build_knowledge_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    if not child_callables:
        raise ValueError("child_callables must be non-empty for the knowledge subgraph")
    if _KNW_DEFAULT_AGENT not in child_callables:
        raise ValueError(
            f"child_callables must include {_KNW_DEFAULT_AGENT!r} (the fallback); "
            f"got slugs {sorted(child_callables)}"
        )
    children = dict(child_callables)
    g = StateGraph(AgentState)
    for slug, fn in children.items():
        g.add_node(slug, fn)
    def _route(state: AgentState) -> str:
        target = state.get("target_agent") if isinstance(state, dict) else None
        if not target or target not in children:
            _log.warning("knw_route_unknown_target", target=target, fallback=_KNW_DEFAULT_AGENT)
            return _KNW_DEFAULT_AGENT
        return str(target)
    g.add_conditional_edges(START, _route, {slug: slug for slug in children})
    for slug in children:
        g.add_edge(slug, END)
    return g
```

**Location:** Append to `packages/sft-agents/src/sft_agents/runtime/clusters.py` (alongside `build_maintenance_subgraph`).

**Gateway `knowledge_agents.py` router endpoints:**

```
POST /v1/agents/shift-handover/compile         200  (dual HITL → 202 may be preferred)
POST /v1/agents/training-coach/session         200
POST /v1/agents/knowledge-curator/ingest       200  (autonomous, synchronous)
POST /v1/agents/documentation-synthesizer/draft  202  (async HITL before indexing)
```

**Dependencies wiring** mirrors `maintenance_agents.py`: inject 4 knowledge agent callables into `build_knowledge_subgraph(...)` in `dependencies.py`, register router in `main.py` `build_app()` function. Lifespan manages agent construction.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RAG retrieval | Custom vector search | `RetrievalPipeline.search()` (Phase 5) | ACL pre-filter, RRF fusion, reranker all in place |
| BGE-M3 embedding | Custom embedder | `BgeM3Embedder.encode()` (Phase 5) | Lazy singleton, dense+sparse, fastembed fallback |
| HITL interrupt | Custom approval mechanism | `interrupt()` from `langgraph.types` + corrected CR-02 pattern | LangGraph checkpoint resume, already tested |
| Supervisor escalation | New HITL tool | `EscalateToSupervisorTool` (Phase 4/6) | Already wired with safety interlock; Pitfall §3 inherited |
| Audit write | Direct SQL | `AuditWriter.write(AuditRecord(...))` | Immutable append-only with all constraints enforced |
| Cosine similarity | numpy dot product | Direct Qdrant `query_points` with `score_threshold` | Engine-side filtering, ACL pre-filter, no Python round-trip |
| Document hash | MD5 / rolling hash | `hashlib.sha256(normalized_text.encode())` | Deterministic, collision-resistant, already established pattern |
| Migration idempotency | Custom tracking | `migrate.py` applied-migrations meta table + `DROP CONSTRAINT IF EXISTS` | Phase 4-7 proven pattern |

**Key insight:** Every custom solution in this domain has already been implemented and tested in Phases 4-7. The value of Phase 8 is composition, not construction.

---

## Common Pitfalls

### Pitfall 1: Citation Drift in DocumentationSynthesizer IT→EN Translation

**What goes wrong:** The LLM translation pass rewrites sentence order, combines paragraphs, or drops anchor markers. Source_uri citations anchored inline to specific claim sentences in the IT text become orphaned or pointing to wrong sentences in the EN output.

**Why it happens:** LLMs do not treat citation anchors as immutable tokens unless explicitly instructed. Even with instruction, a long translation may reflow content unpredictably.

**How to avoid:**
1. Generate IT SOP with explicit anchor markers (e.g., `[SRC:1]`, `[SRC:2]`) embedded in the text at citation points.
2. Maintain a `{anchor: source_uri, timestamp}` map produced during IT generation.
3. Feed the IT text + anchor map to the EN translation prompt: "Translate to English. Preserve all [SRC:N] markers in-place."
4. After translation, validate that all anchors in the EN text correspond to an entry in the anchor map. Any missing anchor = citation drift → validation error → retry.

**Warning signs:** EN text has fewer `[SRC:N]` markers than IT text; source_uri values appear in wrong sections.

### Pitfall 2: Double Audit Row on ShiftHandover Resume (extends CR-01/WR-02)

**What goes wrong:** With two sequential `interrupt()` calls, if `_write_audit` is called before the second `interrupt()`, and LangGraph replays the node on second resume, the first audit row is written twice.

**How to avoid:** Follow CR-02 pattern strictly: write the first audit row after the first `interrupt()` returns. Write the second audit row after the second `interrupt()` returns. Both writes are protected from double-execution because they occur after (not before) their respective interrupt calls.

### Pitfall 3: TrainingCoach Quiz Determinism Broken by LLM Scoring

**What goes wrong:** If the scoring path passes the operator's answer to the LLM and asks "is this correct?", the test suite cannot assert a deterministic pass/fail without an LLM mock that matches perfectly.

**How to avoid:** The quiz model must store `correct_answer_index: int` at quiz generation time. Scoring is `operator_answer_index == correct_answer_index`. The LLM is used only for quiz *generation* (curating questions from SOP content), not for *scoring*. The question bank is either pre-built YAML or generated-then-frozen at session start.

### Pitfall 4: ShiftHandover <3 min Constraint — LLM Latency

**What goes wrong:** Compilation includes a narrative LLM summarization step. With a large audit window (8-hour shift, many events), the LLM context may be large and latency high.

**How to avoid:**
1. Pre-aggregate events into a structured summary dict (SQL aggregates, not raw rows).
2. Cap the number of events fed to the LLM (e.g., top 20 by severity, not all events).
3. Use a deterministic structured template for most fields (counts, timestamps, asset IDs); LLM only for the 3-5 line executive summary.
4. Set an explicit timeout on the LLM call (e.g., 60s). The 3-minute SLA is total wall-clock including two human HITL approvals — the compilation itself should target <30s.

### Pitfall 5: Missing alerts/work_orders Tables

**What goes wrong:** D-SH-02 references "direct queries to source tables (alerts, work_orders)" but migrations 001-009 do not create these tables. ShiftHandover code fails at runtime with relation not found.

**How to avoid:** Migration 010 must explicitly CREATE the `ops.alerts` and `ops.work_orders` tables (even minimal schemas), OR the planner must document that ShiftHandover derives alert data from `audit.actions WHERE action_type='ANOMALY_ALERT'` and work orders from `maintenance.downtime_events.work_order_id`. This must be resolved in the first plan of Phase 8.

### Pitfall 6: KnowledgeCurator Near-Dedup Threshold Tuning

**What goes wrong:** A BGE-M3 cosine threshold set too low (e.g., 0.85) will flag legitimate near-duplicate SOPs for different procedures as duplicates. Too high (e.g., 0.99) misses actual near-duplicates.

**How to avoid:** Use a configurable threshold (default 0.92 — above typical semantic similarity of distinct SOPs, below identical-with-minor-edits). Document the threshold in a config struct with an explicit justification comment. Add a test with known near-dup and known distinct document pairs verifying the threshold boundary.

### Pitfall 7: HITL Approval ID Fabrication (CR-03 Pattern)

**What goes wrong:** Generating a `uuid4()` for `approval_id` at the time of writing the pending HITL audit row (before supervisor has actually approved), then failing downstream JOIN forensics.

**How to avoid:** Always use `approval_id=None` for pending HITL rows (CR-03 fix, verified in AuditRecord validator). The HITL system updates the row (or writes a second row) with the real approval_id upon supervisor approval.

### Pitfall 8: asyncpg datetime / isoformat() mismatch (WR-03 Pattern)

**What goes wrong:** Passing `.isoformat()` string to asyncpg TIMESTAMPTZ parameters instead of datetime objects.

**How to avoid:** Always pass Python `datetime` objects directly to asyncpg parameters. Never call `.isoformat()` before passing to asyncpg. Verified fix from Phase 7 Plan 07-16.

---

## Code Examples

### Correct interrupt()-then-audit for HITL agents

```python
# Source: apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py (CR-02 fix)
# Pattern for all Phase 8 HITL agents

async def __call__(self, state: AgentState) -> dict[str, Any]:
    # ... business logic, no side effects yet ...

    decision = interrupt({            # ← interrupt() DIRECTLY in __call__
        "tier": Tier.SUPERVISOR.value,
        "payload": output.model_dump(mode="json"),
    })

    # ↓ audit write AFTER interrupt() returns (on resume execution)
    await self._audit_writer.write(
        AuditRecord(
            id=uuid4(),
            ts=datetime.now(timezone.utc),
            action_id=uuid4(),
            agent_id=self._agent_id,
            thread_id=state["thread_id"],
            cluster="knowledge",
            action_type=ActionType.SOP_DRAFT.value,     # Phase 8 value
            evidence_panel=evidence_panel,
            decision=Decision.HITL_SUPERVISOR,
            motivation=f"Supervisor approved: {decision}",
            budget_snapshot=budget,
            approval_id=None,   # ← CR-03 fix: never fabricate UUID
        )
    )
    return {...}
```

### ActionType extension (migration 010 pattern)

```sql
-- Mirror of 009_extend_audit_mnt.sql DROP+ADD pattern
ALTER TABLE audit.actions
  DROP CONSTRAINT IF EXISTS audit_actions_action_type_chk;

ALTER TABLE audit.actions
  ADD CONSTRAINT audit_actions_action_type_chk CHECK (
    action_type IN (
      -- Phases 1-5 baseline
      'WRITE_PLC_SETPOINT','ACTUATOR_COMMAND','FIRMWARE_DEPLOY',
      'NETWORK_ACL_CHANGE','GRAPH_RECURSION_REVIEW','GOVERNOR_ALERT',
      -- Phase 6
      'ESCALATION_REQUEST','QUALITY_VERDICT','SCHEDULE_DRAFT','ANOMALY_ALERT',
      -- Phase 7
      'RUL_ESTIMATE','RCA_CHAIN','COACH_STEP','DOWNTIME_VERDICT','OEE_REPORT',
      -- Phase 8 (D-X-01)
      'HANDOVER_DRAFT','HANDOVER_SIGNOFF',
      'TRAINING_SESSION','TRAINING_SIGNOFF',
      'KNOWLEDGE_DEDUP','STALE_FLAG',
      'SOP_DRAFT'
    )
  );
```

### build_knowledge_subgraph pattern (append to clusters.py)

```python
# Source: packages/sft-agents/src/sft_agents/runtime/clusters.py — mirror of build_maintenance_subgraph
_KNW_DEFAULT_AGENT: str = "knowledge-curator"  # autonomous, no irreversible side effects

def build_knowledge_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    if not child_callables:
        raise ValueError("child_callables must be non-empty for the knowledge subgraph")
    if _KNW_DEFAULT_AGENT not in child_callables:
        raise ValueError(
            f"child_callables must include {_KNW_DEFAULT_AGENT!r}; "
            f"got slugs {sorted(child_callables)}"
        )
    children = dict(child_callables)
    g: StateGraph = StateGraph(AgentState)
    for slug, fn in children.items():
        g.add_node(slug, fn)
    def _route(state: AgentState) -> str:
        target = state.get("target_agent") if isinstance(state, dict) else None
        if not target or target not in children:
            _log.warning("knw_route_unknown_target", target=target, fallback=_KNW_DEFAULT_AGENT)
            return _KNW_DEFAULT_AGENT
        return str(target)
    g.add_conditional_edges(START, _route, {slug: slug for slug in children})
    for slug in children:
        g.add_edge(slug, END)
    return g
```

### DocumentationSynthesizer fixed-section SOP template

```python
# Source: D-DS-03 (CONTEXT.md) — fixed sections in Italian as primary language
SECTION_KEYS_IT = ["Scopo", "Prerequisiti", "Passi", "Sicurezza", "Riferimenti"]

class SOPDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    sop_id: str
    title_it: str
    title_en: str
    lang_primary: Literal["it"] = "it"
    sections_it: dict[str, str]  # section_key → content with inline [SRC:N] anchors
    sections_en: dict[str, str]  # translated, anchors preserved
    citations: list[RagCitation]      # source_uri + timestamp for every anchor
    anchor_map: dict[str, str]        # anchor_id → source_uri
    generated_at: datetime
    approved: bool = False
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pre-Phase 7: approval_id=uuid4() for pending HITL | approval_id=None (CR-03 fix, Plan 07-15) | Phase 7 | All Phase 8 HITL agents must use None for pending |
| Pre-Phase 7: _write_audit before interrupt() | interrupt() directly, audit AFTER return (CR-02 fix, Plan 07-14) | Phase 7 | Mandatory for all Phase 8 agents with HITL |
| Pre-Phase 7: self-compile saver inside agent | Saver injected via lifespan DI, RuntimeError guard (CR-01 fix, Plan 07-13) | Phase 7 | ShiftHandover uses LangGraph checkpoint; must follow DI pattern |
| Pre-Phase 7: .isoformat() for asyncpg | datetime objects passed directly (WR-03 fix, Plan 07-16) | Phase 7 | ShiftHandover date queries must use datetime objects |
| Phase 5: single sequential interrupt for HITL | Sequential dual-interrupt for dual-supervisor | Phase 8 | New pattern — no prior precedent in codebase |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ops.alerts` and `ops.work_orders` tables do not exist in migrations 001-009 | RF-4 Data Sources | If they exist in an undiscovered location (app-level create, not in infra/migrations), migration 010 creation will conflict |
| A2 | Persona "roles" for TrainingCoach are derived from SOP frontmatter `role` field, not a dedicated registry file | RF-5 Persona Source | If a dedicated personas.yaml exists somewhere not found by search, the plan should use it instead of SOP frontmatter derivation |
| A3 | The <3 min ShiftHandover SLA is total wall-clock (including human sign-offs), not just compilation time | RF-4 SLA | If it means compilation-only, the constraint is much easier to meet and the LLM summarization warning in Pitfall 4 is unnecessary |
| A4 | `build_knowledge_subgraph` fallback default should be `knowledge-curator` (autonomous, no HITL) | RF-6 | If the safest fallback should be a HITL-gated agent, reconsider to `documentation-synthesizer` |

---

## Open Questions (RESOLVED)

1. **alerts and work_orders tables**
   - What we know: D-SH-02 says ShiftHandover reads from `alerts`, `work_orders`, `downtime_events`. Migrations 001-009 have `maintenance.downtime_events` but no `ops.alerts` or `ops.work_orders`.
   - What's unclear: Were these tables created by Phase 6 agent code (not in infra/migrations), or must Phase 8 create them?
   - Recommendation: First plan in Phase 8 (migration plan) must grep for these table names in all SQL files and app code. If absent, create minimal schemas in migration 010.
   - RESOLVED: Derive alerts and work-order/quality/downtime data from `audit.actions` JSONB (alerts from rows WHERE `action_type='ANOMALY_ALERT'`; work-order/quality/downtime from the corresponding `action_type` rows + `maintenance.downtime_events`). No new `ops.alerts`/`ops.work_orders` tables are created — the audit chain is the single backbone (D-SH-02, locked post-research in 08-CONTEXT.md). Migration 010 extends only the `action_type` CHECK constraint (08-00a), no new tables.

2. **TrainingCoach quiz bank: pre-built YAML vs. runtime LLM generation**
   - What we know: D-TC-01 says questions may be RAG-curated from SOPs, but scoring is deterministic.
   - What's unclear: Are questions generated once at session start (frozen for the session) or pulled from a pre-built YAML bank?
   - Recommendation: Generate questions at session start from RAG retrieval, freeze them into a `QuizSession` Pydantic model with `correct_answer_index` fields. This preserves RAG-curation while keeping scoring LLM-judge-free.
   - RESOLVED: Generate-at-session-start. Questions are RAG-curated from SOP content via the LLM once at session start, then frozen into an `MCQSession` Pydantic model with `correct_answer_index` set; scoring is index equality only, never an LLM call (locked in plan 08-05; Pitfall §3).

3. **ShiftHandover scheduled trigger implementation**
   - What we know: D-SH-01 requires scheduled boundary triggers (06:00/14:00/22:00) plus manual on-demand.
   - What's unclear: Does the scheduler run inside the API gateway (as a background task) or as a separate NATS-event-driven consumer?
   - Recommendation: Mirror the PM NATS consumer pattern — a NATS consumer on `shift.boundary.>` subject listens for boundary events (published by a separate scheduler or the sim-textile simulator). Manual trigger via the `/compile` endpoint.
   - RESOLVED: NATS consumer on the `shift.boundary.>` subject (mirrors the pm-consumer/da-consumer event-driven pattern), NOT an in-process scheduler. Manual on-demand triggering is handled by the gateway `/compile` endpoint (D-SH-01, locked post-research in 08-CONTEXT.md; implemented in plan 08-04).

4. **DocumentationSynthesizer source event scope**
   - What we know: D-DS-02 says source events from `audit.actions` where `action_type IN (RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT)` filtered by failure_mode + asset + configurable window.
   - What's unclear: Should the evidence_panel JSONB be parsed for failure_mode, or should a `failure_mode` column be added to audit.actions?
   - Recommendation: Parse `evidence_panel JSONB` at query time using PG JSONB operators (e.g., `WHERE evidence_panel->>'failure_mode' = $1`). No schema change needed; leverage existing JSONB flexibility.
   - RESOLVED: Parse `evidence_panel` JSONB at query time using PG JSONB operators (e.g., `WHERE evidence_panel->>'failure_mode' = $1` and `evidence_panel->>'asset_id' = $2`). No schema change and no new `failure_mode` column on audit.actions (locked in plan 08-07).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| TimescaleDB (PostgreSQL) | Migration 010, ShiftHandover queries | Expected (Docker Compose) | 2.18.0-pg16 per compose | None — blocking |
| Qdrant | KnowledgeCurator dedup, DocumentationSynthesizer | Expected (Docker Compose) | 1.16.1 per compose | None — blocking |
| LangGraph checkpointer (PostgreSQL) | ShiftHandover dual-interrupt | Expected (migration 005) | Part of Phase 4 | None — blocking |
| BGE-M3 model | KnowledgeCurator, DocumentationSynthesizer | Lazy-load at first encode() call | ~2GB BAAI/bge-m3 | fastembed fallback (dense-only) |
| Ollama / vLLM (LLM backend) | TrainingCoach, DocumentationSynthesizer | Expected (Docker Compose) | Qwen2.5 14B or 7B | None — LLM-free agents still work |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | Per-package pyproject.toml |
| Quick run command | `pytest apps/agents/knowledge/<agent>/tests/ -x` |
| Full suite command | `nx run-many --target=test --projects=trn-shift-handover,trn-training-coach,trn-knowledge-curator,trn-documentation-synthesizer` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRN-02 | TrainingCoach deterministic quiz scoring (pass/fail without LLM-judge) | unit | `pytest apps/agents/knowledge/training-coach/tests/test_quiz_scoring.py -x` | ❌ Wave 0 |
| TRN-02 | TrainingCoach dynamic difficulty adaption (rises on correct, falls on incorrect) | unit | `pytest apps/agents/knowledge/training-coach/tests/test_difficulty.py -x` | ❌ Wave 0 |
| TRN-02 | TrainingCoach competency sign-off HITL one-row audit on resume | unit | `pytest apps/agents/knowledge/training-coach/tests/test_hitl_lifecycle.py -x` | ❌ Wave 0 |
| TRN-03 | ShiftHandover dual-supervisor sequential interrupt — first row written between interrupts | unit | `pytest apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py -x` | ❌ Wave 0 |
| TRN-03 | ShiftHandover cross-cluster audit aggregation (given mock asyncpg → structured report) | unit | `pytest apps/agents/knowledge/shift-handover/tests/test_aggregator.py -x` | ❌ Wave 0 |
| TRN-04 | DocumentationSynthesizer citation re-anchoring: all IT anchors present in EN output | unit | `pytest apps/agents/knowledge/documentation-synthesizer/tests/test_translator.py -x` | ❌ Wave 0 |
| TRN-04 | DocumentationSynthesizer HITL: no Qdrant indexing before interrupt returns | unit | `pytest apps/agents/knowledge/documentation-synthesizer/tests/test_hitl_preindex.py -x` | ❌ Wave 0 |
| TRN-05 | All agent outputs include source_uri + timestamp in citations (citation validator) | unit | `pytest apps/agents/knowledge/*/tests/test_citation_provenance.py -x` | ❌ Wave 0 |
| D-KC-01 | KnowledgeCurator exact-dup SHA-256 detection | unit | `pytest apps/agents/knowledge/knowledge-curator/tests/test_dedup.py::test_exact_dup -x` | ❌ Wave 0 |
| D-KC-01 | KnowledgeCurator near-dup BGE-M3 cosine threshold boundary | unit | `pytest apps/agents/knowledge/knowledge-curator/tests/test_dedup.py::test_near_dup_threshold -x` | ❌ Wave 0 |
| D-X-01 | Migration 010: new ActionType values INSERT successfully; existing values still work | integration | `pytest infra/migrations/timescale/tests/test_migration_010.py -m integration -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest <agent>/tests/ -x -q` (agent under development)
- **Per wave merge:** `nx run-many --target=test --projects=sft-agents,trn-*`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/agents/knowledge/shift-handover/tests/test_aggregator.py`
- [ ] `apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py`
- [ ] `apps/agents/knowledge/training-coach/tests/test_quiz_scoring.py`
- [ ] `apps/agents/knowledge/training-coach/tests/test_difficulty.py`
- [ ] `apps/agents/knowledge/training-coach/tests/test_hitl_lifecycle.py`
- [ ] `apps/agents/knowledge/knowledge-curator/tests/test_dedup.py`
- [ ] `apps/agents/knowledge/documentation-synthesizer/tests/test_translator.py`
- [ ] `apps/agents/knowledge/documentation-synthesizer/tests/test_hitl_preindex.py`
- [ ] `apps/agents/knowledge/*/tests/test_citation_provenance.py` (4 files)
- [ ] `infra/migrations/timescale/tests/test_migration_010.py`
- [ ] All 4 `apps/agents/knowledge/*/src/trn_*/` module files (currently only `__init__.py` present)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 11 JWT — dev-mode user_roles in body |
| V3 Session Management | Yes (ShiftHandover dual-interrupt thread) | LangGraph checkpointer PostgreSQL; thread_id namespacing |
| V4 Access Control | Yes | ROLE_TO_ACL Qdrant pre-filter (Phase 5); user_roles propagated in AgentState |
| V5 Input Validation | Yes | Pydantic frozen+extra=forbid on all request models; length caps on free-text fields |
| V6 Cryptography | Yes (SHA-256 dedup) | stdlib hashlib.sha256 — never hand-roll |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection in quiz content (LLM-curated questions) | Tampering | SEC-04: sanitize SOP content before feeding to LLM; Section keys fixed, not LLM-generated |
| Citation spoofing in DocumentationSynthesizer | Repudiation | Anchor map validated post-translation; source_uri verified against Qdrant payload (not trusting LLM output directly) |
| ShiftHandover window manipulation (client-supplied ts) | Tampering | Pydantic frozen model; server validates window bounds; shift boundary times are server-configured |
| Dedup threshold manipulation | Tampering | Threshold is server-side config, not in API request body |
| HITL approval_id fabrication | Repudiation | CR-03 pattern: approval_id=None always; AuditRecord validator enforces |

---

## Sources

### Primary (HIGH confidence)
- `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py` — RetrievalPipeline.search() exact signature, RagCitation fields [VERIFIED: codebase]
- `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py` — BgeM3Embedder.encode() signature, EncodeOutput fields [VERIFIED: codebase]
- `packages/sft-agents/src/sft_agents/models/enums.py` — Current ActionType enum values (Phases 1-7) [VERIFIED: codebase]
- `packages/sft-agents/src/sft_agents/runtime/clusters.py` — build_maintenance_subgraph verbatim template [VERIFIED: codebase]
- `packages/sft-agents/src/sft_agents/tools/hitl.py` — EscalateToSupervisorTool, RequestHelpTool [VERIFIED: codebase]
- `packages/sft-agents/src/sft_agents/models/audit.py` — AuditRecord validator (approval_id=None for pending HITL) [VERIFIED: codebase]
- `.planning/phases/07-agents-maintenance-reliability/07-VERIFICATION.md` — CR-01/02/03/04/05 defects and fixes [VERIFIED: codebase]
- `.planning/phases/07-agents-maintenance-reliability/07-01-PLAN.md` — Migration 009 DROP+ADD CHECK pattern [VERIFIED: codebase]
- `.planning/phases/07-agents-maintenance-reliability/07-04-PLAN.md` — build_maintenance_subgraph + RequestHelpTool [VERIFIED: codebase]
- `.planning/phases/07-agents-maintenance-reliability/07-10-PLAN.md` — maintenance_agents.py gateway pattern [VERIFIED: codebase]
- `infra/migrations/timescale/008_create_downtime_events.sql` — downtime_events schema [VERIFIED: codebase]
- `infra/migrations/timescale/003_create_audit_actions.sql` — audit.actions schema [VERIFIED: codebase]
- `packages/sft-assets/src/sft_assets/registry.yaml` — 30 Mantis assets (loom/spinning/warping/dyeing/finishing) [VERIFIED: codebase]
- `packages/sft-domain/src/sft_domain/failure_modes.yaml` — failure mode reason_codes [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- `.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md` — Phase 5 Qdrant collections (sop/manuals/troubleshooting/training), BGE-M3 decisions [VERIFIED: codebase]
- `.planning/phases/07-agents-maintenance-reliability/07-11-PLAN.md` — bilingual docs pattern for 07-11 (IT canonical, EN parallel) [VERIFIED: codebase]

### Tertiary (LOW confidence / ASSUMED)
- A1-A4 in Assumptions Log above — unverified by direct code inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are in-repo, verified by reading source
- Architecture: HIGH — mirrors documented patterns from Phase 7 with one new element (dual-interrupt)
- Pitfalls: HIGH — CR-01/02/03 and WR-03 are verified, documented, and tested; Phase 8-specific pitfalls are logical extensions
- Open questions: MEDIUM — conclusions are well-reasoned but require planner validation

**Research date:** 2026-05-24
**Valid until:** Phase 8 execution complete (codebase is stable; patterns proven in Phase 7)
