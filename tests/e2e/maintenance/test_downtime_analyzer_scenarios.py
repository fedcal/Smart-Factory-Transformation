"""Wave 0 stub — full e2e implemented in plan 07-12.

E2E scenarios for DowntimeAnalyzer (MNT-04) — happy/degraded/failure with
deterministic SQL aggregation (no LLM mock). Real assertions land with
plan 07-12 (maintenance e2e scenarios).
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
@pytest.mark.parametrize("scenario", ["happy", "degraded", "failure"])
def test_downtime_analyzer_scenario(scenario: str) -> None:
    pytest.skip("Wave 0 stub — plan 07-12")
