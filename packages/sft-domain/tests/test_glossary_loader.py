"""Test del loader del glossario con lru_cache.

Verifica:
- Lingua non valida solleva ValueError
- File non trovato solleva FileNotFoundError
- Cache LRU funziona (stesso oggetto restituito su chiamate multiple)
- invalidate_cache() svuota la cache
- YAML malformato solleva yaml.YAMLError
- YAML non-lista solleva ValueError
"""

from __future__ import annotations

import pathlib
import tempfile
from unittest.mock import patch

import pytest
import yaml

from sft_domain.glossary._loader import _load_terms_cached, invalidate_cache, load_terms


class TestLoadTermsValidation:
    """Validazione input della funzione load_terms."""

    def test_invalid_lang_raises_value_error(self) -> None:
        """Una lingua non supportata deve sollevare ValueError."""
        with pytest.raises(ValueError, match="Lingua non supportata"):
            load_terms("fr")  # type: ignore[arg-type]

    def test_invalid_lang_de_raises(self) -> None:
        """Lingua 'de' non supportata deve sollevare ValueError."""
        with pytest.raises(ValueError, match="Lingua non supportata"):
            load_terms("de")  # type: ignore[arg-type]


class TestLoadTermsCache:
    """Test della cache LRU del loader."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_invalidate_cache_clears_lru(self) -> None:
        """invalidate_cache() deve svuotare la cache del loader."""
        info_before = _load_terms_cached.cache_info()
        invalidate_cache()
        info_after = _load_terms_cached.cache_info()
        # Dopo invalidazione, currsize deve essere 0
        assert info_after.currsize == 0

    def test_cache_info_tracks_hits(self) -> None:
        """La cache LRU deve tracciare hits e misses."""
        info = _load_terms_cached.cache_info()
        assert hasattr(info, "hits")
        assert hasattr(info, "misses")
        assert hasattr(info, "maxsize")
        assert info.maxsize == 2  # maxsize=2 per it+en


class TestLoadTermsFileHandling:
    """Test della gestione file del loader."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_missing_yaml_raises_file_not_found(self) -> None:
        """Un file YAML mancante deve sollevare FileNotFoundError."""
        # Patcha _GLOSSARY_DIR a una directory temporanea senza it.yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sft_domain.glossary._loader._GLOSSARY_DIR", pathlib.Path(tmpdir)):
                invalidate_cache()
                with pytest.raises(FileNotFoundError, match="File glossario non trovato"):
                    load_terms("it")

    def test_malformed_yaml_raises_yaml_error(self) -> None:
        """Un YAML malformato deve sollevare yaml.YAMLError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = pathlib.Path(tmpdir) / "it.yaml"
            yaml_file.write_text("invalid: yaml: : :\n  - broken[", encoding="utf-8")
            with patch("sft_domain.glossary._loader._GLOSSARY_DIR", pathlib.Path(tmpdir)):
                invalidate_cache()
                with pytest.raises(yaml.YAMLError):
                    load_terms("it")

    def test_non_list_yaml_raises_value_error(self) -> None:
        """Un YAML che non e' una lista deve sollevare ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = pathlib.Path(tmpdir) / "it.yaml"
            yaml_file.write_text("key: value\nnot_a_list: true", encoding="utf-8")
            with patch("sft_domain.glossary._loader._GLOSSARY_DIR", pathlib.Path(tmpdir)):
                invalidate_cache()
                with pytest.raises(ValueError, match="deve contenere una lista YAML"):
                    load_terms("it")

    def test_valid_yaml_returns_list_of_terms(self) -> None:
        """Un YAML valido deve restituire una lista di Term."""
        from sft_domain.glossary._models import Category, Term

        valid_yaml = """
- term: pick density
  definition: "Number of weft picks per centimeter of fabric, determining fabric density."
  category: textile-kpi
  related_terms: [warp_tension]
  source: industry-standard
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = pathlib.Path(tmpdir) / "en.yaml"
            yaml_file.write_text(valid_yaml, encoding="utf-8")
            with patch("sft_domain.glossary._loader._GLOSSARY_DIR", pathlib.Path(tmpdir)):
                invalidate_cache()
                terms = load_terms("en")

        assert isinstance(terms, list)
        assert len(terms) == 1
        assert isinstance(terms[0], Term)
        assert terms[0].term == "pick density"
        assert terms[0].category == Category.TEXTILE_KPI

    def test_cached_call_returns_same_object(self) -> None:
        """Chiamate multiple con la stessa lingua devono restituire lo stesso oggetto (cache hit)."""
        valid_yaml = """
- term: loom
  definition: "A machine for interlacing warp and weft threads to produce woven fabric."
  category: textile-asset
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = pathlib.Path(tmpdir) / "it.yaml"
            yaml_file.write_text(valid_yaml, encoding="utf-8")
            with patch("sft_domain.glossary._loader._GLOSSARY_DIR", pathlib.Path(tmpdir)):
                invalidate_cache()
                terms1 = load_terms("it")
                terms2 = load_terms("it")

        # La cache deve restituire lo stesso oggetto (identita' di riferimento)
        assert terms1 is terms2
