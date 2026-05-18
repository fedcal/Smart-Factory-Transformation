"""
tests/conftest.py

Shared pytest fixtures for the Smart Factory Transformation test suite.

Provides:
- Module-scoped path fixtures for domain analysis pages and synthetic corpus directories.
- Session-scoped compose_stack fixture for IT/OT integration tests (Phase 3).

All paths use pathlib.Path exclusively (no string concatenation or os.path usage —
security V12 path-traversal mitigation as required by the threat model T-02-10).
"""

import pathlib
import subprocess
import time

import pytest


# ---------------------------------------------------------------------------
# Domain page fixtures (Phase 2)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def domain_dir() -> pathlib.Path:
    """Return the root directory of IT domain analysis pages.

    The path is computed relative to this conftest so it works regardless
    of the cwd from which pytest is invoked (typically the repo root).
    """
    return pathlib.Path(__file__).parent.parent / "docs" / "docs" / "domain"


@pytest.fixture(scope="module")
def processes_dir(domain_dir: pathlib.Path) -> pathlib.Path:
    """Return the processes sub-directory of the IT domain analysis."""
    return domain_dir / "processes"


@pytest.fixture(scope="module")
def roles_dir(domain_dir: pathlib.Path) -> pathlib.Path:
    """Return the roles sub-directory of the IT domain analysis."""
    return domain_dir / "roles"


# ---------------------------------------------------------------------------
# pytest marker registration (Phase 3)
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest markers for Phase 3 IT/OT tests."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests requiring docker-compose stack",
    )
    config.addinivalue_line(
        "markers",
        "load: marks tests as load/performance tests",
    )
    config.addinivalue_line(
        "markers",
        "load_smoke: marks tests as smoke load tests (1k×10s CI gate)",
    )
    config.addinivalue_line(
        "markers",
        "load_full: marks tests as full load tests (5k×60s PR-label gated)",
    )
    config.addinivalue_line(
        "markers",
        "e2e: marks tests as full-stack end-to-end (docker compose required)",
    )


# ---------------------------------------------------------------------------
# IT/OT stack lifecycle fixture (Phase 3)
# ---------------------------------------------------------------------------

# Repo root computed relative to this file (robust against any cwd)
_REPO_ROOT = pathlib.Path(__file__).parent.parent

_COMPOSE_CORE = str(_REPO_ROOT / "infra" / "compose" / "core.yml")
_COMPOSE_SIM = str(_REPO_ROOT / "infra" / "compose" / "sim.yml")


@pytest.fixture(scope="session")
def compose_stack() -> dict:  # type: ignore[return]
    """Session-scoped fixture: starts full IT/OT docker-compose stack.

    Starts: timescaledb + redis + qdrant + nats + sim-textile + ot-bridge.
    Yields a dict with connection endpoints for use by integration tests.
    Tears down after all tests in the session complete.

    Skips (not fails) if docker is not available — allows the test suite
    to run in environments without docker without breaking non-integration tests.
    """
    # Check docker availability
    docker_check = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
    )
    if docker_check.returncode != 0:
        pytest.skip("docker not available — skipping integration tests")
        return  # unreachable but satisfies type checker

    # Bring up the full stack
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            _COMPOSE_CORE,
            "-f",
            _COMPOSE_SIM,
            "up",
            "-d",
            "--wait",
        ],
        check=True,
        cwd=str(_REPO_ROOT),
    )

    # Allow sim-textile extra warmup time for OPC-UA emission to start
    time.sleep(5)

    endpoints = {
        "TIMESCALE_DSN": "postgresql://sft:sft_dev_pass@localhost:5432/sft",
        "NATS_URL": "nats://localhost:4222",
        "OPCUA_URL": "opc.tcp://localhost:4840",
    }

    yield endpoints

    # Teardown: stop and remove containers + volumes
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            _COMPOSE_CORE,
            "-f",
            _COMPOSE_SIM,
            "down",
            "-v",
        ],
        check=False,  # non-fatal teardown
        cwd=str(_REPO_ROOT),
    )
