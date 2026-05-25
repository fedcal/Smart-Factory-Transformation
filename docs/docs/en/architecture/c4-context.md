# C4 — Context Diagram

The context level shows **who** interacts with the Smart Factory Transformation platform
and which external systems define its operational boundary.

> **SC-3 — Traceability:** every element corresponds to an implemented component
> (Phase 1–11) or a real external system. No aspirational elements.

```mermaid
C4Context
    title Smart Factory Transformation — C4 Context

    Person(operator, "Production Operator", "Consults real-time AI suggestions and approves proposed actions")
    Person(technician, "Maintenance Technician", "Receives predictive alerts, RCA diagnoses and intervention plans")
    Person(manager, "Manager / Shift Supervisor", "Monitors KPIs, approves high-impact decisions, views dashboards")

    System(sft, "Smart Factory Transformation", "Multi-agent GenAI platform for digital transformation of textile manufacturing. 16 agents / 4 clusters; 4-tier HITL; hybrid RAG BGE-M3 + Qdrant; Angular SSR UI.")

    System_Ext(opcua_sim, "OPC-UA Simulator (svc-ot-bridge)", "Generates textile sensor events (looms, spindles, dyeing tanks) compatible with OPC-UA. UNIDIRECTIONAL flow to NATS JetStream.")
    System_Ext(erp_mes, "Enterprise ERP / MES", "External system out of scope for v1.0. Future integration point for orders and planning data.")
    System_Ext(ollama, "Ollama / vLLM (on-premise)", "Local LLM inference — Qwen2.5. No industrial data leaves the company network.")

    Rel(operator, sft, "Consults, approves/rejects AI decisions", "HTTPS — Angular SSR UI")
    Rel(technician, sft, "Reads diagnoses, plans interventions", "HTTPS — Angular SSR UI")
    Rel(manager, sft, "Monitors KPIs, manages approvals", "HTTPS — Angular SSR UI")
    Rel(opcua_sim, sft, "Publishes sensor events (unidirectional)", "OPC-UA → NATS JetStream")
    Rel(sft, ollama, "Invokes LLM inference", "HTTP REST — internal network")
    Rel(erp_mes, sft, "Future integration (out of scope v1.0)", "—")
```

## Boundary Principles

| Principle | Implementation |
|-----------|----------------|
| **OT data-diode** | `svc-ot-bridge` receives from OPC-UA and publishes to NATS — reverse flow (agents → OT) blocked at Kubernetes NetworkPolicy level (Phase 1) |
| **Self-hostable** | Ollama/vLLM on-premise: no industrial data leaves the company network |
| **4-tier HITL** | Every critical decision goes through human approval before execution (Phase 4) |

## C4 Navigation

- [C4 Container](c4-container.md) — internal components and their communication
- [C4 Component](c4-component.md) — internal structure of the agent runtime
