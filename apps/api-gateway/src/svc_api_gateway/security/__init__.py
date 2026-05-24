"""Security package — Plan 10-01 (SRV-01, HITL-02).

Exports:
    create_token    — issue a HS256 JWT for a seeded persona
    decode_token    — validate + decode a bearer token (raises 401 on failure)
    require_roles   — FastAPI dependency factory for RBAC enforcement
    SEEDED_USERS    — dev-mode persona registry {email: {password, role}}
"""

from __future__ import annotations

from svc_api_gateway.security.jwt import SEEDED_USERS, create_token, decode_token
from svc_api_gateway.security.rbac import require_roles

__all__ = [
    "SEEDED_USERS",
    "create_token",
    "decode_token",
    "require_roles",
]
