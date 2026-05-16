---
phase: 1
plan: 1
slug: nx-workspace
type: execute
wave: 1
depends_on: []
files_modified:
  - nx.json
  - package.json
  - package-lock.json
  - pnpm-workspace.yaml
  - pyproject.toml
  - .gitignore
  - .nvmrc
  - .python-version
  - .tool-versions
  - apps/orchestrator/pyproject.toml
  - apps/orchestrator/project.json
  - apps/orchestrator/src/svc_orchestrator/__init__.py
  - apps/api-gateway/pyproject.toml
  - apps/api-gateway/project.json
  - apps/api-gateway/src/svc_api_gateway/__init__.py
  - apps/factory-ui/project.json
  - apps/factory-ui/server.ts
  - apps/factory-ui/src/main.ts
  - apps/factory-ui/src/main.server.ts
  - apps/factory-ui/src/app/app.config.ts
  - apps/factory-ui/src/app/app.config.server.ts
  - apps/factory-ui/src/app/app.routes.ts
  - apps/agents/ops/operator-assistant/pyproject.toml
  - apps/agents/ops/operator-assistant/project.json
  - apps/agents/ops/operator-assistant/src/ops_operator_assistant/__init__.py
  - apps/agents/ops/production-planner/pyproject.toml
  - apps/agents/ops/production-planner/project.json
  - apps/agents/ops/quality-inspector/pyproject.toml
  - apps/agents/ops/quality-inspector/project.json
  - apps/agents/ops/anomaly-detector/pyproject.toml
  - apps/agents/ops/anomaly-detector/project.json
  - apps/agents/maintenance/predictive-maintenance/pyproject.toml
  - apps/agents/maintenance/predictive-maintenance/project.json
  - apps/agents/maintenance/rca-specialist/pyproject.toml
  - apps/agents/maintenance/rca-specialist/project.json
  - apps/agents/maintenance/maintenance-coach/pyproject.toml
  - apps/agents/maintenance/maintenance-coach/project.json
  - apps/agents/maintenance/downtime-analyzer/pyproject.toml
  - apps/agents/maintenance/downtime-analyzer/project.json
  - apps/agents/knowledge/knowledge-curator/pyproject.toml
  - apps/agents/knowledge/knowledge-curator/project.json
  - apps/agents/knowledge/training-coach/pyproject.toml
  - apps/agents/knowledge/training-coach/project.json
  - apps/agents/knowledge/shift-handover/pyproject.toml
  - apps/agents/knowledge/shift-handover/project.json
  - apps/agents/knowledge/documentation-synthesizer/pyproject.toml
  - apps/agents/knowledge/documentation-synthesizer/project.json
  - apps/agents/supply/inventory-manager/pyproject.toml
  - apps/agents/supply/inventory-manager/project.json
  - apps/agents/supply/energy-optimizer/pyproject.toml
  - apps/agents/supply/energy-optimizer/project.json
  - apps/agents/supply/cost-analyzer/pyproject.toml
  - apps/agents/supply/cost-analyzer/project.json
  - apps/agents/supply/demand-forecaster/pyproject.toml
  - apps/agents/supply/demand-forecaster/project.json
  - packages/sft-agents/pyproject.toml
  - packages/sft-agents/project.json
  - packages/sft-agents/src/sft_agents/__init__.py
  - packages/sft-agents/src/sft_agents/__version__.py
  - packages/sft-domain/pyproject.toml
  - packages/sft-domain/project.json
  - packages/sft-domain/src/sft_domain/__init__.py
  - packages/sft-contracts/pyproject.toml
  - packages/sft-contracts/project.json
  - packages/sft-contracts/src/sft_contracts/__init__.py
  - services/ot-bridge/pyproject.toml
  - services/ot-bridge/project.json
  - services/ot-bridge/src/svc_ot_bridge/__init__.py
  - simulators/sim-textile/pyproject.toml
  - simulators/sim-textile/project.json
  - simulators/sim-textile/src/sim_textile/__init__.py
  - scripts/validate-nx-graph.py
  - scripts/sync-python-versions.py
  - uv.lock
  - docs/contributing/toolchain.md
autonomous: true
requirements: [PLAT-01, PLAT-02, PLAT-03]
tags: [foundation, infra, nx, uv, monorepo]

must_haves:
  truths:
    - "`nx graph` mostra tutti i progetti (3 packages, 18 apps, 1 service, 1 simulator)"
    - "`uv sync --all-packages` completa senza errori e produce uv.lock"
    - "`nx affected` rileva il cambio in packages/sft-contracts e rebuilda apps/factory-ui (via implicitDependencies)"
    - "Esistono le 6 root-folder: apps/, packages/, services/, docs/, infra/, simulators/"
    - "Tutte le directory matchate da [tool.uv.workspace] members contengono un pyproject.toml valido"
  artifacts:
    - path: "nx.json"
      provides: "Configurazione workspace Nx 20.x con plugin @nxlv/python e @nx/angular, Nx Cloud disabled by default"
      contains: '"@nxlv/python"'
    - path: "pyproject.toml"
      provides: "Root uv workspace con tutti i members"
      contains: "[tool.uv.workspace]"
    - path: "package.json"
      provides: "Root Node package con devDependencies Nx + @nxlv/python + @nx/angular"
      contains: '"nx":'
    - path: "scripts/validate-nx-graph.py"
      provides: "Verifica edges Python->TS richiesti nel dep graph"
    - path: "apps/factory-ui/project.json"
      provides: "Angular SSR app con implicitDependencies su sft-contracts"
      contains: '"implicitDependencies"'
  key_links:
    - from: "apps/factory-ui/project.json"
      to: "packages/sft-contracts"
      via: "implicitDependencies"
      pattern: '"implicitDependencies".*"sft-contracts"'
    - from: "apps/api-gateway/project.json"
      to: "packages/sft-contracts, packages/sft-agents, packages/sft-domain"
      via: "implicitDependencies"
      pattern: '"implicitDependencies"'
    - from: "pyproject.toml"
      to: "uv workspace members"
      via: "[tool.uv.workspace].members"
      pattern: "members"
---

<objective>
Creare il monorepo Nx polyglot (Python+Angular) fondazionale che ogni altra fase del progetto userà. Output: workspace Nx 20.x con plugin @nxlv/python 21.x e @nx/angular, uv workspace single-lockfile, 6 root-folder strutturali, 16 directory placeholder per agenti, 3 packages (sft-agents, sft-domain, sft-contracts), apps deployabili (orchestrator, api-gateway, factory-ui SSR), service ot-bridge, simulator sim-textile, edges Python↔TypeScript dichiarati via implicitDependencies, script di validazione dep graph, Nx Cloud disabilitato by default ma env-gated. Tutto pinato a versioni esatte dalla RESEARCH.

Purpose: senza workspace coerente, `nx affected` non funziona, le altre fasi non possono scalare la CI selettiva, e i 16 agenti non hanno un home directory consistente. Soddisfa success criterion #2 (Phase): `nx affected --target=test` risolve correttamente le dipendenze Python↔TypeScript.

Output: workspace navigabile, `npm ci && uv sync` funzionanti, `nx graph` mostra dep tree corretto, primo commit verificato con `make test` placeholder verde.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation-monorepo/01-CONTEXT.md
@.planning/phases/01-foundation-monorepo/01-RESEARCH.md
@CLAUDE.md
</context>

<wave_0_prerequisites>
Strumenti necessari sulla developer machine (documentati in `docs/contributing/toolchain.md`):
- Node.js 20+ (verifica: `node -v` deve essere >= 20)
- pnpm 9+ (verifica: `pnpm -v`) — opzionale, npm 11+ accettato
- uv 0.11+ (>= 0.6) (verifica: `uv --version`)
- Python 3.12 (verifica: `python3.12 --version`)
- docker engine v29+ con compose plugin (verifica: `docker compose version`)
- helm 3.x (verifica: `helm version`)
- k3d (per test locale opzionale; richiesto solo per `make helm-test`)

Se assente, il task 1-01-01 si limita a documentare il requisito in `docs/contributing/toolchain.md`; non esegue install automatica sulla macchina utente.
</wave_0_prerequisites>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| developer machine -> repo | codice committato che entrerà in supply-chain; rischio typosquat e dipendenze non legittime |
| repo -> npm/PyPI install | install di dipendenze esterne (Nx plugins, @changesets, mkdocs-*) richiede legitimacy gate |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-02 | Tampering | npm/PyPI install (nx, @nxlv/python, @nx/angular, @changesets/cli, pre-commit, mkdocs-material) | mitigate | Tutti i pacchetti sono già stati validati nel Package Legitimacy Audit di RESEARCH.md (riga 175-186); usare versioni esatte: `nx@20.8.4`, `@nxlv/python@21.3.1`, `@nx/angular@22.7.2`, `@changesets/cli@2.31.0` — pinate in `package.json` con caret stretto (`~`); npm `--ignore-scripts` non applicabile per Nx (richiede postinstall) |
| T-1-SC | Tampering | install di pacchetti tutti `[OK]` da Audit | mitigate | Audit completo nel RESEARCH.md; nessun pacchetto `[ASSUMED]` o `[SUS]` -> nessun checkpoint blocking-human richiesto in questo plan |
</threat_model>

<tasks>

<task id="1-01-01" wave="1" type="auto">
  <name>Task 1: Documentare toolchain prerequisiti e scaffold root-folder</name>
  <files>docs/contributing/toolchain.md, .gitignore, .nvmrc, .python-version, .tool-versions, apps/.gitkeep, packages/.gitkeep, services/.gitkeep, docs/.gitkeep, infra/.gitkeep, simulators/.gitkeep</files>
  <read_first>
    - CLAUDE.md (technology stack section)
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Environment Availability section, righe ~1726-1748)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-01, Claude's Discretion: Python toolchain Python 3.12)
  </read_first>
  <action>
    Creare `docs/contributing/toolchain.md` che elenca i prerequisiti tool con versioni minime e comandi di verifica (Node 20+, npm 11+, uv 0.6+, Python 3.12, Docker 29+ con compose v2, helm 3.x, k3d opzionale). Includere link a installer ufficiali. Creare `.nvmrc` con contenuto `20`, `.python-version` con `3.12`, `.tool-versions` (asdf) con `python 3.12.7` e `nodejs 20.18.0`. Creare `.gitignore` completo: `node_modules/`, `.nx/cache/`, `.venv/`, `__pycache__/`, `*.pyc`, `dist/`, `tmp/`, `.env`, `.env.local`, `coverage/`, `*.log`, `.DS_Store`. Creare le 6 root-folder vuote con `.gitkeep` (per D-01): `apps/`, `packages/`, `services/`, `docs/`, `infra/`, `simulators/`. Documentare in `toolchain.md` la sezione "Quick start" con sequenza: `nvm use && pip install uv pre-commit && npm ci && uv sync`.
  </action>
  <acceptance_criteria>
    - `docs/contributing/toolchain.md` esiste e contiene le righe `Node.js 20`, `Python 3.12`, `uv >= 0.6`, `Docker 29+`, `helm 3.x`
    - `.nvmrc` esiste e contiene esattamente `20`
    - `.python-version` esiste e contiene esattamente `3.12`
    - `.gitignore` contiene almeno: `node_modules/`, `.nx/cache/`, `.venv/`, `dist/`, `.env`
    - Esistono le directory `apps/`, `packages/`, `services/`, `docs/`, `infra/`, `simulators/` ognuna con `.gitkeep`
    - `command -v node && node -v | grep -E "^v(2[0-9]|[3-9][0-9])"` exits 0
  </acceptance_criteria>
</task>

<task id="1-01-02" wave="1" type="auto">
  <name>Task 2: Bootstrap Nx workspace e plugins (nx.json, package.json)</name>
  <files>nx.json, package.json, package-lock.json, pnpm-workspace.yaml, scripts/validate-nx-graph.py, scripts/sync-python-versions.py</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 1: Nx 20.x Polyglot Workspace Bootstrap, righe ~296-372; Pitfall 4 @nxlv/python Python->TS deps)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-05 naming, Claude's Discretion: Nx Cloud disabled by default env-gated)
    - CLAUDE.md (sezione Recommended Stack: nx 20.x, @nxlv/python 21.x, @nx/angular pinata a major Nx 20)
  </read_first>
  <action>
    Creare `package.json` root con campo `"name": "smart-factory-transformation"`, `"private": true`, `"packageManager": "npm@11.6.3"`, e `devDependencies` esatte: `"nx": "20.8.4"`, `"@nxlv/python": "21.3.1"`, `"@nx/angular": "20.8.1"` (versione major-allineata a Nx 20; verificare con `npm view @nx/angular@20 version` durante esecuzione e usare l'ultima 20.x se 20.8.1 non esiste — NON usare la 22.x indicata in RESEARCH perché disallinea i peer deps con Nx 20). Aggiungere `"@nx/eslint": "20.8.1"`, `"@nx/jest": "20.8.1"`, `"@nx/js": "20.8.1"`, `"@nx/workspace": "20.8.1"`, `"typescript": "5.5.4"`, `"prettier": "3.5.3"`, `"@changesets/cli": "2.31.0"`. Aggiungere campi `scripts`: `"affected": "nx affected"`, `"graph": "nx graph"`, `"format": "nx format:write"`. Eseguire `npm install --legacy-peer-deps` per generare `package-lock.json`. Creare `pnpm-workspace.yaml` vuoto con `packages: []` (non usato attivamente: pnpm dichiarato come opzione futura, npm primary). Creare `nx.json` con:
    - `"$schema": "./node_modules/nx/schemas/nx-schema.json"`
    - `"defaultBase": "main"`
    - `"plugins"`: `[{"plugin": "@nxlv/python", "options": {"packageManager": "uv"}}, "@nx/angular/plugin"]`
    - `"targetDefaults"`: `{"build": {"cache": true, "dependsOn": ["^build"]}, "test": {"cache": true}, "lint": {"cache": true}}`
    - `"namedInputs"`: `{"default": ["{projectRoot}/**/*", "sharedGlobals"], "sharedGlobals": ["{workspaceRoot}/nx.json"]}`
    - `"nxCloudAccessToken": "${NX_CLOUD_ACCESS_TOKEN}"` ONLY come placeholder esempio nel commento; il file `nx.json` finale NON deve contenere il token attivo. Nx Cloud è disabilitato di default — se l'utente vuole abilitarlo deve impostare la env var. NON eseguire `npx nx connect`. Per evitare prompts di telemetry: aggiungere `"neverConnectToCloud": true` se supportato dalla versione, altrimenti documentare in `toolchain.md`.
    Creare `scripts/validate-nx-graph.py` esatto come nel Pattern Code Examples di RESEARCH (righe 1421-1447) con REQUIRED_EDGES `[("ui-factory", "sft-contracts"), ("svc-api-gateway", "sft-contracts"), ("svc-api-gateway", "sft-agents"), ("svc-api-gateway", "sft-domain"), ("svc-orchestrator", "sft-agents")]`. Creare `scripts/sync-python-versions.py` come da RESEARCH Pattern 9 (righe 1217-1238): legge `version` da ciascun `packages/*/package.json` (se presente) e aggiorna `__version__.py` corrispondente.
  </action>
  <acceptance_criteria>
    - `package.json` contiene `"nx": "20.8.4"` e `"@nxlv/python": "21.3.1"` (versioni esatte, NON range con `^`)
    - `nx.json` contiene la stringa `"@nxlv/python"` e la stringa `"@nx/angular/plugin"`
    - `nx.json` NON contiene un token NX Cloud hard-coded (grep `-v '^#' nx.json | grep -E '"nxCloudAccessToken":\s*"nxc_'` esce 1)
    - `npm ci` completa senza errori (oppure `npm install --legacy-peer-deps` se ci sono peer dep conflicts)
    - `npx nx --version` stampa una versione `20.x`
    - `python3 scripts/validate-nx-graph.py --help` o l'esecuzione manuale documenta i required edges
    - File `scripts/validate-nx-graph.py` contiene la riga `REQUIRED_EDGES`
  </acceptance_criteria>
</task>

<task id="1-01-03" wave="1" type="auto">
  <name>Task 3: uv workspace root pyproject.toml con tutti i members</name>
  <files>pyproject.toml</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 2: uv Workspace Root pyproject.toml, righe ~374-417; Pitfall 3 uv workspace nested paths; Code Examples sezione "uv workspace pyproject.toml root completo" righe ~1449-1491)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: single root pyproject.toml con [tool.uv.workspace], lockfile unico, members glob)
  </read_first>
  <action>
    Creare root `pyproject.toml` (per D-01..D-06 e Claude's Discretion uv workspace strategy):
    - `[project]`: `name = "smart-factory-transformation"`, `version = "0.0.0"`, `requires-python = ">=3.12,<3.13"`, `description = "Smart Factory Transformation - workspace root"`
    - `[tool.uv.workspace]` members lista ESPLICITA (NON glob `*` per ridurre rischio Pitfall 3): elencare uno-a-uno tutti i 16 path agente, i 3 package, i 2 app top-level (orchestrator, api-gateway), il service ot-bridge, il simulator sim-textile. Esempio:
      ```
      members = [
        "packages/sft-agents",
        "packages/sft-domain",
        "packages/sft-contracts",
        "apps/orchestrator",
        "apps/api-gateway",
        "apps/agents/ops/operator-assistant",
        "apps/agents/ops/production-planner",
        "apps/agents/ops/quality-inspector",
        "apps/agents/ops/anomaly-detector",
        "apps/agents/maintenance/predictive-maintenance",
        "apps/agents/maintenance/rca-specialist",
        "apps/agents/maintenance/maintenance-coach",
        "apps/agents/maintenance/downtime-analyzer",
        "apps/agents/knowledge/knowledge-curator",
        "apps/agents/knowledge/training-coach",
        "apps/agents/knowledge/shift-handover",
        "apps/agents/knowledge/documentation-synthesizer",
        "apps/agents/supply/inventory-manager",
        "apps/agents/supply/energy-optimizer",
        "apps/agents/supply/cost-analyzer",
        "apps/agents/supply/demand-forecaster",
        "services/ot-bridge",
        "simulators/sim-textile",
      ]
      ```
    - `[tool.uv]`: `dev-dependencies = ["pre-commit>=4.6", "pytest>=8.0", "pytest-asyncio>=0.24", "mypy>=1.10", "ruff>=0.11"]`
    - `[tool.ruff]`: `line-length = 120`, `target-version = "py312"`, `src = ["packages", "apps", "services", "simulators"]`
    - `[tool.ruff.lint]`: `select = ["E", "F", "I", "B", "UP", "N"]`, `ignore = []`
    - `[tool.mypy]`: `python_version = "3.12"`, `strict = true`, `files = ["packages/sft-agents/src", "packages/sft-domain/src", "packages/sft-contracts/src"]` (mypy strict SOLO su packages/sft-*, per Claude's Discretion)
    - `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`
    NON eseguire `uv sync` qui — viene fatto dopo che tutti i pyproject.toml per-progetto sono creati (Task 4).
  </action>
  <acceptance_criteria>
    - `pyproject.toml` root esiste e contiene `[tool.uv.workspace]`
    - Il blocco `members` elenca esattamente 23 path (3 packages + 2 app top + 16 agenti + 1 service + 1 simulator)
    - `pyproject.toml` contiene `requires-python = ">=3.12,<3.13"`
    - `pyproject.toml` contiene `[tool.mypy]` con `strict = true`
    - `python3 -c "import tomllib; m = tomllib.load(open('pyproject.toml','rb'))['tool']['uv']['workspace']['members']; assert len(m) == 23, len(m); print('ok')"` exits 0
  </acceptance_criteria>
</task>

<task id="1-01-04" wave="1" type="auto">
  <name>Task 4: Creare 23 sotto-progetti Python (pyproject.toml + project.json + src skeleton)</name>
  <files>packages/sft-agents/**, packages/sft-domain/**, packages/sft-contracts/**, apps/orchestrator/**, apps/api-gateway/**, apps/agents/**, services/ot-bridge/**, simulators/sim-textile/**, uv.lock</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-02, D-03, D-04, D-05, D-06 naming kebab-case + prefisso area)
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 1: generator Python project esempio sft-agents; Pitfall 3 placeholder pyproject minimale)
  </read_first>
  <action>
    Per OGNUNA delle 23 directory listata sotto, creare:
    1. `<dir>/pyproject.toml` minimale:
       ```toml
       [project]
       name = "<nx-project-name>"
       version = "0.1.0"
       requires-python = ">=3.12,<3.13"
       description = "<short desc>"
       dependencies = []

       [build-system]
       requires = ["hatchling"]
       build-backend = "hatchling.build"

       [tool.hatch.build.targets.wheel]
       packages = ["src/<python_module_name>"]
       ```
       dove `<python_module_name>` = `<nx-project-name>` con `-` -> `_` (snake_case).
    2. `<dir>/project.json` per Nx:
       ```json
       {
         "name": "<nx-project-name>",
         "$schema": "../../node_modules/nx/schemas/project-schema.json",
         "projectType": "<library|application>",
         "sourceRoot": "<dir>/src",
         "targets": {
           "test": {"executor": "@nxlv/python:run-commands", "options": {"command": "uv run pytest", "cwd": "<dir>"}},
           "lint": {"executor": "@nxlv/python:run-commands", "options": {"command": "uv run ruff check src", "cwd": "<dir>"}}
         },
         "implicitDependencies": [<see below>]
       }
       ```
    3. `<dir>/src/<python_module_name>/__init__.py` con contenuto `"""<desc>"""` + `__version__ = "0.1.0"`.
    4. `<dir>/README.md` con titolo + 1 riga di descrizione + nota "Skeleton populated in Phase <N>".

    Mappa nome-dir -> nx-project-name -> projectType -> implicitDependencies:
    | Dir | Nx Name | Type | Implicit Deps |
    |-----|---------|------|---------------|
    | packages/sft-agents | sft-agents | library | [] |
    | packages/sft-domain | sft-domain | library | [] |
    | packages/sft-contracts | sft-contracts | library | [] |
    | apps/orchestrator | svc-orchestrator | application | ["sft-agents", "sft-contracts", "sft-domain"] |
    | apps/api-gateway | svc-api-gateway | application | ["sft-agents", "sft-contracts", "sft-domain"] |
    | apps/agents/ops/operator-assistant | ops-operator-assistant | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/ops/production-planner | ops-production-planner | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/ops/quality-inspector | ops-quality-inspector | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/ops/anomaly-detector | ops-anomaly-detector | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/maintenance/predictive-maintenance | mnt-predictive-maintenance | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/maintenance/rca-specialist | mnt-rca-specialist | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/maintenance/maintenance-coach | mnt-maintenance-coach | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/maintenance/downtime-analyzer | mnt-downtime-analyzer | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/knowledge/knowledge-curator | trn-knowledge-curator | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/knowledge/training-coach | trn-training-coach | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/knowledge/shift-handover | trn-shift-handover | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/knowledge/documentation-synthesizer | trn-documentation-synthesizer | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/supply/inventory-manager | scm-inventory-manager | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/supply/energy-optimizer | scm-energy-optimizer | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/supply/cost-analyzer | scm-cost-analyzer | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | apps/agents/supply/demand-forecaster | scm-demand-forecaster | application | ["sft-agents", "sft-domain", "sft-contracts"] |
    | services/ot-bridge | svc-ot-bridge | application | ["sft-contracts"] |
    | simulators/sim-textile | sim-textile | application | ["sft-contracts"] |

    Per `packages/sft-agents/src/sft_agents/__version__.py` aggiungere `__version__ = "0.1.0"` esplicito (per integrazione Changesets in plan 08).
    Dopo aver creato tutti i file, eseguire `uv sync --all-packages` dalla root del repo per generare `uv.lock`.
  </action>
  <acceptance_criteria>
    - `find apps/ packages/ services/ simulators/ -name pyproject.toml | wc -l` ritorna almeno 23
    - `find apps/ packages/ services/ simulators/ -name project.json | wc -l` ritorna almeno 23
    - `uv sync --all-packages` completa con exit 0 e produce `uv.lock`
    - `uv.lock` esiste e contiene riferimenti a `sft-agents`, `sft-domain`, `sft-contracts`
    - `grep -l '"implicitDependencies": \["sft-contracts"' apps/factory-ui/project.json` non applicabile qui (Task 5), ma `grep '"sft-contracts"' apps/api-gateway/project.json` deve produrre almeno 1 match
    - `python3 -c "import tomllib; m=tomllib.load(open('apps/agents/ops/operator-assistant/pyproject.toml','rb'))['project']; assert m['name']=='ops-operator-assistant'"` exits 0
  </acceptance_criteria>
</task>

<task id="1-01-05" wave="1" type="auto">
  <name>Task 5: Generare Angular SSR app factory-ui con implicitDependencies su sft-contracts</name>
  <files>apps/factory-ui/**, package.json, package-lock.json</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 1: Angular SSR generator esempio; Pitfall 4 implicitDependencies Python->TS)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-05 naming `ui-factory`)
    - CLAUDE.md (Angular 18+ con SSR, @nx/angular setup-ssr)
  </read_first>
  <action>
    Eseguire (in modalità non-interactive, --dry-run prima per validare):
    ```
    npx nx generate @nx/angular:application factory-ui \
      --directory=apps/factory-ui \
      --name=ui-factory \
      --routing \
      --standalone \
      --ssr \
      --style=scss \
      --linter=eslint \
      --unitTestRunner=jest \
      --e2eTestRunner=none \
      --skipInstall=false \
      --no-interactive
    ```
    NOTA: in Nx 20 con @nx/angular il flag generator può essere `setup-ssr` come step separato. Se l'application generator non supporta `--ssr` direttamente nella versione installata, eseguire:
    ```
    npx nx generate @nx/angular:application factory-ui --directory=apps/factory-ui --name=ui-factory --routing --standalone --no-interactive
    npx nx generate @nx/angular:setup-ssr ui-factory
    ```
    Modificare il `apps/factory-ui/project.json` generato per aggiungere `"implicitDependencies": ["sft-contracts"]` (per Pitfall 4 — Nx non infer le deps Python->TS automaticamente). Aggiungere stessa modifica in `apps/api-gateway/project.json` per dichiarare `["sft-contracts", "sft-agents", "sft-domain"]` (già fatto in Task 4 ma verificare). Aggiungere `tsconfig` paths se generator non li imposta. Disabilitare e2e e2eTestRunner (Playwright arriverà in Fase 10).
    Verificare che `nx graph --file=tmp/graph.json` produca un graph JSON; eseguire `python3 scripts/validate-nx-graph.py` e confermare che gli edges richiesti siano presenti. Se mancano, aggiungerli manualmente ai `project.json` corrispondenti.
  </action>
  <acceptance_criteria>
    - `apps/factory-ui/project.json` esiste e contiene `"sourceRoot": "apps/factory-ui/src"`
    - `apps/factory-ui/project.json` contiene la stringa `"implicitDependencies"` con almeno `"sft-contracts"`
    - `apps/factory-ui/server.ts` o `apps/factory-ui/src/main.server.ts` esiste (artifact SSR)
    - `npx nx graph --file=tmp/graph.json` exits 0 (genera il file)
    - `python3 scripts/validate-nx-graph.py` exits 0 dopo creazione graph.json (tutti edges richiesti presenti)
    - `npx nx show project ui-factory --json | grep -q '"name":"ui-factory"'` exits 0
  </acceptance_criteria>
</task>

</tasks>

<verification>
Step finali end-to-end per validare Plan 01:

1. `node -v` -> v20.x+
2. `uv --version` -> 0.6.0+
3. `npm ci` exits 0
4. `uv sync --all-packages` exits 0
5. `npx nx graph --file=tmp/graph.json` produce file JSON valido
6. `python3 scripts/validate-nx-graph.py` exits 0
7. `npx nx show projects | wc -l` ritorna >= 24 (23 Python + 1 Angular)
8. `npx nx show project sft-contracts --json | jq -r '.name'` ritorna `sft-contracts`
9. `npx nx show project ui-factory --json | jq -r '.implicitDependencies[]' | grep sft-contracts` exits 0
10. `git status` mostra file aggiunti coerenti con `files_modified` di questo plan
</verification>

<success_criteria>
- nx workspace funzionante con plugin @nxlv/python e @nx/angular caricati
- uv workspace single-lockfile coerente (uv.lock generato)
- 23 sotto-progetti Python valid + 1 Angular SSR app
- implicitDependencies dichiarate per gli edges Python->TS critici (sft-contracts -> ui-factory, sft-* -> svc-api-gateway, sft-* -> svc-orchestrator)
- `nx affected` correttamente trigger build/test sui consumer quando un package cambia (verificato in Plan 05)
- Nx Cloud disabilitato by default; abilitabile via env var
- Phase Success Criterion #2 abilitato: `nx affected --target=test` può risolvere edges Python↔TypeScript
</success_criteria>

<output>
Create `.planning/phases/01-foundation-monorepo/01-01-SUMMARY.md` quando done.
</output>
