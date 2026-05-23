---
lang: en
agent: operator-assistant
requirements:
  - OPS-05
tags:
  - agents
  - operations
  - OPS-01
  - OPS-05
---

# OperatorAssistant

## Overview

`OperatorAssistant` is the front-line conversational agent for shop-floor
operators at **Mantis Textile Group**. It answers operational questions in
Italian and English (e.g. "Loom LOOM-01 just stopped, what should I do?"),
retrieves the relevant Standard Operating Procedures (SOPs) and sensor data,
and — when the proposed action requires a critical decision — escalates to
the shift supervisor through the Human-in-the-Loop (HITL) pipeline.

The agent is implemented as a ReAct loop (LangGraph
`create_react_agent`, recursion capped at 5 iterations) with a 5-tool
toolbelt. Each request instantiates the tools fresh: `user_roles` flow into
the RAG ACL filter without leaking across sessions (T-V6-injection
mitigation).

## Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Hybrid search over Qdrant `sop_chunks` with ACL pre-filter on `user_roles`. |
| `traverse_graph` | Phase 5 (`sft_knowledge.tools.graph`) | Traversal of the Neo4j Machine→Part→FailureMode→SOP graph. |
| `query_timescale` | Phase 3 (`sft_tools.timescale.query`) | Extracts `sensor_events` slices (TimescaleDB hypertable) per asset/window. |
| `escalate_to_supervisor` | Plan 06-05 (`sft_agents.tools.hitl`) | Creates an `approval_action` tier=SUPERVISOR and publishes it on NATS. |
| `log_event` | Plan 06-05 (`sft_agents.tools.audit`) | Writes one `audit.actions` row with `EvidencePanel` per interaction. |

## Data Sources

- **Qdrant** — `sop_chunks` collection (procedures, runbooks, textile manuals).
- **Neo4j** — textile entity graph (looms, warpers, parts, failure modes, SOPs).
- **TimescaleDB / PostgreSQL** — `sensor_events` hypertable; `audit.actions` table for logs.
- **NATS JetStream** — `hitl.approvals.new.>` subject for HITL escalation.

## HITL Tier

`OperatorAssistant` does not autonomously decide critical actions: every
escalation goes through `escalate_to_supervisor`, which inserts an entry
into the approval queue.

| Decision / Case | Tier | Approver |
|------------------|------|----------|
| Read-only informational answer | none | n/a — `log_event` audit only. |
| Procedural suggestion (link to SOP) | none | n/a — answer with inline citations. |
| Proposed operational action (stop machine, reset) | SUPERVISOR | Shift supervisor on duty. |
| Safety-critical action (PLC intervention) | MANAGER + SAFETY_INTERLOCK | Production manager + safety officer. |

## KPIs Impacted

- **MTTR** (Mean Time To Recovery) — fast answers shorten diagnosis time
  before the technician intervenes.
- **First-Time-Fix Rate** — inline SOP citations improve the odds that the
  first repair attempt actually resolves the issue.
- **Knowledge Reuse Rate** — every successful interaction is logged and
  becomes a candidate dataset for future training/curation.

## Invocation

- **API endpoint**: `POST /v1/agents/operator-assistant/chat` (Plan 06-12)
  with body `{query, user_roles, thread_id, target_agent?}`.
- **Trigger**: Manual (operator via UI), or routed by the supervisor's
  HybridRouter.
- **Thread ID**: convention `ops.operator-assistant.<uuid4>`.
- **Recursion limit**: 5 iterations (D-OA-01) — defensive cap against
  degenerate ReAct loops.

## Audit Footprint

For every interaction, the agent writes one row into `audit.actions` with:

- `agent_id = "operator-assistant"`, `cluster = "ops"`.
- `action_type = ESCALATION` (when `escalate_to_supervisor` is called) or
  log-only via `log_event`.
- `evidence_panel`: holds `input_summary` (max 500 chars), `tool_calls`,
  `rag_citations`, `confidence`, `model`, `prompt_hash`, `tokens`,
  `duration_ms`.
- `thread_id` propagated to allow end-to-end session reconstruction.
- OPS-05 declaration (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) exposed by the agent's `metadata.py` module — single
  source of truth shared with this documentation page.
