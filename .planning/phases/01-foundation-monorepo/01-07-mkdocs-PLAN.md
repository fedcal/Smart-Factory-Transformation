---
phase: 1
plan: 7
slug: mkdocs
type: execute
wave: 2
depends_on: ["01"]
files_modified:
  - docs/mkdocs.yml
  - docs/requirements.txt
  - docs/docs/index.md
  - docs/docs/getting-started.md
  - docs/docs/architecture/overview.md
  - docs/docs/contributing/index.md
  - docs/docs/en/index.md
  - docs/docs/en/getting-started.md
  - docs/docs/en/architecture/overview.md
  - docs/docs/en/contributing/index.md
  - docs/docs/assets/custom.css
  - .github/workflows/docs-deploy.yml
  - Makefile
autonomous: true
requirements: [PLAT-10]
tags: [foundation, docs, mkdocs, i18n, gh-pages]

must_haves:
  truths:
    - "`mkdocs build` su `docs/` produce un sito statico in `docs/site/` senza errori e con plugin i18n attivo"
    - "Il sito ha selettore lingua IT (default) / EN funzionante"
    - "Il workflow `.github/workflows/docs-deploy.yml` su push to main esegue `mkdocs gh-deploy --force` e pubblica su branch `gh-pages`"
    - "Esistono pagine placeholder bilingue: index, getting-started, architecture/overview, contributing"
    - "Il theme è MkDocs Material 9.7+ con `mkdocs-static-i18n` plugin 1.3+"
  artifacts:
    - path: "docs/mkdocs.yml"
      provides: "Configurazione MkDocs Material con plugin i18n IT/EN"
      contains: "mkdocs-static-i18n"
    - path: "docs/requirements.txt"
      provides: "Pinning dipendenze docs build (mkdocs-material 9.7.6, mkdocs-static-i18n 1.3.1, pymdown-extensions)"
    - path: ".github/workflows/docs-deploy.yml"
      provides: "Auto-deploy su gh-pages su push to main"
      contains: "mkdocs gh-deploy"
  key_links:
    - from: "docs/mkdocs.yml"
      to: "plugin i18n + Material theme"
      via: "plugins block"
      pattern: "- i18n:"
    - from: ".github/workflows/docs-deploy.yml"
      to: "branch gh-pages"
      via: "mkdocs gh-deploy --force"
      pattern: "gh-deploy"
---

<objective>
Scaffolding del sito di documentazione MkDocs Material bilingue IT/EN con plugin i18n, struttura folder, pagine placeholder e workflow CI che pubblica automaticamente su GitHub Pages al merge su main. La sostanza del contenuto arriva da Fase 2 in poi (CLaude's Discretion). Soddisfa parte di PLAT-10 (struttura docs + deploy).

Purpose: avere il sito live già in Fase 1 significa che ogni contributo Fase 2+ vede immediatamente come appare il proprio output. Setting up i18n da subito previene refactoring quando si aggiunge EN dopo aver scritto solo IT.

Output: `docs/` build-ready, `make docs` funzionante, primo deploy su `gh-pages` al merge.
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
| docs build -> gh-pages public | sito pubblico; non deve contenere riferimenti al brand originale (DEL-08; verifica finale in Fase 12) né secret |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-03 | Information Disclosure | docs published on public GitHub Pages | mitigate | gitleaks hook (plan 04) scansiona contenuti markdown; brand-scrub CI in Fase 12 verifica DEL-08; in Fase 1 le pagine sono placeholder, low-risk |
| T-1-SC | Tampering | mkdocs-material + mkdocs-static-i18n upstream | mitigate | versioni pinate in `docs/requirements.txt` (9.7.6 e 1.3.1); aggiornamenti richiedono PR review |
</threat_model>

<tasks>

<task id="1-07-01" wave="2" type="auto">
  <name>Task 1: docs/mkdocs.yml + docs/requirements.txt + struttura pagine bilingue</name>
  <files>docs/mkdocs.yml, docs/requirements.txt, docs/docs/index.md, docs/docs/getting-started.md, docs/docs/architecture/overview.md, docs/docs/contributing/index.md, docs/docs/en/index.md, docs/docs/en/getting-started.md, docs/docs/en/architecture/overview.md, docs/docs/en/contributing/index.md, docs/docs/assets/custom.css</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 8: MkDocs Material i18n, righe ~1104-1190)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: Docs scaffolding Fase 1, sostanza arriva da Fase 2)
    - CLAUDE.md (MkDocs Material 9.5+, mkdocs-static-i18n plugin)
  </read_first>
  <action>
    Creare `docs/mkdocs.yml` con:
    ```yaml
    site_name: Smart Factory Transformation
    site_description: Piattaforma opensource agentica per la trasformazione digitale di un'industria tessile manifatturiera
    site_url: https://fedcal.github.io/Smart-Factory-Transformation/
    repo_url: https://github.com/fedcal/Smart-Factory-Transformation
    repo_name: fedcal/Smart-Factory-Transformation
    edit_uri: edit/main/docs/docs/
    docs_dir: docs
    site_dir: site
    theme:
      name: material
      language: it
      features:
        - navigation.tabs
        - navigation.tabs.sticky
        - navigation.sections
        - navigation.expand
        - navigation.instant
        - navigation.top
        - search.suggest
        - search.highlight
        - content.code.copy
        - content.code.annotate
        - toc.follow
      palette:
        - scheme: default
          primary: indigo
          accent: indigo
          toggle:
            icon: material/brightness-7
            name: Switch to dark mode
        - scheme: slate
          primary: indigo
          accent: indigo
          toggle:
            icon: material/brightness-4
            name: Switch to light mode
      icon:
        repo: fontawesome/brands/github
    plugins:
      - search
      - i18n:
          docs_structure: folder
          languages:
            - locale: it
              name: Italiano
              default: true
              build: true
              site_name: Smart Factory Transformation
            - locale: en
              name: English
              build: true
              site_name: Smart Factory Transformation
              nav_translations:
                Architettura: Architecture
                Iniziare: Getting Started
                Contributing: Contributing
          reconfigure_material: true
    markdown_extensions:
      - admonition
      - attr_list
      - md_in_html
      - tables
      - toc:
          permalink: true
      - pymdownx.details
      - pymdownx.superfences:
          custom_fences:
            - name: mermaid
              class: mermaid
              format: !!python/name:pymdownx.superfences.fence_code_format
      - pymdownx.tabbed:
          alternate_style: true
      - pymdownx.snippets
      - pymdownx.highlight:
          anchor_linenums: true
    extra_css:
      - assets/custom.css
    extra:
      social:
        - icon: fontawesome/brands/github
          link: https://github.com/fedcal/Smart-Factory-Transformation
    nav:
      - Home: index.md
      - Iniziare: getting-started.md
      - Architettura:
        - Overview: architecture/overview.md
      - Contributing: contributing/index.md
    ```

    Creare `docs/requirements.txt`:
    ```
    mkdocs-material==9.7.6
    mkdocs-static-i18n==1.3.1
    pymdown-extensions>=10.9
    mkdocs>=1.6.0
    ```

    Creare `docs/docs/index.md` (homepage IT) con:
    - Header "Smart Factory Transformation"
    - Tagline core value: "Ogni decisione critica dell'AI passa per un essere umano informato, ma nessun essere umano è mai solo davanti a un problema operativo."
    - Sezione "Cos'è" (2-3 paragrafi sintetici dal PROJECT.md)
    - Sezione "Per chi" (3 audience: valutatori, community, stakeholder Mantis)
    - Sezione "Stato del progetto" con badge fittizio "Phase 1: Foundation & Monorepo"
    - Link alle pagine successive

    Creare `docs/docs/en/index.md` con la traduzione corrispondente (header "Smart Factory Transformation", tagline EN: "Every critical AI decision passes through an informed human, but no human is ever alone facing an operational problem.", paragrafi tradotti).

    Creare `docs/docs/getting-started.md` (IT) con placeholder che linka:
    - Toolchain prerequisites: `docs/contributing/toolchain.md` (plan 01)
    - Compose dev stack: `docs/contributing/compose-dev-stack.md` (plan 02)
    - CI pipeline: `docs/contributing/ci-pipeline.md` (plan 05)
    - Helm deploy: `docs/operations/helm-deploy.md` (plan 06)
    Nota: "Contenuti sostanziali in espansione nelle fasi 2+".

    Creare `docs/docs/en/getting-started.md` con traduzione equivalente.

    Creare `docs/docs/architecture/overview.md` (IT) placeholder con:
    - "Architettura ad alto livello"
    - Diagramma Mermaid placeholder che mostra: developer -> repo -> CI workflows -> docker compose dev / helm prod -> agents/UI/OT-bridge
    - "Dettagli espansi nelle fasi successive"

    Creare `docs/docs/en/architecture/overview.md` con traduzione equivalente.

    Creare `docs/docs/contributing/index.md` (IT) e `docs/docs/en/contributing/index.md` (EN) come hub che linkano:
    - `commit-conventions.md` (plan 04)
    - `pre-commit.md` (plan 04)
    - `ci-pipeline.md` (plan 05)
    - branch-protection.md (plan 03)

    Creare `docs/docs/assets/custom.css` minimo (può essere vuoto o con commento `/* SFT custom styles - populated as needed */`).
  </action>
  <acceptance_criteria>
    - `docs/mkdocs.yml` esiste e contiene `mkdocs-static-i18n` (via plugin name `i18n`)
    - `docs/mkdocs.yml` contiene `language: it` (default) e `locale: en` (secondary)
    - `docs/requirements.txt` contiene `mkdocs-material==9.7.6` e `mkdocs-static-i18n==1.3.1`
    - Esistono 4 pagine IT (`index.md`, `getting-started.md`, `architecture/overview.md`, `contributing/index.md`) e 4 EN (sotto `docs/docs/en/`)
    - `cd docs && python3 -m pip install -r requirements.txt && mkdocs build` (in CI o env isolato) produce `docs/site/` senza warning critici (deprecation warning di plugin sono OK)
    - `python3 -c "import yaml; yaml.safe_load(open('docs/mkdocs.yml'))"` exits 0 (modulo i `!!python/name:` che yaml safe_load NON parsa — è atteso; usare `yaml.full_load` se necessario)
    - `grep -E "^- i18n:|i18n:" docs/mkdocs.yml` exits 0
  </acceptance_criteria>
</task>

<task id="1-07-02" wave="2" type="auto">
  <name>Task 2: .github/workflows/docs-deploy.yml + Makefile docs target</name>
  <files>.github/workflows/docs-deploy.yml, Makefile</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 8 docs-deploy.yml righe ~1170-1190)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: docs-deploy.yml pronto in Fase 1, effettivo da Fase 2)
  </read_first>
  <action>
    Creare `.github/workflows/docs-deploy.yml`:
    ```yaml
    name: Deploy Docs
    on:
      push:
        branches: [main]
        paths:
          - 'docs/**'
          - '.github/workflows/docs-deploy.yml'
      workflow_dispatch:
    permissions:
      contents: write   # needed for gh-deploy push to gh-pages branch
    concurrency:
      group: docs-deploy-${{ github.ref }}
      cancel-in-progress: true
    jobs:
      deploy:
        runs-on: ubuntu-latest
        timeout-minutes: 10
        steps:
          - uses: actions/checkout@v4
            with:
              fetch-depth: 0
          - uses: actions/setup-python@v5
            with:
              python-version: '3.12'
              cache: 'pip'
          - name: Install docs dependencies
            run: pip install -r docs/requirements.txt
          - name: Build site (validate)
            run: mkdocs build --strict
            working-directory: docs/
          - name: Deploy to gh-pages
            run: mkdocs gh-deploy --force --clean --verbose
            working-directory: docs/
    ```
    Nota: `--strict` fa fallire la build se ci sono broken link o warning critici. Le pagine placeholder devono passare strict mode (per questo le pagine create in Task 1 hanno SOLO link interni risolvibili).

    Aggiornare `Makefile` per migliorare il target `docs`:
    ```
    docs:
    	@command -v mkdocs >/dev/null || (echo "mkdocs non trovato: cd docs && pip install -r requirements.txt" && exit 1)
    	cd docs && mkdocs build --strict
    docs-serve:
    	cd docs && mkdocs serve -a 127.0.0.1:8000
    ```
    Aggiungere `docs-serve` a `.PHONY:`.

    Documentare in `docs/contributing/index.md` (IT) e `docs/contributing/en/index.md` (EN) il comando `make docs-serve` per preview locale.
  </action>
  <acceptance_criteria>
    - `.github/workflows/docs-deploy.yml` esiste e contiene `mkdocs gh-deploy`
    - `.github/workflows/docs-deploy.yml` contiene `permissions: contents: write`
    - `.github/workflows/docs-deploy.yml` contiene `paths:` filter per non triggerare su modifiche non-docs
    - `Makefile` target `docs` esegue `mkdocs build --strict`
    - `Makefile` ha nuovo target `docs-serve`
    - `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/docs-deploy.yml'))"` exits 0
    - `make -n docs` mostra `mkdocs build --strict`
  </acceptance_criteria>
</task>

</tasks>

<verification>
1. `python3 -c "import yaml; yaml.full_load(open('docs/mkdocs.yml'))"` exits 0
2. `find docs/docs -name "*.md" | wc -l` >= 8 (4 IT + 4 EN)
3. `cd docs && pip install -r requirements.txt && mkdocs build --strict` exits 0 (in env con Python 3.12)
4. `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/docs-deploy.yml'))"` exits 0
5. Test post-merge: dopo merge su main, verificare che il branch `gh-pages` venga aggiornato dal workflow e che `https://fedcal.github.io/Smart-Factory-Transformation/` mostri il sito IT + selettore EN.
</verification>

<success_criteria>
- MkDocs Material i18n scaffold funzionante (IT default + EN)
- `mkdocs build --strict` passa senza errori
- `docs-deploy.yml` configurato per gh-pages auto-deploy
- Struttura pronta ad accogliere contenuti Phase 2+
- PLAT-10 parzialmente coperto (docs side; release Changesets in plan 08)
</success_criteria>

<output>
Create `.planning/phases/01-foundation-monorepo/01-07-SUMMARY.md` quando done.
</output>
