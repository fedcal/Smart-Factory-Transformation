---
phase: 08-agents-knowledge-training
plan: "01"
subsystem: runtime/clusters
tags: [knowledge-cluster, routing, subgraph, langgraph, hitl]
dependency_graph:
  requires: [07-04]
  provides: [08-08]
  affects: [packages/sft-agents/src/sft_agents/runtime/clusters.py]
tech_stack:
  added: []
  patterns: [conditional-routing-subgraph, autonomous-fallback-D-KC-04]
key_files:
  created:
    - packages/sft-agents/src/sft_agents/runtime/clusters.py
    - packages/sft-agents/tests/runtime/test_build_knowledge_subgraph.py
  modified: []
decisions:
  - "knowledge-curator chosen as fallback (D-KC-04): autonomous agent, no HITL, no irreversible side effects — safest routing target for unknown-target scenarios (T-08-03 mitigation)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-24T09:55:38Z"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 8 Plan 01: Knowledge Cluster Subgraph Router Summary

**One-liner:** `build_knowledge_subgraph` with autonomous knowledge-curator fallback added to clusters.py mirroring build_maintenance_subgraph (D-X-04 pattern).

## What Was Built

Knowledge cluster routing layer (`build_knowledge_subgraph`) appended to `packages/sft-agents/src/sft_agents/runtime/clusters.py`. The function mirrors `build_maintenance_subgraph` exactly, routing `state["target_agent"]` to one of four knowledge agents (shift-handover, training-coach, knowledge-curator, documentation-synthesizer) with knowledge-curator as the autonomous safe fallback per D-KC-04.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Append build_knowledge_subgraph to clusters.py | 4c7b630 | packages/sft-agents/src/sft_agents/runtime/clusters.py |
| 2 | Unit tests for routing + fallback + validation | ab6df00 | packages/sft-agents/tests/runtime/test_build_knowledge_subgraph.py |

## Verification Results

- `build_knowledge_subgraph` importable: PASSED
- `_KNW_DEFAULT_AGENT == "knowledge-curator"`: PASSED
- `"build_knowledge_subgraph" in __all__`: PASSED
- Empty mapping raises ValueError: PASSED
- Missing knowledge-curator raises ValueError: PASSED
- All 10 pytest tests green: PASSED

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `knowledge-curator` as fallback | Autonomous agent (D-KC-04): no HITL, no irreversible side effects — safest routing target for unknown-target EoP scenarios (T-08-03) |
| Mirror build_maintenance_subgraph verbatim | D-X-04 gateway pattern consistency; structural uniformity across clusters |

## Deviations from Plan

None — plan executed exactly as written. The worktree started from commit `8c2cc5d` (Phase 2), so `clusters.py` and the test directory did not yet exist; both were created as new files (vs. append in the main repo) which is equivalent from a git perspective since the worktree branch diverges from Phase 2.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. The `_route` function in `build_knowledge_subgraph` handles the T-08-03 (Elevation of Privilege) threat by routing unknown targets to the autonomous curator per plan threat model — no new surface beyond what the plan anticipated.

## Self-Check: PASSED

- packages/sft-agents/src/sft_agents/runtime/clusters.py: FOUND (commit 4c7b630)
- packages/sft-agents/tests/runtime/test_build_knowledge_subgraph.py: FOUND (commit ab6df00)
- Commit 4c7b630: FOUND
- Commit ab6df00: FOUND
- All 10 tests: PASSED
