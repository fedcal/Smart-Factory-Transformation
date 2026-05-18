"""Tests for sft_agents.runtime.checkpointer (Plan 04-05 Task 1).

Covers:
    - format_thread_id happy path + error cases (D-59 thread_id convention)
    - parse_thread_id round-trip + malformed input
    - AsyncPostgresSaver context manager round-trip (integration, testcontainers PG)

Integration tests are gated by @pytest.mark.integration (skip on missing Docker).
"""
from __future__ import annotations

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest


# ---------------------------------------------------------------------------
# Unit: format_thread_id
# ---------------------------------------------------------------------------


def test_format_thread_id_happy_path() -> None:
    from sft_agents.runtime import format_thread_id

    out = format_thread_id(
        "ops",
        "operator-assistant",
        UUID("00000000-0000-0000-0000-000000000001"),
    )
    assert out == "ops.operator-assistant.00000000-0000-0000-0000-000000000001"


def test_format_thread_id_accepts_str_uuid() -> None:
    from sft_agents.runtime import format_thread_id

    out = format_thread_id(
        "maintenance",
        "predictive-maintenance",
        "11111111-1111-1111-1111-111111111111",
    )
    assert out == "maintenance.predictive-maintenance.11111111-1111-1111-1111-111111111111"


def test_format_thread_id_rejects_invalid_cluster() -> None:
    from sft_agents.runtime import format_thread_id

    with pytest.raises(ValueError, match="cluster"):
        format_thread_id("badcluster", "operator-assistant", uuid4())


def test_format_thread_id_rejects_agent_id_with_dot() -> None:
    from sft_agents.runtime import format_thread_id

    # Agent id containing '.' would break parse_thread_id round-trip.
    with pytest.raises(ValueError, match="agent_id"):
        format_thread_id("ops", "operator.assistant", uuid4())


def test_format_thread_id_rejects_agent_id_uppercase() -> None:
    from sft_agents.runtime import format_thread_id

    with pytest.raises(ValueError, match="agent_id"):
        format_thread_id("ops", "OperatorAssistant", uuid4())


def test_format_thread_id_rejects_invalid_uuid_string() -> None:
    from sft_agents.runtime import format_thread_id

    with pytest.raises((ValueError, TypeError)):
        format_thread_id("ops", "operator-assistant", "not-a-uuid")


# ---------------------------------------------------------------------------
# Unit: parse_thread_id
# ---------------------------------------------------------------------------


def test_parse_thread_id_round_trip() -> None:
    from sft_agents.runtime import format_thread_id, parse_thread_id

    session = UUID("22222222-2222-2222-2222-222222222222")
    thread_id = format_thread_id("supply", "inventory-manager", session)
    cluster, agent_id, parsed_session = parse_thread_id(thread_id)
    assert cluster == "supply"
    assert agent_id == "inventory-manager"
    assert parsed_session == session


def test_parse_thread_id_rejects_malformed() -> None:
    from sft_agents.runtime import parse_thread_id

    with pytest.raises(ValueError):
        parse_thread_id("not_dot_separated")

    with pytest.raises(ValueError):
        parse_thread_id("ops.too.many.dots.here")


def test_parse_thread_id_rejects_invalid_cluster() -> None:
    from sft_agents.runtime import parse_thread_id

    with pytest.raises(ValueError, match="cluster"):
        parse_thread_id("badcluster.operator-assistant.22222222-2222-2222-2222-222222222222")


def test_parse_thread_id_rejects_invalid_uuid() -> None:
    from sft_agents.runtime import parse_thread_id

    with pytest.raises(ValueError):
        parse_thread_id("ops.operator-assistant.not-a-uuid")


# ---------------------------------------------------------------------------
# Unit: VALID_CLUSTERS + RoutingDecision contract
# ---------------------------------------------------------------------------


def test_valid_clusters_exactly_five() -> None:
    from sft_agents.runtime import VALID_CLUSTERS

    assert VALID_CLUSTERS == frozenset(
        {"ops", "maintenance", "knowledge-curation", "knowledge-training", "supply"}
    )


def test_routing_decision_is_frozen_and_validates() -> None:
    from pydantic import ValidationError

    from sft_agents.runtime import RoutingDecision

    rd = RoutingDecision(cluster="ops", strategy="rules", confidence=1.0, matched_keyword="allarme")
    with pytest.raises(ValidationError):
        rd.cluster = "maintenance"  # type: ignore[misc]  # frozen


def test_routing_decision_rejects_unknown_strategy() -> None:
    from pydantic import ValidationError

    from sft_agents.runtime import RoutingDecision

    with pytest.raises(ValidationError):
        RoutingDecision(cluster="ops", strategy="lol", confidence=0.5)  # type: ignore[arg-type]


def test_routing_decision_confidence_bounded() -> None:
    from pydantic import ValidationError

    from sft_agents.runtime import RoutingDecision

    with pytest.raises(ValidationError):
        RoutingDecision(cluster="ops", strategy="rules", confidence=1.5)
    with pytest.raises(ValidationError):
        RoutingDecision(cluster="ops", strategy="rules", confidence=-0.1)


# ---------------------------------------------------------------------------
# Integration: AsyncPostgresSaver round-trip against testcontainers PG
# ---------------------------------------------------------------------------


_TIMESCALE_IMAGE = "timescale/timescaledb:2.18.0-pg16"
_DB_USER = "sft"
_DB_PASS = "sft_dev_pass"
_DB_NAME = "sft"


@pytest.fixture(scope="module")
def langgraph_pg_dsn() -> Generator[str, None, None]:
    """Module-scoped testcontainer with LangGraph checkpoint tables initialised."""
    pytest.importorskip("testcontainers.postgres")
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer(
        image=_TIMESCALE_IMAGE,
        username=_DB_USER,
        password=_DB_PASS,
        dbname=_DB_NAME,
    ) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        dsn = f"postgresql://{_DB_USER}:{_DB_PASS}@{host}:{port}/{_DB_NAME}"
        yield dsn


@pytest.mark.integration
async def test_get_postgres_checkpointer_round_trip(
    langgraph_pg_dsn: str,
) -> None:
    """AsyncPostgresSaver round-trip: setup → aput → aget_tuple returns the checkpoint."""
    pytest.importorskip("langgraph.checkpoint.postgres.aio")
    from langgraph.checkpoint.base import empty_checkpoint  # noqa: PLC0415

    from sft_agents.runtime import format_thread_id, get_postgres_checkpointer  # noqa: PLC0415

    # First call: run setup() to create checkpoint tables.
    import os

    os.environ["SFT_LANGGRAPH_AUTO_SETUP"] = "1"
    try:
        async with get_postgres_checkpointer(langgraph_pg_dsn) as saver:
            session = uuid4()
            thread_id = format_thread_id("ops", "operator-assistant", session)
            # langgraph-checkpoint-postgres requires both thread_id and checkpoint_ns
            # (namespace, empty-string for the top-level graph).
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": "",
                }
            }

            ckpt = empty_checkpoint()
            # Mark the checkpoint to assert round-trip identity.
            ckpt["channel_values"] = {"marker": "phase-04-plan-05-checkpointer-roundtrip"}

            stored_config = await saver.aput(config, ckpt, {}, {})

            loaded = await saver.aget_tuple(stored_config)
            assert loaded is not None, "Expected aget_tuple to return the checkpoint we just stored"
            assert loaded.checkpoint["channel_values"]["marker"] == (
                "phase-04-plan-05-checkpointer-roundtrip"
            )
    finally:
        os.environ.pop("SFT_LANGGRAPH_AUTO_SETUP", None)
