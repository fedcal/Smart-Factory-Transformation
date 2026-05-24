"""Contract scaffold for RBAC dependency (require_roles guard).

Nyquist scaffold — all tests skipped until implementation in Plan 10-01.
Describes the acceptance contract the RBAC dependency MUST satisfy.

Pattern: the `require_roles` FastAPI dependency is injected on a protected
endpoint; the test builds a JWT token (or uses a stub) and calls the endpoint.

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

# A protected endpoint that only operator role can access.
# When 10-01 creates the route, the path must match or this test is updated.
OPERATOR_PROTECTED_ROUTE = "/v1/approvals"   # or any route guarded by operator role


# ---------------------------------------------------------------------------
# Forbidden: token with wrong role → 403
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="impl in 10-01 — RBAC dependency + auth router not yet created")
@pytest.mark.asyncio
async def test_rbac_forbidden_when_role_not_allowed(client) -> None:
    """A JWT with role 'technician' accessing an operator-only endpoint → 403.

    The response JSON detail must equal the literal string "rbac_forbidden"
    so the Angular error handler can recognise it (10-UI-SPEC copywriting contract).
    """
    # Build a minimal bearer token for the wrong role (technician cannot access approvals)
    # Implementation note: in 10-01 a helper `make_test_token(role)` will live in conftest.
    wrong_role_token = "PLACEHOLDER_technician_jwt"  # replaced by impl

    response = await client.get(
        OPERATOR_PROTECTED_ROUTE,
        headers={"Authorization": f"Bearer {wrong_role_token}"},
    )
    assert response.status_code == 403

    body = response.json()
    assert body.get("detail") == RBAC_FORBIDDEN_DETAIL, (
        f"Expected detail={RBAC_FORBIDDEN_DETAIL!r}, got {body.get('detail')!r}"
    )


@pytest.mark.skip(reason="impl in 10-01 — RBAC dependency + auth router not yet created")
@pytest.mark.asyncio
async def test_rbac_forbidden_when_no_token(client) -> None:
    """No Authorization header on a protected route → 401 (not authenticated).

    Distinction: 401 = not authenticated; 403 = authenticated but not authorised.
    """
    response = await client.get(OPERATOR_PROTECTED_ROUTE)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Allowed: token with correct role → 200 (or non-403)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="impl in 10-01 — RBAC dependency + auth router not yet created")
@pytest.mark.asyncio
async def test_rbac_allowed_when_role_matches(client) -> None:
    """A JWT with role 'operator' accessing an operator-only endpoint → 200 (not 403).

    The test does not assert a specific business response; it only asserts that
    RBAC does not block the request (status != 403 and != 401).
    """
    correct_role_token = "PLACEHOLDER_operator_jwt"  # replaced by impl

    response = await client.get(
        OPERATOR_PROTECTED_ROUTE,
        headers={"Authorization": f"Bearer {correct_role_token}"},
    )
    assert response.status_code not in (401, 403), (
        f"RBAC blocked a valid operator token: {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Multi-role guard: supervisor route accessible by supervisor AND manager
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="impl in 10-01 — RBAC dependency + auth router not yet created")
@pytest.mark.asyncio
async def test_rbac_multi_role_allows_all_listed_roles(client) -> None:
    """A route guarded by require_roles(['shift-supervisor', 'manager']) allows both.

    Ref: 10-UI-SPEC Route /manager row — shift-supervisor + manager roles allowed.
    """
    MANAGER_ROUTE = "/v1/kpi/snapshot"   # will be created in 10-02

    for role_token in ("PLACEHOLDER_supervisor_jwt", "PLACEHOLDER_manager_jwt"):
        response = await client.get(
            MANAGER_ROUTE,
            headers={"Authorization": f"Bearer {role_token}"},
        )
        assert response.status_code not in (401, 403), (
            f"Multi-role RBAC unexpectedly blocked token for role: {role_token}"
        )
