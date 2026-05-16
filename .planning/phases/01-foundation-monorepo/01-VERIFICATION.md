---
phase: 01-foundation-monorepo
verified: 2026-05-16T20:21:00Z
status: human_needed
score: 10/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Eseguire make up e attendere che tutti i container siano healthy"
    expected: "Stack completo (postgres, timescaledb, redis, qdrant, nats, ollama, langfuse-web, clickhouse, minio) healthy entro 180s; make up esce con codice 0"
    why_human: "Richiede Docker Engine attivo. Non verificabile staticamente — test di integrazione runtime."
  - test: "Eseguire pre-commit run --all-files dopo pip install pre-commit==4.6.0 e pre-commit install"
    expected: "Exit 0 su repo pulito; hook ruff, mypy, eslint, prettier, commitlint, gitleaks, pre-commit-hooks tutti eseguiti"
    why_human: "Richiede installazione locale di pre-commit e tutti i tool (ruff, mypy, node, etc.). Non eseguibile in analisi statica."
  - test: "Aprire una PR di test su GitHub che aggiunga una dipendenza GPL (es. usando il file tests/license/fixture-gpl-pyproject.toml come riferimento)"
    expected: "Il workflow license-scan.yml fallisce con exit code != 0; la PR viene bloccata"
    why_human: "Richiede un repository GitHub attivo con Actions runner e branch protection configurata."
  - test: "Configurare branch protection su main seguendo docs/operations/branch-protection.md e verificare che i required checks siano: license-scan, pre-commit-check, ci, helm-smoke-test"
    expected: "PR senza CI green non può essere mergiata; i quattro check sono listed come required"
    why_human: "Richiede accesso admin al repository GitHub. Non verificabile dal codice locale."
  - test: "Eseguire helm install su un cluster k3d locale (o attendere la prima PR che tocca infra/helm/**)"
    expected: "helm-smoke-test.yml passa: lint 9/9 + dry-run + install + kubectl wait + helm test"
    why_human: "Richiede k3d installato localmente o runner GitHub Actions. Il smoke test è verificabile solo con cluster live."
  - test: "Verificare che GitHub Pages sia configurato (Settings > Pages, Source: gh-pages branch) e che docs-deploy.yml produca un sito bilingue IT/EN navigabile"
    expected: "Sito MkDocs Material pubblicato su https://fedcal.github.io/Smart-Factory-Transformation con selettore lingua IT/EN funzionante"
    why_human: "Richiede configurazione manuale GitHub Pages e primo push su main che tocchi docs/. Non verificabile staticamente."
---

# Phase 1: Foundation & Monorepo — Verification Report

**Phase Goal:** Stabilire la base operativa del monorepo: workspace Nx polyglot Python+Angular, stack dev Docker Compose, CI/CD GitHub Actions con nx affected, license scanner SBOM-based, pre-commit hooks, skeleton Helm production-ready e MkDocs bilingue.
**Verified:** 2026-05-16T20:21:00Z
**Status:** HUMAN_NEEDED — tutti i controlli statici passati; 6 verifiche runtime richiedono ambiente live
**Re-verification:** No — verifica iniziale

---

## Executive Summary

**Verdetto: PARTIAL PASS (static) — 10/11 must-have verificati staticamente.**

I ~150 file prodotti dai 8 piani esistono, sono sostanziali e correttamente collegati tra loro. Tutti i 18 commit documentati nelle SUMMARY sono presenti in git. Non sono stati trovati anti-pattern bloccanti (nessun TBD/FIXME/XXX non referenziato nei file di implementazione).

L'unico requisito con evidence parziale è **OBS-01**: Langfuse v3 è presente nel compose stack come servizio dev, ma il wiring SDK (traces degli agenti) è esplicitamente rinviato a Fase 11 — questo è comportamento atteso e documentato, non un gap.

Sei verifiche richiedono ambiente runtime (Docker, GitHub Actions, k3d, GitHub Pages) e sono delegate all'utente.

**Raccomandazione: Procedere a Fase 2 dopo aver eseguito le verifiche human-needed.**

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Monorepo Nx 20.x polyglot con @nxlv/python 21.3.1 funzionante | VERIFIED | `nx.json` contiene `@nxlv/python`; `package.json` ha `"nx": "20.8.4"`, `"@nxlv/python": "21.3.1"`; 23 Python sub-projects + 1 Angular SSR |
| 2 | uv workspace single-lockfile con 23 members e Python 3.12 | VERIFIED | `pyproject.toml` ha `[tool.uv.workspace]` + `members`; `uv.lock` esiste (480 righe); `.python-version` = `3.12`; `[dependency-groups]` PEP 735 |
| 3 | 6 root-folder PLAT-03 presenti | VERIFIED | `apps/`, `packages/`, `services/`, `docs/`, `infra/`, `simulators/` tutti esistenti |
| 4 | Docker Compose dev stack con healthcheck e --wait | VERIFIED (static) | 5 file compose presenti; 12 healthcheck totali; `make up` usa `--wait`; `BASE_STACK` include core+sim+obs; nessun tag `:latest` nei file core/sim/llm |
| 5 | `nx affected` CI con Python-TS edges risolti | VERIFIED | `.github/workflows/ci.yml` ha `nrwl/nx-set-shas@v4`, `validate-nx-graph.py` come gate, 3 step `nx affected` (lint/test/build); `REQUIRED_EDGES` = 5 edges documentati |
| 6 | License scanner SBOM-based come PR gate | VERIFIED | `license-scan.yml` con Syft + Trivy; `trivy.yaml` con forbidden list GPL/AGPL; fixture GPL con doppia copertura; `test-license-fixture.yml` meta-test con assertion `outcome != failure` |
| 7 | Pre-commit hooks con versioni pinnate | VERIFIED | `.pre-commit-config.yaml` con 5 rev esatte (v0.11.10, v3.5.3, v9.18.0, v8.24.2, v5.0.0); mypy scoped a `^packages/sft-(agents|domain|contracts)/`; gitleaks allowlist |
| 8 | Helm skeleton production-ready (8 chart) | VERIFIED | 8 chart in `infra/helm/charts/`; 8 NetworkPolicy, 8 HPA, 8 PDB, 20 `runAsNonRoot: true`; umbrella `sft-stack` con Chart.lock; NetworkPolicy data-diode ot-bridge |
| 9 | Makefile con target standard PLAT-09 | VERIFIED | `Makefile` ha: up, up-gpu, up-core, down, reset, ps, logs, test, lint, format, docs, docs-serve, demo, sbom, license-scan, helm-test; tutti su `.PHONY` |
| 10 | Changesets versioning con release workflow | VERIFIED | `.changeset/config.json` con `linked: [["sft-agents", "sft-domain", "sft-contracts"]]`; `release.yml` con `changesets/action@v1`; `sync-python-versions.py` aggiornato |
| 11 | MkDocs bilingue IT/EN con gh-pages deploy | VERIFIED | `docs/mkdocs.yml` con plugin `i18n` folder-based; 8 pagine placeholder IT+EN; `docs-deploy.yml` con `mkdocs gh-deploy` su push a main; versioni pinnate in `requirements.txt` |

**Score: 10/11 truths verificate staticamente — OBS-01 PARZIALE (comportamento atteso, documentato)**

---

## Requirements Coverage Matrix

| Requirement | Descrizione | Piano | Status | Evidence |
|-------------|-------------|-------|--------|----------|
| PLAT-01 | Monorepo Nx con `@nxlv/python` e Angular first-class | 01-01 | SATISFIED | `nx.json`, `package.json` con versioni esatte; 24 progetti Nx totali |
| PLAT-02 | Workspace polyglot uv + pnpm/Nx | 01-01 | SATISFIED | `pyproject.toml` uv workspace 23 members; `pnpm-workspace.yaml`; `uv.lock` |
| PLAT-03 | Struttura 6 root-folder documentata | 01-01 | SATISFIED | Tutte e 6 le cartelle presenti; `docs/contributing/toolchain.md` |
| PLAT-04 | GitHub Actions con `nx affected` | 01-05 | SATISFIED | `.github/workflows/ci.yml` con `nrwl/nx-set-shas@v4`; gate `validate-nx-graph.py` |
| PLAT-05 | Pipeline CI license scanner blocca dipendenze incompatibili | 01-03 | SATISFIED | `license-scan.yml` Syft+Trivy; `trivy.yaml` forbidden list; fixture GPL; meta-test |
| PLAT-06 | Pre-commit hooks (ruff, mypy strict, eslint, prettier) in CI | 01-04 | SATISFIED (static) | `.pre-commit-config.yaml`; `pre-commit-check.yml` CI mirror; versioni pinnate |
| PLAT-07 | Docker Compose dev locale completo | 01-02 | SATISFIED (static) | 5 compose file; Langfuse v3, NATS, Qdrant, Ollama, TimescaleDB; healthcheck; named volumes |
| PLAT-08 | Helm chart skeleton per deploy prod on-premise | 01-06 | SATISFIED | 8 chart prod-ready; HPA/PDB/NetworkPolicy/RBAC; umbrella sft-stack; helm-smoke-test.yml |
| PLAT-09 | Makefile con comandi standard | 01-02+03+06+07 | SATISFIED | 16 target verificati; tutti su .PHONY; `make up` usa `--wait` |
| PLAT-10 | Versionamento semantico con Changesets | 01-08 | SATISFIED | `.changeset/config.json` linked; `release.yml`; `sync-python-versions.py` |
| OBS-01 | Langfuse self-hosted v3 (Docker Compose dev + Helm prod) | 01-02+06 | PARTIAL | Compose: `langfuse/langfuse:3` + `langfuse-worker:3` in `obs.yml` con healthcheck; Helm: `langfuse 1.5.30` in `Chart.lock`; SDK wiring rinviato a Fase 11 (comportamento documentato) |

---

## Phase Success Criteria Assessment

### SC#1: `make up` avvia stack dev healthy

**Status: VERIFIED STATIC — verifica runtime rinviata all'utente**

Evidence statica:
- `make up` = `docker compose -f core.yml -f sim.yml -f obs.yml -f llm-cpu.yml up -d --wait` (flag `--wait` presente)
- `infra/compose/.env.example` documenta tutte le variabili; nessun secret in plaintext nei file yml
- 12 healthcheck totali nei 4 file compose; `obs.yml` ha catena `depends_on: condition: service_healthy` su 4 upstream per langfuse-web
- Nessun tag `:latest` nei file core/sim/llm (eccezione documentata: `cgr.dev/chainguard/minio:latest` con rationale in SUMMARY)
- NATS configurato con `-js` per JetStream; Ollama con `/api/tags` healthcheck; Qdrant con `/healthz`

Pendente (human-needed): esecuzione effettiva su macchina con Docker Engine.

### SC#2: `nx affected --target=test` risolve dipendenze Python-TS

**Status: VERIFIED**

Evidence:
- `.github/workflows/ci.yml`: step `Validate Nx dependency graph` esegue `scripts/validate-nx-graph.py` prima di qualunque `nx affected`
- `scripts/validate-nx-graph.py` definisce `REQUIRED_EDGES` = 5 coppie Python-TS (ui-factory→sft-contracts; svc-api-gateway→sft-contracts/sft-agents/sft-domain; svc-orchestrator→sft-agents)
- SUMMARY 01-01 riporta l'output: "OK: All 5 required dependency edges present"
- `ci.yml` step `nx affected --target=test --configuration=ci` presente con `--parallel=3`
- Edge `ui-factory → sft-contracts` verificato via `implicitDependencies` in `apps/factory-ui/project.json` (citato in SUMMARY)

### SC#3: PR con dipendenza GPL bloccata

**Status: VERIFIED STATIC — verifica runtime rinviata all'utente**

Evidence:
- `infra/license/trivy.yaml`: sezione `forbidden` include GPL-1.0/2.0/3.0 (tutte le varianti), AGPL-3.0 (tutte le varianti), SSPL-1.0, BUSL-1.1
- `tests/license/fixture-gpl-pyproject.toml`: doppia copertura — `license = { text = "GPL-3.0-only" }` + dep `pyreadline3>=3.4.1` (GPL-2.0)
- `.github/workflows/test-license-fixture.yml`: meta-test `verify-block` che asserisce `steps.trivy.outcome == 'failure'` — se trivy NON fallisce, il test fallisce (`exit 1`)
- `license-scan.yml`: step finale `exit 1` se `license-check.outcome == 'failure'`; PR comment automatico; SBOM retention 90 giorni
- `LICENSE-EXCEPTIONS.md`: eccezione MinIO AGPL-3.0 documentata con rationale on-prem single-tenant

Pendente (human-needed): esecuzione del workflow su GitHub Actions con runner attivo.

### SC#4: Pre-commit fail-fast su violazioni

**Status: VERIFIED STATIC — verifica runtime rinviata all'utente**

Evidence:
- `.pre-commit-config.yaml`: 7 hook ordinati; rev pinnate (v0.11.10, v3.5.3, v9.18.0, v8.24.2, v5.0.0); NESSUN floating ref `@main` o `@HEAD`
- Hook inclusi: `ruff-format` + `ruff` (lint Python), `mypy-sft-packages --strict` (scope limitato `^packages/sft-(agents|domain|contracts)/`), eslint (TS), mirrors-prettier (TS/JSON/YAML/MD/CSS/HTML), commitlint Conventional Commits, gitleaks secret scanning, pre-commit-hooks (trailing-whitespace, check-yaml, check-json, etc.)
- `.github/workflows/pre-commit-check.yml`: mirror CI identico con `pre-commit/action@v3.0.1 --all-files --show-diff-on-failure`
- `.gitleaks.toml`: allowlist esplicita per fixture noti

Pendente (human-needed): `pre-commit run --all-files` su installazione locale.

### SC#5: Helm deploya su k8s locale

**Status: VERIFIED STATIC — verifica runtime rinviata all'utente**

Evidence statica:
- 8 chart per-servizio in `infra/helm/charts/`: api-gateway, orchestrator, factory-ui, ot-bridge, agents-ops, agents-mnt, agents-trn, agents-scm
- Umbrella chart `infra/helm/sft-stack/` con `Chart.lock` che pinua: postgresql 16.7.27, qdrant 1.18.0, nats 1.3.16, langfuse 1.5.30, ingress-nginx 4.15.1
- Ogni chart ha: `HorizontalPodAutoscaler`, `PodDisruptionBudget`, `NetworkPolicy`, `runAsNonRoot: true` (20 occorrenze), `seccompProfile: RuntimeDefault`
- `infra/k3d/ci-config.yaml`: configurazione k3d 1-server, traefik disabled
- `.github/workflows/helm-smoke-test.yml`: trigger su `pull_request` + `push: main` per `infra/helm/**`; usa `AbsaOSS/k3d-action@v2`; installa SealedSecrets controller PRIMA dell'umbrella (Pitfall 5); esegue lint → dry-run → install → kubectl wait → helm test
- NetworkPolicy data-diode ot-bridge: `egress ALLOW NATS:4222+DNS; ingress ALLOW component=simulator; component=agent DENY by absence`

Nota: k3d usa flannel CNI che NON enforce NetworkPolicy — test funzionale con Calico rinviato a Fase 11 (SEC-06). Questo è comportamento documentato e atteso.

Pendente (human-needed): esecuzione del workflow helm-smoke-test su GitHub Actions.

---

## Artifact Verification (Level 1-3)

### Required Artifacts

| Artifact | Status | Evidence |
|----------|--------|----------|
| `nx.json` | VERIFIED | Esiste, contiene `@nxlv/python`; `@nx/angular/plugin` |
| `package.json` (root) | VERIFIED | `"nx": "20.8.4"`, `"@nxlv/python": "21.3.1"` |
| `pyproject.toml` (root) | VERIFIED | `[tool.uv.workspace]` + 23 members + `[dependency-groups]` PEP 735 |
| `uv.lock` | VERIFIED | 480 righe, generato da `uv sync --all-packages` |
| `infra/compose/core.yml` | VERIFIED | TimescaleDB, Redis, Qdrant con healthcheck |
| `infra/compose/obs.yml` | VERIFIED | Langfuse v3 stack completo; catena `depends_on: service_healthy` |
| `infra/compose/sim.yml` | VERIFIED | NATS 2.10-alpine con `-js` JetStream; healthcheck `/healthz` |
| `infra/compose/llm-cpu.yml` | VERIFIED | Ollama 0.6.0 CPU-only; healthcheck `/api/tags` |
| `infra/compose/llm-gpu.yml` | VERIFIED | Ollama 0.6.0 + NVIDIA device reservation |
| `infra/compose/.env.example` | VERIFIED | Nessun secret in plaintext; commenti `openssl rand -hex 32` |
| `Makefile` | VERIFIED | 16 target su .PHONY; `make up` usa `--wait` |
| `LICENSE` | VERIFIED | Apache License 2.0 con copyright 2026 Federico Calo |
| `LICENSE-EXCEPTIONS.md` | VERIFIED | Eccezione MinIO AGPL-3.0 documentata |
| `infra/license/trivy.yaml` | VERIFIED | Sezione `forbidden` con GPL/AGPL/SSPL/BUSL |
| `.github/workflows/license-scan.yml` | VERIFIED | Syft+Trivy; SBOM retention 90gg; PR comment; blocco finale |
| `.github/workflows/test-license-fixture.yml` | VERIFIED | Meta-test con assertion `outcome == failure` |
| `tests/license/fixture-gpl-pyproject.toml` | VERIFIED | GPL-3.0-only dichiarato + pyreadline3 GPL-2.0 |
| `.pre-commit-config.yaml` | VERIFIED | 5 rev pinnate; 7 hook ordinati; mypy scoped |
| `.gitleaks.toml` | VERIFIED | useDefault=true; allowlist per fixture noti |
| `.commitlintrc.cjs` | VERIFIED | 11 tipi; scope kebab-case; header-max 100 |
| `.github/workflows/pre-commit-check.yml` | VERIFIED | pre-commit/action@v3.0.1; mirror CI identico |
| `.github/workflows/ci.yml` | VERIFIED | nrwl/nx-set-shas@v4; fallback-sha; validate-nx-graph gate; 3 step nx affected |
| `scripts/validate-nx-graph.py` | VERIFIED | REQUIRED_EDGES con 5 coppie Python-TS |
| `infra/helm/charts/api-gateway/` | VERIFIED | Deployment+Service+HPA+PDB+NetworkPolicy+Ingress+SA+RBAC |
| `infra/helm/charts/ot-bridge/templates/networkpolicy.yaml` | VERIFIED | Data-diode: egress NATS+DNS; ingress simulator only |
| `infra/helm/sft-stack/Chart.yaml` | VERIFIED | 8 chart locali + 5 upstream con conditions |
| `infra/helm/sft-stack/Chart.lock` | VERIFIED | postgresql 16.7.27, qdrant 1.18.0, nats 1.3.16, langfuse 1.5.30 |
| `.github/workflows/helm-smoke-test.yml` | VERIFIED | AbsaOSS/k3d-action@v2; SealedSecrets before umbrella |
| `infra/k3d/ci-config.yaml` | VERIFIED | 1 server, traefik+metrics-server disabled |
| `docs/mkdocs.yml` | VERIFIED | Plugin i18n folder-based; IT default; EN secondario |
| `docs/requirements.txt` | VERIFIED | mkdocs-material==9.7.6; mkdocs-static-i18n==1.3.1 pinnate |
| `.github/workflows/docs-deploy.yml` | VERIFIED | `mkdocs gh-deploy`; push a main; paths filter |
| `.changeset/config.json` | VERIFIED | `linked: [sft-agents, sft-domain, sft-contracts]`; baseBranch: main |
| `.github/workflows/release.yml` | VERIFIED | changesets/action@v1; permissions minimali |
| `scripts/sync-python-versions.py` | VERIFIED | Sync package.json → __version__.py + pyproject.toml |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `ci.yml` | `validate-nx-graph.py` | step `python3 scripts/validate-nx-graph.py` | WIRED |
| `ci.yml` | `nx affected` | step con `nrwl/nx-set-shas@v4` → `$NX_BASE/$NX_HEAD` | WIRED |
| `license-scan.yml` | `infra/license/trivy.yaml` | `trivy-config: infra/license/trivy.yaml` | WIRED |
| `license-scan.yml` | SBOM → PR comment | `actions/github-script@v7` con `body: report_content` | WIRED |
| `test-license-fixture.yml` | `tests/license/fixture-gpl-pyproject.toml` | `syft tests/license/fixture-gpl-pyproject.toml` | WIRED |
| `pre-commit-check.yml` | `.pre-commit-config.yaml` | `pre-commit/action@v3.0.1` con stessa config | WIRED |
| `helm-smoke-test.yml` | `infra/helm/sft-stack/` | `helm install ... infra/helm/sft-stack/` | WIRED |
| `helm-smoke-test.yml` | `infra/k3d/ci-config.yaml` | `--config infra/k3d/ci-config.yaml` | WIRED |
| `docs-deploy.yml` | `docs/mkdocs.yml` | `mkdocs build --strict` in `docs/` | WIRED |
| `release.yml` | `scripts/sync-python-versions.py` | `npm run version-packages` → `python3 scripts/sync-python-versions.py` | WIRED |
| `Makefile up` | compose files | `docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) up -d --wait` | WIRED |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `infra/helm/sft-stack/values-ci.yaml` | `# PLACEHOLDER NGINX PER SMOKE TEST` | INFO | Intenzionale — nginx:1.27-alpine placeholder per CI senza immagini applicative. Non bloccante. |
| `infra/helm/sft-stack/templates/sealed-secrets-example.yaml` | `# NOTA: il valore ... è un PLACEHOLDER` | INFO | Intenzionale — file di esempio SealedSecrets. Non è codice live. |
| `.github/workflows/license-scan.yml` | `anchore/sbom-action/download-syft@v0` — major-version floating | WARNING | `@v0` è un major-version pin, non un SHA fisso. Aggiornamenti breaking in v0.x potrebbero rompere il workflow senza preavviso. Considerare il pin a SHA specifico. |
| `.github/workflows/release.yml` | `changesets/action@v1` — major-version floating | WARNING | `@v1` è un major-version pin. Standard nella community changesets ma tecnicamente floating. |
| `infra/compose/obs.yml` | `cgr.dev/chainguard/minio:latest` | WARNING (documentato) | AGPL-3.0; `:latest` su registry chainguard è SHA-immutabile (comportamento documentato in SUMMARY). Eccezione in `LICENSE-EXCEPTIONS.md`. |

**Nota:** Nessun TBD/FIXME/XXX non referenziato trovato nei file di implementazione. I due warning di version pinning sono comuni nella community GitHub Actions e non bloccano il goal della fase.

**Nota su stubs intenzionali:** 23 package Python hanno `__init__.py` con solo `__version__ = "0.1.0"`. Questi sono stub **esplicitamente documentati** con fase di risoluzione (Fase 3-9). Non sono anti-pattern in questo contesto.

---

## Commit Verification

Tutti i 18 commit documentati nelle SUMMARY dei piani sono stati verificati in `git log`:

| Piano | Commit | Presenza |
|-------|--------|----------|
| 01-01 | 59078e1, 4516180, d359724, c260111, b8be5a4, 0c0fba8 | TUTTI PRESENTI |
| 01-02 | c0152a4, 27d7f19, 7eef480 | TUTTI PRESENTI |
| 01-03 | cee0d83, caa8020, 8e5d4b1 | TUTTI PRESENTI |
| 01-04 | 47bede0, 2361c61 | TUTTI PRESENTI |
| 01-05 | 68d1ea3, e7f256f | TUTTI PRESENTI |
| 01-06 | f995c70, c9018a8, de02c21 | TUTTI PRESENTI |
| 01-07 | 33e6f80, b5b47bf | TUTTI PRESENTI |
| 01-08 | 1984e6c, 89933bd | TUTTI PRESENTI |

---

## Quality Gates Check

### Pinning versioni esatto — Workflow GitHub Actions

| Workflow | Actions usate | Floating? |
|----------|--------------|-----------|
| ci.yml | checkout@v4, setup-node@v4, setup-python@v5, setup-uv@v5, cache@v4, nx-set-shas@v4 | No (major-version, standard GHA) |
| license-scan.yml | checkout@v4, sbom-action/download-syft@**v0**, trivy-action@0.24.0, upload-artifact@v4, github-script@v7 | sbom @v0 = WARNING |
| pre-commit-check.yml | checkout@v4, setup-node@v4, setup-python@v5, setup-uv@v5, pre-commit/action@v3.0.1 | No |
| helm-smoke-test.yml | checkout@v4, setup-helm@v4, k3d-action@v2 | No |
| docs-deploy.yml | checkout@v4, setup-python@v5 | No |
| release.yml | checkout@v4, setup-node@v4, setup-python@v5, changesets/action@**v1** | @v1 = WARNING |

**Verdetto pinning:** Nessun `@master`, `@main`, `@HEAD` trovato. I due WARNING su `@v0` e `@v1` sono major-version pins — tecnicamente floating ma accettabili per le community policies di questi tool. Nessun BLOCKER.

### No `:latest` nei compose file principali

- `core.yml`, `sim.yml`, `llm-cpu.yml`, `llm-gpu.yml`: ZERO tag `:latest` — PASS
- `obs.yml`: `cgr.dev/chainguard/minio:latest` documentato come eccezione (SHA-immutabile in chainguard registry) — DOCUMENTED

---

## Human Verification Required

### 1. Stack Docker Compose Avvio

**Test:** `cp infra/compose/.env.example .env && make up`
**Expected:** Tutti i container healthy entro 180s; `curl -sf http://localhost:6333/healthz` (Qdrant), `http://localhost:8222/healthz` (NATS), `http://localhost:11434/api/tags` (Ollama), `http://localhost:3000/api/public/health` (Langfuse) rispondono con 2xx
**Perche' human:** Richiede Docker Engine attivo. Non verificabile staticamente — test di integrazione runtime.

### 2. Pre-commit Hooks Funzionali

**Test:** `pip install pre-commit==4.6.0 && pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg && pre-commit run --all-files`
**Expected:** Exit 0 su repo pulito; poi: aggiungere `import os` in un file Python → ruff F401 blocca; commit con messaggio invalido → commitlint blocca; file con secret finto → gitleaks blocca
**Perche' human:** Richiede installazione locale di pre-commit, ruff, mypy, node, eslint. Non eseguibile in analisi statica.

### 3. License Scanner PR Gate

**Test:** Aprire una PR che include `tests/license/fixture-gpl-pyproject.toml` o una dipendenza GPL nel workspace uv
**Expected:** Il workflow `license-scan / license-scan` fallisce con exit code 1; la PR mostra il check rosso; il PR comment mostra il report licenze
**Perche' human:** Richiede repository GitHub attivo con Actions runner.

### 4. Branch Protection Configuration

**Test:** Seguire `docs/operations/branch-protection.md` per configurare branch protection su `main`
**Expected:** I 4 required checks sono listati: `license-scan / license-scan`, `pre-commit-check / pre-commit`, `ci / main`, `helm-smoke-test / helm-test`; una PR senza CI green non può essere mergiata
**Perche' human:** Richiede accesso admin al repository GitHub. Non verificabile staticamente.

### 5. Helm Smoke Test su k3d

**Test:** Aprire una PR che tocchi `infra/helm/**` (o aspettare la prima PR) e verificare che `helm-smoke-test.yml` passi
**Expected:** `helm lint` 9/9 PASS; `helm dependency update` PASS; `helm install --dry-run` PASS; `helm install` + `kubectl wait` PASS; `helm test` PASS
**Perche' human:** Richiede k3d installato o GitHub Actions runner. Non verificabile localmente senza cluster.

### 6. GitHub Pages e Documentazione Bilingue

**Test:** Configurare `Settings > Pages > Source: gh-pages branch`; poi fare un push su `main` che tocchi `docs/`
**Expected:** Sito pubblicato su `https://fedcal.github.io/Smart-Factory-Transformation`; selettore lingua IT/EN navigabile; pagine index, getting-started, architecture/overview, contributing/index presenti in entrambe le lingue
**Perche' human:** Richiede configurazione manuale GitHub Pages e primo deploy. Non verificabile staticamente.

---

## Risk and Open Issues

| Rischio | Severita | Mitigazione esistente | Note |
|---------|----------|----------------------|------|
| `anchore/sbom-action/download-syft@v0` floating major-version | BASSA | Anchore è vendor trustato; v0.x ha storia lunga | Considerare pin a SHA specifico in futuro |
| `changesets/action@v1` floating major-version | BASSA | Pattern standard changesets community | Accettabile per v1 |
| `cgr.dev/chainguard/minio:latest` AGPL + `:latest` | BASSA | Eccezione documentata in LICENSE-EXCEPTIONS.md; chainguard usa SHA immutabili | Documentato esplicitamente |
| k3d flannel NON enforce NetworkPolicy | MEDIO | NetworkPolicy data-diode ot-bridge esiste e ha sintassi corretta; test funzionale rinviato a Fase 11 (SEC-06) | Gap atteso e documentato |
| OBS-01 SDK wiring assente | BASSA | Langfuse container presente; SDK wiring rinviato esplicitamente a Fase 11 | Gap atteso e documentato |
| Langfuse tag `langfuse/langfuse:3` floating major | BASSA | Upstream Langfuse usa major tag come policy; no minor pinning disponibile | Accettabile per dev stack |
| GitHub Pages non configurato | MEDIO | Istruzioni dettagliate in SUMMARY e docs; zero codice necessario | Pura configurazione manuale da fare una tantum |

---

## Cross-Plan Integration Check

### Makefile: integrita' attraverso 4 piani (01-02, 01-03, 01-06, 01-07)

| Piano | Target aggiunto/modificato | Stato finale |
|-------|---------------------------|-------------|
| 01-02 | up, up-gpu, up-core, down, reset, ps, logs, test, lint, format, demo, sbom (stub) | OK |
| 01-03 | sbom (implementato), license-scan (nuovo) | OK — sbom stub sostituito con implementazione |
| 01-06 | helm-test (da placeholder a comandi reali) | OK — stub sostituito |
| 01-07 | docs, docs-serve | OK — docs target aggiornato con --strict |

Makefile finale ha 16 target su `.PHONY`. Nessuna regressione rilevata.

### Package.json: integrita' attraverso 2 piani (01-01, 01-04)

| Piano | Modifiche | Stato finale |
|-------|-----------|-------------|
| 01-01 | Versioni nx, @nxlv/python, @nx/angular e tutti @nx/* | OK |
| 01-04 | Aggiunto @commitlint/cli@19.5.0, @commitlint/config-conventional@19.5.0 | OK — additive change |

Nessuna regressione di versioni tra i piani.

---

## Deviazioni Documentate Rilevanti

Tutte le deviazioni riportate nelle SUMMARY sono classificate correttamente e non costituiscono gap:

- **Plan 01-01:** @nx/angular 20.8.4 (non 20.8.1) — corretta allineamento; uv dev-dependencies → [dependency-groups] PEP 735
- **Plan 01-02:** `make up-core` aggiunto (extra utile); MinIO healthcheck via curl (non mc)
- **Plan 01-03:** Target `license-scan` aggiunto (enhancement rispetto al piano); fixture GPL con doppia copertura
- **Plan 01-04:** alessandrojcm vs opensource-nepal commitlint hook — scelta deliberata e documentata
- **Plan 01-05:** `--configuration=ci` aggiunto (corretto per code coverage); `.gitkeep` con `-f`
- **Plan 01-06:** Piano eseguito esattamente come scritto — zero deviazioni
- **Plan 01-07:** Piano eseguito esattamente come scritto — zero deviazioni
- **Plan 01-08:** .gitignore negation per initial-phase-1.md; sync-python-versions.py esteso

---

## Recommendation

**Procedere a Fase 2 dopo completamento delle 6 verifiche human-needed.**

Le verifiche runtime non bloccano la transizione alla Fase 2 (Documentation & Domain Analysis) perche':
1. La struttura infrastrutturale e CI sono complete e corrette staticamente
2. La Fase 2 non dipende da Docker runtime o da GitHub Actions live
3. Le verifiche human-needed possono essere eseguite in parallelo all'avvio della Fase 2

**Priorita' delle verifiche human-needed:**
1. (Alta) Branch protection + required checks — blocca la qualita' delle PR future
2. (Alta) Pre-commit run --all-files — abilita i quality gate locali
3. (Media) `make up` — necessario per qualsiasi sviluppo che usa le dipendenze runtime
4. (Media) License scanner PR test — validare il gate prima della prima PR di contenuto
5. (Bassa) Helm smoke test — si auto-verifica alla prima PR che tocca infra/helm/
6. (Bassa) GitHub Pages — necessario per la documentazione ma non per lo sviluppo

---

_Verified: 2026-05-16T20:21:00Z_
_Verifier: Claude (gsd-verifier)_
