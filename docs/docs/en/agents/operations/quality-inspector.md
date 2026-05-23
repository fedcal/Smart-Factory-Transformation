---
lang: en
agent: quality-inspector
requirements:
  - OPS-05
tags:
  - agents
  - operations
  - OPS-04
  - OPS-05
---

# QualityInspector

## Overview

`QualityInspector` consumes quality events (`QualityEvent`) emitted on the
NATS bus by **Mantis Textile Group**'s production line — defects detected
during weaving, finishing, or dyeing — and grades them by severity
(`minor` / `major` / `critical`) via an LLM grader. Based on the severity
(with per-defect override from `failure_modes.yaml`), the agent decides
whether the corrective action is auto-loggable or requires human approval.

The dye-lot identifier (`dye_lot_id`) is propagated into every proposed
action and every audit row (D-QI-04 invariant — per-lot traceability).

## Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Retrieves SOPs related to the `defect_type` to enrich the `QualityVerdict`. |

The **LLM grader** (`grade_quality_event` in `ops_quality_inspector.grader`)
is not a LangChain tool but a pure function that invokes the model directly:
this isolates the T-V6-llm-hallucination risk — a conservative fallback is
applied when `ValidationError` is raised on the Pydantic output.

## Data Sources

- **NATS JetStream** — `quality.events.>` subject consumed (input);
  `audit.actions.qi-consumer` for idempotency.
- **YAML domain** — `failure_modes.yaml` (severity → tier override).
- **Qdrant** — `sop_chunks` collection (for verdict citations).
- **PostgreSQL** — `audit.actions` and `approval_actions` tables.

## HITL Tier

Routing is defined by `_DEFAULT_SEVERITY_TIER` with per-defect overrides in
`failure_modes.yaml` (overrides may only **raise** the tier, never lower it
— `_max_tier`).

| Severity | Tier | Approver | Notes |
|----------|------|----------|-------|
| `minor` | `auto-log` (no HITL) | n/a | One `Decision.AUTO` row written to `audit.actions`. |
| `major` | `supervisor` (Tier.SUPERVISOR) | Shift supervisor on duty | Routed via `human_approval_node`. |
| `critical` | `manager+safety` (Tier.MANAGER + SAFETY_INTERLOCK) | Production manager + quality officer | `SafetyInterlockMiddleware.check` invoked even though the `QUALITY_VERDICT` action does not write to PLCs (forensic uniformity, Pitfall §9). |

## KPIs Impacted

- **Defect Rate (4-point system)** — the defect counter lets us track
  quality roll-by-roll (ASTM D5430 standard).
- **Scrap Rate** — `critical` defects with full-width lead to immediate
  scrap; tracking lets us compute the lost fraction per lot.
- **Dye Lot Deviation** — `dye_lot_id` tracks chromatic anomalies that
  stem from dye-bath deviations.

## Invocation

- **Trigger**: NATS push consumer (`quality.events.>`) — the agent is
  invoked for every event published by the line simulator or the real feed.
- **API endpoint**: `POST /v1/agents/quality-inspector/grade` (Plan 06-12,
  synchronous mode for manual inspections from the supervisor UI).
- **Thread ID**: convention `ops.quality-inspector.<event_id>`.
- **Idempotency**: `action_id = event.event_id` on `audit.actions` prevents
  double writes on NATS retries.

## Audit Footprint

- One `audit.actions` row per processed `QualityEvent`, with
  `agent_id = "quality-inspector"`, `cluster = "ops"`,
  `action_type = QUALITY_VERDICT`.
- `evidence_panel`: holds a synthetic `tool_calls=[grade_quality_event]`,
  `rag_citations` (relevant SOPs), `model = "log-only@quality-inspector"`
  for deterministic auto-log rows.
- `decision`: `AUTO` (minor) / `PENDING_APPROVAL` (major/critical).
- OPS-05 declaration (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) exposed by the agent's `metadata.py` module.
