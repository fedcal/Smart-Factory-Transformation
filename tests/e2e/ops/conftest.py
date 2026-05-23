"""Shared fixtures for OPS e2e scenario tests (Plan 06-13).

This conftest provides:

    - `ops_scenario(request)` — yaml.safe_load loader keyed on indirect
      parametrize values (e.g. ``"operator-assistant/happy"``). Returns the
      parsed scenario dict (T-V6-W0-yaml-injection mitigation: safe_load only).
    - `mock_llm_backend(monkeypatch, request)` — sets env LLM_BACKEND=mock +
      MOCK_LLM_FIXTURE=<abs path>; ALSO patches ``sft_agents.llm.factory.build_chat_model``
      and the per-agent ``build_chat_model`` re-export so the MockReplayChatModel
      (Plan 06-01) is instantiated against the corresponding JSONL trace.
    - `seed_audit_actions(scenario)` — helper to pre-populate the rate-limiter
      lookup (anomaly-detector failure scenario uses this).
    - `mock_collaborators()` — factory returning AsyncMock-shaped collaborators
      for any of the 4 agents. Real testcontainers (Qdrant/Neo4j/TSDB/NATS/PG)
      are out-of-scope for the deterministic E2E suite: the tests verify each
      agent's CONTRACT (tool_calls + audit dispatch + tier routing) using
      mocks so the suite runs in <30s on any laptop without docker.

Real-testcontainer E2E (Qdrant+Neo4j+TSDB+NATS+PG seeded per scenario) is
queued for Phase 11 (observability) when the api-gateway endpoint surface
for all 4 OPS agents lands; tracking issue in 06-13-SUMMARY.md Deferred Items.

Marker contract:
    - `e2e` — Plan 06-13 mock-LLM scenarios (this suite, runs in CI).
    - `real-llm` — opt-in real Qwen2.5 (regenerate-llm-fixtures.py + Ollama).

Design rationale:
    Phase 6's success criterion #5 ("each agent's E2E test covers three
    scenarios: happy / degraded / failure") is mechanically satisfied by
    asserting on the agent's deterministic contract — invocation, tool calls,
    HITL tier routing decision, audit dispatch — without spinning the full
    docker stack for every PR. The full docker E2E lives in Phase 11.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Repo root computed relative to this file (robust against cwd).
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SCENARIOS_ROOT = _REPO_ROOT / "tests" / "fixtures" / "ops_scenarios"
_LLM_TRACES_ROOT = _REPO_ROOT / "tests" / "fixtures" / "llm_responses"


# ---------------------------------------------------------------------------
# Indirect-parametrize key resolution
# ---------------------------------------------------------------------------


def _resolve_scenario_key(request: pytest.FixtureRequest) -> str:
    """Extract ``"<agent>/<scenario>"`` from indirect parametrize.

    Tests should pass an indirect parametrize like::

        @pytest.mark.parametrize(
            "ops_scenario",
            ["operator-assistant/happy", "operator-assistant/degraded", ...],
            indirect=True,
        )
    """
    param = getattr(request, "param", None)
    if isinstance(param, str) and "/" in param:
        return param
    return ""


# ---------------------------------------------------------------------------
# ops_scenario fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def ops_scenario(request: pytest.FixtureRequest) -> dict[str, Any]:
    """Load a scenario YAML via ``yaml.safe_load`` (T-V6-yaml-injection).

    Returns:
        Parsed YAML dict, or {} if no scenario was selected / file missing.
    """
    import yaml  # noqa: PLC0415 — lazy import so collection works without PyYAML

    key = _resolve_scenario_key(request)
    if not key:
        return {}
    yaml_path = _SCENARIOS_ROOT / f"{key}.yaml"
    if not yaml_path.exists():
        return {}
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    # Annotate the dict with the scenario key for downstream fixtures.
    raw["_key"] = key
    return raw


# ---------------------------------------------------------------------------
# mock_llm_backend fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_backend(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> dict[str, Any]:
    """Configure env + factory monkeypatch so build_chat_model returns MockReplayChatModel.

    Sets:
        LLM_BACKEND=mock
        MOCK_LLM_FIXTURE=<abs path>

    Patches:
        sft_agents.llm.factory.build_chat_model → returns MockReplayChatModel.

    Returns:
        Dict with ``env``, ``fixture_path``, and ``mock_model`` (the actual
        instance handed back by build_chat_model). Tests may inspect
        ``mock_model._entries`` / ``mock_model._index`` to assert how many
        replay rounds were consumed.
    """
    key = _resolve_scenario_key(request)
    env: dict[str, str] = {"LLM_BACKEND": "mock"}
    fixture_path: pathlib.Path | None = None
    mock_model: Any = None

    if key:
        fixture_path = _LLM_TRACES_ROOT / f"{key}.jsonl"
        env["MOCK_LLM_FIXTURE"] = str(fixture_path)
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    if fixture_path is not None and fixture_path.exists():
        try:
            from sft_agents.llm.mock import MockReplayChatModel  # noqa: PLC0415

            mock_model = MockReplayChatModel(fixture_path)

            def _factory(**_kw: Any) -> Any:
                return mock_model

            # Patch the canonical entry point AND the per-agent re-exports
            # (operator-assistant + production-planner import build_chat_model
            # into their own module namespace).
            try:
                import sft_agents.llm.factory as _factory_mod  # noqa: PLC0415

                monkeypatch.setattr(_factory_mod, "build_chat_model", _factory)
            except ImportError:
                pass
            for mod_path in (
                "ops_operator_assistant.agent",
                "ops_production_planner.agent",
                "ops_quality_inspector.grader",
            ):
                try:
                    mod = __import__(mod_path, fromlist=["build_chat_model"])
                    if hasattr(mod, "build_chat_model"):
                        monkeypatch.setattr(mod, "build_chat_model", _factory)
                except ImportError:
                    # Agent not installed in this env — fine, the test that
                    # needs it will skip via importorskip.
                    pass
        except ImportError:
            # MockReplayChatModel not available — tests that need it will
            # skip via importorskip on the agent package.
            mock_model = None

    return {
        "env": env,
        "fixture_path": fixture_path,
        "mock_model": mock_model,
    }


# ---------------------------------------------------------------------------
# Mock collaborator factory
# ---------------------------------------------------------------------------


def _make_mock_rag_pipeline(qdrant_chunks: list[dict[str, Any]] | None) -> MagicMock:
    """Build a mock RAG pipeline whose .search() yields RagCitation-shaped objects."""
    chunks = qdrant_chunks or []

    citations: list[Any] = []
    try:
        from sft_domain.ops.citation import RagCitation
        from datetime import datetime, timezone

        for chunk in chunks:
            try:
                citations.append(
                    RagCitation(
                        source_uri=chunk.get("source_uri", "unknown://"),
                        snippet=chunk.get("content", "")[:500],
                        score=float(chunk.get("score", 0.85)),
                        retrieved_at=datetime.now(timezone.utc),
                    )
                )
            except Exception:
                # If the RagCitation schema rejects (e.g. missing required field),
                # skip silently — the test asserts citations_min which the
                # scenario YAML keeps loose.
                continue
    except ImportError:
        # Fall back to dict-shaped citations; the validator that checks
        # citations_missing reads .source_uri via getattr (defensive).
        for chunk in chunks:
            mock = MagicMock()
            mock.source_uri = chunk.get("source_uri", "unknown://")
            mock.snippet = chunk.get("content", "")[:500]
            mock.score = float(chunk.get("score", 0.85))
            citations.append(mock)

    pipeline = MagicMock(name="rag_pipeline")
    pipeline.search = AsyncMock(return_value=citations)
    return pipeline


def _make_audit_writer() -> MagicMock:
    writer = MagicMock(name="audit_writer")
    writer.write = AsyncMock(return_value=None)
    writer.writes = []  # collect all AuditRecord instances for assertions

    async def _capture_write(record: Any) -> None:
        writer.writes.append(record)

    writer.write.side_effect = _capture_write
    return writer


def _make_queue_writer() -> MagicMock:
    writer = MagicMock(name="queue_writer")
    writer.insert = AsyncMock(return_value=None)
    writer.inserts = []  # collect every ApprovalRequest

    async def _capture_insert(approval: Any) -> None:
        writer.inserts.append(approval)

    writer.insert.side_effect = _capture_insert
    return writer


def _make_nats_publisher() -> MagicMock:
    nats = MagicMock(name="nats_publisher")
    nats.publish_approval_new = AsyncMock(return_value=None)
    nats.publish_approval_resolved = AsyncMock(return_value=None)
    return nats


def _make_safety_middleware() -> MagicMock:
    safety = MagicMock(name="safety_middleware")
    safety.check = AsyncMock(return_value=None)
    safety.check_invocations = []

    async def _capture_check(*args: Any, **kwargs: Any) -> None:
        safety.check_invocations.append((args, kwargs))

    safety.check.side_effect = _capture_check
    return safety


@pytest.fixture
def mock_collaborators() -> dict[str, Any]:
    """Return a dict of mocked collaborators usable by any OPS agent.

    Each agent picks the subset it needs (no Pydantic constructor rejects
    unused kwargs — agents use kw-only ``__init__``).
    """
    return {
        "audit_writer": _make_audit_writer(),
        "queue_writer": _make_queue_writer(),
        "nats": _make_nats_publisher(),
        "nats_publisher": _make_nats_publisher(),  # quality-inspector uses this name
        "safety_middleware": _make_safety_middleware(),
        "pool": MagicMock(name="pool"),
        "checkpointer": MagicMock(name="checkpointer"),
        "neo4j_driver": MagicMock(name="neo4j_driver"),
    }


@pytest.fixture
def make_rag_pipeline():
    """Return a factory: ``make_rag_pipeline(chunks_from_scenario)``."""
    return _make_mock_rag_pipeline


# ---------------------------------------------------------------------------
# Patched human_approval_node — captures the interrupt() boundary
# ---------------------------------------------------------------------------


@pytest.fixture
def patched_human_approval(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[dict[str, Any]]]:
    """Replace human_approval_node across all OPS agents with an async capturer.

    Returns a dict ``{"calls": [...]}`` where each entry is the kwargs handed
    to the real ``human_approval_node`` — used by tests to assert the HITL
    tier, the ProposedAction shape, and the EvidencePanel attachment.

    The interrupt() boundary is bypassed so the agent's __call__ completes
    without raising GraphInterrupt; this is the standard contract-test
    pattern (see apps/agents/ops/production-planner/tests/test_production_planner.py
    fixture `patched_approval`).
    """
    captured: dict[str, list[dict[str, Any]]] = {"calls": []}

    async def _fake_approval(state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        captured["calls"].append({"state": dict(state), **kwargs})
        return {
            "pending_approval_id": None,
            "evidence": kwargs.get("evidence_panel"),
            "_test_tier": getattr(kwargs.get("tier"), "value", kwargs.get("tier")),
            "_test_action_type": getattr(
                kwargs.get("proposed_action"), "action_type", None
            ),
        }

    for mod_path in (
        "ops_operator_assistant.agent",
        "ops_production_planner.agent",
        "ops_quality_inspector.agent",
    ):
        try:
            mod = __import__(mod_path, fromlist=["human_approval_node"])
            if hasattr(mod, "human_approval_node"):
                monkeypatch.setattr(mod, "human_approval_node", _fake_approval)
        except ImportError:
            # Agent not installed in this env; the consuming test will skip
            # via pytest.importorskip on the agent package.
            pass

    return captured


# ---------------------------------------------------------------------------
# scenario JSONL inspection helper
# ---------------------------------------------------------------------------


@pytest.fixture
def scenario_llm_entries(ops_scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """Read the JSONL trace pointed at by ``ops_scenario.mock_llm_fixture``."""
    relpath = ops_scenario.get("mock_llm_fixture")
    if not relpath:
        return []
    path = _REPO_ROOT / relpath
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Marker registration (defensive — also declared at root conftest.py)
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register e2e + real-llm markers in case this conftest is the only one loaded."""
    config.addinivalue_line(
        "markers",
        "e2e: marks ops e2e scenario tests (Plan 06-13)",
    )
    config.addinivalue_line(
        "markers",
        "real-llm: opt-in real Qwen2.5 smoke tests (default-skipped in CI)",
    )
