"""POST /v1/agents/{slug}/{action} — Plan 08-08 (TRN-02/03/04/05).

Knowledge cluster HTTP surface. Mirrors Phase 7 07-10 maintenance_agents.py
routing pattern; supervisor routes via target_agent into build_knowledge_subgraph
(08-01). Each endpoint sets ``state["target_agent"]`` in the AgentState passed
to the supervisor graph; the supervisor's HybridRouter dispatches into the
knowledge subgraph which routes to the named child callable.

Endpoints
---------
POST /v1/agents/shift-handover/compile         202  Compile + dual HITL (TRN-03, D-SH-01)
POST /v1/agents/training-coach/session         200  Quiz session (TRN-02)
POST /v1/agents/training-coach/resume          200  Resume after competency HITL (TRN-02)
POST /v1/agents/knowledge-curator/ingest       200  Autonomous dedup + stale flag (D-KC-04)
POST /v1/agents/documentation-synthesizer/draft  202  SOP draft + pre-index HITL (TRN-04)

Design notes
------------
* Idempotency-Key applies to shift-handover/compile, training-coach/session,
  training-coach/resume, and documentation-synthesizer/draft endpoints.
  knowledge-curator/ingest is excluded — fully autonomous read/flag operation;
  same document body yields the same dedup/stale verdict (idempotent by nature).
* user_roles propagated verbatim into AgentState (Phase 6 dev-mode ACL
  convention; Phase 11 will replace with JWT-derived claims).

Threats mitigated (T-08-15..T-08-17 register in 08-08 PLAN):
    * T-08-16 Tampering     — frozen+extra=forbid on all Pydantic models.
    * T-08-17 Denial of Service — recursion_limit=5 + RecursionError → 503.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sft_agents.llm.langfuse_callback import build_invocation_config

from svc_api_gateway.dependencies import (
    get_idempotency_cache,
    get_supervisor_graph,
)
from svc_api_gateway.idempotency import IdempotencyCache
from svc_api_gateway.idempotency_middleware import (
    check_idempotency_cache,
    jsonable,
    store_idempotent_response,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["knowledge-agents"])

# Bound the recursion budget so a misbehaving cluster subgraph cannot run away
# (T-08-17). 5 is the per-tick budget per Plan 08-08 contract.
_RECURSION_LIMIT: int = 5

# Retry-After value (seconds) returned on 503 GraphRecursionError (mirror 06-12).
_RETRY_AFTER_SECONDS: int = 5


# ---------------------------------------------------------------------------
# Request models (frozen + extra=forbid — T-08-16)
# ---------------------------------------------------------------------------


class ShiftHandoverCompileRequest(BaseModel):
    """Request body for POST /v1/agents/shift-handover/compile (TRN-03, D-SH-01).

    Manual trigger for the ShiftHandover dual-supervisor HITL flow.
    Complements the NATS-scheduled trigger (D-SH-01).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    shift_start: datetime = Field(description="Shift window start (tz-aware UTC)")
    shift_end: datetime = Field(description="Shift window end (tz-aware UTC)")
    user_roles: list[str] = Field(
        min_length=1,
        description="Caller roles for ACL enforcement (Phase 11)",
    )

    @model_validator(mode="after")
    def _check_window_order(self) -> "ShiftHandoverCompileRequest":
        """Validate shift_end is strictly after shift_start."""
        if self.shift_end <= self.shift_start:
            raise ValueError(
                f"shift_end ({self.shift_end.isoformat()}) must be strictly after "
                f"shift_start ({self.shift_start.isoformat()})"
            )
        return self


class TrainingSessionRequest(BaseModel):
    """Request body for POST /v1/agents/training-coach/session (TRN-02, D-TC-01).

    Starts a new adaptive MCQ quiz session for the operator.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    persona_role: str = Field(
        min_length=1,
        max_length=64,
        description="Operator role from SOP frontmatter (D-X-03, D-TC-01)",
    )
    user_roles: list[str] = Field(
        min_length=1,
        description="Caller roles for ACL enforcement",
    )


class TrainingResumeRequest(BaseModel):
    """Request body for POST /v1/agents/training-coach/resume (TRN-02, D-TC-03).

    Resume a training session after supervisor competency HITL sign-off.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    thread_id: str = Field(
        min_length=1,
        max_length=256,
        description="LangGraph thread_id from the original session (knowledge.training-coach.<uuid>)",
    )
    decision: str = Field(
        min_length=1,
        max_length=64,
        description="Supervisor competency decision (e.g. 'approved', 'rejected')",
    )


class KnowledgeCuratorIngestRequest(BaseModel):
    """Request body for POST /v1/agents/knowledge-curator/ingest (D-KC-04).

    Triggers autonomous dedup + staleness flagging. No HITL gating.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_text: str = Field(
        min_length=1,
        max_length=100_000,
        description="Full document text to curate (max 100 KiB)",
    )
    doc_type: str = Field(
        min_length=1,
        max_length=64,
        description="Document type (e.g. 'sop', 'manual', 'training_material')",
    )
    last_updated: datetime = Field(
        description="Document last-updated timestamp (tz-aware) for staleness check",
    )


class DocumentationDraftRequest(BaseModel):
    """Request body for POST /v1/agents/documentation-synthesizer/draft (TRN-04, D-DS-03).

    Triggers bilingual SOP draft generation with pre-index HITL gating.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    failure_mode: str = Field(
        min_length=1,
        max_length=256,
        description="Failure mode description for SOP context (D-DS-02)",
    )
    asset_id: str = Field(
        min_length=1,
        max_length=64,
        description="Asset identifier for event aggregation (e.g. 'LOOM-01')",
    )
    window_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Historical event window in days for aggregation (default 30)",
    )


# ---------------------------------------------------------------------------
# Helper: surface agent invocation errors as 503 (T-08-17)
# ---------------------------------------------------------------------------


def _handle_recursion_error(exc: RecursionError, thread_id: str) -> JSONResponse:
    """Return 503 with Retry-After header (mirror 06-12 escalation pattern)."""
    logger.warning(
        "knowledge_agent_recursion_overflow",
        thread_id=thread_id,
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "recursion_limit_exceeded", "thread_id": thread_id},
        headers={"Retry-After": str(_RETRY_AFTER_SECONDS)},
    )


def _handle_agent_error(exc: Exception, thread_id: str) -> JSONResponse:
    """Surface unexpected agent invocation errors as 500 (T-08-debugability)."""
    logger.error(
        "knowledge_agent_invocation_error",
        thread_id=thread_id,
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": str(exc), "thread_id": thread_id},
    )


# ---------------------------------------------------------------------------
# POST /v1/agents/shift-handover/compile — ShiftHandover (TRN-03, D-SH-01)
# ---------------------------------------------------------------------------


@router.post(
    "/shift-handover/compile",
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_shift_handover_compile(
    request: Request,
    body: Annotated[ShiftHandoverCompileRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Compile shift handover report via ShiftHandover dual-supervisor HITL (D-SH-01).

    Returns 202 Accepted immediately (HITL async). Thread_id identifies the LangGraph
    thread for subsequent approval workflow via /approvals endpoints.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return JSONResponse(content=cached, status_code=status.HTTP_202_ACCEPTED)

    thread_id = f"knowledge.shift-handover.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.shift-handover.compile"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "shift-handover",
        "shift_start": body.shift_start,
        "shift_end": body.shift_end,
        "user_roles": list(body.user_roles),
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable({"thread_id": thread_id, "hitl_status": "supervisor_pending"})
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_202_ACCEPTED
    )
    return JSONResponse(content=payload, status_code=status.HTTP_202_ACCEPTED)


# ---------------------------------------------------------------------------
# POST /v1/agents/training-coach/session — TrainingCoach start (TRN-02, D-TC-01)
# ---------------------------------------------------------------------------


@router.post(
    "/training-coach/session",
    status_code=status.HTTP_200_OK,
)
async def post_training_session(
    request: Request,
    body: Annotated[TrainingSessionRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Start a new adaptive MCQ quiz session for an operator (TRN-02).

    Returns 200 with the session result or 'awaiting_supervisor_signoff' when the
    operator passes and HITL interrupt is raised (D-TC-03).
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    thread_id = f"knowledge.training-coach.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.training-coach.session"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "training-coach",
        "persona_role": body.persona_role,
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
            "thread_id": thread_id,
            "competency_result": result.get("competency_result"),
            "training_session": result.get("training_session"),
        }
    )
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# POST /v1/agents/training-coach/resume — TrainingCoach resume post-HITL (TRN-02)
# ---------------------------------------------------------------------------


@router.post(
    "/training-coach/resume",
    status_code=status.HTTP_200_OK,
)
async def post_training_resume(
    request: Request,
    body: Annotated[TrainingResumeRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Resume a training session after supervisor competency HITL resolution (D-TC-03).

    Uses the original thread_id from the session so LangGraph replays the
    checkpoint and continues from the interrupt() point.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    thread_id = body.thread_id
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.training-coach.resume"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "training-coach",
        "action": "resume",
        "thread_id": thread_id,
        "decision": body.decision,
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable(
        {
            "thread_id": thread_id,
            "competency_result": result.get("competency_result"),
            "training_session": result.get("training_session"),
        }
    )
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# POST /v1/agents/knowledge-curator/ingest — KnowledgeCurator (D-KC-04)
# ---------------------------------------------------------------------------


@router.post(
    "/knowledge-curator/ingest",
    status_code=status.HTTP_200_OK,
)
async def post_knowledge_curator_ingest(
    request: Request,
    body: Annotated[KnowledgeCuratorIngestRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
) -> Any:
    """Autonomous document curation: dedup detection + staleness flagging (D-KC-04).

    NO Idempotency-Key required — fully autonomous read/flag operation;
    same document body yields the same dedup/stale verdict (idempotent by nature).
    Decision is always Decision.AUTO (D-KC-04 — no HITL gating).
    """
    thread_id = f"knowledge.knowledge-curator.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.knowledge-curator.ingest"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "knowledge-curator",
        "document_text": body.document_text,
        "doc_type": body.doc_type,
        "last_updated": body.last_updated,
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    return jsonable(
        {
            "thread_id": thread_id,
            "curation_report": result.get("curation_report"),
        }
    )


# ---------------------------------------------------------------------------
# POST /v1/agents/documentation-synthesizer/draft — DocumentationSynthesizer (TRN-04)
# ---------------------------------------------------------------------------


@router.post(
    "/documentation-synthesizer/draft",
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_documentation_draft(
    request: Request,
    body: Annotated[DocumentationDraftRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Initiate bilingual SOP draft with pre-index HITL gating (D-DS-03, TRN-04).

    Returns 202 Accepted — generation and Qdrant indexing happen asynchronously
    via the interrupt() / resume pattern. Thread_id identifies the thread for the
    subsequent approval workflow.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return JSONResponse(content=cached, status_code=status.HTTP_202_ACCEPTED)

    thread_id = f"knowledge.documentation-synthesizer.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.documentation-synthesizer.draft"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "documentation-synthesizer",
        "failure_mode": body.failure_mode,
        "asset_id": body.asset_id,
        "window_days": body.window_days,
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable({"thread_id": thread_id, "hitl_status": "supervisor_pending"})
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_202_ACCEPTED
    )
    return JSONResponse(content=payload, status_code=status.HTTP_202_ACCEPTED)


__all__ = ["router"]
