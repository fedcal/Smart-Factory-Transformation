# C4 — Diagramma di Componente

Il livello componente mostra la struttura interna dell'**Agent Runtime**:
supervisor LangGraph, 4 cluster subgraph, meccanismo HITL interrupt-resume.

> **SC-3 — Tracciabilità:** ogni componente corrisponde a codice implementato in
> `packages/sft-agents/` (Fasi 4–9). I nomi dei cluster corrispondono a
> `VALID_CLUSTERS` in `sft_agents/runtime/state.py`.

```mermaid
C4Component
    title Agent Runtime — C4 Component

    Container_Boundary(runtime, "Agent Runtime (packages/sft-agents)") {

        Component(supervisor, "Supervisor LangGraph", "StateGraph(AgentState)", "Orchestratore principale: riceve l'evento, seleziona il cluster target, gestisce il ciclo HITL interrupt-resume. (Fase 4)")

        Component(hitl, "HITL Interrupt-Resume", "LangGraph checkpointer + Postgres", "4 tier di decisione: AUTO / SUGGEST / REVIEW / BLOCK. Sospende il grafo, attende l'azione umana via API Gateway, riprende. (Fase 4)")

        Component(ops_cluster, "OPS Cluster", "build_ops_subgraph()", "4 agenti: OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector. Router condizionale su target_agent. (Fase 6)")

        Component(mnt_cluster, "MNT Cluster", "build_maintenance_subgraph()", "4 agenti: PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer. RCASpecialist fallback (D-RCA-02). (Fase 7)")

        Component(trn_cluster, "TRN/Knowledge Cluster", "build_knowledge_subgraph()", "4 agenti: ShiftHandover, TrainingCoach, KnowledgeCurator, DocumentationSynthesizer. KnowledgeCurator autonomo (D-KC-04). (Fase 8)")

        Component(scm_cluster, "SCM Cluster", "build_supply_subgraph()", "4 agenti: InventoryManager, EnergyOptimizer, DemandForecaster, CostAnalyzer. CostAnalyzer autonomo (D-SCM-AUTO). (Fase 9)")

        Component(audit, "Audit Writer", "asyncpg → PostgreSQL", "Scrive ogni ActionType nel trail di audit. Immutabile — ogni record è insert-only. (Fase 4)")

        Component(rag, "Retrieval Pipeline (RAG)", "BGE-M3 + Qdrant", "Retrieval ibrido dense + sparse BM25. Sanitizzazione documenti post-chunking. Integrato in agenti che necessitano di contesto documentale. (Fase 5)")
    }

    Rel(supervisor, ops_cluster, "Dispatching target_agent=ops/*", "in-process LangGraph")
    Rel(supervisor, mnt_cluster, "Dispatching target_agent=mnt/*", "in-process LangGraph")
    Rel(supervisor, trn_cluster, "Dispatching target_agent=trn/*", "in-process LangGraph")
    Rel(supervisor, scm_cluster, "Dispatching target_agent=scm/*", "in-process LangGraph")
    Rel(supervisor, hitl, "Interrupt quando tier = REVIEW/BLOCK", "LangGraph checkpoint")
    Rel(ops_cluster, audit, "Scrive azioni OPS", "asyncpg")
    Rel(mnt_cluster, audit, "Scrive azioni MNT", "asyncpg")
    Rel(trn_cluster, audit, "Scrive azioni TRN", "asyncpg")
    Rel(scm_cluster, audit, "Scrive azioni SCM", "asyncpg")
    Rel(ops_cluster, rag, "Retrieval contesto documentale", "HTTP")
    Rel(mnt_cluster, rag, "Retrieval manuali tecnici", "HTTP")
    Rel(trn_cluster, rag, "Retrieval procedure SOP", "HTTP")
```

## HITL — Livelli di decisione

| Tier | Label | Comportamento |
|------|-------|--------------|
| 0 | AUTO | Esegue senza approvazione (agenti autonomi: CostAnalyzer, KnowledgeCurator) |
| 1 | SUGGEST | Propone all'operatore, esegue se non rigettato entro timeout |
| 2 | REVIEW | Sospende, attende approvazione esplicita dell'operatore |
| 3 | BLOCK | Sospende, richiede approvazione del manager |

## Navigazione C4

- [C4 Context](c4-context.md) — attori e confini
- [C4 Container](c4-container.md) — applicazioni e database
