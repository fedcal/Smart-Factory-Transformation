"""FastAPI lifespan — Plan 04-07 Task 1.

On startup:
    1. asyncpg pool (size 5-20, statement_cache_size=0 — Pitfall 6 for TimescaleDB)
    2. AuditNatsPublisher.connect()
    3. AsyncPostgresSaver via get_postgres_checkpointer (async context manager)
    4. AuditPgWriter + OutboxWriter + AuditWriter (dual-write orchestrator)
    5. ApprovalQueueWriter
    6. HybridRouter
    7. Compiled supervisor graph (build_supervisor_graph(checkpointer, router))
    8. Background tasks: OutboxRetry, EscalationSupervisor, Governor (asyncio.create_task)
    9. IdempotencyCache (in-memory, 5-min TTL)

On shutdown:
    1. Cancel + await background tasks (CancelledError-tolerant)
    2. NATS drain
    3. Pool close

Env vars:
    TIMESCALE_DSN  — REQUIRED (postgresql://user:pass@host:5432/db)
    NATS_URL       — default nats://localhost:4222
    POOL_MIN_SIZE  — default 5
    POOL_MAX_SIZE  — default 20

CORE-04 (success criterion #4): the AsyncPostgresSaver wraps an existing
``langgraph.checkpoint`` table populated by ``scripts/langgraph-init.py``
(Plan 04-02 BLOCKING task) — paused approvals survive a process restart.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import structlog
from fastapi import FastAPI

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: C901 — startup is necessarily wide
    """Construct + tear down all long-lived resources used by routers."""
    # Local imports keep cold-import time of the module low (only paid at boot).
    from sft_agents.audit import (  # noqa: PLC0415
        AuditNatsPublisher,
        AuditPgWriter,
        AuditWriter,
        OutboxRetry,
        OutboxWriter,
    )
    from sft_agents.hitl import ApprovalQueueWriter  # noqa: PLC0415
    from sft_agents.policies import HybridRouter  # noqa: PLC0415
    from sft_agents.runtime import (  # noqa: PLC0415
        build_supervisor_graph,
        get_postgres_checkpointer,
    )
    from sft_agents.runtime.escalation import EscalationSupervisor  # noqa: PLC0415
    from sft_agents.runtime.governor import Governor  # noqa: PLC0415

    from svc_api_gateway.idempotency import IdempotencyCache  # noqa: PLC0415

    dsn = os.environ.get("TIMESCALE_DSN")
    if not dsn:
        raise RuntimeError(
            "TIMESCALE_DSN env var is required "
            "(postgresql://user:pass@host:5432/db)"
        )
    nats_url = os.environ.get("NATS_URL", "nats://localhost:4222")
    pool_min = int(os.environ.get("POOL_MIN_SIZE", "5"))
    pool_max = int(os.environ.get("POOL_MAX_SIZE", "20"))

    logger.info(
        "api_gateway_starting",
        dsn_prefix=dsn[:24],
        nats_url=nats_url,
        pool_min=pool_min,
        pool_max=pool_max,
    )

    # 1) Pool — statement_cache_size=0 is REQUIRED for TimescaleDB hypertables
    #    (audit.actions is one; Pitfall 6 from Plan 04-02).
    pool = await asyncpg.create_pool(
        dsn,
        min_size=pool_min,
        max_size=pool_max,
        statement_cache_size=0,
        command_timeout=10.0,
    )

    # 2) NATS publisher.
    nats_publisher = AuditNatsPublisher(nats_url)
    await nats_publisher.connect()

    # 3) PG checkpointer — async context manager. We open it manually inside the
    #    lifespan so its lifetime spans the entire app lifetime, then close it
    #    on shutdown. Use the auto-setup path off by default — Plan 04-02
    #    BLOCKING task is the canonical migration runner.
    checkpointer_cm = get_postgres_checkpointer(dsn)
    saver = await checkpointer_cm.__aenter__()

    # 4) Audit writers (PG-first + NATS-async + outbox fallback).
    pg_writer = AuditPgWriter(pool)
    outbox_writer = OutboxWriter(pool)
    audit_writer = AuditWriter(pg_writer, nats_publisher, outbox_writer)

    # 5) Approval queue writer.
    queue_writer = ApprovalQueueWriter(pool)

    # 6) Hybrid router (Stage 1 rules only — Stage 2 LLM is not wired here per
    #    Plan 04-05; future cluster nodes can inject one).
    router = HybridRouter()

    # 7) Supervisor graph compiled with the PG checkpointer.
    supervisor_graph = build_supervisor_graph(checkpointer=saver, router=router)

    # 8) Background tasks.
    outbox_retry = OutboxRetry(pool, nats_publisher)
    escalator = EscalationSupervisor(
        pool=pool,
        audit_writer=audit_writer,
        nats_publisher=nats_publisher,
        queue_writer=queue_writer,
    )
    governor = Governor(
        pool=pool,
        audit_writer=audit_writer,
        nats_publisher=nats_publisher,
        queue_writer=queue_writer,
    )
    outbox_retry_task = asyncio.create_task(
        outbox_retry.run(), name="api-gateway.outbox-retry"
    )
    escalator_task = asyncio.create_task(
        escalator.run(), name="api-gateway.escalation-supervisor"
    )
    governor_task = asyncio.create_task(
        governor.run(), name="api-gateway.governor"
    )

    # 9) Wire app.state.
    app.state.pool = pool
    app.state.nats_publisher = nats_publisher
    app.state.checkpointer = saver
    app.state.audit_writer = audit_writer
    app.state.queue_writer = queue_writer
    app.state.router = router
    app.state.supervisor_graph = supervisor_graph
    app.state.outbox_retry = outbox_retry
    app.state.escalator = escalator
    app.state.governor = governor
    app.state.outbox_retry_task = outbox_retry_task
    app.state.escalator_task = escalator_task
    app.state.governor_task = governor_task
    app.state.idempotency_cache = IdempotencyCache(ttl_seconds=300)
    app.state._checkpointer_cm = checkpointer_cm  # private — for teardown

    logger.info("api_gateway_ready", background_tasks=3)

    try:
        yield
    finally:
        logger.info("api_gateway_stopping")

        # Cancel + await background tasks. Each task supports a graceful stop()
        # via shutdown_event; we call both for robustness.
        for stoppable, task, name in (
            (outbox_retry, outbox_retry_task, "outbox_retry"),
            (escalator, escalator_task, "escalator"),
            (governor, governor_task, "governor"),
        ):
            try:
                await stoppable.stop()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "background_task_stop_failed", task=name, error=str(exc)
                )
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "background_task_await_failed", task=name, error=str(exc)
                )

        # NATS drain (best-effort).
        try:
            await nats_publisher.drain()
        except Exception as exc:  # noqa: BLE001
            logger.warning("nats_drain_failed", error=str(exc))

        # Close checkpointer + pool.
        try:
            await checkpointer_cm.__aexit__(None, None, None)
        except Exception as exc:  # noqa: BLE001
            logger.warning("checkpointer_close_failed", error=str(exc))

        try:
            await pool.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("pool_close_failed", error=str(exc))

        logger.info("api_gateway_stopped")


__all__ = ["lifespan"]
