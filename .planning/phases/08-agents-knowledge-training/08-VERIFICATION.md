---
phase: 08-agents-knowledge-training
verified: 2026-05-24T15:30:00Z
status: human_needed
score: 11/12
overrides_applied: 0
human_verification:
  - test: "Eseguire il flusso HITL completo di ShiftHandover (dual-interrupt) contro un LangGraph runtime reale con checkpointer PostgreSQL"
    expected: "handover_id stabile tra le 3 esecuzioni del nodo (prima esecuzione + due resume); esattamente 2 righe HANDOVER_SIGNOFF e 1 riga HANDOVER_DRAFT in audit.actions"
    why_human: "La stabilita dell'ID dipende dalla propagazione corretta di handover_id nel resumption state via Command(update={...}). Impossibile verificare senza un LangGraph runtime reale con checkpointer."
  - test: "Eseguire la migrazione 010_extend_audit_knw.sql su un cluster TimescaleDB di sviluppo reale (`make migrate-timescale`)"
    expected: "I 7 nuovi valori Phase 8 (HANDOVER_DRAFT, HANDOVER_SIGNOFF, TRAINING_SESSION, TRAINING_SIGNOFF, KNOWLEDGE_DEDUP, STALE_FLAG, SOP_DRAFT) vengono accettati da audit_actions_action_type_chk; i valori Phase 1-7 non regrediscono; doppia applicazione e no-op"
    why_human: "Il test test_migration_010.py richiede testcontainers (PostgreSQL+TimescaleDB live). Non eseguibile senza infrastruttura disponibile."
  - test: "Smoke test con LLM reale (Qwen2.5 via Ollama) per generazione quiz TrainingCoach e traduzione IT->EN DocumentationSynthesizer"
    expected: "Le domande MCQ generate sono pertinenti al ruolo/SOP. La traduzione EN conserva tutti gli anchor [SRC:N]. Le citazioni hanno source_uri + timestamp reali."
    why_human: "La qualita semantica dei contenuti generati da LLM richiede giudizio umano. Non verificabile con grep/assert deterministici."
  - test: "Verifica dual-supervisor approval queue per ShiftHandover via tabella audit"
    expected: "SELECT count(*) FROM audit.actions WHERE decision='hitl_supervisor' AND action_type='HANDOVER_SIGNOFF' restituisce 2 righe per ogni handover completato"
    why_human: "Richiede LangGraph runtime + PostgreSQL live. UI consumer (Phase 10) non ancora disponibile."
---

# Phase 8: Knowledge & Training Agents — Verification Report

**Phase Goal:** KnowledgeCurator, TrainingCoach, ShiftHandover, DocumentationSynthesizer con test — implementare i 4 agenti LangGraph del cluster Knowledge & Training, esporli via API gateway, con copertura test completa.
**Verified:** 2026-05-24T15:30:00Z
**Status:** human_needed
**Re-verification:** No — verifica iniziale

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                          | Status     | Evidence                                                                                                           |
|----|------------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------------|
| 1  | I 4 agenti esistono come moduli Python implementati (non stub)                                 | VERIFIED   | `agent.py` trovato in tutti e 4 i package; ciascuno >200 righe con logica di business reale                       |
| 2  | `build_knowledge_subgraph` router esiste e connette i 4 agenti                                 | VERIFIED   | `packages/sft-agents/src/sft_agents/runtime/clusters.py` riga 264; router condizionale START→agente→END           |
| 3  | API gateway espone 5 endpoint HTTP sotto `/v1/agents/`                                         | VERIFIED   | `knowledge_agents.py`: shift-handover/compile, training-coach/session, training-coach/resume, knowledge-curator/ingest, documentation-synthesizer/draft |
| 4  | Router `knowledge_agents` incluso nel main.py dell'API gateway                                 | VERIFIED   | `main.py` riga 49+66: `include_router(knowledge_agents_router.router)`                                             |
| 5  | HITL ordering corretto: interrupt-then-audit (no double-write su replay)                       | VERIFIED   | ShiftHandover: interrupt()→SIGNOFF#1→interrupt()→SIGNOFF#2→DRAFT; TrainingCoach: interrupt()→TRAINING_SESSION→TRAINING_SIGNOFF |
| 6  | `approval_id=None` per righe HITL pending (CR-03)                                              | VERIFIED   | TrainingCoach `agent.py` riga 292: `approval_id=None`; ShiftHandover `_write_audit()` usa `approval_id=None`       |
| 7  | ID stabili tra replay LangGraph (CR-04)                                                        | UNCERTAIN  | ShiftHandover: `handover_id = state.get("handover_id") or state.get("thread_id") or uuid4()`; SOPBuilder: `sop_id = sop_id or uuid4()`. Pattern implementato, ma stabilita dipende dalla propagazione nel resumption state — non verificabile senza runtime reale |
| 8  | TRN-05: citation provenance enforced (source_uri + retrieved_at obbligatori; output opaco rifiutato) | VERIFIED | `SOPCitationValidator.validate()`: check 1 (empty citations), check 2 (source_uri), check 3 (retrieved_at); 14 test passano |
| 9  | Migration 010 ActionType enum in lockstep                                                      | VERIFIED   | `010_extend_audit_knw.sql` + `enums.py`: 7 valori identici (HANDOVER_DRAFT, HANDOVER_SIGNOFF, TRAINING_SESSION, TRAINING_SIGNOFF, KNOWLEDGE_DEDUP, STALE_FLAG, SOP_DRAFT) |
| 10 | `reuse_rate` clamped a [0.0, 1.0] (CR-05)                                                     | VERIFIED   | `reuse_rate.py` riga 134: `rate = min(float(distinct_cited) / float(total_indexed), 1.0)` con commento CR-05       |
| 11 | Test esistono e passano per tutti i package                                                    | VERIFIED   | 22+16+17+14+24+10 = 103 test eseguiti, 0 falliti (run effettivi in questa sessione di verifica)                   |
| 12 | CR-01 fix: `HistoricalEventAggregator` importato correttamente in lifespan.py                  | VERIFIED   | `lifespan.py` riga 168: `from trn_documentation_synthesizer.event_aggregator import HistoricalEventAggregator`    |

**Score:** 11/12 truths verificate (Truth #7 UNCERTAIN — richiede verifica umana su runtime reale)

---

### Deferred Items

Nessun elemento deferito a fasi successive.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/agents/knowledge/shift-handover/src/trn_shift_handover/agent.py` | ShiftHandover LangGraph node | VERIFIED | 450+ righe; dual-interrupt HITL; stable handover_id |
| `apps/agents/knowledge/training-coach/src/trn_training_coach/agent.py` | TrainingCoach LangGraph node | VERIFIED | Scoring deterministico; single interrupt; AuditRecord corretto post-CR-02 |
| `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/agent.py` | KnowledgeCurator LangGraph node | VERIFIED | Dedup + staleness check; senza HITL (autonomo) |
| `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/agent.py` | DocumentationSynthesizer LangGraph node | VERIFIED | Pre-index HITL; bilingual SOP; SOPCitationValidator wired |
| `packages/sft-agents/src/sft_agents/runtime/clusters.py` | `build_knowledge_subgraph` router | VERIFIED | Funzione a riga 264; conditional routing START→agente→END con fallback knowledge-curator |
| `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py` | 5 endpoint HTTP knowledge cluster | VERIFIED | 5 `@router.post` decoratori; modelli request frozen+extra=forbid |
| `infra/migrations/timescale/010_extend_audit_knw.sql` | Migration idempotente + 7 nuovi ActionType | VERIFIED | DROP IF EXISTS + ADD CONSTRAINT; lockstep con enums.py |
| `packages/sft-agents/src/sft_agents/models/enums.py` | ActionType esteso con 7 valori Phase 8 | VERIFIED | Righe 132-138: 7 nuovi valori con commento D-X-01 |
| `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/validators.py` | SOPCitationValidator TRN-05 | VERIFIED | 3 check: empty citations, source_uri, retrieved_at; piu anchor parity |
| `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/reuse_rate.py` | Reuse-rate KPI con clamp [0.0, 1.0] | VERIFIED | `min(..., 1.0)` a riga 134 post-CR-05 |
| `apps/api-gateway/src/svc_api_gateway/lifespan.py` | HistoricalEventAggregator (post-CR-01) | VERIFIED | Import corretto riga 168; istanziazione riga 197 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `knowledge_agents.py` router | `supervisor_graph` | `get_supervisor_graph` dependency | VERIFIED | `Depends(get_supervisor_graph)` su ogni endpoint |
| `lifespan.py` | 4 agent instances | `app.state.knowledge_children` | VERIFIED | Dict `knowledge_children` con 4 chiavi; disponibile via `get_knowledge_children` |
| `lifespan.py` | `build_knowledge_subgraph` | `from sft_agents.runtime.clusters import build_knowledge_subgraph` | VERIFIED | Riga 170; `_knowledge_subgraph = build_knowledge_subgraph(knowledge_children)` |
| `main.py` | `knowledge_agents.router` | `app.include_router(...)` | VERIFIED | Riga 66: `app.include_router(knowledge_agents_router.router)` |
| `SOPCitationValidator` | `DocumentationSynthesizer.__call__` | `self._validator.validate(sop_draft)` | VERIFIED | `validator=SOPCitationValidator()` passato al costruttore in lifespan.py |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produce Dati Reali | Status |
|----------|---------------|--------|---------------------|--------|
| `knowledge_curator/agent.py` | `CurationReport` | `asyncpg` pool; `ReuseRateKPI.compute()` + `StalenessChecker` + `DedupChecker` | Si (SQL parametrizzato) | FLOWING |
| `shift_handover/agent.py` | `HandoverReport` | `ShiftAggregator(pool=pool)` → asyncpg | Si (SQL parametrizzato) | FLOWING |
| `training_coach/agent.py` | `MCQSession.score` | `score_session()` deterministico (index comparison) | Si (no LLM nel path di scoring) | FLOWING |
| `documentation_synthesizer/agent.py` | `SOPDraft` | `HistoricalEventAggregator(pool=pool)` + LLM (Phase 11) | Dati storici reali; LLM None in Phase 8 (accettabile) | FLOWING (parziale — LLM wired in Phase 11) |

---

### Behavioral Spot-Checks

| Behavior | Comando | Risultato | Status |
|----------|---------|-----------|--------|
| shift-handover tests (22) | `uv run python -m pytest tests/ -x -q` (in shift-handover/) | 22 passed in 0.30s | PASS |
| training-coach tests (16) | `uv run python -m pytest tests/ -x -q` (in training-coach/) | 16 passed in 0.26s | PASS |
| knowledge-curator tests (17) | `uv run python -m pytest tests/ -x -q` (in knowledge-curator/) | 17 passed in 0.57s | PASS |
| documentation-synthesizer tests (14) | `uv run python -m pytest tests/ -x -q` (in documentation-synthesizer/) | 14 passed in 0.36s | PASS |
| api-gateway knowledge router + e2e (24) | `uv run python -m pytest tests/test_knowledge_agents_router.py tests/test_knowledge_cluster_e2e.py -x -q` | 24 passed in 7.26s | PASS |
| sft-agents knowledge subgraph (10) | `uv run python -m pytest tests/runtime/test_build_knowledge_subgraph.py -x -q` | 10 passed in 0.40s | PASS |

**Totale: 103 test passati, 0 falliti**

---

### Probe Execution

Nessun probe `.sh` dichiarato nei PLAN o SUMMARY di questa fase. Step 7c: SKIPPED (nessun probe convenzionale trovato).

---

### Requirements Coverage

| Requisito | Piano | Descrizione | Status | Evidence |
|-----------|-------|-------------|--------|----------|
| TRN-02 | 08-05 | TrainingCoach — adaptive learning su procedure, valuta competenza con quiz contestualizzati | SATISFIED | `trn_training_coach/agent.py`: scoring deterministico, difficulty adattiva (`difficulty.py`), HITL sign-off; 16 test (quiz_scoring, difficulty, hitl_lifecycle) |
| TRN-03 | 08-02, 08-04 | ShiftHandover — sintetizza handover di turno aggregando eventi, decisioni, alert aperti | SATISFIED | `trn_shift_handover/agent.py`: aggregazione multi-sorgente, dual-interrupt sequenziale, 22 test (aggregator, dual_signoff, models) |
| TRN-04 | 08-07 | DocumentationSynthesizer — genera bozze SOP/runbook da eventi storici, sempre con HITL approval | SATISFIED | `trn_documentation_synthesizer/agent.py`: pre-index HITL; `sop_builder.py`, `translator.py`; 14 test (translator, hitl_preindex, citation_provenance) |
| TRN-05 | 08-07 | Tutti gli output TRN includono citazioni con source_uri e timestamp | SATISFIED | `SOPCitationValidator`: rifiuta output senza source_uri/retrieved_at; `KnowledgeCuratorIngestRequest.source_uri` (CR-03 fix); citazioni presenti in tutti i modelli |

**Nota:** TRN-01 (KnowledgeCurator come requisito separato) non figura nella lista dei requisiti dichiarati della fase (TRN-02..05), ma l'agente KnowledgeCurator e implementato (`trn_knowledge_curator/agent.py`) con 17 test passanti — implementazione presente anche se non richiesta esplicitamente nei plan frontmatter.

---

### Anti-Patterns Found

| File | Riga | Pattern | Gravita | Impatto |
|------|------|---------|---------|---------|
| `lifespan.py` | 175-184 | `llm=None`, `retrieval_pipeline=None`, `indexer=None` | INFO | Atteso — documentato come "Phase 11 will inject real implementations". Non e un placeholder nascosto: i costruttori accettano None esplicitamente e sollevano eccezione a call-time |
| `sop_builder.py` | 113 | `sections_en=sections_it` come placeholder | INFO | Documentato nel commento: "placeholder — agent replaces with translated sections". Il flusso corretto sovrascrive questo valore dopo `translate()` |

Nessun marker `TBD`, `FIXME`, `XXX` non referenziati trovati nei file modificati dalla fase.

**Warning rilevati nei test:** `PydanticDeprecatedSince20` da `unittest.mock` e `pytest.mark.timeout` non registrato — preesistenti, non introdotti dalla Phase 8.

---

### Fix Code Review Verificate (5 Critical + 5 Warning)

| Fix | File Modificato | Trovato nel Codice | Status |
|-----|-----------------|-------------------|--------|
| CR-01: ImportError `EventAggregator` → `HistoricalEventAggregator` | `lifespan.py` riga 168 | `from trn_documentation_synthesizer.event_aggregator import HistoricalEventAggregator` | VERIFIED |
| CR-02: `AuditWriter.write()` con `AuditRecord` oggetti completi | `training_coach/agent.py` righe 279-320 | `await self._audit.write(AuditRecord(...))` in tutti e 3 i siti | VERIFIED |
| CR-03: `document_id` + `source_uri` in `KnowledgeCuratorIngestRequest` | `knowledge_agents.py` righe 156-177 | Campi presenti con Field(min_length=1, max_length=...) | VERIFIED |
| CR-04: ID stabili — `handover_id`/`sop_id` da state invece di uuid4() puro | `shift_handover/agent.py` riga 349; `sop_builder.py` riga 120 | `state.get("handover_id") or state.get("thread_id") or str(uuid4())`; `sop_id = sop_id or str(uuid4())` | VERIFIED (logica presente; stabilita completa richiede verifica umana) |
| CR-05: `reuse_rate` clamped a 1.0 | `reuse_rate.py` riga 134 | `rate = min(float(distinct_cited) / float(total_indexed), 1.0)` | VERIFIED |
| WR-01: interrupt stub usa `NotImplementedError` invece di `MagicMock` | `training_coach/agent.py` righe 45-50 | `raise NotImplementedError("langgraph.types.interrupt non disponibile...")` | VERIFIED |
| WR-02: `field_validator` per tz-awareness su datetime | `knowledge_agents.py` righe 87-96, 184-193 | `_require_tz` validator su `shift_start/shift_end` e `last_updated` | VERIFIED |
| WR-03: `user_roles` in `KnowledgeCuratorIngestRequest` | `knowledge_agents.py` righe 179-182 | `user_roles: list[str] = Field(default_factory=list, ...)` | VERIFIED |
| WR-04: `translate_sop()` usa `asyncio.run()` invece di `get_event_loop()` | `translator.py` righe 255-258 | `return asyncio.run(translator.translate(sections_it, anchor_map))` | VERIFIED |
| WR-05: `_handle_agent_error()` non espone `str(exc)` nel body HTTP | `knowledge_agents.py` righe 241-255 | Body: `{"error": "internal_agent_error", ...}`; dettaglio solo nel log | VERIFIED |

---

### Human Verification Required

#### 1. Stabilita ID su replay LangGraph reale (CR-04)

**Test:** Avviare LangGraph con checkpointer PostgreSQL; invocare `ShiftHandover` con un `thread_id` fisso; lasciare che si interrompa al primo `interrupt()`; riprendere il thread due volte. Verificare che `handover_id` sia identico nelle 3 esecuzioni del nodo e che le 2 righe `HANDOVER_SIGNOFF` e la riga `HANDOVER_DRAFT` abbiano tutte lo stesso `handover_id`.

**Expected:** 3 righe in `audit.actions` con `handover_id` identico; nessuna riga con `handover_id` divergente.

**Why human:** Il pattern di stabilita e implementato (`state.get("handover_id") or state.get("thread_id")`), ma la propagazione del valore nel resume state tramite `Command(update={...})` non e verificabile senza un runtime LangGraph reale con checkpointer.

---

#### 2. Migrazione 010 su TimescaleDB live

**Test:** Eseguire `make migrate-timescale` su un cluster di sviluppo; verificare manualmente il constraint `audit_actions_action_type_chk` con `\d audit.actions` in psql.

**Expected:** Il constraint include tutti i 7 valori Phase 8. I valori Phase 1-7 non regrediscono. Doppia applicazione e no-op.

**Why human:** `test_migration_010.py` richiede testcontainers (PostgreSQL+TimescaleDB live) non disponibili nell'ambiente di verifica corrente.

---

#### 3. Smoke test LLM reale

**Test:** `pytest tests/e2e/knowledge/ -m real-llm` con Ollama + Qwen2.5 in esecuzione.

**Expected:** Quiz MCQ pertinenti al ruolo; traduzione EN con tutti gli anchor [SRC:N] conservati; citazioni con source_uri reali.

**Why human:** Qualita semantica non verificabile deterministicamente.

---

#### 4. Dual-supervisor approval queue (ShiftHandover)

**Test:** `SELECT count(*), action_type FROM audit.actions WHERE decision='hitl_supervisor' GROUP BY action_type` dopo un handover completato.

**Expected:** 2 righe `HANDOVER_SIGNOFF`, 1 riga `HANDOVER_DRAFT`.

**Why human:** Richiede LangGraph runtime + PostgreSQL live.

---

### Gaps Summary

Nessun gap bloccante. Tutti i 10 fix del code review sono presenti nel codice. I 103 test passano. Le 4 verifiche manuali non bloccano il rilascio ma devono essere eseguite prima della messa in produzione.

La Truth #7 (ID stabili su replay) e classificata UNCERTAIN (non FAILED) perche il pattern di stabilita e implementato correttamente nel codice — la verifica e impossibile senza runtime reale, non perche il codice sia sbagliato.

---

_Verified: 2026-05-24T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
