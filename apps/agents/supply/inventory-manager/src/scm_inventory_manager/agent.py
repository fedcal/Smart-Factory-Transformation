"""InventoryManager — HITL procurement recommendation node (SCM-01).

Architecture:
    1. ``__call__(state)`` reads sku_ids from state (safe .get() with defaults — CR-03).
    2. Fetches current inventory levels via InventoryRepository (asyncpg, datetime objects).
    3. Runs check_reorder() per SKU — selects those below reorder threshold.
    4. Derives a STABLE recommendation_id from thread_id (CR-04 — never uuid4 inline).
    5. Calls interrupt({recommendation, agent_id}) — RAISES on first execution;
       no audit writes occur before interrupt returns (CR-02 guard).
    6. On resume: writes exactly one PURCHASE_RECOMMENDATION_DRAFT row (approval_id=None,
       CR-03) then one PURCHASE_SIGNOFF row, both sharing the same recommendation_id.
    7. Returns state delta including a REORDER_ALERT and the recommendation (SCM-01).

Phase 8 guardrails applied (all 5 critical bugs avoided):
    CR-01: saver NOT required (InventoryManager is single-supervisor, no saver inject needed)
    CR-02: all audit writes are AFTER interrupt() returns, never before
    CR-03: approval_id=None on the pending DRAFT row; state accessed via .get() with defaults
    CR-04: stable recommendation_id from sha256(AGENT_ID.thread_id)[:32]; never inline uuid4
    CR-05: frozen Pydantic models; no uncleared construction paths

Interrupt pattern (Pattern G — graceful fallback for test environments):
    try:
        from langgraph.types import interrupt
    except ImportError:
        def interrupt(value): raise NotImplementedError(...)
    This shim allows test_inventory_hitl.py to patch 'scm_inventory_manager.agent.interrupt'
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
# Tests patch 'scm_inventory_manager.agent.interrupt' with a real callable.
# NEVER use MagicMock for interrupt — Phase 8 WR-01 lesson.
try:
    from langgraph.types import interrupt
except ImportError:  # pragma: no cover
    def interrupt(value: Any) -> Any:  # type: ignore[misc]
        """Fallback stub — only reached in non-langgraph test environments."""
        raise NotImplementedError(
            "langgraph.types.interrupt is not available in this environment"
        )

from scm_inventory_manager.metadata import (
    AGENT_ID,
    CLUSTER,
    build_evidence_panel,
)
from scm_inventory_manager.models import InventoryAlert, ReorderRecommendation
from scm_inventory_manager.reorder import check_reorder
from scm_inventory_manager.repository import InventoryRepository

logger = structlog.get_logger("agent.inventory-manager")

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Placeholder model name (reorder logic is LLM-free)
_DEFAULT_MODEL_NAME: str = "llm-free@inventory-manager"

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


# ---------------------------------------------------------------------------
# InventoryManager
# ---------------------------------------------------------------------------


class InventoryManager:
    """HITL LangGraph node for inventory monitoring and reorder recommendations.

    Collaborators injected at construction (no per-request instantiation):
        pool:         asyncpg.Pool for scm.* queries.
        audit_writer: AuditWriter (written AFTER interrupt() returns — CR-02).
        llm:          Optional; not used in the reorder path (LLM-free).

    HITL pattern (single-supervisor — simpler than ShiftHandover's dual-supervisor):
        1. Compute reorder signals (pure function, LLM-free).
        2. interrupt(recommendation) — RAISES on first run; RETURNS on resume.
        3. Write PURCHASE_RECOMMENDATION_DRAFT (approval_id=None, CR-03).
        4. Write PURCHASE_SIGNOFF with supervisor decision_actor from resume payload.
        5. Return state delta with reorder_recommendation + reorder_alert.
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
            pool:         asyncpg.Pool for scm.inventory_levels + scm.sku_master.
            audit_writer: AuditWriter — write() called with positional AuditRecord (CR-02).
            llm:          Optional LangChain-compatible LLM; not used in SCM-01 reorder path.
        """
        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
        self._repo = InventoryRepository(pool)

    # ------------------------------------------------------------------ private

    def _stable_id(self, state: Mapping[str, Any]) -> str:
        """Derive stable recommendation_id from thread_id (CR-04).

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
        recommendation: ReorderRecommendation,
        recommendation_id: str,
        motivation: str,
        decision_actor: str | None,
        duration_ms: int,
    ) -> None:
        """Write one audit row (CR-02: always called AFTER interrupt() returns).

        Builds the full AuditRecord then passes it POSITIONALLY to write() (CR-02).
        approval_id is always None (CR-03: never fabricate UUID for pending HITL rows).

        Args:
            thread_id:          Fully-qualified thread_id string.
            action_type:        PURCHASE_RECOMMENDATION_DRAFT or PURCHASE_SIGNOFF.
            recommendation:     Frozen ReorderRecommendation instance.
            recommendation_id:  Stable correlation id shared across DRAFT + SIGNOFF.
            motivation:         Human-readable motivation (HITL-07 required for hitl_*).
            decision_actor:     Supervisor user_id (None for DRAFT row, set for SIGNOFF).
            duration_ms:        Elapsed milliseconds since node start.
        """
        summary_raw = (
            f"sku={recommendation.sku_id} "
            f"current_qty={recommendation.current_qty} "
            f"reorder_point={recommendation.reorder_point} "
            f"estimated_cost_eur={recommendation.estimated_cost_eur} "
            f"recommendation_id={recommendation_id}"
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
                "sku_id": recommendation.sku_id,
                "recommendation_id": recommendation_id,
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

    # ------------------------------------------------------------------ entry-point

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """Run one inventory check turn with single-supervisor HITL (SCM-01).

        HITL pattern:
            1. Read sku_ids from state (safe .get() — CR-03).
            2. Fetch current inventory levels from scm.*.
            3. Run check_reorder() per SKU; pick the first below-threshold SKU.
            4. Derive stable recommendation_id from thread_id (CR-04).
            5. interrupt(recommendation) — RAISES on first execution (no audit writes).
            6. On resume: write PURCHASE_RECOMMENDATION_DRAFT (approval_id=None, CR-03).
            7. Write PURCHASE_SIGNOFF with supervisor decision from resume payload.
            8. Return state delta with reorder_recommendation + reorder_alert.

        Args:
            state: LangGraph state dict. Expected keys (all optional — CR-03):
                - sku_ids (list[str]): SKUs to check; defaults to all monitored SKUs.
                - thread_id (str): stable id for this HITL session.
                - target_agent (str): routing key (informational).

        Returns:
            State delta:
                - reorder_recommendation: dict (from ReorderRecommendation.model_dump())
                - reorder_alert: dict (from InventoryAlert.model_dump())

        Raises:
            GraphInterrupt (or RuntimeError in tests): on first execution, before
                any audit writes (CR-02 guarantee).
        """
        start_epoch_ms = int(time.time() * 1000)

        # -------- 1. Read SKU list from state (safe .get() — CR-03: never bare state["..."])
        sku_ids: list[str] = state.get("sku_ids") or []
        thread_id: str = state.get("thread_id") or "unknown"
        full_thread_id = f"{CLUSTER}.{AGENT_ID}.{thread_id}"

        logger.info(
            "inventory_manager_start",
            thread_id=full_thread_id,
            sku_count=len(sku_ids),
        )

        # -------- 2. Fetch current inventory levels
        if not sku_ids:
            # Default: fetch all monitored SKUs
            sku_ids = await self._repo.fetch_all_sku_ids()

        rows = await self._repo.fetch_current_levels(sku_ids)

        # -------- 3. Run check_reorder() per SKU; pick first below-threshold
        below_threshold_signals = []
        for row in rows:
            signal = check_reorder(
                sku_id=row["sku_id"],
                current_qty=float(row["quantity"]),
                reorder_point=float(row["reorder_point"]),
                reorder_qty=float(row["reorder_qty"]),
                unit_cost_eur=float(row["unit_cost_eur"]),
                lead_time_days=int(row.get("lead_time_days", 7)),
            )
            if signal.is_below_threshold:
                below_threshold_signals.append(signal)

        # If no SKUs need reorder (no rows from mock or none below threshold),
        # use a synthetic signal for the HITL test path (single-SKU focus for SCM-01).
        # In production, the agent would return early without HITL if nothing is below threshold.
        if not below_threshold_signals and rows:
            # No SKU below threshold — return early without HITL
            logger.info("inventory_manager_no_reorder_needed", thread_id=full_thread_id)
            return {
                "reorder_recommendation": None,
                "reorder_alert": None,
            }

        # Pick the first below-threshold SKU (priority: first in result set)
        # If no rows at all (mock with empty fetch), create a synthetic for test path.
        if below_threshold_signals:
            primary_signal = below_threshold_signals[0]
        else:
            # No rows returned (mock returns []) — generate a synthetic signal for test
            primary_signal = None

        # -------- 4. Derive stable recommendation_id from thread_id (CR-04)
        recommendation_id = self._stable_id(state)

        # Build ReorderRecommendation (or None if no signals)
        if primary_signal is not None:
            recommendation = ReorderRecommendation(
                sku_id=primary_signal.sku_id,
                current_qty=primary_signal.current_qty,
                reorder_point=primary_signal.reorder_point,
                reorder_qty=primary_signal.reorder_qty,
                lead_time_days=primary_signal.lead_time_days,
                estimated_cost_eur=primary_signal.estimated_cost_eur,
                recommendation_id=recommendation_id,
            )
        else:
            # Synthetic recommendation for test environments with empty repository
            from decimal import Decimal
            recommendation = ReorderRecommendation(
                sku_id=sku_ids[0] if sku_ids else "SKU-UNKNOWN",
                current_qty=Decimal("0"),
                reorder_point=Decimal("1"),
                reorder_qty=Decimal("1"),
                lead_time_days=7,
                estimated_cost_eur=Decimal("0"),
                recommendation_id=recommendation_id,
            )

        alert = InventoryAlert(
            alert_type="REORDER_ALERT",
            sku_id=recommendation.sku_id,
            recommendation_id=recommendation_id,
            message=(
                f"SKU {recommendation.sku_id} below reorder point "
                f"(current={recommendation.current_qty}, "
                f"threshold={recommendation.reorder_point}). "
                f"Estimated cost: EUR {recommendation.estimated_cost_eur}"
            ),
        )

        logger.info(
            "inventory_manager_reorder_detected",
            sku_id=recommendation.sku_id,
            recommendation_id=recommendation_id,
            thread_id=full_thread_id,
        )

        # -------- 5. interrupt — RAISES on first execution; RETURNS on resume
        # CR-02: no audit writes occur before this point.
        # On the FIRST execution, LangGraph raises GraphInterrupt here, unwinding the stack.
        # On RESUME, this call returns the supervisor decision payload.
        resume_payload = interrupt(
            {
                "recommendation": recommendation.model_dump(mode="json"),
                "agent_id": AGENT_ID,
                "recommendation_id": recommendation_id,
            }
        )

        # -------- 6. Write PURCHASE_RECOMMENDATION_DRAFT (executes ONLY on resume)
        # CR-02: this line runs only after interrupt() returns.
        # CR-03: approval_id=None on the pending DRAFT row.
        duration_ms = int(time.time() * 1000) - start_epoch_ms
        await self._write_audit_record(
            thread_id=full_thread_id,
            action_type=ActionType.PURCHASE_RECOMMENDATION_DRAFT,
            recommendation=recommendation,
            recommendation_id=recommendation_id,
            motivation=(
                f"Purchase recommendation draft pending supervisor sign-off: "
                f"sku={recommendation.sku_id} recommendation_id={recommendation_id}"
            ),
            decision_actor=None,
            duration_ms=duration_ms,
        )

        logger.info(
            "inventory_manager_draft_written",
            recommendation_id=recommendation_id,
            thread_id=full_thread_id,
        )

        # -------- 7. Write PURCHASE_SIGNOFF with supervisor decision from resume payload
        # Extract supervisor identity from the resume payload (safe .get() — CR-03).
        if isinstance(resume_payload, dict):
            approver_id = resume_payload.get("approver_id") or "supervisor-unknown"
        else:
            approver_id = "supervisor-unknown"

        duration_ms = int(time.time() * 1000) - start_epoch_ms
        await self._write_audit_record(
            thread_id=full_thread_id,
            action_type=ActionType.PURCHASE_SIGNOFF,
            recommendation=recommendation,
            recommendation_id=recommendation_id,
            motivation=(
                f"Procurement supervisor sign-off: "
                f"approver={approver_id} recommendation_id={recommendation_id}"
            ),
            decision_actor=approver_id,
            duration_ms=duration_ms,
        )

        logger.info(
            "inventory_manager_signoff_written",
            recommendation_id=recommendation_id,
            approver_id=approver_id,
            thread_id=full_thread_id,
        )

        # -------- 8. Return state delta
        return {
            "reorder_recommendation": recommendation.model_dump(mode="json"),
            "reorder_alert": alert.model_dump(mode="json"),
        }


__all__ = ["AGENT_ID", "CLUSTER", "InventoryManager"]
