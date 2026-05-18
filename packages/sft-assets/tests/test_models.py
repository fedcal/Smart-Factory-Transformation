"""Test dei modelli Pydantic v2 per sft-assets.

Verifica:
    - Asset istanziato con dati validi
    - Asset frozen=True: mutazione solleva ValidationError
    - Asset.opcua_namespace validator: namespace senza prefisso urn:mantis: rifiutato
    - Asset extra="forbid": campi extra sollevano ValidationError
    - AssetFamily enum: esattamente 5 valori
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sft_assets._models import Asset, AssetFamily, Tag


class TestAssetInstantiation:
    """Test istanziazione Asset con dati validi."""

    def test_asset_valid_instantiation(self, sample_asset_dict: dict) -> None:
        """Asset deve istanziarsi correttamente con dati validi."""
        asset = Asset.model_validate(sample_asset_dict)
        assert asset.asset_id == "LOOM-01"
        assert asset.asset_family == AssetFamily.LOOM
        assert asset.line_id == "weaving-line-1"
        assert asset.opcua_namespace == "urn:mantis:loom:LOOM-01"
        assert len(asset.tags) == 2
        assert asset.status == "active"

    def test_asset_frozen_raises_on_mutation(self, sample_asset_dict: dict) -> None:
        """Asset frozen=True: mutazione deve sollevare ValidationError o TypeError."""
        asset = Asset.model_validate(sample_asset_dict)
        with pytest.raises((ValidationError, TypeError)):
            asset.asset_id = "X"  # type: ignore[misc]

    def test_asset_invalid_namespace_raises(self, sample_asset_dict: dict) -> None:
        """Asset con opcua_namespace senza prefisso urn:mantis: deve sollevare ValidationError."""
        bad_data = {**sample_asset_dict, "opcua_namespace": "http://example.com/loom"}
        with pytest.raises(ValidationError, match="urn:mantis:"):
            Asset.model_validate(bad_data)

    def test_asset_extra_field_raises(self, sample_asset_dict: dict) -> None:
        """Asset extra="forbid": campo extra deve sollevare ValidationError."""
        bad_data = {**sample_asset_dict, "extra_field": "x"}
        with pytest.raises(ValidationError):
            Asset.model_validate(bad_data)


class TestAssetFamilyEnum:
    """Test AssetFamily enum."""

    def test_asset_family_has_5_values(self) -> None:
        """AssetFamily deve avere esattamente 5 valori (D-21 + D-44)."""
        values = [e.value for e in AssetFamily]
        assert len(values) == 5, f"AssetFamily ha {len(values)} valori, attesi 5"

    def test_asset_family_contains_expected_values(self) -> None:
        """AssetFamily deve contenere loom, spinning, warping, dyeing, finishing."""
        expected = {"loom", "spinning", "warping", "dyeing", "finishing"}
        actual = {e.value for e in AssetFamily}
        assert actual == expected, f"AssetFamily contiene valori inattesi: {actual - expected}"


class TestTagModel:
    """Test del modello Tag."""

    def test_tag_valid_instantiation(self, sample_tag_dict: dict) -> None:
        """Tag deve istanziarsi correttamente con dati validi."""
        tag = Tag.model_validate(sample_tag_dict)
        assert tag.tag_id == "warp_tension"
        assert tag.unit == "N"
        assert tag.sample_rate_hz == 10.0

    def test_tag_extra_field_raises(self, sample_tag_dict: dict) -> None:
        """Tag extra="forbid": campo extra deve sollevare ValidationError."""
        bad_data = {**sample_tag_dict, "unknown_field": "x"}
        with pytest.raises(ValidationError):
            Tag.model_validate(bad_data)
