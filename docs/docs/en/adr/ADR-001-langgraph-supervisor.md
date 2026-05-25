---
tags:
  - adr
  - architecture
  - agents
---

# ADR-001 — LangGraph supervisor pattern

- **Status:** Accepted
- **Phase:** Phase 4 (Core Agentic Runtime + HITL)
- **Date:** 2026

## Context

The platform must orchestrate several specialized agents (operations,
maintenance, knowledge, supply), coordinating their invocation, shared state and
human approval points. Key requirements:

- deterministic routing to the competent agent or cluster;
- shared state across steps (messages, domain context);
- native human-in-the-loop interruption points, without custom polling;
- guard-rails against costly loops (excessive agency).

An ad-hoc orchestration (imperative chains or direct calls) would make it hard to
insert controlled interruptions and to trace the decision flow.

## Decision

We adopt the **supervisor pattern** implemented with **LangGraph**: a supervisor
graph routes requests to the agents, holds the state and uses LangGraph's native
`interrupt()` to suspend the graph at approval points (HITL). Invocations enforce
an explicit `recursion_limit` as an autonomy guard-rail.

Code reference:

- `packages/sft-agents/src/sft_agents/runtime/supervisor.py` — `safe_invoke`
  (native interrupt + recursion guard).
- `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py` —
  `build_invocation_config` (`recursion_limit=25`).

## Consequences

**Positive**

- native HITL interruptions and resumes via resume-payload, no polling;
- serializable, traceable graph state (OTEL/Langfuse correlation);
- recursion guard-rail that avoids costly loops (`GraphRecursionError → 503`).

**Negative / trade-off**

- coupling to the LangGraph API; switching runtime would require re-wiring the
  graph;
- the graph model has a steeper learning curve than a linear chain.

Decision implemented and verifiable in the Phase 4 agentic runtime.
