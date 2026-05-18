"""GET /v1/approvals + POST /v1/approvals/{id}/decide — Plan 04-07 Task 2.

Task 1 ships an empty router; Task 2 lands handlers + Idempotency-Key wiring.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])


__all__ = ["router"]
