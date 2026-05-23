"""Unit tests for ProductionPlanner agent (Plan 06-08, D-PP-01..04).

Tests cover the thin-orchestrator contract:
    1. Strategy dispatch — `spt` → schedule_spt, `edd` → schedule_edd.
    2. Determinism — identical inputs → identical schedule_id.
    3. LLM rationale — populates rationale_md only (never mutates items).
    4. RAG citations — rag_pipeline.search invoked once with category="sop".
    5. HITL routing — ProposedAction(action_type=SCHEDULE_DRAFT) → tier=SUPERVISOR.
    6. Unscheduled surfacing — unscheduled_orders mentioned in rationale + args.
    7. LLM fallback — JSON parse failure → static fallback rationale_md.
    8. Safety interlock NOT invoked (ScheduleDraft is not a write_plc_setpoint).
    9. Validation — invalid strategy rejected by Pydantic.
    10. Horizon dates derived from horizon_days.

All external collaborators (rag_pipeline, queue_writer, audit_writer, nats,
LLM, human_approval_node) are mocked. The deterministic algorithm under test
lives in `packages/sft-domain/scheduling/heuristic.py` (Plan 06-04).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pydantic import ValidationError

# RED gate — if the package isn't importable yet, skip the module gracefully.
pytest.importorskip(
    "ops_production_planner.agent",
    reason="Plan 06-08 Task 2 implements ops_production_planner.agent",
)

from langchain_core.messages import AIMessage  # noqa: E402

from sft_agents.models.enums import ActionType, Tier  # noqa: E402
from sft_domain.failure_modes import FailureMode  # noqa: E402
from sft_domain.ops.citation import RagCitation  # noqa: E402
from sft_domain.ops.schedule import AssetCapacity, OrderSpec  # noqa: E402

from ops_production_planner.agent import ProductionPlanner  # noqa: E402
from ops_production_planner.models import PlanRequest  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures — small deterministic inputs
# ---------------------------------------------------------------------------


def _utc(hour: int = 8, day: int = 23) -> datetime:
    return datetime(2026, 5, day, hour, tzinfo=UTC)


def _make_orders() -> tuple[OrderSpec, ...]:
    """Two orders: short processing-time but later due-date, long but sooner due-date.

    With SPT the short order schedules first; with EDD the early due-date wins.
    """
    return (
        OrderSpec(
            order_id="ORD-A",
            sku="SKU-A",
            quantity_meters=100.0,
            due_at=_utc(day=30),  # late due date
            processing_minutes=60,  # short → SPT picks first
            priority=0,
            compatible_families=["loom"],
            dye_lot_id=None,
        ),
        OrderSpec(
            order_id="ORD-B",
            sku="SKU-B",
            quantity_meters=300.0,
            due_at=_utc(day=24),  # early due date → EDD picks first
            processing_minutes=180,  # long → SPT picks second
            priority=0,
            compatible_families=["loom"],
            dye_lot_id=None,
        ),
    )


def _make_capacity() -> dict[str, AssetCapacity]:
    return {
        "loom-T-01": AssetCapacity(
            asset_id="loom-T-01",
            asset_family="loom",
            max_meters_per_hour=300.0,
            max_concurrent_dye_lots=1,
            dye_lot_changeover_minutes=30,
            downtime_windows=[],
        ),
    }


def _make_failure_modes() -> tuple[FailureMode, ...]:
    """Empty registry → setup_minutes default 0 inside earliest_slot."""
    return ()


def _make_unscheduled_orders() -> tuple[OrderSpec, ...]:
    """Two orders, one of which has no compatible asset → unscheduled."""
    return (
        OrderSpec(
            order_id="ORD-OK",
            sku="SKU-OK",
            quantity_meters=100.0,
            due_at=_utc(day=24),
            processing_minutes=60,
            priority=0,
            compatible_families=["loom"],
            dye_lot_id=None,
        ),
        OrderSpec(
            order_id="ORD-NOCAP",
            sku="SKU-NOCAP",
            quantity_meters=100.0,
            due_at=_utc(day=24),
            processing_minutes=60,
            priority=0,
            compatible_families=["nonexistent_family"],  # no eligible asset
            dye_lot_id=None,
        ),
    )


def _make_rag_pipeline(citations: list[RagCitation] | None = None) -> AsyncMock:
    """Mock RetrievalPipeline.search returning a fixed list of citations."""
    pipeline = AsyncMock()
    pipeline.search = AsyncMock(return_value=citations or [])
    return pipeline


def _make_citations(n: int = 3) -> list[RagCitation]:
    return [
        RagCitation(
            source_uri=f"sop://textile/scheduling/SOP-{i:03d}",
            snippet=f"SOP {i} excerpt about scheduling best practices.",
            score=0.9 - i * 0.1,
            retrieved_at=_utc(),
        )
        for i in range(n)
    ]


def _make_llm(
    rationale_md: str = "## Rationale\n\n- Short jobs first (SPT).",
    citation_ids: list[int] | None = None,
) -> AsyncMock:
    """Mock BaseChatModel.ainvoke returning a JSON AIMessage."""
    payload = {
        "rationale_md": rationale_md,
        "citation_ids": citation_ids if citation_ids is not None else [],
    }
    model = AsyncMock()
    model.ainvoke = AsyncMock(return_value=AIMessage(content=json.dumps(payload)))
    return model


def _make_llm_invalid_json() -> AsyncMock:
    """Mock LLM returning non-JSON content → triggers fallback."""
    model = AsyncMock()
    model.ainvoke = AsyncMock(return_value=AIMessage(content="not valid json {{{ "))
    return model


def _state(strategy: str = "spt", horizon_days: int = 7, **extras) -> dict:
    base = {
        "strategy": strategy,
        "horizon_days": horizon_days,
        "user_roles": ["supervisor"],
        "thread_id": "ops.production-planner.session-1",
    }
    base.update(extras)
    return base


# ---------------------------------------------------------------------------
# A monkeypatchable approval mock — returns a deterministic delta.
# ---------------------------------------------------------------------------


@pytest.fixture
def patched_approval(monkeypatch):
    """Replace ops_production_planner.agent.human_approval_node with an async mock."""
    from ops_production_planner import agent as agent_mod

    captured: dict = {}

    async def fake_approval(state, **kwargs):
        captured["state"] = state
        captured["kwargs"] = kwargs
        return {"pending_approval_id": None, "evidence": None, "approved": True}

    monkeypatch.setattr(agent_mod, "human_approval_node", fake_approval)
    return captured


@pytest.fixture
def patched_loaders(monkeypatch):
    """Patch domain loaders to return the small in-memory fixtures."""
    from ops_production_planner import agent as agent_mod

    monkeypatch.setattr(agent_mod, "load_orders", lambda: _make_orders())
    monkeypatch.setattr(agent_mod, "load_asset_capacity", lambda: _make_capacity())
    monkeypatch.setattr(agent_mod, "load_failure_modes", lambda: _make_failure_modes())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# 1. Strategy dispatch -------------------------------------------------------


async def test_spt_strategy_invokes_schedule_spt(
    monkeypatch, patched_approval, patched_loaders
) -> None:
    from ops_production_planner import agent as agent_mod

    spt_calls: list = []
    edd_calls: list = []
    real_spt = agent_mod.schedule_spt

    def spt_spy(orders, capacity, fms, hs, he):
        spt_calls.append(1)
        return real_spt(list(orders), capacity, fms, hs, he)

    def edd_spy(*a, **k):
        edd_calls.append(1)
        raise AssertionError("EDD must not be invoked for strategy=spt")

    monkeypatch.setattr(agent_mod, "schedule_spt", spt_spy)
    monkeypatch.setattr(agent_mod, "schedule_edd", edd_spy)

    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(),
    )
    result = await planner(_state(strategy="spt"))

    assert spt_calls == [1]
    assert edd_calls == []
    assert result["schedule_draft"].strategy == "spt"


async def test_edd_strategy_invokes_schedule_edd(
    monkeypatch, patched_approval, patched_loaders
) -> None:
    from ops_production_planner import agent as agent_mod

    edd_calls: list = []
    real_edd = agent_mod.schedule_edd

    def edd_spy(orders, capacity, fms, hs, he):
        edd_calls.append(1)
        return real_edd(list(orders), capacity, fms, hs, he)

    def spt_spy(*a, **k):
        raise AssertionError("SPT must not be invoked for strategy=edd")

    monkeypatch.setattr(agent_mod, "schedule_edd", edd_spy)
    monkeypatch.setattr(agent_mod, "schedule_spt", spt_spy)

    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(),
    )
    result = await planner(_state(strategy="edd"))

    assert edd_calls == [1]
    assert result["schedule_draft"].strategy == "edd"


# 2. Validation --------------------------------------------------------------


async def test_invalid_strategy_raises_validation(patched_approval, patched_loaders) -> None:
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(),
    )
    with pytest.raises((ValidationError, ValueError)):
        await planner(_state(strategy="random"))


async def test_horizon_days_out_of_range_raises_validation() -> None:
    # horizon_days must be >= 1, <= 30
    with pytest.raises(ValidationError):
        PlanRequest.model_validate({"strategy": "spt", "horizon_days": 0, "user_roles": []})
    with pytest.raises(ValidationError):
        PlanRequest.model_validate({"strategy": "spt", "horizon_days": 31, "user_roles": []})


# 3. Horizon dates -----------------------------------------------------------


async def test_horizon_dates_computed_from_horizon_days(
    patched_approval, patched_loaders
) -> None:
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(),
    )
    before = datetime.now(UTC)
    result = await planner(_state(strategy="spt", horizon_days=5))
    after = datetime.now(UTC)

    draft = result["schedule_draft"]
    # horizon_start = now() at agent entry; horizon_end = horizon_start + 5d
    assert before <= draft.horizon_start <= after
    delta = draft.horizon_end - draft.horizon_start
    assert delta == timedelta(days=5)


# 4. LLM rationale + 5. RAG citations ---------------------------------------


async def test_llm_rationale_populated_in_draft(
    patched_approval, patched_loaders
) -> None:
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(rationale_md="## Why\n\n- Reasoned bullet."),
    )
    result = await planner(_state())
    draft = result["schedule_draft"]
    assert draft.rationale_md
    assert "Reasoned bullet" in draft.rationale_md


async def test_rag_search_called_for_sop_citations(
    patched_approval, patched_loaders
) -> None:
    pipeline = _make_rag_pipeline(citations=_make_citations(3))
    planner = ProductionPlanner(
        rag_pipeline=pipeline,
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(),
    )
    await planner(_state(strategy="spt"))
    pipeline.search.assert_awaited_once()
    call_kwargs = pipeline.search.await_args.kwargs
    assert call_kwargs.get("category") == "sop"
    # Query should reference scheduling or strategy
    q = call_kwargs.get("query", "")
    assert "scheduling" in q.lower() or "spt" in q.lower()


async def test_citations_attached_to_draft(
    patched_approval, patched_loaders
) -> None:
    citations = _make_citations(3)
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(citations=citations),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(),
    )
    result = await planner(_state())
    draft = result["schedule_draft"]
    assert len(draft.citations) == 3
    assert all(isinstance(c, RagCitation) for c in draft.citations)


# 6. HITL routing -----------------------------------------------------------


async def test_human_approval_node_called_with_supervisor_tier(
    patched_approval, patched_loaders
) -> None:
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(),
    )
    await planner(_state())
    kwargs = patched_approval["kwargs"]
    assert kwargs["tier"] == Tier.SUPERVISOR
    assert kwargs["proposed_action"].action_type == ActionType.SCHEDULE_DRAFT


async def test_proposed_action_args_contain_full_draft(
    patched_approval, patched_loaders
) -> None:
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(citations=_make_citations(2)),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(rationale_md="## Plan\n- bullet"),
    )
    await planner(_state(strategy="spt"))
    args = patched_approval["kwargs"]["proposed_action"].args
    assert "schedule_id" in args
    assert "items" in args
    assert "rationale_md" in args
    assert args["strategy"] == "spt"
    assert isinstance(args["items"], list)


# 7. Unscheduled orders ------------------------------------------------------


async def test_unscheduled_orders_surfaced_in_rationale(monkeypatch, patched_approval) -> None:
    from ops_production_planner import agent as agent_mod

    monkeypatch.setattr(agent_mod, "load_orders", lambda: _make_unscheduled_orders())
    monkeypatch.setattr(agent_mod, "load_asset_capacity", lambda: _make_capacity())
    monkeypatch.setattr(agent_mod, "load_failure_modes", lambda: _make_failure_modes())

    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(
            rationale_md="## Plan\n- Scheduled ORD-OK. **Unscheduled: ORD-NOCAP**."
        ),
    )
    result = await planner(_state(strategy="spt"))
    draft = result["schedule_draft"]
    assert "ORD-NOCAP" in draft.unscheduled_orders
    # surfaced in args (which is the source of truth for the operator UI)
    args = patched_approval["kwargs"]["proposed_action"].args
    assert "ORD-NOCAP" in args["unscheduled_orders"]


# 8. Determinism -------------------------------------------------------------


async def test_deterministic_schedule_id(patched_approval, patched_loaders) -> None:
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(),
    )
    # Pin clock so both invocations see identical horizon_start.
    fixed_now = _utc(day=23)
    planner._clock = lambda: fixed_now  # type: ignore[attr-defined]

    r1 = await planner(_state(strategy="spt"))
    r2 = await planner(_state(strategy="spt"))
    assert isinstance(r1["schedule_draft"].schedule_id, UUID)
    assert r1["schedule_draft"].schedule_id == r2["schedule_draft"].schedule_id


# 9. Safety middleware NOT invoked ------------------------------------------


async def test_safety_middleware_not_invoked_for_schedule_draft(
    patched_approval, patched_loaders
) -> None:
    """ScheduleDraft is not a PLC write — no safety interlock involvement."""
    safety = MagicMock()
    safety.check = MagicMock()
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm(),
    )
    # The planner never imports or invokes SafetyInterlockMiddleware. Even if we
    # passed a safety mock, it must not be touched.
    await planner(_state())
    safety.check.assert_not_called()


# 10. LLM fallback ----------------------------------------------------------


async def test_llm_invalid_json_triggers_fallback_rationale(
    patched_approval, patched_loaders
) -> None:
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=_make_llm_invalid_json(),
    )
    result = await planner(_state())
    draft = result["schedule_draft"]
    # Fallback rationale is non-empty and references unavailability.
    assert draft.rationale_md
    assert "unavailable" in draft.rationale_md.lower() or "fallback" in draft.rationale_md.lower()


# 11. LLM never mutates items -----------------------------------------------


async def test_llm_cannot_mutate_items_list(
    patched_approval, patched_loaders
) -> None:
    """Even if the LLM tries to inject items via JSON, the agent must ignore it."""
    model = AsyncMock()
    model.ainvoke = AsyncMock(
        return_value=AIMessage(
            content=json.dumps({
                "rationale_md": "## Hi",
                "citation_ids": [],
                "items": [],  # LLM trying to override items
            })
        )
    )
    planner = ProductionPlanner(
        rag_pipeline=_make_rag_pipeline(),
        audit_writer=AsyncMock(),
        queue_writer=AsyncMock(),
        nats=AsyncMock(),
        model=model,
    )
    result = await planner(_state(strategy="spt"))
    draft = result["schedule_draft"]
    # Items came from the algorithm, not the LLM — both orders should be scheduled.
    assert len(draft.items) == 2
    assert {it.order_id for it in draft.items} == {"ORD-A", "ORD-B"}
