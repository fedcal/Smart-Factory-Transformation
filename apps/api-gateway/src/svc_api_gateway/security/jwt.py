"""JWT issuance + validation — Plan 10-01 (SRV-01).

Uses PyJWT (import jwt) with HS256 algorithm.
Secret is read from the API_SECRET_KEY environment variable.

DEV-MODE NOTE:
  The fallback default "_dev_only_change_before_production_" is intentionally
  weak and is documented here as a dev-only convenience. It MUST be overridden
  via the API_SECRET_KEY env var in any non-development environment.
  Phase 11 will enforce secret rotation and JWKS-based validation.

SEEDED_USERS:
  Plaintext passwords are acceptable ONLY for dev-mode persona seeding.
  These are NOT production credentials. They will be replaced by a real
  identity provider (Keycloak) in Phase 11.
"""

from __future__ import annotations

import logging as _logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status

# ---------------------------------------------------------------------------
# Secret key — always read from env, dev default documented above (T-10-01-04).
# CR-02: refuse to start with dev default in non-development environments.
# ---------------------------------------------------------------------------

# DEV DEFAULT — override via API_SECRET_KEY env var before any non-dev usage.
_DEV_ONLY_DEFAULT = "_dev_only_change_before_production_"

_DEV_ENVS = frozenset({"development", "dev", "test"})

_raw_secret = os.environ.get("API_SECRET_KEY")
if _raw_secret is None:
    _app_env = os.environ.get("APP_ENV", "development").lower()
    if _app_env not in _DEV_ENVS:
        raise RuntimeError(
            "API_SECRET_KEY env var is required in non-development environments. "
            f"Current APP_ENV={_app_env!r}. "
            "Set API_SECRET_KEY to a strong random secret before starting the gateway."
        )
    _logging.warning(
        "API_SECRET_KEY not set — using insecure dev default. "
        "DO NOT use in production. Set APP_ENV=production and API_SECRET_KEY."
    )
    _raw_secret = _DEV_ONLY_DEFAULT

SECRET_KEY: str = _raw_secret

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

# ---------------------------------------------------------------------------
# Seeded persona users (10-CONTEXT Dev-Mode JWT table, 10-UI-SPEC).
# DEV-MODE ONLY — plaintext passwords are acceptable here per plan decision.
# Replace with a real IdP in Phase 11.
# ---------------------------------------------------------------------------

SEEDED_USERS: dict[str, dict[str, str]] = {
    "operator@mantis.it": {
        "password": "mantis2026",  # dev-mode seed — NOT a production secret
        "role": "operator",
    },
    "supervisor@mantis.it": {
        "password": "mantis2026",  # dev-mode seed — NOT a production secret
        "role": "shift-supervisor",
    },
    "technician@mantis.it": {
        "password": "mantis2026",  # dev-mode seed — NOT a production secret
        "role": "technician",
    },
    "cio@mantis.it": {
        "password": "mantis2026",  # dev-mode seed — NOT a production secret
        "role": "manager",
    },
    "admin@mantis.it": {
        "password": "mantis2026",  # dev-mode seed — NOT a production secret
        "role": "admin",
    },
}


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


def create_token(email: str, role: str) -> str:
    """Issue a signed HS256 JWT for the given email + role.

    Payload claims: sub, email, role, iat, exp.
    Expiry is TOKEN_EXPIRE_HOURS (8 h) from now (tz-aware UTC — CR-04).

    Args:
        email: The user's email address (used as both sub and email claim).
        role:  The user's role string (e.g. "operator", "shift-supervisor").

    Returns:
        A compact JWT string signed with SECRET_KEY / ALGORITHM.
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=TOKEN_EXPIRE_HOURS)

    payload: dict[str, Any] = {
        "sub": email,
        "email": email,
        "role": role,
        "iat": now,
        "exp": exp,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Token decoding / validation
# ---------------------------------------------------------------------------


def decode_token(token: str) -> dict[str, Any]:
    """Validate + decode a compact JWT string.

    Args:
        token: The raw compact JWT (three-part base64url string).

    Returns:
        The decoded payload dict (sub, email, role, iat, exp).

    Raises:
        HTTPException(401, "token_expired"):  JWT has expired.
        HTTPException(401, "token_invalid"):  Signature mismatch or malformed token.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, jwt.DecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )


__all__ = [
    "ALGORITHM",
    "SECRET_KEY",
    "SEEDED_USERS",
    "TOKEN_EXPIRE_HOURS",
    "create_token",
    "decode_token",
]
