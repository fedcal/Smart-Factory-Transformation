---
phase: 1
plan: 5
slug: ci
type: execute
wave: 3
depends_on: ["01", "02", "04"]
files_modified:
  - .github/workflows/ci.yml
  - .github/workflows/nx-affected-graph.yml
  - .nx/cache/.gitkeep
  - docs/contributing/ci-pipeline.md
autonomous: true
requirements: [PLAT-04, OBS-01]
tags: [foundation, infra, ci, nx-affected, cache]

must_haves:
  truths:
    - "Il workflow `ci.yml` su PR usa `nrwl/nx-set-shas@v4` con `fetch-depth: 0` e `error-on-no-successful-workflow: false` per evitare il bug di Pitfall 2 sul primo commit"
    - "`nx affected --target=lint/test/build` viene chiamato con `--base=$NX_BASE --head=$NX_HEAD`"
    - "Cache uv attiva via `actions/cache@v4` su `~/.cache/uv` con chiave hash su `uv.lock`"
    - "Cache Nx locale attiva via `actions/cache@v4` su `.nx/cache` con chiave hash su `nx.json + package-lock.json`"
    - "PRIMO run del workflow su un repo nuovo NON fallisce (fallback su `npx nx run-many --all` se nessun base SHA disponibile)"
    - "Langfuse è dichiarato come dev observability service (riferimento in `docs/contributing/ci-pipeline.md`); nessuna SDK Langfuse wired in runtime in questa fase (rinviato a Phase 11)"
  artifacts:
    - path: ".github/workflows/ci.yml"
      provides: "Main CI workflow con nx affected, uv cache, Nx cache, parallel=3"
      contains: "nrwl/nx-set-shas@v4"
    - path: ".github/workflows/nx-affected-graph.yml"
      provides: "Workflow secondario che emette nx graph e valida edges Python<->TS"
    - path: "docs/contributing/ci-pipeline.md"
      provides: "Documentazione dei workflows e dei required check"
  key_links:
    - from: ".github/workflows/ci.yml"
      to: "nrwl/nx-set-shas@v4 + actions/cache@v4"
      via: "GitHub Actions setup"
      pattern: "nrwl/nx-set-shas@v4"
    - from: ".github/workflows/ci.yml"
      to: "scripts/validate-nx-graph.py"
      via: "Step Validate dependency graph"
      pattern: "validate-nx-graph"
---

<objective>
Costruire il main CI workflow GitHub Actions con `nx affected` su build/test/lint, gestendo correttamente i casi edge (primo commit, squash merge) e configurando cache uv + cache Nx per ridurre i tempi di esecuzione. Soddisfa Phase Success Criterion #2: `nx affected --target=test` esegue solo i package cambiati e risolve correttamente le dipendenze Python<->TypeScript.

Purpose: senza CI selettiva, ogni PR rieseguirà tutto il workspace polyglot (16 agenti + 3 packages + 3 apps + UI Angular) — 10+ minuti per cambio singolo. nx affected con cache porta a 1-2 minuti tipici.

Output: workflow CI required check, validazione dep graph come step a sé, documentazione operativa per troubleshooting.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-foundation-monorepo/01-CONTEXT.md
@.planning/phases/01-foundation-monorepo/01-RESEARCH.md
@CLAUDE.md
@.planning/phases/01-foundation-monorepo/01-01-SUMMARY.md
@.planning/phases/01-foundation-monorepo/01-02-SUMMARY.md
@.planning/phases/01-foundation-monorepo/01-04-SUMMARY.md
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PR -> CI runner | input non trusted; runner secret access deve essere minimizzato |
| CI -> Nx cache | corruzione cache potrebbe nascondere build failure |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-04 | Tampering | Nx cache poisoning | mitigate | chiave cache include `hashFiles('nx.json', 'package-lock.json')`; cache locale a `.nx/cache`, no remote write da PR; restore-keys partial-match accettata per performance |
| T-1-SC | Tampering | GitHub Actions referenced (nrwl/nx-set-shas@v4, astral-sh/setup-uv@v5, actions/setup-node@v4) | mitigate | pinning a major (`@v4`, `@v5`); per ridurre rischio, considerare pinning a commit SHA in futuro (deferred) |
</threat_model>

<tasks>

<task id="1-05-01" wave="3" type="auto">
  <name>Task 1: .github/workflows/ci.yml — main nx affected pipeline</name>
  <files>.github/workflows/ci.yml, .nx/cache/.gitkeep</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 6: GitHub Actions CI nx affected, righe ~880-949; Pitfall 2 nx affected primo commit; Pitfall 4 Python->TS deps)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: ci.yml senza Nx Cloud, cache locale GitHub Actions; OBS-01 Langfuse referenziato come dev service)
  </read_first>
  <action>
    Creare `.github/workflows/ci.yml` che combina i pattern di RESEARCH ma con le seguenti CORREZIONI sui parametri `nrwl/nx-set-shas@v4`:
    ```yaml
    name: CI
    on:
      pull_request:
      push:
        branches: [main]
    concurrency:
      group: ci-${{ github.workflow }}-${{ github.ref }}
      cancel-in-progress: ${{ github.event_name == 'pull_request' }}
    jobs:
      main:
        runs-on: ubuntu-latest
        timeout-minutes: 30
        env:
          NX_CLOUD_DISTRIBUTED_EXECUTION: 'false'
          NX_DAEMON: 'true'
        steps:
          - uses: actions/checkout@v4
            with:
              fetch-depth: 0   # critico per nx-set-shas (Pitfall 2)
          - uses: actions/setup-node@v4
            with:
              node-version: 20
              cache: 'npm'
          - uses: actions/setup-python@v5
            with:
              python-version: '3.12'
          - name: Install uv
            uses: astral-sh/setup-uv@v5
            with:
              version: "0.6"
              enable-cache: true
          - name: Cache uv
            uses: actions/cache@v4
            with:
              path: ~/.cache/uv
              key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
              restore-keys: uv-${{ runner.os }}-
          - name: Cache Nx
            uses: actions/cache@v4
            with:
              path: .nx/cache
              key: nx-${{ runner.os }}-${{ hashFiles('nx.json', 'package-lock.json') }}
              restore-keys: nx-${{ runner.os }}-
          - name: Install npm dependencies
            run: npm ci
          - name: Install Python dependencies
            run: uv sync --all-packages
          - name: Set NX SHAs
            uses: nrwl/nx-set-shas@v4
            with:
              main-branch-name: main
              workflow-id: ci.yml
              fallback-sha: "HEAD~1"
              error-on-no-successful-workflow: false
          - name: Validate Nx dependency graph (Python<->TS edges)
            run: |
              mkdir -p tmp
              npx nx graph --file=tmp/graph.json
              python3 scripts/validate-nx-graph.py
          - name: Nx Affected Lint
            run: npx nx affected --target=lint --base=$NX_BASE --head=$NX_HEAD --parallel=3
          - name: Nx Affected Test
            run: npx nx affected --target=test --base=$NX_BASE --head=$NX_HEAD --parallel=3
          - name: Nx Affected Build
            run: npx nx affected --target=build --base=$NX_BASE --head=$NX_HEAD --parallel=3
    ```
    Creare `.nx/cache/.gitkeep` per assicurarsi che la directory cache esista in repo (Nx la crea on-demand, ma utile per setup uniforme).
  </action>
  <acceptance_criteria>
    - `.github/workflows/ci.yml` esiste e contiene `nrwl/nx-set-shas@v4`
    - `.github/workflows/ci.yml` contiene `fetch-depth: 0` (Pitfall 2)
    - `.github/workflows/ci.yml` contiene `error-on-no-successful-workflow: false` (Pitfall 2)
    - `.github/workflows/ci.yml` contiene `fallback-sha: "HEAD~1"` (Pitfall 2)
    - `.github/workflows/ci.yml` contiene 3 step `nx affected` (lint, test, build) ognuno con `--parallel=3`
    - `.github/workflows/ci.yml` contiene step `Validate Nx dependency graph (Python<->TS edges)` che esegue `validate-nx-graph.py`
    - `.github/workflows/ci.yml` contiene cache uv e cache Nx con `actions/cache@v4`
    - `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` exits 0
  </acceptance_criteria>
</task>

<task id="1-05-02" wave="3" type="auto">
  <name>Task 2: nx-affected-graph workflow secondario + docs/contributing/ci-pipeline.md</name>
  <files>.github/workflows/nx-affected-graph.yml, docs/contributing/ci-pipeline.md</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Validation Architecture; Code Examples nx graph validation script)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: workflows separati per concern)
  </read_first>
  <action>
    Creare `.github/workflows/nx-affected-graph.yml` che genera nx graph come HTML artifact su PR (per ispezione manuale):
    ```yaml
    name: Nx Affected Graph
    on:
      pull_request:
    jobs:
      graph:
        runs-on: ubuntu-latest
        timeout-minutes: 10
        steps:
          - uses: actions/checkout@v4
            with:
              fetch-depth: 0
          - uses: actions/setup-node@v4
            with:
              node-version: 20
              cache: 'npm'
          - uses: actions/setup-python@v5
            with:
              python-version: '3.12'
          - name: Install npm deps
            run: npm ci
          - name: Set NX SHAs
            uses: nrwl/nx-set-shas@v4
            with:
              main-branch-name: main
              workflow-id: nx-affected-graph.yml
              fallback-sha: "HEAD~1"
              error-on-no-successful-workflow: false
          - name: Generate affected graph HTML
            run: |
              mkdir -p tmp
              npx nx affected:graph --file=tmp/affected.html --base=$NX_BASE --head=$NX_HEAD
              npx nx graph --file=tmp/graph-full.html
          - name: Upload graph artifact
            uses: actions/upload-artifact@v4
            with:
              name: nx-graph-pr-${{ github.event.pull_request.number }}
              path: tmp/
              retention-days: 14
    ```

    Creare `docs/contributing/ci-pipeline.md` che documenta i 5 workflows attivi su Fase 1:
    - `ci.yml` — main pipeline (nx affected lint/test/build, validate graph) — REQUIRED CHECK
    - `pre-commit-check.yml` — quality gates (plan 04) — REQUIRED CHECK
    - `license-scan.yml` — supply-chain (plan 03) — REQUIRED CHECK
    - `helm-smoke-test.yml` — Helm validation (plan 06) — REQUIRED CHECK
    - `docs-deploy.yml` — docs publish (plan 07) — NOT required (runs only on push to main)
    - `nx-affected-graph.yml` — visualizzazione dep graph (questo plan) — NOT required, ma utile in code review
    - `test-license-fixture.yml` (plan 03) — anti-regression weekly — NOT required
    Includere:
    - Sezione "Performance expectations": ~1-2 minuti cold cache, ~30s warm cache per PR tipica
    - Sezione "Troubleshooting": `nx affected` ritorna 0 progetti (verificare `fetch-depth: 0`, `error-on-no-successful-workflow: false`), cache miss frequente (chiave hash include nx.json + package-lock.json), Langfuse dev service citato come "referenziato come stack obs ma SDK runtime non wired in questa fase — vedi Phase 11" per OBS-01.
    - Sezione "Riferimento alla osservabilità (OBS-01)": Langfuse v3 self-hosted è già disponibile via `make up` (plan 02). Gli agent runtime non emettono ancora traces verso Langfuse; quel cablaggio è schedulato a Phase 11. CI non esegue runtime call verso Langfuse.
  </action>
  <acceptance_criteria>
    - `.github/workflows/nx-affected-graph.yml` esiste e contiene `nx affected:graph`
    - `.github/workflows/nx-affected-graph.yml` contiene `actions/upload-artifact@v4`
    - `docs/contributing/ci-pipeline.md` esiste e contiene la stringa `ci.yml` e `nx affected`
    - `docs/contributing/ci-pipeline.md` contiene una tabella dei 5+ workflows con colonna "Required check?"
    - `docs/contributing/ci-pipeline.md` contiene riferimento esplicito a OBS-01 e Phase 11 per il wiring SDK Langfuse
    - `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/nx-affected-graph.yml'))"` exits 0
  </acceptance_criteria>
</task>

</tasks>

<verification>
1. `python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['.github/workflows/ci.yml','.github/workflows/nx-affected-graph.yml']]"` exits 0
2. `grep -E "nrwl/nx-set-shas@v4" .github/workflows/ci.yml` exits 0
3. `grep -E "fallback-sha" .github/workflows/ci.yml` exits 0
4. `grep -E "validate-nx-graph" .github/workflows/ci.yml` exits 0
5. `grep -E "nx affected --target=(lint|test|build)" .github/workflows/ci.yml | wc -l` ritorna >= 3
6. Test end-to-end (post-PR): aprire PR che cambia solo `packages/sft-contracts/`, verificare che `ui-factory` e `svc-api-gateway` siano elencati come affected in CI logs.
</verification>

<success_criteria>
- nx affected con dep graph cross-language (Python -> TypeScript) funziona (Phase Success Criterion #2)
- CI tempi ragionevoli (<= 5 min PR tipica con cache caldo)
- Pitfall 2 (primo commit) evitato grazie a fallback-sha + error-on-no-successful-workflow
- Pitfall 4 (Python -> TS deps mancanti) catturato da validate-nx-graph.py step
- Langfuse documentato come dev service (OBS-01) con wiring rinviato a Phase 11
</success_criteria>

<output>
Create `.planning/phases/01-foundation-monorepo/01-05-SUMMARY.md` quando done.
</output>
