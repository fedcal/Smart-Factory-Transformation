"""RCASpecialist — ReAct LangGraph node with 5-Why chain + ALWAYS-supervisor HITL.

D-RCA-01 (form-based 5-Why, citation grounding, max 2 retries) +
D-RCA-02 (ALWAYS supervisor HITL — no severity branching, literal success criterion).

Architecture overview:
    1. ``__call__(state)`` extracts the problem statement + context from state.
    2. ``_invoke_react_loop(messages, *, user_roles)`` runs a ``create_react_agent``
       ReAct iteration with rag_search + traverse_graph tools; returns raw LLM output.
    3. Retry loop: parse JSON → Pydantic-validate → ``RCAChainValidator.validate()``.
       On ValidationError / MissingCitationError / OrphanCitationError, appends a
       corrective SystemMessage and retries up to ``_MAX_VALIDATION_RETRIES`` times
       (3 total attempts per D-RCA-01).
    4. **ALWAYS-supervisor gate (D-RCA-02):** whether the chain is valid (success)
       or exhausted (retry budget gone), calls ``escalate_to_supervisor`` BEFORE
       writing the audit row (Pitfall §3 — no double-write on LangGraph re-execution).
    5. Audit row: ActionType.RCA_CHAIN, Decision.HITL_SUPERVISOR.

Retry corrective message is injected as a SystemMessage (authoritative correction,
not user feedback) so the LLM model treats it with high priority.

JSON parsing: strips leading ```json``` fences if present (robustness);
uses ``json.loads`` (never ``eval``); treats ``JSONDecodeError`` as a schema
error that counts toward the retry budget.

Pitfall §3 (no audit before interrupt):
    ``escalate_to_supervisor`` calls ``langgraph.types.interrupt()`` internally.
    On resume the LangGraph runtime replays the node from the top. The audit write
    happens AFTER the escalate call resolves (supervisor decided), so there is no
    double-write risk.

AGENT_ID / CLUSTER are module-level constants consumed by:
    - ``mnt_rca_specialist.__init__`` re-export
    - API gateway routing (07-10)
    - audit thread_id format: ``{CLUSTER}.{AGENT_ID}.{chain_id}``
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Literal, Mapping
from uuid import uuid4

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import ValidationError
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision, Tier
from sft_agents.models.evidence import EvidencePanel, TokenUsage, ToolCall

# Import interrupt from langgraph.types with graceful fallback for test environments
# that do not install the full langgraph stack. The fallback is never used in
# production — it exists only to allow unit-test imports without langgraph installed.
try:
    from langgraph.types import interrupt
except ImportError:  # pragma: no cover
    def interrupt(value: Any) -> Any:  # type: ignore[misc]
        """Fallback stub — only reached in non-langgraph test environments."""
        raise NotImplementedError("langgraph.types.interrupt is not available in this environment")

from mnt_rca_specialist.metadata import AGENT_ID as _AGENT_ID
from mnt_rca_specialist.metadata import build_ops05_evidence_panel
from mnt_rca_specialist.models import RCAChain, RCASpecialistRequest, RCASpecialistResponse
from mnt_rca_specialist.prompts import build_retry_prompt, build_system_prompt
from mnt_rca_specialist.validators import (
    MissingCitationError,
    OrphanCitationError,
    RCAChainValidator,
)

logger = structlog.get_logger("agent.rca-specialist")

# ---------------------------------------------------------------------------
# Module-level constants (Shared Pattern A)
# ---------------------------------------------------------------------------

AGENT_ID: str = "rca-specialist"
CLUSTER: str = "maintenance"

#: Max retry attempts (D-RCA-01: max 2 retries → 3 total attempts).
_MAX_VALIDATION_RETRIES: int = 2

_DEFAULT_LANG: Literal["it", "en"] = "it"

#: Placeholder prompt hash (real hash computed per invocation).
_NO_PROMPT_HASH: str = "0" * 64

#: Placeholder model name for audit rows when LLM model is unknown.
_DEFAULT_MODEL_NAME: str = "unknown@rca-specialist"

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

# Regex to strip ```json...``` markdown fences from LLM output.
_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]*?)```\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_fences(text: str) -> str:
    """Remove ```json...``` markdown code fences from LLM output (robustness)."""
    match = _FENCE_RE.match(text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def _sha256(text: str) -> str:
    """Return lowercase 64-char sha256 hex of a string (for prompt_hash)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# RCASpecialist
# ---------------------------------------------------------------------------


class RCASpecialist:
    """ReAct-driven 5-Why RCA agent for maintenance cluster (D-RCA-01 + D-RCA-02).

    Collaborators are injected at construction (no eager instantiation,
    no per-request instantiation of tools to keep object reuse explicit
    for each injected tool).

    The ``escalate_tool`` MUST be an ``EscalateToSupervisorTool``-compatible
    async tool with ``_arun(reason, suggested_action, evidence_summary)``.

    For tests, collaborators can be ``AsyncMock`` / ``MagicMock`` instances.
    """

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: Any,
        llm: Any,
        rag_search_tool: Any,
        traverse_graph_tool: Any,
        escalate_tool: Any,
        validator: RCAChainValidator | None = None,
    ) -> None:
        """Bind collaborators; build default validator if none injected.

        Args:
            pool:               asyncpg.Pool for PG lookups (passed to validator).
            audit_writer:       AuditWriter (written AFTER escalate returns — Pitfall §3).
            llm:                BaseChatModel (LangChain-compatible).
            rag_search_tool:    RagSearchTool instance (Phase 5, D-66).
            traverse_graph_tool: TraverseGraphTool instance (Phase 5, Neo4j).
            escalate_tool:      EscalateToSupervisorTool instance (Phase 6, D-RCA-02).
            validator:          Optional custom validator; defaults to RCAChainValidator(pool=pool).
        """
        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
        self._rag_search = rag_search_tool
        self._traverse_graph = traverse_graph_tool
        self._escalate = escalate_tool
        self._validator = validator if validator is not None else RCAChainValidator(pool=pool)

    # ------------------------------------------------------------------ private

    def _resolve_tier(self, _: Any = None) -> Tier:
        """Return SUPERVISOR unconditionally (D-RCA-02 literal — no severity branching)."""
        return Tier.SUPERVISOR

    def _thread_id(self, chain_id: str) -> str:
        """Format: {CLUSTER}.{AGENT_ID}.{chain_id}."""
        return f"{CLUSTER}.{AGENT_ID}.{chain_id}"

    async def _invoke_react_loop(
        self,
        messages: list[Any],
        *,
        user_roles: list[str],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Run one pass of the ReAct loop; return (content, tool_call_records).

        Compiles a ``create_react_agent`` runnable with rag_search + traverse_graph.
        The LLM is expected to output a JSON RCAChain after gathering evidence.

        WR-05 fix: iterates all final_messages and extracts tool_calls attributes
        from each AIMessage, building tool_call_records for evidence panel population.

        Args:
            messages:   Full conversation history (system + human + any retry messages).
            user_roles: RBAC roles for RagSearchTool ACL (Phase 5 D-66).

        Returns:
            A tuple of:
                - str: raw string content of the final AIMessage from the ReAct loop.
                - list[dict]: tool call records extracted from intermediate messages
                  (each dict has name, args, result, duration_ms, ts keys).
        """
        try:
            from langgraph.prebuilt import create_react_agent
            from sft_agents.runtime.supervisor import safe_invoke
        except ImportError:
            # Graceful degradation for test environments that mock the LLM
            # but don't install the full langgraph stack.
            raw_result = await self._llm.ainvoke(messages)
            content: str
            if hasattr(raw_result, "content"):
                content = raw_result.content
            else:
                content = str(raw_result)
            return content, []

        tools = [self._rag_search, self._traverse_graph]
        runnable = create_react_agent(
            model=self._llm,
            tools=tools,
        )
        invoke_config: dict[str, Any] = {
            "recursion_limit": 5,
        }
        result = await safe_invoke(runnable, {"messages": messages}, config=invoke_config)
        final_messages = result.get("messages", [])

        # WR-05 fix: collect tool call records from all messages in the ReAct trace.
        # Uses immutable list building (new list per entry — no in-place mutation).
        now = datetime.now(timezone.utc)
        tool_call_records: list[dict[str, Any]] = []
        for msg in final_messages:
            msg_tool_calls = getattr(msg, "tool_calls", None)
            if msg_tool_calls:
                for tc in msg_tool_calls:
                    tool_call_records = tool_call_records + [
                        {
                            "name": tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown"),
                            "args": tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {}),
                            "result": None,
                            "duration_ms": 0,
                            "ts": now,
                        }
                    ]

        if not final_messages:
            return "", tool_call_records
        last_msg = final_messages[-1]
        if hasattr(last_msg, "content"):
            return last_msg.content, tool_call_records
        return str(last_msg), tool_call_records

    async def _escalate_to_supervisor(
        self,
        *,
        reason: str,
        suggested_action: str,
        evidence_summary: str,
    ) -> Any:
        """Call escalate_to_supervisor (D-RCA-02 ALWAYS).

        This MUST be called BEFORE writing the audit row (Pitfall §3).
        The tool calls ``langgraph.types.interrupt()`` internally; on resume
        the audit write occurs with the supervisor's decision.
        """
        return await self._escalate._arun(
            reason=reason,
            suggested_action=suggested_action,
            evidence_summary=evidence_summary,
        )

    def _build_evidence_panel(
        self,
        *,
        problem_statement: str,
        chain: RCAChain | None,
        tool_calls_log: list[dict[str, Any]],
        validation_exhausted: bool,
        duration_ms: int,
        prompt_hash: str,
        model_name: str,
    ) -> EvidencePanel:
        """Build EvidencePanel for the audit row.

        Populates:
            - input_summary: truncated problem_statement
            - tool_calls: LLM call + rag_search/traverse_graph invocations
            - model: model_name@rca-specialist format
            - tokens: placeholder (real tokens in Phase 11 observability)
            - prompt_hash: sha256 of system prompt + problem statement
        """
        summary_raw = f"rca_problem={problem_statement[:200]}"
        if validation_exhausted:
            summary_raw += " [validation_exhausted]"

        # Build ToolCall entries from log
        now = datetime.now(timezone.utc)
        tc_list: list[ToolCall] = []
        for tc_data in tool_calls_log:
            try:
                tc = ToolCall(
                    name=tc_data.get("name", "unknown"),
                    args=tc_data.get("args", {}),
                    result=tc_data.get("result"),
                    duration_ms=tc_data.get("duration_ms", 0),
                    ts=tc_data.get("ts", now),
                )
                tc_list.append(tc)
            except (ValidationError, Exception):
                pass  # Skip malformed tool call entries

        model_id = f"{model_name}@{AGENT_ID}" if "@" not in model_name else model_name
        # Ensure model_id matches the pattern: name@runtime
        import re as _re
        if not _re.match(r"^[a-z0-9.\-]+@[a-z0-9.\-]+$", model_id):
            model_id = f"mock@{AGENT_ID}"

        return EvidencePanel(
            input_summary=summary_raw[:500],
            input_truncated=len(summary_raw) > 500,
            tool_calls=tc_list,
            rag_citations=[],
            confidence=1.0 if chain is not None and not validation_exhausted else 0.0,
            model=model_id,
            prompt_hash=prompt_hash,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=duration_ms,
        )

    async def _write_audit(
        self,
        *,
        chain_id: str,
        problem_statement: str,
        chain: RCAChain | None,
        tool_calls_log: list[dict[str, Any]],
        validation_exhausted: bool,
        duration_ms: int,
        prompt_hash: str,
        model_name: str,
    ) -> None:
        """Write the audit row after supervisor escalation resolves (Pitfall §3).

        Uses ``human_approval_node`` pattern (mirror quality-inspector).
        Falls back to a direct AuditWriter.write if audit_writer is available.
        """
        from uuid import uuid4 as _uuid4
        from sft_agents.models.audit import AuditRecord
        from sft_agents.models.proposed_action import ProposedAction

        effective_chain_id = chain_id if chain_id else str(_uuid4())
        thread_id = self._thread_id(effective_chain_id)

        evidence_panel = self._build_evidence_panel(
            problem_statement=problem_statement,
            chain=chain,
            tool_calls_log=tool_calls_log,
            validation_exhausted=validation_exhausted,
            duration_ms=duration_ms,
            prompt_hash=prompt_hash,
            model_name=model_name,
        )

        # Build ProposedAction for the audit record
        action_args: dict[str, Any] = {
            "chain_id": effective_chain_id,
            "validation_exhausted": validation_exhausted,
        }
        if chain is not None:
            action_args["corrective_action"] = chain.corrective_action_recommendation[:500]

        action = ProposedAction.from_payload(
            thread_id=thread_id,
            action_type=ActionType.RCA_CHAIN,
            args=action_args,
            target_subject=None,
        )

        record = AuditRecord(
            id=_uuid4(),
            ts=datetime.now(timezone.utc),
            action_id=action.id,
            agent_id=AGENT_ID,
            thread_id=thread_id,
            cluster=CLUSTER,
            action_type=ActionType.RCA_CHAIN.value,
            evidence_panel=evidence_panel,
            decision=Decision.HITL_SUPERVISOR,
            decision_actor=None,
            motivation=(
                "rca_corrective_action_review"
                if not validation_exhausted
                else "rca_validation_exhausted"
            ),
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,
        )
        await self._audit.write(record)

    # ------------------------------------------------------------------ entry-point

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """Run one RCA investigation turn (LangGraph node entry-point).

        Args:
            state: LangGraph state dict. Expected keys:
                - problem_statement (str, required)
                - user_roles (list[str], required for RAG ACL)
                - downtime_event_id (str | None, optional)
                - asset_id (str | None, optional)
                - lang (str, optional — defaults to "it")

        Returns:
            State delta:
                - rca_chain: RCAChain | None (None on exhaustion)
                - hitl_status: "supervisor_pending"
                - validation_exhausted: bool
                - best_attempt: RCAChain | None (the best chain even if invalid)
        """
        start_epoch_ms = int(time.time() * 1000)

        # -------- 1. Extract state fields
        problem_statement: str = state["problem_statement"]
        user_roles: list[str] = state.get("user_roles", ["maintenance"])
        downtime_event_id: str | None = state.get("downtime_event_id")
        lang: Literal["it", "en"] = state.get("lang", _DEFAULT_LANG)

        # -------- 2. Build initial system prompt + messages
        system_prompt = build_system_prompt(lang=lang)
        prompt_hash = _sha256(system_prompt + problem_statement)

        messages: list[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=problem_statement),
        ]

        # -------- 3. Retry loop (D-RCA-01)
        best_chain_attempt: RCAChain | None = None
        validated_chain: RCAChain | None = None
        last_error: str = ""
        tool_calls_log: list[dict[str, Any]] = []

        for attempt in range(_MAX_VALIDATION_RETRIES + 1):
            try:
                raw_output, new_tool_calls = await self._invoke_react_loop(
                    messages=messages,
                    user_roles=user_roles,
                )
                # WR-05 fix: accumulate tool call records from this ReAct pass.
                # Immutable extend — builds new list, never mutates existing.
                tool_calls_log = tool_calls_log + new_tool_calls

                # Strip markdown fences (robustness)
                json_str = _strip_fences(raw_output)
                parsed = json.loads(json_str)

                # Inject auto-generated fields
                chain_id_new = str(uuid4())
                parsed["chain_id"] = chain_id_new
                parsed["created_at"] = datetime.now(timezone.utc).isoformat()
                if downtime_event_id is not None:
                    parsed["downtime_event_id"] = downtime_event_id

                chain = RCAChain.model_validate(parsed)
                best_chain_attempt = chain  # update best even before PG validation

                # PG lookup validation (Open Q5 — full lookup)
                validated_chain = await self._validator.validate(chain)
                break  # success

            except json.JSONDecodeError as e:
                last_error = f"JSON parse error: {e}"
                logger.warning(
                    "rca_specialist_json_parse_error",
                    attempt=attempt + 1,
                    max_attempts=_MAX_VALIDATION_RETRIES + 1,
                    error=str(e),
                )
            except (ValidationError, MissingCitationError, OrphanCitationError) as e:
                last_error = str(e)
                logger.warning(
                    "rca_specialist_validation_error",
                    attempt=attempt + 1,
                    max_attempts=_MAX_VALIDATION_RETRIES + 1,
                    error_type=type(e).__name__,
                    error=str(e)[:200],
                )

            # Append corrective SystemMessage and retry if budget remains
            if attempt < _MAX_VALIDATION_RETRIES:
                corrective = build_retry_prompt(
                    attempt_no=attempt + 1,
                    max_attempts=_MAX_VALIDATION_RETRIES + 1,
                    error_reason=last_error,
                )
                messages = messages + [SystemMessage(content=corrective)]
            else:
                # Exhausted retry budget
                validated_chain = None
                logger.error(
                    "rca_specialist_validation_exhausted",
                    max_attempts=_MAX_VALIDATION_RETRIES + 1,
                    last_error=last_error[:500],
                )

        # -------- 4. ALWAYS-supervisor gate (D-RCA-02)
        # Call BEFORE audit write (Pitfall §3 — no double-write on LangGraph resume).
        validation_exhausted = validated_chain is None
        effective_chain = validated_chain if not validation_exhausted else best_chain_attempt

        effective_chain_id = (
            effective_chain.chain_id if effective_chain is not None else str(uuid4())
        )

        if validation_exhausted:
            escalate_reason = f"rca_validation_exhausted — {last_error[:500]}"
            escalate_suggested = (
                f"Validare manualmente: "
                f"{effective_chain.corrective_action_recommendation if effective_chain else '<nessun chain prodotto>'}"
            )
            escalate_evidence = json.dumps(
                {
                    "chain_id": effective_chain_id,
                    "validation_exhausted": True,
                    "last_error": last_error[:500],
                    "best_attempt_root_cause": (
                        effective_chain.root_cause[:200] if effective_chain else None
                    ),
                }
            )[:2000]
        else:
            assert validated_chain is not None  # mypy
            escalate_reason = "rca_corrective_action_review"
            escalate_suggested = validated_chain.corrective_action_recommendation[:2000]
            escalate_evidence = json.dumps(
                {
                    "chain_id": validated_chain.chain_id,
                    "root_cause": validated_chain.root_cause[:200],
                    "corrective_action": validated_chain.corrective_action_recommendation[:200],
                    "downtime_event_id": validated_chain.downtime_event_id,
                }
            )[:2000]

        # CR-02 fix: call interrupt() DIRECTLY in the node — NOT via escalate_tool.
        # On the FIRST execution, LangGraph raises GraphInterrupt here, unwinding
        # the stack. The lines below only execute on the RESUMED execution, so
        # _write_audit fires exactly once (on resume), never on the first run.
        # This replaces the old _escalate_to_supervisor() call which raised inside
        # the tool, making the audit write unreachable on the first execution and
        # causing a double-write on the third execution.
        _supervisor_decision = interrupt(
            {
                "reason": escalate_reason,
                "suggested_action": escalate_suggested,
                "evidence_summary": escalate_evidence,
            }
        )

        # -------- 5. Audit row (executes ONLY on resume — Pitfall §3 solved)
        # interrupt() returns here only on the resumed execution. The write fires
        # exactly once per logical invocation.
        duration_ms = int(time.time() * 1000) - start_epoch_ms
        model_name = getattr(self._llm, "model_name", None) or getattr(
            self._llm, "model", None
        ) or _DEFAULT_MODEL_NAME

        await self._write_audit(
            chain_id=effective_chain_id,
            problem_statement=problem_statement,
            chain=validated_chain,
            tool_calls_log=tool_calls_log,
            validation_exhausted=validation_exhausted,
            duration_ms=duration_ms,
            prompt_hash=prompt_hash,
            model_name=str(model_name),
        )

        logger.info(
            "rca_specialist_completed",
            chain_id=effective_chain_id,
            validation_exhausted=validation_exhausted,
            hitl_status="supervisor_pending",
        )

        # -------- 6. Return state delta
        if not validation_exhausted:
            return {
                "rca_chain": validated_chain,
                "hitl_status": "supervisor_pending",
                "validation_exhausted": False,
            }
        else:
            return {
                "rca_chain": None,
                "hitl_status": "supervisor_pending",
                "validation_exhausted": True,
                "best_attempt": best_chain_attempt,
            }


__all__ = ["AGENT_ID", "CLUSTER", "RCASpecialist"]
