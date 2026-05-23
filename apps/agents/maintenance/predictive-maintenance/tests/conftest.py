"""Pytest fixtures for the PredictiveMaintenance agent tests (Plan 07-06).

Provides mocks for the agent's three injected collaborators:
* ``mock_audit_writer`` — AsyncMock with a single ``write(AuditRecord)``
  coroutine; tests inspect ``.call_args_list`` to assert decision / action_type.
* ``mock_query_tool`` — AsyncMock with ``_arun`` returning a pandas.DataFrame.
  Each test sets the per-asset return mapping via ``.return_value`` or ``.side_effect``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_audit_writer() -> AsyncMock:
    """Return an AsyncMock with an awaitable ``write(record)`` method."""
    writer = AsyncMock()
    writer.write = AsyncMock(return_value=None)
    return writer


@pytest.fixture
def mock_query_tool() -> AsyncMock:
    """Return an AsyncMock with an awaitable ``_arun(...)`` method.

    Tests override the return value (or ``.side_effect``) per case.
    """
    tool = AsyncMock()
    tool._arun = AsyncMock(return_value=None)
    return tool
