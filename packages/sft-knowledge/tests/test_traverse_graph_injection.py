"""Regression tests for TraverseGraphTool._arun Cypher injection bypass (CR-01).

Gap closure for VERIFICATION.md gap 1 (KNW-09 BLOCKER):
    TraverseGraphTool._arun() accepts arbitrary strings for seed_label and
    relation_path when called directly, bypassing the Pydantic Literal whitelist
    that only fires on the args_schema/ainvoke() entry path.

Verifier-reproduced payload:
    seed_label='Machine) DETACH DELETE n MATCH (x'
    => composes destructive Cypher that destroys the Neo4j graph.

These tests must FAIL (RED) against the unfixed graph.py because direct
_arun calls do not re-validate inputs before composing Cypher.
After the fix (Task 2 GREEN), all tests must PASS.

Plan: 05-11, Task 1 (RED gate).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from sft_knowledge.tools.graph import TraverseGraphTool


# ---------------------------------------------------------------------------
# Async driver mock helpers
# ---------------------------------------------------------------------------


class _EmptyAsyncIterator:
    """Async iterator that yields no records (empty traversal result)."""

    def __aiter__(self) -> _EmptyAsyncIterator:
        return self

    async def __anext__(self) -> Any:
        raise StopAsyncIteration


def _make_mock_driver() -> MagicMock:
    """Build a MagicMock async Neo4j driver.

    The driver.session() call returns an async context manager whose
    run() returns an async iterator over zero records.
    """
    driver = MagicMock()

    # session.run() returns an empty async iterator
    mock_result = _EmptyAsyncIterator()
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)

    # driver.session() is a sync call returning an async context manager
    @asynccontextmanager
    async def _session_ctx(*args: Any, **kwargs: Any) -> AsyncIterator[AsyncMock]:
        yield mock_session

    driver.session = _session_ctx
    return driver, mock_session


# ---------------------------------------------------------------------------
# Test 1: injection via seed_label
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arun_rejects_injection_seed_label() -> None:
    """_arun MUST raise ValidationError for seed_label='Machine) DETACH DELETE n MATCH (x'.

    The verifier-reproduced payload (VERIFICATION.md gap 1) must be rejected
    BEFORE any Cypher is composed — i.e. before driver.session() is called.
    """
    driver, mock_session = _make_mock_driver()
    tool = TraverseGraphTool(driver=driver)

    with pytest.raises((ValidationError, ValueError)):
        await tool._arun(
            seed_label="Machine) DETACH DELETE n MATCH (x",
            seed_id="m1",
            relation_path=["HAS_PART"],
            max_depth=3,
        )

    # The driver session must NOT have been reached — no Cypher was composed
    mock_session.run.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: injection via relation_path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arun_rejects_injection_relation_path() -> None:
    """_arun MUST raise ValidationError for relation_path=['HAS_PART; DROP DATABASE neo4j'].

    Adversarial relation_path bypasses whitelist unless _arun re-validates.
    driver.session() MUST NOT be called at all.
    """
    driver, mock_session = _make_mock_driver()
    tool = TraverseGraphTool(driver=driver)

    with pytest.raises((ValidationError, ValueError)):
        await tool._arun(
            seed_label="Machine",
            seed_id="m1",
            relation_path=["HAS_PART; DROP DATABASE neo4j"],
            max_depth=3,
        )

    mock_session.run.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: out-of-range max_depth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arun_rejects_out_of_range_max_depth() -> None:
    """_arun MUST raise ValidationError for max_depth=99 (allowed range 1..5).

    driver.session() MUST NOT be called.
    """
    driver, mock_session = _make_mock_driver()
    tool = TraverseGraphTool(driver=driver)

    with pytest.raises((ValidationError, ValueError)):
        await tool._arun(
            seed_label="Machine",
            seed_id="m1",
            relation_path=["HAS_PART"],
            max_depth=99,
        )

    mock_session.run.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: happy path — valid literals must reach driver.session().run()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arun_happy_path_with_valid_literals() -> None:
    """_arun with valid Literals MUST reach driver.session().run() exactly once.

    This proves the fix does not break the legitimate traversal path.
    seed_label='Machine', relation_path=['HAS_PART'], max_depth=2 are all
    within the Pydantic Literal whitelist.
    """
    driver, mock_session = _make_mock_driver()
    tool = TraverseGraphTool(driver=driver)

    result = await tool._arun(
        seed_label="Machine",
        seed_id="m1",
        relation_path=["HAS_PART"],
        max_depth=2,
    )

    # Result must be a list (empty is fine — mock returns no records)
    assert isinstance(result, list)

    # session.run() must have been called exactly once (Cypher was composed and sent)
    mock_session.run.assert_called_once()
