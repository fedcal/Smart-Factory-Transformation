"""Unit tests for SECRET_KEY startup guard — CR-02.

Verifies that the jwt module raises RuntimeError when API_SECRET_KEY is
unset AND APP_ENV is not a dev/test environment, preventing the gateway
from starting silently with the insecure dev default in production.

Plan: 10-01 (SRV-01) — CR-02 fix.
"""

from __future__ import annotations

import importlib
import sys
import os
import pytest


def _reload_jwt_module(env: dict[str, str]) -> object:
    """Reload svc_api_gateway.security.jwt with a custom os.environ snapshot.

    Returns the reloaded module or raises RuntimeError if the guard fires.
    Restores os.environ and sys.modules after each call.
    """
    original_environ = os.environ.copy()
    original_module = sys.modules.pop("svc_api_gateway.security.jwt", None)
    try:
        os.environ.clear()
        os.environ.update(env)
        import svc_api_gateway.security.jwt as mod
        return mod
    finally:
        # Restore state regardless of success/failure
        os.environ.clear()
        os.environ.update(original_environ)
        # Remove the freshly imported module so other tests see a clean slate
        sys.modules.pop("svc_api_gateway.security.jwt", None)
        if original_module is not None:
            sys.modules["svc_api_gateway.security.jwt"] = original_module


# ---------------------------------------------------------------------------
# CR-02: guard must raise RuntimeError in non-dev envs without API_SECRET_KEY
# ---------------------------------------------------------------------------


def test_raises_runtime_error_when_secret_missing_in_production() -> None:
    """CR-02: importing jwt with APP_ENV=production and no API_SECRET_KEY
    must raise RuntimeError — the gateway must not start with the dev default."""
    with pytest.raises(RuntimeError, match="API_SECRET_KEY env var is required"):
        _reload_jwt_module({"APP_ENV": "production"})


def test_raises_runtime_error_when_secret_missing_in_staging() -> None:
    """CR-02: APP_ENV=staging without API_SECRET_KEY must also raise."""
    with pytest.raises(RuntimeError, match="API_SECRET_KEY env var is required"):
        _reload_jwt_module({"APP_ENV": "staging"})


def test_no_error_when_api_secret_key_is_set_in_production() -> None:
    """CR-02: if API_SECRET_KEY is set, the guard must not raise even in production."""
    mod = _reload_jwt_module(
        {"APP_ENV": "production", "API_SECRET_KEY": "a-very-strong-random-secret-32chars"}
    )
    assert mod.SECRET_KEY == "a-very-strong-random-secret-32chars"


def test_dev_default_allowed_in_development_env() -> None:
    """CR-02: in APP_ENV=development without API_SECRET_KEY, the dev default is used
    (with a warning log — no RuntimeError)."""
    mod = _reload_jwt_module({"APP_ENV": "development"})
    assert mod.SECRET_KEY == "_dev_only_change_before_production_"


def test_dev_default_allowed_when_app_env_not_set() -> None:
    """CR-02: when APP_ENV is unset, the guard defaults to 'development' and allows
    the dev default (no RuntimeError)."""
    mod = _reload_jwt_module({})
    assert mod.SECRET_KEY == "_dev_only_change_before_production_"


def test_dev_default_allowed_in_test_env() -> None:
    """CR-02: APP_ENV=test without API_SECRET_KEY is allowed (test runs don't require
    a real secret)."""
    mod = _reload_jwt_module({"APP_ENV": "test"})
    assert mod.SECRET_KEY == "_dev_only_change_before_production_"


def test_explicit_secret_overrides_dev_default_in_dev() -> None:
    """CR-02: if API_SECRET_KEY is set even in dev, it must be used (not the default)."""
    mod = _reload_jwt_module(
        {"APP_ENV": "dev", "API_SECRET_KEY": "explicit-custom-secret"}
    )
    assert mod.SECRET_KEY == "explicit-custom-secret"
