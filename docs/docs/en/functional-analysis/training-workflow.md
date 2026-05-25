# Training / Knowledge Workflow (TRN)

The Knowledge cluster manages operational knowledge transfer, on-the-job training
and curation of the documentary base. It is composed of 4 agents implemented in Phase 8.

> **SC-3 — Traceability:** this workflow maps steps to agents in
> `packages/sft-agents/src/sft_agents/` (Phase 8), the `build_knowledge_subgraph()` router
> and the APIs in `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py`.
> KnowledgeCurator is the router fallback (D-KC-04): operates at tier AUTO, without
> HITL, without irreversible side effects.

## TRN cluster agents

| Agent | Slug | HITL Tier | Role |
|-------|------|-----------|------|
| ShiftHandover | `shift-handover` | REVIEW (2) | End-of-shift handover summary, knowledge transfer |
| TrainingCoach | `training-coach` | SUGGEST (1) | Contextual operator/technician coaching (RAG on SOPs) |
| KnowledgeCurator | `knowledge-curator` | AUTO (0) | Autonomous document curation, RAG index update |
| DocumentationSynthesizer | `documentation-synthesizer` | REVIEW (2) | SOP synthesis and update from operational experience |

## End-to-end workflow: end of shift → handover report

```mermaid
sequenceDiagram
    autonumber
    participant CS as Shift Supervisor<br/>(shift-supervisor role)
    participant GW as API Gateway
    participant SUP as Supervisor<br/>(LangGraph)
    participant SH as ShiftHandover
    participant RAG as RAG Pipeline<br/>(BGE-M3 + Qdrant)
    participant LLM as Ollama — Qwen2.5
    participant DB as PostgreSQL
    participant UI as Factory UI
    participant MAN as Manager / Incoming Supervisor

    CS->>GW: POST /trn/shift-handover (end of shift)
    GW->>SUP: invoke trn cluster / target=shift-handover
    SUP->>SH: dispatch
    SH->>DB: read current shift audit trail (anomalies, interventions, approvals)
    SH->>RAG: retrieval relevant SOPs
    RAG-->>SH: SOP chunks + previous shift notes
    SH->>LLM: generate structured handover (critical events, pending actions, recommendations)
    SH->>DB: insert audit SHIFT_HANDOVER (tier REVIEW)
    SH-->>GW: draft handover + approval request

    CS->>GW: approve handover (POST /approvals/{id}/approve)
    GW->>DB: update approval
    GW->>SUP: resume HITL graph
    DB-->>GW: confirmation
    GW-->>UI: SSE — final handover available
    UI-->>MAN: end-of-shift report visible in dashboard
```

## Workflow: operator coaching during intervention

```mermaid
flowchart TD
    REQ["Operator requests on-the-job assistance"]
    GW["API Gateway — POST /trn/training-coach"]
    TC["TrainingCoach\n(tier SUGGEST)"]
    RAG["RAG: retrieval SOPs + guides\n(BGE-M3 dense + BM25 sparse)"]
    LLM["LLM: generate contextual explanation\nadapted to user role (JWT RBAC)"]
    HITL{"Tier SUGGEST:\noperator accepts / ignores?"}
    DB["PostgreSQL: insert audit\nTRAINING_SESSION"]
    UI["Factory UI: step-by-step response\nvisible to operator"]

    REQ --> GW --> TC --> RAG --> LLM --> HITL
    HITL -->|"Accepted (or timeout)"| DB --> UI
    HITL -->|"Ignored"| DB
```

## Workflow: autonomous document curation

```mermaid
flowchart TD
    TRIG["Trigger: new document uploaded\n(POST /knowledge/ingest)"]
    INGEST["Knowledge Ingest Pipeline\n(chunking + BGE-M3 embedding)"]
    QDRANT["Qdrant: upsert vectors\n(dense + sparse BM25)"]
    KC["KnowledgeCurator\n(tier AUTO — autonomous, D-KC-04)"]
    DB1["PostgreSQL: read recent documents\n(metadata + chunks)"]
    LLM["LLM: assess quality, duplicates,\nconsistency with existing SOPs"]
    DB2["PostgreSQL: insert audit\nKNOWLEDGE_CURATED (insert-only)"]
    NOTE["No HITL:\nautonomous — no irreversible side effects"]

    TRIG --> INGEST --> QDRANT
    INGEST --> KC --> DB1 --> LLM --> DB2 --> NOTE
```

> KnowledgeCurator has no `/resume` endpoint: it is fully autonomous (D-KC-04).
> The gateway returns HTTP 200 (not 202) because execution is synchronous and
> without HITL suspension (Decision Phase 08-08).

## Workflow: SOP synthesis from operational experience

```mermaid
flowchart TD
    REQ["SOP synthesis request\n(manager or shift supervisor)"]
    GW["API Gateway — POST /trn/documentation-synthesizer"]
    DS["DocumentationSynthesizer\n(tier REVIEW)"]
    RAG["RAG: retrieval current SOP +\noperational audit trail"]
    LLM["LLM: generate updated SOP draft"]
    HITL["HITL REVIEW\n(manager approval)"]
    DB["PostgreSQL: insert audit\nSOP_SYNTHESIZED"]
    KC["KnowledgeCurator: index\nnew SOP on Qdrant"]

    REQ --> GW --> DS --> RAG --> LLM --> HITL
    HITL -->|"Approved"| DB --> KC
    HITL -->|"Rejected"| DB
```

## Integration points

| Point | System | Notes |
|-------|--------|-------|
| Shift audit trail | PostgreSQL `audit_log` | Data source for ShiftHandover (Phase 4) |
| SOP retrieval | Qdrant + BGE-M3 | SOPs, operational notes, previous handovers (Phase 5) |
| Document ingest | Knowledge Ingest Pipeline | Chunking + embedding + Qdrant upsert (Phase 5) |
| LLM inference | Ollama — Qwen2.5 | On-premise, internal network |
| Contextual RBAC | JWT — 4 roles | Coach response adapts to requester's role (Phase 10) |
