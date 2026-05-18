"""POST /v1/threads/{thread_id}/resume — Plan 04-07 Task 2.

Task 1 ships an empty router; Task 2 lands the resume handler.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/threads", tags=["threads"])


__all__ = ["router"]
