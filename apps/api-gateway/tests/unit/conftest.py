"""Unit-test fixtures specific to the security package tests (Plan 10-01).

Provides:
    make_test_token  — callable that returns a valid signed JWT for a given role
                       (used by test_rbac.py to replace PLACEHOLDER tokens)

These fixtures complement the parent conftest.py (tests/conftest.py) which
provides app_with_mocks + client.  Pytest discovers both via its conftest chain.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def make_test_token():
    """Return a factory that creates a signed JWT for the given role.

    Usage in tests:
        token = make_test_token("operator")
        token = make_test_token("shift-supervisor")

    The token is signed with the current SECRET_KEY (dev default unless
    API_SECRET_KEY env var is set).  Valid for TOKEN_EXPIRE_HOURS.
    """
    from svc_api_gateway.security.jwt import create_token

    def _factory(role: str, email: str | None = None) -> str:
        resolved_email = email or f"{role.replace('-', '.')}@mantis.it"
        return create_token(email=resolved_email, role=role)

    return _factory
