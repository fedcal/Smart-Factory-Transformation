---
phase: 12-documentation-economic-model-competition-deliverables
plan: 03a
subsystem: docs
tags: [docs, security, governance, stride, owasp-llm, explainability, mkdocs, i18n]
dependency_graph:
  requires: [12-00]
  provides: [security-section-published, ai-explainability-doc]
  affects:
    - docs/docs/security/
    - docs/docs/en/security/
tech_stack:
  added: []
  patterns:
    - "Single source of truth: faithful copy from docs/security/ (Phase 11) with citation header"
    - "Bilingual IT/EN mirror via mkdocs-static-i18n folder structure"
    - "Mermaid text diagrams only (no binary images, SC-5/DOC-15)"
key_files:
  created: []
  modified:
    - docs/docs/security/stride-threat-model.md
    - docs/docs/security/owasp-llm.md
    - docs/docs/security/index.md
    - docs/docs/en/security/stride-threat-model.md
    - docs/docs/en/security/owasp-llm.md
    - docs/docs/en/security/index.md
decisions:
  - "Copia fedele (non pymdownx.snippets) della fonte Phase 11: il path snippet fuori da docs_dir e' fragile sotto --strict; la copia con header citante fonte+data garantisce build deterministico e zero divergenza (T-12-03a-01)"
  - "Tabelle tecniche EN con identificatori invariati (file:funzione, LLM01..LLM10, S1/S2/S3); tradotta solo la prosa introduttiva"
  - "Mermaid flowchart HITL approval->audit aggiunto a security/index.md (IT+EN) — nessuna immagine binaria"
metrics:
  duration_min: 8
  completed_date: "2026-05-25"
  tasks_completed: 2
  files_created: 0
  files_modified: 6
---

# Phase 12 Plan 03a: Security & Governance — STRIDE + OWASP LLM + AI Explainability Summary

Pubblicata la sezione Security & Governance nel sito MkDocs (DOC-11): matrice STRIDE 6×3 code-mapped e mapping OWASP LLM Top-10 riportati fedelmente dalla fonte autoritativa Phase 11, più una sottosezione AI Explainability che documenta HITL 4-tier approval chain, audit trail (`action_type`), decision traceability (OTEL traceparent), `recursion_limit=25` e `MOTIVATION_MIN`. Mirror EN completo; diagrammi solo Mermaid; `mkdocs build --strict` verde.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Pubblicare STRIDE + OWASP LLM nel sito (da fonte Phase 11) | 6cd8c86 | docs/docs/security/{stride-threat-model,owasp-llm}.md + EN mirror |
| 2 | Security overview + AI Explainability (DOC-11) | 32d5456 | docs/docs/security/index.md + EN mirror |

## Verification

- Task 1 automated: `assert 'STRIDE' in s.upper(); 'LLM01' in o; '![' not in s/o` — PASS (sec-pages-ok)
- Task 2 automated: `'explainab'/'governance' + 'hitl'/'audit' in index; '![' absent; EN non-empty` — PASS (sec-index-ok)
- `mkdocs build --strict` exit 0, nessun WARNING/ERROR di contenuto (presente solo l'avviso cosmetico del team Material for MkDocs su MkDocs 2.0, identico al build Wave 0, non-bloccante) — PASS
- Forbidden-string scan (`fedcal|federicocalo|accenture`) su file security IT+EN — PASS (no-forbidden-strings-confirmed)
- Diagrammi: 2 blocchi Mermaid (index IT + EN), zero `![img]()` — PASS

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Copia fedele al posto di pymdownx.snippets `--8<--`**
- **Found during:** Task 1
- **Issue:** La fonte Phase 11 vive in `docs/security/` (fuori da `docs_dir = docs/docs/`). pymdownx.snippets risolve la base path dalla cwd di mkdocs (`docs/`), non da `docs_dir`; un include `--8<--` esterno a docs_dir è fragile sotto `--strict` e il plan vieta modifiche a `mkdocs.yml`. Inoltre la fonte ha frontmatter YAML che, incluso via snippet, renderizzerebbe come testo.
- **Fix:** Copia fedele del corpo (frontmatter sostituito da un header `!!! info` che cita fonte + data + ID requisito). Mitiga T-12-03a-01 (divergenza) come previsto dal threat model del plan: la disposizione "mitigate" ammetteva esplicitamente "snippets OR copia fedele con header fonte+data".
- **Files modified:** docs/docs/security/stride-threat-model.md, owasp-llm.md (+ EN)
- **Commit:** 6cd8c86

**2. [Rule 2 - Neutral placeholders] Provenienza registro de-personalizzata**
- **Found during:** Task 1
- **Issue:** La fonte Phase 11 citava nomi-file di registro per-fase (es. "10-SECURITY.md T-10-01") — neutri, ma per coerenza editoriale del sito pubblicato si è preferito riferirsi alle fasi ("Phase 10 security register") senza esporre path interni `.planning`.
- **Fix:** Sostituiti i riferimenti "NN-SECURITY.md T-NN-xx" con "Phase NN security register" mantenendo la tracciabilità tecnica (codice mappato invariato).
- **Files modified:** STRIDE pages IT+EN
- **Commit:** 6cd8c86

## Known Stubs

Nessuno. Tutti e 6 i file della sezione security (3 IT + 3 EN) sono ora popolati con contenuto sostanziale tracciato al codice; gli stub Wave 0 sono stati sostituiti.

## Threat Flags

Nessuna nuova superficie di sicurezza introdotta — solo documentazione. Il threat model del plan (T-12-03a-01 divergenza fonte/sito, T-12-03a-02 explainability non implementata) è mitigato: header single-source-of-truth + evidence tracciata a Phase 4/9/10/11. La verifica SC-3 finale è demandata a 12-05 come da plan.

## Self-Check: PASSED

- `6cd8c86` presente in git log
- `32d5456` presente in git log
- 6 file security (IT+EN) esistono e popolati su filesystem
- `mkdocs build --strict` exit 0
- nessuna stringa vietata nei file tracciati
