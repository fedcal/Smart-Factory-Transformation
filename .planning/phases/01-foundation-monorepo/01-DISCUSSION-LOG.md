# Phase 1: Foundation & Monorepo - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 1-Foundation & Monorepo
**Areas discussed:** Layout monorepo & SDK, Docker Compose dev stack, License scanner, Helm chart skeleton

---

## Layout monorepo & SDK

### Root layout

| Option | Description | Selected |
|--------|-------------|----------|
| Mantieni 6 cartelle root (PLAT-03) | apps/, packages/, services/, docs/, infra/, simulators/ — massima leggibilità per evaluators | ✓ |
| Convenzione Nx standard: apps/ + libs/ | Più idiomatico Nx, dep-graph più pulito | |
| Ibrido: apps/ + libs/ + simulators/ + infra/ + docs/ | Compromesso | |

**User's choice:** 6 cartelle root.
**Notes:** Coerente con PLAT-03; leggibilità per evaluators ha la priorità sull'idiomaticità Nx.

### SDK location

| Option | Description | Selected |
|--------|-------------|----------|
| packages/sft-agents/ — SDK pure library | Standalone, pubblicabile su PyPI | |
| packages/sft-agents/ + packages/sft-domain/ split | Core SDK + textile domain separati | ✓ |
| libs/sdk/ + libs/domain/ (Nx libs convention) | Stesso split sotto libs/ | |

**User's choice:** Split sft-agents + sft-domain in packages/.
**Notes:** Permette di evolvere l'SDK in altri verticali; coerente con root layout già scelto.

### Agents layout

| Option | Description | Selected |
|--------|-------------|----------|
| packages/agents/{cluster}/ — 4 pacchetti cluster | Agenti come librerie importate dal supervisor | |
| Singolo pacchetto packages/agents/ | Tutto in un pacchetto | |
| apps/agents/{cluster}/ — ogni cluster app deployabile | Cluster come servizi separati con dispatch RPC/NATS | ✓ |

**User's choice:** Apps deployabili per cluster.
**Notes:** Scelta strutturale che impatta Fase 4 (supervisor → cluster via NATS, non import in-process).

### Nx naming

| Option | Description | Selected |
|--------|-------------|----------|
| kebab-case prefisso per area (sft-* / ops-* / ui-* / infra-*) | Prefisso = scope immediato in nx graph | ✓ |
| Path-derived | Nome = path completo | |
| Nome breve diretto + tag Nx | Più idiomatico avanzato, richiede dependency-constraints | |

**User's choice:** Prefisso per area.

### Contracts

| Option | Description | Selected |
|--------|-------------|----------|
| packages/sft-contracts/ — single source of truth | Pydantic + generator TS dentro | ✓ |
| Python + generazione TS al build | Pydantic in pacchetto Python + build step | |
| Decido dopo (Fase 10) | Pragmatico, ma rinvia drift fix | |

**User's choice:** sft-contracts come SSOT.

---

## Docker Compose dev stack

### Compose split

| Option | Description | Selected |
|--------|-------------|----------|
| Singolo compose.yml con profili | Profiles core/llm/obs/gpu | |
| Split per area: core.yml + llm.yml + obs.yml + sim.yml | File separati componibili | ✓ |
| Singolo file, nessun profilo | Tutto on by default, massima semplicità | |

**User's choice:** Split per area.

### GPU policy

| Option | Description | Selected |
|--------|-------------|----------|
| Ollama in llm.yml con GPU obbligatoria + fallback CPU | Default GPU, override manuale CPU | |
| Due overlay: llm-gpu.yml + llm-cpu.yml | Dev sceglie esplicitamente | ✓ |
| Ollama esterno, non in compose | Più leggero ma rompe `make up` | |

**User's choice:** Due overlay separati, default CPU.

### Volumes

| Option | Description | Selected |
|--------|-------------|----------|
| Named volumes Docker, reset via `make reset` | Portabile, no UID issues | ✓ |
| Bind mount in `.data/` gitignored | Ispezionabili da host | |
| Named volumes + `make seed` per fixture | Reset-friendly + onboarding rapido | |

**User's choice:** Named volumes + make reset.

### Healthchecks

| Option | Description | Selected |
|--------|-------------|----------|
| `healthcheck` + `depends_on: condition: service_healthy` | Standard, robusto | ✓ |
| Solo depends_on + wait-for-it.sh | Funziona ma duplica logica | |
| Healthcheck + `make wait-up` separato | Permette CI di affidarsi a wait-up | |

**User's choice:** Healthcheck nativi + depends_on condition.

---

## License scanner

### Scanner tool

| Option | Description | Selected |
|--------|-------------|----------|
| Native stack: pip-licenses + license-checker | Semplice, ecosistema-specifico | |
| SBOM-based: Syft + Grype/Trivy | Unificato, copre container | ✓ |
| FOSSA-CLI gratis tier / ScanCode | SaaS gratis OSS, badge competition | |

**User's choice:** Syft + Grype/Trivy SBOM-based.

### License policy

| Option | Description | Selected |
|--------|-------------|----------|
| Allowlist esplicita | Tutto fuori da allowlist fallisce | |
| Denylist mirata | Blocca solo GPL/AGPL/SSPL etc. | |
| Allowlist + LICENSE-EXCEPTIONS.md versionato | Strict + audit trail | ✓ |

**User's choice:** Allowlist + exceptions file versionato.

### Container scope

| Option | Description | Selected |
|--------|-------------|----------|
| Scan intero stack + MinIO AGPL in eccezione documentata | Trasparenza massima | ✓ |
| Sostituisci MinIO con S3-compat licenza-friendly | Allowlist pulita ma drift rischio | |
| Scan limitato a deps Python/JS | Più pragmatico, evaluators potrebbero contestare | |

**User's choice:** Scan intero stack + eccezione MinIO documentata.

### CI integration

| Option | Description | Selected |
|--------|-------------|----------|
| Job dedicato `license-scan` come required check | Workflow separato, SBOM artefatto | ✓ |
| Step inline dentro nx affected CI | Meno overhead, rischio nx-affected false negative | |
| Pre-commit hook + CI gate ridondante | Doppia rete, pre-commit lento | |

**User's choice:** Workflow dedicato required check.

---

## Helm chart skeleton

### Chart architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Riuso chart upstream + umbrella | Min lavoro, max community support | |
| Chart unico flat con templates + dependencies | Più semplice, values.yaml grosso | |
| Chart separati per servizio + meta-chart sft-stack | Massima modularità, overhead alto | ✓ |

**User's choice:** Chart separati + meta-chart umbrella.

### Skeleton scope

| Option | Description | Selected |
|--------|-------------|----------|
| Skeleton minimo (Deployment+Service+ConfigMap) | Letterale "deploys without error" | |
| Skeleton + NetworkPolicy data-diode | Anticipo controllato SEC-06 | |
| Skeleton production-ready: HPA, PDB, NetworkPolicy, Ingress, External Secrets | Anticipo lavoro Fase 11 | ✓ |

**User's choice:** Production-ready dal Fase 1.
**Notes:** Scelta esplicita di anticipare lavoro che altrimenti pesa Fase 11. Conseguenza: i task Helm di Fase 1 sono materiali, non placeholder.

### Secrets

| Option | Description | Selected |
|--------|-------------|----------|
| External Secrets Operator + backend pluggable | Cloud-friendly, più complesso | |
| SealedSecrets (Bitnami) | Cifrati nel repo, ottimo per single-tenant on-prem | ✓ |
| ESO + SealedSecrets entrambi via values.backend | Più codice da mantenere | |

**User's choice:** SealedSecrets.
**Notes:** Coerente con target single-tenant on-prem; ESO/Vault rinviati a v2.

### Ingress & test

| Option | Description | Selected |
|--------|-------------|----------|
| ingress-nginx + helm-smoke-test su k3d | Standard, ~5-7 min CI | ✓ |
| Traefik (default k3d) + smoke test | Più veloce ma meno portabile | |
| ingress-nginx + cloud overlays AWS/Azure | Più assunzioni cloud | |

**User's choice:** ingress-nginx + smoke test k3d.

---

## Claude's Discretion

Aree dove l'utente non ha richiesto discussione esplicita; default sensati documentati in CONTEXT.md §Claude's Discretion:

- uv workspace strategy (single lockfile, dev/test groups, cache uv in CI)
- Task runner: Makefile (anziché Just)
- Versioning: Changesets per monorepo OSS
- Nx Cloud: disabled by default, opt-in via env var
- Pre-commit framework: `pre-commit` con ruff, mypy strict, eslint, prettier, commitlint, gitleaks
- GitHub Actions structure: 5 workflow distinti (ci, pre-commit, license-scan, helm-smoke-test, docs-deploy)
- Python toolchain: 3.12 only, no matrix
- Docs scaffolding Fase 1: MkDocs Material vuoto + i18n + GitHub Pages deploy stub

## Deferred Ideas

Vedi `01-CONTEXT.md` §Deferred Ideas per la lista completa. Sintesi:

- ESO + Vault (vs. SealedSecrets) → v2 se serve cloud multi-cluster
- Cloud Ingress overlays (AWS/Azure) → v2
- Nx Cloud paid tier → rivedere se CI > 10 min
- Garage / SeaweedFS al posto di MinIO → solo se evaluators contestano AGPL
- PyPI publish automatico SDK → rinviato a post-Fase 4
- Multi-version Python matrix (3.12 + 3.13) → non in v1
- Just al posto di Make → rivalutabile se ergonomia Make pesa
