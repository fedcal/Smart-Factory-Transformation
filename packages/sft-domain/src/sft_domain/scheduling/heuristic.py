"""SPT/EDD euristiche pure-function (RESEARCH §Pattern 5).

`schedule_spt`: ordina per processing_minutes ascendente (Shortest Processing Time).
`schedule_edd`: ordina per due_at ascendente (Earliest Due Date).

Entrambe condividono il loop di assegnazione:
    for order in pending (sorted by strategy key):
        eligible = [a in capacity if a.asset_family in order.compatible_families]
        candidates = [(a, earliest_slot(timelines[a], order, cap, fm, h_start))
                      for a in eligible]
        asset, start = min(candidates, key=lambda x: x[1])
        end = start + timedelta(minutes=order.processing_minutes)
        if end > horizon_end: order goes to unscheduled_orders
        else: append ScheduleDraftItem to timeline + result.items

Determinismo (RESEARCH §Pattern 5 + plan 06-04 truths):
    schedule_id = UUID(hex=sha256("strategy|horizon_start|sorted(order_ids)")[:32])
    created_at = horizon_start (NON datetime.now(UTC) per garantire determinismo)
    Il tie-breaking nei sort e nei candidates usa un secondary key
    su order_id/asset_id (stable sort) per riproducibilita'.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Iterable
from uuid import UUID

from sft_domain.failure_modes import FailureMode
from sft_domain.ops.schedule import (
    AssetCapacity,
    OrderSpec,
    ScheduleDraft,
    ScheduleDraftItem,
)
from sft_domain.scheduling.constraints import earliest_slot


def _deterministic_schedule_id(
    strategy: str,
    horizon_start_iso: str,
    order_ids: Iterable[str],
) -> UUID:
    """UUID stabile dal hash sha256 di (strategy, horizon_start, sorted order_ids)."""
    sorted_ids = sorted(order_ids)
    payload = f"{strategy}|{horizon_start_iso}|{','.join(sorted_ids)}".encode("utf-8")
    digest_hex = hashlib.sha256(payload).hexdigest()[:32]
    return UUID(hex=digest_hex)


def _schedule(
    orders: list[OrderSpec],
    capacity: dict[str, AssetCapacity],
    failure_modes: dict[str, FailureMode],
    horizon_start,
    horizon_end,
    strategy: str,
) -> ScheduleDraft:
    """Loop di scheduling condiviso tra SPT e EDD."""
    # Pending list e' GIA' ordinata dal caller (SPT o EDD).
    # Timelines per asset — order matters (append solo).
    timelines: dict[str, list[ScheduleDraftItem]] = {a: [] for a in sorted(capacity.keys())}
    items: list[ScheduleDraftItem] = []
    unscheduled: list[str] = []
    seq = 0

    for order in orders:
        # Eligible assets: capacity.asset_family ∈ order.compatible_families.
        # Iteriamo in ordine deterministico (sorted by asset_id).
        eligible = [
            (asset_id, capacity[asset_id])
            for asset_id in sorted(capacity.keys())
            if capacity[asset_id].asset_family in order.compatible_families
        ]
        if not eligible:
            unscheduled.append(order.order_id)
            continue

        # Per ogni eligible asset, calcola earliest_slot. Tie-break su asset_id (stabile).
        candidates = [
            (asset_id, earliest_slot(timelines[asset_id], order, cap, failure_modes, horizon_start))
            for asset_id, cap in eligible
        ]
        # min su (start_at, asset_id) per determinismo
        asset_id, slot_start = min(candidates, key=lambda x: (x[1], x[0]))
        slot_end = slot_start + timedelta(minutes=order.processing_minutes)

        if slot_end > horizon_end:
            unscheduled.append(order.order_id)
            continue

        item = ScheduleDraftItem(
            order_id=order.order_id,
            asset_id=asset_id,
            start_at=slot_start,
            end_at=slot_end,
            dye_lot_id=order.dye_lot_id,
            sequence=seq,
        )
        timelines[asset_id].append(item)
        items.append(item)
        seq += 1

    schedule_id = _deterministic_schedule_id(
        strategy, horizon_start.isoformat(), (o.order_id for o in orders)
    )
    return ScheduleDraft(
        schedule_id=schedule_id,
        strategy=strategy,  # type: ignore[arg-type]
        horizon_start=horizon_start,
        horizon_end=horizon_end,
        items=items,
        unscheduled_orders=unscheduled,
        rationale_md="",  # LLM populates post-scheduling (production-planner agent)
        citations=[],
        created_at=horizon_start,  # deterministico — NON datetime.now(UTC)
    )


def schedule_spt(
    orders: list[OrderSpec],
    capacity: dict[str, AssetCapacity],
    failure_modes: dict[str, FailureMode],
    horizon_start,
    horizon_end,
) -> ScheduleDraft:
    """Shortest Processing Time first. Tie-break stabile su order_id."""
    pending = sorted(orders, key=lambda o: (o.processing_minutes, o.order_id))
    return _schedule(pending, capacity, failure_modes, horizon_start, horizon_end, "spt")


def schedule_edd(
    orders: list[OrderSpec],
    capacity: dict[str, AssetCapacity],
    failure_modes: dict[str, FailureMode],
    horizon_start,
    horizon_end,
) -> ScheduleDraft:
    """Earliest Due Date first. Tie-break stabile su order_id."""
    pending = sorted(orders, key=lambda o: (o.due_at, o.order_id))
    return _schedule(pending, capacity, failure_modes, horizon_start, horizon_end, "edd")
