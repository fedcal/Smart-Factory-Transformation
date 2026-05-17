"""Test di meta-validazione degli schemi JSON Draft 2020-12.

Verifica:
    test_glossary_schema_self_valid    — glossary.schema.json e' un JSON Schema valido
    test_sop_schema_self_valid         — sop.schema.json e' un JSON Schema valido
    test_assumption_schema_self_valid  — assumption.schema.json e' un JSON Schema valido

Usa Draft202012Validator.check_schema() che ritorna None su successo e
solleva SchemaError su schema malformato.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

SCHEMAS_DIR = (
    pathlib.Path(__file__).parent.parent
    / "src"
    / "sft_domain"
    / "schemas"
)


def _load_schema(filename: str) -> dict:
    """Carica uno schema JSON dalla directory schemas/."""
    path = SCHEMAS_DIR / filename
    assert path.exists(), f"Schema non trovato: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_glossary_schema_self_valid() -> None:
    """glossary.schema.json deve essere un JSON Schema Draft 2020-12 valido."""
    schema = _load_schema("glossary.schema.json")
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", (
        "glossary.schema.json deve dichiarare $schema Draft 2020-12"
    )
    # check_schema() restituisce None su successo, solleva SchemaError su errore
    result = Draft202012Validator.check_schema(schema)
    assert result is None


def test_sop_schema_self_valid() -> None:
    """sop.schema.json deve essere un JSON Schema Draft 2020-12 valido."""
    schema = _load_schema("sop.schema.json")
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", (
        "sop.schema.json deve dichiarare $schema Draft 2020-12"
    )
    result = Draft202012Validator.check_schema(schema)
    assert result is None


def test_assumption_schema_self_valid() -> None:
    """assumption.schema.json deve essere un JSON Schema Draft 2020-12 valido."""
    schema = _load_schema("assumption.schema.json")
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", (
        "assumption.schema.json deve dichiarare $schema Draft 2020-12"
    )
    result = Draft202012Validator.check_schema(schema)
    assert result is None


def test_sop_schema_has_required_fields(sample_sop_frontmatter: dict) -> None:
    """sop.schema.json deve avere almeno 11 campi required e validare l'esempio D-26."""
    schema = _load_schema("sop.schema.json")
    required = schema.get("required", [])
    assert len(required) >= 11, (
        f"sop.schema.json ha solo {len(required)} campi required, attesi >= 11"
    )
    # Valida l'esempio SOP da conftest
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(sample_sop_frontmatter))
    assert not errors, (
        f"Il sample SOP frontmatter non valida contro sop.schema.json: "
        + "; ".join(e.message for e in errors)
    )


def test_sop_schema_asset_family_has_6_values() -> None:
    """asset_family in sop.schema.json deve avere esattamente 6 valori."""
    schema = _load_schema("sop.schema.json")
    asset_family_enum = schema["properties"]["asset_family"]["enum"]
    assert len(asset_family_enum) == 6, (
        f"asset_family enum ha {len(asset_family_enum)} valori, attesi 6"
    )
    expected = {"weaving", "spinning", "warping", "dyeing", "finishing", "quality_grading"}
    assert set(asset_family_enum) == expected, (
        f"asset_family enum contiene valori inattesi: {set(asset_family_enum) - expected}"
    )


def test_glossary_schema_has_9_categories() -> None:
    """category in glossary.schema.json deve avere esattamente 9 valori (D-30)."""
    schema = _load_schema("glossary.schema.json")
    category_enum = schema["properties"]["category"]["enum"]
    assert len(category_enum) == 9, (
        f"category enum ha {len(category_enum)} valori, attesi 9"
    )


def test_assumption_schema_has_8_categories() -> None:
    """category in assumption.schema.json deve avere esattamente 8 valori (D-34)."""
    schema = _load_schema("assumption.schema.json")
    category_enum = schema["properties"]["category"]["enum"]
    assert len(category_enum) == 8, (
        f"category enum ha {len(category_enum)} valori, attesi 8"
    )


def test_assumption_schema_validates_sample(sample_assumption_dict: dict) -> None:
    """assumption.schema.json deve validare l'esempio A-001 da D-33."""
    schema = _load_schema("assumption.schema.json")
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(sample_assumption_dict))
    assert not errors, (
        f"Il sample assumption non valida contro assumption.schema.json: "
        + "; ".join(e.message for e in errors)
    )
