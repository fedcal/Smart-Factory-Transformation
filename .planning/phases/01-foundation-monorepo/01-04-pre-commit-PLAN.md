---
phase: 1
plan: 4
slug: pre-commit
type: execute
wave: 2
depends_on: ["01"]
files_modified:
  - .pre-commit-config.yaml
  - .commitlintrc.cjs
  - .commitlintrc.json
  - .github/workflows/pre-commit-check.yml
  - .gitleaks.toml
  - docs/contributing/commit-conventions.md
  - docs/contributing/pre-commit.md
  - package.json
autonomous: true
requirements: [PLAT-06]
tags: [foundation, infra, quality-gates, security, gitleaks]

must_haves:
  truths:
    - "`pre-commit run --all-files` esegue ruff format, ruff check, mypy --strict (solo `packages/sft-*`), eslint, prettier, gitleaks senza errori su repo pulito"
    - "`pre-commit run --all-files` con un file Python che ha import non usato fallisce con exit code != 0"
    - "Un commit con messaggio non-Conventional fallisce con exit code != 0 (commitlint stage commit-msg)"
    - "Un file contenente una stringa che matcha pattern gitleaks (es. AWS access key fittizia) fallisce con exit code != 0"
    - "Workflow `.github/workflows/pre-commit-check.yml` esegue lo stesso set di hook su ogni PR come required check"
    - "mypy --strict si applica ESCLUSIVAMENTE ai file in `packages/sft-*/` (Claude's Discretion)"
  artifacts:
    - path: ".pre-commit-config.yaml"
      provides: "Configurazione hook ruff/mypy/eslint/prettier/commitlint/gitleaks"
      contains: "ruff-pre-commit"
    - path: ".commitlintrc.cjs"
      provides: "Conventional Commits config con type-enum esteso"
    - path: ".github/workflows/pre-commit-check.yml"
      provides: "CI required check che riesegue pre-commit"
    - path: ".gitleaks.toml"
      provides: "Configurazione gitleaks con allowlist per fixture/test"
    - path: "docs/contributing/commit-conventions.md"
      provides: "Documentazione Conventional Commits + esempi"
  key_links:
    - from: ".pre-commit-config.yaml"
      to: "ruff, mypy, eslint, prettier, commitlint, gitleaks"
      via: "repos elenco con tag pinati"
      pattern: "rev:"
    - from: ".github/workflows/pre-commit-check.yml"
      to: "pre-commit/action@v3.0.1"
      via: "GitHub Action ufficiale"
      pattern: "pre-commit/action"
---

<objective>
Configurare la pipeline di quality gates locale (pre-commit) e CI (pre-commit-check.yml) coprendo Python (ruff format+check, mypy --strict su `packages/sft-*`), TypeScript/Angular (eslint, prettier), commit hygiene (commitlint Conventional Commits), e secret scanning (gitleaks). Tutti i hook sono pinati a versioni esatte. Soddisfa Phase Success Criterion #4: pre-commit hooks eseguiti su ogni commit fail-fast on violations.

Purpose: senza pre-commit + CI gate, il repository drifta in poche settimane. mypy --strict limitato a `packages/sft-*` (Claude's Discretion) bilancia rigore SDK con velocità dev sulle app. Gitleaks come safety net per T-1-03 secret hygiene.

Output: ogni commit locale e ogni PR superano gli stessi controlli; primo commit del repo passa pre-commit su repo pulito.
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
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| developer commit -> repo | rischio T-1-03 leak di secret in plaintext |
| commit message -> changelog | commit non-conventional rompono Changesets (plan 08) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-03 | Information Disclosure | secret hardcoded in source/config/env files | mitigate | gitleaks hook pre-commit (locale) + CI required check; pattern set v8.24.2 ufficiale; allowlist per file di fixture noti (`tests/license/`) |
| T-1-SC | Tampering | hook upstream (ruff-pre-commit, mirrors-prettier, gitleaks) | mitigate | tutti i `rev:` pinati a tag esatto (v0.11.10, v3.5.3, v8.24.2); `pre-commit autoupdate` controllato manualmente in PR |
</threat_model>

<tasks>

<task id="1-04-01" wave="2" type="auto">
  <name>Task 1: .pre-commit-config.yaml + .gitleaks.toml + .commitlintrc.cjs</name>
  <files>.pre-commit-config.yaml, .gitleaks.toml, .commitlintrc.cjs, package.json</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 5: Pre-commit Configuration, righe ~806-862)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: pre-commit framework, hook ruff/mypy/eslint/prettier/commitlint/gitleaks; mypy --strict solo su `packages/sft-*`)
  </read_first>
  <action>
    Creare `.pre-commit-config.yaml` con repos in ORDINE specifico:
    1. `https://github.com/astral-sh/ruff-pre-commit` rev `v0.11.10`, hooks: `ruff-format` (types_or: python,pyi) e `ruff` (args: `--fix`)
    2. `local` repo per mypy: hook `mypy-sft-packages` con `language: system`, `entry: uv run mypy --strict --config-file pyproject.toml`, `types: [python]`, `files: ^packages/sft-(agents|domain|contracts)/`, `pass_filenames: true` (NOTA: NON limitarsi a `packages/sft-` perché vogliamo evitare match parziali con altri prefissi; usare l'enum esplicito)
    3. `local` repo per eslint Angular: hook `eslint`, `language: node`, `entry: npx eslint --fix`, `types_or: [ts, tsx]`, `files: \\.(ts|tsx)$`, `exclude: ^(node_modules|dist|tmp|coverage)/`. Aggiungere `additional_dependencies: []` (verrà letto da `package.json`).
    4. `https://github.com/pre-commit/mirrors-prettier` rev `v3.5.3`, hook `prettier`, `types_or: [ts, tsx, json, yaml, markdown, scss, css, html]`, `exclude: ^(uv\\.lock|package-lock\\.json|pnpm-lock\\.yaml|tmp/)$`
    5. `https://github.com/alessandrojcm/commitlint-pre-commit-hook` rev `v9.18.0`, hook `commitlint`, `stages: [commit-msg]`, `additional_dependencies: ["@commitlint/config-conventional@19.5.0"]`
    6. `https://github.com/gitleaks/gitleaks` rev `v8.24.2`, hook `gitleaks` (default).
    7. `https://github.com/pre-commit/pre-commit-hooks` rev `v5.0.0`, hooks: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-json` (con `exclude: ^\\.changeset/`), `check-merge-conflict`, `check-added-large-files` (args: `--maxkb=1024`).

    Aggiungere a `package.json` (modificare quello esistente da plan 01) i devDependencies:
    - `"@commitlint/cli": "19.5.0"`
    - `"@commitlint/config-conventional": "19.5.0"`
    - `"eslint": "9.x.x"` (allineato a Nx 20)
    - `"prettier": "3.5.3"` (già presente da plan 01)
    Eseguire `npm install --legacy-peer-deps`.

    Creare `.commitlintrc.cjs`:
    ```js
    module.exports = {
      extends: ["@commitlint/config-conventional"],
      rules: {
        "type-enum": [2, "always",
          ["build","chore","ci","docs","feat","fix","perf","refactor","revert","style","test"]
        ],
        "scope-case": [2, "always", "kebab-case"],
        "header-max-length": [2, "always", 100],
        "subject-case": [0],  // permettere maiuscole iniziali in italiano
        "body-max-line-length": [1, "always", 120]
      }
    };
    ```
    Creare anche `.commitlintrc.json` minimale (fallback per il hook che lo cerca):
    ```json
    {"extends": ["@commitlint/config-conventional"]}
    ```

    Creare `.gitleaks.toml`:
    ```toml
    title = "SFT gitleaks config"
    [extend]
      useDefault = true
    [allowlist]
      description = "Allow known fixture files"
      paths = [
        '''tests/license/.*''',
        '''docs/.*\.md''',
        '''infra/compose/\.env\.example''',
        '''LICENSE-EXCEPTIONS\.md'''
      ]
      regexes = [
        '''<CHANGE_ME[^>]*>''',
        '''_dev_pass''',
        '''0{32,}''',  # placeholder hex zero in .env.example
      ]
    ```
  </action>
  <acceptance_criteria>
    - `.pre-commit-config.yaml` esiste e contiene `ruff-pre-commit`, `mirrors-prettier`, `gitleaks`, `commitlint`
    - `.pre-commit-config.yaml` contiene `rev: v0.11.10` (ruff) e `rev: v8.24.2` (gitleaks)
    - Il hook mypy ha `files: ^packages/sft-(agents|domain|contracts)/` (regex precisa)
    - `.commitlintrc.cjs` esiste e contiene `@commitlint/config-conventional`
    - `.gitleaks.toml` esiste e contiene `useDefault = true`
    - `package.json` contiene `"@commitlint/cli"` e `"@commitlint/config-conventional"`
    - `python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))"` exits 0
    - `pre-commit run --all-files --config .pre-commit-config.yaml || true` esegue senza crash di parsing (i fallimenti di lint sono accettabili in questa fase)
  </acceptance_criteria>
</task>

<task id="1-04-02" wave="2" type="auto">
  <name>Task 2: .github/workflows/pre-commit-check.yml + docs contributing</name>
  <files>.github/workflows/pre-commit-check.yml, docs/contributing/commit-conventions.md, docs/contributing/pre-commit.md</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 5 pre-commit-check.yml righe ~864-878; Don't Hand-Roll)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: required check)
  </read_first>
  <action>
    Creare `.github/workflows/pre-commit-check.yml`:
    ```yaml
    name: Pre-commit Check
    on:
      pull_request:
      push:
        branches: [main]
    jobs:
      pre-commit:
        runs-on: ubuntu-latest
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
          - name: Install uv
            uses: astral-sh/setup-uv@v5
            with:
              version: "0.6"
              enable-cache: true
          - name: Install npm deps
            run: npm ci
          - name: Install Python deps
            run: uv sync --all-packages
          - name: Run pre-commit
            uses: pre-commit/action@v3.0.1
            with:
              extra_args: --all-files --show-diff-on-failure
    ```

    Creare `docs/contributing/commit-conventions.md` (bilingue: IT + sezione EN summary in coda) che documenta:
    - Formato Conventional Commits: `<type>(<scope>): <subject>`
    - Type enum: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`
    - Scope: kebab-case nome progetto Nx (es. `feat(sft-agents): ...`, `fix(svc-orchestrator): ...`)
    - Esempi reali (`feat(sft-agents): add Tool base class`, `fix(svc-ot-bridge): handle reconnect on NATS disconnect`, `docs(phase-1): update CONTEXT.md`)
    - Breaking changes: `feat(api)!: rename endpoint /v1/approve to /v2/approve`
    - Body lines max 120 char
    - Link a Conventional Commits 1.0 spec.

    Creare `docs/contributing/pre-commit.md` che documenta:
    - Installazione: `pip install pre-commit && pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg`
    - Run manuale: `pre-commit run --all-files`
    - Skip temporaneo (sconsigliato): `git commit --no-verify` o `SKIP=mypy-sft-packages git commit ...`
    - Update hook versions: `pre-commit autoupdate` (richiede PR review prima di mergeare)
    - Troubleshooting: `pre-commit clean` per reset cache; eslint che non trova `node_modules` -> `npm ci`.
  </action>
  <acceptance_criteria>
    - `.github/workflows/pre-commit-check.yml` esiste e contiene `pre-commit/action@v3.0.1`
    - `.github/workflows/pre-commit-check.yml` contiene `setup-node@v4` con `node-version: 20`
    - `.github/workflows/pre-commit-check.yml` contiene `setup-python@v5` con `python-version: '3.12'`
    - `docs/contributing/commit-conventions.md` esiste e contiene la stringa "Conventional Commits"
    - `docs/contributing/commit-conventions.md` contiene almeno 3 esempi di commit message
    - `docs/contributing/pre-commit.md` esiste e contiene `pre-commit install`
    - `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pre-commit-check.yml'))"` exits 0
  </acceptance_criteria>
</task>

<task id="1-04-03" wave="2" type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Verifica funzionale pre-commit locale + fixture violazioni</name>
  <what-built>Pre-commit framework installato con 7 hook (ruff format, ruff check, mypy-sft-packages, eslint, prettier, commitlint, gitleaks) e workflow CI mirror. Configurazione pinata a versioni esatte.</what-built>
  <how-to-verify>
    1. Installazione:
       ```bash
       pip install pre-commit==4.6.0
       pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg
       pre-commit run --all-files
       ```
       Atteso: exit 0 su repo pulito (post-Plan 01..03 merged).
    2. Test violazione Python (import non usato):
       ```bash
       echo "import os" > /tmp/test-bad.py
       cp /tmp/test-bad.py packages/sft-agents/src/sft_agents/_bad.py
       git add packages/sft-agents/src/sft_agents/_bad.py
       pre-commit run --files packages/sft-agents/src/sft_agents/_bad.py
       ```
       Atteso: ruff segnala F401 (unused import), exit != 0. Cleanup: `git restore --staged && rm packages/sft-agents/src/sft_agents/_bad.py`.
    3. Test violazione commit message:
       ```bash
       echo "test" > /tmp/dummy && git add /tmp/dummy 2>/dev/null
       git commit -m "broken commit message" --allow-empty
       ```
       Atteso: commitlint blocca con messaggio "subject may not be empty" o "type may not be empty".
    4. Test gitleaks:
       ```bash
       echo 'AWS_SECRET_ACCESS_KEY="AKIAIOSFODNN7EXAMPLE"' > /tmp/leak.env
       cp /tmp/leak.env scripts/_leak_test.env
       git add scripts/_leak_test.env
       pre-commit run gitleaks --files scripts/_leak_test.env
       ```
       Atteso: gitleaks segnala secret, exit != 0. Cleanup: `git restore --staged && rm scripts/_leak_test.env`.
  </how-to-verify>
  <resume-signal>Type "approved" se tutti i 4 test passano come atteso; altrimenti descrivere quale step fallisce.</resume-signal>
</task>

</tasks>

<verification>
1. `python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))"` exits 0
2. `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pre-commit-check.yml'))"` exits 0
3. `grep -E '^\s+rev:' .pre-commit-config.yaml | grep -v "^\s*#" | wc -l` >= 6 (almeno 6 rev pinati)
4. `grep -c "Conventional Commits" docs/contributing/commit-conventions.md` >= 1
5. CI mirror: il workflow `.github/workflows/pre-commit-check.yml` su PR esegue gli stessi hook che girerebbero localmente.
</verification>

<success_criteria>
- pre-commit run --all-files passa su repo pulito (Phase Success Criterion #4)
- mypy --strict applicato SOLO a `packages/sft-(agents|domain|contracts)/` (Claude's Discretion)
- commitlint forza Conventional Commits
- gitleaks come safety net per T-1-03
- CI required check `pre-commit-check.yml` ESPONE gli stessi gate
</success_criteria>

<output>
Create `.planning/phases/01-foundation-monorepo/01-04-SUMMARY.md` quando done.
</output>
