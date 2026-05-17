"""Glossario bilingue IT/EN del dominio textile + agentic platform.

Espone:
    load_terms(lang) -> list[Term]  — carica i termini del glossario per lingua
    Term                            — modello Pydantic frozen per un termine
"""

from sft_domain.glossary._loader import load_terms
from sft_domain.glossary._models import Category, Term

__all__ = ["load_terms", "Term", "Category"]
