---
phase: 10-backend-api-frontend
plan: 00a
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/api-gateway/pyproject.toml
  - package.json
  - apps/factory-ui/postcss.config.json
  - apps/factory-ui/src/styles.scss
autonomous: true
gap_closure: false
requirements: [SRV-01, SRV-02, SRV-04, UI-02, UI-04, UI-05, UI-07, UI-10]
must_haves:
  truths:
    - "api-gateway resolves PyJWT, sse-starlette and the three opentelemetry packages without conflict"
    - "The Angular workspace resolves @angular/material@~19.2, @angular/cdk@~19.2, @angular/localize@~19.2, @jsverse/transloco, ng2-charts@8.x (NOT @10), chart.js@4.x, tailwindcss@4.x + @tailwindcss/postcss without ERESOLVE"
    - "Tailwind v4 PostCSS plugin is wired and a mat-flat-button renders with a 64px min-height (no preflight regression)"
  artifacts:
    - path: "apps/api-gateway/pyproject.toml"
      provides: "Backend Phase 10 deps (PyJWT, sse-starlette, opentelemetry-*)"
      contains: "sse-starlette"
    - path: "package.json"
      provides: "Frontend Phase 10 deps pinned to Angular-19-compatible versions"
      contains: "ng2-charts"
    - path: "apps/factory-ui/postcss.config.json"
      provides: "Tailwind v4 PostCSS plugin registration"
      contains: "@tailwindcss/postcss"
    - path: "apps/factory-ui/src/styles.scss"
      provides: "Tailwind import + Angular Material @use + 64px touch override layer"
      contains: "tailwindcss"
  key_links:
    - from: "apps/factory-ui/postcss.config.json"
      to: "apps/factory-ui/src/styles.scss"
      via: "PostCSS processes the @import \"tailwindcss\" directive"
      pattern: "@tailwindcss/postcss"
---

<objective>
Wave 0 dependency installation for Phase 10: add the backend Python deps to `apps/api-gateway/pyproject.toml` and the frontend npm deps to the workspace `package.json`, then wire Tailwind v4 via PostCSS and verify Angular Material renders with the mandated 64px touch override.

Purpose: Every downstream plan (backend auth/kpi/sse, frontend shell/services/UI/E2E) depends on these libraries existing at the correct, Angular-19-compatible versions. This plan installs nothing it cannot pin.
Output: Updated manifests + a working Tailwind/Material baseline.

Execution note: worktrees are DISABLED — executors run SEQUENTIALLY on the main tree. 10-00a (this plan, deps) and 10-00b (test scaffolds) are both Wave 1 with disjoint files_modified.

Version constraints are LOCKED by 10-RESEARCH + 10-CONTEXT post_research_resolutions:
- ng2-charts MUST be @8.x (peer @angular/core>=19). @10 requires @angular/cdk>=21 and breaks the build (ERESOLVE).
- @angular/material + @angular/cdk + @angular/localize MUST be ~19.2.x (workspace is Angular 19.2).
- i18n uses @jsverse/transloco (runtime, no-reload) per post_research_resolution #1 — NOT @angular/localize for the text toggle.
- JWT lib is PyJWT (already in env) — NOT python-jose.
- Frontend deps go in the WORKSPACE package.json (Nx/Angular convention) — do NOT create apps/factory-ui/package.json.
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
@.planning/phases/10-backend-api-frontend/10-RESEARCH.md
@apps/api-gateway/pyproject.toml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add backend Phase 10 dependencies</name>
  <files>apps/api-gateway/pyproject.toml</files>
  <action>Add to the `[project].dependencies` array of apps/api-gateway/pyproject.toml, alongside the existing fastapi/asyncpg/pydantic/structlog entries: PyJWT>=2.9,<3 ; sse-starlette>=3.4,<4 ; opentelemetry-api>=1.40,<2 ; opentelemetry-sdk>=1.40,<2 ; opentelemetry-instrumentation-fastapi>=0.55b0 . Do NOT add python-jose (per CONTEXT post_research_resolution #5). Keep the array sorted/grouped consistently with the existing style. Then run the workspace's uv lock to resolve. Do NOT touch unrelated dependency constraints.</action>
  <verify>
    <automated>cd apps/api-gateway && uv lock && uv run python -c "import jwt, sse_starlette, opentelemetry.instrumentation.fastapi; print('deps-ok')"</automated>
  </verify>
  <done>The import smoke command prints deps-ok; uv.lock resolves with no version conflict.</done>
</task>

<task type="auto">
  <name>Task 2: Add frontend Phase 10 dependencies (Angular-19-compatible, pinned)</name>
  <files>package.json</files>
  <action>Identify the correct workspace manifest first: the root package.json is the Nx workspace manifest (verified — there is no apps/factory-ui/package.json). Add to it: @angular/material ~19.2.0, @angular/cdk ~19.2.0, @angular/localize ~19.2.0 (localize still needed for DatePipe/number locale data registration), @jsverse/transloco (latest compatible with Angular 19), ng2-charts ^8.0.0 (PIN — never @10), chart.js ^4.4.0 ; and devDependencies @nx/playwright 20.8.4 (match the workspace Nx version) + @playwright/test ^1.50.0 + tailwindcss ^4.3.0 + @tailwindcss/postcss ^4.3.0. Use the workspace package manager (pnpm) to install so the lockfile updates. If ng2-charts resolves to @10, force ^8.0.0 explicitly — verify the installed version is 8.x afterward.</action>
  <verify>
    <automated>node -e "const p=require('./package.json');const all={...p.dependencies,...p.devDependencies};const ng2=all['ng2-charts']||'';if(!ng2.includes('8'))throw new Error('ng2-charts must be 8.x, got '+ng2);for(const k of ['@angular/material','@angular/cdk','@jsverse/transloco','chart.js','tailwindcss','@tailwindcss/postcss','@playwright/test'])if(!all[k])throw new Error('missing '+k);console.log('frontend-deps-ok')"</automated>
  </verify>
  <done>ng2-charts is pinned to 8.x; all required frontend deps present in package.json; lockfile updated.</done>
</task>

<task type="auto">
  <name>Task 3: Wire Tailwind v4 PostCSS + Angular Material baseline, verify 64px touch</name>
  <files>apps/factory-ui/postcss.config.json, apps/factory-ui/src/styles.scss</files>
  <action>Create apps/factory-ui/postcss.config.json registering the "@tailwindcss/postcss" plugin (Tailwind v4 has no tailwind.config.js). In apps/factory-ui/src/styles.scss set the CRITICAL import order per RESEARCH Pattern 6: `@import "tailwindcss";` FIRST, then `@use "@angular/material" as mat;`. Add an `@layer utilities` block forcing `.mat-mdc-button, .mat-mdc-icon-button { min-height:64px; min-width:64px; }` (UI-02 touch target, overrides MDC). Do NOT yet author full theme files (_tokens/_theme.* are Wave 4) — this task only proves the toolchain compiles and the 64px override survives Tailwind preflight. Add a tiny throwaway probe component OR rely on the existing app build to confirm compilation; remove any probe before finishing.</action>
  <verify>
    <automated>nx build ui-factory --configuration=development 2>&1 | tail -5 && grep -q "@tailwindcss/postcss" apps/factory-ui/postcss.config.json && grep -q "min-height:64px\|min-height: 64px" apps/factory-ui/src/styles.scss && echo tailwind-material-ok</automated>
  </verify>
  <done>ui-factory builds with Tailwind + Material; styles.scss contains the 64px touch override in correct import order; postcss config registers the v4 plugin.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| npm/pip registry → build | Third-party package code enters the build at install time |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-SC | Tampering | npm/pip installs | mitigate | All packages were vetted in 10-RESEARCH Package Legitimacy Audit (slopcheck OK / PyPI verified); versions pinned. ng2-charts pinned @8.x to avoid silent incompatible resolution. No [SUS]/[SLOP] packages — no blocking checkpoint required. |
| T-10-00a-01 | Tampering | ng2-charts resolution | mitigate | Explicit ^8.0.0 pin + post-install version assertion in Task 2 verify. |
</threat_model>

<verification>
- `uv lock` resolves backend deps; import smoke passes.
- ng2-charts is 8.x (assertion in verify).
- ui-factory builds with Tailwind v4 + Angular Material; 64px override present.
</verification>

<success_criteria>
Backend and frontend manifests carry all Phase 10 deps at Angular-19/PyPI-compatible pinned versions, and the Tailwind+Material toolchain compiles with the mandated 64px touch override intact.
</success_criteria>

<output>
Create `.planning/phases/10-backend-api-frontend/10-00a-SUMMARY.md` when done.
</output>
