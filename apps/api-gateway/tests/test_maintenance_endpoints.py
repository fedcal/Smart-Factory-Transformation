"""Unit tests for maintenance-cluster HTTP endpoints (Plan 07-10 — Task 1 RED phase).

Covers 6 maintenance agent endpoints (MNT-01..MNT-04):
    POST /v1/agents/predictive-maintenance/score
    POST /v1/agents/rca-specialist/analyze
    POST /v1/agents/maintenance-coach/start
    POST /v1/agents/maintenance-coach/step
    POST /v1/agents/maintenance-coach/resume
    POST /v1/agents/downtime-analyzer/report

All 16 tests RED via ImportError (request models not yet defined) or 404 (router
not yet registered in build_app).

Pattern mirrors test_ops_endpoints.py: fixtures from conftest.py
(app_with_mocks / client) + AsyncMock supervisor_graph + monkeypatch for
Langfuse span names.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc

_VALID_WINDOW_START = datetime(2026, 5, 1, 6, 0, tzinfo=UTC).isoformat()
_VALID_WINDOW_END = datetime(2026, 5, 1, 14, 0, tzinfo=UTC).isoformat()


def _make_oee_report_result() -> dict:
    """Return a minimal valid OEEReport-shaped dict for supervisor mock return value."""
    return {
        "window_start": _VALID_WINDOW_START,
        "window_end": _VALID_WINDOW_END,
        "availability": 0.90,
        "performance": 0.95,
        "quality": 0.98,
        "oee": round(0.90 * 0.95 * 0.98, 9),
        "by_asset": None,
        "pareto": [],
        "report_id": "550e8400-e29b-41d4-a716-446655440000",
        "generated_at": datetime(2026, 5, 1, 14, 1, tzinfo=UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# PredictiveMaintenance — 3 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_pm_score_valid_returns_200_and_invokes_supervisor(
    client, app_with_mocks
) -> None:
    """POST /v1/agents/predictive-maintenance/score invokes supervisor with correct state."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"rul_estimate": None, "messages": []}
    )

    body = {
        "asset_id": "LOOM-01",
        "triggered_by_action_id": "abc-123",
        "user_roles": ["technician"],
    }
    response = await client.post(
        "/v1/agents/predictive-maintenance/score", json=body
    )
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]
    assert state_arg["target_agent"] == "predictive-maintenance"
    assert state_arg["asset_id"] == "LOOM-01"
    assert state_arg["triggered_by_action_id"] == "abc-123"
    assert state_arg["user_roles"] == ["technician"]
    assert config["recursion_limit"] == 5
    assert config["configurable"]["thread_id"].startswith(
        "maintenance.predictive-maintenance."
    )

    payload = response.json()
    assert "thread_id" in payload
    assert payload["thread_id"].startswith("maintenance.predictive-maintenance.")
    assert "rul_estimate" in payload


@pytest.mark.asyncio
async def test_post_pm_score_missing_asset_id_422(client, app_with_mocks) -> None:
    """Missing asset_id → 422 Unprocessable Entity."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/predictive-maintenance/score",
        json={"triggered_by_action_id": "abc", "user_roles": ["technician"]},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_pm_score_empty_user_roles_422(client, app_with_mocks) -> None:
    """Empty user_roles list → 422 (min_length=1 constraint)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/predictive-maintenance/score",
        json={"asset_id": "LOOM-01", "user_roles": []},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# RCASpecialist — 3 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_rca_analyze_valid_returns_202(client, app_with_mocks) -> None:
    """POST /v1/agents/rca-specialist/analyze → 202 with hitl_status='supervisor_pending'."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"chain_id": None, "messages": []}
    )

    body = {
        "problem_statement": "Il telaio LOOM-01 si ferma ogni 30 minuti con errore T01.",
        "user_roles": ["maintenance_tech"],
        "lang": "it",
    }
    response = await client.post("/v1/agents/rca-specialist/analyze", json=body)
    assert response.status_code == 202, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    assert state_arg["target_agent"] == "rca-specialist"
    assert state_arg["user_roles"] == ["maintenance_tech"]

    payload = response.json()
    assert payload["hitl_status"] == "supervisor_pending"
    assert "thread_id" in payload


@pytest.mark.asyncio
async def test_post_rca_analyze_short_problem_statement_422(
    client, app_with_mocks
) -> None:
    """problem_statement shorter than 10 chars → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/rca-specialist/analyze",
        json={"problem_statement": "too short", "user_roles": ["tech"]},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_rca_analyze_bad_lang_422(client, app_with_mocks) -> None:
    """lang='fr' → 422 (Literal['it','en'] constraint)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/rca-specialist/analyze",
        json={
            "problem_statement": "Problema con il telaio LOOM-01.",
            "user_roles": ["tech"],
            "lang": "fr",
        },
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# MaintenanceCoach — 8 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_coach_start_generates_intervention_id_when_absent(
    client, app_with_mocks
) -> None:
    """POST /start without intervention_id → server generates UUID4; thread_id=coach-<uuid>."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "intervention_id": None,
            "current_step": 0,
            "guidance_md": "Inizia con il passo 1.",
            "state": "in_progress",
        }
    )

    body = {
        "asset_id": "LOOM-01",
        "sop_id": "SOP-LOOM-001",
        "technician_id": "TECH-01",
        "user_roles": ["technician"],
    }
    response = await client.post("/v1/agents/maintenance-coach/start", json=body)
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]
    thread_id = config["configurable"]["thread_id"]
    # Server must generate an intervention_id in the thread_id
    assert thread_id.startswith("coach-")
    generated_id = thread_id[len("coach-"):]
    assert len(generated_id) > 0

    payload = response.json()
    assert "intervention_id" in payload


@pytest.mark.asyncio
async def test_post_coach_start_with_explicit_intervention_id(
    client, app_with_mocks
) -> None:
    """POST /start with explicit intervention_id='INTV-001' → thread_id=coach-INTV-001."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "intervention_id": "INTV-001",
            "current_step": 0,
            "guidance_md": "Passo 1: Verifica tensione.",
            "state": "in_progress",
        }
    )

    body = {
        "intervention_id": "INTV-001",
        "asset_id": "LOOM-01",
        "sop_id": "SOP-LOOM-001",
        "technician_id": "TECH-01",
        "user_roles": ["technician"],
    }
    response = await client.post("/v1/agents/maintenance-coach/start", json=body)
    assert response.status_code == 200, response.text

    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]
    assert config["configurable"]["thread_id"] == "coach-INTV-001"


@pytest.mark.asyncio
async def test_post_coach_start_without_technician_id_returns_awaiting_assignment(
    client, app_with_mocks
) -> None:
    """POST /start without technician_id → 200 with state='awaiting_technician_assignment'."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "intervention_id": "INTV-002",
            "current_step": 0,
            "guidance_md": "In attesa di assegnazione tecnico.",
            "state": "awaiting_technician_assignment",
            "technician_id": None,
        }
    )

    body = {
        "intervention_id": "INTV-002",
        "asset_id": "LOOM-02",
        "sop_id": "SOP-LOOM-001",
        "user_roles": ["maintenance_supervisor"],
    }
    response = await client.post("/v1/agents/maintenance-coach/start", json=body)
    assert response.status_code == 200, response.text

    # Supervisor invoked once
    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    # technician_id must be None in state passed to supervisor
    assert state_arg.get("technician_id") is None

    payload = response.json()
    assert payload["state"] == "awaiting_technician_assignment"


@pytest.mark.asyncio
async def test_post_coach_step_resumes_existing_thread(
    client, app_with_mocks
) -> None:
    """POST /step resumes existing thread; thread_id=coach-INTV-001; span tagged correctly."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "intervention_id": "INTV-001",
            "current_step": 1,
            "guidance_md": "Passo 2: Sostituisci il cuscinetto.",
            "state": "in_progress",
        }
    )

    captured_tags: list[list[str]] = []

    def _fake_build_invocation_config(
        thread_id: str,
        user_id=None,
        tags=None,
        recursion_limit: int = 25,
    ):
        captured_tags.append(list(tags or []))
        return {
            "configurable": {"thread_id": thread_id},
            "callbacks": [],
            "metadata": {"langfuse_session_id": thread_id},
            "recursion_limit": recursion_limit,
        }

    with patch(
        "svc_api_gateway.routers.maintenance_agents.build_invocation_config",
        side_effect=_fake_build_invocation_config,
    ):
        response = await client.post(
            "/v1/agents/maintenance-coach/step",
            json={"intervention_id": "INTV-001", "technician_input": "completato"},
        )
    assert response.status_code == 200, response.text

    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]
    assert config["configurable"]["thread_id"] == "coach-INTV-001"
    assert "agent.maintenance-coach.step" in captured_tags[0]


@pytest.mark.asyncio
async def test_post_coach_step_returns_409_when_technician_unassigned(
    client, app_with_mocks
) -> None:
    """POST /step when checkpointer shows technician_id=None → 409 without invoking supervisor."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    # Stub checkpointer returning state with technician_id=None
    cp = app_with_mocks.state.checkpointer
    cp.aget_tuple = AsyncMock(
        return_value=type(
            "_FakeCheckpointTuple",
            (),
            {
                "config": {},
                "checkpoint": {"channel_values": {"technician_id": None}},
                "metadata": {},
                "parent_config": None,
            },
        )()
    )

    response = await client.post(
        "/v1/agents/maintenance-coach/step",
        json={"intervention_id": "INTV-002", "technician_input": "pronto"},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["error"] == "technician_assignment_required"
    assert body["intervention_id"] == "INTV-002"
    # Supervisor must NOT have been invoked
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_coach_step_idempotency_key_caches_response(
    client, app_with_mocks
) -> None:
    """Same Idempotency-Key + body twice → second call returns cached response."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "intervention_id": "INTV-001",
            "current_step": 1,
            "guidance_md": "Passo 2.",
            "state": "in_progress",
        }
    )

    # Make checkpointer return non-null state with technician_id set
    cp = app_with_mocks.state.checkpointer
    cp.aget_tuple = AsyncMock(
        return_value=type(
            "_FakeCheckpointTuple",
            (),
            {
                "config": {},
                "checkpoint": {"channel_values": {"technician_id": "TECH-01"}},
                "metadata": {},
                "parent_config": None,
            },
        )()
    )

    headers = {"Idempotency-Key": "step-idempotent-001"}
    body = {"intervention_id": "INTV-001", "technician_input": "completato"}

    r1 = await client.post(
        "/v1/agents/maintenance-coach/step", json=body, headers=headers
    )
    assert r1.status_code == 200, r1.text

    r2 = await client.post(
        "/v1/agents/maintenance-coach/step", json=body, headers=headers
    )
    assert r2.status_code == 200, r2.text
    assert r2.json() == r1.json()

    # Second call must NOT re-invoke supervisor (cache hit)
    assert graph.ainvoke.await_count == 1


@pytest.mark.asyncio
async def test_post_coach_resume_after_help(client, app_with_mocks) -> None:
    """POST /resume with supervisor_input (post request_help) → supervisor invoked."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "intervention_id": "INTV-001",
            "current_step": 1,
            "guidance_md": "Supervisore ha approvato. Continua con passo 2.",
            "state": "in_progress",
        }
    )

    captured_tags: list[list[str]] = []

    def _fake_build_invocation_config(
        thread_id: str,
        user_id=None,
        tags=None,
        recursion_limit: int = 25,
    ):
        captured_tags.append(list(tags or []))
        return {
            "configurable": {"thread_id": thread_id},
            "callbacks": [],
            "metadata": {"langfuse_session_id": thread_id},
            "recursion_limit": recursion_limit,
        }

    with patch(
        "svc_api_gateway.routers.maintenance_agents.build_invocation_config",
        side_effect=_fake_build_invocation_config,
    ):
        response = await client.post(
            "/v1/agents/maintenance-coach/resume",
            json={
                "intervention_id": "INTV-001",
                "supervisor_input": "Vai avanti, ho verificato.",
                "supervisor_id": "SUP-7",
            },
        )
    assert response.status_code == 200, response.text

    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]
    assert config["configurable"]["thread_id"] == "coach-INTV-001"
    assert "agent.maintenance-coach.resume" in captured_tags[0]


@pytest.mark.asyncio
async def test_post_coach_resume_assigns_technician_id(
    client, app_with_mocks
) -> None:
    """POST /resume with technician_id (post technician_assignment_required) → 200."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "intervention_id": "INTV-002",
            "current_step": 0,
            "guidance_md": "Tecnico assegnato. Inizia passo 1.",
            "state": "in_progress",
            "technician_id": "TECH-42",
        }
    )

    response = await client.post(
        "/v1/agents/maintenance-coach/resume",
        json={
            "intervention_id": "INTV-002",
            "technician_id": "TECH-42",
            "supervisor_id": "SUP-7",
        },
    )
    assert response.status_code == 200, response.text

    # Verify supervisor was invoked with technician_id update
    state_arg = graph.ainvoke.call_args.args[0]
    # The state should have technician_id populated (or command carries it)
    assert state_arg.get("technician_id") == "TECH-42" or (
        "technician_id" in str(state_arg)
    )


@pytest.mark.asyncio
async def test_post_coach_resume_422_when_neither_input_nor_technician(
    client, app_with_mocks
) -> None:
    """POST /resume with neither supervisor_input nor technician_id → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/maintenance-coach/resume",
        json={
            "intervention_id": "INTV-001",
            "supervisor_id": "SUP-7",
        },
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# DowntimeAnalyzer — 3 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_da_report_valid_returns_200_and_oee_report(
    client, app_with_mocks
) -> None:
    """POST /v1/agents/downtime-analyzer/report → 200 with OEEReport-shaped body."""
    from mnt_downtime_analyzer.models import OEEReport

    graph = app_with_mocks.state.supervisor_graph
    oee_data = _make_oee_report_result()
    graph.ainvoke = AsyncMock(return_value={**oee_data})

    body = {
        "window_start": _VALID_WINDOW_START,
        "window_end": _VALID_WINDOW_END,
        "by_asset": False,
        "top_n_pareto": 5,
    }
    response = await client.post(
        "/v1/agents/downtime-analyzer/report", json=body
    )
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    assert state_arg["target_agent"] == "downtime-analyzer"

    # Parse response into OEEReport — no ValidationError means schema matches
    OEEReport.model_validate(response.json())


@pytest.mark.asyncio
async def test_post_da_report_inverted_window_422(client, app_with_mocks) -> None:
    """window_end < window_start → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/downtime-analyzer/report",
        json={
            "window_start": _VALID_WINDOW_END,
            "window_end": _VALID_WINDOW_START,
            "by_asset": False,
            "top_n_pareto": 5,
        },
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_da_report_top_n_overflow_422(client, app_with_mocks) -> None:
    """top_n_pareto=101 → 422 (le=100 constraint)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/downtime-analyzer/report",
        json={
            "window_start": _VALID_WINDOW_START,
            "window_end": _VALID_WINDOW_END,
            "by_asset": False,
            "top_n_pareto": 101,
        },
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# Cross-cutting — 2 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_endpoints_propagate_user_roles_to_state(
    client, app_with_mocks
) -> None:
    """PM + RCA + Coach.start all propagate user_roles into supervisor state dict."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"messages": [], "chain_id": None, "current_step": 0,
                      "guidance_md": "ok", "state": "in_progress",
                      "intervention_id": "INTV-777"}
    )

    # PM
    await client.post(
        "/v1/agents/predictive-maintenance/score",
        json={"asset_id": "LOOM-01", "user_roles": ["technician"]},
    )
    pm_state = graph.ainvoke.call_args_list[0].args[0]
    assert pm_state.get("user_roles") == ["technician"]

    # RCA
    await client.post(
        "/v1/agents/rca-specialist/analyze",
        json={
            "problem_statement": "Il telaio si ferma ogni ora.",
            "user_roles": ["maintenance_lead"],
        },
    )
    rca_state = graph.ainvoke.call_args_list[1].args[0]
    assert rca_state.get("user_roles") == ["maintenance_lead"]

    # Coach start
    await client.post(
        "/v1/agents/maintenance-coach/start",
        json={
            "asset_id": "LOOM-01",
            "sop_id": "SOP-001",
            "user_roles": ["shift_supervisor"],
        },
    )
    coach_state = graph.ainvoke.call_args_list[2].args[0]
    assert coach_state.get("user_roles") == ["shift_supervisor"]


@pytest.mark.asyncio
async def test_recursion_overflow_returns_503(client, app_with_mocks) -> None:
    """RecursionError from supervisor → 503 with Retry-After header."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        side_effect=RecursionError("recursion limit exceeded")
    )

    response = await client.post(
        "/v1/agents/predictive-maintenance/score",
        json={"asset_id": "LOOM-01", "user_roles": ["technician"]},
    )
    assert response.status_code == 503, response.text
    assert "Retry-After" in response.headers
