"""Wave 0 stub for plan 07-09 — implementation lands in 07-09.

Tests for OEE computation:
  - ``test_availability`` — OEE.A on synthetic downtime window (MNT-04).
  - ``test_quality_cross_cluster`` — OEE.Q cross-cluster audit query +
    fallback path (MNT-04 / V8 data integrity).

Real assertions land with plan 07-09 (downtime-analyzer).
"""

from __future__ import annotations

import pytest


def test_placeholder() -> None:
    pytest.skip("Wave 0 stub — implemented in plan 07-09.")
