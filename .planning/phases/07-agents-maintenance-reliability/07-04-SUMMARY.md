---
phase: 07-agents-maintenance-reliability
plan: 04
plan_id: 07-04
subsystem: sft-agents/runtime + sft-agents/tools
tags: [maintenance, cluster-routing, hitl, request-help, escalation, langgraph]
requires:
  - sft_agents.runtime.clusters.build_ops_subgraph  # D-X OPS routing analog (Phase 6 Plan 06-05)
  - sft_agents.runtime.state.AgentState              # TypedDict for routing
  - sft_agents.tools.hitl.EscalateToSupervisorTool   # Phase 6 Plan 06-05 wrapper target
provides:
  - sft_agents.runtime.clusters.build_maintenance_subgraph
  - sft_agents.runtime.clusters._MNT_DEFAULT_AGENT    # = "rca-specialist"
  - sft_agents.tools.hitl.RequestHelpInput
  - sft_agents.tools.hitl.RequestHelpTool
affects:
  - sft_agents.runtime.__init__                       # __all__ + lazy __getattr__ extended
  - sft_agents.tools.__init__                         # __all__ + import extended
tech_stack:
  added: []                                           # no new pip deps (T-V7-SC: n/a)
  patterns:
    - "D-X routing mirror (build_ops_subgraph → build_maintenance_subgraph)"
    - "Pattern D — HITL tool wrapping (no re-implementation of interrupt/safety/audit)"
key_files:
  created:
    - .planning/phases/07-agents-maintenance-reliability/07-04-SUMMARY.md
  modified:
    - packages/sft-agents/src/sft_agents/runtime/clusters.py
    - packages/sft-agents/src/sft_agents/runtime/__init__.py
    - packages/sft-agents/src/sft_agents/tools/hitl.py
    - packages/sft-agents/src/sft_agents/tools/__init__.py
    - packages/sft-agents/tests/runtime/test_clusters_maintenance.py
    - packages/sft-agents/tests/tools/test_request_help.py
decisions:
  - "Fallback default for maintenance subgraph LOCKED: _MNT_DEFAULT_AGENT = 'rca-specialist' (D-RCA-02 always-supervisor agent → safest fallback path)."
  - "RequestHelpTool injects EscalateToSupervisorTool via explicit __init__ kwarg `escalate=` (test-friendly + matches Phase 6 collaborator-injection pattern), not via PrivateAttr default factory."
  - "1000-char context clip in evidence_summary is defense-in-depth on top of schema-level max_length=2000."
metrics:
  duration_minutes: 11
  completed: 2026-05-23T17:56:21Z
  tasks_completed: 2
  files_changed: 6
  tests_added: 27
requirements: [MNT-02, MNT-03]
---

# Phase 7 Plan 04: build_maintenance_subgraph + RequestHelpTool Summary

> Maintenance-cluster intra-subgraph router (mirror of build_ops_subgraph) +
> RequestHelpTool wrapping EscalateToSupervisorTool — infrastructure prerequisites
> for Wave 3 maintenance agents (07-06/07/08/09).

## What Was Built

Two source extensions in `packages/sft-agents/` that unblock the Wave 3
maintenance agents:

1. **`build_maintenance_subgraph(child_callables)`** in
   `packages/sft-agents/src/sft_agents/runtime/clusters.py` — structural
   mirror of Phase 6's `build_ops_subgraph` (D-X OPS routing pattern).
   Routes by `state["target_agent"]` to the matching child callable; falls
   back to `_MNT_DEFAULT_AGENT == "rca-specialist"` on missing / unknown
   target and emits a `mnt_route_unknown_target` structlog warning for
   observability.

2. **`RequestHelpTool` + `RequestHelpInput`** in
   `packages/sft-agents/src/sft_agents/tools/hitl.py` — MaintenanceCoach
   surface for explicit technician help requests. WRAPS
   `EscalateToSupervisorTool._arun` per D-MC-02 / 07-PATTERNS.md Pattern D
   rather than re-implementing the interrupt / safety / audit pipeline.

Both files preserve all existing Phase 4/6 code — no refactoring of
`build_ops_subgraph` or `EscalateToSupervisorTool`.

## Planner Decision Recap — Fallback Default

`_MNT_DEFAULT_AGENT = "rca-specialist"` (locked here, per Plan 07-04
`<planner_decisions>`).

Rationale: RCASpecialist is the always-supervisor agent (D-RCA-02 literal
success criterion). An unknown-target routing therefore falls into the
safest possible path — the HITL gate is guaranteed even when the supervisor
routing table drifts. Alternatives rejected:

- `downtime-analyzer` (read-only / informational) — silently misleading: an
  unknown intent should not be answered by a deterministic SQL aggregator.
- `maintenance-coach` (multi-turn thread + checkpoint) — too much state
  setup for a fallback path.

## Delegation Pattern Verification (Pattern D — D-MC-02)

`RequestHelpTool._arun` performs exactly one call to
`EscalateToSupervisorTool._arun`, composing:

```python
evidence_summary = f"intervention={intervention_id} step={current_step} context={context[:1000]}"
suggested_action = f"Supervisor: review step {current_step} of intervention {intervention_id}"
await self._escalate._arun(reason=reason, suggested_action=..., evidence_summary=..., **kwargs)
```

Verified by `test_arun_delegates_to_escalate_exactly_once` + four field-level
delegation tests. The wrapper performs ZERO audit / queue / NATS side-effects;
all delegation goes through the underlying tool which is itself
side-effect-free pre-`interrupt()`.

## Pitfall §3 Inheritance (No audit before interrupt)

Because the wrapper performs no audit writes itself and the underlying
`EscalateToSupervisorTool` already enforces the "no audit/queue/nats write
before interrupt()" invariant (Plan 06-05 Pitfall §3), `RequestHelpTool`
inherits the guarantee by construction. On `interrupt()` replay the
coroutine re-executes from the top with no double-write risk.

The audit row written by the calling `human_approval_node` must include
`escalation_trigger: 'technician_request'` (D-MC-02) to distinguish
technician-driven escalations from autonomous agent escalations. This
contract is documented in the `RequestHelpTool` class docstring (see
`test_tool_docstring_documents_audit_marker_and_d_mc_02`).

## Test Coverage

| Test module                                                       | Tests | Status |
|-------------------------------------------------------------------|------:|--------|
| `packages/sft-agents/tests/runtime/test_clusters_maintenance.py`  |     8 | green  |
| `packages/sft-agents/tests/tools/test_request_help.py`            |    19 | green  |
| **Total new**                                                     |  **27** | **green** |
| Regression — `tests/runtime/test_clusters_ops.py`                 |     7 | green  |
| Regression — `tests/tools/test_escalate_tool.py`                  |    11 | green  |
| Regression — full `tests/tools/` + `tests/runtime/` sweep         |    63 | green  |

No regression in Phase 6 ops cluster routing or escalate tool.

### Maintenance subgraph coverage breakdown

- `routes_to_target_agent` — predictive-maintenance dispatch
- `routes_to_rca_specialist` — direct dispatch to fallback when explicitly named
- `fallback_when_target_missing` — empty state → rca-specialist + warning
- `fallback_when_target_unknown` — rogue slug → rca-specialist + warning
- `preserves_state_delta` — child-returned `{cluster, thread_id}` reaches final state
- `rejects_empty_mapping` — build-time guard
- `requires_rca_specialist_fallback` — missing fallback → ValueError
- `minimal_only_rca_specialist` — minimal valid build with just the fallback

### RequestHelp coverage breakdown

- Schema (10 tests): frozen, extra=forbid, per-field min/max constraints for
  reason / context / intervention_id / current_step (T-V7-injection-prompt-stuffing,
  T-V7-intervention-id-overflow).
- Metadata (2 tests): tool name + args_schema; docstring documents
  `escalation_trigger` + `D-MC-02`.
- Async-only (1 test): sync `_run` raises NotImplementedError with `'async-only'` hint.
- Delegation (6 tests): exactly-once call, decision passthrough, evidence_summary
  format, suggested_action format, reason passthrough, 1000-char context
  truncation in evidence_summary.

## Deviations from Plan

None — plan executed exactly as written. Both planner decisions documented in
`<planner_decisions>` were honored (rca-specialist fallback) and the verbatim
patterns from 07-PATTERNS.md Sections 1 + 2 were implemented as canonical
code.

## Auth Gates

None encountered.

## Known Stubs

None. Both new public APIs are fully wired with passing tests; no placeholder
code paths remain.

## Threat Flags

No new security-relevant surface beyond what was declared in the plan's
`<threat_model>`. The 4 maintenance threats (T-V7-route-injection,
T-V7-tool-bypass-interrupt, T-V7-injection-prompt-stuffing,
T-V7-intervention-id-overflow) are mitigated as planned via:

- Fallback to `rca-specialist` (always-HITL) for unknown routes.
- Wrapping (vs re-implementing) `EscalateToSupervisorTool` preserves
  Pitfall §3 by construction.
- `RequestHelpInput` field constraints (frozen + extra=forbid + length caps).
- 1000-char context clip in evidence_summary (defense-in-depth).

T-V7-SC (supply-chain) is n/a — no new pip deps; only source extensions in
existing files.

## TDD Gate Compliance

| Gate    | Commit  | Status |
|---------|---------|--------|
| RED     | b52d54a | `test(07-04): failing tests for build_maintenance_subgraph + RequestHelpTool` |
| GREEN 1 | bd1b5d8 | `feat(07-04): build_maintenance_subgraph cluster router (D-X mirror; fallback=rca-specialist)` |
| GREEN 2 | dc0cd90 | `feat(07-04): RequestHelpTool wrapping escalate_to_supervisor (D-MC-02)` |
| REFACTOR | —      | not needed (verbatim from 07-PATTERNS.md, no cleanup applicable) |

## Commits

| Hash    | Message                                                                                       |
|---------|-----------------------------------------------------------------------------------------------|
| b52d54a | test(07-04): failing tests for build_maintenance_subgraph + RequestHelpTool                   |
| bd1b5d8 | feat(07-04): build_maintenance_subgraph cluster router (D-X mirror; fallback=rca-specialist)  |
| dc0cd90 | feat(07-04): RequestHelpTool wrapping escalate_to_supervisor (D-MC-02)                        |

## Wave 3 Unblock

The two artifacts produced here unblock the following Wave 3 plans:

- **07-06** (PredictiveMaintenanceAgent) — needs `build_maintenance_subgraph`
  to be wired as a child callable of the maintenance cluster.
- **07-07** (RCASpecialistAgent) — same, plus relies on `rca-specialist`
  being the documented fallback target.
- **07-08** (MaintenanceCoach) — needs `RequestHelpTool` for the explicit
  technician help-request surface (D-MC-02).
- **07-09** (DowntimeAnalyzerAgent) — needs `build_maintenance_subgraph` for
  cluster routing.
- **07-10** (api-gateway) — invokes the compiled maintenance subgraph as a
  supervisor node.

## Self-Check: PASSED

Verified post-write:

- `packages/sft-agents/src/sft_agents/runtime/clusters.py` — FOUND, includes `build_maintenance_subgraph` (grep'd).
- `packages/sft-agents/src/sft_agents/tools/hitl.py` — FOUND, includes `RequestHelpTool` + `RequestHelpInput` (grep'd).
- Commit `b52d54a` — FOUND in `git log`.
- Commit `bd1b5d8` — FOUND in `git log`.
- Commit `dc0cd90` — FOUND in `git log`.
- All 45 plan-scope tests (8 + 19 + 7 + 11) green under PYTHONPATH override against worktree source.
- `from sft_agents.runtime import build_maintenance_subgraph; from sft_agents.tools.hitl import RequestHelpTool, RequestHelpInput` resolves against the worktree source.
