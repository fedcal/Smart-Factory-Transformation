"""Wave 0 stub for LangGraph recursion_limit handling (CORE-07) — Plan 04-05 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.runtime.supervisor",
    reason="W0 stub — Plan 04-05 implements recursion_limit → GRAPH_RECURSION_REVIEW HITL escalation",
)


def test_recursion_limit_escalates_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-05 implements")
