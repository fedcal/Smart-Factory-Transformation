---
phase: 10-backend-api-frontend
plan: 00b
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/api-gateway/tests/unit/test_auth_router.py
  - apps/api-gateway/tests/unit/test_rbac.py
  - apps/api-gateway/tests/integration/test_sse.py
  - apps/api-gateway/tests/unit/test_kpi_queries.py
  - apps/factory-ui/src/app/core/auth/jwt.service.spec.ts
  - apps/factory-ui/src/app/core/sse/sse.service.spec.ts
  - apps/factory-ui/src/app/shared/approval-card/approval-card.component.spec.ts
autonomous: true
gap_closure: false
requirements: [SRV-01, SRV-02, SRV-05, UI-03, UI-04, UI-07, HITL-07, HITL-10]
must_haves:
  truths:
    - "Failing-by-design pytest scaffolds exist for auth login, RBAC 403, SSE generator, and KPI queries (Nyquist — tests precede implementation)"
    - "Failing-by-design Jest spec scaffolds exist for JwtService, SseService Signal updates, and ApprovalCard evidence/motivation rendering"
    - "Each scaffold is collectable (no import errors) and skips or xfails cleanly until its implementation plan lands"
  artifacts:
    - path: "apps/api-gateway/tests/unit/test_auth_router.py"
      provides: "JWT login + token claim contract scaffold"
      contains: "operator@mantis.it"
    - path: "apps/api-gateway/tests/unit/test_rbac.py"
      provides: "RBAC 403 contract scaffold"
      contains: "rbac_forbidden"
    - path: "apps/api-gateway/tests/integration/test_sse.py"
      provides: "SSE kpi_update event contract scaffold"
      contains: "kpi_update"
    - path: "apps/api-gateway/tests/unit/test_kpi_queries.py"
      provides: "KPI aggregation query contract scaffold"
      contains: "oee"
    - path: "apps/factory-ui/src/app/core/sse/sse.service.spec.ts"
      provides: "SSE Signal update contract scaffold"
      contains: "kpiSnapshot"
  key_links:
    - from: "apps/api-gateway/tests/unit/test_auth_router.py"
      to: "apps/api-gateway/src/svc_api_gateway/routers/auth.py"
      via: "imports the (future) auth router build_app route"
      pattern: "auth|login"
---

<objective>
Wave 0 Nyquist test scaffolds for Phase 10: author failing-by-design test files (pytest for backend auth/RBAC/SSE/KPI, Jest for frontend Jwt/SSE/ApprovalCard) so every downstream implementation plan has a test to satisfy BEFORE code is written.

Purpose: enforces tests-before-implementation per Phase 8/9 convention. Scaffolds use `pytest.mark.skip(reason="impl in 10-01..10-03")` / `it.skip(...)` or xfail so they collect cleanly now and are un-skipped by their owning plan.
Output: 4 pytest scaffolds + 3 Jest scaffolds.

Execution note: worktrees DISABLED — sequential on main tree. 10-00a (deps) and 10-00b (this plan) are Wave 1 with disjoint files_modified.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/10-backend-api-frontend/10-CONTEXT.md
@.planning/phases/10-backend-api-frontend/10-UI-SPEC.md
@.planning/phases/10-backend-api-frontend/10-RESEARCH.md
@apps/api-gateway/tests/test_approvals_router.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend pytest scaffolds (auth, RBAC, SSE, KPI)</name>
  <files>apps/api-gateway/tests/unit/test_auth_router.py, apps/api-gateway/tests/unit/test_rbac.py, apps/api-gateway/tests/integration/test_sse.py, apps/api-gateway/tests/unit/test_kpi_queries.py</files>
  <action>Create the tests/unit and tests/integration dirs if absent (mirror the existing tests/ conftest style). Author four pytest files describing the contracts, each test body marked skip with reason referencing the owning plan: (a) test_auth_router.py — POST /auth/login with operator@mantis.it returns 200 + a JWT whose decoded payload has sub/email/role/exp claims; bad password returns 401 detail token-invalid/credentials. (b) test_rbac.py — a require_roles-protected endpoint returns 403 detail "rbac_forbidden" when the token role is not allowed, 200 when allowed. (c) test_sse.py — the kpi stream generator yields at least one event with event=="kpi_update" and JSON data (mock the pool + asyncio.sleep). (d) test_kpi_queries.py — compute_kpi_snapshot returns the 6 KPI keys (oee, mttr, mtbf, scrap_rate, throughput, downtime) given a mocked asyncpg connection; assert SQL uses $N params only (no f-string). Use exact seeded emails/roles from 10-CONTEXT Dev-Mode JWT table.</action>
  <verify>
    <automated>cd apps/api-gateway && uv run pytest tests/unit/test_auth_router.py tests/unit/test_rbac.py tests/integration/test_sse.py tests/unit/test_kpi_queries.py --collect-only -q 2>&1 | tail -10</automated>
  </verify>
  <done>All four files collect without import errors; tests are skipped pending implementation plans 10-01/10-02/10-03.</done>
</task>

<task type="auto">
  <name>Task 2: Frontend Jest spec scaffolds (Jwt, SSE, ApprovalCard)</name>
  <files>apps/factory-ui/src/app/core/auth/jwt.service.spec.ts, apps/factory-ui/src/app/core/sse/sse.service.spec.ts, apps/factory-ui/src/app/shared/approval-card/approval-card.component.spec.ts</files>
  <action>Author three Jest specs with describe blocks and it.skip bodies referencing owning plans: (a) jwt.service.spec.ts — JwtService stores/reads token only in browser (isPlatformBrowser guard), exposes role()/isAuthenticated() signals, clears on logout. (b) sse.service.spec.ts — SseService.connect is a no-op on server platform; on browser, a kpi_update event sets kpiSnapshot signal and heartbeat sets connectionStatus 'connected'. (c) approval-card.component.spec.ts — ApprovalCard renders evidence-panel sections (input/tool_calls/citations/confidence), disables approve until motivation >=10 chars (HITL-07), and exposes data-testid approval-card/evidence-panel/motivation-textarea/approve-btn/reject-btn per UI-SPEC Playwright contract. Keep imports minimal so the specs compile against the (future) classes — use it.skip so missing impl does not break the suite.</action>
  <verify>
    <automated>nx test ui-factory --testPathPattern="jwt.service|sse.service|approval-card" --passWithNoTests 2>&1 | tail -8</automated>
  </verify>
  <done>The three specs are picked up by Jest, all cases skipped, suite green (no compile errors blocking collection).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| n/a (test scaffolds only) | No runtime trust boundary crossed by skipped tests |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-00b-01 | Tampering | KPI SQL test | mitigate | test_kpi_queries.py asserts $N params only — locks the SQL-injection guardrail (CR-05) into the contract before kpi.py exists. |
| T-10-00b-02 | Information Disclosure | auth test | mitigate | test_auth_router.py asserts error detail is generic (no str(exc)) per CR-02. |
</threat_model>

<verification>
- Backend scaffolds collect (4 files), all skipped.
- Frontend scaffolds run under Jest (3 files), all skipped.
</verification>

<success_criteria>
Every Phase 10 implementation plan has a pre-existing, collectable, skipped test it must turn green — Nyquist satisfied.
</success_criteria>

<output>
Create `.planning/phases/10-backend-api-frontend/10-00b-SUMMARY.md` when done.
</output>
