"""Container entrypoint for the agents-scheduler service.

Wiring:

    1. Configure structlog JSON output (shared pattern with knowledge-ingest
       and ot-bridge so log aggregation downstream stays uniform).
    2. Read env (fail-fast on missing ``API_GATEWAY_URL``).
    3. Build the AsyncIOScheduler with the single anomaly-detector-scan job.
    4. Hold the event loop open until SIGINT/SIGTERM, then shut down cleanly.

Env vars:
    API_GATEWAY_URL          REQUIRED — e.g. ``http://api-gateway:8081``
    ANOMALY_WINDOW_MINUTES   default 15 — forwarded into the JSON body
    ANOMALY_CRON             default ``"*/5 * * * *"`` — UTC cron expression
"""

from __future__ import annotations

import asyncio
import os
import sys

import structlog

from svc_agents_scheduler.client import build_http_client, trigger_anomaly_scan
from svc_agents_scheduler.scheduler import build_scheduler, run_until_signal


def _configure_logging() -> None:
    """Shared structlog JSON setup (mirrors ot-bridge main.py + Pattern 6)."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


def _require_env(name: str) -> str:
    """Fail-fast read of a required env var — exits with rc=2 if missing."""
    value = os.environ.get(name)
    if not value:
        # structlog might not be configured yet on early exit; write to stderr.
        print(
            f'{{"event":"missing_env","level":"error","var":"{name}"}}',
            file=sys.stderr,
        )
        raise SystemExit(2)
    return value


async def main() -> None:
    """Async entrypoint — schedules the job, awaits a stop signal, shuts down."""
    log = structlog.get_logger("agents-scheduler")

    gateway_url = _require_env("API_GATEWAY_URL")
    window_minutes = int(os.environ.get("ANOMALY_WINDOW_MINUTES", "15"))
    cron = os.environ.get("ANOMALY_CRON", "*/5 * * * *")

    log.info(
        "scheduler_starting",
        gateway_url=gateway_url,
        window_minutes=window_minutes,
        cron=cron,
    )

    # Share one keep-warm AsyncClient across all cron fires.
    async with build_http_client() as http_client:

        async def _fire(gateway_url: str, window_minutes: int) -> None:
            try:
                await trigger_anomaly_scan(
                    gateway_url=gateway_url,
                    window_minutes=window_minutes,
                    client=http_client,
                )
            except Exception as exc:  # noqa: BLE001 — log + continue, never crash
                log.error(
                    "scheduler_invoke_failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        sched = build_scheduler(
            cron=cron,
            fn=_fire,
            kwargs={
                "gateway_url": gateway_url,
                "window_minutes": window_minutes,
            },
        )
        sched.start()
        log.info("scheduler_started", cron=cron, window_minutes=window_minutes)
        await run_until_signal(sched)


def main_cli() -> None:
    """Sync wrapper used by the ``agents-scheduler`` console script."""
    _configure_logging()
    asyncio.run(main())


if __name__ == "__main__":
    main_cli()
