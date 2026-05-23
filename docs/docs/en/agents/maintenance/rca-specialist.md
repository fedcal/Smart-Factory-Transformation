---
lang: en
agent: rca-specialist
requirements:
  - MNT-02
  - MNT-05
tags:
  - agents
  - maintenance
  - MNT-02
  - MNT-05
---

# RCASpecialist

## Overview

`RCASpecialist` conducts Root Cause Analysis using an iterative 5-Why
methodology. Each step must be supported by at least one citation retrieved
from the textile knowledge base (SOPs, manuals) via `rag_search`; post-LLM
validation verifies that every `source_uri` exists in PostgreSQL (Open Q5 —
full lookup).

The corrective action recommendation **always** goes through supervisor
approval (D-RCA-02 literal): there is no AUTO path for this agent. This
constraint is hardcoded in `metadata.py` — any caller-supplied tier override
is silently ignored to prevent accidental de-escalation.

Optionally, `traverse_graph` queries the Neo4j knowledge graph (Phase 5) to
explore cause-effect relationships between textile components, enriching the
5-Why chain with structured evidence beyond the SOPs.

## Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Retrieves SOPs and manuals relevant to the `problem_statement`; every `WhyStep` must contain at least one citation. |
| `traverse_graph` | Phase 5 (`sft_knowledge.tools.graph`) | Navigates the Neo4j knowledge graph for cause-effect relationships between plant components. |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Sends the complete RCA (5 WhySteps + `corrective_action`) to the shift supervisor for mandatory approval (D-RCA-02). |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Writes each step of the 5-Why chain to `audit.actions` with `action_type=RCA_CHAIN`. |

## Data Sources

- **Qdrant `sop_chunks`** — Phase 5 vector collection of textile SOPs;
  provides mandatory citations for every WhyStep.
- **Neo4j textile graph** — Phase 5 knowledge graph; used by `traverse_graph`
  for structured cause-effect relationships.
- **PostgreSQL `documents`** — reference table for validating `source_uri`
  post-retrieval (full lookup, Open Q5).
- **`maintenance.downtime_events` (migration 08)** — provides the context of
  the downtime event linked to the RCA request.

## HITL Tier

| Decision / Case | Tier | Approver |
|---|---|---|
| All RCAs — `corrective_action_recommendation` | supervisor (Decision.HITL_SUPERVISOR) | Shift supervisor |

No AUTO path: D-RCA-02 is a literal, non-configurable requirement.

## KPIs Impacted

- **rca_completeness_5why** — percentage of RCAs with a complete 5-level Why
  chain, each level with at least one citation; indicates analysis process
  quality.
- **citation_grounding_rate** — proportion of WhySteps with validated
  `source_uri`; measures residual LLM hallucination.
- **mttr_root_cause_to_fix** — time between RCA opening and application of
  the approved corrective action; reduces overall MTTR.

## Invocation

- **API endpoint**: `POST /v1/agents/rca-specialist/analyze`
  with body `{"problem_statement": "<str>", "downtime_event_id": "<uuid>", "asset_id": "<uuid>", "user_roles": ["technician"], "lang": "en"}`
- **Response**: `202 Accepted` (async HITL); the completed RCA is available
  via `GET /v1/agents/rca-specialist/result/<thread_id>` after approval.
- **Trigger**: on-demand from technician or shift supervisor after a downtime
  event.
- **Thread ID**: convention `maintenance.rca-specialist.<uuid4>`.

## Audit Footprint

- One `audit.actions` row per Why step with `agent_id = "rca-specialist"`,
  `cluster = "maintenance"`, `action_type = RCA_CHAIN`.
- `evidence_panel` includes the full `WhyStep` chain and `rag_citations` for
  every step; field `decision = "hitl_supervisor"` always.
- MNT-05 declaration (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) exposed by the agent's `metadata.py` module.
