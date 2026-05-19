"""Test del loader failure modes con lru_cache + Pydantic strict schema.

Verifica:
- FailureMode e' frozen + extra=forbid (T-05-03-02)
- load_failure_modes() restituisce tuple immutabile con >= 30 entries
- Singleton identity: 2 chiamate -> stesso reference (lru_cache)
- invalidate_cache() svuota la cache
- yaml.safe_load e' usato (T-05-03-01) — mai yaml.load
- Tutte le failure mode hanno >= 1 SOP di riferimento nel corpus
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from sft_domain.failure_modes import (
    FailureMode,
    invalidate_cache,
    load_failure_modes,
    load_failure_modes_dict,
)

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


class TestFailureModeModel:
    """Test del modello Pydantic FailureMode (frozen + extra=forbid)."""

    def test_failure_mode_validates_minimal_entry(self) -> None:
        """FailureMode deve validare un entry minimale con severity default."""
        fm = FailureMode(
            id="broken_end",
            name_it="rottura filo ordito",
            name_en="broken end",
            asset_families=["weaving"],
            parts=["warp"],
        )
        assert fm.id == "broken_end"
        assert fm.severity == "medium"  # default

    def test_frozen_failure_mode_rejects_mutation(self) -> None:
        """Mutare un campo di FailureMode deve sollevare ValidationError (frozen)."""
        fm = FailureMode(
            id="broken_end",
            name_it="rottura filo ordito",
            name_en="broken end",
            asset_families=["weaving"],
            parts=["warp"],
        )
        with pytest.raises(ValidationError):
            fm.id = "altered"  # type: ignore[misc]

    def test_extra_field_forbidden(self) -> None:
        """extra='forbid' deve rifiutare campi non dichiarati."""
        with pytest.raises(ValidationError):
            FailureMode(
                id="broken_end",
                name_it="rottura filo ordito",
                name_en="broken end",
                asset_families=["weaving"],
                parts=["warp"],
                undeclared_field="boom",  # type: ignore[call-arg]
            )

    def test_empty_asset_families_rejected(self) -> None:
        """asset_families vuoto deve essere rifiutato (min_length=1)."""
        with pytest.raises(ValidationError):
            FailureMode(
                id="broken_end",
                name_it="rottura filo ordito",
                name_en="broken end",
                asset_families=[],
                parts=["warp"],
            )

    def test_empty_parts_rejected(self) -> None:
        """parts vuoto deve essere rifiutato (min_length=1)."""
        with pytest.raises(ValidationError):
            FailureMode(
                id="broken_end",
                name_it="rottura filo ordito",
                name_en="broken end",
                asset_families=["weaving"],
                parts=[],
            )

    def test_id_must_be_snake_case_lowercase(self) -> None:
        """id non snake_case lowercase deve essere rifiutato."""
        with pytest.raises(ValidationError):
            FailureMode(
                id="BrokenEnd",
                name_it="x",
                name_en="x",
                asset_families=["weaving"],
                parts=["warp"],
            )

    def test_severity_literal_enforced(self) -> None:
        """severity fuori dal Literal accettato deve essere rifiutato."""
        with pytest.raises(ValidationError):
            FailureMode(
                id="broken_end",
                name_it="rottura filo ordito",
                name_en="broken end",
                asset_families=["weaving"],
                parts=["warp"],
                severity="critical",  # type: ignore[arg-type]
            )


class TestLoadFailureModes:
    """Test del loader lru_cache singleton."""

    def setup_method(self) -> None:
        invalidate_cache()

    def teardown_method(self) -> None:
        invalidate_cache()

    def test_loads_at_least_30_failure_modes(self) -> None:
        """Il YAML deve contenere >= 30 entries (requirement KNW-08 SC#4)."""
        fms = load_failure_modes()
        assert len(fms) >= 30, f"Atteso >=30 failure modes, trovato {len(fms)}"

    def test_returns_tuple_immutable(self) -> None:
        """load_failure_modes() deve restituire una tuple (immutabile)."""
        fms = load_failure_modes()
        assert isinstance(fms, tuple)

    def test_each_entry_is_failure_mode(self) -> None:
        """Ogni entry deve essere un'istanza FailureMode con campi non vuoti."""
        fms = load_failure_modes()
        for fm in fms:
            assert isinstance(fm, FailureMode)
            assert fm.id
            assert fm.name_it
            assert fm.name_en
            assert len(fm.asset_families) >= 1
            assert len(fm.parts) >= 1

    def test_singleton_identity(self) -> None:
        """2 chiamate consecutive devono restituire lo stesso oggetto (lru_cache)."""
        first = load_failure_modes()
        second = load_failure_modes()
        assert first is second

    def test_failure_modes_dict_lookup(self) -> None:
        """load_failure_modes_dict() deve restituire un dict {id: FailureMode}."""
        d = load_failure_modes_dict()
        assert isinstance(d, dict)
        # ogni FailureMode deve essere nel dict
        for fm in load_failure_modes():
            assert d[fm.id] is fm

    def test_failure_modes_dict_singleton(self) -> None:
        """load_failure_modes_dict() deve essere singleton anch'esso."""
        first = load_failure_modes_dict()
        second = load_failure_modes_dict()
        assert first is second

    def test_invalidate_cache_clears_lru(self) -> None:
        """invalidate_cache() deve svuotare la cache del loader."""
        load_failure_modes()
        info_before = load_failure_modes.cache_info()
        assert info_before.currsize == 1
        invalidate_cache()
        info_after = load_failure_modes.cache_info()
        assert info_after.currsize == 0

    def test_spans_five_process_families(self) -> None:
        """Le >=30 entries devono coprire le 5 process families."""
        fms = load_failure_modes()
        families = set()
        for fm in fms:
            families.update(fm.asset_families)
        expected = {"weaving", "spinning", "dyeing", "quality_grading"}
        # almeno 4 famiglie principali (finishing e' opzionale: Phase 2 non ne ha SOP)
        assert expected.issubset(families), (
            f"Atteso almeno {expected}, trovato {families}"
        )


class TestSafeLoadIsUsed:
    """T-05-03-01: il loader deve usare yaml.safe_load, mai yaml.load."""

    def setup_method(self) -> None:
        invalidate_cache()

    def teardown_method(self) -> None:
        invalidate_cache()

    def test_unsafe_loader_not_referenced(self) -> None:
        """Il loader non deve referenziare yaml.Loader / yaml.FullLoader / yaml.UnsafeLoader.

        Solo SafeLoader (implicito in yaml.safe_load) e' consentito.
        """
        from sft_domain.failure_modes import _loader

        src = Path(_loader.__file__).read_text(encoding="utf-8")
        forbidden = ["yaml.Loader", "yaml.FullLoader", "yaml.UnsafeLoader", "unsafe_load"]
        for token in forbidden:
            assert token not in src, (
                f"Token vietato '{token}' trovato in {_loader.__file__} "
                f"(T-05-03-01 / CWE-502)."
            )

    def test_safe_load_returns_expected_count(self) -> None:
        """Esegue safe_load direttamente sul YAML e verifica che il loader ottenga lo stesso risultato."""
        from sft_domain.failure_modes import _loader

        raw = yaml.safe_load(_loader._YAML_PATH.read_text(encoding="utf-8"))
        assert isinstance(raw, dict)
        assert isinstance(raw["failure_modes"], list)
        assert len(raw["failure_modes"]) == len(load_failure_modes())

    def test_loader_source_uses_safe_load(self) -> None:
        """Il sorgente del loader deve contenere yaml.safe_load e non yaml.load() raw."""
        from sft_domain.failure_modes import _loader

        src = Path(_loader.__file__).read_text(encoding="utf-8")
        assert "yaml.safe_load" in src
        # nessuna chiamata raw `yaml.load(` (escluso `yaml.safe_load(`)
        assert "yaml.load(" not in src.replace("yaml.safe_load(", "")


class TestLoaderErrorPaths:
    """Test dei percorsi di errore del loader."""

    def setup_method(self) -> None:
        invalidate_cache()

    def teardown_method(self) -> None:
        invalidate_cache()

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """File YAML mancante deve sollevare FileNotFoundError."""
        from sft_domain.failure_modes import _loader

        missing = tmp_path / "nope.yaml"
        with patch.object(_loader, "_YAML_PATH", missing):
            invalidate_cache()
            with pytest.raises(FileNotFoundError, match="failure_modes.yaml"):
                load_failure_modes()

    def test_non_dict_root_raises_value_error(self, tmp_path: Path) -> None:
        """YAML root non-dict deve sollevare ValueError."""
        from sft_domain.failure_modes import _loader

        bad = tmp_path / "bad.yaml"
        bad.write_text("- not a dict\n- just a list\n", encoding="utf-8")
        with patch.object(_loader, "_YAML_PATH", bad):
            invalidate_cache()
            with pytest.raises(ValueError, match="failure_modes"):
                load_failure_modes()

    def test_missing_failure_modes_key_raises(self, tmp_path: Path) -> None:
        """YAML senza chiave 'failure_modes' deve sollevare ValueError."""
        from sft_domain.failure_modes import _loader

        bad = tmp_path / "bad.yaml"
        bad.write_text("other_key: []\n", encoding="utf-8")
        with patch.object(_loader, "_YAML_PATH", bad):
            invalidate_cache()
            with pytest.raises(ValueError, match="failure_modes"):
                load_failure_modes()

    def test_failure_modes_value_not_list_raises(self, tmp_path: Path) -> None:
        """failure_modes: <non-lista> deve sollevare ValueError."""
        from sft_domain.failure_modes import _loader

        bad = tmp_path / "bad.yaml"
        bad.write_text("failure_modes: not_a_list\n", encoding="utf-8")
        with patch.object(_loader, "_YAML_PATH", bad):
            invalidate_cache()
            with pytest.raises(ValueError, match="lista"):
                load_failure_modes()


class TestFailureModesReferencedByCorpus:
    """Cross-reference: ogni FailureMode deve avere >=1 SOP referenziante."""

    def test_all_failure_modes_referenced_by_at_least_one_sop(self) -> None:
        """Eseguendo il validator CI, deve uscire 0 (zero orphan failure modes).

        Lo script scripts/validate-failure-modes.py viene invocato come subprocess
        per riprodurre l'invocazione reale di CI.
        """
        validator = WORKSPACE_ROOT / "scripts" / "validate-failure-modes.py"
        if not validator.exists():
            pytest.skip("validator non ancora creato (Task 2)")

        result = subprocess.run(
            [sys.executable, str(validator)],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"validate-failure-modes.py ha trovato failure mode orphan:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
