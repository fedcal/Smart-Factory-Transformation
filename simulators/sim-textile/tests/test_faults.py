"""Test delle pure functions di fault injection (IOT-03).

Tutti i test sono deterministici grazie al fixture random_seed_42 (autouse).
Test: apply_jitter, apply_drift (immutabilita'), maybe_nan, check_alarm_storm, apply_burst.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest

from sim_textile.faults import (
    apply_burst,
    apply_drift,
    apply_jitter,
    check_alarm_storm,
    maybe_nan,
)
from sim_textile.models import EmitterState


class TestApplyJitter:
    """Test 1: apply_jitter ritorna valore nel range atteso."""

    def test_apply_jitter_in_range(self) -> None:
        """apply_jitter(100.0, band_pct=10) ritorna valore in [90, 110]."""
        result = apply_jitter(100.0, band_pct=10)
        assert 90.0 <= result <= 110.0, f"Jitter fuori range: {result}"

    def test_apply_jitter_deterministic_with_seed(self) -> None:
        """Con random.seed(42), apply_jitter e' deterministica."""
        import random

        random.seed(42)
        r1 = apply_jitter(100.0, band_pct=10)
        random.seed(42)
        r2 = apply_jitter(100.0, band_pct=10)
        assert r1 == r2

    def test_apply_jitter_zero_band(self) -> None:
        """Con band_pct=0, il valore non cambia."""
        result = apply_jitter(50.0, band_pct=0)
        assert result == 50.0

    def test_apply_jitter_proportional(self) -> None:
        """Band_pct scala proporzionalmente al valore."""
        result = apply_jitter(200.0, band_pct=5)
        assert 190.0 <= result <= 210.0


class TestApplyDrift:
    """Test 2-3: apply_drift aggiorna drift_accumulated e non muta stato originale."""

    def test_apply_drift_accumulates(self) -> None:
        """apply_drift con rate=0.5/h e dt=3600s accumula 0.5."""
        state = EmitterState(drift_accumulated=0.0)
        new_state, drift_val = apply_drift(state, rate_per_hour=0.5, dt_seconds=3600.0)
        assert new_state.drift_accumulated == pytest.approx(0.5)
        assert drift_val == pytest.approx(0.5)

    def test_apply_drift_immutability(self) -> None:
        """apply_drift non muta lo stato originale (frozen dataclass — Test 3)."""
        state = EmitterState(drift_accumulated=0.0)
        original_drift = state.drift_accumulated
        apply_drift(state, rate_per_hour=0.5, dt_seconds=3600.0)
        # Stato originale deve essere invariato
        assert state.drift_accumulated == original_drift

    def test_apply_drift_half_hour(self) -> None:
        """rate=1.0/h × 1800s = 0.5 drift."""
        state = EmitterState(drift_accumulated=0.0)
        new_state, _ = apply_drift(state, rate_per_hour=1.0, dt_seconds=1800.0)
        assert new_state.drift_accumulated == pytest.approx(0.5)

    def test_apply_drift_cumulative(self) -> None:
        """Drift si accumula su chiamate successive."""
        state = EmitterState(drift_accumulated=0.0)
        state, _ = apply_drift(state, rate_per_hour=1.0, dt_seconds=1800.0)
        state, _ = apply_drift(state, rate_per_hour=1.0, dt_seconds=1800.0)
        assert state.drift_accumulated == pytest.approx(1.0)


class TestMaybeNan:
    """Test 4: maybe_nan rispetta probabilita' 0 e 1."""

    def test_zero_probability_never_nan(self) -> None:
        """maybe_nan(1.0, 0.0) ritorna sempre 1.0 (Test 4a)."""
        for _ in range(100):
            result = maybe_nan(1.0, 0.0)
            assert result == 1.0
            assert not math.isnan(result)

    def test_unit_probability_always_nan(self) -> None:
        """maybe_nan(1.0, 1.0) ritorna sempre NaN (Test 4b)."""
        for _ in range(100):
            result = maybe_nan(1.0, 1.0)
            assert math.isnan(result)

    def test_partial_probability(self) -> None:
        """maybe_nan con probabilita' intermedia ritorna mix NaN/valore."""
        import random

        random.seed(42)
        results = [maybe_nan(1.0, 0.5) for _ in range(100)]
        nan_count = sum(1 for r in results if math.isnan(r))
        # Con seed=42 e p=0.5, ci aspettiamo ~50% NaN (range 20-80 per sicurezza)
        assert 20 <= nan_count <= 80


class TestCheckAlarmStorm:
    """Test 5-6: check_alarm_storm triggers e prune eventi vecchi."""

    def test_alarm_storm_triggers(self) -> None:
        """Dopo threshold chiamate consecutive, is_storm == True (Test 5)."""
        state = EmitterState()
        base_time = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)
        threshold = 5
        # Chiamate ravvicinate (stessa finestra)
        for i in range(threshold - 1):
            now = base_time + timedelta(seconds=i * 0.1)
            state, is_storm = check_alarm_storm(state, now, threshold=threshold, window_s=30.0)
            assert not is_storm, f"Storm attivata troppo presto al passo {i}"
        # Chiamata threshold-esima attiva storm
        now = base_time + timedelta(seconds=(threshold - 1) * 0.1)
        state, is_storm = check_alarm_storm(state, now, threshold=threshold, window_s=30.0)
        assert is_storm

    def test_alarm_storm_prune_old_events(self) -> None:
        """Eventi piu' vecchi di window_s non contano (Test 6)."""
        state = EmitterState()
        base_time = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)
        # Aggiungi threshold-1 eventi vecchi (> window_s fa)
        threshold = 5
        window_s = 30.0
        for i in range(threshold - 1):
            old_time = base_time + timedelta(seconds=i)
            state, _ = check_alarm_storm(state, old_time, threshold=threshold, window_s=window_s)
        # Avanza il tempo di oltre window_s — eventi vecchi devono essere prunati
        future_time = base_time + timedelta(seconds=window_s + 10)
        state, is_storm = check_alarm_storm(state, future_time, threshold=threshold, window_s=window_s)
        # Solo 1 evento nella finestra (quello appena aggiunto), storm NON deve scattare
        assert not is_storm

    def test_alarm_storm_immutability(self) -> None:
        """check_alarm_storm non muta lo stato originale."""
        state = EmitterState()
        original_alarms = state.recent_alarms
        now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)
        check_alarm_storm(state, now, threshold=5)
        assert state.recent_alarms == original_alarms


class TestApplyBurst:
    """Test 7: apply_burst amplifica il valore durante il burst."""

    def test_apply_burst_amplifies(self) -> None:
        """apply_burst(10, magnitude_pct=200, t_in_burst=1, duration_s=2) amplifica (Test 7)."""
        result = apply_burst(base_value=10.0, magnitude_pct=200.0, t_in_burst=1.0, duration_s=2.0)
        # t=1 su duration=2: decay_factor=0.5, quindi valore = 10 * (1 + 2.0 * 0.5) = 20
        assert result == pytest.approx(20.0)

    def test_apply_burst_full_at_start(self) -> None:
        """A t_in_burst=0, l'ampiezza e' massima."""
        result = apply_burst(base_value=10.0, magnitude_pct=100.0, t_in_burst=0.0, duration_s=5.0)
        assert result == pytest.approx(20.0)

    def test_apply_burst_zero_at_end(self) -> None:
        """A t_in_burst=duration_s, l'ampiezza decade a zero (decay_factor=0)."""
        result = apply_burst(base_value=10.0, magnitude_pct=100.0, t_in_burst=5.0, duration_s=5.0)
        assert result == pytest.approx(10.0)

    def test_apply_burst_no_change_outside(self) -> None:
        """Fuori dal burst (t > duration_s) il valore non cambia."""
        result = apply_burst(base_value=10.0, magnitude_pct=200.0, t_in_burst=10.0, duration_s=5.0)
        assert result == pytest.approx(10.0)
