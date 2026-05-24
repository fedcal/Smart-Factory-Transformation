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

import pytest


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
    make_interrupt_fn,
) -> None:
    """On first execution, audit_writer.write.call_count == 0 before interrupt raises (CR-02).

    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract (CR-02): "
        "On first execution, interrupt() raises BEFORE any audit_writer.write() call. "
        "Patch 'scm_demand_forecaster.agent.interrupt' with a raise-on-first-call function; "
        "assert audit_writer.write.call_count == 0 after GraphInterrupt is caught."
    )


# ---------------------------------------------------------------------------
# Contract 2: DEMAND_PLAN_DRAFT row after resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demand_plan_draft_written_after_resume(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After interrupt returns (HITL resume): exactly 1 DEMAND_PLAN_DRAFT row (SCM-04).

    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract: after interrupt() returns, "
        "audit_writer.write called with positional AuditRecord whose "
        "action_type == ActionType.DEMAND_PLAN_DRAFT.value. "
        "Patch 'scm_demand_forecaster.agent.interrupt' to return on first call."
    )


# ---------------------------------------------------------------------------
# Contract 3: DEMAND_PLAN_SIGNOFF row after approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demand_plan_signoff_written_after_approval(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After supervisor/planner approval: DEMAND_PLAN_SIGNOFF row present (SCM-04).

    Together: 1 DEMAND_PLAN_DRAFT + 1 DEMAND_PLAN_SIGNOFF. Same stable plan_id.
    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract: after full HITL lifecycle, "
        "audit.actions contains DEMAND_PLAN_DRAFT + DEMAND_PLAN_SIGNOFF rows. "
        "Both rows must use the same stable plan_id derived from thread_id."
    )


# ---------------------------------------------------------------------------
# Contract 4: Demand plan for >= 2 SKU groups in state delta (Open Question 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demand_plan_for_at_least_two_sku_groups_in_state_delta(
    mock_audit_writer,
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
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract (Open Question 2): "
        "result = await DemandForecaster.__call__(state) → "
        "result['demand_plan'] is a dict or list with >= 2 SKU group forecasts. "
        "The gateway uses state['demand_plan'] to route to ProductionPlanner. "
        "No direct call to ProductionPlanner from DemandForecaster."
    )


def test_cross_cluster_routing_via_state_not_direct_invocation() -> None:
    """DemandForecaster communicates with ProductionPlanner via state, not direct calls (SCM-04).

    Open Question 2 resolution: the cross-cluster boundary is crossed via the
    state['demand_plan'] key. The gateway (supply_agents.py) reads this key
    and routes the approved demand plan to the ProductionPlanner cluster.

    No direct import of ProductionPlanner from DemandForecaster module.
    Implementation target: scm_demand_forecaster.agent (module imports)
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract (Open Question 2): "
        "scm_demand_forecaster.agent must NOT import from ops_production_planner "
        "or any other cross-cluster module. The demand plan is passed via state['demand_plan']. "
        "Verify: 'from ops_production_planner' NOT in scm_demand_forecaster/agent.py source."
    )


# ---------------------------------------------------------------------------
# Contract 5: Stable plan_id from thread_id (CR-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_id_stable_across_replay(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """plan_id is derived from thread_id — stable across LangGraph replay (CR-04).

    Both DEMAND_PLAN_DRAFT and DEMAND_PLAN_SIGNOFF rows must share the same plan_id,
    derived deterministically from state['thread_id'] via hashlib.sha256.

    Search: thread_id appears in this test — confirms CR-04 contract is enforced.

    NEVER: plan_id = str(uuid4())  ← re-generates on every replay
    ALWAYS: plan_id = sha256(f"{AGENT_ID}.{thread_id}").hexdigest()[:32]

    Implementation target: scm_demand_forecaster.agent.DemandForecaster._stable_id
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract (CR-04): "
        "thread_id='supply.demand-forecaster.test-001' must produce the SAME "
        "plan_id on two separate __call__ invocations (simulating replay). "
        "Search test for 'thread_id' to confirm this contract is enforced."
    )


# ---------------------------------------------------------------------------
# Contract 6: approval_id=None for pending HITL rows (CR-03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_id_is_none_for_pending_demand_plan_draft(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """The DEMAND_PLAN_DRAFT row has approval_id=None (CR-03).

    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract (CR-03): "
        "The AuditRecord written for DEMAND_PLAN_DRAFT must have approval_id=None. "
        "Never fabricate a UUID for a pending HITL row."
    )


# ---------------------------------------------------------------------------
# Contract 7: AuditWriter.write() called with positional AuditRecord (CR-02)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_written_with_positional_audit_record(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """audit_writer.write() receives a positional AuditRecord — no kwargs (CR-02).

    Implementation target: scm_demand_forecaster.agent.DemandForecaster.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract (CR-02): "
        "audit_writer.write must be called as write(record) — single positional AuditRecord. "
        "Verify: call_args_list[0][0][0] is AuditRecord instance, "
        "call_args_list[0][1] == {} (empty kwargs dict)."
    )
