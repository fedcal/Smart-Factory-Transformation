---
phase: 08-agents-knowledge-training
reviewed: 2026-05-24T14:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - packages/sft-agents/src/sft_agents/models/enums.py
  - packages/sft-agents/src/sft_agents/runtime/clusters.py
  - infra/migrations/timescale/010_extend_audit_knw.sql
  - apps/agents/knowledge/shift-handover/src/trn_shift_handover/models.py
  - apps/agents/knowledge/shift-handover/src/trn_shift_handover/aggregator.py
  - apps/agents/knowledge/shift-handover/src/trn_shift_handover/metadata.py
  - apps/agents/knowledge/shift-handover/src/trn_shift_handover/prompts.py
  - apps/agents/knowledge/shift-handover/src/trn_shift_handover/agent.py
  - apps/agents/knowledge/shift-handover/src/trn_shift_handover/consumer.py
  - apps/agents/knowledge/training-coach/src/trn_training_coach/quiz.py
  - apps/agents/knowledge/training-coach/src/trn_training_coach/difficulty.py
  - apps/agents/knowledge/training-coach/src/trn_training_coach/models.py
  - apps/agents/knowledge/training-coach/src/trn_training_coach/metadata.py
  - apps/agents/knowledge/training-coach/src/trn_training_coach/prompts.py
  - apps/agents/knowledge/training-coach/src/trn_training_coach/agent.py
  - apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/dedup.py
  - apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/staleness.py
  - apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/reuse_rate.py
  - apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/models.py
  - apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/metadata.py
  - apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/agent.py
  - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/models.py
  - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/event_aggregator.py
  - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/sop_builder.py
  - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/translator.py
  - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/validators.py
  - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/metadata.py
  - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/prompts.py
  - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/agent.py
  - apps/api-gateway/src/svc_api_gateway/dependencies.py
  - apps/api-gateway/src/svc_api_gateway/lifespan.py
  - apps/api-gateway/src/svc_api_gateway/main.py
  - apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py
findings:
  critical: 5
  warning: 5
  info: 2
  total: 12
status: issues_found
---

# Phase 8: Code Review Report — Knowledge & Training Agents

**Reviewed:** 2026-05-24T14:00:00Z
**Depth:** standard
**Files Reviewed:** 33
**Status:** issues_found

---

## Summary

La fase 8 implementa 4 agenti LangGraph (ShiftHandover, TrainingCoach, KnowledgeCurator,
DocumentationSynthesizer) più il router HTTP dell'API gateway. La struttura generale è
solida: i modelli Pydantic sono frozen + extra="forbid", il pattern HITL interrupt-then-audit
(CR-02) e approval_id=None (CR-03) sono rispettati nei tre agenti con HITL. Il modulo
SQL 010 è idempotente e in lockstep con l'enum ActionType.

Tuttavia sono stati trovati **5 blocanti (Critical)** che impediscono il funzionamento
corretto in produzione:

1. **Crash al boot** dell'API gateway (ImportError: `EventAggregator` non esiste nel modulo).
2. **TypeError a runtime** in TrainingCoach: `AuditWriter.write()` viene chiamato con
   keyword arguments anziché un oggetto `AuditRecord`.
3. **KeyError a runtime** in KnowledgeCurator: lo state dict del router non include
   `document_id` e `source_uri`, obbligatori per `IngestRequest`.
4. **ID instabili nel replay LangGraph**: `handover_id` (ShiftHandover) e `sop_id`
   (DocumentationSynthesizer) vengono ricalcolati con `uuid4()` ad ogni re-esecuzione del
   nodo (prima esecuzione + ogni resume), rendendo inconsistente la traccia di audit HITL.
5. **ValidationError a runtime** in KnowledgeCurator: `reuse_rate` può superare 1.0 quando
   i documenti citati sono più di quelli indicizzati, rompendo il vincolo `le=1.0` di
   `CurationReport`.

---

## Structural Findings (fallow)

*Nessun blocco `<structural_findings>` fornito per questa fase.*

---

## Narrative Findings (AI reviewer)

### Critical Issues

---

### CR-01: ImportError al boot — `EventAggregator` non esiste nel modulo `event_aggregator`

**File:** `apps/api-gateway/src/svc_api_gateway/lifespan.py:168`

**Issue:** La lifespan importa `EventAggregator` dal modulo
`trn_documentation_synthesizer.event_aggregator`, ma il modulo espone soltanto la classe
`HistoricalEventAggregator` (confermato da `__all__ = ["HistoricalEventAggregator"]` alla
riga 141 di `event_aggregator.py`). Questo causa un `ImportError` immediato all'avvio
dell'API gateway, rendendo il servizio totalmente inutilizzabile.

**Fix:**
```python
# lifespan.py riga 168 — correggere il nome della classe importata
from trn_documentation_synthesizer.event_aggregator import HistoricalEventAggregator  # noqa: PLC0415

# riga 197 — usare il nome corretto
documentation_synthesizer_agent = DocumentationSynthesizer(
    ...
    event_aggregator=HistoricalEventAggregator(pool=pool),
    ...
)
```

---

### CR-02: TypeError a runtime — `TrainingCoach` chiama `AuditWriter.write()` con keyword args invece di `AuditRecord`

**File:** `apps/agents/knowledge/training-coach/src/trn_training_coach/agent.py:244-277`

**Issue:** `AuditWriter.write()` ha la firma `async def write(self, record: AuditRecord) -> None`
(un solo argomento posizionale `record`). TrainingCoach chiama questo metodo passando
keyword arguments arbitrari (`action_type=`, `decision=`, `session_id=`, `score=`, ecc.),
causando `TypeError: write() got unexpected keyword argument 'action_type'` ad ogni
esecuzione del percorso passante (HITL) e di quello fallente (AUTO). L'agente
non scriverà mai righe di audit e l'eccezione propagherà attraverso il router come 500.

**Fix:** costruire un `AuditRecord` completo prima di chiamare `write()`, seguendo il
pattern di `KnowledgeCurator._write_dedup_audit()`:
```python
# agent.py riga 244 (percorso PASS) — sostituire le chiamate errate
from uuid import uuid4
from datetime import datetime, timezone
from sft_agents.models.audit import AuditRecord
from sft_agents.models.evidence import EvidencePanel, TokenUsage
from sft_agents.models.proposed_action import ProposedAction

now = datetime.now(timezone.utc)
evidence_panel = EvidencePanel(
    input_summary=f"session={session_id} role={persona_role} score={score:.2f}"[:500],
    input_truncated=False,
    tool_calls=[],
    rag_citations=[],
    confidence=1.0,
    model="unknown@training-coach",
    prompt_hash="0" * 64,
    tokens=TokenUsage(input=0, output=0, total=0),
    duration_ms=0,
)
action = ProposedAction.from_payload(
    thread_id=f"knowledge.training-coach.{session_id}",
    action_type=ActionType.TRAINING_SESSION,
    args={"session_id": session_id, "persona_role": persona_role, "score": score},
    target_subject=None,
)
record = AuditRecord(
    id=uuid4(),
    ts=now,
    action_id=action.id,
    agent_id="training-coach",
    thread_id=f"knowledge.training-coach.{session_id}",
    cluster="knowledge",
    action_type=ActionType.TRAINING_SESSION.value,
    evidence_panel=evidence_panel,
    decision=Decision.HITL_SUPERVISOR,
    decision_actor=None,
    motivation=f"score={score:.2f} >= threshold={self._pass_threshold}",
    budget_snapshot=_EMPTY_BUDGET,
    approval_id=None,
)
await self._audit.write(record)
```
Ripetere il pattern per `TRAINING_SIGNOFF` e per il percorso fallente (`Decision.AUTO`).

---

### CR-03: KeyError a runtime — `KnowledgeCuratorIngestRequest` non include `document_id` e `source_uri`

**File:** `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py:137-158` e
`apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/agent.py:141-145`

**Issue:** Il router costruisce lo state dict con soli tre campi
(`document_text`, `doc_type`, `last_updated`), ma `KnowledgeCurator.__call__()` accede
a `state["document_id"]` e `state["source_uri"]` senza `get()` con default,
causando `KeyError` immediato ad ogni richiesta POST `/v1/agents/knowledge-curator/ingest`.
Questi campi sono obbligatori per `IngestRequest`.

**Fix in due punti:**

1. Aggiungere i campi al modello di richiesta HTTP:
```python
# routers/knowledge_agents.py — KnowledgeCuratorIngestRequest
class KnowledgeCuratorIngestRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1, max_length=256,
        description="Unique document identifier (client-provided or SHA256 of content)")
    document_text: str = Field(min_length=1, max_length=100_000, ...)
    doc_type: str = Field(min_length=1, max_length=64, ...)
    last_updated: datetime = Field(...)
    source_uri: str = Field(min_length=1, max_length=512,
        description="Document source URI for citation traceability (TRN-05)")
```

2. Propagare i campi nello state dict del router:
```python
# routers/knowledge_agents.py — post_knowledge_curator_ingest
state: dict[str, Any] = {
    "target_agent": "knowledge-curator",
    "document_id": body.document_id,
    "document_text": body.document_text,
    "doc_type": body.doc_type,
    "last_updated": body.last_updated,
    "source_uri": body.source_uri,
}
```

---

### CR-04: ID instabili nel replay LangGraph — `handover_id` e `sop_id` ricalcolati ad ogni esecuzione

**File:**
- `apps/agents/knowledge/shift-handover/src/trn_shift_handover/agent.py:346`
- `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/sop_builder.py:116`

**Issue:** LangGraph re-esegue il nodo dall'inizio ad ogni resume dopo un interrupt.
In `ShiftHandover.__call__()`, `handover_id = str(uuid4())` è chiamato alla riga 346,
fuori da qualsiasi controllo di replay. Di conseguenza:

- Prima esecuzione → `handover_id_A` → interrupt con payload `{handover_id: "A"}`
- Resume 1 → re-esecuzione → `handover_id_B` → scrive SIGNOFF #1 con `handover_id_B` → interrupt #2
- Resume 2 → re-esecuzione → `handover_id_C` → scrive SIGNOFF #2 e DRAFT con `handover_id_C`

Le tre righe di audit avranno tre `handover_id` differenti, rendendo impossibile
correlare i due sign-off con il draft corrispondente. Lo stesso problema si verifica
in `SOPBuilder.build()` dove `sop_id = str(uuid4())` alla riga 116 produce un `sop_id`
diverso tra la prima esecuzione (mostrato nel payload dell'interrupt) e il resume
(usato nella riga di audit `SOP_DRAFT`).

**Fix:** Derivare l'ID dall'input stabile oppure leggerlo dallo state se già presente:
```python
# ShiftHandover.__call__() — riga 344-346
# Leggere handover_id dallo state (se il caller lo fornisce) o generarlo una sola volta
# e includerlo nel payload dell'interrupt perché possa essere ripristinato al resume.
# Soluzione pragmatica: derivarlo dal thread_id del config LangGraph (stabile tra replay).
handover_id = str(state.get("handover_id") or state.get("thread_id", str(uuid4())))
```
Analogamente in `SOPBuilder.build()`:
```python
# sop_builder.py riga 116 — accettare sop_id come parametro opzionale
sop_id = state.get("sop_id") or str(uuid4())
```
Oppure, soluzione robusta: includere `handover_id`/`sop_id` nello state delta di ritorno
e fare in modo che il chiamante li propaghi al resume tramite `Command(update={...})`.

---

### CR-05: `reuse_rate` può superare 1.0 — `ValidationError` a runtime in `CurationReport`

**File:** `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/reuse_rate.py:130-132`

**Issue:** La formula `reuse_rate = distinct_cited / total_indexed` può superare 1.0 quando
i documenti citati nelle audit row (finestra rolling) provengono da documenti poi rimossi
dall'indice (oppure da documenti di altri agenti/cluster che non sono in `documents`).
Il campo `CurationReport.reuse_rate` ha il vincolo `le=1.0` (riga 109 di `models.py`),
causando `ValidationError` al momento della costruzione del report e conseguente crash
dell'agente con 500 al router.

**Fix:** Aggiungere un `min(..., 1.0)` prima di restituire il valore:
```python
# reuse_rate.py — compute_reuse_rate(), dopo riga 131
rate = min(float(distinct_cited) / float(total_indexed), 1.0)
```

---

### Warnings

---

### WR-01: Fallback `interrupt` di TrainingCoach usa `MagicMock` — maschera fallimenti nei test

**File:** `apps/agents/knowledge/training-coach/src/trn_training_coach/agent.py:44-46`

**Issue:** Quando `langgraph` non è installato (ambienti di test), il fallback importa
`unittest.mock.MagicMock` e lo assegna a `interrupt`. Un `MagicMock` chiamato come funzione
restituisce un altro `MagicMock` (truthy) senza sollevare eccezioni, rendendo invisibili
i test che verificano il comportamento dell'interrupt HITL. Il pattern corretto usato
dagli altri agenti (ShiftHandover, DocumentationSynthesizer) è sollevare `NotImplementedError`.

**Fix:**
```python
# agent.py righe 44-46 — sostituire MagicMock con NotImplementedError (Pattern G)
except ImportError:  # Pattern G — test shim
    def interrupt(value: Any) -> Any:  # type: ignore[misc]
        """Fallback stub — only in non-langgraph test environments."""
        raise NotImplementedError(
            "langgraph.types.interrupt non disponibile. "
            "Usare patch('trn_training_coach.agent.interrupt', ...) nei test HITL."
        )
```

---

### WR-02: `ShiftHandoverCompileRequest` e `KnowledgeCuratorIngestRequest` non validano la tz-awareness dei datetime

**File:**
- `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py:80-81` (shift_start/shift_end)
- `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py:155-158` (last_updated)

**Issue:** I modelli di richiesta HTTP non includono un `field_validator` che rifiuti
datetime naive. Se un client omette il timezone offset (es. `"2026-01-01T06:00:00"` senza
`Z` o `+00:00`), Pydantic accetta il valore; la validazione fallisce poi all'interno
dell'agente (ShiftWindow validator o `is_stale()` raise ValueError), producendo una
risposta 500 invece del corretto 422 Unprocessable Entity. Il confine di fiducia deve
essere al perimetro HTTP.

**Fix:** Aggiungere un `field_validator` in entrambi i modelli:
```python
from pydantic import field_validator

@field_validator("shift_start", "shift_end")
@classmethod
def _require_tz(cls, v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError(
            f"Il campo datetime deve essere tz-aware (UTC). "
            f"Ricevuto naive: {v!r}. Aggiungere 'Z' o '+00:00' alla stringa ISO."
        )
    return v
```

---

### WR-03: `KnowledgeCuratorIngestRequest` non espone `user_roles` — nessuna propagazione ACL

**File:** `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py:137-158`

**Issue:** Gli altri endpoint del cluster knowledge (shift-handover, training-coach)
propagano `user_roles` allo state per il filtro RAG ACL (Phase 5). `KnowledgeCuratorIngestRequest`
non include il campo `user_roles`, impedendo qualsiasi futuro controllo di accesso
sul percorso di ingest. Il requisito ACL è documentato come "Phase 11 concern" ma
l'omissione completa rompe la consistenza del modello e rende più difficile l'aggiunta
retroattiva quando il campo diventerà obbligatorio.

**Fix:** Aggiungere il campo con default vuoto (non rompe i client esistenti):
```python
user_roles: list[str] = Field(
    default_factory=list,
    description="Caller roles for future ACL enforcement (Phase 11)",
)
```

---

### WR-04: `translate_sop()` usa `asyncio.get_event_loop()` deprecato — crash su Python 3.12+

**File:** `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/translator.py:258-267`

**Issue:** `asyncio.get_event_loop()` emette `DeprecationWarning` in Python 3.10+ quando
non c'è un event loop corrente, e in Python 3.12+ lancia `RuntimeError` se chiamato
fuori da un contesto async. Il progetto gira su Python 3.14 (confermato dall'ambiente).
La funzione `translate_sop()` è una shim sincrona pensata per i test; la logica di
fallback con `concurrent.futures.ThreadPoolExecutor` è anche semanticamente rischiosa
perché lancia `asyncio.run()` in un thread secondario.

**Fix:**
```python
def translate_sop(sections_it, anchor_map, *, llm):
    """Shim sincrono per ambienti di test — usa asyncio.run() direttamente."""
    import asyncio
    translator = SOPTranslator(llm=llm)
    return asyncio.run(translator.translate(sections_it, anchor_map))
```
`asyncio.run()` crea sempre un nuovo event loop; è sicuro in contesti sincroni
e non deprecato. Rimuovere tutta la logica con `get_event_loop()` e `ThreadPoolExecutor`.

---

### WR-05: `_handle_agent_error()` espone `str(exc)` nel body della risposta HTTP 500

**File:** `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py:210-215`

**Issue:** Il body della risposta 500 contiene `{"error": str(exc), "thread_id": ...}`.
In produzione, `str(exc)` può includere dettagli interni: DSN del database, path del
filesystem, nomi di classi interne, stack trace parziali — tutti utili per un attaccante.
Il pattern è ereditato da `maintenance_agents.py` (Phase 7) e replicato invariato nel
router della Phase 8.

**Fix:** Restituire un messaggio generico nei casi 500; loggare il dettaglio lato server:
```python
def _handle_agent_error(exc: Exception, thread_id: str) -> JSONResponse:
    logger.error(
        "knowledge_agent_invocation_error",
        thread_id=thread_id,
        error=str(exc),      # solo nel log server-side
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_agent_error", "thread_id": thread_id},
    )
```

---

### Info

---

### IN-01: `sections_en` di `SOPDraft` usa chiavi italiane come chiavi del dict

**File:** `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/translator.py:177`

**Issue:** `SOPTranslator.translate()` popola `sections_en[it_key]` (es. `sections_en["Scopo"]`)
anziché `sections_en[en_key]` (es. `sections_en["Purpose"]`). Il validatore di `SOPDraft`
controlla che `sections_en` contenga tutte le `SECTION_KEYS_IT` (italiano), quindi il
codice non crasha, ma la naming è semanticamente ingannevole: un dict chiamato `sections_en`
con chiavi italiane confonde chi legge il codice e potrebbe causare regressioni future
(es. un consumer che si aspetti le chiavi EN).

**Fix (solo nomenclatura):** O aggiornare `_check_sections` di `SOPDraft` per accettare
chiavi EN in `sections_en`, oppure documentare esplicitamente la convenzione nel docstring
del modello e nella firma di `translate()`.

---

### IN-02: `ShiftHandoverCompileRequest` non include `boundary_label` — report con etichetta vuota

**File:** `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py:71-95`

**Issue:** Il modello di richiesta HTTP non espone `boundary_label` (es. `"06:00-14:00"`).
L'agente fa fallback a `state.get("boundary_label", "")` producendo un `HandoverReport`
con `boundary_label=""`. I display HITL mostrano un turno senza etichetta, rendendo
più difficile la revisione da parte del supervisore.

**Fix:** Aggiungere il campo opzionale al modello e propagarlo nello state:
```python
boundary_label: str = Field(
    default="",
    max_length=64,
    description="Human-readable shift label (e.g. '06:00-14:00')",
)
# nello state dict:
"boundary_label": body.boundary_label,
```

---

_Reviewed: 2026-05-24T14:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
