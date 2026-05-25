# C4 — Container Diagram

The container level shows the **processes/applications** that make up the platform,
their technologies and main communications.

> **SC-3 — Traceability:** every container corresponds to an application or service
> implemented in Phases 1–11. No planned but unshipped containers.

```mermaid
C4Container
    title Smart Factory Transformation — C4 Container

    Person(user, "Operator / Technician / Manager", "Interacts via browser")

    Container(ui, "Factory UI", "Angular 18+ SSR (Node.js)", "Control room dashboard: KPIs, approval queue, SSE alerts. JWT RBAC 4 roles. (Phase 10)")
    Container(gateway, "API Gateway", "FastAPI / Python", "Single entry point: JWT auth, routing to agent clusters, SSE streaming, KPI endpoints. (Phase 4, 10)")
    Container(agent_runtime, "Agent Runtime", "LangGraph + Python", "Supervisor + 4 cluster subgraphs (OPS/MNT/TRN/SCM). 16 agents, HITL interrupt-resume. (Phases 6-9)")
    Container(ot_bridge, "OT Bridge", "FastAPI / Python", "Receives OPC-UA events from simulator, publishes to NATS JetStream. Unidirectional data-diode. (Phase 3)")
    Container(knowledge_ingest, "Knowledge Ingest", "FastAPI / Python", "RAG pipeline: chunking, BGE-M3 embedding, upsert to Qdrant. (Phase 5)")

    ContainerDb(postgres, "PostgreSQL + TimescaleDB", "Relational + Time-series DB", "HITL audit trail, approvals, sensor time series, KPIs. (Phase 1)")
    ContainerDb(qdrant, "Qdrant", "Vector DB", "Vector index for hybrid RAG (dense BGE-M3 + sparse BM25). (Phase 5)")
    ContainerDb(nats, "NATS JetStream", "Message Bus", "Async event bus: OT sensors → agents; gateway commands → agents. (Phase 1)")

    System_Ext(ollama, "Ollama / vLLM", "LLM Inference — Qwen2.5 (on-premise)")
    System_Ext(opcua, "OPC-UA Simulator", "Generates textile sensor events")

    Rel(user, ui, "Uses", "HTTPS")
    Rel(ui, gateway, "REST + SSE", "HTTPS / WebSocket")
    Rel(gateway, agent_runtime, "Invokes agent", "NATS JetStream / internal")
    Rel(gateway, postgres, "Reads KPIs, approvals", "asyncpg")
    Rel(agent_runtime, postgres, "Writes audit trail, reads context", "asyncpg")
    Rel(agent_runtime, qdrant, "Hybrid RAG retrieval", "HTTP REST")
    Rel(agent_runtime, ollama, "LLM inference", "HTTP REST")
    Rel(agent_runtime, nats, "Publishes results / receives commands", "NATS JetStream")
    Rel(knowledge_ingest, qdrant, "Upsert vectors", "HTTP REST")
    Rel(knowledge_ingest, postgres, "Writes document metadata", "asyncpg")
    Rel(ot_bridge, nats, "Publishes OT events", "NATS JetStream")
    Rel(opcua, ot_bridge, "Pushes sensor events", "OPC-UA (unidirectional)")
```

## Technology Map

| Container | Technology | Phase |
|-----------|-----------|-------|
| Factory UI | Angular 18+ SSR | 10 |
| API Gateway | FastAPI 0.115+ | 4, 10 |
| Agent Runtime | LangGraph 0.4+ | 4, 6–9 |
| OT Bridge | FastAPI / asyncio | 3 |
| Knowledge Ingest | FastAPI + BGE-M3 | 5 |
| PostgreSQL + TimescaleDB | PG 16 + TimescaleDB 2.x | 1 |
| Qdrant | Qdrant 1.x | 5 |
| NATS JetStream | NATS 2.x | 1 |
| Ollama | Ollama — Qwen2.5 | 1 |

## C4 Navigation

- [C4 Context](c4-context.md) — external actors and boundaries
- [C4 Component](c4-component.md) — internal structure of the agent runtime
