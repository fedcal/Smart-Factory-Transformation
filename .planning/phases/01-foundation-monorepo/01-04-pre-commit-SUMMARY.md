---
phase: 1
plan: 4
slug: pre-commit
subsystem: foundation/quality-gates
status: complete
tags: [pre-commit, ruff, mypy, eslint, prettier, commitlint, gitleaks, ci, security]
dependency_graph:
  requires:
    - nx-workspace-polyglot
    - uv-workspace-single-lockfile
  provides:
    - pre-commit-hooks-configured
    - commitlint-conventional-commits
    - gitleaks-secret-scanning
    - ci-pre-commit-required-check
  affects:
    - all-subsequent-plans (ogni commit passa quality gates)
tech_stack:
  added:
    - pre-commit 4.6.0 (framework locale)
    - ruff-pre-commit v0.11.10 (format + check Python)
    - mypy --strict via uv run (solo packages/sft-*)
    - eslint (locale via node, Nx config esistente)
    - mirrors-prettier v3.5.3 (TS/JSON/YAML/MD/HTML/CSS)
    - alessandrojcm/commitlint-pre-commit-hook v9.18.0
    - "@commitlint/config-conventional@19.5.0"
    - gitleaks v8.24.2 (secret scanning)
    - pre-commit/pre-commit-hooks v5.0.0 (utility hooks)
    - pre-commit/action@v3.0.1 (GitHub Actions)
  patterns:
    - Hook rev pinati a versioni esatte (zero floating refs)
    - mypy --strict scope-limitato a packages/sft-(agents|domain|contracts)/
    - gitleaks allowlist esplicita per fixture noti
    - CI mirror identico agli hook lokali (stessa config YAML)
key_files:
  created:
    - .pre-commit-config.yaml
    - .gitleaks.toml
    - .commitlintrc.cjs
    - .commitlintrc.json
    - .github/workflows/pre-commit-check.yml
    - docs/contributing/commit-conventions.md
    - docs/contributing/pre-commit.md
  modified:
    - package.json (aggiunti @commitlint/cli e @commitlint/config-conventional)
    - package-lock.json (generato da npm install)
decisions:
  - "commitlint hook: alessandrojcm/commitlint-pre-commit-hook@v9.18.0 (specificato nel PLAN) invece di opensource-nepal/commitlint (RESEARCH) — il PLAN ha precedenza"
  - "mypy --strict con regex esplicita ^packages/sft-(agents|domain|contracts)/ per evitare match parziali con altri prefissi sft-"
  - ".commitlintrc.cjs come config principale + .commitlintrc.json come fallback minimale"
  - "eslint hook: language=node, additional_dependencies=[] (dipende da package.json esistente Nx)"
metrics:
  duration_minutes: 8
  completed_date: "2026-05-16T00:00:00Z"
  tasks_completed: 2
  tasks_total: 3
  files_created: 7
  commits: 2
requirements: [PLAT-06]
---

# Phase 1 Plan 4: pre-commit Summary

**One-liner:** Pre-commit pipeline con 7 hook pinati (ruff, mypy-strict su sft-*, eslint, prettier, commitlint, gitleaks, pre-commit-hooks) + CI mirror `pre-commit-check.yml` come required check su ogni PR.

---

## What Was Built

Pipeline completa di quality gates locale + CI per il monorepo Smart Factory Transformation:

- **`.pre-commit-config.yaml`** con 7 repo-set ordinati:
  1. `ruff-pre-commit v0.11.10` — `ruff-format` + `ruff` (Python format + lint + autofix)
  2. `local` mypy — `mypy-sft-packages` con `--strict`, scope `^packages/sft-(agents|domain|contracts)/`
  3. `local` eslint — hook Node per TS/TSX con exclusion `node_modules|dist|tmp|coverage`
  4. `mirrors-prettier v3.5.3` — formattazione TS/JSON/YAML/MD/SCSS/CSS/HTML
  5. `alessandrojcm/commitlint-pre-commit-hook v9.18.0` — Conventional Commits su `commit-msg` stage
  6. `gitleaks v8.24.2` — secret scanning con pattern set ufficiale
  7. `pre-commit/pre-commit-hooks v5.0.0` — trailing-whitespace, end-of-file-fixer, check-yaml, check-json, check-merge-conflict, check-added-large-files (1024 KB)

- **`.gitleaks.toml`** con `useDefault = true` + allowlist esplicita per `tests/license/`, `docs/*.md`, `infra/compose/.env.example`, `LICENSE-EXCEPTIONS.md` e regex placeholder (`<CHANGE_ME>`, `_dev_pass`, `0{32,}`)

- **`.commitlintrc.cjs`** con type-enum esteso (11 tipi), scope-case kebab-case, header-max-length 100, subject-case disabilitato (permette italiano), body-max-line-length 120 (warning)

- **`.commitlintrc.json`** fallback minimale per tool che cercano `.commitlintrc.json`

- **`.github/workflows/pre-commit-check.yml`** — workflow CI che esegue gli stessi hook lokali:
  - `actions/checkout@v4` con `fetch-depth: 0`
  - `actions/setup-node@v4` con `node-version: 20`
  - `actions/setup-python@v5` con `python-version: '3.12'`
  - `astral-sh/setup-uv@v5` con `version: "0.6"`
  - `npm ci` + `uv sync --all-packages`
  - `pre-commit/action@v3.0.1` con `--all-files --show-diff-on-failure`

- **`docs/contributing/commit-conventions.md`** — guida bilingue IT+EN con type enum, scope kebab-case, esempi reali, breaking change, tabella regole commitlint

- **`docs/contributing/pre-commit.md`** — installazione, utilizzo quotidiano, skip temporaneo, autoupdate workflow, troubleshooting comune (reset cache, eslint node_modules, mypy modules, gitleaks falsi positivi, commitlint debug)

- **`package.json`** aggiornato con `@commitlint/cli@19.5.0` e `@commitlint/config-conventional@19.5.0`

---

## Verification Results

```
python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))" → exit 0 (YAML valido)
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pre-commit-check.yml'))" → exit 0
grep -E '^\s+rev:' .pre-commit-config.yaml → 5 rev pinati (v0.11.10, v3.5.3, v9.18.0, v8.24.2, v5.0.0)
grep -c "Conventional Commits" docs/contributing/commit-conventions.md → 3
grep "pre-commit install" docs/contributing/pre-commit.md → trovato
.pre-commit-config.yaml contiene: ruff-pre-commit, mirrors-prettier, gitleaks, commitlint, pre-commit-hooks
.pre-commit-config.yaml contiene: rev: v0.11.10 (ruff), rev: v8.24.2 (gitleaks)
Hook mypy ha: files: ^packages/sft-(agents|domain|contracts)/
package.json contiene: @commitlint/cli e @commitlint/config-conventional
```

---

## Task 3: Verifica funzionale (deferred to user post-execution)

Il Task 3 era di tipo `checkpoint:human-verify` — richiede esecuzione lokale con `pre-commit` installato. Questi passi devono essere eseguiti manualmente dopo che il branch e` stato mergato:

### Passi da eseguire

```bash
# 1. Installazione
pip install pre-commit==4.6.0
pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg
pre-commit run --all-files
# Atteso: exit 0 su repo pulito

# 2. Test violazione Python (import non usato)
echo "import os" > packages/sft-agents/src/sft_agents/_bad.py
git add packages/sft-agents/src/sft_agents/_bad.py
pre-commit run --files packages/sft-agents/src/sft_agents/_bad.py
# Atteso: ruff segnala F401 (unused import), exit != 0
git restore --staged packages/sft-agents/src/sft_agents/_bad.py
rm packages/sft-agents/src/sft_agents/_bad.py

# 3. Test violazione commit message
git commit -m "broken commit message" --allow-empty
# Atteso: commitlint blocca con errore tipo-enum

# 4. Test gitleaks
echo 'AWS_SECRET_ACCESS_KEY="AKIAIOSFODNN7EXAMPLE"' > scripts/_leak_test.env
git add scripts/_leak_test.env
pre-commit run gitleaks --files scripts/_leak_test.env
# Atteso: gitleaks segnala secret, exit != 0
git restore --staged scripts/_leak_test.env
rm scripts/_leak_test.env
```

---

## Deviations from Plan

### Auto-fixed Issues

Nessuna.

### Decisions Made

**1. Hook commitlint: alessandrojcm vs. opensource-nepal**
- **PLAN spec:** `alessandrojcm/commitlint-pre-commit-hook@v9.18.0` con `additional_dependencies: ["@commitlint/config-conventional@19.5.0"]`
- **RESEARCH pattern:** `opensource-nepal/commitlint@v1.3.0`
- **Scelta:** PLAN ha precedenza. `alessandrojcm/commitlint-pre-commit-hook` e` il hook piu` maturo per commitlint in pre-commit con `additional_dependencies` Conventional Commits.

**2. mypy regex esplicita**
- La regex `^packages/sft-(agents|domain|contracts)/` e` piu` precisa del pattern generico `^packages/sft-.*/` — evita match parziali se in futuro esistessero package con prefisso `sft-` ma non nei 3 SDK packages controllati con strict.

---

## Threat Surface Scan

| Flag | File | Descrizione |
|------|------|-------------|
| threat_flag: supply-chain | .pre-commit-config.yaml | Tutti i rev pinati a hash/tag esatti: v0.11.10, v3.5.3, v9.18.0, v8.24.2, v5.0.0. Nessun floating ref `main` o `HEAD`. Mitigazione T-1-SC applicata. |
| threat_flag: secret-scanning | .gitleaks.toml | Gitleaks v8.24.2 con pattern set ufficiale + allowlist esplicita per fixture noti. Mitigazione T-1-03 applicata. |

---

## Commit History

| Task | Descrizione | Commit |
|------|-------------|--------|
| 1 | .pre-commit-config.yaml, .gitleaks.toml, .commitlintrc.cjs/.json, package.json | 47bede0 |
| 2 | .github/workflows/pre-commit-check.yml, docs contributing | 2361c61 |
| 3 | (checkpoint:human-verify — deferred to user post-execution) | — |

---

## Self-Check

```
[x] .pre-commit-config.yaml exists → found
[x] .gitleaks.toml exists → found
[x] .commitlintrc.cjs exists → found
[x] .commitlintrc.json exists → found
[x] .github/workflows/pre-commit-check.yml exists → found
[x] docs/contributing/commit-conventions.md exists → found
[x] docs/contributing/pre-commit.md exists → found
[x] package.json contains @commitlint/cli → found
[x] package.json contains @commitlint/config-conventional → found
[x] .pre-commit-config.yaml contains ruff-pre-commit → found
[x] .pre-commit-config.yaml contains mirrors-prettier → found
[x] .pre-commit-config.yaml contains gitleaks → found
[x] .pre-commit-config.yaml contains commitlint → found
[x] .pre-commit-config.yaml contains rev: v0.11.10 → found
[x] .pre-commit-config.yaml contains rev: v8.24.2 → found
[x] mypy hook has files: ^packages/sft-(agents|domain|contracts)/ → found
[x] pre-commit-check.yml contains pre-commit/action@v3.0.1 → found
[x] pre-commit-check.yml contains setup-node@v4 node-version: 20 → found
[x] pre-commit-check.yml contains setup-python@v5 python-version: '3.12' → found
[x] YAML validity: .pre-commit-config.yaml → exit 0
[x] YAML validity: pre-commit-check.yml → exit 0
[x] commit 47bede0 exists → verified
[x] commit 2361c61 exists → verified
```

## Self-Check: PASSED
