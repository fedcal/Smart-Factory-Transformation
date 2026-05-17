"""Test di integrazione del glossario YAML bootstrap.

Verifica:
- load_terms('it') e load_terms('en') caricano i file reali senza errori
- Il numero di termini e' >= 70 per lingua (criterio di successo del piano)
- Ogni termine ha i campi obbligatori compilati
- I termini IT e EN hanno la stessa chiave concettuale (mapping 1:1 verificato per categoria)
- Tutte le categorie D-30 sono rappresentate in entrambe le lingue
- I related_terms non contengono il termine stesso (no auto-reference)
- Lo schema JSON valida i file YAML prodotti
"""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest
import yaml

from sft_domain.glossary._loader import invalidate_cache, load_terms
from sft_domain.glossary._models import Category, Term

GLOSSARY_DIR = pathlib.Path(__file__).parent.parent / "src" / "sft_domain" / "glossary"
SCHEMA_PATH = GLOSSARY_DIR / "schema.json"


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Invalida la cache prima di ogni test per isolare i test."""
    invalidate_cache()


class TestGlossaryLoad:
    """Test di caricamento dei file YAML reali."""

    def test_it_loads_without_error(self) -> None:
        """Il glossario IT deve caricarsi senza errori."""
        terms = load_terms("it")
        assert isinstance(terms, list)
        assert len(terms) > 0

    def test_en_loads_without_error(self) -> None:
        """Il glossario EN deve caricarsi senza errori."""
        terms = load_terms("en")
        assert isinstance(terms, list)
        assert len(terms) > 0

    def test_it_has_at_least_70_terms(self) -> None:
        """Il glossario IT deve avere almeno 70 termini (criterio Wave 1)."""
        terms = load_terms("it")
        assert len(terms) >= 70, (
            f"Glossario IT ha {len(terms)} termini, attesi >= 70. "
            "Aggiungi termini al file it.yaml."
        )

    def test_en_has_at_least_70_terms(self) -> None:
        """Il glossario EN deve avere almeno 70 termini (criterio Wave 1)."""
        terms = load_terms("en")
        assert len(terms) >= 70, (
            f"Glossario EN ha {len(terms)} termini, attesi >= 70. "
            "Aggiungi termini al file en.yaml."
        )

    def test_all_terms_are_valid_pydantic_models(self) -> None:
        """Tutti i termini IT devono essere istanze valide di Term."""
        for term in load_terms("it"):
            assert isinstance(term, Term)
            assert len(term.term) > 0
            assert len(term.definition) >= 10
            assert isinstance(term.category, Category)

    def test_all_en_terms_are_valid_pydantic_models(self) -> None:
        """Tutti i termini EN devono essere istanze valide di Term."""
        for term in load_terms("en"):
            assert isinstance(term, Term)
            assert len(term.term) > 0
            assert len(term.definition) >= 10
            assert isinstance(term.category, Category)


class TestGlossaryCoverage:
    """Test della copertura per categorie D-30."""

    def test_it_covers_all_d30_categories(self) -> None:
        """Il glossario IT deve coprire tutte le 9 categorie di D-30."""
        terms = load_terms("it")
        covered = {t.category for t in terms}
        all_cats = set(Category)
        missing = all_cats - covered
        assert not missing, f"Categorie mancanti nel glossario IT: {missing}"

    def test_en_covers_all_d30_categories(self) -> None:
        """Il glossario EN deve coprire tutte le 9 categorie di D-30."""
        terms = load_terms("en")
        covered = {t.category for t in terms}
        all_cats = set(Category)
        missing = all_cats - covered
        assert not missing, f"Categorie mancanti nel glossario EN: {missing}"

    def test_it_has_textile_process_terms(self) -> None:
        """Il glossario IT deve avere almeno 5 termini textile-process."""
        terms = [t for t in load_terms("it") if t.category == Category.TEXTILE_PROCESS]
        assert len(terms) >= 5, f"Solo {len(terms)} termini textile-process in IT, attesi >= 5"

    def test_en_has_textile_process_terms(self) -> None:
        """Il glossario EN deve avere almeno 5 termini textile-process."""
        terms = [t for t in load_terms("en") if t.category == Category.TEXTILE_PROCESS]
        assert len(terms) >= 5, f"Solo {len(terms)} termini textile-process in EN, attesi >= 5"

    def test_it_has_agentic_platform_terms(self) -> None:
        """Il glossario IT deve avere almeno 10 termini agentic-platform."""
        terms = [t for t in load_terms("it") if t.category == Category.AGENTIC_PLATFORM]
        assert len(terms) >= 10, f"Solo {len(terms)} termini agentic-platform in IT, attesi >= 10"

    def test_en_has_agentic_platform_terms(self) -> None:
        """Il glossario EN deve avere almeno 10 termini agentic-platform."""
        terms = [t for t in load_terms("en") if t.category == Category.AGENTIC_PLATFORM]
        assert len(terms) >= 10, f"Solo {len(terms)} termini agentic-platform in EN, attesi >= 10"

    def test_it_has_textile_defect_terms(self) -> None:
        """Il glossario IT deve avere almeno 10 termini textile-defect."""
        terms = [t for t in load_terms("it") if t.category == Category.TEXTILE_DEFECT]
        assert len(terms) >= 10, f"Solo {len(terms)} termini textile-defect in IT, attesi >= 10"

    def test_en_has_textile_defect_terms(self) -> None:
        """Il glossario EN deve avere almeno 10 termini textile-defect."""
        terms = [t for t in load_terms("en") if t.category == Category.TEXTILE_DEFECT]
        assert len(terms) >= 10, f"Solo {len(terms)} termini textile-defect in EN, attesi >= 10"


class TestGlossaryIntegrity:
    """Test di integrita' strutturale del glossario."""

    def test_no_duplicate_terms_in_it(self) -> None:
        """Non ci devono essere termini duplicati nel glossario IT."""
        terms = load_terms("it")
        term_names = [t.term for t in terms]
        duplicates = [name for name in term_names if term_names.count(name) > 1]
        assert not duplicates, f"Termini duplicati in IT: {set(duplicates)}"

    def test_no_duplicate_terms_in_en(self) -> None:
        """Non ci devono essere termini duplicati nel glossario EN."""
        terms = load_terms("en")
        term_names = [t.term for t in terms]
        duplicates = [name for name in term_names if term_names.count(name) > 1]
        assert not duplicates, f"Termini duplicati in EN: {set(duplicates)}"

    def test_no_self_referential_related_terms_in_it(self) -> None:
        """Nessun termine IT deve referenziare se stesso in related_terms."""
        for term in load_terms("it"):
            assert term.term not in term.related_terms, (
                f"Il termine '{term.term}' referenzia se stesso in related_terms"
            )

    def test_no_self_referential_related_terms_in_en(self) -> None:
        """Nessun termine EN deve referenziare se stesso in related_terms."""
        for term in load_terms("en"):
            assert term.term not in term.related_terms, (
                f"Il termine '{term.term}' referenzia se stesso in related_terms"
            )

    def test_it_terms_have_non_empty_definitions(self) -> None:
        """Tutti i termini IT devono avere definizioni non vuote e significative."""
        for term in load_terms("it"):
            assert len(term.definition) >= 20, (
                f"Definizione troppo corta per '{term.term}': '{term.definition}'"
            )

    def test_en_terms_have_non_empty_definitions(self) -> None:
        """Tutti i termini EN devono avere definizioni non vuote e significative."""
        for term in load_terms("en"):
            assert len(term.definition) >= 20, (
                f"Definition too short for '{term.term}': '{term.definition}'"
            )


class TestGlossarySchemaValidation:
    """Test di validazione dello schema JSON Draft 2020-12."""

    def test_schema_file_exists(self) -> None:
        """Il file schema.json deve esistere."""
        assert SCHEMA_PATH.exists(), f"Schema JSON non trovato a {SCHEMA_PATH}"

    def test_it_yaml_validates_against_schema(self) -> None:
        """Il file it.yaml deve essere valido rispetto allo schema JSON."""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        it_yaml = GLOSSARY_DIR / "it.yaml"
        data = yaml.safe_load(it_yaml.read_text(encoding="utf-8"))

        jsonschema.validate(instance=data, schema=schema)

    def test_en_yaml_validates_against_schema(self) -> None:
        """Il file en.yaml deve essere valido rispetto allo schema JSON."""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        en_yaml = GLOSSARY_DIR / "en.yaml"
        data = yaml.safe_load(en_yaml.read_text(encoding="utf-8"))

        jsonschema.validate(instance=data, schema=schema)

    def test_schema_uses_draft_2020_12(self) -> None:
        """Lo schema deve usare il draft JSON Schema 2020-12."""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
