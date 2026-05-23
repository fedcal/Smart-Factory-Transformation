"""Tests for WhyStep + RCAChain Pydantic models (D-RCA-01).

All tests import from `mnt_rca_specialist.models` which does not exist yet —
these tests are in the RED phase (Task 1 TDD). They will pass after Task 2
implements the models.

Covers:
    - WhyStep frozen + extra=forbid constraints
    - WhyStep field validation (min/max lengths, confidence range, citations)
    - RCAChain frozen + extra=forbid, exactly 5 named why_* fields
    - RCAChain.created_at tz-aware requirement
    - RCASpecialistRequest + RCASpecialistResponse shape
    - Round-trip serialisation
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sft_agents.models.evidence import RagCitation

from mnt_rca_specialist.models import (
    RCAChain,
    RCASpecialistRequest,
    RCASpecialistResponse,
    WhyStep,
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
    question: str = "Perché si è fermata la macchina?",
    answer: str = "Perché il subbio era usurato.",
    citations: list[RagCitation] | None = None,
    confidence: float = 0.85,
) -> WhyStep:
    return WhyStep(
        question=question,
        answer=answer,
        citations=citations if citations is not None else [_citation()],
        confidence=confidence,
    )


def _rca_chain(**overrides: object) -> RCAChain:
    step = _why_step()
    defaults: dict[str, object] = {
        "chain_id": "123e4567-e89b-12d3-a456-426614174000",
        "problem_statement": "La macchina 01 si è fermata durante la produzione.",
        "why_1": step,
        "why_2": step,
        "why_3": step,
        "why_4": step,
        "why_5": step,
        "root_cause": "Usura eccessiva del subbio per mancata manutenzione programmata.",
        "corrective_action_recommendation": "Sostituire il subbio e ripianificare la manutenzione.",
        "downtime_event_id": None,
        "created_at": _TS,
    }
    defaults.update(overrides)
    return RCAChain.model_validate(defaults)


# ---------------------------------------------------------------------------
# WhyStep tests
# ---------------------------------------------------------------------------


def test_why_step_valid() -> None:
    """Happy path: WhyStep with valid fields constructs without error."""
    step = _why_step()
    assert step.question == "Perché si è fermata la macchina?"
    assert len(step.citations) == 1
    assert step.confidence == 0.85


def test_why_step_frozen_raises_on_mutation() -> None:
    """WhyStep is frozen — attribute assignment raises TypeError."""
    step = _why_step()
    with pytest.raises((TypeError, ValidationError)):
        step.question = "new question"  # type: ignore[misc]


def test_why_step_extra_forbid() -> None:
    """WhyStep extra=forbid — unknown field raises ValidationError."""
    with pytest.raises(ValidationError):
        WhyStep(
            question="Q",
            answer="A",
            citations=[_citation()],
            confidence=0.5,
            unknown_field="x",  # type: ignore[call-arg]
        )


def test_why_step_question_empty_raises() -> None:
    """WhyStep.question min_length=1 — empty string raises."""
    with pytest.raises(ValidationError):
        _why_step(question="")


def test_why_step_question_too_long_raises() -> None:
    """WhyStep.question max_length=500 — 501 chars raises."""
    with pytest.raises(ValidationError):
        _why_step(question="x" * 501)


def test_why_step_answer_too_long_raises() -> None:
    """WhyStep.answer max_length=2000 — 2001 chars raises."""
    with pytest.raises(ValidationError):
        _why_step(answer="x" * 2001)


def test_why_step_citations_empty_raises() -> None:
    """WhyStep.citations min_length=1 — empty list raises."""
    with pytest.raises(ValidationError):
        _why_step(citations=[])


def test_why_step_confidence_below_zero_raises() -> None:
    """WhyStep.confidence ge=0.0 — negative value raises."""
    with pytest.raises(ValidationError):
        _why_step(confidence=-0.1)


def test_why_step_confidence_above_one_raises() -> None:
    """WhyStep.confidence le=1.0 — value > 1 raises."""
    with pytest.raises(ValidationError):
        _why_step(confidence=1.1)


def test_why_step_citation_empty_source_uri_raises() -> None:
    """RagCitation.source_uri min_length=1 — empty string raises."""
    with pytest.raises(ValidationError):
        RagCitation(
            source_uri="",
            snippet="snippet",
            score=0.9,
            retrieved_at=_TS,
        )


# ---------------------------------------------------------------------------
# RCAChain tests
# ---------------------------------------------------------------------------


def test_rca_chain_valid() -> None:
    """Happy path: RCAChain with all 5 why_* fields constructs without error."""
    chain = _rca_chain()
    assert chain.why_1.confidence == 0.85
    assert chain.why_5.confidence == 0.85


def test_rca_chain_frozen() -> None:
    """RCAChain is frozen — attribute assignment raises TypeError."""
    chain = _rca_chain()
    with pytest.raises((TypeError, ValidationError)):
        chain.problem_statement = "new"  # type: ignore[misc]


def test_rca_chain_extra_forbid() -> None:
    """RCAChain extra=forbid — unknown field raises."""
    step = _why_step()
    with pytest.raises(ValidationError):
        RCAChain(
            chain_id="123e4567-e89b-12d3-a456-426614174000",
            problem_statement="La macchina 01 si è fermata.",
            why_1=step,
            why_2=step,
            why_3=step,
            why_4=step,
            why_5=step,
            root_cause="Usura del subbio per mancata manutenzione.",
            corrective_action_recommendation="Sostituire il subbio.",
            created_at=_TS,
            unknown_field="x",  # type: ignore[call-arg]
        )


def test_rca_chain_missing_why_field_raises() -> None:
    """Omitting any why_* field from RCAChain raises ValidationError."""
    step = _why_step()
    with pytest.raises(ValidationError):
        RCAChain(
            chain_id="123e4567-e89b-12d3-a456-426614174000",
            problem_statement="La macchina 01 si è fermata.",
            why_1=step,
            why_2=step,
            why_3=step,
            why_4=step,
            # why_5 MISSING — should raise
            root_cause="Usura del subbio per mancata manutenzione.",
            corrective_action_recommendation="Sostituire il subbio.",
            created_at=_TS,
        )


def test_rca_chain_no_why_list_field() -> None:
    """RCAChain does NOT have a 'whys' list field (D-RCA-01 form-based schema)."""
    chain = _rca_chain()
    assert not hasattr(chain, "whys")


def test_rca_chain_naive_datetime_raises() -> None:
    """RCAChain.created_at must be tz-aware — naive datetime raises."""
    with pytest.raises(ValidationError):
        _rca_chain(created_at=datetime(2026, 5, 23, 10, 0, 0))  # naive


def test_rca_chain_problem_statement_too_short_raises() -> None:
    """RCAChain.problem_statement min_length=10 — short string raises."""
    with pytest.raises(ValidationError):
        _rca_chain(problem_statement="short")


def test_rca_chain_round_trip() -> None:
    """model_dump_json -> json.loads -> model_validate yields equal instance."""
    chain = _rca_chain()
    dumped = chain.model_dump_json()
    reloaded = RCAChain.model_validate(json.loads(dumped))
    assert reloaded == chain


# ---------------------------------------------------------------------------
# RCASpecialistRequest tests
# ---------------------------------------------------------------------------


def test_rca_specialist_request_valid() -> None:
    """RCASpecialistRequest constructs with valid fields."""
    req = RCASpecialistRequest(
        problem_statement="La macchina 01 si è fermata durante la produzione.",
        user_roles=["maintenance"],
    )
    assert req.downtime_event_id is None
    assert req.asset_id is None
    assert req.user_roles == ["maintenance"]


def test_rca_specialist_request_problem_too_short_raises() -> None:
    """problem_statement min_length=10."""
    with pytest.raises(ValidationError):
        RCASpecialistRequest(
            problem_statement="short",
            user_roles=["maintenance"],
        )


def test_rca_specialist_request_empty_roles_raises() -> None:
    """user_roles min_length=1 — empty list raises."""
    with pytest.raises(ValidationError):
        RCASpecialistRequest(
            problem_statement="La macchina 01 si è fermata.",
            user_roles=[],
        )


# ---------------------------------------------------------------------------
# RCASpecialistResponse tests
# ---------------------------------------------------------------------------


def test_rca_specialist_response_supervisor_pending() -> None:
    """RCASpecialistResponse with chain and supervisor_pending status."""
    chain = _rca_chain()
    resp = RCASpecialistResponse(chain=chain, hitl_status="supervisor_pending")
    assert resp.hitl_status == "supervisor_pending"
    assert resp.chain == chain


def test_rca_specialist_response_invalid_status_raises() -> None:
    """hitl_status must be one of the Literal values."""
    with pytest.raises(ValidationError):
        RCASpecialistResponse(
            chain=_rca_chain(),
            hitl_status="unknown_status",  # type: ignore[arg-type]
        )
