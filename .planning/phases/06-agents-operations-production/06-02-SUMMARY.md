---
phase: 06-agents-operations-production
plan: 02
subsystem: runtime
tags: [rate-limiter, postgres, asyncpg, sliding-window, audit, anomaly-detector, D-AD-03, OPS-04]

# Dependency graph
requires:
  - phase: 04-agents-runtime
    provides: "asyncpg pool, audit.actions hypertable, governor.py SQL-constants + structlog pattern (analog)"
  - phase: 06-agents-operations-production
    provides: "Plan 06-01 Decision.SUPPRESSED enum + migration 007 admitting 'suppressed'/'ANOMALY_ALERT'"
provides:
  - "RateLimiter — PG-backed sliding-window limiter (12 alerts/h per agent)"
  - "Pattern reusable by future agents needing global-scope rate limits"
  - "Stateless limiter contract: state lives in audit.actions, restart-resilient"
affects: [06-06-anomaly-detector, 06-pp-production-planner, future ops-agents needing rate limits]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Read-only audit-backed counter (no separate Redis/in-memory state)"
    - "Module-scoped TimescaleDB testcontainer + function-scoped asyncpg pool with TRUNCATE-on-setup isolation"
    - "Async fixture using new_event_loop() for one-shot migration apply (compat with pytest-asyncio auto mode)"

key-files:
  created:
    - packages/sft-agents/src/sft_agents/runtime/rate_limit.py
  modified:
    - packages/sft-agents/src/sft_agents/runtime/__init__.py
    - packages/sft-agents/tests/runtime/test_rate_limiter.py

key-decisions:
  - "RateLimiter is read-only: caller (AnomalyDetector) writes Decision.SUPPRESSED audit row separately — keeps limiter free of AuditWriter coupling and AuditRecord shape decisions"
  - "Seeded with decision='auto' in tests (not 'suppressed') to decouple from migration 007's CHECK constraint membership — limiter cares about COUNT, not the value"
  - "Module-scoped PG container with function-scoped TRUNCATE — faster than per-test container (single ~5s startup amortized over 7 tests, total run 9s)"
  - "Use datetime.UTC alias (Python 3.12 + ruff UP017) over timezone.utc — semantically identical, project codebase mixes both forms, ruff prefers the alias"

patterns-established:
  - "Pattern: agent-scoped rate limiter via audit.actions COUNT — repeat for any agent needing global threshold without per-process state"
  - "Pattern: integration test fixture combo — module-scoped container (heavy) + function-scoped pool with TRUNCATE on setup (cheap isolation)"

requirements-completed: [OPS-04]

# Metrics
duration: ~30min
completed: 2026-05-23
---

# Phase 06 Plan 02: RateLimiter Summary

**PG-backed sliding-window rate limiter (12 alerts/h per agent) using a COUNT(*) over `audit.actions` so the threshold survives restart and the limiter holds no per-process state.**

## Performance

- **Duration:** ~30 min (planning context load + RED + GREEN + ruff align + docs)
- **Started:** 2026-05-23T~12:18Z
- **Completed:** 2026-05-23T12:48Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 3 (1 new, 2 modified)
- **Test suite:** 7 integration tests, 9.0s wall (incl. testcontainer + 7 migrations apply)

## Accomplishments

- Production-ready `RateLimiter` class with strict input validation (`pool is None` and empty `agent_id` rejected at construction).
- Single SQL constant + 3 positional placeholders (T-V6-sql-injection mitigation); zero f-string interpolation in the query path.
- Tz-aware `datetime.now(UTC) - timedelta` cutoff (Pitfall 7 / T-V6-naive-datetime mitigation).
- 7 testcontainers-PG integration tests cover boundary (5/12/15), sliding window, per-agent isolation, per-action-type isolation, and restart resilience.
- `RateLimiter` exported from `sft_agents.runtime` (canonical import path).

## Task Commits

Each task was committed atomically inside the worktree:

1. **Task 1: failing integration tests (RED)** — `699aa62` (test)
2. **Task 2: implement RateLimiter (GREEN)** — `0ea1fed` (feat)

_TDD gate sequence:_ `test(06-02): … (RED)` → `feat(06-02): … (GREEN)` (no REFACTOR commit needed — implementation was already minimal and ruff-clean after the alias adjustment, which was bundled into the GREEN commit).

## Files Created/Modified

- `packages/sft-agents/src/sft_agents/runtime/rate_limit.py` (NEW, 117 lines) — `RateLimiter` class + `_COUNT_RECENT_SQL` constant + `_log` module logger. Read-only against `audit.actions`.
- `packages/sft-agents/src/sft_agents/runtime/__init__.py` (MODIFIED) — added `from … import RateLimiter` + `"RateLimiter"` to `__all__`.
- `packages/sft-agents/tests/runtime/test_rate_limiter.py` (MODIFIED, +257 lines) — replaced Wave 0 stub with 7 integration tests using module-scoped testcontainer + asyncpg pool fixture.

## Decisions Made

1. **Limiter is read-only.** The plan was ambiguous about whether `check_and_emit` should write the `Decision.SUPPRESSED` row itself. I chose not to — the limiter doesn't know which `AuditWriter` instance, which thread_id, or which evidence panel to attach. Plan 06-06 (AnomalyDetector) will own that write, using the `(allowed, count)` return tuple to decide whether to emit. Documented in module docstring (`Pitfall §3 / scope`).
2. **Test seeding uses `decision='auto'`.** The plan explicitly suggested this to decouple from migration 007's CHECK constraint admitting `'suppressed'` — even though 007 is applied in the fixture, the limiter cares only about COUNT membership, not enum value, so `'auto'` keeps the test independent of the Phase 6 migration.
3. **Module-scoped testcontainer.** Spinning a fresh container per test (the pattern in `test_migration_007.py`) costs ~5s of overhead per case = ~35s for 7 tests. Sharing a module-scoped container with `TRUNCATE audit.actions` on each function-scoped pool setup brings the suite to 9s total with identical isolation guarantees.
4. **`datetime.UTC` alias over `timezone.utc`.** Functionally identical; ruff `UP017` flags the longer form. Existing project files (`test_rate_limit_audit_query.py`) already use the alias.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Fixture event-loop collision with pytest-asyncio "auto" mode**
- **Found during:** Task 1 verification (first RED-phase pytest run).
- **Issue:** The plan template suggested seeding via parametrize and using "existing pool fixture from packages/sft-agents/tests/conftest.py" — but the conftest pool is an `AsyncMock`, unsuitable for integration tests. I had to construct a real testcontainer + asyncpg pool fixture combination, and my first cut had two bugs:
  a) The module-scoped DSN fixture called `asyncio.get_event_loop().run_until_complete()` which collides with pytest-asyncio's `Runner.run()` (cannot be called from a running loop).
  b) An autouse async truncate fixture called `request.getfixturevalue("pg_pool")` for a not-yet-resolved async fixture, nesting Runner.run() and raising the same error.
- **Fix:** (a) Switched to `asyncio.new_event_loop() + loop.run_until_complete()` for the one-shot migration apply, properly closed afterwards. (b) Folded the `TRUNCATE audit.actions` step into the `pg_pool` fixture's setup phase (still function-scoped, no autouse needed).
- **Files modified:** packages/sft-agents/tests/runtime/test_rate_limiter.py
- **Verification:** All 7 tests pass cleanly in 9s.
- **Committed in:** 699aa62 (Task 1 commit — fixes were part of the RED-phase iteration before commit).

**2. [Rule 3 — Blocking] Ruff UP017 violation on `timezone.utc`**
- **Found during:** post-GREEN lint check (before Task 2 commit).
- **Issue:** Plan instructed `datetime.now(timezone.utc)` (per Pitfall 7), but ruff `UP017` (`Use datetime.UTC alias`) rejects the longer form on py312+. Pre-commit hook would have blocked the commit.
- **Fix:** Replaced `from datetime import datetime, timedelta, timezone` with `from datetime import UTC, datetime, timedelta`; replaced 3 call sites (1 in rate_limit.py, 2 in test_rate_limiter.py) with `datetime.now(UTC)`. Semantically identical (`datetime.UTC is timezone.utc`).
- **Files modified:** packages/sft-agents/src/sft_agents/runtime/rate_limit.py, packages/sft-agents/tests/runtime/test_rate_limiter.py
- **Verification:** `ruff check` → "All checks passed!"; all 7 tests still pass.
- **Committed in:** 0ea1fed (Task 2 commit — folded into the GREEN commit).

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking).
**Impact on plan:** Zero scope creep. Both fixes are mechanical adaptations to the real test environment (pytest-asyncio behavior + ruff config). The plan's `<behavior>` and `<action>` content was implemented verbatim — only the test-fixture plumbing required iteration.

## Issues Encountered

- **Worktree base mismatch on startup:** The worktree HEAD was at `8c2cc5d` instead of the required `d2bae2d`. The `<worktree_branch_check>` `git reset --hard d2bae2d` resolved it without manual intervention.
- **Pytest `testpaths = ["tests"]` in workspace root config:** Running pytest from the workspace root deselected my tests (root `testpaths` doesn't include `packages/…`). Resolved by running pytest from `packages/sft-agents/` so the sub-package's `pyproject.toml` becomes the active config (`rootdir` = `packages/sft-agents`).

## Self-Check

Verifying claims from this summary:

**Files exist (worktree):**
- `[ -f packages/sft-agents/src/sft_agents/runtime/rate_limit.py ]` → FOUND
- `[ -f packages/sft-agents/src/sft_agents/runtime/__init__.py ]` → FOUND
- `[ -f packages/sft-agents/tests/runtime/test_rate_limiter.py ]` → FOUND
- `[ -f .planning/phases/06-agents-operations-production/06-02-SUMMARY.md ]` → FOUND (this file)

**Commits exist:**
- `699aa62` (Task 1 RED) → FOUND
- `0ea1fed` (Task 2 GREEN) → FOUND

**Behaviour:**
- `from sft_agents.runtime import RateLimiter` → OK
- `pytest tests/runtime/test_rate_limiter.py -m integration` → 7 passed in 9.01s

## Self-Check: PASSED

## Next Phase Readiness

- **Plan 06-06 (AnomalyDetector) is unblocked.** It can now `from sft_agents.runtime import RateLimiter`, call `await limiter.check_and_emit("ANOMALY_ALERT")`, and on `(False, count)` emit its own `AuditRecord(decision=Decision.SUPPRESSED, …)`.
- **Phase 6 PG-backed counter pattern is established** and can be reused by any future agent that needs a global rate limit (e.g. Plan 06-pp production-planner if a per-planner SCHEDULE_DRAFT cap is added in Phase 11).
- **No new dependencies** added; asyncpg + structlog were already locked in Phase 3/4.

---
*Phase: 06-agents-operations-production*
*Plan: 02*
*Completed: 2026-05-23*
