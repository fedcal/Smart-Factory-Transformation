"""Test di validazione schema JSON Draft 2020-12 per fault profiles (Test 10-13).

Verifica:
    test_schema_self_valid           — fault-profile.schema.json e' un JSON Schema valido
    test_all_profiles_schema_valid   — tutti e 5 i YAML validano contro lo schema
    test_invalid_nan_probability_rejected — nan_probability > 1 solleva ValidationError
    test_tags_match_registry         — affected_tags e baseline keys sono in load_tag_dict()
"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from sft_assets import load_tag_dict
from sim_textile.models import FaultProfile
from sim_textile.profile_loader import invalidate_cache

# Percorso schemas/ relativo a questo file di test
_SCHEMAS_DIR = pathlib.Path(__file__).parent.parent / "schemas"
_PROFILES_DIR = pathlib.Path(__file__).parent.parent / "profiles"
_FAMILIES = ("loom", "spinning", "warping", "dyeing", "finishing")


def _load_schema(filename: str) -> dict:
    """Carica uno schema JSON dalla directory schemas/."""
    path = _SCHEMAS_DIR / filename
    assert path.exists(), f"Schema non trovato: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


class TestSchemaMetaValidation:
    """Test 10: fault-profile.schema.json e' un JSON Schema Draft 2020-12 valido."""

    def test_schema_self_valid(self) -> None:
        """fault-profile.schema.json deve essere un JSON Schema Draft 2020-12 valido (Test 10)."""
        schema = _load_schema("fault-profile.schema.json")
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", (
            "fault-profile.schema.json deve dichiarare $schema Draft 2020-12"
        )
        # check_schema() ritorna None su successo, solleva SchemaError su errore
        result = Draft202012Validator.check_schema(schema)
        assert result is None


class TestAllProfilesSchemaValid:
    """Test 11: tutti i 5 YAML validano contro fault-profile.schema.json (0 errori)."""

    def test_all_profiles_schema_valid(self) -> None:
        """Tutti e 5 i YAML fault profiles validano contro lo schema (Test 11)."""
        schema = _load_schema("fault-profile.schema.json")
        validator = Draft202012Validator(schema)

        for family in _FAMILIES:
            yaml_path = _PROFILES_DIR / f"{family}.yaml"
            assert yaml_path.exists(), f"Profile mancante: {yaml_path}"

            with yaml_path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh)  # SEMPRE safe_load (Pattern S-2)

            errors = list(validator.iter_errors(data))
            assert errors == [], (
                f"Profile {family}.yaml ha {len(errors)} errori schema:\n"
                + "\n".join(f"  - {e.message}" for e in errors)
            )


class TestInvalidProfileRejected:
    """Test 12: profilo con nan_probability > 1 solleva ValidationError."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_invalid_nan_probability_rejected(self, sample_invalid_profile_dict: dict) -> None:
        """FaultProfile con nan_probability=1.5 solleva ValidationError (Test 12)."""
        with pytest.raises(ValidationError):
            FaultProfile.model_validate(sample_invalid_profile_dict)

    def test_invalid_sample_rate_rejected(self) -> None:
        """FaultProfile con sample_rate_hz=0 (non > 0) solleva ValidationError."""
        data = {
            "asset_family": "loom",
            "sample_rate_hz": 0,  # INVALID: deve essere > 0
            "fault_injection": {
                "nan_probability": 0.001,
                "drift": {"enabled": False},
                "jitter": {"enabled": False},
                "burst_noise": {"enabled": False},
                "alarm_storm": {"enabled": False},
            },
            "default_baseline": {"warp_tension": {"value": 25.0, "unit": "N"}},
        }
        with pytest.raises(ValidationError):
            FaultProfile.model_validate(data)

    def test_invalid_jitter_band_pct_rejected(self) -> None:
        """FaultProfile con band_pct > 100 solleva ValidationError."""
        data = {
            "asset_family": "loom",
            "sample_rate_hz": 10.0,
            "fault_injection": {
                "nan_probability": 0.001,
                "drift": {"enabled": False},
                "jitter": {"enabled": True, "band_pct": 150.0},  # INVALID: > 100
                "burst_noise": {"enabled": False},
                "alarm_storm": {"enabled": False},
            },
            "default_baseline": {"warp_tension": {"value": 25.0, "unit": "N"}},
        }
        with pytest.raises(ValidationError):
            FaultProfile.model_validate(data)


class TestTagsMatchRegistry:
    """Test 13: affected_tags e baseline keys sono in load_tag_dict()."""

    def test_tags_match_registry(self) -> None:
        """Tutti gli affected_tags e baseline keys referenziano tag_id validi (Test 13)."""
        tag_dict = load_tag_dict()

        for family in _FAMILIES:
            yaml_path = _PROFILES_DIR / f"{family}.yaml"
            with yaml_path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh)

            # Raccoglie tutti i tag_id referenziati nel profilo
            referenced_tags: set[str] = set()

            fi = data.get("fault_injection", {})
            for fault_type in ("drift", "jitter", "burst_noise", "alarm_storm"):
                ft = fi.get(fault_type, {})
                for tag in ft.get("affected_tags", []):
                    referenced_tags.add(tag)

            for tag_key in data.get("default_baseline", {}).keys():
                referenced_tags.add(tag_key)

            # Verifica che tutti i tag esistano nel registry
            missing = referenced_tags - set(tag_dict.keys())
            assert missing == set(), (
                f"Profile {family}.yaml referenzia tag non in registry: {sorted(missing)}\n"
                f"Tag disponibili: {sorted(tag_dict.keys())}"
            )
