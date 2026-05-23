# mnt-maintenance-coach

**Maintenance Agent: Guided Procedure Coach (MNT-03 + MNT-06)**

## Role

MaintenanceCoach is a conversational, multi-turn LangGraph agent that guides factory
technicians step-by-step through Standard Operating Procedures (SOPs) during a
maintenance intervention. Unlike deterministic agents (PredictiveMaintenance, DowntimeAnalyzer),
Coach is interactive: a single intervention may span hours to days with pauses, shift
handovers, and explicit help requests.

## Architecture

- **Async LangGraph thread** (D-MC-01): each intervention = one LangGraph thread with
  state persisted in PostgreSQL via the existing `langgraph_checkpoints` table (Phase 4
  migration 005 — no new migration required).
- **Thread ID**: `coach-<intervention_id>` (e.g. `coach-3f4a...`). Stable across pauses
  and resume; the `coach-` prefix distinguishes Coach threads in shared `langgraph_checkpoints`.
- **Cross-shift resume**: re-invoking with the same `thread_id` reads the persisted checkpoint
  and resumes from the exact step where the technician left off.

## MTTR Measurement

- `mttr_start` = `datetime.now(UTC)` at intervention start.
- `mttr_end` = set by `complete_node` when all SOP steps are done.
- `compute_mttr_minutes(state)` = total elapsed time (pause-inclusive).
- `compute_active_work_minutes(state)` = sum of `StepReport.duration_minutes` (active-only).

## Request Help Integration (D-MC-02)

When a technician types help keywords (`aiuto`, `help`, `stuck`, etc.) or makes an explicit
request, the LLM invokes the `request_help` tool (Phase 7 Plan 07-04). This wraps
`escalate_to_supervisor`, pausing the thread for human supervisor review. The audit row
carries `escalation_trigger: 'technician_request'` for forensic traceability (MNT-06).

## Audit Chain

Per-step audit rows with `action_type=COACH_STEP` are written AFTER each `ainvoke`
returns (Pitfall §3 — no audit before interrupt). Each row's `thread_id` follows the
pattern `maintenance.maintenance-coach.<intervention_id>.<step_no>`.

## Endpoints (implemented in 07-10)

- `POST /v1/agents/maintenance-coach/start`
- `POST /v1/agents/maintenance-coach/step`
- `POST /v1/agents/maintenance-coach/resume`
