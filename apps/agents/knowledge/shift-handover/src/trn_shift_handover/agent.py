"""ShiftHandover — dual-supervisor sequential HITL LangGraph node (SC-1, D-SH-03, TRN-03).

Architecture:
    1. ``__call__(state)`` extracts ShiftWindow from state and compiles a HandoverReport
       via ShiftAggregator (LLM-free deterministic path, Pitfall §4).
    2. LLM generates a capped narrative summary (3-5 lines) from the compiled report.
    3. **Dual-supervisor sequential HITL (D-SH-03):** two interrupt() calls in order:
       a. Outgoing supervisor approval: interrupt() raises on first execution;
          on resume writes HANDOVER_SIGNOFF row #1 (motivation: outgoing).
       b. Incoming supervisor confirmation: second interrupt() raises on the same
          resumed execution; on second resume writes HANDOVER_SIGNOFF row #2
          (motivation: incoming).
    4. After both resumes: writes one HANDOVER_DRAFT row for the compiled report.
    5. Returns {"handover_report": report, "shift_status": "signed_off"}.

CR-02 fix (Phase 7): audit writes happen AFTER interrupt() returns (on resume), not before.
    - On the first execution, interrupt() raises GraphInterrupt — no audit rows written.
    - On the first resume, the first interrupt() returns; row #1 is written; the second
      interrupt() raises GraphInterrupt again.
    - On the second resume, the second interrupt() returns; rows #2 + DRAFT are written.

CR-03 fix (Phase 7): approval_id=None for pending HITL rows. Never fabricate a UUID.

CR-01 fix (Phase 7): saver is injected at construction time; raises RuntimeError if None.

WR-03 fix (Phase 7): datetime.now(timezone.utc) — always tz-aware.

AGENT_ID / CLUSTER are module-level constants.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

import structlog
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision, Tier
from sft_agents.models.evidence import EvidencePanel, TokenUsage

# Import interrupt from langgraph.types with graceful fallback (Pattern G).
# The fallback is never used in production — it exists to allow unit-test imports
# in environments that do not install the full langgraph stack.
try:
    from langgraph.types import interrupt
except ImportError:  # pragma: no cover
    def interrupt(value: Any) -> Any:  # type: ignore[misc]
        """Fallback stub — only reached in non-langgraph test environments."""
        raise NotImplementedError("langgraph.types.interrupt is not available in this environment")

from trn_shift_handover.metadata import AGENT_ID as _AGENT_ID
from trn_shift_handover.metadata import build_trn05_evidence_panel
from trn_shift_handover.models import HandoverReport, ShiftWindow

logger = structlog.get_logger("agent.shift-handover")

# ---------------------------------------------------------------------------
# Module-level constants (Shared Pattern A)
# ---------------------------------------------------------------------------

AGENT_ID: str = "shift-handover"
CLUSTER: str = "knowledge"

#: Placeholder model name for audit rows when LLM model is unknown.
_DEFAULT_MODEL_NAME: str = "unknown@shift-handover"

#: Placeholder prompt hash (64-char SHA-256 zero string).
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


def _sha256(text: str) -> str:
    """Return lowercase 64-char sha256 hex of a string (for prompt_hash)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# ShiftHandover
# ---------------------------------------------------------------------------


class ShiftHandover:
    """Dual-supervisor sequential HITL node for shift handover (D-SH-03, SC-1).

    Collaborators are injected at construction (CR-01 pattern: saver injection,
    no self-compile, no per-request instantiation).

    Dual-supervisor HITL pattern (novel in Phase 8 — no prior codebase precedent):
        interrupt(outgoing) → on resume: write row #1 (HANDOVER_SIGNOFF outgoing)
        interrupt(incoming) → on resume: write row #2 (HANDOVER_SIGNOFF incoming)
        write HANDOVER_DRAFT row (once, after both resumes)

    For tests, collaborators can be AsyncMock / MagicMock instances.
    """

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: Any,
        llm: Any,
        aggregator: Any,
        saver: Any,
    ) -> None:
        """Bind collaborators; guard saver=None per CR-01.

        Args:
            pool:         asyncpg.Pool for PG lookups (passed to aggregator).
            audit_writer: AuditWriter (written AFTER interrupt() returns — CR-02).
            llm:          BaseChatModel (LangChain-compatible); used only for narrative.
            aggregator:   ShiftAggregator instance (compile() builds HandoverReport).
            saver:        AsyncPostgresSaver (LangGraph checkpoint backend).
                          Must be injected — raises RuntimeError if None (CR-01).

        Raises:
            RuntimeError: if saver is None (CR-01 pattern B).
        """
        if saver is None:
            raise RuntimeError(
                "ShiftHandover requires a non-None saver injected at construction. "
                "Inject a pre-built AsyncPostgresSaver via the FastAPI lifespan. "
                "See api-gateway lifespan.py for the correct pattern: "
                "async with AsyncPostgresSaver.from_conn_string(pg_dsn) as saver: "
                "agent = ShiftHandover(..., saver=saver)."
            )
        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
        self._aggregator = aggregator
        self._saver = saver

    # ------------------------------------------------------------------ private

    def _thread_id(self, handover_id: str) -> str:
        """Format: {CLUSTER}.{AGENT_ID}.{handover_id}."""
        return f"{CLUSTER}.{AGENT_ID}.{handover_id}"

    def _resolve_model_name(self) -> str:
        """Extract LLM model name; fallback to default."""
        name = getattr(self._llm, "model_name", None) or getattr(
            self._llm, "model", None
        )
        return str(name) if name else _DEFAULT_MODEL_NAME

    async def _compile_report(self, state: Mapping[str, Any]) -> HandoverReport:
        """Build HandoverReport for the shift window in state.

        Extracts ShiftWindow from state["shift_window"]. If not present, builds
        one from state["shift_start"] / state["shift_end"] / state["boundary_label"]
        for backwards compatibility.

        Then calls aggregator.compile() (LLM-free deterministic path, Pitfall §4).

        Optionally appends an LLM-generated narrative summary (capped 3-5 lines).
        """
        # Extract ShiftWindow from state
        window: ShiftWindow | None = state.get("shift_window")
        if window is None:
            # Backwards-compatible construction from raw fields
            shift_start: datetime = state["shift_start"]
            shift_end: datetime = state["shift_end"]
            boundary_label: str = state.get("boundary_label", "")
            window = ShiftWindow(
                shift_start=shift_start,
                shift_end=shift_end,
                boundary_label=boundary_label,
            )

        # Compile report deterministically (LLM-free aggregation — Pitfall §4)
        report: HandoverReport = await self._aggregator.compile(window)

        # Optionally enrich with LLM narrative summary (capped, best-effort)
        if not report.narrative_summary:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage

                system_msg = SystemMessage(
                    content=(
                        "Sei un assistente di fabbrica. Fornisci un riassunto esecutivo "
                        "del turno in 3-5 righe, basandoti sui dati forniti."
                    )
                )
                human_msg = HumanMessage(
                    content=(
                        f"Turno: {window.boundary_label}\n"
                        f"Alert aperti: {report.open_alerts}\n"
                        f"Ordini di lavoro completati: {report.completed_work_orders}\n"
                        f"Fermi macchina: {report.downtime_events}\n"
                        f"Eventi qualità: {report.quality_events}\n"
                    )
                )
                llm_result = await self._llm.ainvoke([system_msg, human_msg])
                narrative = getattr(llm_result, "content", "") or str(llm_result)
                # Replace narrative_summary (frozen model — create new instance)
                report = HandoverReport(
                    shift_start=report.shift_start,
                    shift_end=report.shift_end,
                    boundary_label=report.boundary_label,
                    open_alerts=report.open_alerts,
                    completed_work_orders=report.completed_work_orders,
                    downtime_events=report.downtime_events,
                    quality_events=report.quality_events,
                    equipment_status=report.equipment_status,
                    narrative_summary=narrative[:500],
                    source_events=report.source_events,
                    citations=report.citations,
                )
            except Exception:  # noqa: BLE001
                # Narrative failure is non-blocking (Pitfall §4 — keep aggregation fast)
                logger.warning("shift_handover_narrative_failed")

        return report

    async def _write_audit(
        self,
        *,
        handover_id: str,
        report: HandoverReport,
        action_type: ActionType,
        motivation: str,
        duration_ms: int = 0,
    ) -> None:
        """Write one audit row (HANDOVER_SIGNOFF or HANDOVER_DRAFT).

        CR-02 fix: called AFTER interrupt() returns (on resume), never on first execution.
        CR-03 fix: approval_id=None — never fabricate a UUID for pending HITL rows.
        WR-03 fix: datetime.now(timezone.utc) — always tz-aware.

        Args:
            handover_id:  UUID string identifying this handover invocation.
            report:       Compiled HandoverReport (used for evidence panel summary).
            action_type:  ActionType.HANDOVER_SIGNOFF or ActionType.HANDOVER_DRAFT.
            motivation:   Human-readable motivation string (HITL-07 — required for HITL).
            duration_ms:  Elapsed milliseconds.
        """
        from uuid import UUID as _UUID

        from sft_agents.models.audit import AuditRecord
        from sft_agents.models.proposed_action import ProposedAction

        thread_id = self._thread_id(handover_id)
        model_name = self._resolve_model_name()
        # Normalise model_name to the expected pattern name@runtime
        import re as _re
        if not _re.match(r"^[a-z0-9.\-]+@[a-z0-9.\-]+$", model_name):
            model_name = f"unknown@{AGENT_ID}"

        # Build EvidencePanel (TRN-05)
        summary_raw = (
            f"shift={report.boundary_label} "
            f"alerts={report.open_alerts} "
            f"wo={report.completed_work_orders} "
            f"dt={report.downtime_events} "
            f"qe={report.quality_events}"
        )
        evidence_panel = EvidencePanel(
            input_summary=summary_raw[:500],
            input_truncated=len(summary_raw) > 500,
            tool_calls=[],
            rag_citations=[],
            confidence=1.0,
            model=model_name,
            prompt_hash=_NO_PROMPT_HASH,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=duration_ms,
        )

        # Build ProposedAction
        action = ProposedAction.from_payload(
            thread_id=thread_id,
            action_type=action_type,
            args={
                "handover_id": handover_id,
                "boundary_label": report.boundary_label,
                "open_alerts": report.open_alerts,
                "action_sub_type": action_type.value,
            },
            target_subject=None,
        )

        # Build AuditRecord (CR-03: approval_id=None, WR-03: tz-aware ts)
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
            decision_actor=None,
            motivation=motivation,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,  # CR-03: never fabricate UUID for pending HITL
        )
        await self._audit.write(record)

    # ------------------------------------------------------------------ entry-point

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """Run one shift handover turn with dual-supervisor sequential HITL (D-SH-03).

        Dual-supervisor sequential HITL pattern (new in Phase 8; no prior analog):
            1. Compile HandoverReport (LLM-free + optional narrative).
            2. interrupt(outgoing) — raises on first execution; returns on first resume.
            3. After first resume: write HANDOVER_SIGNOFF row #1 (outgoing motivation).
            4. interrupt(incoming) — raises on first resume; returns on second resume.
            5. After second resume: write HANDOVER_SIGNOFF row #2 (incoming motivation).
            6. Write HANDOVER_DRAFT row (once, after both sign-offs).
            7. Return {"handover_report": report, "shift_status": "signed_off"}.

        CR-02 guarantee: no audit rows written on the first execution (before any resume).
        CR-03 guarantee: approval_id=None on all HANDOVER_SIGNOFF rows.

        Args:
            state: LangGraph state dict. Expected keys:
                - shift_window (ShiftWindow, preferred) OR
                - shift_start + shift_end + boundary_label (datetime fields, fallback)
                - thread_id (str, optional — used for logging)

        Returns:
            State delta:
                - handover_report: compiled HandoverReport
                - shift_status: "signed_off"
        """
        start_epoch_ms = int(time.time() * 1000)

        # -------- 1. Compile HandoverReport (LLM-free aggregation — Pitfall §4)
        report = await self._compile_report(state)

        # Derive a stable handover_id across LangGraph replays (CR-04).
        # On first execution, state may not carry handover_id yet — fall back to
        # thread_id from config (stable across resumes) or generate once from uuid4.
        # On resume, the interrupt payload propagates handover_id back via state.
        handover_id = str(
            state.get("handover_id")
            or state.get("thread_id")
            or str(uuid4())
        )
        thread_id = self._thread_id(handover_id)

        logger.info(
            "shift_handover_compiled",
            handover_id=handover_id,
            boundary_label=report.boundary_label,
            open_alerts=report.open_alerts,
            downtime_events=report.downtime_events,
        )

        # -------- 2. First interrupt — outgoing supervisor (CR-02 pattern: DIRECT call)
        # On the FIRST execution, LangGraph raises GraphInterrupt here, unwinding
        # the stack. No audit rows are written on the first execution.
        # On the FIRST RESUME, this call returns the supervisor decision.
        decision_outgoing = interrupt(
            {
                "tier": Tier.SUPERVISOR.value,
                "handover_step": "outgoing_approval",
                "handover_id": handover_id,
                "payload": {
                    "boundary_label": report.boundary_label,
                    "open_alerts": report.open_alerts,
                    "completed_work_orders": report.completed_work_orders,
                    "downtime_events": report.downtime_events,
                    "quality_events": report.quality_events,
                    "narrative_summary": report.narrative_summary[:200],
                },
            }
        )

        # -------- 3. Write HANDOVER_SIGNOFF row #1 (executes ONLY on first resume)
        # CR-02: this line runs only after the first interrupt() returns.
        # CR-03: approval_id=None.
        duration_ms = int(time.time() * 1000) - start_epoch_ms
        await self._write_audit(
            handover_id=handover_id,
            report=report,
            action_type=ActionType.HANDOVER_SIGNOFF,
            motivation=f"outgoing supervisor sign-off: handover_step=outgoing_approval decision={decision_outgoing!r}",
            duration_ms=duration_ms,
        )

        logger.info(
            "shift_handover_outgoing_signoff_written",
            handover_id=handover_id,
        )

        # -------- 4. Second interrupt — incoming supervisor (sequential, not parallel)
        # On the FIRST RESUME, LangGraph raises GraphInterrupt here again, unwinding
        # the stack (after writing row #1 above).
        # On the SECOND RESUME, this call returns the incoming decision.
        decision_incoming = interrupt(
            {
                "tier": Tier.SUPERVISOR.value,
                "handover_step": "incoming_confirmation",
                "handover_id": handover_id,
                "payload": {
                    "boundary_label": report.boundary_label,
                    "open_alerts": report.open_alerts,
                    "completed_work_orders": report.completed_work_orders,
                    "downtime_events": report.downtime_events,
                    "quality_events": report.quality_events,
                    "narrative_summary": report.narrative_summary[:200],
                },
            }
        )

        # -------- 5. Write HANDOVER_SIGNOFF row #2 (executes ONLY on second resume)
        # CR-02: this line runs only after the second interrupt() returns.
        # CR-03: approval_id=None.
        duration_ms = int(time.time() * 1000) - start_epoch_ms
        await self._write_audit(
            handover_id=handover_id,
            report=report,
            action_type=ActionType.HANDOVER_SIGNOFF,
            motivation=f"incoming supervisor confirmation: handover_step=incoming_confirmation decision={decision_incoming!r}",
            duration_ms=duration_ms,
        )

        # -------- 6. Write HANDOVER_DRAFT row (once, after both sign-offs — per RF-2)
        # The draft is persisted only once the handover is fully signed off.
        # Written here (after both resumes) so it is never replayed on re-execution.
        duration_ms = int(time.time() * 1000) - start_epoch_ms
        await self._write_audit(
            handover_id=handover_id,
            report=report,
            action_type=ActionType.HANDOVER_DRAFT,
            motivation=(
                f"handover draft persisted after dual sign-off: "
                f"boundary={report.boundary_label}"
            ),
            duration_ms=duration_ms,
        )

        logger.info(
            "shift_handover_completed",
            handover_id=handover_id,
            boundary_label=report.boundary_label,
            shift_status="signed_off",
        )

        # -------- 7. Return state delta
        return {
            "handover_report": report,
            "shift_status": "signed_off",
        }


__all__ = ["AGENT_ID", "CLUSTER", "ShiftHandover"]
