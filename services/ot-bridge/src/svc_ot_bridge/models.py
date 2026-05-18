"""Modelli Pydantic v2 per svc-ot-bridge — SensorEvent frozen + AuditEvent.

Tutti i modelli sono frozen=True, extra="forbid" per immutabilita' e validazione stretta.
Vedi: D-51 Layer 3 (zero write API OPC-UA), D-52 (subject hierarchy), OQ3 (audit.ot.bridge).

Sicurezza:
    - timestamp_utc e server_received_ts devono essere timezone-aware (T-03-04-tz-naive)
    - SensorEvent.source e' Literal per prevenire replay attack cross-source (T-03-04-replay)
    - extra="forbid" previene injection di campi arbitrari
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator
from sft_assets._models import AssetFamily


class SensorEvent(BaseModel):
    """Evento sensore normalizzato — output del bridge OPC-UA → NATS/TimescaleDB.

    Immutabile (frozen=True) — crea nuovi oggetti invece di mutare quelli esistenti.
    Extra fields sono vietati (extra="forbid") per validazione stretta.

    Sicurezza (T-03-04-tz-naive): timestamp_utc e server_received_ts devono essere
    timezone-aware — il validator enforce tzinfo is not None.
    """

    model_config = {"frozen": True, "extra": "forbid"}  # immutable, strict schema

    asset_id: Annotated[str, Field(min_length=1, description="Identificativo asset (match registry)")]
    asset_family: Annotated[AssetFamily, Field(description="Famiglia asset (D-21 + D-44)")]
    tag_id: Annotated[str, Field(min_length=1, description="Identificativo tag (match tag dict)")]
    timestamp_utc: Annotated[
        datetime,
        Field(description="Timestamp evento UTC tz-aware (A-004 — skew < 500ms)"),
    ]
    value: Annotated[
        float | None,
        Field(description="Valore sensore; None se NaN (disconnessione sensore A-002)"),
    ]
    unit: Annotated[str, Field(min_length=1, description="Unita' di misura (OPC-UA engineering unit)")]
    quality_code: Annotated[
        int,
        Field(ge=0, description="OPC-UA StatusCode (Good=0, errori = bit-field positivo)"),
    ]
    source: Annotated[
        Literal["live", "replay_cmapss", "replay_uci"],
        Field(description="Sorgente evento — 'live' per bridge OT (T-03-04-replay)"),
    ] = "live"
    server_received_ts: Annotated[
        datetime,
        Field(description="Timestamp ricezione lato bridge — tz-aware (Pitfall 7)"),
    ]

    @field_validator("timestamp_utc", "server_received_ts")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Impone che i timestamp siano timezone-aware (T-03-04-tz-naive, Pitfall 7).

        Raises:
            ValueError: Se datetime e' naive (tzinfo is None).
        """
        if v.tzinfo is None:
            raise ValueError(
                f"Il timestamp deve essere timezone-aware (tzinfo is not None), "
                f"trovato naive datetime: {v!r}. Usa datetime.now(UTC) o datetime(..., tzinfo=UTC)."
            )
        return v


class AuditEvent(BaseModel):
    """Evento di audit pubblicato su 'audit.ot.bridge' (OQ3).

    Immutabile (frozen=True). Solo ot-bridge pubblica su questo subject (OQ3 resolution).
    sim-textile NON pubblica audit events.

    Struttura: {ts, level, event_type, details} come da OQ3 contract.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    ts: Annotated[
        datetime,
        Field(description="Timestamp evento audit tz-aware"),
    ]
    level: Annotated[
        Literal["INFO", "WARN", "ERROR"],
        Field(description="Livello severita' audit"),
    ]
    event_type: Annotated[
        str,
        Field(min_length=1, description="Tipo evento (es. bridge_start, publish_failure, pool_exhaustion)"),
    ]
    details: Annotated[
        dict[str, str | int | float | bool],
        Field(description="Dettagli evento strutturati (no secrets, no DSN raw — T-03-04-secret-leak)"),
    ] = {}

    @field_validator("ts")
    @classmethod
    def validate_audit_timezone_aware(cls, v: datetime) -> datetime:
        """Impone timezone-aware su audit timestamp."""
        if v.tzinfo is None:
            raise ValueError(
                f"AuditEvent.ts deve essere timezone-aware, trovato naive: {v!r}."
            )
        return v
