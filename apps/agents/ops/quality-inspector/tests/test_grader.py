"""Tests for grader.py — LLM 4-point grading + Pydantic clamp + fallback (D-QI-02).

Mock LLM backend (MockReplayChatModel) replays canned JSONL responses so
tests are deterministic without network access. Each test writes its own
custom JSONL fixture into a tmp_path to override Wave 0 stub content.

Pitfall §7 (LLM hallucination): if QualityVerdict.model_validate_json fails
the grader returns a conservative fallback (score=4, severity="major").
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sft_domain.ops.citation import RagCitation
from sft_domain.ops.quality import QualityEvent, QualityVerdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    defect_type: str = "slub",
    defect_length_inches: float = 1.5,
    full_width: bool = False,
    dye_lot_id: str = "DL-LOOM-01-20260523-a3",
) -> QualityEvent:
    return QualityEvent(
        event_id=uuid4(),
        asset_id="LOOM-01",
        dye_lot_id=dye_lot_id,
        defect_type=defect_type,  # type: ignore[arg-type]
        defect_length_inches=defect_length_inches,
        full_width=full_width,
        position_meters=12.5,
        timestamp=datetime.now(timezone.utc),
        source="simulator",
    )


def _write_fixture(path: pathlib.Path, content: str) -> pathlib.Path:
    """Write a single-entry JSONL fixture file at ``path`` and return it."""
    entry = {
        "prompt_hash": "0" * 64,  # ensures hash-miss → ordered-fallback replay
        "response": {
            "content": content,
            "tool_calls": [],
            "usage_metadata": {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            },
        },
    }
    path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return path


def _mock_model(fixture_path: pathlib.Path) -> Any:
    from sft_agents.llm.mock import MockReplayChatModel

    return MockReplayChatModel(fixture_path=fixture_path)


def _mock_rag_pipeline(citations: list[RagCitation] | None = None) -> AsyncMock:
    pipeline = AsyncMock()
    pipeline.search = AsyncMock(return_value=citations or [])
    return pipeline


def _sample_citation() -> RagCitation:
    return RagCitation(
        source_uri="sop://ASTM-D5430",
        snippet="4-point grading reference: defect <=3in -> 1 point.",
        score=0.95,
        retrieved_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grader_happy_path_minor(tmp_path: pathlib.Path) -> None:
    """Slub 1.5in not full_width -> score=1 severity=minor (ASTM rule 1)."""
    from ops_quality_inspector.grader import grade_quality_event

    fixture = _write_fixture(
        tmp_path / "happy.jsonl",
        json.dumps(
            {
                "score": 1,
                "severity": "minor",
                "rationale_md": "Slub 1.5in -> rule 1 (<=3in -> 1 point).",
                "citations": [],
            }
        ),
    )
    event = _make_event(defect_type="slub", defect_length_inches=1.5)
    rag = _mock_rag_pipeline([_sample_citation()])

    verdict = await grade_quality_event(
        event, rag_pipeline=rag, model=_mock_model(fixture)
    )

    assert isinstance(verdict, QualityVerdict)
    assert verdict.score == 1
    assert verdict.severity == "minor"


@pytest.mark.asyncio
async def test_grader_full_width_critical(tmp_path: pathlib.Path) -> None:
    """Full-width broken_end -> score=4 severity=critical (ASTM rule 5)."""
    from ops_quality_inspector.grader import grade_quality_event

    fixture = _write_fixture(
        tmp_path / "critical.jsonl",
        json.dumps(
            {
                "score": 4,
                "severity": "critical",
                "rationale_md": "Full-width broken_end -> rule 5 (4 points).",
                "citations": [],
            }
        ),
    )
    event = _make_event(
        defect_type="broken_end", defect_length_inches=2.0, full_width=True
    )
    rag = _mock_rag_pipeline([_sample_citation()])

    verdict = await grade_quality_event(
        event, rag_pipeline=rag, model=_mock_model(fixture)
    )

    assert verdict.score == 4
    assert verdict.severity == "critical"


@pytest.mark.asyncio
async def test_grader_pydantic_clamp_score_out_of_range(
    tmp_path: pathlib.Path,
) -> None:
    """LLM returns score=7 -> ValidationError -> conservative fallback."""
    from ops_quality_inspector.grader import grade_quality_event

    fixture = _write_fixture(
        tmp_path / "oor.jsonl",
        json.dumps(
            {
                "score": 7,
                "severity": "minor",
                "rationale_md": "Should be clamped.",
                "citations": [],
            }
        ),
    )
    event = _make_event(defect_type="slub", defect_length_inches=1.5)
    rag = _mock_rag_pipeline([_sample_citation()])

    verdict = await grade_quality_event(
        event, rag_pipeline=rag, model=_mock_model(fixture)
    )

    assert verdict.score == 4, "conservative fallback score is 4"
    assert verdict.severity == "major", "fallback severity is major"
    assert "fallback" in verdict.rationale_md.lower()


@pytest.mark.asyncio
async def test_grader_invalid_severity_falls_back_to_major(
    tmp_path: pathlib.Path,
) -> None:
    """LLM emits severity='high' (not in Literal) -> fallback severity='major'."""
    from ops_quality_inspector.grader import grade_quality_event

    fixture = _write_fixture(
        tmp_path / "badsev.jsonl",
        json.dumps(
            {
                "score": 2,
                "severity": "high",
                "rationale_md": "Bad severity.",
                "citations": [],
            }
        ),
    )
    event = _make_event(defect_type="mispick", defect_length_inches=4.0)
    rag = _mock_rag_pipeline([_sample_citation()])

    verdict = await grade_quality_event(
        event, rag_pipeline=rag, model=_mock_model(fixture)
    )

    assert verdict.severity == "major"


@pytest.mark.asyncio
async def test_grader_invokes_rag_search_for_citations(
    tmp_path: pathlib.Path,
) -> None:
    """rag_pipeline.search called once with category='sop' and defect_type query."""
    from ops_quality_inspector.grader import grade_quality_event

    fixture = _write_fixture(
        tmp_path / "rag.jsonl",
        json.dumps(
            {
                "score": 1,
                "severity": "minor",
                "rationale_md": "RAG citations attached.",
                "citations": [],
            }
        ),
    )
    event = _make_event(defect_type="slub", defect_length_inches=1.5)
    rag = _mock_rag_pipeline([_sample_citation()])

    await grade_quality_event(event, rag_pipeline=rag, model=_mock_model(fixture))

    rag.search.assert_awaited_once()
    call_kwargs = rag.search.await_args.kwargs
    assert call_kwargs["category"] == "sop"
    assert "slub" in call_kwargs["query"]


@pytest.mark.asyncio
async def test_grader_citations_attached_to_verdict(
    tmp_path: pathlib.Path,
) -> None:
    """rag_pipeline returns 2 citations -> verdict.citations has 2 entries."""
    from ops_quality_inspector.grader import grade_quality_event

    fixture = _write_fixture(
        tmp_path / "cit.jsonl",
        json.dumps(
            {
                "score": 1,
                "severity": "minor",
                "rationale_md": "Two citations attached.",
                "citations": [],
            }
        ),
    )
    event = _make_event(defect_type="slub", defect_length_inches=1.5)
    cits = [_sample_citation(), _sample_citation()]
    rag = _mock_rag_pipeline(cits)

    verdict = await grade_quality_event(
        event, rag_pipeline=rag, model=_mock_model(fixture)
    )

    assert len(verdict.citations) == 2


@pytest.mark.asyncio
async def test_grader_no_network_call_with_mock_backend(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LLM_BACKEND=mock + MockReplayChatModel -> no network access happens.

    We rely on the MockReplayChatModel contract (file-only IO) plus the fact
    that we pass the model instance explicitly. Sanity: import block has no
    httpx/aiohttp side-effects.
    """
    from ops_quality_inspector.grader import grade_quality_event

    monkeypatch.setenv("LLM_BACKEND", "mock")
    fixture = _write_fixture(
        tmp_path / "nonet.jsonl",
        json.dumps(
            {
                "score": 1,
                "severity": "minor",
                "rationale_md": "No network.",
                "citations": [],
            }
        ),
    )
    event = _make_event(defect_type="slub", defect_length_inches=1.5)
    rag = _mock_rag_pipeline([_sample_citation()])

    verdict = await grade_quality_event(
        event, rag_pipeline=rag, model=_mock_model(fixture)
    )
    assert verdict.score == 1
