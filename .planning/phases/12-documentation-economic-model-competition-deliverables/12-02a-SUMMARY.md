---
phase: 12-documentation-economic-model-competition-deliverables
plan: 02a
subsystem: docs
tags: [architecture, c4, mermaid, functional-analysis, ops, mnt, trn, bilingual]
dependency_graph:
  requires: [12-00]
  provides: [DEL-01, DEL-02, DOC-04, DOC-06]
  affects: [docs/docs/architecture/, docs/docs/functional-analysis/]
tech_stack:
  added: []
  patterns:
    - C4 Context/Container/Component Mermaid via pymdownx.superfences
    - sequenceDiagram + flowchart Mermaid per workflow end-to-end
    - mkdocs-static-i18n bilingual IT+EN
key_files:
  created:
    - docs/docs/architecture/c4-context.md
    - docs/docs/architecture/c4-container.md
    - docs/docs/architecture/c4-component.md
    - docs/docs/en/architecture/c4-context.md
    - docs/docs/en/architecture/c4-container.md
    - docs/docs/en/architecture/c4-component.md
  modified:
    - docs/docs/architecture/overview.md
    - docs/docs/functional-analysis/index.md
    - docs/docs/functional-analysis/operations-workflow.md
    - docs/docs/functional-analysis/maintenance-workflow.md
    - docs/docs/functional-analysis/training-workflow.md
    - docs/docs/en/functional-analysis/index.md
    - docs/docs/en/functional-analysis/operations-workflow.md
    - docs/docs/en/functional-analysis/maintenance-workflow.md
    - docs/docs/en/functional-analysis/training-workflow.md
    - docs/mkdocs.yml
decisions:
  - "C4 diagrams use Mermaid C4Context/C4Container/C4Component keywords natively supported by pymdownx.superfences (no plugin install needed)"
  - "DowntimeAnalyzer documented as tier AUTO (read-only) — no HITL, consistent with Phase 7 D-DA pattern"
  - "KnowledgeCurator documented as tier AUTO and HTTP 200 (not 202) — consistent with Phase 08-08 decision"
  - "SCM cluster deferred to Economic Analysis section — its workflow is cost/value output, not operational"
  - "nav_translations for C4 Context/Container/Component added as identity translations (same IT=EN label)"
metrics:
  duration: 35min
  completed_date: "2026-05-25"
  tasks: 2
  files: 16
---

# Phase 12 Plan 02a: C4 Architecture Diagrams + OPS/MNT/TRN Functional Workflows Summary

Target Architecture C4 (Context/Container/Component) as Mermaid text plus end-to-end OPS/MNT/TRN workflows as Mermaid sequence/flowchart diagrams, bilingual IT+EN, traceable to shipped agents and gateway code.

## What Was Built

### Task 1: C4 Architecture Diagrams + Overview + Nav

Three new pages under `docs/architecture/`:

- **c4-context.md** — `C4Context` Mermaid: 3 persona (Operatore, Tecnico, Manager), sistema SFT, sistemi esterni (OPC-UA Simulator, ERP/MES fuori scope, Ollama on-premise). Relazione OPC-UA→NATS marcata esplicitamente come unidirezionale.
- **c4-container.md** — `C4Container` Mermaid: Factory UI (Angular 18+ SSR), API Gateway (FastAPI), Agent Runtime (LangGraph), OT Bridge, Knowledge Ingest, PostgreSQL+TimescaleDB, Qdrant, NATS JetStream, Ollama. Solo container implementati (Fasi 1-10).
- **c4-component.md** — `C4Component` Mermaid: struttura interna Agent Runtime — Supervisor, HITL interrupt-resume, 4 cluster subgraph (OPS/MNT/TRN/SCM), Audit Writer, RAG Pipeline. Relazioni di dispatch e audit incluse.

`overview.md` arricchito con data-flow Mermaid end-to-end (event → NATS → Gateway → Supervisor → Cluster → RAG → LLM → HITL → Audit → UI) e tabella livelli C4.

`mkdocs.yml` aggiornato con 3 nuove voci nav sotto Architettura + nav_translations corrispondenti (identità IT=EN).

Tutti i mirror EN creati in `docs/en/architecture/`.

### Task 2: Workflow end-to-end OPS/MNT/TRN

Quattro pagine `functional-analysis/` popolate:

- **index.md** — Tabella cluster/agenti/fasi, diagramma pattern comune flowchart, principi di tracciabilità (SC-3).
- **operations-workflow.md** — `sequenceDiagram` completo anomalia-sensore→alert→assistenza-operatore→approvazione, più `flowchart` controllo qualità (pass/rework/fail → HITL). Agenti: AnomalyDetector, OperatorAssistant, QualityInspector.
- **maintenance-workflow.md** — `sequenceDiagram` vibrazione→alert-predittivo→RCA→coaching-tecnico, più `flowchart` DowntimeAnalyzer autonomo. Agenti: PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer.
- **training-workflow.md** — `sequenceDiagram` ShiftHandover fine-turno con HITL REVIEW, `flowchart` TrainingCoach SUGGEST, `flowchart` KnowledgeCurator AUTO, `flowchart` DocumentationSynthesizer→KC re-index.

Tutti i mirror EN creati in `docs/en/functional-analysis/`.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

```
mkdocs build --strict: PASSED (2.66s)
C4Context keyword in c4-context.md: OK
C4Container keyword in c4-container.md: OK
C4Component keyword in c4-component.md: OK
mermaid in all 3 C4 IT+EN: OK
mermaid in all 3 workflow IT+EN: OK
no binary img ref (![) in workflow files: OK
```

## Known Stubs

None — all pages contain complete Mermaid diagrams traceable to shipped code.

## Threat Flags

None — this plan modifies only documentation files; no new network endpoints, auth paths, or schema changes introduced.

## Self-Check

- [x] `docs/docs/architecture/c4-context.md` — exists, contains `C4Context`
- [x] `docs/docs/architecture/c4-container.md` — exists, contains `C4Container`
- [x] `docs/docs/architecture/c4-component.md` — exists, contains `C4Component`
- [x] All 3 EN mirrors in `docs/en/architecture/` — created
- [x] All 4 `functional-analysis/` IT+EN pages populated with Mermaid
- [x] `mkdocs build --strict` — green
- [x] Commit `de7b6a6` — exists

## Self-Check: PASSED
