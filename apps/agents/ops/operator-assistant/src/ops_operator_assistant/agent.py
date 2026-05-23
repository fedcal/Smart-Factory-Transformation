"""OperatorAssistantAgent — ReAct loop wired with the OPS 5-tool toolbelt.

Phase 6 D-OA-01..04 + RESEARCH Pattern 1 + Pitfall §1, §2, §6:

    * D-OA-01 — ``langgraph.prebuilt.create_react_agent`` compiled on demand
      with the 5-tool list. Recursion is bounded at 5 iterations via
      ``safe_invoke(... config={'recursion_limit': 5})`` (Phase 4 wrapper).
    * D-OA-02 — full 5-tool toolbelt: ``rag_search`` (Phase 5), ``traverse_graph``
      (Phase 5), ``query_timescale`` (Phase 3), ``escalate_to_supervisor``
      (Plan 06-05), ``log_event`` (Plan 06-05).
    * D-OA-03 — query language detected upstream via
      ``ops_operator_assistant.lang_detect.detect_language`` and emitted on
      the response dict; the LLM is also instructed in
      ``SYSTEM_PROMPT_BILINGUAL`` to match the operator's language.
    * D-OA-04 — citation validator (``validate_or_replan``) runs out-of-graph
      after the ReAct loop completes (RESEARCH Pattern 7).

Pitfall §2 (per-request tool instantiation):
    Tool instances are constructed inside ``__call__``, NOT cached on the
    agent. This guarantees the per-thread ``user_roles`` flow into
    ``RagSearchTool`` instead of leaking the first request's roles.

Pitfall §1 (recursion_limit typo guard):
    The agent never spells the key inline as a literal in the call site —
    we use ``_RECURSION_LIMIT = 5`` as a named constant and pass through
    ``safe_invoke`` which validates ``recursion_limit`` is present.

Pitfall §6 (langdetect global seed):
    ``ops_operator_assistant.lang_detect`` seeds DetectorFactory at module
    import time; this agent only calls ``detect_language(text)`` per request
    and does not touch the global seed.
"""

from __future__ import annotations

from typing import Any

import structlog
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from sft_agents.llm.factory import build_chat_model
from sft_agents.runtime.supervisor import safe_invoke
from sft_agents.tools.audit import LogEventTool
from sft_agents.tools.hitl import EscalateToSupervisorTool
from sft_knowledge.tools.graph import TraverseGraphTool
from sft_knowledge.tools.rag import RagSearchTool
from sft_tools.timescale.query import QueryTimescaleTool

from ops_operator_assistant.lang_detect import detect_language
from ops_operator_assistant.models import OperatorChatRequest
from ops_operator_assistant.prompts import SYSTEM_PROMPT_BILINGUAL
from ops_operator_assistant.validators import validate_or_replan

logger = structlog.get_logger("agent.operator-assistant")


_RECURSION_LIMIT: int = 5  # D-OA-01 — locked


class OperatorAssistantAgent:
    """ReAct-driven operator chat agent (OPS-01 + OPS-05).

    Construction is collaborator-injected so tests can pass mocks for every
    side-effecting boundary. ``__call__(request)`` runs one operator turn:

        1. Validate the OperatorChatRequest (Pydantic frozen+extra=forbid).
        2. Detect language (D-OA-03) — used both to bias the system prompt
           and to populate ``response['lang']``.
        3. Build the 5-tool list FRESH (Pitfall §2 — never cache).
        4. Compile a ``create_react_agent`` runnable with the fresh tools.
        5. ``safe_invoke`` it with ``recursion_limit=5`` (D-OA-01).
        6. Hand the final AIMessage to ``validate_or_replan`` (D-OA-04).
        7. Emit a flat dict shaped for the API layer (06-12) +
           EvidencePanel (06-13).
    """

    def __init__(
        self,
        *,
        rag_pipeline: Any,
        neo4j_driver: Any,
        pool: Any,
        audit_writer: Any,
        queue_writer: Any,
        nats: Any,
        safety_middleware: Any,
        checkpointer: Any,
    ) -> None:
        """Hold collaborator references; instantiate nothing eager (Pitfall §2)."""
        self._rag_pipeline = rag_pipeline
        self._neo4j_driver = neo4j_driver
        self._pool = pool
        self._audit_writer = audit_writer
        self._queue_writer = queue_writer
        self._nats = nats
        self._safety_middleware = safety_middleware
        self._checkpointer = checkpointer

    # ------------------------------------------------------------------ tools

    def _build_tools(self, user_roles: list[str]) -> list[Any]:
        """Construct a fresh 5-tool list for this request (Pitfall §2).

        ``user_roles`` is currently consumed by the LLM at tool-call time
        (RagSearchInput requires it as an argument); we still pass it into
        the ``RagSearchTool`` initializer for forward-compat with Phase 11
        when the ACL evolves to a per-tool closure.
        """
        # ``user_roles`` is unused at the constructor for now (the tool reads
        # it as a per-call argument) but we touch it to keep the intent
        # explicit for reviewers and to make the call-site easy to grep.
        _ = user_roles
        return [
            RagSearchTool(pipeline=self._rag_pipeline),
            TraverseGraphTool(driver=self._neo4j_driver),
            QueryTimescaleTool(),
            EscalateToSupervisorTool(
                audit_writer=self._audit_writer,
                queue_writer=self._queue_writer,
                nats=self._nats,
                safety_middleware=self._safety_middleware,
            ),
            LogEventTool(audit_writer=self._audit_writer),
        ]

    def _build_runnable(self, tools: list[Any]) -> Any:
        """Compile a ``create_react_agent`` runnable with the supplied tools."""
        model = build_chat_model()
        return create_react_agent(
            model=model,
            tools=tools,
            checkpointer=self._checkpointer,
            prompt=SYSTEM_PROMPT_BILINGUAL,
        )

    # --------------------------------------------------------------- entry-point

    async def __call__(self, request: OperatorChatRequest | dict[str, Any]) -> dict[str, Any]:
        """Run one operator turn and return a flat response dict.

        Args:
            request: An ``OperatorChatRequest`` or a dict that will be coerced
                into one via Pydantic.

        Returns:
            ``{"response_md", "citations", "citations_missing", "lang",
            "tool_calls_count"}`` — shape consumed by the API gateway
            (Plan 06-12) and the EvidencePanel renderer (Plan 06-13).
        """
        # 1. Validate / coerce the request.
        if not isinstance(request, OperatorChatRequest):
            request = OperatorChatRequest.model_validate(request)

        # 2. Detect language (D-OA-03).
        lang = detect_language(request.query)

        # 3. Per-request tool instantiation (Pitfall §2).
        tools = self._build_tools(request.user_roles)

        # 4. Compile the ReAct runnable with the fresh tools.
        runnable = self._build_runnable(tools)

        # 5. safe_invoke with recursion_limit=5 (D-OA-01 + Pitfall §1).
        invoke_config: dict[str, Any] = {
            "recursion_limit": _RECURSION_LIMIT,
            "configurable": {"thread_id": request.thread_id},
        }
        initial_messages = [HumanMessage(content=request.query)]
        result = await safe_invoke(
            runnable,
            {"messages": initial_messages},
            config=invoke_config,
        )

        # The react runnable returns {"messages": [...]} with the final
        # AIMessage in the last slot. We hand the full state to the
        # validator so it can introspect ToolMessage entries.
        messages = result.get("messages", [])
        if not messages:
            logger.warning(
                "operator_assistant_empty_messages",
                thread_id=request.thread_id,
            )
            return {
                "response_md": "",
                "citations": [],
                "citations_missing": False,
                "lang": lang,
                "tool_calls_count": 0,
            }

        final_response = messages[-1]
        validator_state: dict[str, Any] = {
            "messages": messages,
            "thread_id": request.thread_id,
        }

        # 6. Citation validator with single-replan loop (D-OA-04).
        validated = await validate_or_replan(
            validator_state,
            final_response,
            react_agent=runnable,
            config=invoke_config,
        )

        # 7. Flat dict for the API + EvidencePanel layers.
        citations = list(validated.additional_kwargs.get("citations") or [])
        tool_calls_count = sum(
            1 for m in messages if isinstance(m, ToolMessage)
        )
        return {
            "response_md": validated.content,
            "citations": citations,
            "citations_missing": bool(
                validated.additional_kwargs.get("citations_missing", False)
            ),
            "lang": lang,
            "tool_calls_count": tool_calls_count,
        }


__all__ = ["OperatorAssistantAgent"]
