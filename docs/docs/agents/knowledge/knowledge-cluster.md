---
lang: it
cluster: knowledge-training
requirements:
  - TRN-02
  - TRN-03
  - TRN-04
  - TRN-05
tags:
  - agents
  - knowledge
  - training
  - TRN-02
  - TRN-03
  - TRN-04
  - TRN-05
---

# Cluster Knowledge & Training

## Panoramica

Il cluster **Knowledge & Training** aggrega i quattro agenti responsabili della
gestione della conoscenza operativa e della formazione del personale in fabbrica:

| Agente | Responsabilità principale | HITL |
|--------|--------------------------|------|
| **ShiftHandover** | Compilazione del report di cambio turno con firma duale dei caposquadra | Dual-supervisor sign-off (D-SH-03) |
| **TrainingCoach** | Quiz MCQ adattivo per ruolo/persona + firma competenza supervisore | Supervisor sign-off al superamento (D-TC-03) |
| **KnowledgeCurator** | Deduplicazione + flagging staleness documenti (autonomo) | Nessun HITL (D-KC-04) |
| **DocumentationSynthesizer** | Sintesi SOP bilingue IT/EN da eventi storici RCA/downtime + approvazione pre-indicizzazione | Supervisor pre-index (D-DS-03) |

Tutti gli output del cluster portano **`source_uri` + `timestamp`** su ogni
citazione (TRN-05 — garanzia di provenance). Un output privo di citazioni è
rifiutato dal `SOPCitationValidator` prima che possa essere indicizzato o
consegnato all'operatore (SC-5).

---

## ShiftHandover

### Panoramica

`ShiftHandover` compila il report di fine turno aggregando gli eventi
operativi/manutentivi del turno corrente (da `audit.actions`), li riassume in
un documento strutturato e lo sottopone alla firma duale sequenziale dei
caposquadra uscente e entrante (D-SH-03). Il trigger è automatico (consumer
NATS `shift.boundary.>`) oppure manuale su richiesta del supervisore.

### Strumenti Utilizzati

| Strumento | Origine | Funzione |
|-----------|---------|----------|
| `query_audit_actions` | Phase 4 (`sft_agents.tools.audit`) | Recupera gli eventi del turno da `audit.actions` filtrati per finestra temporale e `action_type` (D-SH-02). |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Invia la richiesta di approvazione al caposquadra uscente (primo sign-off) e poi al caposquadra entrante (secondo sign-off). |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Scrive le righe `HANDOVER_DRAFT` e `HANDOVER_SIGNOFF` in `audit.actions`. |

### Fonti Dati

- **TimescaleDB `audit.actions`** — backbone di audit cross-cluster (ops/maintenance);
  il `ShiftAggregator` legge esclusivamente questa tabella (D-SH-02 — no tabelle
  `ops.alerts` o `ops.work_orders`).
- **TimescaleDB `maintenance.downtime_events`** — eventi di fermo macchina del turno.
- **sft-knowledge Qdrant** — citazioni RAG per il sommario narrativo del handover.

### HITL Tier

| Decisione | Tier | Approvatore |
|-----------|------|-------------|
| Firma turno uscente | supervisor (Decision.HITL_SUPERVISOR) | Caposquadra di turno uscente |
| Firma turno entrante | supervisor (Decision.HITL_SUPERVISOR) | Caposquadra di turno entrante |

Due righe `HANDOVER_SIGNOFF` per handover — firma sequenziale (D-SH-03).

### KPI Impattati

- **handover_completion_rate** — percentuale di turni con handover completato
  entro la scadenza di 3 minuti dal cambio turno.
- **handover_dual_signoff_p95** — latenza p95 del flusso dual-signoff.

### Invocazione

- **Endpoint API**: `POST /v1/agents/shift-handover/compile`
  con body `{"shift_start": "<ISO-UTC>", "shift_end": "<ISO-UTC>", "user_roles": ["shift_supervisor"]}`
- **Trigger NATS**: consumer su `shift.boundary.>` (boundary configurabile, es. 06:00/14:00/22:00).
- **Thread ID**: convenzione `knowledge.shift-handover.<uuid4>`.
- **Risposta**: `202 Accepted` (HITL asincrono).

### Audit Footprint

- `HANDOVER_DRAFT` — una riga al completamento del draft iniziale.
- `HANDOVER_SIGNOFF` — due righe per handover (uscente + entrante, D-SH-03).
- Ogni riga porta `source_uri` + `retrieved_at` sulle citazioni RAG (TRN-05).

---

## TrainingCoach

### Panoramica

`TrainingCoach` eroga sessioni di quiz MCQ adattivo per i diversi ruoli/persona
dell'operatore (tessitore, tintore, manutentore — dal registro Mantis sintetico,
D-X-03). Le domande sono generate deterministicamente da SOPs via RAG. Il punteggio
di competenza è calcolato senza LLM-judge (D-TC-01). Sopra soglia (default 0,80)
la firma di competenza è inviata al supervisore per approvazione HITL (D-TC-03).

### Strumenti Utilizzati

| Strumento | Origine | Funzione |
|-----------|---------|----------|
| `rag_retrieve` | Phase 5 (`sft_knowledge.retrieval.pipeline`) | Recupera chunk SOP rilevanti per il ruolo per la generazione delle domande. |
| `score_quiz` | trn-training-coach | Calcola il punteggio deterministico rispetto alle risposte corrette. |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Invia la richiesta di firma competenza al supervisore quando `score >= threshold`. |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Scrive `TRAINING_SESSION` e `TRAINING_SIGNOFF` in `audit.actions`. |

### Fonti Dati

- **sft-knowledge Qdrant** — index delle SOPs per ruolo; fornisce le citazioni
  RAG con `source_uri` + `retrieved_at` per ogni domanda generata (TRN-05).
- **Registro Mantis personas** — mappa `persona_role` a profilo SOP (D-X-03).

### HITL Tier

| Decisione | Tier | Approvatore |
|-----------|------|-------------|
| Punteggio < soglia (0,80) — fallimento | none (Decision.AUTO) | n/a |
| Punteggio >= soglia — competenza acquisita | supervisor (Decision.HITL_SUPERVISOR) | Caposquadra di turno |

### KPI Impattati

- **training_pass_rate** — percentuale di sessioni con punteggio >= soglia per ruolo.
- **competency_signoff_latency** — latenza tra notifica supervisore e firma.
- **rag_citation_coverage** — percentuale di domande con almeno una citazione `source_uri` (TRN-05).

### Invocazione

- **Sessione** `POST /v1/agents/training-coach/session`
  con body `{"persona_role": "tessitore", "user_roles": ["operator"]}`
- **Resume** `POST /v1/agents/training-coach/resume`
  con body `{"thread_id": "<id>", "decision": "approved"}`
- **Thread ID**: convenzione `knowledge.training-coach.<uuid4>`.
- **Risposta sessione**: `200 OK` con `competency_result` + `training_session`.
- **Risposta resume**: `200 OK` con firma competenza.

### Audit Footprint

- `TRAINING_SESSION` — una riga per sessione (pass o fail).
- `TRAINING_SIGNOFF` — una riga per sessione con punteggio >= soglia (post-HITL).
- Ogni sessione porta citazioni RAG con `source_uri` + `retrieved_at` (TRN-05).

---

## KnowledgeCurator

### Panoramica

`KnowledgeCurator` gestisce autonomamente la qualità del knowledge base:
rileva duplicati (esatti via SHA-256 + near-dup via BGE-M3 cosine, D-KC-01),
flagga documenti obsoleti per tipo (D-KC-02), e calcola il tasso di riutilizzo
dei documenti (D-KC-03). È un agente **completamente autonomo** — nessun HITL
(D-KC-04): le operazioni di dedup e staleness sono solo read/flag, senza azione
irreversibile.

### Strumenti Utilizzati

| Strumento | Origine | Funzione |
|-----------|---------|----------|
| `sha256_hash` | trn-knowledge-curator.dedup | Hash esatto del testo normalizzato per rilevamento duplicati esatti (D-KC-01). |
| `embed_bge_m3` | Phase 5 (`sft_knowledge.embedding.bge_m3`) | Embedding BGE-M3 per rilevamento near-duplicati via cosine similarity (D-KC-01). |
| `check_staleness` | trn-knowledge-curator.staleness | Confronta `last_updated` con la soglia per tipo documento (D-KC-02). |
| `compute_reuse_rate` | trn-knowledge-curator.reuse_rate | Calcola `distinct cited / total indexed` su finestra temporale (D-KC-03). |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Scrive `KNOWLEDGE_DEDUP` e `STALE_FLAG` in `audit.actions`. |

### Fonti Dati

- **sft-knowledge Qdrant** — index documenti; target per near-dup search e
  calcolo reuse-rate.
- **TimescaleDB `audit.actions`** — citazioni `source_uri` emesse dagli agenti
  TRN/MNT/OPS; base per il calcolo del tasso di riutilizzo (D-KC-03).

### HITL Tier

`KnowledgeCurator` è completamente autonomo (Decision.AUTO su tutte le operazioni).
Nessun HITL previsto (D-KC-04).

### KPI Impattati

- **knowledge_dedup_rate** — percentuale di ingest bloccati come duplicati.
- **stale_doc_fraction** — percentuale di documenti flaggati come obsoleti.
- **knowledge_reuse_rate** — `distinct cited / total indexed` (D-KC-03).

### Invocazione

- **Endpoint API**: `POST /v1/agents/knowledge-curator/ingest`
  con body `{"document_text": "...", "doc_type": "sop", "last_updated": "<ISO-UTC>"}`
- **Thread ID**: convenzione `knowledge.knowledge-curator.<uuid4>`.
- **Risposta**: `200 OK` (sincrona, autonoma — mai 202).

### Audit Footprint

- `KNOWLEDGE_DEDUP` — una riga per ingest con verdict (unique/near_duplicate/exact_duplicate).
- `STALE_FLAG` — una riga per documento flaggato come obsoleto.
- Entrambe le righe portano `source_uri` + timestamp (TRN-05).

---

## DocumentationSynthesizer

### Panoramica

`DocumentationSynthesizer` genera SOPs bilingui (IT primario + EN traduzione)
partendo da eventi storici RCA/downtime/coach aggregati per modalità di guasto
e asset (D-DS-02). L'output segue un template a sezioni fisse (Scopo,
Prerequisiti, Passi, Sicurezza, Riferimenti) con ogni affermazione ancorata a
citazioni `[SRC:N]` tracciate a `source_uri` (D-DS-03, TRN-05). L'approvazione
del supervisore è richiesta **prima** dell'indicizzazione in Qdrant (D-DS-03).

La traduzione IT → EN re-ancora le citazioni `[SRC:N]` per prevenire citation
drift (D-DS-01 Pitfall §1). Il `SOPCitationValidator` verifica la parità degli
anchor tra IT e EN prima del commit.

### Strumenti Utilizzati

| Strumento | Origine | Funzione |
|-----------|---------|----------|
| `aggregate_events` | trn-documentation-synthesizer.event_aggregator | Aggrega eventi RCA/downtime/coach da `audit.actions` per `failure_mode` + `asset_id` + `window_days` (D-DS-02). |
| `build_sop` | trn-documentation-synthesizer.sop_builder | Genera SOP IT con sezioni fisse e anchor `[SRC:N]` (D-DS-03). |
| `translate_sop` | trn-documentation-synthesizer.translator | Traduce SOP IT → EN preservando tutti gli anchor `[SRC:N]` (D-DS-01). |
| `validate_citations` | trn-documentation-synthesizer.validators | `SOPCitationValidator`: verifica provenance + parità anchor IT/EN (TRN-05). |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Invia la SOP draft al supervisore per approvazione pre-indicizzazione (D-DS-03). |
| `upsert_qdrant` | Phase 5 (`sft_knowledge`) | Indicizza la SOP approvata in Qdrant solo dopo HITL approval. |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Scrive `SOP_DRAFT` in `audit.actions` dopo l'approvazione. |

### Fonti Dati

- **TimescaleDB `audit.actions`** — eventi storici RCA/downtime/coach aggregati
  per modalità di guasto e asset (D-DS-02).
- **sft-knowledge Qdrant** — target di indicizzazione della SOP approvata.
- **BGE-M3 embedder** (Phase 5) — genera embedding per l'indicizzazione post-HITL.

### HITL Tier

| Decisione | Tier | Approvatore |
|-----------|------|-------------|
| SOP draft generata — pre-indicizzazione | supervisor (Decision.HITL_SUPERVISOR) | Caposquadra di turno |

L'indicizzazione Qdrant avviene **solo dopo** il HITL approval (D-DS-03).

### KPI Impattati

- **sop_generation_rate** — nuove SOPs bilingui approvate per settimana.
- **citation_coverage** — percentuale di sezioni SOP con almeno un anchor `[SRC:N]`.
- **hitl_approval_latency** — latenza p50/p95 dalla notifica supervisore all'approvazione.

### Invocazione

- **Draft** `POST /v1/agents/documentation-synthesizer/draft`
  con body `{"failure_mode": "...", "asset_id": "LOOM-01", "window_days": 30}`
- **Thread ID**: convenzione `knowledge.documentation-synthesizer.<uuid4>`.
- **Risposta draft**: `202 Accepted` con `hitl_status: supervisor_pending`.
- **Resume** via endpoint `/approvals` (Phase 6 HITL workflow).

### Audit Footprint

- `SOP_DRAFT` — una riga **dopo** l'approvazione del supervisore (non prima).
- Ogni citazione nella SOP porta `source_uri` + `retrieved_at` (TRN-05).
- La validazione `SOPCitationValidator` è eseguita prima del commit — output
  senza citazioni o con anchor drift vengono rifiutati (SC-5).

---

## Garanzia di Provenance (TRN-05 / SC-5)

Tutti e quattro gli agenti del cluster Knowledge & Training rispettano il
requisito **TRN-05**: ogni output che raggiunge un operatore o viene indicizzato
in Qdrant deve portare almeno una citazione con `source_uri` + `retrieved_at`
non nullo. Il `SOPCitationValidator` è il gate finale per il cluster
DocumentationSynthesizer; test negativi espliciti nel suite E2E (Plan 08-09)
assicurano che output opachi siano rifiutati in fase di test.

```
SC-5: "Citation provenance enforced; no opaque outputs accepted"
     — verificato da test_knowledge_cluster_e2e.py::test_trn05_opaque_output_rejected_by_sop_citation_validator
```
