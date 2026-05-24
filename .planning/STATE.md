---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 11 Plan 01 complete (Wave 2 OTEL propagation e2e)
last_updated: "2026-05-25T00:32:00Z"
last_activity: 2026-05-25 -- Phase 11 Plan 01 executed (traceparent gateway→NATS→agent + phase11 Langfuse tag)
progress:
  total_phases: 12
  completed_phases: 10
  total_plans: 114
  completed_plans: 112
  percent: 84
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-16)

**Core value:** Ogni decisione critica dell'AI passa per un essere umano informato, ma nessun essere umano è mai solo davanti a un problema operativo.
**Current focus:** Phase 11 — observability-evaluation-security-hardening

## Current Position

Phase: 11 (observability-evaluation-security-hardening) — EXECUTING
Plan: 3 of 6
Status: Executing Phase 11 (Plans 00-01 complete)
Last activity: 2026-05-25 -- Phase 11 Plan 01 complete (OTEL e2e propagation)

Progress: [██████████] 78% (Phase 10 complete — 10 of 12 phases done)

### Phase 1 plans (waves — DAG-computed)

- **Wave 1:** `01-01-nx-workspace-PLAN.md` (5 tasks — PLAT-01/02/03)
- **Wave 2:** `01-02-compose-PLAN.md` (4 — PLAT-07/09 + OBS-01), `01-03-license-scanner-PLAN.md` (3 — PLAT-05), `01-04-pre-commit-PLAN.md` (3 — PLAT-06), `01-07-mkdocs-PLAN.md` (2 — PLAT-10 docs), `01-08-changesets-PLAN.md` (2 — PLAT-10 release)
- **Wave 3:** `01-05-ci-PLAN.md` (2 — PLAT-04 + OBS-01), `01-06-helm-PLAN.md` (3 — PLAT-08)

Next command: `/gsd-execute-phase 1`

## Performance Metrics

**Velocity:**

- Total plans completed: 64
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 04 | 8 | - | - |
| 08 | 10 | - | - |
| 05 | 13 | - | - |
| 09 | 10 | - | - |
| 10 | 13 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 11 P01  | 6min | 2 tasks | 6 files |
| Phase 11 P00  | 17min | 5 tasks | 19 files |
| Phase 10 P11  | 30min | 2 tasks | 15 files |
| Phase 10 P10  | 15min | 2 tasks | 4 files |
| Phase 10 P09  | 8min | 2 tasks | 7 files |
| Phase 10 P08  | 25min | 2 tasks | 10 files |
| Phase 10 P07  | 18min | 2 tasks | 5 files |
| Phase 10 P06  | 9min | 2 tasks | 7 files |
| Phase 10 P03  | 14min | 3 tasks | 6 files |
| Phase 10 P05  | 35min | 3 tasks | 12 files |
| Phase 10 P02  | 35min | 2 tasks | 5 files |
| Phase 10 P04  | 45min | 3 tasks | 18 files |
| Phase 10 P01  | 35min | 2 tasks | 8 files |
| Phase 10 P00b | 25min | 2 tasks | 9 files |
| Phase 10 P00a | 20min | 3 tasks | 8 files |
| Phase 06 P00 | 25min | 3 tasks | 61 files |
| Phase 07 P00 | 15min | 3 tasks | 58 files |
| Phase 08 P02 | 30 | 2 tasks | 6 files |
| Phase 08 P06 | 35 | 2 tasks | 12 files |
| Phase 08 P04 | 25min | 2 tasks | 4 files |
| Phase 08 P08 | 40min | 2 tasks | 6 files |
| Phase 08 P09 | 40min | 2 tasks | 4 files |
| Phase 05 P13 | 25min | 2 tasks | 5 files |
| Phase 09 P01 | 35min | 2 tasks | 4 files |
| Phase 09 P02 | 45min | 2 tasks | 7 files |
| Phase 09 P03 | 30 | 2 tasks | 7 files |
| Phase 09 P04 | 25min | 2 tasks | 7 files |
| Phase 09 P05 | 13min | 2 tasks | 10 files |
| Phase 09 P06 | 20min | 2 tasks | 6 files |
| Phase 09 P07 | 35min | 1 task | 1 file |
| Phase 09 P08 | 20min | 1 task | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: 12 fine-grained phases derived from the hard dependency graph (HITL before agents, simulator before sensor-dependent agents, knowledge layer before knowledge-dependent agents, CostAnalyzer last)
- Architecture: Hierarchical supervisor + cluster subgraphs pattern in LangGraph; OT Bridge enforces strict data-diode at Docker network level
- Stack: All choices locked — Nx 20.x + @nxlv/python 21.x, LangGraph 0.4+, Qwen2.5 via Ollama/vLLM, Qdrant, BGE-M3, TimescaleDB, NATS JetStream, Langfuse v3, Angular 18 SSR, FastAPI
- [Phase ?]: Phase 6 Wave 0: chose def test_placeholder body convention over module-level pytest.skip for predictable per-test reporting
- [Phase ?]: Wave 0 scaffold added packages/sft-agents/tests/runtime/__init__.py for sub-package parity (Rule 3 auto-fix)
- [Phase ?]: Phase 7 Wave 0: maintenance cluster scaffold mirrors Phase 6 06-00 pattern
- [Phase ?]: Phase 7 Wave 0: mock_llm_backend selectively wires MOCK_LLM_FIXTURE only for rca-specialist + maintenance-coach (PM + DA are LLM-free per 07-VALIDATION)
- [Phase ?]: Phase 08-02: ShiftAggregator derives alerts from audit.actions ANOMALY_ALERT only (D-SH-02); WR-03 datetime objects for asyncpg
- [Phase ?]: Phase 08-06: KnowledgeCurator autonomous pattern — audit rows written immediately before return, no HITL gating (D-KC-04)
- [Phase ?]: Phase 08-08: knowledge-curator/ingest is 200 not 202 (autonomous D-KC-04); pyproject.toml extended with trn-* workspace deps for lifespan imports
- [Phase ?]: Phase 08-09: E2E uses MagicMock(spec=SOPDraft) for negative TRN-05 gate to bypass Pydantic frozen model
- [Phase 05-13]: KNW-03 gap closure path (A) chosen: disclaimer + safer CLI flag (--stub default False); live eval deferred to Phase 8 KnowledgeCurator
- [Phase 09-00a]: 8 Phase 9 ActionType values chosen (incl. COST_REPORT for autonomous CostAnalyzer); scm.historical_orders is NOT a hypertable (order frequency too low for time-series partitioning)
- [Phase 09-01]: Hypertable idempotency test limited to PK tables only — inventory_levels and energy_readings are append-only TimescaleDB hypertables without PK; NOW()-based inserts accumulate on re-run (expected behavior)
- [Phase 09-01]: 19 monthly buckets inserted (Jan 2024 — Jul 2025) to guarantee >=18 monthly buckets per sku_group with 1-month margin
- [Phase 09-02]: InventoryManager uses single-supervisor HITL (not dual like ShiftHandover); simpler pattern sufficient for SCM-01
- [Phase 09-02]: scm-inventory-manager was not installed editable in venv — fixed via uv pip install -e; future supply agents need same treatment
- [Phase ?]: Phase 09-03: EnergyOptimizer uses single-supervisor HITL (mirrors InventoryManager SCM-01); off_peak_kwh_pct over ALL readings per Pattern 7; expected_savings_pct clamped [0,100] CR-05
- [Phase ?]: Phase 09-04: CostAnalyzer pienamente autonomo (Decision.AUTO) — anomaly_threshold_pct è WARNING configurabile non regola definitiva F12
- [Phase ?]: Phase 09-05: Open Question 2 resolved — DemandForecaster publishes via state['demand_plan']
- [Phase 09-06]: CostAnalyzer.__init__ takes positional args (not keyword-only *-args) — constructed as CostAnalyzer(pool, audit_writer, None)
- [Phase 09-06]: cost-analyzer/analyze has no resume endpoint (autonomous SCM-03, D-SCM-AUTO); test verifies 404/405 on /cost-analyzer/resume
- [Phase 09-06]: EnergyOptimizeRequest + CostAnalyzeRequest datetime fields are Optional — tz validator fires only when value is not None (WR-02 compliant)
- [Phase 09-07]: Supply cluster E2E uses mock collaborators (not testcontainers) — mirrors Phase 8 knowledge E2E pattern; seed-aware constants used for numeric assertions (not calendar dates) to be robust to NOW()-relative scm_mantis_seed.sql; replay test simulates idempotency cache on second resume
- [Phase 10-00a]: sse-starlette pinned to 2.x (3.3+ requires starlette>=0.49.1 conflicting with fastapi<0.117); SCSS @use before @import required by Dart Sass; prerender:false in dev config (pre-existing NG0401 in empty scaffold)
- [Phase 10-00b]: pytest.mark.skip per test function (not module-level) mirrors Phase 6 per-test reporting convention; test_kpi_sql_uses_parameterised_placeholders auto-skips if queries.py absent (no always-passing assertion); SSE scaffold uses direct pytest.skip() not MagicMock for interrupts; Jest it.skip (not xit/xdescribe) for per-case granularity
- [Phase 10-01]: RBAC test route changed from /v1/approvals (unguarded, Phase 6 legacy) to /auth/me (guarded by require_roles) — backward-compat constraint; dev password "mantis2026" confirmed from test contracts (overrides plan text "operator123")
- [Phase 10-02]: OEE = Availability-only (P=1.0, Q=1.0 PoC); scrap_rate uses QUALITY_VERDICT audit rows as proxy; conn-vs-pool dispatch uses fetchrow presence (not acquire) to avoid AsyncMock false positives; preexisting supply_cluster_e2e failures (2 tests) confirmed unrelated and deferred
- [Phase 10-04]: mat.define-theme() azure palette + --mat-sys-* CSS override pattern for SFT hex values; RBAC_GUARD_SERVICE_TOKEN InjectionToken as stable 10-04/10-05 boundary; ng-content slots in TopBar for LanguageToggle/ThemeToggle/UserChip (10-05/10-06 slot in without AppShell changes)
- [Phase 10-05]: SseService.handleEvent()/handleError() exposed public for direct unit testing (no fake EventSource needed); RBAC_GUARD_SERVICE_TOKEN wired via useExisting:JwtService; project.json assets extended with src/assets for transloco JSON files
- [Phase 10-06]: Shared beforeEach in approval-card spec (not per-test async createComponent) eliminates compileComponents 5s timeout — all 17 tests pass in 2.9s
- [Phase 10-06]: window.confirm for reject destructive dialog (SSR-safe, keyboard-accessible, avoids MatDialog CDK overlay zone timeout in tests)
- [Phase 10-06]: ApprovalCardComponent uses signal()/_touched pattern for motivation gate; EvidencePanelComponent bridges @Input to computed() via OnChanges+signal()
- [Phase 10-07]: input() signal API (Angular 17+) instead of @Input+ngOnChanges for KpiTile — avoids manual signal bridging, fixture.componentRef.setInput() required in specs
- [Phase 10-07]: computeKpiStatus() exported pure function for direct unit testing; throughput uses ratio (value/baseline) vs 1.0/0.9 bounds per UI-SPEC
- [Phase 10-07]: AlertFeed visibleAlerts() caps at 12 (RATE_LIMIT) newest-first mirroring HITL-10 12/hr backend limit; ApprovalQueueFeed maps ApprovalPendingEvent → ApprovalCardData locally
- [Phase 10-08]: @defer on viewport chosen for ChartsRow lazy loading (SSR-safe, no separate lazy route needed); selective Chart.js registration (LineController+BarController only); jest.config.ts transformIgnorePatterns extended for ng2-charts+chart.js+lodash-es ESM
- [Phase 10-08]: app.routes.ts /operator and /manager use loadChildren pointing to feature routes files (operator.routes.ts / manager.routes.ts); RBAC defined inside feature routes
- [Phase 10-09]: All 5 persona routes migrated to loadChildren; CIO Elena reuses ManagerComponent (UI-SPEC maps cio → /manager); AdminComponent demo fallback rows (17/20 AUTO) ensures governor alert demonstrable in dev; DemoComponent placeholder retained as dead file
- [Phase 10-03]: Finite async generator for SSE HTTP tests avoids sse-starlette AppStatus event-loop collision; X-Accel-Buffering + Content-Type combined in one test; auth schema isolation for auth_users; OTEL best-effort guard (try/except) in build_app()
- [Phase 10-10]: Separate Nx project apps/factory-ui-e2e/ (not inline) per Nx e2e convention; audit via GET /v1/approvals filtered by approval_id (no /v1/audit/{id} endpoint); beforeAll reachability guard prevents silent false-green; ubuntu26.04-x64 lacks Playwright browser support — live run is CI/human item
- [Phase 10-11]: openapi-typescript@7.8.0 pinned as workspace devDep; byte-identity divergence guard in contract.spec.ts (21 tests); mkdocs-static-i18n treats root-level dirs as locales — use flat file ui-mock.md not ui/mock-ui.md; placeholder PNGs for mkdocs --strict; SFT_SKIP_SCREENSHOTS=true for CI without display
- [Phase 11-00]: deepeval/ragas in root [dependency-groups].dev (non runtime); ragas 0.4.3 bug langchain-community 0.4.x (ChatVertexAI rimosso) risolto via monkey-patch stub in eval conftest
- [Phase 11-00]: NatsHeaderCarrier(MutableMapping) pattern manuale ~30 righe (opentelemetry-instrumentation-nats non esiste su PyPI — RESEARCH Pitfall 1)
- [Phase 11-00]: setup_tracer_provider singleton-guarded con _initialized flag modulo-level (evita ProviderOverride warning su doppio call)
- [Phase 11-00]: Grafana su host port 3001 (Langfuse possiede 3000) — RESEARCH Pitfall 4; MinIO chainguard preesistente senza comando server: acceptance Langfuse OTLP deferred a fix MinIO
- [Phase 11-01]: publish_agent_command è sync (non async) per testabilità con fake callables; publish_agent_command_async per nats-py reale
- [Phase 11-01]: handle_agent_command sync con process_fn callable — caller responsabile dell'await per async; pattern più testabile
- [Phase 11-01]: setup_tracer_provider nel lifespan è best-effort (try/except) — OTEL failure non impedisce avvio gateway
- [Phase 11-01]: tag 'phase11' aggiunto in build_invocation_metadata (additivo — preserva 'phase4' + tag caller-provided)
- [Phase 11-01]: nessun OTLP exporter verso Langfuse (RESEARCH Pitfall 3: evita trace duplicate); solo CallbackHandler

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3 planning: Textile-specific sensor signatures (loom resonance, spindle vibration, dyeing bath dynamics) require domain-expert validation before simulator calibration is finalized
- Phase 5 planning: BGE-M3 vs multilingual-e5-large final choice requires A/B evaluation on actual Italian textile documents; Neo4j Community 4GB heap limit may be binding — evaluate Memgraph OSS before schema design
- Phase 11/12 planning: OEPV formula mechanics (ribasso anomalo thresholds, Codice Appalti 2023 sub-criteria weighting) need a procurement-law-informed review pass
- Competition deadline: Not documented in any research file — must be confirmed before phase durations are set

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-24T21:31:54.183Z
Stopped at: Phase 11 context gathered
Resume file: .planning/phases/11-observability-evaluation-security-hardening/11-CONTEXT.md
