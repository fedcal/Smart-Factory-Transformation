---
lang: en
agent: maintenance-coach
requirements:
  - MNT-03
  - MNT-05
tags:
  - agents
  - maintenance
  - MNT-03
  - MNT-05
---

# MaintenanceCoach

## Overview

`MaintenanceCoach` guides a technician step-by-step through the execution of
a SOP for asset repair at **Mantis Textile Group**. Each intervention is an
asynchronous LangGraph thread persisted in PostgreSQL (`langgraph_checkpoints`,
migration 005), so the technician can pause and resume across shifts without
losing intervention state.

MTTR (Mean Time To Repair) is computed from `mttr_start` to `mttr_end` of the
intervention and recorded in `audit.actions`.

When the technician uses help-request keywords (`help`, `stuck`, `aiuto`,
`sono bloccato`), the `request_help` tool escalates to the supervisor with
the marker `escalation_trigger='technician_request'` in the audit payload.
The technician receives a response once the supervisor approves the next step
or modifies the SOP instruction.

## Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Retrieves the current SOP step and related safety instructions from the asset family and `reason_code`. |
| `request_help` | Phase 7 07-04 (`sft_agents.tools.hitl`) | Signals that the technician is blocked and requests supervisor assistance; sets `escalation_trigger='technician_request'`. |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Programmatic alternative for direct escalation (e.g. safety conditions). |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Writes every SOP step to `audit.actions` with `action_type=COACH_STEP`. |

## Data Sources

- **Qdrant `sop_chunks`** — Phase 5 vector collection; provides SOP steps for
  the requested asset type and intervention.
- **Phase 5 SOP corpus** — source documents used to populate Qdrant; includes
  SOP-LOOM-001..005, SOP-SPN-001..005, SOP-DYE-001..005.
- **`langgraph_checkpoints` PostgreSQL (migration 005)** — persists LangGraph
  thread state for cross-shift resume.

## HITL Tier

| Decision / Case | Tier | Approver |
|---|---|---|
| Normal SOP step | none (Decision.AUTO) | n/a |
| `request_help` invoked — technician blocked | supervisor (Decision.HITL_SUPERVISOR) | Shift supervisor — marker `escalation_trigger='technician_request'` |

## KPIs Impacted

- **mttr** — Mean Time To Repair computed as `mttr_end - mttr_start`; reduced
  by step-by-step guidance that prevents procedural errors.
- **first_time_fix_rate** — proportion of interventions completed without a
  second opening; indicates effectiveness of procedural coaching.
- **intervention_completion_rate** — percentage of Coach threads reaching
  completion vs. abandoned; measures system usability.
- **technician_help_request_rate** — frequency of `request_help` per
  intervention; high frequency signals SOPs to revise or technicians to train.

## Invocation

- **Start intervention**: `POST /v1/agents/maintenance-coach/start`
  with body `{"asset_id": "<uuid>", "reason_code": "WEAVING-BE-001", "technician_id": "<uuid>", "user_roles": ["technician"]}`
- **Next step**: `POST /v1/agents/maintenance-coach/step`
  with body `{"thread_id": "coach-<intervention_id>", "technician_input": "<str>"}`
- **Cross-shift resume**: `POST /v1/agents/maintenance-coach/resume`
  with body `{"thread_id": "coach-<intervention_id>", "technician_id": "<uuid>"}`
- **Thread ID**: convention `coach-<intervention_id>` (Open Q6).
- **Trigger**: on-demand from technician via factory-floor UI.

## Audit Footprint

- One `audit.actions` row per SOP step with `agent_id = "maintenance-coach"`,
  `cluster = "maintenance"`, `action_type = COACH_STEP`.
- `request_help` rows carry the marker `escalation_trigger='technician_request'`
  in the `action_meta` field of the payload.
- `decision`: `AUTO` (normal step) / `HITL_SUPERVISOR` (request_help).
- MNT-05 declaration (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) exposed by the agent's `metadata.py` module.
