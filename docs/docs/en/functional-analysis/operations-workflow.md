# Operations Workflow (OPS)

The Operations cluster manages real-time production supervision, shift planning and quality control.
It is composed of 4 agents implemented in Phase 6 of the project.

> **SC-3 — Traceability:** this workflow maps steps to agents in
> `packages/sft-agents/src/sft_agents/` (Phase 6), the `build_ops_subgraph()` router
> and the APIs in `apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py`.

## OPS cluster agents

| Agent | Slug | HITL Tier | Role |
|-------|------|-----------|------|
| OperatorAssistant | `operator-assistant` | SUGGEST (1) | Real-time operator support, RAG on SOPs |
| ProductionPlanner | `production-planner` | REVIEW (2) | Shift planning and production targets |
| QualityInspector | `quality-inspector` | REVIEW (2) | Quality inspection, pass/fail/rework verdict |
| AnomalyDetector | `anomaly-detector` | SUGGEST (1) | Sensor anomaly detection, real-time alerts |

## End-to-end workflow: sensor anomaly → operator action

```mermaid
sequenceDiagram
    autonumber
    participant SIM as OPC-UA Simulator<br/>(svc-ot-bridge)
    participant NATS as NATS JetStream
    participant GW as API Gateway<br/>(FastAPI)
    participant SUP as Supervisor<br/>(LangGraph)
    participant AD as AnomalyDetector
    participant OA as OperatorAssistant
    participant RAG as RAG Pipeline<br/>(BGE-M3 + Qdrant)
    participant LLM as Ollama — Qwen2.5
    participant DB as PostgreSQL
    participant UI as Factory UI<br/>(Angular SSR)
    participant OP as Operator

    SIM->>NATS: publish sensor event (OPC-UA → NATS, unidirectional)
    NATS->>GW: deliver message
    GW->>SUP: invoke ops cluster / target=anomaly-detector
    SUP->>AD: dispatch (conditional router on target_agent)
    AD->>DB: read sensor time series (TimescaleDB)
    AD->>LLM: classify anomaly (z-score + LLM label)
    AD->>DB: insert audit ANOMALY_ALERT (insert-only)
    AD-->>GW: alert + tier=SUGGEST
    GW-->>UI: SSE stream alert
    UI-->>OP: anomaly notification in dashboard

    OP->>GW: request assistance (POST /ops/operator-assistant)
    GW->>SUP: invoke ops cluster / target=operator-assistant
    SUP->>OA: dispatch
    OA->>RAG: retrieval SOP + manuals (BGE-M3 dense + BM25 sparse)
    RAG-->>OA: relevant chunks (top-k)
    OA->>LLM: generate contextualised suggestion
    OA->>DB: insert audit OPERATOR_ASSIST (tier SUGGEST)
    OA-->>GW: proposed action + confirmation request
    GW-->>UI: SSE — proposal visible to operator

    OP->>GW: approve / reject (POST /approvals/{id}/approve)
    GW->>DB: update approval status
    GW->>SUP: resume graph (HITL interrupt-resume)
    SUP->>DB: insert audit ACTION_EXECUTED / ACTION_REJECTED
    DB-->>GW: confirmation
    GW-->>UI: SSE — final outcome
```

## Workflow: quality control

```mermaid
flowchart TD
    START["Quality inspection request\n(operator or planner)"]
    GW["API Gateway — POST /ops/quality-inspector"]
    QI["QualityInspector\n(tier REVIEW)"]
    RAG["RAG: retrieve quality criteria\n(textile specs + SOPs)"]
    LLM["LLM: analyse sample\nvs. specifications"]
    VERDICT{"Verdict"}
    PASS["PASS — conforming product\naudit QUALITY_VERDICT"]
    REWORK["REWORK — revision requested\naudit QUALITY_VERDICT"]
    FAIL["FAIL — scrap\naudit QUALITY_VERDICT"]
    HITL["HITL REVIEW\n(awaiting manager approval)"]
    DB["PostgreSQL — insert audit"]
    UI["Factory UI — outcome on screen"]

    START --> GW --> QI --> RAG --> LLM --> VERDICT
    VERDICT -->|"Pass"| PASS --> DB --> UI
    VERDICT -->|"Rework"| REWORK --> HITL --> DB --> UI
    VERDICT -->|"Fail"| FAIL --> HITL --> DB --> UI
```

## Integration points

| Point | System | Notes |
|-------|--------|-------|
| Sensor event input | NATS JetStream ← OPC-UA | Unidirectional — reverse flow blocked |
| Documentary retrieval | Qdrant + BGE-M3 | SOPs, textile quality specs (Phase 5) |
| LLM inference | Ollama — Qwen2.5 | On-premise, internal network |
| Audit trail | PostgreSQL — `audit_log` table | Insert-only, typed ActionType |
| Real-time notifications | SSE stream `GET /sse/events` | Angular SSR receives event stream (Phase 10) |
