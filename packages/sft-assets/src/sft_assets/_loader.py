"""Loader del registro asset con caching LRU per cold-start performance.

Utilizza yaml.safe_load (mai yaml.load) per sicurezza (T-03-01-yaml, RESEARCH §Pitfall Tampering).
Il loader e' idempotente: multiple chiamate restituiscono la stessa tuple cached (lru_cache).

load_tag_dict() impone consistenza inter-asset: stesso tag_id deve avere stessa definizione
(unit + sample_rate_hz + semantic_type) in tutti gli asset che lo espongono.
"""

from __future__ import annotations

import pathlib
from functools import lru_cache

import yaml

from sft_assets._models import Asset, Tag

_REGISTRY_PATH = pathlib.Path(__file__).parent / "registry.yaml"


@lru_cache(maxsize=1)
def load_assets() -> tuple[Asset, ...]:
    """Carica tutti gli asset dal registro YAML con caching LRU.

    Returns:
        Tuple di Asset (modelli Pydantic frozen, immutabili).

    Raises:
        FileNotFoundError: Se registry.yaml non esiste.
        yaml.YAMLError: Se il file YAML e' malformato.
        pydantic.ValidationError: Se un entry non rispetta lo schema.
    """
    if not _REGISTRY_PATH.exists():
        raise FileNotFoundError(
            f"Registry non trovato: {_REGISTRY_PATH}. "
            f"Assicurati che registry.yaml esista in {_REGISTRY_PATH.parent}."
        )

    raw_text = _REGISTRY_PATH.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load, mai yaml.load (T-03-01-yaml)

    if not isinstance(raw_data, list):
        raise ValueError(
            f"registry.yaml deve contenere una lista YAML di asset, "
            f"trovato: {type(raw_data).__name__}"
        )

    return tuple(Asset.model_validate(entry) for entry in raw_data)


@lru_cache(maxsize=1)
def load_assets_dict() -> dict[str, Asset]:
    """Restituisce un dizionario {asset_id: Asset} per lookup O(1).

    Returns:
        Dizionario immutabile {asset_id: Asset}.
    """
    return {asset.asset_id: asset for asset in load_assets()}


@lru_cache(maxsize=1)
def load_tag_dict() -> dict[str, Tag]:
    """Restituisce un dizionario {tag_id: Tag} per lookup O(1).

    Impone consistenza inter-asset: se stesso tag_id appare in piu' asset,
    unit + sample_rate_hz + semantic_type DEVONO essere identici.

    Returns:
        Dizionario {tag_id: Tag} con le definizioni canoniche dei tag.

    Raises:
        AssertionError: Se stesso tag_id ha definizioni divergenti tra asset.
    """
    tag_registry: dict[str, Tag] = {}

    for asset in load_assets():
        for tag in asset.tags:
            if tag.tag_id in tag_registry:
                existing = tag_registry[tag.tag_id]
                assert (
                    existing.unit == tag.unit
                    and existing.sample_rate_hz == tag.sample_rate_hz
                    and existing.semantic_type == tag.semantic_type
                ), (
                    f"Tag '{tag.tag_id}' ha definizioni divergenti tra asset: "
                    f"esistente={existing!r}, trovato in {asset.asset_id}={tag!r}. "
                    f"Allineare unit, sample_rate_hz e semantic_type in registry.yaml."
                )
            else:
                tag_registry[tag.tag_id] = tag

    return tag_registry


def invalidate_cache() -> None:
    """Invalida la cache del loader (utile nei test per ricaricare YAML modificati)."""
    load_assets.cache_clear()
    load_assets_dict.cache_clear()
    load_tag_dict.cache_clear()
