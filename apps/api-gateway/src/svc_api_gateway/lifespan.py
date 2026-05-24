"""FastAPI lifespan — Plan 04-07 Task 1, extended Plan 08-08, Plan 09-06.

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
   10. Knowledge agent instances + knowledge_children dict (Plan 08-08, D-X-04)
   11. Supply agent instances + supply_children dict (Plan 09-06, D-X-04 pattern)

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

Plan 08-08 extension:
    Knowledge agent DI (D-X-04):
        knowledge_children = {
            'shift-handover':              ShiftHandover,
            'training-coach':              TrainingCoach,
            'knowledge-curator':           KnowledgeCurator,
            'documentation-synthesizer':  DocumentationSynthesizer,
        }
    build_knowledge_subgraph wired alongside maintenance subgraph;
    full supervisor routing wired in Phase 11. For 07-10/08-08 tests the
    supervisor_graph is mocked so internal cluster routing is tested E2E in
    a later phase.

Plan 09-06 extension:
    Supply agent DI (D-X-04 pattern — mirrors knowledge DI):
        supply_children = {
            'inventory-manager':  InventoryManager,
            'energy-optimizer':   EnergyOptimizer,
            'cost-analyzer':      CostAnalyzer,
            'demand-forecaster':  DemandForecaster,
        }
    build_supply_subgraph wired; cost-analyzer MUST be present (SCM fallback).
    CR-01: each class imported by EXACT exported name verified against agent modules.
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
    # WR-05: warn if WEB_CONCURRENCY > 1 — the SSE alert rate-limit uses an
    # in-process module-level dict (_alert_rate_state). With multiple Uvicorn/
    # Gunicorn workers each process maintains its own independent rate-limit
    # counter, effectively multiplying the allowed alert rate by the worker count.
    # This violates HITL-10. Phase 11 will replace with a Redis-backed counter.
    # For dev mode, always run with --workers 1 (WEB_CONCURRENCY=1).
    _web_concurrency = int(os.environ.get("WEB_CONCURRENCY", "1"))
    if _web_concurrency > 1:
        import warnings as _warnings
        _warnings.warn(
            f"WEB_CONCURRENCY={_web_concurrency} detected. "
            "The SSE alert rate-limit (_alert_rate_state) is in-process only "
            "and does NOT enforce HITL-10 across multiple workers. "
            "Set WEB_CONCURRENCY=1 for dev mode, or implement a Redis-backed "
            "sliding-window counter (Phase 11) before multi-worker production deploy.",
            RuntimeWarning,
            stacklevel=2,
        )
        logger.warning(
            "sse_rate_limit_multi_worker_violation",
            web_concurrency=_web_concurrency,
            note="HITL-10 rate-limit is per-process only; Phase 11 adds Redis backend",
        )

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

    # 10) Knowledge agent instances + knowledge_children dict (Plan 08-08, D-X-04).
    #     Collaborators that require Phase 5 (retrieval_pipeline, indexer, etc.)
    #     are passed as None — Phase 11 will wire real implementations. The agents
    #     accept None for optional collaborators (they raise at call time, not
    #     construction time, which is acceptable for the gateway DI layer).
    from trn_knowledge_curator.agent import KnowledgeCurator  # noqa: PLC0415
    from trn_shift_handover.agent import ShiftHandover  # noqa: PLC0415
    from trn_shift_handover.aggregator import ShiftAggregator  # noqa: PLC0415
    from trn_training_coach.agent import TrainingCoach  # noqa: PLC0415
    from trn_documentation_synthesizer.agent import DocumentationSynthesizer  # noqa: PLC0415
    from trn_documentation_synthesizer.event_aggregator import HistoricalEventAggregator  # noqa: PLC0415
    from trn_documentation_synthesizer.validators import SOPCitationValidator  # noqa: PLC0415
    from sft_agents.runtime.clusters import build_knowledge_subgraph  # noqa: PLC0415

    shift_handover_agent = ShiftHandover(
        pool=pool,
        audit_writer=audit_writer,
        llm=None,        # Phase 11: inject Qwen2.5 ChatOllama instance
        aggregator=ShiftAggregator(pool=pool),
        saver=saver,
    )
    training_coach_agent = TrainingCoach(
        pool=pool,
        audit_writer=audit_writer,
        llm=None,              # Phase 11: inject LLM
        retrieval_pipeline=None,   # Phase 5/11: inject sft-knowledge RetrievalPipeline
        escalate_tool=None,        # Phase 11: inject EscalateToSupervisorTool
    )
    knowledge_curator_agent = KnowledgeCurator(
        pool=pool,
        audit_writer=audit_writer,
        # near_dedup=None (default) — Phase 11: inject NearDedupChecker with Qdrant client
    )
    documentation_synthesizer_agent = DocumentationSynthesizer(
        pool=pool,
        audit_writer=audit_writer,
        llm=None,               # Phase 11: inject LLM
        retrieval_pipeline=None,    # Phase 5/11: inject sft-knowledge RetrievalPipeline
        indexer=None,               # Phase 11: inject Qdrant indexer
        event_aggregator=HistoricalEventAggregator(pool=pool),
        validator=SOPCitationValidator(),
        saver=saver,
    )

    knowledge_children = {
        "shift-handover": shift_handover_agent,
        "training-coach": training_coach_agent,
        "knowledge-curator": knowledge_curator_agent,
        "documentation-synthesizer": documentation_synthesizer_agent,
    }
    # Build the knowledge subgraph (uncompiled — wired into supervisor in Phase 11).
    # For Phase 8, the supervisor_graph.ainvoke routes via target_agent; the
    # knowledge_children dict is available for direct DI via get_knowledge_children.
    _knowledge_subgraph = build_knowledge_subgraph(knowledge_children)  # noqa: F841 — Phase 11 will wire into supervisor

    # 11) Supply agent instances + supply_children dict (Plan 09-06, D-X-04 pattern).
    #     CR-01: each class imported by EXACT exported name (verified against agent.py).
    #     All four agents use keyword-only __init__ (*, pool, audit_writer, llm) — call with kwargs.
    from scm_inventory_manager.agent import InventoryManager  # noqa: PLC0415
    from scm_energy_optimizer.agent import EnergyOptimizer  # noqa: PLC0415
    from scm_cost_analyzer.agent import CostAnalyzer  # noqa: PLC0415
    from scm_demand_forecaster.agent import DemandForecaster  # noqa: PLC0415
    from sft_agents.runtime.clusters import build_supply_subgraph  # noqa: PLC0415

    inventory_manager_agent = InventoryManager(
        pool=pool,
        audit_writer=audit_writer,
        llm=None,  # Phase 11: inject Qwen2.5 ChatOllama instance (LLM-free reorder path)
    )
    energy_optimizer_agent = EnergyOptimizer(
        pool=pool,
        audit_writer=audit_writer,
        llm=None,  # Phase 11: inject LLM (EnPI path is LLM-free)
    )
    cost_analyzer_agent = CostAnalyzer(
        pool=pool,
        audit_writer=audit_writer,
        llm=None,  # not used (LLM-free, deterministic OEPV)
    )
    demand_forecaster_agent = DemandForecaster(
        pool=pool,
        audit_writer=audit_writer,
        llm=None,  # Phase 11: inject LLM (Holt-Winters path is LLM-free)
    )

    supply_children = {
        "inventory-manager": inventory_manager_agent,
        "energy-optimizer": energy_optimizer_agent,
        "cost-analyzer": cost_analyzer_agent,   # REQUIRED fallback (D-SCM-AUTO)
        "demand-forecaster": demand_forecaster_agent,
    }
    # Build the supply subgraph (uncompiled — wired into supervisor in Phase 11).
    # cost-analyzer MUST be in supply_children (build_supply_subgraph enforces this).
    _supply_subgraph = build_supply_subgraph(supply_children)  # noqa: F841 — Phase 11 will wire into supervisor

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
    app.state.knowledge_children = knowledge_children  # Plan 08-08 D-X-04
    app.state.supply_children = supply_children  # Plan 09-06 D-X-04 pattern

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
