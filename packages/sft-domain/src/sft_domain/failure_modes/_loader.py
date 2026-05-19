"""Loader del registro failure modes con caching LRU per cold-start performance.

Utilizza yaml.safe_load (mai yaml.load) per sicurezza (T-05-03-01 / T-03-01-yaml).
Il loader e' idempotente: chiamate multiple restituiscono la stessa tuple cached (lru_cache).

Singleton identity: `load_failure_modes() is load_failure_modes()` -> True
"""

from __future__ import annotations

import pathlib
from functools import lru_cache

import yaml

from sft_domain.failure_modes.models import FailureMode

# Il file YAML risiede nel package sft_domain (sibling di failure_modes/)
_YAML_PATH = pathlib.Path(__file__).parent.parent / "failure_modes.yaml"


@lru_cache(maxsize=1)
def load_failure_modes() -> tuple[FailureMode, ...]:
    """Carica tutti i FailureMode dal registro YAML con caching LRU.

    Returns:
        Tuple immutabile di FailureMode (modelli Pydantic frozen).
        Chiamate ripetute restituiscono lo stesso oggetto (identita' is).

    Raises:
        FileNotFoundError: Se failure_modes.yaml non esiste.
        ValueError: Se il file non contiene un dict con chiave 'failure_modes' -> lista.
        yaml.YAMLError: Se il file YAML e' malformato.
        pydantic.ValidationError: Se un entry non rispetta lo schema FailureMode.
    """
    if not _YAML_PATH.exists():
        raise FileNotFoundError(
            f"failure_modes.yaml non trovato: {_YAML_PATH}. "
            f"Assicurati che il file esista in {_YAML_PATH.parent}."
        )

    raw_text = _YAML_PATH.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load, mai yaml.load (T-05-03-01)

    if not isinstance(raw_data, dict) or "failure_modes" not in raw_data:
        raise ValueError(
            f"failure_modes.yaml deve contenere un dict con chiave 'failure_modes', "
            f"trovato: {type(raw_data).__name__}"
        )

    entries = raw_data["failure_modes"]
    if not isinstance(entries, list):
        raise ValueError(
            f"La chiave 'failure_modes' deve contenere una lista, "
            f"trovato: {type(entries).__name__}"
        )

    return tuple(FailureMode.model_validate(entry) for entry in entries)


@lru_cache(maxsize=1)
def load_failure_modes_dict() -> dict[str, FailureMode]:
    """Restituisce un dizionario {failure_mode_id: FailureMode} per lookup O(1).

    Returns:
        Dizionario immutabile {id: FailureMode}.
    """
    return {fm.id: fm for fm in load_failure_modes()}


def invalidate_cache() -> None:
    """Invalida la cache del loader (utile nei test per ricaricare YAML modificati)."""
    load_failure_modes.cache_clear()
    load_failure_modes_dict.cache_clear()
