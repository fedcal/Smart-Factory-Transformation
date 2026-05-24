"""Contract tests for RBAC dependency (require_roles guard) — Plan 10-01.

Un-skipped from the Nyquist scaffold in 10-00b.
Verifies the acceptance contract the RBAC dependency must satisfy.

Pattern: the `require_roles` FastAPI dependency is injected on a protected
endpoint.  The test builds a JWT token via create_token (or make_test_token
fixture) and calls the endpoint to verify role enforcement.

The /auth/me endpoint is used as the RBAC-guarded route (created in Plan 10-01).
It accepts all five seeded persona roles.

Ref: 10-CONTEXT.md (Auth/RBAC decisions), 10-UI-SPEC.md (Route per persona table).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Generic detail string for RBAC denial — locked by contract so the frontend
# can match it for the 403 error state.
RBAC_FORBIDDEN_DETAIL = "rbac_forbidden"

# A protected endpoint created by Plan 10-01, guarded by require_roles.
# /auth/me accepts all five seeded roles — used for allowed-role tests.
ME_ROUTE = "/auth/me"


# ---------------------------------------------------------------------------
# Forbidden: token with unrecognised role → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rbac_forbidden_when_role_not_allowed(client, make_test_token) -> None:
    """A JWT with an unrecognised role accessing /auth/me → 403.

    /auth/me uses require_roles(*_ALL_ROLES) where _ALL_ROLES is the set of
    the five seeded persona roles.  A token whose role claim is not in that set
    (e.g. "unknown-role") must receive exactly "rbac_forbidden".

    The response JSON detail must equal the literal string "rbac_forbidden"
    so the Angular error handler can recognise it (10-UI-SPEC copywriting contract).
    """
    unknown_role_token = make_test_token("unknown-role")

    response = await client.get(
        ME_ROUTE,
        headers={"Authorization": f"Bearer {unknown_role_token}"},
    )
    assert response.status_code == 403

    body = response.json()
    assert body.get("detail") == RBAC_FORBIDDEN_DETAIL, (
        f"Expected detail={RBAC_FORBIDDEN_DETAIL!r}, got {body.get('detail')!r}"
    )


@pytest.mark.asyncio
async def test_rbac_forbidden_when_no_token(client) -> None:
    """No Authorization header on a protected route → 401 (not authenticated).

    Distinction: 401 = not authenticated; 403 = authenticated but not authorised.
    HTTPBearer with auto_error=True raises 403 by default when no credentials are
    provided.  FastAPI wraps this as a 403 from HTTPBearer; however, semantically
    the contract is that unauthenticated requests are rejected (4xx) — so we
    assert status_code in (401, 403) to cover both FastAPI versions.
    """
    response = await client.get(ME_ROUTE)
    assert response.status_code in (401, 403), (
        f"Expected 401 or 403 for missing token, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Allowed: token with correct role → 200 (or non-403)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rbac_allowed_when_role_matches(client, make_test_token) -> None:
    """A JWT with role 'operator' accessing /auth/me → 200 (not 403/401).

    The test asserts that RBAC does not block the request.
    """
    operator_token = make_test_token("operator", email="operator@mantis.it")

    response = await client.get(
        ME_ROUTE,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response.status_code not in (401, 403), (
        f"RBAC blocked a valid operator token: {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Multi-role guard: /auth/me accepts all five seeded persona roles
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rbac_multi_role_allows_all_listed_roles(client, make_test_token) -> None:
    """Each of the five seeded persona roles is accepted by /auth/me.

    /auth/me uses require_roles(*_ALL_ROLES) which includes all seeded personas.
    Ref: 10-UI-SPEC Route /manager row — shift-supervisor + manager roles allowed.
    """
    roles_and_emails = [
        ("operator", "operator@mantis.it"),
        ("shift-supervisor", "supervisor@mantis.it"),
        ("technician", "technician@mantis.it"),
        ("manager", "cio@mantis.it"),
        ("admin", "admin@mantis.it"),
    ]

    for role, email in roles_and_emails:
        token = make_test_token(role, email=email)
        response = await client.get(
            ME_ROUTE,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code not in (401, 403), (
            f"Multi-role RBAC unexpectedly blocked token for role: {role!r}"
        )
