# Workflow Operations (OPS)

Il cluster Operations gestisce la supervisione della produzione in tempo reale,
la pianificazione dei turni e il controllo qualità. È composto da 4 agenti
implementati nella Fase 6 del progetto.

> **SC-3 — Tracciabilità:** questo workflow mappa gli step agli agenti in
> `packages/sft-agents/src/sft_agents/` (Fase 6), al router `build_ops_subgraph()`
> e alle API in `apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py`.

## Agenti del cluster OPS

| Agente | Slug | HITL Tier | Ruolo |
|--------|------|-----------|-------|
| OperatorAssistant | `operator-assistant` | SUGGEST (1) | Supporto in tempo reale all'operatore, RAG su SOP |
| ProductionPlanner | `production-planner` | REVIEW (2) | Pianificazione turni e obiettivi produzione |
| QualityInspector | `quality-inspector` | REVIEW (2) | Ispezione qualità, verdict pass/fail/rework |
| AnomalyDetector | `anomaly-detector` | SUGGEST (1) | Rilevamento anomalie sensori, alert in tempo reale |

## Workflow end-to-end: anomalia sensore → azione operatore

```mermaid
sequenceDiagram
    autonumber
    participant SIM as Simulatore OPC-UA<br/>(svc-ot-bridge)
    participant NATS as NATS JetStream
    participant GW as API Gateway<br/>(FastAPI)
    participant SUP as Supervisor<br/>(LangGraph)
    participant AD as AnomalyDetector
    participant OA as OperatorAssistant
    participant RAG as RAG Pipeline<br/>(BGE-M3 + Qdrant)
    participant LLM as Ollama — Qwen2.5
    participant DB as PostgreSQL
    participant UI as Factory UI<br/>(Angular SSR)
    participant OP as Operatore

    SIM->>NATS: pubblica evento sensore (OPC-UA → NATS, unidirezionale)
    NATS->>GW: consegna messaggio
    GW->>SUP: invoca cluster ops / target=anomaly-detector
    SUP->>AD: dispatch (router condizionale su target_agent)
    AD->>DB: legge serie temporale sensore (TimescaleDB)
    AD->>LLM: classifica anomalia (z-score + LLM label)
    AD->>DB: insert audit ANOMALY_ALERT (insert-only)
    AD-->>GW: restituisce alert + tier=SUGGEST
    GW-->>UI: SSE stream alert
    UI-->>OP: notifica anomalia in dashboard

    OP->>GW: richiede assistenza (POST /ops/operator-assistant)
    GW->>SUP: invoca cluster ops / target=operator-assistant
    SUP->>OA: dispatch
    OA->>RAG: retrieval SOP + manuali (BGE-M3 dense + BM25 sparse)
    RAG-->>OA: chunks rilevanti (top-k)
    OA->>LLM: genera suggerimento contestualizzato
    OA->>DB: insert audit OPERATOR_ASSIST (tier SUGGEST)
    OA-->>GW: proposta azione + richiesta conferma
    GW-->>UI: SSE — proposta visibile all'operatore

    OP->>GW: approva / rigetta (POST /approvals/{id}/approve)
    GW->>DB: aggiorna stato approvazione
    GW->>SUP: resume grafo (interrupt-resume HITL)
    SUP->>DB: insert audit ACTION_EXECUTED / ACTION_REJECTED
    DB-->>GW: conferma
    GW-->>UI: SSE — esito finale
```

## Workflow: controllo qualità

```mermaid
flowchart TD
    START["Richiesta ispezione qualità\n(operatore o pianificatore)"]
    GW["API Gateway — POST /ops/quality-inspector"]
    QI["QualityInspector\n(tier REVIEW)"]
    RAG["RAG: recupera criteri qualità\n(specifiche tessile + SOP)"]
    LLM["LLM: analizza campione\nvs. specifiche"]
    VERDICT{"Verdict"}
    PASS["PASS — prodotto conforme\naudit QUALITY_VERDICT"]
    REWORK["REWORK — richiesta revisione\naudit QUALITY_VERDICT"]
    FAIL["FAIL — scarto\naudit QUALITY_VERDICT"]
    HITL["HITL REVIEW\n(attende approvazione manager)"]
    DB["PostgreSQL — insert audit"]
    UI["Factory UI — esito a schermo"]

    START --> GW --> QI --> RAG --> LLM --> VERDICT
    VERDICT -->|"Pass"| PASS --> DB --> UI
    VERDICT -->|"Rework"| REWORK --> HITL --> DB --> UI
    VERDICT -->|"Fail"| FAIL --> HITL --> DB --> UI
```

## Punti di integrazione

| Punto | Sistema | Note |
|-------|---------|------|
| Ingresso evento sensore | NATS JetStream ← OPC-UA | Unidirezionale — flusso inverso bloccato |
| Retrieval documentale | Qdrant + BGE-M3 | SOP, specifiche qualità tessile (Fase 5) |
| Inference LLM | Ollama — Qwen2.5 | On-premise, rete interna |
| Audit trail | PostgreSQL — tabella `audit_log` | Insert-only, ActionType tipizzato |
| Notifiche real-time | SSE stream `GET /sse/events` | Angular SSR riceve event stream (Fase 10) |
