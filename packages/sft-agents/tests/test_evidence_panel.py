"""Test suite for sft_agents.models.evidence (Plan 04-01 Task 2).

Verifies:
    - Pydantic v2 frozen=True (mutation raises ValidationError)
    - extra='forbid' (unknown fields raise ValidationError)
    - All datetime fields reject naive datetime
    - EvidencePanel.input_summary max_length=500
    - EvidencePanel.model matches pattern `name@runtime`
    - EvidencePanel.prompt_hash matches sha256 hex 64-char pattern
    - EvidencePanel.confidence in [0, 1]
    - Defaults: input_truncated=False, tool_calls=[], rag_citations=[]
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

UTC = timezone.utc

VALID_PROMPT_HASH = "a" * 64  # 64 hex chars
VALID_MODEL = "qwen2.5-7b-q4km@ollama-0.6"


def _make_token_usage(**overrides):
    from sft_agents.models import TokenUsage

    base = {"input": 100, "output": 50, "total": 150}
    base.update(overrides)
    return TokenUsage(**base)


def _make_evidence(**overrides):
    from sft_agents.models import EvidencePanel

    base = {
        "input_summary": "Test intent",
        "tool_calls": [],
        "rag_citations": [],
        "confidence": 0.9,
        "model": VALID_MODEL,
        "prompt_hash": VALID_PROMPT_HASH,
        "tokens": _make_token_usage(),
        "duration_ms": 100,
    }
    base.update(overrides)
    return EvidencePanel(**base)


class TestEvidencePanelConstruction:
    """Basic well-formed construction."""

    def test_valid_minimal(self) -> None:
        ev = _make_evidence()
        assert ev.input_summary == "Test intent"
        assert ev.input_truncated is False  # default
        assert ev.tool_calls == []
        assert ev.rag_citations == []
        assert ev.confidence == 0.9
        assert ev.duration_ms == 100

    def test_default_input_truncated_false(self) -> None:
        ev = _make_evidence()
        assert ev.input_truncated is False


class TestEvidencePanelImmutability:
    """frozen=True + extra='forbid' contract."""

    def test_frozen_rejects_mutation(self) -> None:
        ev = _make_evidence()
        with pytest.raises(ValidationError):
            ev.confidence = 0.5

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            _make_evidence(unknown_field="boom")


class TestEvidencePanelInputSummary:
    """input_summary length cap + truncation flag."""

    def test_input_summary_max_500_chars(self) -> None:
        with pytest.raises(ValidationError):
            _make_evidence(input_summary="x" * 501)

    def test_input_summary_500_chars_ok(self) -> None:
        ev = _make_evidence(input_summary="x" * 500)
        assert len(ev.input_summary) == 500


class TestEvidencePanelModelPattern:
    r"""model field regex: r'^[a-z0-9.\-]+@[a-z0-9.\-]+$'."""

    def test_model_missing_at_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_evidence(model="raw-model")

    def test_model_uppercase_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_evidence(model="Qwen2.5@ollama")

    def test_model_valid(self) -> None:
        ev = _make_evidence(model="qwen2.5-14b-awq@vllm-0.8")
        assert ev.model == "qwen2.5-14b-awq@vllm-0.8"


class TestEvidencePanelPromptHash:
    r"""prompt_hash regex: r'^[a-f0-9]{64}$'."""

    def test_short_hash_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_evidence(prompt_hash="a" * 63)

    def test_uppercase_hash_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_evidence(prompt_hash="A" * 64)

    def test_valid_sha256_hex(self) -> None:
        ev = _make_evidence(prompt_hash="0123456789abcdef" * 4)
        assert len(ev.prompt_hash) == 64


class TestEvidencePanelConfidence:
    """confidence in [0, 1]."""

    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_evidence(confidence=-0.1)

    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_evidence(confidence=1.01)


class TestEvidencePanelDurationMs:
    """duration_ms >= 0."""

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_evidence(duration_ms=-1)


class TestToolCallTzAware:
    """ToolCall.ts must be tz-aware."""

    def test_naive_ts_rejected(self) -> None:
        from sft_agents.models import ToolCall

        with pytest.raises(ValidationError):
            ToolCall(
                name="query_timescale",
                args={"asset_id": "LOOM-01"},
                result=None,
                duration_ms=10,
                ts=datetime(2026, 5, 18, 12, 0, 0),  # naive
            )

    def test_tz_aware_ts_ok(self) -> None:
        from sft_agents.models import ToolCall

        tc = ToolCall(
            name="query_timescale",
            args={"asset_id": "LOOM-01"},
            result={"rows": 5},
            duration_ms=10,
            ts=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        )
        assert tc.ts.tzinfo is not None


class TestRagCitationTzAware:
    """RagCitation.retrieved_at must be tz-aware."""

    def test_naive_retrieved_at_rejected(self) -> None:
        from sft_agents.models import RagCitation

        with pytest.raises(ValidationError):
            RagCitation(
                source_uri="sop://heddle/cleaning.md",
                snippet="...",
                score=0.85,
                retrieved_at=datetime(2026, 5, 18, 12, 0, 0),  # naive
            )

    def test_snippet_max_2000_chars(self) -> None:
        from sft_agents.models import RagCitation

        with pytest.raises(ValidationError):
            RagCitation(
                source_uri="sop://heddle/cleaning.md",
                snippet="x" * 2001,
                score=0.85,
                retrieved_at=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
            )


class TestTokenUsage:
    """TokenUsage int ge=0."""

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_token_usage(input=-1)

    def test_frozen(self) -> None:
        tu = _make_token_usage()
        with pytest.raises(ValidationError):
            tu.input = 999
