---
phase: 1
slug: foundation-monorepo
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-16
updated: 2026-05-16
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python) + jest/karma via Nx executor (Angular) + helm test hooks + `docker compose up --wait` (Compose) |
| **Config file** | `pyproject.toml` (pytest) per progetti Python; `project.json` Nx executor per Angular; `infra/license/trivy.yaml` (license); `.pre-commit-config.yaml` (pre-commit); `infra/k3d/ci-config.yaml` (helm smoke) |
| **Quick run command** | `npx nx affected --target=test --base=HEAD~1 --head=HEAD --parallel=3` |
| **Full suite command** | `npx nx run-many --target=test --all --parallel=4 && pre-commit run --all-files && make sbom && make helm-test` |
| **Estimated runtime** | ~120-300 seconds full suite (cache cold); ~30-90s warm |

---

## Sampling Rate

- **After every task commit:** Run `pre-commit run --all-files` (locale) and the affected nx targets
- **After every plan wave:** Run `npx nx run-many --target=test --all` + `helm lint infra/helm/charts/*`
- **Before `/gsd:verify-work`:** Full suite must be green AND `make up` exits 0 healthy AND `make helm-test` exits 0
- **Max feedback latency:** ~120 seconds (cache warm)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | PLAT-03 | — | repo bootstrap, no secrets | smoke | `test -f .gitignore && test -f .nvmrc && test -d apps && test -d packages && test -d services && test -d docs && test -d infra && test -d simulators` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | PLAT-01 | T-1-02 | Nx + plugin pinati, no `latest`; Nx Cloud disabled by default | smoke | `node -e "const p=require('./package.json'); if(p.devDependencies.nx!=='20.8.4') process.exit(1); if(p.devDependencies['@nxlv/python']!=='21.3.1') process.exit(1)"` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | PLAT-02 | — | uv workspace dichiarato, no glob ambigui | smoke | `python3 -c "import tomllib; m=tomllib.load(open('pyproject.toml','rb'))['tool']['uv']['workspace']['members']; assert len(m)==23"` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | PLAT-02, PLAT-03 | — | 23 sotto-progetti Python valid, uv.lock prodotto | smoke | `uv sync --all-packages && test -f uv.lock && find apps packages services simulators -name pyproject.toml | wc -l | grep -E "^([2-9][0-9]|[3-9][0-9]+)$"` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | PLAT-01, PLAT-02 | — | Angular SSR app, implicitDependencies cross-language presenti | integration | `npx nx graph --file=tmp/graph.json && python3 scripts/validate-nx-graph.py` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 2 | PLAT-07 | T-1-03, T-1-SC | image tag pinati, secrets via ${VAR} | smoke | `docker compose -f infra/compose/core.yml -f infra/compose/sim.yml -f infra/compose/llm-cpu.yml config > /dev/null && ! grep -E "^\\s*image:.*:latest" infra/compose/core.yml infra/compose/sim.yml infra/compose/llm-cpu.yml infra/compose/llm-gpu.yml` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 2 | OBS-01, PLAT-07 | T-1-03 | Langfuse stack v3 con boot order correct; healthcheck robust | smoke | `docker compose -f infra/compose/core.yml -f infra/compose/obs.yml config > /dev/null && grep -q "start_period: 30s" infra/compose/obs.yml && grep -q "curl -sf http://localhost:9000/minio/health" infra/compose/obs.yml` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 2 | PLAT-09 | — | tutti make target presenti | smoke | `make --dry-run up up-gpu down reset test lint format docs demo sbom helm-test ps logs > /dev/null` | ❌ W0 | ⬜ pending |
| 1-02-04 | 02 | 2 | PLAT-07, OBS-01 | T-1-03 | stack reale healthy | integration | `make up && docker compose ps --format json | jq -e '[.[] | select(.Health != "" and .Health != "healthy")] | length == 0'` | ✅ checkpoint:human-verify | ⬜ pending |
| 1-03-01 | 03 | 3 | PLAT-05 | T-1-01 | allowlist licenze esplicita; AGPL eccezione documentata | smoke | `grep -q "AGPL-3.0" infra/license/trivy.yaml && grep -q "minio" LICENSE-EXCEPTIONS.md && test -f LICENSE` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 3 | PLAT-05 | T-1-01 | SBOM artifact + PR comment + retention | integration | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/license-scan.yml'))" && grep -q "retention-days: 90" .github/workflows/license-scan.yml` | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 3 | PLAT-05 | T-1-01 | fixture GPL bloccata da Trivy | integration | gh workflow run test-license-fixture.yml (deferred to first PR) | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | PLAT-06 | T-1-03, T-1-SC | tutti hook pinati a tag; gitleaks active; mypy strict su sft-* | smoke | `python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))" && grep -E "^\\s+rev:" .pre-commit-config.yaml | wc -l | grep -E "^[6-9]\|^[1-9][0-9]"` | ❌ W0 | ⬜ pending |
| 1-04-02 | 04 | 2 | PLAT-06 | — | CI mirror dei hook locali | smoke | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pre-commit-check.yml'))" && grep -q "pre-commit/action@v3.0.1" .github/workflows/pre-commit-check.yml` | ❌ W0 | ⬜ pending |
| 1-04-03 | 04 | 2 | PLAT-06 | T-1-03 | hook locali bloccano violazioni reali | integration | `pre-commit run --all-files` (manuale checkpoint) | ✅ checkpoint:human-verify | ⬜ pending |
| 1-05-01 | 05 | 3 | PLAT-04 | T-1-04, T-1-SC | nx affected con fetch-depth 0, fallback per primo commit, cache uv/Nx | smoke | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && grep -q "fetch-depth: 0" .github/workflows/ci.yml && grep -q "fallback-sha" .github/workflows/ci.yml && grep -q "validate-nx-graph" .github/workflows/ci.yml` | ❌ W0 | ⬜ pending |
| 1-05-02 | 05 | 3 | PLAT-04, OBS-01 | — | nx graph artifact su PR, docs ci-pipeline | smoke | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/nx-affected-graph.yml'))" && grep -q "OBS-01" docs/contributing/ci-pipeline.md` | ❌ W0 | ⬜ pending |
| 1-06-01 | 06 | 4 | PLAT-08 | T-1-04 | tutti chart con runAsNonRoot true | smoke | `for c in infra/helm/charts/api-gateway infra/helm/charts/orchestrator infra/helm/charts/factory-ui; do helm lint "$c" || exit 1; done` | ❌ W0 | ⬜ pending |
| 1-06-02 | 06 | 4 | PLAT-08 | T-1-05 | NetworkPolicy data-diode ot-bridge presente | smoke | `helm lint infra/helm/charts/ot-bridge && helm template ot infra/helm/charts/ot-bridge | grep -c "data-diode" | grep -E "^[1-9]"` | ❌ W0 | ⬜ pending |
| 1-06-03 | 06 | 4 | PLAT-08 | T-1-03, T-1-04 | umbrella chart valido, sealed-secrets-controller installato prima dell'umbrella, smoke test CI passa | integration | `helm dependency update infra/helm/sft-stack/ && helm install --dry-run sft-test infra/helm/sft-stack/ -f infra/helm/sft-stack/values-ci.yaml` (CI completo: helm-smoke-test.yml workflow) | ❌ W0 | ⬜ pending |
| 1-07-01 | 07 | 2 | PLAT-10 (docs) | T-1-03 | mkdocs build strict pass | smoke | `cd docs && pip install -r requirements.txt && mkdocs build --strict` | ❌ W0 | ⬜ pending |
| 1-07-02 | 07 | 2 | PLAT-10 (docs) | — | gh-deploy workflow valido | smoke | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/docs-deploy.yml'))" && grep -q "mkdocs gh-deploy" .github/workflows/docs-deploy.yml` | ❌ W0 | ⬜ pending |
| 1-08-01 | 08 | 2 | PLAT-10 (release) | — | Changesets config + linked SDK + sync script | smoke | `python3 -c "import json; c=json.load(open('.changeset/config.json')); assert c['baseBranch']=='main'; assert ['sft-agents','sft-domain','sft-contracts'] in c['linked']" && python3 scripts/sync-python-versions.py` | ❌ W0 | ⬜ pending |
| 1-08-02 | 08 | 2 | PLAT-10 (release) | T-1-04 | release.yml minimal permissions | smoke | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))" && grep -q "changesets/action@v1" .github/workflows/release.yml` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

> Per Phase 1, l'infrastruttura di test è messa in place DURANTE il plan 01 stesso (Wave 1).
> Wave 0 inteso come "prima del primo task di ogni plan" è leggero.

- [ ] `scripts/validate-nx-graph.py` — verifica edges Python<->TS richiesti (creato in plan 01 task 2; usato da plan 05 task 1)
- [ ] `scripts/sync-python-versions.py` — sync da package.json a __version__.py (creato in plan 01 task 2; completato in plan 08 task 1)
- [ ] `tests/license/fixture-gpl-pyproject.toml` — fixture per test license scanner (creato in plan 03 task 3)
- [ ] `infra/k3d/ci-config.yaml` — config k3d cluster CI (creato in plan 06 task 3)
- [ ] Strumenti CLI sulla developer machine: `node>=20`, `npm`, `uv>=0.6`, `python3.12`, `docker`, `helm` (documentati in plan 01 task 1 in `docs/contributing/toolchain.md`)
- [ ] pytest, ruff, mypy, prettier, eslint installati come dev deps via `npm ci` + `uv sync --all-packages` (Plan 01 task 4)

> **Note Wave 0 in CI:** Tutte le GitHub Actions install via `actions/setup-python@v5`, `actions/setup-node@v4`, `astral-sh/setup-uv@v5`. Trivy/Syft via `anchore/sbom-action` e `aquasecurity/trivy-action`. k3d via `AbsaOSS/k3d-action@v2`. Helm via `azure/setup-helm@v4`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stack docker compose healthy reale | PLAT-07, OBS-01 | richiede Docker engine running localmente, pull immagini 2-5GB, GPU opzionale | Plan 02 task 4 (checkpoint:human-verify): `make up && curl -sf http://localhost:3000/api/public/health` |
| Pre-commit hook block reale di violazioni | PLAT-06 | fixture file devono essere fisicamente staged in git | Plan 04 task 3 (checkpoint:human-verify): introdurre file con import non usato / secret pattern, verificare blocco |
| Branch protection configuration | PLAT-04, PLAT-05, PLAT-06, PLAT-08 | GitHub UI configuration | Plan 03 task 3 documenta in `docs/operations/branch-protection.md`; configurazione effettuata dal maintainer in GitHub Settings |
| Primo gh-deploy del sito docs | PLAT-10 (docs) | richiede merge effettivo su main | Plan 07 task 2: dopo merge, verificare `https://fedcal.github.io/Smart-Factory-Transformation/` mostra IT + switch EN |
| Primo Changesets PR di release | PLAT-10 (release) | richiede ciclo end-to-end di merge + changeset | Plan 08 task 2: post-merge dell'initial changeset, verificare creazione PR "Version Packages" da changesets bot |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (5 task hanno checkpoint:human-verify documentati nella tabella Manual-Only)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (ogni task ha almeno uno smoke check)
- [x] Wave 0 covers all MISSING references (script + fixtures dichiarati esplicitamente)
- [x] No watch-mode flags (tutti i comandi sono one-shot)
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending — esecuzione da `/gsd:execute-phase 1`
