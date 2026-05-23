"""Test per quality_event_generator — NATS publish + QualityEvent payload (plan 06-09).

Strategia: mock di `nats.aio.client.Client` (AsyncMock con `.publish`); non avviamo
un broker reale. Test coprono:
    - test_publishes_to_correct_subject     subject `quality.events.<asset_id>`
    - test_payload_validates_as_quality_event  payload e' QualityEvent JSON valido
    - test_includes_current_dye_lot_id      event.dye_lot_id == production_state.current_dye_lot_id
    - test_rate_limited_under_nominal       <=5 events in 30 sim-seconds (sotto 10/min)
    - test_defect_type_biased_by_fault_profile  dyer asset => >=70% shade_deviation/unlevel_dyeing
    - test_full_width_field_present         payload sempre contiene `full_width` (default False)
"""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from sft_assets._models import Asset, AssetFamily, Tag


def _make_asset(asset_id: str, family: AssetFamily) -> Asset:
    """Build a minimal valid Asset for tests."""
    return Asset(
        asset_id=asset_id,
        asset_family=family,
        line_id="LINE-01",
        opcua_namespace=f"urn:mantis:{family.value}:{asset_id}",
        tags=(
            Tag(
                tag_id="warp_tension",
                unit="N",
                sample_rate_hz=10.0,
                semantic_type="tension",
            ),
        ),
        status="active",
    )


def _make_nominal_profile(family: str = "loom") -> Any:
    """Build a minimal nominal FaultProfile (no active faults)."""
    from sim_textile.models import FaultProfile

    return FaultProfile.model_validate(
        {
            "asset_family": family,
            "sample_rate_hz": 10.0,
            "fault_injection": {
                "nan_probability": 0.0,
                "drift": {"enabled": False},
                "jitter": {"enabled": False},
                "burst_noise": {"enabled": False},
                "alarm_storm": {"enabled": False},
            },
            "default_baseline": {
                "warp_tension": {"value": 25.0, "unit": "N"},
            },
        }
    )


def _make_faulted_profile(family: str = "dyeing") -> Any:
    """Build a faulted FaultProfile with drift active (proxy for stress condition)."""
    from sim_textile.models import FaultProfile

    return FaultProfile.model_validate(
        {
            "asset_family": family,
            "sample_rate_hz": 10.0,
            "fault_injection": {
                "nan_probability": 0.01,
                "drift": {
                    "enabled": True,
                    "rate_per_hour": 0.1,
                    "affected_tags": ["warp_tension"],
                },
                "jitter": {"enabled": False},
                "burst_noise": {"enabled": False},
                "alarm_storm": {"enabled": False},
            },
            "default_baseline": {
                "warp_tension": {"value": 25.0, "unit": "N"},
            },
        }
    )


@pytest.mark.asyncio
async def test_publishes_to_correct_subject() -> None:
    """Il generator pubblica su NATS subject `quality.events.<asset_id>`."""
    from sim_textile.production_state import ProductionState
    from sim_textile.quality_event_generator import quality_event_emitter

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")
    ps = ProductionState.bootstrap(asset_id=asset.asset_id, now=datetime.now(UTC))

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    # Forziamo emit_probability=1.0 per garantire emissione su ogni tick
    task = asyncio.create_task(
        quality_event_emitter(
            asset, profile, ps, nc, time_scale=1000.0, emit_probability=1.0
        )
    )
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert nc.publish.await_count >= 1
    subjects = {call.args[0] for call in nc.publish.await_args_list}
    assert subjects == {"quality.events.LOOM-01"}, f"subjects inattesi: {subjects}"


@pytest.mark.asyncio
async def test_payload_validates_as_quality_event() -> None:
    """Payload pubblicato e' JSON valido di QualityEvent con source='simulator'."""
    from sft_domain.ops.quality import QualityEvent

    from sim_textile.production_state import ProductionState
    from sim_textile.quality_event_generator import quality_event_emitter

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")
    ps = ProductionState.bootstrap(asset_id=asset.asset_id, now=datetime.now(UTC))

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    task = asyncio.create_task(
        quality_event_emitter(
            asset, profile, ps, nc, time_scale=1000.0, emit_probability=1.0
        )
    )
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert nc.publish.await_count >= 1
    payload_bytes = nc.publish.await_args_list[0].args[1]
    event = QualityEvent.model_validate_json(payload_bytes)
    assert event.source == "simulator"
    assert event.asset_id == "LOOM-01"


@pytest.mark.asyncio
async def test_includes_current_dye_lot_id() -> None:
    """L'event emesso include il dye_lot_id corrente della ProductionState."""
    from sft_domain.ops.quality import QualityEvent

    from sim_textile.production_state import ProductionState
    from sim_textile.quality_event_generator import quality_event_emitter

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")

    # Stato con dye_lot_id deterministico
    fixed_dye_lot = "DL-LOOM-01-20260523-abcd"
    ps = ProductionState(
        asset_id=asset.asset_id,
        current_dye_lot_id=fixed_dye_lot,
        _last_rotation=datetime.now(UTC),
    )

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    task = asyncio.create_task(
        quality_event_emitter(
            asset, profile, ps, nc, time_scale=1000.0, emit_probability=1.0
        )
    )
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert nc.publish.await_count >= 1
    payload_bytes = nc.publish.await_args_list[0].args[1]
    event = QualityEvent.model_validate_json(payload_bytes)
    assert event.dye_lot_id == fixed_dye_lot


@pytest.mark.asyncio
async def test_rate_limited_under_nominal() -> None:
    """Nominal profile + default rate => pochi eventi anche con time_scale alto."""
    from sim_textile.production_state import ProductionState
    from sim_textile.quality_event_generator import quality_event_emitter

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_nominal_profile("loom")
    ps = ProductionState.bootstrap(asset_id=asset.asset_id, now=datetime.now(UTC))

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    # 30 sim-seconds a time_scale=1.0 => 0.03 sim-seconds wall-time non utile.
    # Test: usiamo emit_probability_override=None (=> default) e attendiamo ~50ms.
    # Sotto profile nominale, emit_probability deve essere clamp <= ~10 events/min
    # Con dt = 0.1s e time_scale=300, 50ms wall => 15 sim-seconds => attesi <= 2.5 eventi.
    task = asyncio.create_task(
        quality_event_emitter(asset, profile, ps, nc, time_scale=300.0)
    )
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Sotto nominale: meno di 10 eventi in 15 sim-seconds (limite 10/min => ~2.5 attesi)
    assert nc.publish.await_count <= 10, (
        f"Troppo rate sotto profilo nominale: {nc.publish.await_count}"
    )


@pytest.mark.asyncio
async def test_defect_type_biased_by_fault_profile() -> None:
    """Asset dyeing => >= 70% degli eventi sono shade_deviation o unlevel_dyeing."""
    from sft_domain.ops.quality import QualityEvent

    from sim_textile.production_state import ProductionState
    from sim_textile.quality_event_generator import quality_event_emitter

    asset = _make_asset("DYER-01", AssetFamily.DYEING)
    profile = _make_faulted_profile("dyeing")
    ps = ProductionState.bootstrap(asset_id=asset.asset_id, now=datetime.now(UTC))

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    task = asyncio.create_task(
        quality_event_emitter(
            asset, profile, ps, nc, time_scale=1000.0, emit_probability=1.0
        )
    )
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert nc.publish.await_count >= 10, (
        f"Campione troppo piccolo per validare bias: {nc.publish.await_count}"
    )

    defects = Counter()
    for call in nc.publish.await_args_list:
        event = QualityEvent.model_validate_json(call.args[1])
        defects[event.defect_type] += 1

    total = sum(defects.values())
    dyer_defects = defects["shade_deviation"] + defects["unlevel_dyeing"]
    ratio = dyer_defects / total
    assert ratio >= 0.7, (
        f"Bias dyer atteso >=70% shade_deviation+unlevel_dyeing, "
        f"trovato {ratio:.2%} su {total} eventi: {dict(defects)}"
    )


@pytest.mark.asyncio
async def test_full_width_field_present() -> None:
    """Ogni event ha il campo `full_width` (bool, default False)."""
    from sft_domain.ops.quality import QualityEvent

    from sim_textile.production_state import ProductionState
    from sim_textile.quality_event_generator import quality_event_emitter

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")
    ps = ProductionState.bootstrap(asset_id=asset.asset_id, now=datetime.now(UTC))

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    task = asyncio.create_task(
        quality_event_emitter(
            asset, profile, ps, nc, time_scale=1000.0, emit_probability=1.0
        )
    )
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert nc.publish.await_count >= 1
    for call in nc.publish.await_args_list:
        event = QualityEvent.model_validate_json(call.args[1])
        assert isinstance(event.full_width, bool)
