"""Helper di vincoli per le euristiche SPT/EDD (RESEARCH §Pattern 5).

Funzioni helper utilizzate da `heuristic.py` per:
- determinare il primo slot disponibile per un ordine su un asset
- applicare setup-time (dye-lot changeover + failure mode setup_minutes)
- propagare la no-overlap invariant per asset

Pure functions — nessun side effect.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from sft_domain.failure_modes import FailureMode
from sft_domain.ops.schedule import AssetCapacity, OrderSpec, ScheduleDraftItem


def setup_minutes_for_transition(
    prev: ScheduleDraftItem | None,
    next_order: OrderSpec,
    cap: AssetCapacity,
    failure_modes: dict[str, FailureMode],
) -> int:
    """Calcola setup-time (in minuti) tra item precedente e nuovo ordine.

    Regole (RESEARCH §Pattern 5):
    1. Se non c'e' item precedente sull'asset → 0 setup.
    2. Se dye_lot_id cambia → max(failure_mode.setup_minutes, cap.dye_lot_changeover_minutes).
    3. Se dye_lot_id uguale → solo failure_mode.setup_minutes (puo' essere 0).
    """
    if prev is None:
        return 0
    fm = failure_modes.get(prev.asset_id)
    fm_setup = fm.setup_minutes if fm is not None else 0
    if prev.dye_lot_id != next_order.dye_lot_id:
        return max(fm_setup, cap.dye_lot_changeover_minutes)
    return fm_setup


def earliest_slot(
    timeline: Iterable[ScheduleDraftItem],
    order: OrderSpec,
    cap: AssetCapacity,
    failure_modes: dict[str, FailureMode],
    horizon_start: datetime,
) -> datetime:
    """Restituisce il primo `start_at` valido per `order` su `cap`.

    Considera:
        - horizon_start come earliest possible start
        - end_at + setup di TUTTI gli item gia' nella timeline
          (we take the latest as our candidate)

    NOTE: il timeline e' assunto append-only nell'ordine di scheduling;
    la funzione e' deterministica.
    """
    items = list(timeline)
    if not items:
        return horizon_start
    last = items[-1]
    setup = setup_minutes_for_transition(last, order, cap, failure_modes)
    candidate = last.end_at + timedelta(minutes=setup)
    return max(horizon_start, candidate)
