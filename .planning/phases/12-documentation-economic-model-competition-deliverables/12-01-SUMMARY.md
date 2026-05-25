---
phase: 12
plan: "01"
subsystem: economic-model
tags: [tco, oepv, value-drivers, risk-register, reproducible, ecm-08]
dependency_graph:
  requires: ["12-00"]
  provides: [tco_oepv_script, tco_table_csv, sensitivity_table_csv, summary_md, economic_analysis_docs_it_en]
  affects: [docs_economic_analysis_pages]
tech_stack:
  added: [tomllib]
  patterns: [single-source-of-truth, vendored-dependency, parametric-simulation]
key_files:
  created:
    - docs/economic-analysis/tco_oepv.py
    - docs/economic-analysis/tco_table.csv
    - docs/economic-analysis/sensitivity_table.csv
    - docs/economic-analysis/summary.md
    - docs/economic-analysis/tests/test_vendor_parity.py
  modified:
    - docs/economic-analysis/params.toml
    - docs/economic-analysis/tests/test_tco_oepv.py
    - docs/docs/economic-analysis/index.md
    - docs/docs/economic-analysis/tco.md
    - docs/docs/economic-analysis/oepv.md
    - docs/docs/economic-analysis/value-drivers.md
    - docs/docs/en/economic-analysis/index.md
    - docs/docs/en/economic-analysis/tco.md
    - docs/docs/en/economic-analysis/oepv.md
    - docs/docs/en/economic-analysis/value-drivers.md
decisions:
  - "Python 3.14 compat fix: sys.modules registration before exec_module per @dataclass(frozen=True) con from __future__ import annotations (regressione Python 3.14)"
  - "Integration e training aggiunti a params.toml come componenti 5 e 6 del TCO per rispettare ECO-06"
  - "Sensitivity table usa pt_optimistic (68.0) come PT fisso — scenario ottimistico per la sensitivity"
  - "Assumption Register voci A-051..A-057 introdotte inline in value-drivers.md (non nel registro principale che richiede YAML autogeneration)"
  - "test_tco_oepv.py mantiene test_vendor_parity() integrato + test_vendor_parity.py separato con 5 test di classe"
metrics:
  duration: "25min"
  completed: "2026-05-25"
  tasks: 2
  files: 15
---

# Phase 12 Plan 01: TCO+OEPV Modello Economico Riproducibile — Summary

**One-liner:** Script Python deterministico (params.toml → tco_oepv.py) genera TCO 3yr 6 componenti (189.570 EUR) + OEPV 70/30 scenari PT 68/55 + sensitivity non lineare 0-20%; value driver come SIMULATED TARGET con baseline Mantis sintetica + letteratura citata; 9 test verdi inclusa parita vendor anti-drift; 8 pagine docs IT+EN popolate; mkdocs build --strict verde.

## Tasks Eseguiti

| Task | Nome | Commit | File chiave |
|---|---|---|---|
| 1 | Implementare tco_oepv.py + test + output generati | 53869d3 | tco_oepv.py, params.toml, test_tco_oepv.py, test_vendor_parity.py, tco_table.csv, sensitivity_table.csv, summary.md |
| 2 | Popolare docs economic-analysis IT+EN | 6284d6c | 8 pagine docs/*.md (index, tco, oepv, value-drivers) IT+EN |

## Artefatti Generati

| Artefatto | Percorso | Contenuto |
|---|---|---|
| Script economico | docs/economic-analysis/tco_oepv.py | TCO 6 componenti + OEPV 2 scenari + sensitivity; riusa _oepv_vendor |
| TCO CSV | docs/economic-analysis/tco_table.csv | 6 componenti + totale annuo/3yr: 189.570 EUR |
| Sensitivity CSV | docs/economic-analysis/sensitivity_table.csv | 41 righe ribasso 0-20% step 0.5%, pe, total_score |
| Summary MD | docs/economic-analysis/summary.md | Tabelle Markdown + nota soglia anomalia + citazione art. 54 |
| Docs IT | docs/docs/economic-analysis/{index,tco,oepv,value-drivers}.md | Pagine complete con numeri da script |
| Docs EN | docs/docs/en/economic-analysis/{index,tco,oepv,value-drivers}.md | Mirror EN tradotto |

## Numeri Chiave (da params.toml → tco_oepv.py)

- **TCO 3yr totale:** 189.570 EUR (annuale: 63.190 EUR)
- **Componente dominante:** FTE parziale 135.000 EUR (71% del totale)
- **OEPV ottimistico (PT=68):** 55.2198 su 100 (ribasso 12.5%)
- **OEPV base (PT=55):** 46.1198 su 100 (ribasso 12.5%)
- **Soglia anomalia:** 20.0% configurabile — ribasso 12.5% lontano 7.5 pp dalla soglia
- **Sensitivity:** 41 righe, range Pe da 0 (ribasso 0%) a 28.51 (ribasso 20%)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fix compatibilita Python 3.14 con importlib.util.spec_from_file_location**

- **Trovato durante:** Task 1 (fase GREEN — test falliti dopo implementazione)
- **Problema:** Python 3.14 ha una regressione: `@dataclass(frozen=True)` con `from __future__ import annotations` richiede che il modulo sia registrato in `sys.modules` PRIMA di `exec_module()`. Il caricamento dinamico via `spec_from_file_location` senza registrazione preventiva provocava `AttributeError: 'NoneType' object has no attribute '__dict__'` in `dataclasses.py:814`.
- **Fix:** Aggiunto `sys.modules[name] = mod` prima di `spec.loader.exec_module(mod)` in `_load_module_local()` (test_tco_oepv.py) e `_load_module()` (test_vendor_parity.py).
- **File modificati:** `docs/economic-analysis/tests/test_tco_oepv.py`, `docs/economic-analysis/tests/test_vendor_parity.py`
- **Commit:** 53869d3 (incluso nel commit principale Task 1)

**2. [Rule 2 - Missing functionality] Aggiunta componenti integration e training a params.toml**

- **Trovato durante:** Task 1 (analisi piano — 6 componenti richieste, solo 4 in params.toml stub)
- **Problema:** Il piano richiede esplicitamente 6 componenti TCO (ECO-03/ECO-06): GPU, energia, FTE, change management, IT/OT integration e training. Il `params.toml` stub aveva solo 4 componenti.
- **Fix:** Aggiunti `integration_eur=9000`, `integration_years=3`, `training_eur=6000`, `training_years=3`, `pt_base=55.0`, `pt_optimistic=68.0` a `params.toml`.
- **File modificati:** `docs/economic-analysis/params.toml`
- **Commit:** 53869d3

## Requisiti Chiusi

| Requisito | Soddisfatto | Evidence |
|---|:---:|---|
| ECO-01 | SI | OEPV 2 scenari PT (68/55) in summary.md e oepv.md |
| ECO-03 | SI | TCO 6 componenti in tco_table.csv e tco.md |
| ECO-04 | SI | 5 value driver SIMULATED TARGET con baseline + letteratura in value-drivers.md |
| ECO-06 | SI | 6 componenti TCO: GPU, energia, FTE, change mgmt, IT/OT, training |
| ECO-07 | SI | Risk register 6 voci in index.md IT+EN |
| ECO-08 | SI | Script deterministico, diff identico tra due run, test_determinism verde |
| DOC-10 | SI | 8 pagine docs/economic-analysis IT+EN complete |
| DEL-06 | SI | Economic Evaluation deliverable: TCO + OEPV + value driver + risk register |

## Threat Mitigation

| Threat | Mitigazione | Verifica |
|---|---|---|
| T-12-01-01 Tampering (numeri divergenti) | Tabelle dalle CSV generate, commento AUTOGENERATED, test determinismo | test_determinism verde; diff CSV identico |
| T-12-01-02 Repudiation (value driver come promesse) | Stringa "SIMULATED TARGET" in ogni value driver; verifica automatica nel piano | python3 -c assert 'SIMULATED TARGET' in vd — OK |
| T-12-01-03 Information Disclosure (soglia come regola legale) | Wording "WARNING configurabile, NON esclusione legale" + citazione art. 54 D.Lgs. 36/2023 | grep 'D.Lgs. 36/2023' in oepv.md — OK |

## Known Stubs

Nessuno — tutti i numeri provengono dallo script, nessun placeholder nelle pagine docs.

## Threat Flags

Nessun nuovo surface non previsto nel threat_model del piano.

## Self-Check: PASSED

- [x] `docs/economic-analysis/tco_oepv.py` esiste e gira
- [x] `docs/economic-analysis/tco_table.csv` esiste (commit 53869d3)
- [x] `docs/economic-analysis/sensitivity_table.csv` esiste (commit 53869d3)
- [x] `docs/economic-analysis/summary.md` esiste (commit 53869d3)
- [x] `docs/docs/economic-analysis/value-drivers.md` contiene "SIMULATED TARGET"
- [x] `docs/docs/economic-analysis/oepv.md` contiene "D.Lgs. 36/2023" e "configurabile"
- [x] `docs/docs/en/economic-analysis/value-drivers.md` contiene "SIMULATED TARGET"
- [x] mkdocs build --strict verde (2.76s, zero warning)
- [x] 9 test verdi (4 in test_tco_oepv.py + 5 in test_vendor_parity.py)
- [x] Commit 53869d3 trovato in git log
- [x] Commit 6284d6c trovato in git log
