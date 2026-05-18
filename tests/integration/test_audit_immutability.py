"""
tests/integration/test_audit_immutability.py

Phase 4 Plan 04-02 — DB-layer enforcement of HITL-05.

Verifies that the ``REVOKE UPDATE, DELETE ON audit.actions FROM agent_role``
statement in ``003_create_audit_actions.sql`` is mechanically effective:

  1. agent_role can INSERT and SELECT rows from audit.actions
  2. agent_role CANNOT UPDATE rows (permission denied)
  3. agent_role CANNOT DELETE rows (permission denied)
  4. has_table_privilege reports the correct grant matrix

This is the T-04-Audit-Tamper mitigation gate: even an attacker with full
application-tier compromise (the agent_role connection string) cannot rewrite
audit history because Postgres rejects the statements at the DB engine.

Requires Docker (testcontainers). Gated by ``@pytest.mark.integration``.
"""
from __future__ import annotations

import json
import sys
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


_TIMESCALE_IMAGE = "timescale/timescaledb:2.18.0-pg16"
_DB_USER = "sft"
_DB_PASS = "sft_dev_pass"
_DB_NAME = "sft"


@pytest.fixture(scope="module")
def audit_test_dsn() -> Generator[str, None, None]:
    """Module-scoped testcontainer for audit immutability tests."""
    pytest.importorskip("testcontainers.postgres")
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer(
        image=_TIMESCALE_IMAGE,
        username=_DB_USER,
        password=_DB_PASS,
        dbname=_DB_NAME,
    ) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        dsn = f"postgresql://{_DB_USER}:{_DB_PASS}@{host}:{port}/{_DB_NAME}"
        yield dsn


async def _ensure_migrated(dsn: str) -> None:
    """Apply Phase 4 migrations exactly once per test module."""
    from infra.migrations.timescale.migrate import migrate  # noqa: PLC0415

    rc = await migrate(dsn)
    assert rc == 0, "Phase 4 migrations must apply successfully"


async def _insert_seed_row_as_superuser(dsn: str) -> uuid.UUID:
    """Insert a seed audit row as superuser; return its action_id for later asserts."""
    import asyncpg  # noqa: PLC0415

    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        action_id = uuid.uuid4()
        await conn.execute(
            "INSERT INTO audit.actions ("
            "  action_id, agent_id, thread_id, cluster, action_type,"
            "  evidence_panel, decision"
            ") VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)",
            action_id,
            "agent.test",
            "thread-test-001",
            "ops",
            "diagnostic_query",
            json.dumps({"input_summary": "seed row", "rag_citations": []}),
            "auto",
        )
        return action_id
    finally:
        await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_role_can_insert_and_select(audit_test_dsn: str) -> None:
    """agent_role can INSERT a new audit row and SELECT it back."""
    import asyncpg  # noqa: PLC0415

    await _ensure_migrated(audit_test_dsn)

    conn = await asyncpg.connect(audit_test_dsn, statement_cache_size=0)
    try:
        # Wrap in a transaction so SET LOCAL ROLE persists across statements
        # (SET LOCAL is bound to the current transaction; outside a tx it is a no-op).
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE agent_role")

            action_id = uuid.uuid4()
            await conn.execute(
                "INSERT INTO audit.actions ("
                "  action_id, agent_id, thread_id, cluster, action_type,"
                "  evidence_panel, decision"
                ") VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)",
                action_id,
                "agent.role.insert",
                "thread-insert-001",
                "ops",
                "diagnostic_query",
                json.dumps({"input_summary": "agent_role insert", "rag_citations": []}),
                "auto",
            )

            count = await conn.fetchval(
                "SELECT COUNT(*) FROM audit.actions WHERE action_id = $1",
                action_id,
            )
            assert count == 1, "agent_role must be able to INSERT and SELECT audit.actions"
    finally:
        await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_role_cannot_update(audit_test_dsn: str) -> None:
    """UPDATE on audit.actions as agent_role raises InsufficientPrivilegeError."""
    import asyncpg  # noqa: PLC0415

    await _ensure_migrated(audit_test_dsn)
    action_id = await _insert_seed_row_as_superuser(audit_test_dsn)

    conn = await asyncpg.connect(audit_test_dsn, statement_cache_size=0)
    try:
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError) as exc:
            async with conn.transaction():
                # SET LOCAL is scoped to the surrounding transaction.
                await conn.execute("SET LOCAL ROLE agent_role")
                await conn.execute(
                    "UPDATE audit.actions SET motivation = $1 WHERE action_id = $2",
                    "tampering attempt",
                    action_id,
                )
        assert "permission denied" in str(exc.value).lower(), (
            f"expected permission denied; got: {exc.value!r}"
        )
    finally:
        await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_role_cannot_delete(audit_test_dsn: str) -> None:
    """DELETE on audit.actions as agent_role raises InsufficientPrivilegeError."""
    import asyncpg  # noqa: PLC0415

    await _ensure_migrated(audit_test_dsn)
    action_id = await _insert_seed_row_as_superuser(audit_test_dsn)

    conn = await asyncpg.connect(audit_test_dsn, statement_cache_size=0)
    try:
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError) as exc:
            async with conn.transaction():
                await conn.execute("SET LOCAL ROLE agent_role")
                await conn.execute(
                    "DELETE FROM audit.actions WHERE action_id = $1",
                    action_id,
                )
        assert "permission denied" in str(exc.value).lower(), (
            f"expected permission denied; got: {exc.value!r}"
        )
    finally:
        await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_privilege_matrix_via_has_table_privilege(audit_test_dsn: str) -> None:
    """has_table_privilege reports INSERT+SELECT yes; UPDATE+DELETE no."""
    import asyncpg  # noqa: PLC0415

    await _ensure_migrated(audit_test_dsn)

    conn = await asyncpg.connect(audit_test_dsn, statement_cache_size=0)
    try:
        results = {
            priv: await conn.fetchval(
                "SELECT has_table_privilege('agent_role','audit.actions', $1)",
                priv,
            )
            for priv in ("INSERT", "SELECT", "UPDATE", "DELETE")
        }
        assert results == {
            "INSERT": True,
            "SELECT": True,
            "UPDATE": False,
            "DELETE": False,
        }, f"unexpected privilege matrix: {results}"
    finally:
        await conn.close()
