---
phase: 05-knowledge-layer-rag-graph
plan: 11
subsystem: sft-knowledge / tools / graph
tags: [security, cypher-injection, pydantic, defense-in-depth, tdd, gap-closure]
dependency_graph:
  requires: [05-09-retrieval-pipeline-tools-memory-SUMMARY.md]
  provides: [TraverseGraphTool injection-proof on both ainvoke and _arun paths]
  affects: [Phase 6 agents wiring TraverseGraphTool into LangChain runnables]
tech_stack:
  added: []
  patterns: [re-validation of raw kwargs via Pydantic model inside _arun (defense-in-depth)]
key_files:
  created:
    - packages/sft-knowledge/tests/test_traverse_graph_injection.py
  modified:
    - packages/sft-knowledge/src/sft_knowledge/tools/graph.py
decisions:
  - "_arun re-validates via TraverseGraphInput as FIRST statement, before any Cypher composition; ValidationError propagates naturally (not caught)"
  - "All post-validation references use validated.* attributes — raw kwargs never reach Cypher after the gate"
  - "_run docstring updated to remove `await tool._arun(...)` invitation; directs callers to `ainvoke({...})` only"
metrics:
  duration: 12min
  completed: 2026-05-24
  tasks_completed: 2
  files_changed: 2
---

# Phase 5 Plan 11: TraverseGraphTool _arun Injection Defense Summary

**One-liner:** Re-validation of `_arun` inputs via `TraverseGraphInput` before Cypher composition closes the CR-01 bypass that allowed arbitrary strings to reach Neo4j when the tool was called directly.

---

## What Was Built

Closed VERIFICATION.md gap 1 (KNW-09 BLOCKER / CR-01): `TraverseGraphTool._arun()` previously accepted arbitrary strings for `seed_label` and `relation_path` because Pydantic `Literal` validation only fired on the `args_schema`/`ainvoke()` entry path. Direct `_arun()` calls bypassed the whitelist and could compose destructive Cypher. The verifier reproduced the bypass in-process with payload `seed_label='Machine) DETACH DELETE n MATCH (x'`.

### Task 1 — RED (test_traverse_graph_injection.py)

Created regression test file with 4 tests:
- `test_arun_rejects_injection_seed_label`: verifier-reproduced payload raises `ValidationError`; `driver.session()` not called.
- `test_arun_rejects_injection_relation_path`: `"HAS_PART; DROP DATABASE neo4j"` raises `ValidationError`; `driver.session()` not called.
- `test_arun_rejects_out_of_range_max_depth`: `max_depth=99` raises `ValidationError`; `driver.session()` not called.
- `test_arun_happy_path_with_valid_literals`: valid Literals reach `session.run()` exactly once; returns a list.

All 3 injection tests FAILED (RED) against the unfixed `graph.py` — confirmed.

### Task 2 — GREEN (graph.py)

Modified `_arun` body to construct `TraverseGraphInput(seed_label=..., seed_id=..., relation_path=..., max_depth=...)` as the **first statement**, before the empty-list early return and before any Cypher composition. All subsequent references use `validated.*` attributes. Any `pydantic.ValidationError` propagates naturally.

Additional changes:
- Module docstring updated to note defense-in-depth re-validation.
- `_run` docstring updated: removed the `await tool._arun(...)` invitation; replaced with `Use \`await tool.ainvoke({...})\` only.`
- `NotImplementedError` message updated to remove `_arun` reference.

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| test_traverse_graph_injection.py | 4 | 4 PASSED (GREEN) |
| test_acl_enforcement.py | 15 | 15 PASSED (no regression) |
| Full sft-knowledge unit suite (not integration, not gpu) | 66 | 66 PASSED |

Static checks:
- `grep -n "TraverseGraphInput(" graph.py | grep -v "args_schema|class"` → line 125 (validation call site in `_arun` body).
- `grep -c "await tool._arun" graph.py` → 0 (misleading hint removed).
- `grep -c "DETACH DELETE n MATCH" test_traverse_graph_injection.py` → 3 (verifier payload present verbatim).

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. The fix reduces attack surface by closing the CR-01 bypass (T-05-11-01 mitigated). No new threat flags.

---

## Self-Check: PASSED

- File `packages/sft-knowledge/tests/test_traverse_graph_injection.py` exists.
- File `packages/sft-knowledge/src/sft_knowledge/tools/graph.py` modified.
- Commit `962a3f5` (test RED) exists.
- Commit `e7d4d03` (fix GREEN) exists.
- All 4 injection regression tests PASS.
- All 66 unit tests PASS.
- `grep -c "await tool._arun" graph.py` = 0.
- `grep -n "TraverseGraphInput(" graph.py | grep -v "args_schema|class"` returns line 125.
