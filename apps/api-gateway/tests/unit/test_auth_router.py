"""Contract scaffold for POST /auth/login (JWT issuance).

Nyquist scaffold — all tests skipped until implementation in Plan 10-01.
Each test describes the acceptance contract the auth router MUST satisfy.

THREAT: T-10-00b-02 — error detail must be generic (no internal exception text).
Ref: 10-CONTEXT.md (Dev-Mode JWT), 10-UI-SPEC.md (Dev-Mode JWT Seeded Persona Users).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Seeded persona users (10-UI-SPEC Dev-Mode JWT table)
# ---------------------------------------------------------------------------
OPERATOR_EMAIL = "operator@mantis.it"
OPERATOR_PASSWORD = "mantis2026"          # dev-mode seed — NOT a secret

SUPERVISOR_EMAIL = "supervisor@mantis.it"
TECHNICIAN_EMAIL = "technician@mantis.it"
CIO_EMAIL = "cio@mantis.it"
ADMIN_EMAIL = "admin@mantis.it"

# JWT payload keys that MUST appear after decoding (HS256, API_SECRET_KEY)
REQUIRED_CLAIMS = {"sub", "email", "role", "exp"}


# ---------------------------------------------------------------------------
# Happy-path: operator login returns 200 + valid JWT
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="impl in 10-01 — auth router not yet created")
@pytest.mark.asyncio
async def test_login_operator_returns_200_with_jwt(client) -> None:
    """POST /auth/login with operator@mantis.it credentials returns HTTP 200.

    Response body shape:
        { "access_token": "<jwt>", "token_type": "bearer" }

    The decoded JWT payload (HS256) must contain: sub, email, role, exp.
    The role claim must equal "operator".
    """
    response = await client.post(
        "/auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD},
    )
    assert response.status_code == 200

    body = response.json()
    assert "access_token" in body
    assert body.get("token_type") == "bearer"

    # Decode without verification (scaffold only — impl will verify signature)
    import base64, json as _json
    payload_b64 = body["access_token"].split(".")[1]
    # Add padding
    payload_b64 += "=" * (-len(payload_b64) % 4)
    payload = _json.loads(base64.urlsafe_b64decode(payload_b64))

    assert REQUIRED_CLAIMS.issubset(payload.keys()), (
        f"JWT missing claims: {REQUIRED_CLAIMS - payload.keys()}"
    )
    assert payload["email"] == OPERATOR_EMAIL
    assert payload["role"] == "operator"


@pytest.mark.skip(reason="impl in 10-01 — auth router not yet created")
@pytest.mark.asyncio
async def test_login_all_seeded_personas_return_200(client) -> None:
    """Each seeded persona can authenticate.  Role is embedded in the JWT claim."""
    personas = [
        (OPERATOR_EMAIL, "operator"),
        (SUPERVISOR_EMAIL, "shift-supervisor"),
        (TECHNICIAN_EMAIL, "technician"),
        (CIO_EMAIL, "manager"),
        (ADMIN_EMAIL, "admin"),
    ]
    for email, expected_role in personas:
        response = await client.post(
            "/auth/login",
            json={"email": email, "password": OPERATOR_PASSWORD},
        )
        assert response.status_code == 200, f"Login failed for {email}"
        token = response.json()["access_token"]
        # Minimal claim check (full decode in test_login_operator_returns_200_with_jwt)
        assert len(token.split(".")) == 3, "Expected a three-part JWT"


# ---------------------------------------------------------------------------
# Error cases — THREAT T-10-00b-02: detail must be GENERIC (no exc text)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="impl in 10-01 — auth router not yet created")
@pytest.mark.asyncio
async def test_login_bad_password_returns_401_token_invalid(client) -> None:
    """Wrong password → HTTP 401.

    The JSON detail key must be the literal string "token-invalid" or
    "credentials" (no exception text, no traceback) — CR-02 / T-10-00b-02.
    """
    response = await client.post(
        "/auth/login",
        json={"email": OPERATOR_EMAIL, "password": "wrong-password"},
    )
    assert response.status_code == 401

    detail = response.json().get("detail", "")
    ALLOWED_DETAIL_TOKENS = {"token-invalid", "credentials"}
    assert any(tok in detail for tok in ALLOWED_DETAIL_TOKENS), (
        f"Unexpected 401 detail (must be generic): {detail!r}"
    )
    # CR-02: must NOT leak exception text
    assert "Exception" not in detail
    assert "Traceback" not in detail


@pytest.mark.skip(reason="impl in 10-01 — auth router not yet created")
@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client) -> None:
    """Unknown email → HTTP 401 (same generic body — timing-safe response)."""
    response = await client.post(
        "/auth/login",
        json={"email": "nobody@mantis.it", "password": "anything"},
    )
    assert response.status_code == 401
    detail = response.json().get("detail", "")
    assert "Exception" not in detail
    assert "Traceback" not in detail


@pytest.mark.skip(reason="impl in 10-01 — auth router not yet created")
@pytest.mark.asyncio
async def test_login_missing_fields_returns_422(client) -> None:
    """Request body without required fields → HTTP 422 (FastAPI validation)."""
    response = await client.post("/auth/login", json={})
    assert response.status_code == 422
