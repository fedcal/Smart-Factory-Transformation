"""Validation tests for Grafana provisioned dashboard JSON files.

Tests:
    - All *.json in infra/grafana/dashboards/ are valid JSON.
    - Each dashboard has required top-level fields: title, panels, schemaVersion.
    - Each dashboard references only provisioned datasource UIDs (prometheus, tempo).
    - Cost dashboard contains 'cost' (OBS-07).
    - Agent KPI dashboard contains p95 latency query (OBS-04).
    - Factory KPI dashboard contains 'OEE' (OBS-04).

Threat model: T-11-04-02 — dashboard JSON schema drift mitigated by these assertions.

Run:
    uv run pytest infra/grafana/tests/test_dashboards_valid.py -x -q
"""

from __future__ import annotations

import json
import pathlib

import pytest

DASHBOARDS_DIR = pathlib.Path(__file__).parents[1] / "dashboards"
PROVISIONED_DATASOURCE_UIDS = frozenset({"prometheus", "tempo"})

# Grafana built-in datasource UIDs that are always valid regardless of provisioning.
GRAFANA_BUILTIN_UIDS = frozenset({"-- Grafana --", "-- Mixed --"})


def _load_dashboard(name: str) -> dict:
    """Load and parse a dashboard JSON file by name."""
    path = DASHBOARDS_DIR / name
    assert path.exists(), f"Dashboard file missing: {path}"
    with open(path) as fh:
        return json.load(fh)


def _all_dashboard_files() -> list[pathlib.Path]:
    """Return all *.json files in the dashboards directory."""
    return sorted(DASHBOARDS_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Parametrized: all dashboard files
# ---------------------------------------------------------------------------


@pytest.fixture(params=_all_dashboard_files(), ids=lambda p: p.name)
def dashboard_path(request: pytest.FixtureRequest) -> pathlib.Path:
    """Fixture yielding each dashboard JSON path."""
    return request.param  # type: ignore[return-value]


def test_dashboard_is_valid_json(dashboard_path: pathlib.Path) -> None:
    """Each dashboard file must be valid JSON."""
    with open(dashboard_path) as fh:
        data = json.load(fh)
    assert isinstance(data, dict), f"{dashboard_path.name}: root must be a JSON object"


def test_dashboard_has_required_fields(dashboard_path: pathlib.Path) -> None:
    """Each dashboard must have title, panels, and schemaVersion."""
    with open(dashboard_path) as fh:
        data = json.load(fh)

    assert "title" in data, f"{dashboard_path.name}: missing 'title'"
    assert data["title"], f"{dashboard_path.name}: 'title' must be non-empty"

    assert "panels" in data, f"{dashboard_path.name}: missing 'panels'"
    assert isinstance(data["panels"], list), f"{dashboard_path.name}: 'panels' must be a list"
    assert len(data["panels"]) > 0, f"{dashboard_path.name}: 'panels' must not be empty"

    assert "schemaVersion" in data, f"{dashboard_path.name}: missing 'schemaVersion'"
    assert isinstance(data["schemaVersion"], int), f"{dashboard_path.name}: 'schemaVersion' must be an integer"
    assert data["schemaVersion"] >= 36, (
        f"{dashboard_path.name}: schemaVersion {data['schemaVersion']} < 36 (Grafana v9+ minimum)"
    )


def test_dashboard_datasources_are_provisioned(dashboard_path: pathlib.Path) -> None:
    """Every panel target must reference a provisioned datasource UID.

    Allowed UIDs: prometheus, tempo (provisioned in datasources.yaml),
    plus Grafana built-in UIDs (-- Grafana --, -- Mixed --).
    Row panels have no datasource — skip them.
    """
    with open(dashboard_path) as fh:
        data = json.load(fh)

    allowed_uids = PROVISIONED_DATASOURCE_UIDS | GRAFANA_BUILTIN_UIDS

    def _check_datasource(panel: dict, panel_id: object) -> None:
        panel_type = panel.get("type", "")
        if panel_type == "row":
            return  # Row panels have no datasource

        ds = panel.get("datasource")
        if ds is None:
            return  # Panel inherits dashboard datasource — acceptable

        if isinstance(ds, dict):
            uid = ds.get("uid")
            if uid and uid not in allowed_uids:
                raise AssertionError(
                    f"{dashboard_path.name} panel id={panel_id}: "
                    f"datasource uid '{uid}' not in provisioned set {PROVISIONED_DATASOURCE_UIDS}"
                )
        elif isinstance(ds, str):
            # Legacy string form — check against allowed set
            if ds and ds not in allowed_uids:
                raise AssertionError(
                    f"{dashboard_path.name} panel id={panel_id}: "
                    f"datasource '{ds}' not in provisioned set {PROVISIONED_DATASOURCE_UIDS}"
                )

    for panel in data.get("panels", []):
        _check_datasource(panel, panel.get("id", "?"))


# ---------------------------------------------------------------------------
# Specific dashboard content assertions
# ---------------------------------------------------------------------------


def test_agent_kpis_has_p95_latency() -> None:
    """agent-kpis.json must contain a p95 latency query (OBS-04/07)."""
    data = _load_dashboard("agent-kpis.json")
    dashboard_str = json.dumps(data)
    has_p95 = "0.95" in dashboard_str or "p95" in dashboard_str
    assert has_p95, (
        "agent-kpis.json: missing p95 latency panel. "
        "Expected histogram_quantile(0.95, ...) query."
    )


def test_agent_kpis_has_p50_and_p99_latency() -> None:
    """agent-kpis.json must contain p50 and p99 latency queries (OBS-07)."""
    data = _load_dashboard("agent-kpis.json")
    dashboard_str = json.dumps(data)
    assert "0.50" in dashboard_str or "p50" in dashboard_str, (
        "agent-kpis.json: missing p50 latency panel."
    )
    assert "0.99" in dashboard_str or "p99" in dashboard_str, (
        "agent-kpis.json: missing p99 latency panel."
    )


def test_factory_kpis_has_oee() -> None:
    """factory-kpis.json must contain OEE metric reference (OBS-04)."""
    data = _load_dashboard("factory-kpis.json")
    assert "OEE" in json.dumps(data), (
        "factory-kpis.json: missing OEE metric. Expected OEE gauge or timeseries panel."
    )


def test_factory_kpis_has_mttr_and_mtbf() -> None:
    """factory-kpis.json must contain MTTR and MTBF panels (OBS-04)."""
    data = _load_dashboard("factory-kpis.json")
    dashboard_str = json.dumps(data)
    assert "MTTR" in dashboard_str, "factory-kpis.json: missing MTTR panel."
    assert "MTBF" in dashboard_str, "factory-kpis.json: missing MTBF panel."


def test_factory_kpis_has_scrap() -> None:
    """factory-kpis.json must contain scrap rate panel (OBS-04)."""
    data = _load_dashboard("factory-kpis.json")
    dashboard_str = json.dumps(data)
    assert "scrap" in dashboard_str.lower() or "Scrap" in dashboard_str, (
        "factory-kpis.json: missing scrap rate panel."
    )


def test_cost_dashboard_has_cost() -> None:
    """cost-dashboard.json must contain cost metric reference (OBS-07)."""
    data = _load_dashboard("cost-dashboard.json")
    assert "cost" in json.dumps(data).lower(), (
        "cost-dashboard.json: missing cost metric. "
        "Expected cost_usd_simulated or cost in panel title/query."
    )


def test_cost_dashboard_has_token_panels() -> None:
    """cost-dashboard.json must contain token consumption panels (OBS-07)."""
    data = _load_dashboard("cost-dashboard.json")
    dashboard_str = json.dumps(data)
    assert "token" in dashboard_str.lower(), (
        "cost-dashboard.json: missing token consumption panel."
    )


def test_cost_dashboard_has_latency_percentiles() -> None:
    """cost-dashboard.json must contain p50/p95/p99 latency panels (OBS-07)."""
    data = _load_dashboard("cost-dashboard.json")
    dashboard_str = json.dumps(data)
    assert "0.95" in dashboard_str or "p95" in dashboard_str, (
        "cost-dashboard.json: missing p95 latency query."
    )
    assert "0.50" in dashboard_str or "p50" in dashboard_str, (
        "cost-dashboard.json: missing p50 latency query."
    )
    assert "0.99" in dashboard_str or "p99" in dashboard_str, (
        "cost-dashboard.json: missing p99 latency query."
    )


def test_dashboards_directory_has_expected_files() -> None:
    """The dashboards directory must contain the three expected dashboard files."""
    expected = {"agent-kpis.json", "factory-kpis.json", "cost-dashboard.json"}
    actual = {p.name for p in DASHBOARDS_DIR.glob("*.json")}
    missing = expected - actual
    assert not missing, f"Missing expected dashboard files: {missing}"


def test_all_dashboards_reference_prometheus_datasource() -> None:
    """All three dashboards must reference the Prometheus datasource (OBS-04)."""
    for name in ("agent-kpis.json", "factory-kpis.json", "cost-dashboard.json"):
        data = _load_dashboard(name)
        dashboard_str = json.dumps(data)
        assert "prometheus" in dashboard_str, (
            f"{name}: does not reference 'prometheus' datasource uid."
        )
