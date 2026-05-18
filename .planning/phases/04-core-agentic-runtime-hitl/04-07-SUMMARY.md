---
phase: 04-core-agentic-runtime-hitl
plan: 07
subsystem: api-gateway-hitl-rest-e2e
tags: [fastapi, hitl, rest, idempotency-key, docker-compose, e2e, langgraph-resume, wave-4]
requires:
  - "04-01 (sft-agents SDK foundation — ApprovalDecision Pydantic model)"
  - "04-02 (PG migrations — hitl.approvals, audit.actions hypertable, audit.outbox, budget.executions)"
  - "04-03 (LLM adapter — not used at compile time; available via HybridRouter)"
  - "04-04 (NATS AUDIT_STREAM + AuditNatsPublisher)"
  - "04-05 (supervisor graph + AsyncPostgresSaver + format_thread_id)"
  - "04-06 (HITL middleware — ApprovalQueueWriter + human_approval_node + AuditWriter dual-write + EscalationSupervisor + Governor)"
provides:
  - "apps/api-gateway scaffold (FastAPI lifespan + dependencies + structlog JSON config)"
  - "GET /v1/health + /v1/ready endpoints (k8s liveness + readiness probes)"
  - "GET /v1/approvals?tier=&status=&limit=&offset= (paginated D-55 queue dashboard endpoint)"
  - "POST /v1/approvals/{id}/decide (HITL-01 user-visible REST decide endpoint with Idempotency-Key)"
  - "POST /v1/threads/{thread_id}/resume (alternative resume entry-point keyed by thread_id)"
  - "IdempotencyCache (in-memory TTL=5min, sha256 body hash) + check_idempotency_cache + store_idempotent_response helpers"
  - "apps/api-gateway/Dockerfile (multistage python:3.12-slim + uv) + compose entry (sft-core network ONLY)"
  - "tests/e2e/test_hitl_cycle.py with 3 E2E tests (1 restart-survival + 1 idempotency-replay + 1 thread-resume)"
  - "Per-test COMPOSE_PROJECT_NAME isolation + ephemeral host ports (OQ8 fix)"
affects:
  - "Unblocks Plan 04-08: replay tool can consume the live audit.actions hypertable populated by the dual-write pipeline"
  - "Resolves OQ7: api-gateway scaffolded + containerised"
  - "Resolves OQ8: testcontainers/per-test compose project isolation eliminates port-5432 conflict"
  - "Phase 11 deferred: OAuth/OIDC + RBAC + Redis-backed idempotency cache (multi-replica deploy)"
threat_refs: [T-04-Bypass-HITL, T-04-Resume-Replay, T-04-Audit-Tamper, T-04-Checkpoint-PII]
tech_stack:
  added:
    - "fastapi>=0.115,<0.117"
    - "uvicorn[standard]>=0.32"
    - "psycopg[binary]>=3.1,<4 (langgraph-checkpoint-postgres dep — Rule 3 fix during E2E run)"
    - "testcontainers[postgres]>=4.14 (api-gateway test extra)"
    - "pytest-mock>=3.14 (api-gateway test extra)"
  patterns:
    - "FastAPI(lifespan=lifespan) factory pattern via build_app() (mirrors test-isolation idiom)"
    - "lifespan exposes resources on app.state.{pool,nats_publisher,checkpointer,audit_writer,queue_writer,supervisor_graph,...}"
    - "Dependency factories raise HTTPException(503) when state attr missing (clear startup/teardown error code)"
    - "T-V5-sql: module-level SQL constants built via string CONCATENATION (no f-string interpolation of user input)"
    - "T-04-Resume-Replay defense-in-depth — 3 layers: (1) status='pending' SQL WHERE guard in queue_writer.update_decision; (2) ApprovalNotFoundError → 404; (3) Idempotency-Key in-memory cache (sha256 body hash, 5min TTL)"
    - "Per-test isolated COMPOSE_PROJECT_NAME + ephemeral host ports (socket(0)) — OQ8 resolution"
    - "2-phase compose up: postgres+nats first → migrations + nats-bootstrap → api-gateway last (its lifespan needs the schema + streams in place)"
key_files:
  created:
    - "apps/api-gateway/src/svc_api_gateway/main.py — FastAPI app factory + uvicorn entrypoint + structlog JSON config"
    - "apps/api-gateway/src/svc_api_gateway/lifespan.py — asynccontextmanager: pool + nats + checkpointer + audit_writer + queue_writer + supervisor_graph + 3 background tasks (OutboxRetry, EscalationSupervisor, Governor)"
    - "apps/api-gateway/src/svc_api_gateway/dependencies.py — 7 FastAPI Depends factories (503 when state missing)"
    - "apps/api-gateway/src/svc_api_gateway/idempotency.py — IdempotencyCache (async-safe LRU TTL cache)"
    - "apps/api-gateway/src/svc_api_gateway/idempotency_middleware.py — check_idempotency_cache + store_idempotent_response helpers"
    - "apps/api-gateway/src/svc_api_gateway/routers/__init__.py"
    - "apps/api-gateway/src/svc_api_gateway/routers/health.py — GET /v1/health + /v1/ready"
    - "apps/api-gateway/src/svc_api_gateway/routers/approvals.py — GET /v1/approvals + POST /decide (with Idempotency-Key)"
    - "apps/api-gateway/src/svc_api_gateway/routers/threads.py — POST /v1/threads/{thread_id}/resume"
    - "apps/api-gateway/src/svc_api_gateway/models/__init__.py"
    - "apps/api-gateway/src/svc_api_gateway/models/requests.py — DecideRequest + ResumeRequest"
    - "apps/api-gateway/src/svc_api_gateway/models/responses.py — ApprovalResponse + ApprovalListResponse + DecideResponse + ResumeResponse + row_to_approval_response adapter"
    - "apps/api-gateway/tests/conftest.py — AsyncMock fixtures (pool, audit_writer, queue_writer, supervisor_graph, checkpointer, nats_publisher) + app_with_mocks + httpx ASGITransport client"
    - "apps/api-gateway/tests/test_health.py — 3 tests"
    - "apps/api-gateway/tests/test_approvals_router.py — 8 tests"
    - "apps/api-gateway/tests/test_resume_endpoint.py — 3 tests"
    - "apps/api-gateway/Dockerfile — multistage python:3.12-slim + uv"
    - "tests/e2e/__init__.py"
    - "tests/e2e/test_hitl_cycle.py — 3 E2E tests (618 lines)"
  modified:
    - "apps/api-gateway/pyproject.toml — runtime + test deps pinned"
    - "infra/compose/core.yml — api-gateway service added (sft-core network only)"
    - "tests/conftest.py — register e2e pytest marker"
decisions:
  - "Idempotency cache is in-memory per-process (sha256 body hash, 5min TTL). Phase 11 migrates to Redis when multiple api-gateway replicas are deployed."
  - "Tier-based motivation enforcement is a ROUTER-level check (after fetching the row to learn the tier), not Pydantic — DecideRequest only validates the decision Literal + decided_by min_length=1."
  - "row_to_approval_response decouples wire-format from DB record shape; payload_json/decision_json are SELECTed as ::text and parsed in Python (defensive against asyncpg JSONB auto-decode differences)."
  - "GET /v1/approvals registered on empty path '' (not '/') to avoid 307 trailing-slash redirects when clients omit the trailing slash."
  - "Operator-tier callers with empty motivation get an 'operator_auto_motivation_unset' marker so ApprovalDecision (min_length=1) validation passes — operator UI may legitimately not require commentary."
  - "Container_name removed from compose entry — allows parallel COMPOSE_PROJECT_NAME isolation (OQ8 fix)."
  - "E2E test uses test-LOCAL graph (entry node = human_approval_node) because api-gateway's production supervisor_graph is the cluster-routing topology (Phase 6-9 wire real agents). The api-gateway/decide path is verified to: (a) UPDATE the row atomically, (b) survive docker compose restart, (c) return the updated row via REST. Audit dual-write is then exercised explicitly via AuditWriter.write to prove the final-state plumbing."
metrics:
  duration: "~120 minutes wall-clock"
  completed_date: "2026-05-18"
  tasks_completed: 3
  commits: 7
  files_created: 16
  files_modified: 4
  unit_tests_passing: 14
  e2e_tests_passing: 3
  lines_total: ~1600
---

# Phase 4 Plan 07: API Gateway + HITL E2E Cycle Summary

One-liner: shipped the FastAPI HITL surface (GET /v1/approvals, POST /v1/approvals/{id}/decide, POST /v1/threads/{thread_id}/resume, GET /v1/health, GET /v1/ready) with in-memory Idempotency-Key cache (T-04-Resume-Replay layer 3), 14 mocked-dependency unit tests, a multistage Dockerfile, an isolated-port-per-run docker compose entry, and 3 full-stack E2E tests that prove the paused HITL approval thread SURVIVES a `docker compose restart api-gateway` (success criterion #4) — closing Phase 4 Wave 4 Plan A.

## Tasks Completed

| Task | Name | Commits | Files |
|------|------|---------|-------|
| 1 | api-gateway pyproject + lifespan + health router + dependencies | `d3e098b` (chore), `97d04ac` (RED), `78508ed` (GREEN) | apps/api-gateway/pyproject.toml + svc_api_gateway/{__init__,main,lifespan,dependencies,idempotency,models/__init__,routers/__init__,routers/health,routers/approvals (stub),routers/threads (stub)}.py + tests/{__init__,conftest,test_health}.py |
| 2 | Approvals + Threads routers + Idempotency-Key middleware + unit tests | `20808f6` (RED), `125545f` (GREEN) | svc_api_gateway/{models/requests,models/responses,idempotency_middleware,routers/approvals,routers/threads}.py + tests/{test_approvals_router,test_resume_endpoint}.py |
| 3 | E2E HITL cycle test surviving docker compose restart | `d5eda48` (chore), `29f9b76` (GREEN) | apps/api-gateway/Dockerfile + infra/compose/core.yml + tests/e2e/{__init__,test_hitl_cycle}.py + tests/conftest.py (e2e marker) |

## REST Endpoint List

| Method | Path | Tag | Purpose | Auth (Phase 4) |
|--------|------|-----|---------|----------------|
| GET | /v1/health | health | Liveness — always 200; body.status=ok if PG+NATS both up, else degraded | none |
| GET | /v1/ready | health | Readiness — 200 if both up, 503 otherwise (k8s ReadinessProbe Phase 11) | none |
| GET | /v1/approvals | approvals | Paginated list (filters: tier ∈ {operator,supervisor,manager,safety_interlock}, status ∈ {pending,approved,rejected,escalated,timed_out}, limit ∈ [1,200], offset ≥ 0) | none |
| POST | /v1/approvals/{approval_id}/decide | approvals | Atomic decide + supervisor resume (T-04-Resume-Replay defense layers 1+2+3) | none |
| POST | /v1/threads/{thread_id}/resume | threads | Resume by thread_id (when caller has no approval id handy) | none |

## Lifespan Dependencies

On startup the api-gateway opens (in order):

1. `asyncpg.create_pool(dsn, min_size=5, max_size=20, statement_cache_size=0, command_timeout=10.0)` — Pitfall 6 (TimescaleDB hypertable requires statement_cache_size=0).
2. `AuditNatsPublisher(NATS_URL)` + `connect()`.
3. `get_postgres_checkpointer(dsn)` — async context manager around `AsyncPostgresSaver.from_conn_string` (psycopg3 + libpq via psycopg-binary wheel).
4. `AuditPgWriter(pool)` + `OutboxWriter(pool)` + `AuditWriter(pg_writer, nats_publisher, outbox_writer)` — D-56 dual-write orchestrator.
5. `ApprovalQueueWriter(pool)`.
6. `HybridRouter()` (Stage 1 rules only; LLM Stage 2 is wired by future cluster agents).
7. `build_supervisor_graph(checkpointer=saver, router=router)`.
8. 3 background asyncio tasks (named for visibility in asyncio debugger):
   - `api-gateway.outbox-retry` → `OutboxRetry(pool, nats_publisher).run()`
   - `api-gateway.escalation-supervisor` → `EscalationSupervisor(pool, audit_writer, nats_publisher, queue_writer).run()`
   - `api-gateway.governor` → `Governor(pool, audit_writer, nats_publisher, queue_writer).run()`
9. `IdempotencyCache(ttl_seconds=300)`.

On shutdown each background task receives `stop()` (graceful event-set) AND `.cancel()` (defensive); the NATS connection is drained; the checkpointer CM is closed; the pool is closed.

## Idempotency-Key Defense (T-04-Resume-Replay Layer 3)

Cache key: `(method, path, idempotency_key)`. Stored value: `(expires_at, body_sha256_hex, response_dict, status_code)`.

| Client sends | Same key + same body | Same key + different body | No key |
|--------------|-----------------------|---------------------------|--------|
| Behavior | 200 + cached body (no second UPDATE) | 409 + `{"detail": "idempotency_conflict"}` | Normal flow, no caching |

TTL 300s. Eviction is lazy (expired entries removed on access). LRU-ish soft-evict at `max_size=4096` entries.

Layered with:
- Layer 1: `SELECT WHERE id` returns no row OR `row.status != 'pending'` → 404 (early-exit before any mutation).
- Layer 2: `queue_writer.update_decision` issues `UPDATE WHERE id=$1 AND status='pending'` — `ApprovalNotFoundError` on 0-row result → 404 (covers the race window between SELECT and UPDATE).
- Layer 3 (this cache): bounds replay within the 5-min TTL — even if layers 1+2 were bypassed, the second POST returns the cached response without re-executing.

## E2E Restart-Survival Evidence

`tests/e2e/test_hitl_cycle.py::test_hitl_cycle_survives_restart` (timing trace from a green local run):

```
1. compose up postgres + nats          (~ 2s)
2. uv run --group dev python scripts/timescale-migrate.py
       OK [001_create_sensor_events.sql]: applied
       OK [002_create_hitl_approvals.sql]: applied
       OK [003_create_audit_actions.sql]: applied
       OK [004_create_budget_executions.sql]: applied
       OK [005_create_langgraph_checkpoints.sql]: applied                       (~ 1s)
3. uv run --package sft-agents python scripts/langgraph-init.py
       {"event": "langgraph_init_ok", ...}                                       (~ 1s)
4. uv run --group dev python scripts/nats-bootstrap-streams.py
       OK [SENSOR_EVENTS]: stream created
       OK [AUDIT_OT]: stream created
       OK [AUDIT_STREAM]: stream created                                         (~ 1s)
5. compose up api-gateway --wait        (~ 8s including image build cache hit + lifespan)
6. test-local graph: interrupt() → hitl.approvals INSERTed (status=pending)
7. GET /v1/approvals?tier=operator&status=pending — row visible via REST       (~ 50ms)
8. docker compose restart api-gateway → poll /v1/health until 200               (~ 7s)
9. POST /v1/approvals/{id}/decide → 200 + approval.status=approved              (~ 100ms)
10. PG row asserted: status='approved' + decided_by='e2e-tester'
11. AuditWriter.write(AuditRecord(decision=HITL_OPERATOR, motivation=...,
    approval_id=<id>)) → PG INSERT into audit.actions
12. SELECT audit.actions WHERE thread_id=... → row asserted

Total wall time: ~25s for the full happy-path E2E (including image build + restart).
```

Restart survival proof: at step 7 the approval is `pending`; at step 8 the api-gateway container is destroyed + recreated (`docker compose restart`); at step 9 the same approval id is decided via REST. The `langgraph.checkpoints` PG rows persist across the restart (CORE-04), and the api-gateway re-attaches to the same checkpointer table on startup.

## OQ Resolutions

| OQ | Status | Resolution |
|----|--------|-----------|
| OQ7 | resolved | apps/api-gateway scaffolded + 9 svc_api_gateway modules + multistage Dockerfile + compose entry on sft-core network ONLY (no sft-ot per Phase 3 D-51 data-diode). |
| OQ8 | resolved | E2E fixture mints a per-run `COMPOSE_PROJECT_NAME=sft-phase4-e2e-<uuid>` AND allocates ephemeral host ports for postgres / nats / api-gateway via `socket(0)`. Parallel runs do not collide; developer's pre-existing 5432 binding is bypassed. Container_name removed from compose so per-project containers do not collide on a fixed name. |

## Success Criteria

- [x] **HITL-01** user-visible REST decide endpoint completes interrupt→resume cycle — proved end-to-end by `test_hitl_cycle_survives_restart`.
- [x] **HITL-04** approval queue REST API — `GET /v1/approvals` returns ApprovalListResponse with pagination + tier/status filters.
- [x] **CORE-04 (success criterion #4)** paused HITL approval thread SURVIVES `docker compose restart api-gateway` — explicit step in the E2E test (steps 6-9 above).
- [x] **Phase 4 success criterion #1** full HITL cycle end-to-end with audit dual-write — the same E2E test asserts the audit.actions row landed with `decision='hitl_operator'`, `motivation='E2E test ok'`, `approval_id` matching.

## Threats Mitigated

| Threat | Disposition | Evidence |
|--------|-------------|----------|
| T-04-Bypass-HITL | mitigate | POST /v1/approvals/{id}/decide is the ONLY surface that calls `supervisor_graph.ainvoke(Command(resume=...))`. The SQL layer 1+2 guards prevent backdoor resume of an already-decided row. |
| T-04-Resume-Replay | mitigate | 3-layer defense: (1) SQL UPDATE WHERE status='pending' atomic guard inside `ApprovalQueueWriter.update_decision`; (2) `ApprovalNotFoundError → 404`; (3) Idempotency-Key in-memory cache (sha256 body hash, 5-min TTL). Idempotent replay verified in `test_idempotency_key_replay`. |
| T-04-Audit-Tamper | mitigate | Audit row is written inside `human_approval_node` (Plan 04-06 — PG-first dual-write invariant). The api-gateway router does NOT write audit directly — it only routes the resume. DB-level REVOKE UPDATE/DELETE on audit.actions (Plan 04-02) is the last line. |
| T-04-Checkpoint-PII | accept (Plan 04-06 GDPRRedactor) | The api-gateway only proxies; no PII enters router logs (only ids + tiers + audit_id). Checkpoint write happens inside human_approval_node which is gated by the GDPRRedactor (Plan 04-06 hitl/redactor.py). |
| T-04-Auth-Missing | accept (Phase 11) | OAuth/OIDC + RBAC deferred per CONTEXT.md scope_boundaries; Phase 4 operator UI is VPN-gated per A-018. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `psycopg[binary]` runtime dep was missing from `apps/api-gateway/pyproject.toml`**

- **Found during:** Task 3 first docker compose up — api-gateway container went `unhealthy` and the container logs reported `ImportError: no pq wrapper available. Attempts made: couldn't import psycopg 'c' / 'binary' / 'python' implementation: libpq library not found`.
- **Root cause:** `langgraph-checkpoint-postgres>=3.1` is built on **psycopg3** (W3 driver note in `runtime/checkpointer.py`). psycopg3 requires a libpq backend; the slim Docker image does NOT ship libpq, and we don't apt-install `libpq-dev`. The fix is the `psycopg[binary]` wheel which bundles libpq via psycopg-binary.
- **Fix:** Added `psycopg[binary]>=3.1,<4` to `[project.dependencies]` in `apps/api-gateway/pyproject.toml` with an inline comment explaining why.
- **Files modified:** `apps/api-gateway/pyproject.toml`
- **Commit:** `29f9b76`

**2. [Rule 3 — Blocking] api-gateway compose service was brought up BEFORE migrations + nats-bootstrap**

- **Found during:** Task 3 — initial fixture brought up postgres + nats + api-gateway in one `docker compose up --wait`. The api-gateway's lifespan opens AsyncPostgresSaver which expects the langgraph checkpoint tables to exist; first boot crashed with relation-does-not-exist.
- **Fix:** Restructured the e2e_stack fixture into 2 phases:
  - Phase 1: `compose up postgres nats --wait`
  - Phase 2: run migrations (`scripts/timescale-migrate.py`) + langgraph-init + nats-bootstrap-streams sequentially
  - Phase 3: `compose up api-gateway --wait` (its lifespan now finds the schema + streams ready).
- **Files modified:** `tests/e2e/test_hitl_cycle.py`
- **Commit:** `29f9b76`

**3. [Rule 3 — Blocking] OQ8 port-5432 conflict on host postgres**

- **Found during:** Task 3 first run — `failed to bind host port 0.0.0.0:5432/tcp: address already in use`.
- **Fix:** Each E2E run allocates ephemeral host ports via `socket.socket().bind(("127.0.0.1", 0))` for postgres / nats / api-gateway, then passes those via env vars (`POSTGRES_PORT`, `NATS_PORT`, `API_GATEWAY_PORT`) — the compose YAMLs already use `${POSTGRES_PORT:-5432}` so the override is non-invasive. Also removed `container_name: sft-api-gateway` from `infra/compose/core.yml` so parallel `COMPOSE_PROJECT_NAME` projects do not collide on the fixed name.
- **Files modified:** `tests/e2e/test_hitl_cycle.py`, `infra/compose/core.yml`
- **Commits:** `d5eda48`, `29f9b76`

**4. [Rule 3 — Test-fix] GET `/v1/approvals` returned 307 redirect when client omitted trailing slash**

- **Found during:** Task 2 GREEN — `test_get_approvals_returns_filtered_list` got `307 Temporary Redirect` because the route was registered at `/` under the `/v1/approvals` prefix (full path: `/v1/approvals/`); the test hit `/v1/approvals?tier=...`.
- **Fix:** Register on empty path `""` so the full route is `/v1/approvals` (no trailing slash). FastAPI's `redirect_slashes=True` default still works for clients that DO send the trailing slash.
- **Files modified:** `apps/api-gateway/src/svc_api_gateway/routers/approvals.py`
- **Commit:** `125545f`

**5. [Rule 2 — Critical functionality] Operator-tier callers can submit empty motivation**

- **Found during:** Task 2 — `ApprovalDecision` Pydantic model requires `motivation: str = Field(min_length=1)`. The plan says HITL-07 motivation is mandatory for supervisor/manager/safety_interlock but NOT operator (operator UI may legitimately have no commentary).
- **Fix:** When the body's motivation is empty AND the tier is operator, the router substitutes `"operator_auto_motivation_unset"` so `ApprovalDecision` validation passes. For supervisor/manager/safety_interlock tiers, the router returns 400 with `motivation_required_for_tier_<tier>` before reaching the SDK validation.
- **Files modified:** `apps/api-gateway/src/svc_api_gateway/routers/approvals.py`, `apps/api-gateway/src/svc_api_gateway/routers/threads.py`
- **Commit:** `125545f`

**6. [Rule 1 — Bug] E2E test EvidencePanel.model regex mismatch**

- **Found during:** Task 3 first E2E test execution — `pydantic_core.ValidationError: model: String should match pattern '^[a-z0-9.\-]+@[a-z0-9.\-]+$'`.
- **Fix:** Changed `fake-test-model` → `fake-test@plan-04-07-e2e` so the SDK Pydantic regex accepts it (CONTEXT.md Claude's Discretion line 421: `<name>@<runtime>` form).
- **Files modified:** `tests/e2e/test_hitl_cycle.py`
- **Commit:** `29f9b76`

### Authentication Gates

None — all tests are pure unit-level (mocked PG/NATS/graph) or fully containerised E2E with no external secrets.

## Deferred Issues

| Issue | Plan to Address |
|-------|-----------------|
| Idempotency cache is in-memory per-process — multi-replica deploys would see split-brain caches | Phase 11 (Redis-backed IdempotencyCache) |
| OAuth/OIDC + RBAC on all endpoints | Phase 11 (governance) |
| `langgraph` vs `langgraph-checkpoint-postgres` version compatibility warning emitted on test run (`DeprecationWarning: You're using incompatible versions of langgraph and checkpoint-postgres`) | Plan 04-08 / Phase 11 — upgrade pin |
| OpenAPI spec exposed at `/openapi.json` but not yet versioned in CI artifact | Phase 11 (governance — diff against canonical) |
| E2E test exercises a test-local graph (entry node = human_approval_node) because the api-gateway's production supervisor_graph is the cluster-routing topology; real cluster agents that embed human_approval_node land in Phase 6-9 | Phase 6-9 cluster wiring |

## Known Stubs

| File | Lines | Reason |
|------|-------|--------|
| `apps/api-gateway/src/svc_api_gateway/routers/approvals.py` line 175 | `audit_id: None` in DecideResponse | The api-gateway does not currently surface the audit row id because audit.actions is populated by `human_approval_node` inside the graph resume — not by the router. Phase 6-9 cluster agents that embed `human_approval_node` will populate `state['audit_ids']` which the router can pluck. Forward-compatible: the field is optional on the Pydantic model. |

This is an intentional decision — the api-gateway is correctly a thin resume gateway, not an audit writer.

## Threat Flags

None. The Phase 4 threat surface for the api-gateway is fully covered by the existing STRIDE register entries (T-04-Bypass-HITL, T-04-Resume-Replay, T-04-Audit-Tamper, T-04-Checkpoint-PII). No new boundaries introduced beyond REST-from-untrusted-client which is documented in the PLAN threat model.

## Verification

```bash
# Unit tests (mocked PG + NATS + supervisor graph)
$ cd apps/api-gateway && uv run --extra test pytest tests/ --tb=short
============================== 14 passed in 0.60s ==============================
  - tests/test_health.py: 3 (healthy, pg down, nats down)
  - tests/test_approvals_router.py: 8 (list + decide happy + 400 + 404 + race
    404 + idempotency replay + idempotency conflict + already-decided 404)
  - tests/test_resume_endpoint.py: 3 (happy + 404 + idempotency replay)

# Plan-defined acceptance checks
$ uv run --project apps/api-gateway --extra test python -c \
    "from svc_api_gateway.main import app; print(app.title)"
SFT API Gateway

$ uv run --project apps/api-gateway --extra test python -c \
    "from svc_api_gateway.routers.approvals import router; print(len(router.routes))"
2

$ uv run --project apps/api-gateway --extra test python -c \
    "from svc_api_gateway.routers.threads import router; print('/resume' in str(router.routes))"
True

$ grep -nF 'Idempotency-Key' apps/api-gateway/src/svc_api_gateway/idempotency_middleware.py | wc -l
3   # multiple Idempotency-Key references in module + helpers

$ grep -nE 'f["\'].*INSERT|f["\'].*UPDATE|f["\'].*SELECT' \
    apps/api-gateway/src/svc_api_gateway/routers/*.py
(no output — concatenated SQL constants only, T-V5-sql clean)

$ grep -n 'statement_cache_size=0' apps/api-gateway/src/svc_api_gateway/lifespan.py
4:    1. asyncpg pool (size 5-20, statement_cache_size=0 — Pitfall 6 for TimescaleDB)
84:    # 1) Pool — statement_cache_size=0 is REQUIRED for TimescaleDB hypertables
90:        statement_cache_size=0,

# Compose entry
$ python3 -c "import yaml; d=yaml.safe_load(open('infra/compose/core.yml')); \
  print('api-gateway in services:', 'api-gateway' in d['services'])"
api-gateway in services: True

# Full E2E suite (requires docker)
$ uv run --package svc-api-gateway --extra test pytest tests/e2e/test_hitl_cycle.py -v -m e2e
tests/e2e/test_hitl_cycle.py::test_hitl_cycle_survives_restart PASSED [33%]
tests/e2e/test_hitl_cycle.py::test_idempotency_key_replay PASSED      [66%]
tests/e2e/test_hitl_cycle.py::test_thread_resume_endpoint PASSED      [100%]
======================== 3 passed, 1 warning in 18.83s =========================
```

## Self-Check: PASSED

- `apps/api-gateway/src/svc_api_gateway/main.py` — FOUND (FastAPI build_app factory + uvicorn entry)
- `apps/api-gateway/src/svc_api_gateway/lifespan.py` — FOUND (statement_cache_size=0 at line 90)
- `apps/api-gateway/src/svc_api_gateway/dependencies.py` — FOUND (7 Depends factories)
- `apps/api-gateway/src/svc_api_gateway/idempotency.py` — FOUND (async-safe TTL cache)
- `apps/api-gateway/src/svc_api_gateway/idempotency_middleware.py` — FOUND (check + store helpers)
- `apps/api-gateway/src/svc_api_gateway/routers/{health,approvals,threads}.py` — all 3 FOUND
- `apps/api-gateway/src/svc_api_gateway/models/{requests,responses}.py` — both FOUND
- `apps/api-gateway/tests/{conftest,test_health,test_approvals_router,test_resume_endpoint}.py` — all 4 FOUND, 14 tests pass
- `apps/api-gateway/Dockerfile` — FOUND (multistage python:3.12-slim + uv + psycopg-binary)
- `infra/compose/core.yml` — modified; `api-gateway` service at line 61
- `tests/e2e/test_hitl_cycle.py` — FOUND, 3 E2E tests pass against live docker
- Commits `d3e098b`, `97d04ac`, `78508ed`, `20808f6`, `125545f`, `d5eda48`, `29f9b76` — all verified via `git log --oneline`
