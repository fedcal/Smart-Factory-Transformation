"""Shared pytest fixtures per i test di sim-textile.

Fornisce:
    sample_fault_profile_dict   — dict valido per FaultProfile (loom)
    sample_invalid_profile_dict — dict non valido: nan_probability fuori range
    frozen_time                 — datetime tz-aware fissa per test deterministici
    random_seed_42              — seed random deterministico per test fault (autouse)
"""

from __future__ import annotations

import random
from datetime import UTC, datetime

import pytest


@pytest.fixture(autouse=True)
def random_seed_42() -> None:
    """Imposta random.seed(42) prima di ogni test per determinismo dei fault functions."""
    random.seed(42)


@pytest.fixture
def frozen_time() -> datetime:
    """Restituisce un datetime tz-aware fisso per test deterministici (Pattern S-6)."""
    return datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def sample_fault_profile_dict() -> dict:
    """Restituisce un dict valido per FaultProfile (loom) — per test loader + validation."""
    return {
        "asset_family": "loom",
        "sample_rate_hz": 10.0,
        "fault_injection": {
            "nan_probability": 0.001,
            "drift": {
                "enabled": True,
                "rate_per_hour": 0.005,
                "affected_tags": ["creel_speed"],
            },
            "jitter": {
                "enabled": True,
                "band_pct": 5.0,
                "affected_tags": ["warp_tension"],
            },
            "burst_noise": {
                "enabled": False,
            },
            "alarm_storm": {
                "enabled": True,
                "threshold_events": 50,
                "window_s": 30.0,
                "affected_tags": ["broken_pick_count"],
            },
        },
        "default_baseline": {
            "warp_tension": {"value": 25.0, "unit": "N"},
            "pick_density": {"value": 24.0, "unit": "picks_per_cm"},
            "creel_speed": {"value": 850.0, "unit": "rpm"},
            "broken_pick_count": {"value": 0.0, "unit": "count"},
            "loom_temperature": {"value": 32.0, "unit": "degC"},
        },
    }


@pytest.fixture
def sample_invalid_profile_dict() -> dict:
    """Restituisce un dict non valido: nan_probability > 1 (range violation)."""
    return {
        "asset_family": "loom",
        "sample_rate_hz": 10.0,
        "fault_injection": {
            "nan_probability": 1.5,  # INVALID: deve essere 0..1
            "drift": {"enabled": False},
            "jitter": {"enabled": False},
            "burst_noise": {"enabled": False},
            "alarm_storm": {"enabled": False},
        },
        "default_baseline": {
            "warp_tension": {"value": 25.0, "unit": "N"},
        },
    }
