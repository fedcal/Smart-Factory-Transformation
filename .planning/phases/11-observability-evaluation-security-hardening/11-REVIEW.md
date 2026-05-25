---
phase: 11-observability-evaluation-security-hardening
reviewed: 2026-05-25T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py
  - services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py
  - packages/sft-agents/src/sft_agents/otel/nats_carrier.py
  - packages/sft-agents/src/sft_agents/otel/provider.py
  - apps/api-gateway/src/svc_api_gateway/nats_publisher.py
  - packages/sft-agents/src/sft_agents/runtime/agent_runner.py
  - tests/eval/conftest.py
  - tests/eval/test_rag_ci_gate.py
  - tests/eval/test_agent_eval.py
  - tests/security/test_prompt_injection.py
  - tests/security/test_ot_bridge_guard.py
  - apps/api-gateway/src/svc_api_gateway/security/jwt.py
  - apps/api-gateway/src/svc_api_gateway/routers/auth.py
  - apps/api-gateway/src/svc_api_gateway/security/rbac.py
  - packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py
  - .github/workflows/ci.yml
findings:
  critical: 4
  warning: 5
  info: 2
  total: 11
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-05-25
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

---

## Sommario

La Phase 11 implementa OTEL trace propagation, un CI gate per la valutazione RAG/agenti, la sanitizzazione anti-prompt-injection nel pipeline di ingest, la guardia AST sul bridge OT, il ruolo auditor RBAC e l'audit log per i documenti restricted. Il cablaggio dei moduli principali (sanitizer, carrier NATS, provider OTEL, retrieval pipeline) è corretto sul piano architetturale. Emergono però quattro difetti critici: (1) i test SEC-04 e SEC-06 non sono eseguiti in CI (il gate di sicurezza è quindi puramente locale); (2) la guardia AST del bridge OT non rileva tutti i pattern di write OPC-UA (manca `call_method` nel grep CI e manca `set_value` nell'AST pytest); (3) il singleton del TracerProvider OTEL non è thread-safe; (4) il ruolo `auditor` e i ruoli `shift-supervisor`/`admin` mancano completamente da `ROLE_TO_ACL`, causando un `ValueError` fail-closed se un utente autenticato tenta il retrieval RAG. Ci sono inoltre cinque warning, tra cui threshold SC-2 discordanti tra docstring e implementazione, e asserzioni di test con pattern OR che rendono i test parzialmente tautologici.

---

## Critical Issues

### CR-01: I test SEC-04 e SEC-06 non sono eseguiti in CI — gate di sicurezza non enforced

**File:** `.github/workflows/ci.yml:165`

**Issue:** Il passo "Run eval CI gate" esegue esclusivamente `pytest tests/eval/ -x -q`. I test in `tests/security/` (SEC-04 `test_prompt_injection.py` e SEC-06 `test_ot_bridge_guard.py`) non sono invocati da nessuno step del workflow. `tests/` non è un progetto Nx, quindi nemmeno l'"Nx Affected Test" li esegue. La garanzia che la sanitizzazione anti-injection sia cablata al pipeline e che il bridge OT non contenga write API è verificata solo localmente dallo sviluppatore.

**Fix:** Aggiungere un passo esplicito in `ci.yml` dopo il gate eval:

```yaml
- name: Run security gate (SEC-04 / SEC-06)
  # Non-skippable: nessun continue-on-error / || true
  run: uv run --python 3.12 python -m pytest tests/security/ -x -q
```

---

### CR-02: Singleton TracerProvider non thread-safe — doppia inizializzazione possibile

**File:** `packages/sft-agents/src/sft_agents/otel/provider.py:52-83`

**Issue:** Il pattern check-then-act sul flag modulo-level `_initialized` non è atomico in ambiente multi-thread. Due thread possono superare il controllo `if _initialized and _provider_instance is not None` nello stesso istante, prima che uno dei due abbia impostato `_initialized = True`. Entrambi chiamano `trace.set_tracer_provider(provider)` e `provider.add_span_processor(BatchSpanProcessor(exporter))`, creando due BatchSpanProcessor con due connessioni gRPC aperte verso Tempo. Il GIL Python non protegge blocchi check-then-act composti.

**Fix:** Usare `threading.Lock` per rendere atomica la sezione critica:

```python
import threading
_lock = threading.Lock()
_initialized: bool = False
_provider_instance: TracerProvider | None = None

def setup_tracer_provider(service_name: str) -> TracerProvider:
    global _initialized, _provider_instance
    with _lock:
        if _initialized and _provider_instance is not None:
            return _provider_instance
        # ... resto dell'inizializzazione ...
        _initialized = True
        _provider_instance = provider
    return provider
```

---

### CR-03: Ruoli `auditor`, `shift-supervisor`, `admin` assenti da `ROLE_TO_ACL` — `ValueError` fail-closed per utenti legittimi

**File:** `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:64-71`

**Issue:** `ROLE_TO_ACL` mappa solo i ruoli `operator`, `technician`, `supervisor`, `manager`, `engineer`, `safety`. Tre ruoli JWT effettivamente emessi dall'autenticazione sono assenti:
- `auditor` (aggiunto in Phase 11, SEC-03)
- `shift-supervisor` (ruolo canonico del JWT, non `supervisor`)
- `admin`

Quando `build_acl_filter(user_roles)` riceve uno di questi ruoli, `frozenset().union(*(ROLE_TO_ACL.get(r, frozenset()) for r in user_roles))` produce `frozenset()` vuoto, e la funzione solleva `ValueError: No ACL levels resolved`. L'utente `auditor@mantis.it` autenticato con successo otterrà un errore 500 a ogni ricerca RAG. Analogamente per `admin@mantis.it` e `supervisor@mantis.it` (che nel JWT ha ruolo `shift-supervisor`).

**Fix:**

```python
ROLE_TO_ACL: dict[str, frozenset[str]] = {
    "operator":        frozenset({"public"}),
    "technician":      frozenset({"public", "internal"}),
    "supervisor":      frozenset({"public", "internal"}),        # esistente
    "shift-supervisor": frozenset({"public", "internal"}),       # AGGIUNGERE: JWT canonical
    "manager":         frozenset({"public", "internal", "restricted"}),
    "engineer":        frozenset({"public", "internal", "restricted"}),
    "safety":          frozenset({"public", "internal", "restricted"}),
    "admin":           frozenset({"public", "internal", "restricted"}),   # AGGIUNGERE
    "auditor":         frozenset({"public", "internal", "restricted"}),   # AGGIUNGERE (SEC-03)
}
```

Verificare con i requisiti RBAC quali livelli ACL spettano ad `auditor` (read-only su tutti i livelli è il mapping più coerente con il ruolo "audit access").

---

### CR-04: Guardia AST OT Bridge e grep CI usano pattern write OPC-UA non sovrapposti — buchi bidirezionali

**File:** `tests/security/test_ot_bridge_guard.py:21-25` e `.github/workflows/ci.yml:111-112`

**Issue:** I due strati di difesa SEC-06 usano set di pattern distinti e non complementari:

| Pattern | CI grep (ci.yml) | AST pytest |
|---------|-----------------|-----------|
| `write_value` | SI | SI |
| `write_attribute` (singolare) | SI | NO |
| `write_attributes` (plurale) | NO | SI |
| `set_attribute` | NO | SI |
| `call_method` | NO | SI |
| `set_value` | SI | NO |

Conseguenze:
1. `set_value` (asyncua Node.set_value, write semantics) passa il test pytest AST ma non il grep CI — poiché il test AST non è in CI (CR-01), questa API non è controllata da nessun gate CI.
2. `call_method` e `set_attribute` passano il grep CI ma non il test AST — dipendono dal test AST che però non è in CI.
3. Il grep CI usa `write_attribute` (singolare) che non è il nome esatto dell'API asyncua (`write_attributes` plurale); una stringa come `node.write_attributes(...)` passerebbe il grep senza essere catturata.

**Fix:** Allineare i due set di pattern e aggiungere `tests/security/` al CI (CR-01):

```yaml
# ci.yml — Gate 3 aggiornato
! grep -rE "(set_value|write_attribute|write_attributes|set_attribute|call_method|write_value)" services/ot-bridge/src/
```

```python
# test_ot_bridge_guard.py
_WRITE_PATTERNS: frozenset[str] = frozenset({
    "write_value",
    "write_attributes",
    "set_attribute",
    "call_method",
    "set_value",        # AGGIUNGERE — asyncua Node.set_value() ha write semantics
})
```

---

## Warnings

### WR-01: Docstring del test di context_precision afferma soglia 0.75 ma il codice usa 0.35 — documenta requisito falso

**File:** `tests/eval/test_rag_ci_gate.py:140`

**Issue:** Il docstring di `test_context_precision_above_threshold` (riga 140) recita `"context_precision media sul dataset golden deve essere >= 0.75 (SC-2)"`. La costante effettiva è `CONTEXT_PRECISION_THRESHOLD = 0.35` (riga 50). Il requisito SC-2 ("hallucination rate >5% OR answer relevance <0.75") non corrisponde al threshold 0.35. Chi legge il test crede che il gate stia verificando 0.75 quando in realtà il controllo effettivo è 0.35 — un gate più di due volte più lasco. Stessa discrepanza in `test_agent_eval.py` dove `CONTEXT_PRECISION_THRESHOLD = 0.30`.

**Fix:**

```python
# Aggiornare il docstring per riflettere il threshold reale e la motivazione
def test_context_precision_above_threshold(self, ground_truth_dataset):
    """context_precision token-level media >= 0.35 (calibrato sul dataset SFT tecnico).
    
    Nota: il threshold 0.35 (non 0.75 SC-2) riflette la metrica token-overlap custom —
    non equivale alla AnswerRelevancyMetric di SC-2 che usa il judge DeepEval.
    """
```

---

### WR-02: Asserzioni tautologiche in `test_sanitize_strips_system_colon_pattern` e `test_sanitize_strips_html_tags`

**File:** `tests/security/test_prompt_injection.py:59` e `tests/security/test_prompt_injection.py:83`

**Issue 1 (riga 59):** Il test `test_sanitize_strips_system_colon_pattern` verifica:
```python
assert "you are now a malicious assistant" not in result.lower() or "[REDACTED]" in result
```
Se il pattern `system:` viene rimosso ma `you are now a` sopravvive, il risultato contiene `"[REDACTED] you are now a malicious assistant"`. L'asserzione OR passa (`[REDACTED]` in result è True) anche se il payload "you are now a" è ancora presente. Il test non rileva il fallimento parziale della sanitizzazione.

**Issue 2 (riga 83):** Il test `test_sanitize_strips_html_tags` verifica:
```python
assert "alert" not in result or "script" not in result
```
`bleach.clean(tags=[], strip=True)` rimuove i tag HTML ma lascia il contenuto del tag. Quindi `<script>alert('xss')</script>` diventa `alert('xss')` — `alert` sopravvive nel testo. La seconda clausola (`"script" not in result`) è sempre True dopo bleach (il tag è rimosso), rendendo l'asserzione OR sempre True indipendentemente dalla presenza del payload.

**Fix:**

```python
# riga 59: asserzione distinta per ogni pattern
assert "you are now a malicious assistant" not in result.lower(), (
    "Injection 'you are now a' sopravvissuta dopo sanitizzazione 'system:'"
)

# riga 83: verificare che il contenuto del tag script sia rimosso
assert "alert" not in result, (
    "Contenuto del tag script ('alert') sopravvissuto — bleach strip non rimuove il contenuto"
)
# Nota: se questo test fallisce, il problema è nel design del sanitizer,
# non nel test. bleach.clean(strip=True) non rimuove il contenuto dei tag.
# Considerare l'uso di html.parser per estrarre solo il testo.
```

---

### WR-03: Audit per chunk restricted scritto anche per hit pre-top-k mai restituiti all'utente

**File:** `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:341-351`

**Issue:** `_write_restricted_audit` riceve `fused_hits` (lista completa Qdrant, prima del rerank e del top-k slicing). Se un chunk `restricted` è in posizione 11-20 nel fused result ma l'utente riceve solo i primi `k=5`, viene scritto un audit row che afferma un accesso a chunk che l'utente non ha mai visto. In un contesto di audit trail legale/compliance, questo produce falsi positivi potenzialmente fuorvianti (il log attesta accessi che non sono avvenuti a livello applicativo).

**Fix:** Passare `top_k` invece di `fused_hits` all'audit writer, oppure distinguere chiaramente nel log se il chunk era nel set restituito o solo nel prefetch:

```python
# Solo chunk restricted effettivamente restituiti:
returned_hit_ids = {hit.id for hit, _ in top_k}
restricted_returned = [h for h in fused_hits if h.id in returned_hit_ids
                       and (h.payload or {}).get("acl_level") == "restricted"]
# oppure documentare esplicitamente la scelta di auditare il prefetch completo
```

---

### WR-04: `test_auditor_login_returns_valid_jwt` è uno stub vuoto — il test non testa nulla

**File:** `apps/api-gateway/tests/test_rbac_auditor.py:37-39`

**Issue:**

```python
def test_auditor_login_returns_valid_jwt(app_with_mocks, anyio_backend):
    """POST /auth/login con auditor@mantis.it deve restituire JWT con role=auditor."""
    pass  # usare test HTTP inline per evitare dipendenza da anyio fixture
```

Il test è un `pass` e viene sempre segnato come "passed" da pytest, creando una falsa garanzia di copertura. Il test successivo (`test_auditor_jwt_contains_role_claim`) copre lo stesso scenario con `@pytest.mark.anyio` — il test stub dovrebbe essere eliminato o completato.

**Fix:** Rimuovere il test stub o sostituirlo con un test funzionale:

```python
# Eliminare completamente:
# def test_auditor_login_returns_valid_jwt(app_with_mocks, anyio_backend):
#     pass

# Il test test_auditor_jwt_contains_role_claim già copre lo stesso scenario.
```

---

### WR-05: Path relativo in `test_ot_bridge_guard.py` e `test_sc3_pipeline_wiring_sanitizes_before_embedding` dipendente da CWD

**File:** `tests/security/test_ot_bridge_guard.py:17` e `tests/security/test_prompt_injection.py:218`

**Issue:** Entrambi i test usano path relativi al CWD corrente:

```python
# test_ot_bridge_guard.py:17
_OT_BRIDGE_SRC = pathlib.Path("services/ot-bridge/src/svc_ot_bridge")

# test_prompt_injection.py:218
pipeline_path = pathlib.Path("services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py")
```

Se pytest viene invocato da una directory diversa dalla root del progetto (es. `cd services/knowledge-ingest && python -m pytest`), i path non esistono e il test fallisce con un `FileNotFoundError` / `AssertionError` prima di eseguire qualsiasi logica. Il conftest radice `tests/conftest.py` usa correttamente `pathlib.Path(__file__).parent.parent / ...` — questo pattern dovrebbe essere replicato.

**Fix:**

```python
# test_ot_bridge_guard.py
import pathlib
_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
_OT_BRIDGE_SRC = _REPO_ROOT / "services" / "ot-bridge" / "src" / "svc_ot_bridge"

# test_prompt_injection.py
_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
pipeline_path = _REPO_ROOT / "services" / "knowledge-ingest" / "src" / "svc_knowledge_ingest" / "pipeline.py"
```

---

## Info

### IN-01: Il sanitizer non copre varianti unicode/homoglyph delle keyword di injection

**File:** `services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py:42-50`

**Issue:** I pattern regex usano `re.IGNORECASE` ma non normalizzano Unicode prima della corrispondenza. Un attaccante sofisticato potrebbe usare caratteri Unicode visualmente simili (es. Cyrillic "о" invece di Latin "o" in "ignore", o caratteri zero-width tra le lettere) per bypassare il denylist. Il non-breaking space (` `) è corrispondito da `\s` in Python, quindi il pattern `ignore\s+previous` cattura `ignore previous`. Ma i caratteri zero-width (`​`, `‌`) NON sono corrisponditi da `\s`.

**Nota:** Per un sistema industriale locale con documenti in italiano questo rischio è basso, ma va documentato come limitazione nota.

**Fix:** Aggiungere normalizzazione Unicode prima della sanitizzazione:

```python
import unicodedata

def sanitize_document(text: str) -> str:
    # Normalizzazione Unicode NFKC: decompone e ricompone caratteri equivalenti
    result = unicodedata.normalize("NFKC", text)
    # ... resto della pipeline ...
```

---

### IN-02: `NatsHeaderCarrier` modifica il dict di input in-place (`inject` lo muta) — violazione immutability convention

**File:** `packages/sft-agents/src/sft_agents/otel/nats_carrier.py:41`

**Issue:** Il docstring afferma `"Viene modificato in-place da inject"`. Il coding style del progetto richiede immutabilità (`NEVER mutate existing ones`). `publish_agent_command` in `nats_publisher.py` crea correttamente un nuovo dict `headers: dict[str, str] = {}` prima di passarlo al carrier, quindi nella pratica non muta nessun dict esterno. Ma il design permette che un chiamante passi un dict pre-esistente che verrebbe mutato. Il contratto non è chiaro.

**Fix:** Aggiungere una copia difensiva nel costruttore per garantire immutabilità del dict originale:

```python
def __init__(self, headers: dict[str, str]) -> None:
    self._headers = dict(headers)  # copia difensiva
```

Aggiornare il docstring rimuovendo il warning "Viene modificato in-place".

---

_Reviewed: 2026-05-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
