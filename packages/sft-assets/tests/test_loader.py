"""Test del loader sft-assets con lru_cache.

Verifica:
    - load_assets() ritorna tuple[Asset, ...] non vuota
    - Due chiamate a load_assets() restituiscono lo stesso oggetto (lru_cache)
    - load_assets_dict() ha key uguali a asset.asset_id
    - load_tag_dict() solleva AssertionError con tag_id divergenti tra asset
    - invalidate_cache() svuota la cache e ricarica dopo modifica
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest
import yaml

from sft_assets._loader import invalidate_cache, load_assets, load_assets_dict, load_tag_dict
from sft_assets._models import Asset


class TestLoadAssetsCache:
    """Test della cache LRU di load_assets."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_load_assets_returns_non_empty_tuple(self) -> None:
        """load_assets() deve ritornare una tuple non vuota."""
        assets = load_assets()
        assert isinstance(assets, tuple), "load_assets() deve ritornare una tuple"
        assert len(assets) > 0, "load_assets() non deve ritornare una tuple vuota"

    def test_load_assets_returns_same_object_on_second_call(self) -> None:
        """Due chiamate a load_assets() devono ritornare lo stesso oggetto (lru_cache)."""
        assets1 = load_assets()
        assets2 = load_assets()
        assert assets1 is assets2, "load_assets() deve ritornare lo stesso oggetto (lru_cache)"

    def test_load_assets_returns_asset_instances(self) -> None:
        """load_assets() deve ritornare tuple di Asset."""
        assets = load_assets()
        for asset in assets:
            assert isinstance(asset, Asset)


class TestLoadAssetsDictAndTagDict:
    """Test di load_assets_dict e load_tag_dict."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_load_assets_dict_keys_match_asset_ids(self) -> None:
        """load_assets_dict() deve avere key uguali a asset.asset_id."""
        assets_dict = load_assets_dict()
        assets = load_assets()
        expected_ids = {a.asset_id for a in assets}
        assert set(assets_dict.keys()) == expected_ids

    def test_load_tag_dict_consistency_check_fails_on_diverging_tags(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_tag_dict() deve sollevare AssertionError se stesso tag_id ha definizioni divergenti."""
        # Due asset con stesso tag_id ma unit diversa
        registry_data = [
            {
                "asset_id": "LOOM-01",
                "asset_family": "loom",
                "line_id": "weaving-line-1",
                "opcua_namespace": "urn:mantis:loom:LOOM-01",
                "tags": [
                    {
                        "tag_id": "warp_tension",
                        "unit": "N",
                        "sample_rate_hz": 10.0,
                        "semantic_type": "tension",
                    }
                ],
                "status": "active",
            },
            {
                "asset_id": "LOOM-02",
                "asset_family": "loom",
                "line_id": "weaving-line-1",
                "opcua_namespace": "urn:mantis:loom:LOOM-02",
                "tags": [
                    {
                        "tag_id": "warp_tension",
                        "unit": "kN",  # divergente da LOOM-01 (N vs kN)
                        "sample_rate_hz": 10.0,
                        "semantic_type": "tension",
                    }
                ],
                "status": "active",
            },
        ]
        registry_file = tmp_path / "registry.yaml"
        registry_file.write_text(yaml.dump(registry_data), encoding="utf-8")

        import sft_assets._loader as loader_module
        monkeypatch.setattr(loader_module, "_REGISTRY_PATH", registry_file)
        invalidate_cache()

        with pytest.raises(AssertionError):
            load_tag_dict()


class TestInvalidateCache:
    """Test di invalidate_cache."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_invalidate_cache_clears_lru(self) -> None:
        """invalidate_cache() deve svuotare la cache del loader."""
        # Carica per popolare la cache
        load_assets()
        info_before = load_assets.cache_info()
        assert info_before.currsize > 0, "Cache deve essere popolata dopo load_assets()"

        invalidate_cache()
        info_after = load_assets.cache_info()
        assert info_after.currsize == 0, "Cache deve essere vuota dopo invalidate_cache()"

    def test_reload_after_invalidate_from_tmp_path(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dopo invalidate_cache(), il loader deve ricaricare dal path modificato."""
        registry_data = [
            {
                "asset_id": "SPIN-01",
                "asset_family": "spinning",
                "line_id": "spinning-line-1",
                "opcua_namespace": "urn:mantis:spinning:SPIN-01",
                "tags": [
                    {
                        "tag_id": "spindle_speed",
                        "unit": "rpm",
                        "sample_rate_hz": 5.0,
                        "semantic_type": "speed",
                    }
                ],
                "status": "active",
            }
        ]
        registry_file = tmp_path / "registry.yaml"
        registry_file.write_text(yaml.dump(registry_data), encoding="utf-8")

        import sft_assets._loader as loader_module
        monkeypatch.setattr(loader_module, "_REGISTRY_PATH", registry_file)
        invalidate_cache()

        assets = load_assets()
        assert len(assets) == 1
        assert assets[0].asset_id == "SPIN-01"
