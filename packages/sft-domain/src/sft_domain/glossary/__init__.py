"""Glossario bilingue IT/EN del dominio textile + agentic platform.

Espone:
    Category                            — enum categorie tassonomiche (D-30)
    Term                                — modello Pydantic frozen per un termine
    load_terms(lang) -> list[Term]      — carica i termini del glossario per lingua
    load_terms_dict(lang) -> dict[str, Term]  — lookup O(1) per termine (chiave lowercase)
"""

from sft_domain.glossary._loader import load_terms, load_terms_dict
from sft_domain.glossary._models import Category, Term

__all__ = ["Category", "Term", "load_terms", "load_terms_dict"]
