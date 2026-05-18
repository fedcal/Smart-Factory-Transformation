---
phase: 04-core-agentic-runtime-hitl
plan: 07
type: execute
wave: 4
depends_on: ["04-02", "04-03", "04-04", "04-05", "04-06"]
files_modified:
  - apps/api-gateway/pyproject.toml
  - apps/api-gateway/project.json
  - apps/api-gateway/src/svc_api_gateway/__init__.py
  - apps/api-gateway/src/svc_api_gateway/main.py
  - apps/api-gateway/src/svc_api_gateway/lifespan.py
  - apps/api-gateway/src/svc_api_gateway/dependencies.py
  - apps/api-gateway/src/svc_api_gateway/routers/__init__.py
  - apps/api-gateway/src/svc_api_gateway/routers/approvals.py
  - apps/api-gateway/src/svc_api_gateway/routers/threads.py
  - apps/api-gateway/src/svc_api_gateway/routers/health.py
  - apps/api-gateway/src/svc_api_gateway/models/__init__.py
  - apps/api-gateway/src/svc_api_gateway/models/requests.py
  - apps/api-gateway/src/svc_api_gateway/models/responses.py
  - apps/api-gateway/tests/__init__.py
  - apps/api-gateway/tests/conftest.py
  - apps/api-gateway/tests/test_health.py
  - apps/api-gateway/tests/test_approvals_router.py
  - apps/api-gateway/tests/test_resume_endpoint.py
  - tests/e2e/__init__.py
  - tests/e2e/test_hitl_cycle.py
autonomous: true
requirements: [HITL-01, HITL-04, CORE-04]
threat_refs: [T-04-Bypass-HITL, T-04-Resume-Replay, T-04-Audit-Tamper, T-04-Checkpoint-PII]

must_haves:
  truths:
    - "FastAPI app boots via `uvicorn svc_api_gateway.main:app` with lifespan that opens asyncpg pool, NATS connection, AsyncPostgresSaver, builds supervisor graph, and starts EscalationSupervisor + Governor + OutboxRetry background tasks"
    - "GET /v1/health returns 200 with body {status:'ok', dependencies:{pg:'up', nats:'up'}}"
    - "GET /v1/approvals?tier=<t>&status=pending&limit=50 returns paginated list from hitl.approvals (D-55)"
    - "POST /v1/approvals/{id}/decide accepts body {decision, motivation, decided_by}; rejects motivation='' when decision in {approve,reject} for non-operator tier; calls supervisor graph resume via Command(resume=ApprovalDecision); returns 200 with updated row; returns 404 when id missing/already decided (T-04-Resume-Replay)"
    - "POST /v1/threads/{thread_id}/resume accepts body {approval_id, decision} → builds Command(resume=) → graph.ainvoke continues from checkpoint"
    - "E2E test_hitl_cycle.py invokes graph with HITL action → pause → POST /v1/approvals/{id}/decide → resume → audit row in PG; survives `docker compose restart api-gateway` mid-cycle (success criterion #4)"
    - "Idempotency-Key header on POST /v1/approvals/{id}/decide cached per-id; replay returns same response (T-04-Resume-Replay second defense layer)"
  artifacts:
    - path: apps/api-gateway/src/svc_api_gateway/main.py
      provides: "FastAPI app + lifespan + router registration"
      contains: "FastAPI(lifespan=lifespan)"
    - path: apps/api-gateway/src/svc_api_gateway/lifespan.py
      provides: "asynccontextmanager lifespan: opens pool, nats, checkpointer, supervisor graph, background tasks"
      contains: "asynccontextmanager"
    - path: apps/api-gateway/src/svc_api_gateway/routers/approvals.py
      provides: "GET /v1/approvals + POST /v1/approvals/{id}/decide"
      contains: "router.post"
    - path: apps/api-gateway/src/svc_api_gateway/routers/threads.py
      provides: "POST /v1/threads/{thread_id}/resume"
      contains: "/resume"
    - path: tests/e2e/test_hitl_cycle.py
      provides: "E2E HITL cycle survives docker compose restart"
      contains: "docker compose restart"
  key_links:
    - from: apps/api-gateway/src/svc_api_gateway/routers/threads.py
      to: packages/sft-agents/src/sft_agents/runtime/supervisor.py
      via: "build_supervisor_graph + safe_invoke (Plan 04-05)"
      pattern: "build_supervisor_graph|safe_invoke"
    - from: apps/api-gateway/src/svc_api_gateway/lifespan.py
      to: packages/sft-agents/src/sft_agents/runtime/escalation.py + governor.py + audit/outbox.py
      via: "asyncio.create_task on startup; cancel on shutdown"
      pattern: "EscalationSupervisor|Governor|OutboxRetry"
---

<objective>
Wave 4 Plan A: scaffold `apps/api-gateway/` FastAPI app and ship the full E2E HITL cycle test. This plan binds together the SDK (Plan 04-01), schema (Plan 04-02), LLM (Plan 04-03), NATS (Plan 04-04), supervisor graph (Plan 04-05), and HITL middleware (Plan 04-06) behind REST endpoints, and proves the end-to-end "agent proposes → interrupt → human decides → resume → audit" cycle works AND survives a full service restart (success criterion #4).

Purpose: deliver HITL-01 user-visible surface (REST decide endpoint), HITL-04 approval queue REST API, CORE-04 final (paused HITL approval thread survives docker compose restart per success criterion #4). Resolves OQ7 (api-gateway scaffold) and OQ8 (testcontainers adoption — fix Phase 3 port-5432 issue as bonus).

Output: 9 svc_api_gateway modules + 4 router unit tests + 1 E2E integration test (docker compose restart) + Idempotency-Key middleware. No OAuth/OIDC (deferred Phase 11 per CONTEXT.md scope_boundaries).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md
@.planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md
@.planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md
@.planning/phases/04-core-agentic-runtime-hitl/04-VALIDATION.md
@services/ot-bridge/pyproject.toml
@services/ot-bridge/src/svc_ot_bridge/main.py
@packages/sft-tools/src/sft_tools/timescale/query.py
@tests/conftest.py
@tests/integration/test_e2e_sim_to_timescale.py
@apps/api-gateway/pyproject.toml

<interfaces>
REST contract (D-55 + CONTEXT.md Claude's Discretion):

GET /v1/health → 200 {"status": "ok", "dependencies": {"pg": "up"|"down", "nats": "up"|"down"}}

GET /v1/approvals?tier={operator|supervisor|manager|safety_interlock}&status={pending|approved|rejected|escalated|timed_out}&limit={1..200}&offset={0..} → 200
  Response: {"items": [ApprovalResponse, ...], "total": int, "limit": int, "offset": int}
  Auth: NONE (Phase 11 adds JWT/RBAC)

POST /v1/approvals/{id}/decide
  Body: {"decision": "approve"|"reject"|"escalate", "motivation": str (required if decision in {approve,reject} for non-operator tier), "decided_by": str (user id)}
  Header: Idempotency-Key: str (recommended; cached 5min per id+key)
  → 200 {"approval": ApprovalResponse, "audit_id": UUID, "resumed": bool}
  → 404 if id not found OR status != 'pending' (T-04-Resume-Replay)
  → 400 if motivation missing/empty when required
  → 409 if Idempotency-Key conflicts with prior different-body submission

POST /v1/threads/{thread_id}/resume
  Body: {"approval_id": UUID, "decision": "approve"|"reject"|"escalate", "motivation": str, "decided_by": str}
  Header: Idempotency-Key: str
  → 200 {"thread_id": str, "state_after": dict (state delta), "audit_ids": list[UUID], "completed": bool}
  → 404 if thread checkpoint not found
  → 409 idempotency conflict

ApprovalResponse Pydantic shape:
  id, agent_id, thread_id, tier, action_type, payload, status, created_at, sla_deadline, decided_at, decided_by, decision, motivation, escalated_to_id

Lifespan dependencies (created on startup, torn down on shutdown):
  - asyncpg.Pool (size 5-20, statement_cache_size=0)
  - NATS connection + AuditNatsPublisher + jetstream
  - AsyncPostgresSaver (from sft_agents.runtime.checkpointer)
  - HybridRouter
  - Compiled supervisor graph (build_supervisor_graph)
  - EscalationSupervisor task (asyncio.create_task)
  - Governor task
  - OutboxRetry task
  - ApprovalQueueWriter
  - AuditWriter

OpenAPI: auto-generated by FastAPI; tags=["health", "approvals", "threads"]; spec exposed at /openapi.json
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <id>04-07-01</id>
  <name>Task 1: api-gateway pyproject + lifespan + health router + dependencies</name>
  <files>apps/api-gateway/pyproject.toml, apps/api-gateway/project.json, apps/api-gateway/src/svc_api_gateway/__init__.py, apps/api-gateway/src/svc_api_gateway/main.py, apps/api-gateway/src/svc_api_gateway/lifespan.py, apps/api-gateway/src/svc_api_gateway/dependencies.py, apps/api-gateway/src/svc_api_gateway/routers/__init__.py, apps/api-gateway/src/svc_api_gateway/routers/health.py, apps/api-gateway/tests/__init__.py, apps/api-gateway/tests/conftest.py, apps/api-gateway/tests/test_health.py</files>
  <read_first>
    services/ot-bridge/pyproject.toml (hatchling + uv.sources workspace + asyncio_mode auto layout — replicate)
    services/ot-bridge/src/svc_ot_bridge/main.py (lifespan-style startup at lines 30-200; structlog wiring 30-40)
    apps/api-gateway/pyproject.toml (current empty scaffold — extend)
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (Claude's Discretion api-gateway endpoint structure lines 423-424)
    .planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md (§3.13 — FastAPI patterns since no in-repo analog)
  </read_first>
  <behavior>
    - `uv sync` in apps/api-gateway succeeds (workspace deps resolve to local sft-agents)
    - `uvicorn svc_api_gateway.main:app --port 8081` starts the app (lifespan opens dependencies)
    - GET /v1/health returns 200 with body `{"status":"ok","dependencies":{"pg":"up","nats":"up"}}` when both deps reachable; "down" otherwise
    - Lifespan correctly tears down background tasks on shutdown (no zombie asyncio tasks)
    - Dependencies module exposes `get_pool()`, `get_audit_writer()`, `get_supervisor_graph()`, `get_queue_writer()` via FastAPI Depends
  </behavior>
  <action>
    Update `apps/api-gateway/pyproject.toml`:
    - `[project] name = "svc-api-gateway"` (already set), add deps: `fastapi>=0.115,<0.117`, `uvicorn[standard]>=0.32`, `langchain-core>=0.3,<0.4`, `asyncpg>=0.30,<0.31`, `nats-py>=2.7,<2.10`, `pydantic>=2.9,<3`, `structlog>=24.4`, `httpx>=0.28` (for embedded test client), `sft-agents` (workspace).
    - `[project.optional-dependencies] test = ["pytest>=8", "pytest-asyncio>=0.24", "pytest-mock>=3.12", "testcontainers[postgres]>=4.8"]`.
    - `[tool.uv.sources] sft-agents = { workspace = true }`.
    - `[tool.pytest.ini_options] asyncio_mode = "auto"`, `markers = ["integration: requires PG+NATS", "e2e: full stack via docker compose"]`.
    Update `apps/api-gateway/project.json` to add nx `test` target (replicate from sft-agents/project.json updated in Plan 04-01).
    Create `src/svc_api_gateway/__init__.py` exporting `__version__ = "0.1.0"`.
    Create `src/svc_api_gateway/dependencies.py`: FastAPI Depends factories that return objects set on `app.state` during lifespan startup (`request.app.state.pool`, `.audit_writer`, `.queue_writer`, `.supervisor_graph`, `.checkpointer`). Each factory raises HTTPException(503) if state not initialized.
    Create `src/svc_api_gateway/lifespan.py`:
    ```
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # startup
        dsn = os.environ["TIMESCALE_DSN"]
        nats_url = os.environ.get("NATS_URL", "nats://localhost:4222")
        pool = await asyncpg.create_pool(dsn, min_size=5, max_size=20, statement_cache_size=0, command_timeout=10.0)
        nats_publisher = AuditNatsPublisher(nats_url); await nats_publisher.connect()
        async with get_postgres_checkpointer(dsn) as saver:
            app.state.pool = pool
            app.state.nats_publisher = nats_publisher
            app.state.checkpointer = saver
            pg_writer = AuditPgWriter(pool)
            outbox_writer = OutboxWriter(pool)
            app.state.audit_writer = AuditWriter(pg_writer, nats_publisher, outbox_writer)
            app.state.queue_writer = ApprovalQueueWriter(pool)
            app.state.router = HybridRouter()
            app.state.supervisor_graph = build_supervisor_graph(checkpointer=saver, router=app.state.router)
            outbox_retry = OutboxRetry(pool, nats_publisher); app.state.outbox_retry_task = asyncio.create_task(outbox_retry.run())
            escalator = EscalationSupervisor(pool=pool, audit_writer=app.state.audit_writer, nats_publisher=nats_publisher, queue_writer=app.state.queue_writer); app.state.escalator_task = asyncio.create_task(escalator.run())
            governor = Governor(pool=pool, audit_writer=app.state.audit_writer, nats_publisher=nats_publisher, queue_writer=app.state.queue_writer); app.state.governor_task = asyncio.create_task(governor.run())
            yield
            # shutdown: cancel tasks + drain NATS + close pool
            for task in (app.state.outbox_retry_task, app.state.escalator_task, app.state.governor_task):
                task.cancel()
                try: await task
                except asyncio.CancelledError: pass
            await nats_publisher.drain()
            await pool.close()
    ```
    Create `src/svc_api_gateway/main.py`: `app = FastAPI(title="SFT API Gateway", version="0.1.0", lifespan=lifespan)`; configure structlog at module-load per ot-bridge/main.py:30-40; include routers from `.routers` (health, approvals, threads — wired progressively across the 3 tasks); `if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=8081)`.
    Create `routers/health.py`: `router = APIRouter(prefix="/v1", tags=["health"])`. `@router.get("/health")` checks pool via `await conn.execute("SELECT 1")` and NATS via `nats_publisher._nc.is_connected` (or jetstream account_info()); returns shaped response. Failure of any dependency → 200 with `dependencies.pg="down"` etc. (do NOT return 503 — Phase 11 readiness probe; for now liveness only). Add `@router.get("/ready")` returning 200 only if both deps up (used by k8s readiness later).
    Create `tests/conftest.py` with fixtures: `app_with_mocks` returns FastAPI app whose lifespan is replaced with a mock-injecting one (manually set app.state attrs to AsyncMocks for unit tests); `client` returns httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test"). For integration tests, `app_with_real_pg` uses testcontainers PG + NATS — share fixture infrastructure with packages/sft-agents/tests/conftest.py via root tests/conftest.py.
    `tests/test_health.py`: 3 tests — health endpoint returns 200; pg down (mock pool.execute raises) → dependencies.pg='down'; nats down → dependencies.nats='down'.

    Conventional commits: (1) `chore(04-07-api-gateway-e2e-01): pin api-gateway pyproject deps + nx test target`, (2) `feat(04-07-api-gateway-e2e-01): fastapi lifespan + dependencies + health router`, (3) `test(04-07-api-gateway-e2e-01): health endpoint unit tests (mocked deps)`.
  </action>
  <pattern_ref>services/ot-bridge/pyproject.toml:1-44 (hatchling + uv.sources workspace + asyncio_mode auto layout) ; services/ot-bridge/src/svc_ot_bridge/main.py:30-40 (structlog config) ; services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:82-91 (asyncpg pool create with statement_cache_size=0)</pattern_ref>
  <threat_ref>—</threat_ref>
  <acceptance_criteria>
    - `python -c "from svc_api_gateway.main import app; print(app.title)"` outputs `SFT API Gateway`
    - `python -c "import tomllib; d=tomllib.loads(open('apps/api-gateway/pyproject.toml').read()); deps=d['project']['dependencies']; assert any('fastapi>=0.115' in s for s in deps); assert any('sft-agents' in s for s in deps); print('ok')"` exits 0
    - `grep -nE 'statement_cache_size=0' apps/api-gateway/src/svc_api_gateway/lifespan.py` returns 1 match
    - `nx test api-gateway --testNamePattern=test_health` exits 0 (3 tests pass)
  </acceptance_criteria>
  <verify>
    <automated>nx test api-gateway --testNamePattern=test_health</automated>
  </verify>
  <done>api-gateway boots; health endpoint live; lifespan creates pool/NATS/checkpointer/supervisor graph + 3 background tasks; pyproject pinned with workspace sft-agents.</done>
  <commit_scope>feat(04-07-api-gateway-e2e)</commit_scope>
</task>

<task type="auto" tdd="true">
  <id>04-07-02</id>
  <name>Task 2: Approvals + Threads routers + Idempotency-Key middleware + unit tests</name>
  <files>apps/api-gateway/src/svc_api_gateway/routers/approvals.py, apps/api-gateway/src/svc_api_gateway/routers/threads.py, apps/api-gateway/src/svc_api_gateway/models/__init__.py, apps/api-gateway/src/svc_api_gateway/models/requests.py, apps/api-gateway/src/svc_api_gateway/models/responses.py, apps/api-gateway/tests/test_approvals_router.py, apps/api-gateway/tests/test_resume_endpoint.py</files>
  <read_first>
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-55 endpoint structure lines 127-128; D-56 audit dual-write)
    .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md (§8 api-gateway endpoint structure; §6 Command(resume=) full HITL cycle pattern)
    packages/sft-agents/src/sft_agents/hitl/approval_queue.py (Plan 04-06 — ApprovalQueueWriter + ApprovalNotFoundError)
    packages/sft-agents/src/sft_agents/hitl/interrupt.py (Plan 04-06 — human_approval_node + Command resume value shape)
    packages/sft-agents/src/sft_agents/models/approval.py (Plan 04-01 — ApprovalRequest + ApprovalDecision)
    packages/sft-agents/src/sft_agents/runtime/supervisor.py (Plan 04-05 — safe_invoke)
  </read_first>
  <behavior>
    - GET /v1/approvals with tier/status/limit/offset returns paginated list from PG via parameterized SQL
    - POST /v1/approvals/{id}/decide: validates body via Pydantic (motivation required for hitl_supervisor and hitl_manager tiers per HITL-07); calls queue_writer.update_decision; on success builds Command(resume=ApprovalDecision); calls safe_invoke(graph, state_from_checkpoint, config); writes audit; returns 200 with approval+audit_id+resumed=True
    - On ApprovalNotFoundError → 404 (T-04-Resume-Replay defense layer 1)
    - On thread checkpoint not found → 404
    - Idempotency-Key middleware: cache 5min per (method, path, key) with stored response body; same key + identical body → return cached response; same key + different body → 409 (T-04-Resume-Replay defense layer 2)
    - POST /v1/threads/{thread_id}/resume: lookup checkpoint via app.state.checkpointer; if not found → 404; else call safe_invoke with Command(resume=ApprovalDecision); return state delta + audit_ids
    - All responses Pydantic-shaped; OpenAPI generates correctly
  </behavior>
  <action>
    `models/requests.py`: Pydantic `DecideRequest(decision: Literal["approve","reject","escalate"], motivation: str = "", decided_by: str (min_length=1))` with `@model_validator(mode="after")` requiring motivation when decision in {approve,reject} for non-operator tiers (validated against tier from URL → done in router after fetching the approval row; Pydantic-level check only does basic non-empty for hitl_supervisor/manager). `ResumeRequest(approval_id: UUID, decision: Literal[...], motivation: str = "", decided_by: str)`.
    `models/responses.py`: `ApprovalResponse` (mirrors hitl.approvals row shape — same fields as sft_agents.models.ApprovalRequest, exported as separate Pydantic frozen response model to decouple wire-format from DB-record). `DecideResponse(approval: ApprovalResponse, audit_id: UUID, resumed: bool)`. `ResumeResponse(thread_id: str, state_after: dict, audit_ids: list[UUID], completed: bool)`. `HealthResponse(status: Literal["ok","degraded"], dependencies: dict[str, Literal["up","down"]])`.
    `routers/approvals.py`: `router = APIRouter(prefix="/v1/approvals", tags=["approvals"])`. SQL constant `_LIST_SQL = "SELECT id, agent_id, thread_id, tier, action_type, payload_json, status, created_at, sla_deadline, decided_at, decided_by, decision_json, escalated_to_id FROM hitl.approvals WHERE tier = $1 AND status = $2 ORDER BY created_at DESC LIMIT $3 OFFSET $4"` (or with COALESCE for optional tier/status filters; use sql_builder for optional params or have a few SQL constants for tier-only / status-only / both-filtered). `@router.get("/")` async: query params tier:Tier|None, status:ApprovalStatus|None, limit:int=50 (le=200), offset:int=0; SELECT into list; total via separate count query. `@router.post("/{approval_id}/decide", response_model=DecideResponse)`: depends on queue_writer, audit_writer, supervisor_graph, checkpointer. Body: DecideRequest. Logic:
    1. Fetch approval row: `SELECT * FROM hitl.approvals WHERE id=$1` — if not found 404; if status != 'pending' 404 (or 409 if we want to differentiate — pick 404 with body `{"detail":"already_decided"}` for simplicity).
    2. Tier-level motivation check: if approval.tier in {supervisor, manager, safety_interlock} AND body.decision in {approve, reject} AND not body.motivation → raise HTTPException(400, "motivation_required_for_tier_{tier}").
    3. Update via queue_writer.update_decision(...); if returns 0 (race condition — already decided) → 404.
    4. Build ApprovalDecision Pydantic model; this is the resume value.
    5. Call `safe_invoke(supervisor_graph, initial_state=None, config={"configurable":{"thread_id":approval.thread_id},"recursion_limit":25}, resume_value=ApprovalDecision)` — note: LangGraph's `Command(resume=value)` is passed by invoking with `Command(resume=value)` instead of state. Implement via `await supervisor_graph.ainvoke(Command(resume=ApprovalDecision_dict), config={"configurable":{"thread_id":...},"recursion_limit":25})`.
    6. Return DecideResponse with approval (refetched), audit_id (from state — human_approval_node returns it in state delta), resumed=True.
    `routers/threads.py`: `router = APIRouter(prefix="/v1/threads", tags=["threads"])`. `@router.post("/{thread_id}/resume", response_model=ResumeResponse)`: body ResumeRequest. Same logic as decide but routed via thread_id (allows resuming when the caller knows thread but not the approval). Internally derives approval_id from body; same safe_invoke call.
    Idempotency-Key middleware: implement as FastAPI middleware in `main.py` or as a small `idempotency.py`. In-memory LRU cache `{(method, path, key): (timestamp, body_hash, response_dict)}` with TTL 5 minutes. On POST/PUT/PATCH with `Idempotency-Key` header: compute body_hash (sha256 of raw body bytes); if key exists with same body_hash → return cached response; if same key + different body_hash → return 409 `{"detail":"idempotency_conflict"}`. Use `functools.lru_cache` or a simple dict + asyncio.Lock + expiration check on each request. NOTE: in-memory cache is per-instance — Phase 11 will migrate to Redis (deferred).
    Register both routers in `main.py`.
    `tests/test_approvals_router.py`: unit tests (mocked queue_writer + supervisor_graph + audit_writer). Test 1: GET /v1/approvals?tier=operator&status=pending returns list shape. Test 2: POST /v1/approvals/{id}/decide happy path with valid body returns 200. Test 3: missing motivation for supervisor tier with decision=approve → 400. Test 4: id not found → 404. Test 5: queue_writer.update_decision raises ApprovalNotFoundError → 404. Test 6: Idempotency-Key replay with same body → returns cached response (verify by counting calls to queue_writer.update_decision — should be 1, not 2). Test 7: Idempotency-Key replay with different body → 409.
    `tests/test_resume_endpoint.py`: unit tests. Test 1: POST /v1/threads/{thread_id}/resume returns ResumeResponse. Test 2: thread_id with no checkpoint → 404 (mock checkpointer.aget_tuple returns None). Test 3: Idempotency-Key replay returns cached.

    Conventional commits: (1) `feat(04-07-api-gateway-e2e-02): pydantic request/response models for approvals + resume`, (2) `feat(04-07-api-gateway-e2e-02): GET /v1/approvals + POST /v1/approvals/{id}/decide router`, (3) `feat(04-07-api-gateway-e2e-02): POST /v1/threads/{thread_id}/resume router`, (4) `feat(04-07-api-gateway-e2e-02): idempotency-key middleware (5min lru cache, T-04-Resume-Replay defense)`, (5) `test(04-07-api-gateway-e2e-02): approvals + resume router unit tests (10 cases)`.
  </action>
  <pattern_ref>packages/sft-tools/src/sft_tools/timescale/query.py:35-43 (SQL constant pattern for list query) ; PATTERNS §3.13 fallback for FastAPI (no in-repo analog)</pattern_ref>
  <threat_ref>T-04-Bypass-HITL (decide endpoint is the ONLY resume path; ApprovalNotFoundError + status check prevent backdoor resume) ; T-04-Resume-Replay (Idempotency-Key middleware + status='pending' check + ApprovalNotFoundError) ; T-04-Audit-Tamper (decide endpoint calls audit_writer.write inside the resume flow; PG-first invariant via Plan 04-06 AuditWriter)</threat_ref>
  <acceptance_criteria>
    - `python -c "from svc_api_gateway.routers.approvals import router; print(len(router.routes))"` outputs at least 2 (GET + POST)
    - `python -c "from svc_api_gateway.routers.threads import router; print('/resume' in str(router.routes))"` outputs True
    - `grep -nF 'Idempotency-Key' apps/api-gateway/src/svc_api_gateway/main.py` or `idempotency.py` returns at least 1 match
    - `grep -nE 'f["\\'].*INSERT|f["\\'].*UPDATE|f["\\'].*SELECT' apps/api-gateway/src/svc_api_gateway/routers/*.py` returns 0 matches (parameterized SQL only)
    - `nx test api-gateway --testNamePattern='test_approvals_router|test_resume_endpoint'` exits 0 (10+ test cases pass)
  </acceptance_criteria>
  <verify>
    <automated>nx test api-gateway --testNamePattern='test_approvals_router|test_resume_endpoint'</automated>
  </verify>
  <done>Approvals + threads routers operational with Pydantic-shaped responses; Idempotency-Key middleware caching 5min per (key, path) + 409 on body-hash mismatch; ApprovalNotFoundError translated to 404; 10+ unit tests green.</done>
  <commit_scope>feat(04-07-api-gateway-e2e)</commit_scope>
</task>

<task type="auto" tdd="true">
  <id>04-07-03</id>
  <name>Task 3: E2E HITL cycle test surviving docker compose restart (success criterion #4)</name>
  <files>tests/e2e/__init__.py, tests/e2e/test_hitl_cycle.py</files>
  <read_first>
    tests/conftest.py (compose_stack fixture lines 84-147)
    tests/integration/test_e2e_sim_to_timescale.py (entire file — E2E pattern with compose_stack)
    .planning/phases/04-core-agentic-runtime-hitl/04-VALIDATION.md (Manual-Only Verifications + Test Infrastructure)
    .planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md (§3.15 — E2E test pattern; known port-5432 issue at OQ8)
    infra/compose/core.yml (read to identify api-gateway service name + ports — may need to add api-gateway service to compose if not already present)
  </read_first>
  <behavior>
    - Compose stack brought up via compose_stack fixture (or testcontainers per OQ8 — pick one consistent strategy)
    - api-gateway service added to compose if absent (image built from `apps/api-gateway/Dockerfile` — create minimal Dockerfile if needed, following services/ot-bridge/Dockerfile pattern from Phase 3)
    - Test flow:
      1. Apply migrations (already in compose lifecycle via Plan 04-02 [BLOCKING], but test also calls `python scripts/timescale-migrate.py` + `langgraph-init.py` defensively)
      2. Build a minimal LangGraph instance whose ONLY node is `human_approval_node` (or use the full supervisor graph compiled with a deterministic fake_llm via FakeListChatModel from Plan 04-03)
      3. Invoke graph with HumanMessage("Approva azione test 1") + initial state containing a ProposedAction with requires_tier=Tier.OPERATOR
      4. Graph pauses; check via HTTP `GET http://localhost:8081/v1/approvals?tier=operator&status=pending` → assert 1 row exists with correct payload
      5. Restart api-gateway: `subprocess.run(["docker","compose","-f","infra/compose/core.yml","restart","api-gateway"], check=True)`; wait until `GET /v1/health` returns 200 again (poll with timeout)
      6. POST `http://localhost:8081/v1/approvals/{id}/decide` with body `{"decision":"approve","motivation":"E2E test ok","decided_by":"test-user"}` + Idempotency-Key header
      7. Assert 200 response with resumed=True
      8. Query PG via asyncpg directly: `SELECT decision, motivation, approval_id FROM audit.actions WHERE thread_id=<test_thread>` → assert decision='hitl_operator', motivation='E2E test ok', approval_id matches
      9. Query NATS via consumer: assert hitl.approvals.new.operator + hitl.approvals.resolved.operator + audit.actions.<cluster>.<agent> were all published
      10. Idempotency replay: POST same decide call again → returns cached response (no new audit row)
    - Test marker: `@pytest.mark.e2e` + `@pytest.mark.integration` for CI selection
    - On port-5432 conflict (OQ8): fallback to testcontainers-spawned PG+NATS bound to ephemeral ports; api-gateway runs as host process (uvicorn) pointing to those ports — document explicitly in test fixture
  </behavior>
  <action>
    Create `tests/e2e/__init__.py` empty.
    Create `tests/e2e/test_hitl_cycle.py` with the test flow above. Top of file:
    ```python
    import asyncio, subprocess, time, json, os
    from uuid import uuid4
    from datetime import datetime, timezone
    import asyncpg, httpx, nats, pytest
    from langgraph.types import Command
    from sft_agents.runtime import build_supervisor_graph, format_thread_id, get_postgres_checkpointer, safe_invoke
    from sft_agents.models import ApprovalDecision, EvidencePanel, ToolCall, TokenUsage, ProposedAction
    from sft_agents.policies.routing import HybridRouter
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from langchain_core.messages import HumanMessage
    ```
    Test function `async def test_hitl_cycle_survives_restart(compose_stack)`: implements 10-step flow. Use `compose_stack` fixture from tests/conftest.py (yields dict with pg_dsn, nats_url, api_gateway_url). If `compose_stack` not configured for api-gateway, fallback to running api-gateway in-process via uvicorn TestClient — but for "survives restart" the service MUST be in compose (not in-process). Decision: this plan requires `infra/compose/core.yml` to include an `api-gateway` service. If it doesn't, add it in this task with minimal Dockerfile + compose entry.
    Add `apps/api-gateway/Dockerfile` (NEW): replicate `services/ot-bridge/Dockerfile` (multistage build with uv); CMD `uvicorn svc_api_gateway.main:app --host 0.0.0.0 --port 8081`. Build context: monorepo root with selective COPY (per pattern from Phase 3).
    Add api-gateway entry to `infra/compose/core.yml`: depends_on postgres + nats; env: TIMESCALE_DSN, NATS_URL; ports: 8081:8081; networks: sft-core (NOT sft-ot — api-gateway must NOT reach OT side per Phase 3 data-diode).
    Add second test `test_idempotency_key_replay` covering Step 10 above.
    Add third test `test_thread_resume_endpoint` POSTing to /v1/threads/{thread_id}/resume directly (vs /v1/approvals/{id}/decide).
    Update `tests/conftest.py` (root): extend `compose_stack` fixture to include `api_gateway_url: str` (e.g. `http://localhost:8081`); add `restart_service(name: str)` helper method on the yielded fixture object — invokes `subprocess.run(["docker","compose","-f","infra/compose/core.yml","restart",name])`.
    Test handles OQ8 port-5432 issue: if compose_stack returns environment that conflicts with host PG, the test should fall back to a per-test docker compose project name via `COMPOSE_PROJECT_NAME=sft-phase4-e2e-{uuid}` so each test run has isolated containers. Document in test docstring.

    Conventional commits: (1) `chore(04-07-api-gateway-e2e-03): add api-gateway service to docker-compose + minimal dockerfile`, (2) `test(04-07-api-gateway-e2e-03): e2e hitl cycle test surviving docker compose restart (success criterion #4)`.
  </action>
  <pattern_ref>tests/integration/test_e2e_sim_to_timescale.py:17-62 (E2E pattern with compose_stack — replicate structure) ; tests/conftest.py:84-147 (compose_stack fixture yield/teardown — extend with api-gateway entry + restart_service method)</pattern_ref>
  <threat_ref>T-04-Bypass-HITL (E2E validates ONLY the official resume path can complete the cycle) ; T-04-Resume-Replay (Step 10 tests Idempotency-Key replay defense)</threat_ref>
  <acceptance_criteria>
    - `tests/e2e/test_hitl_cycle.py` exists with at least 3 test functions
    - `apps/api-gateway/Dockerfile` exists
    - `grep -nE '^\s*api-gateway:' infra/compose/core.yml` returns 1 match (service entry)
    - `grep -nF 'docker compose' tests/e2e/test_hitl_cycle.py` returns at least 1 match (restart invocation)
    - `pytest tests/e2e/test_hitl_cycle.py -m e2e -v` exits 0 against a brought-up compose stack
    - Audit row created in PG with decision='hitl_operator' AND motivation NOT NULL AND approval_id matching the decided approval — asserted in test
    - NATS message round-trip asserted (hitl.approvals.new + resolved + audit.actions subjects all received)
  </acceptance_criteria>
  <verify>
    <automated>pytest tests/e2e/test_hitl_cycle.py -m e2e -v</automated>
  </verify>
  <done>E2E HITL cycle test green; survives docker compose restart of api-gateway; idempotency replay verified; api-gateway service in compose; success criterion #1 + #4 demonstrated end-to-end.</done>
  <commit_scope>test(04-07-api-gateway-e2e), chore(04-07-api-gateway-e2e)</commit_scope>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| External HTTP client → FastAPI | Untrusted; Pydantic validates request body; Idempotency-Key middleware bounds replay |
| FastAPI handler → supervisor graph | Trusted (process-local); resume payload validated against ApprovalDecision schema |
| FastAPI shutdown → background tasks | Graceful cancel via shutdown_event; pool drain; NATS drain |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-Bypass-HITL | Elevation | /v1/approvals/{id}/decide | mitigate | Only path that resumes paused graphs; ApprovalNotFoundError + status='pending' guards prevent backdoor; future Phase 11 adds RBAC |
| T-04-Resume-Replay | Tampering | Idempotency-Key middleware + status check | mitigate | (a) status='pending' enforced at SQL UPDATE in queue_writer (Plan 04-06 atomic with WHERE status='pending'); (b) Idempotency-Key cache 5min per (key, body_hash); (c) ApprovalNotFoundError → 404 |
| T-04-Audit-Tamper | Tampering | Resume path → AuditWriter | mitigate | Resume calls audit_writer.write (Plan 04-06 PG-first invariant); REVOKE at DB-level (Plan 04-02) |
| T-04-Checkpoint-PII | Info Disclosure | Lifespan checkpointer | mitigate | Plan 04-06 GDPRRedactor strips PII pre-checkpoint; api-gateway only proxies; no PII logging in router |
| T-04-Auth-Missing | (deferred) | All endpoints | accept (Phase 11) | OAuth/OIDC + RBAC deferred per CONTEXT.md scope_boundaries; Phase 4 ships endpoints without auth — operator UI behind VPN per A-018 |
</threat_model>

<verification>
- api-gateway boots via uvicorn; lifespan opens pool/NATS/checkpointer/supervisor + 3 background tasks
- GET /v1/health returns 200 with dependency statuses
- GET /v1/approvals with filters + pagination returns ApprovalResponse list
- POST /v1/approvals/{id}/decide validates body, calls queue_writer.update_decision atomically, calls supervisor_graph.ainvoke(Command(resume=...)), returns DecideResponse with audit_id
- 404 on missing/already-decided approval; 400 on missing motivation for required tiers; 409 on Idempotency-Key conflict
- POST /v1/threads/{thread_id}/resume operational
- E2E test survives docker compose restart of api-gateway (success criterion #4)
- Idempotency replay verified (defense layer for T-04-Resume-Replay)
- 14 unit/integration tests + 3 E2E tests green
</verification>

<success_criteria>
- HITL-01 user-visible: REST decide endpoint completes interrupt→resume cycle
- HITL-04 REST API: approvals list + decide endpoints operational
- CORE-04 final: paused HITL approval thread SURVIVES docker compose restart (success criterion #4 demonstrated end-to-end)
- OQ7 resolved: api-gateway scaffolded
- OQ8 resolved: testcontainers / per-test compose project isolation eliminates port-5432 conflict
- Phase 4 success criterion #1: full HITL cycle end-to-end with audit dual-write
</success_criteria>

<output>
Create `.planning/phases/04-core-agentic-runtime-hitl/04-07-SUMMARY.md`. Include: REST endpoint list, lifespan dependencies, background tasks started, E2E restart-survival evidence, Idempotency-Key defense semantics, deferrals (auth, Redis idempotency).
</output>
