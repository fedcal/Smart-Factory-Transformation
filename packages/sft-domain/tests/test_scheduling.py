"""Test delle euristiche di scheduling SPT/EDD (D-PP-03 + RESEARCH §Pattern 5).

Copre:
- SPT ordina per processing_minutes ascendente
- EDD ordina per due_at ascendente
- Nessuna sovrapposizione per asset (invariant)
- Dye-lot changeover applicato come setup gap
- setup_minutes da failure mode rispettato
- Ordini non collocabili nell'horizon surfaceati in unscheduled_orders
- Determinismo: stessi input -> stessi items (UUID schedule_id stabile via hash)
- SPT vs EDD differiscono quando processing-time e due-date sono in ordine inverso
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sft_domain.failure_modes import FailureMode
from sft_domain.ops.schedule import AssetCapacity, OrderSpec, ScheduleDraft
from sft_domain.scheduling import schedule_edd, schedule_spt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _utc(hour: int = 8, day: int = 23) -> datetime:
    return datetime(2026, 5, day, hour, tzinfo=UTC)


def _order(
    order_id: str,
    processing_minutes: int,
    due_at: datetime,
    *,
    dye_lot_id: str | None = None,
    compatible_families: list[str] | None = None,
) -> OrderSpec:
    return OrderSpec(
        order_id=order_id,
        sku=f"SKU-{order_id}",
        quantity_meters=500.0,
        due_at=due_at,
        processing_minutes=processing_minutes,
        priority=0,
        compatible_families=compatible_families or ["loom"],
        dye_lot_id=dye_lot_id,
    )


def _capacity(
    asset_id: str = "LOOM-01",
    asset_family: str = "loom",
    *,
    dye_lot_changeover_minutes: int = 30,
) -> dict[str, AssetCapacity]:
    return {
        asset_id: AssetCapacity(
            asset_id=asset_id,
            asset_family=asset_family,
            max_meters_per_hour=300.0,
            max_concurrent_dye_lots=1,
            dye_lot_changeover_minutes=dye_lot_changeover_minutes,
        )
    }


def _failure_modes() -> dict[str, FailureMode]:
    return {}


HORIZON_START = _utc(6)
HORIZON_END = _utc(6, day=25)  # 48h horizon


# ===========================================================================
# SPT — Shortest Processing Time
# ===========================================================================


def test_spt_orders_by_processing_minutes() -> None:
    """Given 3 orders [60, 30, 90], SPT items sequence is [30, 60, 90]."""
    o1 = _order("O-1", 60, _utc(20))
    o2 = _order("O-2", 30, _utc(20))
    o3 = _order("O-3", 90, _utc(20))
    draft = schedule_spt(
        [o1, o2, o3], _capacity(), _failure_modes(), HORIZON_START, HORIZON_END
    )
    durations = [
        int((it.end_at - it.start_at).total_seconds() // 60) for it in draft.items
    ]
    assert durations == [30, 60, 90]


# ===========================================================================
# EDD — Earliest Due Date
# ===========================================================================


def test_edd_orders_by_due_at() -> None:
    """3 orders with due_at = +6h, +2h, +4h → EDD items in 2h, 4h, 6h order."""
    o1 = _order("O-1", 30, _utc(14))  # due +6h after horizon_start
    o2 = _order("O-2", 30, _utc(10))  # due +2h
    o3 = _order("O-3", 30, _utc(12))  # due +4h
    draft = schedule_edd(
        [o1, o2, o3], _capacity(), _failure_modes(), HORIZON_START, HORIZON_END
    )
    assert [it.order_id for it in draft.items] == ["O-2", "O-3", "O-1"]


# ===========================================================================
# No-overlap invariant
# ===========================================================================


def test_no_overlap_per_asset() -> None:
    """Items on same asset satisfy items[i].end_at <= items[j].start_at for i<j."""
    orders = [_order(f"O-{i}", 60, _utc(20)) for i in range(5)]
    draft = schedule_spt(
        orders, _capacity(), _failure_modes(), HORIZON_START, HORIZON_END
    )
    per_asset: dict[str, list] = {}
    for it in draft.items:
        per_asset.setdefault(it.asset_id, []).append(it)
    for items in per_asset.values():
        items.sort(key=lambda x: x.start_at)
        for prev, nxt in zip(items, items[1:]):
            assert prev.end_at <= nxt.start_at, (
                f"Overlap: {prev.order_id}.end_at={prev.end_at} > "
                f"{nxt.order_id}.start_at={nxt.start_at}"
            )


# ===========================================================================
# Dye-lot changeover
# ===========================================================================


def test_dye_lot_changeover_setup_applied() -> None:
    """Two consecutive orders with different dye_lot_id have gap >= changeover_minutes."""
    cap = _capacity(dye_lot_changeover_minutes=45)
    o1 = _order("O-1", 60, _utc(20), dye_lot_id="DL-LOOM-01-20260523-aa")
    o2 = _order("O-2", 60, _utc(20), dye_lot_id="DL-LOOM-01-20260523-bb")
    draft = schedule_spt(
        [o1, o2], cap, _failure_modes(), HORIZON_START, HORIZON_END
    )
    items = sorted(draft.items, key=lambda x: x.start_at)
    gap_minutes = (items[1].start_at - items[0].end_at).total_seconds() // 60
    assert gap_minutes >= 45, f"Expected >=45min gap for dye-lot changeover, got {gap_minutes}"


def test_no_changeover_when_same_dye_lot() -> None:
    """Two consecutive orders with same dye_lot_id have no setup gap."""
    cap = _capacity(dye_lot_changeover_minutes=45)
    o1 = _order("O-1", 60, _utc(20), dye_lot_id="DL-LOOM-01-20260523-aa")
    o2 = _order("O-2", 60, _utc(20), dye_lot_id="DL-LOOM-01-20260523-aa")
    draft = schedule_spt(
        [o1, o2], cap, _failure_modes(), HORIZON_START, HORIZON_END
    )
    items = sorted(draft.items, key=lambda x: x.start_at)
    gap_minutes = (items[1].start_at - items[0].end_at).total_seconds() // 60
    assert gap_minutes == 0


# ===========================================================================
# failure_modes setup_minutes
# ===========================================================================


def test_setup_minutes_from_failure_mode_applied() -> None:
    """Orders following a failure-mode-tagged asset get gap >= setup_minutes."""
    fm = FailureMode(
        id="broken_end",
        name_it="rottura filo",
        name_en="broken end",
        asset_families=["weaving"],
        parts=["warp"],
        hitl_tier="supervisor",
        setup_minutes=20,
    )
    failure_modes = {"LOOM-01": fm}
    o1 = _order("O-1", 60, _utc(20))
    o2 = _order("O-2", 60, _utc(20))
    draft = schedule_spt(
        [o1, o2], _capacity(), failure_modes, HORIZON_START, HORIZON_END
    )
    items = sorted(draft.items, key=lambda x: x.start_at)
    gap = (items[1].start_at - items[0].end_at).total_seconds() // 60
    assert gap >= 20, f"Expected >=20min setup gap from failure mode, got {gap}"


# ===========================================================================
# Unscheduled overflow
# ===========================================================================


def test_unscheduled_orders_surfaced() -> None:
    """When horizon too short, surplus orders go to unscheduled_orders."""
    short_horizon_end = HORIZON_START + timedelta(minutes=90)
    # 3 orders each 60min, but only 90min available → 1 fits, 2 overflow
    orders = [_order(f"O-{i}", 60, _utc(20)) for i in range(3)]
    draft = schedule_spt(
        orders, _capacity(), _failure_modes(), HORIZON_START, short_horizon_end
    )
    assert len(draft.unscheduled_orders) >= 1
    assert set(draft.unscheduled_orders).issubset({"O-0", "O-1", "O-2"})


def test_due_date_overflow_logged() -> None:
    """Order due before its end_at is still scheduled — no overdue blocking."""
    # Order due at horizon_start + 30min, but its processing is 60min
    o1 = _order("O-late", 60, HORIZON_START + timedelta(minutes=30))
    draft = schedule_spt(
        [o1], _capacity(), _failure_modes(), HORIZON_START, HORIZON_END
    )
    # Item still scheduled
    assert any(it.order_id == "O-late" for it in draft.items)


# ===========================================================================
# Determinism
# ===========================================================================


def test_determinism_items_identical() -> None:
    """Same inputs → identical items list (ignoring schedule_id UUID)."""
    orders = [_order(f"O-{i}", 30 + i * 10, _utc(20)) for i in range(5)]
    cap = _capacity()
    d1 = schedule_spt(orders, cap, _failure_modes(), HORIZON_START, HORIZON_END)
    d2 = schedule_spt(orders, cap, _failure_modes(), HORIZON_START, HORIZON_END)
    # Items immutable + deterministic
    items1 = [(it.order_id, it.asset_id, it.start_at, it.end_at) for it in d1.items]
    items2 = [(it.order_id, it.asset_id, it.start_at, it.end_at) for it in d2.items]
    assert items1 == items2


def test_deterministic_schedule_id() -> None:
    """Same inputs → same schedule_id (UUID derived from stable hash)."""
    orders = [_order(f"O-{i}", 30 + i * 10, _utc(20)) for i in range(3)]
    cap = _capacity()
    d1 = schedule_spt(orders, cap, _failure_modes(), HORIZON_START, HORIZON_END)
    d2 = schedule_spt(orders, cap, _failure_modes(), HORIZON_START, HORIZON_END)
    assert d1.schedule_id == d2.schedule_id


# ===========================================================================
# SPT vs EDD divergence
# ===========================================================================


def test_spt_vs_edd_differ_when_due_inverse_of_processing() -> None:
    """When longest processing has earliest due, SPT and EDD produce different sequences."""
    # O-long has the earliest due but longest processing
    o_long = _order("O-long", 120, _utc(10))  # 2h, due +4h
    o_med = _order("O-med", 60, _utc(14))  # 1h, due +8h
    o_short = _order("O-short", 30, _utc(18))  # 0.5h, due +12h
    orders = [o_long, o_med, o_short]
    cap = _capacity()
    spt = schedule_spt(orders, cap, _failure_modes(), HORIZON_START, HORIZON_END)
    edd = schedule_edd(orders, cap, _failure_modes(), HORIZON_START, HORIZON_END)
    spt_seq = [it.order_id for it in spt.items]
    edd_seq = [it.order_id for it in edd.items]
    assert spt_seq != edd_seq
    assert spt_seq[0] == "O-short"  # shortest first
    assert edd_seq[0] == "O-long"  # earliest due first


def test_returns_schedule_draft_instance() -> None:
    """schedule_spt returns a ScheduleDraft."""
    draft = schedule_spt([], _capacity(), _failure_modes(), HORIZON_START, HORIZON_END)
    assert isinstance(draft, ScheduleDraft)
    assert draft.strategy == "spt"
    assert draft.items == []


def test_edd_returns_strategy_edd() -> None:
    draft = schedule_edd([], _capacity(), _failure_modes(), HORIZON_START, HORIZON_END)
    assert draft.strategy == "edd"
