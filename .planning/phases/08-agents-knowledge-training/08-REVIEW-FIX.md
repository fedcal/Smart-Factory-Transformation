---
phase: 08-agents-knowledge-training
fixed_at: 2026-05-24T14:30:00Z
review_path: .planning/phases/08-agents-knowledge-training/08-REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 10
skipped: 0
status: all_fixed
---

# Phase 8: Code Review Fix Report

**Fixed at:** 2026-05-24T14:30:00Z
**Source review:** `.planning/phases/08-agents-knowledge-training/08-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 10 (5 Critical + 5 Warning)
- Fixed: 10
- Skipped: 0

---

## Fixed Issues

### CR-01: ImportError al boot — `EventAggregator` non esiste nel modulo `event_aggregator`

**Files modified:** `apps/api-gateway/src/svc_api_gateway/lifespan.py`
**Commit:** `7464b92`
**Applied fix:** Corretta l'importazione da `EventAggregator` (inesistente) a `HistoricalEventAggregator`
(l'unica classe esposta dal modulo, confermata da `__all__ = ["HistoricalEventAggregator"]`).
L'istanza alla riga 197 usa già il nome corretto. Il crash al boot dell'API gateway è eliminato.

---

### CR-02: TypeError a runtime — `TrainingCoach` chiama `AuditWriter.write()` con keyword args invece di `AuditRecord`

**Files modified:** `apps/agents/knowledge/training-coach/src/trn_training_coach/agent.py`
**Commit:** `171079b`
**Applied fix:** Tutti e tre i siti di chiamata `write()` (percorso PASS dopo interrupt,
TRAINING_SIGNOFF dopo interrupt, e percorso FAIL autonomo) ora costruiscono un oggetto
`AuditRecord` completo e lo passano come argomento posizionale, seguendo il pattern di
`KnowledgeCurator._write_dedup_audit()`. Il TypeError a runtime è eliminato.

---

### CR-03: KeyError a runtime — `KnowledgeCuratorIngestRequest` non include `document_id` e `source_uri`

**Files modified:** `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py`
**Commit:** `a0b73a9` (insieme a WR-02, WR-03, WR-05)
**Applied fix:** Aggiunti i campi `document_id` (str, min_length=1, max_length=256) e
`source_uri` (str, min_length=1, max_length=512) al modello `KnowledgeCuratorIngestRequest`.
Propagati entrambi nello state dict della funzione `post_knowledge_curator_ingest()`.
Il KeyError a runtime è eliminato.

---

### CR-04: ID instabili nel replay LangGraph — `handover_id` e `sop_id` ricalcolati ad ogni esecuzione

**Files modified:**
`apps/agents/knowledge/shift-handover/src/trn_shift_handover/agent.py`,
`apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/sop_builder.py`
**Commit:** `a0b73a9` (insieme ad altri fix) e `a84fe0c`
**Applied fix (requires human verification):**
- `ShiftHandover.__call__()`: `handover_id` ora deriva da `state.get("handover_id") or state.get("thread_id") or str(uuid4())`.
  Il thread_id LangGraph è stabile tra replay (fornito nella config). Il payload dell'interrupt
  include `handover_id` cosi che il resume possa propagarlo via state update.
- `SOPBuilder.build()`: accetta `sop_id` come parametro opzionale; se fornito dal chiamante
  (che lo legge da `state.get("sop_id")`), non genera un nuovo UUID. Il pattern è
  `sop_id = sop_id or str(uuid4())`.

Nota: la logica di stabilità dipende dal chiamante che propaghi correttamente `handover_id`/`sop_id`
nel resumption state. Si raccomanda verifica manuale del flusso HITL completo con LangGraph
reale prima di portare in produzione.

---

### CR-05: `reuse_rate` può superare 1.0 — `ValidationError` a runtime in `CurationReport`

**Files modified:** `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/reuse_rate.py`
**Commit:** `7cd901c`
**Applied fix:** Aggiunto `min(..., 1.0)` al calcolo: `rate = min(float(distinct_cited) / float(total_indexed), 1.0)`.
Il guard `total_indexed == 0` restituisce `0.0` prima del calcolo (pre-esistente, corretto).
Il vincolo `le=1.0` di `CurationReport.reuse_rate` non può più essere violato.

---

### WR-01: Fallback `interrupt` di TrainingCoach usa `MagicMock` — maschera fallimenti nei test

**Files modified:** `apps/agents/knowledge/training-coach/src/trn_training_coach/agent.py`
**Commit:** `171079b` (insieme a CR-02)
**Applied fix:** Lo stub di fallback ora solleva `NotImplementedError` con messaggio diagnostico
("Usare patch('trn_training_coach.agent.interrupt', ...) nei test HITL."), identico al
Pattern G usato da ShiftHandover e DocumentationSynthesizer. Il `MagicMock` silenzioso
è rimosso.

---

### WR-02: `ShiftHandoverCompileRequest` e `KnowledgeCuratorIngestRequest` non validano la tz-awareness dei datetime

**Files modified:** `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py`
**Commit:** `a0b73a9`
**Applied fix:**
- `ShiftHandoverCompileRequest`: `@field_validator("shift_start", "shift_end")` rifiuta
  datetime naive con `ValueError` comprensibile (messaggio IT + istruzione di correzione),
  producendo 422 Unprocessable Entity invece di 500.
- `KnowledgeCuratorIngestRequest`: `@field_validator("last_updated")` applica la stessa logica.

---

### WR-03: `KnowledgeCuratorIngestRequest` non espone `user_roles` — nessuna propagazione ACL

**Files modified:** `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py`
**Commit:** `a0b73a9`
**Applied fix:** Aggiunto `user_roles: list[str] = Field(default_factory=list, description="Caller roles for future ACL enforcement (Phase 11)")`.
Il campo ha default vuoto per non rompere i client esistenti. Consistente con gli altri
endpoint del cluster knowledge.

---

### WR-04: `translate_sop()` usa `asyncio.get_event_loop()` deprecato — crash su Python 3.12+

**Files modified:** `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/translator.py`
**Commit:** `fe539c1`
**Applied fix:** Rimossa tutta la logica con `get_event_loop()` e `ThreadPoolExecutor`.
`translate_sop()` usa ora `asyncio.run(translator.translate(sections_it, anchor_map))`
direttamente — crea sempre un nuovo event loop, sicuro in contesti sincroni, non deprecato
su Python 3.12+.

---

### WR-05: `_handle_agent_error()` espone `str(exc)` nel body della risposta HTTP 500

**Files modified:** `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py`
**Commit:** `a0b73a9`
**Applied fix:** `_handle_agent_error()` ora restituisce `{"error": "internal_agent_error", "thread_id": thread_id}`
(messaggio generico) nel body HTTP 500, e logga `str(exc)` + `exc_info=True` solo
lato server. DSN, path, nomi di classi interne non raggiungono più il client.

---

## Test Results

Tutti i test delle suite interessate passano:

| Suite | Risultato |
|-------|-----------|
| `apps/agents/knowledge/knowledge-curator` | 17 passed |
| `apps/agents/knowledge/training-coach` | 16 passed |
| `apps/agents/knowledge/shift-handover` | 22 passed |
| `apps/agents/knowledge/documentation-synthesizer` | 14 passed |
| `apps/api-gateway` (test_knowledge_agents_router + test_knowledge_cluster_e2e) | 24 passed |

Totale: **93 test passati, 0 falliti**. Warnings presenti (PydanticDeprecatedSince20 da
`unittest.mock` su Pydantic v2 e `pytest.mark.timeout` non registrato) sono preesistenti
e non introdotti da queste fix.

---

_Fixed: 2026-05-24T14:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
