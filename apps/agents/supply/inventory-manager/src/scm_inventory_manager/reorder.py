"""Reorder-point pure function for InventoryManager (SCM-01).

Pattern 6 from 09-RESEARCH.md — frozen dataclass, Decimal arithmetic,
fully synchronous, no LLM, no asyncpg.

Contract:
    - is_below_threshold == (current_qty < reorder_point) — strictly less than
    - deficit_qty == max(0, reorder_point - current_qty) — Decimal arithmetic
    - estimated_cost_eur == reorder_qty * unit_cost_eur — exact Decimal product
    - All qty/cost fields are Decimal, not float
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ReorderSignal:
    """Frozen result of check_reorder() — all qty/cost fields are Decimal.

    Fields:
        sku_id:              SKU identifier.
        current_qty:         Latest inventory quantity (Decimal).
        reorder_point:       Configured reorder threshold (Decimal).
        reorder_qty:         Fixed order quantity from sku_master (Decimal).
        lead_time_days:      Supplier lead time in days.
        is_below_threshold:  True iff current_qty < reorder_point (strictly).
        deficit_qty:         max(0, reorder_point - current_qty) in Decimal.
        estimated_cost_eur:  reorder_qty * unit_cost_eur in Decimal.
    """

    sku_id: str
    current_qty: Decimal
    reorder_point: Decimal
    reorder_qty: Decimal
    lead_time_days: int
    is_below_threshold: bool
    deficit_qty: Decimal
    estimated_cost_eur: Decimal


def check_reorder(
    sku_id: str,
    current_qty: float,
    reorder_point: float,
    reorder_qty: float,
    unit_cost_eur: float,
    lead_time_days: int = 7,
) -> ReorderSignal:
    """Check if a SKU needs reordering (pure function, no side effects).

    All arithmetic is done in Decimal to avoid floating-point rounding drift.
    The threshold check is strictly less-than (current_qty == reorder_point
    does NOT trigger a reorder).

    Args:
        sku_id:          SKU identifier string.
        current_qty:     Current inventory quantity (float from DB row).
        reorder_point:   Threshold below which reorder is triggered (float from sku_master).
        reorder_qty:     Fixed quantity to order (float from sku_master).
        unit_cost_eur:   Unit cost in EUR (float from sku_master).
        lead_time_days:  Supplier lead time in calendar days (default 7).

    Returns:
        ReorderSignal with all computed fields. is_below_threshold=True when
        a reorder should be initiated.
    """
    # Convert inputs to Decimal using str() to avoid float representation errors
    d_current = Decimal(str(current_qty))
    d_reorder_point = Decimal(str(reorder_point))
    d_reorder_qty = Decimal(str(reorder_qty))
    d_unit_cost = Decimal(str(unit_cost_eur))

    # Strictly less-than (boundary: equal is NOT below threshold)
    below = d_current < d_reorder_point

    # Deficit: how much below the threshold (zero when not below)
    deficit = max(Decimal("0"), d_reorder_point - d_current)

    # Estimated cost is always for the full reorder_qty, not just the deficit
    estimated_cost = d_reorder_qty * d_unit_cost

    return ReorderSignal(
        sku_id=sku_id,
        current_qty=d_current,
        reorder_point=d_reorder_point,
        reorder_qty=d_reorder_qty,
        lead_time_days=lead_time_days,
        is_below_threshold=below,
        deficit_qty=deficit,
        estimated_cost_eur=estimated_cost,
    )


__all__ = ["ReorderSignal", "check_reorder"]
