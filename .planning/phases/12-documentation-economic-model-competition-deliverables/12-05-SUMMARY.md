---
phase: 12-documentation-economic-model-competition-deliverables
plan: "05"
subsystem: ci-infra
tags: [ci, brand-scrub, mike, mkdocs, versioning, sc-3, sc-4, sc-5, del-08, doc-02, doc-03]

requires:
  - phase: 12-04
    provides: SC-5 binary-image removal (6 PNGs git rm'd); transformation.md + glossary Phase 8-11
  - phase: 12-03b
    provides: 5 traced ADRs IT+EN + index + nav
  - phase: 12-03a
    provides: STRIDE threat model + OWASP LLM + security overview IT+EN
  - phase: 12-02b
    provides: Use cases prioritizzati + adoption roadmap IT+EN
  - phase: 12-02a
    provides: C4 diagrams + functional workflows IT+EN (architettura, analisi funzionale)
  - phase: 12-01
    provides: TCO/OEPV script + economic-analysis pages IT+EN
  - phase: 12-00
    provides: MkDocs scaffold, docs structure, requirements.txt (mike==2.2.0)

provides:
  - "Brand-scrub blocking CI gate (DEL-08/SC-4): grep case-insensitive su git ls-files escluso .planning/, termine a parti per evitare self-match"
  - "SC-5 blocking CI gate: zero immagini binarie (png/jpg/jpeg/svg/gif/webp) sotto docs/docs/"
  - "Personal-ref scrub CI gate: pattern a parti per evitare self-match"
  - "Local navigability assertion CI gate: use_directory_urls: false in mkdocs.yml"
  - "mike versioning in docs-deploy.yml: main + latest aliases, mkdocs build --strict come validazione"
  - "index.md aggiornato con indice deliverable di concorso e nota SIMULATED TARGET (SC-3)"
  - "Correzione residuo brand in value-drivers.md IT+EN (A-055: IDC/Aveva al posto del brand rimosso)"
  - "Build strict MkDocs finale: verde"
  - "Review SC-3 completata: ogni sezione deliverable tracciata al codice/SUMMARY"

affects:
  - future-phases
  - ci-gates
  - docs-deploy

tech-stack:
  added: ["mike==2.2.0 (già in requirements.txt da 12-00, ora wired in docs-deploy.yml)"]
  patterns:
    - "Brand-scrub: termine costruito a parti (TERM='accent'; TERM+='ure') per evitare self-match CI workflow"
    - "Personal-ref scrub: pattern costruito a parti (PA='fed'; PB='cal'; PAT='...')"
    - "Gate .planning/ exclusion rationale documentato inline nel workflow"
    - "mike versioning: mike deploy --push --update-aliases main latest + mike set-default --push latest"

key-files:
  created: []
  modified:
    - ".github/workflows/ci.yml"
    - ".github/workflows/docs-deploy.yml"
    - "docs/docs/index.md"
    - "docs/docs/economic-analysis/value-drivers.md"
    - "docs/docs/en/economic-analysis/value-drivers.md"

key-decisions:
  - "Brand-scrub gate esclude .planning/ (meta GSD interno, non superficie deliverable) — rationale documentato nel workflow"
  - "Termine brand costruito a parti in ci.yml per evitare T-12-05-02 self-match"
  - "Personal-ref pattern costruito a parti per lo stesso motivo"
  - "mike sostituisce mkdocs gh-deploy --force nel deploy step; il build strict rimane come validazione separata"
  - "Custom domain (CNAME) documentato come opzionale con commento, non configurato (deferred)"
  - "value-drivers.md A-055: sostituito brand con IDC/Aveva per eliminare residuo SC-4"

patterns-established:
  - "Gate self-match trap: qualsiasi termine grep in un workflow CI deve essere costruito a parti per evitare che il workflow flaggi se stesso"
  - "Gate .planning/ exclusion: i file di pianificazione interna non sono superficie deliverable e vanno sempre esclusi dalla scansione brand/personal"

requirements-completed: [DEL-08, DOC-02, DOC-03, DOC-15]

duration: 20min
completed: "2026-05-25"
---

# Phase 12 Plan 05: CI Brand-Scrub Gates + mike Versioning Summary

**Gate brand-scrub DEL-08/SC-4 e SC-5 blocking in ci.yml (termine a parti, .planning/ escluso con rationale), mike versioning DOC-02/03 in docs-deploy.yml, build strict finale verde, review SC-3 completata.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-25T07:46:00Z
- **Completed:** 2026-05-25T07:51:03Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Brand-scrub gate blocking (DEL-08/SC-4) aggiunto a ci.yml con termine costruito a parti per evitare self-match; esclude .planning/ con rationale documentato inline
- SC-5 gate blocking (zero immagini binarie sotto docs/docs/) aggiunto a ci.yml; entrambi i gate passano sull'albero corrente
- mike versioning (main + latest aliases) wired in docs-deploy.yml; build strict mantenuoto come step di validazione separato
- index.md aggiornato con indice deliverable di concorso e nota SIMULATED TARGET (SC-3)
- Correzione residuo brand in value-drivers.md IT+EN (A-055: sostituito con IDC/Aveva)
- `mkdocs build --strict` finale: verde (3.0s, zero errori/warning)

## Task Commits

1. **Task 1: Gate brand-scrub (DEL-08/SC-4) + SC-5 in ci.yml** — `258bc0e` (feat)
2. **Task 2: mike versioning in docs-deploy.yml (DOC-02/03)** — `d4a463e` (feat)
3. **Task 3: Build strict finale + index.md + SC-3 review** — `701e4d0` (feat)

## Files Created/Modified

- `.github/workflows/ci.yml` — 4 step blocking aggiunti: brand-scrub (DEL-08/SC-4), SC-5 binary-image, personal-ref scrub, local navigability assertion
- `.github/workflows/docs-deploy.yml` — mkdocs gh-deploy sostituito con mike deploy; build strict mantenuto
- `docs/docs/index.md` — indice deliverable di concorso, nota SIMULATED TARGET, navigazione estesa
- `docs/docs/economic-analysis/value-drivers.md` — A-055: rimosso residuo brand (IT)
- `docs/docs/en/economic-analysis/value-drivers.md` — A-055: rimosso residuo brand (EN)

## SC-3 Traceability Review

Review completa: ogni sezione deliverable traccia a codice spedito o SUMMARY di fase.

| Sezione | Evidence |
|---------|---------|
| **Architettura** (C4 context/container/component, HITL, LLM serving) | 12-02a-SUMMARY (Mermaid C4, C4Context/C4Container/C4Component nativo); codice: `architecture/*.md` IT+EN |
| **Analisi Funzionale** (Operations/Maintenance/Training workflows) | 12-02a-SUMMARY (3 workflow Mermaid IT+EN); codice: `functional-analysis/*.md` |
| **Casi d'Uso** (8 use case 0-3m/3-9m/9-18m) | 12-02b-SUMMARY (use case prioritizzati DOC-07/DEL-03); codice: `use-cases/index.md` IT+EN |
| **Roadmap di Adozione** (fasi, KPI, milestone, rischi) | 12-02b-SUMMARY (roadmap DOC-09/DEL-05); codice: `adoption-roadmap/index.md` IT+EN |
| **Analisi Economica** (TCO, OEPV, value driver) | 12-01-SUMMARY (tco_oepv.py + CSV committed + 8 pagine DOC-01/08); valori SIMULATED TARGET ECO-04; A-051..A-057 tracciati |
| **Security & Governance** (STRIDE, OWASP LLM, explainability) | 12-03a-SUMMARY (STRIDE threat model + OWASP LLM Top-10 IT+EN DOC-10/11); codice: `security/*.md` |
| **ADR** (5 Architecture Decision Records) | 12-03b-SUMMARY (5 ADR IT+EN DOC-13); codice: `adr/ADR-00{1-5}-*.md` |
| **Trasformazione** | 12-04-SUMMARY (transformation.md neutral wording DOC-17); codice: `transformation.md` IT+EN |
| **Mock UI / User Journey** | 12-04-SUMMARY (ui-mock Mermaid, 6 PNG rimossi SC-5); codice: `ui-mock.md` IT+EN |
| **Glossario** | 12-04-SUMMARY (Phase 8-11 terms DOC-18); codice: `glossary.md` IT+EN |

**Nessun contenuto aspirazionale identificato.** Tutte le sezioni riportano metriche come SIMULATED TARGET con reference a baseline sintetica (Phase 9) e letteratura. Nessuna sezione promette funzionalità non implementate nel codice.

**Gap identificati (non bloccanti):**
- `ui-mock.md` linka a mock-ups Mermaid ma non a screenshot reali — coerente con PoC su dati simulati; dichiarato esplicitamente
- Agenti reference documentati ma non tutti con endpoint FastAPI completi — fuori scope MVP v1.0, coperto da Assumption Register

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Residuo brand in value-drivers.md IT+EN (A-055)**
- **Found during:** Task 1 — esecuzione brand-scrub locale prima di aggiungere il gate
- **Issue:** `docs/docs/economic-analysis/value-drivers.md` e la versione EN contenevano il brand rimosso nella colonna letteratura di A-055 ("Accenture/IDC Industry 4.0")
- **Fix:** Sostituito con "IDC/Aveva Industry 4.0" in entrambi i file IT+EN (stessa fonte citata nella sezione 3 MTTR reduction)
- **Files modified:** `docs/docs/economic-analysis/value-drivers.md`, `docs/docs/en/economic-analysis/value-drivers.md`
- **Verification:** `git ls-files | grep -v .planning/ | xargs grep -ril "$TERM"` → nessun match
- **Committed in:** `258bc0e` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Pattern personal-ref gate costruito a parti**
- **Found during:** Task 1 — verifica post-gate: il gate personal-ref flag-ava ci.yml stesso
- **Issue:** Lo step "Personal-ref scrub" conteneva `fedcal|federicocalo` come stringa letterale e il gate flaggiava se stesso
- **Fix:** Pattern costruito a parti (`PA="fed"; PB="cal"; PC="federicoc"; PD="alo"; PAT="${PA}${PB}|${PC}${PD}"`) per evitare self-match — stesso pattern del brand-scrub
- **Files modified:** `.github/workflows/ci.yml`
- **Verification:** `git ls-files | grep -v .planning/ | xargs grep -ril -E 'fedcal|federicocalo'` → nessun match
- **Committed in:** `258bc0e` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 residual-brand bug, 1 Rule 2 missing self-match guard)
**Impact on plan:** Entrambe le correzioni necessarie per il corretto funzionamento del gate. Nessuno scope creep.

## Issues Encountered

Nessuno al di là delle deviazioni già documentate. Il build strict è rimasto verde per tutta l'esecuzione.

## User Setup Required

None — nessuna configurazione esterna richiesta. Il deploy mike su gh-pages avverrà automaticamente al prossimo push su main che modifica `docs/**`.

## Next Phase Readiness

Fase 12 (documentation-economic-model-competition-deliverables) **COMPLETATA**. Tutti i deliverable di concorso sono tracciati, documentati bilingue (IT/EN), e serviti via GitHub Pages con versioning mike.

**Gate CI attivi:**
- Brand-scrub DEL-08/SC-4: zero occorrenze brand su tutti i file tracciati (escluso .planning/)
- SC-5: zero immagini binarie sotto docs/docs/
- Personal-ref scrub: zero riferimenti personali nei file tracciati
- Local navigability: use_directory_urls: false assicurato

**Prossimi step eventuali:**
- Deploy live su GitHub Pages verificabile dopo primo push con il nuovo workflow
- CODE_OF_CONDUCT.md (DOC-16) — deferred, non bloccante (README/CONTRIBUTING linkano già al file)

---
*Phase: 12-documentation-economic-model-competition-deliverables*
*Completed: 2026-05-25*

## Self-Check: PASSED

- [x] `.github/workflows/ci.yml` — modificato e committed (`258bc0e`)
- [x] `.github/workflows/docs-deploy.yml` — modificato e committed (`d4a463e`)
- [x] `docs/docs/index.md` — modificato e committed (`701e4d0`)
- [x] `docs/docs/economic-analysis/value-drivers.md` — modificato e committed (`258bc0e`)
- [x] `docs/docs/en/economic-analysis/value-drivers.md` — modificato e committed (`258bc0e`)
- [x] Brand-scrub gate: verde sull'albero corrente
- [x] SC-5 gate: verde (zero immagini binarie)
- [x] Personal-ref scrub: verde
- [x] `mkdocs build --strict`: verde (3.0s)
- [x] CSV economici: nessun drift
