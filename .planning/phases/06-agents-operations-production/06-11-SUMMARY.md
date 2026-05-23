---
phase: 06-agents-operations-production
plan: 11
subsystem: services/agents-scheduler
tags: [apscheduler, cron, httpx, helm, compose, ops, ops-04]
requires:
  - 06-00 (Wave-0 stub: services/agents-scheduler/tests/test_scheduler.py)
  - 06-06 (AnomalyDetector agent — invocation target)
provides:
  - services/agents-scheduler/src/svc_agents_scheduler/scheduler.py (build_scheduler + run_until_signal)
  - services/agents-scheduler/src/svc_agents_scheduler/client.py (trigger_anomaly_scan + build_http_client)
  - services/agents-scheduler/src/svc_agents_scheduler/__main__.py (container entrypoint)
  - services/agents-scheduler/Dockerfile (python:3.12-slim, USER 1000:1000)
  - infra/helm/charts/agents-scheduler/* (Chart.yaml + values.yaml + templates/deployment.yaml)
  - infra/compose/core.yml: agents-scheduler service
affects:
  - workspace root pyproject.toml: services/agents-scheduler registered
  - api-gateway: implicit caller of /v1/agents/anomaly-detector/scan (06-12 ships the endpoint)
tech-stack:
  added:
    - APScheduler 3.11.2 (>=3.10.4,<4) — verified on PyPI (MIT, agronholm/apscheduler)
  patterns:
    - Pattern 4 (06-RESEARCH lines 543-592): AsyncIOScheduler in dedicated container
    - Pitfall §5: misfire_grace_time=300 + coalesce=True + max_instances=1 + replicas=1
key-files:
  created:
    - services/agents-scheduler/pyproject.toml
    - services/agents-scheduler/project.json
    - services/agents-scheduler/Dockerfile
    - services/agents-scheduler/src/svc_agents_scheduler/__init__.py
    - services/agents-scheduler/src/svc_agents_scheduler/__main__.py
    - services/agents-scheduler/src/svc_agents_scheduler/scheduler.py
    - services/agents-scheduler/src/svc_agents_scheduler/client.py
    - services/agents-scheduler/tests/test_client.py
    - infra/helm/charts/agents-scheduler/Chart.yaml
    - infra/helm/charts/agents-scheduler/values.yaml
    - infra/helm/charts/agents-scheduler/templates/_helpers.tpl
    - infra/helm/charts/agents-scheduler/templates/deployment.yaml
  modified:
    - services/agents-scheduler/tests/test_scheduler.py (un-skipped Wave-0 stub)
    - services/agents-scheduler/tests/__init__.py (empty)
    - pyproject.toml (workspace member added)
    - infra/compose/core.yml (agents-scheduler service entry)
    - uv.lock (APScheduler + svc-agents-scheduler resolution)
decisions:
  - "APScheduler legitimacy pre-checked via PyPI JSON API (name=APScheduler, version=3.11.2, license=MIT, maintainer=github.com/agronholm/apscheduler). Task 1 blocking-human checkpoint resolved automatically by orchestrator with on-the-wire verification — not a slopsquat."
  - "AsyncIOScheduler.add_job() kwargs (misfire_grace_time=300, coalesce=True, max_instances=1) pinned at the build_scheduler() construction site, NOT at the caller. Tests assert each flag individually so any future drift surfaces as a test failure."
  - "Single-instance guarantee enforced at three layers: APScheduler max_instances=1 (in-process), Helm replicas=1 + strategy=Recreate (k8s), compose deploy.replicas=1 (documentation parity)."
  - "Helm chart does NOT expose a Service or probes — scheduler has no inbound HTTP. A future log-freshness liveness probe is left for a follow-up plan if false-positive restarts emerge."
  - "Shared httpx.AsyncClient across cron fires (built once in __main__.main, reused by _fire closure). Saves TLS handshake per fire and lets the AsyncHTTPTransport(retries=3) connection pool warm."
  - "Per-fire exception handler in __main__._fire logs and swallows — a single gateway hiccup must not crash the loop. Pitfall §5 + RateLimiter on the detector side (06-02) handle the storm case."
  - "Container CMD uses `python -m svc_agents_scheduler` (not the `agents-scheduler` console script) for symmetry with knowledge-ingest pattern and explicit module resolution."
metrics:
  duration_minutes: 20
  tasks_completed: 4
  tests_added: 10
  files_created: 12
  files_modified: 5
  completed_at: 2026-05-23
---

# Phase 06 Plan 11: agents-scheduler Service Summary

APScheduler-based cron container (`services/agents-scheduler/`) that POSTs to `POST /v1/agents/anomaly-detector/scan` every 5 minutes with `{window_minutes, triggered_by: "scheduler"}` — implements the real-time component of D-AD-04 / OPS-04 with single-instance guarantees pinned at scheduler, Helm, and compose levels (Pitfall §5).

## Cron Configuration

| Layer            | Value                                  | Where                                         |
| ---------------- | -------------------------------------- | --------------------------------------------- |
| Default cron     | `*/5 * * * *` (every 5 min, UTC)       | `__main__.py` default + Helm `values.yaml`    |
| Override env     | `ANOMALY_CRON`                         | Read at container start                       |
| Trigger type     | `CronTrigger.from_crontab(cron)`       | `scheduler.build_scheduler`                   |
| Timezone         | UTC                                    | `AsyncIOScheduler(timezone="UTC")`            |

## Misfire / Concurrency Policy (Pitfall §5)

| Knob                  | Value | Rationale                                                   |
| --------------------- | ----- | ----------------------------------------------------------- |
| `misfire_grace_time`  | 300s  | 5-min catch-up window after container restart                |
| `coalesce`            | True  | Collapses queued catch-up fires into one                     |
| `max_instances`       | 1     | Never overlap two scans even if a single fire runs long      |
| Helm `replicas`       | 1     | No shared jobstore — N>1 replicas would fire cron N times    |
| Helm `strategy`       | Recreate | Avoids two pods coexisting briefly during rolling updates |
| Compose `deploy.replicas` | 1 | Documentation parity for swarm + dev hygiene                |

## Environment Variables

| Var                       | Required | Default               | Purpose                                    |
| ------------------------- | -------- | --------------------- | ------------------------------------------ |
| `API_GATEWAY_URL`         | yes      | —                     | Base URL of api-gateway (fail-fast if unset) |
| `ANOMALY_WINDOW_MINUTES`  | no       | `15`                  | Forwarded in JSON body                     |
| `ANOMALY_CRON`            | no       | `*/5 * * * *`         | Cron expression                            |
| `LOG_LEVEL`               | no       | `INFO`                | structlog level                            |
| `OT_BRIDGE_WRITE_DISABLED`| no       | `true`                | Defence-in-depth flag (D-18)               |

## Test Coverage

| File               | Tests | Asserts                                                          |
| ------------------ | ----- | ---------------------------------------------------------------- |
| `test_scheduler.py`| 6     | CronTrigger built, misfire=300, coalesce=True, max_instances=1, stable `id="anomaly-detector-scan"`, SIGINT/SIGTERM → shutdown(wait=True) |
| `test_client.py`   | 4     | POST URL, body shape (window_minutes + triggered_by="scheduler"), AsyncHTTPTransport(retries=3), `scheduler_invoked` structlog event w/ status_code |
| **Total**          | **10**| **10/10 green**                                                  |

## Verification Run

```text
============================= test session starts ==============================
collecting ... collected 10 items
tests/test_client.py::test_post_to_correct_url PASSED                    [ 10%]
tests/test_client.py::test_post_body_contains_window_minutes_and_triggered_by PASSED [ 20%]
tests/test_client.py::test_build_http_client_uses_retries_3_transport PASSED [ 30%]
tests/test_client.py::test_post_logs_status_code PASSED                  [ 40%]
tests/test_scheduler.py::test_add_job_uses_cron_trigger PASSED           [ 50%]
tests/test_scheduler.py::test_add_job_misfire_grace_time_300 PASSED      [ 60%]
tests/test_scheduler.py::test_add_job_coalesce_true PASSED               [ 70%]
tests/test_scheduler.py::test_add_job_max_instances_1 PASSED             [ 80%]
tests/test_scheduler.py::test_add_job_id_anomaly_detector_scan PASSED    [ 90%]
tests/test_scheduler.py::test_shutdown_on_sigint PASSED                  [100%]
============================== 10 passed in 0.17s ==============================
```

`helm template test-release infra/helm/charts/agents-scheduler/` renders cleanly with `replicas: 1`, `strategy: Recreate`, env wired from `values.yaml`.

## Authentication Gates

None — scheduler ↔ api-gateway is intra-cluster traffic with no token at this phase. Phase 11 may add mTLS service-mesh hooks; this plan does not pre-empt that.

## TDD Gate Compliance

- RED gate: `0d8983e test(06-11): add failing tests for agents-scheduler (scheduler + client)` — confirmed `ModuleNotFoundError: No module named 'svc_agents_scheduler'` before implementation.
- GREEN gate: `b985bf8 feat(06-11): implement svc-agents-scheduler container (APScheduler + httpx)` — all 10 tests pass.
- Wiring gate: `d017078 feat(06-11): wire agents-scheduler compose entry + Helm chart (replicas=1 pin)` — infra-only follow-up (tests stay green).

No REFACTOR commit needed — the implementation is the canonical Pattern 4 shape and required no clean-up after going green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed spurious AsyncHTTPTransport() call in retries=3 test**
- **Found during:** Task 3 GREEN verification
- **Issue:** `test_build_http_client_uses_retries_3_transport` set `transport_cls.return_value = httpx.AsyncHTTPTransport()` to supply a duck-typed return, but that line itself counted as a (real) `AsyncHTTPTransport()` call before the patch took effect — `transport_cls.assert_called_once()` then failed with "Called 2 times."
- **Fix:** Dropped the redundant return_value assignment; the default MagicMock return is enough to satisfy `httpx.AsyncClient(transport=...)` duck-typing. The patch now records exactly the one call made by `build_http_client()`.
- **Files modified:** `services/agents-scheduler/tests/test_client.py`
- **Commit:** Folded into `b985bf8`

### Architectural Choices Within Plan

**1. Shared httpx.AsyncClient across cron fires (not per-fire)**
- Plan sketch in Pattern 4 (lines 557-563) uses `async with httpx.AsyncClient(...)` inside `trigger_anomaly_scan` — a per-fire client. Implementation hoists the `AsyncClient` to `__main__.main` and shares it via the `_fire` closure so the connection pool / TLS handshake / `AsyncHTTPTransport(retries=3)` budget is warm across fires.
- `trigger_anomaly_scan` still supports the per-fire pattern via `client=None` (used by tests and by the documented one-shot integration use).

**2. Per-fire exception swallowing in __main__._fire**
- Pattern 4 sketch lets exceptions propagate. Implementation wraps `_fire` in `try/except` and logs `scheduler_invoke_failed` so a transient gateway error does not crash the asyncio loop and stop all future cron fires. Rationale: `coalesce=True` + the next cron tick already provides the retry; a process exit on transient failure would create thrash.

**3. Strategy: Recreate (Helm)**
- Plan does not specify update strategy. Chose `Recreate` over default `RollingUpdate` to avoid the brief two-pod window during a rolling update — that window would violate the single-instance contract.

### CLAUDE.md Compliance

- Files small + focused: `scheduler.py` 88 LOC, `client.py` 99 LOC, `__main__.py` 96 LOC — all under 200 LOC.
- Immutability: `build_scheduler` returns a new scheduler; `trigger_anomaly_scan` returns a value rather than mutating shared state.
- Error handling: fail-fast on `API_GATEWAY_URL` missing (rc=2), per-fire `try/except` with structured logging.
- Input validation: env vars parsed via `int(...)` with default fallbacks; gateway URL `rstrip("/")` to prevent double-slash.

## Known Stubs

None — every code path required by the 10 tests is wired to production logic. No placeholder data, no TODO-blocked features.

## Threat Flags

None — no new trust boundaries beyond the plan's `<threat_model>`. The scheduler → api-gateway HTTP edge is intra-cluster and already tracked under `T-V6-multi-instance` (mitigated via `replicas: 1` + `max_instances: 1` + `coalesce: True`).

## Files Created / Modified

### Created (12)

- `services/agents-scheduler/pyproject.toml` (35 LOC)
- `services/agents-scheduler/project.json` (33 LOC, 4 Nx targets)
- `services/agents-scheduler/Dockerfile` (43 LOC, multi-stage)
- `services/agents-scheduler/src/svc_agents_scheduler/__init__.py` (9 LOC)
- `services/agents-scheduler/src/svc_agents_scheduler/__main__.py` (96 LOC)
- `services/agents-scheduler/src/svc_agents_scheduler/scheduler.py` (88 LOC)
- `services/agents-scheduler/src/svc_agents_scheduler/client.py` (99 LOC)
- `services/agents-scheduler/tests/test_client.py` (94 LOC, 4 tests)
- `infra/helm/charts/agents-scheduler/Chart.yaml` (17 LOC)
- `infra/helm/charts/agents-scheduler/values.yaml` (74 LOC)
- `infra/helm/charts/agents-scheduler/templates/_helpers.tpl` (62 LOC)
- `infra/helm/charts/agents-scheduler/templates/deployment.yaml` (75 LOC)

### Modified (5)

- `services/agents-scheduler/tests/test_scheduler.py` (un-skipped, 6 tests)
- `services/agents-scheduler/tests/__init__.py` (empty package marker)
- `pyproject.toml` (workspace root: `services/agents-scheduler` registered)
- `infra/compose/core.yml` (new `agents-scheduler` service)
- `uv.lock` (APScheduler + svc-agents-scheduler resolution)

## Commits

| Hash      | Message                                                                            |
| --------- | ---------------------------------------------------------------------------------- |
| `0d8983e` | test(06-11): add failing tests for agents-scheduler (scheduler + client)           |
| `b985bf8` | feat(06-11): implement svc-agents-scheduler container (APScheduler + httpx)        |
| `d017078` | feat(06-11): wire agents-scheduler compose entry + Helm chart (replicas=1 pin)     |

## Self-Check: PASSED

Files verified to exist:
- FOUND: services/agents-scheduler/src/svc_agents_scheduler/scheduler.py
- FOUND: services/agents-scheduler/src/svc_agents_scheduler/client.py
- FOUND: services/agents-scheduler/src/svc_agents_scheduler/__main__.py
- FOUND: services/agents-scheduler/Dockerfile (CMD present)
- FOUND: infra/helm/charts/agents-scheduler/values.yaml (replicas: 1)
- FOUND: infra/helm/charts/agents-scheduler/templates/deployment.yaml
- FOUND: infra/compose/core.yml (agents-scheduler entry)

Commits verified in git log:
- FOUND: 0d8983e
- FOUND: b985bf8
- FOUND: d017078

Tests: 10/10 green via `uv run pytest tests/` in `services/agents-scheduler/`.
Helm: `helm template test-release infra/helm/charts/agents-scheduler/` renders without error.
YAML: `yaml.safe_load` succeeds on `core.yml`, `values.yaml`, `Chart.yaml`.
