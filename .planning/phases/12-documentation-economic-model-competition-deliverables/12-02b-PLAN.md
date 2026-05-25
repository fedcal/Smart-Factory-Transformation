---
phase: 12-documentation-economic-model-competition-deliverables
plan: 02b
type: execute
wave: 3
depends_on: ["12-00"]
files_modified:
  - docs/docs/use-cases/index.md
  - docs/docs/adoption-roadmap/index.md
  - docs/docs/en/use-cases/index.md
  - docs/docs/en/adoption-roadmap/index.md
autonomous: true
gap_closure: false
requirements: [DOC-07, DOC-09, DOC-15, DEL-03, DEL-05]
must_haves:
  truths:
    - "Use Cases are prioritized across the 0-3m / 3-9m / 9-18m horizons, each traced to a shipped agent/capability (DOC-07/DEL-03, SC-3)"
    - "Adoption Roadmap documents phases, KPIs, risks and mitigations (DOC-09/DEL-05)"
    - "Any diagram is Mermaid text; no binary images (SC-5)"
    - "IT pages have EN mirrors; nav already includes both pages from Wave 0; build stays strict-green"
  artifacts:
    - path: "docs/docs/use-cases/index.md"
      provides: "Prioritized use cases (DEL-03) with 3 time horizons"
      contains: "9-18"
    - path: "docs/docs/adoption-roadmap/index.md"
      provides: "Adoption roadmap (DEL-05) with KPIs/risks/mitigations"
      contains: "KPI"
  key_links:
    - from: "docs/docs/use-cases/index.md"
      to: ".planning/phases/06-agents-operations-production"
      via: "each use case maps to a shipped agent capability"
      pattern: "0-3"
---

<objective>
Completare Casi d'Uso (DOC-07/DEL-03) e Roadmap di Adozione (DOC-09/DEL-05): popolare `use-cases/index.md` con i casi d'uso prioritizzati su 3 orizzonti (0-3 mesi / 3-9 mesi / 9-18 mesi), ognuno tracciato a una capability/agente spedito; popolare `adoption-roadmap/index.md` con fasi, KPI, rischi e mitigazioni. Diagrammi come Mermaid (SC-5). Mirror EN.

Purpose: realizza DEL-03 (Prioritized Use Cases) e DEL-05 (Adoption Roadmap).
Output: 2 pagine IT + 2 EN popolate.

Execution note: SEQUENZIALE su main tree. Wave 3; dipende SOLO da 12-00. File disgiunti da 12-02a — questo piano NON tocca mkdocs.yml (use-cases e adoption-roadmap sono già nel nav da Wave 0); tocca solo use-cases/ e adoption-roadmap/.

SC-3: ogni caso d'uso traccia a una feature implementata (Codebase State Audit del RESEARCH). Niente contenuto aspirazionale.
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

<interfaces>
<!-- Prioritizzazione 0-3m/3-9m/9-18m (RESEARCH Recommended Structure). Mappare a feature spedite: -->
<!-- 0-3m: OperatorAssistant + RAG SOP retrieval (Phase 5/6); HITL approval queue (Phase 4/10). -->
<!-- 3-9m: PredictiveMaintenance/RCASpecialist (Phase 7); AnomalyDetector (Phase 6); ShiftHandover/TrainingCoach (Phase 8). -->
<!-- 9-18m: SCM cost-analyzer/OEPV (Phase 9); KnowledgeCurator/DocumentationSynthesizer; estensione multi-impianto. -->
<!-- Roadmap: fasi pilota→scale→consolidamento, KPI (downtime/scrap/MTTR/adoption), rischi+mitigazioni come SIMULATED TARGET. -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Casi d'Uso prioritizzati 0-3m/3-9m/9-18m (DOC-07/DEL-03)</name>
  <files>docs/docs/use-cases/index.md, docs/docs/en/use-cases/index.md</files>
  <action>Popolare `use-cases/index.md` con i casi d'uso organizzati nei 3 orizzonti temporali (0-3 mesi, 3-9 mesi, 9-18 mesi) come tabella o sezioni: per ogni caso d'uso indicare persona, problema, capability/agente implementato che lo abilita (tracciabilità SC-3 — citare la fase/SUMMARY), valore atteso come SIMULATED TARGET. Esempio mappatura: 0-3m → OperatorAssistant + RAG SOP + HITL approval (Phase 4/5/6/10); 3-9m → PredictiveMaintenance/RCASpecialist/AnomalyDetector + ShiftHandover/TrainingCoach (Phase 6/7/8); 9-18m → SCM/OEPV + KnowledgeCurator/DocumentationSynthesizer + estensione (Phase 8/9). Opzionale: un Mermaid timeline/flowchart degli orizzonti. Nessun `![img]()`. Mirror EN.</action>
  <verify>
    <automated>cd docs && python3 -c "s=open('docs/use-cases/index.md').read(); assert '0-3' in s and '3-9' in s and '9-18' in s, 'missing horizons'; assert '![' not in s, 'binary img ref'; en=open('docs/en/use-cases/index.md').read(); assert en.strip(); print('use-cases-ok')" && python3 -m mkdocs build --strict</automated>
  </verify>
  <done>use-cases/index.md (+EN) con i 3 orizzonti, ogni caso tracciato a feature spedita, valori come SIMULATED TARGET; nessuna immagine binaria; build strict verde.</done>
</task>

<task type="auto">
  <name>Task 2: Roadmap di Adozione con fasi/KPI/rischi/mitigazioni (DOC-09/DEL-05)</name>
  <files>docs/docs/adoption-roadmap/index.md, docs/docs/en/adoption-roadmap/index.md</files>
  <action>Popolare `adoption-roadmap/index.md` con: fasi di adozione (es. Pilota → Scale-up → Consolidamento), allineate agli orizzonti dei casi d'uso; per ogni fase i KPI (downtime/scrap/MTTR/adoption-rate/knowledge-reuse come SIMULATED TARGET, coerenti con i value driver di 12-01); una tabella rischi con probability/impact e mitigazione per ciascun rischio di adozione (organizzativo/tecnico/change-management). Opzionale Mermaid timeline o flowchart delle fasi. Nessun `![img]()`. Mirror EN.</action>
  <verify>
    <automated>cd docs && python3 -c "s=open('docs/adoption-roadmap/index.md').read(); assert 'KPI' in s and ('rischi' in s.lower() or 'risk' in s.lower()) and ('mitigaz' in s.lower() or 'mitigat' in s.lower()), 'missing kpi/risk/mitigation'; assert '![' not in s; en=open('docs/en/adoption-roadmap/index.md').read(); assert en.strip(); print('roadmap-ok')" && python3 -m mkdocs build --strict</automated>
  </verify>
  <done>adoption-roadmap/index.md (+EN) con fasi, KPI (SIMULATED TARGET), tabella rischi probability/impact + mitigazioni; nessuna immagine binaria; build strict verde.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| docs claim → shipped code | Casi d'uso/KPI devono tracciare a feature reali e ai value driver di 12-01 (SC-3) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12-02b-01 | Repudiation | caso d'uso/KPI aspirazionale | mitigate | Tracciabilità a SUMMARY di fase + value driver di 12-01; SIMULATED TARGET marcato; SC-3 verificato in 12-05. |
| T-12-02b-02 | Tampering | immagine binaria come diagramma | mitigate | Solo Mermaid; verify asserisce assenza di `![`. |
</threat_model>

<verification>
- use-cases con 3 orizzonti tracciati; adoption-roadmap con fasi/KPI/rischi/mitigazioni; mirror EN.
- Nessun `![img]()`.
- `mkdocs build --strict` verde.
</verification>

<success_criteria>
DOC-07/DEL-03 + DOC-09/DEL-05 chiusi: casi d'uso prioritizzati su 3 orizzonti e roadmap di adozione con KPI/rischi/mitigazioni, tracciati al codice spedito (SC-3).
</success_criteria>

<output>
Create `.planning/phases/12-documentation-economic-model-competition-deliverables/12-02b-SUMMARY.md` when done.
</output>
