---
phase: 12-documentation-economic-model-competition-deliverables
plan: "02b"
subsystem: docs
tags: [docs, use-cases, adoption-roadmap, mermaid, i18n, sc-3, del-03, del-05]
dependency_graph:
  requires: [12-00]
  provides: [use-cases-prioritised, adoption-roadmap-phases-kpi-risks]
  affects:
    - docs/docs/use-cases/index.md
    - docs/docs/adoption-roadmap/index.md
    - docs/docs/en/use-cases/index.md
    - docs/docs/en/adoption-roadmap/index.md
tech_stack:
  added: []
  patterns:
    - Mermaid timeline/gantt/quadrantChart/flowchart/mindmap per documentazione
    - SC-3 traceability: ogni claim tracciato a fase/agente spedito
    - SIMULATED TARGET framing per valori KPI
key_files:
  created: []
  modified:
    - docs/docs/use-cases/index.md
    - docs/docs/en/use-cases/index.md
    - docs/docs/adoption-roadmap/index.md
    - docs/docs/en/adoption-roadmap/index.md
decisions:
  - 9 casi d'uso su 3 orizzonti (0-3m/3-9m/9-18m); ogni UC tracciato a fase+agente per SC-3
  - Valori KPI marcati SIMULATED TARGET derivati da dataset Mantis Phase 9
  - 10 rischi nel registro con probability/impact e mitigazione specifica
  - Mermaid timeline/gantt/quadrantChart/flowchart/mindmap: zero immagini binarie (SC-5)
  - Mirror EN completo e contestuale (non solo traduzione letterale)
metrics:
  duration_min: 25
  completed_date: "2026-05-25"
  tasks_completed: 2
  files_created: 0
  files_modified: 4
---

# Phase 12 Plan 02b: Use Cases + Adoption Roadmap Summary

9 casi d'uso prioritizzati su 3 orizzonti (0-3m/3-9m/9-18m) con tracciabilità SC-3 a fasi/agenti spediti + roadmap adozione con 3 fasi, KPI per fase, registro 10 rischi con mitigazioni, diagrammi Mermaid; mirror EN completo; mkdocs build --strict verde.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Casi d'Uso prioritizzati 0-3m/3-9m/9-18m (DOC-07/DEL-03) | 9dd80f1 | docs/docs/use-cases/index.md, docs/docs/en/use-cases/index.md |
| 2 | Roadmap Adozione con fasi/KPI/rischi/mitigazioni (DOC-09/DEL-05) | 488eba2 | docs/docs/adoption-roadmap/index.md, docs/docs/en/adoption-roadmap/index.md |

## Verification

- `'0-3' in use-cases/index.md and '3-9' in ... and '9-18' in ...` — PASS
- `'![' not in use-cases/index.md` — PASS (nessuna immagine binaria)
- `en/use-cases/index.md non vuoto con SIMULATED TARGET` — PASS
- `'KPI' in adoption-roadmap/index.md and 'rischi' and 'mitigaz'` — PASS
- `'![' not in adoption-roadmap/index.md` — PASS (nessuna immagine binaria)
- `en/adoption-roadmap/index.md non vuoto con KPI, risk, mitigation` — PASS
- `mkdocs build --strict` exit 0, 2.73s, zero WARNING/ERROR — PASS

## Deviations from Plan

Nessuna deviazione — piano eseguito esattamente come scritto.

## SC-3 Traceability Matrix

| Caso d'Uso | Claim | Agente/Feature | Fase | Evidence |
|-----------|-------|----------------|------|---------|
| UC-01 Assistente SOP | RAG + OperatorAssistant | OperatorAssistant agent.py | Phase 6 | 06-00-SUMMARY agents-operations-production |
| UC-01 Assistente SOP | BGE-M3 hybrid retrieval Qdrant | QdrantIndexer + RetrievalPipeline | Phase 5 | 05-04-qdrant-bootstrap-SUMMARY |
| UC-02 Coda HITL | interrupt-to-resume LangGraph | HITL core | Phase 4 | 04-HITL-SUMMARY |
| UC-02 Coda HITL | Angular Approval Queue SSE | ApprovalCardComponent | Phase 10 | 10-VERIFICATION |
| UC-03 Manutenzione Predittiva | PredictiveMaintenance | maintenance agent.py | Phase 7 | 07-01-SUMMARY |
| UC-03 AnomalyDetector | anomaly classification | AnomalyDetector | Phase 6 | 06-00-SUMMARY |
| UC-04 RCA | RCASpecialist + Neo4j | rca-specialist agent.py | Phase 7 | 07-01-SUMMARY |
| UC-05 Shift Handover | ShiftHandover + D-SH-02 | ShiftAggregator ANOMALY_ALERT | Phase 8 | 08-02-SUMMARY |
| UC-06 TrainingCoach | personalised paths | TrainingCoach agent.py | Phase 8 | 08-SUMMARY |
| UC-07 InventoryManager | SCM-01 HITL | InventoryManager + DemandForecaster | Phase 9 | 09-02-SUMMARY, 09-05-SUMMARY |
| UC-08 EnergyOptimizer | off_peak_kwh_pct | EnergyOptimizer CR-05 clamping | Phase 9 | 09-03-SUMMARY |
| UC-09 KnowledgeCurator | D-KC-04 autonomous | KnowledgeCurator + DocumentationSynthesizer | Phase 8 | 08-06-SUMMARY, 08-08-SUMMARY |

## Known Stubs

Nessuno — tutti i contenuti sono popolati con dati tracciati.

## Threat Flags

Nessuna nuova superficie di sicurezza — tutti i file sono documentazione statica senza endpoint di rete.

## Self-Check: PASSED

- `9dd80f1` presente in git log — VERIFIED
- `488eba2` presente in git log — VERIFIED
- docs/docs/use-cases/index.md contiene '0-3', '3-9', '9-18', nessun '![' — VERIFIED
- docs/docs/en/use-cases/index.md non vuoto — VERIFIED
- docs/docs/adoption-roadmap/index.md contiene 'KPI', 'rischi', 'mitigaz' — VERIFIED
- docs/docs/en/adoption-roadmap/index.md non vuoto — VERIFIED
- mkdocs build --strict exit 0 — VERIFIED
