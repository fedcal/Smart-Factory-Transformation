# C4 — Component Diagram

The component level shows the internal structure of the **Agent Runtime**:
LangGraph supervisor, 4 cluster subgraphs, and the HITL interrupt-resume mechanism.

> **SC-3 — Traceability:** every component corresponds to implemented code in
> `packages/sft-agents/` (Phases 4–9). Cluster names correspond to
> `VALID_CLUSTERS` in `sft_agents/runtime/state.py`.

```mermaid
C4Component
    title Agent Runtime — C4 Component

    Container_Boundary(runtime, "Agent Runtime (packages/sft-agents)") {

        Component(supervisor, "Supervisor LangGraph", "StateGraph(AgentState)", "Main orchestrator: receives the event, selects the target cluster, manages the HITL interrupt-resume cycle. (Phase 4)")

        Component(hitl, "HITL Interrupt-Resume", "LangGraph checkpointer + Postgres", "4 decision tiers: AUTO / SUGGEST / REVIEW / BLOCK. Suspends graph, waits for human action via API Gateway, resumes. (Phase 4)")

        Component(ops_cluster, "OPS Cluster", "build_ops_subgraph()", "4 agents: OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector. Conditional router on target_agent. (Phase 6)")

        Component(mnt_cluster, "MNT Cluster", "build_maintenance_subgraph()", "4 agents: PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer. RCASpecialist fallback (D-RCA-02). (Phase 7)")

        Component(trn_cluster, "TRN/Knowledge Cluster", "build_knowledge_subgraph()", "4 agents: ShiftHandover, TrainingCoach, KnowledgeCurator, DocumentationSynthesizer. KnowledgeCurator autonomous (D-KC-04). (Phase 8)")

        Component(scm_cluster, "SCM Cluster", "build_supply_subgraph()", "4 agents: InventoryManager, EnergyOptimizer, DemandForecaster, CostAnalyzer. CostAnalyzer autonomous (D-SCM-AUTO). (Phase 9)")

        Component(audit, "Audit Writer", "asyncpg → PostgreSQL", "Writes every ActionType to the audit trail. Immutable — every record is insert-only. (Phase 4)")

        Component(rag, "Retrieval Pipeline (RAG)", "BGE-M3 + Qdrant", "Hybrid dense + sparse BM25 retrieval. Post-chunking document sanitization. Integrated in agents requiring documentary context. (Phase 5)")
    }

    Rel(supervisor, ops_cluster, "Dispatch target_agent=ops/*", "in-process LangGraph")
    Rel(supervisor, mnt_cluster, "Dispatch target_agent=mnt/*", "in-process LangGraph")
    Rel(supervisor, trn_cluster, "Dispatch target_agent=trn/*", "in-process LangGraph")
    Rel(supervisor, scm_cluster, "Dispatch target_agent=scm/*", "in-process LangGraph")
    Rel(supervisor, hitl, "Interrupt when tier = REVIEW/BLOCK", "LangGraph checkpoint")
    Rel(ops_cluster, audit, "Writes OPS actions", "asyncpg")
    Rel(mnt_cluster, audit, "Writes MNT actions", "asyncpg")
    Rel(trn_cluster, audit, "Writes TRN actions", "asyncpg")
    Rel(scm_cluster, audit, "Writes SCM actions", "asyncpg")
    Rel(ops_cluster, rag, "Documentary context retrieval", "HTTP")
    Rel(mnt_cluster, rag, "Technical manuals retrieval", "HTTP")
    Rel(trn_cluster, rag, "SOP procedure retrieval", "HTTP")
```

## HITL — Decision Tiers

| Tier | Label | Behaviour |
|------|-------|-----------|
| 0 | AUTO | Executes without approval (autonomous agents: CostAnalyzer, KnowledgeCurator) |
| 1 | SUGGEST | Proposes to operator, executes if not rejected within timeout |
| 2 | REVIEW | Suspends, waits for explicit operator approval |
| 3 | BLOCK | Suspends, requires manager approval |

## C4 Navigation

- [C4 Context](c4-context.md) — actors and boundaries
- [C4 Container](c4-container.md) — applications and databases
