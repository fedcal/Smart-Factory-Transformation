"""Loader del glossario bilingue IT/EN con caching LRU per cold-start performance.

Utilizza yaml.safe_load (mai yaml.load) per sicurezza.
Il loader e' idempotente: multiple chiamate con la stessa lingua restituiscono
la stessa lista cached (lru_cache sul parse del file).
"""

from __future__ import annotations

import pathlib
from functools import lru_cache
from typing import Literal

import yaml

from sft_domain.glossary._models import Term

_GLOSSARY_DIR = pathlib.Path(__file__).parent


def load_terms(lang: Literal["it", "en"]) -> list[Term]:
    """Carica i termini del glossario per la lingua specificata.

    Args:
        lang: Codice lingua — "it" (italiano) o "en" (inglese).

    Returns:
        Lista di Term (modelli Pydantic frozen, immutabili).

    Raises:
        ValueError: Se lang non e' "it" o "en".
        FileNotFoundError: Se il file YAML non esiste.
        yaml.YAMLError: Se il file YAML e' malformato.
        pydantic.ValidationError: Se un termine non rispetta lo schema.
    """
    if lang not in ("it", "en"):
        raise ValueError(f"Lingua non supportata: {lang!r}. Usa 'it' o 'en'.")
    return _load_terms_cached(lang)


@lru_cache(maxsize=2)
def _load_terms_cached(lang: Literal["it", "en"]) -> list[Term]:
    """Versione cached di load_terms — massimo 2 entry (it + en)."""
    yaml_path = _GLOSSARY_DIR / f"{lang}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"File glossario non trovato: {yaml_path}. "
            f"Assicurati che il file esista in {_GLOSSARY_DIR}."
        )

    raw_text = yaml_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load, mai yaml.load

    if not isinstance(raw_data, list):
        raise ValueError(
            f"Il file {yaml_path} deve contenere una lista YAML di termini, "
            f"trovato: {type(raw_data).__name__}"
        )

    return [Term.model_validate(entry) for entry in raw_data]


def invalidate_cache() -> None:
    """Invalida la cache del loader (utile nei test per ricaricare YAML modificati)."""
    _load_terms_cached.cache_clear()
