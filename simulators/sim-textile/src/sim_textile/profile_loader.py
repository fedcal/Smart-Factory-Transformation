"""Loader dei fault injection profiles YAML con caching LRU.

Pattern S-2: yaml.safe_load esclusivo (T-03-03-yaml, RESEARCH §Security checks 1).
Pattern S-5: lru_cache + invalidate_cache() (test support).

Sicurezza:
    - yaml.safe_load SEMPRE, mai yaml.load (T-03-03-yaml)
    - Pydantic validation su FaultProfile (frozen=True, extra="forbid") (T-03-03-pydantic)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from sim_textile.models import FaultProfile

# Percorso profiles/ relativo a questo modulo
# src/sim_textile/profile_loader.py -> ../../profiles
_PROFILES_DIR = Path(__file__).parent.parent.parent / "profiles"

_FAMILY_NAMES = ("loom", "spinning", "warping", "dyeing", "finishing")


@lru_cache(maxsize=5)
def load_profile(family: str) -> FaultProfile:
    """Carica il fault profile per una asset_family dal file YAML corrispondente.

    Pattern S-2: usa yaml.safe_load esclusivamente.
    Pattern S-5: lru_cache(maxsize=5) per 5 family.

    Args:
        family: Nome della famiglia asset (es. "loom", "spinning").

    Returns:
        FaultProfile validato e frozen.

    Raises:
        FileNotFoundError: Se il file profiles/{family}.yaml non esiste.
        yaml.YAMLError: Se il YAML e' malformato.
        pydantic.ValidationError: Se il profilo non valida.
    """
    yaml_path = _PROFILES_DIR / f"{family}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Profile non trovato: {yaml_path}. "
            f"Assicurati che il file esista in {_PROFILES_DIR}."
        )

    with yaml_path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)  # SEMPRE safe_load, mai yaml.load (Pattern S-2)

    return FaultProfile.model_validate(raw)


def load_all_profiles() -> dict[str, FaultProfile]:
    """Carica tutti e 5 i fault profiles.

    Returns:
        dict[str, FaultProfile] con chiavi loom, spinning, warping, dyeing, finishing.
    """
    return {family: load_profile(family) for family in _FAMILY_NAMES}


def invalidate_cache() -> None:
    """Invalida la cache del loader (utile nei test per ricaricare YAML modificati)."""
    load_profile.cache_clear()
