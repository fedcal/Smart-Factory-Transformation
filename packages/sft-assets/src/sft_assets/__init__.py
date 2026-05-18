"""Asset registry — sft-assets: platform metadata per sim-textile, ot-bridge, agents Phase 4+ (D-45).

Espone:
    Asset                                    — modello Pydantic frozen per un asset fisico
    Tag                                      — modello Pydantic frozen per un tag sensore
    AssetFamily                              — enum 5 famiglie asset (D-21 + D-44)
    SemanticType                             — enum 10 tipi semantici sensore
    load_assets() -> tuple[Asset, ...]       — carica tutti gli asset con lru_cache
    load_assets_dict() -> dict[str, Asset]   — lookup O(1) per asset_id
    load_tag_dict() -> dict[str, Tag]        — lookup O(1) per tag_id + consistency check
    invalidate_cache() -> None               — invalida tutte le cache LRU (utile nei test)
"""

from sft_assets._loader import invalidate_cache, load_assets, load_assets_dict, load_tag_dict
from sft_assets._models import Asset, AssetFamily, SemanticType, Tag

__all__ = [
    "Asset",
    "AssetFamily",
    "SemanticType",
    "Tag",
    "invalidate_cache",
    "load_assets",
    "load_assets_dict",
    "load_tag_dict",
]
