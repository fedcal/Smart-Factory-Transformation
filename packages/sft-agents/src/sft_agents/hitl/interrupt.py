"""human_approval_node — LangGraph interrupt/resume cycle (HITL-01, HITL-04, HITL-06, HITL-07).

Contract (CONTEXT.md D-55 + PLAN.md <interfaces>):
    1. Build ApprovalRequest from ProposedAction + EvidencePanel; SLA from escalation-sla.yaml
    2. INSERT into hitl.approvals (idempotent ON CONFLICT on sha256-deterministic id)
    3. Publish NATS hitl.approvals.new.<tier>
    4. Call interrupt(payload) — LangGraph persists checkpoint + pauses
    5. On resume: receive ApprovalDecision payload from Command(resume=)
    6. UPDATE hitl.approvals.status + decided_at/by + decision_json
    7. Publish NATS hitl.approvals.resolved.<tier>
    8. Build AuditRecord with tier→Decision mapping; AuditWriter.write()
    9. Return AgentState delta (clear pending_approval_id, attach evidence)

Pitfall §6 note (langgraph re-execution):
    On resume, the node re-executes from the top. The INSERT must therefore be
    idempotent — ApprovalQueueWriter uses ON CONFLICT DO NOTHING and the
    ApprovalRequest.id is derived from ProposedAction.id (sha256-deterministic
    per Plan 04-01) so the same logical action always produces the same row.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import structlog
import yaml

from sft_agents.hitl.approval_queue import ApprovalQueueWriter
from sft_agents.models.approval import ApprovalDecision, ApprovalRequest
from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ApprovalStatus, Decision, Tier
from sft_agents.models.evidence import EvidencePanel
from sft_agents.models.proposed_action import ProposedAction

if TYPE_CHECKING:
    from sft_agents.audit.writer import AuditWriter

logger = structlog.get_logger(__name__)

_DEFAULT_SLA_YAML = (
    Path(__file__).parent.parent / "policies" / "escalation-sla.yaml"
)


def tier_to_decision(tier: Tier, *, decision_verb: str) -> Decision:
    """Map (Tier, approve/reject verb) → audit Decision.

    For ``approve``/``reject`` the audit row records the tier that decided
    (HITL-07: motivation always required). For ``escalate``, the audit row
    is logged separately by the EscalationSupervisor with Decision.ESCALATED.
    """
    if decision_verb == "escalate":
        return Decision.ESCALATED
    mapping = {
        Tier.OPERATOR: Decision.HITL_OPERATOR,
        Tier.SUPERVISOR: Decision.HITL_SUPERVISOR,
        Tier.MANAGER: Decision.HITL_MANAGER,
        Tier.SAFETY_INTERLOCK: Decision.INTERLOCK_REJECT,
    }
    return mapping[tier]


def _load_sla_minutes(yaml_path: Path | None = None) -> dict[str, int | None]:
    """Read escalation-sla.yaml → {tier_value: sla_minutes_or_None}."""
    path = yaml_path or _DEFAULT_SLA_YAML
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    out: dict[str, int | None] = {}
    for tier_key, block in (data or {}).items():
        out[tier_key] = block.get("sla_minutes") if isinstance(block, dict) else None
    return out


def _derive_approval_id(thread_id: str, action_id: UUID) -> UUID:
    """sha256-deterministic id so re-execution after interrupt() is idempotent."""
    import hashlib

    digest = hashlib.sha256(
        f"{thread_id}|approval|{action_id}".encode("utf-8")
    ).hexdigest()
    return UUID(hex=digest[:32])


async def human_approval_node(
    state: dict[str, Any],
    *,
    proposed_action: ProposedAction,
    evidence_panel: EvidencePanel,
    queue_writer: ApprovalQueueWriter,
    nats_publisher: Any,
    audit_writer: "AuditWriter",
    tier: Tier,
    cluster: str,
    agent_id: str,
    sla_yaml_path: Path | None = None,
    budget_snapshot: BudgetSnapshot | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Execute one HITL approval cycle.

    Args:
        state: AgentState dict (must contain ``thread_id``).
        proposed_action: ProposedAction awaiting approval.
        evidence_panel: EvidencePanel attached to this decision (HITL-06).
        queue_writer: ApprovalQueueWriter instance.
        nats_publisher: AuditNatsPublisher with publish_approval_* methods.
        audit_writer: AuditWriter for the dual-write audit step.
        tier: Tier owning this approval.
        cluster: D-53 cluster name (for audit subject derivation).
        agent_id: Agent slug.
        sla_yaml_path: Optional override for the SLA yaml (default
            ``policies/escalation-sla.yaml``).
        budget_snapshot: Optional budget snapshot to embed in AuditRecord.
        now: Injectable clock for deterministic tests.

    Returns:
        AgentState delta:
            ``{"pending_approval_id": None, "evidence": evidence_panel}``

    Raises:
        ApprovalNotFoundError: If resume payload references a stale id
            (T-04-Resume-Replay defense).
        ValidationError: If resume payload is not a valid ApprovalDecision
            (T-04-LLM-Inject defense — motivation required for hitl_*).
    """
    # Imported lazily so the module can be unit-tested without LangGraph.
    from langgraph.types import interrupt  # noqa: PLC0415

    now_ts = now or datetime.now(timezone.utc)
    thread_id: str = str(state.get("thread_id", ""))
    if not thread_id:
        raise ValueError(
            "state.thread_id is required for HITL approval persistence "
            "(D-59 thread_id format: {cluster}.{agent_id}.{session_uuid})"
        )

    sla_minutes = _load_sla_minutes(sla_yaml_path)
    minutes = sla_minutes.get(tier.value)
    if minutes is None:
        # safety_interlock or manager-terminal tier — use a 1-year-in-future
        # placeholder. Schema NOT NULL on sla_deadline, but
        # EscalationSupervisor filters tier != safety_interlock so this row is
        # never auto-escalated.
        sla_deadline = now_ts + timedelta(days=365)
    else:
        sla_deadline = now_ts + timedelta(minutes=int(minutes))

    approval_id = _derive_approval_id(thread_id, proposed_action.id)

    approval = ApprovalRequest(
        id=approval_id,
        agent_id=agent_id,
        thread_id=thread_id,
        tier=tier,
        action_type=proposed_action.action_type.value,
        payload_json={
            "action_id": str(proposed_action.id),
            "args": proposed_action.args,
            "target_subject": proposed_action.target_subject,
        },
        status=ApprovalStatus.PENDING,
        created_at=now_ts,
        sla_deadline=sla_deadline,
    )

    # Step 1+2: persist + notify (idempotent on id).
    await queue_writer.insert(approval)
    try:
        await nats_publisher.publish_approval_new(approval)
    except Exception as exc:  # noqa: BLE001
        # Notification failure is non-fatal — the row is in PG and the UI
        # poller / outbox retry will eventually catch up.
        logger.warning(
            "approval_new_publish_failed",
            approval_id=str(approval.id),
            error=str(exc),
        )

    # Step 3: pause for human decision. The resume value is the dict-form of
    # ApprovalDecision that the api-gateway POSTs to /approvals/{id}/decide.
    resume_payload = interrupt(
        {
            "approval_id": str(approval.id),
            "tier": tier.value,
            "payload": proposed_action.model_dump(mode="json"),
            "evidence_panel": evidence_panel.model_dump(mode="json"),
        }
    )

    # Step 4: validate the resume payload (T-04-LLM-Inject — Pydantic rejects
    # malformed/empty-motivation payloads here).
    decision = ApprovalDecision.model_validate(resume_payload)

    # Step 5: UPDATE the row — raises ApprovalNotFoundError on stale id.
    decided_at = datetime.now(timezone.utc)
    await queue_writer.update_decision(
        approval.id,
        decision=decision.decision,
        decided_by=decision.decided_by,
        motivation=decision.motivation,
        decided_at=decided_at,
    )

    # Step 6: notify resolution.
    resolved = approval.model_copy(
        update={
            "status": (
                ApprovalStatus.APPROVED
                if decision.decision == "approve"
                else ApprovalStatus.REJECTED
                if decision.decision == "reject"
                else ApprovalStatus.ESCALATED
            ),
            "decided_at": decided_at,
            "decided_by": decision.decided_by,
            "decision_json": {
                "decision": decision.decision,
                "motivation": decision.motivation,
                "decided_by": decision.decided_by,
            },
        }
    )
    try:
        await nats_publisher.publish_approval_resolved(resolved)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "approval_resolved_publish_failed",
            approval_id=str(approval.id),
            error=str(exc),
        )

    # Step 7: audit (dual-write).
    audit_decision = tier_to_decision(tier, decision_verb=decision.decision)
    snapshot = budget_snapshot or _empty_budget_snapshot()
    audit_record = AuditRecord(
        id=uuid4(),
        ts=datetime.now(timezone.utc),
        action_id=proposed_action.id,
        agent_id=agent_id,
        thread_id=thread_id,
        cluster=cluster,
        action_type=proposed_action.action_type.value,
        evidence_panel=evidence_panel,
        decision=audit_decision,
        decision_actor=decision.decided_by,
        motivation=decision.motivation,
        budget_snapshot=snapshot,
        approval_id=approval.id,
    )
    await audit_writer.write(audit_record)

    return {
        "pending_approval_id": None,
        "evidence": evidence_panel,
    }


def _empty_budget_snapshot() -> BudgetSnapshot:
    """Fallback when caller did not supply a snapshot.

    Uses the ops-cluster defaults from CONTEXT.md D-60 so the AuditRecord
    Pydantic validation passes (limit_* fields are required, ge=0).
    """
    return BudgetSnapshot(
        tokens_input=0,
        tokens_output=0,
        tokens_total=0,
        cost_usd_simulated=0.0,
        duration_ms=0,
        limit_tokens=50000,
        limit_cost_usd=1.0,
        limit_duration_s=60,
    )
