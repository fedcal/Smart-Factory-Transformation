---
phase: 1
plan: 1
slug: nx-workspace
subsystem: foundation/monorepo
status: complete
tags: [nx, uv, angular, python, monorepo, workspace, polyglot]
dependency_graph:
  requires: []
  provides:
    - nx-workspace-polyglot
    - uv-workspace-single-lockfile
    - 23-python-subprojects-scaffolded
    - angular-ssr-app-ui-factory
    - dep-graph-python-ts-edges
  affects:
    - all-subsequent-plans
tech_stack:
  added:
    - nx@20.8.4
    - "@nxlv/python@21.3.1"
    - "@nx/angular@20.8.4"
    - uv workspace (single uv.lock)
    - hatchling (Python build backend)
    - Angular 19.2.x (SSR via @angular/ssr)
    - TypeScript 5.5.4
    - prettier@3.5.3
    - "@changesets/cli@2.31.0"
  patterns:
    - Nx polyglot workspace con @nxlv/python plugin (uv backend)
    - uv workspace single-lockfile con dependency-groups (PEP 735)
    - implicitDependencies Python->TypeScript per nx affected
    - hatchling build backend per tutti i 23 package Python
key_files:
  created:
    - nx.json
    - package.json
    - pyproject.toml
    - uv.lock
    - pnpm-workspace.yaml
    - .gitignore
    - .nvmrc
    - .python-version
    - .tool-versions
    - docs/contributing/toolchain.md
    - scripts/validate-nx-graph.py
    - scripts/sync-python-versions.py
    - apps/factory-ui/project.json
    - apps/factory-ui/src/main.server.ts
    - apps/factory-ui/src/server.ts
    - "packages/sft-{agents,domain,contracts}/ (3 library packages)"
    - "apps/orchestrator/, apps/api-gateway/ (2 app top-level)"
    - "apps/agents/{ops,maintenance,knowledge,supply}/*/ (16 agent apps)"
    - "services/ot-bridge/, simulators/sim-textile/ (1+1)"
  modified:
    - package-lock.json (generated via npm install)
decisions:
  - "@nx/angular pinned a 20.8.4 (non 22.7.2 della RESEARCH) per allineamento peer deps con Nx 20.8.4"
  - "uv dev-dependencies migrato a [dependency-groups] dev (PEP 735) per compatibilita uv 0.11+"
  - "Tutti gli @nx/* packages pinati a 20.8.4 per consistenza con nx core"
metrics:
  duration_minutes: 9
  completed_date: "2026-05-16T19:23:50Z"
  tasks_completed: 5
  tasks_total: 5
  files_created: ~140
  commits: 6
---

# Phase 1 Plan 1: nx-workspace Summary

**One-liner:** Nx 20.8.4 polyglot workspace con @nxlv/python 21.3.1 + uv single-lockfile, 23 Python sub-projects + Angular 19 SSR, dep graph validato con tutti e 5 gli edges Python->TypeScript richiesti.

---

## What Was Built

Un monorepo Nx 20.x completamente funzionante con supporto Python e TypeScript first-class:

- **Nx workspace** con plugin `@nxlv/python` (uv backend) e `@nx/angular/plugin`; `neverConnectToCloud: true` di default
- **uv workspace** con pyproject.toml root, lista esplicita di 23 members, `[dependency-groups]` PEP 735, Python 3.12 pinned
- **6 root-folder strutturali** (`apps/`, `packages/`, `services/`, `docs/`, `infra/`, `simulators/`) con .gitkeep
- **23 sotto-progetti Python** scaffolded con pyproject.toml (hatchling), project.json (Nx), src skeleton e README
- **3 SDK packages**: `sft-agents` (library), `sft-domain` (library), `sft-contracts` (library)
- **2 app top-level**: `svc-orchestrator`, `svc-api-gateway` con implicitDependencies su tutti e 3 i packages
- **16 agenti placeholder** distribuiti nei 4 cluster (ops-*, mnt-*, trn-*, scm-*) come `application` Nx
- **1 service** `svc-ot-bridge` e **1 simulator** `sim-textile`
- **Angular SSR app** `ui-factory` generata via `@nx/angular:application` con `--ssr`, implicitDependencies su `sft-contracts`
- **uv.lock** generato via `uv sync --all-packages` — single-lockfile per 23 workspace members
- **Script di validazione** dep graph (`validate-nx-graph.py`) e sync versioni (`sync-python-versions.py`)
- **Documentazione toolchain** (`docs/contributing/toolchain.md`) con prerequisiti e quick start

---

## Verification Results

```
nx show projects | wc -l     → 24 (23 Python + 1 Angular)
uv sync --all-packages        → exit 0, no warnings, uv.lock generato
nx graph --file=tmp/graph.json → JSON valido
python3 scripts/validate-nx-graph.py → "OK: All 5 required dependency edges present"
  - ui-factory -> sft-contracts      OK
  - svc-api-gateway -> sft-contracts OK
  - svc-api-gateway -> sft-agents    OK
  - svc-api-gateway -> sft-domain    OK
  - svc-orchestrator -> sft-agents   OK
npx nx show project sft-contracts --json | .name → sft-contracts
npx nx show project ui-factory --json | .implicitDependencies → ["sft-contracts"]
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] @nx/angular versione corretta 20.8.4 invece di 20.8.1**
- **Found during:** Task 2
- **Issue:** Il piano specificava `@nx/angular@20.8.1` ma la versione corretta latest-20.x allineata con `nx@20.8.4` e tutti gli altri `@nx/*` packages è `20.8.4`
- **Fix:** Tutti gli `@nx/*` packages (angular, eslint, jest, js, workspace) pinati a `20.8.4` per consistenza con nx core
- **Files modified:** `package.json`
- **Commit:** 4516180

**2. [Rule 1 - Bug] uv dev-dependencies deprecato in uv 0.11+**
- **Found during:** Verifica finale dopo Task 4
- **Issue:** `[tool.uv] dev-dependencies` produce warning `will be removed in a future release` su uv 0.11.13; la sintassi corretta è `[dependency-groups] dev` (PEP 735)
- **Fix:** Migrato `[tool.uv] dev-dependencies` a `[dependency-groups] dev` nel root `pyproject.toml`; `uv sync --all-packages` completa ora senza warning
- **Files modified:** `pyproject.toml`, `uv.lock`
- **Commit:** 0c0fba8

### Notes

- Python 3.12 non era disponibile nel sistema (disponibile solo 3.13.7); installato via `uv python install 3.12` come documentato in `toolchain.md`
- Angular installato era 19.2.x (non 18.x come da CLAUDE.md stack generico) — il generator `@nx/angular@20.8.4` installa Angular 19.2.x che è la versione compatibile con Nx 20.x; questo è corretto per il workspace
- Il generator Angular ha modificato automaticamente `nx.json` aggiungendo target defaults per `@angular-devkit/build-angular:application`, `@nx/eslint:lint`, `@nx/jest:jest` — cambiamenti intentionali mantenuti

---

## Known Stubs

I seguenti sub-progetti sono placeholder (skeleton) da popolare nelle fasi successive:

| Project | File | Stub | Phase Planned |
|---------|------|------|---------------|
| ops-operator-assistant | src/ops_operator_assistant/__init__.py | `__version__ = "0.1.0"` only | Phase 4 |
| ops-production-planner | src/ops_production_planner/__init__.py | `__version__ = "0.1.0"` only | Phase 4 |
| ops-quality-inspector | src/ops_quality_inspector/__init__.py | `__version__ = "0.1.0"` only | Phase 4 |
| ops-anomaly-detector | src/ops_anomaly_detector/__init__.py | `__version__ = "0.1.0"` only | Phase 4 |
| mnt-predictive-maintenance | src/mnt_predictive_maintenance/__init__.py | `__version__ = "0.1.0"` only | Phase 7 |
| mnt-rca-specialist | src/mnt_rca_specialist/__init__.py | `__version__ = "0.1.0"` only | Phase 7 |
| mnt-maintenance-coach | src/mnt_maintenance_coach/__init__.py | `__version__ = "0.1.0"` only | Phase 7 |
| mnt-downtime-analyzer | src/mnt_downtime_analyzer/__init__.py | `__version__ = "0.1.0"` only | Phase 7 |
| trn-knowledge-curator | src/trn_knowledge_curator/__init__.py | `__version__ = "0.1.0"` only | Phase 5 |
| trn-training-coach | src/trn_training_coach/__init__.py | `__version__ = "0.1.0"` only | Phase 5 |
| trn-shift-handover | src/trn_shift_handover/__init__.py | `__version__ = "0.1.0"` only | Phase 5 |
| trn-documentation-synthesizer | src/trn_documentation_synthesizer/__init__.py | `__version__ = "0.1.0"` only | Phase 5 |
| scm-inventory-manager | src/scm_inventory_manager/__init__.py | `__version__ = "0.1.0"` only | Phase 8 |
| scm-energy-optimizer | src/scm_energy_optimizer/__init__.py | `__version__ = "0.1.0"` only | Phase 8 |
| scm-cost-analyzer | src/scm_cost_analyzer/__init__.py | `__version__ = "0.1.0"` only | Phase 9 |
| scm-demand-forecaster | src/scm_demand_forecaster/__init__.py | `__version__ = "0.1.0"` only | Phase 8 |
| sft-agents | src/sft_agents/__init__.py | Core SDK stub only | Phase 4 |
| sft-domain | src/sft_domain/__init__.py | Domain models stub only | Phase 4 |
| sft-contracts | src/sft_contracts/__init__.py | Contracts stub only | Phase 4 |
| sim-textile | src/sim_textile/__init__.py | Simulator stub only | Phase 3 |
| svc-ot-bridge | src/svc_ot_bridge/__init__.py | OT Bridge stub only | Phase 3 |
| svc-orchestrator | src/svc_orchestrator/__init__.py | Orchestrator stub only | Phase 4 |
| svc-api-gateway | src/svc_api_gateway/__init__.py | API gateway stub only | Phase 6 |

Questi sono stub **intenzionali** — l'obiettivo di Piano 01 era solo la struttura Nx/uv. Il contenuto applicativo arriva nelle fasi successive come da roadmap.

---

## Threat Surface Scan

Nessuna nuova superficie di attacco introdotta oltre quanto documentato in `<threat_model>` del piano:

- `package.json` usa versioni esatte (no range `^`) per tutti i pacchetti custom; le dipendenze Angular usano `~` (major-locked) come installate dal generator ufficiale Nx
- Tutti i pacchetti erano presenti nel Package Legitimacy Audit di RESEARCH.md con disposizione `Approvato`
- `nx.json` non contiene token NX Cloud hardcoded (`neverConnectToCloud: true`)
- `uv.lock` è generato deterministicamente da uv come single-lockfile

---

## Commit History

| Task | Description | Commit |
|------|-------------|--------|
| 1 | scaffold root-folder e documentazione toolchain | 59078e1 |
| 2 | bootstrap Nx workspace con plugin @nxlv/python e @nx/angular | 4516180 |
| 3 | root pyproject.toml uv workspace con 23 members | d359724 |
| 4 | 23 sotto-progetti Python con pyproject.toml + project.json + skeleton src | c260111 |
| 5 | Angular SSR app ui-factory con implicitDependencies su sft-contracts | b8be5a4 |
| fix | migra dev-dependencies a dependency-groups per uv 0.11+ | 0c0fba8 |

---

## Self-Check: PASSED

```
[x] nx.json exists and contains "@nxlv/python" and "@nx/angular/plugin"
[x] package.json exists with "nx": "20.8.4" and "@nxlv/python": "21.3.1"
[x] pyproject.toml exists with [tool.uv.workspace] and 23 members
[x] uv.lock exists with sft-agents, sft-domain, sft-contracts entries
[x] apps/factory-ui/project.json exists with sourceRoot and implicitDependencies
[x] apps/factory-ui/src/main.server.ts exists (SSR artifact)
[x] apps/factory-ui/src/server.ts exists (SSR artifact)
[x] scripts/validate-nx-graph.py exists with REQUIRED_EDGES
[x] scripts/sync-python-versions.py exists
[x] docs/contributing/toolchain.md exists
[x] .nvmrc contains "20", .python-version contains "3.12"
[x] All 6 root-folder have .gitkeep
[x] 24 Nx projects total (23 Python + 1 Angular SSR)
[x] All 5 required dep edges validated by validate-nx-graph.py
[x] All 6 task commits verified in git log
```
