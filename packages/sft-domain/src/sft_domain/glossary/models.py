"""Modelli Pydantic v2 per il glossario bilingue IT/EN — interfaccia pubblica (D-29, D-30).

Questo modulo re-esporta i modelli da _models.py per compatibilita'
con l'interfaccia pubblica del piano (import from sft_domain.glossary.models).

Term: model_config = {"frozen": True, "extra": "forbid"} — immutabile, validazione stretta (T-02-02).
Category: enum con 9 valori D-30.
"""

from sft_domain.glossary._models import Category, Term

__all__ = ["Category", "Term"]
