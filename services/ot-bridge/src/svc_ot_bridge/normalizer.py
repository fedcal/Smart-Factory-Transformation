"""Normalizer puro: trasforma dati OPC-UA in SensorEvent Pydantic frozen.

Pure transform — nessun I/O, nessuna chiamata write OPC-UA, nessun effetto collaterale.
Risolve asset_family e unit tramite sft-assets registry (load_assets_dict + load_tag_dict).

Sicurezza:
    - D-51 Layer 3: subscribe-only, nessuna write API OPC-UA
    - datetime.now(UTC) obbligatorio (Pitfall 7) — server_received viene passato dal caller
    - NaN → None per JSON-safety (A-002 — disconnessione sensore)
"""

from __future__ import annotations

import math
from datetime import datetime

from sft_assets._loader import load_assets_dict, load_tag_dict

from svc_ot_bridge.models import SensorEvent


def normalize_datachange(
    asset_id: str,
    tag_id: str,
    opcua_value: float,
    opcua_status: int,
    source_ts: datetime,
    server_received: datetime,
) -> SensorEvent:
    """Normalizza una DataChangeNotification OPC-UA in un SensorEvent Pydantic frozen.

    Args:
        asset_id: Identificativo asset (es. "LOOM-01") — deve essere nel registry.
        tag_id: Identificativo tag (es. "warp_tension") — deve essere nel tag dict.
        opcua_value: Valore float dal nodo OPC-UA. NaN viene mappato a None.
        opcua_status: OPC-UA StatusCode intero (Good=0, errori = bit-field).
        source_ts: Timestamp sorgente OPC-UA — deve essere timezone-aware (Pitfall 7).
        server_received: Timestamp ricezione bridge — deve essere timezone-aware.

    Returns:
        SensorEvent immutabile con asset_family e unit risolti dal registry.

    Raises:
        ValueError: Se asset_id o tag_id non sono nel registry.
        pydantic.ValidationError: Se source_ts o server_received sono naive.
    """
    # Risolvi asset dal registry (load_assets_dict con lru_cache)
    assets = load_assets_dict()
    asset = assets.get(asset_id)
    if asset is None:
        raise ValueError(
            f"asset_id '{asset_id}' non trovato nel registry sft-assets. "
            f"Verifica che registry.yaml contenga questo asset."
        )

    # Risolvi tag dal tag dict (load_tag_dict con lru_cache)
    tag_dict = load_tag_dict()
    tag = tag_dict.get(tag_id)
    if tag is None:
        raise ValueError(
            f"tag_id '{tag_id}' non trovato nel tag dict sft-assets. "
            f"Verifica che registry.yaml contenga questo tag per almeno un asset."
        )

    # NaN → None (A-002: disconnessione sensore; None e' JSON-serializable)
    value: float | None = None if math.isnan(opcua_value) else opcua_value

    # Costruisci SensorEvent — Pydantic validate enforce timestamp tz-awareness
    return SensorEvent(
        asset_id=asset_id,
        asset_family=asset.asset_family,
        tag_id=tag_id,
        timestamp_utc=source_ts,
        value=value,
        unit=tag.unit,
        quality_code=opcua_status,
        source="live",
        server_received_ts=server_received,
    )
