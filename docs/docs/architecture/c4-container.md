# C4 — Diagramma di Container

Il livello container mostra i **processi/applicazioni** che compongono la piattaforma,
le tecnologie e le comunicazioni principali.

> **SC-3 — Tracciabilità:** ogni container corrisponde a un'applicazione o servizio
> implementato nelle fasi 1–11. Nessun container pianificato ma non spedito.

```mermaid
C4Container
    title Smart Factory Transformation — C4 Container

    Person(user, "Operatore / Tecnico / Manager", "Interagisce via browser")

    Container(ui, "Factory UI", "Angular 18+ SSR (Node.js)", "Dashboard control room: KPI, coda approvazioni, alert SSE. RBAC JWT 4 ruoli. (Fase 10)")
    Container(gateway, "API Gateway", "FastAPI / Python", "Punto di ingresso unico: auth JWT, routing verso cluster agenti, SSE streaming, endpoint KPI. (Fase 4, 10)")
    Container(agent_runtime, "Agent Runtime", "LangGraph + Python", "Supervisor + 4 cluster subgraph (OPS/MNT/TRN/SCM). 16 agenti, HITL interrupt-resume. (Fasi 6-9)")
    Container(ot_bridge, "OT Bridge", "FastAPI / Python", "Riceve eventi OPC-UA dal simulatore, li pubblica su NATS JetStream. Data-diode unidirezionale. (Fase 3)")
    Container(knowledge_ingest, "Knowledge Ingest", "FastAPI / Python", "Pipeline RAG: chunking, embedding BGE-M3, upsert su Qdrant. (Fase 5)")

    ContainerDb(postgres, "PostgreSQL + TimescaleDB", "Relational + Time-series DB", "Audit trail, approvazioni HITL, serie temporali sensori, KPI. (Fase 1)")
    ContainerDb(qdrant, "Qdrant", "Vector DB", "Indice vettoriale per RAG ibrido (dense BGE-M3 + sparse BM25). (Fase 5)")
    ContainerDb(nats, "NATS JetStream", "Message Bus", "Bus eventi asincrono: sensori OT → agenti; comandi gateway → agenti. (Fase 1)")

    System_Ext(ollama, "Ollama / vLLM", "LLM Inference — Qwen2.5 (on-premise)")
    System_Ext(opcua, "Simulatore OPC-UA", "Genera eventi sensore tessile")

    Rel(user, ui, "Usa", "HTTPS")
    Rel(ui, gateway, "REST + SSE", "HTTPS / WebSocket")
    Rel(gateway, agent_runtime, "Invoca agente", "NATS JetStream / interno")
    Rel(gateway, postgres, "Legge KPI, approvazioni", "asyncpg")
    Rel(agent_runtime, postgres, "Scrive audit trail, legge contesto", "asyncpg")
    Rel(agent_runtime, qdrant, "Retrieval RAG ibrido", "HTTP REST")
    Rel(agent_runtime, ollama, "Inference LLM", "HTTP REST")
    Rel(agent_runtime, nats, "Pubblica risultati / riceve comandi", "NATS JetStream")
    Rel(knowledge_ingest, qdrant, "Upsert vettori", "HTTP REST")
    Rel(knowledge_ingest, postgres, "Scrive metadati documento", "asyncpg")
    Rel(ot_bridge, nats, "Pubblica eventi OT", "NATS JetStream")
    Rel(opcua, ot_bridge, "Push eventi sensore", "OPC-UA (unidirezionale)")
```

## Mappa tecnologica

| Container | Tecnologia | Fase |
|-----------|-----------|------|
| Factory UI | Angular 18+ SSR | 10 |
| API Gateway | FastAPI 0.115+ | 4, 10 |
| Agent Runtime | LangGraph 0.4+ | 4, 6–9 |
| OT Bridge | FastAPI / asyncio | 3 |
| Knowledge Ingest | FastAPI + BGE-M3 | 5 |
| PostgreSQL + TimescaleDB | PG 16 + TimescaleDB 2.x | 1 |
| Qdrant | Qdrant 1.x | 5 |
| NATS JetStream | NATS 2.x | 1 |
| Ollama | Ollama — Qwen2.5 | 1 |

## Navigazione C4

- [C4 Context](c4-context.md) — attori esterni e confini
- [C4 Component](c4-component.md) — struttura interna dell'agent runtime
