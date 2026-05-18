"""ABC enforcement + concrete-subclass smoke tests for sft-agents SDK (Plan 04-01 Task 3).

Verifies:
    - Agent / Tool / Memory / Policy are ABCs (cannot be instantiated directly)
    - Subclasses missing required abstract methods raise TypeError on instantiation
    - Concrete subclasses with all abstract methods provided can instantiate
    - Tool._run raises NotImplementedError (forces async _arun)
    - Policy.post_decision_check default no-op returns None
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from sft_agents import (
    ActionType,
    Agent,
    AuditRecord,
    BudgetSnapshot,
    Decision,
    EvidencePanel,
    Memory,
    MemoryRecord,
    Policy,
    ProposedAction,
    TokenUsage,
    Tool,
)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Agent ABC
# ---------------------------------------------------------------------------


class TestAgentABC:
    def test_agent_is_abc_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            Agent()  # type: ignore[abstract]

    def test_subclass_missing_step_cannot_instantiate(self) -> None:
        class BrokenAgent(Agent):
            name = "broken"
            cluster = "ops"
            tools: list[Tool] = []
            memory = None  # type: ignore[assignment]
            policy = None  # type: ignore[assignment]
            # NOTE: deliberately omit `step`

        with pytest.raises(TypeError):
            BrokenAgent()  # type: ignore[abstract]

    def test_subclass_with_step_can_instantiate(self) -> None:
        class GoodAgent(Agent):
            name = "good"
            cluster = "ops"
            tools: list[Tool] = []
            memory = None  # type: ignore[assignment]
            policy = None  # type: ignore[assignment]

            async def step(self, state: dict[str, Any]) -> dict[str, Any]:
                return {"ok": True}

        a = GoodAgent()
        assert a.name == "good"
        assert a.cluster == "ops"


# ---------------------------------------------------------------------------
# Tool ABC
# ---------------------------------------------------------------------------


class TestToolABC:
    def test_tool_is_abc_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            Tool()  # type: ignore[abstract]

    async def test_subclass_with_only_arun_can_instantiate_and_sync_run_raises(self) -> None:
        class EchoTool(Tool):
            name: str = "echo"
            description: str = "Echo tool"

            async def _arun(self, msg: str, **_: Any) -> str:
                return msg

        t = EchoTool()
        # _run is disabled — must raise NotImplementedError
        with pytest.raises(NotImplementedError, match="async-only"):
            t._run(msg="hi")
        # _arun works
        result = await t._arun(msg="hi")
        assert result == "hi"


# ---------------------------------------------------------------------------
# Memory ABC
# ---------------------------------------------------------------------------


class TestMemoryABC:
    def test_memory_is_abc_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            Memory()  # type: ignore[abstract]

    def test_subclass_missing_store_cannot_instantiate(self) -> None:
        class BrokenMemory(Memory):
            async def query(
                self,
                query: str,
                k: int = 5,
                filters: dict[str, Any] | None = None,
            ) -> list[MemoryRecord]:
                return []
            # NOTE: deliberately omit `store`

        with pytest.raises(TypeError):
            BrokenMemory()  # type: ignore[abstract]

    async def test_subclass_with_query_and_store_can_instantiate(self) -> None:
        class StubMemory(Memory):
            async def query(
                self,
                query: str,
                k: int = 5,
                filters: dict[str, Any] | None = None,
            ) -> list[MemoryRecord]:
                return []

            async def store(self, record: MemoryRecord) -> str:
                return "mem://stub/1"

        m = StubMemory()
        assert await m.query("anything") == []
        rec = MemoryRecord(
            source_uri="sop://test",
            content="hello",
            score=0.5,
            ts=datetime.now(UTC),
        )
        assert await m.store(rec) == "mem://stub/1"


# ---------------------------------------------------------------------------
# Policy ABC
# ---------------------------------------------------------------------------


class TestPolicyABC:
    def test_policy_is_abc_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            Policy()  # type: ignore[abstract]

    def test_subclass_missing_pre_tool_check_cannot_instantiate(self) -> None:
        class BrokenPolicy(Policy):
            pass  # NOTE: missing pre_tool_check

        with pytest.raises(TypeError):
            BrokenPolicy()  # type: ignore[abstract]

    async def test_post_decision_check_default_no_op(self) -> None:
        class TrivialPolicy(Policy):
            async def pre_tool_check(self, action: ProposedAction) -> None:
                return None

        p = TrivialPolicy()
        # Build a minimal AuditRecord
        rec = AuditRecord(
            id=uuid4(),
            ts=datetime.now(UTC),
            action_id=uuid4(),
            agent_id="ops.operator-assistant",
            thread_id="ops.operator-assistant.abc",
            cluster="ops",
            action_type="GRAPH_RECURSION_REVIEW",
            evidence_panel=EvidencePanel(
                input_summary="t",
                confidence=0.9,
                model="qwen2.5-7b@ollama-0.6",
                prompt_hash="a" * 64,
                tokens=TokenUsage(input=1, output=1, total=2),
                duration_ms=10,
            ),
            decision=Decision.AUTO,
            budget_snapshot=BudgetSnapshot(
                limit_tokens=1000, limit_cost_usd=1.0, limit_duration_s=60
            ),
        )
        # Default post_decision_check returns None and does not raise
        assert await p.post_decision_check(rec) is None

    async def test_pre_tool_check_invoked_on_subclass(self) -> None:
        invocations: list[ProposedAction] = []

        class RecordingPolicy(Policy):
            async def pre_tool_check(self, action: ProposedAction) -> None:
                invocations.append(action)

        p = RecordingPolicy()
        action = ProposedAction.from_payload(
            thread_id="t1",
            action_type=ActionType.GRAPH_RECURSION_REVIEW,
            args={"x": 1},
        )
        await p.pre_tool_check(action)
        assert len(invocations) == 1
        assert invocations[0].action_type == ActionType.GRAPH_RECURSION_REVIEW
        assert isinstance(invocations[0].id, UUID)
