# Architecture: Overview

!!! info "Details Expanding"
    This page shows the system's high-level architecture. Details for each layer
    will be documented in subsequent phases.

## High-Level Diagram

```mermaid
graph TD
    DEV[Developer / Operator]
    REPO[Monorepo GitHub\nfedcal/Smart-Factory-Transformation]
    CI[GitHub Actions CI\nnx affected + required checks]

    subgraph DEV_STACK["Dev Stack (Docker Compose)"]
        DC_CORE[Core\nPostgres + TimescaleDB + Qdrant]
        DC_OBS[Observability\nLangfuse v3]
        DC_SIM[Simulation\nNATS JetStream + OPC-UA mock]
        DC_LLM[LLM\nOllama — Qwen2.5]
    end

    subgraph PROD_STACK["Production Stack (Helm / k8s)"]
        AGENTS[GenAI Agents\n4 clusters x 4 agents]
        UI[Factory UI\nAngular 18+ SSR]
        OT[OT Bridge\nunidirectional]
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

## Guiding Principles

### Human-in-the-Loop (HITL)

The fundamental architectural principle: **no critical action is executed without human approval**. Every agent proposing a relevant action exposes an approval node in its LangGraph state machine. The operator can approve, modify, or reject before execution.

### OT Layer Unidirectionality

The `svc-ot-bridge` component implements a **data-diode** principle: it receives signals from the OT environment (PLCs, sensors, OPC-UA) and publishes them to NATS JetStream toward the agents layer. The reverse flow (agents to OT) is blocked at the Kubernetes NetworkPolicy level — agents cannot send direct commands to simulators or hardware.

### Self-Hostable Stack

The entire stack is designed for **on-premise single-tenant deployment**: no industrial data leaves the company network. LLM models run locally via Ollama/vLLM. The cloud platform (GitHub) is used only for versioning and public CI.

## Architecture Layers

| Layer | Components | Phase Plan |
|-------|-----------|-----------|
| **Monorepo & CI** | Nx, GitHub Actions, pre-commit | Phase 1 |
| **Dev Stack** | Docker Compose, Langfuse, NATS, Qdrant | Phase 1 |
| **OT Simulation** | Textile simulator, mock OPC-UA, NASA C-MAPSS | Phase 3 |
| **Core Agentic** | LangGraph supervisor, SDK, 16 agents | Phase 4 |
| **Frontend** | Angular 18+ SSR, control room dashboard | Phase 5 |
| **Production** | Helm charts, Kubernetes, SealedSecrets | Phase 1 + 6+ |

---

!!! note "Progressive Updates"
    This diagram will be enriched with component details as subsequent phases
    are completed.
