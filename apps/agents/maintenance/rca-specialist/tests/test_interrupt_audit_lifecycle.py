"""Regression tests for CR-02 (interrupt-before-audit) and WR-05 (empty evidence panel).

CR-02: The audit write must happen exactly once, on the RESUMED execution only.
       Current broken code: _escalate_to_supervisor calls self._escalate._arun()
       which calls langgraph.types.interrupt() internally, unwinding the stack
       before _write_audit is reached on the first run. On the second (resumed)
       run the node replays and audit write fires. On a third run it fires again
       — double-write.

       Fix: call interrupt() DIRECTLY in __call__ (not via escalate tool).
       interrupt() returns on resume; place _write_audit AFTER the return value.
       The escalate tool path no longer controls the interrupt timing.

WR-05: tool_calls_log is initialized [] and never populated, so the evidence
       panel's tool_calls list is always empty. The _invoke_react_loop result
       carries tool-call messages that are silently discarded.

       Fix: in _invoke_react_loop (or in __call__ after calling it), iterate
       final_messages and read getattr(msg, "tool_calls", None) to populate
       tool_calls_log before passing it to _write_audit.

Test A: test_audit_written_once_on_resume_not_first_run
    Mocks escalate_tool._arun to raise GraphInterrupt on first call (first run)
    and return a supervisor decision on second call (resumed run).
    Patches _write_audit as AsyncMock to count calls.

    Against CURRENT CODE:
    - First call: escalate._arun raises GraphInterrupt → node unwinds → _write_audit=0
    - Second call: escalate._arun returns → _write_audit called ONCE
    - The test asserts that after the first call _write_audit.call_count == 0 ✓
    - The test then simulates "direct interrupt() call" by checking whether
      the node, on resume, calls _write_audit via the interrupt() return value
      path. Against current code: interrupt() is never called directly in __call__,
      so patching interrupt() at the module level (with create=True) has no effect.
      The fix replaces the escalate call with a direct interrupt() call.
      Test asserts: after fix, interrupt() is the gate, not escalate._arun.
      Against current code: _write_audit still fires via escalate path (not via
      interrupt return), so the verification that uses interrupt-patched semantics
      to assert "write fires only on interrupt() return" fails.

    Specific failing assertion: after the fix the escalate_tool._arun should NOT
    be called from __call__ (the interrupt is direct). Against current code,
    escalate_tool._arun IS called in __call__. We assert it is NOT called after
    the fix. Against current code this assertion FAILS.

Test B: test_tool_calls_log_populated_from_react_messages
    Stubs the underlying LangGraph safe_invoke result to return AIMessage objects
    with tool_calls attributes. Patches _write_audit to capture tool_calls_log.

    Against CURRENT CODE: _invoke_react_loop only reads last_msg.content; the
    tool_calls in earlier messages are ignored. tool_calls_log stays [].
    The assertion on non-empty tool_calls_log FAILS.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from langgraph.errors import GraphInterrupt

from mnt_rca_specialist.agent import RCASpecialist


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

UTC = timezone.utc
_TS = datetime(2026, 5, 23, 10, 0, 0, tzinfo=UTC)

_VALID_CHAIN_JSON: dict[str, Any] = {
    "chain_id": "123e4567-e89b-12d3-a456-426614174000",
    "problem_statement": "La macchina 01 si è fermata durante la produzione.",
    "why_1": {
        "question": "Perché si è fermata la macchina?",
        "answer": "Perché il subbio era usurato.",
        "citations": [
            {
                "source_uri": "doc://sop-001",
                "snippet": "Sostituire il subbio dopo 5000 ore.",
                "score": 0.92,
                "retrieved_at": "2026-05-23T10:00:00+00:00",
            }
        ],
        "confidence": 0.85,
    },
    "why_2": {
        "question": "Perché il subbio era usurato?",
        "answer": "Perché non era stata effettuata la manutenzione.",
        "citations": [
            {
                "source_uri": "doc://sop-001",
                "snippet": "Manutenzione programmata ogni 5000 ore.",
                "score": 0.88,
                "retrieved_at": "2026-05-23T10:00:00+00:00",
            }
        ],
        "confidence": 0.82,
    },
    "why_3": {
        "question": "Perché non era stata effettuata la manutenzione?",
        "answer": "Perché non era pianificata nel calendario.",
        "citations": [
            {
                "source_uri": "doc://sop-001",
                "snippet": "Piano di manutenzione preventiva.",
                "score": 0.80,
                "retrieved_at": "2026-05-23T10:00:00+00:00",
            }
        ],
        "confidence": 0.78,
    },
    "why_4": {
        "question": "Perché non era pianificata nel calendario?",
        "answer": "Perché il sistema di tracking non era aggiornato.",
        "citations": [
            {
                "source_uri": "doc://sop-001",
                "snippet": "Aggiornamento del sistema CMMS.",
                "score": 0.75,
                "retrieved_at": "2026-05-23T10:00:00+00:00",
            }
        ],
        "confidence": 0.75,
    },
    "why_5": {
        "question": "Perché il sistema CMMS non era aggiornato?",
        "answer": "Perché mancava un processo di verifica periodica.",
        "citations": [
            {
                "source_uri": "doc://sop-001",
                "snippet": "Processo di verifica periodica del CMMS.",
                "score": 0.72,
                "retrieved_at": "2026-05-23T10:00:00+00:00",
            }
        ],
        "confidence": 0.72,
    },
    "root_cause": "Mancanza di processo di manutenzione preventiva strutturato.",
    "corrective_action_recommendation": "Implementare un piano di manutenzione preventiva con CMMS.",
    "downtime_event_id": None,
    "created_at": "2026-05-23T10:00:00+00:00",
}

_STATE: dict[str, Any] = {
    "problem_statement": "La macchina 01 si è fermata durante la produzione.",
    "user_roles": ["maintenance"],
    "downtime_event_id": None,
    "lang": "it",
}


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def _make_validator_mock() -> MagicMock:
    """Return a mock RCAChainValidator that validates any chain successfully."""
    validator = MagicMock()
    validator.validate = AsyncMock(side_effect=lambda chain: chain)
    return validator


def _make_llm_mock() -> MagicMock:
    """Return a mock LLM returning the valid chain JSON via ainvoke."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(
        return_value=MagicMock(content=json.dumps(_VALID_CHAIN_JSON))
    )
    llm.model_name = "qwen2.5-7b"
    return llm


def _make_specialist(
    *,
    escalate_tool: Any | None = None,
) -> tuple[RCASpecialist, MagicMock, MagicMock]:
    """Build an RCASpecialist with collaborators mocked.

    Returns (specialist, escalate_tool_mock, audit_writer_mock).
    """
    esc = escalate_tool or MagicMock()
    audit_writer = MagicMock()
    audit_writer.write = AsyncMock()

    specialist = RCASpecialist(
        pool=MagicMock(),
        audit_writer=audit_writer,
        llm=_make_llm_mock(),
        rag_search_tool=MagicMock(),
        traverse_graph_tool=MagicMock(),
        escalate_tool=esc,
        validator=_make_validator_mock(),
    )
    return specialist, esc, audit_writer


# ---------------------------------------------------------------------------
# Test A — CR-02: interrupt ordering and audit-once-on-resume contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_written_once_on_resume_not_first_run() -> None:
    """CR-02 regression: audit write occurs exactly once, on the resumed execution.

    Simulates first run where escalate raises GraphInterrupt (aborting the node)
    and a second run (resume) where escalate returns normally.

    Contract verified:
    1. After first run (interrupt raised): _write_audit call count == 0.
    2. After second run (resume): _write_audit call count == 1.
    3. After fix: escalate_tool._arun is NOT called from __call__ (interrupt() is
       called directly instead). Against current code, escalate_tool._arun IS called
       from __call__ via _escalate_to_supervisor — this assertion FAILS.

    Assertion (3) is the primary RED assertion: it fails against current code
    because current __call__ invokes self._escalate_to_supervisor() which calls
    self._escalate._arun(). After the fix, __call__ calls interrupt() directly
    and does NOT route through _escalate_to_supervisor() for the interrupt.
    """
    escalate_tool = MagicMock()

    # First call: _arun raises GraphInterrupt (simulates LangGraph first execution).
    # Second call: _arun returns supervisor decision (simulates resume).
    escalate_call_count = 0

    async def _escalate_arun(**kwargs: Any) -> Any:
        nonlocal escalate_call_count
        escalate_call_count += 1
        if escalate_call_count == 1:
            # First execution: interrupt fires inside the tool, unwinding the stack.
            raise GraphInterrupt(
                {
                    "reason": kwargs.get("reason", ""),
                    "suggested_action": kwargs.get("suggested_action", ""),
                    "evidence_summary": kwargs.get("evidence_summary", ""),
                }
            )
        # Resume: return supervisor decision.
        return {"approved": True, "supervisor_id": "user-001"}

    escalate_tool._arun = AsyncMock(side_effect=_escalate_arun)

    specialist, _, audit_writer = _make_specialist(escalate_tool=escalate_tool)

    # Mock _invoke_react_loop to return (valid JSON, []) without invoking real LangGraph.
    # Returns a tuple (content, tool_call_records) as per the WR-05 fix.
    specialist._invoke_react_loop = AsyncMock(  # type: ignore[method-assign]
        return_value=(json.dumps(_VALID_CHAIN_JSON), [])
    )

    # Track interrupt() call count at the module level to simulate first-run vs resume.
    # interrupt() is now imported at module level in agent.py (CR-02 fix).
    interrupt_call_count = 0

    def _simulated_interrupt(value: Any) -> Any:
        nonlocal interrupt_call_count
        interrupt_call_count += 1
        if interrupt_call_count == 1:
            # First execution: interrupt raises, aborting the node.
            raise GraphInterrupt(value)
        # Resume: interrupt returns the supervisor decision.
        return {"approved": True, "decision": "proceed"}

    # ---- First execution: node should unwind before _write_audit ----
    with patch("mnt_rca_specialist.agent.interrupt", _simulated_interrupt):
        with pytest.raises(GraphInterrupt):
            await specialist(state=_STATE)

        assert audit_writer.write.call_count == 0, (
            f"CR-02 FAIL (first run): audit_writer.write was called "
            f"{audit_writer.write.call_count} time(s) — expected 0. "
            f"The audit write must NOT fire on the first execution."
        )

        # ---- Second execution (resume): _write_audit should fire exactly once ----
        # Patch _write_audit to avoid AuditRecord Pydantic constraint (approval_id=None
        # with HITL_SUPERVISOR is a separate pre-existing bug outside CR-02 scope).
        write_audit_calls: list[dict] = []

        async def _spy_write_audit(**kwargs: Any) -> None:
            write_audit_calls.append(dict(kwargs))

        with patch.object(specialist, "_write_audit", side_effect=_spy_write_audit):
            await specialist(state=_STATE)

    assert len(write_audit_calls) == 1, (
        f"CR-02 FAIL (resume): _write_audit was called {len(write_audit_calls)} "
        f"time(s) — expected exactly 1. "
        f"Current code either skips (0) or double-writes (2+)."
    )

    # ---- Key structural assertion: after the fix, escalate_tool._arun must
    # NOT be called from __call__ on the second (resume) execution.
    # After the fix, interrupt() is called directly in __call__; the escalate
    # tool is no longer the mechanism for triggering the interrupt.
    # Against CURRENT code: escalate_tool._arun IS called (escalate_call_count >= 2).
    # After FIX: __call__ uses interrupt() directly — escalate_call_count stays at 1
    # (the first call before the fix is applied; after fix it's 0 in __call__).
    #
    # With the fix in place:
    #   - escalate_call_count after first run = 0 (interrupt() is direct, not via tool)
    #   - escalate_call_count after second run = 0 (still not via tool)
    # Against current code:
    #   - escalate_call_count after first run = 1 (via _escalate_to_supervisor)
    #   - escalate_call_count after second run = 2 (called again on resume)
    # This test has already called the specialist twice; total escalate_call_count
    # after the fix should be 0 (because __call__ no longer calls _arun).
    assert escalate_call_count == 0, (
        f"CR-02 STRUCTURAL FAIL: escalate_tool._arun was called "
        f"{escalate_call_count} time(s) from __call__. "
        f"After the fix, interrupt() is called DIRECTLY in __call__; "
        f"escalate_tool._arun must NOT be called from the node. "
        f"Current code calls _escalate_to_supervisor() which routes to "
        f"escalate_tool._arun — this assertion fails against current code."
    )


# ---------------------------------------------------------------------------
# Test B — WR-05: tool_calls_log populated from ReAct result messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_calls_log_populated_from_react_messages() -> None:
    """WR-05 regression: tool_calls_log contains entries parsed from ReAct messages.

    The LangGraph safe_invoke result includes an AIMessage with a tool_calls
    attribute (simulating a rag_search call made by the LLM). After the fix,
    _invoke_react_loop (or __call__) reads these and populates tool_calls_log.

    Against CURRENT CODE: _invoke_react_loop only reads last_msg.content and
    discards all other messages. tool_calls_log stays []. The assertion that
    tool_calls_log is non-empty FAILS.
    """
    # Build mock final_messages returned by safe_invoke:
    #   msg_0: AIMessage with tool_calls (rag_search invocation)
    #   msg_1: AIMessage with the final JSON chain content (no tool_calls)
    msg_with_tool_calls = MagicMock()
    msg_with_tool_calls.tool_calls = [
        {
            "name": "rag_search",
            "args": {"query": "sostituzione subbio manutenzione preventiva"},
            "id": "tc_rag_001",
        }
    ]
    msg_with_tool_calls.content = ""  # intermediate message, not the final output

    msg_final = MagicMock()
    msg_final.content = json.dumps(_VALID_CHAIN_JSON)
    msg_final.tool_calls = None  # final message has no tool calls

    mock_safe_invoke_result = {
        "messages": [msg_with_tool_calls, msg_final],
    }

    async def _mock_safe_invoke(
        runnable: Any, inputs: Any, *, config: Any = None, **kwargs: Any
    ) -> dict:
        return mock_safe_invoke_result

    # Escalate tool returns immediately (no interrupt — we want to reach _write_audit).
    escalate_tool = MagicMock()
    escalate_tool._arun = AsyncMock(return_value={"approved": True})

    specialist, _, _ = _make_specialist(escalate_tool=escalate_tool)

    # Capture what tool_calls_log is passed to _write_audit.
    captured_tool_calls_log: list[list] = []

    async def _spy_write_audit(**kwargs: Any) -> None:
        captured_tool_calls_log.append(list(kwargs.get("tool_calls_log", [])))

    with (
        patch.object(specialist, "_write_audit", side_effect=_spy_write_audit),
        # Patch interrupt() so it returns a supervisor decision on resume
        # (rather than requiring a real LangGraph runnable context).
        patch("mnt_rca_specialist.agent.interrupt", return_value={"approved": True}),
        patch(
            "langgraph.prebuilt.create_react_agent",
            return_value=MagicMock(),
        ),
        patch(
            "sft_agents.runtime.supervisor.safe_invoke",
            side_effect=_mock_safe_invoke,
        ),
    ):
        await specialist(state=_STATE)

    assert len(captured_tool_calls_log) == 1, (
        f"WR-05 prerequisite FAIL: _write_audit not called "
        f"({len(captured_tool_calls_log)} times). "
        f"Cannot verify tool_calls_log without reaching _write_audit."
    )

    tool_calls_log = captured_tool_calls_log[0]

    assert len(tool_calls_log) > 0, (
        "WR-05 FAIL: tool_calls_log passed to _write_audit is empty []. "
        "_invoke_react_loop must parse tool_calls from final_messages and "
        "accumulate records into tool_calls_log. "
        "Current code: last_msg.content is returned but tool_calls in earlier "
        "messages are silently discarded — tool_calls_log stays []."
    )

    tool_names = [
        tc.get("name") for tc in tool_calls_log if isinstance(tc, dict)
    ]
    assert "rag_search" in tool_names, (
        f"WR-05 FAIL: 'rag_search' not found in tool_calls_log. "
        f"Got names: {tool_names!r}. "
        f"The evidence panel must record which tools the LLM called."
    )
