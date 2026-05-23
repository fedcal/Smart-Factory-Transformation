"""QualityInspector agent — severity -> HITL tier routing (D-QI-03).

Orchestrates a single QualityEvent through:

    1. ``grade_quality_event(...)`` -> QualityVerdict (LLM-graded, conservative
       fallback on ValidationError).
    2. ``_resolve_tier(defect_type, severity)`` consults
       ``failure_modes.yaml`` for a per-defect override; otherwise applies
       the default severity -> tier mapping
       (minor -> None, major -> SUPERVISOR, critical -> MANAGER+SAFETY).
    3. Dispatch:
          - tier == None        -> write Decision.AUTO audit row (no HITL).
          - tier == SUPERVISOR  -> human_approval_node tier=SUPERVISOR.
          - tier == MANAGER     -> SafetyInterlockMiddleware.check +
                                    human_approval_node tier=MANAGER.

dye_lot_id is included in every ProposedAction.args and audit row payload
(D-QI-04 invariant: every quality event carries a dye lot for traceability).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

import structlog
from sft_agents.audit.writer import AuditWriter
from sft_agents.hitl.interrupt import human_approval_node
from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision, Tier
from sft_agents.models.evidence import EvidencePanel, TokenUsage, ToolCall
from sft_agents.models.proposed_action import ProposedAction
from sft_agents.policies.safety_interlock import SafetyInterlockMiddleware
from sft_domain.failure_modes import load_failure_modes_dict
from sft_domain.ops.quality import QualityEvent, QualityVerdict

from ops_quality_inspector.grader import grade_quality_event
from ops_quality_inspector.models import QualityInspectionResponse

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

logger = structlog.get_logger("agent.quality-inspector")


HitlTier = Literal["auto-log", "supervisor", "manager+safety"]


# Default severity -> HitlTier mapping (D-QI-03). The failure_modes.yaml
# hitl_tier field overrides this on a per-defect basis.
_DEFAULT_SEVERITY_TIER: dict[str, HitlTier] = {
    "minor": "auto-log",
    "major": "supervisor",
    "critical": "manager+safety",
}


# Placeholder evidence-panel constants used for log-only / agent-context audit
# rows; mirrors LogEventTool conventions in sft_agents.tools.audit.
_LOG_ONLY_MODEL: str = "log-only@quality-inspector"
_NO_PROMPT_HASH: str = "0" * 64
_EMPTY_BUDGET = BudgetSnapshot(
    tokens_input=0,
    tokens_output=0,
    tokens_total=0,
    cost_usd_simulated=0.0,
    duration_ms=0,
    limit_tokens=50000,
    limit_cost_usd=1.0,
    limit_duration_s=60,
)


def _resolve_tier(
    defect_type: str, severity: str, *, failure_modes: dict[str, Any] | None = None
) -> HitlTier:
    """Resolve the HITL tier for a (defect_type, severity) pair.

    The failure_modes.yaml ``hitl_tier`` override wins over the default
    severity-band mapping. If the defect_type is unknown, fall back to the
    default severity mapping.
    """
    fms = failure_modes if failure_modes is not None else load_failure_modes_dict()
    entry = fms.get(defect_type)
    if entry is not None and getattr(entry, "hitl_tier", None) in (
        "auto-log",
        "supervisor",
        "manager+safety",
    ):
        # YAML override - but only "escalate" never "de-escalate". A YAML
        # configured 'auto-log' should not be allowed to swallow a critical
        # severity; pick the stricter tier.
        yaml_tier: HitlTier = entry.hitl_tier  # type: ignore[assignment]
        default_tier: HitlTier = _DEFAULT_SEVERITY_TIER.get(severity, "supervisor")
        return _max_tier(yaml_tier, default_tier)
    return _DEFAULT_SEVERITY_TIER.get(severity, "supervisor")


_TIER_RANK: dict[HitlTier, int] = {
    "auto-log": 0,
    "supervisor": 1,
    "manager+safety": 2,
}


def _max_tier(a: HitlTier, b: HitlTier) -> HitlTier:
    """Return the stricter of two HitlTier values."""
    return a if _TIER_RANK[a] >= _TIER_RANK[b] else b


class QualityInspector:
    """Orchestrates grade -> resolve_tier -> dispatch (auto-log | HITL).

    Collaborators are injected at construction; all of them are kept as
    private attributes (no PrivateAttr because this is not a pydantic model).
    """

    def __init__(
        self,
        *,
        rag_pipeline: Any,
        audit_writer: AuditWriter,
        queue_writer: Any,
        nats_publisher: Any,
        safety_middleware: SafetyInterlockMiddleware,
        pool: Any,
        agent_id: str = "quality-inspector",
        cluster: str = "ops",
        model: "BaseChatModel | None" = None,
    ) -> None:
        self._rag = rag_pipeline
        self._audit = audit_writer
        self._queue = queue_writer
        self._nats = nats_publisher
        self._safety = safety_middleware
        self._pool = pool
        self._agent_id = agent_id
        self._cluster = cluster
        self._model = model

    async def handle_event(
        self, event: QualityEvent, *, user_roles: list[str] | None = None
    ) -> QualityInspectionResponse:
        """Grade + route a single QualityEvent.

        Returns a QualityInspectionResponse capturing the verdict and the
        resolved HITL tier so callers (e.g. the NATS consumer) can log
        outcome metrics.
        """
        verdict = await grade_quality_event(
            event,
            rag_pipeline=self._rag,
            model=self._model,
            user_roles=user_roles,
        )
        tier_str: HitlTier = _resolve_tier(event.defect_type, verdict.severity)

        if tier_str == "auto-log":
            await self._write_auto_audit(event, verdict)
        elif tier_str == "supervisor":
            await self._dispatch_hitl(
                event, verdict, tier=Tier.SUPERVISOR, run_safety_check=False
            )
        else:  # manager+safety
            await self._dispatch_hitl(
                event, verdict, tier=Tier.MANAGER, run_safety_check=True
            )

        logger.info(
            "quality_event_handled",
            event_id=str(event.event_id),
            asset_id=event.asset_id,
            dye_lot_id=event.dye_lot_id,
            defect_type=event.defect_type,
            severity=verdict.severity,
            score=verdict.score,
            hitl_routed_to=tier_str,
        )
        return QualityInspectionResponse(verdict=verdict, hitl_routed_to=tier_str)

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _thread_id(self, event: QualityEvent) -> str:
        """D-59 thread_id format: {cluster}.{agent_id}.{session_uuid}."""
        return f"{self._cluster}.{self._agent_id}.{event.event_id}"

    def _build_proposed_action(
        self, event: QualityEvent, verdict: QualityVerdict
    ) -> ProposedAction:
        """Build a deterministic ProposedAction for HITL routing.

        ``dye_lot_id`` and ``asset_id`` are injected into args so the
        forensic trail in audit.actions includes the lot context.
        """
        args = {
            "verdict": verdict.model_dump(mode="json"),
            "event": {
                "event_id": str(event.event_id),
                "asset_id": event.asset_id,
                "dye_lot_id": event.dye_lot_id,
                "defect_type": event.defect_type,
                "defect_length_inches": event.defect_length_inches,
                "full_width": event.full_width,
                "position_meters": event.position_meters,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source,
            },
        }
        return ProposedAction.from_payload(
            thread_id=self._thread_id(event),
            action_type=ActionType.QUALITY_VERDICT,
            args=args,
            target_subject=None,
        )

    def _build_evidence_panel(
        self, event: QualityEvent, verdict: QualityVerdict
    ) -> EvidencePanel:
        """Build the EvidencePanel attached to the audit row.

        The synthetic ``ToolCall`` carries the structured event + verdict so
        downstream dashboards (Phase 11) can filter on dye_lot_id and
        defect_type without scanning the raw JSONB payload.
        """
        now = datetime.now(timezone.utc)
        synthetic_call = ToolCall(
            name="grade_quality_event",
            args={
                "event_id": str(event.event_id),
                "asset_id": event.asset_id,
                "dye_lot_id": event.dye_lot_id,
                "defect_type": event.defect_type,
                "defect_length_inches": event.defect_length_inches,
                "full_width": event.full_width,
            },
            result={
                "score": verdict.score,
                "severity": verdict.severity,
            },
            duration_ms=0,
            ts=now,
        )
        summary = (
            f"defect={event.defect_type} dye_lot={event.dye_lot_id} "
            f"score={verdict.score} severity={verdict.severity}"
        )
        return EvidencePanel(
            input_summary=summary[:500],
            input_truncated=len(summary) > 500,
            tool_calls=[synthetic_call],
            rag_citations=[],
            confidence=1.0,
            model=_LOG_ONLY_MODEL,
            prompt_hash=_NO_PROMPT_HASH,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=0,
        )

    async def _write_auto_audit(
        self, event: QualityEvent, verdict: QualityVerdict
    ) -> None:
        """Write a Decision.AUTO audit row for the minor / auto-log branch."""
        action = self._build_proposed_action(event, verdict)
        evidence_panel = self._build_evidence_panel(event, verdict)
        record = AuditRecord(
            id=uuid4(),
            ts=datetime.now(timezone.utc),
            action_id=event.event_id,  # idempotency key for qi-consumer
            agent_id=self._agent_id,
            thread_id=self._thread_id(event),
            cluster=self._cluster,
            action_type=action.action_type.value,
            evidence_panel=evidence_panel,
            decision=Decision.AUTO,
            decision_actor=None,
            motivation=None,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,
        )
        await self._audit.write(record)

    async def _dispatch_hitl(
        self,
        event: QualityEvent,
        verdict: QualityVerdict,
        *,
        tier: Tier,
        run_safety_check: bool,
    ) -> None:
        """Route the event through human_approval_node (and optionally safety)."""
        action = self._build_proposed_action(event, verdict)
        evidence_panel = self._build_evidence_panel(event, verdict)

        if run_safety_check:
            # SafetyInterlockMiddleware.check raises SafetyInterlockRejection
            # on a forbidden action; for QUALITY_VERDICT no PLC actuation
            # exists (target_subject=None) so this is normally a pass-through
            # but the explicit call provides uniform forensic record (Pitfall §9).
            await self._safety.check(
                action,
                agent_id=self._agent_id,
                thread_id=self._thread_id(event),
                cluster=self._cluster,
                evidence_panel=evidence_panel,
                budget_snapshot=_EMPTY_BUDGET,
            )

        state = {"thread_id": self._thread_id(event)}
        await human_approval_node(
            state,
            proposed_action=action,
            evidence_panel=evidence_panel,
            queue_writer=self._queue,
            nats_publisher=self._nats,
            audit_writer=self._audit,
            tier=tier,
            cluster=self._cluster,
            agent_id=self._agent_id,
            budget_snapshot=_EMPTY_BUDGET,
        )


__all__ = ["HitlTier", "QualityInspector", "_resolve_tier"]
