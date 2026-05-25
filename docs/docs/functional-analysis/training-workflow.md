# Workflow Training / Knowledge (TRN)

Il cluster Knowledge gestisce il trasferimento di conoscenza operativa, la formazione
on-the-job e la curazione della base documentale. È composto da 4 agenti
implementati nella Fase 8.

> **SC-3 — Tracciabilità:** questo workflow mappa gli step agli agenti in
> `packages/sft-agents/src/sft_agents/` (Fase 8), al router `build_knowledge_subgraph()`
> e alle API in `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py`.
> KnowledgeCurator è il fallback del router (D-KC-04): opera in tier AUTO, senza
> HITL, senza effetti irreversibili.

## Agenti del cluster TRN

| Agente | Slug | HITL Tier | Ruolo |
|--------|------|-----------|-------|
| ShiftHandover | `shift-handover` | REVIEW (2) | Sintesi verbale fine-turno, trasferimento conoscenza |
| TrainingCoach | `training-coach` | SUGGEST (1) | Coaching contestuale operatore / tecnico (RAG su SOP) |
| KnowledgeCurator | `knowledge-curator` | AUTO (0) | Curazione autonoma documenti, aggiornamento indice RAG |
| DocumentationSynthesizer | `documentation-synthesizer` | REVIEW (2) | Sintesi e aggiornamento SOP da esperienze operative |

## Workflow end-to-end: fine turno → verbale di consegna

```mermaid
sequenceDiagram
    autonumber
    participant CS as Caposquadra<br/>(shift-supervisor role)
    participant GW as API Gateway
    participant SUP as Supervisor<br/>(LangGraph)
    participant SH as ShiftHandover
    participant RAG as RAG Pipeline<br/>(BGE-M3 + Qdrant)
    participant LLM as Ollama — Qwen2.5
    participant DB as PostgreSQL
    participant UI as Factory UI
    participant MAN as Manager / Caposquadra entrante

    CS->>GW: POST /trn/shift-handover (fine turno)
    GW->>SUP: invoca cluster trn / target=shift-handover
    SUP->>SH: dispatch
    SH->>DB: legge audit trail turno corrente (anomalie, interventi, approvazioni)
    SH->>RAG: retrieval contesto SOP rilevanti
    RAG-->>SH: chunks SOP + note turno precedente
    SH->>LLM: genera verbale strutturato (eventi critici, azioni pendenti, raccomandazioni)
    SH->>DB: insert audit SHIFT_HANDOVER (tier REVIEW)
    SH-->>GW: verbale bozza + richiesta approvazione

    CS->>GW: approva verbale (POST /approvals/{id}/approve)
    GW->>DB: aggiorna approvazione
    GW->>SUP: resume grafo HITL
    DB-->>GW: conferma
    GW-->>UI: SSE — verbale definitivo disponibile
    UI-->>MAN: verbale fine turno visibile in dashboard
```

## Workflow: coaching operatore durante intervento

```mermaid
flowchart TD
    REQ["Operatore richiede assistenza\non-the-job"]
    GW["API Gateway — POST /trn/training-coach"]
    TC["TrainingCoach\n(tier SUGGEST)"]
    RAG["RAG: retrieval SOP + video-guide\n(BGE-M3 dense + BM25 sparse)"]
    LLM["LLM: genera spiegazione contestuale\nadattata al ruolo utente (JWT RBAC)"]
    HITL{"Tier SUGGEST:\noperatore accetta / ignora?"}
    DB["PostgreSQL: insert audit\nTRAINING_SESSION"]
    UI["Factory UI: risposta step-by-step\nvisibile all'operatore"]

    REQ --> GW --> TC --> RAG --> LLM --> HITL
    HITL -->|"Accettato (o timeout)"| DB --> UI
    HITL -->|"Ignorato"| DB
```

## Workflow: curazione autonoma documenti

```mermaid
flowchart TD
    TRIG["Trigger: nuovo documento caricato\n(POST /knowledge/ingest)"]
    INGEST["Knowledge Ingest Pipeline\n(chunking + BGE-M3 embedding)"]
    QDRANT["Qdrant: upsert vettori\n(dense + sparse BM25)"]
    KC["KnowledgeCurator\n(tier AUTO — autonomo, D-KC-04)"]
    DB1["PostgreSQL: legge documenti recenti\n(metadati + chunks)"]
    LLM["LLM: valuta qualità, duplicati,\ncoerenza con SOP esistenti"]
    DB2["PostgreSQL: insert audit\nKNOWLEDGE_CURATED (insert-only)"]
    NOTE["Nessun HITL:\nautonomo — nessun effetto irreversibile"]

    TRIG --> INGEST --> QDRANT
    INGEST --> KC --> DB1 --> LLM --> DB2 --> NOTE
```

> KnowledgeCurator non ha endpoint `/resume`: è completamente autonomo (D-KC-04).
> Il gateway restituisce HTTP 200 (non 202) perché l'esecuzione è sincrona e
> senza sospensione HITL (Decisione Fase 08-08).

## Workflow: sintesi SOP da esperienze operative

```mermaid
flowchart TD
    REQ["Richiesta sintesi SOP\n(manager o caposquadra)"]
    GW["API Gateway — POST /trn/documentation-synthesizer"]
    DS["DocumentationSynthesizer\n(tier REVIEW)"]
    RAG["RAG: retrieval SOP attuale +\naudit trail operativo"]
    LLM["LLM: genera bozza SOP aggiornata"]
    HITL["HITL REVIEW\n(approvazione manager)"]
    DB["PostgreSQL: insert audit\nSOP_SYNTHESIZED"]
    KC["KnowledgeCurator: indicizza\nnuova SOP su Qdrant"]

    REQ --> GW --> DS --> RAG --> LLM --> HITL
    HITL -->|"Approvata"| DB --> KC
    HITL -->|"Rigettata"| DB
```

## Punti di integrazione

| Punto | Sistema | Note |
|-------|---------|------|
| Audit trail turno | PostgreSQL `audit_log` | Base dati per ShiftHandover (Fase 4) |
| Retrieval SOP | Qdrant + BGE-M3 | SOP, note operative, verbali precedenti (Fase 5) |
| Ingest documenti | Knowledge Ingest Pipeline | Chunking + embedding + upsert Qdrant (Fase 5) |
| Inference LLM | Ollama — Qwen2.5 | On-premise, rete interna |
| RBAC contestuale | JWT — 4 ruoli | La risposta del coach si adatta al ruolo del richiedente (Fase 10) |
