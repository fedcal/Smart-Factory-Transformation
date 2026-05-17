"""
tests/conftest.py

Shared pytest fixtures for the Smart Factory Transformation test suite.

Provides module-scoped path fixtures for domain analysis pages and
synthetic corpus directories. All paths use pathlib.Path exclusively
(no string concatenation or os.path usage — security V12 path-traversal
mitigation as required by the threat model T-02-10).
"""

import pathlib

import pytest


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
