"""LogEventTool — observability-only audit row tool (D-OA-02 #5).

Use case:
    OperatorAssistant (and other OPS agents) emit observability events that
    are NOT proposed actions and do NOT actuate anything — shift-handover
    inputs, operator questions / notes, KPI observations. We still want a
    forensic record so Phase 11 dashboards can chart operator engagement
    without inventing a parallel logging plane.

Audit shape (D-56 + Decision.LOGGED + ActionType.GOVERNOR_ALERT):
    * ``decision = Decision.LOGGED`` — Phase 6 extension, no HITL involvement.
    * ``action_type = ActionType.GOVERNOR_ALERT`` — placeholder informational
      action type until a dedicated ``OPERATOR_LOG`` enum value is added in a
      later phase (D-OA-02 #5).
    * ``evidence_panel`` is minimally populated (the operator text fits in
      ``input_summary`` capped at 500 chars; the structured payload is
      attached as a synthetic ``tool_call`` for downstream querying).
    * ``approval_id = None`` — no HITL, no interrupt, no replay.

Pitfall §3 (audit double-write) does NOT apply here: there is no
``interrupt()`` call, so the tool never re-executes from a checkpoint.

Async-only convention (PATTERNS Shared Pattern 7): sync ``_run`` raises
``NotImplementedError``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision
from sft_agents.models.evidence import EvidencePanel, TokenUsage, ToolCall

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants — Phase 6 starter event-type whitelist + placeholder identifiers
# ---------------------------------------------------------------------------


#: The 4 starter event types accepted Phase 6. Later phases may extend.
EventType = Literal[
    "shift_handover_input",
    "operator_question",
    "operator_note",
    "kpi_observation",
]


#: EvidencePanel.model accepts ``name@runtime`` — log-only rows never query an
#: LLM, so we record a sentinel value that still matches the regex.
_LOG_ONLY_MODEL: str = "log-only@sft-agents"

#: EvidencePanel.prompt_hash requires 64-hex sha256; we use the zero hash to
#: signal "no prompt was issued for this row" without inventing a fake one.
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


# ---------------------------------------------------------------------------
# Input schema (T-V6-injection mitigation)
# ---------------------------------------------------------------------------


class LogEventInput(BaseModel):
    """Input schema for :class:`LogEventTool`.

    ``event_type`` is constrained to a 4-value whitelist (Phase 6 starter set).
    ``summary`` is required and bounded to [1, 2000] chars.
    ``payload`` is optional (defaults to empty dict).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: EventType = Field(description="Categorical event label.")
    summary: str = Field(
        min_length=1,
        max_length=2000,
        description="Free-text summary of the event for human review.",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured payload (JSON-serializable).",
    )


# ---------------------------------------------------------------------------
# LogEventTool
# ---------------------------------------------------------------------------


_DESCRIPTION = (
    "Log an observability event to the immutable audit trail. Use for "
    "shift-handover inputs, operator questions, operator notes, and KPI "
    "observations. Does NOT propose any action and does NOT require human "
    "approval. Required args: event_type, summary. Optional: payload."
)


class LogEventTool(BaseTool):
    """Append an audit row for an observability-only event.

    Usage::

        tool = LogEventTool(audit_writer=audit_writer)
        result = await tool.ainvoke(
            {
                "event_type": "operator_question",
                "summary": "Operator asked why shade is off on DL-LOOM-01-...",
                "payload": {"lot_id": "DL-LOOM-01-20260518-ab12"},
            },
            config={"configurable": {
                "agent_id": "operator-assistant",
                "thread_id": "ops.operator-assistant.session-xyz",
                "cluster": "ops",
            }},
        )
        assert result == {"logged": True, "action_id": "<uuid>"}

    Context kwargs (``agent_id`` / ``thread_id`` / ``cluster``) are forwarded
    by the calling ReAct node via ``**kwargs`` so the audit row carries the
    standard D-59 identity triple.
    """

    name: str = "log_event"
    description: str = _DESCRIPTION
    args_schema: type[BaseModel] = LogEventInput

    _audit_writer: Any = PrivateAttr()

    def __init__(self, *, audit_writer: Any, **kwargs: Any) -> None:
        """Bind the single collaborator (``AuditWriter`` instance)."""
        super().__init__(**kwargs)
        self._audit_writer = audit_writer

    def _run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Sync ``_run`` disabled — use ``await tool.ainvoke({...})`` instead."""
        raise NotImplementedError(
            "LogEventTool is async-only. "
            "Use `await tool.ainvoke({...})` or `await tool._arun(...)` instead."
        )

    async def _arun(
        self,
        event_type: str,
        summary: str,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Write one ``Decision.LOGGED`` AuditRecord and return its id.

        The full event_type + summary + payload are persisted via the audit
        record's ``evidence_panel`` so Phase 11 dashboards can filter / chart
        operator engagement without scanning the rest of the audit row.
        """
        now = datetime.now(timezone.utc)
        action_id = uuid4()
        agent_id = str(kwargs.get("agent_id", "unknown-agent"))
        thread_id = str(kwargs.get("thread_id", "unknown-thread"))
        cluster = str(kwargs.get("cluster", "ops"))

        # Cap input_summary to 500 chars (EvidencePanel constraint) and record
        # truncation so downstream consumers can lazy-load the full payload
        # from the synthetic tool_call entry below.
        truncated = len(summary) > 500
        input_summary = summary[:500] if truncated else summary

        # Stash the structured event under a synthetic ToolCall so the
        # event_type + payload survive in the audit row in a typed shape that
        # Phase 11 dashboards can query without a JSONB ad-hoc scan.
        event_tool_call = ToolCall(
            name="log_event",
            args={
                "event_type": event_type,
                "summary": summary,
                "payload": payload or {},
            },
            result={"logged": True},
            duration_ms=0,
            ts=now,
        )

        evidence_panel = EvidencePanel(
            input_summary=input_summary,
            input_truncated=truncated,
            tool_calls=[event_tool_call],
            rag_citations=[],
            confidence=1.0,
            model=_LOG_ONLY_MODEL,
            prompt_hash=_NO_PROMPT_HASH,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=0,
        )

        record = AuditRecord(
            id=uuid4(),
            ts=now,
            action_id=action_id,
            agent_id=agent_id,
            thread_id=thread_id,
            cluster=cluster,
            action_type=ActionType.GOVERNOR_ALERT.value,
            evidence_panel=evidence_panel,
            decision=Decision.LOGGED,
            decision_actor=None,
            motivation=None,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,
        )

        await self._audit_writer.write(record)
        logger.info(
            "log_event_written",
            action_id=str(action_id),
            agent_id=agent_id,
            event_type=event_type,
        )
        return {"logged": True, "action_id": str(action_id)}


__all__ = ["EventType", "LogEventInput", "LogEventTool"]
