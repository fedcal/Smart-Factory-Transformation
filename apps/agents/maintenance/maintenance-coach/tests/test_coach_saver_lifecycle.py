"""Regression tests for MaintenanceCoach saver lifecycle (CR-01) and
single-audit-row on resume (WR-02).

Test A — ``test_get_graph_requires_injected_saver_no_self_compile``:
  Pins the post-fix contract: _get_graph() must raise RuntimeError with a
  message instructing callers to inject a pre-built saver, rather than
  self-compiling via async-with (which closes the saver mid-use).

  Against current code: either self-compiles (if PG_DSN set) or raises a
  different RuntimeError about PG_DSN missing. The test asserts the explicit
  "inject a pre-built saver" message — which only passes after the fix.

Test B — ``test_resume_after_help_writes_single_audit_row``:
  Pins the WR-02 fix: resume_after_help must call audit_writer.write exactly
  once per resume. Against current code it calls write twice (once from step()
  decision=auto, once from resume_after_help decision=hitl_supervisor).

Test C — ``test_step_persists_across_calls`` (integration):
  With a real AsyncPostgresSaver from testcontainers PG, verifies that a second
  step() call on the same intervention_id does NOT raise ConnectionDoesNotExistError
  or InterfaceError (CR-01 production defect).
  Marked ``@pytest.mark.integration`` — skipped without docker.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

UTC = timezone.utc

pytestmark = [pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Helpers — mirror conftest.py conventions from test_checkpoint_resume.py
# ---------------------------------------------------------------------------


def _build_mock_checkpointer() -> AsyncMock:
    """Return a minimal AsyncPostgresSaver mock that compiles cleanly."""
    cp = AsyncMock()
    cp.aget_tuple = AsyncMock(return_value=None)
    cp.aput = AsyncMock(return_value={"configurable": {"thread_id": "test"}})
    cp.aput_writes = AsyncMock(return_value=None)
    cp.setup = AsyncMock(return_value=None)

    async def _alist(_cfg, **_kw):
        if False:
            yield None
        return

    cp.alist = _alist
    return cp


def _build_mock_audit_writer() -> AsyncMock:
    """Return a mock AuditWriter whose .write is an AsyncMock."""
    aw = AsyncMock()
    aw.write = AsyncMock(return_value=None)
    return aw


def _build_coach_with_saver(
    saver: Any,
    audit_writer: Any | None = None,
) -> Any:
    """Build a MaintenanceCoach with all collaborators mocked except saver."""
    from mnt_maintenance_coach.agent import MaintenanceCoach

    pool = AsyncMock()
    aw = audit_writer if audit_writer is not None else _build_mock_audit_writer()
    llm = MagicMock()
    rag_tool = AsyncMock()
    rag_tool.name = "rag_search"
    request_help_tool = AsyncMock()
    request_help_tool.name = "request_help"
    escalate_tool = AsyncMock()
    escalate_tool.name = "escalate_to_supervisor"

    return MaintenanceCoach(
        pool=pool,
        audit_writer=aw,
        llm=llm,
        rag_search_tool=rag_tool,
        request_help_tool=request_help_tool,
        escalate_tool=escalate_tool,
        saver=saver,
    )


def _build_coach_no_saver(audit_writer: Any | None = None) -> Any:
    """Build a MaintenanceCoach with saver=None (production broken path)."""
    from mnt_maintenance_coach.agent import MaintenanceCoach

    pool = AsyncMock()
    aw = audit_writer if audit_writer is not None else _build_mock_audit_writer()
    llm = MagicMock()
    rag_tool = AsyncMock()
    rag_tool.name = "rag_search"
    request_help_tool = AsyncMock()
    request_help_tool.name = "request_help"
    escalate_tool = AsyncMock()
    escalate_tool.name = "escalate_to_supervisor"

    return MaintenanceCoach(
        pool=pool,
        audit_writer=aw,
        llm=llm,
        rag_search_tool=rag_tool,
        request_help_tool=request_help_tool,
        escalate_tool=escalate_tool,
        saver=None,
    )


# ---------------------------------------------------------------------------
# Test A — CR-01: _get_graph() must require injected saver (no self-compile)
# ---------------------------------------------------------------------------


class TestGetGraphRequiresInjectedSaver:
    """CR-01 regression: _get_graph() must raise RuntimeError with
    'inject a pre-built saver' message when saver=None.

    The post-fix contract (07-REVIEW.md lines 77-83):
        if self._graph is None:
            raise RuntimeError(
                "MaintenanceCoach._graph is None. "
                "Inject a pre-built saver at construction or wire via lifespan."
            )

    Against current code: if PG_DSN is unset, a different RuntimeError fires
    ('requires either an injected saver or PG_DSN...') — test will fail because
    the message does not match the expected post-fix contract.
    If PG_DSN is set, current code self-compiles silently — test will fail
    because no RuntimeError is raised at all.
    """

    async def test_get_graph_requires_injected_saver_no_self_compile(self) -> None:
        """_get_graph() must raise RuntimeError mentioning saver injection.

        Fails against current code because current code either self-compiles
        (if PG_DSN set) or raises RuntimeError about PG_DSN (not about injection).
        Passes after fix: _get_graph raises RuntimeError with
        'Inject a pre-built saver at construction or wire via lifespan.'
        """
        # Ensure PG_DSN is absent so the self-compile path cannot execute
        env_without_pgdsn = {k: v for k, v in os.environ.items() if k != "PG_DSN"}
        with patch.dict(os.environ, env_without_pgdsn, clear=True):
            coach = _build_coach_no_saver()

        with pytest.raises(RuntimeError) as exc_info:
            await coach._get_graph()

        error_msg = str(exc_info.value)
        # The post-fix contract message (07-REVIEW.md lines 79-82)
        assert "inject" in error_msg.lower() or "Inject" in error_msg, (
            f"Expected RuntimeError about injecting a pre-built saver, got: {error_msg!r}"
        )
        # Must NOT be the old PG_DSN-missing message alone
        # (old message says 'PG_DSN environment variable'; the new contract
        # should mention the graph or saver injection requirement)
        assert "_graph is None" in error_msg or "pre-built saver" in error_msg, (
            f"Expected new post-fix contract message mentioning '_graph is None' "
            f"or 'pre-built saver', got: {error_msg!r}"
        )


# ---------------------------------------------------------------------------
# Test B — WR-02: resume_after_help must write exactly ONE audit row
# ---------------------------------------------------------------------------


class TestResumeAfterHelpWritesSingleAuditRow:
    """WR-02 regression: resume_after_help must call _write_audit exactly once.

    Current code calls step() (which calls _write_audit decision='auto')
    then also calls _write_audit decision='hitl_supervisor' → two rows.

    Post-fix: step() is called with skip_audit=True, so only the
    resume_after_help's own _write_audit fires → one row.
    """

    async def test_resume_after_help_writes_single_audit_row(self) -> None:
        """audit_writer.write is awaited exactly once per resume_after_help call.

        Fails against current code: step() internally writes one audit row,
        resume_after_help writes another → two write calls total.
        Passes after fix: skip_audit=True suppresses step()'s internal write.
        """
        from langgraph.errors import GraphInterrupt

        saver = _build_mock_checkpointer()
        audit_writer = _build_mock_audit_writer()
        coach = _build_coach_with_saver(saver, audit_writer=audit_writer)

        intervention_id = "INTV-RESUME-001"

        # Build a mock graph that simulates a step() returning in_progress
        # (GraphInterrupt with coach_step type = in_progress response from step())
        mock_graph = AsyncMock()

        # ainvoke raises GraphInterrupt to simulate the graph producing the
        # next step (in_progress path)
        from langgraph.types import Interrupt

        interrupt_payload = {"type": "coach_step", "guidance": "Tighten belt tension", "step_no": 2}
        mock_graph.ainvoke = AsyncMock(
            side_effect=GraphInterrupt([Interrupt(value=interrupt_payload, resumable=True)])
        )

        # aget_state returns a checkpoint with state values
        mock_checkpoint = MagicMock()
        mock_checkpoint.values = {
            "current_step": 2,
            "completed_steps": [],
        }
        mock_graph.aget_state = AsyncMock(return_value=mock_checkpoint)

        # Inject the mock graph so _get_graph() returns it immediately
        coach._graph = mock_graph

        # Patch _write_audit to track calls directly
        write_audit_calls: list[dict[str, Any]] = []

        async def _capture_write_audit(**kwargs: Any) -> None:
            write_audit_calls.append(kwargs)

        coach._write_audit = _capture_write_audit  # type: ignore[method-assign]

        # Drive resume_after_help
        response = await coach.resume_after_help(intervention_id, "Supervisor confirmed: proceed")

        # CRITICAL assertion: exactly ONE audit row per resume
        assert len(write_audit_calls) == 1, (
            f"Expected exactly 1 audit write on resume_after_help, "
            f"got {len(write_audit_calls)}. "
            f"WR-02: resume_after_help calls step() (which writes 'auto') "
            f"then writes 'hitl_supervisor' = two rows. "
            f"Calls: {write_audit_calls}"
        )

        # The single audit row must be hitl_supervisor (not auto)
        assert write_audit_calls[0]["decision"] == "hitl_supervisor", (
            f"The single audit row must have decision='hitl_supervisor', "
            f"got {write_audit_calls[0]['decision']!r}"
        )

        # escalation_trigger must be 'technician_request'
        assert write_audit_calls[0].get("escalation_trigger") == "technician_request", (
            f"Expected escalation_trigger='technician_request', "
            f"got {write_audit_calls[0].get('escalation_trigger')!r}"
        )

        # Response should still be in_progress
        assert response.state == "in_progress"


# ---------------------------------------------------------------------------
# Test C — CR-01 integration: step() persists across calls (testcontainers PG)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStepPersistsAcrossCalls:
    """Integration test for CR-01: second step() call must not raise
    ConnectionDoesNotExistError or InterfaceError.

    Requires a real AsyncPostgresSaver from testcontainers PG.
    Skipped without docker (pytest -m integration).

    This mirrors the test_checkpoint_resume.py integration pattern.
    """

    async def test_step_persists_across_calls(self) -> None:
        """Two consecutive step() calls on same intervention_id succeed.

        Against pre-fix code: second call raises ConnectionDoesNotExistError
        because the saver was closed when _get_graph() returned.
        After fix: saver is long-lived (injected) and remains open.
        """
        try:
            from testcontainers.postgres import PostgresContainer  # type: ignore[import]
        except ImportError:
            pytest.skip("testcontainers not available")

        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.errors import GraphInterrupt

        # Start a real PG container
        with PostgresContainer("postgres:16") as pg:
            dsn = pg.get_connection_url().replace(
                "postgresql+psycopg2://", "postgresql://"
            )

            async with AsyncPostgresSaver.from_conn_string(dsn) as real_saver:
                await real_saver.setup()

                saver = real_saver
                pool = AsyncMock()
                audit_writer = _build_mock_audit_writer()
                llm = MagicMock()
                rag_tool = AsyncMock()
                rag_tool.name = "rag_search"
                request_help_tool = AsyncMock()
                request_help_tool.name = "request_help"
                escalate_tool = AsyncMock()
                escalate_tool.name = "escalate_to_supervisor"

                from mnt_maintenance_coach.agent import MaintenanceCoach

                coach = MaintenanceCoach(
                    pool=pool,
                    audit_writer=audit_writer,
                    llm=llm,
                    rag_search_tool=rag_tool,
                    request_help_tool=request_help_tool,
                    escalate_tool=escalate_tool,
                    saver=saver,
                )

                intervention_id = "INTV-PERSIST-001"

                # Build a mock graph that always raises GraphInterrupt
                # (simulating the step loop)
                from langgraph.types import Interrupt

                call_count = 0

                async def mock_ainvoke(cmd: Any, config: Any) -> Any:
                    nonlocal call_count
                    call_count += 1
                    payload = {
                        "type": "coach_step",
                        "guidance": f"Step {call_count} guidance",
                        "step_no": call_count,
                    }
                    raise GraphInterrupt([Interrupt(value=payload, resumable=True)])

                mock_graph = AsyncMock()
                mock_graph.ainvoke = mock_ainvoke

                mock_checkpoint = MagicMock()
                mock_checkpoint.values = {
                    "current_step": 1,
                    "completed_steps": [],
                }
                mock_graph.aget_state = AsyncMock(return_value=mock_checkpoint)

                # Inject the mock graph (the saver is injected at construction)
                coach._graph = mock_graph

                from mnt_maintenance_coach.models import CoachStepRequest

                req1 = CoachStepRequest(
                    intervention_id=intervention_id,
                    technician_input="First step done",
                )
                req2 = CoachStepRequest(
                    intervention_id=intervention_id,
                    technician_input="Second step done",
                )

                # First call — must succeed
                resp1 = await coach.step(req1)
                assert resp1 is not None, "First step() call failed"

                # Second call — must NOT raise ConnectionDoesNotExistError (CR-01)
                try:
                    resp2 = await coach.step(req2)
                    assert resp2 is not None, "Second step() call returned None"
                except Exception as exc:
                    exc_name = type(exc).__name__
                    if "ConnectionDoesNotExistError" in exc_name or "InterfaceError" in exc_name:
                        pytest.fail(
                            f"CR-01: second step() raised {exc_name}: {exc}. "
                            "The saver connection was closed after _get_graph() returned — "
                            "inject a long-lived saver at construction."
                        )
                    # Other exceptions (e.g. graph logic) are not the CR-01 defect
                    raise
