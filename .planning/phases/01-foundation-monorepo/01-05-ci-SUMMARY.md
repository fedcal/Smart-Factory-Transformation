---
phase: 1
plan: 5
slug: ci
subsystem: ci
tags: [foundation, infra, ci, nx-affected, cache, github-actions]
completed: 2026-05-16
duration_minutes: 15

dependency_graph:
  requires:
    - "01-01-nx-workspace (Nx workspace + nx.json)"
    - "01-02-compose (Docker Compose dev stack)"
    - "01-04-pre-commit (pre-commit-check.yml esistente)"
  provides:
    - ".github/workflows/ci.yml — main CI pipeline nx affected"
    - ".github/workflows/nx-affected-graph.yml — grafo affected come PR artifact"
    - ".nx/cache/.gitkeep — cache dir presente in repo"
    - "docs/contributing/ci-pipeline.md — documentazione operativa"
  affects:
    - "Tutte le PR future: ci.yml e' required check su branch protection main"
    - "Phase 11: OBS-01 Langfuse SDK wiring schedulato qui"

tech_stack:
  added:
    - "nrwl/nx-set-shas@v4 — SHA detection per nx affected"
    - "astral-sh/setup-uv@v5 — uv Python package manager in CI"
    - "actions/cache@v4 — cache uv e Nx locale"
    - "actions/upload-artifact@v4 — artifact nx graph su PR"
  patterns:
    - "nx affected con NX_BASE/NX_HEAD per build selettiva polyglot"
    - "concurrency group con cancel-in-progress per PR"
    - "fallback-sha + error-on-no-successful-workflow=false per primo commit"
    - "validate-nx-graph.py step come gate pre-affected"

key_files:
  created:
    - ".github/workflows/ci.yml"
    - ".github/workflows/nx-affected-graph.yml"
    - ".nx/cache/.gitkeep"
    - "docs/contributing/ci-pipeline.md"
  modified: []

decisions:
  - "fetch-depth: 0 obbligatorio per nrwl/nx-set-shas (storia Git completa)"
  - "fallback-sha: HEAD~1 + error-on-no-successful-workflow: false per Pitfall 2 (primo commit)"
  - "Cache chiave Nx include nx.json + package-lock.json per mitigazione T-1-04 cache poisoning"
  - "nx affected --target=test con --configuration=ci per code coverage in CI"
  - ".nx/cache/.gitkeep force-added (-f) perche .nx/cache/ e' in .gitignore"
  - "Langfuse documentato come dev service (OBS-01) con SDK wiring rinviato a Phase 11"
  - "nx-affected-graph.yml NOT required check — informativo per code review"

metrics:
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
  commits:
    - hash: "68d1ea3"
      message: "feat(01-05): add CI workflow with nx affected pipeline"
      task: "1-05-01"
    - hash: "e7f256f"
      message: "feat(01-05): add nx-affected-graph workflow and ci-pipeline docs"
      task: "1-05-02"
---

# Phase 1 Plan 5: CI Pipeline Summary

**One-liner:** GitHub Actions CI con `nx affected` polyglot (lint/test/build), cache uv + Nx locale, fallback primo-commit via `nrwl/nx-set-shas@v4`, e validazione dep graph Python↔TS come gate pre-affected.

---

## Obiettivo raggiunto

Soddisfatti i Phase Success Criteria #2 (nx affected cross-language) e PLAT-04 (CI pipeline) e OBS-01 (Langfuse documentato):

- `ci.yml` esegue `nx affected --target=lint/test/build` solo sui progetti cambiati dalla PR
- Dipendenze Python↔TypeScript verificate prima di affected tramite `validate-nx-graph.py`
- Pitfall 2 (primo commit / repo nuovo) evitato con `fallback-sha: HEAD~1` + `error-on-no-successful-workflow: false`
- Cache `uv` e `Nx` configurate per ridurre i tempi da ~5 min (cold) a ~30s (warm)
- `nx-affected-graph.yml` genera grafo HTML interattivo come artifact PR per code review
- `docs/contributing/ci-pipeline.md` documenta tutti e 7 i workflow con tabella required/informativo

---

## Task eseguiti

### Task 1-05-01: `.github/workflows/ci.yml` + `.nx/cache/.gitkeep`

Creato il workflow principale CI con:

- `fetch-depth: 0` — storia Git completa per `nrwl/nx-set-shas@v4`
- `nrwl/nx-set-shas@v4` con `fallback-sha: "HEAD~1"` e `error-on-no-successful-workflow: false`
- Cache uv su `~/.cache/uv` con chiave `uv-{os}-{hash(uv.lock)}`
- Cache Nx su `.nx/cache` con chiave `nx-{os}-{hash(nx.json, package-lock.json)}`
- Step `Validate Nx dependency graph` che esegue `scripts/validate-nx-graph.py`
- 3 step `nx affected` (lint, test con `--configuration=ci`, build) ciascuno con `--parallel=3`
- `concurrency` group con `cancel-in-progress` per PR (non per push su main)
- `NX_CLOUD_DISTRIBUTED_EXECUTION: 'false'` + `NX_DAEMON: 'true'`

`.nx/cache/.gitkeep` aggiunto con `-f` perche la directory e' in `.gitignore`.

**Commit:** `68d1ea3`

### Task 1-05-02: `nx-affected-graph.yml` + `docs/contributing/ci-pipeline.md`

Creato il workflow secondario `nx-affected-graph.yml`:

- Trigger solo su PR (non required check)
- Genera `tmp/affected.html` e `tmp/graph-full.html`
- Upload artifact `nx-graph-pr-{PR_NUMBER}` con retention 14 giorni

Creato `docs/contributing/ci-pipeline.md` con:

- Tabella di tutti e 7 i workflow con colonna "Required check?"
- Documentazione dettagliata step-by-step di `ci.yml`
- Sezione cache con chiavi e motivazione (threat T-1-04)
- Performance expectations (cold/warm cache)
- Troubleshooting: nx affected 0 progetti, cache miss, build fails in CI, missing edges
- Sezione OBS-01: Langfuse documentato come dev service, SDK wiring rinviato a Phase 11
- Sezione aggiornamento nelle fasi successive (Phase 6, 11, 12)

**Commit:** `e7f256f`

---

## Deviations from Plan

### Auto-fix applicati

**1. [Rule 2 - Missing] `--configuration=ci` aggiunto a `nx affected --target=test`**
- **Found during:** Task 1
- **Issue:** Il target `test` in `nx.json` ha la configurazione `ci` definita con `codeCoverage: true`. La pipeline CI deve usare questa configurazione per ottenere code coverage report.
- **Fix:** Aggiunto `--configuration=ci` allo step `Nx Affected Test`
- **Files modified:** `.github/workflows/ci.yml`
- **Commit:** `68d1ea3`

**2. [Rule 2 - Missing] `.gitkeep` aggiunto con `-f` flag**
- **Found during:** Task 1
- **Issue:** `.nx/cache/` e' in `.gitignore` (corretto per non tracciare il contenuto della cache). L'aggiunta del `.gitkeep` richiedeva `git add -f`.
- **Fix:** `git add -f .nx/cache/.gitkeep` per tracciare solo il placeholder, non il contenuto della cache
- **Files modified:** `.nx/cache/.gitkeep`
- **Commit:** `68d1ea3`

---

## Known Stubs

Nessuno — tutti i workflow e la documentazione sono completi e operativi.

---

## Threat Flags

Nessuna nuova superficie di sicurezza introdotta rispetto al threat model del piano. Threat T-1-04 (cache poisoning) mitigato correttamente dalla chiave cache.

---

## Verifica

Tutti i check di verifica del piano superati:

```
PASS: Both YAML valid (python3 -c "import yaml; ...")
PASS: nrwl/nx-set-shas@v4 present in ci.yml
PASS: fallback-sha present in ci.yml
PASS: validate-nx-graph present in ci.yml
PASS: 3 nx affected steps (lint, test, build)
PASS: ci-pipeline.md contains ci.yml and nx affected
PASS: ci-pipeline.md contains Required check table with 7+ workflows
PASS: ci-pipeline.md references OBS-01 and Phase 11
```

Il test end-to-end (aprire PR reale su GitHub e verificare CI logs) e' rinviato a SUMMARY notes — non e' possibile eseguirlo localmente senza un repository GitHub attivo con runner configurati.

---

## Self-Check

### File creati verificati

- `.github/workflows/ci.yml` — FOUND (commit 68d1ea3)
- `.github/workflows/nx-affected-graph.yml` — FOUND (commit e7f256f)
- `.nx/cache/.gitkeep` — FOUND (commit 68d1ea3, force-added)
- `docs/contributing/ci-pipeline.md` — FOUND (commit e7f256f)

### Commit verificati

- `68d1ea3` — FOUND
- `e7f256f` — FOUND

### Workflow esistenti preservati (non modificati)

- `license-scan.yml` — intatto (01-03)
- `test-license-fixture.yml` — intatto (01-03)
- `pre-commit-check.yml` — intatto (01-04)
- `docs-deploy.yml` — intatto (01-07)
- `release.yml` — intatto (01-08)

## Self-Check: PASSED
