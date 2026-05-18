"""Wave 0 stub for budget/quota middleware (HITL-09, HITL-10, CORE-09) — Plan 04-06 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.hitl.budget",
    reason="W0 stub — Plan 04-06 implements BudgetTracker middleware",
)


def test_budget_middleware_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-06 implements")
