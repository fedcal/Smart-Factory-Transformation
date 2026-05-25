# Workflow Maintenance (MNT)

Il cluster Maintenance gestisce la manutenzione predittiva, la diagnosi di cause radice
e la formazione tecnica on-the-job. È composto da 4 agenti implementati nella Fase 7.

> **SC-3 — Tracciabilità:** questo workflow mappa gli step agli agenti in
> `packages/sft-agents/src/sft_agents/` (Fase 7), al router `build_maintenance_subgraph()`
> e alle API in `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py`.
> RCASpecialist è il fallback del router (D-RCA-02): un target sconosciuto viene
> sempre instradato a RCA, garantendo il gate HITL.

## Agenti del cluster MNT

| Agente | Slug | HITL Tier | Ruolo |
|--------|------|-----------|-------|
| PredictiveMaintenance | `predictive-maintenance` | SUGGEST (1) | Previsione guasti da serie temporali (NASA C-MAPSS) |
| RCASpecialist | `rca-specialist` | REVIEW (2) | Analisi causa radice — fallback del router (D-RCA-02) |
| MaintenanceCoach | `maintenance-coach` | SUGGEST (1) | Guida step-by-step intervento tecnico (RAG su manuali) |
| DowntimeAnalyzer | `downtime-analyzer` | AUTO (0) | Calcolo MTTR/MTBF da audit trail (lettura pura) |

## Workflow end-to-end: alert predittivo → intervento tecnico

```mermaid
sequenceDiagram
    autonumber
    participant SIM as Simulatore OPC-UA<br/>(svc-ot-bridge)
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
    participant TEC as Tecnico

    SIM->>NATS: vibrazione anomala (OPC-UA → NATS, unidirezionale)
    NATS->>GW: consegna evento
    GW->>SUP: invoca cluster mnt / target=predictive-maintenance
    SUP->>PM: dispatch
    PM->>DB: legge serie temporale vibrazioni (TimescaleDB)
    PM->>LLM: stima RUL (Remaining Useful Life) — modello C-MAPSS
    PM->>DB: insert audit MAINTENANCE_PREDICTION (tier SUGGEST)
    PM-->>GW: alert predittivo + probabilità guasto
    GW-->>UI: SSE — alert al tecnico

    TEC->>GW: richiede diagnosi causa radice
    GW->>SUP: invoca cluster mnt / target=rca-specialist
    SUP->>RCA: dispatch
    RCA->>RAG: retrieval manuali tecnici + storico guasti
    RAG-->>RCA: chunks rilevanti (top-k)
    RCA->>LLM: genera ipotesi causa radice
    RCA->>DB: insert audit RCA_DIAGNOSIS (tier REVIEW)
    RCA-->>GW: diagnosi + azioni proposte + richiesta approvazione

    TEC->>GW: approva diagnosi (POST /approvals/{id}/approve)
    GW->>DB: aggiorna approvazione
    GW->>SUP: resume grafo HITL

    TEC->>GW: richiede guida intervento
    GW->>SUP: invoca cluster mnt / target=maintenance-coach
    SUP->>MC: dispatch
    MC->>RAG: retrieval procedura intervento (manuale + SOP)
    RAG-->>MC: passi di intervento contestualizzati
    MC->>LLM: adatta procedura a contesto corrente
    MC->>DB: insert audit MAINTENANCE_GUIDE (tier SUGGEST)
    MC-->>GW: procedura step-by-step
    GW-->>UI: SSE — guida visibile al tecnico
    TEC->>GW: conferma completamento intervento
    GW->>DB: insert audit MAINTENANCE_COMPLETED
```

## Workflow: analisi downtime (autonomo)

```mermaid
flowchart TD
    REQ["Richiesta analisi downtime\n(schedulata o on-demand)"]
    GW["API Gateway — POST /mnt/downtime-analyzer"]
    DA["DowntimeAnalyzer\n(tier AUTO — autonomo)"]
    DB1["PostgreSQL: legge audit trail\n(eventi MAINTENANCE_* + ANOMALY_*)"]
    CALC["Calcola MTTR / MTBF\nper asset e periodo"]
    DB2["PostgreSQL: insert audit\nDOWNTIME_REPORT (insert-only)"]
    UI["Factory UI — report KPI manutenzione"]

    REQ --> GW --> DA --> DB1 --> CALC --> DB2 --> UI
```

> DowntimeAnalyzer opera in tier AUTO: è un agente di sola lettura che calcola
> metriche da dati storici senza proporre azioni irreversibili. Non richiede
> approvazione umana (D-DA pattern, Fase 7).

## Punti di integrazione

| Punto | Sistema | Note |
|-------|---------|------|
| Ingresso vibrazione | NATS JetStream ← OPC-UA | Unidirezionale |
| Retrieval manuali | Qdrant + BGE-M3 | Manuali tecnici, storico guasti (Fase 5) |
| Modello predittivo | NASA C-MAPSS | Embeddings per stima RUL (Fase 3/7) |
| Audit trail | PostgreSQL `audit_log` | Insert-only, ActionType tipizzato |
| KPI manutenzione | TimescaleDB | MTTR/MTBF calcolati da hypertable |
