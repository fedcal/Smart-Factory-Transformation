"""Test di meta-validazione dello schema JSON Draft 2020-12 e del registry YAML.

Verifica:
    test_asset_schema_self_valid         — asset.schema.json e' un JSON Schema valido (Draft 2020-12)
    test_registry_validates_against_schema — ogni entry di registry.yaml valida contro lo schema
    test_registry_asset_ids_unique        — tutti gli asset_id in registry.yaml sono unici
    test_registry_count_matches_breakdown — 30 asset, breakdown per family corretto
"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

from sft_assets._loader import invalidate_cache, load_assets, load_tag_dict

SCHEMAS_DIR = (
    pathlib.Path(__file__).parent.parent
    / "src"
    / "sft_assets"
    / "schemas"
)

REGISTRY_PATH = (
    pathlib.Path(__file__).parent.parent
    / "src"
    / "sft_assets"
    / "registry.yaml"
)


def _load_schema(filename: str) -> dict:
    """Carica uno schema JSON dalla directory schemas/."""
    path = SCHEMAS_DIR / filename
    assert path.exists(), f"Schema non trovato: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_asset_schema_self_valid() -> None:
    """asset.schema.json deve essere un JSON Schema Draft 2020-12 valido."""
    schema = _load_schema("asset.schema.json")
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", (
        "asset.schema.json deve dichiarare $schema Draft 2020-12"
    )
    result = Draft202012Validator.check_schema(schema)
    assert result is None


def test_registry_validates_against_schema() -> None:
    """Ogni entry di registry.yaml deve validare contro asset.schema.json."""
    schema = _load_schema("asset.schema.json")
    validator = Draft202012Validator(schema)

    assert REGISTRY_PATH.exists(), f"registry.yaml non trovato: {REGISTRY_PATH}"
    with REGISTRY_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)  # SEMPRE safe_load, mai yaml.load

    assert isinstance(data, list), "registry.yaml deve essere una lista"
    assert len(data) > 0, "registry.yaml non deve essere vuoto"

    errors = []
    for idx, entry in enumerate(data):
        asset_id = entry.get("asset_id", f"<entry #{idx + 1}>") if isinstance(entry, dict) else f"<entry #{idx + 1}>"
        for schema_error in sorted(validator.iter_errors(entry), key=lambda e: list(e.path)):
            field_path = " -> ".join(str(p) for p in schema_error.path) if schema_error.path else "(root)"
            errors.append(f"[{asset_id}] field '{field_path}': {schema_error.message}")

    assert not errors, "Errori di validazione in registry.yaml:\n" + "\n".join(errors)


def test_registry_asset_ids_unique() -> None:
    """Tutti gli asset_id in registry.yaml devono essere unici (case-sensitive)."""
    assert REGISTRY_PATH.exists(), f"registry.yaml non trovato: {REGISTRY_PATH}"
    with REGISTRY_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)  # SEMPRE safe_load, mai yaml.load

    asset_ids = [entry.get("asset_id") for entry in data if isinstance(entry, dict) and "asset_id" in entry]
    assert len(asset_ids) == len(set(asset_ids)), (
        f"asset_id non unici in registry.yaml: {[x for x in asset_ids if asset_ids.count(x) > 1]}"
    )


def test_registry_count_matches_breakdown() -> None:
    """registry.yaml deve contenere esattamente 30 asset con breakdown: loom=12, spinning=8, warping=4, dyeing=4, finishing=2."""
    invalidate_cache()
    assets = load_assets()

    assert len(assets) == 30, f"registry.yaml contiene {len(assets)} asset, attesi 30"

    by_family = {}
    for asset in assets:
        family = asset.asset_family.value
        by_family[family] = by_family.get(family, 0) + 1

    expected = {"loom": 12, "spinning": 8, "warping": 4, "dyeing": 4, "finishing": 2}
    assert by_family == expected, f"Breakdown per family: {by_family}, atteso: {expected}"


def test_registry_tag_dict_has_sufficient_distinct_tags() -> None:
    """load_tag_dict() deve ritornare almeno 20 tag distinti."""
    invalidate_cache()
    tag_dict = load_tag_dict()
    assert len(tag_dict) >= 20, f"tag_dict contiene {len(tag_dict)} tag distinti, attesi >= 20"
