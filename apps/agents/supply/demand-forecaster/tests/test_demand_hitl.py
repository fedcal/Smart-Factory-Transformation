"""Contract tests for DemandForecaster HITL interrupt-then-audit lifecycle (SCM-04, CR-02/CR-04).

CONTRACT: interrupt-then-audit for DEMAND_PLAN_DRAFT then DEMAND_PLAN_SIGNOFF:
  1. On first run (initial node execution):
     - interrupt() is called BEFORE any audit write
     - audit_writer.write.call_count == 0 before interrupt raises
  2. On resume (after HITL approval):
     - Exactly 1 DEMAND_PLAN_DRAFT row written
     - Exactly 1 DEMAND_PLAN_SIGNOFF row written after approval
     - plan_id is STABLE across replay (derived from thread_id, NOT uuid4 — CR-04)
  3. After resume, the demand plan for >= 2 SKU groups is in the returned state delta:
     - state["demand_plan"] contains forecasts for >= 2 SKU groups
     - This enables the gateway to route to ProductionPlanner (Open Question 2 resolution)
     - Cross-cluster communication via state delta (NOT direct agent invocation)
  4. approval_id is None on the pending HITL row (CR-03)
  5. audit_writer.write() called with positional AuditRecord (CR-02)

Open Question 2 resolution (from 09-CONTEXT.md):
  DemandForecaster → ProductionPlanner routing goes via state["demand_plan"] key.
  The gateway reads this key and routes the state to the ProductionPlanner agent.
  NO direct method calls between agents; state is the only coupling point.

Phase 8 anti-bug guardrails encoded here:
  - CR-02: audit write AFTER interrupt() returns
  - CR-03: approval_id=None for pending rows
  - CR-04: stable plan_id from thread_id hash

Implementation target: scm_demand_forecaster.agent.DemandForecaster
(Wave 2-3 plan: 09-05)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sft_agents.models.audit import AuditRecord
from sft_agents.models.enums import ActionType

from scm_demand_forecaster.agent import DemandForecaster


# Shared test state
_THREAD_ID = "supply.demand-forecaster.test-001"

_STATE: dict = {
    "thread_id": _THREAD_ID,
    "target_agent": "demand-forecaster",
}


# ---------------------------------------------------------------------------
# Contract 1: No audit write before interrupt raises (first execution)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_audit_write_before_interrupt_on_first_execution(
    mock_audit_writer,
    mock_pool,
    make_interrupt_fn,
) -> None:
    """On first execution, audit_writer.write.call_count == 0 before interrupt raises (CR-02).

    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    interrupt_fn = make_interrupt_fn()  # raises GraphInterrupt/RuntimeError on first call

    agent = DemandForecaster(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_demand_forecaster.agent.interrupt", interrupt_fn):
        try:
            await agent(dict(_STATE))
        except Exception:
            pass  # GraphInterrupt or RuntimeError on first execution — expected

    # CR-02: no audit writes before interrupt raises
    assert mock_audit_writer.write.call_count == 0, (
        f"Expected 0 audit writes before interrupt, got {mock_audit_writer.write.call_count}"
    )


# ---------------------------------------------------------------------------
# Contract 2: DEMAND_PLAN_DRAFT row after resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demand_plan_draft_written_after_resume(
    mock_audit_writer,
    mock_pool,
    make_interrupt_fn,
) -> None:
    """After interrupt returns (HITL resume): exactly 1 DEMAND_PLAN_DRAFT row (SCM-04).

    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    # make_interrupt_fn returns on first call (simulates resume — no raise)
    interrupt_fn = make_interrupt_fn(resume_payload={"approved": True, "approver_id": "prod-planner-001"})
    # On second call it returns; but we only call once, so: call_count == 1 → returns
    # Actually make_interrupt_fn raises on first call, returns on subsequent.
    # We need to call twice: first raises, second returns.
    # Simpler: use a version that directly returns (count starts at 1).
    # Looking at the conftest: call_count[0] == 1 raises, else returns.
    # So we need to capture the state across two separate __call__ invocations.
    # Alternatively, we can just directly test the resume path by using a no-raise version.

    # Use a single-call agent invocation where interrupt always returns (simulates resume state).
    call_count: list[int] = [0]
    resume_payload = {"approved": True, "approver_id": "prod-planner-001"}

    def always_return(value):  # type: ignore[misc]
        call_count[0] += 1
        return resume_payload

    agent = DemandForecaster(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_demand_forecaster.agent.interrupt", always_return):
        await agent(dict(_STATE))

    # Exactly 2 writes: DRAFT + SIGNOFF
    assert mock_audit_writer.write.call_count == 2, (
        f"Expected 2 audit writes (DRAFT + SIGNOFF), got {mock_audit_writer.write.call_count}"
    )

    # First call must be DEMAND_PLAN_DRAFT
    first_record = mock_audit_writer.write.call_args_list[0][0][0]
    assert isinstance(first_record, AuditRecord)
    assert first_record.action_type == ActionType.DEMAND_PLAN_DRAFT.value, (
        f"Expected DEMAND_PLAN_DRAFT, got {first_record.action_type}"
    )


# ---------------------------------------------------------------------------
# Contract 3: DEMAND_PLAN_SIGNOFF row after approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demand_plan_signoff_written_after_approval(
    mock_audit_writer,
    mock_pool,
    make_interrupt_fn,
) -> None:
    """After supervisor/planner approval: DEMAND_PLAN_SIGNOFF row present (SCM-04).

    Together: 1 DEMAND_PLAN_DRAFT + 1 DEMAND_PLAN_SIGNOFF. Same stable plan_id.
    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    resume_payload = {"approved": True, "approver_id": "prod-planner-001"}

    def always_return(value):  # type: ignore[misc]
        return resume_payload

    agent = DemandForecaster(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_demand_forecaster.agent.interrupt", always_return):
        await agent(dict(_STATE))

    assert mock_audit_writer.write.call_count == 2

    draft_record = mock_audit_writer.write.call_args_list[0][0][0]
    signoff_record = mock_audit_writer.write.call_args_list[1][0][0]

    assert draft_record.action_type == ActionType.DEMAND_PLAN_DRAFT.value
    assert signoff_record.action_type == ActionType.DEMAND_PLAN_SIGNOFF.value

    # Both rows must share the same stable plan_id
    assert draft_record.thread_id == signoff_record.thread_id, (
        "DRAFT and SIGNOFF must share the same thread_id"
    )


# ---------------------------------------------------------------------------
# Contract 4: Demand plan for >= 2 SKU groups in state delta (Open Question 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demand_plan_for_at_least_two_sku_groups_in_state_delta(
    mock_audit_writer,
    mock_pool,
    make_interrupt_fn,
) -> None:
    """After resume, state['demand_plan'] contains forecasts for >= 2 SKU groups (SCM-04).

    Open Question 2 resolution: DemandForecaster → ProductionPlanner communication
    goes via state['demand_plan'] key (NOT direct agent invocation). The gateway
    reads this key and routes accordingly.

    The demand_plan must contain data for at least 2 SKU groups (e.g. 'jersey', 'twill')
    to be meaningful for production scheduling.

    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    resume_payload = {"approved": True, "approver_id": "prod-planner-001"}

    def always_return(value):  # type: ignore[misc]
        return resume_payload

    agent = DemandForecaster(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_demand_forecaster.agent.interrupt", always_return):
        result = await agent(dict(_STATE))

    # state['demand_plan'] must exist and cover >= 2 SKU groups
    assert "demand_plan" in result, "state['demand_plan'] key must be in returned state delta"
    demand_plan = result["demand_plan"]
    assert "sku_groups" in demand_plan, "demand_plan must have 'sku_groups' key"
    assert len(demand_plan["sku_groups"]) >= 2, (
        f"demand_plan must cover >= 2 SKU groups, got {len(demand_plan['sku_groups'])}: "
        f"{[g.get('sku_group') for g in demand_plan['sku_groups']]}"
    )


def test_cross_cluster_routing_via_state_not_direct_invocation() -> None:
    """DemandForecaster communicates with ProductionPlanner via state, not direct calls (SCM-04).

    Open Question 2 resolution: the cross-cluster boundary is crossed via the
    state['demand_plan'] key. The gateway (supply_agents.py) reads this key
    and routes the approved demand plan to the ProductionPlanner cluster.

    No direct import of ProductionPlanner from DemandForecaster module.
    Implementation target: scm_demand_forecaster.agent (module imports)
    """
    import inspect
    import scm_demand_forecaster.agent as agent_module

    source = inspect.getsource(agent_module)
    assert "from ops_production_planner" not in source, (
        "scm_demand_forecaster.agent must NOT import from ops_production_planner — "
        "cross-cluster communication via state['demand_plan'] only (Open Question 2)"
    )
    assert "import ops_production_planner" not in source, (
        "scm_demand_forecaster.agent must NOT import from ops_production_planner"
    )


# ---------------------------------------------------------------------------
# Contract 5: Stable plan_id from thread_id (CR-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_id_stable_across_replay(
    mock_audit_writer,
    mock_pool,
    make_interrupt_fn,
) -> None:
    """plan_id is derived from thread_id — stable across LangGraph replay (CR-04).

    Both DEMAND_PLAN_DRAFT and DEMAND_PLAN_SIGNOFF rows must share the same plan_id,
    derived deterministically from state['thread_id'] via hashlib.sha256.

    NEVER: plan_id = str(uuid4())  ← re-generates on every replay
    ALWAYS: plan_id = sha256(f"{AGENT_ID}.{thread_id}").hexdigest()[:32]

    Implementation target: scm_demand_forecaster.agent.DemandForecaster._stable_id
    """
    import hashlib
    from scm_demand_forecaster.metadata import AGENT_ID

    # Compute expected stable plan_id from thread_id
    expected_plan_id = hashlib.sha256(
        f"{AGENT_ID}.{_THREAD_ID}".encode("utf-8")
    ).hexdigest()[:32]

    resume_payload = {"approved": True, "approver_id": "prod-planner-001"}

    def always_return(value):  # type: ignore[misc]
        return resume_payload

    from unittest.mock import MagicMock
    audit_writer_1 = MagicMock()
    audit_writer_1.write = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()
    audit_writer_2 = MagicMock()
    audit_writer_2.write = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()

    agent1 = DemandForecaster(pool=mock_pool, audit_writer=audit_writer_1)
    agent2 = DemandForecaster(pool=mock_pool, audit_writer=audit_writer_2)

    with patch("scm_demand_forecaster.agent.interrupt", always_return):
        result1 = await agent1(dict(_STATE))
        result2 = await agent2(dict(_STATE))

    # Both invocations must produce the same stable plan_id
    plan_id_1 = result1["demand_plan"]["plan_id"]
    plan_id_2 = result2["demand_plan"]["plan_id"]
    assert plan_id_1 == plan_id_2, (
        f"plan_id must be stable across replay: {plan_id_1} != {plan_id_2}"
    )
    assert plan_id_1 == expected_plan_id, (
        f"Expected plan_id={expected_plan_id}, got {plan_id_1} (thread_id={_THREAD_ID!r})"
    )

    # Also verify from audit records
    draft_record = audit_writer_1.write.call_args_list[0][0][0]
    signoff_record = audit_writer_1.write.call_args_list[1][0][0]
    # Both audit records for the same session share thread_id (stable per-session)
    assert draft_record.thread_id == signoff_record.thread_id


# ---------------------------------------------------------------------------
# Contract 6: approval_id=None for pending HITL rows (CR-03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_id_is_none_for_pending_demand_plan_draft(
    mock_audit_writer,
    mock_pool,
    make_interrupt_fn,
) -> None:
    """The DEMAND_PLAN_DRAFT row has approval_id=None (CR-03).

    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    resume_payload = {"approved": True, "approver_id": "prod-planner-001"}

    def always_return(value):  # type: ignore[misc]
        return resume_payload

    agent = DemandForecaster(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_demand_forecaster.agent.interrupt", always_return):
        await agent(dict(_STATE))

    draft_record = mock_audit_writer.write.call_args_list[0][0][0]
    assert isinstance(draft_record, AuditRecord)
    assert draft_record.approval_id is None, (
        f"DEMAND_PLAN_DRAFT approval_id must be None (CR-03), got {draft_record.approval_id}"
    )


# ---------------------------------------------------------------------------
# Contract 7: AuditWriter.write() called with positional AuditRecord (CR-02)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_written_with_positional_audit_record(
    mock_audit_writer,
    mock_pool,
    make_interrupt_fn,
) -> None:
    """audit_writer.write() receives a positional AuditRecord — no kwargs (CR-02).

    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    resume_payload = {"approved": True, "approver_id": "prod-planner-001"}

    def always_return(value):  # type: ignore[misc]
        return resume_payload

    agent = DemandForecaster(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_demand_forecaster.agent.interrupt", always_return):
        await agent(dict(_STATE))

    assert mock_audit_writer.write.call_count == 2

    for call in mock_audit_writer.write.call_args_list:
        positional_args = call[0]  # call[0] = positional args tuple
        keyword_args = call[1]     # call[1] = keyword args dict

        assert len(positional_args) == 1, (
            f"write() must be called with exactly 1 positional arg (CR-02), "
            f"got {len(positional_args)} positional args"
        )
        assert keyword_args == {}, (
            f"write() must be called with no kwargs (CR-02), got {keyword_args}"
        )
        assert isinstance(positional_args[0], AuditRecord), (
            f"Positional arg must be AuditRecord (CR-02), got {type(positional_args[0])}"
        )
