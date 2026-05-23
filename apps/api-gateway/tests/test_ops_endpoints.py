"""Unit tests for OPS-agent HTTP endpoints (Plan 06-12 Task 1 — RED phase).

Covers (OPS-01/02/03/04):
    1. test_post_anomaly_scan_invokes_supervisor
    2. test_post_anomaly_scan_triggered_by_enum (422 on bogus value)
    3. test_post_planner_plan_invokes_supervisor
    4. test_post_planner_plan_strategy_validates (422 on `random`)
    5. test_post_operator_chat_invokes_supervisor
    6. test_post_operator_chat_query_min_length (422 on empty)
    7. test_endpoints_emit_langfuse_span (monkeypatch — assert span name `agent.<slug>.invoke`)

All endpoints invoke the supervisor graph via `target_agent=<slug>` (Plan 06-05
OPS routing). user_roles is propagated when supplied. Langfuse spans are tagged
``agent.<slug>.invoke`` per Phase 4 observability convention.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# --- /v1/agents/anomaly-detector/scan -------------------------------------


@pytest.mark.asyncio
async def test_post_anomaly_scan_invokes_supervisor(
    client, app_with_mocks
) -> None:
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"anomalies": [], "messages": [], "proposed_actions": []}
    )

    body = {"window_minutes": 15, "triggered_by": "operator"}
    response = await client.post(
        "/v1/agents/anomaly-detector/scan", json=body
    )
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    state_arg, kwargs = graph.ainvoke.call_args.args[0], graph.ainvoke.call_args.kwargs
    assert state_arg["target_agent"] == "anomaly-detector"
    assert state_arg["window_minutes"] == 15
    assert state_arg["triggered_by"] == "operator"
    # Bounded recursion as per Plan 06-12 + T-V6-recursion-bomb mitigation.
    cfg = kwargs.get("config") or {}
    assert cfg.get("recursion_limit") == 5
    assert "configurable" in cfg
    assert cfg["configurable"]["thread_id"].startswith("ops.anomaly-detector.")

    payload = response.json()
    assert "anomalies" in payload
    assert payload["thread_id"].startswith("ops.anomaly-detector.")


@pytest.mark.asyncio
async def test_post_anomaly_scan_triggered_by_enum(
    client, app_with_mocks
) -> None:
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/anomaly-detector/scan",
        json={"window_minutes": 15, "triggered_by": "bogus-source"},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# --- /v1/agents/production-planner/plan -----------------------------------


@pytest.mark.asyncio
async def test_post_planner_plan_invokes_supervisor(
    client, app_with_mocks
) -> None:
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "messages": [],
            "proposed_actions": [],
            "pending_approval_id": None,
        }
    )

    body = {
        "horizon_days": 7,
        "strategy": "edd",
        "user_roles": ["operator", "scheduler"],
    }
    response = await client.post(
        "/v1/agents/production-planner/plan", json=body
    )
    assert response.status_code == 202, response.text

    assert graph.ainvoke.await_count == 1
    state_arg, kwargs = graph.ainvoke.call_args.args[0], graph.ainvoke.call_args.kwargs
    assert state_arg["target_agent"] == "production-planner"
    assert state_arg["horizon_days"] == 7
    assert state_arg["strategy"] == "edd"
    assert state_arg["user_roles"] == ["operator", "scheduler"]
    cfg = kwargs.get("config") or {}
    assert cfg.get("recursion_limit") == 5
    assert cfg["configurable"]["thread_id"].startswith(
        "ops.production-planner."
    )

    payload = response.json()
    assert payload["thread_id"].startswith("ops.production-planner.")


@pytest.mark.asyncio
async def test_post_planner_plan_strategy_validates(
    client, app_with_mocks
) -> None:
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/production-planner/plan",
        json={"horizon_days": 7, "strategy": "random"},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# --- /v1/agents/operator-assistant/chat -----------------------------------


@pytest.mark.asyncio
async def test_post_operator_chat_invokes_supervisor(
    client, app_with_mocks
) -> None:
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={
            "response_md": "Ciao operatore.",
            "citations": [],
            "citations_missing": False,
            "lang": "it",
            "tool_calls_count": 0,
        }
    )

    body = {
        "query": "Quali sono i SOP per il rotolo LOOM-01?",
        "user_roles": ["operator"],
        "thread_id": "ops.operator-assistant.sess-001",
    }
    response = await client.post(
        "/v1/agents/operator-assistant/chat", json=body
    )
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    state_arg, kwargs = graph.ainvoke.call_args.args[0], graph.ainvoke.call_args.kwargs
    assert state_arg["target_agent"] == "operator-assistant"
    assert state_arg["query"] == body["query"]
    assert state_arg["user_roles"] == ["operator"]
    cfg = kwargs.get("config") or {}
    assert cfg.get("recursion_limit") == 5
    # Client-supplied thread_id MUST be honoured (multi-turn chat).
    assert cfg["configurable"]["thread_id"] == "ops.operator-assistant.sess-001"

    payload = response.json()
    assert payload["response_md"] == "Ciao operatore."
    assert payload["lang"] == "it"


@pytest.mark.asyncio
async def test_post_operator_chat_query_min_length(
    client, app_with_mocks
) -> None:
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/operator-assistant/chat",
        json={
            "query": "",
            "user_roles": ["operator"],
            "thread_id": "ops.operator-assistant.sess-002",
        },
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# --- Langfuse-span tagging convention --------------------------------------


@pytest.mark.asyncio
async def test_endpoints_emit_langfuse_span(client, app_with_mocks) -> None:
    """All 3 /v1/agents endpoints must tag the invocation with `agent.<slug>.invoke`.

    The router accomplishes this by passing ``tags=["agent.<slug>.invoke"]``
    into ``build_invocation_config``. We monkey-patch that helper to capture
    the tags actually supplied.
    """
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"anomalies": []})

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
        "svc_api_gateway.routers.ops_agents.build_invocation_config",
        side_effect=_fake_build_invocation_config,
    ):
        # anomaly-detector
        r1 = await client.post(
            "/v1/agents/anomaly-detector/scan",
            json={"window_minutes": 5, "triggered_by": "operator"},
        )
        assert r1.status_code == 200, r1.text

        # production-planner
        graph.ainvoke = AsyncMock(return_value={"messages": []})
        r2 = await client.post(
            "/v1/agents/production-planner/plan",
            json={"horizon_days": 3, "strategy": "spt"},
        )
        assert r2.status_code == 202, r2.text

        # operator-assistant
        graph.ainvoke = AsyncMock(
            return_value={
                "response_md": "ok",
                "citations": [],
                "citations_missing": False,
                "lang": "en",
                "tool_calls_count": 0,
            }
        )
        r3 = await client.post(
            "/v1/agents/operator-assistant/chat",
            json={
                "query": "hello",
                "user_roles": [],
                "thread_id": "ops.operator-assistant.sess-span",
            },
        )
        assert r3.status_code == 200, r3.text

    assert len(captured_tags) == 3
    assert "agent.anomaly-detector.invoke" in captured_tags[0]
    assert "agent.production-planner.invoke" in captured_tags[1]
    assert "agent.operator-assistant.invoke" in captured_tags[2]
