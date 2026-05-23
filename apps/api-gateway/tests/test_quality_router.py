"""Unit tests for POST /v1/quality/events (Plan 06-12 Task 1 — RED phase).

Covers:
    1. test_post_quality_event_valid_returns_202
    2. test_post_quality_event_bad_dye_lot_id_422
    3. test_post_quality_event_forces_source_operator
    4. test_post_quality_event_idempotency_key_cached
    5. test_post_quality_event_unknown_defect_type_422

All tests use the `app_with_mocks`/`client` fixtures from conftest.py.
The mock NATS publisher is wired on `app.state.nats_publisher` (an
`AuditNatsPublisher` shape) — we monkey-patch its ``publish_raw`` because the
new ``/v1/quality/events`` route publishes to the bespoke
``quality.events.<asset_id>`` subject (D-QI-01 — operator-side ingest).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest


UTC = timezone.utc

_VALID_BODY = {
    "asset_id": "LOOM-01",
    "dye_lot_id": "DL-LOOMA-20260518-7ab9",
    "defect_type": "broken_end",
    "defect_length_inches": 2.5,
    "full_width": False,
    "position_meters": 12.3,
    "timestamp": datetime(2026, 5, 18, 12, 0, tzinfo=UTC).isoformat(),
}


@pytest.mark.asyncio
async def test_post_quality_event_valid_returns_202(
    client, app_with_mocks
) -> None:
    pub = app_with_mocks.state.nats_publisher
    pub.publish_raw = AsyncMock(return_value=None)

    response = await client.post("/v1/quality/events", json=_VALID_BODY)
    assert response.status_code == 202, response.text

    # Body envelope.
    body = response.json()
    assert body["accepted"] is True
    assert "event_id" in body

    # NATS publish-raw called exactly once with the asset-id subject.
    assert pub.publish_raw.await_count == 1
    subject, payload = pub.publish_raw.call_args.args
    assert subject == "quality.events.LOOM-01"
    # Payload is bytes, JSON-encoded QualityEvent.
    import json

    decoded = json.loads(payload.decode("utf-8"))
    assert decoded["asset_id"] == "LOOM-01"
    assert decoded["source"] == "operator"


@pytest.mark.asyncio
async def test_post_quality_event_bad_dye_lot_id_422(client, app_with_mocks) -> None:
    pub = app_with_mocks.state.nats_publisher
    pub.publish_raw = AsyncMock(return_value=None)

    bad = {**_VALID_BODY, "dye_lot_id": "not-a-dyelot"}
    response = await client.post("/v1/quality/events", json=bad)
    assert response.status_code == 422, response.text
    # Must NOT publish on validation failure.
    assert pub.publish_raw.await_count == 0


@pytest.mark.asyncio
async def test_post_quality_event_forces_source_operator(
    client, app_with_mocks
) -> None:
    """Server overrides any caller-supplied source value to 'operator' (T-V6-source-spoof)."""
    pub = app_with_mocks.state.nats_publisher
    pub.publish_raw = AsyncMock(return_value=None)

    # The request schema *forbids* `source` (extra=forbid via the dedicated
    # operator-request shape); 422 means the spoof attempt was rejected at the
    # validation boundary BEFORE reaching the publish step.
    spoofed = {**_VALID_BODY, "source": "simulator"}
    response = await client.post("/v1/quality/events", json=spoofed)
    assert response.status_code == 422, response.text
    assert pub.publish_raw.await_count == 0

    # And a clean body (no source key) still publishes with source=operator.
    response = await client.post("/v1/quality/events", json=_VALID_BODY)
    assert response.status_code == 202, response.text
    import json

    _, payload = pub.publish_raw.call_args.args
    decoded = json.loads(payload.decode("utf-8"))
    assert decoded["source"] == "operator"


@pytest.mark.asyncio
async def test_post_quality_event_idempotency_key_cached(
    client, app_with_mocks
) -> None:
    pub = app_with_mocks.state.nats_publisher
    pub.publish_raw = AsyncMock(return_value=None)

    headers = {"Idempotency-Key": "qe-replay-1"}
    r1 = await client.post("/v1/quality/events", json=_VALID_BODY, headers=headers)
    assert r1.status_code == 202, r1.text

    r2 = await client.post("/v1/quality/events", json=_VALID_BODY, headers=headers)
    assert r2.status_code == 202, r2.text

    # Same body envelope — including the stable server-generated event_id.
    assert r1.json() == r2.json()
    # Only ONE publish across the two calls (idempotent).
    assert pub.publish_raw.await_count == 1


@pytest.mark.asyncio
async def test_post_quality_event_unknown_defect_type_422(
    client, app_with_mocks
) -> None:
    pub = app_with_mocks.state.nats_publisher
    pub.publish_raw = AsyncMock(return_value=None)

    bad = {**_VALID_BODY, "defect_type": "purple_unicorn"}
    response = await client.post("/v1/quality/events", json=bad)
    assert response.status_code == 422, response.text
    assert pub.publish_raw.await_count == 0
