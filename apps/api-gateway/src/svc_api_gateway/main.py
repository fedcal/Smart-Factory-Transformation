"""FastAPI app entrypoint — Plan 04-07 Task 1.

Composition:
    app = FastAPI(title=..., lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(approvals.router)    # Task 2
    app.include_router(threads.router)      # Task 2

Run via:
    uvicorn svc_api_gateway.main:app --host 0.0.0.0 --port 8081

or via the console script:
    api-gateway

structlog is configured at module import time (mirrors
``services/ot-bridge/src/svc_ot_bridge/main.py:30-40``).
"""

from __future__ import annotations

import sys

import structlog
from fastapi import FastAPI

from svc_api_gateway import __version__
from svc_api_gateway.lifespan import lifespan

# ---------------------------------------------------------------------------
# structlog config — JSON stderr, identical to ot-bridge for log consistency.
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)


def build_app() -> FastAPI:
    """Construct the FastAPI app (factory pattern — used by tests + main)."""
    # Local imports avoid pulling router-module side effects at module import time
    # for unit tests that want a fresh app per fixture.
    from svc_api_gateway.routers import approvals as approvals_router  # noqa: PLC0415
    from svc_api_gateway.routers import auth as auth_router  # noqa: PLC0415
    from svc_api_gateway.routers import health as health_router  # noqa: PLC0415
    from svc_api_gateway.routers import knowledge_agents as knowledge_agents_router  # noqa: PLC0415
    from svc_api_gateway.routers import maintenance_agents as maintenance_agents_router  # noqa: PLC0415
    from svc_api_gateway.routers import ops_agents as ops_agents_router  # noqa: PLC0415
    from svc_api_gateway.routers import quality as quality_router  # noqa: PLC0415
    from svc_api_gateway.routers import supply_agents as supply_agents_router  # noqa: PLC0415
    from svc_api_gateway.routers import threads as threads_router  # noqa: PLC0415

    app = FastAPI(
        title="SFT API Gateway",
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(health_router.router)
    app.include_router(auth_router.router)  # Plan 10-01 — SRV-01 JWT auth + RBAC
    app.include_router(approvals_router.router)
    app.include_router(threads_router.router)
    app.include_router(quality_router.router)  # Plan 06-12 — OPS-04 ingest
    app.include_router(ops_agents_router.router)  # Plan 06-12 — OPS-01/02/03
    app.include_router(maintenance_agents_router.router)  # Plan 07-10 — MNT-01/02/03/04
    app.include_router(knowledge_agents_router.router)  # Plan 08-08 — TRN-02/03/04/05
    app.include_router(supply_agents_router.router)  # Plan 09-06 — SCM-01/02/03/04
    return app


# Module-level singleton consumed by `uvicorn svc_api_gateway.main:app`.
app = build_app()


def run() -> None:
    """Console-script entry point (`api-gateway`)."""
    import os  # noqa: PLC0415

    import uvicorn  # noqa: PLC0415

    port = int(os.environ.get("API_GATEWAY_PORT", "8081"))
    uvicorn.run(
        "svc_api_gateway.main:app",
        host="0.0.0.0",  # noqa: S104 — bind 0.0.0.0 inside container; Phase 11 fronts via ingress
        port=port,
        log_config=None,  # structlog handles output; suppress uvicorn dictConfig
    )


__all__ = ["app", "build_app", "run"]


if __name__ == "__main__":
    run()
