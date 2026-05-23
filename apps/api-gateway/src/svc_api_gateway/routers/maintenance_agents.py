"""POST /v1/agents/{slug}/{action} — Plan 07-10 (MNT-01/02/03/04).

Maintenance cluster HTTP surface. Mirrors Phase 6 06-12 ops_agents.py routing
pattern; supervisor routes via target_agent into build_maintenance_subgraph
(07-04). Each endpoint sets ``state["target_agent"]`` in the AgentState passed
to the supervisor graph; the supervisor's HybridRouter dispatches into the
maintenance subgraph which routes to the named child callable.

Endpoints
---------
POST /v1/agents/predictive-maintenance/score     200  PM score (MNT-01)
POST /v1/agents/rca-specialist/analyze           202  RCA + always-HITL (MNT-02)
POST /v1/agents/maintenance-coach/start          200  Coach start intervention (MNT-03)
POST /v1/agents/maintenance-coach/step           200  Coach step (MNT-03)
POST /v1/agents/maintenance-coach/resume         200  Coach resume post-HITL (MNT-03)
POST /v1/agents/downtime-analyzer/report         200  OEE + Pareto report (MNT-04)

Design notes
------------
* Idempotency-Key applies to PM/RCA/Coach endpoints (non-idempotent).
  DA /report is excluded — read-only analytics; same window yields the same
  OEE report within CAGG refresh tolerance; no Idempotency-Key required.
* Maintenance-coach /step + /resume use direct DI access to the checkpointer
  to read state before supervisor invocation. This is necessary because the
  LangGraph Command(resume=...) pattern for thread continuation does not
  transparently pass through the supervisor routing layer as a new ainvoke —
  the supervisor would re-route instead of resuming the existing thread.
  Decision: /step and /resume still call supervisor_graph.ainvoke (LangGraph
  handles checkpoint replay via thread_id), but the endpoint additionally reads
  the checkpoint to enforce the 409 guard before invoking.
* user_roles propagated verbatim into AgentState (Phase 6 dev-mode ACL
  convention, T-V6-acl-leak limitation documented; Phase 11 will replace
  with JWT-derived claims — TODO: remove user_roles from body in Phase 11).

Threats mitigated (T-V7-router-* register in 07-10 PLAN):
    * T-V7-router-injection      — frozen+extra=forbid on all Pydantic models.
    * T-V7-router-recursion-bomb — recursion_limit=5 + RecursionError → 503.
    * T-V7-router-idempotency-replay — Idempotency-Key for PM/RCA/Coach.
    * T-V7-router-coach-resume-namespace — thread_id=coach-<id> documented.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import uuid4

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sft_agents.llm.langfuse_callback import build_invocation_config

from svc_api_gateway.dependencies import (
    get_checkpointer,
    get_idempotency_cache,
    get_supervisor_graph,
)
from svc_api_gateway.idempotency import IdempotencyCache
from svc_api_gateway.idempotency_middleware import (
    check_idempotency_cache,
    jsonable,
    store_idempotent_response,
)

# Re-import domain models — keeps the router thin (no business logic here).
from mnt_predictive_maintenance.models import RULEstimate
from mnt_maintenance_coach.models import CoachResponse
from mnt_downtime_analyzer.models import OEEReport, ReportRequest

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["maintenance-agents"])

# Bound the recursion budget so a misbehaving cluster subgraph cannot run away
# (T-V7-router-recursion-bomb). 5 is the per-tick budget per Plan 07-10 contract.
_RECURSION_LIMIT: int = 5

# Retry-After value (seconds) returned on 503 GraphRecursionError (mirror 06-12).
_RETRY_AFTER_SECONDS: int = 5


# ---------------------------------------------------------------------------
# Request / Response models (frozen + extra=forbid — T-V7-router-injection)
# ---------------------------------------------------------------------------


class PMScoreRequest(BaseModel):
    """Request body for POST /v1/agents/predictive-maintenance/score (MNT-01)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: str = Field(min_length=1, max_length=64)
    triggered_by_action_id: str | None = Field(
        default=None,
        description="Upstream AnomalyDetector audit row action_id for MNT-06 chain",
    )
    user_roles: list[str] = Field(
        min_length=1, description="Caller roles for ACL enforcement (Phase 5)"
    )


class PMScoreResponse(BaseModel):
    """Response envelope for POST /v1/agents/predictive-maintenance/score."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rul_estimate: RULEstimate | None = Field(
        default=None,
        description="RUL estimate (None when agent escalated to HITL supervisor)",
    )
    thread_id: str = Field(description="LangGraph thread_id for this invocation")


class RCAAnalyzeRequest(BaseModel):
    """Request body for POST /v1/agents/rca-specialist/analyze (MNT-02)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    problem_statement: str = Field(
        min_length=10,
        max_length=2000,
        description="Problem description (min 10 chars for meaningful RCA)",
    )
    downtime_event_id: str | None = Field(
        default=None,
        description="Optional downtime_event_id from maintenance.downtime_events (07-05)",
    )
    asset_id: str | None = Field(default=None, description="Optional asset_id scope filter")
    user_roles: list[str] = Field(
        min_length=1, description="Caller roles (min 1 required for ACL)"
    )
    lang: Literal["it", "en"] = Field(
        default="it", description="RCA report language (IT default per D-RCA-01)"
    )


class RCAAnalyzeResponse(BaseModel):
    """Response envelope for POST /v1/agents/rca-specialist/analyze."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chain_id: str | None = Field(
        default=None,
        description="RCAChain UUID4 (None until supervisor approves post-HITL)",
    )
    thread_id: str = Field(description="LangGraph thread_id for this invocation")
    hitl_status: Literal["supervisor_pending"] = Field(
        description="Always 'supervisor_pending' per D-RCA-02 always-HITL contract"
    )
    validation_exhausted: bool = Field(
        default=False,
        description="True when 07-07 retry budget (3 attempts) was exhausted before escalation",
    )


class CoachStartRequestHTTP(BaseModel):
    """Request body for POST /v1/agents/maintenance-coach/start.

    ``intervention_id`` is optional at the HTTP boundary — the server generates
    a UUID4 when absent. This wraps 07-08's CoachStartRequest which requires
    intervention_id; the server fills it in before invoking the supervisor.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    intervention_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Client-generated intervention ID; server generates UUID4 if absent",
    )
    asset_id: str = Field(min_length=1, description="Asset under maintenance (e.g. LOOM-01)")
    sop_id: str = Field(min_length=1, description="SOP identifier (e.g. SOP-LOOM-001)")
    technician_id: str | None = Field(
        default=None,
        description="Optional: omit for RCA auto-open path (Open Q3 RESOLVED in 07-08)",
    )
    user_roles: list[str] = Field(
        default_factory=list,
        description="Caller roles for RAG search ACL (Phase 5)",
    )


class CoachStepRequestHTTP(BaseModel):
    """Request body for POST /v1/agents/maintenance-coach/step."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intervention_id: str = Field(min_length=1, max_length=64)
    technician_input: str = Field(
        min_length=1,
        max_length=4000,
        description="Technician confirmation / notes (cap 4000 — T-V7-coach-injection)",
    )


class CoachResumeRequestHTTP(BaseModel):
    """Request body for POST /v1/agents/maintenance-coach/resume.

    Two resume paths (Open Q3 RESOLVED in 07-08):
      (a) post request_help interrupt — ``supervisor_input`` required
      (b) post technician_assignment_required interrupt — ``technician_id`` required

    At least one of supervisor_input or technician_id MUST be provided (422 otherwise).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    intervention_id: str = Field(min_length=1, max_length=64)
    supervisor_input: str | None = Field(
        default=None,
        min_length=1,
        max_length=4000,
        description="Supervisor response text (required for post-help resume path)",
    )
    supervisor_id: str = Field(
        min_length=1,
        max_length=64,
        description="Supervisor identifier for audit trail",
    )
    technician_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Technician ID to assign (required for post-technician-assignment path)",
    )

    @model_validator(mode="after")
    def _require_one_of(self) -> "CoachResumeRequestHTTP":
        """At least one of supervisor_input or technician_id must be provided."""
        if self.supervisor_input is None and self.technician_id is None:
            raise ValueError(
                "At least one of supervisor_input or technician_id must be provided. "
                "Use supervisor_input for post-help resume (path a) or technician_id "
                "for post-technician-assignment resume (path b)."
            )
        return self


# ---------------------------------------------------------------------------
# Helper: surface agent invocation errors as 503 (T-V7-router-recursion-bomb)
# ---------------------------------------------------------------------------


def _handle_recursion_error(exc: RecursionError, thread_id: str) -> JSONResponse:
    """Return 503 with Retry-After header (mirror 06-12 escalation pattern)."""
    logger.warning(
        "maintenance_agent_recursion_overflow",
        thread_id=thread_id,
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "recursion_limit_exceeded", "thread_id": thread_id},
        headers={"Retry-After": str(_RETRY_AFTER_SECONDS)},
    )


def _handle_agent_error(exc: Exception, thread_id: str) -> JSONResponse:
    """Surface unexpected agent invocation errors as 500 (T-V7-router-debugability)."""
    logger.error(
        "maintenance_agent_invocation_error",
        thread_id=thread_id,
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": str(exc), "thread_id": thread_id},
    )


# ---------------------------------------------------------------------------
# /v1/agents/predictive-maintenance/score — PM (MNT-01)
# ---------------------------------------------------------------------------


@router.post(
    "/predictive-maintenance/score",
    status_code=status.HTTP_200_OK,
    response_model=PMScoreResponse,
)
async def post_pm_score(
    request: Request,
    body: Annotated[PMScoreRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Run one PredictiveMaintenance tick via the supervisor graph (MNT-01)."""
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    thread_id = f"maintenance.predictive-maintenance.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.predictive-maintenance.invoke"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "predictive-maintenance",
        "asset_id": body.asset_id,
        "triggered_by_action_id": body.triggered_by_action_id,
        "user_roles": list(body.user_roles),
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable(
        {
            "rul_estimate": _model_dump_or_none(result.get("rul_estimate")),
            "thread_id": thread_id,
        }
    )
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# /v1/agents/rca-specialist/analyze — RCA (MNT-02)
# ---------------------------------------------------------------------------


@router.post(
    "/rca-specialist/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RCAAnalyzeResponse,
)
async def post_rca_analyze(
    request: Request,
    body: Annotated[RCAAnalyzeRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Initiate RCA chain via RCASpecialist — always 202 (HITL async, D-RCA-02)."""
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return JSONResponse(content=cached, status_code=status.HTTP_202_ACCEPTED)

    thread_id = f"maintenance.rca-specialist.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.rca-specialist.invoke"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "rca-specialist",
        "problem_statement": body.problem_statement,
        "downtime_event_id": body.downtime_event_id,
        "asset_id": body.asset_id,
        "user_roles": list(body.user_roles),
        "lang": body.lang,
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable(
        {
            "chain_id": _maybe_str(result.get("chain_id")),
            "thread_id": thread_id,
            "hitl_status": "supervisor_pending",
            "validation_exhausted": bool(result.get("validation_exhausted", False)),
        }
    )
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_202_ACCEPTED
    )
    return JSONResponse(content=payload, status_code=status.HTTP_202_ACCEPTED)


# ---------------------------------------------------------------------------
# /v1/agents/maintenance-coach/start — Coach start (MNT-03)
# ---------------------------------------------------------------------------


@router.post(
    "/maintenance-coach/start",
    status_code=status.HTTP_200_OK,
)
async def post_coach_start(
    request: Request,
    body: Annotated[CoachStartRequestHTTP, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Open a new coaching intervention (or return awaiting_technician_assignment).

    Server generates intervention_id when absent. If technician_id is None,
    the supervisor coach node emits a technician_assignment_required HITL
    interrupt and the response carries state='awaiting_technician_assignment'.
    Client must then call /resume with technician_id to proceed.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    # Server generates UUID4 when intervention_id absent (Open Q3 support)
    intervention_id = body.intervention_id or str(uuid4())
    thread_id = f"coach-{intervention_id}"

    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.maintenance-coach.start"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "maintenance-coach",
        "action": "start",
        "intervention_id": intervention_id,
        "asset_id": body.asset_id,
        "sop_id": body.sop_id,
        "technician_id": body.technician_id,
        "user_roles": list(body.user_roles),
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable(_build_coach_payload(result, intervention_id))
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# /v1/agents/maintenance-coach/step — Coach step (MNT-03)
# ---------------------------------------------------------------------------


@router.post(
    "/maintenance-coach/step",
    status_code=status.HTTP_200_OK,
)
async def post_coach_step(
    request: Request,
    body: Annotated[CoachStepRequestHTTP, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    checkpointer: Any = Depends(get_checkpointer),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Advance an existing coaching intervention by one step.

    Returns 409 Conflict if the intervention thread still has technician_id=None
    (technician must be assigned first via /resume with technician_id).

    Design note: LangGraph replays the checkpoint automatically when the same
    thread_id is used in config. The supervisor routes to maintenance-coach
    which reads the persisted step state + advances it.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    thread_id = f"coach-{body.intervention_id}"

    # 409 guard: check checkpoint for technician_id=None before invoking supervisor.
    try:
        checkpoint_tuple = await checkpointer.aget_tuple(
            {"configurable": {"thread_id": thread_id}}
        )
    except Exception:  # noqa: BLE001 — checkpointer not available or thread not found
        checkpoint_tuple = None

    if checkpoint_tuple is not None:
        channel_values: dict[str, Any] = {}
        checkpoint = getattr(checkpoint_tuple, "checkpoint", None)
        if isinstance(checkpoint, dict):
            channel_values = checkpoint.get("channel_values", {})
        if channel_values.get("technician_id") is None and "technician_id" in channel_values:
            # Thread exists but technician not yet assigned — 409 per plan contract
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "technician_assignment_required",
                    "intervention_id": body.intervention_id,
                },
            )

    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.maintenance-coach.step"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "maintenance-coach",
        "action": "step",
        "intervention_id": body.intervention_id,
        "technician_input": body.technician_input,
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable(_build_coach_payload(result, body.intervention_id))
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# /v1/agents/maintenance-coach/resume — Coach resume post-HITL (MNT-03)
# ---------------------------------------------------------------------------


@router.post(
    "/maintenance-coach/resume",
    status_code=status.HTTP_200_OK,
)
async def post_coach_resume(
    request: Request,
    body: Annotated[CoachResumeRequestHTTP, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Resume a coaching intervention after HITL interrupt resolution.

    Two paths (Open Q3 RESOLVED in 07-08):
      (a) post request_help interrupt — supervisor_input required
          → invoke supervisor with Command(resume=supervisor_input) semantics
          → state carries escalation_trigger='technician_request' marker
      (b) post technician_assignment_required interrupt — technician_id required
          → invoke supervisor with Command(update={'technician_id': ...}, resume=True)
          → state advances from step 0 with technician assigned
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    thread_id = f"coach-{body.intervention_id}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.maintenance-coach.resume"],
        recursion_limit=_RECURSION_LIMIT,
    )

    # Build state for the resume invocation — both paths merge into supervisor
    state: dict[str, Any] = {
        "target_agent": "maintenance-coach",
        "action": "resume",
        "intervention_id": body.intervention_id,
        "supervisor_id": body.supervisor_id,
    }

    if body.technician_id is not None:
        # Path (b): technician assignment — populate technician_id in state
        state["technician_id"] = body.technician_id
        state["resume_type"] = "technician_assignment"
    else:
        # Path (a): post-help resume — propagate supervisor decision
        state["supervisor_input"] = body.supervisor_input
        state["escalation_trigger"] = "technician_request"
        state["resume_type"] = "post_help"

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable(_build_coach_payload(result, body.intervention_id))
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# /v1/agents/downtime-analyzer/report — DA (MNT-04)
# ---------------------------------------------------------------------------


class _ReportRequestHTTP(ReportRequest):
    """HTTP wrapper for ReportRequest that enforces window_end > window_start at ingestion.

    ReportRequest (from 07-09) does not validate window order (OEEReport does).
    This wrapper adds the cross-field validator so the 422 fires at request
    parsing rather than at response serialization.
    """

    @model_validator(mode="after")
    def _check_window_order(self) -> "_ReportRequestHTTP":
        if self.window_end <= self.window_start:
            raise ValueError(
                f"window_end ({self.window_end.isoformat()}) must be strictly after "
                f"window_start ({self.window_start.isoformat()})"
            )
        return self


@router.post(
    "/downtime-analyzer/report",
    status_code=status.HTTP_200_OK,
)
async def post_da_report(
    request: Request,
    body: Annotated[_ReportRequestHTTP, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
) -> Any:
    """Run on-demand OEE + Pareto report via DowntimeAnalyzer (MNT-04).

    NO Idempotency-Key required — read-only analytics; the same window always
    yields the same OEE within CAGG refresh tolerance (maintenance.oee_hourly
    CAGG from 07-05 migration 008). Documented as idempotency-not-needed:
    the caller can safely retry without risk of duplicate side-effects.
    """
    thread_id = f"maintenance.downtime-analyzer.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.downtime-analyzer.report"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "downtime-analyzer",
        "window_start": body.window_start.isoformat(),
        "window_end": body.window_end.isoformat(),
        "by_asset": body.by_asset,
        "top_n_pareto": body.top_n_pareto,
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    # Return OEEReport-shaped dict (agent returns it in result or in result["oee_report"])
    oee_data = result.get("oee_report") or result
    return jsonable(oee_data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_coach_payload(result: dict[str, Any], intervention_id: str) -> dict[str, Any]:
    """Coerce agent result into CoachResponse-compatible dict."""
    return {
        "intervention_id": result.get("intervention_id") or intervention_id,
        "current_step": int(result.get("current_step", 0)),
        "guidance_md": str(result.get("guidance_md", "")),
        "completed_step": _model_dump_or_none(result.get("completed_step")),
        "mttr_minutes_so_far": result.get("mttr_minutes_so_far"),
        "state": result.get("state", "in_progress"),
    }


def _model_dump_or_none(v: Any) -> Any:
    """Best-effort coerce Pydantic model to dict, or return as-is."""
    if v is None:
        return None
    dump = getattr(v, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    return v


def _maybe_str(v: Any) -> str | None:
    if v is None:
        return None
    return str(v)


__all__ = ["router"]
