"""Wave 0 stub for replay tool (CORE-10) — Plan 04-08 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.replay",
    reason="W0 stub — Plan 04-08 implements deterministic replay from checkpoint + audit log",
)


def test_replay_determinism_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-08 implements")
