"""audit.outbox writer + retry loop (D-56 + T-04-Outbox-Drop mitigation).

The outbox is a unified ``(subject, payload_json)`` retry queue (OQ5 resolution
documented in ``infra/migrations/timescale/003_create_audit_actions.sql``).
``AuditWriter`` (writer.py) enqueues a row whenever a NATS publish fails so the
record can be replayed once NATS is healthy again.

Background loop pattern:
    Mirrors ``services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:146-158``:
    ``while not shutdown: sleep(interval); _run_once()`` with CancelledError
    re-raised and other exceptions logged + swallowed (to avoid breaking the
    long-running task).

Exponential backoff:
    ``next_attempt_at = NOW() + min(2 ** attempts, 3600) seconds``
    Capped at 1 hour. After ``max_attempts=10`` the row is no longer scanned
    (Phase 11 ships dead-letter alerting).

Security (T-04-NATS-Spoofed):
    ``OutboxWriter.enqueue`` does NOT accept arbitrary subjects from external
    callers — the only caller (``AuditWriter``) derives subjects via the
    ``subject_for_*`` validated helpers in ``audit.subjects``.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)

# SQL constants — T-V5-sql (zero f-string interpolation).
_OUTBOX_INSERT_SQL: str = (
    "INSERT INTO audit.outbox (id, subject, payload_json, attempts, next_attempt_at, created_at) "
    "VALUES ($1, $2, $3::jsonb, 0, NOW(), NOW()) RETURNING id"
)

_OUTBOX_SELECT_SQL: str = (
    "SELECT id, subject, payload_json::text AS payload_json, attempts "
    "FROM audit.outbox "
    "WHERE published_at IS NULL AND attempts < $1 "
    "AND (next_attempt_at IS NULL OR next_attempt_at < NOW()) "
    "ORDER BY created_at "
    "LIMIT $2"
)

_OUTBOX_MARK_PUBLISHED_SQL: str = (
    "UPDATE audit.outbox SET published_at = NOW() WHERE id = $1"
)

# Exponential backoff: attempts++ AND next_attempt_at = NOW() + INTERVAL '<n>s'.
# We compute the interval seconds in Python (capped to 1h) and inline as a
# literal integer in the INTERVAL expression so asyncpg can parse it without
# parameter binding (PostgreSQL forbids parameter binding inside INTERVAL).
# The value is server-side computed from an int constant; no user input flows
# through the literal — defense-in-depth is the cap.
_OUTBOX_BUMP_FAILURE_SQL_TEMPLATE: str = (
    "UPDATE audit.outbox "
    "SET attempts = attempts + 1, "
    "    last_attempt_at = NOW(), "
    "    next_attempt_at = NOW() + INTERVAL '{seconds}s' "
    "WHERE id = $1"
)


def _backoff_seconds(attempts: int) -> int:
    """Exponential backoff: min(2 ** attempts, 3600) seconds.

    Args:
        attempts: The current ``attempts`` value (before this failure is recorded;
            the formula matches the pre-increment view since the test asserts
            ``~2s`` for the first failure, i.e. ``attempts=0 → 2^1=2``).

    Returns:
        Capped, non-negative integer number of seconds.
    """
    # Bump baseline so the very first retry waits ~2s (per Test 5 in PLAN.md).
    exp = attempts + 1
    if exp < 0:
        exp = 0
    if exp > 16:  # 2**16 = 65536, cap dominates anyway
        exp = 16
    return min(2**exp, 3600)


# The schema is locked at code-review time; only an integer (clamped to
# ``_backoff_seconds`` range) is ever inlined.
def _build_bump_sql(seconds: int) -> str:
    """Build the bump-failure UPDATE with a clamped integer interval.

    The integer is the return of ``_backoff_seconds`` which is always in
    ``[2, 3600]`` — outside the parameter-binding path because PostgreSQL forbids
    parameterizing INTERVAL literals. ``seconds`` is asserted >= 0 here as a
    belt-and-braces guard.
    """
    if not isinstance(seconds, int) or seconds < 0 or seconds > 3600:
        raise ValueError(
            f"backoff seconds must be 0..3600 integer; got {seconds!r}"
        )
    return _OUTBOX_BUMP_FAILURE_SQL_TEMPLATE.format(seconds=seconds)


class OutboxWriter:
    """Enqueue rows into ``audit.outbox`` on NATS publish failure (T-04-Outbox-Drop)."""

    def __init__(self, pool: Any) -> None:
        """Bind to an existing asyncpg pool.

        Args:
            pool: ``asyncpg.Pool`` (or pool-shaped duck type).
        """
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool

    async def enqueue(self, subject: str, payload: bytes) -> UUID:
        """Persist a ``(subject, payload)`` row for later retry.

        Args:
            subject: NATS subject the failed publish targeted. Must be ASCII —
                we validate UTF-8 + ASCII to prevent injection of binary garbage
                into the JSONB column.
            payload: Raw bytes payload (typically ``record.model_dump_json().encode("utf-8")``).

        Returns:
            The UUID PK of the inserted row.

        Raises:
            ValueError: If subject is non-ASCII or payload is not valid UTF-8.
            Any asyncpg error: re-raised so the caller (AuditWriter) can decide.
        """
        if not isinstance(subject, str) or not subject:
            raise ValueError(f"subject must be non-empty str; got {subject!r}")
        try:
            subject.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(
                f"subject must be ASCII (defense-in-depth); got {subject!r}"
            ) from exc

        if not isinstance(payload, (bytes, bytearray)):
            raise ValueError(
                f"payload must be bytes; got {type(payload).__name__}"
            )
        try:
            payload_str = bytes(payload).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "payload must be valid UTF-8 (audit.outbox.payload_json is JSONB)"
            ) from exc

        new_id = uuid4()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                _OUTBOX_INSERT_SQL, new_id, subject, payload_str
            )
        if row is None:
            # Mock paths may return None — surface the id we minted.
            returned_id = new_id
        else:
            returned_id = row["id"]
        logger.info(
            "audit_outbox_enqueued",
            outbox_id=str(returned_id),
            subject=subject,
            payload_bytes=len(payload),
        )
        return returned_id


class OutboxRetry:
    """Background task: re-publish pending ``audit.outbox`` rows via NATS.

    The loop wakes every ``interval_s`` seconds, runs one batch via
    :meth:`run_once`, and continues until :meth:`stop` is called.
    """

    def __init__(
        self,
        pool: Any,
        nats_publisher: Any,
        *,
        interval_s: float = 30.0,
        max_attempts: int = 10,
        batch_size: int = 50,
    ) -> None:
        """Bind dependencies.

        Args:
            pool: asyncpg pool.
            nats_publisher: Object exposing ``publish_raw(subject, payload)`` —
                see :class:`AuditNatsPublisher.publish_raw` extension below.
            interval_s: Sleep between scans (default 30s).
            max_attempts: Rows with ``attempts >= max_attempts`` are skipped
                (Phase 11 dead-letter alerting).
            batch_size: Max rows per scan iteration (default 50).
        """
        if pool is None:
            raise ValueError("pool must not be None")
        if nats_publisher is None:
            raise ValueError("nats_publisher must not be None")
        self._pool = pool
        self._nats = nats_publisher
        self._interval_s = float(interval_s)
        self._max_attempts = int(max_attempts)
        self._batch_size = int(batch_size)
        self._shutdown = asyncio.Event()

    async def run_once(self) -> int:
        """Process up to ``batch_size`` eligible rows; return rows processed.

        Returns:
            Number of rows that were SELECTed (regardless of publish outcome).
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                _OUTBOX_SELECT_SQL, self._max_attempts, self._batch_size
            )
            processed = 0
            for row in rows:
                processed += 1
                row_id: UUID = row["id"]
                subject: str = row["subject"]
                payload_str: str = row["payload_json"]
                attempts: int = row["attempts"]

                payload_bytes = payload_str.encode("utf-8")
                try:
                    await self._nats.publish_raw(subject, payload_bytes)
                except Exception as exc:
                    backoff = _backoff_seconds(attempts)
                    sql = _build_bump_sql(backoff)
                    await conn.execute(sql, row_id)
                    logger.warning(
                        "audit_outbox_retry_failed",
                        outbox_id=str(row_id),
                        subject=subject,
                        attempts=attempts + 1,
                        backoff_s=backoff,
                        error=str(exc),
                    )
                else:
                    await conn.execute(_OUTBOX_MARK_PUBLISHED_SQL, row_id)
                    logger.info(
                        "audit_outbox_retry_published",
                        outbox_id=str(row_id),
                        subject=subject,
                    )
            return processed

    async def run(self) -> None:
        """Main loop: sleep + run_once until ``stop()`` is called.

        Cancellation-safe per ``services/ot-bridge`` flush-loop pattern:
        ``CancelledError`` re-raises; other exceptions are logged + swallowed so
        the task survives transient DB hiccups.
        """
        try:
            while not self._shutdown.is_set():
                try:
                    await asyncio.wait_for(
                        self._shutdown.wait(), timeout=self._interval_s
                    )
                    # Event was set during sleep — break the loop.
                    break
                except asyncio.TimeoutError:
                    pass
                try:
                    await self.run_once()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.error("audit_outbox_retry_loop_error", error=str(exc))
        except asyncio.CancelledError:
            logger.info("audit_outbox_retry_cancelled")
            raise

    async def stop(self) -> None:
        """Signal the loop to exit at the next sleep boundary."""
        self._shutdown.set()
