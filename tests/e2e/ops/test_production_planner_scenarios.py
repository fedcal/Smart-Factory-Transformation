"""ProductionPlanner (OPS-02) — happy / degraded / failure E2E scenarios.

Plan 06-13 / success criterion #5.

Happy:
    SPT strategy, 3-day horizon, seed orders.yaml → ScheduleDraft with N
    items + supervisor HITL approval queued.

Degraded:
    EDD, 1-day horizon (many unscheduled), LLM emits invalid JSON → agent
    falls back to _FALLBACK_RATIONALE string but still queues supervisor HITL.

Failure:
    Invalid strategy "random" → PlanRequest Pydantic ValidationError BEFORE
    any heuristic / HITL dispatch (T-V6-injection mitigation).

Mock collaborators + patched human_approval_node — see conftest.py.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# RED gate — skip if the agent isn't installed in this env.
pytest.importorskip(
    "ops_production_planner.agent",
    reason="Plan 06-08 implements ops_production_planner.agent",
)

from langchain_core.messages import AIMessage  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from ops_production_planner.agent import ProductionPlanner  # noqa: E402


pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


_SCENARIOS = [
    "production-planner/happy",
    "production-planner/degraded",
    "production-planner/failure",
]


def _build_llm_from_entries(entries: list[dict[str, Any]]) -> Any:
    """Return a chat-model-like mock whose ainvoke yields the first entry's content."""
    model = MagicMock(name="llm")

    if not entries:
        model.ainvoke = AsyncMock(return_value=AIMessage(content=""))
        return model

    # Use the first entry's content; the production-planner only does one LLM
    # round per call (rationale generation).
    content = entries[0].get("response", {}).get("content", "")
    model.ainvoke = AsyncMock(return_value=AIMessage(content=content))
    return model


@pytest.mark.parametrize("ops_scenario", _SCENARIOS, indirect=True)
async def test_production_planner_scenario(
    ops_scenario: dict[str, Any],
    mock_llm_backend: dict[str, Any],
    scenario_llm_entries: list[dict[str, Any]],
    mock_collaborators: dict[str, Any],
    patched_human_approval: dict[str, list[dict[str, Any]]],
    make_rag_pipeline,
) -> None:
    """Drive ProductionPlanner.__call__ end-to-end against the JSONL trace."""
    assert ops_scenario, f"scenario YAML missing for key {mock_llm_backend.get('env')!r}"
    expected = ops_scenario["expected"]
    body = ops_scenario["input"]["body"]

    rag_pipeline = make_rag_pipeline(ops_scenario.get("seed", {}).get("qdrant_chunks") or [])

    planner = ProductionPlanner(
        rag_pipeline=rag_pipeline,
        audit_writer=mock_collaborators["audit_writer"],
        queue_writer=mock_collaborators["queue_writer"],
        nats=mock_collaborators["nats"],
        model=_build_llm_from_entries(scenario_llm_entries),
    )

    state = {
        "strategy": body.get("strategy"),
        "horizon_days": body.get("horizon_days"),
        "user_roles": body.get("user_roles", []),
        "thread_id": body.get("thread_id"),
    }

    if expected.get("raises") == "pydantic.ValidationError":
        # Failure path: PlanRequest rejects the strategy at the boundary.
        with pytest.raises(ValidationError):
            await planner(state)
        # No HITL approval queued.
        assert len(patched_human_approval["calls"]) == 0
        # RAG pipeline NOT invoked (validation happens first).
        rag_pipeline.search.assert_not_called()
        return

    # Happy / degraded paths: agent completes and queues supervisor HITL.
    result = await planner(state)

    # Schedule produced.
    assert "schedule_draft" in result
    draft = result["schedule_draft"]
    assert len(draft.items) >= expected.get("schedule_items_min", 0)
    if "unscheduled_min" in expected:
        assert len(draft.unscheduled_orders) >= expected["unscheduled_min"]

    # Rationale present.
    if expected.get("has_rationale_md"):
        assert isinstance(draft.rationale_md, str)
        assert len(draft.rationale_md) > 0
    if expected.get("rationale_is_fallback"):
        # _FALLBACK_RATIONALE contains the literal "_LLM rationale is unavailable"
        assert "_LLM rationale is unavailable" in draft.rationale_md

    # HITL dispatch
    assert len(patched_human_approval["calls"]) >= expected.get("hitl_approvals_min", 1)
    call = patched_human_approval["calls"][0]
    if "hitl_tier" in expected:
        from sft_agents.models.enums import Tier

        assert call["tier"] == Tier.SUPERVISOR, (
            f"expected supervisor tier, got {call['tier']!r}"
        )

    # ProposedAction shape.
    proposed = call["proposed_action"]
    if "action_type" in expected and expected["action_type"]:
        assert proposed.action_type.value == expected["action_type"]
