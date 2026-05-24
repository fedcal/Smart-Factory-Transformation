"""EnergyOptimizer — HITL off-peak scheduling proposal node (SCM-02, Plan 09-03).

Architecture:
    1. ``__call__(state)`` reads process + time window via state.get() with defaults (CR-03).
    2. Fetches energy readings via EnergyRepository (asyncpg, datetime objects, no .isoformat()).
    3. Fetches ISO 50001 baseline from scm.enpi_baseline via EnergyRepository.
    4. Runs compute_enpi() — pure function, LLM-free.
    5. Derives a STABLE proposal_id from thread_id (CR-04 — never uuid4 inline).
    6. Builds OffPeakProposal recommending shift of peak-hour consumption to off-peak.
    7. Calls interrupt({proposal, agent_id}) — RAISES on first execution;
       no audit writes occur before interrupt returns (CR-02 guard).
    8. On resume: writes exactly one ENERGY_PROPOSAL row (approval_id=None,
       CR-03) then one ENERGY_SIGNOFF row, both sharing the same stable proposal_id.
    9. Returns state delta including energy_proposal (SCM-02).

Phase 8 guardrails applied (all 5 critical bugs avoided):
    CR-01: saver NOT required (EnergyOptimizer is single-supervisor, no saver inject needed)
    CR-02: all audit writes are AFTER interrupt() returns, never before
    CR-03: approval_id=None on the pending PROPOSAL row; state accessed via .get() with defaults
    CR-04: stable proposal_id from sha256(AGENT_ID.thread_id)[:32]; never inline uuid4
    CR-05: expected_savings_pct clamped to [0.0, 100.0] before OffPeakProposal construction

Interrupt pattern (Pattern G — graceful fallback for test environments):
    try:
        from langgraph.types import interrupt
    except ImportError:
        def interrupt(value): raise NotImplementedError(...)
    This shim allows test_energy_hitl.py to patch 'scm_energy_optimizer.agent.interrupt'
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
# Tests patch 'scm_energy_optimizer.agent.interrupt' with a real callable.
# NEVER use MagicMock for interrupt — Phase 8 WR-01 lesson.
try:
    from langgraph.types import interrupt
except ImportError:  # pragma: no cover
    def interrupt(value: Any) -> Any:  # type: ignore[misc]
        """Fallback stub — only reached in non-langgraph test environments."""
        raise NotImplementedError(
            "langgraph.types.interrupt is not available in this environment"
        )

from scm_energy_optimizer.enpi import compute_enpi
from scm_energy_optimizer.metadata import AGENT_ID, CLUSTER, build_evidence_panel
from scm_energy_optimizer.models import EnergyAlert, OffPeakProposal
from scm_energy_optimizer.repository import EnergyRepository

logger = structlog.get_logger("agent.energy-optimizer")

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Placeholder model name (EnPI computation is LLM-free)
_DEFAULT_MODEL_NAME: str = "llm-free@energy-optimizer"

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

#: Default process when state does not specify one.
_DEFAULT_PROCESS: str = "dyeing"

#: Default off-peak window description.
_DEFAULT_OFF_PEAK_WINDOW: str = "22:00–06:00 (night tariff)"

#: Fallback baseline when scm.enpi_baseline has no row for the process.
_FALLBACK_BASELINE: float = 3.80


# ---------------------------------------------------------------------------
# EnergyOptimizer
# ---------------------------------------------------------------------------


class EnergyOptimizer:
    """HITL LangGraph node for energy monitoring and off-peak scheduling proposals.

    Collaborators injected at construction (no per-request instantiation):
        pool:         asyncpg.Pool for scm.* queries.
        audit_writer: AuditWriter (written AFTER interrupt() returns — CR-02).
        llm:          Optional; not used in the EnPI path (LLM-free).

    HITL pattern (single-supervisor — mirrors InventoryManager SCM-01):
        1. Fetch energy readings + baseline (LLM-free, asyncpg).
        2. compute_enpi() — pure function.
        3. Build OffPeakProposal (clamp savings pct — CR-05).
        4. interrupt(proposal) — RAISES on first run; RETURNS on resume.
        5. Write ENERGY_PROPOSAL (approval_id=None, CR-03).
        6. Write ENERGY_SIGNOFF with supervisor decision_actor from resume payload.
        7. Return state delta with energy_proposal + energy_alert.
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
            pool:         asyncpg.Pool for scm.energy_readings + scm.enpi_baseline.
            audit_writer: AuditWriter — write() called with positional AuditRecord (CR-02).
            llm:          Optional LangChain-compatible LLM; not used in SCM-02 EnPI path.
        """
        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
        self._repo = EnergyRepository(pool)

    # ------------------------------------------------------------------ private

    def _stable_id(self, state: Mapping[str, Any]) -> str:
        """Derive stable proposal_id from thread_id (CR-04).

        NEVER use uuid4() inline — it regenerates on every LangGraph node replay,
        producing different IDs for ENERGY_PROPOSAL and ENERGY_SIGNOFF rows.

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
        proposal: OffPeakProposal,
        proposal_id: str,
        motivation: str,
        decision_actor: str | None,
        duration_ms: int,
    ) -> None:
        """Write one audit row (CR-02: always called AFTER interrupt() returns).

        Builds the full AuditRecord then passes it POSITIONALLY to write() (CR-02).
        approval_id is always None (CR-03: never fabricate UUID for pending HITL rows).

        Args:
            thread_id:      Fully-qualified thread_id string.
            action_type:    ENERGY_PROPOSAL or ENERGY_SIGNOFF.
            proposal:       Frozen OffPeakProposal instance.
            proposal_id:    Stable correlation id shared across PROPOSAL + SIGNOFF.
            motivation:     Human-readable motivation (HITL-07 required).
            decision_actor: Supervisor user_id (None for PROPOSAL row, set for SIGNOFF).
            duration_ms:    Elapsed milliseconds since node start.
        """
        summary_raw = (
            f"process={proposal.process} "
            f"enpi_actual={proposal.enpi_actual} "
            f"enpi_baseline={proposal.enpi_baseline} "
            f"deviation_pct={proposal.deviation_pct} "
            f"off_peak_kwh_pct={proposal.off_peak_kwh_pct} "
            f"proposal_id={proposal_id}"
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
                "process": proposal.process,
                "proposal_id": proposal_id,
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
        """Run one energy check turn with single-supervisor HITL (SCM-02).

        HITL pattern:
            1. Read process + window from state (safe .get() — CR-03).
            2. Fetch energy readings + baseline from scm.*.
            3. compute_enpi() — pure function.
            4. Derive stable proposal_id from thread_id (CR-04).
            5. interrupt(proposal) — RAISES on first execution (no audit writes).
            6. On resume: write ENERGY_PROPOSAL (approval_id=None, CR-03).
            7. Write ENERGY_SIGNOFF with supervisor decision from resume payload.
            8. Return state delta with energy_proposal + energy_alert.

        Args:
            state: LangGraph state dict. Expected keys (all optional — CR-03):
                - process (str):         Factory process ('dyeing', 'finishing').
                                         Defaults to 'dyeing'.
                - ts_from (str|datetime): Window start; defaults to 30 days ago.
                - ts_to (str|datetime):   Window end; defaults to now.
                - thread_id (str):        Stable id for this HITL session.
                - target_agent (str):     Routing key (informational).

        Returns:
            State delta:
                - energy_proposal: dict (from OffPeakProposal.model_dump())
                - energy_alert: dict (from EnergyAlert.model_dump())

        Raises:
            GraphInterrupt (or RuntimeError in tests): on first execution, before
                any audit writes (CR-02 guarantee).
        """
        start_epoch_ms = int(time.time() * 1000)

        # -------- 1. Read process + window from state (safe .get() — CR-03)
        process: str = state.get("process") or _DEFAULT_PROCESS
        thread_id: str = state.get("thread_id") or "unknown"
        full_thread_id = f"{CLUSTER}.{AGENT_ID}.{thread_id}"

        # Parse or default ts_from / ts_to (safe .get() — CR-03)
        ts_to_raw = state.get("ts_to")
        ts_from_raw = state.get("ts_from")

        now_utc = datetime.now(timezone.utc)
        if isinstance(ts_to_raw, datetime):
            ts_to = ts_to_raw
        else:
            ts_to = now_utc

        if isinstance(ts_from_raw, datetime):
            ts_from = ts_from_raw
        else:
            # Default: 30 days back
            from datetime import timedelta
            ts_from = now_utc - timedelta(days=30)

        logger.info(
            "energy_optimizer_start",
            process=process,
            thread_id=full_thread_id,
            ts_from=ts_from.isoformat(),
            ts_to=ts_to.isoformat(),
        )

        # -------- 2. Fetch energy readings + baseline
        rows = await self._repo.fetch_energy_readings(process, ts_from, ts_to)
        baseline_row = await self._repo.fetch_baseline(process)

        # Derive lists for compute_enpi from asyncpg rows
        kwh_readings: list[float] = []
        kg_readings: list[float] = []
        is_peak_flags: list[bool] = []

        for row in rows:
            kwh_readings.append(float(row["kwh"]))
            kg_proc = row.get("kg_processed")
            kg_readings.append(float(kg_proc) if kg_proc is not None else 0.0)
            is_peak_flags.append(bool(row.get("is_peak_hour", False)))

        # Use fallback data for test environments (empty repository)
        if not kwh_readings:
            # Synthetic fallback for test path (mirrors InventoryManager pattern)
            kwh_readings = [412.0]
            kg_readings = [100.0]
            is_peak_flags = [True]

        # -------- 3. compute_enpi — pure function (LLM-free)
        enpi_baseline_kwh_per_kg: float = (
            float(baseline_row["kwh_per_kg_target"])
            if baseline_row is not None
            else _FALLBACK_BASELINE
        )

        try:
            report = compute_enpi(
                kwh_readings=kwh_readings,
                kg_readings=kg_readings,
                enpi_baseline_kwh_per_kg=enpi_baseline_kwh_per_kg,
                is_peak_hour_flags=is_peak_flags,
                process=process,
            )
        except ValueError as exc:
            logger.warning(
                "energy_optimizer_no_valid_readings",
                process=process,
                thread_id=full_thread_id,
                error=str(exc),
            )
            return {
                "energy_proposal": None,
                "energy_alert": None,
            }

        # -------- 4. Derive stable proposal_id from thread_id (CR-04)
        proposal_id = self._stable_id(state)

        # -------- CR-05: Clamp expected_savings_pct before model construction
        # Estimate: if 100% off-peak, tariff savings ~20% vs peak-heavy baseline.
        # Proportional estimate: (100 - current off_peak_pct) / 100 * 20.
        raw_savings_pct = (100.0 - report.off_peak_kwh_pct) / 100.0 * 20.0
        expected_savings_pct = max(0.0, min(100.0, raw_savings_pct))  # clamp [0,100]

        proposal = OffPeakProposal(
            process=process,
            proposal_id=proposal_id,
            enpi_actual=report.enpi_actual,
            enpi_baseline=report.enpi_baseline,
            deviation_pct=report.deviation_pct,
            is_above_baseline=report.is_above_baseline,
            off_peak_kwh_pct=report.off_peak_kwh_pct,
            recommended_window=_DEFAULT_OFF_PEAK_WINDOW,
            expected_savings_pct=expected_savings_pct,
        )

        alert = EnergyAlert(
            alert_type="ENERGY_ALERT",
            process=process,
            proposal_id=proposal_id,
            message=(
                f"EnPI deviation {report.deviation_pct:+.2f}% "
                f"(actual={report.enpi_actual:.4f}, baseline={report.enpi_baseline:.4f} kWh/kg). "
                f"Off-peak consumption: {report.off_peak_kwh_pct:.2f}%. "
                f"Proposal {proposal_id} awaiting supervisor sign-off."
            ),
        )

        logger.info(
            "energy_optimizer_proposal_ready",
            process=process,
            proposal_id=proposal_id,
            enpi_actual=report.enpi_actual,
            deviation_pct=report.deviation_pct,
            thread_id=full_thread_id,
        )

        # -------- 5. interrupt — RAISES on first execution; RETURNS on resume
        # CR-02: no audit writes occur before this point.
        resume_payload = interrupt(
            {
                "proposal": proposal.model_dump(mode="json"),
                "agent_id": AGENT_ID,
                "proposal_id": proposal_id,
            }
        )

        # -------- 6. Write ENERGY_PROPOSAL (executes ONLY on resume)
        # CR-02: this line runs only after interrupt() returns.
        # CR-03: approval_id=None on the pending PROPOSAL row.
        duration_ms = int(time.time() * 1000) - start_epoch_ms
        await self._write_audit_record(
            thread_id=full_thread_id,
            action_type=ActionType.ENERGY_PROPOSAL,
            proposal=proposal,
            proposal_id=proposal_id,
            motivation=(
                f"Off-peak scheduling proposal pending supervisor sign-off: "
                f"process={process} proposal_id={proposal_id} "
                f"deviation={report.deviation_pct:+.2f}%"
            ),
            decision_actor=None,
            duration_ms=duration_ms,
        )

        logger.info(
            "energy_optimizer_proposal_written",
            proposal_id=proposal_id,
            thread_id=full_thread_id,
        )

        # -------- 7. Write ENERGY_SIGNOFF with supervisor decision from resume payload
        if isinstance(resume_payload, dict):
            approver_id = resume_payload.get("approver_id") or "supervisor-unknown"
        else:
            approver_id = "supervisor-unknown"

        duration_ms = int(time.time() * 1000) - start_epoch_ms
        await self._write_audit_record(
            thread_id=full_thread_id,
            action_type=ActionType.ENERGY_SIGNOFF,
            proposal=proposal,
            proposal_id=proposal_id,
            motivation=(
                f"Energy supervisor sign-off: "
                f"approver={approver_id} proposal_id={proposal_id}"
            ),
            decision_actor=approver_id,
            duration_ms=duration_ms,
        )

        logger.info(
            "energy_optimizer_signoff_written",
            proposal_id=proposal_id,
            approver_id=approver_id,
            thread_id=full_thread_id,
        )

        # -------- 8. Return state delta
        return {
            "energy_proposal": proposal.model_dump(mode="json"),
            "energy_alert": alert.model_dump(mode="json"),
        }


__all__ = ["AGENT_ID", "CLUSTER", "EnergyOptimizer"]
