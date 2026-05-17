"""Loader del glossario bilingue IT/EN — interfaccia pubblica (D-29).

Questo modulo re-esporta le funzioni da _loader.py per compatibilita'
con l'interfaccia pubblica del piano (import from sft_domain.glossary.loader).

Usa yaml.safe_load (mai yaml.load) per sicurezza — T-02-01.
lru_cache(maxsize=2) per cold-start performance.
"""

from sft_domain.glossary._loader import load_terms, load_terms_dict

__all__ = ["load_terms", "load_terms_dict"]
