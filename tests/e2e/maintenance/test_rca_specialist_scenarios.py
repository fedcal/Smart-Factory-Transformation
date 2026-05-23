"""RCASpecialist (MNT-02) — happy / degraded / failure E2E scenarios.

Plan 07-12 / success criterion #5 (Phase 7).

Happy:
    5-Why analysis on broken_end downtime with valid citations from SOP corpus.
    LLM mock: 4 rounds — rag_search → traverse_graph → valid RCAChain JSON
    → escalate_to_supervisor.
    Expected: status_code=202, decision=hitl_supervisor, hitl_status=supervisor_pending,
    validation_exhausted=false.

Degraded:
    1st LLM call returns orphan citation (source_uri not in pg_documents)
    → RCAChainValidator raises OrphanCitationError → retry corrective prompt
    → 2nd call succeeds. Expected: validation_exhausted=false, retry_count >= 1.

Failure:
    3 consecutive LLM calls return invalid output (invalid JSON, orphan citations,
    incomplete chain). Retries exhausted. Escalation carries best_attempt +
    validation_exhausted=true.

Mock LLM: ordered-fallback JSONL replay via MockReplayChatModel (06-03).
No real testcontainer needed — all infrastructure is mocked.
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

_SCENARIOS = [
    "rca-specialist/happy",
    "rca-specialist/degraded",
    "rca-specialist/failure",
]


@pytest.mark.timeout(120)
@pytest.mark.parametrize("mnt_scenario", _SCENARIOS, indirect=True)
async def test_rca_specialist_scenario(
    mnt_scenario: dict[str, Any],
    mock_llm_backend: dict[str, Any],
    seed_testcontainers: dict[str, Any],
    api_gateway_client: Any,
) -> None:
    """Drive RCASpecialist end-to-end against scenario YAML spec."""
    assert mnt_scenario, "scenario YAML must not be empty"
    spec = mnt_scenario
    expected = spec["expected"]
    body = spec["input"]["body"]
    endpoint = spec["input"]["endpoint"].replace("POST ", "")

    response = await api_gateway_client.post(endpoint, json=body)

    assert response.status_code == expected["status_code"], (
        f"Expected status {expected['status_code']}, got {response.status_code}: {response.json()}"
    )

    data = response.json()

    # --- Decision must always be hitl_supervisor (MNT-02 success criterion #2) ---
    assert data.get("decision") == "hitl_supervisor", (
        f"RCASpecialist must always escalate to hitl_supervisor; got {data.get('decision')!r}"
    )

    # --- HITL status ---
    expected_hitl_status = expected.get("hitl_status")
    if expected_hitl_status:
        actual_hitl = data.get("hitl_status")
        assert actual_hitl == expected_hitl_status, (
            f"Expected hitl_status={expected_hitl_status!r}, got {actual_hitl!r}"
        )

    # --- validation_exhausted ---
    expected_exhausted = expected.get("validation_exhausted", False)
    actual_exhausted = data.get("validation_exhausted", False)
    assert actual_exhausted == expected_exhausted, (
        f"Expected validation_exhausted={expected_exhausted}, got {actual_exhausted}"
    )

    # --- best_attempt present (failure scenario) ---
    if expected.get("best_attempt_present"):
        best_attempt = data.get("best_attempt")
        assert best_attempt is not None, (
            "Expected best_attempt to be present in failure scenario response"
        )

    # --- Retry count for degraded scenario ---
    if expected.get("retry_count_min"):
        retry_count = data.get("retry_count", 0)
        assert retry_count >= expected["retry_count_min"], (
            f"Expected retry_count >= {expected['retry_count_min']}, got {retry_count}"
        )

    # --- Audit rows ---
    audit_writer = seed_testcontainers["audit_writer"]
    audit_rows_written = len(audit_writer.writes)
    audit_rows_min = expected.get("audit_rows_min", 0)
    assert audit_rows_written >= audit_rows_min, (
        f"Expected >= {audit_rows_min} audit rows written, got {audit_rows_written}"
    )

    # --- Audit row decision for RCA ---
    if audit_writer.writes:
        for write in audit_writer.writes:
            action_type = getattr(write, "action_type", None)
            if action_type == "RCA_CHAIN":
                actual_decision = getattr(write, "decision", None)
                assert actual_decision == "hitl_supervisor", (
                    f"RCA_CHAIN audit row must have decision=hitl_supervisor, got {actual_decision!r}"
                )

    # --- action_type check ---
    if expected.get("action_type"):
        actual_at = data.get("action_type")
        assert actual_at == expected["action_type"], (
            f"Expected action_type={expected['action_type']!r}, got {actual_at!r}"
        )
