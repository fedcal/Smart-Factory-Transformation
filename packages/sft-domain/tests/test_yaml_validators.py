"""Cross-reference validators per i 3 YAML seed di Phase 6 (Pitfall §8).

- orders.yaml.compatible_families ⊆ asset_capacity.yaml.asset_family
- asset_capacity.yaml.asset_id ⊆ packages/sft-assets/src/sft_assets/registry.yaml.asset_id
- anomaly_baselines.yaml.asset_family ⊆ registry.asset_family

Carica i YAML direttamente via yaml.safe_load per evitare dipendenza di
sft-domain su sft-assets (sft-assets dichiara sft-domain ma non viceversa).
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from sft_domain.ops.anomaly import (
    AnomalyBaseline,
    invalidate_anomaly_baselines_cache,
    load_anomaly_baselines,
)
from sft_domain.ops.schedule import (
    AssetCapacity,
    OrderSpec,
    invalidate_capacity_cache,
    invalidate_orders_cache,
    load_asset_capacity,
    load_orders,
)


WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[3]
REGISTRY_YAML = WORKSPACE_ROOT / "packages" / "sft-assets" / "src" / "sft_assets" / "registry.yaml"


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    invalidate_orders_cache()
    invalidate_capacity_cache()
    invalidate_anomaly_baselines_cache()
    yield
    invalidate_orders_cache()
    invalidate_capacity_cache()
    invalidate_anomaly_baselines_cache()


def _registry_assets() -> list[dict]:
    raw = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    assert isinstance(raw, list), "registry.yaml deve essere lista a top-level"
    return raw


# ===========================================================================
# Loader smoke tests
# ===========================================================================


def test_orders_yaml_loads() -> None:
    orders = load_orders()
    assert len(orders) >= 15, f"Atteso >=15 orders, trovato {len(orders)}"
    for o in orders:
        assert isinstance(o, OrderSpec)


def test_asset_capacity_yaml_loads() -> None:
    capacity = load_asset_capacity()
    # 30 asset nel registry
    assert len(capacity) >= 25, f"Atteso >=25 asset capacity, trovato {len(capacity)}"
    for c in capacity.values():
        assert isinstance(c, AssetCapacity)


def test_anomaly_baselines_yaml_loads() -> None:
    baselines = load_anomaly_baselines()
    assert len(baselines) >= 5, f"Atteso >=5 anomaly baselines, trovato {len(baselines)}"
    for k, b in baselines.items():
        assert isinstance(k, tuple) and len(k) == 2
        assert isinstance(b, AnomalyBaseline)


# ===========================================================================
# Cross-references (Pitfall §8 — drift prevention)
# ===========================================================================


def test_orders_compatible_families_subset_of_capacity_families() -> None:
    """Ogni order.compatible_families deve avere almeno un asset corrispondente."""
    orders = load_orders()
    capacity = load_asset_capacity()
    available_families = {c.asset_family for c in capacity.values()}
    for o in orders:
        intersect = set(o.compatible_families) & available_families
        assert intersect, (
            f"Order {o.order_id} compatible_families={o.compatible_families} "
            f"non ha alcun match con asset_capacity.yaml families={available_families}"
        )


def test_asset_capacity_asset_id_subset_of_registry() -> None:
    """Ogni asset_capacity.yaml asset_id deve esistere in sft-assets registry."""
    capacity = load_asset_capacity()
    registry_ids = {a["asset_id"] for a in _registry_assets()}
    capacity_ids = set(capacity.keys())
    missing = capacity_ids - registry_ids
    assert not missing, (
        f"Asset IDs in asset_capacity.yaml non presenti in registry: {missing}"
    )


def test_anomaly_baselines_asset_family_in_registry() -> None:
    """Ogni anomaly_baselines.yaml asset_family deve corrispondere ad almeno un asset."""
    baselines = load_anomaly_baselines()
    registry_families = {a["asset_family"] for a in _registry_assets()}
    for (asset_family, sensor_id), _ in baselines.items():
        assert asset_family in registry_families, (
            f"anomaly_baselines.yaml asset_family='{asset_family}' (sensor={sensor_id}) "
            f"non presente in registry families={registry_families}"
        )


def test_asset_capacity_family_matches_registry_for_each_asset() -> None:
    """asset_capacity.yaml.asset_family deve combaciare con registry.asset_family per ogni asset_id."""
    capacity = load_asset_capacity()
    registry = {a["asset_id"]: a["asset_family"] for a in _registry_assets()}
    for asset_id, cap in capacity.items():
        expected = registry.get(asset_id)
        assert cap.asset_family == expected, (
            f"asset_capacity.yaml {asset_id}: asset_family={cap.asset_family!r} "
            f"!= registry={expected!r}"
        )


def test_safe_load_used_in_anomaly_loader() -> None:
    """Loader anomaly_baselines deve usare yaml.safe_load (T-V6-yaml-injection)."""
    from sft_domain.ops import anomaly as anom_mod

    src = pathlib.Path(anom_mod.__file__).read_text(encoding="utf-8")
    assert "yaml.safe_load" in src
    assert "yaml.load(" not in src.replace("yaml.safe_load(", "")


def test_safe_load_used_in_schedule_loader() -> None:
    """Loader orders + capacity deve usare yaml.safe_load."""
    from sft_domain.ops import schedule as sched_mod

    src = pathlib.Path(sched_mod.__file__).read_text(encoding="utf-8")
    assert "yaml.safe_load" in src
    assert "yaml.load(" not in src.replace("yaml.safe_load(", "")
