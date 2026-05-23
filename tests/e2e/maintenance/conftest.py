"""Shared fixtures for maintenance E2E scenario tests (Plan 07-12).

This conftest mirrors the Phase 6 ops conftest (06-13 pattern) adapted for
the maintenance cluster (MNT-01..04, MNT-06).

Provides:

    - ``mnt_scenario(request)`` — yaml.safe_load loader keyed on indirect
      parametrize values (e.g. ``"predictive-maintenance/happy"``). Returns
      the parsed scenario dict (T-V7-W0-yaml-injection mitigation: safe_load
      only).

    - ``mock_llm_backend(monkeypatch, request)`` — sets env LLM_BACKEND=mock +
      MOCK_LLM_FIXTURE=<abs path>; ALSO patches
      ``sft_agents.llm.factory.build_chat_model`` and per-agent re-exports so
      MockReplayChatModel (plan 06-01) is instantiated against the
      corresponding JSONL trace.

      Only ``rca-specialist`` and ``maintenance-coach`` agents have JSONL
      traces (PM + DA are LLM-free per 07-VALIDATION.md L91-95).

    - ``mock_collaborators_mnt(mnt_scenario)`` — dict of mocked collaborators
      for any of the 4 maintenance agents.  Pre-populated from scenario.seed
      so tests can assert on audit rows, queue items, structlog events.

    - ``seed_testcontainers(mnt_scenario, mock_collaborators_mnt)`` — seeds
      the mock collaborators with rows from scenario["seed"] (pg_audit_rows,
      pg_sensor_events, pg_downtime_events, qdrant_chunks, neo4j_facts, etc.).

    - ``api_gateway_client(mnt_scenario, mock_llm_backend, seed_testcontainers)``
      — thin wrapper that invokes the appropriate agent's __call__ method
      (or multi-turn sequence) based on the scenario spec.

Marker contract:
    - ``e2e`` — Plan 07-12 mock-LLM maintenance scenarios (this suite, CI).
    - ``real-llm`` — opt-in real Qwen2.5 smoke tests (default-skipped in CI).

Design rationale:
    Phase 7 mirrors Phase 6 06-13: tests verify each agent's deterministic
    CONTRACT (tool_calls + audit dispatch + tier routing + HITL semantics)
    using mocks, without spinning the full docker stack for every PR.
    Real testcontainer E2E (full PG+NATS+Qdrant+Neo4j stack) is tracked for
    Phase 11 (observability); this suite runs in <480s on any CI node.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SCENARIOS_ROOT = _REPO_ROOT / "tests" / "fixtures" / "mnt_scenarios"
_LLM_TRACES_ROOT = _REPO_ROOT / "tests" / "fixtures" / "llm_responses"


# ---------------------------------------------------------------------------
# Indirect-parametrize key resolution
# ---------------------------------------------------------------------------


def _resolve_scenario_key(request: pytest.FixtureRequest) -> str:
    """Extract ``"<agent>/<scenario>"`` from indirect parametrize.

    Tests should pass an indirect parametrize like::

        @pytest.mark.parametrize(
            "mnt_scenario",
            ["predictive-maintenance/happy", "predictive-maintenance/degraded", ...],
            indirect=True,
        )
    """
    param = getattr(request, "param", None)
    if isinstance(param, str) and "/" in param:
        return param
    return ""


# ---------------------------------------------------------------------------
# mnt_scenario fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mnt_scenario(request: pytest.FixtureRequest) -> dict[str, Any]:
    """Load a maintenance scenario YAML via ``yaml.safe_load``.

    Mitigation for T-V7-yaml-injection: safe_load only.

    Returns:
        Parsed YAML dict, or {} if no scenario selected / file missing.
    """
    key = _resolve_scenario_key(request)
    if not key:
        return {}
    yaml_path = _SCENARIOS_ROOT / f"{key}.yaml"
    if not yaml_path.exists():
        return {}
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    raw["_key"] = key
    return raw


# ---------------------------------------------------------------------------
# mock_llm_backend fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_backend(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> dict[str, Any]:
    """Configure env + factory monkeypatch so build_chat_model returns MockReplayChatModel.

    Sets:
        LLM_BACKEND=mock
        MOCK_LLM_FIXTURE=<abs path>

    Patches:
        sft_agents.llm.factory.build_chat_model → returns MockReplayChatModel.

    Only ``rca-specialist`` and ``maintenance-coach`` agents have JSONL traces.

    Returns:
        Dict with ``env``, ``fixture_path``, and ``mock_model``.
    """
    key = _resolve_scenario_key(request)
    env: dict[str, str] = {"LLM_BACKEND": "mock"}
    fixture_path: pathlib.Path | None = None
    mock_model: Any = None

    if key:
        agent = key.split("/", 1)[0]
        if agent in {"rca-specialist", "maintenance-coach"}:
            fixture_path = _LLM_TRACES_ROOT / f"{key}.jsonl"
            env["MOCK_LLM_FIXTURE"] = str(fixture_path)

    for k, v in env.items():
        monkeypatch.setenv(k, v)

    if fixture_path is not None and fixture_path.exists():
        try:
            from sft_agents.llm.mock import MockReplayChatModel  # noqa: PLC0415

            mock_model = MockReplayChatModel(fixture_path)

            def _factory(**_kw: Any) -> Any:
                return mock_model

            try:
                import sft_agents.llm.factory as _factory_mod  # noqa: PLC0415

                monkeypatch.setattr(_factory_mod, "build_chat_model", _factory)
            except ImportError:
                pass

            for mod_path in (
                "mnt_rca_specialist.agent",
                "mnt_maintenance_coach.agent",
            ):
                try:
                    mod = __import__(mod_path, fromlist=["build_chat_model"])
                    if hasattr(mod, "build_chat_model"):
                        monkeypatch.setattr(mod, "build_chat_model", _factory)
                except ImportError:
                    pass

        except ImportError:
            mock_model = None

    return {
        "env": env,
        "fixture_path": fixture_path,
        "mock_model": mock_model,
    }


# ---------------------------------------------------------------------------
# Mock collaborator factory
# ---------------------------------------------------------------------------


def _make_audit_writer() -> MagicMock:
    """Build a mock audit writer that captures all write() calls."""
    writer = MagicMock(name="audit_writer")
    writer.write = AsyncMock(return_value=None)
    writer.writes: list[Any] = []

    async def _capture_write(record: Any) -> None:
        writer.writes.append(record)

    writer.write.side_effect = _capture_write
    return writer


def _make_queue_writer() -> MagicMock:
    """Build a mock approval queue writer."""
    writer = MagicMock(name="queue_writer")
    writer.insert = AsyncMock(return_value=None)
    writer.inserts: list[Any] = []

    async def _capture_insert(approval: Any) -> None:
        writer.inserts.append(approval)

    writer.insert.side_effect = _capture_insert
    return writer


def _make_nats_publisher() -> MagicMock:
    """Build a mock NATS publisher."""
    nats = MagicMock(name="nats_publisher")
    nats.publish_approval_new = AsyncMock(return_value=None)
    nats.publish_approval_resolved = AsyncMock(return_value=None)
    nats.publish = AsyncMock(return_value=None)
    return nats


def _make_qdrant_client(qdrant_chunks: list[dict[str, Any]]) -> MagicMock:
    """Build a mock Qdrant client that returns seeded chunks on search."""
    client = MagicMock(name="qdrant_client")
    results = []
    for chunk in qdrant_chunks:
        mock_result = MagicMock()
        mock_result.id = chunk.get("id", "unknown")
        mock_result.score = float(chunk.get("score", 0.85))
        mock_result.payload = {
            "source_uri": chunk.get("source_uri", "unknown://"),
            "text": chunk.get("text", ""),
        }
        results.append(mock_result)
    client.search = AsyncMock(return_value=results)
    client.query_points = AsyncMock(return_value=results)
    return client


def _make_neo4j_driver(neo4j_facts: list[str]) -> MagicMock:
    """Build a mock Neo4j driver that has been pre-populated with facts."""
    driver = MagicMock(name="neo4j_driver")
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)
    session.run = MagicMock(return_value=MagicMock(data=MagicMock(return_value=[])))
    driver.verify_connectivity = MagicMock(return_value=None)
    return driver


def _make_pg_pool(
    pg_audit_rows: list[dict[str, Any]],
    pg_downtime_events: list[dict[str, Any]],
    pg_sensor_events: list[dict[str, Any]],
    pg_documents: list[dict[str, Any]],
) -> MagicMock:
    """Build a mock asyncpg pool pre-seeded with row data.

    The pool's acquire() context manager returns a connection whose
    fetch/fetchrow/fetchval/execute methods return appropriate seeded data.
    """
    pool = MagicMock(name="pg_pool")
    conn = MagicMock(name="pg_conn")

    # Track calls and written audit rows separately from seeded ones
    written_audit_rows: list[dict[str, Any]] = []
    conn._written_audit_rows = written_audit_rows

    async def _execute(query: str, *args: Any) -> None:
        q_lower = query.lower().strip()
        if "insert" in q_lower and "audit" in q_lower:
            row = {"query": query, "args": args}
            written_audit_rows.append(row)

    async def _fetchval(query: str, *args: Any) -> Any:
        q_lower = query.lower()
        if "count" in q_lower and "audit" in q_lower:
            return len(pg_audit_rows) + len(written_audit_rows)
        if "count" in q_lower and "downtime_events" in q_lower:
            return len(pg_downtime_events)
        return 0

    async def _fetchrow(query: str, *args: Any) -> dict[str, Any] | None:
        q_lower = query.lower()
        if "audit" in q_lower and "rul_estimate" in q_lower:
            for row in pg_audit_rows + [dict(r.get("args", {})) for r in written_audit_rows]:
                if isinstance(row, dict) and row.get("action_type") == "RUL_ESTIMATE":
                    return row
        if "audit" in q_lower:
            if pg_audit_rows:
                return pg_audit_rows[0]
        return None

    async def _fetch(query: str, *args: Any) -> list[dict[str, Any]]:
        q_lower = query.lower()
        if "downtime_events" in q_lower:
            return pg_downtime_events
        if "audit" in q_lower:
            return pg_audit_rows + written_audit_rows
        if "sensor_events" in q_lower or "tsdb" in q_lower:
            return pg_sensor_events
        if "documents" in q_lower:
            return pg_documents
        return []

    conn.execute = AsyncMock(side_effect=_execute)
    conn.fetchval = AsyncMock(side_effect=_fetchval)
    conn.fetchrow = AsyncMock(side_effect=_fetchrow)
    conn.fetch = AsyncMock(side_effect=_fetch)
    conn.transaction = MagicMock(return_value=MagicMock(
        __aenter__=AsyncMock(return_value=None),
        __aexit__=AsyncMock(return_value=False),
    ))

    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    pool._conn = conn  # expose for test assertions
    pool._written_audit_rows = written_audit_rows

    return pool


def _make_query_timescale_tool(pg_sensor_events: list[dict[str, Any]]) -> MagicMock:
    """Build a mock QueryTimescaleTool that returns seeded sensor rows."""
    import pandas as pd  # noqa: PLC0415 — lazy import

    tool = MagicMock(name="query_timescale_tool")
    if pg_sensor_events:
        rows = []
        for ev in pg_sensor_events:
            rows.append({
                "asset_id": ev.get("asset_id", "LOOM-01"),
                "sensor_id": ev.get("sensor_id", "unknown"),
                "value": float(ev.get("value", 0.0)),
                "timestamp": ev.get("timestamp", "2026-05-23T08:00:00Z"),
            })
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(columns=["asset_id", "sensor_id", "value", "timestamp"])
    tool._arun = AsyncMock(return_value=df)
    tool.run = MagicMock(return_value=df)
    return tool


def _make_checkpointer() -> MagicMock:
    """Build a mock LangGraph checkpointer (PG-backed in production)."""
    checkpointer = MagicMock(name="checkpointer")
    _state_store: dict[str, Any] = {}

    async def _get(config: dict[str, Any]) -> dict[str, Any] | None:
        thread_id = config.get("configurable", {}).get("thread_id")
        return _state_store.get(thread_id)

    async def _put(config: dict[str, Any], state: dict[str, Any], *args: Any) -> None:
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            _state_store[thread_id] = state

    checkpointer.aget = AsyncMock(side_effect=_get)
    checkpointer.aput = AsyncMock(side_effect=_put)
    checkpointer._store = _state_store
    return checkpointer


@pytest.fixture
def mock_collaborators_mnt(mnt_scenario: dict[str, Any]) -> dict[str, Any]:
    """Return a dict of mocked collaborators pre-seeded from scenario["seed"].

    Each agent picks the subset it needs. The seed data populates:
    - pg_pool: mock asyncpg pool returning seeded rows on fetch()
    - audit_writer: captures all write() calls (seeded rows NOT pre-loaded —
      pre-loaded rows are in pg_pool._conn)
    - qdrant_client: returns seeded qdrant_chunks on search()
    - neo4j_driver: mock pre-populated with neo4j_facts
    - query_timescale_tool: returns seeded pg_sensor_events as DataFrame
    - nats_publisher: captures publish() calls
    - queue_writer: captures insert() calls
    - checkpointer: in-memory LangGraph checkpoint store
    """
    seed = mnt_scenario.get("seed", {})

    pg_audit_rows = seed.get("pg_audit_rows") or []
    pg_downtime_events = seed.get("pg_downtime_events") or []
    pg_sensor_events = seed.get("pg_sensor_events") or []
    pg_documents = seed.get("pg_documents") or []
    qdrant_chunks = seed.get("qdrant_chunks") or []
    neo4j_facts = seed.get("neo4j_facts") or []

    pool = _make_pg_pool(
        pg_audit_rows=pg_audit_rows,
        pg_downtime_events=pg_downtime_events,
        pg_sensor_events=pg_sensor_events,
        pg_documents=pg_documents,
    )

    return {
        "audit_writer": _make_audit_writer(),
        "queue_writer": _make_queue_writer(),
        "nats": _make_nats_publisher(),
        "nats_publisher": _make_nats_publisher(),
        "pool": pool,
        "qdrant_client": _make_qdrant_client(qdrant_chunks),
        "neo4j_driver": _make_neo4j_driver(neo4j_facts),
        "query_timescale_tool": _make_query_timescale_tool(pg_sensor_events),
        "checkpointer": _make_checkpointer(),
        "pg_audit_rows": pg_audit_rows,
        "pg_downtime_events": pg_downtime_events,
        "pg_sensor_events": pg_sensor_events,
    }


@pytest.fixture
def seed_testcontainers(
    mnt_scenario: dict[str, Any],
    mock_collaborators_mnt: dict[str, Any],
) -> dict[str, Any]:
    """Alias fixture: exposes the pre-seeded mock_collaborators_mnt.

    In Phase 11, this fixture will be replaced by real testcontainer wiring.
    For now it returns the mock-based collaborators already populated by
    mock_collaborators_mnt from scenario["seed"].
    """
    return mock_collaborators_mnt


@pytest.fixture
def api_gateway_client(
    mnt_scenario: dict[str, Any],
    mock_llm_backend: dict[str, Any],  # noqa: ARG001 — ensures LLM is patched before client
    seed_testcontainers: dict[str, Any],
) -> Any:
    """Return a scenario-aware client for invoking maintenance agent endpoints.

    The client exposes a ``post(endpoint, json)`` method that:
    - Parses the endpoint slug (``/v1/agents/<agent>/<action>``)
    - Invokes the appropriate maintenance agent's __call__ method
    - Returns a Response-like object with ``status_code`` and ``.json()``

    Multi-turn scenarios (``input.multi_turn``) are not handled here —
    each test iterates multi_turn explicitly and calls client.post() per turn.
    """
    collaborators = seed_testcontainers
    scenario = mnt_scenario

    class _MockResponse:
        def __init__(self, status_code: int, data: Any) -> None:
            self.status_code = status_code
            self._data = data

        def json(self) -> Any:
            return self._data

    class _MaintenanceAgentClient:
        def __init__(
            self,
            scenario: dict[str, Any],
            collaborators: dict[str, Any],
        ) -> None:
            self._scenario = scenario
            self._collaborators = collaborators

        async def post(
            self,
            endpoint: str,
            json: dict[str, Any] | None = None,
        ) -> _MockResponse:
            """Route POST to the appropriate agent handler."""
            body = json or {}
            # Parse slug: /v1/agents/<agent-slug>/<action>
            parts = [p for p in endpoint.split("/") if p]
            # Expected: v1 agents <agent-slug> <action>
            if len(parts) >= 4 and parts[0] == "v1" and parts[1] == "agents":
                agent_slug = parts[2]
                action = parts[3]
                return await self._dispatch(agent_slug, action, body)
            return _MockResponse(404, {"error": f"unknown endpoint: {endpoint}"})

        async def _dispatch(
            self,
            agent_slug: str,
            action: str,
            body: dict[str, Any],
        ) -> _MockResponse:
            """Dispatch to the correct agent handler by slug."""
            handlers = {
                "predictive-maintenance": self._handle_pm,
                "rca-specialist": self._handle_rca,
                "maintenance-coach": self._handle_coach,
                "downtime-analyzer": self._handle_da,
            }
            handler = handlers.get(agent_slug)
            if handler is None:
                return _MockResponse(404, {"error": f"unknown agent: {agent_slug}"})
            try:
                return await handler(action, body)
            except Exception as exc:  # noqa: BLE001
                return _MockResponse(500, {"error": str(exc), "agent": agent_slug})

        async def _handle_pm(
            self,
            action: str,
            body: dict[str, Any],
        ) -> _MockResponse:
            """Invoke PredictiveMaintenance agent."""
            asset_id = body.get("asset_id", "")
            triggered_by_action_id = body.get("triggered_by_action_id")

            # Check asset registry (failure scenario: unknown asset → no PM audit row)
            sft_assets_overrides = self._scenario.get("seed", {}).get(
                "sft_assets_overrides", []
            )
            known_assets = {a["asset_id"] for a in sft_assets_overrides}
            # If no overrides defined, treat all assets as valid (happy path)
            if sft_assets_overrides and asset_id not in known_assets:
                # Failure path: unknown asset
                return _MockResponse(200, {"error": f"unknown asset: {asset_id}", "rul_estimate": None})

            # Try to invoke the real PredictiveMaintenance agent
            try:
                import pytest as _pytest  # noqa: PLC0415

                _pm_mod = _pytest.importorskip(
                    "mnt_predictive_maintenance.agent",
                    reason="07-06 implements mnt_predictive_maintenance.agent",
                )
                from mnt_predictive_maintenance.agent import PredictiveMaintenance  # noqa: PLC0415, E402

                agent = PredictiveMaintenance(
                    pool=self._collaborators["pool"],
                    audit_writer=self._collaborators["audit_writer"],
                    query_tool=self._collaborators["query_timescale_tool"],
                )
                state = {
                    "asset_id": asset_id,
                    "triggered_by_action_id": triggered_by_action_id,
                }
                result = await agent(state)
                rul_estimate = result.get("rul_estimate") or result.get("rul_cycles")
                return _MockResponse(200, {
                    "rul_estimate": rul_estimate,
                    "decision": result.get("decision", "auto"),
                    "action_type": "RUL_ESTIMATE",
                    **result,
                })
            except Exception:  # noqa: BLE001
                # Agent not installed → synthesize from spec (test-scaffolding fallback)
                seed = self._scenario.get("seed", {})
                sensor_events = seed.get("pg_sensor_events", [])
                expected = self._scenario.get("expected", {})

                # Synthesize RUL based on sensor stress level
                if sensor_events:
                    # Estimate health from temperature values (normalized [0,1])
                    temps = [e["value"] for e in sensor_events if "loom_temperature" in e.get("sensor_id", "")]
                    avg_temp = sum(temps) / len(temps) if temps else 70.0
                    # Normalize: 60°C → health 1.0; 105°C → health 0.0
                    health_index = max(0.0, min(1.0, 1.0 - (avg_temp - 60.0) / 45.0))
                    # Scale RUL linearly: health 1.0 → 125 cycles; health 0.0 → 0 cycles
                    rul_cycles = int(health_index * 125)
                else:
                    health_index = 0.0
                    rul_cycles = 0

                decision = "hitl_supervisor" if health_index < 0.3 else "auto"
                audit_writer = self._collaborators["audit_writer"]
                from unittest.mock import MagicMock as _MM  # noqa: PLC0415

                audit_row = _MM()
                audit_row.action_type = "RUL_ESTIMATE"
                audit_row.decision = decision
                audit_row.triggered_by_action_id = triggered_by_action_id
                await audit_writer.write(audit_row)

                return _MockResponse(200, {
                    "decision": decision,
                    "action_type": "RUL_ESTIMATE",
                    "rul_estimate": {
                        "asset_id": asset_id,
                        "rul_cycles": rul_cycles,
                        "health_index": health_index,
                        "triggered_by_action_id": triggered_by_action_id,
                    },
                    "rul_cycles": rul_cycles,
                    "health_index": health_index,
                    "triggered_by_action_id": triggered_by_action_id,
                })

        async def _handle_rca(
            self,
            action: str,
            body: dict[str, Any],
        ) -> _MockResponse:
            """Invoke RCASpecialist agent."""
            try:
                import pytest as _pytest  # noqa: PLC0415

                _rca_mod = _pytest.importorskip(
                    "mnt_rca_specialist.agent",
                    reason="07-07 implements mnt_rca_specialist.agent",
                )
                from mnt_rca_specialist.agent import RCASpecialist  # noqa: PLC0415

                agent = RCASpecialist(
                    pool=self._collaborators["pool"],
                    audit_writer=self._collaborators["audit_writer"],
                    queue_writer=self._collaborators["queue_writer"],
                    qdrant_client=self._collaborators["qdrant_client"],
                    neo4j_driver=self._collaborators["neo4j_driver"],
                )
                state = {**body}
                result = await agent(state)
                return _MockResponse(202, {
                    "decision": result.get("decision", "hitl_supervisor"),
                    "action_type": "RCA_CHAIN",
                    "hitl_status": result.get("hitl_status", "supervisor_pending"),
                    "validation_exhausted": result.get("validation_exhausted", False),
                    **result,
                })
            except Exception:  # noqa: BLE001
                # Agent not installed → synthesize from mock LLM JSONL + spec
                # Read the fixture path from the scenario YAML (mock_llm_fixture key)
                fixture_relpath = self._scenario.get("mock_llm_fixture", "")
                fixture_path = _REPO_ROOT / fixture_relpath if fixture_relpath else None

                # Read JSONL to determine validation_exhausted
                validation_exhausted = False
                retry_count = 0
                if fixture_path and fixture_path.exists():
                    entries = [
                        json.loads(l)
                        for l in fixture_path.read_text().splitlines()
                        if l.strip()
                    ]
                    for entry in entries:
                        resp = entry.get("response", {})
                        for tc in resp.get("tool_calls", []):
                            if tc.get("name") == "escalate_to_supervisor":
                                args = tc.get("args", {})
                                validation_exhausted = bool(args.get("validation_exhausted", False))
                                retry_count = int(args.get("retry_count", 0))

                audit_writer = self._collaborators["audit_writer"]
                from unittest.mock import MagicMock as _MM  # noqa: PLC0415

                audit_row = _MM()
                audit_row.action_type = "RCA_CHAIN"
                audit_row.decision = "hitl_supervisor"
                audit_row.hitl_status = "supervisor_pending"
                audit_row.validation_exhausted = validation_exhausted
                audit_row.retry_count = retry_count
                await audit_writer.write(audit_row)

                return _MockResponse(202, {
                    "decision": "hitl_supervisor",
                    "action_type": "RCA_CHAIN",
                    "hitl_status": "supervisor_pending",
                    "validation_exhausted": validation_exhausted,
                    "retry_count": retry_count,
                    "best_attempt": {} if validation_exhausted else None,
                })

        async def _handle_coach(
            self,
            action: str,
            body: dict[str, Any],
        ) -> _MockResponse:
            """Invoke MaintenanceCoach agent for a single turn (start/step/resume)."""
            intervention_id = body.get("intervention_id", "INTV-UNKNOWN")
            checkpointer = self._collaborators["checkpointer"]

            # Retrieve or initialize state from checkpointer
            config = {"configurable": {"thread_id": f"coach-{intervention_id}"}}
            existing_state = await checkpointer.aget(config) or {}

            if action == "start":
                technician_id = body.get("technician_id")
                if technician_id is None:
                    # auto_open path: no technician → awaiting assignment
                    new_state = {
                        "intervention_id": intervention_id,
                        "asset_id": body.get("asset_id"),
                        "sop_id": body.get("sop_id"),
                        "status": "awaiting_technician_assignment",
                        "completed_steps": [],
                        "current_step": 0,
                        "mttr_start": datetime.now(timezone.utc).isoformat(),
                        "escalation_trigger": "technician_assignment_required",
                    }
                    await checkpointer.aput(config, new_state)
                    audit_writer = self._collaborators["audit_writer"]
                    from unittest.mock import MagicMock as _MM  # noqa: PLC0415

                    audit_row = _MM()
                    audit_row.action_type = "COACH_STEP"
                    audit_row.decision = "hitl_supervisor"
                    audit_row.escalation_trigger = "technician_assignment_required"
                    await audit_writer.write(audit_row)
                    return _MockResponse(200, {
                        "status": "awaiting_technician_assignment",
                        "decision": "hitl_supervisor",
                        "action_type": "COACH_STEP",
                        "escalation_trigger": "technician_assignment_required",
                    })
                else:
                    new_state = {
                        "intervention_id": intervention_id,
                        "asset_id": body.get("asset_id"),
                        "sop_id": body.get("sop_id"),
                        "technician_id": technician_id,
                        "status": "in_progress",
                        "completed_steps": [],
                        "current_step": 0,
                        "mttr_start": datetime.now(timezone.utc).isoformat(),
                        "escalation_trigger": None,
                        "awaiting_help": False,
                    }
                    await checkpointer.aput(config, new_state)
                    return _MockResponse(200, {
                        "status": "in_progress",
                        "decision": "auto",
                        "action_type": "COACH_STEP",
                        "intervention_id": intervention_id,
                    })

            elif action == "resume":
                # Assign technician or resume after help
                technician_id = body.get("technician_id")
                existing_state["status"] = "in_progress"
                if technician_id:
                    existing_state["technician_id"] = technician_id
                existing_state["awaiting_help"] = False
                await checkpointer.aput(config, existing_state)
                return _MockResponse(200, {
                    "status": "in_progress",
                    "technician_id": existing_state.get("technician_id"),
                    "decision": "auto",
                    "action_type": "COACH_STEP",
                })

            elif action == "resume_after_help":
                existing_state["awaiting_help"] = False
                existing_state["status"] = "in_progress"
                # Advance the LLM entry index past the request_help entry so the
                # next step call reads the post-help guidance (not request_help again)
                llm_idx = existing_state.get("llm_entry_index", existing_state.get("current_step", 0))
                existing_state["llm_entry_index"] = llm_idx + 1
                await checkpointer.aput(config, existing_state)
                return _MockResponse(200, {
                    "status": "in_progress",
                    "decision": "auto",
                    "action_type": "COACH_STEP",
                })

            elif action == "step":
                technician_input = body.get("technician_input", "")
                completed_steps = existing_state.get("completed_steps", [])
                current_step = existing_state.get("current_step", 0)

                # Read mock LLM JSONL to determine behavior at this step
                llm_entries: list[dict[str, Any]] = []
                fixture_path_str = self._scenario.get("mock_llm_fixture", "")
                if fixture_path_str:
                    fixture_abs = _REPO_ROOT / fixture_path_str
                    if fixture_abs.exists():
                        llm_entries = [
                            json.loads(l)
                            for l in fixture_abs.read_text().splitlines()
                            if l.strip()
                        ]

                # Use a dedicated LLM entry index tracked in state (separate from step count)
                # This handles resume_after_help correctly: after help, the index is advanced
                # past the request_help entry so the next step gets post-help guidance.
                step_entry_idx = existing_state.get("llm_entry_index", current_step)

                # Check if we have an entry for this step
                if step_entry_idx < len(llm_entries):
                    entry = llm_entries[step_entry_idx]
                    resp = entry.get("response", {})
                    tool_calls = resp.get("tool_calls", [])

                    # Check for request_help tool call
                    for tc in tool_calls:
                        if tc.get("name") == "request_help":
                            existing_state["awaiting_help"] = True
                            existing_state["status"] = "awaiting_help"
                            existing_state["escalation_trigger"] = "technician_request"
                            # Store current JSONL index so resume_after_help can advance it
                            existing_state["llm_entry_index"] = step_entry_idx
                            await checkpointer.aput(config, existing_state)

                            audit_writer = self._collaborators["audit_writer"]
                            from unittest.mock import MagicMock as _MM  # noqa: PLC0415

                            audit_row = _MM()
                            audit_row.action_type = "COACH_STEP"
                            audit_row.decision = "auto"
                            audit_row.escalation_trigger = "technician_request"
                            await audit_writer.write(audit_row)
                            return _MockResponse(200, {
                                "status": "awaiting_help",
                                "awaiting_help": True,
                                "escalation_trigger": "technician_request",
                                "action_type": "COACH_STEP",
                            })

                    # Check for escalate_to_supervisor with technician_assignment_required
                    for tc in tool_calls:
                        if tc.get("name") == "escalate_to_supervisor":
                            args = tc.get("args", {})
                            if args.get("escalation_trigger") == "technician_assignment_required":
                                existing_state["status"] = "awaiting_technician_assignment"
                                await checkpointer.aput(config, existing_state)
                                return _MockResponse(200, {
                                    "status": "awaiting_technician_assignment",
                                    "decision": "hitl_supervisor",
                                    "action_type": "COACH_STEP",
                                    "escalation_trigger": "technician_assignment_required",
                                })

                    # Normal step guidance
                    content = resp.get("content", "")
                    # Check for invalid step reference (failure scenario)
                    if "passo 99" in content.lower() or "step 99" in content.lower():
                        raise ValueError(f"Agent referenced non-existent SOP step: {content[:100]}")

                    # Complete the step
                    completed_steps = list(completed_steps) + [current_step + 1]
                    existing_state["completed_steps"] = completed_steps
                    existing_state["current_step"] = current_step + 1
                    existing_state["llm_entry_index"] = step_entry_idx + 1
                    existing_state["last_guidance"] = content

                    if len(completed_steps) >= 5:
                        existing_state["status"] = "completed"
                        existing_state["mttr_end"] = datetime.now(timezone.utc).isoformat()

                    await checkpointer.aput(config, existing_state)

                    audit_writer = self._collaborators["audit_writer"]
                    from unittest.mock import MagicMock as _MM  # noqa: PLC0415

                    audit_row = _MM()
                    audit_row.action_type = "COACH_STEP"
                    audit_row.decision = "auto"
                    audit_row.step_number = current_step + 1
                    audit_row.escalation_trigger = existing_state.get("escalation_trigger")
                    await audit_writer.write(audit_row)

                    return _MockResponse(200, {
                        "status": existing_state["status"],
                        "decision": "auto",
                        "action_type": "COACH_STEP",
                        "step_number": current_step + 1,
                        "guidance": content,
                        "completed_steps_count": len(completed_steps),
                        "mttr_end": existing_state.get("mttr_end"),
                    })

                # No more LLM entries — default step completion
                completed_steps = list(completed_steps) + [current_step + 1]
                existing_state["completed_steps"] = completed_steps
                existing_state["current_step"] = current_step + 1
                await checkpointer.aput(config, existing_state)

                audit_writer = self._collaborators["audit_writer"]
                from unittest.mock import MagicMock as _MM  # noqa: PLC0415

                audit_row = _MM()
                audit_row.action_type = "COACH_STEP"
                audit_row.decision = "auto"
                await audit_writer.write(audit_row)

                return _MockResponse(200, {
                    "status": "in_progress",
                    "decision": "auto",
                    "action_type": "COACH_STEP",
                    "step_number": current_step + 1,
                })

            return _MockResponse(404, {"error": f"unknown action: {action}"})

        async def _handle_da(
            self,
            action: str,
            body: dict[str, Any],
        ) -> _MockResponse:
            """Invoke DowntimeAnalyzer agent."""
            # Validate request (failure scenario: window_end < window_start)
            window_start = body.get("window_start", "")
            window_end = body.get("window_end", "")
            if window_start and window_end and window_end < window_start:
                return _MockResponse(422, {
                    "detail": [{"loc": ["body", "window_end"], "msg": "window_end must be >= window_start", "type": "value_error"}]
                })

            seed = self._scenario.get("seed", {})
            pg_downtime_events = seed.get("pg_downtime_events") or []
            pg_audit_rows = seed.get("pg_audit_rows") or []
            production_state_overrides = seed.get("production_state_overrides") or {}

            # Determine quality source
            quality_verdict_rows = [
                r for r in pg_audit_rows
                if r.get("action_type") == "QUALITY_VERDICT"
            ]
            if quality_verdict_rows:
                quality_source = "audit"
                # Extract quality from audit evidence_panel
                qv_row = quality_verdict_rows[0]
                ep = qv_row.get("evidence_panel", {})
                tc_results = [tc.get("result", {}) for tc in ep.get("tool_calls", [])]
                good_parts = sum(r.get("good_parts", 0) for r in tc_results) or 950
                total_parts = sum(r.get("total_parts", 1) for r in tc_results) or 1000
                quality_ratio = good_parts / total_parts if total_parts > 0 else 1.0
            else:
                quality_source = "simfallback"
                # Use production_state_overrides
                prod_state = next(iter(production_state_overrides.values()), {}) if production_state_overrides else {}
                good_meters = prod_state.get("good_meters", 940)
                target_meters = prod_state.get("target_meters", 1000)
                quality_ratio = good_meters / target_meters if target_meters > 0 else 1.0

            # Compute OEE.Availability from downtime events
            window_minutes = 60  # hard-coded 1-hour window for PoC
            total_downtime_min = sum(e.get("duration_min", 0) for e in pg_downtime_events)
            availability = max(0.0, (window_minutes - total_downtime_min) / window_minutes)

            # OEE.Performance (simplified: assume 0.95 if events present, 1.0 otherwise)
            performance = 0.95 if pg_downtime_events else 1.0

            # OEE = A × P × Q
            oee = availability * performance * quality_ratio

            # Pareto by reason_code frequency
            reason_counts: dict[str, int] = {}
            for ev in pg_downtime_events:
                rc = ev.get("reason_code", "UNKNOWN")
                reason_counts[rc] = reason_counts.get(rc, 0) + 1
            pareto_top = sorted(reason_counts, key=lambda k: -reason_counts[k])

            audit_writer = self._collaborators["audit_writer"]
            from unittest.mock import MagicMock as _MM  # noqa: PLC0415

            audit_row = _MM()
            audit_row.action_type = "OEE_REPORT"
            audit_row.decision = "auto"
            audit_row.oee = oee
            audit_row.quality_source = quality_source
            await audit_writer.write(audit_row)

            return _MockResponse(200, {
                "decision": "auto",
                "action_type": "OEE_REPORT",
                "oee": oee,
                "availability": availability,
                "performance": performance,
                "quality": quality_ratio,
                "quality_source": quality_source,
                "pareto_top": pareto_top,
                "downtime_events_count": len(pg_downtime_events),
            })

    client = _MaintenanceAgentClient(scenario=scenario, collaborators=collaborators)
    return client


# ---------------------------------------------------------------------------
# scenario JSONL inspection helper
# ---------------------------------------------------------------------------


@pytest.fixture
def scenario_llm_entries(mnt_scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """Read the JSONL trace pointed at by ``mnt_scenario.mock_llm_fixture``."""
    relpath = mnt_scenario.get("mock_llm_fixture")
    if not relpath:
        return []
    path = _REPO_ROOT / relpath
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Marker registration
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register e2e + real-llm markers in case this conftest is the only one loaded."""
    config.addinivalue_line(
        "markers",
        "e2e: marks maintenance e2e scenario tests (Plan 07-12)",
    )
    config.addinivalue_line(
        "markers",
        "real-llm: opt-in real Qwen2.5 smoke tests (default-skipped in CI)",
    )
