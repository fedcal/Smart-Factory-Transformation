"""Modelli Pydantic v2 per sft-tools replay loaders e query TimescaleDB.

Tutti i modelli sono frozen=True, extra="forbid" per immutabilita' e validazione stretta.
Timestamp UTC obbligatori via field_validator (RESEARCH §Pitfall 7).

CRITICAL: importa SOLO da `pydantic` (v2 native). NON usare compat shim LangChain
ne' il backport Pydantic v1 — Pitfall 5 (langchain-core 1.x e' Pydantic v2 native).

Decisioni implementate:
    D-46 (ReplayRecord schema unificato)
    OQ5 (target_asset_id optional override in ReplayCMAPSSArgs)
    T-03-02-pydantic (frozen + extra=forbid + tz-aware validator)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

UTC = timezone.utc


class ReplayRecord(BaseModel):
    """Schema unificato output per replay loaders (D-46).

    Immutabile (frozen=True) — crea nuovi oggetti invece di mutare quelli esistenti.
    Extra fields sono vietati (extra="forbid") per validazione stretta.
    timestamp deve essere tz-aware UTC (RESEARCH §Pitfall 7).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    asset_id: Annotated[str, Field(min_length=1, description="Asset ID canonico (es. LOOM-01)")]
    timestamp: Annotated[datetime, Field(description="Timestamp UTC tz-aware (obbligatorio)")]
    sensor_id: Annotated[str, Field(min_length=1, description="ID sensore (es. sensor_2)")]
    value: Annotated[float, Field(description="Valore misurato")]
    unit: Annotated[str, Field(min_length=1, description="Unita' di misura (es. raw, N, celsius)")]
    source_dataset: Annotated[
        Literal["cmapss", "uci"],
        Field(description="Dataset sorgente: 'cmapss' o 'uci'"),
    ]
    source_unit: Annotated[
        str,
        Field(min_length=1, description="Identificatore originale nel dataset sorgente"),
    ]

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_have_timezone(cls, v: datetime) -> datetime:
        """Verifica che il timestamp sia tz-aware (tzinfo is not None).

        Raises:
            ValueError: Se il timestamp non ha timezone info (naive datetime).
        """
        if v.tzinfo is None:
            raise ValueError(
                f"timestamp deve essere tz-aware UTC, ricevuto naive datetime: {v!r}. "
                "Usa datetime(year, month, day, tzinfo=timezone.utc) oppure "
                "datetime(...).replace(tzinfo=timezone.utc)."
            )
        return v


class ReplayCMAPSSArgs(BaseModel):
    """Args schema per ReplayCMAPSSTool (Pydantic v2 native, BaseTool.args_schema).

    OQ5 resolution: target_asset_id e' opzionale — se None, mapping deterministic-hash
    unit_id → asset_id via sft-assets registry.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    unit_id: Annotated[
        int,
        Field(ge=1, le=260, description="C-MAPSS engine unit ID (1..260, across FD001..FD004)"),
    ]
    dataset: Annotated[
        Literal["FD001", "FD002", "FD003", "FD004"],
        Field(default="FD001", description="C-MAPSS sub-dataset (Phase 3: FD001 only; FD002-04 deferred Phase 7)"),
    ] = "FD001"
    time_range: Annotated[
        tuple[datetime, datetime] | None,
        Field(default=None, description="Intervallo UTC opzionale; None = tutta la traiettoria"),
    ] = None
    sensor_subset: Annotated[
        list[str] | None,
        Field(default=None, description="Sottoinsieme dei 21 sensori (sensor_1..sensor_21); None = tutti"),
    ] = None
    target_asset_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Override esplicito asset_id output (OQ5). Se None, "
                        "usa deterministic-hash unit_id → sft-assets registry.",
        ),
    ] = None


class ReplayUCIArgs(BaseModel):
    """Args schema per ReplayUCITool (Pydantic v2 native, BaseTool.args_schema)."""

    model_config = {"frozen": True, "extra": "forbid"}

    dataset: Annotated[
        Literal["air_quality", "energy", "production"],
        Field(description="UCI Manufacturing dataset variant"),
    ]
    asset_id: Annotated[
        str,
        Field(min_length=1, description="Asset ID di destinazione (nessun auto-mapping — richiesto esplicito)"),
    ]
    time_range: Annotated[
        tuple[datetime, datetime] | None,
        Field(default=None, description="Intervallo UTC opzionale; None = tutti i record"),
    ] = None


class QueryTimescaleArgs(BaseModel):
    """Args schema per QueryTimescaleTool (Pydantic v2 native, BaseTool.args_schema).

    Tutti i timestamp devono essere tz-aware (RESEARCH §Pitfall 7).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    asset_id: Annotated[
        str,
        Field(min_length=1, description="Asset ID da interrogare (es. LOOM-01)"),
    ]
    time_range: Annotated[
        tuple[datetime, datetime],
        Field(description="Intervallo UTC [start, end] (entrambi tz-aware obbligatori)"),
    ]
    tags: Annotated[
        list[str] | None,
        Field(default=None, description="Lista tag_id da filtrare; None = tutti i tag"),
    ] = None

    @field_validator("time_range")
    @classmethod
    def time_range_must_be_tz_aware(cls, v: tuple[datetime, datetime]) -> tuple[datetime, datetime]:
        """Verifica che entrambi i timestamp del time_range siano tz-aware."""
        start, end = v
        if start.tzinfo is None:
            raise ValueError(
                f"time_range[0] (start) deve essere tz-aware UTC, ricevuto naive: {start!r}"
            )
        if end.tzinfo is None:
            raise ValueError(
                f"time_range[1] (end) deve essere tz-aware UTC, ricevuto naive: {end!r}"
            )
        return v
