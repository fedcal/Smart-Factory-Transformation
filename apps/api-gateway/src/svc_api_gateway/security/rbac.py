"""RBAC dependency factory — Plan 10-01 (SRV-01, HITL-02) + Plan 10-03 (SSE query-param JWT).

Provides two dependency factories:

1. `require_roles(*allowed_roles)` — reads Bearer token from the Authorization header
   (HTTPBearer). Used by all standard REST endpoints.

2. `require_roles_qs(*allowed_roles)` — reads the `token` query parameter instead of
   the Authorization header. Used ONLY by SSE endpoints because EventSource (browser API)
   cannot set custom headers. The JWT is validated identically (same decode_token call,
   same role enforcement). This is accepted in dev-mode per T-10-03-01; Phase 11 will
   harden to HttpOnly cookie.

The literal string "rbac_forbidden" is a frontend contract (10-UI-SPEC):
the Angular error handler matches this exact string to show the correct
access-denied state — do NOT change it without a coordinated frontend update.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from svc_api_gateway.security.jwt import decode_token

# Single shared HTTPBearer instance — reused across all RBAC-guarded endpoints.
bearer_scheme = HTTPBearer(auto_error=True)


def require_roles(*allowed_roles: str):
    """Factory: return a FastAPI Depends-compatible callable that enforces RBAC.

    Usage:
        @router.get("/protected")
        async def protected(
            principal: dict = Depends(require_roles("operator", "admin"))
        ):
            ...

    Args:
        *allowed_roles: Role strings from the JWT `role` claim that are
                        authorised to access the endpoint.

    Returns:
        A FastAPI dependency callable.  When injected, it returns the decoded
        JWT payload dict if the role is allowed, or raises HTTPException:
            - 401  — bearer_scheme raised it (no / malformed Authorization header)
            - 401  — token_expired or token_invalid (from decode_token)
            - 403  — authenticated but role not in allowed_roles ("rbac_forbidden")
    """
    allowed_set = frozenset(allowed_roles)

    async def _check_roles(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    ) -> dict[str, Any]:
        payload = decode_token(credentials.credentials)

        role: str = payload.get("role", "")
        if role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="rbac_forbidden",  # LOCKED — frontend contract (10-UI-SPEC)
            )

        return payload

    return _check_roles


def require_roles_qs(*allowed_roles: str):
    """Factory: return a FastAPI Depends-compatible callable for SSE query-param JWT auth.

    Reads the JWT from the `token` query parameter instead of the Authorization header.
    This is required for SSE endpoints because the browser EventSource API cannot set
    custom headers (T-10-03-01 / post_research_resolution #2).

    Security: the JWT is validated identically to require_roles via the same decode_token
    call and the same role enforcement. URL exposure is accepted in dev-mode; Phase 11
    will harden to HttpOnly cookie.

    Usage:
        @router.get("/v1/stream/kpi")
        async def kpi_stream(
            principal: dict = Depends(require_roles_qs("operator", "manager"))
        ):
            ...

    Args:
        *allowed_roles: Role strings from the JWT `role` claim that are authorised.

    Returns:
        A FastAPI dependency callable. When injected, returns the decoded JWT payload
        dict if the role is allowed, or raises HTTPException:
            - 401  — missing/empty token query param or token_expired/token_invalid
            - 403  — authenticated but role not in allowed_roles ("rbac_forbidden")
    """
    allowed_set = frozenset(allowed_roles)

    async def _check_roles_qs(
        token: Annotated[str | None, Query(description="JWT token (SSE — EventSource cannot set headers)")] = None,
    ) -> dict[str, Any]:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token_missing",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # decode_token raises 401 on expiry/invalid — propagates unchanged.
        payload = decode_token(token)

        role: str = payload.get("role", "")
        if role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="rbac_forbidden",  # LOCKED — frontend contract (10-UI-SPEC)
            )

        return payload

    return _check_roles_qs


__all__ = ["bearer_scheme", "require_roles", "require_roles_qs"]
