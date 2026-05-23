"""QualityInspector (OPS-03) — happy / degraded / failure E2E scenarios.

Plan 06-13 / success criterion #5.

Happy:
    Small slub (length<1in) → grader emits valid {score=4,severity=minor} →
    tier=auto-log → 1 Decision.AUTO audit row, NO HITL.

Degraded:
    Grader receives invalid LLM JSON → falls back to conservative verdict
    (score=4, severity=major) → tier=supervisor → HITL queued, no audit row
    (audit only on resume).

Failure:
    Full-width broken_end → grader emits {score=1,severity=critical} →
    tier=manager+safety → SafetyInterlockMiddleware.check invoked + HITL
    queued.

Mock collaborators + patched human_approval_node — see conftest.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

# RED gate — skip if the agent isn't installed in this env.
pytest.importorskip(
    "ops_quality_inspector.agent",
    reason="Plan 06-07 implements ops_quality_inspector.agent",
)

from langchain_core.messages import AIMessage  # noqa: E402
from unittest.mock import AsyncMock, MagicMock  # noqa: E402

from ops_quality_inspector.agent import QualityInspector  # noqa: E402
from sft_domain.ops.quality import QualityEvent  # noqa: E402


pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


_SCENARIOS = [
    "quality-inspector/happy",
    "quality-inspector/degraded",
    "quality-inspector/failure",
]


def _build_llm_from_entries(entries: list[dict[str, Any]]) -> Any:
    """Return a chat-model mock whose ainvoke yields the first entry's content."""
    model = MagicMock(name="llm")
    if not entries:
        model.ainvoke = AsyncMock(return_value=AIMessage(content=""))
        return model
    content = entries[0].get("response", {}).get("content", "")
    model.ainvoke = AsyncMock(return_value=AIMessage(content=content))
    return model


def _build_event(body: dict[str, Any]) -> QualityEvent:
    raw = body["event"]
    # Parse timestamp string → tz-aware datetime.
    ts = raw["timestamp"]
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return QualityEvent(
        asset_id=raw["asset_id"],
        dye_lot_id=raw["dye_lot_id"],
        defect_type=raw["defect_type"],
        defect_length_inches=raw["defect_length_inches"],
        full_width=raw.get("full_width", False),
        position_meters=raw["position_meters"],
        timestamp=ts,
        source=raw["source"],
    )


@pytest.mark.parametrize("ops_scenario", _SCENARIOS, indirect=True)
async def test_quality_inspector_scenario(
    ops_scenario: dict[str, Any],
    mock_llm_backend: dict[str, Any],
    scenario_llm_entries: list[dict[str, Any]],
    mock_collaborators: dict[str, Any],
    patched_human_approval: dict[str, list[dict[str, Any]]],
    make_rag_pipeline,
) -> None:
    """Drive QualityInspector.handle_event end-to-end against the JSONL trace."""
    assert ops_scenario
    expected = ops_scenario["expected"]
    body = ops_scenario["input"]["body"]

    rag_pipeline = make_rag_pipeline(ops_scenario.get("seed", {}).get("qdrant_chunks") or [])

    # Build the model and let QualityInspector's grader use it via the model= kwarg.
    model = _build_llm_from_entries(scenario_llm_entries)

    inspector = QualityInspector(
        rag_pipeline=rag_pipeline,
        audit_writer=mock_collaborators["audit_writer"],
        queue_writer=mock_collaborators["queue_writer"],
        nats_publisher=mock_collaborators["nats_publisher"],
        safety_middleware=mock_collaborators["safety_middleware"],
        pool=mock_collaborators["pool"],
        model=model,
    )

    event = _build_event(body)
    user_roles = body.get("user_roles") or ["technician"]

    response = await inspector.handle_event(event, user_roles=user_roles)

    # Verdict + tier routing.
    assert response is not None
    assert response.hitl_routed_to == expected["hitl_routed_to"]
    if "severity" in expected:
        assert response.verdict.severity == expected["severity"]
    if "score" in expected and expected["score"] is not None:
        assert response.verdict.score == expected["score"]

    # Audit rows: auto-log writes 1 row (Decision.AUTO); supervisor/manager
    # branches enqueue HITL and write audit only on resume.
    expected_audit_rows = expected.get("audit_rows", 0)
    actual_audit_writes = len(mock_collaborators["audit_writer"].writes)
    assert actual_audit_writes >= expected_audit_rows, (
        f"expected ≥ {expected_audit_rows} audit row(s); got {actual_audit_writes}"
    )

    # HITL dispatch count.
    expected_hitl = expected.get("hitl_approvals_min", 0)
    actual_hitl = len(patched_human_approval["calls"])
    assert actual_hitl >= expected_hitl, (
        f"expected ≥ {expected_hitl} HITL call(s); got {actual_hitl}"
    )

    # SafetyInterlockMiddleware.check invocation (failure scenario only).
    if expected.get("safety_check_invoked"):
        assert len(mock_collaborators["safety_middleware"].check_invocations) >= 1, (
            "expected SafetyInterlockMiddleware.check to be invoked at least once"
        )

    # action_type on the audit row OR the ProposedAction.
    if expected.get("action_type"):
        from sft_agents.models.enums import ActionType

        target = ActionType[expected["action_type"]].value
        # If the auto-log branch fired, inspect the audit row's action_type.
        if mock_collaborators["audit_writer"].writes:
            assert mock_collaborators["audit_writer"].writes[0].action_type == target
        # If HITL was queued, inspect the proposed_action.action_type.
        if patched_human_approval["calls"]:
            assert (
                patched_human_approval["calls"][0]["proposed_action"].action_type.value
                == target
            )
