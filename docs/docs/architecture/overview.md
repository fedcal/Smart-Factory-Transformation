# Architettura: Overview

Questa pagina illustra l'architettura ad alto livello di Smart Factory Transformation,
con il data-flow end-to-end e i collegamenti ai tre livelli C4.

## Stack e layer

```mermaid
graph TD
    DEV[Developer / Operatore]
    REPO[Monorepo GitHub\nsmart-factory-transformation/smart-factory-transformation]
    CI[GitHub Actions CI\nnx affected + required checks]

    subgraph DEV_STACK["Stack Dev (Docker Compose)"]
        DC_CORE[Core\nPostgres + TimescaleDB + Qdrant]
        DC_OBS[Observability\nLangfuse v3]
        DC_SIM[Simulation\nNATS JetStream + OPC-UA mock]
        DC_LLM[LLM\nOllama — Qwen2.5]
    end

    subgraph PROD_STACK["Stack Produzione (Helm / k8s)"]
        AGENTS[Agenti GenAI\n4 cluster × 4 agenti]
        UI[Factory UI\nAngular 18+ SSR]
        OT[OT Bridge\nunidirezionale]
        GW[API Gateway\nFastAPI]
    end

    DOCS[GitHub Pages\nMkDocs Material IT/EN]

    DEV --> REPO
    REPO --> CI
    CI --> DEV_STACK
    CI --> DOCS
    DEV_STACK --> PROD_STACK
    PROD_STACK --> AGENTS
    PROD_STACK --> UI
    PROD_STACK --> OT
    PROD_STACK --> GW
```

## Data-flow end-to-end

Il flusso principale da evento sensore a risposta operatore:

```mermaid
flowchart LR
    SIM["Simulatore OPC-UA\n(svc-ot-bridge)"]
    NATS["NATS JetStream"]
    GW["API Gateway\n(FastAPI)"]
    SUP["Supervisor LangGraph"]
    CLU["Cluster Agente\n(OPS / MNT / TRN / SCM)"]
    RAG["RAG Pipeline\n(BGE-M3 + Qdrant)"]
    LLM["Ollama — Qwen2.5"]
    HITL["HITL\nInterrupt-Resume"]
    DB["PostgreSQL\nAudit + KPI"]
    UI["Factory UI\nAngular 18+ SSR"]
    USER["Operatore / Tecnico\n/ Manager"]

    SIM -->|"OPC-UA → NATS\n(unidirezionale)"| NATS
    NATS --> GW
    GW -->|"Invoca agente"| SUP
    SUP -->|"Router condizionale"| CLU
    CLU -->|"Retrieval contesto"| RAG
    CLU -->|"Inference LLM"| LLM
    CLU -->|"Tier REVIEW/BLOCK"| HITL
    CLU -->|"Insert audit"| DB
    HITL -->|"Espone approvazione"| GW
    GW -->|"SSE stream"| UI
    UI --> USER
    USER -->|"Approva / Rigetta"| GW
    GW -->|"Resume grafo"| SUP
```

## Principi guida

### Human-in-the-Loop (HITL)

Il principio fondamentale dell'architettura: **nessuna azione critica viene eseguita senza approvazione umana**. Ogni agente che propone un'azione rilevante espone un nodo di approvazione nella sua state machine LangGraph. L'operatore può approvare, modificare o rigettare prima dell'esecuzione.

### Unidirezionalità del layer OT

Il componente `svc-ot-bridge` implementa un principio **data-diode**: riceve segnali dall'ambiente OT (PLC, sensori, OPC-UA) e li pubblica su NATS JetStream verso il layer agenti. Il flusso inverso (agenti verso OT) è bloccato a livello di NetworkPolicy Kubernetes — gli agenti non possono inviare comandi diretti ai simulatori o all'hardware.

### Stack self-hostable

Tutto lo stack è progettato per deploy **on-premise single-tenant**: nessun dato industriale esce dalla rete aziendale. I modelli LLM girano localmente via Ollama/vLLM. La piattaforma cloud (GitHub) è usata solo per versionamento e CI pubblici.

## Layer dell'architettura

| Layer | Componenti | Piano di fase |
|-------|-----------|---------------|
| **Monorepo & CI** | Nx, GitHub Actions, pre-commit | Fase 1 |
| **Dev Stack** | Docker Compose, Langfuse, NATS, Qdrant | Fase 1 |
| **Simulazione OT** | Simulatore tessile, mock OPC-UA, NASA C-MAPSS | Fase 3 |
| **Core Agentico** | LangGraph supervisor, SDK, 16 agenti | Fase 4 |
| **Knowledge Layer** | RAG ibrido BGE-M3 + Qdrant | Fase 5 |
| **Agenti OPS** | OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector | Fase 6 |
| **Agenti MNT** | PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer | Fase 7 |
| **Agenti TRN** | ShiftHandover, TrainingCoach, KnowledgeCurator, DocumentationSynthesizer | Fase 8 |
| **Agenti SCM** | InventoryManager, EnergyOptimizer, DemandForecaster, CostAnalyzer | Fase 9 |
| **Frontend** | Angular 18+ SSR, dashboard control room | Fase 10 |
| **Osservabilità** | Langfuse v3, OpenTelemetry, Grafana | Fase 11 |

## Livelli C4

| Livello | Contenuto |
|---------|-----------|
| [C4 Context](c4-context.md) | Attori (operatore, tecnico, manager) e sistemi esterni (OPC-UA, ERP) |
| [C4 Container](c4-container.md) | Applicazioni interne: API Gateway, Agent Runtime, OT Bridge, Qdrant, NATS |
| [C4 Component](c4-component.md) | Struttura interna Agent Runtime: supervisor, 4 cluster, HITL, audit, RAG |
