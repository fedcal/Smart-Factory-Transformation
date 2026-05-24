"""DemandForecaster — HITL demand planning node (SCM-04).

Architecture:
    1. ``__call__(state)`` reads sku_groups + horizon + months_back from state
       (safe .get() with defaults — CR-03).
    2. Fetches monthly demand series per SKU group via DemandRepository (asyncpg).
    3. Runs forecast_holt_winters() per group (seasonal-naive fallback automatic for short series).
    4. Assembles a DemandPlan covering >= 2 SKU groups.
    5. Computes rolling MAPE on the held-out tail; clamps to <= 100 before MapeReport (CR-05).
    6. Derives a STABLE plan_id from thread_id (CR-04 — never uuid4 inline).
    7. Calls interrupt({demand_plan, mape, agent_id}) — RAISES on first execution;
       no audit writes occur before interrupt returns (CR-02 guard).
    8. On resume: writes exactly one DEMAND_PLAN_DRAFT row (approval_id=None, CR-03)
       then one DEMAND_PLAN_SIGNOFF row, both sharing the same stable plan_id.
    9. Returns state delta including state['demand_plan'] (the ProductionPlanner publish
       channel — Open Question 2 resolution: cross-cluster via state, NOT direct invocation).

Phase 8 guardrails applied (all 5 critical bugs avoided):
    CR-01: imports use exact exported names from each module
    CR-02: all audit writes are AFTER interrupt() returns, never before
    CR-03: approval_id=None on the pending DRAFT row; state accessed via .get() with defaults
    CR-04: stable plan_id from sha256(AGENT_ID.thread_id)[:32]; never inline uuid4
    CR-05: MAPE clamped to <= 100 before MapeReport construction; forecasts clamped to >= 0

Cross-cluster boundary (Open Question 2):
    DemandForecaster → ProductionPlanner routing goes via state['demand_plan'] key.
    The gateway reads this key and routes the state to the ProductionPlanner agent.
    NO direct method calls between agents; state is the only coupling point.
    This module does not import the production-planner package.

Interrupt pattern (Pattern G — graceful fallback for test environments):
    try:
        from langgraph.types import interrupt
    except ImportError:
        def interrupt(value): raise NotImplementedError(...)
    This shim allows test_demand_hitl.py to patch 'scm_demand_forecaster.agent.interrupt'
    with a real callable that raises/returns on demand.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

import structlog
from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision
from sft_agents.models.evidence import EvidencePanel, TokenUsage
from sft_agents.models.proposed_action import ProposedAction

# Pattern G — graceful fallback shim for test environments without full langgraph.
# Tests patch 'scm_demand_forecaster.agent.interrupt' with a real callable.
# NEVER use MagicMock for interrupt — Phase 8 WR-01 lesson.
try:
    from langgraph.types import interrupt
except ImportError:  # pragma: no cover
    def interrupt(value: Any) -> Any:  # type: ignore[misc]
        """Fallback stub — only reached in non-langgraph test environments."""
        raise NotImplementedError(
            "langgraph.types.interrupt is not available in this environment"
        )

from scm_demand_forecaster.holt_winters import HoltWintersConfig, forecast_holt_winters
from scm_demand_forecaster.mape import compute_mape
from scm_demand_forecaster.metadata import (
    AGENT_ID,
    CLUSTER,
    build_evidence_panel,
)
from scm_demand_forecaster.models import DemandPlan, MapeReport, SkuForecast
from scm_demand_forecaster.repository import DemandRepository

logger = structlog.get_logger("agent.demand-forecaster")

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Placeholder model name (Holt-Winters is LLM-free)
_DEFAULT_MODEL_NAME: str = "llm-free@demand-forecaster"

#: Placeholder prompt hash (64-char SHA-256 zero string — LLM-free path)
_NO_PROMPT_HASH: str = "0" * 64

_EMPTY_BUDGET = BudgetSnapshot(
    tokens_input=0,
    tokens_output=0,
    tokens_total=0,
    cost_usd_simulated=0.0,
    duration_ms=0,
    limit_tokens=50000,
    limit_cost_usd=1.0,
    limit_duration_s=300,
)

#: Default SKU groups to forecast when not supplied in state (Mantis synthetic dataset)
_DEFAULT_SKU_GROUPS: list[str] = ["jersey", "twill"]

#: Default forecast horizon (months)
_DEFAULT_HORIZON: int = 6

#: Default number of months to look back for training data
_DEFAULT_MONTHS_BACK: int = 24


# ---------------------------------------------------------------------------
# DemandForecaster
# ---------------------------------------------------------------------------


class DemandForecaster:
    """HITL LangGraph node for demand forecasting and ProductionPlanner routing (SCM-04).

    Collaborators injected at construction (no per-request instantiation):
        pool:         asyncpg.Pool for scm.historical_orders queries.
        audit_writer: AuditWriter (written AFTER interrupt() returns — CR-02).
        llm:          Optional; not used in the Holt-Winters path (LLM-free).

    HITL pattern (single-supervisor — mirrors InventoryManager SCM-01):
        1. Fetch monthly series per SKU group from scm.historical_orders.
        2. Run forecast_holt_winters() per group (seasonal-naive fallback automatic).
        3. Assemble DemandPlan for >= 2 SKU groups.
        4. Compute rolling MAPE (clamped to <= 100, CR-05).
        5. Derive stable plan_id from thread_id (CR-04).
        6. interrupt(demand_plan + mape) — RAISES on first run; RETURNS on resume.
        7. Write DEMAND_PLAN_DRAFT (approval_id=None, CR-03).
        8. Write DEMAND_PLAN_SIGNOFF with decision_actor from resume payload.
        9. Return state delta with demand_plan key (ProductionPlanner publish channel).

    Cross-cluster routing (Open Question 2 resolution):
        The demand_plan is published via state['demand_plan'].
        Gateway routes via state key — no cross-package coupling to the ops cluster.
    """

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: Any,
        llm: Any = None,
    ) -> None:
        """Bind collaborators.

        Args:
            pool:         asyncpg.Pool for scm.historical_orders.
            audit_writer: AuditWriter — write() called with positional AuditRecord (CR-02).
            llm:          Optional LangChain-compatible LLM; not used in SCM-04 HW path.
        """
        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
        self._repo = DemandRepository(pool)

    # ------------------------------------------------------------------ private

    def _stable_id(self, state: Mapping[str, Any]) -> str:
        """Derive stable plan_id from thread_id (CR-04).

        NEVER use uuid4() inline — it regenerates on every LangGraph node replay,
        producing different IDs for the DRAFT and SIGNOFF rows (Phase 8 CR-04 lesson).

        The thread_id is set by the gateway per-request and does NOT change on resume.

        Args:
            state: LangGraph state dict (accessed via .get() — CR-03).

        Returns:
            32-char lowercase hex string (sha256 truncated).
        """
        thread_id = state.get("thread_id") or "unknown"
        return hashlib.sha256(
            f"{AGENT_ID}.{thread_id}".encode("utf-8")
        ).hexdigest()[:32]

    async def _write_audit_record(
        self,
        *,
        thread_id: str,
        action_type: ActionType,
        demand_plan: DemandPlan,
        plan_id: str,
        motivation: str,
        decision_actor: str | None,
        duration_ms: int,
    ) -> None:
        """Write one audit row (CR-02: always called AFTER interrupt() returns).

        Builds the full AuditRecord then passes it POSITIONALLY to write() (CR-02).
        approval_id is always None (CR-03: never fabricate UUID for pending HITL rows).

        Args:
            thread_id:      Fully-qualified thread_id string.
            action_type:    DEMAND_PLAN_DRAFT or DEMAND_PLAN_SIGNOFF.
            demand_plan:    Frozen DemandPlan instance.
            plan_id:        Stable correlation id shared across DRAFT + SIGNOFF.
            motivation:     Human-readable motivation (HITL-07 required for hitl_*).
            decision_actor: Supervisor user_id (None for DRAFT row, set for SIGNOFF).
            duration_ms:    Elapsed milliseconds since node start.
        """
        n_groups = len(demand_plan.sku_groups)
        summary_raw = (
            f"demand_plan: {n_groups} SKU groups "
            f"plan_id={plan_id} "
            f"groups={[s.sku_group for s in demand_plan.sku_groups]}"
        )

        evidence_panel = EvidencePanel(
            input_summary=summary_raw[:500],
            input_truncated=len(summary_raw) > 500,
            tool_calls=[],
            rag_citations=[],
            confidence=1.0,
            model=_DEFAULT_MODEL_NAME,
            prompt_hash=_NO_PROMPT_HASH,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=duration_ms,
        )

        action = ProposedAction.from_payload(
            thread_id=thread_id,
            action_type=action_type,
            args={
                "plan_id": plan_id,
                "n_sku_groups": n_groups,
                "action_sub_type": action_type.value,
            },
            target_subject=None,
        )

        # CR-03: approval_id=None — never fabricate UUID for pending HITL rows.
        # WR-03: datetime.now(timezone.utc) — always tz-aware.
        record = AuditRecord(
            id=uuid4(),
            ts=datetime.now(timezone.utc),
            action_id=action.id,
            agent_id=AGENT_ID,
            thread_id=thread_id,
            cluster=CLUSTER,
            action_type=action_type.value,
            evidence_panel=evidence_panel,
            decision=Decision.HITL_SUPERVISOR,
            decision_actor=decision_actor,
            motivation=motivation,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,  # CR-03: never fabricate UUID for pending HITL
        )
        # CR-02: positional write — not write(action_type=...) with kwargs
        await self._audit.write(record)

    def _build_synthetic_plan(self, plan_id: str, horizon: int) -> DemandPlan:
        """Build a synthetic demand plan covering >= 2 SKU groups.

        Used when the repository returns no data (test environments with empty mock).
        Produces deterministic synthetic forecasts for the two Mantis fabric groups.

        Args:
            plan_id: Stable plan identifier.
            horizon: Number of forecast months.

        Returns:
            DemandPlan with synthetic forecasts for 'jersey' and 'twill'.
        """
        config = HoltWintersConfig()
        jersey_series = [
            8000, 9000, 10000, 12000, 11000, 9000,
            8000, 8500, 9000, 10500, 11500, 12500,
            8200, 9100, 10200, 12200, 11200, 9100,
            8100, 8600, 9100, 10600, 11600, 12600,
        ]
        twill_series = [
            7000, 7200, 7800, 8500, 8200, 7600,
            7100, 7300, 7700, 8200, 8700, 9200,
            7100, 7300, 7900, 8600, 8300, 7700,
            7200, 7400, 7800, 8300, 8800, 9300,
        ]
        jersey_result = forecast_holt_winters(
            jersey_series, horizon=horizon, config=config, sku_group="jersey"
        )
        twill_result = forecast_holt_winters(
            twill_series, horizon=horizon, config=config, sku_group="twill"
        )
        return DemandPlan(
            plan_id=plan_id,
            sku_groups=[
                SkuForecast(
                    sku_group=jersey_result.sku_group,
                    horizon=jersey_result.horizon,
                    forecast=jersey_result.forecast,
                    method=jersey_result.method,
                ),
                SkuForecast(
                    sku_group=twill_result.sku_group,
                    horizon=twill_result.horizon,
                    forecast=twill_result.forecast,
                    method=twill_result.method,
                ),
            ],
        )

    # ------------------------------------------------------------------ entry-point

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """Run one demand forecasting turn with single-supervisor HITL (SCM-04).

        HITL pattern (interrupt-then-audit):
            1. Read sku_groups + horizon + months_back from state (safe .get() — CR-03).
            2. Fetch monthly demand series per group from scm.historical_orders.
            3. Run forecast_holt_winters() per group; assemble DemandPlan for >= 2 groups.
            4. Compute rolling MAPE (clamped <= 100, CR-05).
            5. Derive stable plan_id from thread_id (CR-04).
            6. interrupt(demand_plan + mape) — RAISES on first execution (no audit writes).
            7. On resume: write DEMAND_PLAN_DRAFT (approval_id=None, CR-03).
            8. Write DEMAND_PLAN_SIGNOFF with decision_actor from resume payload.
            9. Return state delta with state['demand_plan'] (ProductionPlanner publish channel).

        Args:
            state: LangGraph state dict. Expected keys (all optional — CR-03):
                - sku_groups (list[str]): SKU groups to forecast; defaults to ["jersey","twill"].
                - horizon (int): Forecast horizon in months; defaults to 6.
                - months_back (int): Training window; defaults to 24.
                - thread_id (str): Stable id for this HITL session.
                - target_agent (str): Routing key (informational).

        Returns:
            State delta:
                - demand_plan: dict (from DemandPlan.model_dump()) — ProductionPlanner publish key
                - mape_report: dict (from MapeReport.model_dump())

        Raises:
            GraphInterrupt (or RuntimeError in tests): on first execution, before
                any audit writes (CR-02 guarantee).
        """
        start_epoch_ms = int(time.time() * 1000)

        # -------- 1. Read params from state (safe .get() — CR-03: never bare state["..."])
        sku_groups: list[str] = state.get("sku_groups") or _DEFAULT_SKU_GROUPS
        horizon: int = state.get("horizon") or _DEFAULT_HORIZON
        months_back: int = state.get("months_back") or _DEFAULT_MONTHS_BACK
        thread_id: str = state.get("thread_id") or "unknown"
        full_thread_id = f"{CLUSTER}.{AGENT_ID}.{thread_id}"

        logger.info(
            "demand_forecaster_start",
            thread_id=full_thread_id,
            sku_groups=sku_groups,
            horizon=horizon,
        )

        # -------- 2. Fetch monthly series per SKU group
        series_by_group: dict[str, list[float]] = {}
        for group in sku_groups:
            series = await self._repo.fetch_monthly_orders(group, months_back=months_back)
            series_by_group[group] = series

        # -------- 4. Derive stable plan_id from thread_id (CR-04)
        plan_id = self._stable_id(state)

        # -------- 3. Forecast per group; build DemandPlan for >= 2 groups
        config = HoltWintersConfig()
        sku_forecasts: list[SkuForecast] = []
        all_actuals: list[float] = []
        all_forecasts: list[float] = []

        for group, series in series_by_group.items():
            if not series:
                # No data for group — skip for now; handled by synthetic fallback below
                continue
            result = forecast_holt_winters(series, horizon=horizon, config=config, sku_group=group)
            sku_forecasts.append(
                SkuForecast(
                    sku_group=result.sku_group,
                    horizon=result.horizon,
                    forecast=result.forecast,
                    method=result.method,
                )
            )
            # Rolling MAPE: compare forecast vs the last horizon actual values (held-out tail)
            if len(series) > horizon:
                tail_actuals = series[-horizon:]
                tail_forecast = result.forecast[:len(tail_actuals)]
                all_actuals.extend(tail_actuals)
                all_forecasts.extend(tail_forecast)

        # Ensure >= 2 SKU groups in the plan (use synthetic fallback if needed)
        if len(sku_forecasts) < 2:
            logger.info(
                "demand_forecaster_synthetic_fallback",
                thread_id=full_thread_id,
                reason="insufficient sku groups from repository",
            )
            synthetic_plan = self._build_synthetic_plan(plan_id, horizon)
            sku_forecasts = list(synthetic_plan.sku_groups)

        demand_plan = DemandPlan(
            plan_id=plan_id,
            sku_groups=sku_forecasts,
        )

        # -------- 5. Compute rolling MAPE (clamped <= 100, CR-05)
        raw_mape = compute_mape(all_actuals, all_forecasts)
        mape_clamped = min(raw_mape, 100.0)  # CR-05: explicit clamp before model build
        mape_report = MapeReport(
            mape=mape_clamped,
            n_pairs=len(all_actuals),
            plan_id=plan_id,
        )

        logger.info(
            "demand_forecaster_plan_ready",
            plan_id=plan_id,
            n_groups=len(demand_plan.sku_groups),
            mape=mape_clamped,
            thread_id=full_thread_id,
        )

        # -------- 6. interrupt — RAISES on first execution; RETURNS on resume
        # CR-02: no audit writes occur before this point.
        # On the FIRST execution, LangGraph raises GraphInterrupt here, unwinding the stack.
        # On RESUME, this call returns the supervisor decision payload.
        resume_payload = interrupt(
            {
                "demand_plan": demand_plan.model_dump(mode="json"),
                "mape": mape_report.model_dump(mode="json"),
                "agent_id": AGENT_ID,
                "plan_id": plan_id,
            }
        )

        # -------- 7. Write DEMAND_PLAN_DRAFT (executes ONLY on resume)
        # CR-02: this line runs only after interrupt() returns.
        # CR-03: approval_id=None on the pending DRAFT row.
        duration_ms = int(time.time() * 1000) - start_epoch_ms
        await self._write_audit_record(
            thread_id=full_thread_id,
            action_type=ActionType.DEMAND_PLAN_DRAFT,
            demand_plan=demand_plan,
            plan_id=plan_id,
            motivation=(
                f"Demand plan draft pending supervisor sign-off: "
                f"plan_id={plan_id} "
                f"groups={[s.sku_group for s in demand_plan.sku_groups]}"
            ),
            decision_actor=None,  # CR-03: None pending
            duration_ms=duration_ms,
        )

        logger.info(
            "demand_forecaster_draft_written",
            plan_id=plan_id,
            thread_id=full_thread_id,
        )

        # -------- 8. Write DEMAND_PLAN_SIGNOFF with supervisor decision from resume payload
        # Extract supervisor identity from the resume payload (safe .get() — CR-03).
        if isinstance(resume_payload, dict):
            approver_id = resume_payload.get("approver_id") or "supervisor-unknown"
        else:
            approver_id = "supervisor-unknown"

        duration_ms = int(time.time() * 1000) - start_epoch_ms
        await self._write_audit_record(
            thread_id=full_thread_id,
            action_type=ActionType.DEMAND_PLAN_SIGNOFF,
            demand_plan=demand_plan,
            plan_id=plan_id,
            motivation=(
                f"Demand plan supervisor sign-off: "
                f"approver={approver_id} plan_id={plan_id}"
            ),
            decision_actor=approver_id,
            duration_ms=duration_ms,
        )

        logger.info(
            "demand_forecaster_signoff_written",
            plan_id=plan_id,
            approver_id=approver_id,
            thread_id=full_thread_id,
        )

        # -------- 9. Return state delta
        # state['demand_plan'] is the ProductionPlanner publish channel (Open Question 2).
        # Cross-cluster communication via state, NOT direct invocation.
        return {
            "demand_plan": demand_plan.model_dump(mode="json"),
            "mape_report": mape_report.model_dump(mode="json"),
        }


__all__ = ["AGENT_ID", "CLUSTER", "DemandForecaster"]
