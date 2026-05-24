"""RBAC dependency factory — Plan 10-01 (SRV-01, HITL-02).

Provides `require_roles(*allowed_roles)` — a FastAPI dependency factory that:
1. Extracts the Bearer token from the Authorization header (HTTPBearer).
2. Validates + decodes the JWT via decode_token.
3. Checks that the token's `role` claim is in the allowed set.
4. Returns the payload dict on success.
5. Raises HTTP 403 "rbac_forbidden" if role is not allowed (T-10-01-02).

The literal string "rbac_forbidden" is a frontend contract (10-UI-SPEC):
the Angular error handler matches this exact string to show the correct
access-denied state — do NOT change it without a coordinated frontend update.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
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


__all__ = ["bearer_scheme", "require_roles"]
