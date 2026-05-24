---
phase: 05-knowledge-layer-rag-graph
plan: 12
subsystem: knowledge-sdk
type: gap-closure
tags: [source-uri, path-utils, refactor, cr-02, knw-07]
dependency_graph:
  requires: [05-01, 05-10]
  provides: [sft_knowledge.path_utils.derive_source_uri]
  affects: [parsers/markdown.py, pipeline.py]
tech_stack:
  added: [sft_knowledge.path_utils]
  patterns: [single-source-of-truth, canonical-helper]
key_files:
  created:
    - packages/sft-knowledge/src/sft_knowledge/path_utils.py
    - packages/sft-knowledge/tests/test_source_uri_resolution.py
  modified:
    - packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py
    - services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py
    - packages/sft-knowledge/src/sft_knowledge/__init__.py
decisions:
  - "WORKSPACE_ROOT anchored via parents[4] from path_utils.py (packages/sft-knowledge/src/sft_knowledge/) giving the monorepo root consistently"
  - "Fallback uses .lstrip('/') not .lstrip(os.sep) to avoid cross-platform divergence when as_posix() always produces forward slashes"
  - "derive_source_uri and WORKSPACE_ROOT added to sft_knowledge.__all__ (now 24 symbols) so test harnesses can inject custom roots without reaching into internals"
metrics:
  duration: 5min
  completed: 2026-05-24T12:44:04Z
  tasks: 2
  files: 5
requirements: [KNW-07]
---

# Phase 05 Plan 12: source_uri Canonicalization (CR-02) Summary

**One-liner:** Single `derive_source_uri()` helper in `sft_knowledge.path_utils` replaces duplicated workspace-root walks in parser and orchestrator, closing CR-02 silent-drift surface for KNW-07 SC#3.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add equality + edge-case test for source_uri resolution | `3c8528a` | `tests/test_source_uri_resolution.py` |
| 2 (GREEN) | Extract derive_source_uri helper and route both call sites | `d487763` | `path_utils.py`, `parsers/markdown.py`, `pipeline.py`, `__init__.py` |

## What Was Built

### `sft_knowledge.path_utils` (new module)

Canonical `derive_source_uri(path, workspace_root=None) -> str` helper:
- `WORKSPACE_ROOT` computed once via `Path(__file__).resolve().parents[4]` (path_utils.py → sft_knowledge → src → sft-knowledge → packages → workspace)
- Tries `resolved.relative_to(workspace_root)` → `corpus://<rel-posix>` for in-workspace paths
- Falls back to `corpus://<resolved.as_posix().lstrip('/')>` for out-of-workspace paths
- Uses `lstrip('/')` not `lstrip(os.sep)` — cross-platform consistency since `as_posix()` always produces `/`-separated paths

### `parsers/markdown.py` refactor

- Removed `_WORKSPACE_ROOT: Path = Path(__file__).resolve().parents[5]` module constant
- Removed inline `try/except` block that duplicated the derivation logic
- Replaced with single `source_uri = derive_source_uri(path)` call
- Added `from sft_knowledge.path_utils import derive_source_uri` import

### `pipeline.py` refactor

- Removed `_derive_source_uri()` function (22 lines) and its `import os` line
- Replaced `source_uri = _derive_source_uri(path)` with `source_uri = derive_source_uri(path)`
- Added `from sft_knowledge.path_utils import derive_source_uri` import (moved outside TYPE_CHECKING block)

### `__init__.py` update

- Added `from sft_knowledge.path_utils import WORKSPACE_ROOT, derive_source_uri`
- Added both symbols to `__all__` — SDK now exports 24 symbols (was 22)

### Test suite: `test_source_uri_resolution.py`

4 parametrized tests:
1. `test_derive_source_uri_workspace_file` — in-workspace SOP gets `corpus://simulators/synthetic-corpus/...` with no backslashes
2. `test_derive_source_uri_equals_markdown_parser_output` — helper URI == MarkdownParser URI (the KNW-07 SC#3 invariant)
3. `test_derive_source_uri_tmp_path_outside_workspace` — tmp_path gets `corpus://...` with no double-slash after scheme
4. `test_derive_source_uri_symlink_inside_workspace` — symlink and realpath produce identical URI via `.resolve()`

## Verification Results

```
packages/sft-knowledge/tests/    70 passed, 23 deselected (includes 4 new)
services/knowledge-ingest/tests/  9 passed,  8 deselected
Total unit:                       79 passed  (baseline was 71; target was ≥75)
```

Static checks:
- `grep -c "_derive_source_uri|_WORKSPACE_ROOT" pipeline.py parsers/markdown.py` → 0/0 (legacy symbols removed)
- `grep -c "from sft_knowledge.path_utils import derive_source_uri" pipeline.py` → 1
- `grep -c "from sft_knowledge.path_utils import derive_source_uri" parsers/markdown.py` → 1
- `grep -c "derive_source_uri" __init__.py` → 2 (import + __all__ entry)
- `grep -rn "parents\[5\]|parents\[4\]" packages/sft-knowledge/src services/knowledge-ingest/src` → 1 match only (inside `path_utils.py`)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. This is a pure refactor/canonicalization; no new data flows or UI surfaces introduced.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## TDD Gate Compliance

- RED gate commit: `3c8528a` (test(05-12): add RED equality test for source_uri resolution helper)
- GREEN gate commit: `d487763` (refactor(05-12): extract sft_knowledge.path_utils.derive_source_uri (CR-02))
- REFACTOR gate: not needed — implementation was clean on first pass

## Self-Check: PASSED

Files exist:
- [x] `packages/sft-knowledge/src/sft_knowledge/path_utils.py` — FOUND
- [x] `packages/sft-knowledge/tests/test_source_uri_resolution.py` — FOUND

Commits exist:
- [x] `3c8528a` — FOUND (RED test)
- [x] `d487763` — FOUND (GREEN implementation)
