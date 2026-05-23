"""APScheduler ``AsyncIOScheduler`` wiring for the agents-scheduler service.

The single job ``anomaly-detector-scan`` fires on the cron expression
``ANOMALY_CRON`` (default ``*/5 * * * *``) and posts to the api-gateway via
:mod:`svc_agents_scheduler.client`.

Pitfall §5 mandates the following kwargs — they live here at the construction
site (not at the caller) so any future drift surfaces as a test failure (see
``tests/test_scheduler.py``):

* ``misfire_grace_time=300`` — 5-minute window for catch-up after a
  container restart.
* ``coalesce=True`` — collapse missed-run catch-ups into a single fire.
* ``max_instances=1`` — never overlap two scans (the api-gateway endpoint
  is idempotent but we still avoid the wasted work).
* ``id="anomaly-detector-scan"`` — stable id so re-adds replace rather
  than duplicate.

The container hosts exactly one job; if more arrive in the future, prefer
a separate ``add_job`` call rather than parameterising this builder
further — keeps the test assertions surgical.
"""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Callable, Mapping
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

_log = structlog.get_logger("agents-scheduler.scheduler")

#: Stable job id — re-adding via the same id replaces in-place.
JOB_ID: str = "anomaly-detector-scan"

#: Misfire grace window in seconds (Pitfall §5).
MISFIRE_GRACE_TIME: int = 300


def build_scheduler(
    *,
    cron: str,
    fn: Callable[..., Any],
    kwargs: Mapping[str, Any],
) -> AsyncIOScheduler:
    """Build an ``AsyncIOScheduler`` with the single anomaly-detector-scan job.

    Parameters
    ----------
    cron:
        Cron expression parsed by ``CronTrigger.from_crontab`` (UTC tz).
    fn:
        Coroutine (or sync callable) invoked on each fire.
    kwargs:
        Keyword arguments forwarded to ``fn`` at fire time.

    Returns
    -------
    AsyncIOScheduler
        Scheduler with the job registered but **not yet started**. Caller
        is responsible for ``sched.start()`` inside a running event loop.
    """
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(
        fn,
        trigger=CronTrigger.from_crontab(cron),
        kwargs=dict(kwargs),
        id=JOB_ID,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=MISFIRE_GRACE_TIME,
        replace_existing=True,
    )
    return sched


async def run_until_signal(sched: AsyncIOScheduler) -> None:
    """Block until SIGINT/SIGTERM, then shut the scheduler down cleanly.

    ``shutdown(wait=True)`` lets the current job complete before the process
    exits — required so an in-flight ``trigger_anomaly_scan`` finishes its
    POST and the api-gateway has a chance to record the audit row.
    """
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover — non-Unix
            _log.warning("signal_handler_unsupported", signal=int(sig))
    _log.info("scheduler_running")
    await stop.wait()
    _log.info("scheduler_shutdown_begin")
    sched.shutdown(wait=True)
    _log.info("scheduler_shutdown_done")


__all__ = ["JOB_ID", "MISFIRE_GRACE_TIME", "build_scheduler", "run_until_signal"]
