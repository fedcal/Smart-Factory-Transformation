# Phase 1: Foundation & Monorepo - Research

**Researched:** 2026-05-16
**Domain:** Nx polyglot monorepo (Python + Angular), Docker Compose multi-stack, GitHub Actions CI, license scanner SBOM, pre-commit, Helm skeleton, MkDocs i18n, Changesets
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Monorepo Layout & Naming (D-01 to D-06)**
- D-01: 6 root-folder: `apps/`, `packages/`, `services/`, `docs/`, `infra/`, `simulators/`
- D-02: `packages/sft-agents/` (SDK) e `packages/sft-domain/` (dominio tessile) come package separati
- D-03: Agenti come app deployabili sotto `apps/agents/{ops,maintenance,knowledge,supply}/{agent-name}/`; supervisor li chiama via RPC/NATS, non import diretto
- D-04: `packages/sft-contracts/` come single source of truth Pydantic + TypeScript; build target Nx genera OpenAPI JSON e tipi TS in `dist/ts/`
- D-05: Naming kebab-case con prefisso area: `sft-*`, `ops-*`, `mnt-*`, `trn-*`, `scm-*`, `ui-*`, `svc-*`, `sim-*`, `infra-*`
- D-06: `apps/orchestrator/` nome Nx `svc-orchestrator`

**Docker Compose Dev Stack (D-07 to D-11)**
- D-07: Split in 4 file: `infra/compose/core.yml`, `infra/compose/llm-cpu.yml` / `llm-gpu.yml`, `infra/compose/obs.yml`, `infra/compose/sim.yml`; Qdrant in `core.yml`
- D-08: Due overlay LLM: `llm-gpu.yml` (Ollama con NVIDIA) e `llm-cpu.yml` (Ollama CPU-only); `make up` di default usa `llm-cpu.yml`; `make up-gpu` usa `llm-gpu.yml`
- D-09: Persistenza via named volumes (non bind mount); `make reset` = `docker compose down -v && make up`
- D-10: Healthchecks nativi Docker Compose per ogni servizio; `depends_on: condition: service_healthy`
- D-11: `.env.example` documentato in `infra/compose/`

**License Scanner (D-12 to D-15)**
- D-12: Syft (generazione SBOM CycloneDX) + Grype o Trivy; una pipeline copre deps Python+JS e immagini container
- D-13: Allowlist esplicita: `MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, PSF-2.0, Unlicense, CC0-1.0, Python-2.0`; eccezioni in `LICENSE-EXCEPTIONS.md`
- D-14: MinIO (AGPL-3.0) entra immediatamente in `LICENSE-EXCEPTIONS.md` con motivazione
- D-15: CI GitHub Actions dedicata `license-scan.yml`; required status check; SBOM artifact 90 giorni; PR comment con diff licenze

**Helm Chart Skeleton (D-16 to D-20)**
- D-16: Chart per-servizio in `infra/helm/charts/` + umbrella `infra/helm/sft-stack/` con deps upstream
- D-17: Skeleton production-ready: HPA, PDB, NetworkPolicy, Ingress, resource limits, ServiceAccount, RBAC, PodSecurityContext `runAsNonRoot: true`
- D-18: NetworkPolicy data-diode OT in `svc-ot-bridge`: egress verso NATS consentito, nessun ingress dal layer agenti verso `sim-textile`
- D-19: Secret management = SealedSecrets (Bitnami); secrets cifrati con chiave cluster e committati come CRD
- D-20: Ingress controller = ingress-nginx; smoke test CI con k3d

### Claude's Discretion

- **uv workspace**: single root `pyproject.toml` con `[tool.uv.workspace]`, lockfile unico `uv.lock`, cache CI via `actions/cache` su `~/.cache/uv`
- **Task runner**: Makefile (comandi: `make up`, `make up-gpu`, `make down`, `make reset`, `make test`, `make lint`, `make format`, `make docs`, `make demo`, `make sbom`, `make helm-test`)
- **Versioning**: Changesets (`@changesets/cli`) per monorepo polyglot; emette `__version__.py` + tag + GH Release per `sft-agents`; PyPI rinviato
- **Nx Cloud**: disabilitato per default; abilitabile via `NX_CLOUD_ACCESS_TOKEN`
- **Pre-commit**: `pre-commit` framework con ruff, mypy --strict (solo `packages/sft-*`), eslint, prettier, commitlint, gitleaks
- **GitHub Actions**: `ci.yml`, `pre-commit-check.yml`, `license-scan.yml`, `helm-smoke-test.yml`, `docs-deploy.yml`
- **Python toolchain**: Python 3.12 pinned, no matrix multi-versione
- **Docs Fase 1**: struttura MkDocs Material vuota + i18n + GitHub Pages deploy funzionante

### Deferred Ideas (OUT OF SCOPE)

- External Secrets Operator + Vault
- Cloud Ingress overlays (AWS App Gateway, Azure App Gateway)
- Nx Cloud paid tier
- Garage / SeaweedFS come alternativa a MinIO
- PyPI publish automatico per `sft-agents`
- Multi-version Python matrix in CI (3.12 + 3.13)
- Just (justfile) al posto di Make
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLAT-01 | Monorepo Nx con plugin `@nxlv/python` e supporto Angular first-class | Sezione 1: Nx 20.x bootstrap, `@nxlv/python` 21.x generator |
| PLAT-02 | Workspace polyglot con uv per Python e pnpm/Nx per TypeScript/Angular | Sezione 2: uv workspace config, `[tool.uv.workspace]` root pyproject.toml |
| PLAT-03 | Struttura `apps/`, `packages/`, `services/`, `docs/`, `infra/`, `simulators/` | Sezione Architecture Patterns: project structure |
| PLAT-04 | GitHub Actions con `nx affected` per build/test/lint selettivi | Sezione 6: `ci.yml` con `nrwl/nx-set-shas@v4` |
| PLAT-05 | Pipeline CI con license scanner che blocca dipendenze incompatibili | Sezione 4: Syft + Trivy, `license-scan.yml` |
| PLAT-06 | Pre-commit hooks (ruff, mypy strict, eslint, prettier) eseguiti in CI | Sezione 5: `.pre-commit-config.yaml`, `pre-commit-check.yml` |
| PLAT-07 | Docker Compose per dev locale con PostgreSQL+TimescaleDB, Qdrant, NATS, Ollama, Langfuse | Sezione 3: Docker Compose multi-file layout |
| PLAT-08 | Helm chart skeleton per deploy prod on-premise | Sezione 7: umbrella + per-service charts, k3d smoke test |
| PLAT-09 | Makefile con comandi standard (`make up`, `make test`, `make docs`, `make demo`) | Sezione Claude's Discretion: Makefile entry points |
| PLAT-10 | Versionamento semantico con Changesets | Sezione 9: Changesets polyglot setup |
| OBS-01 | Langfuse self-hosted v3 (Docker Compose dev + Helm prod) come traces backend | Sezione 3: obs.yml con Langfuse v3 stack |
</phase_requirements>

---

## Summary

La Fase 1 è la fondazione tecnica dell'intero progetto. Il suo scopo è abilitare ogni fase successiva: senza workspace Nx funzionante, CI selettiva, Docker Compose healthy e pre-commit enforced, nessuna iterazione di sviluppo successiva può essere efficiente. Il dominio tecnico coperto è infrastrutturale (non applicativo), ma le decisioni prese qui — naming conventions, layout di cartelle, topologia Docker, struttura Helm — sono costose da cambiare retroattivamente.

La ricerca ha identificato cinque aree di complessità tecnica reale: (1) la configurazione polylgot di Nx con `@nxlv/python` richiede dichiarazione esplicita delle dipendenze Python→TypeScript che non avviene automaticamente; (2) il workspace uv con glob nidificati multipli (`apps/agents/*/*`) richiede attenzione all'uso di pattern glob vs. path espliciti; (3) Langfuse v3 richiede ClickHouse 24.3+, MinIO e Redis dedicati — non condivisi con lo stack core — con ordine di boot critico (`clickhouse` healthy prima di `langfuse-web`); (4) il license scanner SBOM-based funziona meglio con Trivy (che ha policy file nativa per licenze) rispetto a Grype (che è vulnerability scanner, non license scanner); (5) il primo commit in un repository nuovo e i merge squash causano comportamenti edge-case di `nrwl/nx-set-shas@v4` che richiedono configurazione esplicita di `fallback-sha`.

**Raccomandazione primaria:** Usare Trivy (non Grype) per la license policy enforcement — Trivy ha `trivy.yaml` con `license.forbidden` nativo per GPL/AGPL. Syft genera l'SBOM CycloneDX, Trivy scansiona l'SBOM per licenze. Questa pipeline copre sia deps Python/JS sia immagini container.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Monorepo build graph | Build System (Nx) | — | Nx dep graph determina quali progetti rebuilda nx affected |
| Python dep management | Package Manager (uv) | Nx executor | uv risolve deps; @nxlv/python lo integra come Nx executor |
| TypeScript dep management | Package Manager (npm/pnpm) | Nx | npm gestisce node_modules; Nx cache artifact |
| Dev service orchestration | Docker Compose | — | `make up` avvia tutti i servizi; Compose gestisce network, healthcheck, depends_on |
| Kubernetes production deploy | Helm | k3d (CI test) | Chart per-servizio + umbrella; k3d per smoke test in GitHub Actions |
| License compliance enforcement | CI (GitHub Actions) | Pre-commit (local) | `license-scan.yml` come required check blocca PR; pre-commit per feedback locale rapido |
| Secret management (k8s) | SealedSecrets controller | kubeseal CLI | Controller decripta in cluster; kubeseal cifra localmente con chiave pubblica cluster |
| Commit quality enforcement | Pre-commit hooks | CI (pre-commit-check.yml) | Hooks locali per feedback immediato; CI come fallback required check |
| Documentation build | MkDocs (static build) | GitHub Actions (deploy) | Build locale via `make docs`; Actions deploy su gh-pages |
| Release versioning | Changesets | GitHub Actions (release workflow) | Changesets gestisce CHANGELOG e bump; Actions crea GitHub Release + tag |

---

## Standard Stack

### Core (Versioni verificate su npm/PyPI registry 2026-05-16)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nx | 20.8.4 (latest 20.x) | Monorepo orchestrator, affected commands, dep graph | Unico strumento maturo polyglot Python+Angular con cache e dep graph |
| @nxlv/python | 21.3.1 (latest 21.x) | Plugin Nx per Python con uv workspace | Unico plugin che integra uv workspaces in Nx affected e dep graph |
| @nx/angular | 22.7.2 (attuale, usa pinning major 20 per Nx 20 workspace) | Generator Angular app + SSR | First-class Angular support in Nx; generator `setup-ssr` |
| create-nx-workspace | 22.7.2 (usa `@latest` con `--nxVersion=20`) | Bootstrap workspace | CLI ufficiale per creare workspace Nx |
| @changesets/cli | 2.31.0 | Versioning semantico polyglot | Standard de facto per monorepo con changelog e GitHub Release |
| pre-commit | 4.6.0 (PyPI) | Framework hook pre-commit | Standard Python; configurazione YAML versionata |
| mkdocs-material | 9.7.6 (PyPI) | Documentazione bilingue IT/EN | i18n built-in, GitHub Pages, Mermaid nativo |
| mkdocs-static-i18n | 1.3.1 (PyPI) | Internazionalizzazione IT/EN per MkDocs | Compatibile Material; language switcher automatico |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uv | 0.11.13 (disponibile in env; spec: 0.6+) | Python package manager workspace | Sostituisce pip/poetry in ogni project Python; workspace mode |
| syft | CLI binary (non PyPI) | Generazione SBOM CycloneDX/SPDX | Step 1 della pipeline license scan; output JSON/CycloneDX |
| trivy | CLI binary (non PyPI) | License policy enforcement su SBOM | Policy file nativa `trivy.yaml` con `license.forbidden`; integra SBOM di Syft |
| gitleaks | v8.24.2 (pre-commit hook) | Secret scanning su commit | Hook pre-commit; scansiona diff per API keys e credenziali |
| AbsaOSS/k3d-action | v2 (GitHub Action) | Cluster k3d in CI per Helm smoke test | k3d pronto in 20-30 secondi vs Kind (90s) vs Minikube (2min) |
| nrwl/nx-set-shas | v4 | Calcola base/head SHA per nx affected | Essenziale per CI selettiva su PR; gestisce squash merge e first commit |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Trivy (license) | Grype | Grype è vulnerability scanner, non license scanner; Trivy ha `license.forbidden` nativo |
| Trivy (license) | pip-licenses / license-checker | Questi coprono solo deps Python/JS rispettivamente; Trivy + Syft copre anche immagini container |
| mkdocs-static-i18n | mkdocs-i18n (ultrabug) | Entrambi validi; mkdocs-static-i18n ha supporto Material theme nativo con language switcher automatico |
| pre-commit | husky + lint-staged | pre-commit è tool Python universale; husky è Node.js only; in monorepo polyglot pre-commit copre entrambi gli ecosistemi |
| SealedSecrets | ESO + Vault | SealedSecrets è più semplice per single-tenant on-prem; ESO/Vault per multi-cluster (deferred) |

**Installation:**
```bash
# Nx workspace bootstrap
npx create-nx-workspace@latest smart-factory-transformation \
  --preset=empty \
  --packageManager=npm \
  --nxVersion=20

# Nx plugins
npm install -D @nxlv/python@21 @nx/angular@20 --legacy-peer-deps

# Changesets
npm install -D @changesets/cli

# Python tooling
pip install pre-commit mkdocs-material mkdocs-static-i18n

# Syft + Trivy: install via official scripts (not PyPI)
# curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh
# curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh
```

---

## Package Legitimacy Audit

> Nota: slopcheck v0.6.1 disponibile. Le query sui package npm (es. @nx/angular, @nxlv/python) hanno restituito falso-positivo SLOP perché slopcheck verifica di default su PyPI. La verifica corretta per npm è stata eseguita manualmente via `npm view`.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| nx (20.8.4) | npm | 10+ anni | 10M+/week | github.com/nrwl/nx | OK (npm verified) | Approvato |
| @nxlv/python (21.3.1) | npm | 3+ anni | 100K+/week | github.com/lucasvieirasilva/nx-plugins | OK (npm verified) | Approvato |
| @nx/angular (22.7.2) | npm | 10+ anni | 1M+/week | github.com/nrwl/nx | OK (npm verified) | Approvato |
| @changesets/cli (2.31.0) | npm | 5+ anni | 5M+/week | github.com/changesets/changesets | OK (npm verified) | Approvato |
| pre-commit (4.6.0) | PyPI | 10+ anni | 5M+/week | github.com/pre-commit/pre-commit | [OK] | Approvato |
| mkdocs-material (9.7.6) | PyPI | 8+ anni | 3M+/week | github.com/squidfunk/mkdocs-material | [OK] | Approvato |
| mkdocs-static-i18n (1.3.1) | PyPI | 3+ anni | 50K+/week | github.com/ultrabug/mkdocs-static-i18n | [OK] | Approvato |
| syft | GitHub Releases (binary) | 4+ anni | mainstream | github.com/anchore/syft | N/A (binary) | Approvato (anchore.com ufficiale) |
| trivy | GitHub Releases (binary) | 5+ anni | mainstream | github.com/aquasecurity/trivy | N/A (binary) | Approvato (aquasecurity.github.io ufficiale) |
| gitleaks (v8.24.2) | GitHub (pre-commit) | 5+ anni | mainstream | github.com/gitleaks/gitleaks | N/A (binary) | Approvato |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Developer / CI
     |
     | git commit / PR
     v
[GitHub Actions] -----> [pre-commit-check.yml] (required check)
     |              +--> [license-scan.yml]     (required check)
     |              +--> [ci.yml]               (nx affected, required check)
     |              +--> [helm-smoke-test.yml]  (required check)
     |              +--> [docs-deploy.yml]      (gh-pages deploy)
     |
     | make up
     v
[Docker Compose]
  core.yml ---------> postgres+timescale:16 (pg_isready healthcheck)
                 +--> qdrant:1.16            (/healthz healthcheck)
                 +--> redis:7               (redis-cli ping)
  obs.yml  ---------> clickhouse:24.3+      (wget /ping healthcheck)
                 +--> minio (chainguard)    (mc ready local)
                 +--> langfuse-pg:17        (pg_isready)
                 +--> langfuse-web:3        (depends: all healthy)
                 +--> langfuse-worker:3     (depends: all healthy)
  sim.yml  ---------> nats:2.10+           (/healthz healthcheck)
                 +--> [sim-textile placeholder]
  llm-cpu.yml ------> ollama              (/api/tags healthcheck)
  llm-gpu.yml ------> ollama+nvidia       (variante GPU)

     | make helm-test
     v
[k3d cluster in GitHub Actions]
  --> helm dependency update sft-stack/
  --> helm install --dry-run
  --> helm install sft-stack
  --> kubectl wait --for=condition=ready
  --> helm test
```

### Recommended Project Structure

```
smart-factory-transformation/
├── apps/
│   ├── agents/
│   │   ├── ops/
│   │   │   └── operator-assistant/    # Python app (ops-operator-assistant)
│   │   ├── maintenance/
│   │   ├── knowledge/
│   │   └── supply/
│   ├── orchestrator/                  # Python app (svc-orchestrator)
│   ├── api-gateway/                   # Python app (svc-api-gateway)
│   └── factory-ui/                    # Angular SSR app (ui-factory)
├── packages/
│   ├── sft-agents/                    # Python library (SDK)
│   ├── sft-domain/                    # Python library (textile domain)
│   └── sft-contracts/                 # Python + TS (Pydantic -> OpenAPI -> TS types)
├── services/
│   └── ot-bridge/                     # Python app (svc-ot-bridge)
├── docs/
│   ├── mkdocs.yml
│   ├── docs/                          # IT (default)
│   └── docs/en/                       # EN
├── infra/
│   ├── compose/
│   │   ├── core.yml
│   │   ├── obs.yml
│   │   ├── sim.yml
│   │   ├── llm-cpu.yml
│   │   ├── llm-gpu.yml
│   │   └── .env.example
│   └── helm/
│       ├── charts/
│       │   ├── api-gateway/
│       │   ├── ot-bridge/
│       │   ├── orchestrator/
│       │   ├── agents-ops/
│       │   ├── agents-mnt/
│       │   ├── agents-trn/
│       │   ├── agents-scm/
│       │   └── factory-ui/
│       └── sft-stack/                 # Umbrella chart
├── simulators/
│   └── sim-textile/                   # Placeholder Fase 3
├── LICENSE-EXCEPTIONS.md
├── pyproject.toml                     # uv workspace root
├── uv.lock
├── nx.json
├── package.json
├── .pre-commit-config.yaml
├── .changeset/
├── Makefile
└── .github/
    └── workflows/
        ├── ci.yml
        ├── pre-commit-check.yml
        ├── license-scan.yml
        ├── helm-smoke-test.yml
        └── docs-deploy.yml
```

### Pattern 1: Nx 20.x Polyglot Workspace Bootstrap

**Cosa:** Workspace Nx con preset empty, plugins `@nxlv/python` e `@nx/angular`, configurato per rilevare automaticamente il workspace uv dalla presenza di `uv.lock` a root.

**Quando:** Primo step di tutta la fase.

**Configurazione nx.json:**
```json
{
  "$schema": "./node_modules/nx/schemas/nx-schema.json",
  "defaultBase": "main",
  "plugins": [
    {
      "plugin": "@nxlv/python",
      "options": {
        "packageManager": "uv"
      }
    },
    "@nx/angular/plugin"
  ],
  "targetDefaults": {
    "build": { "cache": true, "dependsOn": ["^build"] },
    "test":  { "cache": true },
    "lint":  { "cache": true }
  },
  "namedInputs": {
    "default": ["{projectRoot}/**/*", "sharedGlobals"],
    "sharedGlobals": ["{workspaceRoot}/nx.json"]
  }
}
```

**Generator Python project (es. `sft-agents`):**
```bash
nx generate @nxlv/python:uv-project sft-agents \
  --projectType=library \
  --directory=packages/sft-agents \
  --srcDir \
  --buildSystem=uv \
  --unitTestRunner=pytest \
  --linter=ruff
```

**Generator Angular SSR app:**
```bash
nx generate @nx/angular:application factory-ui \
  --directory=apps/factory-ui \
  --routing \
  --standalone \
  --ssr
```

**Python -> TypeScript implicitDependencies (project.json di sft-contracts):**
```json
{
  "name": "sft-contracts",
  "targets": {
    "generate-ts": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "command": "python scripts/gen_openapi.py"
      }
    }
  },
  "implicitDependencies": []
}
```

Per dichiarare che `ui-factory` dipende da `sft-contracts` (Python):
```json
// apps/factory-ui/project.json
{
  "implicitDependencies": ["sft-contracts"]
}
```

Questo fa sì che `nx affected` rebuildi `ui-factory` quando `sft-contracts` cambia.

### Pattern 2: uv Workspace Root pyproject.toml

**Configurazione root `pyproject.toml`:**
```toml
[project]
name = "smart-factory-transformation"
version = "0.0.0"
requires-python = ">=3.12"

[tool.uv.workspace]
members = [
  "packages/sft-agents",
  "packages/sft-domain",
  "packages/sft-contracts",
  "apps/orchestrator",
  "apps/api-gateway",
  "apps/agents/ops/*",
  "apps/agents/maintenance/*",
  "apps/agents/knowledge/*",
  "apps/agents/supply/*",
  "services/ot-bridge",
  "simulators/sim-textile",
]

[tool.uv]
dev-dependencies = [
  "pre-commit>=4.6",
  "pytest>=8.0",
  "pytest-asyncio>=0.24",
]
```

**Nota importante:** ogni directory inclusa dal glob members DEVE contenere un `pyproject.toml`. In Fase 1 i placeholder degli agenti sotto `apps/agents/` avranno un `pyproject.toml` minimale.

**Cache CI:**
```yaml
- name: Cache uv
  uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
    restore-keys: uv-${{ runner.os }}-
```

### Pattern 3: Docker Compose Multi-Stack con Healthchecks

**`infra/compose/core.yml`:**
```yaml
services:
  postgres:
    image: timescale/timescaledb:2.18.0-pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-sft}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-sft_dev_pass}
      POSTGRES_DB: ${POSTGRES_DB:-sft}
    volumes:
      - pg-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-sft}"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 3s
      retries: 10

  qdrant:
    image: qdrant/qdrant:v1.16.1
    volumes:
      - qdrant-data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:6333/healthz | grep -q ok"]
      interval: 5s
      retries: 10

volumes:
  pg-data:
  redis-data:
  qdrant-data:
```

**`infra/compose/obs.yml` (Langfuse v3 stack):**
```yaml
# IMPORTANTE: ordine boot = clickhouse healthy -> minio healthy -> redis healthy -> langfuse-web
services:
  langfuse-pg:
    image: postgres:17
    environment:
      POSTGRES_USER: ${LANGFUSE_PG_USER:-langfuse}
      POSTGRES_PASSWORD: ${LANGFUSE_PG_PASSWORD:-langfuse_pass}
      POSTGRES_DB: ${LANGFUSE_PG_DB:-langfuse}
    volumes:
      - langfuse-pg-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${LANGFUSE_PG_USER:-langfuse}"]
      interval: 3s
      retries: 10

  clickhouse:
    image: clickhouse/clickhouse-server:24.3-alpine
    environment:
      CLICKHOUSE_DB: ${CLICKHOUSE_DB:-langfuse}
      CLICKHOUSE_USER: ${CLICKHOUSE_USER:-langfuse}
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-langfuse_ch_pass}
    volumes:
      - langfuse-clickhouse-data:/var/lib/clickhouse
      - langfuse-clickhouse-logs:/var/log/clickhouse-server
    ports:
      - "8123:8123"
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:8123/ping"]
      interval: 5s
      retries: 10

  minio:
    image: cgr.dev/chainguard/minio:latest
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-langfuse}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-langfuse_minio_pass}
    volumes:
      - langfuse-minio-data:/data
    ports:
      - "9090:9000"
    healthcheck:
      test: ["CMD-SHELL", "mc ready local"]
      interval: 1s
      retries: 5

  langfuse-redis:
    image: redis:7-alpine
    volumes:
      - langfuse-redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      retries: 10

  langfuse-web:
    image: langfuse/langfuse:3
    environment:
      DATABASE_URL: postgresql://${LANGFUSE_PG_USER:-langfuse}:${LANGFUSE_PG_PASSWORD:-langfuse_pass}@langfuse-pg:5432/${LANGFUSE_PG_DB:-langfuse}
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET:-change_me_in_prod}
      SALT: ${LANGFUSE_SALT:-change_me_in_prod}
      ENCRYPTION_KEY: ${LANGFUSE_ENCRYPTION_KEY:-0000000000000000000000000000000000000000000000000000000000000000}
      CLICKHOUSE_URL: http://clickhouse:8123
      CLICKHOUSE_USER: ${CLICKHOUSE_USER:-langfuse}
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-langfuse_ch_pass}
      REDIS_HOST: langfuse-redis
      LANGFUSE_S3_MEDIA_UPLOAD_BUCKET: langfuse
      LANGFUSE_S3_EVENT_UPLOAD_BUCKET: langfuse
    ports:
      - "3000:3000"
    depends_on:
      langfuse-pg:    { condition: service_healthy }
      clickhouse:     { condition: service_healthy }
      minio:          { condition: service_healthy }
      langfuse-redis: { condition: service_healthy }

  langfuse-worker:
    image: langfuse/langfuse-worker:3
    environment:
      DATABASE_URL: postgresql://${LANGFUSE_PG_USER:-langfuse}:${LANGFUSE_PG_PASSWORD:-langfuse_pass}@langfuse-pg:5432/${LANGFUSE_PG_DB:-langfuse}
      SALT: ${LANGFUSE_SALT:-change_me_in_prod}
      ENCRYPTION_KEY: ${LANGFUSE_ENCRYPTION_KEY:-0000000000000000000000000000000000000000000000000000000000000000}
      CLICKHOUSE_URL: http://clickhouse:8123
      CLICKHOUSE_USER: ${CLICKHOUSE_USER:-langfuse}
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-langfuse_ch_pass}
      REDIS_HOST: langfuse-redis
      LANGFUSE_S3_EVENT_UPLOAD_BUCKET: langfuse
    depends_on:
      langfuse-pg:    { condition: service_healthy }
      clickhouse:     { condition: service_healthy }
      minio:          { condition: service_healthy }
      langfuse-redis: { condition: service_healthy }

volumes:
  langfuse-pg-data:
  langfuse-clickhouse-data:
  langfuse-clickhouse-logs:
  langfuse-minio-data:
  langfuse-redis-data:
```

**`infra/compose/sim.yml`:**
```yaml
services:
  nats:
    image: nats:2.10-alpine
    command: ["-js", "-m", "8222"]
    ports:
      - "4222:4222"
      - "8222:8222"
    volumes:
      - nats-data:/data
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8222/healthz | grep -q ok"]
      interval: 3s
      retries: 10

  # sim-textile placeholder - popolato in Fase 3
  # sim-textile:
  #   build: ../../simulators/sim-textile
  #   ...

volumes:
  nats-data:
```

**`infra/compose/llm-cpu.yml`:**
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    environment:
      OLLAMA_NUM_PARALLEL: "2"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:11434/api/tags | grep -q models"]
      interval: 10s
      retries: 12

volumes:
  ollama-models:
```

**Makefile `make up`:**
```makefile
COMPOSE_FILES := -f infra/compose/core.yml -f infra/compose/sim.yml \
                 -f infra/compose/obs.yml -f infra/compose/llm-cpu.yml

up:
	docker compose $(COMPOSE_FILES) up -d --wait

up-gpu:
	docker compose -f infra/compose/core.yml -f infra/compose/sim.yml \
	               -f infra/compose/obs.yml -f infra/compose/llm-gpu.yml \
	               up -d --wait

down:
	docker compose $(COMPOSE_FILES) down

reset:
	docker compose $(COMPOSE_FILES) down -v && $(MAKE) up
```

**Port matrix (`infra/compose/.env.example`):**
```bash
# Core services
POSTGRES_USER=sft
POSTGRES_PASSWORD=sft_dev_pass
POSTGRES_DB=sft
POSTGRES_PORT=5432

REDIS_PORT=6379

QDRANT_PORT=6333

# Langfuse obs stack (SEPARATO da core redis/postgres)
LANGFUSE_PG_USER=langfuse
LANGFUSE_PG_PASSWORD=langfuse_pass
LANGFUSE_PG_DB=langfuse
LANGFUSE_NEXTAUTH_SECRET=change_me_in_production_32chars
LANGFUSE_SALT=change_me_in_production_32chars
LANGFUSE_ENCRYPTION_KEY=0000000000000000000000000000000000000000000000000000000000000000
LANGFUSE_PORT=3000

CLICKHOUSE_DB=langfuse
CLICKHOUSE_USER=langfuse
CLICKHOUSE_PASSWORD=langfuse_ch_pass
CLICKHOUSE_PORT=8123

MINIO_ROOT_USER=langfuse
MINIO_ROOT_PASSWORD=langfuse_minio_pass
MINIO_PORT=9090

# NATS
NATS_PORT=4222
NATS_MONITORING_PORT=8222

# LLM
OLLAMA_PORT=11434
OLLAMA_MODEL_DEFAULT=qwen2.5:7b-instruct-q4_K_M
```

### Pattern 4: License Scanner (Syft + Trivy)

**`infra/license/trivy.yaml` (policy file versionato):**
```yaml
# Trivy license policy per SFT
# Categorie: notice (permissive), reciprocal (weak copyleft), restricted (strong copyleft), forbidden (AGPL/GPL)
license:
  # Licenze permesse senza restrizioni
  notice:
    - MIT
    - Apache-2.0
    - BSD-2-Clause
    - BSD-3-Clause
    - ISC
    - Unlicense
    - CC0-1.0
    - PSF-2.0
    - Python-2.0
    - 0BSD
  # Licenze copyleft debole - flagging con warning, non blocco
  reciprocal:
    - MPL-2.0
    - LGPL-2.1
    - LGPL-3.0
  # Licenze che bloccano la build
  forbidden:
    - GPL-1.0
    - GPL-2.0
    - GPL-3.0
    - GPL-2.0-only
    - GPL-3.0-only
    - GPL-2.0-or-later
    - GPL-3.0-or-later
    - AGPL-3.0
    - AGPL-3.0-only
    - AGPL-3.0-or-later
    - SSPL-1.0
    - BUSL-1.1
```

**`.github/workflows/license-scan.yml`:**
```yaml
name: License Scan (SBOM)
on:
  pull_request:
  push:
    branches: [main]

jobs:
  license-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - name: Install Syft
        uses: anchore/sbom-action/download-syft@v0

      - name: Install Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          exit-code: '0'  # non fallire qui, step separato per license
          format: 'table'

      - name: Generate SBOM (CycloneDX)
        run: |
          syft . --output cyclonedx-json=sbom.json
          syft . --output cyclonedx-json=sbom-src.json --source-name "sft-source"

      - name: Trivy license scan su SBOM
        id: license-check
        run: |
          trivy sbom sbom.json \
            --scanners license \
            --config infra/license/trivy.yaml \
            --format json \
            --output license-report.json \
            --exit-code 1 \
            --severity CRITICAL || FAILED=true

          # Genera report Markdown per PR comment
          trivy sbom sbom.json \
            --scanners license \
            --config infra/license/trivy.yaml \
            --format table > license-report.md 2>&1

          if [ "$FAILED" = "true" ]; then
            echo "license_failed=true" >> $GITHUB_OUTPUT
          fi

      - name: Upload SBOM artifact
        uses: actions/upload-artifact@v4
        with:
          name: sbom-cyclonedx
          path: sbom.json
          retention-days: 90

      - name: Comment PR with license diff
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('license-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## License Scan Report\n\n```\n' + report + '\n```'
            });

      - name: Fail se licenze vietate trovate
        if: steps.license-check.outputs.license_failed == 'true'
        run: exit 1
```

**`LICENSE-EXCEPTIONS.md` (da creare in Fase 1):**
```markdown
# License Exceptions

Packages explicitly approved for use despite being outside the standard allowlist.

| Package | Version | License | Reason | Approved Date | Approver |
|---------|---------|---------|--------|---------------|----------|
| minio | latest (container) | AGPL-3.0 | Usato as-is via container upstream come dipendenza di Langfuse v3. AGPL applica solo se si modifica il software. Usiamo MinIO senza modifiche in deploy single-tenant on-premise (no SaaS hosting, no public network service trigger). Compatibile con Apache-2.0 del progetto. | 2026-05-16 | Federico |
```

### Pattern 5: Pre-commit Configuration

**`.pre-commit-config.yaml`:**
```yaml
repos:
  # Python: ruff format
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.10
    hooks:
      - id: ruff-format
        types_or: [python, pyi]
      - id: ruff
        types_or: [python, pyi]
        args: [--fix]

  # Python: mypy strict (solo packages/sft-*)
  - repo: local
    hooks:
      - id: mypy-sft-packages
        name: mypy --strict (packages/sft-*)
        language: system
        entry: uv run mypy --strict
        types: [python]
        files: ^packages/sft-.*/
        pass_filenames: true

  # TypeScript/Angular: eslint
  - repo: local
    hooks:
      - id: eslint
        name: ESLint
        language: node
        entry: npx eslint --fix
        types_or: [ts, tsx]
        files: \.(ts|tsx)$

  # TypeScript/Angular: prettier
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.5.3
    hooks:
      - id: prettier
        types_or: [ts, tsx, json, yaml, markdown]
        exclude: ^(uv\.lock|package-lock\.json)$

  # Commit message: commitlint (Conventional Commits)
  - repo: https://github.com/opensource-nepal/commitlint
    rev: v1.3.0
    hooks:
      - id: commitlint
        stages: [commit-msg]

  # Secret scanning: gitleaks
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks
```

**`.github/workflows/pre-commit-check.yml`:**
```yaml
name: Pre-commit Check
on: [pull_request, push]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: pre-commit/action@v3.0.1
```

### Pattern 6: GitHub Actions CI (nx affected)

**`.github/workflows/ci.yml`:**
```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]

jobs:
  main:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # CRITICO: nrwl/nx-set-shas richiede full history

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
          # Se nessun run precedente trovato (primo commit), usa HEAD~1
          error-on-no-successful-workflow: false

      - name: Nx Affected Lint
        run: npx nx affected --target=lint --base=$NX_BASE --head=$NX_HEAD --parallel=3

      - name: Nx Affected Test
        run: npx nx affected --target=test --base=$NX_BASE --head=$NX_HEAD --parallel=3

      - name: Nx Affected Build
        run: npx nx affected --target=build --base=$NX_BASE --head=$NX_HEAD --parallel=3
```

### Pattern 7: Helm Umbrella Chart

**`infra/helm/sft-stack/Chart.yaml`:**
```yaml
apiVersion: v2
name: sft-stack
description: Smart Factory Transformation - Umbrella Chart
type: application
version: 0.1.0
appVersion: "0.1.0"
dependencies:
  # Charts interni (per-servizio)
  - name: api-gateway
    version: "0.1.0"
    repository: "file://../charts/api-gateway"
  - name: ot-bridge
    version: "0.1.0"
    repository: "file://../charts/ot-bridge"
  - name: orchestrator
    version: "0.1.0"
    repository: "file://../charts/orchestrator"
  - name: factory-ui
    version: "0.1.0"
    repository: "file://../charts/factory-ui"
  # Upstream charts
  - name: postgresql
    version: "16.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  - name: qdrant
    version: "1.x.x"
    repository: "https://qdrant.github.io/qdrant-helm"
    condition: qdrant.enabled
  - name: nats
    version: "1.x.x"
    repository: "https://nats-io.github.io/k8s/helm/charts/"
    condition: nats.enabled
  - name: ingress-nginx
    version: "4.x.x"
    repository: "https://kubernetes.github.io/ingress-nginx"
    condition: ingress-nginx.enabled
```

**Template NetworkPolicy data-diode per `infra/helm/charts/ot-bridge/templates/networkpolicy.yaml`:**
```yaml
{{- if .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "ot-bridge.fullname" . }}-data-diode
  labels: {{ include "ot-bridge.labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels: {{ include "ot-bridge.selectorLabels" . | nindent 6 }}
  policyTypes:
    - Ingress
    - Egress
  # EGRESS: ot-bridge può pubblicare su NATS
  egress:
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: nats
      ports:
        - protocol: TCP
          port: 4222
    # DNS resolution
    - to: []
      ports:
        - protocol: UDP
          port: 53
  # INGRESS: accetta connessioni solo dal simulatore OPC-UA (namespace sim-*)
  # Blocca esplicitamente connessioni dal layer agenti
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: simulator
      ports:
        - protocol: TCP
          port: 4840  # OPC-UA
  # Nessuna regola ingress per agenti -> agenti non possono raggiungere ot-bridge
{{- end }}
```

**Template PodSecurityContext standard per ogni chart:**
```yaml
# in templates/deployment.yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
```

**Smoke test Helm in CI (`.github/workflows/helm-smoke-test.yml`):**
```yaml
name: Helm Smoke Test
on: [pull_request, push]

jobs:
  helm-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup k3d
        uses: AbsaOSS/k3d-action@v2
        with:
          cluster-name: sft-test
          args: >-
            --config infra/k3d/ci-config.yaml

      - name: Helm dependency update
        run: helm dependency update infra/helm/sft-stack/

      - name: Helm dry-run
        run: |
          helm install sft-test infra/helm/sft-stack/ \
            --dry-run \
            --values infra/helm/sft-stack/values-ci.yaml

      - name: Helm install (skeleton)
        run: |
          helm install sft-test infra/helm/sft-stack/ \
            --values infra/helm/sft-stack/values-ci.yaml \
            --timeout 3m \
            --wait

      - name: Wait for pods
        run: kubectl wait --for=condition=ready pod --all --timeout=120s

      - name: Helm test
        run: helm test sft-test
```

**`infra/k3d/ci-config.yaml`:**
```yaml
apiVersion: k3d.io/v1alpha5
kind: Simple
metadata:
  name: sft-test
servers: 1
agents: 0
options:
  k3s:
    extraArgs:
      - arg: --disable=traefik
        nodeFilters: [server:*]
```

### Pattern 8: MkDocs Material i18n

**`docs/mkdocs.yml`:**
```yaml
site_name: Smart Factory Transformation
site_url: https://fedcal.github.io/Smart-Factory-Transformation/
docs_dir: docs
theme:
  name: material
  language: it
  features:
    - navigation.tabs
    - navigation.instant
    - content.code.copy
  palette:
    - scheme: default
      toggle:
        icon: material/brightness-7
        name: Dark mode
    - scheme: slate
      toggle:
        icon: material/brightness-4
        name: Light mode

plugins:
  - search
  - i18n:
      docs_structure: folder
      languages:
        - locale: it
          name: Italiano
          default: true
          build: true
        - locale: en
          name: English
          build: true
      reconfigure_material: true

markdown_extensions:
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - admonition
  - pymdownx.details

nav:
  - index.md
  - Architettura: architecture/index.md
  - Agenti: agents/index.md
```

**Struttura file docs (IT default + EN folder):**
```
docs/
├── docs/
│   ├── index.md               # IT (default)
│   └── architecture/
│       └── index.md
└── docs/en/
    ├── index.md               # EN
    └── architecture/
        └── index.md
```

**`.github/workflows/docs-deploy.yml`:**
```yaml
name: Deploy Docs
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install mkdocs-material mkdocs-static-i18n
      - run: mkdocs gh-deploy --force
        working-directory: docs/
```

### Pattern 9: Changesets Setup Polyglot

**Init Changesets:**
```bash
cd /repo
npx changeset init
# Crea .changeset/config.json
```

**`.changeset/config.json`:**
```json
{
  "$schema": "https://unpkg.com/@changesets/config/schema.json",
  "changelog": "@changesets/cli/changelog",
  "commit": false,
  "fixed": [],
  "linked": [],
  "access": "restricted",
  "baseBranch": "main",
  "updateInternalDependencies": "patch",
  "ignore": []
}
```

**Script Python per sincronizzare versione da package.json a `__version__.py`:**
```python
# scripts/sync-python-versions.py
import json
import pathlib

workspace_root = pathlib.Path(__file__).parent.parent

def sync_versions():
    # Legge versione da package.json principale o da changeset bump
    for pkg_dir in (workspace_root / "packages").iterdir():
        pkg_json = pkg_dir / "package.json"
        if not pkg_json.exists():
            continue
        version = json.loads(pkg_json.read_text())["version"]
        py_version_file = pkg_dir / "src" / pkg_dir.name.replace("-", "_") / "__version__.py"
        if py_version_file.exists():
            py_version_file.write_text(f'__version__ = "{version}"\n')
            print(f"Updated {py_version_file} to {version}")

if __name__ == "__main__":
    sync_versions()
```

**GitHub Actions release workflow (abilitato dopo configurazione Changesets):**
```yaml
# .github/workflows/release.yml (aggiunto dopo setup iniziale)
name: Release
on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - name: Create Release PR or Tag
        uses: changesets/action@v1
        with:
          version: npm run version-packages
          publish: npm run release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Pattern 10: SealedSecrets Workflow

**Bootstrap SealedSecrets (da fare UNA VOLTA per cluster):**
```bash
# Installa controller nel cluster
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets-controller sealed-secrets/sealed-secrets \
  --namespace kube-system

# Installa kubeseal CLI
curl -L https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.27.0/kubeseal-0.27.0-linux-amd64.tar.gz \
  | tar -xz -C /usr/local/bin kubeseal

# Fetch chiave pubblica (per cifrare localmente)
kubeseal --fetch-cert > infra/helm/sealed-secrets-pub-key.pem
```

**Creare un SealedSecret (da fare per ogni secret):**
```bash
# 1. Crea Secret normale (NON committare questo file)
kubectl create secret generic sft-api-keys \
  --dry-run=client \
  --from-literal=langfuse-secret=myvalue \
  -o yaml > /tmp/secret.yaml

# 2. Cifra con kubeseal usando chiave pubblica del cluster
kubeseal --format yaml \
  --cert infra/helm/sealed-secrets-pub-key.pem \
  < /tmp/secret.yaml \
  > infra/helm/charts/api-gateway/templates/sealed-secret.yaml

# 3. Committed! Il file sealed-secret.yaml è sicuro in git
```

**NOTA CRITICA:** Il controller deve essere installato PRIMA di `helm install sft-stack`. Il smoke test CI deve installare sealed-secrets-controller separatamente nel cluster k3d prima di installare l'umbrella chart.

### Anti-Patterns to Avoid

- **Bind mounts invece di named volumes:** Causa UID mismatch su Linux e non è portabile su macOS. Usare sempre named volumes (D-09).
- **Mettere Langfuse obs stack in core.yml:** Langfuse richiede Postgres dedicato e ClickHouse separato. Il mix con il Postgres principale causa conflitti di schema e problemi di boot order.
- **Condividere redis tra core e obs:** Il Redis di Langfuse (per worker queue) non deve essere lo stesso del Redis dell'applicazione (per cache agenti e LangGraph).
- **grype invece di trivy per license scanning:** Grype è un vulnerability scanner (CVE). Non ha `license.forbidden` nativo. Usare Trivy per license policy.
- **nx affected senza `fetch-depth: 0`:** Senza storia completa, `nrwl/nx-set-shas@v4` non riesce a trovare il base SHA e fallisce o usa HEAD~1.
- **uv workspace members senza pyproject.toml nelle directory placeholder:** Se la directory è inclusa dal glob ma non ha `pyproject.toml`, uv fallisce con errore.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SBOM generation | Script custom che legge package.json/pyproject.toml | Syft | Syft copre 30+ ecosistemi incluse immagini container; singolo comando per tutto il repo |
| License policy enforcement | Script Python che parsa file LICENSE | Trivy `license.forbidden` | Trivy normalizza nomi licenze SPDX, gestisce licenze dual, copre containers |
| Secret encryption per GitOps | Cripto custom o base64 in git | SealedSecrets | Solo il controller del cluster può decifrare; chiave privata mai esce dal cluster |
| SHA base/head per nx affected | Script custom che legge git log | `nrwl/nx-set-shas@v4` | Gestisce PR, squash merge, merge queue; considera solo run CI successful |
| i18n per MkDocs | Folder structure manuale + script | mkdocs-static-i18n | Language switcher automatico, Material theme integration, fallback configurabile |
| Pre-commit CI check | Script bash che riesegue hook | `pre-commit/action@v3.0.1` | Cache pre-commit envs tra run; configura Python automaticamente |

**Key insight:** In questa fase quasi tutto ciò che serve ha una soluzione matura di terze parti. La tentazione di "scrivere un piccolo script" per ciascuno è forte ma sbagliata: ogni tool nella lista gestisce decine di edge case che emergono solo dopo la prima settimana di sviluppo reale.

---

## Common Pitfalls

### Pitfall 1: Langfuse v3 ClickHouse Boot Order

**Cosa va storto:** Langfuse web e worker fanno healthcheck su ClickHouse alla startup. Se ClickHouse non risponde alla ping HTTP su porta 8123 entro il timeout di `depends_on`, i container Langfuse crashano e non fanno retry automatico (docker compose non riavvia container che escono con errore da depends_on).

**Perché accade:** ClickHouse richiede 20-30 secondi per inizializzare a freddo (journal recovery). Il healthcheck di default `wget /ping` con `interval: 5s, retries: 10` copre 50 secondi, ma se il volume è nuovo e il clickhouse-server fa migration, può superarlo.

**Come evitare:** Aumentare `retries: 20` su ClickHouse nel primo deploy. Aggiungere `start_period: 30s` al healthcheck. Il `--wait` di `docker compose up` aspetta tutti i healthcheck, ma solo se configurati correttamente.

**Warning signs:** `langfuse-web` esce con `ECONNREFUSED` su porta 8123; log di ClickHouse che mostrano `Starting ClickHouse server...` più a lungo del solito.

### Pitfall 2: nx affected sul Primo Commit

**Cosa va storto:** `nrwl/nx-set-shas@v4` cerca l'ultimo run CI successful per `ci.yml` su `main`. Sul primo push su `main` (o su un repo nuovo), non esiste nessun run precedente. L'azione logga warning e usa `HEAD~1` come base, che su un repo con un solo commit è lo stesso di HEAD. Il risultato è che `nx affected` mostra zero progetti cambiati.

**Perché accade:** Il meccanismo "last successful run" richiede almeno un run CI completato con successo.

**Come evitare:** Nella configurazione `nrwl/nx-set-shas@v4` aggiungere:
```yaml
- uses: nrwl/nx-set-shas@v4
  with:
    fallback-sha: "HEAD~1"   # o hash del primo commit
    error-on-no-successful-workflow: false
```
Per il primo run usare `npx nx run-many --all --target=test` invece di `nx affected`.

**Warning signs:** CI completa in 5 secondi senza eseguire nessun test; output "No affected projects".

### Pitfall 3: uv workspace con path nidificati

**Cosa va storto:** Il glob `apps/agents/ops/*` in `[tool.uv.workspace]` deve matchare directory che contengono un `pyproject.toml`. Se si crea la directory `apps/agents/ops/operator-assistant/` come placeholder senza `pyproject.toml`, uv fallisce con errore durante `uv sync`.

**Perché accade:** uv richiede che ogni directory matchata dal glob sia un Python project valido.

**Come evitare:** Creare un `pyproject.toml` minimale in ogni directory placeholder agente in Fase 1:
```toml
[project]
name = "ops-operator-assistant"
version = "0.1.0"
requires-python = ">=3.12"
description = "Operator Assistant agent (skeleton - populated in Phase 6)"
```

**Warning signs:** `uv sync` fallisce con "No pyproject.toml found in..."; CI fallisce su `Install Python dependencies`.

### Pitfall 4: @nxlv/python - Dipendenze Python→TypeScript non Automatiche

**Cosa va storto:** `nx affected` non sa che `ui-factory` (Angular) dipende da `sft-contracts` (Python). Se cambio il codice Pydantic in `sft-contracts`, il target `build` di `ui-factory` non viene rilanciato.

**Perché accade:** Nx non può inferire dipendenze cross-language automaticamente. `@nxlv/python` gestisce la dep graph Python→Python, ma non Python→TypeScript.

**Come evitare:** Dichiarare `implicitDependencies` esplicite nel `project.json` di `ui-factory` e `svc-api-gateway`:
```json
{
  "implicitDependencies": ["sft-contracts", "sft-agents", "sft-domain"]
}
```
Validare la dep graph in CI: `npx nx graph --file=graph.json && python scripts/validate-graph.py`.

**Warning signs:** Cambia interfaccia Pydantic in `sft-contracts`, build Angular passa in CI, ma i tipi TS sono stale; errori runtime invece che build-time.

### Pitfall 5: SealedSecrets Controller Non Installato Prima dell'Umbrella Chart

**Cosa va storto:** Il helm smoke test installa `sft-stack` che contiene template `SealedSecret`. Se il CRD di SealedSecrets non è già installato nel cluster, Helm fallisce con `no matches for kind "SealedSecret"`.

**Perché accade:** SealedSecrets controller installa il CRD; senza controller, il kind non esiste.

**Come evitare:** Nel workflow `helm-smoke-test.yml`, installare sealed-secrets controller PRIMA dell'umbrella chart:
```yaml
- name: Install SealedSecrets controller
  run: |
    helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
    helm install sealed-secrets-controller sealed-secrets/sealed-secrets \
      --namespace kube-system --wait
```

**Warning signs:** `helm install` fallisce con `unable to recognize "" no matches for kind "SealedSecret"`.

### Pitfall 6: MinIO chainguard image e `mc` binary

**Cosa va storto:** L'immagine MinIO di Langfuse (`cgr.dev/chainguard/minio`) ha healthcheck `mc ready local` ma `mc` non è nel PATH di default nella chainguard image. Il healthcheck fallisce sempre.

**Perché accade:** La Chainguard image è hardened e non include tools extra. Il `mc` binary potrebbe non essere disponibile nel container.

**Come evitare:** Verificare il healthcheck su immagine chainguard; alternativa: usare `curl -sf http://localhost:9000/minio/health/ready` come healthcheck. Controllare upstream [Langfuse docker-compose.yml](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml) per il healthcheck corretto al momento del deploy.

---

## Code Examples

### nx graph validation script

```python
# scripts/validate-nx-graph.py
# Source: best practice da .planning/research/PITFALLS.md (Pitfall 16)
import json
import sys

with open("graph.json") as f:
    graph = json.load(f)

REQUIRED_EDGES = [
    ("ui-factory", "sft-contracts"),
    ("svc-api-gateway", "sft-contracts"),
    ("svc-api-gateway", "sft-agents"),
]

deps = graph.get("graph", {}).get("dependencies", {})
missing = []
for source, target in REQUIRED_EDGES:
    targets = [d["target"] for d in deps.get(source, [])]
    if target not in targets:
        missing.append(f"MISSING: {source} -> {target}")

if missing:
    print("\n".join(missing))
    sys.exit(1)
print("All required dependency edges present.")
```

### uv workspace pyproject.toml root completo

```toml
# Source: docs.astral.sh/uv/concepts/projects/workspaces/ [VERIFIED]
[project]
name = "smart-factory-transformation"
version = "0.0.0"
requires-python = ">=3.12"
description = "Smart Factory Transformation - workspace root"

[tool.uv.workspace]
members = [
  "packages/sft-agents",
  "packages/sft-domain",
  "packages/sft-contracts",
  "apps/orchestrator",
  "apps/api-gateway",
  "apps/agents/ops/*",
  "apps/agents/maintenance/*",
  "apps/agents/knowledge/*",
  "apps/agents/supply/*",
  "services/ot-bridge",
  "simulators/sim-textile",
]
exclude = []

[tool.uv]
dev-dependencies = [
  "pre-commit>=4.6",
  "pytest>=8",
  "pytest-asyncio>=0.24",
  "mypy>=1.10",
  "ruff>=0.11",
]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
```

### Makefile completo per Fase 1

```makefile
# Smart Factory Transformation - Makefile
# Source: decisioni D-09, D-10, Claude's Discretion (Makefile)

COMPOSE_CORE     := infra/compose/core.yml
COMPOSE_OBS      := infra/compose/obs.yml
COMPOSE_SIM      := infra/compose/sim.yml
COMPOSE_LLM_CPU  := infra/compose/llm-cpu.yml
COMPOSE_LLM_GPU  := infra/compose/llm-gpu.yml

BASE_STACK := -f $(COMPOSE_CORE) -f $(COMPOSE_SIM) -f $(COMPOSE_OBS)

.PHONY: up up-gpu down reset test lint format docs demo sbom helm-test

up:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) up -d --wait

up-gpu:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_GPU) up -d --wait

down:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) down

reset:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) down -v
	$(MAKE) up

test:
	npx nx run-many --target=test --all --parallel=4

lint:
	npx nx run-many --target=lint --all --parallel=4
	pre-commit run --all-files

format:
	npx nx run-many --target=format --all
	pre-commit run ruff-format --all-files
	pre-commit run prettier --all-files

docs:
	cd docs && mkdocs build

demo:
	@echo "Demo script non ancora implementato (Fase 5+)"

sbom:
	syft . --output cyclonedx-json=sbom.json
	trivy sbom sbom.json --scanners license --config infra/license/trivy.yaml

helm-test:
	cd infra/helm/sft-stack && helm dependency update .
	helm install sft-test infra/helm/sft-stack/ --dry-run
```

---

## Order of Build (Dependency Graph)

L'ordine logico delle task all'interno della Fase 1, con parallelismo identificato:

```
Wave 0 (setup prerequisiti): NO parallelismo
  1. Bootstrap Nx workspace (create-nx-workspace)
  2. Installazione plugins npm (@nxlv/python, @nx/angular)
  3. Configurazione nx.json + nx cloud disabled
  4. Creazione struttura directory (6 root folders)

Wave 1 (fondamenta Python): IN PARALLELO con Wave 1b
  5. Root pyproject.toml + [tool.uv.workspace]
  6. Package placeholder con pyproject.toml minimale:
     - packages/sft-agents/, packages/sft-domain/, packages/sft-contracts/
     - apps/orchestrator/, apps/api-gateway/
     - apps/agents/ops/operator-assistant/ (e altri 15 placeholder)
     - services/ot-bridge/
     - simulators/sim-textile/
  7. `uv sync` per creare uv.lock

Wave 1b (fondamenta TypeScript): IN PARALLELO con Wave 1
  8. nx generate @nx/angular:application factory-ui --ssr
  9. nx generate per Angular library se serve

Wave 2 (pre-commit + CI): DOPO Wave 0, IN PARALLELO
  10. .pre-commit-config.yaml + commitlint.config.js
  11. ci.yml + pre-commit-check.yml
  12. LICENSE + LICENSE-EXCEPTIONS.md + infra/license/trivy.yaml
  13. license-scan.yml

Wave 3 (Docker Compose): IN PARALLELO dopo Wave 0
  14. infra/compose/core.yml + obs.yml + sim.yml + llm-cpu.yml + llm-gpu.yml
  15. infra/compose/.env.example
  16. Makefile con tutti i target
  17. Test: `make up` -> verifica healthcheck

Wave 4 (Helm skeleton): DOPO Wave 0, IN PARALLELO con Wave 3
  18. infra/helm/charts/{api-gateway,ot-bridge,orchestrator,factory-ui}/
      -> Chart.yaml, values.yaml, templates/deployment.yaml, service.yaml
      -> templates/hpa.yaml, pdb.yaml, networkpolicy.yaml, ingress.yaml
      -> templates/serviceaccount.yaml, rbac.yaml
  19. infra/helm/sft-stack/ (umbrella)
      -> Chart.yaml con dependencies
      -> values.yaml con defaults
      -> values-ci.yaml (per smoke test)
  20. helm-smoke-test.yml + infra/k3d/ci-config.yaml

Wave 5 (Changesets + docs): DOPO Wave 0
  21. npx changeset init
  22. .changeset/config.json
  23. scripts/sync-python-versions.py
  24. docs/mkdocs.yml + struttura placeholder IT/EN
  25. docs-deploy.yml

Wave 6 (SealedSecrets): DIPENDE da Wave 4
  26. Documentazione workflow kubeseal
  27. Aggiunta step sealed-secrets-controller in helm-smoke-test.yml
  28. infra/helm/sealed-secrets-pub-key.pem (da popolare con cluster reale)

Verifica finale:
  29. make up -> stack healthy (success criterion #1)
  30. nx affected graph assertion (success criterion #2)
  31. PR test con dep GPL fittizia -> license-scan blocca (success criterion #3)
  32. git commit con violazione -> pre-commit fallisce (success criterion #4)
  33. make helm-test -> smoke test passa (success criterion #5)
```

---

## Validation Architecture

> Questa sezione viene usata dall'orchestratore per emettere VALIDATION.md (Nyquist).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (Python) + jest/karma (Angular, via Nx executor) |
| Config file | `pyproject.toml` (pytest) per progetti Python; `project.json` executor per Angular |
| Quick run command | `npx nx affected --target=test --base=HEAD~1 --head=HEAD` |
| Full suite command | `npx nx run-many --target=test --all --parallel=4` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLAT-01 | Nx dep graph mostra tutti i progetti | Smoke | `npx nx graph --file=graph.json && python scripts/validate-nx-graph.py` | ❌ Wave 0 |
| PLAT-02 | uv sync completa senza errori | Smoke | `uv sync --all-packages` | ❌ Wave 1 |
| PLAT-03 | Struttura directory corretta | Smoke | `ls apps/ packages/ services/ docs/ infra/ simulators/` | ❌ Wave 0 |
| PLAT-04 | nx affected seleziona solo progetti cambiati | Integration | `ci.yml` con nrwl/nx-set-shas@v4 | ❌ Wave 2 |
| PLAT-05 | PR con dep GPL blocca CI | Integration | `license-scan.yml` + fixture test-gpl-dep | ❌ Wave 2+3 |
| PLAT-06 | pre-commit hooks eseguiti su ogni commit | Smoke | `pre-commit run --all-files` | ❌ Wave 2 |
| PLAT-07 | make up avvia stack healthy | Smoke | `make up && docker compose ps --format=json \| jq '.[] \| select(.Health != "healthy")'` | ❌ Wave 3 |
| PLAT-08 | Helm chart skeleton deploya su k3d senza errore | Integration | `helm-smoke-test.yml` | ❌ Wave 4+5 |
| PLAT-09 | Tutti i make targets esistono | Smoke | `make --dry-run up up-gpu down reset test lint format docs demo sbom helm-test` | ❌ Wave 3 |
| PLAT-10 | Changesets emette tag + GH Release su bump | Manual | Aprire PR con changeset, merge, verifica tag | ❌ Wave 5 |
| OBS-01 | Langfuse v3 raggiungibile su :3000 | Smoke | `curl -sf http://localhost:3000/api/public/health \| jq '.status'` | ❌ Wave 3 |

### Sampling Rate
- **Per commit:** `pre-commit run --all-files`
- **Per PR merge:** `npx nx affected --target=test --base=$NX_BASE --head=$NX_HEAD`
- **Phase gate:** Full suite + `make up` + healthcheck + `make helm-test` prima di `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `scripts/validate-nx-graph.py` — valida dep graph Python→TypeScript
- [ ] `scripts/sync-python-versions.py` — sync __version__.py da Changesets
- [ ] `tests/license/test_gpl_fixture.txt` — fixture per test license scanner

*(Nessun test framework da installare: pytest è già nella lista dev-dependencies uv)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Fase 1 infra only) | — |
| V3 Session Management | no | — |
| V4 Access Control | parziale | SealedSecrets per secrets management; RBAC nei chart Helm |
| V5 Input Validation | no (no user input in Fase 1) | — |
| V6 Cryptography | parziale | SealedSecrets usa RSA asymmetric; secrets non in plaintext in git |
| V14 Configuration | yes | `.env.example` documentato; no secrets hardcoded; gitleaks pre-commit hook |

### Known Threat Patterns for Infrastructure Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secrets in git (API keys, passwords) | Information Disclosure | gitleaks hook pre-commit + `--global` gitignore per file `.env` |
| GPL transitive dep contaminates Apache-2.0 codebase | — (legal risk) | Trivy license scanner in CI come required check |
| SealedSecrets controller downtime -> secrets inaccessibili | Denial of Service | Backup chiave privata controller (documentato nel runbook); SealedSecrets key rotation plan |
| Docker named volumes con UID mismatch (Linux) | — (operational) | Named volumes standard; no bind mount (D-09) |
| MinIO AGPL-3.0 in stack -> potenziale obbligo source disclosure | — (legal) | Usato as-is senza modifiche; documentato in LICENSE-EXCEPTIONS.md (D-14) |

---

## Open Questions

1. **ClickHouse versione tag esatta**
   - Cosa sappiamo: Langfuse v3 richiede ClickHouse 24.3+. Il docker-compose ufficiale usa `clickhouse/clickhouse-server` senza tag (latest).
   - Cosa è incerto: il tag `24.3-alpine` esiste su Docker Hub? O occorre usare `24.3.3.7-alpine`?
   - Raccomandazione: Usare tag `24.3-alpine` e verificare esistenza con `docker pull clickhouse/clickhouse-server:24.3-alpine` prima del primo `make up`. Se non disponibile, usare `latest` e documentare.

2. **@nxlv/python 21.x con Nx 20.x: compatibilità esatta**
   - Cosa sappiamo: @nxlv/python 21.x e Nx 20.x sono entrambi in versione major recente. CLAUDE.md afferma compatibilità.
   - Cosa è incerto: @nxlv/python versione README non specifica quali versioni di Nx 20.x sono supportate. L'ultima versione @nxlv/python 21.3.1 è testata con Nx 20.8.4?
   - Raccomandazione: Usare `@nxlv/python@21` e `nx@20` (latest minor) e testare durante Wave 0. Se incompatibilità, pinare alla versione verificata.

3. **Helm chart upstream: versioni stabili Bitnami postgresql e qdrant/qdrant**
   - Cosa sappiamo: CLAUDE.md specifica PostgreSQL 16+, Qdrant 1.16+. Le versioni Helm chart corrispondenti non sono specificate.
   - Cosa è incerto: `bitnami/postgresql` chart 16.x.x e `qdrant/qdrant` chart 1.x.x: qual è l'ultima versione stabile da usare in `Chart.yaml`?
   - Raccomandazione: Lasciare `*` come range in Chart.yaml e pinare con `helm dependency update` generando `Chart.lock`. Questo garantisce riproducibilità senza dover ricercare la versione esatta ora.

4. **k3d NetworkPolicy enforcement**
   - Cosa sappiamo: k3d usa k3s che include flannel come CNI di default. Flannel supporta NetworkPolicy SOLO se CNI policy engine è configurato (es. Calico).
   - Cosa è incerto: Il smoke test CI che usa k3d/flannel verifica davvero il comportamento della NetworkPolicy data-diode? Senza Calico, le NetworkPolicy potrebbero essere ignorate silenziosamente.
   - Raccomandazione: Nel `ci-config.yaml` k3d, disabilitare flannel e abilitare Calico, oppure limitare il smoke test al fatto che il chart si installa senza errori (non che la policy funzioni). La verifica funzionale della NetworkPolicy rimane a Fase 11.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | @nxlv/python 21.3.1 è compatibile con nx 20.8.4 | Standard Stack | Workflow bootstrap fallisce; occorre pinare versioni compatibili diverse |
| A2 | Il tag `24.3-alpine` esiste per clickhouse-server su Docker Hub | Pattern 3 (obs.yml) | docker compose pull fallisce; occorre usare tag diverso (es. `24.3.3.7-alpine`) |
| A3 | `AbsaOSS/k3d-action@v2` è lo step ottimale per k3d in GitHub Actions CI | Pattern 7 | K3d setup fallisce; alternativa: nolar/setup-k3d-k3s |
| A4 | `cgr.dev/chainguard/minio` ha healthcheck `mc ready local` funzionante | Pattern 3 (obs.yml) | Healthcheck sempre failed; occorre usare curl come alternativa |
| A5 | nrwl/nx-set-shas@v4 ha compatibilità stabile con GitHub Actions current runner | Pattern 6 | SHA non settati; fallback su `npx nx run-many --all` per CI |
| A6 | Changesets può emettere tag e GH Release per package Python senza pubblicare su PyPI | Pattern 9 | Workflow release non funzionante; occorre script custom |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | PLAT-07 (docker compose) | ✓ | 29.3.0 | — |
| docker compose v2 | PLAT-07 | ✓ (builtin in Docker 29) | v2.x | — |
| Node.js | PLAT-01 (Nx) | ✓ | 24.11.0 (LTS ok) | — |
| npm | PLAT-01 | ✓ | 11.6.3 | — |
| uv | PLAT-02 | ✓ | 0.11.13 (>= 0.6 ok) | — |
| Python 3.12 | PLAT-02 | verifica locale necessaria | — | pyenv per installazione |
| helm | PLAT-08 | ✗ (non trovato in env) | — | Installare via script ufficiale |
| k3d | PLAT-08 (smoke test CI) | ✗ (non trovato in env) | — | Installare via GitHub Action AbsaOSS/k3d-action in CI (non serve localmente) |
| pre-commit | PLAT-06 | verifica locale necessaria | — | `pip install pre-commit` |
| syft | PLAT-05 | ✗ (non trovato in env) | — | Script install in CI |
| trivy | PLAT-05 | ✗ (non trovato in env) | — | Script install in CI o `aquasecurity/trivy-action` |

**Missing dependencies with no fallback:** nessuna (tutte le dipendenze mancanti hanno un install path chiaro)

**Missing dependencies with fallback via CI action:**
- helm: `helm/kind-action` o installatore in CI step
- syft: `anchore/sbom-action` GitHub Action
- trivy: `aquasecurity/trivy-action` GitHub Action
- k3d: `AbsaOSS/k3d-action` — non serve localmente per sviluppo

---

## Sources

### Primary (HIGH confidence)

- [uv workspace docs - astral.sh](https://docs.astral.sh/uv/concepts/projects/workspaces/) — formato `[tool.uv.workspace]`, members glob, lockfile unico [VERIFIED]
- [Langfuse docker-compose.yml - github.com/langfuse](https://raw.githubusercontent.com/langfuse/langfuse/main/docker-compose.yml) — immagini esatte (postgres:17, clickhouse-server, chainguard/minio, redis:7, langfuse:3), healthchecks, depends_on [VERIFIED]
- [@nxlv/python README - github.com/lucasvieirasilva/nx-plugins](https://github.com/lucasvieirasilva/nx-plugins/blob/main/packages/nx-python/README.md) — uv workspace auto-detection, generator commands, executors [CITED]
- [nrwl/nx-set-shas action.yml](https://github.com/nrwl/nx-set-shas/blob/main/action.yml) — parametri input/output, comportamento su primo commit (fallback HEAD~1), workflow-id option [VERIFIED]
- [Trivy license scanning docs - trivy.dev](https://trivy.dev/docs/v0.54/scanner/license/) — `trivy.yaml` con `license.forbidden`, comandi, `trivy sbom` [CITED]
- [Gitleaks pre-commit - github.com/gitleaks](https://github.com/gitleaks/gitleaks#pre-commit) — repo URL, hook ID, tag v8.24.2 [VERIFIED]
- [npm registry - nx@20](https://registry.npmjs.org/nx) — versione 20.8.4 [VERIFIED: npm registry]
- [npm registry - @nxlv/python@21](https://registry.npmjs.org/@nxlv/python) — versione 21.3.1 [VERIFIED: npm registry]
- [npm registry - @nx/angular](https://registry.npmjs.org/@nx/angular) — versione 22.7.2 [VERIFIED: npm registry]
- [npm registry - @changesets/cli](https://registry.npmjs.org/@changesets/cli) — versione 2.31.0 [VERIFIED: npm registry]
- [PyPI - mkdocs-material](https://pypi.org/project/mkdocs-material/) — versione 9.7.6 [VERIFIED: PyPI]
- [PyPI - mkdocs-static-i18n](https://pypi.org/project/mkdocs-static-i18n/) — versione 1.3.1 [VERIFIED: PyPI]
- [PyPI - pre-commit](https://pypi.org/project/pre-commit/) — versione 4.6.0 [VERIFIED: PyPI]
- `.planning/research/STACK.md` — stack validato, versioni, compatibility matrix [CITED]
- `.planning/research/PITFALLS.md` — Pitfall 16 (Nx polyglot misconfiguration), Pitfall 20 (GPL license conflicts) [CITED]
- `.planning/phases/01-foundation-monorepo/01-CONTEXT.md` — D-01..D-20, Claude's Discretion decisions [CITED]

### Secondary (MEDIUM confidence)

- [mkdocs-static-i18n docs - ultrabug.github.io](https://ultrabug.github.io/mkdocs-static-i18n/) — configurazione IT/EN, `docs_structure: folder`, `reconfigure_material: true` [CITED]
- [Changesets polyglot monorepo - luke.hsiao.dev](https://luke.hsiao.dev/blog/changesets-polyglot-monorepo/) — script `sync-versions.py`, workflow release senza PyPI [CITED; pagina 403 durante fetch, referenziata da WebSearch]
- [SealedSecrets docs - bitnami-labs/sealed-secrets](https://github.com/bitnami-labs/sealed-secrets) — bootstrap workflow, kubeseal CLI, controller install [CITED]
- [AbsaOSS/k3d-action - github.com](https://github.com/AbsaOSS/k3d-action) — k3d in CI, cluster config file support, 20-30s startup [CITED]
- [Trivy license scan guide - oneuptime.com](https://oneuptime.com/blog/post/2026-01-30-trivy-license-scanning/view) — struttura allowlist/denylist/flaglist, best practices [CITED]

### Tertiary (LOW confidence — verificare durante esecuzione)

- ClickHouse 24.3-alpine tag esistenza su Docker Hub [ASSUMED] — verificare con `docker pull` al primo bootstrap
- @nxlv/python 21.x + Nx 20.8.4 compatibilità testata [ASSUMED] — verificare durante Wave 0 del plan
- Chainguard MinIO healthcheck `mc ready local` funzionante [ASSUMED] — verificare con `docker run` isolato

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versioni verificate su npm/PyPI registry, tools principali da fonti ufficiali
- Docker Compose layout: HIGH — Langfuse docker-compose.yml letto direttamente da GitHub; pattern healthcheck da docs Docker
- License scanner: HIGH — Trivy docs verificati; architettura Syft+Trivy ben documentata
- Helm skeleton: MEDIUM — pattern di template standard Kubernetes; dettagli upstream chart versions sono ASSUMED
- Nx polyglot graph: MEDIUM — documentazione @nxlv/python non copre esplicitamente Python→TypeScript implicit deps; pattern da PITFALLS.md
- Changesets polyglot: LOW-MEDIUM — articolo di riferimento non raggiungibile (403); pattern descritti sono ragionevoli ma non verificati end-to-end
- SealedSecrets: MEDIUM — docs ufficiali letti; workflow bootstrap è standard

**Research date:** 2026-05-16
**Valid until:** 2026-06-16 (tools stabili; unico rischio è bump di versioni minor che cambiano API)
