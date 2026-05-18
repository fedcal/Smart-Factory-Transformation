"""Wave 0 stub for approval-rate governor (HITL-07, HITL-08) — Plan 04-06 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.hitl.governor",
    reason="W0 stub — Plan 04-06 implements 1h sliding-window approval-rate governor",
)


def test_governor_threshold_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-06 implements")
