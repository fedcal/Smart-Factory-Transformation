"""Wave 0 stub — full e2e implemented in plan 06-12.

E2E scenarios for AnomalyDetector (OPS-04) — happy/degraded/failure.
Real assertions land with plan 06-12 (e2e-scenarios).
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
@pytest.mark.parametrize("scenario", ["happy", "degraded", "failure"])
def test_anomaly_detector_scenario(scenario: str) -> None:
    pytest.skip("Wave 0 stub — plan 06-12")
