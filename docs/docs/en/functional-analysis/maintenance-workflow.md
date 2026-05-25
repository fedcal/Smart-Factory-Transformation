# Maintenance Workflow (MNT)

The Maintenance cluster manages predictive maintenance, root cause analysis and
technical on-the-job training. It is composed of 4 agents implemented in Phase 7.

> **SC-3 — Traceability:** this workflow maps steps to agents in
> `packages/sft-agents/src/sft_agents/` (Phase 7), the `build_maintenance_subgraph()` router
> and the APIs in `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py`.
> RCASpecialist is the router fallback (D-RCA-02): an unknown target is always routed
> to RCA, guaranteeing the HITL gate.

## MNT cluster agents

| Agent | Slug | HITL Tier | Role |
|-------|------|-----------|------|
| PredictiveMaintenance | `predictive-maintenance` | SUGGEST (1) | Failure prediction from time series (NASA C-MAPSS) |
| RCASpecialist | `rca-specialist` | REVIEW (2) | Root cause analysis — router fallback (D-RCA-02) |
| MaintenanceCoach | `maintenance-coach` | SUGGEST (1) | Step-by-step intervention guide (RAG on manuals) |
| DowntimeAnalyzer | `downtime-analyzer` | AUTO (0) | MTTR/MTBF calculation from audit trail (read-only) |

## End-to-end workflow: predictive alert → technical intervention

```mermaid
sequenceDiagram
    autonumber
    participant SIM as OPC-UA Simulator<br/>(svc-ot-bridge)
    participant NATS as NATS JetStream
    participant GW as API Gateway
    participant SUP as Supervisor<br/>(LangGraph)
    participant PM as PredictiveMaintenance
    participant RCA as RCASpecialist
    participant MC as MaintenanceCoach
    participant RAG as RAG Pipeline<br/>(BGE-M3 + Qdrant)
    participant LLM as Ollama — Qwen2.5
    participant DB as PostgreSQL
    participant UI as Factory UI
    participant TEC as Technician

    SIM->>NATS: abnormal vibration (OPC-UA → NATS, unidirectional)
    NATS->>GW: deliver event
    GW->>SUP: invoke mnt cluster / target=predictive-maintenance
    SUP->>PM: dispatch
    PM->>DB: read vibration time series (TimescaleDB)
    PM->>LLM: estimate RUL (Remaining Useful Life) — C-MAPSS model
    PM->>DB: insert audit MAINTENANCE_PREDICTION (tier SUGGEST)
    PM-->>GW: predictive alert + failure probability
    GW-->>UI: SSE — alert to technician

    TEC->>GW: request root cause diagnosis
    GW->>SUP: invoke mnt cluster / target=rca-specialist
    SUP->>RCA: dispatch
    RCA->>RAG: retrieval technical manuals + failure history
    RAG-->>RCA: relevant chunks (top-k)
    RCA->>LLM: generate root cause hypotheses
    RCA->>DB: insert audit RCA_DIAGNOSIS (tier REVIEW)
    RCA-->>GW: diagnosis + proposed actions + approval request

    TEC->>GW: approve diagnosis (POST /approvals/{id}/approve)
    GW->>DB: update approval
    GW->>SUP: resume HITL graph

    TEC->>GW: request intervention guide
    GW->>SUP: invoke mnt cluster / target=maintenance-coach
    SUP->>MC: dispatch
    MC->>RAG: retrieval intervention procedure (manual + SOP)
    RAG-->>MC: contextualised intervention steps
    MC->>LLM: adapt procedure to current context
    MC->>DB: insert audit MAINTENANCE_GUIDE (tier SUGGEST)
    MC-->>GW: step-by-step procedure
    GW-->>UI: SSE — guide visible to technician
    TEC->>GW: confirm intervention completion
    GW->>DB: insert audit MAINTENANCE_COMPLETED
```

## Workflow: downtime analysis (autonomous)

```mermaid
flowchart TD
    REQ["Downtime analysis request\n(scheduled or on-demand)"]
    GW["API Gateway — POST /mnt/downtime-analyzer"]
    DA["DowntimeAnalyzer\n(tier AUTO — autonomous)"]
    DB1["PostgreSQL: read audit trail\n(MAINTENANCE_* + ANOMALY_* events)"]
    CALC["Calculate MTTR / MTBF\nper asset and period"]
    DB2["PostgreSQL: insert audit\nDOWNTIME_REPORT (insert-only)"]
    UI["Factory UI — maintenance KPI report"]

    REQ --> GW --> DA --> DB1 --> CALC --> DB2 --> UI
```

> DowntimeAnalyzer operates at tier AUTO: it is a read-only agent that computes
> metrics from historical data without proposing irreversible actions. No human
> approval is required (D-DA pattern, Phase 7).

## Integration points

| Point | System | Notes |
|-------|--------|-------|
| Vibration input | NATS JetStream ← OPC-UA | Unidirectional |
| Manual retrieval | Qdrant + BGE-M3 | Technical manuals, failure history (Phase 5) |
| Predictive model | NASA C-MAPSS | Embeddings for RUL estimation (Phase 3/7) |
| Audit trail | PostgreSQL `audit_log` | Insert-only, typed ActionType |
| Maintenance KPIs | TimescaleDB | MTTR/MTBF computed from hypertable |
