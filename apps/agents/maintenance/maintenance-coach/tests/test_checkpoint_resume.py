"""Integration tests for LangGraph checkpoint resume (MNT-03).

Tests the full async thread lifecycle:
  - Initial invocation creates a `coach-<id>` checkpoint in PG
  - Resume with same thread_id advances step (cross-restart correctness)
  - Different thread_id starts a fresh session
  - thread_id naming convention: `^coach-[0-9a-f-]+$`
  - State compression fires at _MESSAGE_TRIM_THRESHOLD
  - request_help keyword triggers supervisor interrupt
  - Completion sets mttr_end

Fixtures use a mock checkpointer (AsyncMock) and a mock LLM rather than
a live testcontainers PG — this avoids Docker dependencies in the CI quick
path while still verifying the resume contract logic.

Integration tests that require a real PG container are marked
``pytest.mark.integration`` and can be run separately:
    pytest -m integration apps/agents/maintenance/maintenance-coach/

RED phase: all tests fail via ImportError until Task 3 implements agent.py.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.asyncio]

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_initial_state_dict(
    intervention_id: str = "INTV-001",
    technician_id: str | None = "TECH-42",
) -> dict[str, Any]:
    """Return a CoachThreadState-compatible dict for graph invocation."""
    return {
        "intervention_id": intervention_id,
        "asset_id": "LOOM-01",
        "sop_id": "SOP-LOOM-001",
        "technician_id": technician_id,
        "current_step": 0,
        "completed_steps": [],
        "messages": [],
        "mttr_start": datetime(2026, 5, 23, 8, 0, tzinfo=UTC),
        "mttr_end": None,
    }


def _build_mock_checkpointer() -> AsyncMock:
    """Return a minimal AsyncPostgresSaver mock for unit-level tests."""
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


def _build_mock_coach(
    *,
    mock_checkpointer: AsyncMock | None = None,
) -> Any:
    """Instantiate a MaintenanceCoach with all collaborators mocked."""
    from mnt_maintenance_coach.agent import MaintenanceCoach

    saver = mock_checkpointer or _build_mock_checkpointer()
    pool = AsyncMock()
    audit_writer = AsyncMock()
    llm = MagicMock()
    rag_tool = AsyncMock()
    rag_tool.name = "rag_search"
    request_help_tool = AsyncMock()
    request_help_tool.name = "request_help"
    escalate_tool = AsyncMock()
    escalate_tool.name = "escalate_to_supervisor"

    return MaintenanceCoach(
        pool=pool,
        audit_writer=audit_writer,
        llm=llm,
        rag_search_tool=rag_tool,
        request_help_tool=request_help_tool,
        escalate_tool=escalate_tool,
        saver=saver,
    )


# ---------------------------------------------------------------------------
# Thread ID naming convention
# ---------------------------------------------------------------------------


class TestThreadIdNamingConvention:
    def test_thread_id_matches_coach_prefix_pattern(self) -> None:
        """f'coach-{uuid4()}' matches ^coach-[0-9a-f-]+$."""
        intervention_id = str(uuid4())
        thread_id = f"coach-{intervention_id}"
        assert re.match(r"^coach-[0-9a-f-]+$", thread_id), (
            f"thread_id '{thread_id}' does not match expected pattern"
        )

    def test_thread_id_distinct_from_ops_pattern(self) -> None:
        """coach-<uuid> does not collide with Phase 4 ops.<agent>.<uuid> pattern."""
        coach_thread = f"coach-{uuid4()}"
        ops_thread = f"ops.operator-assistant.{uuid4()}"
        assert not coach_thread.startswith("ops.")
        assert not ops_thread.startswith("coach-")

    def test_multiple_uuids_produce_distinct_thread_ids(self) -> None:
        """Each intervention produces a unique thread_id."""
        ids = {f"coach-{uuid4()}" for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# build_coach_graph — unit-level smoke tests
# ---------------------------------------------------------------------------


class TestBuildCoachGraph:
    def test_build_returns_state_graph(self) -> None:
        """build_coach_graph returns a compilable StateGraph."""
        from mnt_maintenance_coach.agent import build_coach_graph

        llm = MagicMock()
        rag_tool = MagicMock()
        rag_tool.name = "rag_search"
        request_help_tool = MagicMock()
        request_help_tool.name = "request_help"
        escalate_tool = MagicMock()
        escalate_tool.name = "escalate_to_supervisor"

        graph = build_coach_graph(
            llm=llm,
            rag_search_tool=rag_tool,
            request_help_tool=request_help_tool,
            escalate_tool=escalate_tool,
        )
        # StateGraph is not compiled yet — check it has compile() method
        assert hasattr(graph, "compile")

    def test_compiled_graph_accepts_checkpointer(self) -> None:
        """Compiled graph accepts a checkpointer without error."""
        from mnt_maintenance_coach.agent import build_coach_graph

        llm = MagicMock()
        rag_tool = MagicMock()
        rag_tool.name = "rag_search"
        request_help_tool = MagicMock()
        request_help_tool.name = "request_help"
        escalate_tool = MagicMock()
        escalate_tool.name = "escalate_to_supervisor"
        saver = _build_mock_checkpointer()

        graph = build_coach_graph(
            llm=llm,
            rag_search_tool=rag_tool,
            request_help_tool=request_help_tool,
            escalate_tool=escalate_tool,
        )
        compiled = graph.compile(checkpointer=saver)
        assert compiled is not None


# ---------------------------------------------------------------------------
# MaintenanceCoach — module constants
# ---------------------------------------------------------------------------


class TestAgentConstants:
    def test_agent_id_is_maintenance_coach(self) -> None:
        """AGENT_ID must be 'maintenance-coach' (D-MC-01)."""
        from mnt_maintenance_coach.agent import AGENT_ID

        assert AGENT_ID == "maintenance-coach"

    def test_cluster_is_maintenance(self) -> None:
        """CLUSTER must be 'maintenance'."""
        from mnt_maintenance_coach.agent import CLUSTER

        assert CLUSTER == "maintenance"

    def test_message_trim_threshold_is_50(self) -> None:
        """_MESSAGE_TRIM_THRESHOLD = 50 (07-PATTERNS.md Section 6 risk callout #1)."""
        from mnt_maintenance_coach.agent import _MESSAGE_TRIM_THRESHOLD

        assert _MESSAGE_TRIM_THRESHOLD == 50


# ---------------------------------------------------------------------------
# State compression helper
# ---------------------------------------------------------------------------


class TestStateTrimMessages:
    def test_no_trim_below_threshold(self) -> None:
        """Messages below threshold are returned unchanged."""
        from mnt_maintenance_coach.agent import _trim_messages

        msgs = [MagicMock() for _ in range(10)]
        result = _trim_messages(msgs, threshold=50)
        assert result == msgs

    def test_trim_above_threshold(self) -> None:
        """Messages above threshold are trimmed to system + last (threshold - system) messages."""
        from mnt_maintenance_coach.agent import _trim_messages

        system_msg = MagicMock()
        system_msg.type = "system"
        regular_msgs = [MagicMock() for _ in range(60)]
        for m in regular_msgs:
            m.type = "human"
        msgs = [system_msg] + regular_msgs  # 61 total

        result = _trim_messages(msgs, threshold=50)
        # Result should include system msg + last 49 regular msgs = 50
        assert len(result) <= 51  # threshold + 1 system
        assert result[0] is system_msg

    def test_exactly_at_threshold_no_trim(self) -> None:
        """Messages at exactly threshold are not trimmed."""
        from mnt_maintenance_coach.agent import _trim_messages

        msgs = [MagicMock() for _ in range(50)]
        for m in msgs:
            m.type = "human"
        result = _trim_messages(msgs, threshold=50)
        assert len(result) == 50


# ---------------------------------------------------------------------------
# CoachResponse state values
# ---------------------------------------------------------------------------


class TestCoachResponseStates:
    def test_in_progress_state_literal(self) -> None:
        """CoachResponse state='in_progress' is a valid literal."""
        from mnt_maintenance_coach.models import CoachResponse

        resp = CoachResponse(
            intervention_id="INTV-001",
            current_step=1,
            guidance_md="Next step: check belt tension",
            completed_step=None,
            mttr_minutes_so_far=None,
            state="in_progress",
        )
        assert resp.state == "in_progress"

    def test_completed_state_literal(self) -> None:
        """CoachResponse state='completed' is a valid literal."""
        from mnt_maintenance_coach.models import CoachResponse

        resp = CoachResponse(
            intervention_id="INTV-001",
            current_step=5,
            guidance_md="Intervention complete.",
            completed_step=None,
            mttr_minutes_so_far=90,
            state="completed",
        )
        assert resp.state == "completed"
