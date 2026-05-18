"""Wave 0 stub for tool registry (CORE-07) — Plan 04-05 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.runtime.tool_registry",
    reason="W0 stub — Plan 04-05 implements Tool registry + JSON-schema export",
)


def test_tool_registry_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-05 implements")
