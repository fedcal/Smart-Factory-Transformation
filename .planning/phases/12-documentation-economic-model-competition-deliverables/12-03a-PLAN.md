---
phase: 12-documentation-economic-model-competition-deliverables
plan: 03a
type: execute
wave: 4
depends_on: ["12-00"]
files_modified:
  - docs/docs/security/index.md
  - docs/docs/security/stride-threat-model.md
  - docs/docs/security/owasp-llm.md
  - docs/docs/en/security/index.md
  - docs/docs/en/security/stride-threat-model.md
  - docs/docs/en/security/owasp-llm.md
autonomous: true
gap_closure: false
requirements: [DOC-11, DOC-15]
must_haves:
  truths:
    - "Security & Governance section surfaces the Phase 11 STRIDE threat model and OWASP LLM Top-10 mapping inside the published MkDocs site (DOC-11)"
    - "An AI Explainability subsection documents HITL approval chain, audit trail and decision traceability as implemented"
    - "Content traces to the existing docs/security/ source files (single source of truth, no divergence)"
    - "IT pages have EN mirrors; nav already includes them from Wave 0; build stays strict-green; any diagram is Mermaid (SC-5)"
  artifacts:
    - path: "docs/docs/security/stride-threat-model.md"
      provides: "Published STRIDE matrix (DOC-11) sourced from docs/security/STRIDE-threat-model.md"
      contains: "STRIDE"
    - path: "docs/docs/security/owasp-llm.md"
      provides: "Published OWASP LLM Top-10 mapping"
      contains: "LLM01"
    - path: "docs/docs/security/index.md"
      provides: "Security & Governance overview + AI explainability"
      contains: "explainab"
  key_links:
    - from: "docs/docs/security/stride-threat-model.md"
      to: "docs/security/STRIDE-threat-model.md"
      via: "pymdownx.snippets include or faithful copy of the Phase 11 source"
      pattern: "STRIDE"
---

<objective>
Pubblicare la sezione Security & Governance (DOC-11) nel sito MkDocs: popolare `docs/docs/security/index.md` (panoramica + AI Explainability), `stride-threat-model.md` (matrice STRIDE da Phase 11) e `owasp-llm.md` (mapping OWASP LLM Top-10 da Phase 11). La fonte autoritativa è in `docs/security/{STRIDE-threat-model.md, owasp-llm-top10.md}` (Phase 11, fuori da docs/docs/): includere via `pymdownx.snippets` o copia fedele — single source of truth, nessuna divergenza. Mirror EN.

Purpose: realizza DOC-11 (threat model, mitigazioni, AI explainability) come sezione navigabile del sito.
Output: 3 pagine security IT + 3 EN popolate.

Execution note: SEQUENZIALE su main tree. Wave 4; dipende SOLO da 12-00. File disgiunti da 12-03b (security/ vs adr/ + root community files). NON tocca mkdocs.yml (le pagine security sono già nel nav da Wave 0).

Nota: `docs/security/` (Phase 11) contiene STRIDE 6×3 code-mapped + OWASP LLM Top-10 + rate-limit-scaling. Riusare quel contenuto, non riscriverlo.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/12-documentation-economic-model-competition-deliverables/12-CONTEXT.md
@.planning/phases/12-documentation-economic-model-competition-deliverables/12-RESEARCH.md
@.planning/phases/12-documentation-economic-model-competition-deliverables/12-00-SUMMARY.md
@docs/security/STRIDE-threat-model.md
@docs/security/owasp-llm-top10.md

<interfaces>
<!-- pymdownx.snippets è già abilitato in mkdocs.yml (markdown_extensions). Pattern include: -->
<!-- --8<-- "../security/STRIDE-threat-model.md"  (path relativo a docs_dir o snippet base path) -->
<!-- Se il path relativo è fragile fuori da docs_dir, preferire copia fedele del contenuto con header che cita la fonte Phase 11. -->
<!-- AI Explainability (DOC-11): HITL 4-tier approval chain (Phase 4), audit trail action_type (Phase 9/11 migration), decision traceability, recursion_limit=25, MOTIVATION_MIN. -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Pubblicare STRIDE + OWASP LLM nel sito (da fonte Phase 11)</name>
  <files>docs/docs/security/stride-threat-model.md, docs/docs/security/owasp-llm.md, docs/docs/en/security/stride-threat-model.md, docs/docs/en/security/owasp-llm.md</files>
  <action>Popolare `docs/docs/security/stride-threat-model.md` riportando la matrice STRIDE 6×3 code-mapped da `docs/security/STRIDE-threat-model.md` (Phase 11) — preferire `pymdownx.snippets` include (`--8<--`) se il path risolve sotto strict build; altrimenti copia fedele con header che cita la fonte e la data (single source of truth, no divergenza T-12-03a-01). Popolare `docs/docs/security/owasp-llm.md` da `docs/security/owasp-llm-top10.md` (LLM01..LLM10 → mitigazione code-mapped). Mirror EN: tradurre il testo introduttivo ma mantenere coerenza con la fonte (le tabelle tecniche possono restare con identificatori invariati). Nessun `![img]()`; eventuali diagrammi solo Mermaid. Verificare che il build strict non si rompa (se si usa snippets, validare il path).</action>
  <verify>
    <automated>cd docs && python3 -c "s=open('docs/security/stride-threat-model.md').read(); assert 'STRIDE' in s.upper() or '8<' in s; o=open('docs/security/owasp-llm.md').read(); assert 'LLM01' in o or '8<' in o; assert '![' not in s and '![' not in o; print('sec-pages-ok')" && python3 -m mkdocs build --strict</automated>
  </verify>
  <done>STRIDE + OWASP LLM pubblicati nel sito (include o copia fedele dalla fonte Phase 11); mirror EN; nessuna immagine binaria; build strict verde.</done>
</task>

<task type="auto">
  <name>Task 2: Security overview + AI Explainability (DOC-11)</name>
  <files>docs/docs/security/index.md, docs/docs/en/security/index.md</files>
  <action>Popolare `docs/docs/security/index.md` con: panoramica Security & Governance (link a STRIDE e OWASP), una sottosezione "AI Explainability & Governance" che documenta — come implementato (SC-3) — la HITL 4-tier approval chain (Phase 4), l'audit trail (action_type, Phase 9/11 migration), la decision traceability, recursion_limit=25, MOTIVATION_MIN per le decisioni HITL. Opzionale Mermaid flowchart del flusso HITL approval→audit. Citare le fasi/SUMMARY come evidence. Mirror EN. Nessun `![img]()`.</action>
  <verify>
    <automated>cd docs && python3 -c "s=open('docs/security/index.md').read().lower(); assert 'explainab' in s or 'governance' in s; assert 'hitl' in s or 'audit' in s; assert '![' not in open('docs/security/index.md').read(); en=open('docs/en/security/index.md').read(); assert en.strip(); print('sec-index-ok')" && python3 -m mkdocs build --strict</automated>
  </verify>
  <done>security/index.md (+EN) con panoramica + AI Explainability tracciata al codice (HITL/audit/recursion_limit); nessuna immagine binaria; build strict verde.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| docs/security source → published site | Il contenuto pubblicato deve restare allineato alla fonte Phase 11 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12-03a-01 | Tampering | divergenza tra docs/docs/security e docs/security fonte | mitigate | Preferire snippets include; se copia, header con fonte+data; SC-3 review in 12-05. |
| T-12-03a-02 | Repudiation | AI explainability descrive feature non implementata | mitigate | Tracciabilità a Phase 4/9/11 SUMMARY; SC-3 verificato in 12-05. |
</threat_model>

<verification>
- STRIDE + OWASP pubblicati (include o copia fedele); security/index con AI explainability; mirror EN.
- Nessuna immagine binaria; `mkdocs build --strict` verde.
</verification>

<success_criteria>
DOC-11 chiuso: Security & Governance navigabile nel sito (STRIDE, OWASP LLM Top-10, AI explainability) allineato alla fonte Phase 11 (SC-3).
</success_criteria>

<output>
Create `.planning/phases/12-documentation-economic-model-competition-deliverables/12-03a-SUMMARY.md` when done.
</output>
