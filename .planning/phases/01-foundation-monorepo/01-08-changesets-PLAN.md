---
phase: 1
plan: 8
slug: changesets
type: execute
wave: 2
depends_on: ["01"]
files_modified:
  - .changeset/config.json
  - .changeset/README.md
  - .changeset/initial-phase-1.md
  - .github/workflows/release.yml
  - scripts/sync-python-versions.py
  - packages/sft-agents/src/sft_agents/__version__.py
  - packages/sft-domain/src/sft_domain/__version__.py
  - packages/sft-contracts/src/sft_contracts/__version__.py
  - packages/sft-agents/package.json
  - packages/sft-domain/package.json
  - packages/sft-contracts/package.json
  - package.json
  - docs/contributing/release.md
autonomous: true
requirements: [PLAT-10]
tags: [foundation, release, versioning, changesets]

must_haves:
  truths:
    - "`npx changeset` apre il prompt e crea un file `.changeset/<random>.md` valido"
    - "`npx changeset version` aggiorna `package.json` dei pacchetti `sft-agents`, `sft-domain`, `sft-contracts` e propaga la versione a `src/<module>/__version__.py` via `scripts/sync-python-versions.py`"
    - "Workflow `.github/workflows/release.yml` su push to main crea automaticamente una PR di release (Changesets bot) o, se la PR di release esiste già, crea tag + GH Release"
    - "Il README `.changeset/README.md` documenta che la pubblicazione PyPI è rinviata oltre v1 (deferred); il workflow emette SOLO tag + GH Release"
    - "I 3 packages pubblicabili (`sft-agents`, `sft-domain`, `sft-contracts`) hanno `package.json` minimo che dichiara il `name` e la `version` allineata al `__version__.py`"
  artifacts:
    - path: ".changeset/config.json"
      provides: "Configurazione Changesets per monorepo polyglot"
      contains: '"baseBranch": "main"'
    - path: ".github/workflows/release.yml"
      provides: "GitHub Actions release workflow con changesets/action@v1"
      contains: "changesets/action"
    - path: "scripts/sync-python-versions.py"
      provides: "Sync versione da package.json -> __version__.py per i package Python pubblicabili"
  key_links:
    - from: ".github/workflows/release.yml"
      to: "scripts/sync-python-versions.py"
      via: "step pre-publish"
      pattern: "sync-python-versions"
---

<objective>
Configurare Changesets per il versioning semantico del monorepo polyglot, focalizzato sui 3 packages pubblicabili (`sft-agents`, `sft-domain`, `sft-contracts`) come SDK. Il workflow `release.yml` su push to main usa l'azione Changesets per: 1) creare PR di release con bump versione + CHANGELOG, 2) al merge della PR, creare tag + GH Release. PyPI publish è rinviato (Claude's Discretion).

Purpose: ship-fast richiede release tracking automatico già da Phase 1, anche se la pubblicazione effettiva su PyPI arriva dopo che `sft-agents` ha API stabilizzata (probabilmente post-Phase 4). Avere il workflow pronto significa che ogni feature merge produce un changelog atomico.

Output: Changesets installato, primo changeset di esempio creato, workflow CI che emette tag + GH Release.
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
| changeset/action -> GitHub tags + releases | richiede GITHUB_TOKEN; rischio T-1-04 se permission sbagliato |
| changelog -> public release notes | rischio T-1-03 leak se messaggi commit contengono secret |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-04 | Elevation of Privilege | GITHUB_TOKEN scope in release workflow | mitigate | `permissions: {contents: write, pull-requests: write}` minimal — sufficiente per tag + release + PR creation; nessun `id-token: write` (non serve PyPI OIDC v1) |
| T-1-03 | Information Disclosure | release notes contengono commit message; gitleaks (plan 04) blocca secret in messaggi | mitigate | gitleaks scansiona file modificati, non i commit message direttamente — relying su pre-commit; documentare in `release.md` di non includere secret in changeset descriptions |
| T-1-SC | Tampering | @changesets/action@v1 upstream | mitigate | pinning a `@v1` major (security patches); future pin a commit SHA possible |
</threat_model>

<tasks>

<task id="1-08-01" wave="2" type="auto">
  <name>Task 1: .changeset/ setup + package.json per packages pubblicabili</name>
  <files>.changeset/config.json, .changeset/README.md, .changeset/initial-phase-1.md, packages/sft-agents/package.json, packages/sft-domain/package.json, packages/sft-contracts/package.json, packages/sft-agents/src/sft_agents/__version__.py, packages/sft-domain/src/sft_domain/__version__.py, packages/sft-contracts/src/sft_contracts/__version__.py, package.json, scripts/sync-python-versions.py</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 9: Changesets Setup Polyglot, righe ~1192-1264)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: Changesets per monorepo polyglot; PyPI deferred)
  </read_first>
  <action>
    Eseguire `npx changeset init` per inizializzare `.changeset/`. Modificare il `.changeset/config.json` generato per il polyglot setup:
    ```json
    {
      "$schema": "https://unpkg.com/@changesets/config/schema.json",
      "changelog": "@changesets/cli/changelog",
      "commit": false,
      "fixed": [],
      "linked": [["sft-agents", "sft-domain", "sft-contracts"]],
      "access": "restricted",
      "baseBranch": "main",
      "updateInternalDependencies": "patch",
      "ignore": []
    }
    ```
    NOTA: usare `linked` per i 3 SDK packages perché sono usati insieme dagli agenti e dovrebbero bumpare insieme; `access: restricted` significa "no auto-publish a npm" (e non-Node `__version__.py` sync è gestito da script custom).

    Modificare `.changeset/README.md` (creato da init) per includere una sezione dedicata "Polyglot policy":
    > Questo monorepo emette release per i 3 SDK Python (sft-agents, sft-domain, sft-contracts). Changesets gestisce: bump version in `packages/*/package.json`, generazione CHANGELOG.md, creazione tag git, creazione GitHub Release. La pubblicazione effettiva su PyPI è DEFERRED oltre v1 — verrà abilitata quando l'SDK ha superficie API stabile (probabilmente post-Phase 4). Le app Python (orchestrator, api-gateway, agenti) e le app/lib Angular NON sono pubblicate: vivono in `apps/` e sono buildate come container.

    Creare un changeset iniziale `.changeset/initial-phase-1.md` per dare un esempio:
    ```markdown
    ---
    "sft-agents": minor
    "sft-domain": minor
    "sft-contracts": minor
    ---

    Phase 1 — Foundation & Monorepo scaffolding. Initial SDK skeletons for sft-agents, sft-domain, sft-contracts. No public API surface yet; intended as foundation for Phase 4+.
    ```

    Per OGNI package pubblicabile (`packages/sft-agents`, `packages/sft-domain`, `packages/sft-contracts`):
    - Creare `package.json` minimale:
      ```json
      {
        "name": "<pkg-name>",
        "version": "0.1.0",
        "description": "<short>",
        "private": false,
        "license": "Apache-2.0",
        "repository": {
          "type": "git",
          "url": "https://github.com/fedcal/Smart-Factory-Transformation.git",
          "directory": "packages/<pkg-name>"
        }
      }
      ```
      NOTA: `version` deve corrispondere a quanto già presente in `pyproject.toml` (creato in plan 01 task 4: `0.1.0`). Lo `name` deve essere identico al `name` Nx-project.
    - Assicurarsi che esista `src/<module>/__version__.py` con `__version__ = "0.1.0"` (sft-agents lo ha da plan 01; aggiungerlo anche a sft-domain e sft-contracts).

    Modificare `package.json` root per aggiungere scripts:
    ```json
    {
      "scripts": {
        "changeset": "changeset",
        "version-packages": "changeset version && python3 scripts/sync-python-versions.py",
        "release": "echo 'PyPI publish deferred — emitting tags+release only'"
      },
      "workspaces": [
        "packages/sft-agents",
        "packages/sft-domain",
        "packages/sft-contracts"
      ]
    }
    ```
    NOTA: `workspaces` di npm può convivere con `pnpm-workspace.yaml`. Aggiungere solo i 3 packages pubblicabili (gli altri Python project non sono npm workspace members).

    Aggiornare `scripts/sync-python-versions.py` (creato da plan 01 task 2) per essere completo:
    ```python
    """Synchronize Python package versions from package.json to src/<module>/__version__.py.
    Executed by `npm run version-packages` after `changeset version`.
    """
    import json
    import pathlib
    import sys

    ROOT = pathlib.Path(__file__).resolve().parent.parent
    PUBLISHABLE = ["sft-agents", "sft-domain", "sft-contracts"]

    def sync_versions() -> int:
        errors = 0
        for pkg_name in PUBLISHABLE:
            pkg_dir = ROOT / "packages" / pkg_name
            pkg_json = pkg_dir / "package.json"
            if not pkg_json.exists():
                print(f"[skip] {pkg_name}: no package.json", file=sys.stderr)
                continue
            version = json.loads(pkg_json.read_text())["version"]
            module_name = pkg_name.replace("-", "_")
            version_file = pkg_dir / "src" / module_name / "__version__.py"
            if not version_file.exists():
                print(f"[error] {pkg_name}: missing {version_file}", file=sys.stderr)
                errors += 1
                continue
            version_file.write_text(f'__version__ = "{version}"\n')
            print(f"[ok] {pkg_name} -> {version}")

            # Also update pyproject.toml version field (idempotent regex replace)
            pyproject = pkg_dir / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text()
                import re
                new_content = re.sub(
                    r'^version\s*=\s*"[^"]+"',
                    f'version = "{version}"',
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )
                if new_content != content:
                    pyproject.write_text(new_content)
                    print(f"[ok] {pkg_name} pyproject.toml -> {version}")
        return errors

    if __name__ == "__main__":
        sys.exit(sync_versions())
    ```
  </action>
  <acceptance_criteria>
    - `.changeset/config.json` esiste e contiene `"baseBranch": "main"`
    - `.changeset/config.json` contiene `"linked": [["sft-agents", "sft-domain", "sft-contracts"]]`
    - `.changeset/README.md` esiste e contiene la stringa "PyPI" e "DEFERRED" (o "deferred")
    - `.changeset/initial-phase-1.md` esiste e contiene 3 entry minor per gli SDK
    - `packages/sft-agents/package.json` esiste con `"name": "sft-agents"` e `"version": "0.1.0"`
    - `packages/sft-domain/package.json` esiste e analogo
    - `packages/sft-contracts/package.json` esiste e analogo
    - `packages/sft-domain/src/sft_domain/__version__.py` e `packages/sft-contracts/src/sft_contracts/__version__.py` esistono con `__version__ = "0.1.0"`
    - `package.json` root contiene `"workspaces"` con 3 packages
    - `python3 scripts/sync-python-versions.py` exits 0 dopo modifica versioni in package.json di test (idempotente su versione corrente)
  </acceptance_criteria>
</task>

<task id="1-08-02" wave="2" type="auto">
  <name>Task 2: .github/workflows/release.yml + docs/contributing/release.md</name>
  <files>.github/workflows/release.yml, docs/contributing/release.md</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 9 release.yml righe ~1240-1264)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: workflow Changesets emette version/tag/GH Release; PyPI rinviato)
  </read_first>
  <action>
    Creare `.github/workflows/release.yml`:
    ```yaml
    name: Release
    on:
      push:
        branches: [main]
    permissions:
      contents: write
      pull-requests: write
    concurrency:
      group: release-${{ github.workflow }}-${{ github.ref }}
    jobs:
      release:
        runs-on: ubuntu-latest
        timeout-minutes: 15
        steps:
          - uses: actions/checkout@v4
            with:
              fetch-depth: 0
              persist-credentials: true
          - uses: actions/setup-node@v4
            with:
              node-version: 20
              cache: 'npm'
          - uses: actions/setup-python@v5
            with:
              python-version: '3.12'
          - name: Install dependencies
            run: npm ci
          - name: Create Release PR or publish tags
            id: changesets
            uses: changesets/action@v1
            with:
              version: npm run version-packages
              publish: npm run release   # echo only; PyPI publish deferred
              commit: "chore(release): version packages"
              title: "chore(release): version packages"
            env:
              GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    ```
    NOTA: `publish` step esegue `npm run release` che è `echo` (no-op effettivo); la creation del tag + GH Release è gestita internamente da changesets/action quando rileva consumed changesets. Se in futuro si abilita PyPI publish, modificare lo script `release` per chiamare `uv build && uv publish` per ciascuno dei 3 packages.

    Creare `docs/contributing/release.md` (IT con sezione EN summary) che documenta:
    - "Quando un PR introduce una modifica che merita un bump version dei pacchetti SDK (sft-agents/sft-domain/sft-contracts), aggiungere un changeset: `npx changeset` e seguire il prompt"
    - Tipi di bump: `patch` (bugfix), `minor` (feat backward-compatible), `major` (breaking)
    - I 3 SDK sono `linked` -> bumpano insieme. Se cambia uno, cambia anche gli altri due
    - Flow di release:
      1. Sviluppatore apre PR con `.changeset/<random>.md`
      2. PR merged su main
      3. Workflow `release.yml` rileva changeset, crea una PR di release ("Version Packages") con CHANGELOG aggiornato
      4. Maintainer merge la PR di release
      5. `release.yml` rileva PR merged -> crea tag git `v<X.Y.Z>` + GitHub Release con changelog
      6. PyPI publish: NON automatico in v1; manuale per `sft-agents` quando API stabile (deferred)
    - Esempio changeset:
      ```markdown
      ---
      "sft-agents": minor
      "sft-domain": patch
      "sft-contracts": patch
      ---
      
      Add new Tool interface to sft-agents (sft-domain and sft-contracts adapt internal types).
      ```
    - Troubleshooting: PR di release non viene creata -> verificare permission `contents: write` + `pull-requests: write`; CHANGELOG.md non sincronizzato con `__version__.py` -> rieseguire `python3 scripts/sync-python-versions.py` e committare.
  </action>
  <acceptance_criteria>
    - `.github/workflows/release.yml` esiste e contiene `changesets/action@v1`
    - `.github/workflows/release.yml` contiene `version: npm run version-packages`
    - `.github/workflows/release.yml` contiene `permissions: contents: write` e `pull-requests: write`
    - `docs/contributing/release.md` esiste e contiene "changeset" e "linked"
    - `docs/contributing/release.md` documenta esplicitamente che PyPI publish è deferred
    - `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"` exits 0
  </acceptance_criteria>
</task>

</tasks>

<verification>
1. `.changeset/config.json` valido (`python3 -c "import json; json.load(open('.changeset/config.json'))"` exits 0)
2. `npx changeset status` exits 0 (sa che esistono `initial-phase-1.md` come pending)
3. `python3 scripts/sync-python-versions.py` exits 0
4. `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"` exits 0
5. Test end-to-end (post-merge): merge PR con cambio in `packages/sft-contracts` + nuovo changeset; verificare che `release.yml` crei una PR "Version Packages"; merge della PR; verificare che venga creato tag `v0.2.0` + GH Release.
</verification>

<success_criteria>
- Changesets installato e funzionante (Phase Success Criterion: PLAT-10 finale)
- 3 SDK packages (sft-agents/sft-domain/sft-contracts) linked e versioned
- Workflow `release.yml` emette tag + GH Release automaticamente
- PyPI publish documentato come deferred (Claude's Discretion)
- Sync version da package.json a `__version__.py` automatico via script
</success_criteria>

<output>
Create `.planning/phases/01-foundation-monorepo/01-08-SUMMARY.md` quando done.
</output>
