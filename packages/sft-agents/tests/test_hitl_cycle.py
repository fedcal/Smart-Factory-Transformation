"""Unit tests for human_approval_node + ApprovalQueueWriter + GDPRRedactor (Plan 04-06 Task 02).

The full LangGraph interrupt/resume e2e (with a real StateGraph + Command(resume=))
is covered by the api-gateway integration suite in Plan 04-07. Here we test the
node's intermediate contract against mocks:

    Test 1 (happy path): node persists ApprovalRequest, calls interrupt(), validates
            resume payload, UPDATEs the row, publishes resolved, audits.
    Test 2 (motivation required): empty motivation on hitl_* decision raises ValidationError.
    Test 3 (idempotent replay): re-invocation with same thread_id+action returns same approval_id.
    Test 4 (T-04-Resume-Replay): update_decision with non-existent id raises ApprovalNotFoundError.
    Test 5 (GDPRRedactor): phone/email/CF redaction in EvidencePanel.input_summary.

`interrupt()` is monkey-patched at module scope to return a deterministic payload.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

# Skip the whole module if the new package paths don't exist yet (TDD RED gate).
pytest.importorskip(
    "sft_agents.hitl.interrupt",
    reason="Plan 04-06 Task 02 implements hitl.interrupt",
)

from sft_agents.hitl import (  # noqa: E402
    ApprovalNotFoundError,
    ApprovalQueueWriter,
    GDPRRedactor,
    human_approval_node,
    redact_str,
    tier_to_decision,
)
from sft_agents.hitl.interrupt import _derive_approval_id  # noqa: E402
from sft_agents.models.approval import ApprovalDecision  # noqa: E402
from sft_agents.models.budget import BudgetSnapshot  # noqa: E402
from sft_agents.models.enums import ActionType, Decision, Tier  # noqa: E402
from sft_agents.models.evidence import EvidencePanel, TokenUsage  # noqa: E402
from sft_agents.models.proposed_action import ProposedAction  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(summary: str = "test input") -> EvidencePanel:
    return EvidencePanel(
        input_summary=summary,
        tool_calls=[],
        rag_citations=[],
        confidence=0.9,
        model="qwen2.5-14b-awq@vllm-0.8",
        prompt_hash="a" * 64,
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


def _make_proposed_action() -> ProposedAction:
    return ProposedAction.from_payload(
        thread_id="ops.operator-assistant.session-1",
        action_type=ActionType.WRITE_PLC_SETPOINT,
        args={"asset_id": "loom-T-12", "value": 1.0},
        target_subject="cmd.plc.setpoint.loom-T-12.speed",
    )


def _make_queue_writer(mock_pool) -> tuple[ApprovalQueueWriter, AsyncMock]:
    """Wire the writer + return the underlying conn mock so tests can assert calls."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    # fetchrow returns a dict-like row for both INSERT...RETURNING and
    # UPDATE...RETURNING; we configure per-test.
    return ApprovalQueueWriter(mock_pool), conn


def _make_audit_writer() -> AsyncMock:
    audit = AsyncMock()
    audit.write = AsyncMock(return_value=None)
    return audit


def _make_nats() -> AsyncMock:
    nats_pub = AsyncMock()
    nats_pub.publish_approval_new = AsyncMock(return_value=None)
    nats_pub.publish_approval_resolved = AsyncMock(return_value=None)
    return nats_pub


@pytest.fixture
def patch_interrupt(monkeypatch):
    """Replace ``langgraph.types.interrupt`` with a deterministic payload sink."""
    from sft_agents.hitl import interrupt as interrupt_mod

    captured: dict[str, object] = {}

    def fake_interrupt(payload):
        captured["payload"] = payload
        return captured["resume"]

    monkeypatch.setattr(
        "langgraph.types.interrupt",
        fake_interrupt,
        raising=False,
    )

    # ALSO patch the imported reference inside interrupt_mod in case the module
    # already imported the symbol at top level (it imports lazily in our case).
    monkeypatch.setattr(
        interrupt_mod,
        "_test_interrupt",
        fake_interrupt,
        raising=False,
    )
    return captured


# ---------------------------------------------------------------------------
# Test 1: happy path
# ---------------------------------------------------------------------------


async def test_happy_path_operator(mock_pool: AsyncMock, patch_interrupt) -> None:
    """Operator-tier approve cycle: insert → interrupt → resume → update → audit."""
    queue_writer, conn = _make_queue_writer(mock_pool)

    # INSERT returns a row (idempotent on id).
    conn.fetchrow.return_value = {"id": uuid4()}

    audit_writer = _make_audit_writer()
    nats_pub = _make_nats()

    proposed = _make_proposed_action()
    panel = _make_evidence("Set loom T-12 speed to 1.0")
    state = {"thread_id": "ops.operator-assistant.session-1"}

    # Configure resume payload.
    patch_interrupt["resume"] = {
        "decision": "approve",
        "motivation": "ok by shift lead",
        "decided_by": "user-1",
    }

    delta = await human_approval_node(
        state,
        proposed_action=proposed,
        evidence_panel=panel,
        queue_writer=queue_writer,
        nats_publisher=nats_pub,
        audit_writer=audit_writer,
        tier=Tier.OPERATOR,
        cluster="ops",
        agent_id="operator-assistant",
        budget_snapshot=_make_budget(),
    )

    # Delta clears pending_approval_id + attaches evidence.
    assert delta["pending_approval_id"] is None
    assert delta["evidence"] is panel

    # NATS notifies.
    nats_pub.publish_approval_new.assert_awaited_once()
    nats_pub.publish_approval_resolved.assert_awaited_once()

    # Audit dual-write fired exactly once.
    audit_writer.write.assert_awaited_once()
    audit_record = audit_writer.write.await_args.args[0]
    assert audit_record.decision == Decision.HITL_OPERATOR
    assert audit_record.motivation == "ok by shift lead"
    assert audit_record.approval_id is not None
    assert audit_record.action_id == proposed.id


# ---------------------------------------------------------------------------
# Test 2: motivation required for hitl_*
# ---------------------------------------------------------------------------


async def test_motivation_required_for_hitl(
    mock_pool: AsyncMock, patch_interrupt
) -> None:
    """Empty motivation on approve verb fails ApprovalDecision Pydantic validation."""
    queue_writer, conn = _make_queue_writer(mock_pool)
    conn.fetchrow.return_value = {"id": uuid4()}

    audit_writer = _make_audit_writer()
    nats_pub = _make_nats()

    patch_interrupt["resume"] = {
        "decision": "approve",
        "motivation": "",  # invalid — min_length=1
        "decided_by": "user-1",
    }

    with pytest.raises(ValidationError):
        await human_approval_node(
            {"thread_id": "ops.operator-assistant.session-1"},
            proposed_action=_make_proposed_action(),
            evidence_panel=_make_evidence(),
            queue_writer=queue_writer,
            nats_publisher=nats_pub,
            audit_writer=audit_writer,
            tier=Tier.OPERATOR,
            cluster="ops",
            agent_id="operator-assistant",
            budget_snapshot=_make_budget(),
        )

    # Audit was NOT written — motivation validation runs BEFORE the audit step.
    audit_writer.write.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 3: idempotent replay (sha256-deterministic id)
# ---------------------------------------------------------------------------


async def test_idempotent_replay() -> None:
    """Same thread_id + ProposedAction → same approval_id (Pitfall §6)."""
    proposed = _make_proposed_action()
    thread = "ops.operator-assistant.session-1"
    id1 = _derive_approval_id(thread, proposed.id)
    id2 = _derive_approval_id(thread, proposed.id)
    assert id1 == id2
    assert isinstance(id1, UUID)
    # Different action → different id.
    proposed2 = ProposedAction.from_payload(
        thread_id=thread,
        action_type=ActionType.FIRMWARE_DEPLOY,
        args={"image": "x"},
    )
    assert _derive_approval_id(thread, proposed2.id) != id1


# ---------------------------------------------------------------------------
# Test 4: T-04-Resume-Replay defense
# ---------------------------------------------------------------------------


async def test_approval_not_found_on_stale_id(mock_pool: AsyncMock) -> None:
    """update_decision with no matching pending row raises ApprovalNotFoundError."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetchrow.return_value = None  # 0 rows matched

    qw = ApprovalQueueWriter(mock_pool)
    with pytest.raises(ApprovalNotFoundError):
        await qw.update_decision(
            uuid4(),
            decision="approve",
            decided_by="user-1",
            motivation="x",
            decided_at=datetime(2026, 5, 18, tzinfo=UTC),
        )


async def test_update_decision_rejects_invalid_verb(mock_pool: AsyncMock) -> None:
    qw = ApprovalQueueWriter(mock_pool)
    with pytest.raises(ValueError, match="approve/reject/escalate"):
        await qw.update_decision(
            uuid4(),
            decision="banana",
            decided_by="user-1",
            motivation="x",
            decided_at=datetime(2026, 5, 18, tzinfo=UTC),
        )


# ---------------------------------------------------------------------------
# Test 5: GDPRRedactor
# ---------------------------------------------------------------------------


def test_redact_phone() -> None:
    out = redact_str("call +39 333 1234567 now")
    assert "[REDACTED-PHONE]" in out
    assert "1234567" not in out


def test_redact_email() -> None:
    out = redact_str("email a@b.it for help")
    assert "[REDACTED-EMAIL]" in out
    assert "a@b.it" not in out


def test_redact_codice_fiscale() -> None:
    out = redact_str("CF: RSSMRA80A01H501Z confidential")
    assert "[REDACTED-CF]" in out
    assert "RSSMRA80A01H501Z" not in out


def test_redactor_returns_new_panel() -> None:
    panel = _make_evidence("contact a@b.it for details")
    redactor = GDPRRedactor()
    out = redactor.redact(panel)
    assert "[REDACTED-EMAIL]" in out.input_summary
    # Original is frozen — unchanged.
    assert "a@b.it" in panel.input_summary
    # Other fields are preserved.
    assert out.confidence == panel.confidence
    assert out.tokens == panel.tokens


# ---------------------------------------------------------------------------
# tier_to_decision helper
# ---------------------------------------------------------------------------


def test_tier_to_decision_mapping() -> None:
    assert tier_to_decision(Tier.OPERATOR, decision_verb="approve") == Decision.HITL_OPERATOR
    assert tier_to_decision(Tier.SUPERVISOR, decision_verb="reject") == Decision.HITL_SUPERVISOR
    assert tier_to_decision(Tier.MANAGER, decision_verb="approve") == Decision.HITL_MANAGER
    assert tier_to_decision(Tier.OPERATOR, decision_verb="escalate") == Decision.ESCALATED


# ---------------------------------------------------------------------------
# ApprovalQueueWriter — INSERT parameterized SQL shape
# ---------------------------------------------------------------------------


async def test_approval_insert_uses_on_conflict_do_nothing(mock_pool: AsyncMock) -> None:
    qw = ApprovalQueueWriter(mock_pool)
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetchrow.return_value = {"id": uuid4()}

    from sft_agents.models.approval import ApprovalRequest
    from sft_agents.models.enums import ApprovalStatus

    approval = ApprovalRequest(
        id=uuid4(),
        agent_id="operator-assistant",
        thread_id="ops.operator-assistant.session-1",
        tier=Tier.OPERATOR,
        action_type="TEST",
        payload_json={},
        status=ApprovalStatus.PENDING,
        created_at=datetime(2026, 5, 18, tzinfo=UTC),
        sla_deadline=datetime(2026, 5, 18, 0, 2, tzinfo=UTC),
    )
    await qw.insert(approval)

    args, _ = conn.fetchrow.call_args
    sql = args[0]
    assert "INSERT INTO hitl.approvals" in sql
    assert "ON CONFLICT (id) DO NOTHING" in sql
    assert "$1" in sql and "$9" in sql


async def test_approval_queue_rejects_none_pool() -> None:
    with pytest.raises(ValueError, match="pool must not be None"):
        ApprovalQueueWriter(None)
