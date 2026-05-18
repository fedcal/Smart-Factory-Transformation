"""tests/integration/test_audit_stream_bootstrap.py

End-to-end verification of the Plan 04-04 audit NATS substrate:

1. `scripts/nats-bootstrap-streams.py` declares `AUDIT_STREAM` idempotently
   with the 3 wildcard subjects (`audit.actions.>`, `hitl.approvals.>`,
   `hitl.governor.>`) and 90-day retention.
2. `AuditNatsPublisher.publish_audit(record)` publishes a JSON-encoded
   AuditRecord to the derived subject; a pull consumer can read it back.

Strategy:
    Use a testcontainers-managed `nats:2.10-alpine` container with JetStream
    enabled (`-js` flag). Self-contained — no dependency on the compose stack.

Skip conditions:
    - testcontainers or nats-py not installed
    - Docker daemon not running
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import subprocess
import sys
from datetime import UTC, datetime
from uuid import uuid4

import pytest

# Skip the whole module if testcontainers is missing
testcontainers = pytest.importorskip(
    "testcontainers.core.container",
    reason="testcontainers not installed",
)
pytest.importorskip("nats", reason="nats-py not installed")

from testcontainers.core.container import DockerContainer  # noqa: E402
from testcontainers.core.waiting_utils import wait_for_logs  # noqa: E402

_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
_BOOTSTRAP_SCRIPT = _REPO_ROOT / "scripts" / "nats-bootstrap-streams.py"
_NATS_PORT = 4222


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(scope="module")
def nats_container():
    """Spin up a NATS JetStream container, yield its bound URL, then teardown."""
    if not _docker_available():
        pytest.skip("docker not available — skipping NATS integration test")

    container = (
        DockerContainer("nats:2.10-alpine")
        .with_command("-js")
        .with_exposed_ports(_NATS_PORT)
    )
    container.start()
    try:
        # Wait until JetStream is fully initialized
        wait_for_logs(container, "Server is ready", timeout=30)
        host = container.get_container_host_ip()
        port = container.get_exposed_port(_NATS_PORT)
        url = f"nats://{host}:{port}"
        yield url
    finally:
        container.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_creates_audit_stream(nats_container: str) -> None:
    """First run of nats-bootstrap-streams.py creates AUDIT_STREAM with the
    declared 3 wildcard subjects + 90-day retention + FileStorage."""
    import nats
    from nats.js.api import StorageType

    env = {**os.environ, "NATS_URL": nats_container}
    proc = subprocess.run(
        [sys.executable, str(_BOOTSTRAP_SCRIPT), "--server", nats_container],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"bootstrap failed: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )

    nc = await nats.connect(nats_container)
    try:
        js = nc.jetstream()
        info = await js.stream_info("AUDIT_STREAM")
        cfg = info.config
        assert set(cfg.subjects) == {
            "audit.actions.>",
            "hitl.approvals.>",
            "hitl.governor.>",
        }, f"expected 3 wildcard subjects, got {cfg.subjects}"
        # nats-py 2.14 returns max_age in seconds (the wire format is ns;
        # the client converts back on retrieve). 90 days * 86400 s/day = 7776000 s.
        assert cfg.max_age == 90 * 24 * 3600, (
            f"expected 90-day retention in seconds, got {cfg.max_age}"
        )
        assert cfg.storage == StorageType.FILE

        # Regression: SENSOR_EVENTS + AUDIT_OT MUST still exist
        sensor_info = await js.stream_info("SENSOR_EVENTS")
        assert "sensor.events.>" in sensor_info.config.subjects
        audit_ot_info = await js.stream_info("AUDIT_OT")
        assert "audit.ot.>" in audit_ot_info.config.subjects
    finally:
        await nc.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_is_idempotent(nats_container: str) -> None:
    """Second run hits BadRequestError → update_stream branch → exit 0."""
    proc = subprocess.run(
        [sys.executable, str(_BOOTSTRAP_SCRIPT), "--server", nats_container],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"second bootstrap run failed: "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    # update_stream branch should fire on at least one of the existing streams
    assert "updated" in proc.stdout or "created" in proc.stdout


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_publisher_round_trip(nats_container: str) -> None:
    """AuditNatsPublisher.publish_audit() lands a JSON-encoded record on
    `audit.actions.<cluster>.<agent_id>` and a pull consumer reads it back."""
    import nats
    from sft_agents.audit.nats_publisher import AuditNatsPublisher
    from sft_agents.models.audit import AuditRecord
    from sft_agents.models.budget import BudgetSnapshot
    from sft_agents.models.enums import Decision
    from sft_agents.models.evidence import EvidencePanel, TokenUsage

    # Publish
    publisher = AuditNatsPublisher(nats_container)
    await publisher.connect()
    try:
        evidence = EvidencePanel(
            input_summary="integration test",
            tool_calls=[],
            rag_citations=[],
            confidence=0.9,
            model="qwen2.5-14b-awq@vllm-0.8",
            prompt_hash="b" * 64,
            tokens=TokenUsage(input=10, output=5, total=15),
            duration_ms=42,
        )
        budget = BudgetSnapshot(
            tokens_input=10,
            tokens_output=5,
            tokens_total=15,
            cost_usd_simulated=0.01,
            duration_ms=42,
            limit_tokens=50000,
            limit_cost_usd=1.0,
            limit_duration_s=60,
        )
        record = AuditRecord(
            id=uuid4(),
            ts=datetime.now(UTC),
            action_id=uuid4(),
            agent_id="operator-assistant",
            thread_id="ops.operator-assistant.it-1",
            cluster="ops",
            action_type="TEST_ROUND_TRIP",
            evidence_panel=evidence,
            decision=Decision.AUTO,
            budget_snapshot=budget,
        )
        await publisher.publish_audit(record)
    finally:
        await publisher.drain()

    # Consume via a pull subscriber on the AUDIT_STREAM
    nc = await nats.connect(nats_container)
    try:
        js = nc.jetstream()
        sub = await js.pull_subscribe(
            "audit.actions.ops.operator-assistant",
            durable="audit-it-consumer",
            stream="AUDIT_STREAM",
        )
        msgs = await asyncio.wait_for(sub.fetch(1, timeout=10), timeout=15)
        assert len(msgs) == 1, f"expected exactly 1 msg, got {len(msgs)}"

        import json

        payload = json.loads(msgs[0].data.decode("utf-8"))
        assert payload["agent_id"] == "operator-assistant"
        assert payload["cluster"] == "ops"
        assert payload["decision"] == "auto"
        assert payload["action_type"] == "TEST_ROUND_TRIP"
        await msgs[0].ack()
    finally:
        await nc.close()
