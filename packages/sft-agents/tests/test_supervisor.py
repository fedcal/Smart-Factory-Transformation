"""Wave 0 stub for LangGraph supervisor (CORE-02, CORE-03, CORE-07) — Plan 04-05 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.runtime.supervisor",
    reason="W0 stub — Plan 04-05 implements LangGraph StateGraph supervisor",
)


def test_supervisor_compile_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-05 implements")
