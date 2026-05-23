"""EscalateToSupervisorTool — LangChain BaseTool wrapping the HITL escalation cycle.

D-OA-02 #4 + Pitfall §3 + Pitfall §9:
    The tool is invoked inside the OperatorAssistant ReAct loop when the LLM
    decides that the user's request requires authority the agent does not have
    (e.g. production stop, safety override). It must:

    1. Construct a synthetic ``ProposedAction`` with
       ``action_type=ActionType.ESCALATION_REQUEST`` so the audit shape is
       uniform with all other proposed actions (Pitfall §9 — same evidence
       chain, no special-case bypass of the safety interlock).
    2. Route the action through ``SafetyInterlockMiddleware.check`` — even
       though escalations carry no NATS target_subject, the explicit pass
       guarantees forensic uniformity and catches forbidden-action-type
       additions in the future without surprising the call-site.
    3. Call ``langgraph.types.interrupt(...)`` with a structured payload so
       the supervisor UI receives a well-typed envelope. The interrupt pauses
       the whole ReAct runnable; LangGraph persists the checkpoint and resumes
       once the supervisor POSTs a decision to ``/approvals/{id}/decide``.

Pitfall §3 (re-execution corrupts double-write):
    The HITL approval node (``sft_agents.hitl.interrupt.human_approval_node``)
    is responsible for the audit dual-write **after** resume. This tool MUST
    NOT call ``AuditWriter.write`` before ``interrupt()`` — on resume the node
    re-executes from the top, which would double-write the audit row.

Async-only convention (PATTERNS Shared Pattern 7):
    Sync ``_run`` raises ``NotImplementedError`` to prevent silent deadlocks
    when callers wrap a sync agent loop around an async tool.
"""

from __future__ import annotations

from typing import Any

import structlog
from langchain_core.tools import BaseTool
from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from sft_agents.models.enums import ActionType, Tier
from sft_agents.models.proposed_action import ProposedAction

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Input schema (T-V6-injection mitigation: frozen + extra=forbid + length caps)
# ---------------------------------------------------------------------------


class EscalateInput(BaseModel):
    """Input schema for :class:`EscalateToSupervisorTool`.

    Field length caps mitigate prompt-injection payload bloat (T-V6-injection).
    All three free-text fields are required and bounded to [10, 2000] chars.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(
        min_length=10,
        max_length=2000,
        description="Why the agent is escalating (why it cannot decide itself).",
    )
    suggested_action: str = Field(
        min_length=10,
        max_length=2000,
        description="What the agent recommends the supervisor approve.",
    )
    evidence_summary: str = Field(
        min_length=10,
        max_length=2000,
        description="Short evidence brief — facts the supervisor needs.",
    )


# ---------------------------------------------------------------------------
# EscalateToSupervisorTool
# ---------------------------------------------------------------------------


_DESCRIPTION = (
    "Pause the agent and route the current decision to a human supervisor for "
    "explicit approval. Use when the user's request requires authority the agent "
    "does not have (e.g., production stop, safety override). "
    "Required args: reason, suggested_action, evidence_summary."
)


class EscalateToSupervisorTool(BaseTool):
    """ReAct-loop tool that pauses the agent for supervisor approval.

    Usage::

        tool = EscalateToSupervisorTool(
            audit_writer=audit_writer,
            queue_writer=queue_writer,
            nats=nats_publisher,
            safety_middleware=safety,
        )
        decision = await tool.ainvoke({
            "reason": "...",
            "suggested_action": "...",
            "evidence_summary": "...",
        })

    The returned ``decision`` dict is what the supervisor POSTed to
    ``/approvals/{id}/decide`` — the LLM receives it as ``ToolMessage`` content.
    """

    name: str = "escalate_to_supervisor"
    description: str = _DESCRIPTION
    args_schema: type[BaseModel] = EscalateInput

    # PrivateAttr keeps langchain_core from treating these as tool parameters.
    _audit_writer: Any = PrivateAttr()
    _queue_writer: Any = PrivateAttr()
    _nats: Any = PrivateAttr()
    _safety: Any = PrivateAttr()

    def __init__(
        self,
        *,
        audit_writer: Any,
        queue_writer: Any,
        nats: Any,
        safety_middleware: Any,
        **kwargs: Any,
    ) -> None:
        """Bind the four collaborators required by the HITL pipeline.

        Args:
            audit_writer: ``AuditWriter`` instance. Held by the tool for
                completeness but NOT invoked here — the calling
                ``human_approval_node`` owns the post-resume audit write
                (Pitfall §3).
            queue_writer: ``ApprovalQueueWriter`` instance. Held by the tool
                for completeness but NOT invoked here — same Pitfall §3.
            nats: ``AuditNatsPublisher`` instance. Held by the tool for
                completeness but NOT invoked here.
            safety_middleware: ``SafetyInterlockMiddleware`` instance. Used
                to validate the synthetic escalation action before interrupt.
        """
        super().__init__(**kwargs)
        self._audit_writer = audit_writer
        self._queue_writer = queue_writer
        self._nats = nats
        self._safety = safety_middleware

    def _run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Sync ``_run`` disabled — use ``await tool.ainvoke({...})`` instead."""
        raise NotImplementedError(
            "EscalateToSupervisorTool is async-only. "
            "Use `await tool.ainvoke({...})` or `await tool._arun(...)` instead."
        )

    async def _arun(
        self,
        reason: str,
        suggested_action: str,
        evidence_summary: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Construct ProposedAction → safety check → interrupt → return decision.

        On resume the LangGraph runtime replays this coroutine from the top.
        Because no PG/NATS side-effects occur before ``interrupt()`` and the
        ``ProposedAction.id`` is sha256-deterministic from
        (thread_id, action_type, canonical_args), the tool is idempotent
        across re-execution (Pitfall §3).
        """
        # Construct synthetic ProposedAction. thread_id is not yet known at this
        # depth (it lives in AgentState); we use a stable placeholder so the
        # deterministic id depends only on the action shape. The calling
        # human_approval_node re-derives the approval_id from
        # (state.thread_id, action.id) inside the resume path.
        action = ProposedAction.from_payload(
            thread_id="escalate_to_supervisor",
            action_type=ActionType.ESCALATION_REQUEST,
            args={
                "reason": reason,
                "suggested_action": suggested_action,
                "evidence_summary": evidence_summary,
            },
            target_subject=None,
        )

        # Pitfall §9 — uniform safety gate. SafetyInterlockMiddleware.check is
        # async + keyword-only; the calling ReAct node forwards the AgentState
        # context via **kwargs (agent_id / thread_id / cluster / evidence_panel
        # / budget_snapshot). We pop those from kwargs to keep the call generic
        # and to allow tests to pass an AsyncMock without context. The
        # middleware short-circuits before touching these on the happy path
        # (action_type ESCALATION_REQUEST is not in the forbidden whitelist).
        safety_ctx = {
            key: kwargs[key]
            for key in (
                "agent_id",
                "thread_id",
                "cluster",
                "evidence_panel",
                "budget_snapshot",
            )
            if key in kwargs
        }
        await self._safety.check(action, **safety_ctx)

        # Pitfall §3 — NO audit / queue / nats side-effects before interrupt().
        # The human_approval_node performs the dual-write after resume.
        logger.info(
            "escalate_to_supervisor_invoked",
            action_id=str(action.id),
            tier=Tier.SUPERVISOR.value,
        )
        decision = interrupt(
            {
                "tool": "escalate_to_supervisor",
                "tier": Tier.SUPERVISOR.value,
                "payload": action.model_dump(mode="json"),
            }
        )
        return decision


# ---------------------------------------------------------------------------
# RequestHelpTool — Phase 7 Plan 07-04 MaintenanceCoach wrapper (D-MC-02)
# ---------------------------------------------------------------------------


class RequestHelpInput(BaseModel):
    """Input schema for :class:`RequestHelpTool`.

    Used by MaintenanceCoach to surface an explicit technician help request
    (keywords like ``aiuto`` / ``help`` / ``stuck`` in the conversation).
    The fields capture the intervention context that the supervisor will see
    when the wrapped :func:`EscalateToSupervisorTool` calls ``interrupt()``.

    Field constraints mitigate prompt-injection (T-V7-injection-prompt-stuffing,
    T-V7-intervention-id-overflow):

    * ``reason`` / ``context``: ``[10, 2000]`` chars — same bounds as
      ``EscalateInput``.
    * ``intervention_id``: ``[1, 64]`` chars — matches Phase 4 thread_id length
      convention.
    * ``current_step``: ``[0, 100]`` — guided procedures cap at 100 steps.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(
        min_length=10,
        max_length=2000,
        description="Why the technician is asking for help (natural language).",
    )
    context: str = Field(
        min_length=10,
        max_length=2000,
        description="Short context: what was tried, what is observed.",
    )
    intervention_id: str = Field(
        min_length=1,
        max_length=64,
        description="Maintenance intervention identifier (correlates with audit row).",
    )
    current_step: int = Field(
        ge=0,
        le=100,
        description="Zero-based index of the current step in the guided procedure.",
    )


_REQUEST_HELP_DESCRIPTION = (
    "Technician explicit help request (keyword: 'aiuto', 'help', 'stuck'). "
    "Wraps escalate_to_supervisor: pauses the agent and routes the request to "
    "a human supervisor for explicit guidance. "
    "Required args: reason, context, intervention_id, current_step."
)


class RequestHelpTool(BaseTool):
    """MaintenanceCoach wrapper around :class:`EscalateToSupervisorTool` (D-MC-02).

    Why a wrapper and not a re-implementation
    -----------------------------------------
    D-MC-02 (07-CONTEXT.md) explicitly mandates that ``request_help`` *wraps*
    ``escalate_to_supervisor`` rather than duplicating the interrupt /
    safety-check / audit pipeline. The wrapping pattern preserves the
    following Phase 6 invariants by construction:

    * **Pitfall §3 inheritance (no audit before interrupt)** — this tool
      performs NO ``AuditWriter.write``, NO ``ApprovalQueueWriter.insert``,
      and NO ``AuditNatsPublisher.publish`` call. It only formats the
      escalation payload and delegates to ``EscalateToSupervisorTool._arun``,
      which is itself audit-side-effect-free before ``interrupt()``. The
      ``human_approval_node`` performs the dual-write after resume.

    * **Pitfall §9 (uniform safety gate)** — the underlying
      ``EscalateToSupervisorTool`` still routes the synthetic
      ``ProposedAction`` through ``SafetyInterlockMiddleware.check`` before
      calling ``interrupt()``.

    * **Async-only convention (Shared Pattern B)** — sync ``_run`` raises
      ``NotImplementedError`` so synchronous agent loops cannot silently
      deadlock on an async tool.

    Audit marker (D-MC-02)
    ----------------------
    The audit row written by the calling ``human_approval_node`` MUST include
    ``escalation_trigger: 'technician_request'`` in the payload to distinguish
    technician-driven escalations from autonomous agent escalations. This
    tool does NOT write that row itself (see Pitfall §3 above) — the marker
    is the responsibility of the calling node and is documented here so the
    contract is discoverable from the tool surface.

    Composition contract
    --------------------
    ``_arun`` composes the wrapped call as::

        evidence_summary = f"intervention={intervention_id} step={current_step} "
                            f"context={context[:1000]}"
        suggested_action = f"Supervisor: review step {current_step} of "
                            f"intervention {intervention_id}"
        return await self._escalate._arun(
            reason=reason,
            suggested_action=suggested_action,
            evidence_summary=evidence_summary,
            **kwargs,
        )

    The 1000-char ``context`` clip in ``evidence_summary`` is defense-in-depth
    on top of the schema-level ``max_length=2000`` — the supervisor UI panel
    has a soft cap and the truncation keeps the audit payload predictable.
    """

    name: str = "request_help"
    description: str = _REQUEST_HELP_DESCRIPTION
    args_schema: type[BaseModel] = RequestHelpInput

    # PrivateAttr keeps langchain_core from treating this as a tool parameter.
    _escalate: EscalateToSupervisorTool = PrivateAttr()

    def __init__(
        self,
        *,
        escalate: EscalateToSupervisorTool,
        **kwargs: Any,
    ) -> None:
        """Bind the underlying :class:`EscalateToSupervisorTool` instance.

        Args:
            escalate: A constructed ``EscalateToSupervisorTool`` (already wired
                with audit_writer / queue_writer / nats / safety_middleware).
                The wrapping tool does NOT instantiate one itself — callers
                inject so the same audit / safety pipeline backs both tools.
        """
        super().__init__(**kwargs)
        self._escalate = escalate

    def _run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Sync ``_run`` disabled — use ``await tool.ainvoke({...})`` instead."""
        raise NotImplementedError(
            "RequestHelpTool is async-only. "
            "Use `await tool.ainvoke({...})` or `await tool._arun(...)` instead."
        )

    async def _arun(
        self,
        reason: str,
        context: str,
        intervention_id: str,
        current_step: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Compose the escalation payload and delegate to the wrapped tool.

        See class docstring for the composition contract and the Pitfall §3
        inheritance rationale. The returned dict is the supervisor's decision
        as POSTed to ``/approvals/{id}/decide`` — propagated verbatim from
        the underlying ``EscalateToSupervisorTool._arun``.
        """
        evidence_summary = (
            f"intervention={intervention_id} step={current_step} "
            f"context={context[:1000]}"
        )
        suggested_action = (
            f"Supervisor: review step {current_step} of intervention {intervention_id}"
        )
        return await self._escalate._arun(
            reason=reason,
            suggested_action=suggested_action,
            evidence_summary=evidence_summary,
            **kwargs,
        )


__all__ = [
    "EscalateInput",
    "EscalateToSupervisorTool",
    "RequestHelpInput",
    "RequestHelpTool",
]
