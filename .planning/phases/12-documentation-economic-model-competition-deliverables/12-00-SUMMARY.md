---
phase: 12-documentation-economic-model-competition-deliverables
plan: "00"
subsystem: docs
tags: [docs, mkdocs, oepv, economic-model, mike, i18n, scaffold]
dependency_graph:
  requires: []
  provides: [mike-pin, oepv-vendor, nav-stubs, economic-scaffold]
  affects: [docs/mkdocs.yml, docs/requirements.txt, docs/economic-analysis/, docs/docs/]
tech_stack:
  added: [mike==2.2.0]
  patterns: [mkdocs-static-i18n folder structure, OEPV vendor copy stdlib-only, Nyquist scaffold test]
key_files:
  created:
    - docs/requirements.txt (mike==2.2.0 aggiunto)
    - docs/economic-analysis/_oepv_vendor.py
    - docs/economic-analysis/params.toml
    - docs/economic-analysis/tco_oepv.py
    - docs/economic-analysis/tests/__init__.py
    - docs/economic-analysis/tests/test_tco_oepv.py
    - docs/docs/functional-analysis/index.md
    - docs/docs/functional-analysis/operations-workflow.md
    - docs/docs/functional-analysis/maintenance-workflow.md
    - docs/docs/functional-analysis/training-workflow.md
    - docs/docs/use-cases/index.md
    - docs/docs/adoption-roadmap/index.md
    - docs/docs/economic-analysis/index.md
    - docs/docs/economic-analysis/tco.md
    - docs/docs/economic-analysis/oepv.md
    - docs/docs/economic-analysis/value-drivers.md
    - docs/docs/security/index.md
    - docs/docs/security/stride-threat-model.md
    - docs/docs/security/owasp-llm.md
    - docs/docs/adr/index.md
    - docs/docs/transformation.md
    - docs/docs/en/functional-analysis/index.md
    - docs/docs/en/functional-analysis/operations-workflow.md
    - docs/docs/en/functional-analysis/maintenance-workflow.md
    - docs/docs/en/functional-analysis/training-workflow.md
    - docs/docs/en/use-cases/index.md
    - docs/docs/en/adoption-roadmap/index.md
    - docs/docs/en/economic-analysis/index.md
    - docs/docs/en/economic-analysis/tco.md
    - docs/docs/en/economic-analysis/oepv.md
    - docs/docs/en/economic-analysis/value-drivers.md
    - docs/docs/en/security/index.md
    - docs/docs/en/security/stride-threat-model.md
    - docs/docs/en/security/owasp-llm.md
    - docs/docs/en/adr/index.md
    - docs/docs/en/transformation.md
  modified:
    - docs/mkdocs.yml (nav espanso + nav_translations EN + duplicato Architettura rimosso)
decisions:
  - mike==2.2.0 via pip in docs/requirements.txt (non npm)
  - oepv.py vendorato byte-for-byte con header-commento origine (no drift silenzioso)
  - params.toml separato per sezione [oepv] e [tco] (Wave 1 finalizza valori placeholder)
  - Nyquist scaffold: 2 test @pytest.mark.skip (non module-level skip) per granularità per-test
  - Duplicato chiave Architettura rimosso da nav_translations (YAML non ammette chiavi duplicate)
metrics:
  duration_min: 6
  completed_date: "2026-05-25"
  tasks_completed: 3
  files_created: 36
  files_modified: 2
---

# Phase 12 Plan 00: Docs Foundation — mike pin + nav stubs + OEPV vendor + Nyquist scaffold

Wave 0 foundation per Phase 12: mike==2.2.0 pinnato, 30 stub IT+EN creati e referenziati nel nav, _oepv_vendor.py importabile standalone da Phase 9, scaffold economico tco_oepv.py + params.toml, test Nyquist skipped; mkdocs build --strict verde.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Pin mike + vendorare oepv.py + scaffold economico/test | 1bf9e66 | docs/requirements.txt, _oepv_vendor.py, params.toml, tco_oepv.py, tests/ |
| 2 | Creare stub IT + mirror EN (15+15 file) | e6d6b54 | 30 file stub in docs/docs/ e docs/docs/en/ |
| 3 | Espandere mkdocs.yml nav + nav_translations + build strict | 09f4d9a | docs/mkdocs.yml |

## Verification

- `grep -q "mike==2.2.0" docs/requirements.txt` — PASS
- `python3 -c "from _oepv_vendor import compute_oepv, OepvConfig; r=compute_oepv(12.5, 68.0, OepvConfig()); assert 0<=r.total_score<=100"` — PASS (score=55.2198)
- `python3 -c "import tomllib; p=tomllib.load(open('params.toml','rb')); assert p['oepv']['base_d_asta_eur']==108000.0"` — PASS
- All 15 IT + 15 EN stubs exist — PASS (all-stubs-mirrored-ok)
- `mkdocs build --strict` exit 0, zero WARNING/ERROR — PASS

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rimosso duplicato chiave `Architettura` in nav_translations**
- **Found during:** Task 3
- **Issue:** Il blocco nav_translations originale conteneva `Architettura: Architecture` due volte; YAML non ammette chiavi duplicate (la seconda sovrascrive silenziosamente la prima)
- **Fix:** Mantenuta una sola occorrenza; build --strict non impattato
- **Files modified:** docs/mkdocs.yml
- **Commit:** 09f4d9a

## Known Stubs

| File | Reason | Resolving plan |
|------|--------|----------------|
| docs/docs/functional-analysis/*.md | Stub placeholder — contenuto Wave 1-4 | 12-01 e successivi |
| docs/docs/use-cases/index.md | Stub placeholder | 12-02 |
| docs/docs/adoption-roadmap/index.md | Stub placeholder | 12-03 |
| docs/docs/economic-analysis/*.md | Stub placeholder — TCO/OEPV Wave 1 | 12-01 |
| docs/docs/security/*.md | Stub placeholder | 12-04 |
| docs/docs/adr/index.md | Stub placeholder | 12-05 |
| docs/docs/transformation.md | Stub placeholder | 12-06 |
| docs/economic-analysis/tco_oepv.py | Stub script — Wave 1 implementa calcoli | 12-01 |
| docs/economic-analysis/tests/test_tco_oepv.py | Nyquist scaffold skipped — Wave 1 | 12-01 |

Tutti gli stub sono intenzionali: garantiscono `mkdocs build --strict` verde mentre Wave 1-5 popolano il contenuto.

## Threat Flags

Nessuna nuova superficie di sicurezza introdotta — tutti i file sono documentazione/script locali senza endpoint di rete.

## Self-Check: PASSED

- `1bf9e66` presente in git log
- `e6d6b54` presente in git log
- `09f4d9a` presente in git log
- docs/requirements.txt contiene mike==2.2.0
- 30 stub IT+EN esistono su filesystem
- mkdocs build --strict exit 0
