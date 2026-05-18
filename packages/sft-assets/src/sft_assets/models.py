"""Modelli Pydantic v2 per il registro asset — interfaccia pubblica (D-45).

Questo modulo re-esporta i modelli da _models.py per compatibilita'
con l'interfaccia pubblica del piano (import from sft_assets.models).

Asset: model_config = {"frozen": True, "extra": "forbid"} — immutabile, validazione stretta (T-03-01-pydantic).
Tag: model_config = {"frozen": True, "extra": "forbid"} — immutabile, validazione stretta.
AssetFamily: enum con 5 valori D-21 + D-44.
SemanticType: enum con 10 valori canonici.
"""

from sft_assets._models import Asset, AssetFamily, SemanticType, Tag

__all__ = ["Asset", "AssetFamily", "SemanticType", "Tag"]
