"""Unit tests for supply-cluster HTTP endpoints (Plan 09-06 — SCM-01/02/03/04).

Covers 7 supply agent endpoints:
    POST /v1/agents/inventory-manager/check    (202, SCM-01 HITL start)
    POST /v1/agents/inventory-manager/resume   (200, SCM-01 post-HITL resume)
    POST /v1/agents/energy-optimizer/optimize  (202, SCM-02 HITL start)
    POST /v1/agents/energy-optimizer/resume    (200, SCM-02 post-HITL resume)
    POST /v1/agents/cost-analyzer/analyze      (200, SCM-03 autonomous)
    POST /v1/agents/demand-forecaster/forecast (202, SCM-04 HITL start)
    POST /v1/agents/demand-forecaster/resume   (200, SCM-04 post-HITL resume)

All tests use FastAPI TestClient (httpx.AsyncClient) with a stubbed supervisor
graph (AsyncMock ainvoke) — internal cluster routing verified E2E in a later phase.
Pattern mirrors test_knowledge_agents_router.py using conftest.py fixtures.

Key assertions:
    1. Each endpoint returns its expected status code (202/200/200/202/202/200).
    2. cost-analyzer/analyze has NO resume endpoint (autonomous SCM-03).
    3. Naive datetime on energy/cost requests → 422 (WR-02, not 500).
    4. A forced agent exception → generic 500 body without str(exc) (WR-05).
    5. RecursionError → 503 + Retry-After header (T-09-24).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc

_VALID_TS_FROM = datetime(2026, 1, 1, 0, 0, tzinfo=UTC).isoformat()
_VALID_TS_TO = datetime(2026, 2, 1, 0, 0, tzinfo=UTC).isoformat()

# Naive (no tzinfo) — must be rejected by WR-02 validators
_NAIVE_TS = "2026-01-01T00:00:00"


# ---------------------------------------------------------------------------
# InventoryManager /check — 3 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_inventory_check_returns_202(client, app_with_mocks) -> None:
    """POST /v1/agents/inventory-manager/check → 202 with hitl_status='supervisor_pending'."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"messages": []})

    body = {
        "sku_ids": ["SKU-001", "SKU-002"],
        "user_roles": ["procurement_manager"],
    }
    response = await client.post("/v1/agents/inventory-manager/check", json=body)
    assert response.status_code == 202, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]

    assert state_arg["target_agent"] == "inventory-manager"
    assert state_arg["sku_ids"] == ["SKU-001", "SKU-002"]
    assert state_arg["user_roles"] == ["procurement_manager"]
    assert config["recursion_limit"] == 5
    assert config["configurable"]["thread_id"].startswith("supply.inventory-manager.")

    payload = response.json()
    assert payload["hitl_status"] == "supervisor_pending"
    assert "thread_id" in payload
    assert payload["thread_id"].startswith("supply.inventory-manager.")


@pytest.mark.asyncio
async def test_post_inventory_check_without_sku_ids_returns_202(
    client, app_with_mocks
) -> None:
    """POST /v1/agents/inventory-manager/check without sku_ids → 202 (sku_ids is optional)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"messages": []})

    # sku_ids is optional — omitting it is valid
    body = {"user_roles": ["procurement_manager"]}
    response = await client.post("/v1/agents/inventory-manager/check", json=body)
    assert response.status_code == 202, response.text

    state_arg = graph.ainvoke.call_args.args[0]
    assert state_arg["sku_ids"] is None


@pytest.mark.asyncio
async def test_post_inventory_check_extra_field_422(client, app_with_mocks) -> None:
    """Extra field on frozen model → 422 (extra=forbid — T-09-22)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {"user_roles": ["manager"], "unknown_field": "should_fail"}
    response = await client.post("/v1/agents/inventory-manager/check", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# InventoryManager /resume — 2 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_inventory_resume_returns_200(client, app_with_mocks) -> None:
    """POST /v1/agents/inventory-manager/resume → 200 with reorder_recommendation."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "reorder_recommendation": {"sku_id": "SKU-001", "qty": 100},
            "reorder_alert": None,
        }
    )

    thread_id = "supply.inventory-manager.abc123"
    body = {
        "thread_id": thread_id,
        "decision": "approved",
        "decision_actor": "supervisor@factory.it",
    }
    response = await client.post("/v1/agents/inventory-manager/resume", json=body)
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]

    assert state_arg["target_agent"] == "inventory-manager"
    assert state_arg["decision"] == "approved"
    assert state_arg["thread_id"] == thread_id
    assert config["configurable"]["thread_id"] == thread_id

    payload = response.json()
    assert "thread_id" in payload
    assert payload["thread_id"] == thread_id


@pytest.mark.asyncio
async def test_post_inventory_resume_missing_decision_actor_422(
    client, app_with_mocks
) -> None:
    """Missing decision_actor → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/inventory-manager/resume",
        json={"thread_id": "supply.inventory-manager.abc123", "decision": "approved"},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# EnergyOptimizer /optimize — 4 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_energy_optimize_returns_202(client, app_with_mocks) -> None:
    """POST /v1/agents/energy-optimizer/optimize → 202 with hitl_status='supervisor_pending'."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"messages": []})

    body = {
        "process": "dyeing",
        "ts_from": _VALID_TS_FROM,
        "ts_to": _VALID_TS_TO,
        "user_roles": ["energy_manager"],
    }
    response = await client.post("/v1/agents/energy-optimizer/optimize", json=body)
    assert response.status_code == 202, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]

    assert state_arg["target_agent"] == "energy-optimizer"
    assert state_arg["process"] == "dyeing"
    assert state_arg["user_roles"] == ["energy_manager"]
    assert config["recursion_limit"] == 5
    assert config["configurable"]["thread_id"].startswith("supply.energy-optimizer.")

    payload = response.json()
    assert payload["hitl_status"] == "supervisor_pending"
    assert "thread_id" in payload


@pytest.mark.asyncio
async def test_post_energy_optimize_naive_ts_from_422(client, app_with_mocks) -> None:
    """Naive ts_from → 422 (WR-02 tz-aware validator, not 500)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {
        "process": "dyeing",
        "ts_from": _NAIVE_TS,  # naive — must be rejected by validator
        "ts_to": _VALID_TS_TO,
        "user_roles": ["energy_manager"],
    }
    response = await client.post("/v1/agents/energy-optimizer/optimize", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_energy_optimize_naive_ts_to_422(client, app_with_mocks) -> None:
    """Naive ts_to → 422 (WR-02 tz-aware validator, not 500)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {
        "process": "spinning",
        "ts_from": _VALID_TS_FROM,
        "ts_to": _NAIVE_TS,  # naive — must be rejected by validator
        "user_roles": ["energy_manager"],
    }
    response = await client.post("/v1/agents/energy-optimizer/optimize", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_energy_optimize_without_timestamps_202(
    client, app_with_mocks
) -> None:
    """POST /v1/agents/energy-optimizer/optimize without ts_from/ts_to → 202 (optional fields)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"messages": []})

    body = {"user_roles": ["energy_manager"]}
    response = await client.post("/v1/agents/energy-optimizer/optimize", json=body)
    assert response.status_code == 202, response.text


# ---------------------------------------------------------------------------
# EnergyOptimizer /resume — 2 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_energy_resume_returns_200(client, app_with_mocks) -> None:
    """POST /v1/agents/energy-optimizer/resume → 200 with energy_proposal."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"energy_proposal": None, "energy_alert": None}
    )

    thread_id = "supply.energy-optimizer.abc456"
    body = {
        "thread_id": thread_id,
        "decision": "approved",
        "decision_actor": "supervisor@factory.it",
    }
    response = await client.post("/v1/agents/energy-optimizer/resume", json=body)
    assert response.status_code == 200, response.text

    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]
    assert state_arg["target_agent"] == "energy-optimizer"
    assert config["configurable"]["thread_id"] == thread_id

    payload = response.json()
    assert payload["thread_id"] == thread_id


@pytest.mark.asyncio
async def test_post_energy_resume_missing_decision_422(client, app_with_mocks) -> None:
    """Missing decision → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/energy-optimizer/resume",
        json={
            "thread_id": "supply.energy-optimizer.abc456",
            "decision_actor": "supervisor@factory.it",
        },
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# CostAnalyzer /analyze — autonomous (SCM-03) — 5 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_cost_analyze_returns_200(client, app_with_mocks) -> None:
    """POST /v1/agents/cost-analyzer/analyze → 200 (autonomous, synchronous — SCM-03)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"cost_breakdown": None, "oepv_report": None, "messages": []}
    )

    body = {
        "ribasso_pct": 12.5,
        "pt": 60.0,
        "user_roles": ["procurement_manager"],
    }
    response = await client.post("/v1/agents/cost-analyzer/analyze", json=body)
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]

    assert state_arg["target_agent"] == "cost-analyzer"
    assert state_arg["ribasso_pct"] == 12.5
    assert state_arg["pt"] == 60.0
    assert config["recursion_limit"] == 5
    assert config["configurable"]["thread_id"].startswith("supply.cost-analyzer.")

    payload = response.json()
    assert "thread_id" in payload
    assert payload["thread_id"].startswith("supply.cost-analyzer.")


@pytest.mark.asyncio
async def test_post_cost_analyze_no_resume_endpoint(client, app_with_mocks) -> None:
    """cost-analyzer has NO resume endpoint (autonomous SCM-03 — D-SCM-AUTO).

    Verifies /cost-analyzer/resume returns 404 (route not registered).
    """
    response = await client.post(
        "/v1/agents/cost-analyzer/resume",
        json={"thread_id": "supply.cost-analyzer.abc", "decision": "approved"},
    )
    assert response.status_code == 405 or response.status_code == 404, (
        f"cost-analyzer/resume should not exist; got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_post_cost_analyze_naive_ts_from_422(client, app_with_mocks) -> None:
    """Naive ts_from on CostAnalyzeRequest → 422 (WR-02)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {
        "ribasso_pct": 10.0,
        "pt": 50.0,
        "ts_from": _NAIVE_TS,  # naive — must be rejected
        "ts_to": _VALID_TS_TO,
        "user_roles": ["procurement_manager"],
    }
    response = await client.post("/v1/agents/cost-analyzer/analyze", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_cost_analyze_naive_ts_to_422(client, app_with_mocks) -> None:
    """Naive ts_to on CostAnalyzeRequest → 422 (WR-02)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {
        "ribasso_pct": 10.0,
        "pt": 50.0,
        "ts_from": _VALID_TS_FROM,
        "ts_to": _NAIVE_TS,  # naive — must be rejected
        "user_roles": ["procurement_manager"],
    }
    response = await client.post("/v1/agents/cost-analyzer/analyze", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_cost_analyze_ribasso_out_of_range_422(
    client, app_with_mocks
) -> None:
    """ribasso_pct > 100 → 422 (le=100 constraint on CostAnalyzeRequest)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {"ribasso_pct": 150.0, "pt": 50.0, "user_roles": ["manager"]}
    response = await client.post("/v1/agents/cost-analyzer/analyze", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# DemandForecaster /forecast — 3 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_demand_forecast_returns_202(client, app_with_mocks) -> None:
    """POST /v1/agents/demand-forecaster/forecast → 202 with hitl_status='supervisor_pending'."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"messages": []})

    body = {
        "sku_groups": ["jersey", "twill"],
        "horizon": 6,
        "months_back": 24,
        "user_roles": ["supply_planner"],
    }
    response = await client.post("/v1/agents/demand-forecaster/forecast", json=body)
    assert response.status_code == 202, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]

    assert state_arg["target_agent"] == "demand-forecaster"
    assert state_arg["sku_groups"] == ["jersey", "twill"]
    assert state_arg["horizon"] == 6
    assert state_arg["months_back"] == 24
    assert state_arg["user_roles"] == ["supply_planner"]
    assert config["recursion_limit"] == 5
    assert config["configurable"]["thread_id"].startswith("supply.demand-forecaster.")

    payload = response.json()
    assert payload["hitl_status"] == "supervisor_pending"
    assert "thread_id" in payload


@pytest.mark.asyncio
async def test_post_demand_forecast_horizon_out_of_range_422(
    client, app_with_mocks
) -> None:
    """horizon > 36 → 422 (le=36 constraint on DemandForecastRequest)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {"sku_groups": ["jersey"], "horizon": 37, "user_roles": ["supply_planner"]}
    response = await client.post("/v1/agents/demand-forecaster/forecast", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_demand_forecast_without_sku_groups_202(
    client, app_with_mocks
) -> None:
    """POST /v1/agents/demand-forecaster/forecast without sku_groups → 202 (optional field)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"messages": []})

    body = {"user_roles": ["supply_planner"]}
    response = await client.post("/v1/agents/demand-forecaster/forecast", json=body)
    assert response.status_code == 202, response.text

    state_arg = graph.ainvoke.call_args.args[0]
    assert state_arg["sku_groups"] is None


# ---------------------------------------------------------------------------
# DemandForecaster /resume — 2 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_demand_resume_returns_200(client, app_with_mocks) -> None:
    """POST /v1/agents/demand-forecaster/resume → 200 with demand_plan."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"demand_plan": None, "mape_report": None}
    )

    thread_id = "supply.demand-forecaster.abc789"
    body = {
        "thread_id": thread_id,
        "decision": "approved",
        "decision_actor": "supervisor@factory.it",
    }
    response = await client.post("/v1/agents/demand-forecaster/resume", json=body)
    assert response.status_code == 200, response.text

    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]
    assert state_arg["target_agent"] == "demand-forecaster"
    assert state_arg["decision"] == "approved"
    assert state_arg["decision_actor"] == "supervisor@factory.it"
    assert config["configurable"]["thread_id"] == thread_id

    payload = response.json()
    assert payload["thread_id"] == thread_id


@pytest.mark.asyncio
async def test_post_demand_resume_missing_thread_id_422(client, app_with_mocks) -> None:
    """Missing thread_id → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/demand-forecaster/resume",
        json={"decision": "approved", "decision_actor": "supervisor@factory.it"},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# Cross-cutting — 3 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recursion_overflow_returns_503_with_retry_after(
    client, app_with_mocks
) -> None:
    """RecursionError from supervisor → 503 with Retry-After header (T-09-24)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(side_effect=RecursionError("recursion limit exceeded"))

    body = {"sku_ids": ["SKU-001"], "user_roles": ["manager"]}
    response = await client.post("/v1/agents/inventory-manager/check", json=body)
    assert response.status_code == 503, response.text
    assert "Retry-After" in response.headers
    body_json = response.json()
    assert body_json["error"] == "recursion_limit_exceeded"
    assert "thread_id" in body_json


@pytest.mark.asyncio
async def test_agent_exception_returns_generic_500_body(client, app_with_mocks) -> None:
    """Forced agent exception → 500 with generic body, no str(exc) leak (WR-05/T-09-23)."""
    graph = app_with_mocks.state.supervisor_graph
    secret_detail = "db_password=s3cr3t"  # must NOT appear in response body
    graph.ainvoke = AsyncMock(
        side_effect=RuntimeError(f"internal error: {secret_detail}")
    )

    body = {"user_roles": ["manager"]}
    response = await client.post("/v1/agents/inventory-manager/check", json=body)
    assert response.status_code == 500, response.text

    body_json = response.json()
    assert body_json["error"] == "internal_agent_error"
    assert "thread_id" in body_json
    # WR-05: raw exception detail must NOT be in the HTTP response body
    assert secret_detail not in response.text


@pytest.mark.asyncio
async def test_cost_analyze_agent_exception_generic_500(client, app_with_mocks) -> None:
    """Forced exception on cost-analyzer/analyze → generic 500 body (WR-05)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(side_effect=ValueError("oepv_internal_crash"))

    body = {"ribasso_pct": 10.0, "pt": 50.0, "user_roles": ["procurement_manager"]}
    response = await client.post("/v1/agents/cost-analyzer/analyze", json=body)
    assert response.status_code == 500, response.text

    body_json = response.json()
    assert body_json["error"] == "internal_agent_error"
    # WR-05: raw exception detail must NOT be in the HTTP response body
    assert "oepv_internal_crash" not in response.text
