"""POST /v1/quality/events — Plan 06-12 (OPS-04 / D-QI-01).

Operator-side ingest for `QualityEvent` rows. The route does NOT invoke
QualityInspector directly; instead it forces ``source="operator"`` server-side
(T-V6-source-spoof mitigation), assigns a fresh ``event_id`` server-side and
publishes the event to ``quality.events.<asset_id>`` on NATS. QualityInspector
consumes that subject and runs the agentic ASTM D5430 grading flow.

Threats mitigated here:
    * T-V6-injection      — `QualityEventOperatorRequest` is frozen+extra=forbid
                            so unknown / spoofed fields are 422-rejected before
                            reaching the publish step.
    * T-V6-source-spoof   — `source` is OMITTED from the request schema (the
                            shape forbids extra keys); the server unconditionally
                            stamps `source="operator"` on the validated payload.
    * T-V6-idempotency-replay — Idempotency-Key header caches the full response
                            envelope for 5 minutes (approvals.py pattern).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sft_domain.ops._validators import tz_aware
from sft_domain.ops.quality import DefectType, QualityEvent

from svc_api_gateway.dependencies import (
    get_idempotency_cache,
    get_nats_publisher,
)
from svc_api_gateway.idempotency import IdempotencyCache
from svc_api_gateway.idempotency_middleware import (
    check_idempotency_cache,
    jsonable,
    store_idempotent_response,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/quality", tags=["quality"])


class QualityEventOperatorRequest(BaseModel):
    """Operator-facing QualityEvent payload (T-V6-source-spoof mitigation).

    Mirrors ``sft_domain.ops.quality.QualityEvent`` but DELIBERATELY OMITS:

      * ``event_id``  — server generates fresh UUID4.
      * ``source``    — server forces "operator"; reject unknown keys via
                        ``extra="forbid"`` so a client cannot smuggle
                        ``source="simulator"`` into the publish payload.

    All other validation rules (regex on dye_lot_id, defect_type Literal,
    tz-aware timestamp, bounded defect_length_inches) are mirrored.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: Annotated[str, Field(min_length=1, description="Asset ID")]
    dye_lot_id: Annotated[
        str,
        Field(
            pattern=r"^DL-[A-Z0-9-]+-\d{8}-[0-9a-f]+$",
            description="Dye-lot identifier (D-QI-04 regex).",
        ),
    ]
    defect_type: Annotated[
        DefectType, Field(description="Tipo difetto (7-defect taxonomy)")
    ]
    defect_length_inches: Annotated[
        float, Field(ge=0.0, description="Defect length in inches (>=0)")
    ]
    full_width: Annotated[
        bool, Field(default=False, description="Full-width (selvedge-to-selvedge)")
    ] = False
    position_meters: Annotated[
        float, Field(description="Linear position on the roll (meters)")
    ]
    timestamp: Annotated[datetime, Field(description="UTC tz-aware observation")]

    @field_validator("timestamp")
    @classmethod
    def _tz(cls, v: datetime) -> datetime:
        return tz_aware(v)


class QualityEventAcceptedResponse(BaseModel):
    """202 envelope returned by POST /v1/quality/events."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    event_id: UUID


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=QualityEventAcceptedResponse,
)
async def post_quality_event(
    request: Request,
    body: Annotated[QualityEventOperatorRequest, Body()],
    nats_publisher: Any = Depends(get_nats_publisher),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Accept an operator-submitted QualityEvent and forward to NATS.

    Returns 202 Accepted because the downstream QualityInspector agent runs
    asynchronously via the NATS consumer wiring (see Plan 06-07 worker loop).
    """
    raw_body = await request.body()

    # Idempotency replay defense (T-V6-idempotency-replay).
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return JSONResponse(
            content=cached, status_code=status.HTTP_202_ACCEPTED
        )

    # Server-forced source + server-generated event_id (T-V6-source-spoof).
    event = QualityEvent(
        event_id=uuid4(),
        source="operator",
        **body.model_dump(),
    )

    subject = f"quality.events.{event.asset_id}"
    payload = event.model_dump_json().encode("utf-8")
    await nats_publisher.publish_raw(subject, payload)

    logger.info(
        "quality_event_ingested",
        event_id=str(event.event_id),
        asset_id=event.asset_id,
        dye_lot_id=event.dye_lot_id,
        defect_type=event.defect_type,
        source=event.source,
    )

    response_payload = jsonable({"accepted": True, "event_id": str(event.event_id)})
    await store_idempotent_response(
        request,
        cache,
        body_hash,
        response_payload,
        status_code=status.HTTP_202_ACCEPTED,
    )
    return JSONResponse(
        content=response_payload, status_code=status.HTTP_202_ACCEPTED
    )


__all__ = ["router"]
