"""Wave 0 stub — full e2e implemented in plan 07-12.

E2E scenarios for MaintenanceCoach (MNT-03) — happy/degraded/failure with
mock LLM JSONL traces + checkpoint replay. Real assertions land with plan
07-12 (maintenance e2e scenarios).

NOTE: 07-12 adds a 4th ``auto_open`` scenario at Wave 5 (per 07-PLAN
inventory); Wave 0 covers only the canonical 3.
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
@pytest.mark.parametrize("scenario", ["happy", "degraded", "failure"])
def test_maintenance_coach_scenario(scenario: str) -> None:
    pytest.skip("Wave 0 stub — plan 07-12")
