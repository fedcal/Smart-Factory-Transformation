"""Tests for svc_agents_scheduler.client module (Plan 06-11).

RED-phase target: assert ``trigger_anomaly_scan`` posts to the canonical
api-gateway URL with the agreed payload, uses retries=3 transport, and emits
the ``scheduler_invoked`` structlog event with the response status code.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_post_to_correct_url() -> None:
    """trigger_anomaly_scan posts to {gateway_url}/v1/agents/anomaly-detector/scan."""
    from svc_agents_scheduler.client import trigger_anomaly_scan

    response = MagicMock(status_code=202)
    client = MagicMock()
    client.post = AsyncMock(return_value=response)

    await trigger_anomaly_scan(
        gateway_url="http://api-gateway:8081",
        window_minutes=15,
        client=client,
    )

    args, kwargs = client.post.call_args
    assert args[0] == "http://api-gateway:8081/v1/agents/anomaly-detector/scan"


@pytest.mark.asyncio
async def test_post_body_contains_window_minutes_and_triggered_by() -> None:
    """Payload carries window_minutes + triggered_by='scheduler' (constant)."""
    from svc_agents_scheduler.client import trigger_anomaly_scan

    response = MagicMock(status_code=202)
    client = MagicMock()
    client.post = AsyncMock(return_value=response)

    await trigger_anomaly_scan(
        gateway_url="http://api-gateway:8081",
        window_minutes=15,
        client=client,
    )

    _, kwargs = client.post.call_args
    body = kwargs["json"]
    assert body["window_minutes"] == 15
    assert body["triggered_by"] == "scheduler"


def test_build_http_client_uses_retries_3_transport() -> None:
    """The default AsyncClient is built with AsyncHTTPTransport(retries=3)."""
    import httpx

    from svc_agents_scheduler.client import build_http_client

    with patch(
        "svc_agents_scheduler.client.httpx.AsyncHTTPTransport"
    ) as transport_cls:
        transport_cls.return_value = httpx.AsyncHTTPTransport()
        build_http_client()
        transport_cls.assert_called_once()
        _, kwargs = transport_cls.call_args
        assert kwargs.get("retries") == 3


@pytest.mark.asyncio
async def test_post_logs_status_code() -> None:
    """Successful post emits structlog event ``scheduler_invoked`` with status_code."""
    from svc_agents_scheduler import client as client_mod

    response = MagicMock(status_code=202)
    http_client = MagicMock()
    http_client.post = AsyncMock(return_value=response)

    events: list[tuple[str, dict]] = []

    class _Recorder:
        def info(self, event: str, **kwargs: object) -> None:
            events.append((event, dict(kwargs)))

        def bind(self, **_: object) -> "_Recorder":
            return self

    with patch.object(client_mod, "_log", _Recorder()):
        await client_mod.trigger_anomaly_scan(
            gateway_url="http://api-gateway:8081",
            window_minutes=15,
            client=http_client,
        )

    matched = [e for e in events if e[0] == "scheduler_invoked"]
    assert matched, f"missing scheduler_invoked event; got {events}"
    assert matched[0][1].get("status_code") == 202
