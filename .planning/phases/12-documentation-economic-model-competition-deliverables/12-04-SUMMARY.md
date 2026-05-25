---
phase: 12-documentation-economic-model-competition-deliverables
plan: "04"
subsystem: docs
tags:
  - ui-mock
  - transformation
  - glossary
  - mermaid
  - sc-5
  - sc-4
  - doc-17
  - doc-18
  - doc-08
  - del-04
dependency_graph:
  requires:
    - "12-00"
  provides:
    - DOC-08
    - DOC-17
    - DOC-18
    - DEL-04
  affects:
    - docs/docs/ui-mock.md
    - docs/docs/en/ui-mock.md
    - docs/docs/transformation.md
    - docs/docs/en/transformation.md
    - docs/docs/glossary.md
    - docs/docs/en/glossary.md
tech_stack:
  added: []
  patterns:
    - Mermaid flowchart and sequenceDiagram for user journey documentation
    - Neutral wording for competition-origin content (SC-4 compliance)
    - Bilingual IT+EN glossary extension pattern
key_files:
  created:
    - docs/docs/transformation.md
    - docs/docs/en/transformation.md
  modified:
    - docs/docs/ui-mock.md
    - docs/docs/en/ui-mock.md
    - docs/docs/glossary.md
    - docs/docs/en/glossary.md
  deleted:
    - docs/docs/assets/screenshots/it/login.png
    - docs/docs/assets/screenshots/it/operator-approval.png
    - docs/docs/assets/screenshots/it/manager-dashboard.png
    - docs/docs/assets/screenshots/en/login.png
    - docs/docs/assets/screenshots/en/operator-approval.png
    - docs/docs/assets/screenshots/en/manager-dashboard.png
decisions:
  - "SC-4: transformation.md uses 'traccia originale del concorso / original competition track' throughout — never the brand name"
  - "SC-5: 6 placeholder PNGs removed via git rm; zero binary images remain under docs/docs/"
  - "DOC-18 gap: OEPV, STRIDE, TCO, RCA, base_asta/base_bid, ribasso_anomalo/abnormal_low_bid added to both IT+EN glossaries as new 'Economico / Gara' section"
  - "Technician persona (RCA/Maintenance view) added to ui-mock — was present in the app (TechnicianComponent exists) but missing from Phase 10-11 mock UI docs"
metrics:
  duration: "26min"
  completed_date: "2026-05-25"
  tasks: 2
  files: 10
---

# Phase 12 Plan 04: Mock UI Mermaid + Transformation + Glossary Summary

## One-liner

Rewrote ui-mock IT+EN with per-persona Mermaid flow diagrams, git-removed 6 placeholder
PNGs (SC-5 compliance), authored transformation.md IT+EN with neutral competition-track
wording (SC-4), and extended the bilingual glossary with 6 OEPV/STRIDE/supply chain
terms from Phases 8-11 (DOC-18).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite ui-mock IT+EN + git rm 6 PNGs | 840dc0c | docs/ui-mock.md, docs/en/ui-mock.md, 6 deleted PNGs |
| 2 | transformation.md IT+EN + glossary extension | 5f1c0dd | transformation.md ×2, glossary.md ×2 |

## What Was Built

### Task 1: ui-mock Rewrite + PNG Removal (DOC-08, DEL-04, SC-5)

All six `![img](assets/screenshots/*.png)` references replaced with Mermaid diagrams:

- **Login flow** (flowchart): credential validation → dev-mode persona chips → role dashboard
- **Operator HITL** (flowchart + sequenceDiagram): approval queue → EvidencePanel → motivaton gate → approve/reject → SSE resolved
- **Technician RCA** (flowchart, NEW): AlertFeed → RCA view → HITL approval → work order
- **Manager/CIO KPI** (flowchart): SSE connection → KpiGrid → threshold breach → governor alert → drill-down

Six placeholder PNGs from Phase 10 removed via `git rm`:
- `docs/docs/assets/screenshots/{it,en}/{login,operator-approval,manager-dashboard}.png`

`.gitkeep` files retained to preserve directory structure (not required by SC-5 which only
prohibits binary images, but harmless).

### Task 2: transformation.md (DOC-17) + Glossary (DOC-18)

**transformation.md IT+EN** (both previously stubs — only 1 line of placeholder text):
Full content covering: project origin, 5 "what changed and why" sections (self-hosted,
HITL, 4 clusters, domain data, OEPV model), key elements retained, transformation
choices, excluded elements, requirements traceability. Neutral wording throughout:
"traccia originale del concorso / original competition track". Zero brand references.

**Glossary extension** — new "Economico / Gara / Economic / Procurement" section (6 terms):

| IT term | EN term | Reason added |
|---------|---------|--------------|
| `oepv` | `oepv` | Core Phase 9-12 economic model concept; missing from glossary |
| `base_asta` | `base_bid` | Referenced in OEPV model; not glossarised |
| `ribasso_anomalo` | `abnormal_low_bid` | Phase 12 economic analysis; regulatory concept |
| `tco` | `tco` | Phase 11-12 cloud-vs-self-hosted comparison |
| `stride` | `stride` | Phase 11 threat model; security section references it |
| `rca` | `rca` | RCASpecialist agent; Technician flow; maintenance cluster core concept |

## Verification Results

```
IT ui-mock: no screenshot refs     PASS
EN ui-mock: no screenshot refs     PASS
IT ui-mock: has mermaid            PASS
EN ui-mock: has mermaid            PASS
Binary images under docs/: 0       PASS
transformation IT non-empty        PASS
transformation EN non-empty        PASS
brand 'accent' in IT transform     ABSENT (PASS)
brand 'accent' in EN transform     ABSENT (PASS)
brand 'accent' in glossary         ABSENT (PASS)
oepv/stride/tco in glossary        PRESENT (PASS)
mkdocs build --strict              EXIT 0 (PASS)
```

## Deviations from Plan

### Auto-added functionality

**1. [Rule 2 - Missing Content] Technician persona added to ui-mock**
- **Found during:** Task 1 implementation
- **Issue:** The plan specified flowcharts for "operator, technician, manager, CIO" personas but the original ui-mock.md had no technician section. TechnicianComponent exists in the codebase (Phase 10, route `/technician`, roles `technician`/`maintenance-engineer`).
- **Fix:** Added Technician RCA/Maintenance flowchart as a new section in both IT and EN ui-mock.md.
- **Files modified:** docs/docs/ui-mock.md, docs/docs/en/ui-mock.md
- **Commit:** 840dc0c

## Known Stubs

None — transformation.md is fully populated; ui-mock has complete Mermaid diagrams for all 4 personas; glossary terms are definitions, not placeholders.

## Threat Flags

No new security-relevant surface introduced. This plan removes binary images and adds documentation text only.

## Self-Check: PASSED

Files exist:
- docs/docs/ui-mock.md: FOUND
- docs/docs/en/ui-mock.md: FOUND
- docs/docs/transformation.md: FOUND
- docs/docs/en/transformation.md: FOUND
- docs/docs/glossary.md: FOUND (extended)
- docs/docs/en/glossary.md: FOUND (extended)

Deleted files confirmed absent:
- docs/docs/assets/screenshots/it/login.png: DELETED (git rm confirmed)
- docs/docs/assets/screenshots/en/login.png: DELETED (git rm confirmed)
- (all 6 PNGs): DELETED

Commits exist:
- 840dc0c: feat(12-04): rewrite ui-mock IT+EN with Mermaid diagrams; git rm 6 placeholder PNGs (SC-5)
- 5f1c0dd: docs(12-04): transformation.md IT+EN (DOC-17, no brand) + glossary Phase 8-11 terms (DOC-18)
