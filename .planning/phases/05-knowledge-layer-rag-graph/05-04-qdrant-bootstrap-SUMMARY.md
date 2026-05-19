---
phase: 05-knowledge-layer-rag-graph
plan: 04
subsystem: infra
tags: [qdrant, vector-database, bootstrap, testcontainers, idempotency, hybrid-retrieval, bm42, bge-m3]

# Dependency graph
requires:
  - phase: 05-knowledge-layer-rag-graph (Wave 1, Plan 05-01)
    provides: packages/sft-knowledge SDK skeleton + tests/conftest.py with qdrant_client fixture stub
provides:
  - Idempotent CLI to bootstrap 4 Qdrant collections (sop, manuals, troubleshooting, training)
  - Named dense vector ("dense", 1024-d, COSINE, hnsw m=16 ef_construct=100) + named sparse vector ("sparse", on_disk=False) on every collection
  - 7 KEYWORD payload indexes per collection (source_uri, acl_level, lang, category, version, asset_family, sop_id)
  - Integration test (testcontainer Qdrant v1.16.1) proving first-run creation + second-run no-op idempotency
  - Working conftest qdrant_client fixture (fix for testcontainers 4.x API change)
affects: [05-08-qdrant-indexer, 05-09-retrieval-pipeline, 05-10-knowledge-ingest-service, 11-production-hardening]

# Tech tracking
tech-stack:
  added:
    - testcontainers[qdrant,neo4j]>=4.8 (sft-knowledge dev extra)
  patterns:
    - "Bootstrap-script idempotency pattern: get_collections() set-membership before create_collection; create_payload_index is server-side idempotent"
    - "CLI shape mirrors scripts/nats-bootstrap-streams.py: --<service>-url (env fallback) + --dry-run + asyncio.run(bootstrap(...))"
    - "Testcontainer URL discovery via request.config stash (avoids private _client introspection in tests)"

key-files:
  created:
    - scripts/qdrant-bootstrap.py
    - .planning/phases/05-knowledge-layer-rag-graph/05-04-qdrant-bootstrap-SUMMARY.md
  modified:
    - packages/sft-knowledge/tests/test_qdrant_indexer.py
    - packages/sft-knowledge/tests/conftest.py
    - packages/sft-knowledge/pyproject.toml
    - uv.lock

key-decisions:
  - "Lazy-import qdrant-client + model types inside bootstrap() so --dry-run works without the package installed (mirrors nats-bootstrap-streams.py pattern)"
  - "Use subprocess.run from the integration test (Approach A from PLAN) rather than importing the hyphenated script module — keeps the bootstrap a real CLI artifact and avoids __init__.py gymnastics in scripts/"
  - "Publish testcontainer URL on request.config._qdrant_url instead of having tests poke AsyncQdrantClient._client — keeps the public-fixture contract small"
  - "Add testcontainers[qdrant,neo4j] to sft-knowledge dev extras (Rule 3): Plan 05-01 imported it lazily but never declared it, blocking integration tests from running"

patterns-established:
  - "Pattern: idempotent service-bootstrap CLI — argparse(--<svc>-url + --dry-run) → asyncio.run(bootstrap(url, dry_run)) → exit 0/1"
  - "Pattern: integration-test container URL discovery via conftest stash on request.config (avoids leaking client internals)"

requirements-completed: [KNW-01]

# Metrics
duration: ~28min
completed: 2026-05-19
---

# Phase 5 Plan 04: Qdrant Idempotent Collection Bootstrap Summary

**Idempotent CLI + testcontainer-driven integration test that brings up 4 Qdrant knowledge collections (sop/manuals/troubleshooting/training) with dense (1024-d cosine) + sparse named vectors and 7 KEYWORD payload indexes, proven safe to re-run.**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-05-19T10:08:00Z (approx, from worktree spawn)
- **Completed:** 2026-05-19T10:36:11Z
- **Tasks:** 2 (matches PLAN estimate of 2 atomic commits)
- **Files modified:** 4 (1 created script + 3 modified test/config files; uv.lock auto-regenerated)

## Accomplishments

- 4 Qdrant collections defined as module-level constant + bootstrapped idempotently via `get_collections()` set-membership check before each `create_collection` call.
- Both `--dry-run` (no client import required) and live execution paths exercised; `--dry-run` exits 0 in CI without Docker.
- Integration test runs the real script as a subprocess against a live testcontainer Qdrant v1.16.1, validates dense vector size + COSINE distance + sparse named vector presence + all 7 KEYWORD payload indexes, then re-runs the script and asserts every collection logs `OK [name]: exists` (idempotency proof).
- Added a second smoke test (`test_payload_indexes_complete`) that filter-queries every indexed field to confirm runtime usability of each index.
- Closes requirement **KNW-01** (collection bootstrap).

## Task Commits

1. **Task 1: scripts/qdrant-bootstrap.py — idempotent 4-collection bootstrap** — `ca4e6a8` (feat)
2. **Task 2: Integration test test_collection_bootstrap_idempotent via testcontainer Qdrant** — `6fe48a2` (test)

_Note: STATE.md / ROADMAP.md update was explicitly excluded for this executor (parallel-wave invariant)._

## Files Created/Modified

- `scripts/qdrant-bootstrap.py` — new CLI script with `--qdrant-url` / `--dry-run`, module-level `COLLECTIONS`, `PAYLOAD_INDEX_FIELDS`, `DENSE_DIM`, async `bootstrap(url, dry_run)` entry point, lazy qdrant-client imports.
- `packages/sft-knowledge/tests/test_qdrant_indexer.py` — replaced Plan-05-01 skip-only stub with two `@pytest.mark.integration` tests: `test_collection_bootstrap_idempotent` (full schema + idempotency check) and `test_payload_indexes_complete` (filter-query smoke). `test_provenance_fields_complete` retained as a skip stub for Plan 05-08.
- `packages/sft-knowledge/tests/conftest.py` — fixed `qdrant_client` fixture to use `get_container_host_ip() + get_exposed_port(_rest_port)` instead of the non-existent `get_client_url()`; published the container URL on `request.config._qdrant_url`.
- `packages/sft-knowledge/pyproject.toml` — added `testcontainers[qdrant,neo4j]>=4.8` to dev extras.
- `uv.lock` — auto-regenerated by `uv sync --extra dev`.

## Decisions Made

- **Subprocess vs. import** — chose `subprocess.run([sys.executable, "scripts/qdrant-bootstrap.py", ...])` from the test (PLAN "Approach A"). Rationale: filename has a hyphen and `scripts/` has no `__init__.py`; turning the script into an import target would add packaging noise without functional benefit, and subprocess exercises the actual user-facing CLI surface.
- **URL discovery via fixture stash** — instead of poking `qdrant_client._client.rest_uri` (private), the conftest fixture writes the container URL to `request.config._qdrant_url`. Tests read it back through a helper that fails loudly if absent — keeps the test ↔ fixture contract explicit.
- **Lazy qdrant-client imports inside `bootstrap()`** — matches `scripts/nats-bootstrap-streams.py`. Lets `--dry-run` execute on hosts where `qdrant-client` isn't installed (e.g., a thin CI runner that only validates argparse / dry-run plans).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Broken `qdrant_client` fixture in conftest.py (inherited from Plan 05-01)**
- **Found during:** Task 2 (first run of `test_collection_bootstrap_idempotent`)
- **Issue:** `QdrantContainer.get_client_url()` does not exist in `testcontainers` 4.14.2; the fixture raised `AttributeError` and the test errored out (not just skipped).
- **Fix:** Build the URL from `container.get_container_host_ip()` + `container.get_exposed_port(container._rest_port)`. Also published the URL on `request.config._qdrant_url` so the test can consume it without scraping client internals.
- **Files modified:** `packages/sft-knowledge/tests/conftest.py`
- **Verification:** `uv run pytest tests/test_qdrant_indexer.py -m integration -v` → 2 passed.
- **Committed in:** `6fe48a2` (Task 2 commit)

**2. [Rule 3 — Blocking] Missing `testcontainers` dev dependency**
- **Found during:** Task 2 (fixture skipped with `ImportError`)
- **Issue:** `tests/conftest.py` imported `testcontainers.qdrant.QdrantContainer` and `testcontainers.neo4j.Neo4jContainer`, but `packages/sft-knowledge/pyproject.toml` did not declare `testcontainers` in `[project.optional-dependencies].dev`. Plan 05-01 added the imports without the dependency, so every integration test silently skipped.
- **Fix:** Added `testcontainers[qdrant,neo4j]>=4.8` to dev extras; ran `uv sync --extra dev`.
- **Files modified:** `packages/sft-knowledge/pyproject.toml`, `uv.lock`
- **Verification:** `python -c "from testcontainers.qdrant import QdrantContainer"` succeeds; the integration test now actually runs (previously was a silent skip).
- **Committed in:** `6fe48a2` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking dependency).
**Impact on plan:** Both fixes were necessary for the integration test to run at all — they un-break Plan 05-01 wiring that no test had previously exercised. No scope creep; no architectural changes.

## Issues Encountered

- `qdrant-client` version 1.18.0 (installed) emits a `UserWarning` against Qdrant server 1.16.1 ("minor version difference must not exceed 1"). Functional behavior unaffected for our usage (collection CRUD + payload index creation + filter queries). Documented here for awareness; no action taken — server image is pinned in `testcontainers` invocation and the warning does not gate `--check-compatibility=False`. A future Plan 05-08/05-09 may want to either pin the client to `~=1.16` or pass `check_compatibility=False`.

## User Setup Required

None — `scripts/qdrant-bootstrap.py` runs against any Qdrant URL (`--qdrant-url` or `QDRANT_URL` env) and the integration test self-provisions a container via `testcontainers`. No external service credentials needed for this plan.

## Next Phase Readiness

- **Ready for Plan 05-08** (`QdrantIndexer.upsert_batch`): collections + payload schema exist with the topology Plan 05-08 expects; the `test_provenance_fields_complete` stub is in place awaiting that plan's implementation.
- **Ready for Plan 05-09** (`RetrievalPipeline`): hybrid dense+sparse named vectors are in place per D-61, retrieval can target `using="dense"` / `using="sparse"`.
- **Ready for Plan 05-10** (`knowledge-ingest` service): the `nx run knowledge-ingest:bootstrap` step can shell out to `scripts/qdrant-bootstrap.py` once that target is defined.
- **No blockers.** Phase 11 (production hardening) will need to add TLS + API key to the script (currently dev-only `http://` URL).

## Self-Check: PASSED

- `scripts/qdrant-bootstrap.py` — FOUND
- `packages/sft-knowledge/tests/test_qdrant_indexer.py` — FOUND
- `packages/sft-knowledge/tests/conftest.py` — FOUND
- `packages/sft-knowledge/pyproject.toml` (testcontainers dev extra) — FOUND
- Commit `ca4e6a8` — FOUND in git log
- Commit `6fe48a2` — FOUND in git log
- `uv run pytest -m integration -k test_collection_bootstrap_idempotent` exit code 0 — VERIFIED
- `nx run sft-knowledge:test --args="-m integration -k test_collection_bootstrap_idempotent -v"` exit code 0 — VERIFIED
- `python3 scripts/qdrant-bootstrap.py --dry-run` exit code 0 — VERIFIED

---
*Phase: 05-knowledge-layer-rag-graph*
*Plan: 04-qdrant-bootstrap*
*Completed: 2026-05-19*
