"""
tests/test_assumption_register.py

Sanity checks per il registro delle assunzioni di progetto (D-33, D-35).

Verifica:
  - Il file register.yaml è un YAML valido e contiene una lista
  - Il numero corrente di entries corrisponde all'invariante del piano 02-03 (30 entries)
  - Gli id formano un intervallo contiguo A-001..A-030 senza buchi
  - Gli id sono tutti univoci (nessun duplicato)

Queste invarianti vengono aggiornate in Piano 06 quando il registro viene espanso a ~50 entries.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml


WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent
REGISTER_FILE = WORKSPACE_ROOT / "docs" / "assumptions" / "register.yaml"


@pytest.fixture(scope="module")
def register_data() -> list[dict]:
    """Carica il register.yaml e lo restituisce come lista di dizionari."""
    with REGISTER_FILE.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, list), (
        f"{REGISTER_FILE.relative_to(WORKSPACE_ROOT)} deve essere una lista YAML al top level"
    )
    return data


def test_register_yaml_loads(register_data: list[dict]) -> None:
    """Il file register.yaml si carica senza errori e restituisce una lista non vuota."""
    assert len(register_data) > 0, (
        "Il register.yaml non deve essere vuoto: deve contenere almeno un'assunzione."
    )


def test_register_has_30_entries(register_data: list[dict]) -> None:
    """Il registro contiene esattamente 30 entries (invariante di Piano 02-03).

    Piano 06 (Wave 3) espanderà il registro a ~50 entries; aggiornare questo test
    contestualmente.
    """
    assert len(register_data) == 30, (
        f"Attese 30 entries nel registro (Piano 02-03), trovate {len(register_data)}. "
        "Se hai aggiunto nuove entries, aggiorna questo test a Piano 06."
    )


def test_register_ids_contiguous(register_data: list[dict]) -> None:
    """Gli id delle entries formano un intervallo contiguo A-001..A-030 senza buchi."""
    import re

    id_pattern = re.compile(r"^A-([0-9]{3})$")
    numeric_ids: list[int] = []

    for entry in register_data:
        entry_id = entry.get("id", "")
        match = id_pattern.match(str(entry_id))
        assert match is not None, (
            f"Entry con id '{entry_id}' non rispetta il pattern A-NNN. "
            "Fix: correggere il campo id in docs/assumptions/register.yaml."
        )
        numeric_ids.append(int(match.group(1)))

    numeric_ids_sorted = sorted(numeric_ids)
    expected = list(range(1, len(numeric_ids_sorted) + 1))
    assert numeric_ids_sorted == expected, (
        f"Gli id del registro non formano un intervallo contiguo. "
        f"Trovati (ordinati): {[f'A-{n:03d}' for n in numeric_ids_sorted]}. "
        f"Attesi: {[f'A-{n:03d}' for n in expected]}. "
        "Fix: aggiungere le entries mancanti o rinumerare il registro."
    )


def test_register_ids_unique(register_data: list[dict]) -> None:
    """Ogni id nel registro appare esattamente una volta (nessun duplicato)."""
    id_values: list[str] = [str(entry.get("id", "")) for entry in register_data]
    seen: set[str] = set()
    duplicates: list[str] = []

    for entry_id in id_values:
        if entry_id in seen:
            duplicates.append(entry_id)
        seen.add(entry_id)

    assert len(duplicates) == 0, (
        f"Trovati id duplicati nel registro: {sorted(set(duplicates))}. "
        "Fix: assicurarsi che ogni id appaia esattamente una volta in "
        "docs/assumptions/register.yaml."
    )


def test_register_required_fields_present(register_data: list[dict]) -> None:
    """Ogni entry contiene tutti i campi richiesti dallo schema D-33."""
    required_fields = [
        "id",
        "statement",
        "category",
        "affected_components",
        "rationale",
        "validation_method",
        "risk_if_wrong",
        "status",
        "created_in_phase",
        "last_reviewed_in_phase",
        "superseded_by",
    ]
    missing_per_entry: list[str] = []

    for entry in register_data:
        entry_id = entry.get("id", "<unknown>")
        for field in required_fields:
            if field not in entry:
                missing_per_entry.append(f"  [{entry_id}] campo mancante: '{field}'")

    assert len(missing_per_entry) == 0, (
        f"Entries con campi mancanti ({len(missing_per_entry)} errori):\n"
        + "\n".join(missing_per_entry)
        + "\nFix: aggiungere i campi mancanti in docs/assumptions/register.yaml."
    )


def test_register_all_active_status(register_data: list[dict]) -> None:
    """Tutte le 30 entries di questo piano hanno status: active (invariante Piano 02-03)."""
    non_active: list[str] = [
        f"  [{entry.get('id', '<unknown>')}] status='{entry.get('status')}'"
        for entry in register_data
        if entry.get("status") != "active"
    ]
    assert len(non_active) == 0, (
        f"Le seguenti entries non hanno status 'active' (atteso per Piano 02-03):\n"
        + "\n".join(non_active)
        + "\nFix: impostare status: active o aggiornare questo test se lo status "
        "è stato deliberatamente modificato."
    )


def test_register_all_created_phase_2(register_data: list[dict]) -> None:
    """Tutte le entries di questo piano hanno created_in_phase: 2."""
    wrong_phase: list[str] = [
        f"  [{entry.get('id', '<unknown>')}] created_in_phase={entry.get('created_in_phase')}"
        for entry in register_data
        if entry.get("created_in_phase") != 2
    ]
    assert len(wrong_phase) == 0, (
        f"Le seguenti entries non hanno created_in_phase=2:\n"
        + "\n".join(wrong_phase)
        + "\nFix: correggere il campo created_in_phase in docs/assumptions/register.yaml."
    )
