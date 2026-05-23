"""OrderSpec + AssetCapacity + ScheduleDraft + ScheduleDraftItem (D-PP-03).

`OrderSpec` rappresenta un ordine di produzione tessile.
`AssetCapacity` la capacita' di un asset specifico.
`ScheduleDraftItem` un'assegnazione (order → asset, [start, end]).
`ScheduleDraft` l'output completo di una strategia di scheduling.

Loader `load_orders()` + `load_asset_capacity()` lru_cached + yaml.safe_load
(T-V6-yaml-injection).
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from sft_domain.ops._validators import tz_aware
from sft_domain.ops.citation import RagCitation

# YAML files al package root (packages/sft-domain/<file>.yaml) per separare
# data fixture editoriali dal source code Python.
_PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
_ORDERS_PATH = _PACKAGE_ROOT / "orders.yaml"
_CAPACITY_PATH = _PACKAGE_ROOT / "asset_capacity.yaml"


class OrderSpec(BaseModel):
    """Ordine di produzione tessile (D-PP-03)."""

    model_config = {"frozen": True, "extra": "forbid"}

    order_id: Annotated[str, Field(min_length=1, description="Identificatore univoco ordine")]
    sku: Annotated[str, Field(min_length=1, description="Codice SKU prodotto")]
    quantity_meters: Annotated[float, Field(ge=0.0, description="Metri lineari richiesti (>=0)")]
    due_at: Annotated[datetime, Field(description="UTC tz-aware deadline consegna")]
    processing_minutes: Annotated[int, Field(gt=0, description="Minuti di processing stimati (>0)")]
    priority: Annotated[int, Field(default=0, description="Priorita' (default 0; alto = piu' urgente)")]
    compatible_families: Annotated[
        list[str],
        Field(
            min_length=1,
            description="Asset family compatibili (es. ['loom']); subset di asset_capacity.yaml",
        ),
    ]
    dye_lot_id: Annotated[
        str | None,
        Field(default=None, description="Dye-lot opzionale per scheduling changeover"),
    ]

    @field_validator("due_at")
    @classmethod
    def _tz(cls, v: datetime) -> datetime:
        return tz_aware(v)


class AssetCapacity(BaseModel):
    """Capacita' produttiva di un asset (D-PP-03)."""

    model_config = {"frozen": True, "extra": "forbid"}

    asset_id: Annotated[str, Field(min_length=1, description="asset_id (cross-ref sft-assets registry)")]
    asset_family: Annotated[str, Field(min_length=1, description="Famiglia asset")]
    max_meters_per_hour: Annotated[float, Field(gt=0.0, description="Throughput massimo (>0)")]
    max_concurrent_dye_lots: Annotated[
        int,
        Field(default=1, ge=1, description="Massimi dye-lot concorrenti (>=1)"),
    ]
    dye_lot_changeover_minutes: Annotated[
        int,
        Field(default=30, ge=0, description="Minuti di setup tra dye-lot differenti"),
    ]
    downtime_windows: Annotated[
        list[dict[str, Any]],
        Field(default_factory=list, description="Finestre di downtime pianificato"),
    ]


class ScheduleDraftItem(BaseModel):
    """Singola assegnazione order → asset in uno ScheduleDraft."""

    model_config = {"frozen": True, "extra": "forbid"}

    order_id: Annotated[str, Field(min_length=1, description="Order identifier")]
    asset_id: Annotated[str, Field(min_length=1, description="Asset assegnato")]
    start_at: Annotated[datetime, Field(description="UTC tz-aware start")]
    end_at: Annotated[datetime, Field(description="UTC tz-aware end (> start_at)")]
    dye_lot_id: Annotated[
        str | None,
        Field(default=None, description="Dye-lot eredita da OrderSpec"),
    ]
    sequence: Annotated[int, Field(ge=0, description="Sequence index nel draft")]

    @field_validator("start_at")
    @classmethod
    def _tz_start(cls, v: datetime) -> datetime:
        return tz_aware(v)

    @field_validator("end_at")
    @classmethod
    def _tz_end(cls, v: datetime) -> datetime:
        return tz_aware(v)

    @model_validator(mode="after")
    def _end_after_start(self) -> ScheduleDraftItem:
        if self.end_at <= self.start_at:
            raise ValueError(
                f"end_at ({self.end_at!r}) must be strictly greater than start_at ({self.start_at!r})"
            )
        return self


class ScheduleDraft(BaseModel):
    """Output di una strategia di scheduling (SPT, EDD, ...).

    `unscheduled_orders` surfaces gli ordini non collocabili nell'horizon
    (Pitfall §8 surface-gap). `rationale_md` + `citations` sono popolati
    dall'LLM post-scheduling (heuristic e' deterministica e pura).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    schedule_id: Annotated[UUID, Field(default_factory=uuid4, description="Identificatore univoco draft")]
    strategy: Annotated[Literal["spt", "edd"], Field(description="Strategia di scheduling")]
    horizon_start: Annotated[datetime, Field(description="UTC tz-aware inizio horizon")]
    horizon_end: Annotated[datetime, Field(description="UTC tz-aware fine horizon")]
    items: Annotated[
        list[ScheduleDraftItem],
        Field(description="Assegnazioni ordinate per sequence"),
    ]
    unscheduled_orders: Annotated[
        list[str],
        Field(default_factory=list, description="Order ID non collocati nell'horizon"),
    ]
    rationale_md: Annotated[
        str,
        Field(default="", description="Markdown rationale LLM (post-scheduling)"),
    ]
    citations: Annotated[
        list[RagCitation],
        Field(default_factory=list, description="Citazioni RAG a SOP/glossary"),
    ]
    created_at: Annotated[
        datetime,
        Field(default_factory=lambda: datetime.now(UTC), description="UTC tz-aware creation time"),
    ]

    @field_validator("horizon_start")
    @classmethod
    def _tz_start(cls, v: datetime) -> datetime:
        return tz_aware(v)

    @field_validator("horizon_end")
    @classmethod
    def _tz_end(cls, v: datetime) -> datetime:
        return tz_aware(v)

    @field_validator("created_at")
    @classmethod
    def _tz_created(cls, v: datetime) -> datetime:
        return tz_aware(v)


@lru_cache(maxsize=1)
def load_orders(path: pathlib.Path | None = None) -> tuple[OrderSpec, ...]:
    """Carica orders.yaml restituendo tuple di OrderSpec.

    Args:
        path: Override per test; default `packages/sft-domain/orders.yaml`.
    """
    yaml_path = path or _ORDERS_PATH
    if not yaml_path.exists():
        raise FileNotFoundError(f"orders.yaml non trovato: {yaml_path}")
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "orders" not in raw:
        raise ValueError(
            f"orders.yaml deve contenere chiave 'orders', trovato: {type(raw).__name__}"
        )
    entries = raw["orders"]
    if not isinstance(entries, list):
        raise ValueError(f"'orders' deve essere lista, trovato: {type(entries).__name__}")
    return tuple(OrderSpec.model_validate(e) for e in entries)


@lru_cache(maxsize=1)
def load_asset_capacity(path: pathlib.Path | None = None) -> dict[str, AssetCapacity]:
    """Carica asset_capacity.yaml restituendo dict keyed da asset_id."""
    yaml_path = path or _CAPACITY_PATH
    if not yaml_path.exists():
        raise FileNotFoundError(f"asset_capacity.yaml non trovato: {yaml_path}")
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "asset_capacity" not in raw:
        raise ValueError(
            f"asset_capacity.yaml deve contenere chiave 'asset_capacity', "
            f"trovato: {type(raw).__name__}"
        )
    entries = raw["asset_capacity"]
    if not isinstance(entries, list):
        raise ValueError(f"'asset_capacity' deve essere lista, trovato: {type(entries).__name__}")
    result: dict[str, AssetCapacity] = {}
    for e in entries:
        cap = AssetCapacity.model_validate(e)
        result[cap.asset_id] = cap
    return result


def invalidate_orders_cache() -> None:
    load_orders.cache_clear()


def invalidate_capacity_cache() -> None:
    load_asset_capacity.cache_clear()
