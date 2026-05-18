"""
tests/load/conftest.py

pytest options per i load test IT/OT (Phase 3).

Registra il flag --full-load-test che abilita il test 5k×60s (IOT-10 full gate).
Il test è gated per evitare runtime eccessivo in CI default: viene eseguito solo
su demand tramite PR label `load-test` o flag esplicito (D-48 + CI strategy claudes_discretion).
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Aggiunge opzione --full-load-test al runner pytest.

    Args:
        parser: pytest argument parser.
    """
    parser.addoption(
        "--full-load-test",
        action="store_true",
        default=False,
        help="Enable full 5k×60s load test (IOT-10 full gate). "
        "Richiesto da: make load-test-full o CI PR-label load-test.",
    )
