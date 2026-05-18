"""Wave 0 stub for 4-tier escalation chain (HITL-03..05) — Plan 04-06 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.hitl.escalation",
    reason="W0 stub — Plan 04-06 implements EscalationSupervisor + Safety Interlock",
)


def test_escalation_chain_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-06 implements")
