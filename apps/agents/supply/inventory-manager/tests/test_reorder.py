"""Contract tests for InventoryManager reorder-point pure function (SCM-01).

CONTRACT: check_reorder() deterministic pure function:
  - is_below_threshold = True when current_qty < reorder_point
  - deficit_qty = max(0, reorder_point - current_qty) — Decimal arithmetic
  - estimated_cost_eur = reorder_qty * unit_cost_eur — exact Decimal
  - No LLM involved; no asyncpg; fully synchronous.

Implementation target: scm_inventory_manager.reorder.check_reorder
(Wave 2-3 plan: 09-02)
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from scm_inventory_manager.reorder import check_reorder, ReorderSignal


# ---------------------------------------------------------------------------
# is_below_threshold contract
# ---------------------------------------------------------------------------


def test_is_below_threshold_true_when_current_qty_below_reorder_point() -> None:
    """check_reorder: current_qty=300 < reorder_point=850 → is_below_threshold=True (SCM-01)."""
    signal = check_reorder(
        sku_id="SKU-YARN-NE20-BLU",
        current_qty=300.0,
        reorder_point=850.0,
        reorder_qty=500.0,
        unit_cost_eur=3.20,
    )
    assert signal.is_below_threshold is True


def test_is_below_threshold_false_when_current_qty_above_reorder_point() -> None:
    """check_reorder: current_qty=1000 >= reorder_point=850 → is_below_threshold=False (SCM-01)."""
    signal = check_reorder(
        sku_id="SKU-YARN-NE20-BLU",
        current_qty=1000.0,
        reorder_point=850.0,
        reorder_qty=500.0,
        unit_cost_eur=3.20,
    )
    assert signal.is_below_threshold is False


def test_is_below_threshold_false_when_qty_equals_reorder_point() -> None:
    """check_reorder: current_qty == reorder_point → is_below_threshold=False (boundary, SCM-01).

    Boundary: strictly less than, not less-than-or-equal.
    """
    signal = check_reorder(
        sku_id="SKU-YARN-NE20-BLU",
        current_qty=850.0,
        reorder_point=850.0,
        reorder_qty=500.0,
        unit_cost_eur=3.20,
    )
    assert signal.is_below_threshold is False


# ---------------------------------------------------------------------------
# deficit_qty contract
# ---------------------------------------------------------------------------


def test_deficit_qty_is_max_zero_reorder_point_minus_current() -> None:
    """check_reorder: deficit_qty = max(0, reorder_point - current_qty) — Decimal (SCM-01).

    Example: reorder_point=850, current_qty=300 → deficit_qty=Decimal('550.0')
    """
    signal = check_reorder(
        sku_id="SKU-YARN-NE20-BLU",
        current_qty=300.0,
        reorder_point=850.0,
        reorder_qty=500.0,
        unit_cost_eur=3.20,
    )
    assert signal.deficit_qty == Decimal("550.0")
    assert isinstance(signal.deficit_qty, Decimal)


def test_deficit_qty_is_zero_when_not_below_threshold() -> None:
    """check_reorder: deficit_qty=0 when current_qty >= reorder_point (SCM-01)."""
    signal = check_reorder(
        sku_id="SKU-YARN-NE20-BLU",
        current_qty=1000.0,
        reorder_point=850.0,
        reorder_qty=500.0,
        unit_cost_eur=3.20,
    )
    assert signal.deficit_qty == Decimal("0")
    assert isinstance(signal.deficit_qty, Decimal)


# ---------------------------------------------------------------------------
# estimated_cost_eur contract
# ---------------------------------------------------------------------------


def test_estimated_cost_eur_equals_reorder_qty_times_unit_cost() -> None:
    """check_reorder: estimated_cost_eur = reorder_qty * unit_cost_eur — exact Decimal (SCM-01).

    Example: reorder_qty=500 kg, unit_cost_eur=3.20 EUR/kg → estimated_cost_eur=Decimal('1600.00')
    """
    signal = check_reorder(
        sku_id="SKU-YARN-NE20-BLU",
        current_qty=300.0,
        reorder_point=850.0,
        reorder_qty=500.0,
        unit_cost_eur=3.20,
    )
    assert signal.estimated_cost_eur == Decimal("1600.00")
    assert isinstance(signal.estimated_cost_eur, Decimal)


def test_estimated_cost_eur_uses_reorder_qty_regardless_of_deficit() -> None:
    """check_reorder: estimated_cost_eur uses reorder_qty (not deficit_qty) (SCM-01).

    Even when below threshold, the cost is for the full reorder_qty, not the deficit.
    """
    signal_below = check_reorder(
        sku_id="SKU-YARN-NE20-BLU",
        current_qty=300.0,
        reorder_point=850.0,
        reorder_qty=500.0,
        unit_cost_eur=3.20,
    )
    signal_above = check_reorder(
        sku_id="SKU-YARN-NE20-BLU",
        current_qty=1000.0,
        reorder_point=850.0,
        reorder_qty=500.0,
        unit_cost_eur=3.20,
    )
    # Cost is always reorder_qty * unit_cost_eur — same regardless of threshold
    assert signal_below.estimated_cost_eur == Decimal("1600.00")
    assert signal_above.estimated_cost_eur == Decimal("1600.00")


# ---------------------------------------------------------------------------
# Return type contract
# ---------------------------------------------------------------------------


def test_check_reorder_returns_frozen_dataclass_with_decimal_fields() -> None:
    """check_reorder: returns a frozen ReorderSignal dataclass with Decimal fields (SCM-01).

    Fields: sku_id (str), current_qty (Decimal), reorder_point (Decimal),
            reorder_qty (Decimal), lead_time_days (int), is_below_threshold (bool),
            deficit_qty (Decimal), estimated_cost_eur (Decimal).
    """
    signal = check_reorder(
        sku_id="SKU-YARN-NE20-BLU",
        current_qty=300.0,
        reorder_point=850.0,
        reorder_qty=500.0,
        unit_cost_eur=3.20,
        lead_time_days=7,
    )
    # Check return type
    assert isinstance(signal, ReorderSignal)

    # Check field types
    assert isinstance(signal.sku_id, str)
    assert isinstance(signal.current_qty, Decimal)
    assert isinstance(signal.reorder_point, Decimal)
    assert isinstance(signal.reorder_qty, Decimal)
    assert isinstance(signal.lead_time_days, int)
    assert isinstance(signal.is_below_threshold, bool)
    assert isinstance(signal.deficit_qty, Decimal)
    assert isinstance(signal.estimated_cost_eur, Decimal)

    # Check frozen: mutation must raise
    with pytest.raises((AttributeError, TypeError)):
        signal.sku_id = "changed"  # type: ignore[misc]
