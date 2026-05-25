---
tags:
  - adr
  - architecture
  - governance
---

# ADR-004 — Approvazione HITL a 4 livelli

- **Status:** Accepted
- **Fase:** Phase 4 (runtime) / Phase 10 (UI)
- **Data:** 2026

## Context

Le azioni agentiche con effetto operativo non possono essere applicate in modo
autonomo: serve un controllo umano proporzionato al rischio e attribuibile.
Requisiti:

- separazione dei poteri per ruolo (RBAC);
- ogni decisione umana giustificata e tracciabile (audit trail);
- accesso in sola lettura per l'audit, senza potere di approvazione;
- nessuna azione operativa applicata senza approvazione esplicita.

## Decision

Adottiamo una **catena di approvazione human-in-the-loop a 4 livelli**, mappata
sui ruoli e applicata tramite l'`interrupt()` di LangGraph (cfr. ADR-001):

- **operator** — propone/esegue azioni di routine entro il proprio perimetro;
- **technician** — approva interventi tecnici e manutentivi;
- **shift supervisor** — approva azioni di pianificazione e cross-team;
- **auditor** — accesso in sola lettura all'audit trail, nessuna approvazione.

Il frontend impone una motivazione minima (`MOTIVATION_MIN_LENGTH = 10`
caratteri) per ogni approvazione/rifiuto; ogni decisione genera un `AuditRecord`
immutabile con `decision_actor` (sub del JWT) e `query_hash`.

Riferimento codice:

- `packages/sft-agents/src/sft_agents/runtime/supervisor.py` — `safe_invoke`.
- `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts` —
  `MOTIVATION_MIN_LENGTH`.
- [HITL Cycle](../architecture/hitl-cycle.md).

## Consequences

**Positive**

- separazione dei poteri e attribuibilità delle decisioni (RBAC + JWT);
- audit trail immutabile e motivato per ogni azione;
- nessuna azione operativa autonoma non approvata.

**Negative / trade-off**

- latenza aggiuntiva nel ciclo decisionale (attesa dell'approvazione umana);
- necessità di mantenere il mapping ruoli ↔ tier coerente tra runtime e UI.

Decisione implementata nel runtime (Phase 4) e nella UI di approvazione
(Phase 10).
