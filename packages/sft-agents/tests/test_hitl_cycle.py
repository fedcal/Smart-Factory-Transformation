"""Wave 0 stub for HITL interrupt/resume cycle (HITL-01, HITL-02, HITL-06) — Plan 04-06 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.hitl.interrupt",
    reason="W0 stub — Plan 04-06 implements interrupt() / Command(resume=) middleware",
)


def test_hitl_interrupt_resume_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-06 implements")
