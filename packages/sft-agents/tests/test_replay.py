"""Unit tests for replay_thread (CORE-10, HITL-08) — Plan 04-08 Task 1.

Per Plan 04-08 the replay tool re-executes an agent thread from PG checkpoint +
audit log:
    - Tool calls are deterministic (mocked from audit log evidence_panel.tool_calls)
    - LLM calls: with fake_llm given, compare prompt_hash; without → skip
    - write_audit=False (default): no new audit rows; replayed_audit_ids is None
    - write_audit=True: writes new audit rows with action_type prefixed 'REPLAY:'
      (T-04-Audit-Tamper distinction)
    - action_id parameter: truncates replay after that recorded action_id
    - Empty audit log → empty steps, divergence_at_step=None

Tests use ``mock_pool`` fixture (asyncpg pool mock) + mock_checkpointer +
in-process AuditWriter mock — fully deterministic, no docker required. The
integration round-trip path against testcontainers PG is deferred to a
future @pytest.mark.integration test (Phase 4 ships unit coverage only;
e2e PG round-trip is Plan 04-07 api-gateway territory).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

pytest.importorskip(
    "sft_agents.replay",
    reason="Plan 04-08 Task 1 implements replay_thread",
)

from sft_agents.models.audit import AuditRecord  # noqa: E402
from sft_agents.models.budget import BudgetSnapshot  # noqa: E402
from sft_agents.models.enums import Decision  # noqa: E402
from sft_agents.models.evidence import EvidencePanel, ToolCall, TokenUsage  # noqa: E402
from sft_agents.replay import (  # noqa: E402
    ReplayedAgentStep,
    ReplayResult,
    replay_thread,
)
from sft_agents.replay.from_checkpoint import _hash_prompt  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(*, summary: str = "ev1", prompt_hash: str | None = None) -> EvidencePanel:
    return EvidencePanel(
        input_summary=summary,
        tool_calls=[
            ToolCall(
                name="query_timescale",
                args={"asset_id": "LOOM-01"},
                result={"rows": 1},
                duration_ms=5,
                ts=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
            )
        ],
        rag_citations=[],
        confidence=0.9,
        model="qwen2.5-14b-awq@vllm-0.8",
        prompt_hash=prompt_hash or ("a" * 64),
        tokens=TokenUsage(input=10, output=5, total=15),
        duration_ms=42,
    )


def _make_budget() -> BudgetSnapshot:
    return BudgetSnapshot(
        tokens_input=10,
        tokens_output=5,
        tokens_total=15,
        cost_usd_simulated=0.01,
        duration_ms=42,
        limit_tokens=50000,
        limit_cost_usd=1.0,
        limit_duration_s=60,
    )


def _make_record(
    *,
    thread_id: str = "ops.operator-assistant.session-1",
    ts: datetime | None = None,
    summary: str = "ev1",
    action_id: UUID | None = None,
    prompt_hash: str | None = None,
) -> AuditRecord:
    return AuditRecord(
        id=uuid4(),
        ts=ts or datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        action_id=action_id or uuid4(),
        agent_id="operator-assistant",
        thread_id=thread_id,
        cluster="ops",
        action_type="QUERY_SENSORS",
        evidence_panel=_make_evidence(summary=summary, prompt_hash=prompt_hash),
        decision=Decision.AUTO,
        decision_actor=None,
        motivation=None,
        budget_snapshot=_make_budget(),
        approval_id=None,
    )


def _seed_records(count: int, *, thread_id: str = "ops.operator-assistant.session-1") -> list[AuditRecord]:
    records = []
    base = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)
    for i in range(count):
        ts = base.replace(minute=i)
        records.append(
            _make_record(
                thread_id=thread_id,
                ts=ts,
                summary=f"ev-{i}",
            )
        )
    return records


def _row_for(record: AuditRecord) -> dict:
    return {
        "id": record.id,
        "ts": record.ts,
        "action_id": record.action_id,
        "agent_id": record.agent_id,
        "thread_id": record.thread_id,
        "cluster": record.cluster,
        "action_type": record.action_type,
        "evidence_panel": record.evidence_panel.model_dump_json(),
        "decision": record.decision.value,
        "decision_actor": record.decision_actor,
        "motivation": record.motivation,
        "budget_snapshot": record.budget_snapshot.model_dump_json(),
        "approval_id": record.approval_id,
    }


# ---------------------------------------------------------------------------
# Test 1: happy path — no fake_llm, deterministic tool calls
# ---------------------------------------------------------------------------


async def test_replay_thread_happy_path_no_llm(
    mock_pool: AsyncMock, mock_checkpointer: AsyncMock
) -> None:
    """Without fake_llm: 5 audit rows → 5 ReplayedAgentSteps; no divergence; no audit writes."""
    records = _seed_records(5)
    rows = [_row_for(r) for r in records]
    mock_pool.acquire.return_value.__aenter__.return_value.fetch.return_value = rows

    result = await replay_thread(
        thread_id="ops.operator-assistant.session-1",
        pool=mock_pool,
        checkpointer=mock_checkpointer,
        fake_llm=None,
        action_id=None,
        write_audit=False,
    )

    assert isinstance(result, ReplayResult)
    assert result.thread_id == "ops.operator-assistant.session-1"
    assert len(result.replayed_steps) == 5
    assert result.divergence_at_step is None
    assert len(result.recorded_audit_ids) == 5
    assert result.replayed_audit_ids is None
    assert result.ts_replay_start.tzinfo is not None
    assert result.ts_replay_end.tzinfo is not None
    assert result.ts_replay_end >= result.ts_replay_start
    assert all(s.tool_calls_match for s in result.replayed_steps)
    assert all(s.llm_prompt_hash_match for s in result.replayed_steps)


# ---------------------------------------------------------------------------
# Test 2: with fake_llm matching → no divergence
# ---------------------------------------------------------------------------


async def test_replay_thread_with_fake_llm_matching_prompt_hash(
    mock_pool: AsyncMock, mock_checkpointer: AsyncMock
) -> None:
    """fake_llm with matching responses → all llm_prompt_hash_match=True."""
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    proto = _seed_records(3)
    # Recompute the canonical hash for each record's input + tool_calls
    expected_hashes = [
        await _hash_prompt(r.evidence_panel.input_summary, r.evidence_panel.tool_calls)
        for r in proto
    ]
    matching_records = [
        _make_record(
            thread_id=r.thread_id,
            ts=r.ts,
            summary=r.evidence_panel.input_summary,
            action_id=r.action_id,
            prompt_hash=expected_hashes[i],
        )
        for i, r in enumerate(proto)
    ]
    rows = [_row_for(r) for r in matching_records]
    mock_pool.acquire.return_value.__aenter__.return_value.fetch.return_value = rows

    fake_llm = FakeListChatModel(responses=["fake"] * 3)

    result = await replay_thread(
        thread_id="ops.operator-assistant.session-1",
        pool=mock_pool,
        checkpointer=mock_checkpointer,
        fake_llm=fake_llm,
        action_id=None,
        write_audit=False,
    )

    assert len(result.replayed_steps) == 3
    assert result.divergence_at_step is None
    assert all(s.llm_prompt_hash_match for s in result.replayed_steps)
    assert all(s.divergence_reason is None for s in result.replayed_steps)


# ---------------------------------------------------------------------------
# Test 3: divergence on first step (fake_llm prompt_hash mismatch)
# ---------------------------------------------------------------------------


async def test_replay_thread_divergence_at_step_zero(
    mock_pool: AsyncMock, mock_checkpointer: AsyncMock
) -> None:
    """fake_llm given + recorded prompt_hash != canonical → divergence_at_step=0."""
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    # Recorded hash is bogus ('b's) so canonical recomputation will diverge
    records = [
        _make_record(prompt_hash="b" * 64),
        _make_record(prompt_hash="b" * 64),
    ]
    rows = [_row_for(r) for r in records]
    mock_pool.acquire.return_value.__aenter__.return_value.fetch.return_value = rows

    fake_llm = FakeListChatModel(responses=["fake"] * 2)

    result = await replay_thread(
        thread_id="ops.operator-assistant.session-1",
        pool=mock_pool,
        checkpointer=mock_checkpointer,
        fake_llm=fake_llm,
        write_audit=False,
    )

    assert result.divergence_at_step == 0
    assert result.replayed_steps[0].llm_prompt_hash_match is False
    assert result.replayed_steps[0].divergence_reason is not None
    assert "prompt_hash" in result.replayed_steps[0].divergence_reason.lower()


# ---------------------------------------------------------------------------
# Test 4: action_id truncation (HITL-08 rollback substrate)
# ---------------------------------------------------------------------------


async def test_replay_thread_action_id_truncates(
    mock_pool: AsyncMock, mock_checkpointer: AsyncMock
) -> None:
    """When action_id provided, replay stops AFTER reaching the matching action."""
    records = _seed_records(5)
    target_action_id = records[2].action_id  # 3rd record (0-indexed)
    rows = [_row_for(r) for r in records]
    mock_pool.acquire.return_value.__aenter__.return_value.fetch.return_value = rows

    result = await replay_thread(
        thread_id="ops.operator-assistant.session-1",
        pool=mock_pool,
        checkpointer=mock_checkpointer,
        action_id=target_action_id,
        write_audit=False,
    )

    # Replay STOPS AFTER reaching the action_id → first 3 records included
    assert len(result.replayed_steps) == 3
    assert result.replayed_steps[-1].recorded_action.action_id == target_action_id


# ---------------------------------------------------------------------------
# Test 5: write_audit=True writes REPLAY:-prefixed audit rows
# ---------------------------------------------------------------------------


async def test_replay_thread_write_audit_true(
    mock_pool: AsyncMock, mock_checkpointer: AsyncMock
) -> None:
    """write_audit=True invokes audit_writer.write for each step with REPLAY: prefix."""
    records = _seed_records(3)
    rows = [_row_for(r) for r in records]
    mock_pool.acquire.return_value.__aenter__.return_value.fetch.return_value = rows

    audit_writer = AsyncMock()
    audit_writer.write = AsyncMock(return_value=None)

    result = await replay_thread(
        thread_id="ops.operator-assistant.session-1",
        pool=mock_pool,
        checkpointer=mock_checkpointer,
        write_audit=True,
        audit_writer=audit_writer,
    )

    assert audit_writer.write.call_count == 3
    # Each call's first positional arg is an AuditRecord with action_type prefix
    for c in audit_writer.write.call_args_list:
        written_record: AuditRecord = c.args[0]
        assert written_record.action_type.startswith("REPLAY:")
        assert written_record.decision == Decision.AUTO
        assert written_record.evidence_panel.input_summary.startswith("[REPLAY of ")
    assert result.replayed_audit_ids is not None
    assert len(result.replayed_audit_ids) == 3
    assert all(isinstance(uid, UUID) for uid in result.replayed_audit_ids)


# ---------------------------------------------------------------------------
# Test 6: empty audit log → empty steps
# ---------------------------------------------------------------------------


async def test_replay_thread_empty_audit_log(
    mock_pool: AsyncMock, mock_checkpointer: AsyncMock
) -> None:
    """Empty audit log → ReplayResult with empty replayed_steps, divergence=None."""
    mock_pool.acquire.return_value.__aenter__.return_value.fetch.return_value = []

    result = await replay_thread(
        thread_id="ops.operator-assistant.session-empty",
        pool=mock_pool,
        checkpointer=mock_checkpointer,
        write_audit=False,
    )

    assert result.replayed_steps == []
    assert result.divergence_at_step is None
    assert result.recorded_audit_ids == []
    assert result.replayed_audit_ids is None


# ---------------------------------------------------------------------------
# Module-level checks: ReplayedAgentStep + ReplayResult are Pydantic frozen
# ---------------------------------------------------------------------------


def test_replay_models_are_frozen() -> None:
    """ReplayedAgentStep and ReplayResult must be frozen + extra=forbid."""
    assert ReplayedAgentStep.model_config.get("frozen") is True
    assert ReplayedAgentStep.model_config.get("extra") == "forbid"
    assert ReplayResult.model_config.get("frozen") is True
    assert ReplayResult.model_config.get("extra") == "forbid"


async def test_hash_prompt_is_deterministic() -> None:
    """_hash_prompt returns the same sha256 for same input."""
    h1 = await _hash_prompt("test", [])
    h2 = await _hash_prompt("test", [])
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex
    h3 = await _hash_prompt("different", [])
    assert h1 != h3
