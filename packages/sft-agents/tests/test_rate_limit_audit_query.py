"""Wave 0 stub for HITL-10 audit query primitive — Plan 04-06 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.audit.rate_limit",
    reason="W0 stub — Plan 04-06 implements per-persona alarm rate query primitive",
)


def test_rate_limit_audit_query_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-06 implements")
