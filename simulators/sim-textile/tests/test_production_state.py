"""Test per ProductionState — dye_lot_id rotation (plan 06-09, D-QI-04).

Verifica:
    - test_initial_dye_lot_id_format               formato iniziale matches regex
    - test_maybe_rotate_no_rotation_before_interval  no-op prima dell'intervallo
    - test_maybe_rotate_rotation_after_interval    rotation dopo intervallo
    - test_rotation_idempotent_within_interval_after_rotation  doppio rotate -> 1 cambio
    - test_seq_token_uses_secrets_module           token hex varies tra rotazioni
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import pytest

DYE_LOT_REGEX = re.compile(r"^DL-[A-Z0-9-]+-\d{8}-[0-9a-f]+$")


@pytest.fixture
def t0() -> datetime:
    """Istante iniziale UTC tz-aware deterministico."""
    return datetime(2026, 5, 23, 12, 0, 0, tzinfo=UTC)


def test_initial_dye_lot_id_format(t0: datetime) -> None:
    """ProductionState.bootstrap genera dye_lot_id che matcha il regex D-QI-04."""
    from sim_textile.production_state import ProductionState

    state = ProductionState.bootstrap(asset_id="LOOM-01", now=t0)
    assert DYE_LOT_REGEX.match(state.current_dye_lot_id), (
        f"dye_lot_id {state.current_dye_lot_id!r} non matcha {DYE_LOT_REGEX.pattern}"
    )
    # Verifica componenti specifici
    assert state.current_dye_lot_id.startswith("DL-LOOM-01-20260523-")


def test_maybe_rotate_no_rotation_before_interval(t0: datetime) -> None:
    """maybe_rotate(now) con now < _last_rotation + rotation_interval => False, dye_lot invariato."""
    from sim_textile.production_state import ProductionState

    state = ProductionState.bootstrap(asset_id="LOOM-01", now=t0)
    original = state.current_dye_lot_id

    rotated = state.maybe_rotate(t0 + timedelta(minutes=30))
    assert rotated is False
    assert state.current_dye_lot_id == original


def test_maybe_rotate_rotation_after_interval(t0: datetime) -> None:
    """maybe_rotate(now) con now >= _last_rotation + interval => True, dye_lot cambia."""
    from sim_textile.production_state import ProductionState

    state = ProductionState.bootstrap(asset_id="LOOM-01", now=t0)
    original = state.current_dye_lot_id

    rotated = state.maybe_rotate(t0 + timedelta(minutes=61))
    assert rotated is True
    assert state.current_dye_lot_id != original
    assert DYE_LOT_REGEX.match(state.current_dye_lot_id)


def test_rotation_idempotent_within_interval_after_rotation(t0: datetime) -> None:
    """Dopo una rotazione, chiamare maybe_rotate immediatamente => False."""
    from sim_textile.production_state import ProductionState

    state = ProductionState.bootstrap(asset_id="LOOM-01", now=t0)
    rotation_time = t0 + timedelta(minutes=61)

    first = state.maybe_rotate(rotation_time)
    assert first is True
    after_first = state.current_dye_lot_id

    # Immediatamente dopo la rotazione (delta = 1 secondo) => nessun cambio
    second = state.maybe_rotate(rotation_time + timedelta(seconds=1))
    assert second is False
    assert state.current_dye_lot_id == after_first


def test_seq_token_uses_secrets_module(t0: datetime) -> None:
    """Il seq token e' 4 hex chars e varia tra rotazioni consecutive (no caching)."""
    from sim_textile.production_state import ProductionState

    state = ProductionState.bootstrap(asset_id="LOOM-01", now=t0)
    tokens: set[str] = set()
    tokens.add(state.current_dye_lot_id.split("-")[-1])

    # Esegui 5 rotazioni consecutive
    now = t0
    for _ in range(5):
        now = now + timedelta(minutes=61)
        rotated = state.maybe_rotate(now)
        assert rotated is True
        seq = state.current_dye_lot_id.split("-")[-1]
        assert len(seq) == 4, f"seq lunghezza {len(seq)} != 4: {seq!r}"
        assert re.match(r"^[0-9a-f]{4}$", seq), f"seq {seq!r} non e' hex 4-char"
        tokens.add(seq)

    # secrets.token_hex e' high-entropy => 6 token devono essere quasi sempre distinti.
    # Soglia conservativa: almeno 4 distinti su 6 (collisione 4-char hex e' ~1/65536).
    assert len(tokens) >= 4, f"Token poco variabili: {tokens}"


def test_dye_lot_id_changes_date_when_crossing_midnight(t0: datetime) -> None:
    """Se la rotazione attraversa la mezzanotte, la parte YYYYMMDD cambia."""
    from sim_textile.production_state import ProductionState

    # Inizializza a 23:30 del 2026-05-23
    late_night = datetime(2026, 5, 23, 23, 30, 0, tzinfo=UTC)
    state = ProductionState.bootstrap(asset_id="LOOM-01", now=late_night)
    assert "20260523" in state.current_dye_lot_id

    # Rotazione alle 00:35 del 2026-05-24 => 65 min dopo
    next_day = late_night + timedelta(minutes=65)
    rotated = state.maybe_rotate(next_day)
    assert rotated is True
    assert "20260524" in state.current_dye_lot_id
