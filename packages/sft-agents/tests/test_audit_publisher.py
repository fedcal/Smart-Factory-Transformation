"""Unit tests for sft_agents.audit.nats_publisher (Plan 04-04 Task 02).

Verifies the `AuditNatsPublisher` shape + dispatch logic using the `mock_nats_js`
fixture from conftest. These tests run fast and do not require docker; the
integration test (tests/integration/test_audit_stream_bootstrap.py) covers the
real JetStream round-trip.

Covers:
    - publish_audit derives subject via subject_for_audit + publishes JSON bytes
    - publish_approval_new / publish_approval_resolved derive HITL subjects
    - publish_governor_alert publishes JSON-encoded dict to constant subject
    - drain() gracefully closes the underlying NC
    - Publish failures propagate (caller is responsible for outbox retry)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

pytest.importorskip(
    "sft_agents.audit.nats_publisher",
    reason="Plan 04-04 Task 02 implements AuditNatsPublisher",
)

from sft_agents.audit.nats_publisher import AuditNatsPublisher  # noqa: E402
from sft_agents.models.approval import ApprovalRequest  # noqa: E402
from sft_agents.models.audit import AuditRecord  # noqa: E402
from sft_agents.models.budget import BudgetSnapshot  # noqa: E402
from sft_agents.models.enums import ApprovalStatus, Decision, Tier  # noqa: E402
from sft_agents.models.evidence import EvidencePanel, TokenUsage  # noqa: E402

UTC = timezone.utc


def _make_evidence() -> EvidencePanel:
    return EvidencePanel(
        input_summary="test input",
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


def _make_audit_record(
    *, cluster: str = "ops", agent_id: str = "operator-assistant"
) -> AuditRecord:
    return AuditRecord(
        id=uuid4(),
        ts=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        action_id=uuid4(),
        agent_id=agent_id,
        thread_id="ops.operator-assistant.session-1",
        cluster=cluster,
        action_type="TEST_ACTION",
        evidence_panel=_make_evidence(),
        decision=Decision.AUTO,
        decision_actor=None,
        motivation=None,
        budget_snapshot=_make_budget(),
        approval_id=None,
    )


def _make_approval(*, tier: Tier = Tier.OPERATOR) -> ApprovalRequest:
    return ApprovalRequest(
        id=uuid4(),
        agent_id="operator-assistant",
        thread_id="ops.operator-assistant.session-1",
        tier=tier,
        action_type="TEST",
        payload_json={"foo": "bar"},
        status=ApprovalStatus.PENDING,
        created_at=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        sla_deadline=datetime(2026, 5, 18, 12, 2, 0, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# publish_audit
# ---------------------------------------------------------------------------


class TestPublishAudit:
    @pytest.mark.asyncio
    async def test_publishes_to_derived_subject(self, mock_nats_js: AsyncMock) -> None:
        pub = AuditNatsPublisher("nats://stub")
        pub._js = mock_nats_js  # inject mock, skip real connect()
        record = _make_audit_record()

        await pub.publish_audit(record)

        mock_nats_js.publish.assert_awaited_once()
        args, _kwargs = mock_nats_js.publish.call_args
        subject, payload = args
        assert subject == "audit.actions.ops.operator-assistant"
        # Payload is bytes; deserialize and check round-trip
        parsed = json.loads(payload.decode("utf-8"))
        assert parsed["agent_id"] == "operator-assistant"
        assert parsed["decision"] == "auto"

    @pytest.mark.asyncio
    async def test_payload_is_bytes(self, mock_nats_js: AsyncMock) -> None:
        pub = AuditNatsPublisher("nats://stub")
        pub._js = mock_nats_js
        record = _make_audit_record()

        await pub.publish_audit(record)
        _subject, payload = mock_nats_js.publish.call_args.args
        assert isinstance(payload, bytes)

    @pytest.mark.asyncio
    async def test_subject_derived_for_each_cluster(
        self, mock_nats_js: AsyncMock
    ) -> None:
        pub = AuditNatsPublisher("nats://stub")
        pub._js = mock_nats_js
        for cluster in ("ops", "maintenance", "supply"):
            mock_nats_js.publish.reset_mock()
            record = _make_audit_record(
                cluster=cluster, agent_id="operator-assistant"
            )
            await pub.publish_audit(record)
            subject = mock_nats_js.publish.call_args.args[0]
            assert subject == f"audit.actions.{cluster}.operator-assistant"

    @pytest.mark.asyncio
    async def test_publish_failure_propagates(self, mock_nats_js: AsyncMock) -> None:
        # AuditWriter (Plan 04-06) is responsible for outbox retry — publisher
        # MUST re-raise on failure (T-04-Outbox-Drop mitigation contract).
        mock_nats_js.publish = AsyncMock(side_effect=RuntimeError("nats down"))
        pub = AuditNatsPublisher("nats://stub")
        pub._js = mock_nats_js

        with pytest.raises(RuntimeError, match="nats down"):
            await pub.publish_audit(_make_audit_record())


# ---------------------------------------------------------------------------
# publish_approval_new / resolved
# ---------------------------------------------------------------------------


class TestPublishApproval:
    @pytest.mark.asyncio
    async def test_new_uses_tier_subject(self, mock_nats_js: AsyncMock) -> None:
        pub = AuditNatsPublisher("nats://stub")
        pub._js = mock_nats_js
        approval = _make_approval(tier=Tier.SUPERVISOR)
        await pub.publish_approval_new(approval)

        subject = mock_nats_js.publish.call_args.args[0]
        assert subject == "hitl.approvals.new.supervisor"

    @pytest.mark.asyncio
    async def test_resolved_uses_tier_subject(self, mock_nats_js: AsyncMock) -> None:
        pub = AuditNatsPublisher("nats://stub")
        pub._js = mock_nats_js
        approval = _make_approval(tier=Tier.MANAGER)
        await pub.publish_approval_resolved(approval)

        subject = mock_nats_js.publish.call_args.args[0]
        assert subject == "hitl.approvals.resolved.manager"

    @pytest.mark.asyncio
    async def test_approval_payload_round_trips(
        self, mock_nats_js: AsyncMock
    ) -> None:
        pub = AuditNatsPublisher("nats://stub")
        pub._js = mock_nats_js
        approval = _make_approval(tier=Tier.OPERATOR)
        await pub.publish_approval_new(approval)
        payload = mock_nats_js.publish.call_args.args[1]
        parsed = json.loads(payload.decode("utf-8"))
        assert parsed["tier"] == "operator"
        assert parsed["status"] == "pending"


# ---------------------------------------------------------------------------
# publish_governor_alert
# ---------------------------------------------------------------------------


class TestPublishGovernorAlert:
    @pytest.mark.asyncio
    async def test_constant_subject(self, mock_nats_js: AsyncMock) -> None:
        pub = AuditNatsPublisher("nats://stub")
        pub._js = mock_nats_js
        await pub.publish_governor_alert(
            {"auto_rate": 0.85, "sample_size": 30, "top_agents": ["operator-assistant"]}
        )
        subject = mock_nats_js.publish.call_args.args[0]
        assert subject == "hitl.governor.alert"

    @pytest.mark.asyncio
    async def test_payload_json_encoded(self, mock_nats_js: AsyncMock) -> None:
        pub = AuditNatsPublisher("nats://stub")
        pub._js = mock_nats_js
        payload_in = {"auto_rate": 0.85, "sample_size": 30}
        await pub.publish_governor_alert(payload_in)
        payload_bytes = mock_nats_js.publish.call_args.args[1]
        assert isinstance(payload_bytes, bytes)
        assert json.loads(payload_bytes.decode("utf-8")) == payload_in


# ---------------------------------------------------------------------------
# Lifecycle: drain
# ---------------------------------------------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_drain_calls_nc_drain(self) -> None:
        pub = AuditNatsPublisher("nats://stub")
        nc_mock = AsyncMock()
        nc_mock.drain = AsyncMock(return_value=None)
        pub._nc = nc_mock
        await pub.drain()
        nc_mock.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_drain_is_safe_when_not_connected(self) -> None:
        pub = AuditNatsPublisher("nats://stub")
        # Never called connect — _nc is None; drain must not raise
        await pub.drain()

    def test_init_stores_url(self) -> None:
        pub = AuditNatsPublisher("nats://example:4222")
        assert pub._url == "nats://example:4222"
        assert pub._nc is None
        assert pub._js is None
