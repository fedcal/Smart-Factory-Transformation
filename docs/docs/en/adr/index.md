---
tags:
  - adr
  - architecture
---

# ADR — Architecture Decision Records

This register collects the significant architectural decisions made during the
development of the open-source agentic platform for the textile manufacturing
industry. Each ADR follows a MADR-like format (Title, Status, Context, Decision,
Consequences) and **traces to a decision that was actually implemented**, citing
the development phase and the reference code (SC-3).

## Register

| # | Title | Status | Phase | Decision |
|---|-------|--------|-------|----------|
| [ADR-001](ADR-001-langgraph-supervisor.md) | LangGraph supervisor pattern | Accepted | Phase 4 | Agentic orchestration via supervisor graph + native HITL |
| [ADR-002](ADR-002-qdrant-bge-m3.md) | Qdrant + BGE-M3 hybrid retrieval | Accepted | Phase 5 | Qdrant vector store with multilingual BGE-M3 embeddings (dense+sparse) |
| [ADR-003](ADR-003-self-hosted-llm.md) | Self-hosted LLM via Ollama | Accepted | Phase 1/4 | On-premise LLM inference, no cloud API dependency |
| [ADR-004](ADR-004-hitl-tiers.md) | 4-tier HITL approval | Accepted | Phase 4 | Human-in-the-loop approval chain per role (RBAC) |
| [ADR-005](ADR-005-mkdocs-i18n.md) | MkDocs Material docs + i18n | Accepted | Phase 1 | Bilingual IT/EN docs site with mkdocs-static-i18n |

## Format

Each ADR documents:

- **Status** — decision status (`Accepted`, `Superseded`, ...).
- **Context** — the problem and constraints that motivated the decision.
- **Decision** — the choice that was adopted.
- **Consequences** — positive and negative consequences, accepted trade-offs.

!!! note "Traceability (SC-3)"
    Every decision recorded here is verifiable in the code and in the cited
    development phases; ADRs do not describe hypothetical or unimplemented
    decisions.
