---
phase: 06-agents-operations-production
plan: 12
plan_id: 06-12
subsystem: api-gateway
tags: [http, ops-agents, quality, fastapi, supervisor-graph, idempotency, langfuse]
dependency_graph:
  requires:
    - 06-00  # tracking + dev tooling
    - 06-05  # build_ops_subgraph (target_agent routing)
    - 06-06  # AnomalyDetector contract
    - 06-07  # QualityInspector contract (NATS subject)
    - 06-08  # ProductionPlanner contract
    - 06-10  # OperatorAssistant contract
  provides:
    - "HTTP entrypoint: POST /v1/quality/events"
    - "HTTP entrypoint: POST /v1/agents/anomaly-detector/scan"
    - "HTTP entrypoint: POST /v1/agents/production-planner/plan"
    - "HTTP entrypoint: POST /v1/agents/operator-assistant/chat"
  affects:
    - 06-11  # scheduler will POST to /v1/agents/anomaly-detector/scan
    - 06-13  # E2E tests will hit all 4 endpoints
    - "Phase 10 demo UI (consumes all 4 endpoints)"
tech-stack:
  added: []
  patterns:
    - "FastAPI APIRouter prefix='/v1/quality' + '/v1/agents'"
    - "Pydantic frozen=True + extra='forbid' request shapes (T-V6-injection)"
    - "Server-forced source='operator' (T-V6-source-spoof)"
    - "Idempotency-Key cache via check_idempotency_cache + store_idempotent_response"
    - "supervisor_graph.ainvoke(state, config=build_invocation_config(...))"
    - "Langfuse tag 'agent.<slug>.invoke' per Phase 4 observability"
    - "recursion_limit=5 enforced on every OPS-agent invocation (T-V6-recursion-bomb)"
key-files:
  created:
    - apps/api-gateway/src/svc_api_gateway/routers/quality.py
    - apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py
    - apps/api-gateway/tests/test_quality_router.py
  modified:
    - apps/api-gateway/src/svc_api_gateway/main.py
    - apps/api-gateway/src/svc_api_gateway/models/requests.py
    - apps/api-gateway/tests/test_ops_endpoints.py
decisions:
  - "Re-declare ops-agent request shapes locally in models/requests.py (AnomalyScanRequestBody, PlanRequestBody, OperatorChatRequestBody) instead of importing from apps/agents/ops/<slug>/models.py — keeps api-gateway decoupled from every ops-agent package; rules stay in sync via Phase 6 contract tests."
  - "Reuse get_nats_publisher (AuditNatsPublisher.publish_raw) instead of introducing a new get_nats_client dependency — the publisher already exposes raw publish for arbitrary subjects (used by OutboxRetry) and forcing two NATS clients per process duplicates connection state."
  - "Forward source='operator' server-side and OMIT source from the operator request schema (extra=forbid) — defense-in-depth for T-V6-source-spoof: a client attempting source='simulator' gets 422 BEFORE reaching the publish step."
  - "Honour client-supplied thread_id for /v1/agents/operator-assistant/chat (multi-turn checkpoint reuse); generate fresh thread_id for /scan and /plan (one-shot tasks)."
  - "Return 202 from /production-planner/plan (HITL approval is asynchronous); 200 from /scan + /chat (synchronous responses)."
  - "recursion_limit=5 (not 25 like Phase 4 /decide) — OPS agents are per-tick bounded; supervisor escalates overflow to HITL via safe_invoke."
metrics:
  duration_minutes: 25
  completed_date: "2026-05-23"
  tasks_completed: 2
  tests_added: 12
  files_created: 3
  files_modified: 3
---

# Phase 06 Plan 12: API Gateway OPS Endpoints Summary

**One-liner.** 4 FastAPI endpoints (`POST /v1/quality/events` + 3 `POST /v1/agents/<slug>/<action>`) wire operator HTTP calls into the OPS supervisor graph via `target_agent` routing, with Pydantic frozen+extra=forbid validation, Idempotency-Key replay defense, and Langfuse `agent.<slug>.invoke` tagging.

## What shipped

### 1. `POST /v1/quality/events` (OPS-04 / D-QI-01)

| Field           | Value                                                          |
| --------------- | -------------------------------------------------------------- |
| Status          | 202 Accepted                                                   |
| Request model   | `QualityEventOperatorRequest` (asset_id, dye_lot_id, defect_type, defect_length_inches, full_width, position_meters, timestamp) |
| Response        | `{"accepted": true, "event_id": "<uuid4>"}`                    |
| NATS subject    | `quality.events.<asset_id>`                                    |
| Idempotency     | Yes (Idempotency-Key header → 5 min in-memory cache)           |
| Span tag        | n/a (NATS publish, not supervisor invocation)                  |

The route deliberately rejects any client-supplied `source` field via `extra="forbid"` (T-V6-source-spoof — the spoof attempt returns 422 before the publish step) and stamps `source="operator"` server-side on the validated payload that is forwarded to NATS.

### 2. `POST /v1/agents/anomaly-detector/scan` (OPS-01)

| Field           | Value                                                          |
| --------------- | -------------------------------------------------------------- |
| Status          | 200 OK                                                         |
| Request model   | `AnomalyScanRequestBody` (window_minutes: 1..180, triggered_by: scheduler/operator/agent) |
| State injected  | `{"target_agent": "anomaly-detector", "thread_id": "ops.anomaly-detector.<uuid4>", "window_minutes", "triggered_by"}` |
| Response        | `{"anomalies": [...], "suppressed_count": N, "thread_id": "..."}` |
| Idempotency     | Yes                                                            |
| Span tag        | `agent.anomaly-detector.invoke`                                |

### 3. `POST /v1/agents/production-planner/plan` (OPS-02)

| Field           | Value                                                          |
| --------------- | -------------------------------------------------------------- |
| Status          | 202 Accepted (HITL approval is async)                          |
| Request model   | `PlanRequestBody` (strategy: spt/edd, horizon_days: 1..30, user_roles) |
| State injected  | `{"target_agent": "production-planner", "thread_id", "horizon_days", "strategy", "user_roles"}` |
| Response        | `{"thread_id", "pending_approval_id" (nullable), "proposed_actions_count"}` |
| Idempotency     | Yes                                                            |
| Span tag        | `agent.production-planner.invoke`                              |

Operator polls `GET /v1/approvals` (or NATS push) and resolves via `POST /v1/approvals/{id}/decide` — pre-existing Phase 4 HITL flow.

### 4. `POST /v1/agents/operator-assistant/chat` (OPS-03)

| Field           | Value                                                          |
| --------------- | -------------------------------------------------------------- |
| Status          | 200 OK                                                         |
| Request model   | `OperatorChatRequestBody` (query: 1..2000 chars, user_roles, thread_id) |
| State injected  | `{"target_agent": "operator-assistant", "thread_id", "query", "user_roles"}` |
| Response        | `{"response_md", "citations", "citations_missing", "lang", "tool_calls_count", "thread_id"}` |
| Idempotency     | Yes                                                            |
| Span tag        | `agent.operator-assistant.invoke`                              |

Client-supplied `thread_id` is honoured verbatim — multi-turn chat reuses the same LangGraph checkpoint via the AsyncPostgresSaver.

## Threat mitigations enforced

| Threat ID             | Where enforced                                                | Test                                                       |
| --------------------- | ------------------------------------------------------------- | ---------------------------------------------------------- |
| T-V6-injection        | Pydantic frozen + extra=forbid on all 4 request shapes        | `test_post_quality_event_unknown_defect_type_422`, `test_post_anomaly_scan_triggered_by_enum`, `test_post_planner_plan_strategy_validates`, `test_post_operator_chat_query_min_length` |
| T-V6-source-spoof     | `source` field absent from QualityEventOperatorRequest        | `test_post_quality_event_forces_source_operator`           |
| T-V6-idempotency-replay | `check_idempotency_cache` + `store_idempotent_response`     | `test_post_quality_event_idempotency_key_cached`           |
| T-V6-recursion-bomb   | `build_invocation_config(..., recursion_limit=5)`             | `test_post_anomaly_scan_invokes_supervisor` (asserts cfg.recursion_limit==5) |
| T-V6-acl-leak (dev)   | `user_roles` propagated verbatim into AgentState              | Documented in assumptions/register.yaml; Phase 11 JWT replaces |

## Langfuse / observability

Every OPS-agent endpoint passes `tags=["agent.<slug>.invoke"]` to `sft_agents.llm.langfuse_callback.build_invocation_config`, which composes Langfuse v3 metadata + callback handler (no-op when `LANGFUSE_HOST` is unset). The dedicated test `test_endpoints_emit_langfuse_span` monkey-patches the helper and asserts the tag for all 3 endpoints.

## Idempotency policy

| Endpoint                                | Idempotency-Key cached? | Rationale                                                 |
| --------------------------------------- | ----------------------- | --------------------------------------------------------- |
| `POST /v1/quality/events`               | yes                     | Replay defense for operator double-submit                 |
| `POST /v1/agents/anomaly-detector/scan` | yes                     | Replay defense for scheduler retries (Plan 06-11)         |
| `POST /v1/agents/production-planner/plan` | yes                   | Long-running HITL — replay returns cached thread_id       |
| `POST /v1/agents/operator-assistant/chat` | yes                   | Multi-turn chat — caller may include header per-turn      |

In-process in-memory cache (TTL 300 s). Phase 11 migrates to Redis (documented in 04-07 SUMMARY).

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 1 — Simplification] Reused `get_nats_publisher` instead of adding `get_nats_client`**
- **Found during:** Task 2
- **Issue:** Plan specified adding a new `get_nats_client()` dependency for raw NATS publishing.
- **Fix:** `AuditNatsPublisher` already exposes `publish_raw(subject, payload)` (used by the existing OutboxRetry). Reusing the existing publisher avoids two concurrent NATS connections per process and reuses the established `app.state.nats_publisher` lifespan wiring.
- **Files modified:** `apps/api-gateway/src/svc_api_gateway/routers/quality.py`
- **Commit:** `b8e91ca`

**2. [Rule 1 — Decoupling] Mirrored ops-agent request models locally in `models/requests.py`**
- **Found during:** Task 2
- **Issue:** Plan suggested importing `AnomalyScanRequest`, `PlanRequest`, `OperatorChatRequest` from the per-agent packages. The api-gateway `pyproject.toml` does not (and should not) depend on every ops-agent package — adding 4 implicit Python deps would couple deploy units that we deliberately keep apart.
- **Fix:** Re-declared the same Pydantic contracts (`AnomalyScanRequestBody`, `PlanRequestBody`, `OperatorChatRequestBody`) in `svc_api_gateway/models/requests.py` with identical `frozen=True, extra="forbid"` rules and identical Field constraints.
- **Risk:** Contract drift. Mitigated by Plan 06-13 E2E tests which hit the HTTP boundary and exercise both shapes end-to-end; any divergence will surface there.
- **Files modified:** `apps/api-gateway/src/svc_api_gateway/models/requests.py`
- **Commit:** `b8e91ca`

## Verification

| Check                                                              | Result                                  |
| ------------------------------------------------------------------ | --------------------------------------- |
| `uv run pytest apps/api-gateway/tests/` (full module suite)        | 26 passed (12 new + 14 pre-existing)    |
| All 4 routes appear in `app.openapi()` schema                      | Confirmed                               |
| Module import smoke (`python -c "from svc_api_gateway.routers import quality, ops_agents"`) | OK                              |
| `uv run ruff check src`                                            | 30 errors (2 fewer than baseline of 32) |

## Self-Check: PASSED

- File `apps/api-gateway/src/svc_api_gateway/routers/quality.py` — FOUND
- File `apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py` — FOUND
- File `apps/api-gateway/tests/test_quality_router.py` — FOUND
- File `apps/api-gateway/tests/test_ops_endpoints.py` (full implementation) — FOUND
- Commit `e1632d3` (RED: test(06-12)) — FOUND in git log
- Commit `b8e91ca` (GREEN: feat(06-12)) — FOUND in git log

## TDD Gate Compliance

- RED commit `e1632d3` — `test(06-12): add failing tests` — present
- GREEN commit `b8e91ca` — `feat(06-12): add /v1/quality/events + /v1/agents/...` — present
- REFACTOR commit — not required; implementation was clean on first GREEN pass
