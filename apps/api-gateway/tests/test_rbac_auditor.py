"""Test RBAC auditor role (SEC-03) + ActionType.RESTRICTED_DOC_ACCESS (SEC-07).

Tests:
    1. auditor@mantis.it in SEEDED_USERS con role 'auditor' ottiene JWT valido.
    2. Il ruolo 'auditor' è NEGATO (403) su endpoint admin-only (Elevation of Privilege bloccato).
    3. ActionType.RESTRICTED_DOC_ACCESS esiste con .value == 'RESTRICTED_DOC_ACCESS'.

Plan 11-03, Task 1 (SEC-03/SEC-07).
"""

from __future__ import annotations

import pytest
import httpx


# ---------------------------------------------------------------------------
# Test 1: auditor@mantis.it è seeded con role 'auditor'
# ---------------------------------------------------------------------------


def test_auditor_in_seeded_users():
    """auditor@mantis.it deve essere in SEEDED_USERS con role='auditor'."""
    from svc_api_gateway.security.jwt import SEEDED_USERS

    assert "auditor@mantis.it" in SEEDED_USERS, (
        "auditor@mantis.it mancante in SEEDED_USERS (SEC-03)"
    )
    entry = SEEDED_USERS["auditor@mantis.it"]
    assert entry["role"] == "auditor", (
        f"Expected role='auditor', got {entry['role']!r}"
    )
    assert "password" in entry, "Entry deve avere campo 'password'"
    # Nessun secret in chiaro oltre il pattern dev esistente — verificato dal commento nel codice


def test_auditor_login_returns_valid_jwt(app_with_mocks, anyio_backend):
    """POST /auth/login con auditor@mantis.it deve restituire JWT con role=auditor."""
    pass  # usare test HTTP inline per evitare dipendenza da anyio fixture


@pytest.mark.anyio
async def test_auditor_jwt_contains_role_claim(app_with_mocks):
    """POST /auth/login auditor ottiene JWT con claim role=auditor."""
    transport = httpx.ASGITransport(app=app_with_mocks)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/auth/login",
            json={"email": "auditor@mantis.it", "password": "mantis2026"},
        )
    assert resp.status_code == 200, f"Login fallito: {resp.text}"
    data = resp.json()
    assert data["role"] == "auditor", f"Claim role errato: {data!r}"
    assert "access_token" in data


# ---------------------------------------------------------------------------
# Test 2: auditor è NEGATO (403) su endpoint che non lo include (admin-only)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_auditor_denied_on_admin_only_endpoint(app_with_mocks):
    """Il ruolo 'auditor' ottiene 403 su un endpoint che richiede 'admin' — Elevation of Privilege bloccato (SEC-03).

    /auth/me include tutti i ruoli; usiamo un endpoint che non include 'auditor'.
    Qui testiamo direttamente via require_roles per isolare il comportamento RBAC
    senza dipendenza da quale endpoint specifico è admin-only.
    """
    from svc_api_gateway.security.jwt import create_token
    from svc_api_gateway.security.rbac import require_roles

    # Crea token auditor
    token = create_token(email="auditor@mantis.it", role="auditor")

    # Dependency require_roles("admin") deve rifiutare il token auditor con 403
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    dep = require_roles("admin")

    # Creiamo fake credentials con il token auditor
    fake_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        # La dependency è async — chiamiamo direttamente
        await dep(credentials=fake_credentials)

    assert exc_info.value.status_code == 403, (
        f"Atteso 403, ottenuto {exc_info.value.status_code}"
    )
    assert exc_info.value.detail == "rbac_forbidden", (
        f"Detail errato: {exc_info.value.detail!r}"
    )


@pytest.mark.anyio
async def test_auditor_allowed_on_endpoint_that_includes_auditor(app_with_mocks):
    """Il ruolo 'auditor' è AMMESSO su endpoint che include 'auditor' in allowed_roles."""
    from svc_api_gateway.security.jwt import create_token
    from svc_api_gateway.security.rbac import require_roles
    from fastapi.security import HTTPAuthorizationCredentials

    token = create_token(email="auditor@mantis.it", role="auditor")
    dep = require_roles("auditor", "admin")
    fake_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    payload = await dep(credentials=fake_credentials)
    assert payload["role"] == "auditor"
    assert payload["email"] == "auditor@mantis.it"


# ---------------------------------------------------------------------------
# Test 3: ActionType.RESTRICTED_DOC_ACCESS esiste e lockstep con migration 014
# ---------------------------------------------------------------------------


def test_restricted_doc_access_action_type_exists():
    """ActionType.RESTRICTED_DOC_ACCESS esiste e .value == 'RESTRICTED_DOC_ACCESS' (SEC-07/migration-014 lockstep)."""
    from sft_agents.models.enums import ActionType

    assert hasattr(ActionType, "RESTRICTED_DOC_ACCESS"), (
        "ActionType.RESTRICTED_DOC_ACCESS mancante in enums.py (SEC-07)"
    )
    assert ActionType.RESTRICTED_DOC_ACCESS.value == "RESTRICTED_DOC_ACCESS", (
        f"Valore non corrispondente al CHECK di migration 014: {ActionType.RESTRICTED_DOC_ACCESS.value!r}"
    )
