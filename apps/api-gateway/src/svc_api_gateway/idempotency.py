"""In-memory Idempotency-Key cache for POST/PUT/PATCH replay defense (T-04-Resume-Replay layer 2).

Contract:
    Cache key: (method, path, idempotency_key) — opaque tuple.
    Stored value: (timestamp_monotonic, body_sha256_hex, response_dict).

    On second request with SAME (method, path, key):
        - SAME body hash → return cached response_dict (200 replay).
        - DIFFERENT body hash → caller raises HTTPException(409 idempotency_conflict).

TTL: default 300s (5 minutes). Eviction is lazy — entries are checked on access.

Scope:
    Per-process in-memory only. Phase 11 migrates to Redis when multiple
    api-gateway replicas are deployed (documented in SUMMARY as deferred).

Concurrency:
    All mutations are guarded by ``asyncio.Lock``. The cache is safe to share
    across concurrent FastAPI request handlers in the same event loop.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _Entry:
    expires_at: float  # monotonic seconds
    body_hash: str
    response: dict[str, Any]
    status_code: int


class IdempotencyCache:
    """Async-safe TTL cache for idempotent POST/PUT/PATCH replays."""

    def __init__(self, *, ttl_seconds: int = 300, max_size: int = 4096) -> None:
        if ttl_seconds <= 0:
            raise ValueError(f"ttl_seconds must be > 0; got {ttl_seconds!r}")
        if max_size <= 0:
            raise ValueError(f"max_size must be > 0; got {max_size!r}")
        self._ttl_seconds = float(ttl_seconds)
        self._max_size = int(max_size)
        self._store: dict[tuple[str, str, str], _Entry] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def hash_body(body: bytes) -> str:
        """sha256 hex of the raw request body bytes."""
        return hashlib.sha256(body).hexdigest()

    async def get(
        self, method: str, path: str, key: str
    ) -> _Entry | None:
        """Return the cached entry if present + not expired; else None.

        Expired entries are removed on access.
        """
        cache_key = (method.upper(), path, key)
        async with self._lock:
            entry = self._store.get(cache_key)
            if entry is None:
                return None
            if time.monotonic() >= entry.expires_at:
                self._store.pop(cache_key, None)
                return None
            return entry

    async def put(
        self,
        method: str,
        path: str,
        key: str,
        *,
        body_hash: str,
        response: dict[str, Any],
        status_code: int = 200,
    ) -> None:
        """Insert a fresh entry (overwrites any prior entry for same key)."""
        cache_key = (method.upper(), path, key)
        expires_at = time.monotonic() + self._ttl_seconds
        async with self._lock:
            # LRU-ish eviction: if at cap, drop oldest entry by expiry.
            if len(self._store) >= self._max_size:
                oldest_key = min(self._store, key=lambda k: self._store[k].expires_at)
                self._store.pop(oldest_key, None)
            self._store[cache_key] = _Entry(
                expires_at=expires_at,
                body_hash=body_hash,
                response=response,
                status_code=status_code,
            )

    async def size(self) -> int:
        async with self._lock:
            return len(self._store)


__all__ = ["IdempotencyCache"]
