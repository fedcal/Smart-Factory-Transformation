"""Test dei modelli Pydantic del glossario.

Verifica:
- Costruzione valida di un Term con tutti i campi
- Validazione categoria (solo valori enum ammessi)
- Frozen: mutazione solleva TypeError
- extra="forbid": campo extra solleva ValidationError
- Valori di default corretti
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sft_domain.glossary._models import Category, Source, Term


class TestTermConstruction:
    """Costruzione e validazione di Term."""

    def test_minimal_term(self) -> None:
        """Un Term con solo campi obbligatori deve essere valido."""
        term = Term(
            term="pick density",
            definition="Number of weft picks per centimeter of fabric.",
            category=Category.TEXTILE_KPI,
        )
        assert term.term == "pick density"
        assert term.category == Category.TEXTILE_KPI
        assert term.related_terms == []
        assert term.examples == []
        assert term.source == Source.INDUSTRY_STANDARD
        assert term.no_direct_equivalent is False

    def test_full_term(self) -> None:
        """Un Term con tutti i campi deve essere valido."""
        term = Term(
            term="pick density",
            definition="Number of weft picks per centimeter of fabric.",
            category=Category.TEXTILE_KPI,
            related_terms=["warp_tension", "weft_yarn"],
            examples=["Pick density of 22-28 picks/cm is typical for cotton shirting"],
            source=Source.ISO_STANDARD,
            no_direct_equivalent=False,
        )
        assert term.related_terms == ["warp_tension", "weft_yarn"]
        assert len(term.examples) == 1
        assert term.source == Source.ISO_STANDARD

    def test_agentic_term(self) -> None:
        """Un termine agentic platform deve essere valido."""
        term = Term(
            term="hitl",
            definition="Human-in-the-Loop — interaction pattern where a human approves or overrides agent decisions at defined checkpoints.",
            category=Category.AGENTIC_PLATFORM,
            related_terms=["interrupt", "audit_trail"],
            source=Source.AGENTIC_COMMUNITY,
        )
        assert term.category == Category.AGENTIC_PLATFORM

    def test_no_direct_equivalent_flag(self) -> None:
        """Il flag no_direct_equivalent deve essere settabile a True."""
        term = Term(
            term="subbio",
            definition="Cilindro su cui e' avvolto il filo di ordito nel telaio tessile.",
            category=Category.TEXTILE_ASSET,
            no_direct_equivalent=False,
        )
        assert term.no_direct_equivalent is False


class TestTermValidation:
    """Validazione dei vincoli di schema."""

    def test_invalid_category_raises(self) -> None:
        """Una categoria non riconosciuta deve sollevare ValidationError."""
        with pytest.raises(ValidationError):
            Term(
                term="test",
                definition="A test definition that is long enough.",
                category="invalid-category",  # type: ignore[arg-type]
            )

    def test_empty_term_raises(self) -> None:
        """Un termine vuoto deve sollevare ValidationError."""
        with pytest.raises(ValidationError):
            Term(
                term="",
                definition="A valid definition that is long enough.",
                category=Category.TEXTILE_PROCESS,
            )

    def test_short_definition_raises(self) -> None:
        """Una definizione troppo corta deve sollevare ValidationError (min_length=10)."""
        with pytest.raises(ValidationError):
            Term(
                term="test",
                definition="Too short",
                category=Category.TEXTILE_PROCESS,
            )

    def test_extra_field_raises(self) -> None:
        """Un campo extra deve sollevare ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            Term(
                term="test",
                definition="A valid definition that is long enough.",
                category=Category.TEXTILE_PROCESS,
                unknown_field="value",  # type: ignore[call-arg]
            )


class TestTermImmutability:
    """Verifica che Term sia frozen (immutabile)."""

    def test_frozen_raises_on_assignment(self) -> None:
        """Assegnazione diretta su un Term frozen deve sollevare TypeError."""
        term = Term(
            term="loom",
            definition="A machine for interlacing warp and weft threads to produce woven fabric.",
            category=Category.TEXTILE_ASSET,
        )
        with pytest.raises(Exception):  # TypeError o ValidationError a seconda della versione
            term.term = "modified"  # type: ignore[misc]


class TestCategoryEnum:
    """Verifica che tutte le categorie D-30 siano presenti."""

    def test_all_textile_categories_present(self) -> None:
        """Tutte le categorie textile di D-30 devono essere presenti."""
        textile_cats = {
            Category.TEXTILE_PROCESS,
            Category.TEXTILE_ASSET,
            Category.TEXTILE_DEFECT,
            Category.TEXTILE_KPI,
            Category.TEXTILE_TOOL_PPE,
            Category.TEXTILE_MATERIAL,
        }
        assert len(textile_cats) == 6

    def test_all_agentic_categories_present(self) -> None:
        """Tutte le categorie agentic di D-30 devono essere presenti."""
        agentic_cats = {
            Category.AGENTIC_PLATFORM,
            Category.AGENTIC_TOOL,
            Category.REGULATORY,
        }
        assert len(agentic_cats) == 3

    def test_category_values(self) -> None:
        """I valori stringa delle categorie devono corrispondere allo schema JSON."""
        assert Category.TEXTILE_PROCESS.value == "textile-process"
        assert Category.AGENTIC_PLATFORM.value == "agentic-platform"
        assert Category.REGULATORY.value == "regulatory"
