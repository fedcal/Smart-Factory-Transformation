"""Tests for svc_agents_scheduler.scheduler module (Plan 06-11).

RED-phase target: assert APScheduler ``AsyncIOScheduler.add_job`` is called
with the exact set of flags mandated by Pitfall §5 (single-instance + misfire
recovery + coalesce) and the constant ``id="anomaly-detector-scan"``.
"""

from __future__ import annotations

import signal
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# build_scheduler — add_job inspection
# ---------------------------------------------------------------------------


def test_add_job_uses_cron_trigger() -> None:
    """add_job receives a CronTrigger built from the supplied crontab string."""
    from apscheduler.triggers.cron import CronTrigger

    from svc_agents_scheduler.scheduler import build_scheduler

    fn = MagicMock()
    sched = build_scheduler(cron="*/5 * * * *", fn=fn, kwargs={"x": 1})
    # APScheduler exposes the registered job; introspect its trigger.
    jobs = sched.get_jobs()
    assert len(jobs) == 1
    assert isinstance(jobs[0].trigger, CronTrigger)


def test_add_job_misfire_grace_time_300() -> None:
    """misfire_grace_time=300s catches up after container restart (Pitfall §5)."""
    from svc_agents_scheduler.scheduler import build_scheduler

    fn = MagicMock()
    sched = build_scheduler(cron="*/5 * * * *", fn=fn, kwargs={})
    job = sched.get_jobs()[0]
    assert job.misfire_grace_time == 300


def test_add_job_coalesce_true() -> None:
    """coalesce=True collapses missed-run catch-ups into a single fire."""
    from svc_agents_scheduler.scheduler import build_scheduler

    fn = MagicMock()
    sched = build_scheduler(cron="*/5 * * * *", fn=fn, kwargs={})
    job = sched.get_jobs()[0]
    assert job.coalesce is True


def test_add_job_max_instances_1() -> None:
    """max_instances=1 prevents overlap if a scan runs long."""
    from svc_agents_scheduler.scheduler import build_scheduler

    fn = MagicMock()
    sched = build_scheduler(cron="*/5 * * * *", fn=fn, kwargs={})
    job = sched.get_jobs()[0]
    assert job.max_instances == 1


def test_add_job_id_anomaly_detector_scan() -> None:
    """Job id must be stable so re-adds replace rather than duplicate."""
    from svc_agents_scheduler.scheduler import build_scheduler

    fn = MagicMock()
    sched = build_scheduler(cron="*/5 * * * *", fn=fn, kwargs={})
    job = sched.get_jobs()[0]
    assert job.id == "anomaly-detector-scan"


@pytest.mark.asyncio
async def test_shutdown_on_sigint() -> None:
    """run_until_signal installs SIGINT/SIGTERM handlers and calls shutdown(wait=True)."""
    from svc_agents_scheduler.scheduler import run_until_signal

    sched = MagicMock()
    sched.shutdown = MagicMock()

    # Patch asyncio.Event so wait() returns immediately
    with patch("svc_agents_scheduler.scheduler.asyncio.Event") as ev_cls:
        ev = MagicMock()

        async def _wait() -> None:
            return None

        ev.wait = _wait
        ev.set = MagicMock()
        ev_cls.return_value = ev

        # Patch loop.add_signal_handler — we don't actually want to trap signals
        with patch("svc_agents_scheduler.scheduler.asyncio.get_running_loop") as gl:
            loop = MagicMock()
            loop.add_signal_handler = MagicMock()
            gl.return_value = loop

            await run_until_signal(sched)

            # Confirm SIGINT + SIGTERM handlers registered
            registered = {c.args[0] for c in loop.add_signal_handler.call_args_list}
            assert signal.SIGINT in registered
            assert signal.SIGTERM in registered

    sched.shutdown.assert_called_once_with(wait=True)
