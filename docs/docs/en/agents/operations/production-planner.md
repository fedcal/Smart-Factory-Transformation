---
lang: en
agent: production-planner
requirements:
  - OPS-05
tags:
  - agents
  - operations
  - OPS-03
  - OPS-05
---

# ProductionPlanner

## Overview

`ProductionPlanner` is the production-scheduling agent for **Mantis Textile
Group**. It consumes the open-order list, the asset capacity table (looms,
warpers, finishing lines), and the registry of known failure modes, then
emits a deterministic schedule draft using a heuristic chosen by the caller
(`spt` — Shortest Processing Time, or `edd` — Earliest Due Date).

The LLM **never mutates** the planned items: it is invoked solely to generate
the `rationale_md` (T-V6-llm-hallucination). The final draft is always
routed to the shift supervisor (`Tier.SUPERVISOR`) via
`human_approval_node`.

## Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Retrieves 5 SOPs relevant to the strategy (`spt`/`edd`); used only for citations in the rationale. |

Note: the scheduling algorithm is a pure function
(`sft_domain.scheduling.heuristic.schedule_spt` / `schedule_edd`,
Plan 06-04) and is **not** exposed as a tool — it is called directly by
the orchestrator.

## Data Sources

- **YAML domain** — `orders.yaml`, `asset_capacity.yaml`,
  `failure_modes.yaml` loaded via `sft_domain.ops.schedule` loaders.
- **Qdrant** — `sop_chunks` collection (used for rationale citations).
- **PostgreSQL** — `audit.actions` table (output: schedule draft + HITL decision).
- **NATS JetStream** — `hitl.approvals.new.ops.production-planner.>` subject.

## HITL Tier

`ProductionPlanner` never has auto-apply rights: every schedule draft
requires human approval regardless of strategy or horizon.

| Decision / Case | Tier | Approver |
|------------------|------|----------|
| Schedule draft (any strategy / horizon) | SUPERVISOR | Shift supervisor on duty. |
| Explicit SafetyInterlock override | n/a — scheduling does not write PLCs | n/a |

T-V6-hitl-bypass is mitigated by the fact that the agent has no
`Decision.AUTO` branch.

## KPIs Impacted

- **On-Time Delivery Rate** — the EDD heuristic maximises the probability
  of delivering before `due_at`; SPT minimises the makespan.
- **OEE Availability** — deterministically filling asset windows reduces
  dead time between orders.
- **Schedule Stability** — deterministic recomputations (same input ⇒ same
  `schedule_id`) let the supervisor compare drafts side by side.

## Invocation

- **API endpoint**: `POST /v1/agents/production-planner/plan` (Plan 06-12)
  with body `{strategy, horizon_days, user_roles, thread_id}`.
- **Trigger**: Manual (shift supervisor / planner via UI) — not an automated
  scheduler (planning is a management act, not a loop).
- **Thread ID**: convention `ops.production-planner.<session-uuid>`.

## Audit Footprint

- `audit.actions` row with `agent_id = "production-planner"`,
  `action_type = SCHEDULE_DRAFT`, `decision = PENDING_APPROVAL`.
- `evidence_panel`: `tool_calls=[]` (deterministic algorithm),
  `rag_citations` populated with the 5 retrieved SOPs,
  `model = "schedule-heuristic@sft-domain"` for the deterministic row.
- `approval_id` linked to the row in `approval_actions`.
- OPS-05 declaration (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) exposed by the agent's `metadata.py` module.
