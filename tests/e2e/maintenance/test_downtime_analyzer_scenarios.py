"""DowntimeAnalyzer (MNT-04) — happy / degraded / failure E2E scenarios.

Plan 07-12 / success criterion #5 (Phase 7).

Happy:
    10 DowntimeEvents over 1-hour window for LOOM-01 with reason_codes from
    failure_modes.yaml taxonomy (WEAVING-MP-002 × 4, WEAVING-BE-001 × 3,
    WEAVING-SF-003 × 3). 1 QUALITY_VERDICT audit row for the same window.
    Expected: status_code=200, quality_source="audit",
    pareto_top=["WEAVING-MP-002", "WEAVING-BE-001", "WEAVING-SF-003"],
    oee_bounds=[0.7, 1.0].

Degraded:
    Same downtime events, NO QUALITY_VERDICT rows (cross-cluster gap), but
    production_state_overrides.LOOM-01: { good_meters: 940, target_meters: 1000 }.
    Expected: quality_source="simfallback", report still produced.

Failure:
    Invalid ReportRequest: window_end < window_start.
    Expected: status_code=422 from api-gateway.

Deterministic SQL aggregation — NO mock LLM needed (DA is LLM-free per
07-VALIDATION.md L91-95). All infrastructure is mocked.
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

_SCENARIOS = [
    "downtime-analyzer/happy",
    "downtime-analyzer/degraded",
    "downtime-analyzer/failure",
]


@pytest.mark.timeout(120)
@pytest.mark.parametrize("mnt_scenario", _SCENARIOS, indirect=True)
async def test_downtime_analyzer_scenario(
    mnt_scenario: dict[str, Any],
    mock_llm_backend: dict[str, Any],
    seed_testcontainers: dict[str, Any],
    api_gateway_client: Any,
) -> None:
    """Drive DowntimeAnalyzer end-to-end against scenario YAML spec."""
    assert mnt_scenario, "scenario YAML must not be empty"
    spec = mnt_scenario
    expected = spec["expected"]
    body = spec["input"]["body"]
    endpoint = spec["input"]["endpoint"].replace("POST ", "")

    response = await api_gateway_client.post(endpoint, json=body)

    assert response.status_code == expected["status_code"], (
        f"Expected status {expected['status_code']}, got {response.status_code}: {response.json()}"
    )

    if expected["status_code"] == 200:
        data = response.json()

        # --- Decision must be auto (DA is deterministic SQL, no LLM) ---
        assert data.get("decision") == "auto", (
            f"DowntimeAnalyzer expected decision=auto (deterministic), got {data.get('decision')!r}"
        )

        # --- action_type ---
        if expected.get("action_type"):
            assert data.get("action_type") == expected["action_type"], (
                f"Expected action_type={expected['action_type']!r}, got {data.get('action_type')!r}"
            )

        # --- OEE bounds ---
        oee_bounds = expected.get("oee_bounds")
        if oee_bounds:
            oee_low, oee_high = oee_bounds
            oee_value = data.get("oee")
            assert oee_value is not None, "Expected OEE value in response"
            assert oee_low <= oee_value <= oee_high, (
                f"Expected OEE in [{oee_low}, {oee_high}], got {oee_value}"
            )

        # --- quality_source ---
        expected_quality_source = expected.get("quality_source")
        if expected_quality_source:
            actual_quality_source = data.get("quality_source")
            assert actual_quality_source == expected_quality_source, (
                f"Expected quality_source={expected_quality_source!r}, "
                f"got {actual_quality_source!r}"
            )

        # --- Pareto top-N reason_codes ---
        expected_pareto = expected.get("pareto_top", [])
        if expected_pareto:
            actual_pareto = data.get("pareto_top", [])
            # Check the top entries match expected order (at least the first entries)
            top_n = min(len(expected_pareto), len(actual_pareto))
            if top_n > 0:
                for idx, expected_rc in enumerate(expected_pareto[:top_n]):
                    if idx < len(actual_pareto):
                        assert actual_pareto[idx] == expected_rc, (
                            f"Pareto position {idx}: expected {expected_rc!r}, "
                            f"got {actual_pareto[idx]!r}. Full pareto: {actual_pareto}"
                        )

        # --- Audit rows (OEE_REPORT row must be written) ---
        audit_writer = seed_testcontainers["audit_writer"]
        audit_rows_min = expected.get("audit_rows_min", 0)
        assert len(audit_writer.writes) >= audit_rows_min, (
            f"Expected >= {audit_rows_min} audit rows, got {len(audit_writer.writes)}"
        )

        if audit_rows_min > 0 and audit_writer.writes:
            oee_report_writes = [
                w for w in audit_writer.writes
                if getattr(w, "action_type", None) == "OEE_REPORT"
            ]
            assert len(oee_report_writes) >= 1, (
                "Expected at least 1 OEE_REPORT audit row"
            )

    elif expected["status_code"] == 422:
        # Failure scenario: 422 validation error
        data = response.json()
        # Standard FastAPI validation error format
        assert "detail" in data or "error" in data, (
            f"Expected error detail in 422 response, got: {data}"
        )
        # No audit rows should be written for validation failures
        audit_writer = seed_testcontainers["audit_writer"]
        assert len(audit_writer.writes) == 0, (
            f"Expected 0 audit rows for 422 failure, got {len(audit_writer.writes)}"
        )
