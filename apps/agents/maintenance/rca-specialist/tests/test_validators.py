"""Tests for RCAChainValidator + domain exceptions (D-RCA-01 post-LLM enforcement).

All tests import from `mnt_rca_specialist.validators` which does not exist yet —
these tests are in the RED phase (Task 1 TDD). They will pass after Task 2
implements the validators.

Covers:
    - RCAChainValidator constructor with pool=None (shape-only fallback)
    - validate() returns chain unchanged when all citations resolve in PG
    - OrphanCitationError raised on first unresolvable source_uri
    - MissingCitationError raised (defense-in-depth) when a step has no citations
    - Pool=None logs structlog ERROR + returns chain (shape-only fallback)
    - SQL parameterization: no f-string interpolation (T-V5-sql)
    - Async validate (requires async context)
    - All-citations-orphan stress test: fail-fast on first orphan
    - Source_uri case-sensitive comparison, no whitespace trimming
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from pydantic import ValidationError
from sft_agents.models.evidence import RagCitation

from mnt_rca_specialist.models import RCAChain, WhyStep
from mnt_rca_specialist.validators import (
    MissingCitationError,
    OrphanCitationError,
    RCAChainValidator,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

UTC = timezone.utc
_TS = datetime(2026, 5, 23, 10, 0, 0, tzinfo=UTC)


def _citation(source_uri: str = "doc://sop-001") -> RagCitation:
    return RagCitation(
        source_uri=source_uri,
        snippet="Sostituire il subbio dopo 5000 ore.",
        score=0.92,
        retrieved_at=_TS,
    )


def _why_step(
    citations: list[RagCitation] | None = None,
) -> WhyStep:
    return WhyStep(
        question="Perché si è fermata la macchina?",
        answer="Perché il subbio era usurato.",
        citations=citations if citations is not None else [_citation()],
        confidence=0.85,
    )


def _make_valid_chain(citations_per_step: list[RagCitation] | None = None) -> RCAChain:
    """Return a fully valid RCAChain with a single citation per step."""
    step = _why_step(citations=citations_per_step)
    return RCAChain(
        chain_id="123e4567-e89b-12d3-a456-426614174000",
        problem_statement="La macchina 01 si è fermata durante la produzione.",
        why_1=step,
        why_2=step,
        why_3=step,
        why_4=step,
        why_5=step,
        root_cause="Usura eccessiva del subbio per mancata manutenzione programmata.",
        corrective_action_recommendation="Sostituire il subbio e ripianificare la manutenzione.",
        created_at=_TS,
    )


def _make_chain_with_orphan_at(step_idx: int, citation_idx: int) -> RCAChain:
    """Return a chain where step at step_idx has an orphan citation at citation_idx.

    step_idx is 1-based (1..5), citation_idx is 0-based.
    Valid citations precede the orphan; all other steps have valid citations.
    """
    orphan_uri = "doc://orphan-does-not-exist"
    valid_step = _why_step(citations=[_citation("doc://sop-001")])

    # Build the step at step_idx with an orphan at citation_idx
    normal_citation = _citation("doc://sop-002")
    orphan_citation = _citation(orphan_uri)
    citations_for_step: list[RagCitation]
    if citation_idx == 0:
        citations_for_step = [orphan_citation, normal_citation]
    else:
        citations_for_step = [normal_citation] * citation_idx + [orphan_citation]
    orphan_step = _why_step(citations=citations_for_step)

    steps = {
        f"why_{i}": orphan_step if i == step_idx else valid_step
        for i in range(1, 6)
    }
    return RCAChain(
        chain_id="123e4567-e89b-12d3-a456-426614174001",
        problem_statement="La macchina 01 si è fermata durante la produzione.",
        **steps,
        root_cause="Usura eccessiva del subbio per mancata manutenzione programmata.",
        corrective_action_recommendation="Sostituire il subbio e ripianificare la manutenzione.",
        created_at=_TS,
    )


def _make_mock_pool(valid_uris: set[str]) -> MagicMock:
    """Build a MagicMock asyncpg pool returning True for valid URIs, None for others."""
    pool = MagicMock()
    conn = AsyncMock()

    async def _fetchval(sql: str, uri: str) -> int | None:
        return 1 if uri in valid_uris else None

    conn.fetchval = AsyncMock(side_effect=_fetchval)

    # pool.acquire() returns an async context manager
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acquire_cm)

    return pool, conn


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------


def test_validator_constructor_pool_none() -> None:
    """RCAChainValidator accepts pool=None for shape-only fallback mode."""
    v = RCAChainValidator(pool=None)
    assert v is not None


def test_validator_constructor_pool_injected() -> None:
    """RCAChainValidator accepts a pool object."""
    pool = MagicMock()
    v = RCAChainValidator(pool=pool)
    assert v is not None


# ---------------------------------------------------------------------------
# validate() is async
# ---------------------------------------------------------------------------


def test_validate_is_coroutine() -> None:
    """validate() must be a coroutine function (async def)."""
    v = RCAChainValidator(pool=None)
    assert inspect.iscoroutinefunction(v.validate)


# ---------------------------------------------------------------------------
# Happy-path PG lookup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_all_valid_returns_chain() -> None:
    """validate() returns the chain unchanged when all citations resolve in PG."""
    valid_uris = {"doc://sop-001"}
    pool, _conn = _make_mock_pool(valid_uris)
    v = RCAChainValidator(pool=pool)
    chain = _make_valid_chain()
    result = await v.validate(chain)
    assert result is chain  # same object returned


# ---------------------------------------------------------------------------
# OrphanCitationError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_orphan_citation_raises() -> None:
    """validate() raises OrphanCitationError when a citation source_uri is not in PG."""
    # Step 3 (index 2 zero-based), citation 0 has orphan
    orphan_uri = "doc://orphan-does-not-exist"
    valid_uris = {"doc://sop-001", "doc://sop-002"}  # orphan NOT included
    pool, _conn = _make_mock_pool(valid_uris)
    v = RCAChainValidator(pool=pool)
    chain = _make_chain_with_orphan_at(step_idx=3, citation_idx=0)

    with pytest.raises(OrphanCitationError) as exc_info:
        await v.validate(chain)

    err = exc_info.value
    # Error must mention the step (3) and the orphan URI
    assert orphan_uri in str(err)
    # step_index and citation_index attributes
    assert err.step_index == 3
    assert err.citation_index == 0


@pytest.mark.asyncio
async def test_validate_all_orphan_stress_test() -> None:
    """5 steps × 2 citations = 10 orphans → raises OrphanCitationError on FIRST orphan."""
    # All citations are orphans
    orphan_pool, _conn = _make_mock_pool(set())  # empty set → all URIs are orphan
    v = RCAChainValidator(pool=orphan_pool)
    chain = _make_valid_chain()  # default citations are "doc://sop-001"

    with pytest.raises(OrphanCitationError) as exc_info:
        await v.validate(chain)

    err = exc_info.value
    # Must fail on the very first step/citation
    assert err.step_index == 1
    assert err.citation_index == 0


# ---------------------------------------------------------------------------
# SQL parameterization check (T-V5-sql)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_sql_parameterized() -> None:
    """The SQL used by the validator must NOT use f-string interpolation.

    Test inspects conn.fetchval.call_args to verify the URI is passed as
    a parameter ($1), never concatenated into the SQL string.
    """
    valid_uris = {"doc://sop-001"}
    pool, conn = _make_mock_pool(valid_uris)
    v = RCAChainValidator(pool=pool)
    chain = _make_valid_chain()
    await v.validate(chain)

    # At least one call was made
    assert conn.fetchval.called

    # Inspect the SQL argument: it must use $1 placeholder
    # and never contain the literal URI string
    for call_args in conn.fetchval.call_args_list:
        args = call_args.args if call_args.args else tuple()
        if not args:
            args = tuple(call_args.kwargs.values())
        sql_arg = args[0]
        uri_arg = args[1]
        # SQL must contain $1 (parameterized)
        assert "$1" in sql_arg, f"SQL must use $1 placeholder, got: {sql_arg!r}"
        # SQL must NOT contain the URI string directly (no f-string interpolation)
        assert uri_arg not in sql_arg, (
            f"URI must not be in SQL string (prevents injection), "
            f"found {uri_arg!r} in {sql_arg!r}"
        )


# ---------------------------------------------------------------------------
# RCAChainValidator._SQL class variable
# ---------------------------------------------------------------------------


def test_validator_sql_class_var() -> None:
    """_SQL is a class-level constant (ClassVar) accessible on class + instance."""
    assert hasattr(RCAChainValidator, "_SQL")
    sql = RCAChainValidator._SQL
    assert "$1" in sql
    assert "documents" in sql
    assert "source_uri" in sql


# ---------------------------------------------------------------------------
# Pool=None fallback (shape-only, structlog ERROR)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_pool_none_returns_chain(caplog: pytest.LogCaptureFixture) -> None:
    """When pool=None, validate() returns chain + logs structlog ERROR."""
    import logging

    v = RCAChainValidator(pool=None)
    chain = _make_valid_chain()

    with caplog.at_level(logging.ERROR, logger="mnt_rca_specialist.validators"):
        result = await v.validate(chain)

    assert result is chain
    # Should have logged an error about pool unavailability
    log_text = " ".join(caplog.messages)
    assert "pg_pool" in log_text.lower() or "pool" in log_text.lower()


# ---------------------------------------------------------------------------
# MissingCitationError (defense-in-depth)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_missing_citation_defense_in_depth() -> None:
    """MissingCitationError raised when a step's citations list is empty.

    This should not happen after Pydantic validates the chain, but the
    validator is robust to construction-bypass (e.g. model_construct).
    """
    # Use model_construct to bypass Pydantic validation
    empty_step = WhyStep.model_construct(
        question="Q",
        answer="A",
        citations=[],  # bypass min_length=1
        confidence=0.5,
    )
    valid_step = _why_step()
    chain = RCAChain.model_construct(
        chain_id="test-id",
        problem_statement="Test problem statement long enough.",
        why_1=empty_step,  # step 1 has no citations
        why_2=valid_step,
        why_3=valid_step,
        why_4=valid_step,
        why_5=valid_step,
        root_cause="Root cause here must be long enough.",
        corrective_action_recommendation="Corrective action here must be long enough.",
        created_at=_TS,
    )
    pool, _conn = _make_mock_pool({"doc://sop-001"})
    v = RCAChainValidator(pool=pool)

    with pytest.raises(MissingCitationError) as exc_info:
        await v.validate(chain)

    err = exc_info.value
    assert err.step_index == 1


# ---------------------------------------------------------------------------
# Error attributes
# ---------------------------------------------------------------------------


def test_orphan_citation_error_attributes() -> None:
    """OrphanCitationError carries step_index, citation_index, source_uri."""
    err = OrphanCitationError(step_index=2, citation_index=1, source_uri="doc://x")
    assert err.step_index == 2
    assert err.citation_index == 1
    assert err.source_uri == "doc://x"
    assert "doc://x" in str(err)


def test_missing_citation_error_attributes() -> None:
    """MissingCitationError carries step_index."""
    err = MissingCitationError(step_index=4)
    assert err.step_index == 4
    assert "4" in str(err)


# ---------------------------------------------------------------------------
# Source_uri case-sensitive, no whitespace trimming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_source_uri_case_sensitive() -> None:
    """source_uri comparison is case-sensitive: 'Doc://SOP-001' != 'doc://sop-001'."""
    # Only 'doc://sop-001' (lowercase) is valid in PG
    valid_uris = {"doc://sop-001"}
    pool, _conn = _make_mock_pool(valid_uris)
    v = RCAChainValidator(pool=pool)

    # Citation with different case — should be treated as orphan
    upper_citation = _citation("Doc://SOP-001")
    chain = _make_valid_chain(citations_per_step=[upper_citation])

    with pytest.raises(OrphanCitationError):
        await v.validate(chain)


@pytest.mark.asyncio
async def test_validate_source_uri_no_whitespace_trim() -> None:
    """source_uri is matched raw — trailing whitespace makes it an orphan."""
    # Only exact URI is valid
    valid_uris = {"doc://sop-001"}
    pool, _conn = _make_mock_pool(valid_uris)
    v = RCAChainValidator(pool=pool)

    trailing_ws_citation = _citation("doc://sop-001 ")  # trailing space
    chain = _make_valid_chain(citations_per_step=[trailing_ws_citation])

    with pytest.raises(OrphanCitationError):
        await v.validate(chain)
