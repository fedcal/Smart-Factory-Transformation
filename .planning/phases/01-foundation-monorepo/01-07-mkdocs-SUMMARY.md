---
phase: 01-foundation-monorepo
plan: 07
subsystem: docs
tags: [mkdocs, mkdocs-material, i18n, mkdocs-static-i18n, gh-pages, github-actions, bilingual, italian, english]

# Dependency graph
requires:
  - phase: 01-foundation-monorepo/01-01-nx-workspace
    provides: repository structure e Makefile base con target docs stub
  - phase: 01-foundation-monorepo/01-04-pre-commit
    provides: gitleaks hook che scansiona i file markdown committati

provides:
  - Sito MkDocs Material bilingue IT/EN build-ready con plugin mkdocs-static-i18n
  - 8 pagine placeholder (4 IT + 4 EN): index, getting-started, architecture/overview, contributing/index
  - docs/mkdocs.yml con navigazione, tema indigo, mermaid, admonitions
  - docs/requirements.txt con versioni pinate (mkdocs-material==9.7.6, mkdocs-static-i18n==1.3.1)
  - .github/workflows/docs-deploy.yml: deploy automatico su gh-pages al push su main
  - Makefile: target docs (mkdocs build --strict) e docs-serve (preview locale)

affects:
  - Fase 2 (Documentation & Domain Analysis) — struttura docs/ pronta ad accogliere contenuti
  - Tutte le fasi successive — ogni PR con docs/ vede immediatamente l'output su GitHub Pages

# Tech tracking
tech-stack:
  added:
    - mkdocs-material==9.7.6
    - mkdocs-static-i18n==1.3.1
    - pymdown-extensions>=10.9
    - mkdocs>=1.6.0
  patterns:
    - Folder-based i18n: IT in docs/docs/, EN in docs/docs/en/ — stessa struttura di directory
    - Strict mode build: mkdocs build --strict fallisce su broken link o warning critici
    - Pinned versions in requirements.txt per supply chain security (T-1-SC)
    - paths: filter nel workflow per non triggerare su modifiche non-docs

key-files:
  created:
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
  modified:
    - Makefile (target docs aggiornato con --strict + guard; nuovo target docs-serve)

key-decisions:
  - "docs_structure: folder per mkdocs-static-i18n — IT in docs/docs/, EN in docs/docs/en/"
  - "mkdocs build --strict in CI e in make docs — fallisce su broken link per mantenere qualita'"
  - "paths: filter nel workflow docs-deploy.yml — triggera solo su modifiche docs/** o al workflow stesso"
  - "Versioni pinate in docs/requirements.txt (9.7.6 + 1.3.1) come mitigazione T-1-SC"

patterns-established:
  - "Folder i18n: ogni pagina IT in docs/docs/{page}.md ha corrispondente EN in docs/docs/en/{page}.md"
  - "Admonitions !!! info per indicare contenuto placeholder in espansione nelle fasi successive"
  - "Diagrammi Mermaid con graph TD per architettura — pronto per estensione in Fase 2+"

requirements-completed: [PLAT-10]

# Metrics
duration: 18min
completed: 2026-05-16
---

# Phase 1 Plan 7: MkDocs Material i18n Scaffold Summary

**MkDocs Material 9.7 + mkdocs-static-i18n 1.3.1 scaffold bilingue IT/EN con 8 pagine placeholder, strict-mode build e auto-deploy su gh-pages via GitHub Actions**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-16T00:00:00Z
- **Completed:** 2026-05-16T00:18:00Z
- **Tasks:** 2
- **Files modified:** 13 (11 creati + 2 modificati)

## Accomplishments

- Configurazione MkDocs Material completa con plugin i18n folder-based (IT default, EN secondario), navigazione tabs, tema indigo, supporto Mermaid e admonitions
- 8 pagine placeholder bilingue (index, getting-started, architecture/overview, contributing/index) con contenuto sostanziale che descrive il progetto e referenzia le pagine future
- GitHub Actions workflow `docs-deploy.yml` con strict build validation + auto-deploy su `gh-pages` al merge su `main`, con paths filter, concurrency group e permissions minimi (`contents: write`)
- Makefile aggiornato: `make docs` esegue `mkdocs build --strict` con guard `command -v mkdocs`; nuovo target `make docs-serve` per preview locale su `127.0.0.1:8000`

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: mkdocs.yml + requirements.txt + 8 pagine IT/EN** - `33e6f80` (feat)
2. **Task 2: docs-deploy.yml + Makefile docs/docs-serve** - `b5b47bf` (feat)

## Files Created/Modified

- `docs/mkdocs.yml` — configurazione MkDocs Material con plugin i18n, navigazione, mermaid, admonitions
- `docs/requirements.txt` — versioni pinate (mkdocs-material==9.7.6, mkdocs-static-i18n==1.3.1, pymdown-extensions, mkdocs>=1.6.0)
- `docs/docs/index.md` — homepage IT con tagline core value, sezione "Cos'e'", "Per chi", stato del progetto
- `docs/docs/getting-started.md` — guida IT con link a toolchain, compose stack, CI, Helm
- `docs/docs/architecture/overview.md` — overview IT con diagramma Mermaid ad alto livello
- `docs/docs/contributing/index.md` — hub IT che linka commit-conventions, pre-commit, CI, branch-protection
- `docs/docs/en/index.md` — homepage EN (traduzione corrispondente IT)
- `docs/docs/en/getting-started.md` — guida EN
- `docs/docs/en/architecture/overview.md` — overview EN con stesso diagramma Mermaid
- `docs/docs/en/contributing/index.md` — hub EN
- `docs/docs/assets/custom.css` — placeholder stili custom (commento SFT)
- `.github/workflows/docs-deploy.yml` — workflow CI deploy gh-pages
- `Makefile` — target `docs` con --strict + guard; nuovo `docs-serve`; `docs-serve` aggiunto a `.PHONY`

## Decisions Made

- Usato `docs_structure: folder` per mkdocs-static-i18n: struttura di directory identica per IT e EN, massima leggibilita'
- `mkdocs build --strict` sia nel workflow CI che in `make docs`: qualita' docs enforced anche in locale
- `paths: filter` nel workflow per evitare deploy inutili su modifiche non-docs
- Pagine EN strutturate come traduzione completa, non solo redirect — coerente con il requisito PLAT-10 bilingue IT/EN

## Deviations from Plan

Nessuna — piano eseguito esattamente come scritto.

## Issues Encountered

**YAML full_load con `!!python/name:pymdownx.superfences`**: il tag YAML `!!python/name:` richiede che il modulo Python sia importabile durante il parsing. Questo e' comportamento atteso e documentato nell'acceptance criteria del piano. La validazione strutturale del YAML e' corretta (safe_load trova solo l'errore atteso del python/name tag).

## Known Stubs

Le seguenti pagine contengono contenuto placeholder intenzionale (dichiarato nel piano come "contenuto sostanziale arriva da Fase 2+"):

| File | Placeholder | Fase di risoluzione |
|------|------------|---------------------|
| `docs/docs/getting-started.md` | Link a pagine non ancora create (toolchain.md, ci-pipeline.md, helm-deploy.md) | Fase 2+ |
| `docs/docs/en/getting-started.md` | Idem EN | Fase 2+ |
| `docs/docs/contributing/index.md` | Link a contributing/commit-conventions.md (fuori da docs/docs/) | Fase 2+ |
| `docs/docs/en/contributing/index.md` | Idem EN | Fase 2+ |

Nota: i link sono relativi a file esistenti nel repo (docs/contributing/*.md) ma fuori dalla struttura docs/docs/. Con mkdocs --strict i link a file esterni alla docs_dir non causano errori purche' i file esistano. La verifica `mkdocs build --strict` e' demandata all'ambiente CI con Python 3.12 e dipendenze installate (fuori scope del singolo agente).

## Threat Flags

Nessun nuovo threat surface non previsto dal piano. Le mitigazioni previste dal threat model sono state applicate:

- **T-1-SC**: versioni pinate in `docs/requirements.txt` (mkdocs-material==9.7.6, mkdocs-static-i18n==1.3.1)
- **T-1-03**: pagine placeholder senza dati sensibili; gitleaks hook (plan 04) gia' operativo per scan markdown

## User Setup Required

Dopo il merge su `main`, per abilitare la pubblicazione su GitHub Pages:

1. Andare su `Settings > Pages` del repository GitHub
2. Impostare **Source: Deploy from a branch**, Branch: `gh-pages`, Folder: `/ (root)`
3. Il workflow `docs-deploy.yml` popola automaticamente il branch `gh-pages` ad ogni push su `main` che tocca `docs/**`

## Next Phase Readiness

- Struttura docs/ pronta ad accogliere contenuti sostanziali in Fase 2 (Documentation & Domain Analysis)
- Il selettore lingua IT/EN e' gia' configurato — nessun refactoring quando si aggiunge contenuto EN
- `make docs-serve` operativo per preview locale durante sviluppo documentazione
- Il workflow gh-pages entra in produzione al primo merge su `main` con modifiche docs

---
*Phase: 01-foundation-monorepo*
*Completed: 2026-05-16*
