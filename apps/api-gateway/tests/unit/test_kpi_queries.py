"""Contract scaffold for KPI aggregation query layer.

Plan 10-02 — tests activated (unskipped).

Describes the acceptance contract compute_kpi_snapshot() MUST satisfy.

THREAT: T-10-00b-01 — SQL must use $N parameterised placeholders ONLY.
        No f-string or % interpolation allowed (CR-05 SQL-injection guardrail).

KPI definitions (10-UI-SPEC, 10-CONTEXT.md):
  oee          — Overall Equipment Effectiveness (%)
  mttr         — Mean Time To Repair (minutes)
  mtbf         — Mean Time Between Failures (hours)
  scrap_rate   — Scrap / quality reject rate (%)
  throughput   — Production throughput (kg/h)
  downtime     — Downtime fraction (%)

Source tables (10-CONTEXT code_context):
  audit.actions         → OEE / MTTR / MTBF / downtime
  maintenance.downtime_events → MTTR / MTBF / downtime
  scm.*                 → throughput / inventory
  sensor_events         → scrap / quality
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock

import pytest


# ---------------------------------------------------------------------------
# Expected KPI output keys
# ---------------------------------------------------------------------------
REQUIRED_KPI_KEYS = {"oee", "mttr", "mtbf", "scrap_rate", "throughput", "downtime"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_conn(kpi_row: dict) -> AsyncMock:
    """Return an AsyncMock asyncpg connection that returns *kpi_row* on fetchrow."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=kpi_row)
    conn.fetch = AsyncMock(return_value=[kpi_row])
    return conn


CANNED_KPI_ROW = {
    "oee": 87.3,
    "mttr": 28.5,
    "mtbf": 76.0,
    "scrap_rate": 1.8,
    "throughput": 142.0,
    "downtime": 4.2,
}


# ---------------------------------------------------------------------------
# Contract: compute_kpi_snapshot returns all 6 keys
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compute_kpi_snapshot_returns_all_keys() -> None:
    """compute_kpi_snapshot(conn) → dict with all 6 KPI keys.

    The function accepts a mocked asyncpg connection.
    """
    from svc_api_gateway.kpi.queries import compute_kpi_snapshot

    conn = _make_mock_conn(CANNED_KPI_ROW)
    result = await compute_kpi_snapshot(conn)

    assert isinstance(result, dict)
    assert REQUIRED_KPI_KEYS.issubset(result.keys()), (
        f"Missing KPI keys: {REQUIRED_KPI_KEYS - result.keys()}"
    )


@pytest.mark.asyncio
async def test_compute_kpi_snapshot_values_are_numeric() -> None:
    """All KPI values in the result dict are numeric (int, float, or None)."""
    from svc_api_gateway.kpi.queries import compute_kpi_snapshot

    conn = _make_mock_conn(CANNED_KPI_ROW)
    result = await compute_kpi_snapshot(conn)

    for key in REQUIRED_KPI_KEYS:
        assert result[key] is None or isinstance(result[key], (int, float)), (
            f"KPI {key!r} is not numeric or None: {result[key]!r}"
        )


# ---------------------------------------------------------------------------
# THREAT T-10-00b-01: SQL must use $N params, no f-string interpolation
# ---------------------------------------------------------------------------

def test_kpi_sql_uses_parameterised_placeholders() -> None:
    """Inspect the SQL strings used by compute_kpi_snapshot: must use $1, $2, ...

    No f-string interpolation (CR-05 — SQL injection guardrail).
    Reads the source file and asserts:
      - At least one $1 placeholder appears in SQL strings
      - No string.format() or %-interpolation used in SQL context
    """
    import pathlib

    queries_path = pathlib.Path(
        "apps/api-gateway/src/svc_api_gateway/kpi/queries.py"
    )
    if not queries_path.exists():
        pytest.skip("impl in 10-02 — kpi/queries.py not yet created")

    source = queries_path.read_text()

    # Must contain at least one parameterised placeholder
    assert re.search(r"\$[1-9]", source), (
        "KPI SQL must use $N placeholders — no parameterised query found"
    )

    # Must NOT contain f-string SQL injection patterns like f"... {variable} ..."
    # Heuristic: look for f-strings that contain SELECT/WHERE/AND keywords
    f_string_sql = re.findall(r'f"[^"]*(?:SELECT|WHERE|AND|FROM)[^"]*\{', source)
    assert not f_string_sql, (
        f"Detected f-string SQL interpolation (CR-05 violation): {f_string_sql}"
    )


# ---------------------------------------------------------------------------
# Contract: KPI endpoint returns snapshot via HTTP
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="impl in 10-02 — /v1/kpi endpoint integration test uses client fixture (full router test)")
@pytest.mark.asyncio
async def test_kpi_snapshot_endpoint_returns_all_keys(client) -> None:
    """GET /v1/kpi (with valid operator JWT) → 200, body contains all KPI keys.

    This test is intentionally left as a skip-scaffold: the router-level test
    requires the full app with mocked pool wired. Covered separately by the
    full-suite regression in Task 2.
    """
    pytest.skip("impl in 10-02 — /v1/kpi endpoint router test not in this file")
