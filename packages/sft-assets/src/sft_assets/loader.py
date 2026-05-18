"""Loader del registro asset — interfaccia pubblica (D-45).

Questo modulo re-esporta le funzioni da _loader.py per compatibilita'
con l'interfaccia pubblica del piano (import from sft_assets.loader).

Usa yaml.safe_load (mai yaml.load) per sicurezza — T-03-01-yaml.
lru_cache(maxsize=1) per cold-start performance.
invalidate_cache() per i test (invalida tutte le cache LRU).
"""

from sft_assets._loader import invalidate_cache, load_assets, load_assets_dict, load_tag_dict

__all__ = ["invalidate_cache", "load_assets", "load_assets_dict", "load_tag_dict"]
