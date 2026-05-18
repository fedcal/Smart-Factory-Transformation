"""Wave 0 stub for migration idempotency (CORE-04) — Plan 04-02 implements."""

from __future__ import annotations

import pytest

# Target lives in Plan 04-02 (migrations runner). importorskip prevents collection-time
# ImportError until the module exists.
pytest.importorskip(
    "sft_agents.migrations",
    reason="W0 stub — Plan 04-02 implements migration runner / idempotency check",
)


def test_migrations_idempotent_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-02 implements")
