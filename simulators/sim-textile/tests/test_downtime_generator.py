"""Test per downtime_event_generator — NATS publish + DowntimeEvent payload (plan 07-05).

Strategia: mock di `nats.aio.client.Client` (AsyncMock con `.publish`); non avviamo
un broker reale. Mirror diretto di test_quality_generator.py (Phase 6 06-09).

Test coprono:
    - DowntimeEvent Pydantic invariants (frozen, extra=forbid, tz-aware,
      severity Literal, duration_min>=0, JSON round-trip).
    - subject NATS `maintenance.downtime.<asset_id>` (D-DA-01).
    - reason_code drawn from failure_modes.yaml maintenance taxonomy
      (MNT-05 / D-MNT-TAX) filtered per family.
    - per-asset RNG isolation + determinism (seed reproducibility).
    - rate-limit nominal (<= 2 events/min default).
    - asyncio.CancelledError handling (Pattern S-6 inherited).
    - severity distribution (most events 'minor', few 'critical').
    - asset con family non-supportata (no maintenance taxonomy) => no events,
      no crash (skip + log).
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from sft_assets._models import Asset, AssetFamily, Tag


def _make_asset(asset_id: str, family: AssetFamily) -> Asset:
    """Build a minimal valid Asset for tests (mirror test_quality_generator.py)."""
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


def _make_faulted_profile(family: str = "loom") -> Any:
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


# ---------------------------------------------------------------------------
# DowntimeEvent Pydantic invariants
# ---------------------------------------------------------------------------


def test_downtime_event_is_frozen_and_extra_forbid() -> None:
    """DowntimeEvent frozen + extra=forbid (D-DA-01)."""
    from pydantic import ValidationError

    from sim_textile.downtime_event_generator import DowntimeEvent

    event = DowntimeEvent(
        event_id="00000000-0000-4000-8000-000000000001",
        asset_id="LOOM-01",
        reason_code="WEAVING-BE-001",
        duration_min=30,
        severity="minor",
        work_order_id=None,
        dye_lot_id=None,
        source="simulator",
        timestamp=datetime.now(UTC),
    )
    # frozen: mutation must raise (Pydantic v2 raises ValidationError)
    with pytest.raises(ValidationError):
        event.duration_min = 99  # type: ignore[misc]

    # extra=forbid: unknown fields must raise at construction time
    with pytest.raises(ValidationError):
        DowntimeEvent(
            event_id="00000000-0000-4000-8000-000000000002",
            asset_id="LOOM-01",
            reason_code="WEAVING-BE-001",
            duration_min=10,
            severity="minor",
            work_order_id=None,
            dye_lot_id=None,
            source="simulator",
            timestamp=datetime.now(UTC),
            unexpected_field="x",  # type: ignore[call-arg]
        )


def test_downtime_event_rejects_naive_datetime() -> None:
    """DowntimeEvent timestamp must be tz-aware (Pattern S-6, T-V7-naive-datetime)."""
    from pydantic import ValidationError

    from sim_textile.downtime_event_generator import DowntimeEvent

    naive = datetime(2026, 5, 23, 12, 0, 0)  # no tzinfo
    with pytest.raises(ValidationError):
        DowntimeEvent(
            event_id="00000000-0000-4000-8000-000000000003",
            asset_id="LOOM-01",
            reason_code="WEAVING-BE-001",
            duration_min=10,
            severity="minor",
            work_order_id=None,
            dye_lot_id=None,
            source="simulator",
            timestamp=naive,
        )


def test_downtime_event_severity_literal() -> None:
    """severity must be one of {minor, major, critical}."""
    from pydantic import ValidationError

    from sim_textile.downtime_event_generator import DowntimeEvent

    with pytest.raises(ValidationError):
        DowntimeEvent(
            event_id="00000000-0000-4000-8000-000000000004",
            asset_id="LOOM-01",
            reason_code="WEAVING-BE-001",
            duration_min=10,
            severity="catastrophic",  # type: ignore[arg-type]
            work_order_id=None,
            dye_lot_id=None,
            source="simulator",
            timestamp=datetime.now(UTC),
        )


def test_downtime_event_duration_min_ge_zero() -> None:
    """duration_min must be >= 0."""
    from pydantic import ValidationError

    from sim_textile.downtime_event_generator import DowntimeEvent

    with pytest.raises(ValidationError):
        DowntimeEvent(
            event_id="00000000-0000-4000-8000-000000000005",
            asset_id="LOOM-01",
            reason_code="WEAVING-BE-001",
            duration_min=-1,
            severity="minor",
            work_order_id=None,
            dye_lot_id=None,
            source="simulator",
            timestamp=datetime.now(UTC),
        )


def test_downtime_event_json_roundtrip() -> None:
    """model_dump_json → json.loads → model_validate roundtrip equality."""
    from sim_textile.downtime_event_generator import DowntimeEvent

    original = DowntimeEvent(
        event_id="11111111-1111-4111-8111-111111111111",
        asset_id="LOOM-01",
        reason_code="WEAVING-BE-001",
        duration_min=30,
        severity="major",
        work_order_id="WO-2026-0001",
        dye_lot_id="DL-LOOM-01-20260523-abcd",
        source="simulator",
        timestamp=datetime(2026, 5, 23, 12, 0, 0, tzinfo=UTC),
    )
    payload = original.model_dump_json()
    parsed = json.loads(payload)
    revived = DowntimeEvent.model_validate(parsed)
    assert revived == original


# ---------------------------------------------------------------------------
# DowntimeEventGenerator: NATS publish + reason_code taxonomy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publishes_to_correct_subject() -> None:
    """Generator pubblica su NATS subject `maintenance.downtime.<asset_id>`."""
    from sim_textile.downtime_event_generator import downtime_event_emitter

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    task = asyncio.create_task(
        downtime_event_emitter(
            asset, profile, nc, time_scale=1000.0, emit_probability=1.0
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
    assert subjects == {"maintenance.downtime.LOOM-01"}, (
        f"subjects inattesi: {subjects}"
    )


@pytest.mark.asyncio
async def test_payload_validates_as_downtime_event() -> None:
    """Payload pubblicato e' JSON valido di DowntimeEvent con source='simulator'."""
    from sim_textile.downtime_event_generator import (
        DowntimeEvent,
        downtime_event_emitter,
    )

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    task = asyncio.create_task(
        downtime_event_emitter(
            asset, profile, nc, time_scale=1000.0, emit_probability=1.0
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
    event = DowntimeEvent.model_validate_json(payload_bytes)
    assert event.source == "simulator"
    assert event.asset_id == "LOOM-01"
    assert event.timestamp.tzinfo is not None
    # ensure tz-aware
    assert event.timestamp.utcoffset() is not None


@pytest.mark.asyncio
async def test_reason_code_drawn_from_failure_modes_taxonomy() -> None:
    """reason_code emesso e' uno dei codici della failure_modes.yaml maintenance taxonomy per la family."""
    from sft_domain.failure_modes import load_failure_modes

    from sim_textile.downtime_event_generator import (
        DowntimeEvent,
        downtime_event_emitter,
    )

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    task = asyncio.create_task(
        downtime_event_emitter(
            asset, profile, nc, time_scale=1000.0, emit_probability=1.0
        )
    )
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert nc.publish.await_count >= 1

    # Build expected reason_code set: tutte le FailureMode con maintenance!=None
    # la cui asset_families include "weaving" (mapping LOOM -> weaving).
    fms = load_failure_modes()
    expected_codes = {
        fm.maintenance.reason_code
        for fm in fms
        if fm.maintenance is not None and "weaving" in fm.asset_families
    }
    assert expected_codes, "Taxonomy weaving deve contenere almeno 1 reason_code"

    for call in nc.publish.await_args_list:
        event = DowntimeEvent.model_validate_json(call.args[1])
        assert event.reason_code in expected_codes, (
            f"reason_code {event.reason_code} non in taxonomy weaving {expected_codes}"
        )


@pytest.mark.asyncio
async def test_rate_limited_under_nominal() -> None:
    """Profile nominale + rate default => pochi eventi (downtime e' raro)."""
    from sim_textile.downtime_event_generator import downtime_event_emitter

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_nominal_profile("loom")

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    # time_scale=300 + 50ms wall => 15 sim-seconds; rate nominale 2/min => 0.5 attesi.
    task = asyncio.create_task(
        downtime_event_emitter(asset, profile, nc, time_scale=300.0)
    )
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Sotto nominale: <=5 eventi in 15 sim-seconds (limite 2/min => 0.5 attesi, +buffer)
    assert nc.publish.await_count <= 5, (
        f"Troppo rate sotto profilo nominale: {nc.publish.await_count}"
    )


@pytest.mark.asyncio
async def test_severity_distribution_skews_to_minor() -> None:
    """Su un sample grande: >=55% minor, <=25% critical (loose)."""
    from sim_textile.downtime_event_generator import (
        DowntimeEvent,
        downtime_event_emitter,
    )

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    # Sample ~200 eventi con emit_probability=1.0
    task = asyncio.create_task(
        downtime_event_emitter(
            asset, profile, nc, time_scale=1000.0, emit_probability=1.0
        )
    )
    await asyncio.sleep(0.4)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert nc.publish.await_count >= 50, (
        f"Campione insufficiente per validare distribution: {nc.publish.await_count}"
    )

    sev = Counter()
    for call in nc.publish.await_args_list:
        event = DowntimeEvent.model_validate_json(call.args[1])
        sev[event.severity] += 1
    total = sum(sev.values())
    ratio_minor = sev["minor"] / total
    ratio_critical = sev["critical"] / total
    assert ratio_minor >= 0.55, (
        f"minor ratio atteso >=55%, trovato {ratio_minor:.2%}: {dict(sev)}"
    )
    assert ratio_critical <= 0.25, (
        f"critical ratio atteso <=25%, trovato {ratio_critical:.2%}: {dict(sev)}"
    )


@pytest.mark.asyncio
async def test_cancellation_graceful() -> None:
    """asyncio.CancelledError esce pulito (re-raised come da Pattern S-6)."""
    from sim_textile.downtime_event_generator import downtime_event_emitter

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")
    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    task = asyncio.create_task(
        downtime_event_emitter(asset, profile, nc, time_scale=10.0)
    )
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_skip_when_family_has_no_maintenance_taxonomy() -> None:
    """Asset con family priva di maintenance entries => 0 publish, no crash."""
    from sim_textile.downtime_event_generator import downtime_event_emitter

    # FINISHING family ha 0 entries in failure_modes.yaml maintenance taxonomy.
    asset = _make_asset("FIN-01", AssetFamily.FINISHING)
    profile = _make_faulted_profile("finishing")

    nc = AsyncMock()
    nc.publish = AsyncMock(return_value=None)

    task = asyncio.create_task(
        downtime_event_emitter(
            asset, profile, nc, time_scale=1000.0, emit_probability=1.0
        )
    )
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert nc.publish.await_count == 0, (
        f"FINISHING family non ha taxonomy => non deve emettere; emessi: "
        f"{nc.publish.await_count}"
    )


@pytest.mark.asyncio
async def test_per_asset_rng_determinism() -> None:
    """Due run del medesimo asset producono identica sequenza reason_code (per-asset seed)."""
    from sim_textile.downtime_event_generator import (
        DowntimeEvent,
        downtime_event_emitter,
    )

    asset = _make_asset("LOOM-01", AssetFamily.LOOM)
    profile = _make_faulted_profile("loom")

    async def _run() -> list[str]:
        nc = AsyncMock()
        nc.publish = AsyncMock(return_value=None)
        task = asyncio.create_task(
            downtime_event_emitter(
                asset, profile, nc, time_scale=1000.0, emit_probability=1.0
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return [
            DowntimeEvent.model_validate_json(call.args[1]).reason_code
            for call in nc.publish.await_args_list
        ]

    seq_a = await _run()
    seq_b = await _run()
    # Stesso asset_id => seed identico => prefisso comune (almeno i primi N).
    n = min(len(seq_a), len(seq_b), 5)
    assert n > 0, "Test richiede almeno 1 evento generato per validare determinism"
    assert seq_a[:n] == seq_b[:n], (
        f"Sequenze non deterministiche: {seq_a[:n]} vs {seq_b[:n]}"
    )
