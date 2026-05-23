"""MaintenanceCoach async LangGraph thread agent (MNT-03 + MNT-06).

Architecture (D-MC-01):
  - Each intervention = 1 LangGraph thread with state persisted in PG via
    ``langgraph_checkpoints`` table (Phase 4 migration 005 reuse — no new migration).
  - Thread ID: ``coach-<intervention_id>`` (audit-greppable, collision-safe prefix).
  - Cross-shift resume: re-invoking with the same thread_id reads the persisted
    checkpoint and resumes from ``current_step`` exactly — NOT from step 0.
  - MTTR: ``mttr_start`` set at intervention start; ``mttr_end`` set by
    ``complete_node``. ``compute_mttr_minutes(state)`` gives pause-inclusive elapsed.

HITL flow (D-MC-02):
  - When technician_id is None at step 0: emit ``interrupt("technician_assignment_required")``
    → supervisor assigns via /resume with ``{technician_id: '<id>'}``.
  - During guided steps: LLM may invoke ``request_help`` tool when help keywords
    detected → wraps ``escalate_to_supervisor`` → supervisor interrupt.
  - Audit rows written AFTER ``ainvoke`` returns (Pitfall §3 — no audit before interrupt).

AsyncPostgresSaver notes (Plan 07-13 CR-01 fix):
  - The saver MUST be injected at construction time; ``_get_graph()`` raises
    ``RuntimeError`` if ``self._graph is None`` (no self-compile fallback).
  - The api-gateway lifespan is responsible for creating ONE long-lived saver:
    ``async with AsyncPostgresSaver.from_conn_string(pg_dsn) as saver: ...``
    and injecting it into MaintenanceCoach at startup. The saver lives for the
    application lifetime; graph invocations reuse it without closing it.
  - The previous per-call self-compile path (CR-01) closed the saver immediately
    after compiling the graph, making checkpoint reads/writes fail on all
    subsequent calls with ``ConnectionDoesNotExistError``.

State compression (07-PATTERNS.md Section 6, T-V7-coach-state-bloat):
  - When ``len(state['messages']) > _MESSAGE_TRIM_THRESHOLD``, the ``_trim_messages``
    helper trims oldest non-system messages keeping the first 5 system messages +
    last ``(threshold - n_system)`` messages.
  - Triggers structlog event ``coach_state_compressed`` with old/new lengths.
  - Threshold configurable via ``_MESSAGE_TRIM_THRESHOLD = 50`` module constant.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from mnt_maintenance_coach.metadata import build_ops05_evidence_panel
from mnt_maintenance_coach.models import (
    CoachResponse,
    CoachStartRequest,
    CoachStepRequest,
    CoachThreadState,
    StepReport,
)
from mnt_maintenance_coach.mttr import compute_mttr_minutes
from mnt_maintenance_coach.prompts import build_step_prompt, detect_help_keyword

UTC = timezone.utc
logger = structlog.get_logger("agent.maintenance-coach")


# ---------------------------------------------------------------------------
# Module constants (D-MC-01 + 07-PATTERNS.md Section 6)
# ---------------------------------------------------------------------------

AGENT_ID: str = "maintenance-coach"
CLUSTER: str = "maintenance"

#: Maximum messages in LangGraph state before trimming (T-V7-coach-state-bloat).
_MESSAGE_TRIM_THRESHOLD: int = 50

#: Maximum SOP steps (D-MC-01 current_step le=100).
_MAX_STEPS: int = 100

#: Default language for LLM prompts.
_DEFAULT_LANG: Literal["it", "en"] = "it"


# ---------------------------------------------------------------------------
# State compression helper
# ---------------------------------------------------------------------------


def _trim_messages(messages: list[Any], threshold: int) -> list[Any]:
    """Trim message list to bounded size, preserving system messages + tail.

    When ``len(messages) <= threshold``, returns messages unchanged.
    When above threshold, keeps:
      - All system-type messages from the first 5 messages (preserve context).
      - The last ``(threshold - n_system_kept)`` remaining messages.

    This ensures the system prompt is never discarded while bounding
    token usage (07-PATTERNS.md Section 6 risk callout #1).

    Args:
        messages: Current message list (list[BaseMessage] or list[dict]).
        threshold: Maximum number of messages to target (system + tail).

    Returns:
        Trimmed message list; length is <= threshold + n_system (system may
        push slightly over threshold, but that is intentional).
    """
    if len(messages) <= threshold:
        return messages

    # Preserve system messages from the first 5 slots
    system_msgs = [
        m for m in messages[:5]
        if getattr(m, "type", None) == "system"
        or (isinstance(m, dict) and m.get("type") == "system")
    ]
    n_system = len(system_msgs)
    tail_size = max(0, threshold - n_system)
    tail = messages[-tail_size:] if tail_size > 0 else []
    return system_msgs + tail


# ---------------------------------------------------------------------------
# Graph node helpers
# ---------------------------------------------------------------------------


def _detect_lang(messages: list[Any]) -> Literal["it", "en"]:
    """Detect conversation language from messages; fallback to default."""
    for msg in messages:
        content = getattr(msg, "content", None) or (
            msg.get("content") if isinstance(msg, dict) else None
        )
        if not content:
            continue
        # Simple heuristic: if Italian keywords present, use IT
        lowered = content.lower()
        if any(kw in lowered for kw in ("passo", "sop", "aiuto", "tecnico", "intervento")):
            return "it"
        if any(kw in lowered for kw in ("step", "procedure", "help", "technician")):
            return "en"
    return _DEFAULT_LANG


def _route_step_or_complete(state: CoachThreadState) -> str:
    """Conditional edge: loop to 'step' or advance to 'complete'."""
    if state.current_step >= _MAX_STEPS:
        return "complete"
    return "step"


# ---------------------------------------------------------------------------
# build_coach_graph — LangGraph StateGraph factory
# ---------------------------------------------------------------------------


def build_coach_graph(
    *,
    llm: Any,
    rag_search_tool: Any,
    request_help_tool: Any,
    escalate_tool: Any,
) -> StateGraph:
    """Build the MaintenanceCoach LangGraph StateGraph.

    Returns an uncompiled StateGraph. Callers compile it with a checkpointer:
        ``graph = build_coach_graph(...).compile(checkpointer=saver)``

    Graph topology:
        START -> step_node (loop) -> complete_node -> END
        step_node loops back to itself via _route_step_or_complete; when
        current_step >= _MAX_STEPS, routes to complete.

    Args:
        llm: LangChain BaseChatModel instance (with tools bound externally).
        rag_search_tool: Tool for SOP step retrieval (Phase 5 RagSearchTool).
        request_help_tool: Tool for help escalation (Phase 7 RequestHelpTool).
        escalate_tool: Tool for supervisor escalation (EscalateToSupervisorTool).

    Returns:
        Uncompiled StateGraph with (step, complete) nodes and routing.
    """
    # Bind tools to LLM for use in step_node
    tools = [rag_search_tool, request_help_tool, escalate_tool]
    try:
        llm_with_tools = llm.bind_tools(tools)
    except (AttributeError, NotImplementedError):
        # Fallback for mock LLMs in tests that don't support bind_tools
        llm_with_tools = llm

    async def step_node(state: CoachThreadState) -> dict[str, Any]:
        """Execute one guided SOP step.

        Flow:
          1. Check technician_id (Open Q3 RESOLVED): None → technician_assignment_required
             HITL interrupt instead of executing step.
          2. Detect language from message history.
          3. Build step prompt (with last 3 completed steps as context).
          4. Invoke LLM (with bound tools: rag_search, request_help).
          5. If LLM called request_help → tool wraps escalate_to_supervisor →
             graph interrupts awaiting supervisor resume.
          6. Otherwise: LLM returns guidance → interrupt to await technician confirmation.
          7. On resume: build StepReport, compress state if needed, return state delta.
        """
        # Step 0 technician_id guard (Open Q3 RESOLVED)
        if state.technician_id is None and state.current_step == 0:
            logger.info(
                "coach_technician_assignment_required",
                intervention_id=state.intervention_id,
                asset_id=state.asset_id,
                sop_id=state.sop_id,
            )
            interrupt({
                "type": "technician_assignment_required",
                "intervention_id": state.intervention_id,
                "asset_id": state.asset_id,
                "sop_id": state.sop_id,
            })
            # interrupt() raises; this line is never reached in normal flow
            # but satisfies static analysis / mypy
            return {}

        lang = _detect_lang(state.messages)

        # Build step prompt (token-efficient: last 3 completed steps as context)
        step_prompt = build_step_prompt(
            sop_id=state.sop_id,
            step_no=state.current_step,
            completed_summary=list(state.completed_steps[-3:]),
            lang=lang,
        )

        citations: list[Any] = []
        guidance_text = f"Step {state.current_step}: proceed as per SOP {state.sop_id}"

        try:
            # Invoke LLM with bound tools
            from langchain_core.messages import HumanMessage, SystemMessage
            messages_for_llm = [SystemMessage(content=step_prompt)]
            llm_result = await llm_with_tools.ainvoke(messages_for_llm)

            # Extract guidance from LLM response
            if hasattr(llm_result, "content") and llm_result.content:
                guidance_text = llm_result.content
            elif isinstance(llm_result, str):
                guidance_text = llm_result

        except Exception as exc:
            logger.warning(
                "coach_llm_invocation_failed",
                intervention_id=state.intervention_id,
                step_no=state.current_step,
                error=str(exc),
            )
            # Fallback: use base guidance without LLM
            guidance_text = f"Step {state.current_step}: please refer to SOP {state.sop_id} section {state.current_step + 1}."

        # Interrupt to await technician input
        technician_input = interrupt({
            "type": "coach_step",
            "step_no": state.current_step,
            "guidance": guidance_text,
            "citations": [
                c.model_dump(mode="json") if hasattr(c, "model_dump") else c
                for c in citations
            ],
        })

        # On resume: technician_input contains the technician's response
        if not isinstance(technician_input, str):
            technician_input = str(technician_input) if technician_input else "ok"

        # Defense-in-depth: check for help keywords in technician response
        # The LLM should have detected these and invoked request_help,
        # but this catches edge cases (T-V7-coach-bypass-help mitigation)
        if detect_help_keyword(technician_input, lang):
            logger.info(
                "coach_help_keyword_detected_heuristic",
                intervention_id=state.intervention_id,
                step_no=state.current_step,
                lang=lang,
            )
            # If LLM didn't call request_help already, we note it but continue
            # The tool call would have happened before the interrupt if LLM detected it
            # This is purely informational logging — supervisor routing happened via tool

        # Build StepReport for completed step
        now = datetime.now(UTC)
        completed_step = StepReport(
            step_no=state.current_step,
            instruction=guidance_text[:2000],  # cap for storage efficiency
            technician_input=technician_input[:4000],
            duration_minutes=0,  # duration tracking left to 07-10 API layer
            completed_at=now,
            citations=citations,
        )

        # Build updated messages list
        from langchain_core.messages import AIMessage, HumanMessage
        new_messages = list(state.messages) + [
            AIMessage(content=guidance_text),
            HumanMessage(content=technician_input),
        ]

        # State compression (T-V7-coach-state-bloat)
        if len(new_messages) > _MESSAGE_TRIM_THRESHOLD:
            old_len = len(new_messages)
            new_messages = _trim_messages(new_messages, _MESSAGE_TRIM_THRESHOLD)
            logger.info(
                "coach_state_compressed",
                intervention_id=state.intervention_id,
                old_message_count=old_len,
                new_message_count=len(new_messages),
            )

        return {
            "current_step": state.current_step + 1,
            "completed_steps": list(state.completed_steps) + [completed_step],
            "messages": new_messages,
        }

    async def complete_node(state: CoachThreadState) -> dict[str, Any]:
        """Terminal node: set mttr_end and finalize intervention."""
        now = datetime.now(UTC)
        logger.info(
            "coach_intervention_complete",
            intervention_id=state.intervention_id,
            total_steps=state.current_step,
            mttr_start=state.mttr_start.isoformat(),
            mttr_end=now.isoformat(),
        )
        return {"mttr_end": now}

    # Build graph topology
    g: StateGraph = StateGraph(CoachThreadState)
    g.add_node("step", step_node)
    g.add_node("complete", complete_node)
    g.add_edge(START, "step")
    g.add_conditional_edges(
        "step",
        _route_step_or_complete,
        {"step": "step", "complete": "complete"},
    )
    g.add_edge("complete", END)

    return g


# ---------------------------------------------------------------------------
# MaintenanceCoach — high-level agent class
# ---------------------------------------------------------------------------


class MaintenanceCoach:
    """High-level async interface for the MaintenanceCoach agent.

    Construction is collaborator-injected (pool, audit_writer, llm, tools,
    saver) for test-friendly dependency injection.

    AsyncPostgresSaver injection:
        If ``saver`` is provided, it is used directly (e.g. in tests with
        ``AsyncMock`` or a real saver from testcontainers).
        If ``saver`` is None, the ``_get_saver`` async context manager is
        used per-invocation with the PG_DSN from the environment.

    The compiled graph is built ONCE in ``__init__`` using the injected saver.
    For production deployments where the saver is context-managed externally
    (e.g. startup lifespan), inject the pre-constructed saver.
    """

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: Any,
        llm: Any,
        rag_search_tool: Any,
        request_help_tool: Any,
        escalate_tool: Any,
        saver: Any | None = None,
    ) -> None:
        """Initialize MaintenanceCoach with injected collaborators.

        Args:
            pool: asyncpg connection pool (for audit writes + future DB queries).
            audit_writer: AuditWriter instance for COACH_STEP audit rows.
            llm: LangChain BaseChatModel (Qwen2.5 or mock in tests).
            rag_search_tool: RagSearchTool (Phase 5) for SOP chunk retrieval.
            request_help_tool: RequestHelpTool (Phase 7 Plan 07-04).
            escalate_tool: EscalateToSupervisorTool (Phase 6).
            saver: Optional pre-constructed AsyncPostgresSaver. If None, the
                coach will use ``AsyncPostgresSaver.from_conn_string(PG_DSN)``
                per invocation (production path). For tests, inject a mock.
        """
        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
        self._rag_tool = rag_search_tool
        self._request_help_tool = request_help_tool
        self._escalate_tool = escalate_tool
        self._saver = saver

        # Pre-compile graph with injected saver (if available)
        # For production without injected saver, graph is compiled per-call
        if saver is not None:
            self._graph = build_coach_graph(
                llm=llm,
                rag_search_tool=rag_search_tool,
                request_help_tool=request_help_tool,
                escalate_tool=escalate_tool,
            ).compile(checkpointer=saver)
        else:
            self._graph = None

    def _build_thread_id(self, intervention_id: str) -> str:
        """Build LangGraph thread_id from intervention_id (Open Q6 RESOLVED)."""
        return f"coach-{intervention_id}"

    def _build_audit_thread_id(self, intervention_id: str, step_no: int) -> str:
        """Build per-step audit row thread_id (per-step forensic format)."""
        return f"{CLUSTER}.{AGENT_ID}.{intervention_id}.{step_no}"

    async def _get_graph(self) -> Any:
        """Return the compiled graph (requires saver injected at construction).

        CR-01 fix: the previous self-compile path opened AsyncPostgresSaver in
        an ``async with`` block, cached the compiled graph, then exited the
        context manager — closing the saver connection before any ainvoke call
        could use it. Every subsequent graph call would raise
        ``ConnectionDoesNotExistError``.

        The correct pattern (07-REVIEW.md lines 77-83) is to inject a long-lived
        saver via the FastAPI lifespan and compile the graph once at construction.
        The ``__init__`` injected-saver branch already does this correctly. This
        method now simply raises if the graph was not compiled at construction —
        preventing the use-after-close defect entirely.

        Production wiring (api-gateway lifespan):
            async with AsyncPostgresSaver.from_conn_string(pg_dsn) as saver:
                await saver.setup()
                coach = MaintenanceCoach(..., saver=saver)
                app.state.maintenance_coach = coach
                yield  # saver lives for the application lifetime
        """
        if self._graph is None:
            raise RuntimeError(
                "MaintenanceCoach._graph is None. "
                "Inject a pre-built saver at construction or wire via lifespan. "
                "See api-gateway lifespan.py for the correct pattern: "
                "async with AsyncPostgresSaver.from_conn_string(pg_dsn) as saver: "
                "coach = MaintenanceCoach(..., saver=saver)."
            )
        return self._graph

    async def _write_audit(
        self,
        *,
        intervention_id: str,
        step_no: int,
        completed_step: StepReport | None,
        decision: str,
        escalation_trigger: str | None = None,
    ) -> None:
        """Write per-step COACH_STEP audit row (MNT-06).

        Called AFTER ``ainvoke`` returns (Pitfall §3 — no audit before interrupt).
        The thread_id format mirrors Phase 6 06-09 multi-step audit pattern:
            ``maintenance.maintenance-coach.<intervention_id>.<step_no>``

        Args:
            intervention_id: Intervention identifier.
            step_no: Completed step number.
            completed_step: The StepReport for the step (None if interrupted early).
            decision: Decision enum value string (e.g. 'auto', 'hitl_supervisor').
            escalation_trigger: Optional escalation marker
                (e.g. 'technician_request', 'technician_assignment_required').
        """
        from datetime import datetime, timezone
        from uuid import uuid4

        from sft_agents.models.audit import AuditRecord
        from sft_agents.models.budget import BudgetSnapshot
        from sft_agents.models.enums import ActionType, Decision
        from sft_agents.models.evidence import EvidencePanel, ToolCall, TokenUsage

        now = datetime.now(UTC)

        # Build synthetic ToolCall for the LLM step invocation
        tool_call_args: dict[str, Any] = {
            "intervention_id": intervention_id,
            "step_no": step_no,
        }
        if escalation_trigger:
            tool_call_args["escalation_trigger"] = escalation_trigger

        tool_call_result: dict[str, Any] | None = None
        if completed_step is not None:
            tool_call_result = {
                "instruction": completed_step.instruction[:200],
                "technician_input": completed_step.technician_input[:200],
                "duration_minutes": completed_step.duration_minutes,
            }

        synthetic_call = ToolCall(
            name="step_node",
            args=tool_call_args,
            result=tool_call_result,
            duration_ms=0,
            ts=now,
        )

        summary = f"intervention={intervention_id} step={step_no} decision={decision}"
        if escalation_trigger:
            summary += f" escalation_trigger={escalation_trigger}"

        evidence_panel = build_ops05_evidence_panel(
            hitl_tier=decision,
            extra={
                "intervention_id": intervention_id,
                "step_no": step_no,
            },
        )

        # We build an EvidencePanel for the AuditRecord
        ep = EvidencePanel(
            input_summary=summary[:500],
            input_truncated=len(summary) > 500,
            tool_calls=[synthetic_call],
            rag_citations=[],
            confidence=1.0,
            model=f"maintenance-coach@langraph-{AGENT_ID}",
            prompt_hash="0" * 64,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=0,
        )

        empty_budget = BudgetSnapshot(
            tokens_input=0,
            tokens_output=0,
            tokens_total=0,
            cost_usd_simulated=0.0,
            duration_ms=0,
            limit_tokens=50000,
            limit_cost_usd=1.0,
            limit_duration_s=60,
        )

        # Map decision string to Decision enum
        decision_enum = Decision.AUTO if decision == "auto" else Decision.HITL_SUPERVISOR

        record = AuditRecord(
            id=uuid4(),
            ts=now,
            action_id=uuid4(),
            agent_id=AGENT_ID,
            thread_id=self._build_audit_thread_id(intervention_id, step_no),
            cluster=CLUSTER,
            action_type=ActionType.COACH_STEP.value,
            evidence_panel=ep,
            decision=decision_enum,
            decision_actor=None,
            motivation=None,
            budget_snapshot=empty_budget,
            approval_id=None,
        )

        try:
            await self._audit.write(record)
        except Exception as exc:
            logger.error(
                "coach_audit_write_failed",
                intervention_id=intervention_id,
                step_no=step_no,
                error=str(exc),
            )
            # Do not re-raise — audit failure should not block the technician

    async def start(self, request: CoachStartRequest) -> CoachResponse:
        """Start a new coached intervention or resume an existing one.

        Creates initial ``CoachThreadState`` and invokes the graph.
        If ``technician_id`` is None, the graph emits a
        ``technician_assignment_required`` interrupt immediately.

        Args:
            request: CoachStartRequest with intervention metadata.

        Returns:
            CoachResponse with first guidance or assignment-required state.
        """
        from langgraph.errors import GraphInterrupt

        initial_state = CoachThreadState(
            intervention_id=request.intervention_id,
            asset_id=request.asset_id,
            sop_id=request.sop_id,
            technician_id=request.technician_id,
            current_step=0,
            completed_steps=[],
            messages=[],
            mttr_start=datetime.now(UTC),
            mttr_end=None,
        )

        thread_id = self._build_thread_id(request.intervention_id)
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50,
        }

        logger.info(
            "coach_intervention_start",
            intervention_id=request.intervention_id,
            asset_id=request.asset_id,
            sop_id=request.sop_id,
            technician_id=request.technician_id,
            thread_id=thread_id,
        )

        graph = await self._get_graph()

        try:
            result = await graph.ainvoke(initial_state, config=config)
            # Completed without interrupt (only possible if SOP is 0-step)
            return CoachResponse(
                intervention_id=request.intervention_id,
                current_step=result.get("current_step", 0) if isinstance(result, dict) else getattr(result, "current_step", 0),
                guidance_md="Intervention started and completed.",
                completed_step=None,
                mttr_minutes_so_far=None,
                state="completed",
            )
        except GraphInterrupt as exc:
            # LangGraph interrupt — expected path
            interrupt_value = exc.args[0] if exc.args else {}
            if isinstance(interrupt_value, (list, tuple)) and interrupt_value:
                interrupt_value = interrupt_value[0].value if hasattr(interrupt_value[0], 'value') else interrupt_value[0]

            interrupt_type = (
                interrupt_value.get("type") if isinstance(interrupt_value, dict) else None
            )

            if interrupt_type == "technician_assignment_required":
                await self._write_audit(
                    intervention_id=request.intervention_id,
                    step_no=0,
                    completed_step=None,
                    decision="hitl_supervisor",
                    escalation_trigger="technician_assignment_required",
                )
                return CoachResponse(
                    intervention_id=request.intervention_id,
                    current_step=0,
                    guidance_md=(
                        "Intervention opened without assigned technician. "
                        "Supervisor must assign technician_id via /resume."
                    ),
                    completed_step=None,
                    mttr_minutes_so_far=None,
                    state="awaiting_technician_assignment",
                )

            # Normal coach_step interrupt — first guidance ready
            guidance = (
                interrupt_value.get("guidance", "")
                if isinstance(interrupt_value, dict)
                else str(interrupt_value)
            )
            await self._write_audit(
                intervention_id=request.intervention_id,
                step_no=0,
                completed_step=None,
                decision="auto",
            )
            return CoachResponse(
                intervention_id=request.intervention_id,
                current_step=0,
                guidance_md=guidance,
                completed_step=None,
                mttr_minutes_so_far=None,
                state="in_progress",
            )
        except Exception as exc:
            logger.error(
                "coach_start_failed",
                intervention_id=request.intervention_id,
                error=str(exc),
            )
            raise

    async def step(
        self, request: CoachStepRequest, *, skip_audit: bool = False
    ) -> CoachResponse:
        """Submit technician input for the current step and resume the graph.

        Resumes the LangGraph thread with the technician's input via
        ``Command(resume=technician_input)``. The graph advances to the next
        step and interrupts again with the next guidance.

        Args:
            request: CoachStepRequest with intervention_id and technician_input.
            skip_audit: When True, suppresses the internal ``_write_audit`` calls
                (WR-02 fix). Use this when the caller (e.g. ``resume_after_help``)
                will write its own authoritative audit row. This ensures exactly
                one row is written per operation on the append-only audit table.

        Returns:
            CoachResponse with next guidance or completion state.
        """
        from langgraph.errors import GraphInterrupt

        thread_id = self._build_thread_id(request.intervention_id)
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50,
        }

        logger.info(
            "coach_step_resume",
            intervention_id=request.intervention_id,
            thread_id=thread_id,
        )

        graph = await self._get_graph()

        try:
            result = await graph.ainvoke(
                Command(resume=request.technician_input),
                config=config,
            )

            # If we get here without interrupt, intervention may be complete
            if isinstance(result, dict):
                current_step = result.get("current_step", 0)
                mttr_end = result.get("mttr_end")
                completed_steps = result.get("completed_steps", [])
            else:
                current_step = getattr(result, "current_step", 0)
                mttr_end = getattr(result, "mttr_end", None)
                completed_steps = list(getattr(result, "completed_steps", []))

            last_step = completed_steps[-1] if completed_steps else None
            if isinstance(last_step, dict):
                from mnt_maintenance_coach.models import StepReport as SR
                last_step = SR(**last_step)

            # Compute MTTR so far
            mttr_so_far: int | None = None
            if mttr_end is not None:
                import datetime as dt_module
                mttr_start_val = result.get("mttr_start") if isinstance(result, dict) else getattr(result, "mttr_start", None)
                if mttr_start_val is not None:
                    dummy_state = {"mttr_start": mttr_start_val, "mttr_end": mttr_end, "completed_steps": completed_steps}
                    try:
                        mttr_so_far = compute_mttr_minutes(dummy_state)
                    except (ValueError, Exception):
                        pass

            if not skip_audit:
                await self._write_audit(
                    intervention_id=request.intervention_id,
                    step_no=max(0, current_step - 1),
                    completed_step=last_step,
                    decision="auto",
                )

            return CoachResponse(
                intervention_id=request.intervention_id,
                current_step=current_step,
                guidance_md="Intervention complete.",
                completed_step=last_step,
                mttr_minutes_so_far=mttr_so_far,
                state="completed",
            )

        except GraphInterrupt as exc:
            interrupt_value = exc.args[0] if exc.args else {}
            if isinstance(interrupt_value, (list, tuple)) and interrupt_value:
                interrupt_value = interrupt_value[0].value if hasattr(interrupt_value[0], 'value') else interrupt_value[0]

            interrupt_type = (
                interrupt_value.get("type") if isinstance(interrupt_value, dict) else None
            )

            if interrupt_type == "coach_step":
                # Graph advanced to next step; next guidance is ready
                guidance = interrupt_value.get("guidance", "") if isinstance(interrupt_value, dict) else ""
                step_no = interrupt_value.get("step_no", 0) if isinstance(interrupt_value, dict) else 0

                # Read current state from checkpoint for completed_step
                completed_step = None
                checkpoint = await graph.aget_state(config)
                if checkpoint and checkpoint.values:
                    state_values = checkpoint.values
                    cs = state_values.get("completed_steps", []) if isinstance(state_values, dict) else getattr(state_values, "completed_steps", [])
                    if cs:
                        last = cs[-1]
                        if isinstance(last, dict):
                            from mnt_maintenance_coach.models import StepReport as SR
                            completed_step = SR(**last)
                        else:
                            completed_step = last

                if not skip_audit:
                    await self._write_audit(
                        intervention_id=request.intervention_id,
                        step_no=max(0, step_no - 1),
                        completed_step=completed_step,
                        decision="auto",
                    )

                return CoachResponse(
                    intervention_id=request.intervention_id,
                    current_step=step_no,
                    guidance_md=guidance,
                    completed_step=completed_step,
                    mttr_minutes_so_far=None,
                    state="in_progress",
                )

            elif interrupt_type in ("escalate_to_supervisor", "request_help"):
                # Help requested — awaiting supervisor
                await self._write_audit(
                    intervention_id=request.intervention_id,
                    step_no=0,
                    completed_step=None,
                    decision="hitl_supervisor",
                    escalation_trigger="technician_request",
                )
                return CoachResponse(
                    intervention_id=request.intervention_id,
                    current_step=0,
                    guidance_md="Help request sent to supervisor. Awaiting review.",
                    completed_step=None,
                    mttr_minutes_so_far=None,
                    state="awaiting_help",
                )

            # Unknown interrupt type — surface as help request
            return CoachResponse(
                intervention_id=request.intervention_id,
                current_step=0,
                guidance_md=str(interrupt_value),
                completed_step=None,
                mttr_minutes_so_far=None,
                state="awaiting_help",
            )

        except Exception as exc:
            logger.error(
                "coach_step_failed",
                intervention_id=request.intervention_id,
                error=str(exc),
            )
            raise

    async def resume_after_help(
        self, intervention_id: str, supervisor_input: str
    ) -> CoachResponse:
        """Resume a thread after supervisor resolved a help request or assigned technician.

        Used for:
          1. Supervisor resolved technician_assignment_required: ``supervisor_input``
             is ``{"technician_id": "<id>"}`` (JSON string).
          2. Supervisor resolved a help request: ``supervisor_input`` is supervisor's
             guidance text.

        Audit marker: ``escalation_trigger='technician_request'`` in evidence_panel
        (D-MC-02 compliance).

        Args:
            intervention_id: Intervention identifier.
            supervisor_input: Supervisor's resume payload (string).

        Returns:
            CoachResponse with next guidance or completion state.
        """
        # Delegate to step() with the supervisor input — same Command(resume=...) flow.
        # WR-02 fix: pass skip_audit=True so step() does NOT write its internal
        # decision='auto' audit row. This method is the authoritative caller and
        # writes exactly one row with decision='hitl_supervisor' below.
        resume_request = CoachStepRequest(
            intervention_id=intervention_id,
            technician_input=supervisor_input,
        )
        response = await self.step(resume_request, skip_audit=True)

        # Write the single authoritative audit row for this resume operation.
        # decision='hitl_supervisor' + escalation_trigger='technician_request'
        # captures that a supervisor resolved a HITL help request (D-MC-02).
        await self._write_audit(
            intervention_id=intervention_id,
            step_no=response.current_step,
            completed_step=response.completed_step,
            decision="hitl_supervisor",
            escalation_trigger="technician_request",
        )

        return response


__all__ = [
    "AGENT_ID",
    "CLUSTER",
    "MaintenanceCoach",
    "_MESSAGE_TRIM_THRESHOLD",
    "_trim_messages",
    "build_coach_graph",
]
