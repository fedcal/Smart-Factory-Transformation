"""Idempotency-Key request-level helper used by mutating routes.

The full ASGI middleware pattern would intercept ALL POST/PUT/PATCH; we instead
expose a small async helper that each mutating endpoint calls explicitly. This
gives us:
    - Per-route control over which methods deserve caching (e.g. /decide yes,
      future bulk-uploads probably not).
    - The ability to cache the FULL response (status + body) rather than only
      successful 200s.

Contract:
    1. Compute body_hash = sha256(raw_body_bytes).
    2. If client provided ``Idempotency-Key`` header:
       a. Cache hit + same body_hash → return cached (200 replay).
       b. Cache hit + different body_hash → raise HTTPException(409).
       c. Cache miss → proceed; caller stores the response on completion via
          ``store_idempotent_response``.
    3. If client did NOT provide Idempotency-Key, the helper is a no-op
       (returns (None, None)).

T-04-Resume-Replay: this is defense layer 2 (layer 1 is the SQL UPDATE WHERE
status='pending' atomic guard inside ApprovalQueueWriter.update_decision).
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, Request, status

from svc_api_gateway.idempotency import IdempotencyCache


async def check_idempotency_cache(
    request: Request,
    cache: IdempotencyCache,
    raw_body: bytes,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return (cached_response, body_hash) if header present.

    Cached response is None if no cache hit (caller proceeds normally + later
    stores the response via :func:`store_idempotent_response`). Raises
    HTTPException(409) on body-hash conflict.

    When the ``Idempotency-Key`` header is absent, returns (None, None) — the
    caller should skip the store step too.
    """
    key = request.headers.get("Idempotency-Key") or request.headers.get(
        "idempotency-key"
    )
    if not key:
        return None, None

    body_hash = IdempotencyCache.hash_body(raw_body)
    entry = await cache.get(request.method, request.url.path, key)
    if entry is None:
        return None, body_hash

    if entry.body_hash != body_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="idempotency_conflict: same key submitted with different body",
        )
    return entry.response, body_hash


async def store_idempotent_response(
    request: Request,
    cache: IdempotencyCache,
    body_hash: str | None,
    response: dict[str, Any],
    status_code: int = 200,
) -> None:
    """Persist (method, path, key) → response into the in-memory cache.

    No-op when body_hash is None (caller did not supply Idempotency-Key) or
    the header is absent at store time.
    """
    if body_hash is None:
        return
    key = request.headers.get("Idempotency-Key") or request.headers.get(
        "idempotency-key"
    )
    if not key:
        return
    await cache.put(
        request.method,
        request.url.path,
        key,
        body_hash=body_hash,
        response=response,
        status_code=status_code,
    )


def jsonable(obj: Any) -> Any:
    """Recursively coerce to JSON-serialisable primitives.

    Used to normalise Pydantic model dumps + asyncpg Records before caching.
    """
    return json.loads(json.dumps(obj, default=str))


__all__ = [
    "check_idempotency_cache",
    "jsonable",
    "store_idempotent_response",
]
