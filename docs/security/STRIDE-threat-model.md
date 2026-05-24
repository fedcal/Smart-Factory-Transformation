---
phase: 11-observability-evaluation-security-hardening
plan: 05
type: stride-threat-model
surfaces: [IT/OT boundary, RAG ingest, Agent orchestration]
categories: [Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege]
cells: 18
asvs_level: 2
created: 2026-05-25
consolidates: [08-SECURITY.md, 09-SECURITY.md, 10-SECURITY.md]
---

# STRIDE Threat Model — Smart Factory Transformation (v1.0)

Modello STRIDE trasversale: 6 categorie × 3 superfici = **18 celle**.
Ciascuna cella indica il threat, la mitigazione implementata e il riferimento al codice sorgente.

Consolida i registri per-fase:
- **Phase 08:** ShiftHandover, TrainingCoach, KnowledgeCurator, DocumentationSynthesizer
- **Phase 09:** InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster (09-SECURITY.md)
- **Phase 10:** API Gateway, SSE, Angular UI, HITL approvals (10-SECURITY.md)

---

## Superfici Analizzate

| ID | Superficie | Descrizione |
|----|------------|-------------|
| S1 | **IT/OT boundary** | Confine tra rete IT (NATS, API Gateway, AI) e rete OT (OPC-UA / PLC). Data-diode via Docker network. |
| S2 | **RAG ingest** | Pipeline di ingestione documenti: parse → sanitizzazione → chunking → embedding → Qdrant. |
| S3 | **Agent orchestration** | Supervisore LangGraph + cluster agenti: routing, HITL interrupt, audit, budget control. |

---

## Matrice STRIDE 6×3

### S — Spoofing (Impersonazione)

#### S1: IT/OT boundary — Spoofing

| Campo | Valore |
|-------|--------|
| **Threat** | Un attaccante IT invia dati OPC-UA fasulli sulla rete NATS spacciandosi per l'OT Bridge, inquinando le time-series TimescaleDB. |
| **Mitigazione** | L'OT Bridge è l'unico publisher autorizzato su `sensor.*`. Il confine Docker network isola il segmento OT (D-51). La firma del subject NATS è derivata dall'asset ID normalizzato, non modificabile a runtime. |
| **Codice mappato** | `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:NatsPublisher.publish` — subject derivato da `normalizer.derive_subject(asset_id, metric)`, non da input utente. |
| **Provenienza registro** | 10-SECURITY.md T-10-SC (Tampering supply-chain, adattato) |

#### S2: RAG ingest — Spoofing

| Campo | Valore |
|-------|--------|
| **Threat** | Un documento malevolo impersona una fonte autorevole (es. SOP ufficiale) per manipolare le risposte RAG. |
| **Mitigazione** | Il parser associa ogni chunk a `source_uri` e `acl_level` al momento dell'ingest. Il campo `source_uri` non è scrivibile dall'utente finale — è impostato dall'operatore ingest autenticato. |
| **Codice mappato** | `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py:IngestPipeline.ingest` — `source_uri` derivato dal path del documento, non da metadati del documento. |
| **Provenienza registro** | Nuovo (Phase 11, SEC-01) |

#### S3: Agent orchestration — Spoofing

| Campo | Valore |
|-------|--------|
| **Threat** | Un client non autenticato invoca endpoint agente (`/v1/approvals`, `/agents/*`) spoofeando un ruolo elevato nel body della richiesta. |
| **Mitigazione** | `require_roles()` decodifica il JWT firmato HS256 e ne estrae il claim `role`. Il body è ignorato per l'autorizzazione. Secret guard in `jwt.py` righe 38-53 garantisce che `API_SECRET_KEY` sia presente in produzione. |
| **Codice mappato** | `apps/api-gateway/src/svc_api_gateway/security/jwt.py:decode_token` + `apps/api-gateway/src/svc_api_gateway/security/rbac.py:require_roles` |
| **Provenienza registro** | 10-SECURITY.md T-10-01-01, T-10-01-02 |

---

### T — Tampering (Manomissione)

#### T1: IT/OT boundary — Tampering

| Campo | Valore |
|-------|--------|
| **Threat** | Un componente IT tenta di scrivere valori OPC-UA verso il PLC (comando in write-back), bypassando il data-diode. |
| **Mitigazione** | L'OT Bridge usa asyncua in modalità subscriber-only (D-51). Il test AST SC-5 verifica a ogni CI che nessun modulo ot-bridge chiami `write_value`, `call_method`, `set_attribute`, o `write_attributes`. |
| **Codice mappato** | `tests/security/test_ot_bridge_guard.py:test_ot_bridge_has_no_write_api_calls` — AST walk su `services/ot-bridge/src/svc_ot_bridge/*.py`. |
| **Provenienza registro** | Phase 08 (D-51 data-diode, 11-03 SEC-06) |

#### T2: RAG ingest — Tampering

| Campo | Valore |
|-------|--------|
| **Threat** | Un documento malevolo contiene istruzioni prompt-injection (es. "Ignore previous instructions") che sopravvivono al parsing e raggiungono l'embedder o il modello LLM. |
| **Mitigazione** | `sanitize_document()` applica una denylist regex deterministica (7 pattern) + `bleach.clean(tags=[], strip=True)` sul testo plain post-parse. Nessuna istruzione imperativa sopravvive (SC-3). |
| **Codice mappato** | `services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py:sanitize_document` |
| **Provenienza registro** | 10-SECURITY.md T-10-06-02 (adattato); Phase 11 SEC-04 |

#### T3: Agent orchestration — Tampering

| Campo | Valore |
|-------|--------|
| **Threat** | Un agente modifica il proprio stato LangGraph per bypassare il checkpoint HITL e auto-approvarsi. |
| **Mitigazione** | Il flusso HITL usa `interrupt()` nativo LangGraph: l'agente non può riprendere senza il resume-payload dell'API. `AuditRecord` viene scritto post-interrupt con `Decision.SIGNOFF` firmato dal principal JWT. |
| **Codice mappato** | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` — `recursion_limit` obbligatorio + interrupt semantics. |
| **Provenienza registro** | 09-SECURITY.md T-09-05, T-09-11 |

---

### R — Repudiation (Ripudio)

#### R1: IT/OT boundary — Repudiation

| Campo | Valore |
|-------|--------|
| **Threat** | Un operatore nega di aver letto dati restricted OT-derived inviati sulla rete IT senza lasciare traccia audit. |
| **Mitigazione** | W3C traceparent propagato via `NatsHeaderCarrier` (OTEL). Ogni span NATS è tracciato in Langfuse e Tempo. La correlazione trace-to-audit permette di ricostruire il flusso completo. |
| **Codice mappato** | `packages/sft-agents/src/sft_agents/otel/nats_carrier.py:NatsHeaderCarrier` — inject/extract W3C traceparent su header NATS. |
| **Provenienza registro** | Phase 11 11-01 (NatsHeaderCarrier OTEL propagation) |

#### R2: RAG ingest — Repudiation

| Campo | Valore |
|-------|--------|
| **Threat** | Un operatore ingest carica un documento e nega successivamente di averlo ingerito o di aver modificato i metadati. |
| **Mitigazione** | Il pipeline ingest scrive un `AuditRecord` con `ActionType.RESTRICTED_DOC_ACCESS` e `query_hash` SHA-256 per ogni accesso a chunk restricted. Il `source_uri` e `acl_level` sono immutabili post-ingest (Qdrant payload). |
| **Codice mappato** | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:RetrievalPipeline._write_restricted_audit` — RESTRICTED_DOC_ACCESS audit row con query_hash. |
| **Provenienza registro** | Phase 11 SEC-07, T-11-03-04 |

#### R3: Agent orchestration — Repudiation

| Campo | Valore |
|-------|--------|
| **Threat** | Un operatore approva o rifiuta un'azione HITL e nega di averlo fatto, o nega la motivazione fornita. |
| **Mitigazione** | `MOTIVATION_MIN_LENGTH = 10` (frontend enforcement). Backend scrive `AuditRecord` con `decision`, `motivation`, `decision_actor` = sub JWT. E2E test asserisce la presenza dell'audit record post-approvazione. |
| **Codice mappato** | `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts:MOTIVATION_MIN_LENGTH` + 10-SECURITY.md T-10-06-01 |
| **Provenienza registro** | 10-SECURITY.md T-10-06-01, T-10-10-01 |

---

### I — Information Disclosure (Divulgazione)

#### I1: IT/OT boundary — Information Disclosure

| Campo | Valore |
|-------|--------|
| **Threat** | Dati OT sensibili (setpoint, stati macchina riservati) escono dalla rete OT verso client IT non autorizzati tramite NATS. |
| **Mitigazione** | Il soggetto NATS `sensor.*` è consumato solo dall'API Gateway con ruolo autenticato. L'OT Bridge non espone endpoint HTTP; solo il gateway pubblica verso i client. Docker network separa i segmenti. |
| **Codice mappato** | `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:NatsPublisher` — pubblica solo su `sensor.{asset_id}.{metric}` senza endpoint HTTP. |
| **Provenienza registro** | Phase 11 (D-51 data-diode boundary) |

#### I2: RAG ingest — Information Disclosure

| Campo | Valore |
|-------|--------|
| **Threat** | Chunk di documenti `restricted` (es. brevetti, SOP confidenziali) vengono restituiti a utenti con ruolo `operator` che non ha accesso ACL. |
| **Mitigazione** | `build_acl_filter()` applica un pre-filter Qdrant in-engine basato su `ROLE_TO_ACL` (operator → solo `public`). Il filtro è engine-side, non post-filter Python — non bypassabile. Fail-closed se nessun ruolo mappa. |
| **Codice mappato** | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:build_acl_filter` — `Filter(must=[FieldCondition(key="acl_level", match=MatchAny(any=sorted(allowed)))])` |
| **Provenienza registro** | Phase 05 T-05-09-01; Phase 11 SEC-07 |

#### I3: Agent orchestration — Information Disclosure

| Campo | Valore |
|-------|--------|
| **Threat** | Un errore dell'agente espone stack trace, dettagli del modello LLM o dati di stato interno nel corpo della risposta API. |
| **Mitigazione** | `_handle_agent_error()` restituisce `{"error":"internal_agent_error"}` — nessun `str(exc)` nel body. I dettagli sono loggati solo via structlog sul server. Pattern identico in auth, kpi, sse. |
| **Codice mappato** | `apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py:_handle_agent_error` (righe 320-334) + 10-SECURITY.md T-10-01-03 |
| **Provenienza registro** | 09-SECURITY.md T-09-23, 10-SECURITY.md T-10-01-03 |

---

### D — Denial of Service (Negazione del servizio)

#### D1: IT/OT boundary — Denial of Service

| Campo | Valore |
|-------|--------|
| **Threat** | Un attaccante inonda il bridge NATS con messaggi finti a frequenza elevata, saturando la coda e bloccando i dati OT legittimi. |
| **Mitigazione** | Il bridge NATS usa una coda interna bounded. I messaggi in eccesso vengono droppati con log `opcua_queue_full_drop`. La subscription OPC-UA è in read-only — nessun feedback al PLC. |
| **Codice mappato** | `services/ot-bridge/src/svc_ot_bridge/opcua_client.py:OpcUaClient` — coda bounded con log `opcua_queue_full_drop`. |
| **Provenienza registro** | Phase 08 (D-51, coda bounded OT bridge) |

#### D2: RAG ingest — Denial of Service

| Campo | Valore |
|-------|--------|
| **Threat** | Un document upload massivo (file giganti o ingest loop) blocca il worker ingest esaurendo CPU/memoria, rendendo il servizio non disponibile. |
| **Mitigazione** | Il servizio knowledge-ingest ha un rate-limit in-process e processa un documento alla volta nel lifespan. La dimensione del file può essere limitata dal reverse proxy (Nginx max_body_size). |
| **Codice mappato** | `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py:IngestPipeline.ingest` — processing sequenziale; il gateway FastAPI limita la dimensione body via `max_request_body_size`. |
| **Provenienza registro** | Phase 11 (nuovo, SEC-01) |

#### D3: Agent orchestration — Denial of Service

| Campo | Valore |
|-------|--------|
| **Threat** | Un agente LangGraph entra in loop infinito (ricorsione), esaurisce CPU e blocca altri thread del supervisor. |
| **Mitigazione** | `recursion_limit=25` obbligatorio in ogni `build_invocation_config()`. Il supervisor solleva `GraphRecursionError → 503` se il limite è superato. `_RECURSION_LIMIT=5` nei cluster supply (più conservativo). |
| **Codice mappato** | `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py:build_invocation_config` — `"recursion_limit": 25` hardcoded come default. |
| **Provenienza registro** | 09-SECURITY.md T-09-24; Phase 11 CORE-03 |

---

### E — Elevation of Privilege (Escalation di privilegi)

#### E1: IT/OT boundary — Elevation of Privilege

| Campo | Valore |
|-------|--------|
| **Threat** | Un processo IT ottiene accesso write alla rete OT (es. inviando comandi a un PLC via OPC-UA) bypassando il data-diode. |
| **Mitigazione** | L'AST guard SC-5 (test CI) verifica che nessun modulo ot-bridge chiami le API write OPC-UA. Il Docker network `ot-net` è separato da `it-net`; solo l'OT Bridge ha accesso a entrambi (D-51). |
| **Codice mappato** | `tests/security/test_ot_bridge_guard.py:test_ot_bridge_has_no_write_api_calls` — AST walk + frozenset WRITE_PATTERNS. |
| **Provenienza registro** | Phase 11 SEC-06, SC-5 |

#### E2: RAG ingest — Elevation of Privilege

| Campo | Valore |
|-------|--------|
| **Threat** | Un utente con ruolo `operator` accede a chunk `restricted` tramite manipolazione dei parametri di query (es. passando `acl_level=restricted` nella request). |
| **Mitigazione** | Il filtro ACL è applicato dall'engine Qdrant (pre-filter), non dal codice Python. `build_acl_filter()` costruisce il filtro esclusivamente da `ROLE_TO_ACL[user_roles]` — il chiamante non può specificare i livelli ACL ammessi. |
| **Codice mappato** | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:build_acl_filter` — `ROLE_TO_ACL` è un dict immutabile a livello di modulo. |
| **Provenienza registro** | Phase 05 T-05-09-01; 10-SECURITY.md T-10-06-03 |

#### E3: Agent orchestration — Elevation of Privilege

| Campo | Valore |
|-------|--------|
| **Threat** | Un agente con excessive agency esegue azioni oltre il perimetro autorizzato (es. scrive su DB produzione, invia comandi a sistemi esterni) senza approvazione HITL. |
| **Mitigazione** | Ogni agente ha un `recursion_limit=25` + HITL mandatory per azioni `Decision.APPROVE`. I tool disponibili sono dichiarati esplicitamente nella toolspec LangGraph — nessun tool generico di shell/file. |
| **Codice mappato** | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` — HITL interrupt obbligatorio per azioni rilevanti + `recursion_limit` come guard. |
| **Provenienza registro** | 09-SECURITY.md T-09-25; OWASP LLM06 (excessive agency) |

---

## Riepilogo Mitigazioni per Categoria

| Categoria | S1 IT/OT | S2 RAG ingest | S3 Agent orch. |
|-----------|----------|---------------|----------------|
| **Spoofing** | Docker network + NATS subject derivato | source_uri impostato dall'operatore | JWT HS256 + require_roles |
| **Tampering** | AST guard D-51 (no write OPC-UA) | sanitize_document() denylist+bleach | LangGraph interrupt + audit post-HITL |
| **Repudiation** | NatsHeaderCarrier W3C traceparent | RESTRICTED_DOC_ACCESS audit + query_hash | MOTIVATION_MIN_LENGTH + AuditRecord |
| **Info Disclosure** | Docker network segmentation | build_acl_filter Qdrant pre-filter | _handle_agent_error generico |
| **Denial of Service** | OpcUaClient bounded queue | IngestPipeline sequential + proxy limit | recursion_limit=25 + GraphRecursionError→503 |
| **EoP** | AST guard CI (test_ot_bridge_guard) | build_acl_filter immutabile | safe_invoke HITL + tool scope limitato |

---

## Registro per-fase consolidato

### Phase 08 — Knowledge & Training Agents

| Threat ID | Superficie STRIDE | Cella |
|-----------|-------------------|-------|
| D-51 data-diode | IT/OT boundary | T1 (Tampering), E1 (EoP) |
| SEC-04 sanitize_document | RAG ingest | T2 (Tampering) |
| SEC-06 AST guard | IT/OT boundary | T1, E1 |
| SEC-07 RESTRICTED_DOC_ACCESS | RAG ingest | R2 (Repudiation), I2 (Info Disc) |

### Phase 09 — Supply Chain & Economics

| Threat ID | Superficie STRIDE | Cella |
|-----------|-------------------|-------|
| T-09-24 recursion_limit | Agent orch. | D3 (DoS) |
| T-09-05 HITL audit | Agent orch. | R3 (Repudiation) |
| T-09-25 JWT/RBAC deferred | Agent orch. | S3 (Spoofing) |
| T-09-23 error body | Agent orch. | I3 (Info Disc) |

### Phase 10 — Backend API & Frontend

| Threat ID | Superficie STRIDE | Cella |
|-----------|-------------------|-------|
| T-10-01-01 JWT HS256 | Agent orch. | S3 (Spoofing) |
| T-10-01-03 error body | Agent orch. | I3 (Info Disc) |
| T-10-06-01 MOTIVATION_MIN | Agent orch. | R3 (Repudiation) |
| T-10-06-03 acl_level UI | RAG ingest | E2 (EoP) |
| T-10-02-04 DoS heavy query | Agent orch. | D3 (DoS) — AR-01 |
| T-10-03-01 SSE token URL | Agent orch. | I3 (Info Disc) — AR-02 |

---

## Note di Chiusura

Questo documento realizza **SC-4** (STRIDE ≥1 threat per categoria × 3 superfici con mitigazione mappata a codice) ed è il contratto di sicurezza trasversale del progetto v1.0.

I rischi accettati **AR-01..AR-07** sono documentati in `.planning/phases/10-backend-api-frontend/10-SECURITY.md` e annotati nella sezione "Phase 11 Closure" di quel documento.
