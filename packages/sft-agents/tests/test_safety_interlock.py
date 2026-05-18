"""Wave 0 stub for Safety Interlock middleware (HITL-04) — Plan 04-06 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.hitl.safety_interlock",
    reason="W0 stub — Plan 04-06 implements Safety Interlock NATS-command whitelist",
)


def test_safety_interlock_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-06 implements")
