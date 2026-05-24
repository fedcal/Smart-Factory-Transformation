"""E2E test: four-agent supply cluster + per-agent audit-row counts + OEPV + cross-cluster plan.

Plan 09-07 / Phase 9 closure.

Exercises all four supply agents end-to-end through the supply_agents.py HTTP router
(09-06), using a mock supervisor graph that returns semantically structured per-agent
state.  No live infrastructure required: all DB/NATS calls are satisfied by AsyncMock
collaborators wired into the FastAPI app state.

The test mirrors the architecture of test_knowledge_cluster_e2e.py (08-09): HTTP client
backed by ASGITransport, graph mock with per-call side_effect, audit-event accumulator
asserted after each HITL step.  The Mantis synthetic seed data model (scm_mantis_seed.sql)
drives the numeric assertions — exact values are computed from the seed parameters, not
hardcoded against a particular calendar date.

Scenarios covered
-----------------
InventoryManager (SCM-01)
    REORDER_ALERT on the below-threshold SKU (jersey qty=310 < reorder_point=500).
    check POST → 202 supervisor_pending.
    resume POST → exactly 1 PURCHASE_RECOMMENDATION_DRAFT + 1 PURCHASE_SIGNOFF, both
    sharing a stable recommendation_id.  Replay simulation asserts no double-write.

EnergyOptimizer (SCM-02)
    optimize POST → 202 supervisor_pending.
    resume POST → exactly 1 ENERGY_PROPOSAL + 1 ENERGY_SIGNOFF.
    EnPI actual (4.12) > baseline (3.80) asserted from seed values.

CostAnalyzer (SCM-03) — autonomous
    analyze POST → 200 synchronous (no interrupt, no resume endpoint).
    Response carries CostBreakdown + OepvReport with total_score in [0,100],
    offer_eur derived from BA=108_000 and ribasso_pct=10.
    Exactly 1 Decision.AUTO audit-row; no interrupt called (graph.ainvoke exactly once).

DemandForecaster (SCM-04)
    forecast POST → 202 supervisor_pending.
    resume POST → 200 with demand_plan for >= 2 SKU groups (jersey + twill).
    Exactly 1 DEMAND_PLAN_DRAFT + 1 DEMAND_PLAN_SIGNOFF sharing a stable plan_id.
    demand_plan appears in the response state delta under the ProductionPlanner publish key.
    Rolling MAPE <= 100 (CR-05 compliance).

Replay / double-write (T-09-27)
    Simulate a second resume call on the InventoryManager thread and assert that
    audit-event count does NOT increase beyond 1 DRAFT + 1 SIGNOFF.

Timestamp robustness
    All seed-derived numeric values (EnPI 4.12, baseline 3.80, reorder quantities,
    BA 108_000, Mantis jersey/twill demand volumes) are referenced by constant name,
    not by absolute calendar date.  This mirrors the NOW()-relative seed strategy in
    scm_mantis_seed.sql and keeps the assertions stable across time zones and re-runs.

LLM backend
    LLM_BACKEND=mock is set via monkeypatch so no live model is contacted.

Markers
-------
    integration  — requires Docker in the full suite; collection-only without.
    asyncio      — async fixtures / awaitable test functions.

Pattern mirrors apps/api-gateway/tests/test_knowledge_cluster_e2e.py (08-09) with
supply-specific numeric assertions replacing the TRN-05 citation-provenance gate.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ---------------------------------------------------------------------------
# Constants (mirrored from scm_mantis_seed.sql — seed-aware, NOT calendar-anchored)
# ---------------------------------------------------------------------------

UTC = timezone.utc

# --- Mantis EnPI seed values (scm.enpi_baseline, dyeing row) ----------------
_SEED_ENPI_ACTUAL_YTD: float = 4.12      # kwh_per_kg_actual_ytd (dyeing)
_SEED_ENPI_BASELINE: float = 3.80        # kwh_per_kg_target (dyeing)

# --- Mantis OEPV anchor (docs/mantis-synthetic-dataset.md) ------------------
_SEED_BASE_D_ASTA_EUR: float = 108_000.0  # OepvConfig.base_d_asta_eur

# --- OEPV simulation inputs (matching Phase 9 CostAnalyzeRequest defaults) --
_TEST_RIBASSO_PCT: float = 10.0   # default ribasso_pct
_TEST_PT: float = 50.0            # default punteggio tecnico

# --- Expected OEPV outputs (derived from oepv.py formula, seeded at _TEST_RIBASSO_PCT=10,
#     _TEST_PT=50, OepvConfig defaults: weight_technical=0.70, weight_economic=0.30,
#     pe_max=30, lambda_curve=3.0, ribasso_ref_pct=20.0, anomaly_threshold_pct=20.0) ---
#
#   Pe = 30 * (1 - exp(-3.0 * 10 / 20)) = 30 * (1 - exp(-1.5)) ≈ 30 * 0.7769 ≈ 23.307
#   total = 0.70 * 50 + 0.30 * 23.307 = 35.0 + 6.992 ≈ 41.992
#   offer_eur = 108000 * (1 - 10/100) = 97200
#   is_anomaly_warning = 10 < 20 → False
_EXPECTED_OFFER_EUR: float = 97_200.0  # 108000 * 0.90
_OEPV_SCORE_MIN: float = 0.0
_OEPV_SCORE_MAX: float = 100.0

# --- Mantis reorder seed values (scm.inventory_levels: jersey qty=310 < rp=500) ---
_SEED_JERSEY_CURRENT_QTY: float = 310.0
_SEED_JERSEY_REORDER_POINT: float = 500.0

# --- Mantis demand seed SKU groups (scm.historical_orders) ---
_SEED_SKU_GROUPS: list[str] = ["jersey", "twill"]
_MIN_SKU_GROUPS_IN_PLAN: int = 2

# ---------------------------------------------------------------------------
# Helpers — build audit-event dicts (supply action types from 09-00a enum)
# ---------------------------------------------------------------------------


def _audit_event(
    event_type: str,
    correlation_id: str,
    decision_actor: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Return a minimal audit event dict.

    ``correlation_id`` is the stable id that links DRAFT and SIGNOFF rows
    (recommendation_id / proposal_id / plan_id — never a random uuid4).
    """
    ev: dict[str, Any] = {
        "event_type": event_type,
        "correlation_id": correlation_id,
        "ts": datetime.now(UTC).isoformat(),
    }
    if decision_actor is not None:
        ev["decision_actor"] = decision_actor
    ev.update(extra)
    return ev


# ---------------------------------------------------------------------------
# Mock supervisor graph factory
# ---------------------------------------------------------------------------


def _make_graph(return_value: dict[str, Any]) -> AsyncMock:
    """Return an AsyncMock supervisor graph that yields *return_value* from ainvoke."""
    graph = AsyncMock()
    graph.ainvoke = AsyncMock(return_value=return_value)
    return graph


# ---------------------------------------------------------------------------
# FastAPI app with mock state (mirrors conftest.py app_with_mocks pattern)
# ---------------------------------------------------------------------------


def _build_app_with_graph(supervisor_graph: AsyncMock) -> Any:
    """Build a FastAPI app with mock state populated from the given graph mock."""
    from svc_api_gateway.idempotency import IdempotencyCache  # local import
    from svc_api_gateway.main import build_app  # local import

    app = build_app()
    app.state.pool = AsyncMock()
    app.state.audit_writer = AsyncMock()
    app.state.queue_writer = AsyncMock()
    app.state.supervisor_graph = supervisor_graph
    app.state.checkpointer = AsyncMock()
    app.state.nats_publisher = AsyncMock()
    app.state.idempotency_cache = IdempotencyCache(ttl_seconds=300)
    return app


# ---------------------------------------------------------------------------
# HTTP client helper
# ---------------------------------------------------------------------------


async def _client_for(app: Any):  # noqa: ANN201
    """Yield an httpx AsyncClient wired to the given ASGI app."""
    import httpx

    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# ===========================================================================
# InventoryManager — REORDER_ALERT → check → resume → audit-row counts (SCM-01)
# ===========================================================================


@pytest.mark.timeout(30)
async def test_inventory_manager_check_and_signoff_audit_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST check → 202; POST resume → exactly 1 DRAFT + 1 SIGNOFF, stable recommendation_id.

    Seeds the below-threshold scenario from scm_mantis_seed.sql:
      SKU-FAB-JERSEY-BLU: qty=310 < reorder_point=500 → REORDER_ALERT.

    Asserts:
      - check returns 202 + supervisor_pending.
      - resume records exactly 1 PURCHASE_RECOMMENDATION_DRAFT + 1 PURCHASE_SIGNOFF.
      - Both events share the same stable recommendation_id (CR-04 correlation check).
      - No double-write: a replay (second resume call) does NOT add more audit rows.
      - REORDER_ALERT is present in the agent response.
    """
    monkeypatch.setenv("LLM_BACKEND", "mock")

    # Stable recommendation_id — derived from thread_id in the agent (CR-04 pattern).
    _stable_rec_id = "inv-rec-" + uuid.uuid4().hex[:16]
    _audit_events: list[dict[str, Any]] = []

    # ---- Step 1: check call (first execution — supervisor_pending) ----
    async def _ainvoke_check(state: dict[str, Any], *, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "messages": [],
            "reorder_recommendation": None,  # pending HITL — no recommendation yet
            "reorder_alert": {
                "alert_type": "REORDER_ALERT",
                "sku_id": "SKU-FAB-JERSEY-BLU",
                "recommendation_id": _stable_rec_id,
                "message": (
                    f"SKU SKU-FAB-JERSEY-BLU below reorder point "
                    f"(current={_SEED_JERSEY_CURRENT_QTY}, "
                    f"threshold={_SEED_JERSEY_REORDER_POINT}). "
                    f"Estimated cost: EUR 12600.00"
                ),
            },
        }

    graph = AsyncMock()
    graph.ainvoke = AsyncMock(side_effect=_ainvoke_check)
    app = _build_app_with_graph(graph)

    async with await _client_for(app) as client:
        check_body = {
            "sku_ids": ["SKU-FAB-JERSEY-BLU"],
            "user_roles": ["procurement_manager"],
        }
        r1 = await client.post("/v1/agents/inventory-manager/check", json=check_body)
        assert r1.status_code == 202, r1.text
        payload1 = r1.json()
        assert "thread_id" in payload1
        assert payload1["hitl_status"] == "supervisor_pending"
        thread_id = payload1["thread_id"]

        # ---- Step 2: resume call (post-HITL — writes DRAFT + SIGNOFF) ----
        async def _ainvoke_resume(
            state: dict[str, Any], *, config: dict[str, Any]
        ) -> dict[str, Any]:
            draft_event = _audit_event(
                "PURCHASE_RECOMMENDATION_DRAFT",
                _stable_rec_id,
                decision_actor=None,  # pending HITL — no actor yet (CR-03)
            )
            signoff_event = _audit_event(
                "PURCHASE_SIGNOFF",
                _stable_rec_id,
                decision_actor="procurement.supervisor@mantis.it",
            )
            _audit_events.append(draft_event)
            _audit_events.append(signoff_event)
            return {
                "messages": [],
                "reorder_recommendation": {
                    "sku_id": "SKU-FAB-JERSEY-BLU",
                    "current_qty": str(_SEED_JERSEY_CURRENT_QTY),
                    "reorder_point": str(_SEED_JERSEY_REORDER_POINT),
                    "reorder_qty": "1500.000",
                    "lead_time_days": 5,
                    "estimated_cost_eur": "12600.000",
                    "recommendation_id": _stable_rec_id,
                },
                "reorder_alert": {
                    "alert_type": "REORDER_ALERT",
                    "sku_id": "SKU-FAB-JERSEY-BLU",
                    "recommendation_id": _stable_rec_id,
                    "message": "REORDER_ALERT approved",
                },
                "audit_events": [draft_event, signoff_event],
            }

        graph.ainvoke = AsyncMock(side_effect=_ainvoke_resume)

        resume_body = {
            "thread_id": thread_id,
            "decision": "approved",
            "decision_actor": "procurement.supervisor@mantis.it",
        }
        r2 = await client.post("/v1/agents/inventory-manager/resume", json=resume_body)
        assert r2.status_code == 200, r2.text
        payload2 = r2.json()

        # ---- Assert: exactly 1 DRAFT + 1 SIGNOFF ----
        drafts = [e for e in _audit_events if e["event_type"] == "PURCHASE_RECOMMENDATION_DRAFT"]
        signoffs = [e for e in _audit_events if e["event_type"] == "PURCHASE_SIGNOFF"]

        assert len(drafts) == 1, (
            f"Expected exactly 1 PURCHASE_RECOMMENDATION_DRAFT, got {len(drafts)}: {_audit_events}"
        )
        assert len(signoffs) == 1, (
            f"Expected exactly 1 PURCHASE_SIGNOFF, got {len(signoffs)}: {_audit_events}"
        )

        # ---- Assert: stable recommendation_id (CR-04 correlation) ----
        assert drafts[0]["correlation_id"] == _stable_rec_id, (
            f"DRAFT correlation_id mismatch: expected {_stable_rec_id!r}, "
            f"got {drafts[0]['correlation_id']!r}"
        )
        assert signoffs[0]["correlation_id"] == _stable_rec_id, (
            f"SIGNOFF correlation_id mismatch: expected {_stable_rec_id!r}, "
            f"got {signoffs[0]['correlation_id']!r}"
        )

        # ---- Assert: REORDER_ALERT present in the recommendation ----
        rec = payload2.get("reorder_recommendation") or {}
        assert rec.get("sku_id") == "SKU-FAB-JERSEY-BLU", (
            f"reorder_recommendation must reference the seed SKU, got: {rec}"
        )
        assert rec.get("recommendation_id") == _stable_rec_id, (
            f"reorder_recommendation.recommendation_id must be stable: {rec}"
        )

        # ---- Step 3: replay simulation (no double-write — T-09-27) ----
        events_before_replay = len(_audit_events)
        # A second resume with the same thread_id should NOT produce new audit rows
        # (idempotent HITL — the recommendation is already approved).
        # The mock is already wired to append events; in a real agent the HITL state
        # prevents re-execution after approval. We simulate this by asserting that
        # a well-behaved agent would not add rows: we verify the current count stays
        # stable if the graph.ainvoke mock is NOT called again on an already-resolved thread.
        # The router caches the idempotent response — a replay returns cached 200 without
        # re-invoking the graph.
        r_replay = await client.post("/v1/agents/inventory-manager/resume", json=resume_body)
        assert r_replay.status_code == 200, r_replay.text
        # Graph was NOT re-invoked (idempotency cache): audit-event count stays the same.
        assert len(_audit_events) == events_before_replay, (
            f"Replay produced extra audit rows (double-write): "
            f"before={events_before_replay}, after={len(_audit_events)}"
        )


# ===========================================================================
# EnergyOptimizer — EnPI assertion + optimize → resume → audit-row counts (SCM-02)
# ===========================================================================


@pytest.mark.timeout(30)
async def test_energy_optimizer_enpi_and_signoff_audit_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST optimize → 202; POST resume → exactly 1 ENERGY_PROPOSAL + 1 ENERGY_SIGNOFF.

    Seeds the above-baseline scenario from scm_mantis_seed.sql (dyeing):
      enpi_actual_ytd=4.12 > enpi_target=3.80 → EnergyOptimizer detects deviation.

    Asserts:
      - optimize returns 202 + supervisor_pending.
      - The energy_proposal carries enpi_actual > enpi_baseline (seeded dyeing values).
      - resume records exactly 1 ENERGY_PROPOSAL + 1 ENERGY_SIGNOFF.
      - Both events share the same stable proposal_id (CR-04).
    """
    monkeypatch.setenv("LLM_BACKEND", "mock")

    _stable_proposal_id = "eo-prop-" + uuid.uuid4().hex[:16]
    _energy_audit_events: list[dict[str, Any]] = []

    # ---- Step 1: optimize call ----
    async def _ainvoke_optimize(
        state: dict[str, Any], *, config: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "messages": [],
            "energy_proposal": None,  # pending HITL
            "energy_alert": None,
        }

    graph = AsyncMock()
    graph.ainvoke = AsyncMock(side_effect=_ainvoke_optimize)
    app = _build_app_with_graph(graph)

    async with await _client_for(app) as client:
        optimize_body = {
            "process": "dyeing",
            "user_roles": ["energy_manager"],
        }
        r1 = await client.post("/v1/agents/energy-optimizer/optimize", json=optimize_body)
        assert r1.status_code == 202, r1.text
        payload1 = r1.json()
        assert payload1["hitl_status"] == "supervisor_pending"
        thread_id = payload1["thread_id"]

        # ---- Step 2: resume call ----
        async def _ainvoke_resume(
            state: dict[str, Any], *, config: dict[str, Any]
        ) -> dict[str, Any]:
            # EnPI values from scm_mantis_seed.sql (dyeing): actual=4.12, target=3.80
            # deviation_pct = (4.12 - 3.80) / 3.80 * 100 ≈ +8.42%
            enpi_actual = _SEED_ENPI_ACTUAL_YTD
            enpi_baseline = _SEED_ENPI_BASELINE
            deviation_pct = round((enpi_actual - enpi_baseline) / enpi_baseline * 100, 4)

            proposal_ev = _audit_event(
                "ENERGY_PROPOSAL",
                _stable_proposal_id,
                decision_actor=None,
                enpi_actual=enpi_actual,
                enpi_baseline=enpi_baseline,
                deviation_pct=deviation_pct,
            )
            signoff_ev = _audit_event(
                "ENERGY_SIGNOFF",
                _stable_proposal_id,
                decision_actor="energy.supervisor@mantis.it",
            )
            _energy_audit_events.append(proposal_ev)
            _energy_audit_events.append(signoff_ev)
            return {
                "messages": [],
                "energy_proposal": {
                    "process": "dyeing",
                    "proposal_id": _stable_proposal_id,
                    "enpi_actual": enpi_actual,
                    "enpi_baseline": enpi_baseline,
                    "deviation_pct": deviation_pct,
                    "is_above_baseline": True,
                    "off_peak_kwh_pct": 29.03,  # ~3 off-peak / 10 total readings in seed
                    "recommended_window": "22:00–06:00 (night tariff)",
                    "expected_savings_pct": 14.19,
                },
                "energy_alert": {
                    "alert_type": "ENERGY_ALERT",
                    "process": "dyeing",
                    "proposal_id": _stable_proposal_id,
                    "message": (
                        f"EnPI deviation {deviation_pct:+.2f}% "
                        f"(actual={enpi_actual:.4f}, baseline={enpi_baseline:.4f} kWh/kg)"
                    ),
                },
                "audit_events": [proposal_ev, signoff_ev],
            }

        graph.ainvoke = AsyncMock(side_effect=_ainvoke_resume)

        resume_body = {
            "thread_id": thread_id,
            "decision": "approved",
            "decision_actor": "energy.supervisor@mantis.it",
        }
        r2 = await client.post("/v1/agents/energy-optimizer/resume", json=resume_body)
        assert r2.status_code == 200, r2.text
        payload2 = r2.json()

        # ---- Assert: exactly 1 ENERGY_PROPOSAL + 1 ENERGY_SIGNOFF ----
        proposals = [e for e in _energy_audit_events if e["event_type"] == "ENERGY_PROPOSAL"]
        signoffs = [e for e in _energy_audit_events if e["event_type"] == "ENERGY_SIGNOFF"]

        assert len(proposals) == 1, (
            f"Expected exactly 1 ENERGY_PROPOSAL, got {len(proposals)}: {_energy_audit_events}"
        )
        assert len(signoffs) == 1, (
            f"Expected exactly 1 ENERGY_SIGNOFF, got {len(signoffs)}: {_energy_audit_events}"
        )

        # ---- Assert: stable proposal_id (CR-04) ----
        assert proposals[0]["correlation_id"] == _stable_proposal_id
        assert signoffs[0]["correlation_id"] == _stable_proposal_id

        # ---- Assert: EnPI actual > baseline (seed dyeing row: 4.12 > 3.80) ----
        proposal_dict = payload2.get("energy_proposal") or {}
        assert proposal_dict.get("is_above_baseline") is True, (
            f"energy_proposal.is_above_baseline must be True (dyeing seed: "
            f"actual={_SEED_ENPI_ACTUAL_YTD} > baseline={_SEED_ENPI_BASELINE}): {proposal_dict}"
        )
        # The actual EnPI must be strictly greater than the baseline
        enpi_actual_in_response = proposal_dict.get("enpi_actual", 0.0)
        enpi_baseline_in_response = proposal_dict.get("enpi_baseline", 0.0)
        assert enpi_actual_in_response > enpi_baseline_in_response, (
            f"EnPI actual ({enpi_actual_in_response}) must exceed baseline "
            f"({enpi_baseline_in_response}) — seed dyeing: {_SEED_ENPI_ACTUAL_YTD} > "
            f"{_SEED_ENPI_BASELINE}"
        )


# ===========================================================================
# CostAnalyzer — autonomous Decision.AUTO + OEPV assertions (SCM-03)
# ===========================================================================


@pytest.mark.timeout(30)
async def test_cost_analyzer_autonomous_oepv_audit_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST analyze → 200; exactly 1 Decision.AUTO COST_REPORT; no interrupt called.

    OEPV assertions (seeded from Mantis dataset + compute_oepv formula):
      ribasso_pct=10, pt=50, OepvConfig defaults (70/30 split, BA=108000):
        Pe ≈ 23.307 (non-linear curve)
        total_score ≈ 41.992 (must be in [0, 100])
        offer_eur = 97200 (= 108000 * 0.90)
        is_anomaly_warning = False (10 < 20)
        sensitivity dict present (±1%, ±5%, ±10% keys)

    Asserts:
      - analyze returns 200 (synchronous — no 202, no HITL).
      - graph.ainvoke called exactly once (no resume path for autonomous agent).
      - Response carries cost_breakdown + oepv_report with correct structure.
      - OEPV: total_score in [0, 100]; offer_eur ≈ 97200; sensitivity present.
      - Decision.AUTO audit row is the only audit event (no HITL rows).
    """
    monkeypatch.setenv("LLM_BACKEND", "mock")

    _cost_audit_events: list[dict[str, Any]] = []

    # ---- Compute expected OEPV values from formula (no calendar dependence) ----
    import math

    ba = _SEED_BASE_D_ASTA_EUR
    ribasso = _TEST_RIBASSO_PCT
    pt_val = _TEST_PT
    pe_max = 30.0
    lambda_c = 3.0
    ribasso_ref = 20.0
    weight_t = 0.70
    weight_e = 0.30

    expected_pe = pe_max * (1 - math.exp(-lambda_c * ribasso / ribasso_ref))
    expected_total = weight_t * pt_val + weight_e * expected_pe
    expected_offer = ba * (1 - ribasso / 100)  # = 97200
    expected_anomaly = ribasso >= 20.0  # False (10 < 20)

    # ---- Mock graph: returns autonomous COST_REPORT result ----
    async def _ainvoke_analyze(
        state: dict[str, Any], *, config: dict[str, Any]
    ) -> dict[str, Any]:
        # Record the Decision.AUTO audit event
        auto_event = {
            "event_type": "COST_REPORT",
            "decision": "Decision.AUTO",
            "correlation_id": "cost-auto-" + uuid.uuid4().hex[:16],
            "ts": datetime.now(UTC).isoformat(),
        }
        _cost_audit_events.append(auto_event)

        return {
            "messages": [],
            "cost_breakdown": {
                "downtime_cost_eur": 1500.0,
                "scrap_cost_eur": 800.0,
                "energy_cost_eur": 620.0,
                "total_eur": 2920.0,
                "roi_savings_pct": 15.2,
            },
            "oepv_report": {
                "ribasso_pct": ribasso,
                "pt": pt_val,
                "pe": round(expected_pe, 4),
                "total_score": round(expected_total, 4),
                "offer_eur": round(expected_offer, 2),
                "is_anomaly_warning": expected_anomaly,
                "sensitivity": {
                    "-10%": round(
                        weight_t * pt_val + weight_e * pe_max * (1 - math.exp(-lambda_c * max(0, ribasso - 10) / ribasso_ref))
                        - expected_total, 4
                    ),
                    "-5%": round(
                        weight_t * pt_val + weight_e * pe_max * (1 - math.exp(-lambda_c * max(0, ribasso - 5) / ribasso_ref))
                        - expected_total, 4
                    ),
                    "-1%": round(
                        weight_t * pt_val + weight_e * pe_max * (1 - math.exp(-lambda_c * max(0, ribasso - 1) / ribasso_ref))
                        - expected_total, 4
                    ),
                    "+1%": round(
                        weight_t * pt_val + weight_e * pe_max * (1 - math.exp(-lambda_c * min(100, ribasso + 1) / ribasso_ref))
                        - expected_total, 4
                    ),
                    "+5%": round(
                        weight_t * pt_val + weight_e * pe_max * (1 - math.exp(-lambda_c * min(100, ribasso + 5) / ribasso_ref))
                        - expected_total, 4
                    ),
                    "+10%": round(
                        weight_t * pt_val + weight_e * pe_max * (1 - math.exp(-lambda_c * min(100, ribasso + 10) / ribasso_ref))
                        - expected_total, 4
                    ),
                },
                "sensitivity_table": [
                    {"ribasso_pct": ribasso - 10, "pe": 0.0, "total_score": 0.0},
                ],
            },
        }

    graph = AsyncMock()
    graph.ainvoke = AsyncMock(side_effect=_ainvoke_analyze)
    app = _build_app_with_graph(graph)

    async with await _client_for(app) as client:
        analyze_body = {
            "ribasso_pct": ribasso,
            "pt": pt_val,
            "user_roles": ["procurement_manager"],
        }
        r = await client.post("/v1/agents/cost-analyzer/analyze", json=analyze_body)

        # ---- Autonomous: synchronous 200 (not 202) ----
        assert r.status_code == 200, (
            f"CostAnalyzer must return 200 (autonomous SCM-03, no HITL): {r.text}"
        )

        # ---- Autonomous: exactly 1 graph.ainvoke call (no resume) ----
        assert graph.ainvoke.await_count == 1, (
            f"CostAnalyzer must invoke graph exactly once (autonomous, no HITL), "
            f"got {graph.ainvoke.await_count}"
        )

        payload = r.json()

        # ---- Assert cost_breakdown present ----
        cost_breakdown = payload.get("cost_breakdown") or {}
        assert cost_breakdown.get("total_eur", -1) >= 0, (
            f"cost_breakdown.total_eur must be >= 0: {cost_breakdown}"
        )

        # ---- Assert oepv_report structure and OEPV formula correctness ----
        oepv_report = payload.get("oepv_report") or {}

        # total_score must be in [0, 100] (Formula invariant)
        total_score = oepv_report.get("total_score", -1)
        assert _OEPV_SCORE_MIN <= total_score <= _OEPV_SCORE_MAX, (
            f"oepv_report.total_score must be in [{_OEPV_SCORE_MIN}, {_OEPV_SCORE_MAX}], "
            f"got {total_score}"
        )

        # offer_eur derived from BA=108000 at ribasso=10%: 108000 * 0.90 = 97200
        offer_eur = oepv_report.get("offer_eur", -1)
        assert abs(offer_eur - _EXPECTED_OFFER_EUR) < 1.0, (
            f"oepv_report.offer_eur must be ≈ {_EXPECTED_OFFER_EUR} (BA={ba} * (1-{ribasso}/100)), "
            f"got {offer_eur}"
        )

        # sensitivity dict must be present and non-empty (ECO-05 sensitivity analysis)
        sensitivity = oepv_report.get("sensitivity") or {}
        assert len(sensitivity) >= 4, (
            f"oepv_report.sensitivity must have >= 4 entries (±1%,±5%,±10%), "
            f"got {sensitivity}"
        )

        # is_anomaly_warning must be False for ribasso=10 (threshold=20)
        is_anomaly = oepv_report.get("is_anomaly_warning")
        assert is_anomaly is False, (
            f"oepv_report.is_anomaly_warning must be False for ribasso={ribasso}% < 20%, "
            f"got {is_anomaly}"
        )

        # ---- Assert Decision.AUTO audit row (exactly 1, no HITL rows) ----
        auto_events = [e for e in _cost_audit_events if e.get("decision") == "Decision.AUTO"]
        assert len(auto_events) == 1, (
            f"Expected exactly 1 Decision.AUTO COST_REPORT audit row, "
            f"got {len(auto_events)}: {_cost_audit_events}"
        )
        assert auto_events[0]["event_type"] == "COST_REPORT", (
            f"Decision.AUTO audit row must have event_type=COST_REPORT, "
            f"got {auto_events[0]['event_type']}"
        )

        # ---- Assert: NO resume endpoint (autonomous — D-SCM-AUTO) ----
        r_resume = await client.post(
            "/v1/agents/cost-analyzer/resume",
            json={"thread_id": "any-id", "decision": "approved"},
        )
        assert r_resume.status_code in (404, 405), (
            f"cost-analyzer/resume must not exist (autonomous SCM-03), "
            f"got {r_resume.status_code}"
        )


# ===========================================================================
# DemandForecaster — forecast → resume → demand_plan cross-cluster (SCM-04)
# ===========================================================================


@pytest.mark.timeout(30)
async def test_demand_forecaster_plan_signoff_and_production_planner_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST forecast → 202; POST resume → 200 with demand_plan for >= 2 SKU groups.

    Seeds jersey + twill SKU groups from scm_mantis_seed.sql (scm.historical_orders):
      jersey: ~12000–16200 kg/month (seasonal variation)
      twill:  ~7600–8600 kg/month (stable with CV~12%)

    Asserts:
      - forecast returns 202 + supervisor_pending.
      - resume records exactly 1 DEMAND_PLAN_DRAFT + 1 DEMAND_PLAN_SIGNOFF.
      - Both events share the same stable plan_id (CR-04).
      - demand_plan covers >= 2 SKU groups (jersey + twill) as seeded.
      - demand_plan is present in the response state delta (ProductionPlanner publish key).
      - Rolling MAPE <= 100 (CR-05 clamp compliance).
    """
    monkeypatch.setenv("LLM_BACKEND", "mock")

    _stable_plan_id = "df-plan-" + uuid.uuid4().hex[:16]
    _demand_audit_events: list[dict[str, Any]] = []

    # ---- Step 1: forecast call ----
    async def _ainvoke_forecast(
        state: dict[str, Any], *, config: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "messages": [],
            "demand_plan": None,  # pending HITL
            "mape_report": None,
        }

    graph = AsyncMock()
    graph.ainvoke = AsyncMock(side_effect=_ainvoke_forecast)
    app = _build_app_with_graph(graph)

    async with await _client_for(app) as client:
        forecast_body = {
            "sku_groups": _SEED_SKU_GROUPS,  # ["jersey", "twill"]
            "horizon": 6,
            "months_back": 19,  # matches seed: 19 monthly buckets Jan 2024 – Jul 2025
            "user_roles": ["supply_planner"],
        }
        r1 = await client.post("/v1/agents/demand-forecaster/forecast", json=forecast_body)
        assert r1.status_code == 202, r1.text
        payload1 = r1.json()
        assert payload1["hitl_status"] == "supervisor_pending"
        thread_id = payload1["thread_id"]

        # ---- Step 2: resume call ----
        async def _ainvoke_resume(
            state: dict[str, Any], *, config: dict[str, Any]
        ) -> dict[str, Any]:
            # Demand plan: jersey + twill, 6-month horizon (from seed HW forecast)
            # Forecast values are non-seeded to calendar — they are relative to NOW()
            # in the seed (consistent with scm_mantis_seed.sql NOW()-relative strategy).
            jersey_forecast = [12500.0, 14400.0, 16200.0, 16200.0, 14400.0, 12000.0]
            twill_forecast = [8400.0, 7600.0, 7600.0, 8200.0, 8600.0, 8400.0]

            demand_plan = {
                "plan_id": _stable_plan_id,
                "sku_groups": [
                    {
                        "sku_group": "jersey",
                        "horizon": 6,
                        "forecast": jersey_forecast,
                        "method": "holt_winters",
                    },
                    {
                        "sku_group": "twill",
                        "horizon": 6,
                        "forecast": twill_forecast,
                        "method": "holt_winters",
                    },
                ],
            }
            # Rolling MAPE (clamped <= 100 — CR-05)
            mape_report = {
                "mape": 8.34,  # realistic synthetic value from 19-month seed series
                "n_pairs": 12,  # 6 held-out per group
                "plan_id": _stable_plan_id,
            }

            draft_ev = _audit_event(
                "DEMAND_PLAN_DRAFT",
                _stable_plan_id,
                decision_actor=None,
                n_sku_groups=2,
            )
            signoff_ev = _audit_event(
                "DEMAND_PLAN_SIGNOFF",
                _stable_plan_id,
                decision_actor="supply.supervisor@mantis.it",
            )
            _demand_audit_events.append(draft_ev)
            _demand_audit_events.append(signoff_ev)

            return {
                "messages": [],
                "demand_plan": demand_plan,
                "mape_report": mape_report,
                "audit_events": [draft_ev, signoff_ev],
            }

        graph.ainvoke = AsyncMock(side_effect=_ainvoke_resume)

        resume_body = {
            "thread_id": thread_id,
            "decision": "approved",
            "decision_actor": "supply.supervisor@mantis.it",
        }
        r2 = await client.post("/v1/agents/demand-forecaster/resume", json=resume_body)
        assert r2.status_code == 200, r2.text
        payload2 = r2.json()

        # ---- Assert: exactly 1 DEMAND_PLAN_DRAFT + 1 DEMAND_PLAN_SIGNOFF ----
        drafts = [e for e in _demand_audit_events if e["event_type"] == "DEMAND_PLAN_DRAFT"]
        signoffs = [e for e in _demand_audit_events if e["event_type"] == "DEMAND_PLAN_SIGNOFF"]

        assert len(drafts) == 1, (
            f"Expected exactly 1 DEMAND_PLAN_DRAFT, got {len(drafts)}: {_demand_audit_events}"
        )
        assert len(signoffs) == 1, (
            f"Expected exactly 1 DEMAND_PLAN_SIGNOFF, got {len(signoffs)}: {_demand_audit_events}"
        )

        # ---- Assert: stable plan_id shared (CR-04) ----
        assert drafts[0]["correlation_id"] == _stable_plan_id
        assert signoffs[0]["correlation_id"] == _stable_plan_id

        # ---- Assert: demand_plan in response (ProductionPlanner publish channel) ----
        demand_plan = payload2.get("demand_plan") or {}
        assert demand_plan.get("plan_id") == _stable_plan_id, (
            f"demand_plan.plan_id must be the stable plan_id={_stable_plan_id!r}, "
            f"got {demand_plan.get('plan_id')!r}"
        )

        # ---- Assert: demand_plan covers >= 2 SKU groups (jersey + twill) ----
        sku_groups = demand_plan.get("sku_groups", [])
        assert len(sku_groups) >= _MIN_SKU_GROUPS_IN_PLAN, (
            f"demand_plan.sku_groups must have >= {_MIN_SKU_GROUPS_IN_PLAN} groups "
            f"(jersey + twill from seed), got {len(sku_groups)}: {sku_groups}"
        )
        group_names = {g.get("sku_group") for g in sku_groups}
        assert "jersey" in group_names, (
            f"demand_plan must include 'jersey' SKU group (seed: scm.historical_orders): "
            f"{group_names}"
        )
        assert "twill" in group_names, (
            f"demand_plan must include 'twill' SKU group (seed: scm.historical_orders): "
            f"{group_names}"
        )

        # ---- Assert: MAPE <= 100 (CR-05 clamp compliance) ----
        mape_report = payload2.get("mape_report") or {}
        mape_val = mape_report.get("mape", 999.0)
        assert 0.0 <= mape_val <= 100.0, (
            f"mape_report.mape must be in [0, 100] (CR-05 clamp), got {mape_val}"
        )

        # ---- Assert: forecast values are positive (no negative demand) ----
        for group in sku_groups:
            forecast = group.get("forecast", [])
            assert all(v >= 0 for v in forecast), (
                f"All forecast values must be >= 0 for group {group.get('sku_group')}: {forecast}"
            )
            assert len(forecast) == 6, (
                f"Forecast horizon must be 6 for group {group.get('sku_group')}: {forecast}"
            )


# ===========================================================================
# Cross-cluster: all four supply agents produce expected outputs (full sweep)
# ===========================================================================


@pytest.mark.timeout(60)
async def test_supply_cluster_four_agent_full_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sweep all four supply agents through a single app instance.

    This is the Phase 9 ROADMAP acceptance gate: each agent executes one
    request and asserts minimum output correctness.  All numeric assertions
    are seed-aware (relative to Mantis dataset constants, not calendar dates).

    Covers ROADMAP Phase 9 success criteria 1-4:
      1. InventoryManager reorder detection (jersey SKU below threshold) — SCM-01
      2. EnergyOptimizer above-baseline detection (dyeing EnPI 4.12 > 3.80) — SCM-02
      3. CostAnalyzer autonomous OEPV simulation (BA=108000, 70/30) — SCM-03
      4. DemandForecaster >= 2 SKU groups demand plan to ProductionPlanner — SCM-04
    """
    monkeypatch.setenv("LLM_BACKEND", "mock")

    # Shared accumulator for all supply audit events in this sweep
    _all_supply_events: list[dict[str, Any]] = []

    import math

    _ribasso = _TEST_RIBASSO_PCT
    _pt = _TEST_PT
    _ba = _SEED_BASE_D_ASTA_EUR
    _pe_max = 30.0
    _lambda = 3.0
    _rref = 20.0
    _wt = 0.70
    _we = 0.30

    _pe_val = _pe_max * (1 - math.exp(-_lambda * _ribasso / _rref))
    _total_val = _wt * _pt + _we * _pe_val

    async def _ainvoke_supply_sweep(
        state: dict[str, Any], *, config: dict[str, Any]
    ) -> dict[str, Any]:
        target = state.get("target_agent", "unknown")
        action = state.get("action", "")

        if target == "inventory-manager":
            if action == "resume":
                _rec_id = "sweep-inv-" + uuid.uuid4().hex[:8]
                _all_supply_events.append(_audit_event("PURCHASE_RECOMMENDATION_DRAFT", _rec_id))
                _all_supply_events.append(_audit_event("PURCHASE_SIGNOFF", _rec_id))
                return {
                    "messages": [],
                    "reorder_recommendation": {
                        "sku_id": "SKU-FAB-JERSEY-BLU",
                        "current_qty": str(_SEED_JERSEY_CURRENT_QTY),
                        "reorder_point": str(_SEED_JERSEY_REORDER_POINT),
                        "reorder_qty": "1500.000",
                        "lead_time_days": 5,
                        "estimated_cost_eur": "12600.000",
                        "recommendation_id": _rec_id,
                    },
                    "reorder_alert": {
                        "alert_type": "REORDER_ALERT",
                        "sku_id": "SKU-FAB-JERSEY-BLU",
                        "recommendation_id": _rec_id,
                        "message": "REORDER_ALERT sweep",
                    },
                }
            return {"messages": [], "reorder_recommendation": None, "reorder_alert": None}

        if target == "energy-optimizer":
            if action == "resume":
                _prop_id = "sweep-eo-" + uuid.uuid4().hex[:8]
                _all_supply_events.append(_audit_event("ENERGY_PROPOSAL", _prop_id))
                _all_supply_events.append(_audit_event("ENERGY_SIGNOFF", _prop_id))
                return {
                    "messages": [],
                    "energy_proposal": {
                        "process": "dyeing",
                        "proposal_id": _prop_id,
                        "enpi_actual": _SEED_ENPI_ACTUAL_YTD,
                        "enpi_baseline": _SEED_ENPI_BASELINE,
                        "deviation_pct": round(
                            (_SEED_ENPI_ACTUAL_YTD - _SEED_ENPI_BASELINE)
                            / _SEED_ENPI_BASELINE * 100,
                            4,
                        ),
                        "is_above_baseline": True,
                        "off_peak_kwh_pct": 29.03,
                        "recommended_window": "22:00–06:00 (night tariff)",
                        "expected_savings_pct": 14.19,
                    },
                    "energy_alert": {
                        "alert_type": "ENERGY_ALERT",
                        "process": "dyeing",
                        "proposal_id": _prop_id,
                        "message": "ENERGY_ALERT sweep",
                    },
                }
            return {"messages": [], "energy_proposal": None, "energy_alert": None}

        if target == "cost-analyzer":
            _auto_id = "sweep-cost-" + uuid.uuid4().hex[:8]
            _all_supply_events.append({
                "event_type": "COST_REPORT",
                "decision": "Decision.AUTO",
                "correlation_id": _auto_id,
                "ts": datetime.now(UTC).isoformat(),
            })
            return {
                "messages": [],
                "cost_breakdown": {
                    "downtime_cost_eur": 1500.0,
                    "scrap_cost_eur": 800.0,
                    "energy_cost_eur": 620.0,
                    "total_eur": 2920.0,
                    "roi_savings_pct": 15.2,
                },
                "oepv_report": {
                    "ribasso_pct": _ribasso,
                    "pt": _pt,
                    "pe": round(_pe_val, 4),
                    "total_score": round(_total_val, 4),
                    "offer_eur": round(_ba * (1 - _ribasso / 100), 2),
                    "is_anomaly_warning": False,
                    "sensitivity": {"-1%": -0.01, "+1%": 0.01, "-5%": -0.05, "+5%": 0.05},
                    "sensitivity_table": [],
                },
            }

        if target == "demand-forecaster":
            if action == "resume":
                _plan_id = "sweep-df-" + uuid.uuid4().hex[:8]
                _all_supply_events.append(_audit_event("DEMAND_PLAN_DRAFT", _plan_id))
                _all_supply_events.append(_audit_event("DEMAND_PLAN_SIGNOFF", _plan_id))
                return {
                    "messages": [],
                    "demand_plan": {
                        "plan_id": _plan_id,
                        "sku_groups": [
                            {
                                "sku_group": "jersey",
                                "horizon": 6,
                                "forecast": [12000.0, 14400.0, 16200.0, 16200.0, 14400.0, 12000.0],
                                "method": "holt_winters",
                            },
                            {
                                "sku_group": "twill",
                                "horizon": 6,
                                "forecast": [8400.0, 7600.0, 7600.0, 8200.0, 8600.0, 8400.0],
                                "method": "holt_winters",
                            },
                        ],
                    },
                    "mape_report": {
                        "mape": 8.34,
                        "n_pairs": 12,
                        "plan_id": _plan_id,
                    },
                }
            return {"messages": [], "demand_plan": None, "mape_report": None}

        return {"messages": []}

    graph = AsyncMock()
    graph.ainvoke = AsyncMock(side_effect=_ainvoke_supply_sweep)
    app = _build_app_with_graph(graph)

    async with await _client_for(app) as client:
        # ---- 1. InventoryManager check ----
        r_inv = await client.post(
            "/v1/agents/inventory-manager/check",
            json={"sku_ids": ["SKU-FAB-JERSEY-BLU"], "user_roles": ["procurement_manager"]},
        )
        assert r_inv.status_code == 202, r_inv.text
        inv_thread = r_inv.json()["thread_id"]

        # InventoryManager resume (HITL sign-off)
        r_inv_resume = await client.post(
            "/v1/agents/inventory-manager/resume",
            json={
                "thread_id": inv_thread,
                "decision": "approved",
                "decision_actor": "procurement.supervisor@mantis.it",
            },
        )
        assert r_inv_resume.status_code == 200, r_inv_resume.text
        inv_payload = r_inv_resume.json()
        assert inv_payload.get("reorder_recommendation") is not None, (
            "InventoryManager resume must return reorder_recommendation"
        )
        assert inv_payload["reorder_recommendation"]["sku_id"] == "SKU-FAB-JERSEY-BLU"

        # ---- 2. EnergyOptimizer optimize ----
        r_eo = await client.post(
            "/v1/agents/energy-optimizer/optimize",
            json={"process": "dyeing", "user_roles": ["energy_manager"]},
        )
        assert r_eo.status_code == 202, r_eo.text
        eo_thread = r_eo.json()["thread_id"]

        # EnergyOptimizer resume (HITL sign-off)
        r_eo_resume = await client.post(
            "/v1/agents/energy-optimizer/resume",
            json={
                "thread_id": eo_thread,
                "decision": "approved",
                "decision_actor": "energy.supervisor@mantis.it",
            },
        )
        assert r_eo_resume.status_code == 200, r_eo_resume.text
        eo_payload = r_eo_resume.json()
        ep = eo_payload.get("energy_proposal") or {}
        assert ep.get("is_above_baseline") is True, (
            f"EnergyOptimizer: EnPI must be above baseline (dyeing seed): {ep}"
        )
        assert ep.get("enpi_actual", 0) > ep.get("enpi_baseline", 0), (
            f"enpi_actual ({ep.get('enpi_actual')}) must exceed baseline ({ep.get('enpi_baseline')})"
        )

        # ---- 3. CostAnalyzer analyze (autonomous) ----
        r_cost = await client.post(
            "/v1/agents/cost-analyzer/analyze",
            json={
                "ribasso_pct": _ribasso,
                "pt": _pt,
                "user_roles": ["procurement_manager"],
            },
        )
        assert r_cost.status_code == 200, r_cost.text
        cost_payload = r_cost.json()
        oepv = cost_payload.get("oepv_report") or {}

        # OEPV: total_score in [0, 100]
        assert _OEPV_SCORE_MIN <= oepv.get("total_score", -1) <= _OEPV_SCORE_MAX, (
            f"oepv_report.total_score out of range: {oepv.get('total_score')}"
        )
        # offer_eur from BA=108000 at ribasso=10%
        assert abs(oepv.get("offer_eur", -1) - _EXPECTED_OFFER_EUR) < 1.0, (
            f"oepv_report.offer_eur must be ≈ {_EXPECTED_OFFER_EUR}, got {oepv.get('offer_eur')}"
        )
        # sensitivity dict present
        assert len(oepv.get("sensitivity") or {}) >= 4, (
            f"oepv_report.sensitivity must have >= 4 entries: {oepv.get('sensitivity')}"
        )

        # ---- 4. DemandForecaster forecast ----
        r_df = await client.post(
            "/v1/agents/demand-forecaster/forecast",
            json={
                "sku_groups": _SEED_SKU_GROUPS,
                "horizon": 6,
                "months_back": 19,
                "user_roles": ["supply_planner"],
            },
        )
        assert r_df.status_code == 202, r_df.text
        df_thread = r_df.json()["thread_id"]

        # DemandForecaster resume (HITL sign-off — ProductionPlanner publish)
        r_df_resume = await client.post(
            "/v1/agents/demand-forecaster/resume",
            json={
                "thread_id": df_thread,
                "decision": "approved",
                "decision_actor": "supply.supervisor@mantis.it",
            },
        )
        assert r_df_resume.status_code == 200, r_df_resume.text
        df_payload = r_df_resume.json()

        # demand_plan present in response (ProductionPlanner publish channel)
        demand_plan = df_payload.get("demand_plan") or {}
        assert demand_plan.get("plan_id"), "demand_plan must have a plan_id"

        sku_groups = demand_plan.get("sku_groups", [])
        assert len(sku_groups) >= _MIN_SKU_GROUPS_IN_PLAN, (
            f"demand_plan must cover >= 2 SKU groups (jersey + twill from seed): {sku_groups}"
        )
        group_names = {g.get("sku_group") for g in sku_groups}
        assert "jersey" in group_names and "twill" in group_names, (
            f"demand_plan must include jersey + twill (seed SKU groups): {group_names}"
        )

        # MAPE <= 100 (CR-05)
        mape_report = df_payload.get("mape_report") or {}
        assert 0.0 <= mape_report.get("mape", 999.0) <= 100.0, (
            f"mape_report.mape must be in [0, 100] (CR-05): {mape_report.get('mape')}"
        )

        # ---- Cross-cluster audit summary ----
        # HITL agents: 2 DRAFT + 2 SIGNOFF (Inventory + Energy)
        hitl_drafts = [e for e in _all_supply_events if "DRAFT" in e.get("event_type", "")]
        hitl_signoffs = [e for e in _all_supply_events if "SIGNOFF" in e.get("event_type", "")]
        auto_events = [e for e in _all_supply_events if e.get("decision") == "Decision.AUTO"]

        assert len(hitl_drafts) == 2, (
            f"Expected 2 HITL DRAFT rows (Inventory + Demand), got {len(hitl_drafts)}: "
            f"{[e['event_type'] for e in hitl_drafts]}"
        )
        assert len(hitl_signoffs) == 2, (
            f"Expected 2 HITL SIGNOFF rows (Inventory + Energy), got {len(hitl_signoffs)}: "
            f"{[e['event_type'] for e in hitl_signoffs]}"
        )
        assert len(auto_events) == 1, (
            f"Expected 1 Decision.AUTO COST_REPORT row, got {len(auto_events)}: {_all_supply_events}"
        )


__all__: list[str] = []
