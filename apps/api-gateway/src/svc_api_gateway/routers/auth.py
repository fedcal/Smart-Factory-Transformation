"""POST /auth/login + GET /auth/me — Plan 10-01 (SRV-01, HITL-02).

Endpoints:
    POST /auth/login   — exchange dev-mode credentials for a HS256 JWT
    GET  /auth/me      — echo the authenticated principal (sub, email, role)

Security contract (T-10-01-03 — Information Disclosure):
    - 401 detail is always "invalid_credentials" (generic, no user enumeration)
    - 500 detail is always "internal_server_error" (no exception text in body)
    - Detailed errors are logged server-side only via structlog.error

Request model is Pydantic with extra="forbid", frozen=True (CR-03).
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr

from svc_api_gateway.security.jwt import SEEDED_USERS, create_token
from svc_api_gateway.security.rbac import require_roles

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# All seeded persona roles — used for /auth/me (any authenticated user passes).
_ALL_ROLES = ("operator", "shift-supervisor", "technician", "manager", "admin")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Credentials for POST /auth/login (dev-mode seeded personas only).

    extra="forbid" and frozen=True enforce strict input validation (CR-03).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: str
    password: str


class LoginResponse(BaseModel):
    """Successful login response containing a signed JWT."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str
    role: str


class MeResponse(BaseModel):
    """Principal echo for GET /auth/me."""

    model_config = ConfigDict(frozen=True)

    sub: str
    email: str
    role: str


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate with dev-mode seeded credentials",
)
async def post_login(body: LoginRequest) -> LoginResponse:
    """Exchange dev-mode persona credentials for a signed HS256 JWT.

    On success returns { access_token, token_type: "bearer", role }.
    On failure always returns HTTP 401 with generic detail "invalid_credentials"
    to avoid leaking user enumeration information (T-10-01-03 / CR-02).
    """
    try:
        user = SEEDED_USERS.get(body.email)

        # Constant-time-ish comparison: check both email existence and password
        # in the same code path to reduce timing-oracle risk.  For dev-mode this
        # is acceptable; Phase 11 will use a real constant-time PBKDF2 compare.
        if user is None or user["password"] != body.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_credentials",  # generic — no user enumeration (T-10-01-03)
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_token(email=body.email, role=user["role"])
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            role=user["role"],
        )

    except HTTPException:
        raise  # propagate auth errors as-is

    except Exception as exc:  # noqa: BLE001
        # Wrap unexpected errors: log detail server-side, return generic 500 body (CR-02).
        logger.error(
            "auth_login_unexpected_error",
            email=body.email,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal_server_error",  # no exception text in body (T-10-01-03)
        )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the authenticated principal",
)
async def get_me(
    principal: dict[str, Any] = Depends(require_roles(*_ALL_ROLES)),
) -> MeResponse:
    """Echo the decoded JWT principal: sub, email, role.

    Requires a valid Bearer token with any recognised role.  The RBAC dependency
    handles 401 (no/invalid token) and 403 (unknown role) automatically.
    """
    return MeResponse(
        sub=principal.get("sub", ""),
        email=principal.get("email", ""),
        role=principal.get("role", ""),
    )


__all__ = ["router"]
