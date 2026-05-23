"""Post-LLM validator for RCAChain (D-RCA-01 Open Q5 resolved as full PG lookup).

Validation contract
-------------------
After the LLM produces a raw JSON chain and Pydantic validates the schema
structure, ``RCAChainValidator.validate(chain)`` performs:

    1. **MissingCitationError** (defense-in-depth): raises if a step's
       ``citations`` list is empty — should never happen post-Pydantic but
       the validator is robust to ``model_construct``-bypassed chains.

    2. **OrphanCitationError**: for every citation in every step, executes
       the canonical parameterized PG lookup::

           SELECT 1 FROM documents WHERE source_uri = $1 LIMIT 1

       If PG returns ``None`` (no such row), raises ``OrphanCitationError``
       with the step index + citation index + offending URI.
       Fail-fast: raises on the FIRST orphan found (step ordering: why_1 → why_5).

    3. **Pool=None fallback** (Open Q5 degraded mode): when the pool was not
       injected (``None``), the validator logs a structlog ERROR once and
       returns the chain unchanged (shape-only pass). This is intentionally
       LOUD (ERROR, not WARNING) — silent shape-only is the WRONG default;
       use it only when PG is genuinely unavailable.

SQL parameterization (T-V5-sql)
---------------------------------
The SQL constant ``_SQL`` is a **class-level ClassVar** so tests can inspect
it directly without instantiating the validator::

    assert "$1" in RCAChainValidator._SQL
    assert "documents" in RCAChainValidator._SQL

The URI is ALWAYS passed as positional argument to ``conn.fetchval``; it is
NEVER interpolated into the SQL string (no f-string or %-format).

Source_uri comparison policy
------------------------------
- **Case-sensitive**: the stored ``source_uri`` value is matched verbatim.
  ``"Doc://SOP-001"`` ≠ ``"doc://sop-001"``.
- **No whitespace trimming**: trailing/leading whitespace is treated as part
  of the URI. ``"doc://sop-001 "`` (with space) is an orphan if the stored
  value is ``"doc://sop-001"`` (without space).

These choices match the raw stored value in the ``documents`` table without
any normalisation pass. Document them here to prevent "helpful" refactoring.
"""

from __future__ import annotations

from typing import ClassVar

import structlog

from mnt_rca_specialist.models import RCAChain

logger = structlog.get_logger("mnt_rca_specialist.validators")


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class MissingCitationError(Exception):
    """Raised when a WhyStep has an empty citations list (defense-in-depth).

    This should never occur after Pydantic validates the chain (``min_length=1``),
    but the validator is robust to ``model_construct``-bypassed objects.
    """

    def __init__(self, *, step_index: int) -> None:
        self.step_index = step_index
        super().__init__(
            f"WhyStep at why_{step_index} has no citations (MissingCitationError). "
            "The 5-Why chain is invalid: every step requires at least one citation."
        )


class OrphanCitationError(Exception):
    """Raised when a citation's source_uri does not resolve in the PG documents table.

    Attributes:
        step_index:     1-based index of the failing WhyStep (1..5).
        citation_index: 0-based index of the failing citation within the step.
        source_uri:     The URI that was not found in PG.
    """

    def __init__(self, *, step_index: int, citation_index: int, source_uri: str) -> None:
        self.step_index = step_index
        self.citation_index = citation_index
        self.source_uri = source_uri
        super().__init__(
            f"OrphanCitation at why_{step_index}[{citation_index}]: "
            f"source_uri={source_uri!r} not found in PG documents table. "
            "The LLM cited a non-existent document (T-V7-llm-hallucination mitigation)."
        )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class RCAChainValidator:
    """Post-LLM RCA chain validator with full PG source_uri lookup.

    Open Q5 resolved: **full PG lookup, audit-friendly** (locked in
    CONTEXT.md L284). See module docstring for policy details.

    Usage::

        validator = RCAChainValidator(pool=asyncpg_pool)
        validated_chain = await validator.validate(chain)
        # raises MissingCitationError or OrphanCitationError on failure

    Pool-free mode::

        validator = RCAChainValidator(pool=None)  # shape-only fallback
        # logs structlog ERROR + returns chain unchanged
    """

    #: Canonical parameterized SQL for source_uri existence check (T-V5-sql).
    #: NEVER interpolate the URI into this string — pass it as the $1 argument.
    _SQL: ClassVar[str] = "SELECT 1 FROM documents WHERE source_uri = $1 LIMIT 1"

    def __init__(self, *, pool: object | None = None) -> None:
        """Construct the validator.

        Args:
            pool: An ``asyncpg.Pool`` instance for PG lookups, or ``None``
                  to enable shape-only fallback mode (logs ERROR, returns chain).
        """
        self._pool = pool
        self._pool_error_logged = False  # log pool-unavailable error only once

    async def validate(self, chain: RCAChain) -> RCAChain:
        """Validate all citations in the 5-Why chain against PG.

        Args:
            chain: A Pydantic-validated ``RCAChain`` instance.

        Returns:
            The same ``chain`` object unchanged when validation passes.

        Raises:
            MissingCitationError: If a step's citations list is empty
                                  (defense-in-depth post-Pydantic check).
            OrphanCitationError:  If a citation's source_uri is not found
                                  in the PG ``documents`` table. Fail-fast:
                                  raises on the first orphan found.
        """
        if self._pool is None:
            if not self._pool_error_logged:
                logger.error(
                    "rca_validator_pg_pool_unavailable_falling_back_to_shape_only",
                    validator=self.__class__.__name__,
                    note=(
                        "Shape-only validation active. Citation source_uri existence "
                        "NOT verified against PG. This degrades audit quality. "
                        "Inject a live asyncpg.Pool to enable full PG lookup (Open Q5)."
                    ),
                )
                self._pool_error_logged = True
            return chain

        steps = [
            (1, chain.why_1),
            (2, chain.why_2),
            (3, chain.why_3),
            (4, chain.why_4),
            (5, chain.why_5),
        ]

        async with self._pool.acquire() as conn:
            for step_index, step in steps:
                # Defense-in-depth: check for empty citations list
                # (should not happen after Pydantic validation, but be robust)
                if not step.citations:
                    raise MissingCitationError(step_index=step_index)

                for citation_index, citation in enumerate(step.citations):
                    # Parameterized query — URI passed as argument, NOT in SQL string.
                    # Case-sensitive, no whitespace trimming (see module docstring).
                    result = await conn.fetchval(self._SQL, citation.source_uri)
                    if result is None:
                        raise OrphanCitationError(
                            step_index=step_index,
                            citation_index=citation_index,
                            source_uri=citation.source_uri,
                        )

        return chain


__all__ = [
    "MissingCitationError",
    "OrphanCitationError",
    "RCAChainValidator",
]
