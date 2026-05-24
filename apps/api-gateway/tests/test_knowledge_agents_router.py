"""Unit tests for knowledge-cluster HTTP endpoints (Plan 08-08 — TRN-02/03/04/05).

Covers 5 knowledge agent endpoints:
    POST /v1/agents/shift-handover/compile         (202, D-SH-01 manual trigger)
    POST /v1/agents/training-coach/session         (200, TRN-02 quiz start)
    POST /v1/agents/training-coach/resume          (200, TRN-02 post-HITL resume)
    POST /v1/agents/knowledge-curator/ingest       (200, D-KC-04 autonomous)
    POST /v1/agents/documentation-synthesizer/draft (202, TRN-04 async HITL)

All tests use FastAPI TestClient (httpx.AsyncClient) with a stubbed supervisor graph
(AsyncMock ainvoke) — internal cluster routing is verified E2E in a later phase.
Pattern mirrors test_maintenance_endpoints.py using conftest.py fixtures.

Key assertions:
    1. Each endpoint returns its expected status code (202/200/200/200/202).
    2. Each endpoint sets state["target_agent"] to the correct slug.
    3. ShiftHandoverCompileRequest validates shift_end > shift_start (422 on inversion).
    4. knowledge-curator/ingest does NOT require Idempotency-Key (autonomous, D-KC-04).
    5. RecursionError → 503 + Retry-After header.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc

_VALID_SHIFT_START = datetime(2026, 5, 24, 6, 0, tzinfo=UTC).isoformat()
_VALID_SHIFT_END = datetime(2026, 5, 24, 14, 0, tzinfo=UTC).isoformat()
_VALID_LAST_UPDATED = datetime(2026, 5, 1, 10, 0, tzinfo=UTC).isoformat()


# ---------------------------------------------------------------------------
# ShiftHandover /compile — 4 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_shift_handover_compile_returns_202(
    client, app_with_mocks
) -> None:
    """POST /v1/agents/shift-handover/compile → 202 with hitl_status='supervisor_pending'."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"handover_report": None, "messages": []})

    body = {
        "shift_start": _VALID_SHIFT_START,
        "shift_end": _VALID_SHIFT_END,
        "user_roles": ["shift_supervisor"],
    }
    response = await client.post("/v1/agents/shift-handover/compile", json=body)
    assert response.status_code == 202, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]

    assert state_arg["target_agent"] == "shift-handover"
    assert state_arg["user_roles"] == ["shift_supervisor"]
    assert config["recursion_limit"] == 5
    assert config["configurable"]["thread_id"].startswith("knowledge.shift-handover.")

    payload = response.json()
    assert payload["hitl_status"] == "supervisor_pending"
    assert "thread_id" in payload
    assert payload["thread_id"].startswith("knowledge.shift-handover.")


@pytest.mark.asyncio
async def test_post_shift_handover_compile_inverted_window_422(
    client, app_with_mocks
) -> None:
    """shift_end <= shift_start → 422 (model_validator constraint)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {
        "shift_start": _VALID_SHIFT_END,   # inverted: start after end
        "shift_end": _VALID_SHIFT_START,
        "user_roles": ["shift_supervisor"],
    }
    response = await client.post("/v1/agents/shift-handover/compile", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_shift_handover_compile_missing_user_roles_422(
    client, app_with_mocks
) -> None:
    """Missing user_roles → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {
        "shift_start": _VALID_SHIFT_START,
        "shift_end": _VALID_SHIFT_END,
    }
    response = await client.post("/v1/agents/shift-handover/compile", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_shift_handover_compile_empty_user_roles_422(
    client, app_with_mocks
) -> None:
    """Empty user_roles list → 422 (min_length=1 constraint)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    body = {
        "shift_start": _VALID_SHIFT_START,
        "shift_end": _VALID_SHIFT_END,
        "user_roles": [],
    }
    response = await client.post("/v1/agents/shift-handover/compile", json=body)
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# TrainingCoach /session — 3 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_training_session_returns_200(client, app_with_mocks) -> None:
    """POST /v1/agents/training-coach/session → 200 with thread_id."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"competency_result": None, "training_session": None, "messages": []}
    )

    body = {
        "persona_role": "tessitore",
        "user_roles": ["operator"],
    }
    response = await client.post("/v1/agents/training-coach/session", json=body)
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]

    assert state_arg["target_agent"] == "training-coach"
    assert state_arg["persona_role"] == "tessitore"
    assert state_arg["user_roles"] == ["operator"]
    assert config["recursion_limit"] == 5
    assert config["configurable"]["thread_id"].startswith("knowledge.training-coach.")

    payload = response.json()
    assert "thread_id" in payload
    assert payload["thread_id"].startswith("knowledge.training-coach.")


@pytest.mark.asyncio
async def test_post_training_session_missing_persona_role_422(
    client, app_with_mocks
) -> None:
    """Missing persona_role → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/training-coach/session",
        json={"user_roles": ["operator"]},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_training_session_empty_user_roles_422(
    client, app_with_mocks
) -> None:
    """Empty user_roles → 422 (min_length=1)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/training-coach/session",
        json={"persona_role": "tessitore", "user_roles": []},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# TrainingCoach /resume — 2 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_training_resume_returns_200(client, app_with_mocks) -> None:
    """POST /v1/agents/training-coach/resume → 200, sets target_agent=training-coach."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"competency_result": None, "training_session": None}
    )

    thread_id = "knowledge.training-coach.abc123"
    body = {
        "thread_id": thread_id,
        "decision": "approved",
    }
    response = await client.post("/v1/agents/training-coach/resume", json=body)
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    assert state_arg["target_agent"] == "training-coach"
    assert state_arg["decision"] == "approved"
    assert state_arg["thread_id"] == thread_id

    # Config thread_id must match the provided thread_id (LangGraph checkpoint replay)
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]
    assert config["configurable"]["thread_id"] == thread_id


@pytest.mark.asyncio
async def test_post_training_resume_missing_decision_422(
    client, app_with_mocks
) -> None:
    """Missing decision → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/training-coach/resume",
        json={"thread_id": "knowledge.training-coach.abc123"},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# KnowledgeCurator /ingest — 4 tests (autonomous, no Idempotency-Key)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_knowledge_curator_ingest_returns_200(
    client, app_with_mocks
) -> None:
    """POST /v1/agents/knowledge-curator/ingest → 200, autonomous (D-KC-04)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"curation_report": None, "messages": []}
    )

    body = {
        "document_id": "doc-test-001",
        "document_text": "Questo è un documento di prova per il test di dedup.",
        "doc_type": "sop",
        "last_updated": _VALID_LAST_UPDATED,
        "source_uri": "sop://test/doc-001",
    }
    response = await client.post("/v1/agents/knowledge-curator/ingest", json=body)
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]

    assert state_arg["target_agent"] == "knowledge-curator"
    assert state_arg["document_id"] == "doc-test-001"
    assert state_arg["doc_type"] == "sop"
    assert state_arg["source_uri"] == "sop://test/doc-001"
    assert config["configurable"]["thread_id"].startswith("knowledge.knowledge-curator.")

    payload = response.json()
    assert "thread_id" in payload
    assert payload["thread_id"].startswith("knowledge.knowledge-curator.")


@pytest.mark.asyncio
async def test_post_knowledge_curator_ingest_no_hitl_resume_path(
    client, app_with_mocks
) -> None:
    """knowledge-curator/ingest is autonomous (D-KC-04): no HITL interrupt expected.

    Asserts the endpoint returns synchronously with 200 (not 202) — confirms the
    autonomous design where no supervisor sign-off is needed.
    """
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"curation_report": {"dedup_verdict": "unique", "stale": False}}
    )

    body = {
        "document_id": "doc-auto-test-001",
        "document_text": "Documento di test per verifica autonomia.",
        "doc_type": "manual",
        "last_updated": _VALID_LAST_UPDATED,
        "source_uri": "sop://test/autonomia-001",
    }
    response = await client.post("/v1/agents/knowledge-curator/ingest", json=body)
    # Autonomous: always synchronous 200, never 202
    assert response.status_code == 200, response.text
    # Only one ainvoke call — no resume step needed
    assert graph.ainvoke.await_count == 1


@pytest.mark.asyncio
async def test_post_knowledge_curator_ingest_missing_document_text_422(
    client, app_with_mocks
) -> None:
    """Missing document_text → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/knowledge-curator/ingest",
        json={"doc_type": "sop", "last_updated": _VALID_LAST_UPDATED},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_knowledge_curator_ingest_missing_doc_type_422(
    client, app_with_mocks
) -> None:
    """Missing doc_type → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/knowledge-curator/ingest",
        json={
            "document_text": "Testo documento.",
            "last_updated": _VALID_LAST_UPDATED,
        },
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# DocumentationSynthesizer /draft — 3 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_documentation_draft_returns_202(client, app_with_mocks) -> None:
    """POST /v1/agents/documentation-synthesizer/draft → 202 with hitl_status='supervisor_pending'."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"sop_draft": None, "messages": []}
    )

    body = {
        "failure_mode": "surriscaldamento motore",
        "asset_id": "LOOM-01",
        "window_days": 30,
    }
    response = await client.post(
        "/v1/agents/documentation-synthesizer/draft", json=body
    )
    assert response.status_code == 202, response.text

    assert graph.ainvoke.await_count == 1
    state_arg = graph.ainvoke.call_args.args[0]
    config = graph.ainvoke.call_args.kwargs.get("config") or graph.ainvoke.call_args.args[1]

    assert state_arg["target_agent"] == "documentation-synthesizer"
    assert state_arg["failure_mode"] == "surriscaldamento motore"
    assert state_arg["asset_id"] == "LOOM-01"
    assert state_arg["window_days"] == 30
    assert config["recursion_limit"] == 5
    assert config["configurable"]["thread_id"].startswith(
        "knowledge.documentation-synthesizer."
    )

    payload = response.json()
    assert payload["hitl_status"] == "supervisor_pending"
    assert "thread_id" in payload


@pytest.mark.asyncio
async def test_post_documentation_draft_missing_failure_mode_422(
    client, app_with_mocks
) -> None:
    """Missing failure_mode → 422."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/documentation-synthesizer/draft",
        json={"asset_id": "LOOM-01", "window_days": 30},
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


@pytest.mark.asyncio
async def test_post_documentation_draft_window_days_out_of_range_422(
    client, app_with_mocks
) -> None:
    """window_days > 365 → 422 (le=365 constraint)."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={})

    response = await client.post(
        "/v1/agents/documentation-synthesizer/draft",
        json={
            "failure_mode": "rottura cinghia",
            "asset_id": "LOOM-01",
            "window_days": 366,
        },
    )
    assert response.status_code == 422, response.text
    assert graph.ainvoke.await_count == 0


# ---------------------------------------------------------------------------
# Cross-cutting — 2 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recursion_overflow_returns_503_with_retry_after(
    client, app_with_mocks
) -> None:
    """RecursionError from supervisor → 503 with Retry-After header."""
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        side_effect=RecursionError("recursion limit exceeded")
    )

    # Use the shift-handover endpoint (202 endpoint) for this cross-cutting test
    body = {
        "shift_start": _VALID_SHIFT_START,
        "shift_end": _VALID_SHIFT_END,
        "user_roles": ["shift_supervisor"],
    }
    response = await client.post("/v1/agents/shift-handover/compile", json=body)
    assert response.status_code == 503, response.text
    assert "Retry-After" in response.headers
    body_json = response.json()
    assert body_json["error"] == "recursion_limit_exceeded"
    assert "thread_id" in body_json


@pytest.mark.asyncio
async def test_knowledge_curator_ingest_idempotency_key_not_required(
    client, app_with_mocks
) -> None:
    """knowledge-curator/ingest accepts repeated identical calls without Idempotency-Key.

    Two identical POSTs both return 200 and both invoke supervisor — the
    endpoint is idempotent by design (D-KC-04 autonomous verdict is deterministic)
    but does NOT use the idempotency cache middleware (no Idempotency-Key param).
    """
    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(
        return_value={"curation_report": {"dedup_verdict": "unique", "stale": False}}
    )

    body = {
        "document_id": "doc-idem-test-001",
        "document_text": "Testo ripetuto per test idempotency.",
        "doc_type": "training_material",
        "last_updated": _VALID_LAST_UPDATED,
        "source_uri": "sop://test/idempotency-001",
    }

    r1 = await client.post("/v1/agents/knowledge-curator/ingest", json=body)
    r2 = await client.post("/v1/agents/knowledge-curator/ingest", json=body)

    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    # Both calls reach the supervisor (no caching — D-KC-04 autonomous design)
    assert graph.ainvoke.await_count == 2
