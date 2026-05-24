# Phase 9: Agents — Supply Chain & Economics - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning
**Mode:** Interactive discuss (4 gray areas resolved with user)

<domain>
## Phase Boundary

Implement the four Supply Chain & Economics cluster LangGraph agents with realistic synthetic Mantis Textile Group data:

- **InventoryManager (SCM-01)** — monitors stock (raw yarn, accessories, spare parts), fires a reorder alert when a SKU drops below its reorder point, generates a purchase-recommendation draft, routes it to procurement-supervisor HITL before any order action.
- **EnergyOptimizer (SCM-02)** — computes energy-per-unit (kWh/kg) for dyeing and finishing against an ISO 50001 EnPI baseline, recommends off-peak scheduling via HITL-gated proposal.
- **CostAnalyzer (SCM-03)** — aggregates downtime cost + scrap cost + energy cost into an ROI dashboard and produces a **parametric** OEPV ribasso simulation with sensitivity analysis (autonomous / read-only).
- **DemandForecaster (SCM-04)** — produces a demand plan for ≥2 fabric SKU groups via deterministic forecast, publishes it to ProductionPlanner (apps/agents/ops/production-planner) through HITL-gated approval, tracks a forecast-accuracy KPI.

Plus: realistic numerical Mantis examples documented explicitly as synthetic in `docs/`.

**Out of scope (deferred):** definitive procurement-law precision of the OEPV model (exact Codice Appalti anomaly thresholds, official ECO/DEL deliverable) → Phase 12.
</domain>

<decisions>
## Implementation Decisions

### Data sources (gray area 1) — LOCKED
New synthetic `scm.*` schema in TimescaleDB, NOT derived from existing tables.
- New tables (planner to finalize exact DDL): `scm.inventory_levels`, `scm.energy_readings`, `scm.historical_orders` (+ any reorder-point / SKU master needed).
- Seeded from a documented synthetic Mantis dataset (seed migration + fixture).
- Queried via the established asyncpg pattern (datetime objects, never `.isoformat()`).
- **Why:** inventory / energy / historical-order data genuinely do not exist in audit.actions / downtime_events / sensor_events; a queryable, time-series source is required for reorder logic, rolling KPIs, and EnPI baselines. (Contrast with Phase 8 D-SH-02 which could derive from existing tables.)

### OEPV / ribasso boundary F9 ↔ F12 (gray area 2) — LOCKED
Phase 9 builds a **functional parametric simulator**; Phase 12 does the legal refinement.
- F9 CostAnalyzer: working OEPV simulation — 70 technical / 30 economic scoring + non-linear ribasso curve (ECO-02) + sensitivity analysis (ECO-05), with the formula **parameterized / configurable** (coefficients, BA, thresholds as inputs).
- F9 anomaly-threshold (ribasso anomalo) handling: present as a configurable warning, NOT the definitive Codice Appalti rule.
- Deferred to F12: exact Codice Appalti 2023 anomaly thresholds, official OEPV/BA/Ri deliverable (ECO/DEL-06), procurement-law-informed review.
- **Why:** unblocks the ROI dashboard + ribasso simulation now without stalling on the procurement-law review flagged in STATE blockers.

### DemandForecaster method (gray area 3) — LOCKED
Deterministic statistical forecast — Holt-Winters (with seasonal-naive fallback for short series), LLM-free.
- Input: `scm.historical_orders`; output: demand plan for ≥2 fabric SKU groups.
- "Configurable external signals" (SCM-04): seasonal/promotional adjustment factors injected via config (no live external API).
- Accuracy KPI: rolling MAPE tracked over time.
- HITL: demand plan published to ProductionPlanner via HITL-gated approval.
- **Why:** consistent with prior phases' preference for deterministic, reproducible, testable computation over LLM for numeric KPIs.

### Mantis Textile example data (gray area 4) — LOCKED
Claude generates realistic synthetic values; documented explicitly as synthetic in `docs/`.
- Product lines, plant capacity, unit costs, ISO 50001 EnPI baseline (kWh/kg per process), BA €108.000 anchor.
- Plausible for an Italian textile SME; clearly labeled synthetic (no real company data).

### Carried forward from Phases 6/7/8 (NOT re-discussed)
- Cluster subgraph pattern: add `build_supply_subgraph` to `packages/sft-agents/src/sft_agents/runtime/clusters.py`, mirroring `build_maintenance_subgraph` / `build_knowledge_subgraph`. CostAnalyzer (autonomous) is the safe fallback default.
- HITL ordering: interrupt-then-audit, no audit writes before resume, no double-write on replay, `approval_id=None` for pending HITL rows, stable IDs across replay (derive from state/thread_id, never inline uuid4 — Phase 8 CR-04 lesson).
- Audit: extend `ActionType` enum (enums.py:67) + a new TimescaleDB CHECK-constraint migration in lockstep (Phase 8 08-00a pattern) for new action types (e.g. REORDER_ALERT, PURCHASE_RECOMMENDATION_DRAFT, PURCHASE_SIGNOFF, ENERGY_PROPOSAL, ENERGY_SIGNOFF, DEMAND_PLAN_DRAFT, DEMAND_PLAN_SIGNOFF). Planner to finalize names.
- Frozen Pydantic models; deterministic LLM-free core logic; provenance/source on outputs (TRN-05 style where applicable).
- API gateway router pattern (mirror `routers/knowledge_agents.py`): request models frozen + extra=forbid + tz-aware validators + `user_roles` ACL + generic 500 body (Phase 8 review lessons WR-02/03/05).
- Bilingual IT/EN docs under `docs/docs/...` + `docs/docs/en/...`, mkdocs nav (Phase 8 08-09 actual layout, not root mkdocs.yml).
- Nyquist: scaffold agent test contracts before implementation (Phase 8 08-00b pattern).
- Execution: worktrees DISABLED — sequential executors on main tree (this session's reliability fix).
</decisions>

<code_context>
## Existing Code Insights

- Cluster scaffolds already present: `apps/agents/supply/{inventory-manager,energy-optimizer,cost-analyzer}` (README/project.json/pyproject/__init__). **DemandForecaster scaffold missing — create `apps/agents/supply/demand-forecaster`.**
- Router/DI/lifespan to extend: `apps/api-gateway/src/svc_api_gateway/{routers/,dependencies.py,lifespan.py,main.py}` — mirror the knowledge cluster wiring from Phase 8 (08-08).
- Runtime router: `packages/sft-agents/src/sft_agents/runtime/clusters.py` (build_ops/maintenance/knowledge_subgraph).
- Audit: `packages/sft-agents/src/sft_agents/audit/writer.py` (`AuditWriter.write(record: AuditRecord)` — positional AuditRecord, NOT kwargs; Phase 8 CR-02 lesson).
- TimescaleDB migrations: `infra/migrations/timescale/` (next index after 010; idempotent CHECK-constraint extension pattern, test_migration_NNN.py).
- DemandForecaster HITL publish target: `apps/agents/ops/production-planner`.
</code_context>

<specifics>
## Specific Ideas

- OEPV anchor: Base d'Asta €108.000, 70% technical / 30% economic (from REQUIREMENTS economic model).
- Forecast: Holt-Winters; KPI = rolling MAPE.
- Energy: ISO 50001 EnPI baseline expressed as kWh/kg per dyeing & finishing process.
</specifics>

<canonical_refs>
## Canonical References (downstream agents MUST read)

- `.planning/REQUIREMENTS.md` — SCM-01..04, ECO-02, ECO-05, SEC-02 (OWASP LLM supply-chain).
- `.planning/ROADMAP.md` — Phase 9 goal + success criteria.
- `.planning/phases/08-agents-knowledge-training/08-CONTEXT.md` + `08-REVIEW.md` — agent-cluster patterns and the 5 Critical/5 Warning lessons to avoid (import names, AuditRecord signature, KeyError on state, unstable replay IDs, reuse-rate clamp, tz validators, ACL, generic error body).
- `packages/sft-agents/src/sft_agents/runtime/clusters.py` — subgraph pattern to mirror.
- `infra/migrations/timescale/010_extend_audit_knw.sql` — enum-lockstep migration template.
- No procurement-law spec exists yet — OEPV legal precision is explicitly deferred to Phase 12.
</canonical_refs>

<deferred>
## Deferred Ideas

- Definitive OEPV / ribasso procurement-law model (exact Codice Appalti 2023 anomaly thresholds, official deliverable) → Phase 12 (ECO-02/05, DEL-06).
- Live external demand signals (real APIs) → out of milestone scope; F9 uses config-driven synthetic signals.
</deferred>
