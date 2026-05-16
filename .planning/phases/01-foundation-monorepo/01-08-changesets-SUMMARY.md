---
phase: 1
plan: 8
slug: changesets
subsystem: versioning
tags: [foundation, release, versioning, changesets, polyglot]
requirements: [PLAT-10]

dependency_graph:
  requires:
    - "01-01-nx-workspace (monorepo structure, packages/ dir)"
    - "01-01-nx-workspace (scripts/sync-python-versions.py baseline)"
  provides:
    - ".changeset/ configuration with linked sft-* packages"
    - "release.yml GitHub Actions workflow (changesets/action@v1)"
    - "package.json per publishable SDK package (Changesets discovery)"
    - "sync-python-versions.py: propagates package.json version to __version__.py + pyproject.toml"
  affects:
    - "packages/sft-{agents,domain,contracts}: version tracking"
    - ".github/workflows: release automation"

tech_stack:
  added:
    - "@changesets/cli 2.31.0 (already in devDependencies from prior plan)"
    - "changesets/action@v1 (GitHub Actions)"
    - "npm workspaces (packages/sft-{agents,domain,contracts})"
  patterns:
    - "Changesets linked versioning for polyglot monorepo"
    - "package.json → __version__.py version propagation"
    - "Deferred PyPI publish pattern"

key_files:
  created:
    - ".changeset/config.json"
    - ".changeset/README.md"
    - ".changeset/initial-phase-1.md"
    - ".github/workflows/release.yml"
    - "packages/sft-agents/package.json"
    - "packages/sft-domain/package.json"
    - "packages/sft-contracts/package.json"
    - "packages/sft-domain/src/sft_domain/__version__.py"
    - "packages/sft-contracts/src/sft_contracts/__version__.py"
    - "docs/contributing/release.md"
  modified:
    - "package.json (workspaces + changeset/version-packages/release scripts)"
    - "scripts/sync-python-versions.py (enhanced: pyproject.toml sync added)"
    - ".gitignore (allow initial-phase-1.md via negation rule)"

decisions:
  - "linked policy for sft-{agents,domain,contracts}: tre SDK bumpano sempre insieme alla stessa versione"
  - "access: restricted in changeset config significa no auto-publish npm (workflow usa solo tag+release)"
  - "PyPI publish deferred oltre v1: release script è echo no-op; verrà abilitato post-Phase 4"
  - "script sync-python-versions.py aggiorna anche pyproject.toml (non solo __version__.py) per coerenza"
  - "concurrency group nel workflow previene release parallele su push ravvicinati a main"
  - ".gitignore aggiornato con negation per initial-phase-1.md (file di esempio da tracciare)"

metrics:
  duration: "~20 minutes"
  completed: "2026-05-16T19:53:15Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 10
  files_modified: 3
---

# Phase 1 Plan 8: Changesets Versioning Setup Summary

**One-liner:** Changesets configurato con policy `linked` per i 3 SDK Python (sft-agents, sft-domain, sft-contracts), release workflow GitHub Actions che emette tag + GH Release su push a main, con PyPI publish esplicitamente deferred oltre v1.

## Tasks Completati

| Task | Nome | Commit | File principali |
|------|------|--------|-----------------|
| 1-08-01 | .changeset/ setup + package.json publishable | `1984e6c` | .changeset/config.json, README.md, initial-phase-1.md, packages/*/package.json, __version__.py, sync script |
| 1-08-02 | release.yml + docs/contributing/release.md | `89933bd` | .github/workflows/release.yml, docs/contributing/release.md |

## Artefatti prodotti

### `.changeset/config.json`
- `baseBranch: main`
- `linked: [["sft-agents", "sft-domain", "sft-contracts"]]` — i 3 SDK bumpano sempre insieme
- `access: restricted` — no auto-publish npm
- `updateInternalDependencies: patch`

### `.changeset/README.md`
Documenta la Polyglot policy: PyPI DEFERRED oltre v1, emissione solo tag + GH Release.

### `.changeset/initial-phase-1.md`
Esempio di changeset `minor` per i 3 SDK: "Phase 1 — Foundation & Monorepo scaffolding."

### `packages/sft-{agents,domain,contracts}/package.json`
Minimal: `name`, `version: 0.1.0`, `private: false`, `license: Apache-2.0`, `repository` field.
Necessari per la discovery di Changesets nel monorepo.

### `packages/sft-{domain,contracts}/src/sft_*//__version__.py`
Creati a `0.1.0` (sft-agents già esistente da plan 01-01).

### `scripts/sync-python-versions.py` (enhanced)
Aggiunto sync di `pyproject.toml` oltre a `__version__.py`. Preserva: `--dry-run`, argparse,
gestione errori, skipped packages senza package.json. Nuovo: regex idempotente su campo
`version = "..."` in pyproject.toml.

### `.github/workflows/release.yml`
- Trigger: `push: branches: [main]`
- Permissions: `contents: write`, `pull-requests: write` (minimali; no `id-token: write`)
- `changesets/action@v1` con:
  - `version: npm run version-packages` (changeset version + sync-python-versions.py)
  - `publish: npm run release` (echo no-op; PyPI deferred)
- `concurrency: cancel-in-progress: false` (release non si cancella)

### `docs/contributing/release.md`
Documentazione completa in IT con EN summary: flow di release, tipi di bump, linked behavior,
PyPI deferred policy, troubleshooting, note di sicurezza.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] .gitignore bloccava initial-phase-1.md**
- **Found during:** Task 1 — `git add .changeset/initial-phase-1.md`
- **Issue:** Il `.gitignore` aveva regola `!.changeset/README.md` e `!.changeset/config.json` ma non `initial-phase-1.md`, che era bloccato dalla regola `.changeset/*.md`
- **Fix:** Aggiunta negation `!.changeset/initial-phase-1.md` al `.gitignore`
- **Files modified:** `.gitignore`
- **Commit:** `1984e6c`

**2. [Rule 1 - Enhancement] sync-python-versions.py: aggiunta sync pyproject.toml**
- **Found during:** Task 1 — confronto script esistente vs requisiti del piano
- **Issue:** Lo script da plan 01-01 sincronizzava solo `__version__.py`, non `pyproject.toml`. Il piano 01-08 richiede sync anche di pyproject.toml per coerenza completa
- **Fix:** Aggiunto blocco regex idempotente per aggiornare `version = "..."` in pyproject.toml. Preserve: dry-run, argparse, error handling, skipped packages
- **Files modified:** `scripts/sync-python-versions.py`
- **Commit:** `1984e6c`

## Threat Surface Scan

| Flag | File | Descrizione |
|------|------|-------------|
| threat_flag: T-1-04 mitigated | .github/workflows/release.yml | GITHUB_TOKEN scope `contents: write` + `pull-requests: write` — minimale. No `id-token: write` (PyPI OIDC non richiesto in v1) |
| threat_flag: T-1-03 mitigated | docs/contributing/release.md | Documentato esplicitamente: "Non includere secret nelle descrizioni dei changeset" |
| threat_flag: T-1-SC mitigated | .github/workflows/release.yml | `changesets/action@v1` pinned a major tag (security patches automatici) |

## Known Stubs

- `npm run release` esegue `echo 'PyPI publish deferred...'` — intenzionale, documentato
- `npx changeset status` non testabile offline (richiede node_modules installati o CI). Verificato in CI al primo push su main.

## Self-Check

- [x] `.changeset/config.json` esiste e contiene `"baseBranch": "main"` — verificato con python3
- [x] `.changeset/config.json` contiene `"linked": [["sft-agents", "sft-domain", "sft-contracts"]]` — verificato
- [x] `.changeset/README.md` esiste e contiene "PyPI" e "DEFERRED" — verificato con grep
- [x] `.changeset/initial-phase-1.md` esiste con 3 entry minor — verificato
- [x] `packages/sft-agents/package.json` con `"name": "sft-agents"` e `"version": "0.1.0"` — verificato
- [x] `packages/sft-domain/package.json` analogo — verificato
- [x] `packages/sft-contracts/package.json` analogo — verificato
- [x] `packages/sft-domain/src/sft_domain/__version__.py` con `0.1.0` — verificato
- [x] `packages/sft-contracts/src/sft_contracts/__version__.py` con `0.1.0` — verificato
- [x] `package.json` root contiene `"workspaces"` con 3 packages — verificato
- [x] `python3 scripts/sync-python-versions.py` exits 0 — verificato (3 packages updated)
- [x] `.github/workflows/release.yml` contiene `changesets/action@v1` — verificato
- [x] `.github/workflows/release.yml` contiene `version: npm run version-packages` — verificato
- [x] `.github/workflows/release.yml` ha `permissions: contents: write` e `pull-requests: write` — verificato
- [x] `docs/contributing/release.md` contiene "changeset" e "linked" — verificato
- [x] `docs/contributing/release.md` documenta PyPI publish come deferred — verificato
- [x] YAML valido: `python3 -c "import yaml; yaml.safe_load(...)"` exits 0 — verificato
- [x] Commit `1984e6c` esiste — verificato via `git log`
- [x] Commit `89933bd` esiste — verificato via `git log`

## Self-Check: PASSED
